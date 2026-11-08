"""SOS desde fuera de las apps con cuenta (ver services/sos.py).

  POST /api/v1/customer/rides/{ride_id}/sos   — botón de /seguimiento (público, por link del viaje)
  POST /api/v1/sos/whatsapp                   — el gateway, al recibir "SOS"/"auxilio" (clave interna)
  GET/POST/PUT/DELETE /api/v1/admin/base-managers — encargados de cada base (admin)
"""
import logging

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..models import BaseManager, TaxiGroup, Trip
from ..services import sos
from .admin import _admin_auth

logger = logging.getLogger(__name__)

router = APIRouter(tags=["sos"])
admin_router = APIRouter(prefix="/api/v1/admin", tags=["sos"], dependencies=[Depends(_admin_auth)])


class _Where(BaseModel):
    lat: float | None = None
    lng: float | None = None


@router.post("/api/v1/customer/rides/{ride_id}/sos")
async def sos_from_tracking(ride_id: str, body: _Where, db: Session = Depends(get_db)):
    """Lo activa el pasajero desde su página de seguimiento. Solo mientras el
    viaje está activo o terminó hace poco: el link no sirve para alertas viejas."""
    trip = db.query(Trip).filter(Trip.trip_id == ride_id).first()
    if not trip:
        raise HTTPException(404, "Viaje no encontrado")
    if not sos.trip_is_recent(trip):
        raise HTTPException(400, f"Este viaje ya terminó. Si estás en peligro, llama al {settings.EMERGENCY_PHONE}.")
    inc, _ = await sos.raise_sos(db, reporter_type="customer", phone=trip.customer_phone,
                                 name=trip.customer_name, trip=trip, lat=body.lat, lng=body.lng,
                                 source="seguimiento")
    return {"success": True, "incident_id": inc.incident_id,
            "emergency_phone": settings.EMERGENCY_PHONE,
            "message": "Alerta enviada. El encargado de la base te va a contactar."}


class _WhatsAppSos(BaseModel):
    phone: str = Field(min_length=8, max_length=30)
    name: str | None = Field(None, max_length=150)


@router.post("/api/v1/sos/whatsapp")
async def sos_from_whatsapp(body: _WhatsAppSos, db: Session = Depends(get_db),
                            x_taxi_internal_key: str = Header("")):
    # Sin clave configurada no se acepta: cualquiera podría disparar alertas a nombre de otro
    if not settings.WHATSAPP_SECRET or x_taxi_internal_key != settings.WHATSAPP_SECRET:
        raise HTTPException(403, "No autorizado")
    phone = body.phone.strip()
    trip = sos.trip_for(db, phone, "customer")
    inc, new = await sos.raise_sos(db, reporter_type="customer", phone=phone,
                                   name=(trip.customer_name if trip else None) or body.name,
                                   trip=trip, source="whatsapp")
    return {"reply": sos.reporter_reply(inc, trip, for_whatsapp=True), "incident_id": inc.incident_id,
            "new": new}


# ── Encargados de base (admin) ────────────────────────────────────────────────

class _ManagerIn(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    phone: str = Field(min_length=8, max_length=30)
    group_id: int | None = None
    priority: int = Field(1, ge=1, le=2)
    is_active: bool = True


def _manager_dict(m: BaseManager) -> dict:
    return {"id": m.id, "name": m.name, "phone": m.phone, "group_id": m.group_id,
            "priority": m.priority, "is_active": m.is_active,
            "telegram_linked": bool(m.telegram_chat_id)}


@admin_router.get("/base-managers")
def list_managers(db: Session = Depends(get_db)):
    groups = {g.id: g.name for g in db.query(TaxiGroup).all()}
    return [{**_manager_dict(m), "group": groups.get(m.group_id, "")}
            for m in db.query(BaseManager).order_by(BaseManager.group_id, BaseManager.priority).all()]


@admin_router.post("/base-managers")
def create_manager(body: _ManagerIn, db: Session = Depends(get_db)):
    if body.group_id and not db.get(TaxiGroup, body.group_id):
        raise HTTPException(404, "Base no encontrada")
    if db.query(BaseManager).filter(BaseManager.phone == body.phone.strip()).first():
        raise HTTPException(409, "Ya hay un encargado con ese teléfono")
    m = BaseManager(name=body.name.strip(), phone=body.phone.strip(), group_id=body.group_id,
                    priority=body.priority, is_active=body.is_active)
    db.add(m)
    db.commit()
    db.refresh(m)
    return {"success": True, "manager": _manager_dict(m),
            "next": f"Que abra el bot de Telegram y escriba: /encargado {m.phone}"}


@admin_router.put("/base-managers/{manager_id}")
def update_manager(manager_id: int, body: _ManagerIn, db: Session = Depends(get_db)):
    m = db.get(BaseManager, manager_id)
    if not m:
        raise HTTPException(404, "Encargado no encontrado")
    if body.phone.strip() != m.phone:
        m.telegram_chat_id = None   # otro teléfono → que vuelva a vincularse
    m.name, m.phone, m.group_id = body.name.strip(), body.phone.strip(), body.group_id
    m.priority, m.is_active = body.priority, body.is_active
    db.commit()
    return {"success": True, "manager": _manager_dict(m)}


@admin_router.delete("/base-managers/{manager_id}")
def delete_manager(manager_id: int, db: Session = Depends(get_db)):
    m = db.get(BaseManager, manager_id)
    if not m:
        raise HTTPException(404, "Encargado no encontrado")
    db.delete(m)
    db.commit()
    return {"success": True}
