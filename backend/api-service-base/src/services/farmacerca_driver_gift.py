"""Regalo de FarmaCerca para los choferes de TaxiCerca (2026-11-13, decisión del dueño).

$50 al darse de alta (cuando liga su Telegram con el bot) y otros $50 al terminar su PRIMER viaje por TaxiCerca.
Los abona FarmaCerca por servidor (`POST /api/v1/allies/partner-credit`, aliado FARMACERCA_DRIVER_ALLY con su
propio monto, vigencia de 90 días y uso completo, sin la regla de "hasta la mitad"). FarmaCerca no repite un abono
con la misma referencia (AL… alta, V1… primer viaje), así que volver a ligar el Telegram no paga dos veces; el
aviso por Telegram solo sale cuando sí se abonó. FARMACERCA_DRIVER_SECRET vacío = apagado.
"""
import logging
import re
from urllib.parse import quote

import httpx
from sqlalchemy.orm import Session

from ..config import settings
from ..models import Trip, TripStatus
from .telegram import send_message

logger = logging.getLogger(__name__)


def is_first_trip(db: Session, driver_phone: str) -> bool:
    """True si el chofer lleva exactamente un viaje terminado (el que se acaba de completar)."""
    return db.query(Trip.id).filter(Trip.driver_phone == driver_phone,
                                    Trip.status == TripStatus.COMPLETED).limit(2).count() == 1


async def _credit(phone: str, ref: str) -> dict | None:
    if not settings.FARMACERCA_DRIVER_SECRET:
        return None
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(f"{settings.FARMACERCA_API_URL.rstrip('/')}/api/v1/allies/partner-credit",
                                  json={"ally_code": settings.FARMACERCA_DRIVER_ALLY, "phone": phone, "ref": ref},
                                  headers={"X-Ally-Secret": settings.FARMACERCA_DRIVER_SECRET})
        if r.status_code != 200:
            logger.warning(f"[RegaloChofer] FarmaCerca {r.status_code} para {ref}: {r.text[:200]}")
            return None
        return r.json()
    except Exception as e:
        logger.warning(f"[RegaloChofer] FarmaCerca no respondió para {ref}: {e}")
        return None


def _wallet_link() -> str:
    digits = re.sub(r"\D", "", settings.FARMACERCA_WA_NUMBER)
    return f"https://wa.me/{digits}?text={quote('Quiero ver mi monedero')}"


async def give(kind: str, phone: str, name: str | None, chat_id: str | None) -> bool:
    """kind = "alta" | "viaje". Abona y, si fue nuevo, le avisa por Telegram. Nunca lanza excepción."""
    key = re.sub(r"\D", "", phone or "")[-10:]
    if len(key) < 10:
        return False
    res = await _credit(phone, ("AL" if kind == "alta" else "V1") + key)
    if not res or not res.get("credited"):
        return False
    amount = f"${float(res['credited']):,.0f}"
    first = (name or "").split()[0] if name else ""
    if kind == "alta":
        head = (f"🎁 <b>¡Bienvenido a TaxiCerca{', ' + first if first else ''}!</b>\n"
                f"Te regalamos <b>{amount}</b> en tu Monedero FarmaCerca, <i>Tu farmacia por WhatsApp</i>.\n"
                f"Y al terminar tu primer viaje por TaxiCerca te llegan otros <b>{amount}</b>.")
    else:
        head = (f"🎁 <b>¡Primer viaje con TaxiCerca!</b>\n"
                f"Te llegaron otros <b>{amount}</b> a tu Monedero FarmaCerca. "
                f"Ya tienes <b>${float(res.get('balance') or 0):,.0f}</b>.")
    text = (f"{head}\n\n💊 Úsalo completo en tus medicinas o las de tu familia, con envío gratis a domicilio."
            f"\n⏳ Vence el {res.get('expires_label') or 'plazo indicado en tu Monedero'}."
            f"\n👉 Pídelas aquí: {_wallet_link()}")
    logger.info(f"[RegaloChofer] {kind} ••••{key[-4:]}: +{res['credited']}")
    if chat_id:
        try:
            await send_message(chat_id, text)
        except Exception as e:
            logger.warning(f"[RegaloChofer] no se pudo avisar por Telegram: {e}")
    return True
