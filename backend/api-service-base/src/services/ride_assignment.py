"""
Servicio de asignación de viajes.

Prioridad al asignar conductor a un viaje nuevo:
  1. Conductor preferido del cliente (si está online y activo)
  2. Conductor más cercano al origen dentro de AUTO_ASSIGN_MAX_KM
  3. Pool abierto — broadcast a todos los conductores online
"""
import logging
import math
from typing import Optional, Tuple

from sqlalchemy.orm import Session

from ..models import Driver

logger = logging.getLogger(__name__)

AUTO_ASSIGN_MAX_KM: float = 8.0   # radio máximo de auto-asignación directa


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    )
    return R * 2 * math.asin(math.sqrt(a))


def find_best_driver(
    db: Session,
    origin_lat: float,
    origin_lng: float,
    preferred_phone: Optional[str] = None,
) -> Tuple[Optional[Driver], Optional[float]]:
    """
    Busca el mejor conductor disponible para un viaje.

    Returns:
        (Driver, distance_km) si hay candidato directo.
        (None, None) si debe usarse pool abierto.
    """
    candidates = (
        db.query(Driver)
        .filter(
            Driver.is_online  == True,
            Driver.is_active  == True,
            Driver.current_lat.isnot(None),
            Driver.current_lng.isnot(None),
        )
        .all()
    )

    if not candidates:
        return None, None

    # 1. Conductor preferido del cliente (si está disponible)
    if preferred_phone:
        for d in candidates:
            if d.phone == preferred_phone:
                km = _haversine_km(
                    origin_lat, origin_lng,
                    float(d.current_lat), float(d.current_lng),
                ) if (origin_lat and origin_lng) else 0.0
                logger.info(f"[Assignment] Conductor preferido disponible: {d.name} ({km:.1f} km)")
                return d, km

    if not (origin_lat and origin_lng):
        return None, None

    # 2. Conductor más cercano dentro del radio
    nearest: Optional[Driver] = None
    nearest_km: float = float("inf")
    for d in candidates:
        km = _haversine_km(
            origin_lat, origin_lng,
            float(d.current_lat), float(d.current_lng),
        )
        if km < nearest_km:
            nearest_km = km
            nearest = d

    if nearest and nearest_km <= AUTO_ASSIGN_MAX_KM:
        logger.info(f"[Assignment] Conductor más cercano: {nearest.name} ({nearest_km:.1f} km)")
        return nearest, nearest_km

    logger.info(f"[Assignment] Sin conductor cercano (más próximo a {nearest_km:.1f} km) → pool abierto")
    return None, None
