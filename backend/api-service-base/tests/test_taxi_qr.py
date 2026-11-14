"""QR de la tarjetita del taxi (/tc, igual para todos; /t/23 de los QR viejos) y de la calcomanía (/t): abren el
WhatsApp de TaxiCerca; al escanear, "guarda este chat" + regalo de FarmaCerca (sin número de taxi: FarmaCerca da
$5 una sola vez por número)."""
from urllib.parse import unquote

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from conftest import _override_get_db
from src.config import settings
from src.database import get_db
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


def _scan(client, taxi, key="clave"):
    return client.post("/api/v1/whatsapp/taxi-scan", json={"phone": "+524611234567", "taxi": taxi},
                       headers={"X-Taxi-Internal-Key": key})


def test_card_qr_same_for_every_taxi(client):
    r = client.get("/tc", follow_redirects=False)
    assert r.status_code == 302
    loc = unquote(r.headers["location"])
    assert loc.startswith("https://wa.me/13162412111?text=")
    assert "voy en un taxi" in loc


def test_old_card_qr_with_taxi_number(client):
    loc = unquote(client.get("/t/23", follow_redirects=False).headers["location"])
    assert "voy en el taxi 23" in loc


def test_street_qr_asks_for_a_taxi(client):
    loc = unquote(client.get("/t", follow_redirects=False).headers["location"])
    assert "quiero pedir un taxi" in loc


def test_scan_gets_save_chat_and_gift_without_taxi_number(client):
    reply = _scan(client, "").json()["reply"]
    assert "Vas en un taxi de *TaxiCerca*" in reply and "Guarda este chat" in reply
    assert reply.rstrip().endswith("https://farmacia.nexoai.lat/r/taxi")


def test_old_qr_names_the_taxi_and_still_gifts(client):
    reply = _scan(client, "a7").json()["reply"]
    assert "el taxi *A7*" in reply and "https://farmacia.nexoai.lat/r/taxi" in reply


def test_gift_off(client, monkeypatch):
    monkeypatch.setattr(settings, "FARMACERCA_GIFT_URL", "")
    assert "farmacia" not in _scan(client, "").json()["reply"]


def test_needs_internal_key(client):
    assert _scan(client, "", key="mala").status_code == 403
