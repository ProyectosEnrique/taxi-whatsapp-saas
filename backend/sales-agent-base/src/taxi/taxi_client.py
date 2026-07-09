"""
Cliente HTTP hacia taxi-api (geocoding, tarifas, viajes, alta de cliente).
"""
import logging
from typing import Optional

import httpx

from src.config import settings

logger = logging.getLogger(__name__)

API_BASE          = settings.MENU_SERVICE_URL
WHATSAPP_SECRET   = settings.WHATSAPP_SECRET
CUSTOMER_APP_URL  = settings.CUSTOMER_APP_URL
# Derive base domain for tracking URLs (strip /cliente suffix if present)
TRACKING_BASE     = CUSTOMER_APP_URL.replace('/cliente', '').rstrip('/')

_HEADERS = {"X-Taxi-Internal-Key": WHATSAPP_SECRET} if WHATSAPP_SECRET else {}


def geocode(query: str) -> list:
    try:
        with httpx.Client(timeout=8.0) as c:
            resp = c.get(
                f"{API_BASE}/api/v1/whatsapp/geocode",
                params={"q": query},
                headers=_HEADERS,
            )
            return resp.json().get("results", [])
    except Exception as e:
        logger.warning(f"[TaxiAgent] geocode error: {e}")
        return []


def reverse_geocode(lat: float, lng: float) -> Optional[dict]:
    try:
        with httpx.Client(timeout=6.0) as c:
            resp = c.get(
                f"{API_BASE}/api/v1/whatsapp/reverse-geocode",
                params={"lat": lat, "lon": lng},
                headers=_HEADERS,
            )
            return resp.json()
    except Exception as e:
        logger.warning(f"[TaxiAgent] reverse_geocode error: {e}")
        return None


def estimate(origin_lat: float, origin_lng: float, dest_lat: float, dest_lng: float) -> dict:
    try:
        with httpx.Client(timeout=5.0) as c:
            resp = c.post(
                f"{API_BASE}/api/v1/whatsapp/rides/estimate",
                json={
                    "origin":      {"lat": origin_lat, "lng": origin_lng},
                    "destination": {"lat": dest_lat,   "lng": dest_lng},
                },
                headers=_HEADERS,
            )
            return resp.json()
    except Exception as e:
        logger.warning(f"[TaxiAgent] estimate error: {e}")
        return {"fare": 80.0, "distance_km": 5.0, "duration_minutes": 15}


def create_ride(
    phone: str,
    origin: dict,
    destination: dict,
    scheduled_at: Optional[str] = None,
) -> Optional[dict]:
    payload: dict = {
        "customer_phone": phone,
        "origin":         origin,
        "destination":    destination,
        "payment_method": "cash",
    }
    if scheduled_at:
        payload["scheduled_at"] = scheduled_at
    try:
        with httpx.Client(timeout=8.0) as c:
            resp = c.post(
                f"{API_BASE}/api/v1/whatsapp/rides/create",
                json=payload,
                headers=_HEADERS,
            )
            if resp.status_code == 200:
                return resp.json()
            logger.error(f"[TaxiAgent] create_ride {resp.status_code}: {resp.text}")
    except Exception as e:
        logger.error(f"[TaxiAgent] create_ride error: {e}")
    return None


def cancel_ride(ride_id: str):
    try:
        with httpx.Client(timeout=4.0) as c:
            c.post(
                f"{API_BASE}/api/v1/whatsapp/rides/{ride_id}/cancel",
                headers=_HEADERS,
            )
    except Exception as e:
        logger.debug(f"[TaxiAgent] cancel_ride: {e}")


def get_ride(ride_id: str) -> Optional[dict]:
    try:
        with httpx.Client(timeout=4.0) as c:
            resp = c.get(
                f"{API_BASE}/api/v1/whatsapp/rides/{ride_id}",
                headers=_HEADERS,
            )
            return resp.json()
    except Exception as e:
        logger.debug(f"[TaxiAgent] get_ride: {e}")
    return None


def init_customer(phone: str):
    try:
        with httpx.Client(timeout=3.0) as c:
            c.post(
                f"{API_BASE}/api/v1/whatsapp/customer/init",
                json={"phone": phone},
                headers=_HEADERS,
            )
    except Exception:
        pass
