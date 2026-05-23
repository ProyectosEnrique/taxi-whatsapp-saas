"""
Endpoints para conductores: auth, estado, ubicación, gestión de viajes.
Rutas: /api/v1/driver/*
"""
import logging
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Driver, Trip, TripStatus, TaxiGroup
from ..auth import hash_password, verify_password, create_token, get_current_driver
from ..config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/driver", tags=["driver"])


# ── Helpers ───────────────────────────────────────────────────────────────────

def _driver_to_dict(driver: Driver) -> dict:
    return {
        "id":        driver.id,
        "phone":     driver.phone,
        "name":      driver.name,
        "is_online": driver.is_online,
        "rating":    float(driver.rating or 5.0),
        "total_trips": driver.total_trips,
        "vehicle": {
            "brand":  driver.vehicle_brand,
            "model":  driver.vehicle_model,
            "plates": driver.vehicle_plates,
            "color":  driver.vehicle_color,
            "year":   driver.vehicle_year,
        },
        "location": {
            "lat": float(driver.current_lat or 0),
            "lng": float(driver.current_lng or 0),
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
            "lat": float(trip.origin_lat or 0),
            "lng": float(trip.origin_lng or 0),
        },
        "destination": {
            "address": trip.destination_address or "",
            "lat": float(trip.destination_lat or 0),
            "lng": float(trip.destination_lng or 0),
        },
        "fare":             float(trip.fare or 0),
        "total_fare":       float(trip.fare or 0),        # alias para el frontend
        "distance_km":      distance,
        "duration_minutes": max(1, round(distance / 0.5)), # ~30 km/h en ciudad
        "expires_in":       30,                            # segundos para aceptar
        "payment_method":   trip.payment_method,
        "created_at":       trip.created_at.isoformat() if trip.created_at else None,
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
    trips = db.query(Trip).filter(
        Trip.driver_phone == current.phone,
        Trip.status == TripStatus.COMPLETED
    ).all()
    total = sum(float(t.fare or 0) for t in trips)
    return {
        "period":   period,
        "total":    round(total, 2),
        "currency": "MXN",
        "trips":    len(trips),
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


@router.get("/rides/{ride_id}")
def get_ride_detail(ride_id: str, current: Driver = Depends(get_current_driver), db: Session = Depends(get_db)):
    trip = db.query(Trip).filter(Trip.trip_id == ride_id).first()
    if not trip:
        raise HTTPException(404, "Viaje no encontrado")
    return {"ride": _trip_to_dict(trip)}


@router.post("/rides/{ride_id}/accept")
def accept_ride(ride_id: str, current: Driver = Depends(get_current_driver), db: Session = Depends(get_db)):
    trip = db.query(Trip).filter(Trip.trip_id == ride_id).first()
    if not trip:
        raise HTTPException(404, "Viaje no encontrado")
    if trip.status != TripStatus.REQUESTED or trip.driver_phone:
        raise HTTPException(409, "Viaje ya fue tomado por otro conductor")
    trip.driver_phone = current.phone
    trip.driver_name  = current.name
    trip.status       = TripStatus.CONFIRMED
    db.commit()
    logger.info(f"[Driver] {current.name} aceptó viaje {ride_id}")
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
    # Marcamos CONFIRMED para que el cliente sepa que el conductor llegó
    # (el cliente verá "Conductor en camino" → "Conductor llegó")
    return {"success": True, "status": trip.status.value}


@router.post("/rides/{ride_id}/start")
def start_ride(ride_id: str, current: Driver = Depends(get_current_driver), db: Session = Depends(get_db)):
    trip = db.query(Trip).filter(Trip.trip_id == ride_id, Trip.driver_phone == current.phone).first()
    if not trip:
        raise HTTPException(404, "Viaje no encontrado")
    if trip.status != TripStatus.CONFIRMED:
        raise HTTPException(400, "El viaje no está en estado confirmado")
    trip.status = TripStatus.IN_PROGRESS
    db.commit()
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
