"""
Webhook del bot de Telegram para choferes.

Comandos:
  /vincular <tel>  — vincula la cuenta del chofer con Telegram
  /disponible      — marcar como online (recibir viajes)
  /descanso        — marcar como offline
  /estado          — ver viaje activo con botones de acción
  /ganancias       — resumen de ganancias de hoy y la semana
  /ubicacion       — cómo compartir la ubicación en tiempo real
  /desvincular     — desvincular la cuenta

Ubicación: el chofer comparte "ubicación en tiempo real" en este chat una vez
por turno; Telegram manda cada actualización como edited_message y con eso se
guarda su posición (sin app abierta ni pantalla encendida). La usa
notify_drivers_new_ride para avisar primero a los choferes cercanos, y
durante el viaje: cerca del pasajero "Llegué" se marca solo, y cerca del
destino se le manda el botón de completar (así el chofer casi no sale de Maps).

Callbacks inline:
  accept_<id>    — aceptar viaje
  arrived_<id>   — llegué al punto de origen
  start_<id>     — iniciar viaje (pasajero a bordo)
  complete_<id>  — completar viaje
"""
import asyncio
import logging
import math
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from ..database import SessionLocal, get_db
from ..models import BaseManager, Driver, TaxiGroup, Trip, TripStatus
from ..config import settings
from . import nav_link
from ..services import ride_notifs, sos, telegram_link
from ..services.farmacerca_gift import gift_line
from ..services.telegram import (
    answer_callback,
    edit_message_text,
    send_message,
    send_with_buttons,
    send_to_operator,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/telegram", tags=["telegram-bot"])


# ── Auth ─────────────────────────────────────────────────────────────────────

def _verify_secret(x_telegram_bot_api_secret_token: str = Header(default="")):
    secret = settings.TELEGRAM_WEBHOOK_SECRET
    if secret and x_telegram_bot_api_secret_token != secret:
        raise HTTPException(403, "Token inválido")


# ── Helpers ───────────────────────────────────────────────────────────────────

def customer_label(name: str | None, phone: str | None) -> str:
    """Nombre del pasajero; si no se sabe ("Cliente"), los últimos 4 dígitos del teléfono."""
    if name and name.strip() not in ("Cliente", "Cliente WhatsApp"):
        return name.strip()
    digits = "".join(c for c in (phone or "") if c.isdigit())
    return f"Cliente …{digits[-4:]}" if digits else "Cliente"


def _trip_summary(trip: Trip) -> str:
    return (
        f"🚖 <b>Viaje {trip.trip_id}</b>\n"
        f"📍 Origen: {trip.origin_address}\n"
        f"🏁 Destino: {trip.destination_address}\n"
        f"💰 Tarifa aprox.: ${float(trip.fare):.0f} | {trip.distance_km} km\n"
        f"👤 Cliente: {customer_label(trip.customer_name, trip.customer_phone)}"
    )


def _maps(lat, lng) -> str | None:
    if lat and lng:
        return f"https://maps.google.com/?q={lat},{lng}"
    return None


def _nav_buttons(lat, lng, label: str) -> list[list[dict]]:
    """Un solo botón a lo ancho que abre Google Maps ya navegando (sin pasos extra)."""
    if not (lat and lng):
        return []
    return [[{"text": f"🚕 {label}", "url": nav_link.maps_url(lat, lng)}]]


def _pickup_nav_buttons(trip: Trip) -> list[list[dict]]:
    """Al aceptar: una sola ruta de Maps pasando por el pasajero hasta el destino,
    así el chofer no regresa a Telegram para navegar. Sin Waze (no acepta paradas)."""
    if not (trip.origin_lat and trip.origin_lng):
        return []
    if not (trip.destination_lat and trip.destination_lng):
        return _nav_buttons(trip.origin_lat, trip.origin_lng, "Ir por el pasajero")
    url = nav_link.maps_url(trip.destination_lat, trip.destination_lng, via=(trip.origin_lat, trip.origin_lng))
    return [[{"text": "🚕 Ruta completa", "url": url}]]


def _short_link_line(trip: Trip) -> str:
    """Enlace visible: Telegram lo abre sin preguntar "¿Abrir este enlace?" (el botón sí pregunta)."""
    if not nav_link.route_url(trip):
        return ""
    return f"\n\n👉 Abre directo en Maps: {nav_link.short_url(trip)}"


_LOCATION_HELP = (
    "📍 <b>Comparte tu ubicación en tiempo real</b>\n"
    "Una sola vez al empezar tu turno:\n"
    "1. Toca el clip 📎 abajo, en este chat\n"
    "2. Elige <b>Ubicación</b>\n"
    "3. Toca <b>Compartir ubicación en tiempo real</b>\n"
    "4. Elige <b>8 horas</b>\n\n"
    "Con eso <b>quedas disponible</b> y te llegan los viajes cerca de ti. "
    "Funciona aunque apagues la pantalla; deja el celular cargando 🔌\n\n"
    "Al terminar tu turno toca <b>Detener</b> en tu ubicación y quedas en descanso."
)

_OFF_LIVE_MSG = (
    "🔴 <b>Estás en descanso</b>: dejaste de compartir tu ubicación y ya no te llegan viajes.\n"
    "Para volver, comparte otra vez tu ubicación en tiempo real (📎 → Ubicación)."
)


async def expire_live_locations(db: Session) -> int:
    """Choferes cuya ubicación en vivo ya venció (se acabaron las 8 h) → descanso.
    Telegram no avisa cuando vence sola, así que lo revisa un ciclo de main.py."""
    now = datetime.now(timezone.utc)
    drivers = (db.query(Driver)
                 .filter(Driver.is_online == True, Driver.location_live_until.isnot(None),
                         Driver.location_live_until < now)
                 .all())
    for d in drivers:
        d.is_online = False
        d.location_live_until = None
    if drivers:
        db.commit()
    for d in drivers:
        logger.info(f"[TelegramBot] ubicación en vivo de {d.name} venció → descanso")
        if d.telegram_chat_id:
            await send_message(d.telegram_chat_id,
                               "⏰ Se terminó el tiempo de tu ubicación en vivo.\n" + _OFF_LIVE_MSG)
    return len(drivers)


def _aware(dt: datetime | None) -> datetime | None:
    """La base de pruebas (SQLite) devuelve fechas sin zona: se asumen UTC."""
    if dt is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6371.0
    dlat, dlng = math.radians(lat2 - lat1), math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


async def _handle_location(msg: dict, edited: bool, db: Session) -> None:
    """Guarda la posición que manda el chofer (fija o en vivo).
    Las actualizaciones en vivo llegan como edited_message: se guardan en silencio."""
    chat_id = str(msg["chat"]["id"])
    loc     = msg["location"]
    driver  = db.query(Driver).filter(Driver.telegram_chat_id == chat_id).first()
    if not driver:
        if not edited:
            await send_message(chat_id, "❌ No estás vinculado. Usa /vincular primero.")
        return

    now  = datetime.now(timezone.utc)
    live = loc.get("live_period")
    was_live = driver.location_live_until is not None
    driver.current_lat = loc["latitude"]
    driver.current_lng = loc["longitude"]
    driver.location_updated_at = now
    if not live:
        driver.location_live_until = None
    elif not edited:
        # live_period cuenta desde que se envió el mensaje; "hasta que la desactive" = 0x7FFFFFFF
        sent_at = datetime.fromtimestamp(msg.get("date") or now.timestamp(), timezone.utc)
        driver.location_live_until = sent_at + timedelta(seconds=min(live, 86400))
    elif live >= 86400:
        # "Hasta que la desactive": no tiene fin conocido; mientras siga mandando
        # posiciones se considera vigente (si no, a las 24 h pasaría a descanso)
        driver.location_live_until = max(_aware(driver.location_live_until) or now,
                                         now + timedelta(hours=2))
    # Compartir la ubicación en vivo = estar disponible; detenerla = descanso.
    # Así el chofer no tiene que escribir /disponible ni /descanso cada día.
    became_online = bool(live) and not edited and not driver.is_online
    stopped_live = edited and not live and was_live
    if became_online:
        driver.is_online = True
    if stopped_live and driver.is_online:
        driver.is_online = False
    db.commit()
    if stopped_live:
        logger.info(f"[TelegramBot] {driver.name} detuvo su ubicación en vivo → descanso")
        await send_message(chat_id, _OFF_LIVE_MSG)
        return
    try:
        await _check_trip_proximity(driver, db)
    except Exception as e:  # nunca romper el guardado de ubicación por esto
        logger.warning(f"[TelegramBot] proximidad falló para {driver.name}: {e}")
    if edited:
        return

    if not live:
        await send_message(
            chat_id,
            "📍 Recibí tu ubicación, pero es <b>fija</b>: en unos minutos ya no sabremos dónde andas.\n\n"
            + _LOCATION_HELP,
        )
        return
    # Telegram manda 0x7FFFFFFF cuando el chofer elige "hasta que la desactive"
    duration = "hasta que la desactives" if live >= 86400 else f"por {max(1, round(live / 3600))} h"
    logger.info(f"[TelegramBot] {driver.name} compartió ubicación en vivo ({live}s)")
    await send_message(
        chat_id,
        f"✅ <b>Ubicación en vivo activada</b> {duration}.\n"
        f"🟢 <b>Ya estás disponible</b>: te llegarán los viajes cerca de ti.\n\n"
        f"Al terminar tu turno toca <b>Detener</b> en tu ubicación y quedas en descanso.",
    )


def _vehicle_line(driver: Driver) -> str:
    """'Vehículo: Nissan Tsuru (blanco) — *ABC-123*' con solo los datos que hay
    (nada de "N/D": da desconfianza)."""
    car = " ".join(p for p in (driver.vehicle_brand, driver.vehicle_model) if p)
    if driver.vehicle_color:
        car = f"{car} ({driver.vehicle_color})" if car else driver.vehicle_color
    if driver.vehicle_plates:
        car = f"{car} — *{driver.vehicle_plates}*" if car else f"Placas *{driver.vehicle_plates}*"
    return f"Vehículo: {car}\n" if car else ""


def _eta_line(driver: Driver, trip: Trip) -> str:
    """' · llega en ~5 min' según la distancia del chofer al pasajero (si su
    ubicación es reciente); vacío si no se sabe."""
    if not (_location_fresh(driver) and trip.origin_lat and trip.origin_lng):
        return ""
    km = _haversine_km(float(driver.current_lat), float(driver.current_lng),
                       float(trip.origin_lat), float(trip.origin_lng))
    # línea recta × 1.3 por calles, ~25 km/h en ciudad
    minutes = max(2, round(km * 1.3 / 25 * 60))
    return f" · llega en ~{minutes} min"


def _notify_customer_wa(
    customer_phone: str, driver: Driver, trip: Trip, event: str = "accepted"
) -> None:
    """Notifica al cliente vía WhatsApp gateway (fire-and-forget)."""
    import httpx
    gateway = settings.WHATSAPP_GATEWAY_URL
    secret = settings.WHATSAPP_SECRET
    if not gateway or not customer_phone:
        return

    vehicle = _vehicle_line(driver)
    eta = _eta_line(driver, trip)
    messages = {
        "accepted": (
            f"🚕 *¡Conductor asignado!*\n\n"
            f"Tu taxi está en camino 🟢{eta}\n"
            f"Conductor: *{driver.name}*\n"
            f"{vehicle}\n"
            f"📍 Sigue tu viaje:\n{settings.PUBLIC_URL}/seguimiento/{trip.trip_id}"
        ),
        "arriving": (
            f"🚕 *¡Tu conductor está llegando!*\n\n"
            f"Ve saliendo: *{driver.name}* está a unos pasos.\n"
            f"{vehicle}\n"
            f"📍 {settings.PUBLIC_URL}/seguimiento/{trip.trip_id}"
        ),
        "completed": (
            f"✅ *¡Llegaste a tu destino!*\n\n"
            f"Viaje completado con *{driver.name}*.\n"
            f"💰 Tarifa aproximada: *${float(trip.fare or 0):.0f} MXN*\n\n"
            f"¡Gracias por usar nuestro servicio! 🙌\n"
            f"Para agendar tu próximo viaje escríbeme aquí."
            f"{gift_line(trip, driver) if event == 'completed' else ''}"
        ),
    }
    msg = messages.get(event)
    if not msg:
        return
    try:
        httpx.post(
            f"{gateway}/notify/customer",
            json={"phone": customer_phone, "message": msg},
            headers={"X-Taxi-Internal-Key": secret},
            timeout=5.0,
        )
    except Exception as e:
        logger.warning(f"[TelegramBot] WA notify failed ({event}): {e}")


# ── Webhook principal ─────────────────────────────────────────────────────────

@router.post("/webhook")
async def telegram_webhook(
    request: Request,
    db: Session = Depends(get_db),
    _=Depends(_verify_secret),
):
    data = await request.json()

    # ── Ubicación del chofer (fija, o en vivo: llega como edited_message) ────
    loc_msg = data.get("message") or data.get("edited_message")
    if loc_msg and loc_msg.get("location"):
        await _handle_location(loc_msg, "edited_message" in data, db)
        return {"ok": True}

    # ── Comandos de texto ────────────────────────────────────────────────────
    if "message" in data:
        msg     = data["message"]
        chat_id = str(msg["chat"]["id"])
        text    = (msg.get("text") or "").strip()

        if text.startswith("/start"):
            # Enlace personal del panel: t.me/<bot>?start=<código> → "/start <código>"
            parts = text.split(maxsplit=1)
            code = parts[1].strip() if len(parts) > 1 else ""
            phone = await telegram_link.consume(code) if code else None
            driver = (db.query(Driver).filter(Driver.phone == phone, Driver.is_active == True).first()
                      if phone else None)
            if driver:
                await _link_driver(driver, chat_id, db)
            elif code:
                await send_message(chat_id, "❌ Este enlace ya se usó o venció. Pide uno nuevo a tu base.")
            else:
                await send_message(
                    chat_id,
                    "👋 <b>Bienvenido a TaxiCerca</b>\n"
                    "Para recibir viajes, toca el enlace personal que te mandó tu base.\n"
                    f"Tu ID de Telegram es <code>{chat_id}</code>."
                )

        elif text.startswith("/vincular"):
            parts = text.split()
            if len(parts) < 2:
                await send_message(chat_id, "Usa: <code>/vincular +52XXXXXXXXXX</code>")
                return {"ok": True}
            phone  = parts[1].strip()
            driver = db.query(Driver).filter(Driver.phone == phone, Driver.is_active == True).first()
            if not driver:
                await send_message(chat_id, f"❌ No encontré ningún chofer con el número <code>{phone}</code>.")
                return {"ok": True}
            await _link_driver(driver, chat_id, db)

        elif text.startswith("/disponible"):
            driver = db.query(Driver).filter(Driver.telegram_chat_id == chat_id).first()
            if not driver:
                await send_message(chat_id, "❌ No estás vinculado. Usa /vincular primero.")
                return {"ok": True}
            driver.is_online = True
            db.commit()
            logger.info(f"[TelegramBot] {driver.name} se puso online vía Telegram")
            await send_message(
                chat_id,
                f"🟢 <b>¡Estás disponible!</b>\n"
                f"Recibirás notificaciones de nuevos viajes aquí."
            )
            if not _location_fresh(driver):
                await send_message(chat_id, _LOCATION_HELP)

        elif text.startswith("/sos"):
            # Escrito a mano ya es intencional: se manda sin pedir confirmación
            driver = db.query(Driver).filter(Driver.telegram_chat_id == chat_id).first()
            if not driver:
                await send_message(chat_id, f"Si estás en peligro, llama al <b>{settings.EMERGENCY_PHONE}</b>.")
                return {"ok": True}
            await _driver_sos(driver, sos.trip_for(db, driver.phone, "driver"), db)

        elif text.startswith("/encargado"):
            parts = text.split()
            if len(parts) < 2:
                await send_message(chat_id, "Usa: <code>/encargado +52XXXXXXXXXX</code>")
                return {"ok": True}
            mgr = db.query(BaseManager).filter(BaseManager.phone == parts[1].strip(),
                                               BaseManager.is_active == True).first()
            if not mgr:
                await send_message(chat_id, f"❌ No hay ningún encargado con el número <code>{parts[1]}</code>.")
                return {"ok": True}
            mgr.telegram_chat_id = chat_id
            db.commit()
            group = db.get(TaxiGroup, mgr.group_id) if mgr.group_id else None
            logger.info(f"[TelegramBot] encargado {mgr.name} vinculado chat_id={chat_id}")
            await send_message(
                chat_id,
                f"✅ <b>¡Listo, {mgr.name}!</b>\n"
                f"Aquí te llegarán las alertas 🚨 SOS de los viajes"
                f"{' de ' + group.name if group else ''}"
                f"{' (como respaldo, si nadie atiende en ' + str(settings.SOS_ESCALATE_MIN) + ' min)' if mgr.priority == 2 else ''}.\n\n"
                f"Cuando llegue una, toca <b>✅ Ya lo atiendo</b> para que los demás sepan que la tomaste "
                f"y contacta a la persona. Si hay peligro, llama al {settings.EMERGENCY_PHONE}.\n\n"
                f"<i>Activa el sonido de las notificaciones de este chat.</i>"
            )

        elif text.startswith("/ubicacion") or text.startswith("/ubicación"):
            await send_message(chat_id, _LOCATION_HELP)

        elif text.startswith("/descanso"):
            driver = db.query(Driver).filter(Driver.telegram_chat_id == chat_id).first()
            if not driver:
                await send_message(chat_id, "❌ No estás vinculado. Usa /vincular primero.")
                return {"ok": True}
            driver.is_online = False
            db.commit()
            logger.info(f"[TelegramBot] {driver.name} se puso offline vía Telegram")
            await send_message(
                chat_id,
                f"🔴 <b>Estás en descanso.</b>\n"
                f"No recibirás nuevos viajes hasta que uses /disponible."
            )

        elif text.startswith("/estado"):
            driver = db.query(Driver).filter(Driver.telegram_chat_id == chat_id).first()
            if not driver:
                await send_message(chat_id, "❌ No estás vinculado. Usa /vincular primero.")
                return {"ok": True}
            trip = (
                db.query(Trip)
                .filter(
                    Trip.driver_phone == driver.phone,
                    Trip.status.in_([
                        TripStatus.CONFIRMED,
                        TripStatus.DRIVER_ARRIVED,
                        TripStatus.IN_PROGRESS,
                    ]),
                )
                .order_by(Trip.created_at.desc())
                .first()
            )
            if not trip:
                status_icon = "🟢" if driver.is_online else "🔴"
                await send_message(
                    chat_id,
                    f"No tienes un viaje activo.\n"
                    f"Estado: {status_icon} {'Disponible' if driver.is_online else 'En descanso'}"
                )
            else:
                await _send_ride_action(chat_id, trip)

        elif text.startswith("/ganancias"):
            driver = db.query(Driver).filter(Driver.telegram_chat_id == chat_id).first()
            if not driver:
                await send_message(chat_id, "❌ No estás vinculado. Usa /vincular primero.")
                return {"ok": True}

            now        = datetime.now(timezone.utc)
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            week_start  = today_start - timedelta(days=today_start.weekday())

            trips_today = db.query(Trip).filter(
                Trip.driver_phone == driver.phone,
                Trip.status       == TripStatus.COMPLETED,
                Trip.completed_at >= today_start,
            ).all()
            trips_week = db.query(Trip).filter(
                Trip.driver_phone == driver.phone,
                Trip.status       == TripStatus.COMPLETED,
                Trip.completed_at >= week_start,
            ).all()

            earn_today = sum(float(t.fare or 0) for t in trips_today)
            earn_week  = sum(float(t.fare or 0) for t in trips_week)
            status_icon = "🟢" if driver.is_online else "🔴"

            await send_message(
                chat_id,
                f"💰 <b>Mis ganancias — {driver.name}</b>\n\n"
                f"📅 Hoy: <b>${earn_today:.2f} MXN</b> ({len(trips_today)} viajes)\n"
                f"🗓 Esta semana: <b>${earn_week:.2f} MXN</b> ({len(trips_week)} viajes)\n\n"
                f"⭐ Rating: {float(driver.rating or 5.0):.1f}\n"
                f"Estado: {status_icon} {'Disponible' if driver.is_online else 'En descanso'}"
            )

        elif text.startswith("/desvincular"):
            driver = db.query(Driver).filter(Driver.telegram_chat_id == chat_id).first()
            if driver:
                driver.telegram_chat_id = None
                db.commit()
                await send_message(chat_id, "✅ Desvinculado. Ya no recibirás notificaciones de viajes.")
            else:
                await send_message(chat_id, "No estabas vinculado.")

        else:
            await send_message(
                chat_id,
                "<b>Comandos disponibles:</b>\n"
                "/vincular +52XXXXXXXXXX — vincular tu cuenta\n"
                "/disponible — activarte para recibir viajes\n"
                "/descanso — ponerte offline\n"
                "/estado — ver viaje activo\n"
                "/ganancias — ver tus ganancias del día\n"
                "/ubicacion — compartir tu ubicación en tiempo real\n"
                "/sos — 🚨 alerta de emergencia al encargado de tu base\n"
                "/desvincular — dejar de recibir notificaciones"
            )

    # ── Callbacks de botones inline ──────────────────────────────────────────
    elif "callback_query" in data:
        cq      = data["callback_query"]
        cq_id   = cq["id"]
        chat_id = str(cq["from"]["id"])
        cq_data = cq.get("data", "")

        # ── SOS ──────────────────────────────────────────────────────────────
        # (antes que los demás: "sos_" no debe confundirse con otro prefijo)
        if cq_data.startswith("sosack_"):
            msg_chat = str((cq.get("message") or {}).get("chat", {}).get("id", ""))
            reply = await sos.acknowledge(db, cq_data[len("sosack_"):], chat_id, msg_chat)
            await answer_callback(cq_id, reply, alert=True)
            return {"ok": True}

        if cq_data.startswith("sos_"):
            # Un toque por accidente no debe alertar a nadie: se pide confirmar
            await answer_callback(cq_id)
            await send_with_buttons(
                chat_id,
                "🚨 <b>¿Enviar alerta de emergencia?</b>\n"
                "Se avisa al encargado de tu base con tu ubicación y los datos del viaje.\n"
                f"Si estás en peligro, llama también al <b>{settings.EMERGENCY_PHONE}</b>.",
                [[{"text": "🚨 Sí, enviar alerta", "callback_data": f"sosgo_{cq_data[len('sos_'):]}"}]],
            )
            return {"ok": True}

        if cq_data.startswith("sosgo_"):
            driver = db.query(Driver).filter(Driver.telegram_chat_id == chat_id).first()
            if not driver:
                await answer_callback(cq_id, f"Llama al {settings.EMERGENCY_PHONE}", alert=True)
                return {"ok": True}
            trip = db.query(Trip).filter(Trip.trip_id == cq_data[len("sosgo_"):],
                                         Trip.driver_phone == driver.phone).first()
            await answer_callback(cq_id, "🚨 Alerta enviada")
            await _driver_sos(driver, trip or sos.trip_for(db, driver.phone, "driver"), db)
            return {"ok": True}

        # ── Aceptar viaje ────────────────────────────────────────────────────
        if cq_data.startswith("accept_"):
            ride_id = cq_data[len("accept_"):]
            driver  = db.query(Driver).filter(Driver.telegram_chat_id == chat_id).first()
            trip    = db.query(Trip).filter(Trip.trip_id == ride_id).first()

            if not driver or not trip:
                await answer_callback(cq_id, "❌ Viaje no encontrado", alert=True)
                return {"ok": True}
            # Conductor diferente ya lo tomó
            if trip.driver_phone and trip.driver_phone != driver.phone:
                await answer_callback(cq_id, "⚠️ Este viaje ya fue tomado por otro conductor", alert=True)
                return {"ok": True}
            # Viaje ya no está disponible (confirmado por otro medio)
            if trip.status != TripStatus.REQUESTED:
                await answer_callback(cq_id, "⚠️ Este viaje ya no está disponible", alert=True)
                return {"ok": True}

            trip.driver_phone = driver.phone
            trip.driver_name  = driver.name
            trip.status       = TripStatus.CONFIRMED
            db.commit()
            logger.info(f"[TelegramBot] {driver.name} aceptó viaje {ride_id} vía Telegram")

            await answer_callback(cq_id, "✅ ¡Viaje aceptado!")
            await _send_ride_action(chat_id, trip)

            try:
                await send_to_operator(
                    f"✅ Viaje <code>{ride_id}</code> tomado por <b>{driver.name}</b> vía Telegram"
                )
            except Exception:
                pass

            _notify_customer_wa(trip.customer_phone, driver, trip, "accepted")

            # Marcar como tomado en los chats de los demás conductores
            for d_chat, msg_id in await ride_notifs.get(ride_id):
                if d_chat != chat_id:
                    await edit_message_text(
                        d_chat, msg_id,
                        f"🚫 <b>Viaje {ride_id} ya fue tomado</b>\n"
                        f"Otro conductor lo aceptó primero."
                    )
            await ride_notifs.remove(ride_id)

        # ── Llegué al origen ─────────────────────────────────────────────────
        elif cq_data.startswith("arrived_"):
            ride_id = cq_data[len("arrived_"):]
            driver, trip, err = _get_driver_and_trip(chat_id, ride_id, db)
            if err:
                await answer_callback(cq_id, err, alert=True)
                return {"ok": True}
            if trip.status == TripStatus.DRIVER_ARRIVED:
                await answer_callback(cq_id, "📍 Tu llegada ya estaba registrada")
                return {"ok": True}
            if trip.status != TripStatus.CONFIRMED:
                await answer_callback(cq_id, "⚠️ El viaje no está en estado correcto", alert=True)
                return {"ok": True}

            await answer_callback(cq_id, "📍 ¡Llegada registrada!")
            await _mark_arrived(driver, trip, db)

        # ── Iniciar viaje ────────────────────────────────────────────────────
        elif cq_data.startswith("start_"):
            ride_id = cq_data[len("start_"):]
            driver, trip, err = _get_driver_and_trip(chat_id, ride_id, db)
            if err:
                await answer_callback(cq_id, err, alert=True)
                return {"ok": True}
            if trip.status == TripStatus.IN_PROGRESS:
                await answer_callback(cq_id, "🚗 El viaje ya estaba iniciado")
                return {"ok": True}
            if trip.status not in (TripStatus.CONFIRMED, TripStatus.DRIVER_ARRIVED):
                await answer_callback(cq_id, "⚠️ El viaje no está en estado correcto", alert=True)
                return {"ok": True}

            await answer_callback(cq_id, "🚗 ¡Viaje iniciado!")
            await _mark_started(driver, trip, db)

        # ── Completar viaje ──────────────────────────────────────────────────
        elif cq_data.startswith("complete_"):
            ride_id = cq_data[len("complete_"):]
            driver, trip, err = _get_driver_and_trip(chat_id, ride_id, db)
            if err:
                await answer_callback(cq_id, err, alert=True)
                return {"ok": True}
            if trip.status != TripStatus.IN_PROGRESS:
                await answer_callback(cq_id, "⚠️ El viaje no está en curso", alert=True)
                return {"ok": True}

            trip.status       = TripStatus.COMPLETED
            trip.completed_at = datetime.now(timezone.utc)
            driver.total_trips    = (driver.total_trips or 0) + 1
            driver.total_earnings = (
                Decimal(str(driver.total_earnings or 0)) + Decimal(str(trip.fare or 0))
            )
            db.commit()
            logger.info(f"[TelegramBot] Viaje {ride_id} completado por {driver.name}")

            await answer_callback(cq_id, "✅ ¡Viaje completado!")
            await send_message(
                chat_id,
                f"✅ <b>¡Viaje completado!</b>\n\n"
                f"👤 Cliente: {trip.customer_name}\n"
                f"🏁 Destino: {trip.destination_address}\n"
                f"💰 Ganancia: <b>${float(trip.fare or 0):.2f} MXN</b>\n"
                f"📏 Distancia: {trip.distance_km} km\n\n"
                f"Acumulado total: ${float(driver.total_earnings or 0):.2f} MXN\n\n"
                f"Usa /disponible para recibir el siguiente viaje. 🚕"
            )
            _notify_customer_wa(trip.customer_phone, driver, trip, "completed")

    return {"ok": True}


# ── Helpers internos ──────────────────────────────────────────────────────────

def _get_driver_and_trip(chat_id: str, ride_id: str, db) -> tuple:
    """Devuelve (driver, trip, error_msg). error_msg es None si todo está bien."""
    driver = db.query(Driver).filter(Driver.telegram_chat_id == chat_id).first()
    trip   = db.query(Trip).filter(Trip.trip_id == ride_id).first()
    if not driver or not trip:
        return None, None, "❌ Viaje no encontrado"
    if trip.driver_phone != driver.phone:
        return None, None, "⚠️ Este viaje no te pertenece"
    return driver, trip, None


async def _link_driver(driver: Driver, chat_id: str, db: Session) -> None:
    """Liga este chat al chofer (enlace personal o /vincular) y le explica qué sigue."""
    # Un chat = un chofer: si este Telegram estaba ligado a otra cuenta, se suelta
    db.query(Driver).filter(Driver.telegram_chat_id == chat_id, Driver.id != driver.id) \
        .update({Driver.telegram_chat_id: None})
    driver.telegram_chat_id = chat_id
    db.commit()
    logger.info(f"[TelegramBot] {driver.name} vinculó Telegram chat_id={chat_id}")
    await send_message(
        chat_id,
        f"✅ <b>¡Listo, {driver.name}!</b>\n"
        f"Cuenta vinculada. Recibirás viajes aquí con botón para aceptar.\n\n"
        f"<b>Comandos disponibles:</b>\n"
        f"• /disponible — activarte para recibir viajes\n"
        f"• /descanso — ponerte offline\n"
        f"• /estado — ver tu viaje activo\n"
        f"• /ganancias — ver tus ganancias del día\n"
        f"• /ubicacion — compartir tu ubicación en tiempo real\n"
        f"• /sos — 🚨 alerta de emergencia al encargado de tu base\n"
        f"• /desvincular — dejar de recibir notificaciones"
    )
    await send_message(chat_id, _LOCATION_HELP)


def _sos_row(trip: Trip) -> list[list[dict]]:
    return [[{"text": "🚨 SOS", "callback_data": f"sos_{trip.trip_id}"}]]


async def _driver_sos(driver: Driver, trip: Trip | None, db: Session) -> None:
    """El chofer pidió ayuda: alerta a su base + operador y le confirma."""
    inc, new = await sos.raise_sos(db, reporter_type="driver", phone=driver.phone, name=driver.name,
                                   trip=trip, source="telegram")
    msg = sos.reporter_reply(inc, trip, for_whatsapp=False)
    if not _location_fresh(driver):
        msg += "\n\n" + _LOCATION_HELP
    await send_message(driver.telegram_chat_id, msg if new else "🚨 Tu alerta ya está enviada. " + msg)


async def _send_ride_action(chat_id: str, trip: Trip) -> None:
    """
    Envía el mensaje de estado del viaje con el botón de acción correspondiente
    al estado actual. Centraliza toda la lógica de qué botón mostrar.
    """
    if trip.status == TripStatus.CONFIRMED:
        await send_with_buttons(
            chat_id,
            f"✅ <b>Viaje aceptado — en camino al pasajero</b>\n\n{_trip_summary(trip)}\n\n"
            f"<i>🚕 Ruta completa: Maps te lleva al pasajero y sigue al destino. "
            f"Llegué e Iniciar se marcan solos; el botón verde es por si no se marca.</i>"
            f"{_short_link_line(trip)}",
            _pickup_nav_buttons(trip)
            + [[{"text": "🟢 Llegué al origen", "callback_data": f"arrived_{trip.trip_id}"}]]
            + _sos_row(trip),
        )

    elif trip.status == TripStatus.DRIVER_ARRIVED:
        await send_with_buttons(
            chat_id,
            f"📍 <b>Llegaste — esperando al pasajero</b>\n\n"
            f"{_trip_summary(trip)}\n\nCuando suba el pasajero, arranca: el viaje se inicia solo "
            f"al alejarte del punto. El botón es por si no se marca.",
            [[{"text": "🚕 Iniciar viaje", "callback_data": f"start_{trip.trip_id}"}]]
            + _sos_row(trip),
        )

    elif trip.status == TripStatus.IN_PROGRESS:
        await send_with_buttons(
            chat_id,
            f"🚗 <b>Viaje en curso</b>\n\n{_trip_summary(trip)}\n\n"
            f"<i>Cerca del destino te mando el botón para completar.</i>"
            f"{_short_link_line(trip)}",
            _nav_buttons(trip.destination_lat, trip.destination_lng, "Ir al destino")
            + [[{"text": "✅ Completar viaje", "callback_data": f"complete_{trip.trip_id}"}]]
            + _sos_row(trip),
        )


async def _mark_arrived(driver: Driver, trip: Trip, db: Session, auto: bool = False) -> None:
    """Pasa el viaje a "llegó al origen" y les avisa al chofer y al pasajero."""
    trip.status = TripStatus.DRIVER_ARRIVED
    db.commit()
    logger.info(f"[TelegramBot] {driver.name} llegó al origen ({'auto' if auto else 'botón'}) — viaje {trip.trip_id}")
    await _send_ride_action(driver.telegram_chat_id, trip)
    await _notify_arriving(driver, trip)


async def _mark_started(driver: Driver, trip: Trip, db: Session, auto: bool = False) -> None:
    """Pasa el viaje a "en curso" y le manda al chofer el botón al destino.
    Al pasajero no se le avisa: ya va en el taxi."""
    trip.status = TripStatus.IN_PROGRESS
    db.commit()
    logger.info(f"[TelegramBot] {driver.name} inició viaje ({'auto' if auto else 'botón'}) {trip.trip_id}")
    await _send_ride_action(driver.telegram_chat_id, trip)


async def _notify_arriving(driver: Driver, trip: Trip) -> None:
    """"Tu conductor está llegando": una sola vez por viaje, lo que pase primero
    (acercarse a ARRIVING_NOTICE_RADIUS_M, el "Llegué" automático o el botón)."""
    if await ride_notifs.claim_once("arriving_msg", trip.trip_id):
        _notify_customer_wa(trip.customer_phone, driver, trip, "arriving")


def _seconds_since(dt: datetime | None) -> float:
    if dt is None:
        return float("inf")
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - dt).total_seconds()


async def _check_trip_proximity(driver: Driver, db: Session) -> None:
    """Con cada ubicación del chofer: cerca del pasajero marca "Llegué" solo;
    al alejarse del punto ya con el pasajero inicia el viaje; cerca del
    destino le manda el botón de completar (cada aviso una sola vez)."""
    trip = (db.query(Trip)
              .filter(Trip.driver_phone == driver.phone,
                      Trip.status.in_([TripStatus.CONFIRMED, TripStatus.DRIVER_ARRIVED,
                                       TripStatus.IN_PROGRESS]))
              .order_by(Trip.updated_at.desc())
              .first())
    if not trip or _seconds_since(trip.updated_at) < settings.PROXIMITY_MIN_AGE_S:
        return
    here = (float(driver.current_lat), float(driver.current_lng))

    if trip.status == TripStatus.CONFIRMED and trip.origin_lat:
        meters = _haversine_km(*here, float(trip.origin_lat), float(trip.origin_lng)) * 1000
        if meters <= settings.ARRIVING_NOTICE_RADIUS_M:
            await _notify_arriving(driver, trip)
        if (settings.AUTO_ARRIVE_RADIUS_M and meters <= settings.AUTO_ARRIVE_RADIUS_M
                and await ride_notifs.claim_once("arrived", trip.trip_id)):
            await _mark_arrived(driver, trip, db, auto=True)

    elif trip.status == TripStatus.DRIVER_ARRIVED and settings.AUTO_START_RADIUS_M and trip.origin_lat:
        meters = _haversine_km(*here, float(trip.origin_lat), float(trip.origin_lng)) * 1000
        if meters > settings.AUTO_START_RADIUS_M and await ride_notifs.claim_once("started", trip.trip_id):
            await _mark_started(driver, trip, db, auto=True)

    elif trip.status == TripStatus.IN_PROGRESS and settings.NEAR_DEST_RADIUS_M and trip.destination_lat:
        meters = _haversine_km(*here, float(trip.destination_lat), float(trip.destination_lng)) * 1000
        if meters <= settings.NEAR_DEST_RADIUS_M and await ride_notifs.claim_once("near_dest", trip.trip_id):
            logger.info(f"[TelegramBot] {driver.name} cerca del destino — viaje {trip.trip_id}")
            await send_with_buttons(
                driver.telegram_chat_id,
                f"🏁 <b>Ya casi llegas al destino</b>\n{trip.destination_address}\n\n"
                f"💰 Tarifa aprox. <b>${float(trip.fare or 0):.0f}</b> (cobra según tu base) y toca completar.",
                [[{"text": "✅ Completar viaje", "callback_data": f"complete_{trip.trip_id}"}]],
            )


# ── Notificación de nuevo viaje: primero a los cercanos, luego a todos ───────

def _location_fresh(driver: Driver) -> bool:
    at = driver.location_updated_at
    if not at or driver.current_lat is None or driver.current_lng is None:
        return False
    now = datetime.now(timezone.utc)
    if at.tzinfo is None:
        at = at.replace(tzinfo=timezone.utc)
    if now - at <= timedelta(minutes=settings.LOCATION_FRESH_MIN):
        return True
    # Con ubicación en vivo activa, Telegram solo manda cambios: estacionado
    # puede pasar mucho sin actualizar, y su última posición sigue siendo buena.
    until = driver.location_live_until
    if until and until.tzinfo is None:
        until = until.replace(tzinfo=timezone.utc)
    return bool(until and until > now and now - at <= timedelta(minutes=settings.LOCATION_LIVE_FRESH_MIN))


def _rings_km() -> list[float]:
    try:
        return [float(x) for x in settings.DISPATCH_RINGS_KM.split(",") if x.strip()]
    except ValueError:
        logger.warning(f"[TelegramBot] DISPATCH_RINGS_KM inválido: {settings.DISPATCH_RINGS_KM!r} — aviso a todos")
        return []


async def _send_ride(trip: Trip, drivers: list[Driver], dist: dict[int, float]) -> None:
    maps_orig = _maps(trip.origin_lat, trip.origin_lng)
    maps_dest = _maps(trip.destination_lat, trip.destination_lng)
    orig_link = f"<a href='{maps_orig}'>Origen</a>" if maps_orig else "Origen"
    dest_link = f"<a href='{maps_dest}'>Destino</a>" if maps_dest else "Destino"

    text = (
        f"🚖 <b>Nuevo viaje disponible</b>\n\n"
        f"ID: <code>{trip.trip_id}</code>\n"
        f"📍 {orig_link}: {trip.origin_address}\n"
        f"🏁 {dest_link}: {trip.destination_address}\n"
        f"💰 Tarifa aprox.: ${float(trip.fare):.0f} | {trip.distance_km} km\n"
        f"👤 Cliente: {customer_label(trip.customer_name, trip.customer_phone)}"
    )
    buttons = [[{"text": "✅ Aceptar viaje", "callback_data": f"accept_{trip.trip_id}"}]]

    notifications: list[tuple[str, int]] = []
    for driver in drivers:
        km = dist.get(driver.id)
        near = f"\n📏 Estás a {km:.1f} km del cliente" if km is not None else ""
        result = await send_with_buttons(driver.telegram_chat_id, text + near, buttons)
        if result and result.get("message_id"):
            notifications.append((driver.telegram_chat_id, result["message_id"]))
            logger.info(f"[TelegramBot] Notificado {driver.name} — viaje {trip.trip_id}")

    await ride_notifs.add(trip.trip_id, notifications)


async def _dispatch(trip: Trip, db: Session, ring: int, everyone: bool = False) -> int | None:
    """Avisa del viaje al círculo `ring` o al siguiente que tenga choferes, sin
    repetir a quien ya se le avisó. Devuelve el círculo que sigue (para
    ampliarlo si nadie acepta) o None si ya se avisó a todos."""
    drivers = (
        db.query(Driver)
        .filter(
            Driver.is_online  == True,
            Driver.is_active  == True,
            Driver.telegram_chat_id.isnot(None),
        )
        .all()
    )
    if not everyone:
        notified = {chat for chat, _ in await ride_notifs.get(trip.trip_id)}
        drivers = [d for d in drivers if d.telegram_chat_id not in notified]
    if not drivers:
        logger.info(f"[TelegramBot] Sin choferes online vinculados para notificar viaje {trip.trip_id}")
        return None

    dist: dict[int, float] = {}
    if trip.origin_lat is not None and trip.origin_lng is not None:
        for d in drivers:
            if _location_fresh(d):
                dist[d.id] = _haversine_km(float(d.current_lat), float(d.current_lng),
                                           float(trip.origin_lat), float(trip.origin_lng))

    rings = [] if everyone or not dist else _rings_km()
    for i in range(ring, len(rings)):
        near = sorted((d for d in drivers if dist.get(d.id, math.inf) <= rings[i]), key=lambda d: dist[d.id])
        if near:
            logger.info(f"[TelegramBot] Viaje {trip.trip_id}: {len(near)} chofer(es) a ≤{rings[i]:g} km")
            await _send_ride(trip, near, dist)
            return i + 1

    await _send_ride(trip, drivers, dist)
    return None


async def _expand_later(trip_id: str, ring: int) -> None:
    """Si nadie aceptó en DISPATCH_RING_WAIT_S, avisa al siguiente círculo.
    Corre aparte (asyncio.create_task); si el proceso se reinicia antes, el
    _ride_timeout_monitor de main.py re-avisa a todos a los 3 min."""
    while ring is not None:
        await asyncio.sleep(settings.DISPATCH_RING_WAIT_S)
        db = SessionLocal()
        try:
            trip = db.query(Trip).filter(Trip.trip_id == trip_id).first()
            if not trip or trip.status != TripStatus.REQUESTED or trip.driver_phone:
                return
            ring = await _dispatch(trip, db, ring)
        except Exception as exc:
            logger.warning(f"[TelegramBot] Ampliar aviso de {trip_id} falló: {exc}")
            return
        finally:
            db.close()


async def notify_drivers_new_ride(trip: Trip, db: Session, everyone: bool = False) -> None:
    """Avisa de un viaje nuevo: primero a los choferes con ubicación reciente
    dentro del 1er círculo (DISPATCH_RINGS_KM), luego amplía cada
    DISPATCH_RING_WAIT_S, y al final a todos los online. Si nadie tiene
    ubicación reciente (o everyone=True) avisa a todos de una vez, como antes.
    El primero que acepta se lo lleva (callback accept_)."""
    next_ring = await _dispatch(trip, db, 0, everyone=everyone)
    if next_ring is not None:
        asyncio.create_task(_expand_later(trip.trip_id, next_ring))
