"""Regalo de FarmaCerca para el pasajero en su PRIMER viaje terminado.

El link (FARMACERCA_GIFT_URL = /r/taxi, sin número de taxi desde 2026-11-13) lo maneja FarmaCerca: abre su
WhatsApp y le abona $5 de bienvenida UNA sola vez por número (el mismo regalo que da la tarjetita QR; si ya lo
recibió, FarmaCerca se lo dice). Ya no hay que dar de alta cada taxi en FarmaCerca: los choferes reciben su
propio regalo de alta (services/farmacerca_driver_gift.py).

Se menciona una sola vez: en el aviso de "Llegaste" y como banner en la página
de seguimiento. FARMACERCA_GIFT_URL vacío = apagado.
"""
from sqlalchemy.orm import Session, object_session

from ..config import settings
from ..models import Driver, Trip, TripStatus


def gift_for(trip: Trip, driver: Driver | None, db: Session | None = None) -> dict | None:
    """{"amount": 5, "url": ".../r/taxi/23"} si a este viaje le toca regalo."""
    base = (settings.FARMACERCA_GIFT_URL or "").rstrip("/")
    if not base or not trip.customer_phone or trip.status == TripStatus.CANCELLED:
        return None
    db = db or object_session(trip)
    if db is None:
        return None
    earlier = (db.query(Trip.id)
                 .filter(Trip.customer_phone == trip.customer_phone,
                         Trip.status == TripStatus.COMPLETED,
                         Trip.id != trip.id)
                 .first())
    if earlier:
        return None
    return {"amount": settings.FARMACERCA_GIFT_AMOUNT, "url": base}


def gift_line(trip: Trip, driver: Driver | None) -> str:
    """Línea extra del aviso de "Llegaste a tu destino" (vacía si no aplica)."""
    gift = gift_for(trip, driver)
    if not gift:
        return ""
    return (f"\n\n🎁 Por viajar con TaxiCerca te regalamos *${gift['amount']}* en tu "
            f"Monedero FarmaCerca, _Tu farmacia por WhatsApp_.\n"
            f"Recógelo aquí 👉 {gift['url']}")
