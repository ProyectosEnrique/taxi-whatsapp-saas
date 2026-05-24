"""
Endpoints para clientes: auth, solicitar viaje, tracking, historial.
Rutas: /api/v1/customer/*
"""
import logging
import math
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Customer, Driver, Trip, TripRating, TripStatus, TaxiGroup
from ..auth import hash_password, verify_password, create_token, get_current_customer
from ..fare_service import get_fare_config, calculate_fare

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/customer", tags=["customer"])


# ── Helpers ───────────────────────────────────────────────────────────────────

def _haversine_km(lat1, lon1, lat2, lon2) -> float:
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.asin(math.sqrt(a))


def _trip_to_dict(trip: Trip, driver: Driver | None = None) -> dict:
    d = {
        "ride_id":      trip.trip_id,
        "status":       trip.status.value if trip.status else "requested",
        "origin":       {"address": trip.origin_address, "lat": float(trip.origin_lat or 0), "lng": float(trip.origin_lng or 0)},
        "destination":  {"address": trip.destination_address, "lat": float(trip.destination_lat or 0), "lng": float(trip.destination_lng or 0)},
        "total_fare":   float(trip.fare or 0),
        "distance_km":  float(trip.distance_km or 0),
        "duration_minutes": max(5, int(float(trip.distance_km or 0) * 2.5)),
        "payment_method": trip.payment_method,
        "payment_status": trip.payment_status,
        "created_at":   trip.created_at.isoformat() if trip.created_at else None,
        "scheduled_at":          trip.scheduled_at.isoformat() if trip.scheduled_at else None,
        "preferred_driver_name": trip.preferred_driver_name,
        "preferred_driver_phone":trip.preferred_driver_phone,
        "driver": None,
    }
    if driver:
        d["driver"] = {
            "name":   driver.name,
            "phone":  driver.phone,
            "rating": float(driver.rating or 5.0),
            "current_lat": float(driver.current_lat or 0),
            "current_lon": float(driver.current_lng or 0),
            "vehicle": {
                "brand":  driver.vehicle_brand,
                "model":  driver.vehicle_model,
                "plates": driver.vehicle_plates,
                "color":  driver.vehicle_color,
            },
        }
    return d


# ── Auth ──────────────────────────────────────────────────────────────────────

@router.post("/register")
def register(payload: dict, db: Session = Depends(get_db)):
    phone    = (payload.get("phone") or "").strip()
    password = payload.get("password") or ""
    name     = payload.get("name") or ""
    if not phone or not password:
        raise HTTPException(400, "phone y password requeridos")
    if db.query(Customer).filter(Customer.phone == phone).first():
        raise HTTPException(409, "Teléfono ya registrado")
    customer = Customer(phone=phone, name=name, password_hash=hash_password(password))
    db.add(customer)
    db.commit()
    db.refresh(customer)
    token = create_token(customer.phone, "customer")
    return {"token": token, "customer": {"id": customer.id, "phone": customer.phone, "name": customer.name}}


@router.post("/login")
def login(payload: dict, db: Session = Depends(get_db)):
    phone    = (payload.get("phone") or "").strip()
    password = payload.get("password") or ""
    customer = db.query(Customer).filter(Customer.phone == phone).first()
    if not customer or not verify_password(password, customer.password_hash):
        raise HTTPException(401, "Credenciales incorrectas")
    token = create_token(customer.phone, "customer")
    return {"token": token, "customer": {"id": customer.id, "phone": customer.phone, "name": customer.name}}


@router.post("/logout")
def logout():
    return {"status": "ok"}


@router.get("/verify")
def verify(current: Customer = Depends(get_current_customer)):
    return {"valid": True, "customer": {"id": current.id, "phone": current.phone, "name": current.name}}


@router.get("/profile")
def get_profile(current: Customer = Depends(get_current_customer)):
    return {"id": current.id, "phone": current.phone, "name": current.name, "email": current.email}


@router.put("/profile")
def update_profile(payload: dict, current: Customer = Depends(get_current_customer), db: Session = Depends(get_db)):
    if "name" in payload:
        current.name = payload["name"]
    if "email" in payload:
        current.email = payload["email"]
    db.commit()
    return {"id": current.id, "phone": current.phone, "name": current.name, "email": current.email}


# ── Rides ─────────────────────────────────────────────────────────────────────

@router.post("/rides/estimate")
def estimate_fare(payload: dict, current: Customer = Depends(get_current_customer), db: Session = Depends(get_db)):
    origin      = payload.get("origin", {})
    destination = payload.get("destination", {})
    def _lng(obj): return float(obj.get("lng") or obj.get("lon") or 0)
    try:
        dist = _haversine_km(
            float(origin.get("lat", 0)), _lng(origin),
            float(destination.get("lat", 0)), _lng(destination),
        )
    except Exception:
        dist = 3.0
    dist  = max(dist, 1.0)
    cfg   = get_fare_config(db)
    fare  = calculate_fare(cfg, dist)
    mins  = max(5, int(dist * 2.5))
    return {"estimate": {"fare": fare, "distance_km": round(dist, 2), "duration_minutes": mins, "currency": "MXN"}}


@router.post("/rides/request")
def request_ride(payload: dict, current: Customer = Depends(get_current_customer), db: Session = Depends(get_db)):
    origin      = payload.get("origin", {})
    destination = payload.get("destination", {})

    def _lng(obj): return obj.get("lng") or obj.get("lon")
    try:
        dist = _haversine_km(
            float(origin.get("lat", 0)), float(_lng(origin) or 0),
            float(destination.get("lat", 0)), float(_lng(destination) or 0),
        )
    except Exception:
        dist = 3.0
    dist = max(dist, 1.0)
    cfg  = get_fare_config(db)
    fare = calculate_fare(cfg, dist)

    trip = Trip(
        customer_phone      = current.phone,
        customer_name       = current.name,
        origin_address      = origin.get("address", ""),
        destination_address = destination.get("address", ""),
        origin_lat          = origin.get("lat"),
        origin_lng          = _lng(origin),
        destination_lat     = destination.get("lat"),
        destination_lng     = _lng(destination),
        fare                = fare,
        distance_km         = round(dist, 2),
        payment_method      = payload.get("payment_method", "cash"),
        status              = TripStatus.REQUESTED,
        payment_status      = "pending",
    )
    db.add(trip)
    db.commit()
    db.refresh(trip)
    logger.info(f"[Rides] Viaje {trip.trip_id} solicitado por {current.phone}")
    return {"ride": _trip_to_dict(trip)}


@router.get("/rides/active")
def get_active_ride(current: Customer = Depends(get_current_customer), db: Session = Depends(get_db)):
    trip = (
        db.query(Trip)
        .filter(
            Trip.customer_phone == current.phone,
            Trip.status.in_([TripStatus.REQUESTED, TripStatus.CONFIRMED, TripStatus.IN_PROGRESS]),
        )
        .order_by(Trip.created_at.desc())
        .first()
    )
    if not trip:
        return {"ride": None}
    driver = db.query(Driver).filter(Driver.phone == trip.driver_phone).first() if trip.driver_phone else None
    return {"ride": _trip_to_dict(trip, driver)}


@router.get("/rides/history")
def get_history(current: Customer = Depends(get_current_customer), db: Session = Depends(get_db)):
    trips = (
        db.query(Trip)
        .filter(Trip.customer_phone == current.phone)
        .order_by(Trip.created_at.desc())
        .limit(20)
        .all()
    )
    return {"rides": [_trip_to_dict(t) for t in trips]}


@router.post("/rides/schedule")
def schedule_ride(payload: dict, current: Customer = Depends(get_current_customer), db: Session = Depends(get_db)):
    origin      = payload.get("origin", {})
    destination = payload.get("destination", {})
    scheduled_at_str = payload.get("scheduled_at")

    if not scheduled_at_str:
        raise HTTPException(400, "scheduled_at es requerido (ISO 8601)")

    try:
        scheduled_at = datetime.fromisoformat(scheduled_at_str.replace("Z", "+00:00"))
        if scheduled_at.tzinfo is None:
            scheduled_at = scheduled_at.replace(tzinfo=timezone.utc)
    except ValueError:
        raise HTTPException(400, "Formato de fecha inválido. Usa ISO 8601")

    min_advance = datetime.now(timezone.utc) + timedelta(minutes=30)
    if scheduled_at < min_advance:
        raise HTTPException(400, "El viaje debe programarse con al menos 30 minutos de anticipación")

    def _lng(obj): return obj.get("lng") or obj.get("lon")
    try:
        dist = _haversine_km(
            float(origin.get("lat", 0)), float(_lng(origin) or 0),
            float(destination.get("lat", 0)), float(_lng(destination) or 0),
        )
    except Exception:
        dist = 3.0
    dist = max(dist, 1.0)
    cfg  = get_fare_config(db)
    fare = calculate_fare(cfg, dist)

    # Pre-asignar al conductor preferido del cliente
    preferred = None
    if current.preferred_driver_id:
        preferred = db.query(Driver).filter(Driver.id == current.preferred_driver_id).first()

    trip = Trip(
        customer_phone         = current.phone,
        customer_name          = current.name,
        origin_address         = origin.get("address", ""),
        destination_address    = destination.get("address", ""),
        origin_lat             = origin.get("lat"),
        origin_lng             = _lng(origin),
        destination_lat        = destination.get("lat"),
        destination_lng        = _lng(destination),
        fare                   = fare,
        distance_km            = round(dist, 2),
        payment_method         = payload.get("payment_method", "cash"),
        status                 = TripStatus.SCHEDULED,
        payment_status         = "pending",
        scheduled_at           = scheduled_at,
        driver_phone           = preferred.phone if preferred else None,
        driver_name            = preferred.name  if preferred else None,
        preferred_driver_phone = preferred.phone if preferred else None,
        preferred_driver_name  = preferred.name  if preferred else None,
    )
    db.add(trip)
    db.commit()
    db.refresh(trip)
    logger.info(f"[Rides] Viaje programado {trip.trip_id} para {scheduled_at.isoformat()} → conductor: {preferred.name if preferred else 'pool'}")
    return {"ride": _trip_to_dict(trip)}


@router.get("/rides/scheduled")
def get_scheduled_rides(current: Customer = Depends(get_current_customer), db: Session = Depends(get_db)):
    trips = (
        db.query(Trip)
        .filter(
            Trip.customer_phone == current.phone,
            Trip.status.in_([TripStatus.SCHEDULED, TripStatus.DRIVER_RELEASED]),
        )
        .order_by(Trip.scheduled_at.asc())
        .all()
    )
    return {"rides": [_trip_to_dict(t) for t in trips]}


@router.post("/rides/{ride_id}/reassign")
def reassign_ride(ride_id: str, current: Customer = Depends(get_current_customer), db: Session = Depends(get_db)):
    """El cliente acepta que se asigne a otro conductor (después de que el preferido liberó)."""
    trip = db.query(Trip).filter(Trip.trip_id == ride_id, Trip.customer_phone == current.phone).first()
    if not trip:
        raise HTTPException(404, "Viaje no encontrado")
    if trip.status != TripStatus.DRIVER_RELEASED:
        raise HTTPException(400, "El viaje no está en estado de liberación")
    trip.status      = TripStatus.SCHEDULED
    trip.driver_phone = None
    trip.driver_name  = None
    db.commit()
    logger.info(f"[Rides] Cliente {current.phone} acepta reasignación del viaje {ride_id} al pool")
    return {"success": True, "ride": _trip_to_dict(trip)}


@router.post("/preferred-driver")
def set_preferred_driver(payload: dict, current: Customer = Depends(get_current_customer), db: Session = Depends(get_db)):
    """Guarda el conductor preferido del cliente (se llama tras escanear el QR del taxi)."""
    driver_code = (payload.get("driver_code") or "").strip()
    if not driver_code:
        raise HTTPException(400, "driver_code requerido")
    driver = db.query(Driver).filter(Driver.driver_code == driver_code).first()
    if not driver:
        raise HTTPException(404, "Conductor no encontrado")
    current.preferred_driver_id = driver.id
    db.commit()
    return {"success": True, "driver": {"name": driver.name, "phone": driver.phone}}


@router.get("/rides/{ride_id}")
def get_ride(ride_id: str, current: Customer = Depends(get_current_customer), db: Session = Depends(get_db)):
    trip = db.query(Trip).filter(Trip.trip_id == ride_id, Trip.customer_phone == current.phone).first()
    if not trip:
        raise HTTPException(404, "Viaje no encontrado")
    driver = db.query(Driver).filter(Driver.phone == trip.driver_phone).first() if trip.driver_phone else None
    return {"ride": _trip_to_dict(trip, driver)}


@router.post("/rides/{ride_id}/cancel")
def cancel_ride(ride_id: str, payload: dict, current: Customer = Depends(get_current_customer), db: Session = Depends(get_db)):
    trip = db.query(Trip).filter(Trip.trip_id == ride_id, Trip.customer_phone == current.phone).first()
    if not trip:
        raise HTTPException(404, "Viaje no encontrado")
    if trip.status == TripStatus.IN_PROGRESS:
        raise HTTPException(400, "No se puede cancelar un viaje en curso")
    if trip.status == TripStatus.COMPLETED:
        raise HTTPException(400, "El viaje ya fue completado")
    trip.status              = TripStatus.CANCELLED
    trip.cancellation_reason = payload.get("reason", "Cliente canceló")
    trip.cancelled_at        = datetime.now(timezone.utc)
    db.commit()
    return {"success": True}


@router.post("/rides/{ride_id}/rate")
def rate_ride(ride_id: str, payload: dict, current: Customer = Depends(get_current_customer), db: Session = Depends(get_db)):
    trip = db.query(Trip).filter(Trip.trip_id == ride_id, Trip.customer_phone == current.phone).first()
    if not trip:
        raise HTTPException(404, "Viaje no encontrado")
    if trip.status != TripStatus.COMPLETED:
        raise HTTPException(400, "Solo se pueden calificar viajes completados")
    if db.query(TripRating).filter(TripRating.trip_id == ride_id).first():
        raise HTTPException(409, "Este viaje ya fue calificado")

    stars = int(payload.get("rating", 5))
    stars = max(1, min(5, stars))
    rating = TripRating(trip_id=ride_id, stars=stars, comment=payload.get("comment", ""))
    db.add(rating)

    # Actualizar rating promedio del conductor
    if trip.driver_phone:
        driver = db.query(Driver).filter(Driver.phone == trip.driver_phone).first()
        if driver:
            all_ratings = db.query(TripRating).join(
                Trip, TripRating.trip_id == Trip.trip_id
            ).filter(Trip.driver_phone == trip.driver_phone).all()
            avg = (sum(r.stars for r in all_ratings) + stars) / (len(all_ratings) + 1)
            driver.rating = round(avg, 2)

    db.commit()
    return {"success": True}
