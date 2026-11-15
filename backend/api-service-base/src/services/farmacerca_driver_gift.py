"""Regalo de FarmaCerca para los choferes de TaxiCerca (decisión del dueño, 2026-11-15; antes $50 + $50).

$30 al darse de alta (cuando liga su Telegram con el bot) y $5 por cada uno de sus primeros 10 viajes terminados
por TaxiCerca, dentro de los 14 días desde su primer viaje y contando una sola vez a cada pasajero (frena los viajes
de mentira entre conocidos). Máximo $80 por chofer.

Los abona FarmaCerca por servidor (`POST /api/v1/allies/partner-credit`): el alta con el aliado
FARMACERCA_DRIVER_ALLY ($30) y los viajes con FARMACERCA_DRIVER_TRIP_ALLY ($5), mismo secreto, vigencia de 90 días y
uso completo, sin la regla de "hasta la mitad". FarmaCerca no repite un abono con la misma referencia (AL… alta,
V01…V10 viajes), así que volver a ligar el Telegram no paga dos veces; el aviso por Telegram solo sale cuando sí se
abonó. FARMACERCA_DRIVER_SECRET vacío = apagado.
"""
import logging
import re
from datetime import timedelta
from urllib.parse import quote

import httpx
from sqlalchemy.orm import Session

from ..config import settings
from ..models import Trip, TripStatus
from .telegram import send_message

logger = logging.getLogger(__name__)


TRIP_GIFTS = 10      # viajes con regalo por chofer
TRIP_DAYS = 14       # desde su primer viaje terminado


def _key(phone: str | None) -> str:
    return re.sub(r"\D", "", phone or "")[-10:]


def trip_gift_number(db: Session, driver_phone: str, trip: Trip) -> int | None:
    """Número de viaje con regalo (1..10) que le toca a este viaje recién terminado, o None si no le toca:
    pasaron los 14 días, ya llevaba 10, o ese pasajero ya le había contado antes."""
    customer = _key(trip.customer_phone)
    if len(customer) < 10:
        return None
    rows = (db.query(Trip.id, Trip.customer_phone, Trip.completed_at)
            .filter(Trip.driver_phone == driver_phone, Trip.status == TripStatus.COMPLETED)
            .order_by(Trip.completed_at, Trip.id).all())
    start = rows[0].completed_at if rows else None
    seen: list[str] = []
    for r in rows:
        if start and r.completed_at and r.completed_at - start > timedelta(days=TRIP_DAYS):
            return None
        k = _key(r.customer_phone)
        if r.id == trip.id:
            return len(seen) + 1 if k not in seen and len(seen) < TRIP_GIFTS else None
        if k not in seen:
            seen.append(k)
    return None


async def _credit(ally: str, phone: str, ref: str) -> dict | None:
    if not settings.FARMACERCA_DRIVER_SECRET:
        return None
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(f"{settings.FARMACERCA_API_URL.rstrip('/')}/api/v1/allies/partner-credit",
                                  json={"ally_code": ally, "phone": phone, "ref": ref},
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


async def give(kind: str, phone: str, name: str | None, chat_id: str | None, n: int = 0) -> bool:
    """kind = "alta" | "viaje" (n = número de viaje con regalo, 1..10). Abona y, si fue nuevo, le avisa por
    Telegram. Nunca lanza excepción."""
    key = _key(phone)
    if len(key) < 10 or (kind != "alta" and not 1 <= n <= TRIP_GIFTS):
        return False
    if kind == "alta":
        res = await _credit(settings.FARMACERCA_DRIVER_ALLY, phone, "AL" + key)
    else:
        res = await _credit(settings.FARMACERCA_DRIVER_TRIP_ALLY, phone, f"V{n:02d}{key}")
    if not res or not res.get("credited"):
        return False
    amount = f"${float(res['credited']):,.0f}"
    first = (name or "").split()[0] if name else ""
    if kind == "alta":
        head = (f"🎁 <b>¡Bienvenido a TaxiCerca{', ' + first if first else ''}!</b>\n"
                f"Te regalamos <b>{amount}</b> en tu Monedero FarmaCerca, <i>Tu farmacia por WhatsApp</i>.\n"
                f"Y por cada uno de tus primeros <b>{TRIP_GIFTS} viajes</b> por TaxiCerca te llegan "
                f"<b>${settings.FARMACERCA_DRIVER_TRIP_AMOUNT}</b> más (en tus primeras 2 semanas; "
                f"cada pasajero cuenta una vez).")
    else:
        head = (f"🎁 <b>Viaje {n} de {TRIP_GIFTS} con TaxiCerca</b>\n"
                f"Te llegaron <b>{amount}</b> a tu Monedero FarmaCerca. "
                f"Ya tienes <b>${float(res.get('balance') or 0):,.0f}</b>.")
    text = (f"{head}\n\n💊 Úsalo completo en tus medicinas o las de tu familia, con envío gratis a domicilio."
            f"\n⏳ Vence el {res.get('expires_label') or 'plazo indicado en tu Monedero'}."
            f"\n👉 Pídelas aquí: {_wallet_link()}")
    logger.info(f"[RegaloChofer] {kind}{n or ''} ••••{key[-4:]}: +{res['credited']}")
    if chat_id:
        try:
            await send_message(chat_id, text)
        except Exception as e:
            logger.warning(f"[RegaloChofer] no se pudo avisar por Telegram: {e}")
    return True
