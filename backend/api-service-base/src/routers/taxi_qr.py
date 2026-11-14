"""QR de la tarjetita dentro del taxi y de la calcomanía de afuera (2026-11-13).

Hoy los pasajeros paran el taxi en la calle: la tarjetita del respaldo les enseña
que la próxima vez lo pueden pedir por WhatsApp. Un solo QR, de TaxiCerca:

  GET /tc          → tarjetita igual para todos los taxis (2026-11-13): "Hola TaxiCerca 🚕 voy en un taxi"
  GET /t/{número}  → WhatsApp de TaxiCerca con "Hola TaxiCerca 🚕 voy en el taxi 23" (QR viejos con número)
  GET /t           → calcomanía de afuera: "Hola TaxiCerca 🚕 quiero pedir un taxi"
                     (ese mensaje lo atiende el bot como cualquier pedido)

El gateway reconoce "voy en el taxi 23" (main_taxi._TAXI_SCAN_RE), no lo pasa a
la IA y pregunta aquí qué contestar:

  POST /api/v1/whatsapp/taxi-scan  {"phone", "taxi"}  → {"reply": "…"}

La respuesta pide guardar el chat y trae el link del regalo de FarmaCerca (FARMACERCA_GIFT_URL, sin número de
taxi): $5 de bienvenida una sola vez por número, lo controla FarmaCerca. Ya no depende de dar de alta cada taxi;
los choferes tienen su propio regalo de alta (services/farmacerca_driver_gift.py). Regalo apagado
(FARMACERCA_GIFT_URL vacío) = solo la parte de TaxiCerca.
Nada de esto pide un viaje ni avisa a choferes.
"""
import logging
import re
from urllib.parse import quote

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db

logger = logging.getLogger(__name__)
router = APIRouter(tags=["taxi-qr"])

_UNIT_RE = re.compile(r"^[A-Za-z0-9]{1,10}$")


def _wa(text: str) -> str:
    digits = "".join(c for c in settings.TAXICERCA_WA_NUMBER if c.isdigit())
    return f"https://wa.me/{digits}?text={quote(text)}"


@router.get("/t")
def street_qr():
    logger.info("[QR] calcomanía de afuera escaneada")
    return RedirectResponse(_wa("Hola TaxiCerca 🚕 quiero pedir un taxi"), status_code=302)


@router.get("/tc")
def card_qr():
    logger.info("[QR] tarjetita del taxi escaneada")
    return RedirectResponse(_wa("Hola TaxiCerca 🚕 voy en un taxi"), status_code=302)


@router.get("/t/{unit}")
def taxi_qr(unit: str):
    if not _UNIT_RE.match(unit):
        return RedirectResponse(_wa("Hola TaxiCerca 🚕 quiero pedir un taxi"), status_code=302)
    logger.info(f"[QR] tarjeta del taxi {unit.upper()} escaneada")
    return RedirectResponse(_wa(f"Hola TaxiCerca 🚕 voy en el taxi {unit.upper()}"), status_code=302)


class _Scan(BaseModel):
    phone: str = Field(min_length=8, max_length=30)
    taxi: str = Field("", max_length=10)   # vacío = tarjetita igual para todos


def scan_reply(db: Session, taxi: str) -> str:
    unit = (taxi or "").strip().upper()
    where = f"el taxi *{unit}*" if _UNIT_RE.match(unit) else "un taxi"
    text = (f"🚕 ¡Hola! Vas en {where} de *TaxiCerca*, tu taxi por WhatsApp.\n\n"
            "📲 *Guarda este chat:* la próxima vez pide tu taxi aquí. Te damos el precio antes "
            "y te avisamos cuando tu taxi esté llegando. Solo escríbenos a dónde vas o mándanos "
            "tu ubicación 📍.")
    base = (settings.FARMACERCA_GIFT_URL or "").rstrip("/")
    if base:
        text += (f"\n\n🎁 *De regalo:* ${settings.FARMACERCA_GIFT_AMOUNT} en tu Monedero FarmaCerca, "
                 "_Tu farmacia por WhatsApp_, con envío gratis a domicilio.\n"
                 f"Recógelo aquí 👉 {base}")
    return text


@router.post("/api/v1/whatsapp/taxi-scan")
def taxi_scan(body: _Scan, x_taxi_internal_key: str = Header(""), db: Session = Depends(get_db)):
    if not settings.WHATSAPP_SECRET or x_taxi_internal_key != settings.WHATSAPP_SECRET:
        raise HTTPException(403, "No autorizado")
    return {"reply": scan_reply(db, body.taxi)}
