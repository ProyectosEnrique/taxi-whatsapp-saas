"""
Endpoints internos para la integración WhatsApp ↔ taxi-api.
Protegidos con X-Taxi-Internal-Key.
"""
import logging
import math
import re
import uuid

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Customer, Driver, Trip, TripStatus
from ..auth import hash_password
from ..fare_service import get_fare_config, calculate_fare, route_km_min
from ..config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/whatsapp", tags=["whatsapp-internal"])

NOMINATIM_URL = "https://nominatim.openstreetmap.org"
_NOM_HEADERS  = {"User-Agent": "TaxiApp/1.0"}
GMAPS_URL     = "https://maps.googleapis.com/maps/api/geocode/json"
GMAPS_REV_URL = "https://maps.googleapis.com/maps/api/geocode/json"
PLACES_URL    = "https://places.googleapis.com/v1/places:searchText"
PLACES_FIELDS = ("places.displayName,places.formattedAddress,places.location,"
                 "places.types,places.addressComponents")
PLACES_BIAS_RADIUS_M = 20000.0   # preferir lugares a ≤ 20 km del pasajero (máx. de Google: 50 km)

# Common Spanish place-name aliases that Nominatim doesn't index literally
_QUERY_SUBS = [
    (re.compile(r'\bcentral de autobuses\b', re.I), 'terminal autobuses'),
    (re.compile(r'\bcentral camionera\b', re.I), 'terminal autobuses'),
    (re.compile(r'\bcamionera central\b', re.I), 'terminal autobuses'),
    (re.compile(r'\bCAPU\b', re.I), 'terminal autobuses'),
    (re.compile(r'\baeroporto\b', re.I), 'aeropuerto'),
    (re.compile(r'\bclinica\b', re.I), 'hospital'),
    (re.compile(r'\bIMSS\b'), 'Instituto Mexicano del Seguro Social'),
    (re.compile(r'\bISSTE\b'), 'ISSSTE'),
]

# Preposiciones iniciales que el cliente escribe pero confunden a Nominatim
# "En veneto 119 Celaya" → "veneto 119 Celaya"
_LEADING_PREP = re.compile(
    r'^(en|voy a|me lleva a|llévame a|llevame a|hasta|quiero ir a|ir a|al|a la|a)\s+',
    re.I,
)
# "col san cristobal en Salvatierra" → "col san cristobal, Salvatierra"
# Convierte " en <Ciudad>" al final de un segmento en ", <Ciudad>" para que el
# geocodificador pueda activar el shortcut calle+ciudad (requiere ≥ 3 partes).
_MID_EN = re.compile(r'\s+en\s+', re.I)


def _clean_query(q: str) -> str:
    """Limpieza basica del query para Google Maps (no aplica aliases de POIs)."""
    q = _LEADING_PREP.sub('', q).strip()
    q = _MID_EN.sub(', ', q)
    return q.strip()


def _normalize_query(q: str) -> str:
    """Limpieza + aliases de nombres de lugares. Solo para Nominatim."""
    q = _clean_query(q)
    for pattern, replacement in _QUERY_SUBS:
        q = pattern.sub(replacement, q)
    return q.strip()


def _within_radius(result: dict, ref_lat: float | None = None, ref_lng: float | None = None) -> bool:
    """Rechaza resultados fuera de zona: a más de CITY_BBOX_DEG x 111 x 1.5 km (~50 km)
    del centro de operación Y del pasajero (si se conoce). Así sirve para otras bases."""
    d = settings.CITY_BBOX_DEG or 0.3
    max_km = d * 111 * 1.5
    centers = [(c_lat, c_lng) for c_lat, c_lng in ((settings.CITY_LAT, settings.CITY_LNG), (ref_lat, ref_lng))
               if c_lat and c_lng]
    if not centers:
        return True
    return any(_haversine_km(c_lat, c_lng, result['lat'], result['lng']) <= max_km
               for c_lat, c_lng in centers)


def _parse_display_name(display_name: str) -> tuple[str, str]:
    """Returns (name, short_address) from a Nominatim display_name string."""
    parts = [p.strip() for p in display_name.split(",") if p.strip()]
    name = parts[0] if parts else ""
    # If first part is too short (e.g. "Hola"), combine with second
    if len(name) < 4 and len(parts) > 1:
        name = f"{parts[0]}, {parts[1]}"
    short_address = ", ".join(p for p in parts[1:3] if len(p) > 2)
    return name, short_address


def _auth(x_taxi_internal_key: str = Header(...)):
    if settings.WHATSAPP_SECRET and x_taxi_internal_key != settings.WHATSAPP_SECRET:
        raise HTTPException(403, "Clave interna inválida")


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    a = (math.sin(math.radians(lat2 - lat1) / 2) ** 2
         + math.cos(phi1) * math.cos(phi2)
         * math.sin(math.radians(lon2 - lon1) / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.post("/customer/init")
def customer_init(payload: dict, db: Session = Depends(get_db), _=Depends(_auth)):
    phone = (payload.get("phone") or "").strip()
    name = (payload.get("name") or "Cliente").strip()
    driver_code = (payload.get("driver_code") or "").strip()
    if not phone:
        raise HTTPException(400, "phone requerido")
    customer = db.query(Customer).filter(Customer.phone == phone).first()
    is_new = customer is None
    if is_new:
        pwd_seed = phone[-6:] if len(phone) >= 6 else "123456"
        customer = Customer(phone=phone, name=name, password_hash=hash_password(pwd_seed))
        db.add(customer)
        db.commit()
        db.refresh(customer)
    if driver_code:
        driver = db.query(Driver).filter(Driver.driver_code == driver_code, Driver.is_active == True).first()
        if driver:
            customer.preferred_driver_id = driver.id
            db.commit()
    return {"customer_id": customer.id, "phone": customer.phone, "name": customer.name, "is_new": is_new}


@router.get("/driver/{driver_code}")
def get_driver_by_code(driver_code: str, db: Session = Depends(get_db), _=Depends(_auth)):
    driver = db.query(Driver).filter(Driver.driver_code == driver_code, Driver.is_active == True).first()
    if not driver:
        raise HTTPException(404, "Conductor no encontrado")
    return {"driver_code": driver.driver_code, "name": driver.name, "phone": driver.phone}


# ── Búsqueda de lugares (lo que escribe el pasajero → punto en el mapa) ───────
# Orden: Google Places (nombres de lugares: "Hospital General", "Soriana") →
# Google Geocoding (calle y número) → Nominatim. Cada resultado trae colonia,
# ciudad y si es aproximado; los de nivel ciudad se descartan (el taxi
# terminaría en el centro). Todo se busca cerca del pasajero (lat/lon) si se
# conoce, para que "Hidalgo 45" salga en su ciudad y no en la de la base.

# Tipos de Google que solo dicen la ciudad, municipio o estado
_CITY_LEVEL = {"locality", "administrative_area_level_1", "administrative_area_level_2",
               "administrative_area_level_3", "country", "postal_code", "postal_town"}
# Tipos que dicen una zona (colonia, calle sin número): sirven, pero el punto es aproximado
_AREA_LEVEL = {"sublocality", "sublocality_level_1", "sublocality_level_2", "neighborhood",
               "route", "colloquial_area"}
_PRECISE = {"street_address", "premise", "subpremise", "establishment", "point_of_interest",
            "intersection", "plus_code"}
# Lo mismo para Nominatim (campo addresstype de jsonv2)
_NOM_CITY_LEVEL = {"city", "town", "village", "municipality", "county", "state", "country",
                   "postcode", "region"}
_NOM_AREA_LEVEL = {"suburb", "neighbourhood", "quarter", "city_district", "road", "residential",
                   "hamlet", "isolated_dwelling"}


def _precision(types: set, location_type: str | None = None) -> str:
    """'ciudad' (se descarta), 'zona' (aproximado) o 'exacto'."""
    if types & _PRECISE:
        return "zona" if location_type == "APPROXIMATE" else "exacto"
    if types & _CITY_LEVEL and not (types & _AREA_LEVEL):
        return "ciudad"
    if types & _AREA_LEVEL or location_type == "APPROXIMATE":
        return "zona"
    return "exacto"


def _colonia_ciudad(components: list, text_key: str) -> tuple[str, str]:
    """Colonia y ciudad de los address_components de Google (Geocoding: long_name,
    Places: longText)."""
    def pick(*wanted):
        for t in wanted:
            for c in components:
                if t in (c.get("types") or []):
                    return c.get(text_key) or ""
        return ""
    colonia = pick("sublocality_level_1", "neighborhood", "sublocality")
    ciudad = pick("locality", "administrative_area_level_2")
    return colonia, ciudad


def _result(name, address, lat, lng, colonia, ciudad, precision) -> dict:
    return {
        "name":          name,
        "short_address": ", ".join(p.strip() for p in address.split(",")[:2]),
        "address":       address,
        "lat":           lat,
        "lng":           lng,
        "colonia":       colonia,
        "ciudad":        ciudad,
        "aproximado":    precision != "exacto",
        "_precision":    precision,
    }


async def _places_search(query: str, client: httpx.AsyncClient,
                         ref_lat: float | None, ref_lng: float | None) -> list:
    """Google Places Text Search (New): entiende nombres de lugares y negocios.
    Requiere la "Places API (New)" habilitada en el proyecto de la clave."""
    key = settings.GOOGLE_MAPS_API_KEY
    if not key:
        return []
    body: dict = {"textQuery": query, "languageCode": "es", "regionCode": "MX", "maxResultCount": 5}
    if ref_lat and ref_lng:
        body["locationBias"] = {"circle": {"center": {"latitude": ref_lat, "longitude": ref_lng},
                                           "radius": PLACES_BIAS_RADIUS_M}}
    resp = await client.post(PLACES_URL, json=body, headers={
        "X-Goog-Api-Key": key, "X-Goog-FieldMask": PLACES_FIELDS})
    if resp.status_code != 200:
        # 403 = la Places API (New) no está habilitada para esta clave: se sigue con Geocoding
        logger.warning(f"[Geocode/Places] HTTP {resp.status_code} para '{query}': {resp.text[:150]}")
        return []
    results = []
    for p in resp.json().get("places", []):
        loc = p.get("location") or {}
        if "latitude" not in loc:
            continue
        colonia, ciudad = _colonia_ciudad(p.get("addressComponents") or [], "longText")
        name = (p.get("displayName") or {}).get("text") or p.get("formattedAddress", "").split(",")[0]
        results.append(_result(name, p.get("formattedAddress", ""), loc["latitude"], loc["longitude"],
                               colonia, ciudad, _precision(set(p.get("types") or []))))
    return results


async def _geocode_google(query: str, client: httpx.AsyncClient,
                          ref_lat: float | None = None, ref_lng: float | None = None) -> list:
    """Google Geocoding: direcciones con calle y número."""
    key = settings.GOOGLE_MAPS_API_KEY
    if not key:
        return []
    params = {"address": query, "key": key, "language": "es", "region": "MX",
              "components": "country:MX"}
    if ref_lat and ref_lng:
        d = settings.CITY_BBOX_DEG or 0.3
        params["bounds"] = f"{ref_lat - d},{ref_lng - d}|{ref_lat + d},{ref_lng + d}"
    resp = await client.get(GMAPS_URL, params=params)
    resp.raise_for_status()
    data = resp.json()
    if data.get("status") not in ("OK", "ZERO_RESULTS"):
        logger.warning(f"[Geocode/GMaps] status={data.get('status')} para '{query}'")
        return []
    results = []
    for r in data.get("results", []):
        loc = r["geometry"]["location"]
        colonia, ciudad = _colonia_ciudad(r.get("address_components") or [], "long_name")
        results.append(_result(r["formatted_address"].split(",")[0], r["formatted_address"],
                               loc["lat"], loc["lng"], colonia, ciudad,
                               _precision(set(r.get("types") or []), r["geometry"].get("location_type"))))
    return results


async def _geocode_nominatim(query: str, client: httpx.AsyncClient,
                              viewbox: str | None = None) -> list:
    """Nominatim (OSM) — último recurso."""
    q_norm = _normalize_query(query)
    parts  = [p.strip() for p in query.split(",") if p.strip()]
    candidates = []
    if len(parts) >= 3:
        candidates.append(f"{parts[0]} {parts[-1]}")
    candidates.append(query)
    if q_norm.lower() != query.lower():
        candidates.append(q_norm)
    q_no_num = re.sub(r"[0-9]+", "", query).strip(" ,")
    if q_no_num and q_no_num.lower() != query.lower():
        candidates.append(q_no_num)
    if len(parts) >= 2:
        candidates.append(", ".join(parts[-2:]))
    seen: set = set()
    candidates = [x for x in candidates if x.lower() not in seen and not seen.add(x.lower())]

    base = {"format": "jsonv2", "limit": 4, "countrycodes": "mx", "addressdetails": 1}
    for q_str in candidates:
        tries = [{**base, "q": q_str, "viewbox": viewbox, "bounded": 1}] if viewbox else []
        tries.append({**base, "q": q_str})
        for params in tries:
            resp = await client.get(f"{NOMINATIM_URL}/search", params=params, headers=_NOM_HEADERS)
            resp.raise_for_status()
            items = resp.json()
            if items:
                return [_nom_to_result(i) for i in items]
    return []


def _nom_to_result(item: dict) -> dict:
    name, _ = _parse_display_name(item.get("display_name", ""))
    addr = item.get("address") or {}
    kind = item.get("addresstype") or item.get("type") or ""
    if kind in _NOM_CITY_LEVEL:
        precision = "ciudad"
    elif kind in _NOM_AREA_LEVEL:
        precision = "zona"
    else:
        precision = "exacto"
    colonia = addr.get("suburb") or addr.get("neighbourhood") or addr.get("quarter") or ""
    ciudad = addr.get("city") or addr.get("town") or addr.get("village") or addr.get("municipality") or ""
    return _result(name, item.get("display_name", ""), float(item.get("lat", 0)),
                   float(item.get("lon", 0)), colonia, ciudad, precision)


_STOP_WORDS = {"de", "del", "la", "el", "los", "las", "en", "y", "a",
               "con", "por", "para", "al", "calle", "avenida", "av", "c",
               "col", "colonia", "fracc", "fraccionamiento", "numero", "num"}

def _query_words(q: str) -> set:
    """Extrae palabras significativas del query (>2 chars, sin stopwords, sin números puros)."""
    tokens = re.sub(r"[^\w\s]", " ", q.lower()).split()
    return {t for t in tokens if len(t) > 2 and t not in _STOP_WORDS and not t.isdigit()}

def _result_matches_query(result: dict, query: str) -> bool:
    """
    Verifica que el resultado geocodificado tenga relación con el query original.
    Retorna False si ninguna palabra significativa del query aparece en la dirección resultado.
    Esto evita que Google/Nominatim devuelva una calle cercana-pero-incorrecta.
    """
    q_words = _query_words(query)
    if not q_words:
        return True  # query muy corto — aceptar
    # Usar solo name+short_address; el address completo incluye ciudad/pais que daria falsos positivos
    local_text = (result.get("name", "") + " " + result.get("short_address", "")).lower()
    matches = sum(1 for w in q_words if w in local_text)
    # Al menos 1 palabra significativa debe coincidir
    return matches > 0


def _keep(results: list, query: str, ref_lat, ref_lng) -> list:
    """Quita lo de nivel ciudad, lo que no tiene que ver con lo que escribió y lo que
    está fuera de zona; los exactos primero."""
    out = [r for r in results
           if r["_precision"] != "ciudad"
           and _result_matches_query(r, query)
           and _within_radius(r, ref_lat, ref_lng)]
    out.sort(key=lambda r: r["aproximado"])   # estable: respeta el orden del proveedor
    for r in out:
        r.pop("_precision", None)
    return out


@router.get("/geocode")
async def geocode_address(
    q: str,
    lat: float | None = None,
    lon: float | None = None,
    _=Depends(_auth),
):
    q_google = _clean_query(q)     # Google: sin aliases, entiende lugares por nombre
    q_nom    = _normalize_query(q)  # Nominatim: con aliases (terminal, hospital, etc.)
    # Cerca de dónde: el pasajero (lat/lon) si se conoce; si no, el centro de operación
    ref_lat = lat if lat is not None else (settings.CITY_LAT or None)
    ref_lon = lon if lon is not None else (settings.CITY_LNG or None)

    viewbox = None
    if ref_lat and ref_lon:
        d = settings.CITY_BBOX_DEG or 0.3
        viewbox = f"{ref_lon - d},{ref_lat - d},{ref_lon + d},{ref_lat + d}"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            if settings.GOOGLE_MAPS_API_KEY:
                results = _keep(await _places_search(q_google, client, ref_lat, ref_lon),
                                q_google, lat, lon)
                if results:
                    logger.info(f"[Geocode] Places: '{q_google}' → {results[0]['name']}")
                    return {"results": results}
                results = _keep(await _geocode_google(q_google, client, ref_lat, ref_lon),
                                q_google, lat, lon)
                if results:
                    logger.info(f"[Geocode] GMaps: '{q_google}' → {results[0]['name']}")
                    return {"results": results}
                logger.warning(f"[Geocode] Google sin resultados útiles para '{q_google}', usando Nominatim")

            results = _keep(await _geocode_nominatim(q_nom, client, viewbox), q_nom, lat, lon)
            if results:
                logger.info(f"[Geocode] Nominatim: '{q_nom}' → {results[0]['name']}")
            else:
                logger.warning(f"[Geocode] Sin resultados útiles para '{q_nom}' — pedir más detalle o GPS")
            return {"results": results}

    except Exception as e:
        raise HTTPException(503, f"Geocodificación no disponible: {e}")


@router.get("/reverse-geocode")
async def reverse_geocode(
    lat: float,
    lon: float,
    _=Depends(_auth),
):
    """Coordenadas GPS → dirección legible (con colonia y ciudad). Google primario, Nominatim fallback."""
    key = settings.GOOGLE_MAPS_API_KEY
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            if key:
                resp = await client.get(GMAPS_REV_URL, params={
                    "latlng": f"{lat},{lon}", "key": key,
                    "language": "es", "result_type": "street_address|route|neighborhood",
                })
                resp.raise_for_status()
                data = resp.json()
                if data.get("status") == "OK" and data.get("results"):
                    r       = data["results"][0]
                    address = r["formatted_address"]
                    colonia, ciudad = _colonia_ciudad(r.get("address_components") or [], "long_name")
                    return {"name": address.split(",")[0], "short_address": ", ".join(address.split(",")[:2]),
                            "address": address, "lat": lat, "lng": lon,
                            "colonia": colonia, "ciudad": ciudad}

            # Fallback Nominatim
            resp = await client.get(f"{NOMINATIM_URL}/reverse",
                params={"lat": lat, "lon": lon, "format": "jsonv2", "addressdetails": 1},
                headers=_NOM_HEADERS)
            resp.raise_for_status()
            r = _nom_to_result(resp.json())
            return {"name": r["name"], "short_address": r["short_address"], "address": r["address"],
                    "lat": lat, "lng": lon, "colonia": r["colonia"], "ciudad": r["ciudad"]}

    except Exception as e:
        raise HTTPException(503, f"Geocodificación inversa no disponible: {e}")


@router.post("/rides/estimate")
def estimate_fare(payload: dict, db: Session = Depends(get_db), _=Depends(_auth)):
    orig = payload.get("origin") or {}
    dest = payload.get("destination") or {}
    olat, olng = float(orig.get("lat") or 0), float(orig.get("lng") or 0)
    dlat, dlng = float(dest.get("lat") or 0), float(dest.get("lng") or 0)
    distance_km, minutes = route_km_min(olat, olng, dlat, dlng)   # por calle, no línea recta
    cfg = get_fare_config(db)
    fare = calculate_fare(cfg, distance_km)
    return {
        "fare": round(fare, 2),
        "distance_km": round(distance_km, 2),
        "duration_minutes": minutes,
    }


@router.post("/rides/create")
async def create_ride(payload: dict, db: Session = Depends(get_db), _=Depends(_auth)):
    from datetime import datetime as _dt
    phone = (payload.get("customer_phone") or "").strip()
    if not phone:
        raise HTTPException(400, "customer_phone requerido")
    orig = payload.get("origin") or {}
    dest = payload.get("destination") or {}
    if not dest:
        raise HTTPException(400, "destination requerido")

    customer = db.query(Customer).filter(Customer.phone == phone).first()
    c_name = (customer.name if customer else None) or payload.get("customer_name") or "Cliente WhatsApp"

    olat = float(orig.get("lat") or 0)
    olng = float(orig.get("lng") or 0)
    dlat = float(dest.get("lat") or 0)
    dlng = float(dest.get("lng") or 0)
    distance_km, _ = route_km_min(olat, olng, dlat, dlng)   # mismo cálculo que la estimación
    cfg = get_fare_config(db)
    fare = calculate_fare(cfg, distance_km)

    # Viaje programado si viene scheduled_at
    scheduled_at_raw = payload.get("scheduled_at")
    scheduled_at = None
    trip_status = TripStatus.REQUESTED
    if scheduled_at_raw and not settings.SCHEDULED_RIDES_ENABLED:
        raise HTTPException(409, "Por ahora solo hay viajes para este momento")
    if scheduled_at_raw:
        try:
            scheduled_at = _dt.fromisoformat(scheduled_at_raw)
            trip_status = TripStatus.SCHEDULED
        except ValueError:
            logger.warning(f"[WA] scheduled_at inválido: {scheduled_at_raw!r} — creando viaje inmediato")

    trip = Trip(
        trip_id=f"WA-{uuid.uuid4().hex[:8].upper()}",
        customer_phone=phone,
        customer_name=c_name,
        origin_address=orig.get("address") or "Punto de recogida (WhatsApp)",
        origin_lat=olat or None,
        origin_lng=olng or None,
        destination_address=dest.get("address", ""),
        destination_lat=dlat,
        destination_lng=dlng,
        fare=fare,
        distance_km=distance_km,
        payment_method=payload.get("payment_method", "cash"),
        payment_status="pending",
        status=trip_status,
        scheduled_at=scheduled_at,
        preferred_driver_phone=payload.get("preferred_driver_phone") or None,
        preferred_driver_name=payload.get("preferred_driver_name") or None,
    )
    db.add(trip)
    db.commit()
    db.refresh(trip)
    logger.info(f"[WA] Viaje {trip.trip_id} creado para {phone} (status={trip_status.value})")

    tracking_url = f"{settings.PUBLIC_URL}/seguimiento/{trip.trip_id}"

    # ── Asignación inteligente (solo para viajes inmediatos) ──────────────────
    auto_assigned_driver = None
    if trip_status == TripStatus.REQUESTED:
        try:
            from ..services.ride_assignment import find_best_driver
            best_driver, dist_km = find_best_driver(
                db, olat, olng,
                preferred_phone=payload.get("preferred_driver_phone") or None,
            )
            if best_driver:
                from ..routers.sse import push_event
                trip.driver_phone = best_driver.phone
                trip.driver_name  = best_driver.name
                # status se mantiene REQUESTED — conductor debe aceptar explícitamente
                db.commit()
                auto_assigned_driver = best_driver
                logger.info(
                    f"[WA] Auto-asignado {trip.trip_id} → {best_driver.name} "
                    f"({'preferido' if best_driver.phone == payload.get('preferred_driver_phone') else f'{dist_km:.1f} km'})"
                )
                # SSE al conductor asignado
                await push_event(best_driver.phone, "assigned", {
                    "ride_id":     trip.trip_id,
                    "origin":      {"address": trip.origin_address, "lat": olat, "lng": olng},
                    "destination": {"address": trip.destination_address, "lat": dlat, "lng": dlng},
                    "fare":        round(float(fare), 2),
                    "distance_km": round(distance_km, 1),
                    "customer":    c_name,
                    "tracking_url": tracking_url,
                })
                # Telegram solo al conductor asignado
                if best_driver.telegram_chat_id:
                    try:
                        from ..services.telegram import send_message, send_with_buttons
                        from .telegram_bot import _maps
                        maps_o = _maps(olat, olng) or ""
                        maps_d = _maps(dlat, dlng) or ""
                        await send_with_buttons(
                            best_driver.telegram_chat_id,
                            f"🎯 <b>Viaje asignado directamente a ti</b>\n\n"
                            f"ID: <code>{trip.trip_id}</code>\n"
                            f"📍 <a href='{maps_o}'>Origen</a>: {trip.origin_address}\n"
                            f"🏁 <a href='{maps_d}'>Destino</a>: {trip.destination_address}\n"
                            f"💰 ${float(fare):.0f} MXN | {round(distance_km, 1)} km\n"
                            f"👤 {c_name}",
                            [[{"text": "✅ Aceptar viaje", "callback_data": f"accept_{trip.trip_id}"}]],
                        )
                    except Exception:
                        pass
        except Exception as assign_err:
            logger.warning(f"[WA] Auto-assign error: {assign_err}")

    # ── Sin auto-asignación → broadcast al pool ───────────────────────────────
    if not auto_assigned_driver and trip_status == TripStatus.REQUESTED:
        ride_data = {
            "ride_id":     trip.trip_id,
            "origin":      {"address": trip.origin_address, "lat": olat, "lng": olng},
            "destination": {"address": trip.destination_address, "lat": dlat, "lng": dlng},
            "fare":        round(float(fare), 2),
            "distance_km": round(distance_km, 1),
            "customer":    c_name,
        }
        try:
            from ..routers.sse import broadcast_event
            await broadcast_event("new_ride", ride_data)
        except Exception as sse_err:
            logger.warning(f"[WA] SSE broadcast error: {sse_err}")
        try:
            from .telegram_bot import notify_drivers_new_ride
            await notify_drivers_new_ride(trip, db)
        except Exception as drv_err:
            logger.warning(f"[WA] Driver Telegram notify failed: {drv_err}")

    # ── Notificar al operador ─────────────────────────────────────────────────
    # Si el chat del operador también es chofer y ya le llegó "Nuevo viaje
    # disponible", no se le repite el mismo viaje (pasaba en pruebas del dueño).
    try:
        from ..services import ride_notifs
        notified = {chat for chat, _ in await ride_notifs.get(trip.trip_id)}
    except Exception:
        notified = set()
    operator_already_notified = bool(settings.TELEGRAM_ALERT_CHAT_ID) and settings.TELEGRAM_ALERT_CHAT_ID in notified
    try:
        from ..services.telegram import send_to_operator
        from .telegram_bot import customer_label
        maps_orig = f"https://maps.google.com/?q={olat},{olng}" if (olat and olng) else "Sin coords"
        maps_dest = f"https://maps.google.com/?q={dlat},{dlng}"
        label = "📅 PROGRAMADO" if scheduled_at else "🚖 INMEDIATO"
        asign_note = f"\n🎯 Auto-asignado a: {auto_assigned_driver.name}" if auto_assigned_driver else ""
        msg = (
            f"{label} — <b>Viaje WhatsApp</b>\n"
            f"ID: <code>{trip.trip_id}</code>\n"
            f"Cliente: {customer_label(c_name, phone)} | <code>{phone}</code>\n"
            f"📍 <a href='{maps_orig}'>Origen</a>: {trip.origin_address}\n"
            f"🏁 <a href='{maps_dest}'>Destino</a>: {trip.destination_address}\n"
            f"💰 Tarifa aprox.: ${fare:.0f} | {round(distance_km, 1)} km\n"
            f"🔍 <a href='{tracking_url}'>Seguimiento en vivo</a>"
            f"{asign_note}"
        )
        if scheduled_at:
            msg += f"\n🕐 Hora: {scheduled_at.strftime('%d/%m %H:%M')}"
        if not operator_already_notified:
            await send_to_operator(msg)
    except Exception as tg_err:
        logger.warning(f"[WA] Telegram notify failed: {tg_err}")

    return {
        "ride_id": trip.trip_id,
        "status": trip.status.value,
        "fare": round(float(fare), 2),
        "distance_km": round(float(distance_km), 2),
        "origin_address": trip.origin_address,
        "destination_address": trip.destination_address,
        "scheduled_at": scheduled_at.isoformat() if scheduled_at else None,
        "tracking_url": tracking_url,
    }


@router.get("/rides/{ride_id}")
def get_ride(ride_id: str, db: Session = Depends(get_db), _=Depends(_auth)):
    trip = db.query(Trip).filter(Trip.trip_id == ride_id).first()
    if not trip:
        raise HTTPException(404, "Viaje no encontrado")
    return {
        "ride_id": trip.trip_id,
        "status": trip.status.value,
        "fare": float(trip.fare or 0),
        "driver_name": trip.driver_name,
        "driver_phone": trip.driver_phone,
        "origin_address": trip.origin_address,
        "destination_address": trip.destination_address,
    }


@router.post("/rides/{ride_id}/cancel")
def cancel_ride(ride_id: str, db: Session = Depends(get_db), _=Depends(_auth)):
    trip = db.query(Trip).filter(Trip.trip_id == ride_id).first()
    if not trip:
        raise HTTPException(404, "Viaje no encontrado")
    if trip.status in (TripStatus.COMPLETED, TripStatus.CANCELLED):
        raise HTTPException(400, "El viaje ya está terminado")
    trip.status = TripStatus.CANCELLED
    db.commit()
    return {"success": True, "ride_id": ride_id}
