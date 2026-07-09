"""
Sesión de conversación por teléfono, persistida en Redis (fallback:
sesión vacía en memoria si Redis no está disponible).
"""
import json
import logging
import os

logger = logging.getLogger(__name__)

SESSION_TTL           = 1800   # 30 min sin actividad → conversación vence
SESSION_TTL_WITH_RIDE  = 86400  # 24 h una vez que hay viaje confirmado
MAX_HISTORY            = 20     # mensajes a retener por sesión

try:
    import redis as _redis_lib
    _redis_client = _redis_lib.from_url(
        os.getenv("REDIS_URL", ""), decode_responses=True
    ) if os.getenv("REDIS_URL") else None
except Exception:
    _redis_client = None


def _session_key(phone: str) -> str:
    return f"taxi:agent:{phone}"


def load(phone: str) -> dict:
    if not _redis_client:
        return {"history": [], "context": {}}
    try:
        raw = _redis_client.get(_session_key(phone))
        if raw:
            return json.loads(raw)
    except Exception as e:
        logger.warning(f"[TaxiAgent] session load: {e}")
    return {"history": [], "context": {}}


def save(phone: str, session: dict):
    if not _redis_client:
        return
    try:
        if len(session.get("history", [])) > MAX_HISTORY:
            session["history"] = session["history"][-MAX_HISTORY:]
        _redis_client.setex(_session_key(phone), SESSION_TTL, json.dumps(session))
    except Exception as e:
        logger.warning(f"[TaxiAgent] session save: {e}")


def extend_ttl_for_ride(phone: str):
    """Al confirmarse un viaje, la sesión vive 24h en vez de 30min."""
    if not _redis_client:
        return
    try:
        _redis_client.expire(_session_key(phone), SESSION_TTL_WITH_RIDE)
    except Exception:
        pass
