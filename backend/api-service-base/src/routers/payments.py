"""
Pagos con MercadoPago — preferencias de checkout, webhook y limpieza de viajes expirados.
Portado desde mandaya/payments.py y adaptado para viajes de taxi.
"""
import asyncio
import logging
from datetime import datetime, timezone, timedelta

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ..database import get_db, SessionLocal
from ..models import Driver, Trip, TripStatus
from ..config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/payments", tags=["payments"])

# MP_ACCESS_TOKEN: token de la propia aplicación de la plataforma — hoy solo se
# usa para consultar el webhook (ver mercadopago_webhook), NO para crear
# preferencias de viaje. Cada viaje con tarjeta cobra con el token del
# conductor asignado (MercadoPago Connect — ver create_mp_preference).
MP_ACCESS_TOKEN = settings.MERCADOPAGO_ACCESS_TOKEN
WA_GATEWAY_URL  = settings.WHATSAPP_GATEWAY_URL
PUBLIC_URL      = settings.PUBLIC_URL
MP_API          = "https://api.mercadopago.com"
BUSINESS_NAME   = settings.BUSINESS_NAME


# ── Core helper (importable desde otros módulos) ──────────────────────────────

async def create_preference(
    token: str,
    trip_id: str,
    amount: float,
    title: str,
    business_name: str,
) -> dict | None:
    """
    Crea una preferencia de checkout en MercadoPago.
    Retorna {"preference_id": str, "init_point": str} o None si falla.
    """
    expiry = (datetime.now(timezone.utc) + timedelta(hours=2)).strftime(
        "%Y-%m-%dT%H:%M:%S.000+00:00"
    )
    preference = {
        "items": [{
            "title":       title[:256],
            "quantity":    1,
            "unit_price":  amount,
            "currency_id": "MXN",
        }],
        "back_urls": {
            "success": f"{PUBLIC_URL}/cliente/?trip={trip_id}",
            "failure": f"{PUBLIC_URL}/cliente/",
            "pending": f"{PUBLIC_URL}/cliente/?trip={trip_id}",
        },
        "auto_return":          "approved",
        "notification_url":     f"{PUBLIC_URL}/api/v1/payments/webhook/mercadopago",
        "external_reference":   trip_id,
        "statement_descriptor": business_name[:22],
        "expires":              True,
        "expiration_date_to":   expiry,
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as c:
            r = await c.post(
                f"{MP_API}/checkout/preferences",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json=preference,
            )
        if r.status_code not in (200, 201):
            logger.error(f"[MP] Error creando preferencia {trip_id}: {r.status_code} {r.text[:300]}")
            return None
        pref = r.json()
        logger.info(f"[MP] Preferencia {pref['id']} creada para {trip_id}")
        return {"preference_id": pref["id"], "init_point": pref["init_point"]}
    except Exception as exc:
        logger.error(f"[MP] Excepción creando preferencia {trip_id}: {exc}")
        return None


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/mp-preference")
async def create_mp_preference(payload: dict, db: Session = Depends(get_db)):
    """
    Crea una preferencia MP para un viaje con pago con tarjeta — el cobro cae
    directo a la cuenta de MercadoPago del conductor asignado (MercadoPago
    Connect), no a una cuenta de la plataforma. Por eso solo se puede llamar
    DESPUÉS de que un conductor aceptó el viaje (ver accept_ride en
    driver_rides.py, que ya bloquea aceptar viajes con tarjeta si el
    conductor no tiene MercadoPago conectado).
    Body: {"trip_id": "TRIP-XXXXXXXX"}
    """
    trip_id = payload.get("trip_id")
    if not trip_id:
        raise HTTPException(400, "trip_id requerido")

    trip = db.query(Trip).filter(Trip.trip_id == trip_id).first()
    if not trip:
        raise HTTPException(404, "Viaje no encontrado")

    if not trip.driver_phone:
        raise HTTPException(409, "Aún no hay conductor asignado a este viaje")

    driver = db.query(Driver).filter(Driver.phone == trip.driver_phone).first()
    if not driver or not driver.mp_access_token:
        raise HTTPException(409, "El conductor de este viaje no tiene MercadoPago conectado")

    title = (
        f"Viaje #{trip_id}"
        + (f" — {trip.destination_address[:40]}" if trip.destination_address else "")
    )
    pref = await create_preference(
        token=driver.mp_access_token,
        trip_id=trip_id,
        amount=float(trip.fare),
        title=title,
        business_name=BUSINESS_NAME,
    )
    if not pref:
        raise HTTPException(502, "Error al crear preferencia en MercadoPago")

    trip.mp_preference_id = pref["preference_id"]
    trip.payment_status   = "pending_payment"
    db.commit()
    return {"preference_id": pref["preference_id"], "init_point": pref["init_point"]}


@router.post("/webhook/mercadopago")
async def mercadopago_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Webhook público — recibe notificaciones de MercadoPago.
    MercadoPago lo llama con ?topic=payment&id={payment_id} o vía JSON.
    """
    params = dict(request.query_params)
    body   = {}
    try:
        body = await request.json()
    except Exception:
        pass

    topic       = params.get("topic") or params.get("type") or body.get("type", "")
    resource_id = (
        params.get("id")
        or params.get("data.id")
        or (body.get("data") or {}).get("id")
    )

    if topic != "payment" or not resource_id:
        return {"status": "ignored"}

    if not MP_ACCESS_TOKEN:
        logger.warning("[MP Webhook] No hay token configurado")
        return {"status": "no_token"}

    payment = None
    async with httpx.AsyncClient(timeout=10.0) as c:
        r = await c.get(
            f"{MP_API}/v1/payments/{resource_id}",
            headers={"Authorization": f"Bearer {MP_ACCESS_TOKEN}"},
        )
        if r.status_code == 200:
            payment = r.json()

    if not payment:
        logger.warning(f"[MP Webhook] No se pudo consultar pago {resource_id}")
        return {"status": "error"}

    trip_id   = payment.get("external_reference")
    mp_status = payment.get("status")
    logger.info(f"[MP Webhook] pago {resource_id} → ref {trip_id} → status {mp_status}")

    if not trip_id:
        return {"status": "no_reference"}

    trip = db.query(Trip).filter(Trip.trip_id == trip_id).first()
    if not trip:
        logger.warning(f"[MP Webhook] Viaje {trip_id} no encontrado")
        return {"status": "trip_not_found"}

    phone = trip.customer_phone or ""

    if mp_status == "approved" and trip.payment_status != "paid":
        trip.payment_status = "paid"
        trip.mp_payment_id  = str(resource_id)
        if trip.status == TripStatus.REQUESTED:
            trip.status = TripStatus.CONFIRMED
        db.commit()
        logger.info(f"[MP] ✅ Pago confirmado — viaje {trip_id}")

        if phone:
            await _notify(phone, (
                f"✅ *¡Pago confirmado!*\n"
                f"Viaje *#{trip_id}* — ${float(trip.fare):.0f} MXN\n\n"
                f"Tu conductor está en camino 🚗\n"
                f"Rastrea tu viaje: {PUBLIC_URL}/cliente/?trip={trip_id}"
            ))

    elif mp_status in ("rejected", "cancelled") and trip.payment_status not in ("paid", "failed"):
        trip.payment_status      = "failed"
        trip.status              = TripStatus.CANCELLED
        trip.cancellation_reason = "Pago rechazado o cancelado por MercadoPago"
        trip.cancelled_at        = datetime.now(timezone.utc)
        trip.mp_payment_id       = str(resource_id)
        db.commit()
        logger.info(f"[MP] ❌ Pago rechazado — viaje {trip_id}")

        if phone:
            await _notify(phone, (
                f"❌ El pago de tu viaje *#{trip_id}* no fue procesado.\n\n"
                "Puedes intentar de nuevo o solicitar un viaje en efectivo 💵"
            ))

    return {"status": "ok"}


@router.get("/status/{trip_id}")
async def get_payment_status(trip_id: str, db: Session = Depends(get_db)):
    """Consulta el estado de pago de un viaje (para polling desde frontend)."""
    trip = db.query(Trip).filter(Trip.trip_id == trip_id).first()
    if not trip:
        raise HTTPException(404, "Viaje no encontrado")
    return {
        "trip_id":        trip.trip_id,
        "payment_status": trip.payment_status,
        "trip_status":    trip.status,
        "fare":           float(trip.fare),
        "init_point":     None,
    }


# ── Helpers internos ──────────────────────────────────────────────────────────

async def _notify(phone: str, message: str) -> None:
    try:
        async with httpx.AsyncClient(timeout=8.0) as c:
            await c.post(
                f"{WA_GATEWAY_URL}/api/v1/send-message",
                json={"phone": phone, "message": message},
            )
    except Exception as exc:
        logger.warning(f"[MP Notify] No se pudo notificar a {phone}: {exc}")


async def cleanup_expired_pending_payments() -> None:
    """
    Background task: cada 30 min cancela viajes con payment_status='pending_payment'
    con más de 2 horas de antigüedad (el link de MP ya expiró).
    """
    await asyncio.sleep(60)
    while True:
        db = None
        try:
            db = SessionLocal()
            cutoff = datetime.now(timezone.utc) - timedelta(hours=2)
            expired = (
                db.query(Trip)
                .filter(
                    Trip.payment_status == "pending_payment",
                    Trip.created_at <= cutoff,
                    Trip.status != TripStatus.CANCELLED,
                )
                .all()
            )
            for trip in expired:
                trip.payment_status      = "failed"
                trip.status              = TripStatus.CANCELLED
                trip.cancellation_reason = "Pago no completado en el tiempo límite (2 h)"
                trip.cancelled_at        = datetime.now(timezone.utc)
                logger.info(f"[MP Cleanup] Viaje {trip.trip_id} cancelado por pago no completado")
                if trip.customer_phone:
                    await _notify(
                        trip.customer_phone,
                        f"⏰ Tu viaje *#{trip.trip_id}* fue cancelado porque el pago "
                        f"no se completó en 2 horas.\n\n"
                        "Escríbenos para solicitar un nuevo viaje 🚕",
                    )
            if expired:
                db.commit()
                logger.info(f"[MP Cleanup] {len(expired)} viaje(s) cancelado(s)")
        except Exception as exc:
            logger.error(f"[MP Cleanup] Error: {exc}")
        finally:
            if db:
                db.close()
        await asyncio.sleep(1800)
