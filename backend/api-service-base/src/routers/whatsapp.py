"""
Endpoints internos para la integración WhatsApp ↔ taxi-api.
Protegidos con X-Taxi-Internal-Key.
"""
import logging
import math
import re
import uuid

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Customer, Driver, Trip, TripStatus
from ..auth import hash_password
from ..fare_service import get_fare_config, calculate_fare
from ..config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/whatsapp", tags=["whatsapp-internal"])

NOMINATIM_URL = "https://nominatim.openstreetmap.org"
_NOM_HEADERS = {"User-Agent": "TaxiApp/1.0"}

# Common Spanish place-name aliases that Nominatim doesn't index literally
_QUERY_SUBS = [
    (re.compile(r'\bcentral de autobuses\b', re.I), 'terminal autobuses'),
    (re.compile(r'\bcentral camionera\b', re.I), 'terminal autobuses'),
    (re.compile(r'\bcamionera central\b', re.I), 'terminal autobuses'),
    (re.compile(r'\bCAPU\b', re.I), 'terminal autobuses'),
    (re.compile(r'\baeroporto\b', re.I), 'aeropuerto'),
    (re.compile(r'\bclinica\b', re.I), 'hospital'),
    (re.compile(r'\bIMSS\b'), 'Instituto Mexicano del Seguro Social'),
    (re.compile(r'\bISSTE\b'), 'ISSSTE'),
]

# Preposiciones iniciales que el cliente escribe pero confunden a Nominatim
# "En veneto 119 Celaya" → "veneto 119 Celaya"
_LEADING_PREP = re.compile(
    r'^(en|voy a|me lleva a|llévame a|llevame a|hasta|quiero ir a|ir a|al|a la|a)\s+',
    re.I,
)
# "col san cristobal en Salvatierra" → "col san cristobal, Salvatierra"
# Convierte " en <Ciudad>" al final de un segmento en ", <Ciudad>" para que el
# geocodificador pueda activar el shortcut calle+ciudad (requiere ≥ 3 partes).
_MID_EN = re.compile(r'\s+en\s+', re.I)


def _normalize_query(q: str) -> str:
    # 1. Quitar preposición inicial
    q = _LEADING_PREP.sub('', q).strip()
    # 2. Sustituir " en " interno por ", " para crear partes separadas por coma
    q = _MID_EN.sub(', ', q)
    # 3. Aliases de nombres de lugares
    for pattern, replacement in _QUERY_SUBS:
        q = pattern.sub(replacement, q)
    return q.strip()


def _parse_display_name(display_name: str) -> tuple[str, str]:
    """Returns (name, short_address) from a Nominatim display_name string."""
    parts = [p.strip() for p in display_name.split(",") if p.strip()]
    name = parts[0] if parts else ""
    # If first part is too short (e.g. "Hola"), combine with second
    if len(name) < 4 and len(parts) > 1:
        name = f"{parts[0]}, {parts[1]}"
    short_address = ", ".join(p for p in parts[1:3] if len(p) > 2)
    return name, short_address


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
    driver_code = (payload.get("driver_code") or "").strip()
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
    if driver_code:
        driver = db.query(Driver).filter(Driver.driver_code == driver_code, Driver.is_active == True).first()
        if driver:
            customer.preferred_driver_id = driver.id
            db.commit()
    return {"customer_id": customer.id, "phone": customer.phone, "name": customer.name, "is_new": is_new}


@router.get("/driver/{driver_code}")
def get_driver_by_code(driver_code: str, db: Session = Depends(get_db), _=Depends(_auth)):
    driver = db.query(Driver).filter(Driver.driver_code == driver_code, Driver.is_active == True).first()
    if not driver:
        raise HTTPException(404, "Conductor no encontrado")
    return {"driver_code": driver.driver_code, "name": driver.name, "phone": driver.phone}


@router.get("/geocode")
async def geocode_address(
    q: str,
    lat: float | None = None,
    lon: float | None = None,
    _=Depends(_auth),
):
    ref_lat = lat if lat is not None else (settings.CITY_LAT if settings.CITY_LAT else None)
    ref_lon = lon if lon is not None else (settings.CITY_LNG if settings.CITY_LNG else None)

    # Build query variants: original + alias + simplificaciones progresivas
    import re as _re
    q_normalized = _normalize_query(q)
    _parts = [p.strip() for p in q.split(",") if p.strip()]
    queries = []
    # Variante calle+ciudad sin colonia intermedia — va primero porque Nominatim resuelve
    # calles específicas mejor sin la colonia en el medio.
    # Ej: "Rayando el sol 22, col san cristobal, Salvatierra Gto" → "Rayando el sol 22 Salvatierra Gto"
    if len(_parts) >= 3:
        q_street_city = f"{_parts[0]} {_parts[-1]}"
        queries.append(q_street_city)
    queries.append(q)
    if q_normalized.lower() != q.lower():
        queries.append(q_normalized)
    # Sin numero: "Calle Sol 22, Col Centro" -> "Calle Sol, Col Centro"
    q_no_num = _re.sub("[0-9]+", "", q).strip(" ,")
    if q_no_num and q_no_num.lower() != q.lower():
        queries.append(q_no_num)
    # Ultimas partes separadas por coma (colonia+ciudad, solo ciudad)
    if len(_parts) >= 2:
        queries.append(", ".join(_parts[-2:]))
    if _parts:
        queries.append(_parts[-1])
    # Deduplicar preservando orden
    _seen_q: set = set()
    queries = [x for x in queries if x.lower() not in _seen_q and not _seen_q.add(x.lower())]

    viewbox_str = None
    if ref_lat is not None and ref_lon is not None:
        d = settings.CITY_BBOX_DEG or 0.25
        viewbox_str = f"{ref_lon - d},{ref_lat - d},{ref_lon + d},{ref_lat + d}"

    items: list = []
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            for query_str in queries:
                # Attempt 1: viewbox estricto (bounded) — solo dentro de la ciudad de operación
                if viewbox_str:
                    params: dict = {
                        "q": query_str, "format": "json", "limit": 4,
                        "countrycodes": "mx", "addressdetails": 0,
                        "viewbox": viewbox_str, "bounded": 1,
                    }
                    resp = await client.get(f"{NOMINATIM_URL}/search", params=params, headers=_NOM_HEADERS)
                    resp.raise_for_status()
                    items = resp.json()
                    if items:
                        break

                # Attempt 2: búsqueda nacional sin restricción geográfica
                # Nota: no usamos viewbox "preference" porque sesga hacia calles con nombre
                # similar al municipio de destino (ej. "Calle Salvatierra" en Celaya
                # en lugar de la ciudad de Salvatierra, Gto.)
                params = {"q": query_str, "format": "json", "limit": 4, "countrycodes": "mx", "addressdetails": 0}
                resp = await client.get(f"{NOMINATIM_URL}/search", params=params, headers=_NOM_HEADERS)
                resp.raise_for_status()
                items = resp.json()
                if items:
                    break
    except Exception as e:
        raise HTTPException(503, f"Geocodificación no disponible: {e}")

    return {
        "results": [
            {
                "name": _parse_display_name(item.get("display_name", ""))[0],
                "short_address": _parse_display_name(item.get("display_name", ""))[1],
                "address": item.get("display_name", ""),
                "lat": float(item.get("lat", 0)),
                "lng": float(item.get("lon", 0)),
            }
            for item in items
        ]
    }


@router.get("/reverse-geocode")
async def reverse_geocode(
    lat: float,
    lon: float,
    _=Depends(_auth),
):
    """Convierte coordenadas GPS a una dirección legible."""
    params = {"lat": lat, "lon": lon, "format": "json", "addressdetails": 0}
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(f"{NOMINATIM_URL}/reverse", params=params, headers=_NOM_HEADERS)
            resp.raise_for_status()
            item = resp.json()
    except Exception as e:
        raise HTTPException(503, f"Geocodificación inversa no disponible: {e}")
    display = item.get("display_name", "")
    name, short_address = _parse_display_name(display)
    return {
        "name": name,
        "short_address": short_address,
        "address": display,
        "lat": lat,
        "lng": lon,
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
async def create_ride(payload: dict, db: Session = Depends(get_db), _=Depends(_auth)):
    from datetime import datetime as _dt
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

    # Viaje programado si viene scheduled_at
    scheduled_at_raw = payload.get("scheduled_at")
    scheduled_at = None
    trip_status = TripStatus.REQUESTED
    if scheduled_at_raw:
        try:
            scheduled_at = _dt.fromisoformat(scheduled_at_raw)
            trip_status = TripStatus.SCHEDULED
        except ValueError:
            logger.warning(f"[WA] scheduled_at inválido: {scheduled_at_raw!r} — creando viaje inmediato")

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
        status=trip_status,
        scheduled_at=scheduled_at,
        preferred_driver_phone=payload.get("preferred_driver_phone") or None,
        preferred_driver_name=payload.get("preferred_driver_name") or None,
    )
    db.add(trip)
    db.commit()
    db.refresh(trip)
    logger.info(f"[WA] Viaje {trip.trip_id} creado para {phone} (status={trip_status.value})")

    # Notificar a choferes online por Telegram
    try:
        from .telegram_bot import notify_drivers_new_ride
        await notify_drivers_new_ride(trip, db)
    except Exception as drv_err:
        logger.warning(f"[WA] Driver Telegram notify failed: {drv_err}")

    tracking_url = f"{settings.PUBLIC_URL}/seguimiento/{trip.trip_id}"

    # Notificar al operador por Telegram
    try:
        from ..services.telegram import send_to_operator
        maps_orig = (
            f"https://maps.google.com/?q={olat},{olng}" if (olat and olng) else "Sin coords"
        )
        maps_dest = f"https://maps.google.com/?q={dlat},{dlng}"
        label = "📅 PROGRAMADO" if scheduled_at else "🚖 INMEDIATO"
        msg = (
            f"{label} — <b>Viaje WhatsApp</b>\n"
            f"ID: <code>{trip.trip_id}</code>\n"
            f"Cliente: {c_name} | <code>{phone}</code>\n"
            f"📍 <a href='{maps_orig}'>Origen</a>: {trip.origin_address}\n"
            f"🏁 <a href='{maps_dest}'>Destino</a>: {trip.destination_address}\n"
            f"💰 Tarifa: ${fare:.2f} | {round(distance_km, 1)} km\n"
            f"🔍 <a href='{tracking_url}'>Seguimiento en vivo</a>"
        )
        if scheduled_at:
            msg += f"\n🕐 Hora: {scheduled_at.strftime('%d/%m %H:%M')}"
        await send_to_operator(msg)
    except Exception as tg_err:
        logger.warning(f"[WA] Telegram notify failed: {tg_err}")

    return {
        "ride_id": trip.trip_id,
        "status": trip.status.value,
        "fare": round(float(fare), 2),
        "distance_km": round(float(distance_km), 2),
        "origin_address": trip.origin_address,
        "destination_address": trip.destination_address,
        "scheduled_at": scheduled_at.isoformat() if scheduled_at else None,
        "tracking_url": tracking_url,
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
