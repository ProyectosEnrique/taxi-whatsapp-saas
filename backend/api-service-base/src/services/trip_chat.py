"""Chat del chofer limpio al terminar cada viaje.

Cada mensaje con botones que el bot le manda al chofer de un viaje se anota
aquí (Redis `taxi:tripmsgs:{trip_id}`, 48 h: después Telegram ya no deja
borrarlos). Al completar o cancelar el viaje, `finish()` los borra y deja un
solo resumen sin botones; si alguno ya no se puede borrar, al menos se le
quitan los botones para que no queden controles activos.

Los avisos de "viaje nuevo" de los choferes que no lo tomaron viven en
ride_notifs: se borran unos minutos después de que otro lo acepta
(`drop_taken_notices`) o en cuanto se cancela sin chofer.

Los mensajes de SOS no se anotan aquí: nunca se borran.
"""
import asyncio
import json
import logging

from . import ride_notifs
from .telegram import delete_message, remove_buttons, send_message

logger = logging.getLogger(__name__)

_TTL = 48 * 3600
_memory: dict[str, list[tuple[str, int]]] = {}

TAKEN_NOTICE_DELETE_S = 120   # "ya fue tomado" se ve un momento y luego se borra


def _key(trip_id: str) -> str:
    return f"taxi:tripmsgs:{trip_id}"


async def track(trip_id: str, chat_id: str, message: dict | None) -> None:
    """Anota un mensaje enviado (el dict que devuelve send_with_buttons)."""
    if not message or not message.get("message_id") or not chat_id:
        return
    entry = (str(chat_id), int(message["message_id"]))
    r = ride_notifs._redis_client
    if r is not None:
        try:
            await r.rpush(_key(trip_id), json.dumps(entry))
            await r.expire(_key(trip_id), _TTL)
            return
        except Exception as exc:
            logger.warning(f"[trip_chat] track falló, usando memoria: {exc}")
    _memory.setdefault(trip_id, []).append(entry)


async def _pop_all(trip_id: str) -> list[tuple[str, int]]:
    r = ride_notifs._redis_client
    if r is not None:
        try:
            raw = await r.lrange(_key(trip_id), 0, -1)
            await r.delete(_key(trip_id))
            return [tuple(json.loads(x)) for x in raw]
        except Exception as exc:
            logger.warning(f"[trip_chat] lectura falló, usando memoria: {exc}")
    return _memory.pop(trip_id, [])


async def _clear(chat_id: str, message_id: int) -> None:
    if not await delete_message(chat_id, message_id):
        await remove_buttons(chat_id, message_id)


async def finish(trip_id: str, chat_id: str | None, summary: str | None) -> None:
    """Viaje terminado: borra sus mensajes y deja el resumen (si hay chofer)."""
    for chat, msg_id in await _pop_all(trip_id):
        await _clear(chat, msg_id)
    # Avisos de "viaje nuevo" que aún tengan el botón Aceptar (cancelado sin chofer)
    for chat, msg_id in await ride_notifs.get(trip_id):
        await _clear(chat, msg_id)
    await ride_notifs.remove(trip_id)
    if chat_id and summary:
        await send_message(chat_id, summary)


async def drop_taken_notices(notices: list[tuple[str, int]], delay_s: float = TAKEN_NOTICE_DELETE_S) -> None:
    """Borra, tras un momento, los "ya fue tomado" de los choferes que no lo alcanzaron."""
    if not notices:
        return
    await asyncio.sleep(delay_s)
    for chat, msg_id in notices:
        await _clear(chat, msg_id)


def trip_summary_line(trip) -> str:
    origin = trip.origin_address or "Origen"
    dest = trip.destination_address or "Destino"
    return f"{origin} → {dest}"


async def notify_cancelled(trip, db, by: str = "el cliente") -> None:
    """Viaje cancelado: limpia el chat y, si ya tenía chofer, le avisa que no vaya."""
    from ..models import Driver
    chat = None
    if trip.driver_phone:
        driver = db.query(Driver).filter(Driver.phone == trip.driver_phone).first()
        chat = driver.telegram_chat_id if driver else None
    summary = (f"❌ <b>Viaje cancelado por {by}</b>\n{trip_summary_line(trip)}\n\n"
               f"Ya no tienes que ir. 🚕") if chat else None
    await finish(trip.trip_id, chat, summary)
