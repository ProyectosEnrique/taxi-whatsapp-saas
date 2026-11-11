"""Chat del chofer limpio al terminar el viaje: se borran los mensajes con
botones y queda un resumen; a quien no alcanzó el viaje se le borra el aviso;
si se cancela, el chofer se entera. Telegram simulado: no sale nada a la red."""
import asyncio

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from conftest import _override_get_db
from src.auth import hash_password
from src.config import settings
from src.database import get_db
from src.models import Driver, Trip, TripStatus
from src.routers import telegram_bot, whatsapp
from src.services import ride_notifs, trip_chat


@pytest.fixture
def tg(monkeypatch):
    log = {"deleted": [], "unbuttoned": [], "sent": [], "next_id": 100}

    async def fake_send_with_buttons(chat_id, text, buttons):
        log["next_id"] += 1
        return {"message_id": log["next_id"]}

    async def fake_send_message(chat_id, text, parse_mode="HTML"):
        log["sent"].append((chat_id, text))
        return True

    async def fake_delete(chat_id, message_id):
        log["deleted"].append((chat_id, message_id))
        return message_id != 999          # 999 = "muy viejo", no se deja borrar

    async def fake_remove_buttons(chat_id, message_id):
        log["unbuttoned"].append((chat_id, message_id))
        return True

    async def noop(*a, **k):
        return True

    monkeypatch.setattr(telegram_bot, "send_with_buttons", fake_send_with_buttons)
    monkeypatch.setattr(telegram_bot, "send_message", fake_send_message)
    monkeypatch.setattr(telegram_bot, "answer_callback", noop)
    monkeypatch.setattr(telegram_bot, "edit_message_text", noop)
    monkeypatch.setattr(telegram_bot, "send_to_operator", noop)
    monkeypatch.setattr(telegram_bot, "_notify_customer_wa", lambda *a, **k: None)
    monkeypatch.setattr(trip_chat, "send_message", fake_send_message)
    monkeypatch.setattr(trip_chat, "delete_message", fake_delete)
    monkeypatch.setattr(trip_chat, "remove_buttons", fake_remove_buttons)
    monkeypatch.setattr(settings, "TELEGRAM_WEBHOOK_SECRET", "")
    monkeypatch.setattr(settings, "WHATSAPP_SECRET", "")
    ride_notifs._memory_claims.clear()
    ride_notifs._memory_store.clear()
    trip_chat._memory.clear()
    yield log


def _client():
    app = FastAPI()
    app.include_router(telegram_bot.router)
    app.include_router(whatsapp.router)
    app.dependency_overrides[get_db] = _override_get_db
    return TestClient(app)


def _setup(db, status=TripStatus.REQUESTED):
    d = Driver(phone="+524610000001", name="Chofer 1", password_hash=hash_password("x"),
               is_online=True, is_active=True, telegram_chat_id="chat1")
    t = Trip(trip_id="TRIP-AAAA0001", customer_phone="+524610000099", origin_address="Centro",
             destination_address="Col. Alameda", origin_lat=20.54, origin_lng=-100.8,
             destination_lat=20.52, destination_lng=-100.815, fare=80, distance_km=3.5, status=status)
    if status != TripStatus.REQUESTED:
        t.driver_phone, t.driver_name = d.phone, d.name
    db.add_all([d, t])
    db.commit()
    return t


def _tap(client, data):
    cq = {"update_id": 1, "callback_query": {"id": "q", "from": {"id": "chat1"}, "data": data}}
    assert client.post("/api/v1/telegram/webhook", json=cq).status_code == 200


def test_completing_deletes_trip_messages_and_leaves_summary(db_session, tg):
    t = _setup(db_session)
    c = _client()
    # Aviso del viaje nuevo al chofer 1 y a otro chofer que no lo alcanza
    asyncio.run(ride_notifs.save(t.trip_id, [("chat1", 50), ("chat2", 60)]))
    _tap(c, f"accept_{t.trip_id}")            # → "Viaje aceptado" (101)
    _tap(c, f"arrived_{t.trip_id}")           # → "Llegaste" (102)
    _tap(c, f"start_{t.trip_id}")             # → "Viaje en curso" (103)
    _tap(c, f"complete_{t.trip_id}")

    deleted = {m for chat, m in tg["deleted"] if chat == "chat1"}
    assert {50, 101, 102, 103} <= deleted
    chat, summary = tg["sent"][-1]
    assert chat == "chat1" and "Viaje terminado" in summary and "Centro → Col. Alameda" in summary
    assert "$80" in summary


def test_taken_notices_of_other_drivers_are_deleted_later(tg):
    asyncio.run(trip_chat.drop_taken_notices([("chat2", 60), ("chat3", 999)], delay_s=0))
    assert ("chat2", 60) in tg["deleted"]
    # El que ya no se puede borrar al menos se queda sin botones
    assert tg["unbuttoned"] == [("chat3", 999)]


def test_cancel_tells_assigned_driver_and_cleans_chat(db_session, tg):
    t = _setup(db_session, TripStatus.CONFIRMED)
    asyncio.run(trip_chat.track(t.trip_id, "chat1", {"message_id": 101}))
    r = _client().post(f"/api/v1/whatsapp/rides/{t.trip_id}/cancel", headers={"x-taxi-internal-key": "x"})
    assert r.status_code == 200
    assert ("chat1", 101) in tg["deleted"]
    assert tg["sent"][-1][0] == "chat1" and "cancelado" in tg["sent"][-1][1]


def test_cancel_before_anyone_accepts_removes_accept_buttons(db_session, tg):
    t = _setup(db_session)
    asyncio.run(ride_notifs.save(t.trip_id, [("chat1", 50), ("chat2", 60)]))
    _client().post(f"/api/v1/whatsapp/rides/{t.trip_id}/cancel", headers={"x-taxi-internal-key": "x"})
    assert {("chat1", 50), ("chat2", 60)} <= set(tg["deleted"])
    assert tg["sent"] == []                   # sin chofer asignado: nadie que avisar
