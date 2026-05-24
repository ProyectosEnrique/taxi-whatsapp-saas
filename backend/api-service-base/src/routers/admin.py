"""
Admin endpoints — gestión de conductores, viajes y estadísticas.
No requiere auth (despliegue interno en VPS).
Rutas: /api/v1/admin/*
"""
import logging
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Driver, Trip, TripStatus, Incident, FareConfig
from ..auth import hash_password
from ..fare_service import get_fare_config, fare_config_to_dict, invalidate_cache

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


def _driver_to_dict(driver: Driver) -> dict:
    status = "offline"
    if driver.is_online:
        status = "available"
    return {
        "driver_id":  driver.id,
        "phone":      driver.phone,
        "name":       driver.name,
        "status":     status,
        "is_active":  driver.is_active,
        "rating":     float(driver.rating or 5.0),
        "total_rides": driver.total_trips or 0,
        "total_earnings": float(driver.total_earnings or 0),
        "acceptance_rate": 0.95,
        "vehicle": {
            "brand":  driver.vehicle_brand or "",
            "model":  driver.vehicle_model or "",
            "plates": driver.vehicle_plates or "",
            "color":  driver.vehicle_color or "",
            "year":   driver.vehicle_year,
        },
        "location": {
            "lat": float(driver.current_lat or 0),
            "lng": float(driver.current_lng or 0),
        },
        "created_at": driver.created_at.isoformat() if driver.created_at else None,
    }


def _trip_to_dict(trip: Trip) -> dict:
    return {
        "ride_id":    trip.trip_id,
        "status":     trip.status.value if trip.status else "requested",
        "customer": {
            "name":  trip.customer_name or "Pasajero",
            "phone": trip.customer_phone or "",
        },
        "driver": {
            "name":  trip.driver_name or "",
            "phone": trip.driver_phone or "",
        } if trip.driver_phone else None,
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
        "total_fare":        float(trip.fare or 0),
        "distance_km":       float(trip.distance_km or 0),
        "duration_minutes":  max(5, int(float(trip.distance_km or 0) * 2.5)),
        "payment_method":    trip.payment_method,
        "requested_at":      trip.created_at.isoformat() if trip.created_at else None,
        "completed_at":      trip.completed_at.isoformat() if trip.completed_at else None,
        "customer_rating":   None,
    }


# ── Stats ─────────────────────────────────────────────────────────────────────

@router.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    total_drivers    = db.query(Driver).filter(Driver.is_active == True).count()
    online_drivers   = db.query(Driver).filter(Driver.is_online == True).count()
    busy_drivers     = db.query(Trip).filter(
        Trip.status.in_([TripStatus.CONFIRMED, TripStatus.IN_PROGRESS])
    ).distinct(Trip.driver_phone).count()

    active_trips     = db.query(Trip).filter(
        Trip.status.in_([TripStatus.REQUESTED, TripStatus.CONFIRMED, TripStatus.IN_PROGRESS])
    ).count()

    completed_today  = db.query(Trip).filter(
        Trip.status == TripStatus.COMPLETED,
        Trip.completed_at >= today_start
    ).count()

    earnings_today_row = db.query(func.sum(Trip.fare)).filter(
        Trip.status == TripStatus.COMPLETED,
        Trip.completed_at >= today_start
    ).scalar()
    earnings_today = float(earnings_today_row or 0)

    total_completed  = db.query(Trip).filter(Trip.status == TripStatus.COMPLETED).count()
    earnings_total_row = db.query(func.sum(Trip.fare)).filter(Trip.status == TripStatus.COMPLETED).scalar()

    active_incidents = db.query(Incident).filter(Incident.status == "active").count()

    return {
        "drivers": {
            "total":   total_drivers,
            "online":  online_drivers,
            "busy":    busy_drivers,
            "offline": total_drivers - online_drivers,
        },
        "trips": {
            "active":          active_trips,
            "completed_today": completed_today,
            "total":           total_completed,
        },
        "earnings": {
            "today": earnings_today,
            "total": float(earnings_total_row or 0),
        },
        "incidents": {
            "active": active_incidents,
        },
    }


# ── Drivers ───────────────────────────────────────────────────────────────────

@router.get("/drivers")
def list_drivers(db: Session = Depends(get_db)):
    drivers = db.query(Driver).order_by(Driver.created_at.desc()).all()
    return {"drivers": [_driver_to_dict(d) for d in drivers]}


@router.post("/drivers")
def create_driver(payload: dict, db: Session = Depends(get_db)):
    phone    = (payload.get("phone") or "").strip()
    name     = (payload.get("name") or "").strip()
    password = payload.get("password") or "1234"
    if not phone or not name:
        raise HTTPException(400, "phone y name requeridos")
    if db.query(Driver).filter(Driver.phone == phone).first():
        raise HTTPException(409, "Teléfono ya registrado")

    driver = Driver(
        phone          = phone,
        name           = name,
        password_hash  = hash_password(password),
        vehicle_brand  = payload.get("vehicle_brand", ""),
        vehicle_model  = payload.get("vehicle_model", ""),
        vehicle_plates = payload.get("vehicle_plates", ""),
        vehicle_color  = payload.get("vehicle_color", ""),
        vehicle_year   = payload.get("vehicle_year"),
        is_active      = True,
        is_online      = False,
    )
    db.add(driver)
    db.commit()
    db.refresh(driver)
    return {"success": True, "driver": _driver_to_dict(driver)}


@router.put("/drivers/{phone}")
def update_driver(phone: str, payload: dict, db: Session = Depends(get_db)):
    driver = db.query(Driver).filter(Driver.phone == phone).first()
    if not driver:
        raise HTTPException(404, "Conductor no encontrado")
    for field in ("name", "vehicle_brand", "vehicle_model", "vehicle_plates", "vehicle_color", "vehicle_year"):
        if field in payload:
            setattr(driver, field, payload[field])
    if "is_active" in payload:
        driver.is_active = payload["is_active"]
    if "password" in payload and payload["password"]:
        driver.password_hash = hash_password(payload["password"])
    db.commit()
    db.refresh(driver)
    return {"success": True, "driver": _driver_to_dict(driver)}


@router.delete("/drivers/{phone}")
def delete_driver(phone: str, db: Session = Depends(get_db)):
    driver = db.query(Driver).filter(Driver.phone == phone).first()
    if not driver:
        raise HTTPException(404, "Conductor no encontrado")
    driver.is_active = False
    driver.is_online = False
    db.commit()
    return {"success": True}


# ── Fare Config ───────────────────────────────────────────────────────────────

@router.get("/fares")
def get_fares(db: Session = Depends(get_db)):
    cfg = get_fare_config(db)
    return fare_config_to_dict(cfg)


@router.put("/fares")
def update_fares(payload: dict, db: Session = Depends(get_db)):
    cfg = db.query(FareConfig).filter(FareConfig.id == 1).first()
    if not cfg:
        cfg = FareConfig(id=1)
        db.add(cfg)

    if "base_fare"       in payload: cfg.base_fare       = payload["base_fare"]
    if "per_km_rate"     in payload: cfg.per_km_rate      = payload["per_km_rate"]
    if "per_minute_rate" in payload: cfg.per_minute_rate  = payload["per_minute_rate"]
    if "minimum_fare"    in payload: cfg.minimum_fare     = payload["minimum_fare"]

    surge = payload.get("surge_pricing", {})
    if "enabled"               in surge: cfg.surge_enabled           = surge["enabled"]
    if "peak_hours_multiplier" in surge: cfg.surge_peak_multiplier   = surge["peak_hours_multiplier"]
    if "late_night_multiplier" in surge: cfg.surge_night_multiplier  = surge["late_night_multiplier"]
    if "weekend_multiplier"    in surge: cfg.surge_weekend_multiplier = surge["weekend_multiplier"]

    charges = payload.get("special_charges", {})
    if "airport_pickup"  in charges: cfg.charge_airport_pickup  = charges["airport_pickup"]
    if "airport_dropoff" in charges: cfg.charge_airport_dropoff = charges["airport_dropoff"]
    if "extra_passenger" in charges: cfg.charge_extra_passenger = charges["extra_passenger"]
    if "luggage"         in charges: cfg.charge_luggage         = charges["luggage"]

    discounts = payload.get("discounts", {})
    if "frequent_rider" in discounts: cfg.discount_frequent_rider = discounts["frequent_rider"]
    if "corporate"      in discounts: cfg.discount_corporate      = discounts["corporate"]

    db.commit()
    db.refresh(cfg)
    invalidate_cache()
    return {"success": True, "config": fare_config_to_dict(cfg)}


# ── Rides ─────────────────────────────────────────────────────────────────────

@router.get("/rides")
def list_rides(
    status: str = "",
    limit: int = 100,
    db: Session = Depends(get_db)
):
    q = db.query(Trip)
    if status:
        try:
            q = q.filter(Trip.status == TripStatus(status))
        except ValueError:
            pass
    trips = q.order_by(Trip.created_at.desc()).limit(limit).all()
    return {"rides": [_trip_to_dict(t) for t in trips]}
