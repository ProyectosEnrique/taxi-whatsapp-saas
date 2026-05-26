"""
Botón de pánico SOS — incidentes de seguridad para conductores y clientes.

Rutas:
  POST /api/v1/customer/incidents                      — activar SOS (cliente)
  POST /api/v1/driver/incidents                        — activar SOS (conductor)
  POST /api/v1/customer/incidents/{id}/location        — actualizar GPS en vivo
  POST /api/v1/driver/incidents/{id}/location          — actualizar GPS en vivo
  POST /api/v1/customer/incidents/{id}/audio           — subir audio grabado
  POST /api/v1/driver/incidents/{id}/audio             — subir audio grabado
  GET  /api/v1/incidents/{id}/track                    — rastreo público (sin auth)
  GET  /api/v1/incidents                               — listar (admin)
  POST /api/v1/incidents/{id}/resolve                  — marcar resuelto (admin)
"""
import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Customer, Driver, Incident
from ..auth import get_current_customer, get_current_driver
from ..config import settings
from ..services.telegram import send_to_operator, send_message

logger = logging.getLogger(__name__)

customer_router = APIRouter(prefix="/api/v1/customer", tags=["incidents"])
driver_router   = APIRouter(prefix="/api/v1/driver",   tags=["incidents"])
admin_router    = APIRouter(prefix="/api/v1",           tags=["incidents"])

UPLOAD_DIR = Path("/app/uploads/incidents")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _tracking_url(incident_id: str) -> str:
    return f"{settings.PUBLIC_URL}/track/{incident_id}"


def _maps_url(lat, lng) -> str:
    if lat and lng:
        return f"https://maps.google.com/?q={lat},{lng}"
    return "Sin ubicación"


async def _alert_operator(incident: Incident) -> None:
    """Manda alerta Telegram al grupo del operador."""
    maps = _maps_url(incident.lat, incident.lng)
    track = _tracking_url(incident.incident_id)
    tipo = "Conductor" if incident.reporter_type == "driver" else "Cliente"
    text = (
        f"🚨 <b>ALERTA SOS</b>\n"
        f"Tipo: {tipo}\n"
        f"Nombre: <b>{incident.reporter_name}</b>\n"
        f"Tel: {incident.reporter_phone}\n"
        f"Viaje: {incident.trip_id or 'N/A'}\n"
        f"Hora: {datetime.now(timezone.utc).strftime('%H:%M UTC')}\n"
        f"📍 <a href='{maps}'>Ver en mapa</a>\n"
        f"🔗 <a href='{track}'>Rastreo en vivo</a>"
    )
    await send_to_operator(text)


async def _alert_emergency_contact(incident: Incident, contact_name: str,
                                   contact_phone: str, contact_telegram_id: str) -> None:
    """Manda alerta Telegram al contacto de emergencia personal."""
    if not contact_telegram_id:
        return
    maps = _maps_url(incident.lat, incident.lng)
    track = _tracking_url(incident.incident_id)
    tipo = "conductor de taxi" if incident.reporter_type == "driver" else "pasajero"
    text = (
        f"🚨 <b>ALERTA DE EMERGENCIA</b>\n\n"
        f"{incident.reporter_name} ({tipo}) activó el botón SOS.\n\n"
        f"📍 <a href='{maps}'>Ver ubicación ahora</a>\n"
        f"🔗 <a href='{track}'>Rastreo en vivo</a>\n\n"
        f"Tel: {incident.reporter_phone}\n"
        f"Si no puedes comunicarte, llama al {settings.EMERGENCY_PHONE}."
    )
    await send_message(contact_telegram_id, text)


def _create_incident(db: Session, reporter_type, phone, name, payload: dict) -> Incident:
    incident = Incident(
        trip_id           = payload.get("trip_id"),
        reporter_type     = reporter_type,
        reporter_phone    = phone,
        reporter_name     = name,
        lat               = payload.get("lat"),
        lng               = payload.get("lng"),
        last_location_lat = payload.get("lat"),
        last_location_lng = payload.get("lng"),
        last_location_at  = datetime.now(timezone.utc) if payload.get("lat") else None,
        notes             = payload.get("notes", ""),
    )
    db.add(incident)
    db.commit()
    db.refresh(incident)
    return incident


def _incident_response(incident: Incident) -> dict:
    return {
        "success":       True,
        "incident_id":   incident.incident_id,
        "tracking_url":  _tracking_url(incident.incident_id),
        "emergency_phone": settings.EMERGENCY_PHONE,
        "message":       "Alerta enviada. Tu contacto de emergencia y el operador han sido notificados.",
    }


# ── Customer SOS ──────────────────────────────────────────────────────────────

@customer_router.post("/incidents")
async def report_incident_customer(
    payload: dict,
    current: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    incident = _create_incident(db, "customer", current.phone, current.name or "Cliente", payload)
    logger.warning(f"[SOS] CLIENTE {current.phone} — {incident.incident_id}")

    await _alert_operator(incident)
    await _alert_emergency_contact(
        incident,
        current.emergency_contact_name or "",
        current.emergency_contact_phone or "",
        current.emergency_contact_telegram_id or "",
    )
    return _incident_response(incident)


# ── Driver SOS ────────────────────────────────────────────────────────────────

@driver_router.post("/incidents")
async def report_incident_driver(
    payload: dict,
    current: Driver = Depends(get_current_driver),
    db: Session = Depends(get_db),
):
    incident = _create_incident(db, "driver", current.phone, current.name, payload)
    logger.warning(f"[SOS] CONDUCTOR {current.phone} — {incident.incident_id}")

    await _alert_operator(incident)
    await _alert_emergency_contact(
        incident,
        current.emergency_contact_name or "",
        current.emergency_contact_phone or "",
        current.emergency_contact_telegram_id or "",
    )
    return _incident_response(incident)


# ── GPS en vivo ───────────────────────────────────────────────────────────────

def _update_location(incident_id: str, lat: float, lng: float, db: Session) -> dict:
    incident = db.query(Incident).filter(Incident.incident_id == incident_id).first()
    if not incident:
        raise HTTPException(404, "Incidente no encontrado")
    incident.last_location_lat = lat
    incident.last_location_lng = lng
    incident.last_location_at  = datetime.now(timezone.utc)
    db.commit()
    return {"success": True}


@customer_router.post("/incidents/{incident_id}/location")
def update_location_customer(
    incident_id: str,
    payload: dict,
    current: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    return _update_location(incident_id, payload.get("lat"), payload.get("lng"), db)


@driver_router.post("/incidents/{incident_id}/location")
def update_location_driver(
    incident_id: str,
    payload: dict,
    current: Driver = Depends(get_current_driver),
    db: Session = Depends(get_db),
):
    return _update_location(incident_id, payload.get("lat"), payload.get("lng"), db)


# ── Audio grabado ─────────────────────────────────────────────────────────────

def _save_audio(incident_id: str, file: UploadFile, db: Session) -> dict:
    incident = db.query(Incident).filter(Incident.incident_id == incident_id).first()
    if not incident:
        raise HTTPException(404, "Incidente no encontrado")

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    ext = Path(file.filename).suffix if file.filename else ".webm"
    dest = UPLOAD_DIR / f"{incident_id}{ext}"
    with dest.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    incident.audio_url = f"{settings.PUBLIC_URL}/uploads/incidents/{incident_id}{ext}"
    db.commit()
    return {"success": True, "audio_url": incident.audio_url}


@customer_router.post("/incidents/{incident_id}/audio")
def upload_audio_customer(
    incident_id: str,
    file: UploadFile = File(...),
    current: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    return _save_audio(incident_id, file, db)


@driver_router.post("/incidents/{incident_id}/audio")
def upload_audio_driver(
    incident_id: str,
    file: UploadFile = File(...),
    current: Driver = Depends(get_current_driver),
    db: Session = Depends(get_db),
):
    return _save_audio(incident_id, file, db)


# ── Rastreo público ───────────────────────────────────────────────────────────

@admin_router.get("/incidents/{incident_id}/track")
def public_track(incident_id: str, db: Session = Depends(get_db)):
    """Sin auth — para compartir el link con contacto de emergencia."""
    incident = db.query(Incident).filter(Incident.incident_id == incident_id).first()
    if not incident:
        raise HTTPException(404, "Incidente no encontrado")
    return {
        "incident_id":   incident.incident_id,
        "reporter_name": incident.reporter_name,
        "reporter_type": incident.reporter_type,
        "trip_id":       incident.trip_id,
        "status":        incident.status,
        "origin_lat":    float(incident.lat)               if incident.lat else None,
        "origin_lng":    float(incident.lng)               if incident.lng else None,
        "lat":           float(incident.last_location_lat) if incident.last_location_lat else None,
        "lng":           float(incident.last_location_lng) if incident.last_location_lng else None,
        "updated_at":    incident.last_location_at.isoformat() if incident.last_location_at else None,
        "created_at":    incident.created_at.isoformat()   if incident.created_at else None,
        "audio_url":     incident.audio_url,
        "emergency_phone": settings.EMERGENCY_PHONE,
    }


# ── Admin ─────────────────────────────────────────────────────────────────────

@admin_router.get("/incidents")
def list_incidents(db: Session = Depends(get_db)):
    incidents = (
        db.query(Incident)
        .order_by(Incident.created_at.desc())
        .limit(100)
        .all()
    )
    return {"incidents": [
        {
            "incident_id":    i.incident_id,
            "trip_id":        i.trip_id,
            "reporter_type":  i.reporter_type,
            "reporter_name":  i.reporter_name,
            "reporter_phone": i.reporter_phone,
            "lat":            float(i.lat)               if i.lat else None,
            "lng":            float(i.lng)               if i.lng else None,
            "last_location_lat": float(i.last_location_lat) if i.last_location_lat else None,
            "last_location_lng": float(i.last_location_lng) if i.last_location_lng else None,
            "last_location_at":  i.last_location_at.isoformat() if i.last_location_at else None,
            "notes":          i.notes,
            "status":         i.status,
            "escalated":      i.escalated,
            "audio_url":      i.audio_url,
            "tracking_url":   _tracking_url(i.incident_id),
            "created_at":     i.created_at.isoformat() if i.created_at else None,
        }
        for i in incidents
    ]}


@admin_router.post("/incidents/{incident_id}/resolve")
def resolve_incident(incident_id: str, db: Session = Depends(get_db)):
    incident = db.query(Incident).filter(Incident.incident_id == incident_id).first()
    if not incident:
        raise HTTPException(404, "Incidente no encontrado")
    incident.status = "resolved"
    db.commit()
    return {"success": True}
