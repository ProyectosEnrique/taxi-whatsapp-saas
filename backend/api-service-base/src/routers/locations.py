"""
Geocodificación y POIs locales para la app del cliente.

GET  /api/v1/locations/search?q=...    → buscar dirección (Google Maps → Nominatim)
POST /api/v1/locations/reverse-geocode → coords → dirección (Google Maps → Nominatim)
POST /api/v1/locations/geocode         → texto → coords
GET  /api/v1/locations/popular         → top destinos del historial de viajes
GET  /api/v1/locations/pois            → POIs locales guardados (buscar por nombre)
POST /api/v1/locations/pois            → agregar POI local
DELETE /api/v1/locations/pois/{id}     → eliminar POI
"""
import math
import logging

import httpx
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..database import get_db
from ..config import settings
from ..models import Trip, TripStatus, LocalPOI

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/locations", tags=["Locations"])

NOMINATIM_URL = "https://nominatim.openstreetmap.org"
NOM_HEADERS   = {"User-Agent": "TaxiApp/1.0"}
GMAPS_URL     = "https://maps.googleapis.com/maps/api/geocode/json"


# ── Helpers ────────────────────────────────────────────────────────────────────

def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    a = (math.sin(math.radians(lat2 - lat1) / 2) ** 2
         + math.cos(phi1) * math.cos(phi2)
         * math.sin(math.radians(lng2 - lng1) / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _in_city(lat: float, lng: float) -> bool:
    if not (settings.CITY_LAT and settings.CITY_LNG):
        return True
    max_km = (settings.CITY_BBOX_DEG or 0.3) * 111 * 1.5
    return _haversine_km(settings.CITY_LAT, settings.CITY_LNG, lat, lng) <= max_km


def _gmaps_fmt(r: dict) -> dict:
    loc  = r["geometry"]["location"]
    name = r["formatted_address"].split(",")[0].strip()
    return {
        "id":      r.get("place_id", ""),
        "name":    name,
        "address": r["formatted_address"],
        "lat":     loc["lat"],
        "lng":     loc["lng"],
        "source":  "google",
    }


def _nom_fmt(item: dict, idx: int) -> dict:
    parts = [p.strip() for p in item.get("display_name", "").split(",") if p.strip()]
    name  = parts[0] if parts else ""
    addr  = ", ".join(parts[:4])
    return {
        "id":      str(item.get("place_id", idx)),
        "name":    name,
        "address": addr,
        "lat":     float(item.get("lat", 0)),
        "lng":     float(item.get("lon", 0)),
        "source":  "osm",
    }


def _poi_fmt(poi: LocalPOI) -> dict:
    return {
        "id":      f"poi-{poi.id}",
        "name":    poi.name,
        "address": poi.address or poi.name,
        "lat":     float(poi.lat),
        "lng":     float(poi.lng),
        "source":  "local",
    }


async def _google_search(q: str, client: httpx.AsyncClient,
                         ref_lat: float | None = None, ref_lng: float | None = None) -> list:
    if not settings.GOOGLE_MAPS_API_KEY:
        return []
    params: dict = {
        "address":    q,
        "key":        settings.GOOGLE_MAPS_API_KEY,
        "language":   "es",
        "region":     "MX",
        "components": "country:MX",
    }
    clat = ref_lat or settings.CITY_LAT
    clng = ref_lng or settings.CITY_LNG
    if clat and clng:
        d = settings.CITY_BBOX_DEG or 0.3
        params["bounds"] = f"{clat - d},{clng - d}|{clat + d},{clng + d}"
    resp = await client.get(GMAPS_URL, params=params)
    resp.raise_for_status()
    data = resp.json()
    if data.get("status") not in ("OK", "ZERO_RESULTS"):
        logger.warning(f"[Locations/GMaps] status={data.get('status')} para '{q}'")
        return []
    return [_gmaps_fmt(r) for r in data.get("results", []) if _in_city(r["geometry"]["location"]["lat"], r["geometry"]["location"]["lng"])]


async def _nom_search(q: str, client: httpx.AsyncClient,
                      ref_lat: float | None = None, ref_lng: float | None = None) -> list:
    params: dict = {"q": q, "format": "json", "limit": 6, "addressdetails": 0, "countrycodes": "mx"}
    if ref_lat is not None and ref_lng is not None:
        d = settings.CITY_BBOX_DEG or 0.3
        params["viewbox"]  = f"{ref_lng - d},{ref_lat - d},{ref_lng + d},{ref_lat + d}"
        params["bounded"]  = 1
    resp = await client.get(f"{NOMINATIM_URL}/search", params=params, headers=NOM_HEADERS)
    resp.raise_for_status()
    items = resp.json()
    return [_nom_fmt(i, idx) for idx, i in enumerate(items) if _in_city(float(i.get("lat", 0)), float(i.get("lon", 0)))]


# ── Búsqueda de POIs locales ───────────────────────────────────────────────────

def _search_local_pois(q: str, db: Session) -> list:
    """Búsqueda case-insensitive de POIs locales por nombre."""
    q_lower = f"%{q.lower()}%"
    pois = db.query(LocalPOI).filter(
        LocalPOI.is_active == True,
        func.lower(LocalPOI.name).like(q_lower),
    ).limit(5).all()
    return [_poi_fmt(p) for p in pois]


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.get("/search")
async def search_address(
    q: str = Query(..., min_length=3),
    lat: float | None = None,
    lon: float | None = None,
    db: Session = Depends(get_db),
):
    """Busca direcciones: POIs locales → Google Maps → Nominatim."""
    ref_lat = lat or (settings.CITY_LAT or None)
    ref_lng = lon or (settings.CITY_LNG or None)

    # 0. POIs locales primero (respuesta inmediata, sin red)
    local = _search_local_pois(q, db)
    if local:
        logger.info(f"[Locations] POI local: '{q}' → {local[0]['name']}")

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            # 1. Google Maps
            if settings.GOOGLE_MAPS_API_KEY:
                gmaps = await _google_search(q, client, ref_lat, ref_lng)
                if gmaps or local:
                    results = local + [r for r in gmaps if r["id"] not in {p["id"] for p in local}]
                    logger.info(f"[Locations] GMaps: '{q}' → {gmaps[0]['name'] if gmaps else 'sin resultados'}")
                    return {"results": results}
                logger.warning(f"[Locations] GMaps sin resultados en radio para '{q}', usando Nominatim")

            # 2. Nominatim fallback
            nom = await _nom_search(q, client, ref_lat, ref_lng)
            results = local + [r for r in nom if r["id"] not in {p["id"] for p in local}]
            if results:
                logger.info(f"[Locations] Nominatim: '{q}' → {nom[0]['name'] if nom else 'solo POIs locales'}")
            return {"results": results}

    except Exception as e:
        logger.error(f"[Locations] search error: {e}")
        # Si falla la red, al menos devolver POIs locales
        return {"results": local}


@router.post("/reverse-geocode")
async def reverse_geocode(payload: dict):
    """Coordenadas → dirección legible. Google Maps primario, Nominatim fallback."""
    lat = payload.get("lat")
    lon = payload.get("lon")
    if lat is None or lon is None:
        raise HTTPException(400, "lat y lon son requeridos")
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            if settings.GOOGLE_MAPS_API_KEY:
                resp = await client.get(GMAPS_URL, params={
                    "latlng":      f"{lat},{lon}",
                    "key":         settings.GOOGLE_MAPS_API_KEY,
                    "language":    "es",
                    "result_type": "street_address|route|neighborhood",
                })
                resp.raise_for_status()
                data = resp.json()
                if data.get("status") == "OK" and data.get("results"):
                    addr = data["results"][0]["formatted_address"]
                    return {"address": addr, "name": addr.split(",")[0].strip()}
            # Nominatim fallback
            resp = await client.get(
                f"{NOMINATIM_URL}/reverse",
                params={"lat": lat, "lon": lon, "format": "json"},
                headers=NOM_HEADERS,
            )
            resp.raise_for_status()
            data = resp.json()
            display = data.get("display_name", f"{lat}, {lon}")
            return {"address": display, "name": display.split(",")[0].strip()}
    except Exception as e:
        raise HTTPException(503, f"Error al geocodificar: {e}")


@router.post("/geocode")
async def geocode(payload: dict):
    """Texto → coordenadas. Google Maps primario, Nominatim fallback."""
    address = (payload.get("address") or "").strip()
    if not address:
        raise HTTPException(400, "address es requerido")
    ref_lat = settings.CITY_LAT or None
    ref_lng = settings.CITY_LNG or None
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            if settings.GOOGLE_MAPS_API_KEY:
                results = await _google_search(address, client, ref_lat, ref_lng)
                if results:
                    r = results[0]
                    return {"location": {"lat": r["lat"], "lon": r["lng"], "address": r["address"]}}
            results = await _nom_search(address, client, ref_lat, ref_lng)
            if not results:
                raise HTTPException(404, "Dirección no encontrada")
            r = results[0]
            return {"location": {"lat": r["lat"], "lon": r["lng"], "address": r["address"]}}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(503, f"Error al geocodificar: {e}")


@router.get("/popular")
async def popular_destinations(limit: int = 10, db: Session = Depends(get_db)):
    """Top destinos por frecuencia en viajes completados."""
    rows = (
        db.query(
            Trip.destination_address,
            Trip.destination_lat,
            Trip.destination_lng,
            func.count(Trip.id).label("trips"),
        )
        .filter(
            Trip.status == TripStatus.COMPLETED,
            Trip.destination_address.isnot(None),
            Trip.destination_lat.isnot(None),
        )
        .group_by(Trip.destination_address, Trip.destination_lat, Trip.destination_lng)
        .order_by(func.count(Trip.id).desc())
        .limit(limit)
        .all()
    )
    return {
        "destinations": [
            {
                "id":      f"popular-{i}",
                "name":    row.destination_address.split(",")[0].strip(),
                "address": row.destination_address,
                "lat":     float(row.destination_lat),
                "lng":     float(row.destination_lng),
                "trips":   row.trips,
                "source":  "history",
            }
            for i, row in enumerate(rows)
        ]
    }


# ── POIs locales CRUD ──────────────────────────────────────────────────────────

class POICreate(BaseModel):
    name:     str
    address:  str | None = None
    lat:      float
    lng:      float
    added_by: str = "admin"


@router.get("/pois")
def list_pois(q: str | None = None, db: Session = Depends(get_db)):
    """Lista POIs locales, con búsqueda opcional por nombre."""
    qs = db.query(LocalPOI).filter(LocalPOI.is_active == True)
    if q:
        qs = qs.filter(func.lower(LocalPOI.name).like(f"%{q.lower()}%"))
    pois = qs.order_by(LocalPOI.name).limit(50).all()
    return {"pois": [_poi_fmt(p) | {"db_id": p.id, "added_by": p.added_by} for p in pois]}


@router.post("/pois", status_code=201)
def create_poi(body: POICreate, db: Session = Depends(get_db)):
    """Agregar un lugar local (conductor o admin)."""
    poi = LocalPOI(
        name=body.name.strip(),
        address=body.address,
        lat=body.lat,
        lng=body.lng,
        added_by=body.added_by,
    )
    db.add(poi)
    db.commit()
    db.refresh(poi)
    logger.info(f"[Locations] POI creado: '{poi.name}' por {poi.added_by}")
    return _poi_fmt(poi) | {"db_id": poi.id}


@router.delete("/pois/{poi_id}", status_code=200)
def delete_poi(poi_id: int, db: Session = Depends(get_db)):
    """Desactivar un POI (soft delete)."""
    poi = db.query(LocalPOI).filter(LocalPOI.id == poi_id).first()
    if not poi:
        raise HTTPException(404, "POI no encontrado")
    poi.is_active = False
    db.commit()
    return {"ok": True, "deleted": poi.name}
