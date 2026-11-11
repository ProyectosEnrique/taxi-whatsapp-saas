"""Enlace corto /r/<código> del chofer: visible en el mensaje de Telegram (se abre
sin "¿Abrir este enlace?") y redirige a Maps según el estado del viaje."""
import asyncio

from fastapi import FastAPI
from fastapi.testclient import TestClient

from conftest import _override_get_db
from src.database import get_db
from src.models import Trip, TripStatus
from src.routers import nav_link, telegram_bot


def _client():
    app = FastAPI()
    app.include_router(nav_link.router)
    app.dependency_overrides[get_db] = _override_get_db
    return TestClient(app)


def _trip(db, status):
    t = Trip(trip_id="TRIP-1A2B3C4D", customer_phone="+524610000099", origin_address="Centro",
             destination_address="Alameda", origin_lat=20.54, origin_lng=-100.8,
             destination_lat=20.52, destination_lng=-100.815, fare=70, status=status)
    db.add(t)
    db.commit()
    return t


def _go(code="1a2b3c4d"):
    return _client().get(f"/r/{code}", follow_redirects=False)


def test_accepted_opens_full_route(db_session):
    t = _trip(db_session, TripStatus.CONFIRMED)
    assert nav_link.short_url(t).endswith("/r/1a2b3c4d")
    r = _go()
    assert r.status_code == 302
    assert "destination=20.52" in r.headers["location"]
    assert "waypoints=20.54" in r.headers["location"]


def test_in_progress_goes_to_destination_only(db_session):
    _trip(db_session, TripStatus.IN_PROGRESS)
    loc = _go().headers["location"]
    assert "destination=20.52" in loc and "waypoints" not in loc


def test_finished_or_unknown_trip_is_404(db_session):
    _trip(db_session, TripStatus.COMPLETED)
    assert _go().status_code == 404
    assert _go("ffffffff").status_code == 404


def test_bot_message_has_visible_short_link(db_session, monkeypatch):
    sent = []

    async def fake_send_with_buttons(chat_id, text, buttons):
        sent.append(text)

    monkeypatch.setattr(telegram_bot, "send_with_buttons", fake_send_with_buttons)
    t = _trip(db_session, TripStatus.CONFIRMED)
    asyncio.run(telegram_bot._send_ride_action("chat1", t))
    assert "https://taxi.nexoai.lat/r/1a2b3c4d" in sent[-1]
