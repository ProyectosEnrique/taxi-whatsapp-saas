"""
Endpoints internos para la integración WhatsApp ↔ taxi-api.
Protegidos con X-Taxi-Internal-Key.
"""
import logging
import math
import uuid

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Customer, Trip, TripStatus
from ..auth import hash_password
from ..fare_service import get_fare_config, calculate_fare
from ..config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/whatsapp", tags=["whatsapp-internal"])

NOMINATIM_URL = "https://nominatim.openstreetmap.org"
_NOM_HEADERS = {"User-Agent": "TaxiApp/1.0"}


def _auth(x_taxi_internal_key: str = Header(...)):
    if settings.WHATSAPP_SECRET and x_taxi_internal_key != settings.WHATSAPP_SECRET:
        raise HTTPException(403, "Clave interna inválida")


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    a = (math.sin(math.radians(lat2 - lat1) / 2) ** 2
         + math.cos(phi1) * math.cos(phi2)
         * math.sin(math.radians(lon2 - lon1) / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.post("/customer/init")
def customer_init(payload: dict, db: Session = Depends(get_db), _=Depends(_auth)):
    phone = (payload.get("phone") or "").strip()
    name = (payload.get("name") or "Cliente").strip()
    if not phone:
        raise HTTPException(400, "phone requerido")
    customer = db.query(Customer).filter(Customer.phone == phone).first()
    is_new = customer is None
    if is_new:
        pwd_seed = phone[-6:] if len(phone) >= 6 else "123456"
        customer = Customer(phone=phone, name=name, password_hash=hash_password(pwd_seed))
        db.add(customer)
        db.commit()
        db.refresh(customer)
    return {"customer_id": customer.id, "phone": customer.phone, "name": customer.name, "is_new": is_new}


@router.get("/geocode")
async def geocode_address(
    q: str,
    lat: float | None = None,
    lon: float | None = None,
    _=Depends(_auth),
):
    params: dict = {"q": q, "format": "json", "limit": 4, "countrycodes": "mx", "addressdetails": 0}
    if lat is not None and lon is not None:
        delta = 0.4
        params["viewbox"] = f"{lon - delta},{lat - delta},{lon + delta},{lat + delta}"
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(f"{NOMINATIM_URL}/search", params=params, headers=_NOM_HEADERS)
            resp.raise_for_status()
            items = resp.json()
    except Exception as e:
        raise HTTPException(503, f"Geocodificación no disponible: {e}")
    return {
        "results": [
            {
                "name": item.get("display_name", "").split(",")[0].strip(),
                "address": item.get("display_name", ""),
                "lat": float(item.get("lat", 0)),
                "lng": float(item.get("lon", 0)),
            }
            for item in items
        ]
    }


@router.post("/rides/estimate")
def estimate_fare(payload: dict, db: Session = Depends(get_db), _=Depends(_auth)):
    orig = payload.get("origin") or {}
    dest = payload.get("destination") or {}
    olat, olng = float(orig.get("lat") or 0), float(orig.get("lng") or 0)
    dlat, dlng = float(dest.get("lat") or 0), float(dest.get("lng") or 0)
    distance_km = _haversine_km(olat, olng, dlat, dlng) if (olat and dlat) else 5.0
    cfg = get_fare_config(db)
    fare = calculate_fare(cfg, distance_km)
    return {
        "fare": round(fare, 2),
        "distance_km": round(distance_km, 2),
        "duration_minutes": max(5, int(distance_km * 2.5)),
    }


@router.post("/rides/create")
def create_ride(payload: dict, db: Session = Depends(get_db), _=Depends(_auth)):
    phone = (payload.get("customer_phone") or "").strip()
    if not phone:
        raise HTTPException(400, "customer_phone requerido")
    orig = payload.get("origin") or {}
    dest = payload.get("destination") or {}
    if not dest:
        raise HTTPException(400, "destination requerido")

    customer = db.query(Customer).filter(Customer.phone == phone).first()
    c_name = (customer.name if customer else None) or payload.get("customer_name") or "Cliente WhatsApp"

    olat = float(orig.get("lat") or 0)
    olng = float(orig.get("lng") or 0)
    dlat = float(dest.get("lat") or 0)
    dlng = float(dest.get("lng") or 0)
    distance_km = _haversine_km(olat, olng, dlat, dlng) if (olat and dlat) else 5.0
    cfg = get_fare_config(db)
    fare = calculate_fare(cfg, distance_km)

    trip = Trip(
        trip_id=f"WA-{uuid.uuid4().hex[:8].upper()}",
        customer_phone=phone,
        customer_name=c_name,
        origin_address=orig.get("address") or "Punto de recogida (WhatsApp)",
        origin_lat=olat or None,
        origin_lng=olng or None,
        destination_address=dest.get("address", ""),
        destination_lat=dlat,
        destination_lng=dlng,
        fare=fare,
        distance_km=distance_km,
        payment_method=payload.get("payment_method", "cash"),
        payment_status="pending",
        status=TripStatus.REQUESTED,
    )
    db.add(trip)
    db.commit()
    db.refresh(trip)
    logger.info(f"[WA] Viaje {trip.trip_id} creado para {phone}")
    return {
        "ride_id": trip.trip_id,
        "status": trip.status.value,
        "fare": round(float(fare), 2),
        "distance_km": round(float(distance_km), 2),
        "origin_address": trip.origin_address,
        "destination_address": trip.destination_address,
    }


@router.get("/rides/{ride_id}")
def get_ride(ride_id: str, db: Session = Depends(get_db), _=Depends(_auth)):
    trip = db.query(Trip).filter(Trip.trip_id == ride_id).first()
    if not trip:
        raise HTTPException(404, "Viaje no encontrado")
    return {
        "ride_id": trip.trip_id,
        "status": trip.status.value,
        "fare": float(trip.fare or 0),
        "driver_name": trip.driver_name,
        "driver_phone": trip.driver_phone,
        "origin_address": trip.origin_address,
        "destination_address": trip.destination_address,
    }


@router.post("/rides/{ride_id}/cancel")
def cancel_ride(ride_id: str, db: Session = Depends(get_db), _=Depends(_auth)):
    trip = db.query(Trip).filter(Trip.trip_id == ride_id).first()
    if not trip:
        raise HTTPException(404, "Viaje no encontrado")
    if trip.status in (TripStatus.COMPLETED, TripStatus.CANCELLED):
        raise HTTPException(400, "El viaje ya está terminado")
    trip.status = TripStatus.CANCELLED
    db.commit()
    return {"success": True, "ride_id": ride_id}
