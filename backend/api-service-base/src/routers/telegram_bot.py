"""
Webhook del bot de Telegram para choferes.

Comandos disponibles:
  /vincular <teléfono>  — vincula la cuenta del chofer con Telegram
  /estado               — muestra el viaje activo asignado

Callbacks inline:
  accept_<ride_id>      — acepta y toma el viaje
"""
import logging
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

# ── Auth ────────────────────────────────────────────────────────────────────────

def _verify_secret(x_telegram_bot_api_secret_token: str = Header(default="")):
    secret = settings.TELEGRAM_WEBHOOK_SECRET
    if secret and x_telegram_bot_api_secret_token != secret:
        raise HTTPException(403, "Token inválido")


# ── Helpers ─────────────────────────────────────────────────────────────────────

def _trip_summary(trip: Trip) -> str:
    return (
        f"🚖 <b>Viaje {trip.trip_id}</b>\n"
        f"📍 Origen: {trip.origin_address}\n"
        f"🏁 Destino: {trip.destination_address}\n"
        f"💰 Tarifa: ${float(trip.fare):.2f} | {trip.distance_km} km\n"
        f"👤 Cliente: {trip.customer_name}"
    )


def _notify_customer_wa(customer_phone: str, driver: Driver, trip: Trip) -> None:
    """Llama al gateway de WhatsApp para avisar al cliente."""
    import httpx
    try:
        gateway = settings.WHATSAPP_GATEWAY_URL
        secret  = settings.WHATSAPP_SECRET
        msg = (
            f"🚕 *¡Conductor asignado!*\n\n"
            f"Tu taxi está en camino 🟢\n"
            f"Conductor: *{driver.name}*\n"
            f"Vehículo: {driver.vehicle_brand or ''} {driver.vehicle_model or ''} "
            f"({driver.vehicle_color or ''}) — *{driver.vehicle_plates or 'N/D'}*\n\n"
            f"📍 Sigue tu viaje en tiempo real:\n"
            f"{settings.PUBLIC_URL}/seguimiento/{trip.trip_id}"
        )
        httpx.post(
            f"{gateway}/notify/customer",
            json={"phone": customer_phone, "message": msg},
            headers={"X-Taxi-Internal-Key": secret},
            timeout=5.0,
        )
    except Exception as e:
        logger.warning(f"[TelegramBot] WA notify failed: {e}")


# ── Webhook principal ────────────────────────────────────────────────────────────

@router.post("/webhook")
async def telegram_webhook(
    request: Request,
    db: Session = Depends(get_db),
    _=Depends(_verify_secret),
):
    data = await request.json()

    # ── Mensajes de texto (comandos) ─────────────────────────────────────────
    if "message" in data:
        msg     = data["message"]
        chat_id = str(msg["chat"]["id"])
        text    = (msg.get("text") or "").strip()

        if text.startswith("/vincular"):
            parts = text.split()
            if len(parts) < 2:
                await send_message(chat_id, "Usa: <code>/vincular +52XXXXXXXXXX</code>")
                return {"ok": True}
            phone = parts[1].strip()
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
                f"Tu cuenta está vinculada. Recibirás notificaciones de viajes disponibles aquí.\n\n"
                f"Cuando llegue un viaje, presiona el botón para aceptarlo."
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
                    Trip.status.in_([TripStatus.CONFIRMED, TripStatus.DRIVER_ARRIVED, TripStatus.IN_PROGRESS]),
                )
                .order_by(Trip.created_at.desc())
                .first()
            )
            if not trip:
                await send_message(chat_id, "No tienes un viaje activo en este momento.")
            else:
                await send_message(chat_id, _trip_summary(trip) + f"\n📋 Estado: <b>{trip.status.value}</b>")

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
                "Comandos disponibles:\n"
                "/vincular +52XXXXXXXXXX — vincular tu cuenta\n"
                "/estado — ver viaje activo\n"
                "/desvincular — dejar de recibir notificaciones"
            )

    # ── Callback de botón inline ─────────────────────────────────────────────
    elif "callback_query" in data:
        cq      = data["callback_query"]
        cq_id   = cq["id"]
        chat_id = str(cq["from"]["id"])
        cq_data = cq.get("data", "")

        if cq_data.startswith("accept_"):
            ride_id = cq_data[len("accept_"):]
            driver  = db.query(Driver).filter(Driver.telegram_chat_id == chat_id).first()
            trip    = db.query(Trip).filter(Trip.trip_id == ride_id).first()

            if not driver or not trip:
                await answer_callback(cq_id, "❌ Viaje no encontrado", alert=True)
                return {"ok": True}

            if trip.status != TripStatus.REQUESTED or trip.driver_phone:
                await answer_callback(cq_id, "⚠️ Este viaje ya fue tomado por otro conductor", alert=True)
                return {"ok": True}

            # Asignar el viaje
            trip.driver_phone = driver.phone
            trip.driver_name  = driver.name
            trip.status       = TripStatus.CONFIRMED
            db.commit()
            logger.info(f"[TelegramBot] {driver.name} aceptó viaje {ride_id} vía Telegram")

            await answer_callback(cq_id, "✅ ¡Viaje aceptado!")

            # Confirmar al chofer que aceptó
            maps_orig = (
                f"https://maps.google.com/?q={trip.origin_lat},{trip.origin_lng}"
                if trip.origin_lat else "Sin coords"
            )
            await send_message(
                chat_id,
                f"✅ <b>Viaje aceptado — {ride_id}</b>\n\n"
                f"{_trip_summary(trip)}\n\n"
                f"📍 <a href='{maps_orig}'>Abrir origen en Maps</a>\n\n"
                f"Cuando llegues al punto de recogida, usa tu app para marcar la llegada."
            )

            # Avisar al operador
            try:
                await send_to_operator(
                    f"✅ Viaje <code>{ride_id}</code> tomado por <b>{driver.name}</b> vía Telegram"
                )
            except Exception:
                pass

            # Notificar al cliente por WhatsApp
            _notify_customer_wa(trip.customer_phone, driver, trip)

            # Editar el mensaje en el chat de los demás choferes notificados
            others = [
                (d_chat, msg_id)
                for d_chat, msg_id in ride_notifs.get(ride_id)
                if d_chat != chat_id
            ]
            for d_chat, msg_id in others:
                await edit_message_text(
                    d_chat, msg_id,
                    f"🚫 <b>Viaje {ride_id} ya fue tomado</b>\n"
                    f"Otro conductor lo aceptó primero."
                )
            ride_notifs.remove(ride_id)

    return {"ok": True}


# ── Función de notificación a choferes (usada desde whatsapp.py y customer_rides.py) ──

async def notify_drivers_new_ride(trip: Trip, db: Session) -> None:
    """Notifica a todos los choferes online vinculados de un nuevo viaje disponible."""
    drivers = (
        db.query(Driver)
        .filter(
            Driver.is_online == True,
            Driver.is_active == True,
            Driver.telegram_chat_id.isnot(None),
        )
        .all()
    )
    if not drivers:
        logger.info(f"[TelegramBot] Sin choferes online vinculados para notificar viaje {trip.trip_id}")
        return

    maps_dest = f"https://maps.google.com/?q={trip.destination_lat},{trip.destination_lng}"
    text = (
        f"🚖 <b>Nuevo viaje disponible</b>\n\n"
        f"ID: <code>{trip.trip_id}</code>\n"
        f"📍 Origen: {trip.origin_address}\n"
        f"🏁 <a href='{maps_dest}'>Destino</a>: {trip.destination_address}\n"
        f"💰 Tarifa: ${float(trip.fare):.2f} | {trip.distance_km} km\n"
        f"👤 Cliente: {trip.customer_name}"
    )
    buttons = [[{"text": "✅ Aceptar viaje", "callback_data": f"accept_{trip.trip_id}"}]]

    notifications: list[tuple[str, int]] = []
    for driver in drivers:
        result = await send_with_buttons(driver.telegram_chat_id, text, buttons)
        if result and result.get("message_id"):
            notifications.append((driver.telegram_chat_id, result["message_id"]))
            logger.info(f"[TelegramBot] Notificado {driver.name} ({driver.telegram_chat_id}) — viaje {trip.trip_id}")

    ride_notifs.save(trip.trip_id, notifications)
