"""QR de la tarjetita del taxi (/t/23) y de la calcomanía (/t): abren el WhatsApp de
TaxiCerca; al escanear, "guarda este chat" + regalo de FarmaCerca solo si el taxi existe."""
from urllib.parse import unquote

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from conftest import _override_get_db
from src.config import settings
from src.database import get_db
from src.models import Driver
from src.routers import taxi_qr


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(settings, "WHATSAPP_SECRET", "clave")
    monkeypatch.setattr(settings, "TAXICERCA_WA_NUMBER", "+13162412111")
    monkeypatch.setattr(settings, "FARMACERCA_GIFT_URL", "https://farmacia.nexoai.lat/r/taxi")
    app = FastAPI()
    app.include_router(taxi_qr.router)
    app.dependency_overrides[get_db] = _override_get_db
    return TestClient(app)


def _driver(db, taxi="23", active=True):
    db.add(Driver(phone="+524610000023", name="Carlos Pérez", password_hash="x", is_active=active, taxi_number=taxi))
    db.commit()


def _scan(client, taxi, key="clave"):
    return client.post("/api/v1/whatsapp/taxi-scan", json={"phone": "+524611234567", "taxi": taxi},
                       headers={"X-Taxi-Internal-Key": key})


def test_card_qr_opens_taxicerca_with_taxi_number(client):
    r = client.get("/t/23", follow_redirects=False)
    assert r.status_code == 302
    loc = unquote(r.headers["location"])
    assert loc.startswith("https://wa.me/13162412111?text=")
    assert "voy en el taxi 23" in loc


def test_street_qr_asks_for_a_taxi(client):
    loc = unquote(client.get("/t", follow_redirects=False).headers["location"])
    assert "quiero pedir un taxi" in loc


def test_known_taxi_gets_save_chat_and_gift(client, db_session):
    _driver(db_session, "a7")
    reply = _scan(client, "A7").json()["reply"]
    assert "Guarda este chat" in reply
    assert "https://farmacia.nexoai.lat/r/taxi/a7" in reply


def test_unknown_or_inactive_taxi_gets_no_gift(client, db_session):
    _driver(db_session, "23", active=False)
    for taxi in ("23", "99"):
        reply = _scan(client, taxi).json()["reply"]
        assert "Guarda este chat" in reply and "farmacia" not in reply


def test_gift_off(client, db_session, monkeypatch):
    _driver(db_session)
    monkeypatch.setattr(settings, "FARMACERCA_GIFT_URL", "")
    assert "farmacia" not in _scan(client, "23").json()["reply"]


def test_needs_internal_key(client):
    assert _scan(client, "23", key="mala").status_code == 403
