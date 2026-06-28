"""
SSE (Server-Sent Events) — push en tiempo real a la app del conductor.
Los conductores se suscriben a GET /api/v1/driver/stream y reciben eventos
sin necesidad de polling.

Eventos emitidos:
  new_ride    — nuevo viaje disponible en el pool
  ride_taken  — un viaje fue tomado por otro conductor (quitarlo de la lista)
  assigned    — el servidor te asignó un viaje directamente
  connected   — confirmación de conexión exitosa
"""
import asyncio
import json
import logging
from typing import AsyncGenerator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from ..auth import get_current_driver
from ..models import Driver

logger = logging.getLogger(__name__)
router = APIRouter()

# driver_phone → asyncio.Queue de eventos pendientes
_connections: dict[str, asyncio.Queue] = {}

_KEEPALIVE_SECS = 25   # nginx cierra conexiones inactivas ~60s; latidos cada 25s


# ── API pública ────────────────────────────────────────────────────────────────

def connected_phones() -> set[str]:
    """Retorna el conjunto de teléfonos de conductores con SSE activo."""
    return set(_connections.keys())


async def push_event(driver_phone: str, event_type: str, data: dict) -> None:
    """Envía un evento a UN conductor específico."""
    q = _connections.get(driver_phone)
    if q:
        try:
            q.put_nowait({"type": event_type, "data": data})
        except asyncio.QueueFull:
            logger.warning(f"[SSE] Cola llena para {driver_phone}, descartando evento {event_type}")


async def broadcast_event(event_type: str, data: dict) -> None:
    """Envía un evento a TODOS los conductores conectados por SSE."""
    payload = {"type": event_type, "data": data}
    for phone, q in list(_connections.items()):
        try:
            q.put_nowait(payload)
        except asyncio.QueueFull:
            logger.warning(f"[SSE] Cola llena para {phone}, descartando broadcast {event_type}")


# ── Endpoint ───────────────────────────────────────────────────────────────────

@router.get("/api/v1/driver/stream")
async def driver_event_stream(current: Driver = Depends(get_current_driver)):
    """
    SSE stream para la app del conductor.
    El cliente se conecta una vez y recibe eventos en tiempo real.
    La app sigue soportando polling como fallback — ambos conviven.
    """
    q: asyncio.Queue = asyncio.Queue(maxsize=100)
    _connections[current.phone] = q
    logger.info(f"[SSE] {current.name} conectado ({len(_connections)} activos)")

    async def generate() -> AsyncGenerator[str, None]:
        try:
            yield f"data: {json.dumps({'type': 'connected', 'data': {'driver': current.name}})}\n\n"
            while True:
                try:
                    event = await asyncio.wait_for(q.get(), timeout=_KEEPALIVE_SECS)
                    yield f"data: {json.dumps(event)}\n\n"
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        finally:
            _connections.pop(current.phone, None)
            logger.info(f"[SSE] {current.name} desconectado ({len(_connections)} activos)")

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control":     "no-cache",
            "Connection":        "keep-alive",
            "X-Accel-Buffering": "no",   # desactiva buffer de nginx para SSE
        },
    )
