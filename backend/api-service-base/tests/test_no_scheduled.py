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
