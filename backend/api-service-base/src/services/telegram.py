"""
Telegram Bot helper — envío de mensajes via Bot API.
Requiere TELEGRAM_BOT_TOKEN en settings.
"""
import logging
import httpx
from ..config import settings

logger = logging.getLogger(__name__)

_BASE = "https://api.telegram.org/bot{token}/{method}"


async def send_message(chat_id: str, text: str, parse_mode: str = "HTML") -> bool:
    """Envía un mensaje a un chat/grupo/canal. Retorna True si tuvo éxito."""
    if not settings.TELEGRAM_BOT_TOKEN or not chat_id:
        logger.debug("[Telegram] Bot token o chat_id no configurado — mensaje omitido")
        return False
    url = _BASE.format(token=settings.TELEGRAM_BOT_TOKEN, method="sendMessage")
    try:
        async with httpx.AsyncClient(timeout=6.0) as client:
            resp = await client.post(url, json={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": parse_mode,
            })
            if resp.status_code != 200:
                logger.warning(f"[Telegram] Error {resp.status_code}: {resp.text[:200]}")
                return False
            return True
    except Exception as e:
        logger.warning(f"[Telegram] Excepción al enviar: {e}")
        return False


async def send_to_operator(text: str) -> bool:
    """Envía al chat_id del operador configurado en TELEGRAM_ALERT_CHAT_ID."""
    return await send_message(settings.TELEGRAM_ALERT_CHAT_ID, text)
