"""
Webhook del bot de Telegram para choferes.

Comandos:
  /vincular <tel>  — vincula la cuenta del chofer con Telegram
  /disponible      — marcar como online (recibir viajes)
  /descanso        — marcar como offline
  /estado          — ver viaje activo con botones de acción
  /ganancias       — resumen de ganancias de hoy y la semana
  /desvincular     — desvincular la cuenta

Callbacks inline:
  accept_<id>    — aceptar viaje
  arrived_<id>   — llegué al punto de origen
  start_<id>     — iniciar viaje (pasajero a bordo)
  complete_<id>  — completar viaje
"""
import logging
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Driver, Trip, TripStatus
from ..config import settings
from ..services import ride_notifs
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

def _trip_summary(trip: Trip) -> str:
    return (
        f"🚖 <b>Viaje {trip.trip_id}</b>\n"
        f"📍 Origen: {trip.origin_address}\n"
        f"🏁 Destino: {trip.destination_address}\n"
        f"💰 Tarifa: ${float(trip.fare):.2f} | {trip.distance_km} km\n"
        f"👤 Cliente: {trip.customer_name}"
    )


def _maps(lat, lng) -> str | None:
    if lat and lng:
        return f"https://maps.google.com/?q={lat},{lng}"
    return None


def _notify_customer_wa(
    customer_phone: str, driver: Driver, trip: Trip, event: str = "accepted"
) -> None:
    """Notifica al cliente vía WhatsApp gateway (fire-and-forget)."""
    import httpx
    gateway = settings.WHATSAPP_GATEWAY_URL
    secret = settings.WHATSAPP_SECRET
    if not gateway or not customer_phone:
        return

    messages = {
        "accepted": (
            f"🚕 *¡Conductor asignado!*\n\n"
            f"Tu taxi está en camino 🟢\n"
            f"Conductor: *{driver.name}*\n"
            f"Vehículo: {driver.vehicle_brand or ''} {driver.vehicle_model or ''} "
            f"({driver.vehicle_color or ''}) — *{driver.vehicle_plates or 'N/D'}*\n\n"
            f"📍 Sigue tu viaje:\n{settings.PUBLIC_URL}/seguimiento/{trip.trip_id}"
        ),
        "arrived": (
            f"🚕 *¡Tu taxi llegó!*\n\n"
            f"Tu conductor *{driver.name}* está esperándote.\n"
            f"Vehículo: {driver.vehicle_brand or ''} {driver.vehicle_model or ''} "
            f"({driver.vehicle_color or ''}) — *{driver.vehicle_plates or 'N/D'}*\n\n"
            f"📍 {settings.PUBLIC_URL}/seguimiento/{trip.trip_id}"
        ),
        "started": (
            f"🚗 *¡Viaje en camino!*\n\n"
            f"Tu conductor *{driver.name}* ha iniciado el trayecto.\n"
            f"Destino: {trip.destination_address or 'Tu destino'}\n\n"
            f"_Escribe *estado* en cualquier momento para consultar tu viaje._"
        ),
        "completed": (
            f"✅ *¡Llegaste a tu destino!*\n\n"
            f"Viaje completado con *{driver.name}*.\n"
            f"💰 Total: *${float(trip.fare or 0):.0f} MXN*\n\n"
            f"¡Gracias por usar nuestro servicio! 🙌\n"
            f"Para agendar tu próximo viaje escríbeme aquí."
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

    # ── Comandos de texto ────────────────────────────────────────────────────
    if "message" in data:
        msg     = data["message"]
        chat_id = str(msg["chat"]["id"])
        text    = (msg.get("text") or "").strip()

        if text.startswith("/vincular"):
            parts = text.split()
            if len(parts) < 2:
                await send_message(chat_id, "Usa: <code>/vincular +52XXXXXXXXXX</code>")
                return {"ok": True}
            phone  = parts[1].strip()
            driver = db.query(Driver).filter(Driver.phone == phone, Driver.is_active == True).first()
            if not driver:
                await send_message(chat_id, f"❌ No encontré ningún chofer con el número <code>{phone}</code>.")
                return {"ok": True}
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
                f"• /desvincular — dejar de recibir notificaciones"
            )

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
                "/desvincular — dejar de recibir notificaciones"
            )

    # ── Callbacks de botones inline ──────────────────────────────────────────
    elif "callback_query" in data:
        cq      = data["callback_query"]
        cq_id   = cq["id"]
        chat_id = str(cq["from"]["id"])
        cq_data = cq.get("data", "")

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
            for d_chat, msg_id in ride_notifs.get(ride_id):
                if d_chat != chat_id:
                    await edit_message_text(
                        d_chat, msg_id,
                        f"🚫 <b>Viaje {ride_id} ya fue tomado</b>\n"
                        f"Otro conductor lo aceptó primero."
                    )
            ride_notifs.remove(ride_id)

        # ── Llegué al origen ─────────────────────────────────────────────────
        elif cq_data.startswith("arrived_"):
            ride_id = cq_data[len("arrived_"):]
            driver, trip, err = _get_driver_and_trip(chat_id, ride_id, db)
            if err:
                await answer_callback(cq_id, err, alert=True)
                return {"ok": True}
            if trip.status != TripStatus.CONFIRMED:
                await answer_callback(cq_id, "⚠️ El viaje no está en estado correcto", alert=True)
                return {"ok": True}

            trip.status = TripStatus.DRIVER_ARRIVED
            db.commit()
            logger.info(f"[TelegramBot] {driver.name} llegó al origen — viaje {ride_id}")

            await answer_callback(cq_id, "📍 ¡Llegada registrada!")
            await _send_ride_action(chat_id, trip)
            _notify_customer_wa(trip.customer_phone, driver, trip, "arrived")

        # ── Iniciar viaje ────────────────────────────────────────────────────
        elif cq_data.startswith("start_"):
            ride_id = cq_data[len("start_"):]
            driver, trip, err = _get_driver_and_trip(chat_id, ride_id, db)
            if err:
                await answer_callback(cq_id, err, alert=True)
                return {"ok": True}
            if trip.status not in (TripStatus.CONFIRMED, TripStatus.DRIVER_ARRIVED):
                await answer_callback(cq_id, "⚠️ El viaje no está en estado correcto", alert=True)
                return {"ok": True}

            trip.status = TripStatus.IN_PROGRESS
            db.commit()
            logger.info(f"[TelegramBot] {driver.name} inició viaje {ride_id}")

            await answer_callback(cq_id, "🚗 ¡Viaje iniciado!")
            await _send_ride_action(chat_id, trip)
            _notify_customer_wa(trip.customer_phone, driver, trip, "started")

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


async def _send_ride_action(chat_id: str, trip: Trip) -> None:
    """
    Envía el mensaje de estado del viaje con el botón de acción correspondiente
    al estado actual. Centraliza toda la lógica de qué botón mostrar.
    """
    maps_orig = _maps(trip.origin_lat, trip.origin_lng)
    maps_dest = _maps(trip.destination_lat, trip.destination_lng)

    if trip.status == TripStatus.CONFIRMED:
        nl = chr(10)
        orig_line = (nl*2 + chr(0x1f4cd) + " <a href='" + maps_orig + "'>Abrir en Maps</a>") if maps_orig else ""
        import base64 as _b64
        _p = _b64.urlsafe_b64encode((trip.driver_phone or "").encode()).decode().rstrip("=")
        nav_url = f"{settings.PUBLIC_URL}/conductor/viaje/{trip.trip_id}?p={_p}"
        nav_line = nl*2 + chr(0x1f5fa) + " Navegar al origen: " + nav_url
        msg = (chr(0x2705) + " <b>Viaje aceptado " + chr(0x2014) + " en camino al origen</b>" +
               nl*2 + _trip_summary(trip) + orig_line + nav_line)
        await send_with_buttons(
            chat_id,
            msg,
            [[{"text": chr(0x1f7e2) + " Llegue al origen", "callback_data": f"arrived_{trip.trip_id}"}]],
        )

    elif trip.status == TripStatus.DRIVER_ARRIVED:
        dest_line = f"\n\n🏁 <a href='{maps_dest}'>Abrir destino en Maps</a>" if maps_dest else ""
        await send_with_buttons(
            chat_id,
            f"📍 <b>Llegaste al origen — esperando al pasajero</b>\n\n"
            f"{_trip_summary(trip)}{dest_line}",
            [[{"text": "🚗 Iniciar viaje", "callback_data": f"start_{trip.trip_id}"}]],
        )

    elif trip.status == TripStatus.IN_PROGRESS:
        dest_line = f"\n\n🏁 <a href='{maps_dest}'>Abrir destino en Maps</a>" if maps_dest else ""
        await send_with_buttons(
            chat_id,
            f"🚗 <b>Viaje en curso</b>\n\n"
            f"{_trip_summary(trip)}{dest_line}",
            [[{"text": "✅ Completar viaje", "callback_data": f"complete_{trip.trip_id}"}]],
        )


# ── Notificación de nuevo viaje a todos los choferes online ──────────────────

async def notify_drivers_new_ride(trip: Trip, db: Session) -> None:
    """Notifica a todos los choferes online vinculados de un nuevo viaje disponible."""
    drivers = (
        db.query(Driver)
        .filter(
            Driver.is_online  == True,
            Driver.is_active  == True,
            Driver.telegram_chat_id.isnot(None),
        )
        .all()
    )
    if not drivers:
        logger.info(f"[TelegramBot] Sin choferes online vinculados para notificar viaje {trip.trip_id}")
        return

    maps_orig = _maps(trip.origin_lat, trip.origin_lng)
    maps_dest = _maps(trip.destination_lat, trip.destination_lng)
    orig_link = f"<a href='{maps_orig}'>Origen</a>" if maps_orig else "Origen"
    dest_link = f"<a href='{maps_dest}'>Destino</a>" if maps_dest else "Destino"

    text = (
        f"🚖 <b>Nuevo viaje disponible</b>\n\n"
        f"ID: <code>{trip.trip_id}</code>\n"
        f"📍 {orig_link}: {trip.origin_address}\n"
        f"🏁 {dest_link}: {trip.destination_address}\n"
        f"💰 Tarifa: ${float(trip.fare):.2f} | {trip.distance_km} km\n"
        f"👤 Cliente: {trip.customer_name}"
    )
    buttons = [[{"text": "✅ Aceptar viaje", "callback_data": f"accept_{trip.trip_id}"}]]

    notifications: list[tuple[str, int]] = []
    for driver in drivers:
        result = await send_with_buttons(driver.telegram_chat_id, text, buttons)
        if result and result.get("message_id"):
            notifications.append((driver.telegram_chat_id, result["message_id"]))
            logger.info(f"[TelegramBot] Notificado {driver.name} — viaje {trip.trip_id}")

    ride_notifs.save(trip.trip_id, notifications)
