"""Botón de pánico: la alerta va a los encargados de la base del taxi involucrado
(y siempre al operador), se puede atender una sola vez y escala si nadie atiende.
Telegram y WhatsApp se simulan: no sale nada a la red."""
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from conftest import _override_get_db
from src.auth import hash_password
from src.config import settings
from src.database import get_db
from src.models import BaseManager, Driver, Incident, TaxiGroup, Trip, TripStatus
from src.routers import sos as sos_router
from src.routers import telegram_bot
from src.services import sos

OPERATOR = "op-chat"
PASSENGER = "+524610000099"


@pytest.fixture
def sent(monkeypatch):
    log = {"tg": [], "wa": [], "callbacks": []}

    async def fake_buttons(chat_id, text, buttons):
        log["tg"].append((str(chat_id), text, buttons))
        return {"message_id": 1}

    async def fake_send(chat_id, text, parse_mode="HTML"):
        log["tg"].append((str(chat_id), text, None))
        return True

    async def fake_operator(text):
        log["tg"].append((OPERATOR, text, None))
        return True

    async def fake_answer(cq_id, text="", alert=False):
        log["callbacks"].append(text)

    for mod in (sos, telegram_bot):
        monkeypatch.setattr(mod, "send_with_buttons", fake_buttons)
        monkeypatch.setattr(mod, "send_message", fake_send)
    monkeypatch.setattr(sos, "send_to_operator", fake_operator)
    monkeypatch.setattr(telegram_bot, "answer_callback", fake_answer)
    monkeypatch.setattr(sos, "notify_whatsapp", lambda phone, msg: log["wa"].append((phone, msg)))
    monkeypatch.setattr(settings, "TELEGRAM_ALERT_CHAT_ID", OPERATOR)
    monkeypatch.setattr(settings, "TELEGRAM_WEBHOOK_SECRET", "")
    monkeypatch.setattr(settings, "WHATSAPP_SECRET", "clave")
    return log


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(telegram_bot.router)
    app.include_router(sos_router.router)
    app.dependency_overrides[get_db] = _override_get_db
    return TestClient(app)


def _world(db):
    """Dos bases (Celaya y Salvatierra) con encargado principal y de respaldo;
    un chofer de Salvatierra en viaje con un pasajero."""
    cel = TaxiGroup(name="Base Celaya", whatsapp_number="+1")
    sal = TaxiGroup(name="Base Salvatierra", whatsapp_number="+2")
    db.add_all([cel, sal])
    db.commit()
    db.add_all([
        BaseManager(group_id=cel.id, name="Encargado Celaya", phone="+5201", telegram_chat_id="cel1", priority=1),
        BaseManager(group_id=sal.id, name="Don Beto", phone="+5202", telegram_chat_id="sal1", priority=1),
        BaseManager(group_id=sal.id, name="Respaldo Sal", phone="+5203", telegram_chat_id="sal2", priority=2),
    ])
    d = Driver(phone="+524610000001", name="Pedro", password_hash=hash_password("x"), is_active=True,
               telegram_chat_id="drv1", group_id=sal.id, taxi_number="23", vehicle_plates="ABC-123",
               current_lat=20.54, current_lng=-100.80)
    t = Trip(customer_phone=PASSENGER, customer_name="Juan", origin_address="Centro",
             destination_address="Alameda", origin_lat=20.54, origin_lng=-100.80,
             destination_lat=20.52, destination_lng=-100.81, fare=45, status=TripStatus.IN_PROGRESS,
             driver_phone=d.phone, driver_name="Pedro")
    db.add_all([d, t])
    db.commit()
    return d, t


def _to(sent, chat):
    return [m for m in sent["tg"] if m[0] == chat]


def _tg(client, update):
    assert client.post("/api/v1/telegram/webhook", json=update).status_code == 200


def _cmd(client, chat, text):
    _tg(client, {"update_id": 1, "message": {"message_id": 1, "chat": {"id": chat}, "text": text}})


def _press(client, chat, data, msg_chat=None):
    cq = {"id": "q1", "from": {"id": chat}, "data": data}
    if msg_chat:
        cq["message"] = {"chat": {"id": msg_chat}}
    _tg(client, {"update_id": 2, "callback_query": cq})


# ── Chofer (Telegram) ─────────────────────────────────────────────────────────

def test_driver_sos_goes_to_his_base_and_operator(client, db_session, sent):
    _world(db_session)
    _cmd(client, "drv1", "/sos")

    assert len(_to(sent, "sal1")) == 1                      # encargado de SU base
    assert _to(sent, "cel1") == []                          # la otra base no se entera
    assert _to(sent, "sal2") == []                          # respaldo: solo si nadie atiende
    assert len(_to(sent, OPERATOR)) == 1                    # operador siempre
    alert = _to(sent, "sal1")[0]
    assert "CHOFER" in alert[1] and "Juan" in alert[1] and "911" in alert[1]
    assert "/seguimiento/" in alert[1]
    assert any(b.get("callback_data", "").startswith("sosack_") for row in alert[2] for b in row)
    assert "Alerta enviada" in _to(sent, "drv1")[-1][1]
    inc = db_session.query(Incident).one()
    assert inc.reporter_type == "driver" and inc.lat is not None


def test_sos_button_asks_to_confirm_first(client, db_session, sent):
    _, trip = _world(db_session)
    _press(client, "drv1", f"sos_{trip.trip_id}")
    assert db_session.query(Incident).count() == 0
    assert "¿Enviar alerta" in _to(sent, "drv1")[-1][1]

    _press(client, "drv1", f"sosgo_{trip.trip_id}")
    assert db_session.query(Incident).count() == 1
    assert len(_to(sent, "sal1")) == 1


def test_repeated_sos_does_not_spam(client, db_session, sent):
    _world(db_session)
    _cmd(client, "drv1", "/sos")
    _cmd(client, "drv1", "/sos")
    assert db_session.query(Incident).count() == 1
    assert len(_to(sent, "sal1")) == 1
    assert "ya está enviada" in _to(sent, "drv1")[-1][1]


def test_ride_messages_have_sos_button(db_session, sent):
    import asyncio
    _, trip = _world(db_session)
    asyncio.run(telegram_bot._send_ride_action("drv1", trip))
    labels = [b["text"] for row in sent["tg"][-1][2] for b in row]
    assert "🚨 SOS" in labels


# ── Pasajero (WhatsApp y página de seguimiento) ──────────────────────────────

def test_whatsapp_sos_needs_internal_key(client, db_session, sent):
    _world(db_session)
    r = client.post("/api/v1/sos/whatsapp", json={"phone": PASSENGER}, headers={"X-Taxi-Internal-Key": "mala"})
    assert r.status_code == 403
    assert db_session.query(Incident).count() == 0


def test_whatsapp_sos_alerts_drivers_base(client, db_session, sent):
    _world(db_session)
    r = client.post("/api/v1/sos/whatsapp", json={"phone": PASSENGER, "name": "Juanito"},
                    headers={"X-Taxi-Internal-Key": "clave"})
    assert r.status_code == 200
    assert "911" in r.json()["reply"]
    alert = _to(sent, "sal1")[0][1]
    assert "PASAJERO" in alert and "taxi 23" in alert and "ABC-123" in alert


def test_whatsapp_sos_without_trip_still_reaches_operator(client, db_session, sent):
    r = client.post("/api/v1/sos/whatsapp", json={"phone": "+524619999999"},
                    headers={"X-Taxi-Internal-Key": "clave"})
    assert r.status_code == 200
    assert "Mándanos tu ubicación" in r.json()["reply"]
    assert "no tiene encargado" in _to(sent, OPERATOR)[0][1]


def test_tracking_page_sos(client, db_session, sent):
    _, trip = _world(db_session)
    r = client.post(f"/api/v1/customer/rides/{trip.trip_id}/sos", json={"lat": 20.53, "lng": -100.805})
    assert r.status_code == 200
    inc = db_session.query(Incident).one()
    assert inc.reporter_phone == PASSENGER and float(inc.lat) == pytest.approx(20.53)


def test_tracking_page_sos_rejected_for_old_trip(client, db_session, sent):
    _, trip = _world(db_session)
    trip.status = TripStatus.COMPLETED
    db_session.commit()
    trip.updated_at = datetime.now(timezone.utc) - timedelta(hours=2)
    db_session.commit()
    r = client.post(f"/api/v1/customer/rides/{trip.trip_id}/sos", json={})
    assert r.status_code == 400
    assert db_session.query(Incident).count() == 0


# ── Atender y escalar ────────────────────────────────────────────────────────

def test_manager_acknowledges_once_and_passenger_is_told(client, db_session, sent):
    _world(db_session)
    client.post("/api/v1/sos/whatsapp", json={"phone": PASSENGER}, headers={"X-Taxi-Internal-Key": "clave"})
    inc = db_session.query(Incident).one()

    _press(client, "sal1", f"sosack_{inc.incident_id}")
    assert "tú lo atiendes" in sent["callbacks"][-1]
    assert sent["wa"] and "Don Beto" in sent["wa"][-1][1]
    assert any("Don Beto" in m[1] for m in _to(sent, OPERATOR))

    _press(client, OPERATOR, f"sosack_{inc.incident_id}")
    assert "Ya lo está atendiendo Don Beto" in sent["callbacks"][-1]


def test_strangers_cannot_acknowledge(client, db_session, sent):
    _world(db_session)
    _cmd(client, "drv1", "/sos")
    inc = db_session.query(Incident).one()
    _press(client, "intruso", f"sosack_{inc.incident_id}")
    db_session.expire_all()
    assert db_session.query(Incident).one().acknowledged_by is None


def test_unattended_alert_escalates_to_backup(client, db_session, sent):
    import asyncio
    _world(db_session)
    _cmd(client, "drv1", "/sos")
    inc = db_session.query(Incident).one()
    inc.created_at = datetime.now(timezone.utc) - timedelta(minutes=5)
    db_session.commit()

    assert asyncio.run(sos.escalate_pending(db_session)) == 1
    assert "SIN ATENDER" in _to(sent, "sal2")[0][1]
    assert asyncio.run(sos.escalate_pending(db_session)) == 0   # una sola vez


def test_acknowledged_alert_does_not_escalate(client, db_session, sent):
    import asyncio
    _world(db_session)
    _cmd(client, "drv1", "/sos")
    inc = db_session.query(Incident).one()
    _press(client, "sal1", f"sosack_{inc.incident_id}")
    inc.created_at = datetime.now(timezone.utc) - timedelta(minutes=5)
    db_session.commit()
    assert asyncio.run(sos.escalate_pending(db_session)) == 0
    assert all("SIN ATENDER" not in m[1] for m in _to(sent, "sal2"))


# ── Alta del encargado ───────────────────────────────────────────────────────

def test_manager_links_telegram(client, db_session, sent):
    db_session.add(BaseManager(name="Nuevo", phone="+5209", priority=1))
    db_session.commit()
    _cmd(client, "nuevo-chat", "/encargado +5209")
    db_session.expire_all()
    assert db_session.query(BaseManager).filter_by(phone="+5209").one().telegram_chat_id == "nuevo-chat"
    assert "alertas" in _to(sent, "nuevo-chat")[-1][1]
