"""
Carga la configuración de tarifas desde DB con cache de 60 segundos.
Centraliza el cálculo de tarifa para estimate, request y schedule.
"""
import time
from datetime import datetime, timezone

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


def calculate_fare(cfg: FareConfig, distance_km: float) -> float:
    """Tarifa base + por km, aplicando surge si corresponde."""
    base      = float(cfg.base_fare)
    per_km    = float(cfg.per_km_rate)
    minimum   = float(cfg.minimum_fare)

    raw = base + distance_km * per_km

    if cfg.surge_enabled:
        multiplier = _surge_multiplier(cfg)
        raw *= multiplier

    return round(max(raw, minimum), 2)


def _surge_multiplier(cfg: FareConfig) -> float:
    now  = datetime.now(timezone.utc)
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
