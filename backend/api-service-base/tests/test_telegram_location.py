"""Ubicación en vivo de los choferes por Telegram + despacho por cercanía.

Telegram se simula: send_message/send_with_buttons se reemplazan por funciones
que solo anotan a quién se le escribió, así no sale nada a la red.
"""
import asyncio
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from conftest import TestingSessionLocal, _override_get_db
from src.auth import hash_password
from src.config import settings
from src.database import get_db
from src.models import Driver, Trip, TripStatus
from src.routers import telegram_bot
from src.services import ride_notifs

# La Central de Autobuses de Celaya, aprox.
_ORIGIN = (20.5400, -100.8000)


@pytest.fixture
def sent(monkeypatch):
    """Registra los mensajes enviados: {"text": [(chat, texto)], "ride": [(chat, texto)]}."""
    log = {"text": [], "ride": []}
    counter = iter(range(1, 10_000))

    async def fake_send_message(chat_id, text, parse_mode="HTML"):
        log["text"].append((chat_id, text))
        return True

    async def fake_send_with_buttons(chat_id, text, buttons):
        log["ride"].append((chat_id, text))
        return {"message_id": next(counter)}

    monkeypatch.setattr(telegram_bot, "send_message", fake_send_message)
    monkeypatch.setattr(telegram_bot, "send_with_buttons", fake_send_with_buttons)
    monkeypatch.setattr(telegram_bot, "SessionLocal", TestingSessionLocal)
    monkeypatch.setattr(settings, "TELEGRAM_WEBHOOK_SECRET", "")
    monkeypatch.setattr(settings, "DISPATCH_RINGS_KM", "2,4")
    monkeypatch.setattr(settings, "DISPATCH_RING_WAIT_S", 0)
    ride_notifs._memory_store.clear()
    yield log
    ride_notifs._memory_store.clear()


@pytest.fixture
def tg_client():
    app = FastAPI()
    app.include_router(telegram_bot.router)
    app.dependency_overrides[get_db] = _override_get_db
    return TestClient(app)


def _driver(db, n, lat=None, lng=None, minutes_ago=1, online=True):
    d = Driver(
        phone=f"+52461000000{n}", name=f"Chofer {n}", password_hash=hash_password("x"),
        is_online=online, is_active=True, telegram_chat_id=f"chat{n}",
        current_lat=lat, current_lng=lng,
        location_updated_at=(datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)) if lat else None,
    )
    db.add(d)
    db.commit()
    return d


def _trip(db):
    t = Trip(customer_phone="+524610000099", customer_name="Juan", origin_address="Central de Autobuses",
             destination_address="Col. Alameda", origin_lat=_ORIGIN[0], origin_lng=_ORIGIN[1],
             fare=70, distance_km=3, status=TripStatus.REQUESTED)
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


def _chats(log):
    return [chat for chat, _ in log["ride"]]


# ── Webhook: ubicación ───────────────────────────────────────────────────────

def _loc_update(kind, chat, lat, lng, live=None):
    loc = {"latitude": lat, "longitude": lng}
    if live:
        loc["live_period"] = live
    return {"update_id": 1, kind: {"message_id": 5, "chat": {"id": chat}, "location": loc}}


def test_live_location_saves_position_and_confirms(tg_client, db_session, sent):
    _driver(db_session, 1)
    resp = tg_client.post("/api/v1/telegram/webhook", json=_loc_update("message", "chat1", 20.55, -100.81, live=28800))
    assert resp.status_code == 200

    db_session.expire_all()
    d = db_session.query(Driver).filter(Driver.telegram_chat_id == "chat1").one()
    assert float(d.current_lat) == pytest.approx(20.55)
    assert d.location_updated_at is not None
    assert "Ubicación en vivo activada" in sent["text"][0][1]
    assert "por 8 h" in sent["text"][0][1]


def test_live_location_until_disabled(tg_client, db_session, sent):
    _driver(db_session, 1)
    tg_client.post("/api/v1/telegram/webhook", json=_loc_update("message", "chat1", 20.55, -100.81, live=0x7FFFFFFF))
    assert "hasta que la desactives" in sent["text"][0][1]


def test_live_updates_are_saved_silently(tg_client, db_session, sent):
    _driver(db_session, 1, lat=20.50, lng=-100.80)
    tg_client.post("/api/v1/telegram/webhook", json=_loc_update("edited_message", "chat1", 20.56, -100.82, live=28800))

    db_session.expire_all()
    d = db_session.query(Driver).filter(Driver.telegram_chat_id == "chat1").one()
    assert float(d.current_lat) == pytest.approx(20.56)
    assert sent["text"] == []


def test_static_location_explains_how_to_share_live(tg_client, db_session, sent):
    _driver(db_session, 1)
    tg_client.post("/api/v1/telegram/webhook", json=_loc_update("message", "chat1", 20.55, -100.81))
    assert "fija" in sent["text"][0][1]
    assert "Compartir ubicación en tiempo real" in sent["text"][0][1]


def test_location_from_unlinked_chat_is_rejected(tg_client, db_session, sent):
    tg_client.post("/api/v1/telegram/webhook", json=_loc_update("message", "desconocido", 20.55, -100.81, live=900))
    assert "No estás vinculado" in sent["text"][0][1]


def test_ubicacion_command_sends_instructions(tg_client, db_session, sent):
    tg_client.post("/api/v1/telegram/webhook",
                   json={"update_id": 2, "message": {"message_id": 6, "chat": {"id": "chat9"}, "text": "/ubicacion"}})
    assert "Compartir ubicación en tiempo real" in sent["text"][0][1]


# ── Despacho por cercanía ────────────────────────────────────────────────────

def test_rides_go_to_nearest_ring_first_then_expand(db_session, sent):
    _driver(db_session, 1, lat=20.5490, lng=-100.8000)                  # ~1 km
    _driver(db_session, 2, lat=20.5670, lng=-100.8000)                  # ~3 km
    _driver(db_session, 3)                                              # sin ubicación
    _driver(db_session, 4, lat=20.5410, lng=-100.8000, minutes_ago=30)  # cerca pero vieja
    trip = _trip(db_session)

    nxt = asyncio.run(telegram_bot._dispatch(trip, db_session, 0))
    assert _chats(sent) == ["chat1"]
    assert "Estás a 1.0 km" in sent["ride"][0][1]
    assert nxt == 1

    nxt = asyncio.run(telegram_bot._dispatch(trip, db_session, nxt))
    assert _chats(sent) == ["chat1", "chat2"]
    assert nxt == 2

    nxt = asyncio.run(telegram_bot._dispatch(trip, db_session, nxt))
    assert sorted(_chats(sent)[2:]) == ["chat3", "chat4"]
    assert nxt is None
    # Todos los avisos quedan guardados para marcarlos "ya fue tomado"
    assert len(asyncio.run(ride_notifs.get(trip.trip_id))) == 4


def test_empty_rings_are_skipped(db_session, sent):
    _driver(db_session, 2, lat=20.5670, lng=-100.8000)  # ~3 km: nadie a ≤2 km
    _driver(db_session, 3)
    trip = _trip(db_session)

    nxt = asyncio.run(telegram_bot._dispatch(trip, db_session, 0))
    assert _chats(sent) == ["chat2"]
    assert nxt == 2


def test_without_fresh_locations_everyone_is_notified_at_once(db_session, sent):
    _driver(db_session, 1)
    _driver(db_session, 2, lat=20.5410, lng=-100.8000, minutes_ago=30)
    _driver(db_session, 3, online=False)
    trip = _trip(db_session)

    nxt = asyncio.run(telegram_bot._dispatch(trip, db_session, 0))
    assert sorted(_chats(sent)) == ["chat1", "chat2"]
    assert nxt is None


def test_expand_later_walks_all_rings(db_session, sent):
    _driver(db_session, 1, lat=20.5490, lng=-100.8000)
    _driver(db_session, 2, lat=20.5670, lng=-100.8000)
    _driver(db_session, 3)
    trip = _trip(db_session)

    asyncio.run(telegram_bot._dispatch(trip, db_session, 0))
    asyncio.run(telegram_bot._expand_later(trip.trip_id, 1))
    assert _chats(sent) == ["chat1", "chat2", "chat3"]


def test_expand_later_stops_once_accepted(db_session, sent):
    _driver(db_session, 1, lat=20.5490, lng=-100.8000)
    _driver(db_session, 2, lat=20.5670, lng=-100.8000)
    trip = _trip(db_session)

    asyncio.run(telegram_bot._dispatch(trip, db_session, 0))
    trip.status = TripStatus.CONFIRMED
    trip.driver_phone = "+524610000001"
    db_session.commit()
    asyncio.run(telegram_bot._expand_later(trip.trip_id, 1))
    assert _chats(sent) == ["chat1"]


def test_everyone_flag_renotifies_all(db_session, sent):
    _driver(db_session, 1, lat=20.5490, lng=-100.8000)
    _driver(db_session, 2, lat=20.5670, lng=-100.8000)
    trip = _trip(db_session)

    asyncio.run(telegram_bot._dispatch(trip, db_session, 0))
    asyncio.run(telegram_bot._dispatch(trip, db_session, 0, everyone=True))
    assert sorted(_chats(sent)[1:]) == ["chat1", "chat2"]
