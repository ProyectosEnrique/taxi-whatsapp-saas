"""
Telegram Bot helper — envío de mensajes via Bot API.
Requiere TELEGRAM_BOT_TOKEN en settings.
"""
import logging
import httpx
from ..config import settings

logger = logging.getLogger(__name__)

_BASE = "https://api.telegram.org/bot{token}/{method}"


def _url(method: str) -> str:
    return _BASE.format(token=settings.TELEGRAM_BOT_TOKEN, method=method)


async def send_message(chat_id: str, text: str, parse_mode: str = "HTML") -> bool:
    """Envía un mensaje de texto. Retorna True si tuvo éxito."""
    if not settings.TELEGRAM_BOT_TOKEN or not chat_id:
        return False
    try:
        async with httpx.AsyncClient(timeout=6.0) as client:
            resp = await client.post(_url("sendMessage"), json={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": parse_mode,
                # Sin vista previa de los links de Maps (mostraba un mapa de otro país)
                "disable_web_page_preview": True,
            })
            if resp.status_code != 200:
                logger.warning(f"[Telegram] sendMessage error {resp.status_code}: {resp.text[:200]}")
                return False
            return True
    except Exception as e:
        logger.warning(f"[Telegram] sendMessage exception: {e}")
        return False


async def send_with_buttons(chat_id: str, text: str, buttons: list[list[dict]]) -> dict | None:
    """
    Envía mensaje con inline keyboard.
    buttons = [[{"text": "...", "callback_data": "..."}], ...]
    Retorna el dict del mensaje enviado (incluye message_id) o None si falla.
    """
    if not settings.TELEGRAM_BOT_TOKEN or not chat_id:
        return None
    try:
        async with httpx.AsyncClient(timeout=6.0) as client:
            resp = await client.post(_url("sendMessage"), json={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
                "reply_markup": {"inline_keyboard": buttons},
            })
            if resp.status_code != 200:
                logger.warning(f"[Telegram] sendMessage(buttons) error {resp.status_code}: {resp.text[:200]}")
                return None
            return resp.json().get("result")
    except Exception as e:
        logger.warning(f"[Telegram] sendMessage(buttons) exception: {e}")
        return None


async def edit_message_text(chat_id: str, message_id: int, text: str) -> bool:
    """Edita el texto de un mensaje ya enviado (para actualizar estado del viaje)."""
    if not settings.TELEGRAM_BOT_TOKEN or not chat_id:
        return False
    try:
        async with httpx.AsyncClient(timeout=6.0) as client:
            resp = await client.post(_url("editMessageText"), json={
                "chat_id": chat_id,
                "message_id": message_id,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            })
            return resp.status_code == 200
    except Exception as e:
        logger.warning(f"[Telegram] editMessageText exception: {e}")
        return False


async def answer_callback(callback_query_id: str, text: str = "", alert: bool = False) -> bool:
    """Responde a un callback_query (quita el spinner del botón)."""
    if not settings.TELEGRAM_BOT_TOKEN:
        return False
    try:
        async with httpx.AsyncClient(timeout=4.0) as client:
            resp = await client.post(_url("answerCallbackQuery"), json={
                "callback_query_id": callback_query_id,
                "text": text,
                "show_alert": alert,
            })
            return resp.status_code == 200
    except Exception as e:
        logger.warning(f"[Telegram] answerCallback exception: {e}")
        return False


async def set_webhook(webhook_url: str, secret_token: str = "") -> bool:
    """Registra el webhook del bot con Telegram."""
    if not settings.TELEGRAM_BOT_TOKEN:
        return False
    # edited_message explícito: la ubicación en vivo de los choferes llega como
    # ediciones del mensaje original (si no se pide, Telegram reusa el último ajuste)
    payload: dict = {"url": webhook_url, "allowed_updates": ["message", "edited_message", "callback_query"]}
    if secret_token:
        payload["secret_token"] = secret_token
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(_url("setWebhook"), json=payload)
            ok = resp.status_code == 200 and resp.json().get("ok")
            if ok:
                logger.info(f"[Telegram] Webhook registrado: {webhook_url}")
            else:
                logger.warning(f"[Telegram] setWebhook failed: {resp.text[:200]}")
            return ok
    except Exception as e:
        logger.warning(f"[Telegram] setWebhook exception: {e}")
        return False


async def send_to_operator(text: str) -> bool:
    """Envía al chat_id del operador configurado en TELEGRAM_ALERT_CHAT_ID."""
    return await send_message(settings.TELEGRAM_ALERT_CHAT_ID, text)


async def delete_message(chat_id: str, message_id: int) -> bool:
    """Borra un mensaje del bot (Telegram solo deja los de las últimas 48 h)."""
    if not settings.TELEGRAM_BOT_TOKEN or not chat_id:
        return False
    try:
        async with httpx.AsyncClient(timeout=6.0) as client:
            resp = await client.post(_url("deleteMessage"), json={"chat_id": chat_id, "message_id": message_id})
            return resp.status_code == 200 and resp.json().get("ok", False)
    except Exception as e:
        logger.warning(f"[Telegram] deleteMessage exception: {e}")
        return False


async def remove_buttons(chat_id: str, message_id: int) -> bool:
    """Quita los botones de un mensaje (cuando ya no se puede borrar)."""
    if not settings.TELEGRAM_BOT_TOKEN or not chat_id:
        return False
    try:
        async with httpx.AsyncClient(timeout=6.0) as client:
            resp = await client.post(_url("editMessageReplyMarkup"), json={
                "chat_id": chat_id, "message_id": message_id, "reply_markup": {"inline_keyboard": []},
            })
            return resp.status_code == 200
    except Exception as e:
        logger.warning(f"[Telegram] editMessageReplyMarkup exception: {e}")
        return False
