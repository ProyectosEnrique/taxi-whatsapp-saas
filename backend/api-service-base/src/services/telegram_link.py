"""Enlace personal para que un chofer vincule su Telegram con un toque.

El admin da de alta al chofer en el panel y pide su enlace
(`t.me/<bot>?start=<código>`); se lo manda por WhatsApp y el chofer solo toca
"Iniciar". Sin escribir comandos ni su número (antes: `/vincular +52…`).

El código es secreto, de un solo uso y vence en LINK_TTL: quien lo tenga queda
vinculado como ese chofer, así que no se reutiliza. Vive en Redis (el mismo
cliente de ride_notifs); sin Redis, en memoria.
"""
import secrets

from ..config import settings
from . import ride_notifs

LINK_TTL = 7 * 24 * 3600
_PREFIX = "taxi:tglink:"
_memory: dict[str, str] = {}


def bot_url(code: str) -> str:
    return f"https://t.me/{settings.TELEGRAM_BOT_USERNAME}?start={code}"


async def create(driver_phone: str) -> str:
    code = secrets.token_urlsafe(12)   # 16 caracteres válidos para ?start= (A-Z a-z 0-9 _ -)
    r = ride_notifs._redis_client
    if r is not None:
        await r.set(_PREFIX + code, driver_phone, ex=LINK_TTL)
    else:
        _memory[code] = driver_phone
    return code


async def consume(code: str) -> str | None:
    """Teléfono del chofer dueño del código, y lo invalida. None si no existe o venció."""
    if not code or len(code) > 64:
        return None
    r = ride_notifs._redis_client
    if r is not None:
        phone = await r.getdel(_PREFIX + code)
        return phone or None
    return _memory.pop(code, None)
