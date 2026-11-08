"""Botón de pánico (SOS) para chofer y pasajero.

Quién lo activa y desde dónde:
- Chofer: botón 🚨 SOS en los mensajes del viaje en Telegram (pide confirmar) o /sos.
- Pasajero: escribir "SOS"/"auxilio" en WhatsApp (el gateway no lo pasa por la IA)
  o el botón de la página /seguimiento (mantener presionado).
- Las apps con cuenta (/cliente, /driver) siguen usando routers/incidents.py.

A quién le llega (Telegram, porque WhatsApp no deja escribir sin plantilla fuera
de la ventana de 24 h y una alerta no puede depender de eso):
- A los encargados principales (priority 1) de la BASE DEL TAXI involucrado,
  sin importar quién presionó: la base responde por su unidad y su chofer.
- Siempre copia al operador (TELEGRAM_ALERT_CHAT_ID).
- Si nadie toca "✅ Ya lo atiendo" en SOS_ESCALATE_MIN, va a los de respaldo
  (priority 2) y al operador como "SIN ATENDER" (escalate_pending, cada 30 s).

Cada mensaje deja claro que el 911 va primero: el encargado ayuda, no rescata.
"""
import logging
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy.orm import Session

from ..config import settings
from ..models import BaseManager, Driver, Incident, Trip, TripStatus
from .telegram import send_message, send_to_operator, send_with_buttons

logger = logging.getLogger(__name__)

ACTIVE = [TripStatus.CONFIRMED, TripStatus.DRIVER_ARRIVED, TripStatus.IN_PROGRESS]
RECENT_TRIP_MIN = 30     # un viaje que acaba de terminar todavía cuenta
DEDUP_MIN = 10           # misma persona otra vez en este rato → misma alerta


# ── Búsquedas ─────────────────────────────────────────────────────────────────

def _utc(dt: datetime | None) -> datetime | None:
    if dt is not None and dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def trip_for(db: Session, phone: str, role: str) -> Trip | None:
    """Viaje activo de esa persona, o el último si terminó hace poco."""
    col = Trip.driver_phone if role == "driver" else Trip.customer_phone
    trip = (db.query(Trip).filter(col == phone, Trip.status.in_(ACTIVE))
              .order_by(Trip.updated_at.desc()).first())
    if trip:
        return trip
    last = db.query(Trip).filter(col == phone).order_by(Trip.updated_at.desc()).first()
    if last and trip_is_recent(last):
        return last
    return None


def trip_is_recent(trip: Trip) -> bool:
    if trip.status in ACTIVE:
        return True
    when = _utc(trip.updated_at or trip.created_at)
    return bool(when) and datetime.now(timezone.utc) - when <= timedelta(minutes=RECENT_TRIP_MIN)


def managers(db: Session, group_id: int | None, priority: int) -> list[BaseManager]:
    if not group_id:
        return []
    return (db.query(BaseManager)
              .filter(BaseManager.group_id == group_id, BaseManager.priority == priority,
                      BaseManager.is_active == True, BaseManager.telegram_chat_id.isnot(None))
              .all())


# ── Textos ────────────────────────────────────────────────────────────────────

def _wa(phone: str) -> str:
    return "https://wa.me/" + "".join(c for c in (phone or "") if c.isdigit())


def _maps(lat, lng) -> str | None:
    return f"https://maps.google.com/?q={lat},{lng}" if lat and lng else None


def _alert_text(inc: Incident, trip: Trip | None, driver: Driver | None, header: str) -> str:
    who = "CHOFER" if inc.reporter_type == "driver" else "PASAJERO"
    lines = [f"{header} — {who}", f"<b>{inc.reporter_name or 'Sin nombre'}</b> · 📞 {inc.reporter_phone}"]
    if trip:
        if driver:
            car = " ".join(p for p in (driver.vehicle_brand, driver.vehicle_model, driver.vehicle_color) if p)
            taxi = f"taxi {driver.taxi_number} · " if driver.taxi_number else ""
            plates = f" · {driver.vehicle_plates}" if driver.vehicle_plates else ""
            lines.append(f"🚕 {taxi}{driver.name} ({car}{plates}) · 📞 {driver.phone}")
        if inc.reporter_type == "driver":
            lines.append(f"🧍 Pasajero: {trip.customer_name or ''} 📞 {trip.customer_phone}")
        lines.append(f"🛣️ {trip.origin_address or '?'} → {trip.destination_address or '?'}")
        lines.append(f"🔗 Taxi en vivo: {settings.PUBLIC_URL}/seguimiento/{trip.trip_id}")
    maps = _maps(inc.last_location_lat or inc.lat, inc.last_location_lng or inc.lng)
    lines.append(f"📍 <a href='{maps}'>Ubicación</a>" if maps else "📍 Sin ubicación todavía")
    lines.append(f"🕒 {datetime.now(timezone.utc).strftime('%H:%M UTC')} · {inc.incident_id}")
    lines.append(f"\n⚠️ Si no contestan o hay peligro, llama al <b>{settings.EMERGENCY_PHONE}</b>.")
    return "\n".join(lines)


def _alert_buttons(inc: Incident, trip: Trip | None, driver: Driver | None) -> list[list[dict]]:
    contact = [{"text": "💬 WhatsApp de quien avisó", "url": _wa(inc.reporter_phone)}]
    if trip and inc.reporter_type == "customer" and driver:
        contact.append({"text": "💬 WhatsApp del chofer", "url": _wa(driver.phone)})
    elif trip and inc.reporter_type == "driver" and trip.customer_phone:
        contact.append({"text": "💬 WhatsApp del pasajero", "url": _wa(trip.customer_phone)})
    return [[{"text": "✅ Ya lo atiendo", "callback_data": f"sosack_{inc.incident_id}"}], contact]


def reporter_reply(inc: Incident, trip: Trip | None, for_whatsapp: bool) -> str:
    """Lo que ve quien presionó el botón."""
    b = "*" if for_whatsapp else "<b>"
    e = "*" if for_whatsapp else "</b>"
    msg = (f"🚨 {b}Alerta enviada.{e} El encargado de la base ya tiene tus datos"
           f"{' y los del viaje' if trip else ''} y te va a contactar.\n"
           f"Si estás en peligro, llama al {b}{settings.EMERGENCY_PHONE}{e} ahora.")
    if not (inc.last_location_lat or inc.lat):
        msg += "\n📍 Mándanos tu ubicación (📎 → Ubicación) para ubicarte."
    return msg


# ── Activar ───────────────────────────────────────────────────────────────────

async def raise_sos(db: Session, *, reporter_type: str, phone: str, name: str | None,
                    trip: Trip | None, lat=None, lng=None, source: str = "") -> tuple[Incident, bool]:
    """Crea el incidente y avisa. Devuelve (incidente, es_nuevo); si la misma
    persona ya activó uno hace menos de DEDUP_MIN, devuelve ese sin volver a avisar."""
    since = datetime.now(timezone.utc) - timedelta(minutes=DEDUP_MIN)
    dup = (db.query(Incident)
             .filter(Incident.reporter_phone == phone, Incident.status == "active",
                     Incident.created_at >= since)
             .order_by(Incident.created_at.desc()).first())
    if dup:
        if lat and lng:
            dup.last_location_lat, dup.last_location_lng = lat, lng
            dup.last_location_at = datetime.now(timezone.utc)
            db.commit()
        return dup, False

    driver = None
    if trip and trip.driver_phone:
        driver = db.query(Driver).filter(Driver.phone == trip.driver_phone).first()
    elif reporter_type == "driver":
        driver = db.query(Driver).filter(Driver.phone == phone).first()
    # Sin GPS de quien avisó: la del taxi (van juntos o acaban de estarlo)
    if not (lat and lng) and driver and driver.current_lat:
        lat, lng = float(driver.current_lat), float(driver.current_lng)

    inc = Incident(
        trip_id=trip.trip_id if trip else None, reporter_type=reporter_type,
        reporter_phone=phone, reporter_name=name or ("Chofer" if reporter_type == "driver" else "Pasajero"),
        lat=lat, lng=lng, last_location_lat=lat, last_location_lng=lng,
        last_location_at=datetime.now(timezone.utc) if lat else None,
        notes=f"origen: {source}" if source else None,
        group_id=driver.group_id if driver else None,
    )
    db.add(inc)
    db.commit()
    db.refresh(inc)
    logger.warning(f"[SOS] {reporter_type} {phone} ({source}) — {inc.incident_id} base={inc.group_id}")

    buttons = _alert_buttons(inc, trip, driver)
    primary = managers(db, inc.group_id, 1)
    for m in primary:
        await send_with_buttons(m.telegram_chat_id, _alert_text(inc, trip, driver, "🚨 <b>SOS</b>"), buttons)
    note = "" if primary else "\n<i>(Esta base no tiene encargado registrado: atiéndelo tú.)</i>"
    if settings.TELEGRAM_ALERT_CHAT_ID:
        await send_with_buttons(settings.TELEGRAM_ALERT_CHAT_ID,
                                _alert_text(inc, trip, driver, "🚨 <b>SOS</b>") + note, buttons)
    return inc, True


# ── Atender ───────────────────────────────────────────────────────────────────

async def acknowledge(db: Session, incident_id: str, from_id: str, chat_id: str) -> str:
    """Botón "✅ Ya lo atiendo". Devuelve el texto para el aviso del botón."""
    inc = db.query(Incident).filter(Incident.incident_id == incident_id).first()
    if not inc:
        return "❌ Alerta no encontrada"
    mgr = db.query(BaseManager).filter(BaseManager.telegram_chat_id.in_([from_id, chat_id])).first()
    is_operator = settings.TELEGRAM_ALERT_CHAT_ID in (from_id, chat_id)
    if not mgr and not is_operator:
        return "⚠️ Solo los encargados pueden atender alertas"
    if inc.acknowledged_by:
        return f"Ya lo está atendiendo {inc.acknowledged_by}"

    who = mgr.name if mgr else "Operador TaxiCerca"
    inc.acknowledged_by = who
    inc.acknowledged_at = datetime.now(timezone.utc)
    db.commit()
    logger.warning(f"[SOS] {incident_id} atendido por {who}")

    # Avisar a los demás encargados de esa base y al operador
    notice = f"✅ <b>{who}</b> ya atiende la alerta {incident_id} ({inc.reporter_name})."
    for m in managers(db, inc.group_id, 1) + managers(db, inc.group_id, 2):
        if m.telegram_chat_id not in (from_id, chat_id):
            await send_message(m.telegram_chat_id, notice)
    if not is_operator:
        await send_to_operator(notice)

    # Avisar a quien presionó el botón
    reporter_msg = f"✅ {who}, encargado de la base, ya está atendiendo tu alerta. Te va a contactar."
    if inc.reporter_type == "driver":
        d = db.query(Driver).filter(Driver.phone == inc.reporter_phone).first()
        if d and d.telegram_chat_id:
            await send_message(d.telegram_chat_id, reporter_msg)
    else:
        notify_whatsapp(inc.reporter_phone, reporter_msg)
    return "✅ Registrado: tú lo atiendes"


def notify_whatsapp(phone: str, message: str) -> None:
    if not settings.WHATSAPP_GATEWAY_URL or not phone:
        return
    try:
        httpx.post(f"{settings.WHATSAPP_GATEWAY_URL}/notify/customer",
                   json={"phone": phone, "message": message},
                   headers={"X-Taxi-Internal-Key": settings.WHATSAPP_SECRET}, timeout=5.0)
    except Exception as e:
        logger.warning(f"[SOS] aviso WhatsApp a {phone} falló: {e}")


# ── Escalar ───────────────────────────────────────────────────────────────────

async def escalate_pending(db: Session) -> int:
    """Alertas sin atender después de SOS_ESCALATE_MIN → respaldo + operador."""
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=settings.SOS_ESCALATE_MIN)
    pending = (db.query(Incident)
                 .filter(Incident.status == "active", Incident.escalated == False,
                         Incident.acknowledged_by.is_(None), Incident.created_at <= cutoff)
                 .all())
    for inc in pending:
        trip = db.query(Trip).filter(Trip.trip_id == inc.trip_id).first() if inc.trip_id else None
        driver = db.query(Driver).filter(Driver.phone == trip.driver_phone).first() \
            if trip and trip.driver_phone else None
        text = _alert_text(inc, trip, driver,
                           f"⚠️ <b>SOS SIN ATENDER ({settings.SOS_ESCALATE_MIN} min)</b>")
        buttons = _alert_buttons(inc, trip, driver)
        for m in managers(db, inc.group_id, 2):
            await send_with_buttons(m.telegram_chat_id, text, buttons)
        if settings.TELEGRAM_ALERT_CHAT_ID:
            await send_with_buttons(settings.TELEGRAM_ALERT_CHAT_ID, text, buttons)
        inc.escalated = True
        logger.warning(f"[SOS] escalado sin atender: {inc.incident_id}")
    if pending:
        db.commit()
    return len(pending)
