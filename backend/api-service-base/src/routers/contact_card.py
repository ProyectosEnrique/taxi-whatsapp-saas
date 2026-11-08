"""Tarjeta de contacto "TaxiCerca" en el primer mensaje de cada cliente.

El gateway de WhatsApp no tiene dónde recordar a quién ya se la mandó (todo lo
suyo vive en memoria y se pierde al reiniciar), así que pregunta aquí:

  POST /api/v1/contact-card/claim  {"phone": "+52…"}  → {"send": true|false}

true solo la primera vez por teléfono (Redis SET NX, ride_notifs.claim_once).
"""
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from ..config import settings
from ..services import ride_notifs

router = APIRouter(prefix="/api/v1/contact-card", tags=["contact-card"])

_ONE_YEAR = 365 * 24 * 3600


class _Claim(BaseModel):
    phone: str = Field(min_length=8, max_length=30)


@router.post("/claim")
async def claim(body: _Claim, x_taxi_internal_key: str = Header("")):
    if not settings.WHATSAPP_SECRET or x_taxi_internal_key != settings.WHATSAPP_SECRET:
        raise HTTPException(403, "No autorizado")
    phone = "+" + "".join(c for c in body.phone if c.isdigit())
    return {"send": await ride_notifs.claim_once("vcard", phone, ttl=_ONE_YEAR)}
