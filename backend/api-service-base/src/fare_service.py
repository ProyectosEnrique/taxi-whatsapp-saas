"""
Carga la configuración de tarifas desde DB con cache de 60 segundos.
Centraliza el cálculo de tarifa para estimate, request y schedule.
"""
import time
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from .models import FareConfig

_cache: dict = {}
_cache_ttl   = 60  # segundos


def _cfg_to_snapshot(cfg: FareConfig) -> dict:
    """Serializa FareConfig a dict plano para evitar DetachedInstanceError en caché."""
    return {k: getattr(cfg, k) for k in [
        "id", "base_fare", "per_km_rate", "per_minute_rate", "minimum_fare",
        "surge_enabled", "surge_peak_multiplier", "surge_night_multiplier", "surge_weekend_multiplier",
        "charge_airport_pickup", "charge_airport_dropoff", "charge_extra_passenger",
        "charge_luggage", "discount_frequent_rider", "discount_corporate", "updated_at",
        "night_surcharge", "night_start_hour", "night_end_hour",
    ]}


class _FareConfigProxy:
    """Objeto que imita FareConfig pero vive fuera de la sesión DB."""
    def __init__(self, snapshot: dict):
        for k, v in snapshot.items():
            setattr(self, k, v)


def get_fare_config(db: Session) -> "_FareConfigProxy":
    now = time.monotonic()
    if _cache.get("config") and now - _cache.get("ts", 0) < _cache_ttl:
        return _cache["config"]

    cfg = db.query(FareConfig).filter(FareConfig.id == 1).first()
    if not cfg:
        cfg = FareConfig(id=1)
        db.add(cfg)
        db.commit()
        db.refresh(cfg)

    proxy = _FareConfigProxy(_cfg_to_snapshot(cfg))
    _cache["config"] = proxy
    _cache["ts"]     = now
    return proxy


def invalidate_cache():
    _cache.clear()


# ── Distancia por calle (2026-11-09) ──────────────────────────────────────────
# Antes la tarifa usaba la línea recta: un viaje con rodeos salía más barato de
# lo que el chofer cobra. Ahora OSRM (mismo servicio que dibuja la ruta en
# /seguimiento); si no responde, línea recta × 1.3 (no cobrar de menos).
# Caché corta por coordenadas: la estimación y la creación del viaje dan el
# mismo precio aunque OSRM conteste distinto entre una y otra.
OSRM_URL = "https://router.project-osrm.org/route/v1/driving"
_ROUTE_TTL = 1800
_route_cache: dict[tuple, tuple[float, float, float]] = {}


def _straight_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    import math
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = (math.sin(math.radians(lat2 - lat1) / 2) ** 2
         + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lng2 - lng1) / 2) ** 2)
    return 6371.0 * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _osrm_route(olat: float, olng: float, dlat: float, dlng: float) -> tuple[float, float] | None:
    """(km, minutos) por calle según OSRM, o None si no responde."""
    try:
        import httpx
        r = httpx.get(f"{OSRM_URL}/{olng},{olat};{dlng},{dlat}", params={"overview": "false"}, timeout=4.0)
        route = (r.json().get("routes") or [None])[0]
        if route:
            return route["distance"] / 1000, route["duration"] / 60
    except Exception:
        pass
    return None


def route_km_min(olat: float, olng: float, dlat: float, dlng: float) -> tuple[float, int]:
    """(km por calle, minutos estimados)."""
    if not (olat and olng and dlat and dlng):
        return 5.0, 12
    key = (round(olat, 4), round(olng, 4), round(dlat, 4), round(dlng, 4))
    hit = _route_cache.get(key)
    if hit and time.monotonic() - hit[2] < _ROUTE_TTL:
        return hit[0], int(hit[1])
    km, minutes = _osrm_route(olat, olng, dlat, dlng) or (None, None)
    if km is None:
        km = _straight_km(olat, olng, dlat, dlng) * 1.3
        minutes = km / 25 * 60          # ~25 km/h en ciudad
    km = max(km, 1.0)
    minutes = max(3, round(minutes))
    _route_cache[key] = (km, minutes, time.monotonic())
    if len(_route_cache) > 2000:
        _route_cache.clear()
    return km, minutes


def _mexico_now() -> datetime:
    # Hora de México (UTC-6, sin horario de verano desde 2022)
    return datetime.now(timezone.utc) - timedelta(hours=6)


def is_night(cfg) -> bool:
    """¿Corre la tarifa de noche? Horas de México; inicio > fin cruza la medianoche (22 → 6)."""
    start = getattr(cfg, "night_start_hour", None)
    end = getattr(cfg, "night_end_hour", None)
    if start is None or end is None or start == end:
        return False
    hour = _mexico_now().hour
    return (start <= hour < end) if start < end else (hour >= start or hour < end)


def night_surcharge(cfg) -> float:
    return float(getattr(cfg, "night_surcharge", 0) or 0) if is_night(cfg) else 0.0


def calculate_fare(cfg: FareConfig, distance_km: float) -> float:
    """Banderazo + por km (redondeado a $5, sin bajar de la mínima) + suma fija de noche.
    El surge (multiplicador) sigue existiendo pero está apagado en la base de Celaya."""
    base      = float(cfg.base_fare)
    per_km    = float(cfg.per_km_rate)
    minimum   = float(cfg.minimum_fare)

    raw = base + distance_km * per_km

    if cfg.surge_enabled:
        multiplier = _surge_multiplier(cfg)
        raw *= multiplier

    # En taxi se cobra en pesos redondos: al múltiplo de $5 más cercano (77.92 → 80),
    # sin bajar de la mínima
    return float(max(_round_to_5(raw), minimum) + night_surcharge(cfg))


# ── Lista de precios de la Central (2026-11-24) ──────────────────────────────
# La base de la Central de Autobuses de Celaya tiene lista DÍA/NOCHE por colonia, hotel o
# clínica (`local_pois.central_price_*`). Si el viaje sale de la Central o llega a ella y el
# otro punto es un lugar de la lista, se cobra la lista; si no, la fórmula.
CENTRAL_RADIUS_M = 400      # "estoy en la Central": el GPS dentro del andén/estacionamiento
EXACT_PLACE_M = 150         # el destino es ese lugar (se eligió por nombre)
COLONIA_RADIUS_M = 500      # calle dentro de una colonia de la lista: la colonia más cercana


def _meters(lat1, lng1, lat2, lng2) -> float:
    return _straight_km(float(lat1), float(lng1), float(lat2), float(lng2)) * 1000


def central_list_price(db: Session, cfg, olat, olng, dlat, dlng) -> float | None:
    """Precio de la lista si el viaje es Central ↔ lugar de la lista; None si no aplica."""
    from .models import LocalPOI
    if not (olat and olng and dlat and dlng):
        return None
    try:
        pois = db.query(LocalPOI).filter(LocalPOI.is_active == True).filter(  # noqa: E712
            (LocalPOI.kind == "central") | (LocalPOI.central_price_day.isnot(None))).all()
    except Exception:
        return None
    centrals = [p for p in pois if p.kind == "central"]
    if not centrals:
        return None

    def at_central(lat, lng):
        return any(_meters(lat, lng, c.lat, c.lng) <= CENTRAL_RADIUS_M for c in centrals)

    if at_central(olat, olng):
        lat, lng = dlat, dlng
    elif at_central(dlat, dlng):
        lat, lng = olat, olng
    else:
        return None
    if at_central(lat, lng):
        return None
    priced = [(p, _meters(lat, lng, p.lat, p.lng)) for p in pois if p.central_price_day is not None]
    exact = [x for x in priced if x[1] <= EXACT_PLACE_M]
    near = exact or [x for x in priced if x[0].kind == "colonia" and x[1] <= COLONIA_RADIUS_M]
    if not near:
        return None
    poi = min(near, key=lambda x: x[1])[0]
    if is_night(cfg) and poi.central_price_night is not None:
        return float(poi.central_price_night)
    if is_night(cfg):
        return float(poi.central_price_day) + float(getattr(cfg, "night_surcharge", 0) or 0)
    return float(poi.central_price_day)


def trip_fare(db: Session, cfg, olat, olng, dlat, dlng, distance_km: float) -> float:
    """Tarifa de un viaje: lista de la Central si aplica, si no la fórmula."""
    listed = central_list_price(db, cfg, olat, olng, dlat, dlng)
    return listed if listed is not None else calculate_fare(cfg, distance_km)


def _round_to_5(amount: float) -> int:
    return int(5 * round(amount / 5))


def _surge_multiplier(cfg: FareConfig) -> float:
    # Hora de México (UTC-6, sin horario de verano desde 2022). Antes usaba UTC:
    # la "madrugada" empezaba a las 5 pm.
    now  = _mexico_now()
    hour = now.hour
    dow  = now.weekday()  # 0=lunes … 6=domingo

    # Madrugada (11pm-5am)
    if hour >= 23 or hour < 5:
        return float(cfg.surge_night_multiplier)

    # Fin de semana
    if dow >= 5:
        return float(cfg.surge_weekend_multiplier)

    # Horas pico (7-9am, 18-21pm)
    if 7 <= hour < 9 or 18 <= hour < 21:
        return float(cfg.surge_peak_multiplier)

    return 1.0


def fare_config_to_dict(cfg: FareConfig) -> dict:
    return {
        "base_fare":       float(cfg.base_fare),
        "per_km_rate":     float(cfg.per_km_rate),
        "per_minute_rate": float(cfg.per_minute_rate),
        "minimum_fare":    float(cfg.minimum_fare),
        "night": {
            "surcharge":  float(getattr(cfg, "night_surcharge", 0) or 0),
            "start_hour": getattr(cfg, "night_start_hour", None),
            "end_hour":   getattr(cfg, "night_end_hour", None),
        },
        "surge_pricing": {
            "enabled":               cfg.surge_enabled,
            "peak_hours_multiplier": float(cfg.surge_peak_multiplier),
            "late_night_multiplier": float(cfg.surge_night_multiplier),
            "weekend_multiplier":    float(cfg.surge_weekend_multiplier),
        },
        "special_charges": {
            "airport_pickup":   float(cfg.charge_airport_pickup),
            "airport_dropoff":  float(cfg.charge_airport_dropoff),
            "extra_passenger":  float(cfg.charge_extra_passenger),
            "luggage":          float(cfg.charge_luggage),
        },
        "discounts": {
            "frequent_rider": float(cfg.discount_frequent_rider),
            "corporate":      float(cfg.discount_corporate),
        },
        "updated_at": cfg.updated_at.isoformat() if cfg.updated_at else None,
    }
