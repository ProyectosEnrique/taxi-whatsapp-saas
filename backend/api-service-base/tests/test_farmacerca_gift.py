"""Regalo de FarmaCerca: solo en el primer viaje terminado del pasajero. Desde 2026-11-13 el link no lleva
número de taxi (FarmaCerca da $5 de bienvenida una sola vez por número)."""
from fastapi import FastAPI
from fastapi.testclient import TestClient

from conftest import _override_get_db
from src.auth import hash_password
from src.config import settings
from src.database import get_db
from src.models import Driver, Trip, TripStatus
from src.routers import customer_rides
from src.services.farmacerca_gift import gift_for, gift_line

_PASSENGER = "+524610000099"


def _driver(db, taxi_number="23"):
    d = Driver(phone="+524610000001", name="Chofer 1", password_hash=hash_password("x"),
               taxi_number=taxi_number)
    db.add(d)
    db.commit()
    return d


def _trip(db, status=TripStatus.COMPLETED, phone=_PASSENGER):
    t = Trip(customer_phone=phone, origin_address="A", destination_address="B",
             origin_lat=20.54, origin_lng=-100.80, destination_lat=20.52, destination_lng=-100.81,
             fare=45, status=status, driver_phone="+524610000001", driver_name="Chofer 1")
    db.add(t)
    db.commit()
    return t


def test_first_trip_gets_gift_link(db_session):
    d = _driver(db_session)
    t = _trip(db_session)
    assert gift_for(t, d) == {"amount": 5, "url": "https://farmacia.nexoai.lat/r/taxi"}
    line = gift_line(t, d)
    assert "$5" in line and "Tu farmacia por WhatsApp" in line and line.rstrip().endswith("/r/taxi")


def test_no_gift_on_second_trip(db_session):
    d = _driver(db_session)
    _trip(db_session)
    t2 = _trip(db_session)
    assert gift_for(t2, d) is None
    assert gift_line(t2, d) == ""


def test_banner_shows_during_first_trip(db_session):
    d = _driver(db_session)
    t = _trip(db_session, status=TripStatus.IN_PROGRESS)
    assert gift_for(t, d) is not None


def test_cancelled_trips_do_not_use_up_the_gift(db_session):
    d = _driver(db_session)
    _trip(db_session, status=TripStatus.CANCELLED)
    t = _trip(db_session)
    assert gift_for(t, d) is not None


def test_gift_without_taxi_number(db_session):
    d = _driver(db_session, taxi_number=None)
    t = _trip(db_session)
    assert gift_for(t, d) is not None


def test_gift_can_be_turned_off(db_session, monkeypatch):
    monkeypatch.setattr(settings, "FARMACERCA_GIFT_URL", "")
    d = _driver(db_session)
    assert gift_for(_trip(db_session), d) is None


def test_public_track_includes_gift(db_session):
    _driver(db_session)
    t = _trip(db_session, status=TripStatus.CONFIRMED)
    app = FastAPI()
    app.include_router(customer_rides.router)
    app.dependency_overrides[get_db] = _override_get_db
    client = TestClient(app)
    paths = [r.path for r in app.routes if "public-track" in getattr(r, "path", "")]
    data = client.get(paths[0].replace("{ride_id}", t.trip_id)).json()
    assert data["gift"]["url"].endswith("/r/taxi")
