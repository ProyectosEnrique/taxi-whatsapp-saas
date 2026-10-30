"""
Store: {ride_id: [(telegram_chat_id, message_id), ...]}
Usado para editar las notificaciones de los choferes cuando alguien mas
toma el viaje ("ya fue tomado").

Vive en Redis (no en un dict de Python en memoria): taxi-api corre con 1
solo worker hoy, pero si algun dia se escala a mas de 1 (como ya paso con
taxi-agent, Gunicorn con 2 workers) un dict en memoria solo lo ve el worker
que lo escribio — notify_drivers_new_ride() puede correr en un worker y el
callback_query de "accept_" (que necesita leer esa lista para avisarle a
los DEMAS choferes) llegar en otro, dejando esos mensajes sin actualizar
en silencio. Mismo bug real encontrado y corregido en el proyecto Ricomar
(mismo patron) el 2026-08-02.

Si REDIS_URL no esta configurado, cae a un dict en memoria como antes
(mejor eso que romper el servicio por completo).
"""
import json
import logging
from typing import Optional

from ..config import settings

logger = logging.getLogger(__name__)

_TTL = 3600  # 1h — un viaje sin tomar por mas tiempo que eso ya no aplica
_KEY_PREFIX = "taxi:ride_notifs:"

_memory_store: dict[str, list[tuple[str, int]]] = {}
_redis_client = None

if settings.REDIS_URL:
    try:
        import redis.asyncio as _redis_async
        _redis_client = _redis_async.from_url(settings.REDIS_URL, decode_responses=True)
    except Exception as exc:
        logger.warning(f"[ride_notifs] No se pudo inicializar Redis, usando memoria: {exc}")
        _redis_client = None


def _key(ride_id: str) -> str:
    return f"{_KEY_PREFIX}{ride_id}"


async def save(ride_id: str, notifications: list[tuple[str, int]]) -> None:
    if _redis_client is not None:
        try:
            await _redis_client.set(_key(ride_id), json.dumps(notifications), ex=_TTL)
            return
        except Exception as exc:
            logger.warning(f"[ride_notifs] save fallo, usando memoria: {exc}")
    _memory_store[ride_id] = notifications


async def get(ride_id: str) -> list[tuple[str, int]]:
    if _redis_client is not None:
        try:
            raw = await _redis_client.get(_key(ride_id))
            return [tuple(e) for e in json.loads(raw)] if raw else []
        except Exception as exc:
            logger.warning(f"[ride_notifs] get fallo, usando memoria: {exc}")
    return _memory_store.get(ride_id, [])


async def add(ride_id: str, notifications: list[tuple[str, int]]) -> None:
    """Agrega avisos a los ya guardados — el despacho por círculos manda el
    mismo viaje en varias tandas y todas deben marcarse "ya fue tomado"."""
    await save(ride_id, await get(ride_id) + notifications)


async def remove(ride_id: str) -> None:
    if _redis_client is not None:
        try:
            await _redis_client.delete(_key(ride_id))
            return
        except Exception as exc:
            logger.warning(f"[ride_notifs] remove fallo, usando memoria: {exc}")
    _memory_store.pop(ride_id, None)
