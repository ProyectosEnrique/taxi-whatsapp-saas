"""
Botón de pánico — registra incidentes de seguridad para conductores y clientes.
Rutas:
  POST /api/v1/customer/incidents
  POST /api/v1/driver/incidents
  GET  /api/v1/incidents              (admin: todos los incidentes activos)
"""
import logging
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Customer, Driver, Incident
from ..auth import get_current_customer, get_current_driver
from ..config import settings

logger = logging.getLogger(__name__)

customer_router = APIRouter(prefix="/api/v1/customer", tags=["incidents"])
driver_router   = APIRouter(prefix="/api/v1/driver",   tags=["incidents"])
admin_router    = APIRouter(prefix="/api/v1",           tags=["incidents"])


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _send_whatsapp_alert(incident: Incident, extra_info: str = ""):
    """Envía alerta al número de flota vía WhatsApp gateway (best-effort)."""
    if not settings.WHATSAPP_NUMBER or not settings.WHATSAPP_GATEWAY_URL:
        return
    maps_link = (
        f"https://maps.google.com/?q={incident.lat},{incident.lng}"
        if incident.lat and incident.lng else "Sin ubicación"
    )
    msg = (
        f"🚨 *ALERTA DE PÁNICO*\n"
        f"Tipo: {'Conductor' if incident.reporter_type == 'driver' else 'Cliente'}\n"
        f"Nombre: {incident.reporter_name}\n"
        f"Tel: {incident.reporter_phone}\n"
        f"Viaje: {incident.trip_id or 'N/A'}\n"
        f"Ubicación: {maps_link}\n"
        f"Hora: {datetime.now(timezone.utc).strftime('%H:%M:%S UTC')}\n"
        f"{extra_info}"
    )
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(
                f"{settings.WHATSAPP_GATEWAY_URL}/send",
                json={"to": settings.WHATSAPP_NUMBER, "message": msg},
            )
    except Exception as e:
        logger.warning(f"[Panic] No se pudo enviar alerta WhatsApp: {e}")


def _create_incident(db: Session, reporter_type, phone, name, payload: dict) -> Incident:
    incident = Incident(
        trip_id       = payload.get("trip_id"),
        reporter_type = reporter_type,
        reporter_phone= phone,
        reporter_name = name,
        lat           = payload.get("lat"),
        lng           = payload.get("lng"),
        notes         = payload.get("notes", ""),
    )
    db.add(incident)
    db.commit()
    db.refresh(incident)
    return incident


# ── Customer endpoint ─────────────────────────────────────────────────────────

@customer_router.post("/incidents")
async def report_incident_customer(
    payload: dict,
    current: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    incident = _create_incident(db, "customer", current.phone, current.name or "Cliente", payload)
    logger.warning(f"[Panic] CLIENTE {current.phone} activó pánico — incidente {incident.incident_id}")
    await _send_whatsapp_alert(incident)
    return {
        "success":     True,
        "incident_id": incident.incident_id,
        "emergency_phone": settings.EMERGENCY_PHONE,
        "message":     "Incidente registrado. Llama al número de emergencias ahora.",
    }


# ── Driver endpoint ───────────────────────────────────────────────────────────

@driver_router.post("/incidents")
async def report_incident_driver(
    payload: dict,
    current: Driver = Depends(get_current_driver),
    db: Session = Depends(get_db),
):
    incident = _create_incident(db, "driver", current.phone, current.name, payload)
    logger.warning(f"[Panic] CONDUCTOR {current.phone} activó pánico — incidente {incident.incident_id}")
    await _send_whatsapp_alert(incident)
    return {
        "success":     True,
        "incident_id": incident.incident_id,
        "emergency_phone": settings.EMERGENCY_PHONE,
        "message":     "Incidente registrado. Llama al número de emergencias ahora.",
    }


# ── Admin: listar incidentes activos ─────────────────────────────────────────

@admin_router.get("/incidents")
def list_incidents(db: Session = Depends(get_db)):
    incidents = (
        db.query(Incident)
        .order_by(Incident.created_at.desc())
        .limit(50)
        .all()
    )
    return {"incidents": [
        {
            "incident_id":    i.incident_id,
            "trip_id":        i.trip_id,
            "reporter_type":  i.reporter_type,
            "reporter_name":  i.reporter_name,
            "reporter_phone": i.reporter_phone,
            "lat":            float(i.lat) if i.lat else None,
            "lng":            float(i.lng) if i.lng else None,
            "notes":          i.notes,
            "status":         i.status,
            "created_at":     i.created_at.isoformat() if i.created_at else None,
        }
        for i in incidents
    ]}
