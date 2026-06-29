"""
Endpoints para conductores: auth, estado, ubicación, gestión de viajes.
Rutas: /api/v1/driver/*
"""
import logging
import os
import time
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from pathlib import Path

import httpx
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Driver, Trip, TripStatus, TaxiGroup
from ..auth import hash_password, verify_password, create_token, get_current_driver
from ..config import settings

logger = logging.getLogger(__name__)


def _notify_customer(phone: str, message: str) -> None:
    """Envía notificación proactiva al cliente vía WhatsApp gateway (fire-and-forget)."""
    gateway = settings.WHATSAPP_GATEWAY_URL
    secret = settings.WHATSAPP_SECRET
    if not gateway or not phone:
        return
    try:
        with httpx.Client(timeout=3.0) as client:
            client.post(
                f"{gateway}/notify/customer",
                json={"phone": phone, "message": message},
                headers={"X-Taxi-Internal-Key": secret},
            )
    except Exception as e:
        logger.warning(f"[Notify] No se pudo notificar a {phone}: {e}")
router = APIRouter(prefix="/api/v1/driver", tags=["driver"])


# ── Helpers ───────────────────────────────────────────────────────────────────

def _sf(val):
    """Return float(val) if val is set, else None — avoids sending 0.0 for missing coords."""
    return float(val) if val is not None else None


def _driver_to_dict(driver: Driver) -> dict:
    return {
        "id":        driver.id,
        "phone":     driver.phone,
        "name":      driver.name,
        "is_online": driver.is_online,
        "rating":    float(driver.rating or 5.0),
        "total_trips": driver.total_trips,
        "vehicle": {
            "brand":     driver.vehicle_brand,
            "model":     driver.vehicle_model,
            "plates":    driver.vehicle_plates,
            "color":     driver.vehicle_color,
            "year":      driver.vehicle_year,
            "photo_url": driver.vehicle_photo_url,
        },
        "location": {
            "lat": _sf(driver.current_lat),
            "lng": _sf(driver.current_lng),
        },
    }


def _trip_to_dict(trip: Trip) -> dict:
    distance = float(trip.distance_km or 0)
    return {
        "ride_id": trip.trip_id,
        "status":  trip.status.value if trip.status else "requested",
        # estructura anidada que espera el frontend
        "customer": {
            "name":  trip.customer_name or "Pasajero",
            "phone": trip.customer_phone or "",
        },
        "origin": {
            "address": trip.origin_address or "",
            "lat": _sf(trip.origin_lat),
            "lng": _sf(trip.origin_lng),
        },
        "destination": {
            "address": trip.destination_address or "",
            "lat": _sf(trip.destination_lat),
            "lng": _sf(trip.destination_lng),
        },
        "fare":             float(trip.fare or 0),
        "total_fare":       float(trip.fare or 0),        # alias para el frontend
        "distance_km":      distance,
        "duration_minutes": max(1, round(distance / 0.5)), # ~30 km/h en ciudad
        "expires_in":       30,                            # segundos para aceptar
        "payment_method":          trip.payment_method,
        "created_at":              trip.created_at.isoformat() if trip.created_at else None,
        "scheduled_at":            trip.scheduled_at.isoformat() if trip.scheduled_at else None,
        "preferred_driver_name":   trip.preferred_driver_name,
        "preferred_driver_phone":  trip.preferred_driver_phone,
    }


# ── Auth ──────────────────────────────────────────────────────────────────────

@router.post("/login")
def login(payload: dict, db: Session = Depends(get_db)):
    phone    = (payload.get("phone") or "").strip()
    password = payload.get("password") or ""
    driver   = db.query(Driver).filter(Driver.phone == phone).first()
    if not driver or not verify_password(password, driver.password_hash):
        raise HTTPException(401, "Credenciales incorrectas")
    token = create_token(driver.phone, "driver")
    return {"token": token, "driver": _driver_to_dict(driver)}


@router.post("/logout")
def logout(current: Driver = Depends(get_current_driver), db: Session = Depends(get_db)):
    current.is_online = False
    db.commit()
    return {"status": "ok"}


@router.get("/verify")
def verify(current: Driver = Depends(get_current_driver)):
    return {"valid": True, "driver": _driver_to_dict(current)}


@router.get("/profile")
def get_profile(current: Driver = Depends(get_current_driver)):
    return _driver_to_dict(current)


@router.put("/profile")
def update_profile(payload: dict, current: Driver = Depends(get_current_driver), db: Session = Depends(get_db)):
    for field in ("name", "vehicle_brand", "vehicle_model", "vehicle_plates", "vehicle_color", "vehicle_year"):
        if field in payload:
            setattr(current, field, payload[field])
    db.commit()
    return _driver_to_dict(current)


_UPLOAD_DIR = Path("/app/uploads/vehicles")
_ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
_MAX_SIZE = 5 * 1024 * 1024  # 5 MB


@router.post("/profile/vehicle-photo")
async def upload_vehicle_photo(
    file: UploadFile = File(...),
    current: Driver = Depends(get_current_driver),
    db: Session = Depends(get_db),
):
    if file.content_type not in _ALLOWED_TYPES:
        raise HTTPException(400, "Solo se permiten imágenes JPG, PNG o WebP")

    data = await file.read()
    if len(data) > _MAX_SIZE:
        raise HTTPException(400, "La imagen no puede superar 5 MB")

    _UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in (file.filename or "") else "jpg"
    safe_phone = current.phone.lstrip("+").replace(" ", "")
    filename = f"{safe_phone}_{int(time.time())}.{ext}"
    dest = _UPLOAD_DIR / filename
    dest.write_bytes(data)

    # Borrar foto anterior si existe y es diferente
    if current.vehicle_photo_url:
        old_name = current.vehicle_photo_url.rsplit("/", 1)[-1]
        old_path = _UPLOAD_DIR / old_name
        if old_path.exists() and old_name != filename:
            old_path.unlink(missing_ok=True)

    url = f"/uploads/vehicles/{filename}"
    current.vehicle_photo_url = url
    db.commit()
    return {"photo_url": url}


@router.get("/profile/emergency-contact")
def get_emergency_contact(current: Driver = Depends(get_current_driver)):
    return {
        "name":        current.emergency_contact_name or "",
        "phone":       current.emergency_contact_phone or "",
        "telegram_id": current.emergency_contact_telegram_id or "",
    }


@router.put("/profile/password")
def change_password(
    payload: dict,
    current: Driver = Depends(get_current_driver),
    db: Session = Depends(get_db),
):
    current_password = payload.get("current_password") or ""
    new_password     = payload.get("new_password") or ""
    if not current_password or not new_password:
        raise HTTPException(400, "current_password y new_password requeridos")
    if len(new_password) < 6:
        raise HTTPException(400, "La nueva contraseña debe tener al menos 6 caracteres")
    if not verify_password(current_password, current.password_hash):
        raise HTTPException(401, "Contraseña actual incorrecta")
    current.password_hash = hash_password(new_password)
    db.commit()
    return {"success": True}


@router.put("/profile/emergency-contact")
def set_emergency_contact(
    payload: dict,
    current: Driver = Depends(get_current_driver),
    db: Session = Depends(get_db),
):
    current.emergency_contact_name        = (payload.get("name") or "").strip()
    current.emergency_contact_phone       = (payload.get("phone") or "").strip()
    current.emergency_contact_telegram_id = (payload.get("telegram_id") or "").strip()
    db.commit()
    return {"success": True}


# ── Estado y ubicación ────────────────────────────────────────────────────────

@router.put("/status")
def update_status(payload: dict, current: Driver = Depends(get_current_driver), db: Session = Depends(get_db)):
    status = payload.get("status")
    if status not in ("online", "offline"):
        raise HTTPException(400, "status debe ser 'online' o 'offline'")
    current.is_online = (status == "online")
    db.commit()
    return {"is_online": current.is_online}


@router.put("/location")
def update_location(payload: dict, current: Driver = Depends(get_current_driver), db: Session = Depends(get_db)):
    current.current_lat = payload.get("lat")
    current.current_lng = payload.get("lon") or payload.get("lng")
    db.commit()
    return {"status": "ok"}


@router.get("/stats")
def get_stats(current: Driver = Depends(get_current_driver), db: Session = Depends(get_db)):
    completed = db.query(Trip).filter(
        Trip.driver_phone == current.phone,
        Trip.status == TripStatus.COMPLETED
    ).count()
    return {
        "total_trips":    current.total_trips,
        "total_earnings": float(current.total_earnings or 0),
        "rating":         float(current.rating or 5.0),
        "completed_today": completed,
    }


@router.get("/earnings")
def get_earnings(period: str = "week", current: Driver = Depends(get_current_driver), db: Session = Depends(get_db)):
    from collections import defaultdict
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    if period == "today":
        period_start = today_start
    elif period == "week":
        period_start = today_start - timedelta(days=today_start.weekday())
    elif period == "month":
        period_start = today_start.replace(day=1)
    elif period == "year":
        period_start = today_start.replace(month=1, day=1)
    else:
        period_start = today_start - timedelta(days=7)

    trips = db.query(Trip).filter(
        Trip.driver_phone == current.phone,
        Trip.status == TripStatus.COMPLETED,
        Trip.completed_at >= period_start,
    ).all()

    today_earnings = sum(float(t.fare or 0) for t in trips if t.completed_at and t.completed_at >= today_start)

    total = sum(float(t.fare or 0) for t in trips)
    total_rides = len(trips)
    cash_trips = [t for t in trips if (t.payment_method or "cash") == "cash"]
    card_trips  = [t for t in trips if (t.payment_method or "cash") != "cash"]

    daily: dict = defaultdict(lambda: {"rides": 0, "earnings": 0.0})
    for t in trips:
        if t.completed_at:
            day = t.completed_at.strftime("%Y-%m-%d")
            daily[day]["rides"] += 1
            daily[day]["earnings"] += float(t.fare or 0)

    daily_list = [
        {"date": d, "rides": v["rides"], "earnings": round(v["earnings"], 2)}
        for d, v in sorted(daily.items())
    ]
    best_day = max(daily_list, key=lambda x: x["earnings"]) if daily_list else None

    return {
        "period":           period,
        "total":            round(total, 2),
        "total_rides":      total_rides,
        "average_per_ride": round(total / total_rides, 2) if total_rides else 0,
        "cash":             round(sum(float(t.fare or 0) for t in cash_trips), 2),
        "cash_rides":       len(cash_trips),
        "card":             round(sum(float(t.fare or 0) for t in card_trips), 2),
        "card_rides":       len(card_trips),
        "today":            round(today_earnings, 2),
        "daily_breakdown":  daily_list,
        "best_day":         best_day,
        "currency":         "MXN",
    }


# ── Gestión de viajes ─────────────────────────────────────────────────────────

@router.get("/rides/pending")
def get_pending_rides(current: Driver = Depends(get_current_driver), db: Session = Depends(get_db)):
    """Viajes solicitados sin conductor asignado, disponibles para tomar."""
    if not current.is_online:
        return {"rides": []}
    trips = (
        db.query(Trip)
        .filter(Trip.status == TripStatus.REQUESTED, Trip.driver_phone.is_(None))
        .order_by(Trip.created_at.asc())
        .limit(10)
        .all()
    )
    return {"rides": [_trip_to_dict(t) for t in trips]}


@router.get("/rides/active")
def get_active_ride(current: Driver = Depends(get_current_driver), db: Session = Depends(get_db)):
    trip = (
        db.query(Trip)
        .filter(
            Trip.driver_phone == current.phone,
            Trip.status.in_([TripStatus.CONFIRMED, TripStatus.IN_PROGRESS]),
        )
        .order_by(Trip.created_at.desc())
        .first()
    )
    return {"ride": _trip_to_dict(trip) if trip else None}


@router.get("/rides/scheduled")
def get_scheduled_rides(current: Driver = Depends(get_current_driver), db: Session = Depends(get_db)):
    """
    Devuelve dos listas:
    - mine: viajes programados donde el conductor es el asignado
    - pool: viajes programados sin conductor asignado (disponibles para reservar)
    """
    mine = (
        db.query(Trip)
        .filter(Trip.driver_phone == current.phone, Trip.status == TripStatus.SCHEDULED)
        .order_by(Trip.scheduled_at.asc())
        .all()
    )
    pool = (
        db.query(Trip)
        .filter(Trip.driver_phone.is_(None), Trip.status == TripStatus.SCHEDULED)
        .order_by(Trip.scheduled_at.asc())
        .limit(20)
        .all()
    )
    def _with_flag(trips, is_mine):
        result = []
        for t in trips:
            d = _trip_to_dict(t)
            d["is_mine"] = is_mine
            result.append(d)
        return result
    return {"mine": _with_flag(mine, True), "pool": _with_flag(pool, False)}


@router.get("/rides/history")
def get_ride_history(
    limit: int = 20,
    offset: int = 0,
    current: Driver = Depends(get_current_driver),
    db: Session = Depends(get_db),
):
    trips = (
        db.query(Trip)
        .filter(Trip.driver_phone == current.phone, Trip.status == TripStatus.COMPLETED)
        .order_by(Trip.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return {"rides": [_trip_to_dict(t) for t in trips]}


@router.post("/rides/{ride_id}/claim")
def claim_scheduled_ride(ride_id: str, current: Driver = Depends(get_current_driver), db: Session = Depends(get_db)):
    """Conductor reserva un viaje programado del pool."""
    trip = db.query(Trip).filter(Trip.trip_id == ride_id).first()
    if not trip:
        raise HTTPException(404, "Viaje no encontrado")
    if trip.status != TripStatus.SCHEDULED:
        raise HTTPException(409, "Este viaje ya no está disponible")
    if trip.driver_phone:
        raise HTTPException(409, "Este viaje ya fue reservado por otro conductor")
    trip.driver_phone           = current.phone
    trip.driver_name            = current.name
    trip.preferred_driver_phone = current.phone
    trip.preferred_driver_name  = current.name
    db.commit()
    logger.info(f"[Driver] {current.name} reservó viaje programado {ride_id}")
    return {"success": True, "ride": _trip_to_dict(trip)}


@router.post("/rides/{ride_id}/release")
def release_scheduled_ride(ride_id: str, current: Driver = Depends(get_current_driver), db: Session = Depends(get_db)):
    """Conductor libera un viaje programado que tenía reservado — notifica al cliente."""
    trip = db.query(Trip).filter(Trip.trip_id == ride_id, Trip.driver_phone == current.phone).first()
    if not trip:
        raise HTTPException(404, "Viaje no encontrado o no te pertenece")
    if trip.status not in (TripStatus.SCHEDULED, TripStatus.CONFIRMED):
        raise HTTPException(400, "Solo se pueden liberar viajes programados o confirmados")
    trip.status            = TripStatus.DRIVER_RELEASED
    trip.driver_phone      = None
    trip.driver_name       = None
    trip.driver_released_at = datetime.now(timezone.utc)
    db.commit()
    logger.info(f"[Driver] {current.name} liberó viaje {ride_id} → notificando al cliente")
    return {"success": True}


@router.get("/rides/{ride_id}")
def get_ride_detail(ride_id: str, current: Driver = Depends(get_current_driver), db: Session = Depends(get_db)):
    trip = db.query(Trip).filter(Trip.trip_id == ride_id).first()
    if not trip:
        raise HTTPException(404, "Viaje no encontrado")
    return {"ride": _trip_to_dict(trip)}


@router.post("/rides/{ride_id}/accept")
async def accept_ride(ride_id: str, current: Driver = Depends(get_current_driver), db: Session = Depends(get_db)):
    # with_for_update() bloquea la fila hasta hacer commit — evita que dos
    # conductores acepten el mismo viaje simultáneamente (race condition)
    trip = db.query(Trip).filter(Trip.trip_id == ride_id).with_for_update().first()
    if not trip:
        raise HTTPException(404, "Viaje no encontrado")
    if trip.status != TripStatus.REQUESTED or trip.driver_phone:
        raise HTTPException(409, "Viaje ya fue tomado por otro conductor")
    trip.driver_phone = current.phone
    trip.driver_name  = current.name
    trip.status       = TripStatus.CONFIRMED
    db.commit()
    logger.info(f"[Driver] {current.name} aceptó viaje {ride_id}")

    # SSE: avisar a todos los demás conductores que este viaje ya no está disponible
    try:
        from .sse import broadcast_event
        await broadcast_event("ride_taken", {"ride_id": ride_id, "by": current.name})
    except Exception as sse_err:
        logger.warning(f"[Driver] SSE ride_taken error: {sse_err}")

    _notify_customer(
        trip.customer_phone,
        f"🚕 *¡Conductor asignado!*\n\n"
        f"Tu taxi está en camino 🟢\n"
        f"Conductor: *{current.name}*\n"
        f"Vehículo: {current.vehicle_brand or ''} {current.vehicle_model or ''} "
        f"({current.vehicle_color or ''}) — *{current.vehicle_plates or 'N/D'}*\n\n"
        f"📍 Sigue tu viaje en tiempo real:\n"
        f"{settings.PUBLIC_URL}/seguimiento/{trip.trip_id}\n\n"
        f"_Escribe *estado* para más info o *cancelar* si ya no lo necesitas._",
    )
    return {"success": True, "ride": _trip_to_dict(trip)}


@router.post("/rides/{ride_id}/reject")
def reject_ride(ride_id: str, current: Driver = Depends(get_current_driver), db: Session = Depends(get_db)):
    # Solo loga — el viaje vuelve a estar disponible para otros
    logger.info(f"[Driver] {current.name} rechazó viaje {ride_id}")
    return {"success": True}


@router.post("/rides/{ride_id}/arrived")
def driver_arrived(ride_id: str, current: Driver = Depends(get_current_driver), db: Session = Depends(get_db)):
    trip = db.query(Trip).filter(Trip.trip_id == ride_id, Trip.driver_phone == current.phone).first()
    if not trip:
        raise HTTPException(404, "Viaje no encontrado")
    if trip.status != TripStatus.CONFIRMED:
        raise HTTPException(400, "El viaje no está en estado confirmado")
    trip.status = TripStatus.DRIVER_ARRIVED
    db.commit()
    logger.info(f"[Driver] {current.name} llegó al origen del viaje {ride_id}")
    _notify_customer(
        trip.customer_phone,
        f"🚕 *¡Tu taxi llegó!*\n\n"
        f"Tu conductor *{current.name}* está esperándote.\n"
        f"Vehículo: {current.vehicle_brand or ''} {current.vehicle_model or ''} "
        f"({current.vehicle_color or ''}) — *{current.vehicle_plates or 'N/D'}*\n\n"
        f"📍 {settings.PUBLIC_URL}/seguimiento/{trip.trip_id}",
    )
    return {"success": True, "ride": _trip_to_dict(trip)}


@router.post("/rides/{ride_id}/start")
def start_ride(ride_id: str, current: Driver = Depends(get_current_driver), db: Session = Depends(get_db)):
    trip = db.query(Trip).filter(Trip.trip_id == ride_id, Trip.driver_phone == current.phone).first()
    if not trip:
        raise HTTPException(404, "Viaje no encontrado")
    if trip.status not in (TripStatus.CONFIRMED, TripStatus.DRIVER_ARRIVED):
        raise HTTPException(400, "El viaje debe estar confirmado o con conductor esperando")
    trip.status = TripStatus.IN_PROGRESS
    db.commit()
    _notify_customer(
        trip.customer_phone,
        f"🚗 *¡Viaje en camino!*\n\n"
        f"Tu conductor *{current.name}* ha iniciado el trayecto.\n"
        f"Destino: {trip.destination_address or 'Tu destino'}\n\n"
        f"_Escribe *estado* en cualquier momento para consultar tu viaje._",
    )
    return {"success": True, "ride": _trip_to_dict(trip)}


@router.post("/rides/{ride_id}/complete")
def complete_ride(ride_id: str, current: Driver = Depends(get_current_driver), db: Session = Depends(get_db)):
    trip = db.query(Trip).filter(Trip.trip_id == ride_id, Trip.driver_phone == current.phone).first()
    if not trip:
        raise HTTPException(404, "Viaje no encontrado")
    if trip.status != TripStatus.IN_PROGRESS:
        raise HTTPException(400, "El viaje no está en curso")
    trip.status       = TripStatus.COMPLETED
    trip.completed_at = datetime.now(timezone.utc)
    current.total_trips    = (current.total_trips or 0) + 1
    current.total_earnings = Decimal(str(current.total_earnings or 0)) + Decimal(str(trip.fare or 0))
    db.commit()
    logger.info(f"[Driver] Viaje {ride_id} completado por {current.name}")
    _notify_customer(
        trip.customer_phone,
        f"✅ *¡Llegaste a tu destino!*\n\n"
        f"Viaje completado con *{current.name}*.\n"
        f"💰 Total: *${float(trip.fare or 0):.0f} MXN*\n\n"
        f"¡Gracias por usar nuestro servicio! 🙌\n"
        f"Para agendar tu próximo viaje escríbeme aquí o visita:\n"
        f"{settings.PUBLIC_URL}/cliente",
    )
    return {"success": True, "ride": _trip_to_dict(trip)}


# ── Seed: crear conductores de demo ───────────────────────────────────────────

@router.post("/seed-demo", include_in_schema=False)
def seed_demo_drivers(db: Session = Depends(get_db)):
    """Crea conductores de demo + grupo de flota si no existen. Solo para desarrollo."""
    # Crear / recuperar grupo demo
    group = db.query(TaxiGroup).filter(TaxiGroup.name == "Taxi Demo Flota").first()
    if not group:
        wa = settings.WHATSAPP_NUMBER or "+521234500000"
        group = TaxiGroup(name="Taxi Demo Flota", whatsapp_number=wa)
        db.add(group)
        db.flush()

    demos = [
        dict(phone="+521234567001", name="Carlos Méndez",   password="demo1234", driver_code="carlos-001",
             vehicle_brand="Toyota",    vehicle_model="Corolla", vehicle_plates="ABC-123", vehicle_color="Blanco", vehicle_year=2020),
        dict(phone="+521234567002", name="María González",  password="demo1234", driver_code="maria-001",
             vehicle_brand="Nissan",    vehicle_model="Versa",   vehicle_plates="XYZ-456", vehicle_color="Gris",   vehicle_year=2021),
        dict(phone="+521234567003", name="Roberto Sánchez", password="demo1234", driver_code="roberto-001",
             vehicle_brand="Chevrolet", vehicle_model="Aveo",    vehicle_plates="DEF-789", vehicle_color="Negro",  vehicle_year=2019),
    ]
    created = []
    for d in demos:
        existing = db.query(Driver).filter(Driver.phone == d["phone"]).first()
        if not existing:
            driver = Driver(
                phone=d["phone"], name=d["name"],
                password_hash=hash_password(d["password"]),
                driver_code=d["driver_code"],
                group_id=group.id,
                vehicle_brand=d["vehicle_brand"], vehicle_model=d["vehicle_model"],
                vehicle_plates=d["vehicle_plates"], vehicle_color=d["vehicle_color"],
                vehicle_year=d["vehicle_year"],
                is_online=True,
                current_lat=20.5881, current_lng=-100.3889,
            )
            db.add(driver)
            created.append(d["name"])
        elif not existing.driver_code:
            existing.driver_code = d["driver_code"]
            existing.group_id    = group.id
    db.commit()
    base = settings.PUBLIC_URL
    links = [f"{base}/u/{d['driver_code']}" for d in demos]
    return {
        "created": created,
        "message": f"{len(created)} conductor(es) creado(s)",
        "group": group.name,
        "landing_pages": links,
    }


# ── Acción de conductor desde página web (sin JWT, validado por driver_phone) ─
from pydantic import BaseModel as _BM

class _DriverActionBody(_BM):
    action: str        # arrived | start | complete
    driver_phone: str

@router.post("/rides/{ride_id}/driver-action")
async def driver_action_web(ride_id: str, body: _DriverActionBody, db: Session = Depends(get_db)):
    """Transición de estado desde la página web del conductor (sin login)."""
    trip = db.query(Trip).filter(Trip.trip_id == ride_id).first()
    if not trip:
        raise HTTPException(404, "Viaje no encontrado")
    if trip.driver_phone != body.driver_phone:
        raise HTTPException(403, "No autorizado")

    driver = db.query(Driver).filter(Driver.phone == body.driver_phone).first()

    valid = {
        "arrived":  ([TripStatus.CONFIRMED],                                  TripStatus.DRIVER_ARRIVED),
        "start":    ([TripStatus.CONFIRMED, TripStatus.DRIVER_ARRIVED],       TripStatus.IN_PROGRESS),
        "complete": ([TripStatus.IN_PROGRESS],                                TripStatus.COMPLETED),
    }
    if body.action not in valid:
        raise HTTPException(400, "Acción inválida")

    allowed_from, to_status = valid[body.action]
    if trip.status not in allowed_from:
        raise HTTPException(400, f"Estado actual no permite esta acción: {trip.status.value}")

    trip.status = to_status
    if to_status == TripStatus.COMPLETED:
        trip.completed_at = datetime.now(timezone.utc)
    db.commit()
    logger.info(f"[WebAction] {body.action} viaje {ride_id} por {body.driver_phone}")

    # Notificar cliente WhatsApp
    if driver and trip.customer_phone:
        try:
            from .telegram_bot import _notify_customer_wa
            event_map = {"arrived": "arrived", "start": "started", "complete": "completed"}
            _notify_customer_wa(trip.customer_phone, driver, trip, event_map[body.action])
        except Exception as e:
            logger.warning(f"[WebAction] notify WA failed: {e}")

    # Notificar operador Telegram
    try:
        from ..services.telegram import send_to_operator
        labels = {"arrived": "llegó al origen", "start": "inició el viaje", "complete": "completó el viaje"}
        name = driver.name if driver else body.driver_phone
        import asyncio
        msg = f"Conductor {name} {labels[body.action]} - Viaje {ride_id}"
        asyncio.create_task(send_to_operator(msg))
    except Exception:
        pass

    return {"status": to_status.value, "ok": True}
