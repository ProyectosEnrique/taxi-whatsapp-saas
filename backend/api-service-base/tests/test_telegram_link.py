"""Enlace personal para vincular Telegram: el admin lo genera, el chofer toca
"Iniciar" y queda vinculado; sirve una sola vez. Telegram se simula."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from conftest import _override_get_db
from src.auth import hash_password
from src.config import settings
from src.database import get_db
from src.models import Driver
from src.routers import admin, telegram_bot
from src.services import telegram_link


@pytest.fixture
def setup(monkeypatch, db_session):
    sent = []

    async def fake_send(chat_id, text, parse_mode="HTML"):
        sent.append((str(chat_id), text))
        return True

    monkeypatch.setattr(telegram_bot, "send_message", fake_send)
    monkeypatch.setattr(settings, "TELEGRAM_WEBHOOK_SECRET", "")
    monkeypatch.setattr(settings, "ADMIN_PASSWORD", "clave-admin")
    monkeypatch.setattr(telegram_link.ride_notifs, "_redis_client", None)
    telegram_link._memory.clear()
    app = FastAPI()
    app.include_router(admin.router)
    app.include_router(telegram_bot.router)
    app.dependency_overrides[get_db] = _override_get_db
    db_session.add(Driver(phone="+524610000001", name="Pedro", password_hash=hash_password("x"), is_active=True))
    db_session.commit()
    return TestClient(app), sent


def _link(client):
    r = client.post("/api/v1/admin/drivers/+524610000001/telegram-link", headers={"x-admin-key": "clave-admin"})
    assert r.status_code == 200
    return r.json()["url"]


def _start(client, chat, text):
    upd = {"update_id": 1, "message": {"message_id": 1, "chat": {"id": chat}, "text": text}}
    assert client.post("/api/v1/telegram/webhook", json=upd).status_code == 200


def test_link_once_and_driver_is_linked(setup, db_session):
    client, sent = setup
    url = _link(client)
    assert url.startswith("https://t.me/TaxiNexoaiBot?start=")
    code = url.split("start=")[1]

    _start(client, "chat-pedro", f"/start {code}")
    db_session.expire_all()
    assert db_session.query(Driver).one().telegram_chat_id == "chat-pedro"
    assert "¡Listo, Pedro!" in sent[0][1]

    # Otro Telegram con el mismo enlace: ya no sirve
    _start(client, "chat-intruso", f"/start {code}")
    db_session.expire_all()
    assert db_session.query(Driver).one().telegram_chat_id == "chat-pedro"
    assert "ya se usó o venció" in sent[-1][1]


def test_plain_start_shows_id(setup):
    client, sent = setup
    _start(client, "12345", "/start")
    assert "12345" in sent[-1][1]


def test_admin_key_required(setup):
    client, _ = setup
    r = client.post("/api/v1/admin/drivers/+524610000001/telegram-link", headers={"x-admin-key": "mala"})
    assert r.status_code == 401
