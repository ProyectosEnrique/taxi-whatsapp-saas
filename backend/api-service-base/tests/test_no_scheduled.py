"""Arranque solo con viajes al momento: un viaje programado se RECHAZA (no se
convierte en inmediato, que mandaría un taxi ya a quien lo quería mañana)."""
from fastapi import FastAPI
from fastapi.testclient import TestClient

from conftest import _override_get_db
from src.config import settings
from src.database import get_db
from src.models import Trip
from src.routers import whatsapp

_RIDE = {"customer_phone": "+524610000099",
         "origin": {"address": "Centro", "lat": 20.52, "lng": -100.81},
         "destination": {"address": "Alameda", "lat": 20.53, "lng": -100.82}}


def _client(monkeypatch):
    monkeypatch.setattr(settings, "WHATSAPP_SECRET", "")
    app = FastAPI()
    app.include_router(whatsapp.router)
    app.dependency_overrides[get_db] = _override_get_db
    return TestClient(app)


def test_scheduled_ride_is_rejected(monkeypatch, db_session):
    monkeypatch.setattr(settings, "SCHEDULED_RIDES_ENABLED", False)
    r = _client(monkeypatch).post("/api/v1/whatsapp/rides/create",
                                  json={**_RIDE, "scheduled_at": "2026-11-10T07:00:00"},
                                  headers={"x-taxi-internal-key": "x"})
    assert r.status_code == 409
    assert db_session.query(Trip).count() == 0


# ── Pedir desde la web: apagado, solo WhatsApp ────────────────────────────────

def _web_client():
    from src.routers import customer_rides
    app = FastAPI()
    app.include_router(customer_rides.router)
    app.dependency_overrides[get_db] = _override_get_db
    return TestClient(app)


def test_web_register_and_request_are_off(monkeypatch, db_session):
    monkeypatch.setattr(settings, "WEB_RIDES_ENABLED", False)
    c = _web_client()
    r = c.post("/api/v1/customer/register", json={"phone": "+521111111111", "password": "x"})
    assert r.status_code == 403 and "WhatsApp" in r.json()["detail"]
    assert c.post("/api/v1/customer/login", json={"phone": "+521111111111", "password": "x"}).status_code == 403
    assert c.post("/api/v1/customer/rides/request", json=_RIDE).status_code == 403
    assert db_session.query(Trip).count() == 0


def test_public_tracking_still_works_with_web_off(monkeypatch, db_session):
    monkeypatch.setattr(settings, "WEB_RIDES_ENABLED", False)
    t = Trip(customer_phone="+524610000099", origin_address="Centro", destination_address="Alameda",
             origin_lat=20.52, origin_lng=-100.81, destination_lat=20.53, destination_lng=-100.82, fare=70)
    db_session.add(t)
    db_session.commit()
    assert _web_client().get(f"/api/v1/customer/rides/{t.trip_id}/public-track").status_code == 200
