"""
Geocodificación vía Nominatim (OpenStreetMap) — sin API key requerida.

GET  /api/v1/locations/search?q=...       → buscar dirección
POST /api/v1/locations/reverse-geocode    → coords → dirección
POST /api/v1/locations/geocode            → texto → coords
GET  /api/v1/locations/popular            → destinos populares (stub)
"""
import httpx
from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/api/v1/locations", tags=["Locations"])

NOMINATIM_URL = "https://nominatim.openstreetmap.org"
HEADERS = {"User-Agent": "TaxiApp/1.0"}


def _format_result(item: dict, index: int) -> dict:
    name_parts = item.get("display_name", "").split(",")
    name = name_parts[0].strip()
    address = ", ".join(p.strip() for p in name_parts[1:4]) if len(name_parts) > 1 else item.get("display_name", "")
    return {
        "id": str(item.get("place_id", index)),
        "name": name,
        "address": item.get("display_name", ""),
        "lat": float(item.get("lat", 0)),
        "lng": float(item.get("lon", 0)),   # lng para consistencia con el resto de la API
    }


@router.get("/search")
async def search_address(q: str = Query(..., min_length=3)):
    """Busca direcciones usando Nominatim/OpenStreetMap."""
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(
                f"{NOMINATIM_URL}/search",
                params={"q": q, "format": "json", "limit": 6, "addressdetails": 0},
                headers=HEADERS,
            )
            resp.raise_for_status()
            items = resp.json()
    except Exception as e:
        raise HTTPException(503, f"Error al contactar servicio de geocodificación: {e}")

    results = [_format_result(item, i) for i, item in enumerate(items)]
    return {"results": results}


@router.post("/reverse-geocode")
async def reverse_geocode(payload: dict):
    lat = payload.get("lat")
    lon = payload.get("lon")
    if lat is None or lon is None:
        raise HTTPException(400, "lat y lon son requeridos")
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(
                f"{NOMINATIM_URL}/reverse",
                params={"lat": lat, "lon": lon, "format": "json"},
                headers=HEADERS,
            )
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        raise HTTPException(503, f"Error al geocodificar: {e}")

    return {"address": data.get("display_name", f"{lat}, {lon}")}


@router.post("/geocode")
async def geocode(payload: dict):
    address = (payload.get("address") or "").strip()
    if not address:
        raise HTTPException(400, "address es requerido")
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(
                f"{NOMINATIM_URL}/search",
                params={"q": address, "format": "json", "limit": 1},
                headers=HEADERS,
            )
            resp.raise_for_status()
            items = resp.json()
    except Exception as e:
        raise HTTPException(503, f"Error al geocodificar: {e}")

    if not items:
        raise HTTPException(404, "Dirección no encontrada")
    item = items[0]
    return {"location": {"lat": float(item["lat"]), "lon": float(item["lon"]), "address": item["display_name"]}}


@router.get("/popular")
async def popular_destinations():
    """Destinos frecuentes — se puede poblar desde DB en el futuro."""
    return {"destinations": []}
