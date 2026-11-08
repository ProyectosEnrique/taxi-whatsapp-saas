"""La tarjeta de contacto se manda una sola vez por teléfono y solo a pedido
del gateway (clave interna)."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.config import settings
from src.routers import contact_card
from src.services import ride_notifs


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(settings, "WHATSAPP_SECRET", "clave")
    ride_notifs._memory_claims.clear()
    app = FastAPI()
    app.include_router(contact_card.router)
    yield TestClient(app)
    ride_notifs._memory_claims.clear()


def _claim(client, phone, key="clave"):
    return client.post("/api/v1/contact-card/claim", json={"phone": phone},
                       headers={"X-Taxi-Internal-Key": key})


def test_only_first_time(client):
    assert _claim(client, "+524611234567").json() == {"send": True}
    assert _claim(client, "+524611234567").json() == {"send": False}
    # mismo número escrito distinto sigue siendo el mismo cliente
    assert _claim(client, "whatsapp:+52 461 123 4567").json() == {"send": False}
    assert _claim(client, "+524619999999").json() == {"send": True}


def test_needs_internal_key(client):
    assert _claim(client, "+524611234567", key="mala").status_code == 403
    assert _claim(client, "+524611234567").json() == {"send": True}
