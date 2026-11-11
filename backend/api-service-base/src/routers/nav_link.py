"""Enlace corto de navegación para el chofer: taxi.nexoai.lat/r/<código>.

Los botones con enlace de Telegram siempre preguntan "¿Abrir este enlace?".
Un enlace escrito y visible en el mensaje se abre directo, así que el bot
pone este enlace corto además del botón 🚕.

  GET /r/{código}  → 302 a Google Maps ya navegando, según el estado del viaje
                     al momento de tocarlo:
                     aceptado        → ruta completa (pasajero como parada → destino)
                     llegó / en curso → al destino

El código es la parte hex de trip_id (TRIP-1A2B3C4D → 1a2b3c4d); expone lo
mismo que /seguimiento/{trip_id}.
"""
from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..models import Trip, TripStatus

router = APIRouter(tags=["nav-link"])

_PREFIX = "TRIP-"


def maps_url(lat, lng, via: tuple | None = None) -> str:
    """Google Maps ya navegando hacia (lat, lng), con una parada opcional."""
    stop = f"&waypoints={via[0]},{via[1]}" if via else ""
    return (f"https://www.google.com/maps/dir/?api=1&destination={lat},{lng}{stop}"
            f"&travelmode=driving&dir_action=navigate")


def route_url(trip: Trip) -> str | None:
    has_origin = bool(trip.origin_lat and trip.origin_lng)
    has_dest = bool(trip.destination_lat and trip.destination_lng)
    if trip.status == TripStatus.CONFIRMED and has_origin:
        if not has_dest:
            return maps_url(trip.origin_lat, trip.origin_lng)
        return maps_url(trip.destination_lat, trip.destination_lng, via=(trip.origin_lat, trip.origin_lng))
    if trip.status in (TripStatus.DRIVER_ARRIVED, TripStatus.IN_PROGRESS) and has_dest:
        return maps_url(trip.destination_lat, trip.destination_lng)
    return None


def short_url(trip: Trip) -> str:
    code = trip.trip_id[len(_PREFIX):] if trip.trip_id.startswith(_PREFIX) else trip.trip_id
    return f"{settings.PUBLIC_URL}/r/{code.lower()}"


@router.get("/r/{code}")
def open_route(code: str, db: Session = Depends(get_db)):
    trip = db.query(Trip).filter(Trip.trip_id == _PREFIX + code.upper()[:20]).first()
    url = route_url(trip) if trip else None
    if not url:
        return HTMLResponse("<h2 style='font-family:sans-serif'>Este viaje ya terminó o no existe.</h2>",
                            status_code=404)
    return RedirectResponse(url, status_code=302, headers={"Cache-Control": "no-store"})
