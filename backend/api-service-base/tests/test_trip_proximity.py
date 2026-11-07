"""Durante el viaje, con la ubicación en vivo del chofer:
- cerca del pasajero "Llegué" se marca solo,
- cerca del destino se le manda el botón de completar,
y los mensajes del bot traen botones que abren Maps/Waze ya navegando.

Telegram y el aviso por WhatsApp se simulan: no sale nada a la red.
"""
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from conftest import _override_get_db
from src.auth import hash_password
from src.config import settings
from src.database import get_db
from src.models import Driver, Trip, TripStatus
from src.routers import telegram_bot
from src.services import ride_notifs

_ORIGIN = (20.5400, -100.8000)
_DEST = (20.5200, -100.8150)
_NEAR_ORIGIN = (20.5404, -100.8000)   # ~45 m
_NEAR_DEST = (20.5210, -100.8150)     # ~110 m
_FAR = (20.5600, -100.8000)           # ~2 km


@pytest.fixture
def bot(monkeypatch):
    log = {"buttons": [], "callbacks": [], "wa": []}

    async def fake_send_message(chat_id, text, parse_mode="HTML"):
        return True

    async def fake_send_with_buttons(chat_id, text, buttons):
        log["buttons"].append((chat_id, text, buttons))
        return {"message_id": 1}

    async def fake_answer_callback(cq_id, text, alert=False):
        log["callbacks"].append(text)

    def fake_notify(phone, driver, trip, event="accepted"):
        log["wa"].append(event)

    monkeypatch.setattr(telegram_bot, "send_message", fake_send_message)
    monkeypatch.setattr(telegram_bot, "send_with_buttons", fake_send_with_buttons)
    monkeypatch.setattr(telegram_bot, "answer_callback", fake_answer_callback)
    monkeypatch.setattr(telegram_bot, "_notify_customer_wa", fake_notify)
    monkeypatch.setattr(settings, "TELEGRAM_WEBHOOK_SECRET", "")
    ride_notifs._memory_claims.clear()
    yield log
    ride_notifs._memory_claims.clear()


@pytest.fixture
def tg_client():
    app = FastAPI()
    app.include_router(telegram_bot.router)
    app.dependency_overrides[get_db] = _override_get_db
    return TestClient(app)


def _setup(db, status, seconds_ago=120):
    d = Driver(phone="+524610000001", name="Chofer 1", password_hash=hash_password("x"),
               is_online=True, is_active=True, telegram_chat_id="chat1")
    t = Trip(customer_phone="+524610000099", customer_name="Juan",
             origin_address="Central de Autobuses", destination_address="Col. Alameda",
             origin_lat=_ORIGIN[0], origin_lng=_ORIGIN[1],
             destination_lat=_DEST[0], destination_lng=_DEST[1],
             fare=70, distance_km=3, status=status,
             driver_phone="+524610000001", driver_name="Chofer 1")
    db.add_all([d, t])
    db.commit()
    t.updated_at = datetime.now(timezone.utc) - timedelta(seconds=seconds_ago)
    db.commit()
    db.refresh(t)
    return t


def _move(client, lat, lng):
    loc = {"latitude": lat, "longitude": lng, "live_period": 28800}
    upd = {"update_id": 1, "edited_message": {"message_id": 5, "chat": {"id": "chat1"}, "location": loc}}
    assert client.post("/api/v1/telegram/webhook", json=upd).status_code == 200


def _status(db, trip):
    db.expire_all()
    return db.query(Trip).filter(Trip.trip_id == trip.trip_id).one().status


def _labels(buttons):
    return [b["text"] for row in buttons for b in row]


# ── "Llegué" automático ───────────────────────────────────────────────────────

def test_arrives_automatically_near_pickup(tg_client, db_session, bot):
    trip = _setup(db_session, TripStatus.CONFIRMED)
    _move(tg_client, *_NEAR_ORIGIN)

    assert _status(db_session, trip) == TripStatus.DRIVER_ARRIVED
    assert bot["wa"] == ["arrived"]
    assert "🚗 Iniciar viaje" in _labels(bot["buttons"][-1][2])


def test_no_auto_arrival_while_far(tg_client, db_session, bot):
    trip = _setup(db_session, TripStatus.CONFIRMED)
    _move(tg_client, *_FAR)
    assert _status(db_session, trip) == TripStatus.CONFIRMED
    assert bot["wa"] == []


def test_no_auto_arrival_right_after_accepting(tg_client, db_session, bot):
    # Aceptó estando ya junto al pasajero: no avisar "llegó" en el mismo segundo
    trip = _setup(db_session, TripStatus.CONFIRMED, seconds_ago=5)
    _move(tg_client, *_NEAR_ORIGIN)
    assert _status(db_session, trip) == TripStatus.CONFIRMED


def test_auto_arrival_only_once(tg_client, db_session, bot):
    trip = _setup(db_session, TripStatus.CONFIRMED)
    _move(tg_client, *_NEAR_ORIGIN)
    _move(tg_client, *_NEAR_ORIGIN)
    assert bot["wa"] == ["arrived"]


def test_manual_button_after_auto_arrival_is_harmless(tg_client, db_session, bot):
    trip = _setup(db_session, TripStatus.CONFIRMED)
    _move(tg_client, *_NEAR_ORIGIN)
    cq = {"update_id": 2, "callback_query": {"id": "q1", "from": {"id": "chat1"},
                                              "data": f"arrived_{trip.trip_id}"}}
    tg_client.post("/api/v1/telegram/webhook", json=cq)
    assert bot["wa"] == ["arrived"]
    assert "ya estaba registrada" in bot["callbacks"][-1]


def test_auto_arrival_can_be_disabled(tg_client, db_session, bot, monkeypatch):
    monkeypatch.setattr(settings, "AUTO_ARRIVE_RADIUS_M", 0)
    trip = _setup(db_session, TripStatus.CONFIRMED)
    _move(tg_client, *_NEAR_ORIGIN)
    assert _status(db_session, trip) == TripStatus.CONFIRMED


# ── Cerca del destino ─────────────────────────────────────────────────────────

def test_near_destination_offers_complete_once(tg_client, db_session, bot):
    trip = _setup(db_session, TripStatus.IN_PROGRESS)
    _move(tg_client, *_NEAR_DEST)
    _move(tg_client, *_NEAR_DEST)

    prompts = [b for b in bot["buttons"] if "Ya casi llegas" in b[1]]
    assert len(prompts) == 1
    assert _labels(prompts[0][2]) == ["✅ Completar viaje"]
    assert "$70" in prompts[0][1]
    # Completar sigue siendo manual
    assert _status(db_session, trip) == TripStatus.IN_PROGRESS


def test_no_destination_prompt_while_far(tg_client, db_session, bot):
    _setup(db_session, TripStatus.IN_PROGRESS)
    _move(tg_client, *_FAR)
    assert bot["buttons"] == []


# ── Botones de navegación ─────────────────────────────────────────────────────

def test_accepted_message_has_direct_navigation_buttons(db_session, bot):
    import asyncio
    trip = _setup(db_session, TripStatus.CONFIRMED)
    asyncio.run(telegram_bot._send_ride_action("chat1", trip))

    _, text, buttons = bot["buttons"][-1]
    urls = [b.get("url", "") for row in buttons for b in row]
    assert any("google.com/maps/dir/" in u and "dir_action=navigate" in u
               and f"destination={_ORIGIN[0]}" in u for u in urls)
    assert any(u.startswith("https://waze.com/ul?") and "navigate=yes" in u for u in urls)
    assert "🟢 Llegué al origen" in _labels(buttons)
    assert "/conductor/viaje/" not in text


def test_in_progress_message_navigates_to_destination(db_session, bot):
    import asyncio
    trip = _setup(db_session, TripStatus.IN_PROGRESS)
    asyncio.run(telegram_bot._send_ride_action("chat1", trip))

    buttons = bot["buttons"][-1][2]
    urls = [b.get("url", "") for row in buttons for b in row]
    assert any(f"destination={_DEST[0]}" in u for u in urls)
    assert "✅ Completar viaje" in _labels(buttons)
