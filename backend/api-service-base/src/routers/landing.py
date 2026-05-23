"""
Landing pages para conductores — acceso vía QR.

GET  /u/{driver_code}     → HTML (perfil del conductor + botón WhatsApp)
GET  /u/{driver_code}/qr  → PNG  (código QR con la URL de la landing)
POST /api/v1/groups        → Crear grupo/flota
GET  /api/v1/groups        → Listar grupos
POST /api/v1/driver/{id}/assign-group → Asignar conductor a grupo
"""
import io
import secrets
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse, Response
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Driver, TaxiGroup
from ..config import settings

router = APIRouter()

_STARS = ["", "⭐", "⭐⭐", "⭐⭐⭐", "⭐⭐⭐⭐", "⭐⭐⭐⭐⭐"]


# ── HTML de landing ────────────────────────────────────────────────────────────

def _landing_html(driver: Driver) -> str:
    rating      = float(driver.rating or 5.0)
    stars       = _STARS[min(round(rating), 5)]
    online_cls  = "online" if driver.is_online else "offline"
    online_txt  = "● En línea" if driver.is_online else "○ No disponible"
    vehicle     = " ".join(filter(None, [
        driver.vehicle_brand, driver.vehicle_model,
        "·", driver.vehicle_color, str(driver.vehicle_year or ""),
    ])).strip(" ·")
    plates      = driver.vehicle_plates or "---"
    group_name  = driver.group.name if driver.group else settings.BUSINESS_NAME
    wa_number   = (driver.group.whatsapp_number if driver.group else None) or settings.WHATSAPP_NUMBER

    if wa_number:
        wa_clean = wa_number.replace("+", "").replace(" ", "")
        text     = f"Hola! Me conecto por el QR del taxi de {driver.name}. Código: [{driver.driver_code}]"
        wa_href  = f"https://wa.me/{wa_clean}?text={quote(text)}"
        first    = driver.name.split()[0]
        wa_btn   = f"""<a class="btn-wa" href="{wa_href}">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="white" style="vertical-align:middle;margin-right:8px">
              <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/>
            </svg>
            Pedir taxi con {first}
          </a>"""
    else:
        wa_btn = '<p style="color:#475569;font-size:.875rem;margin-top:1rem">Contacta al operador para solicitar un viaje</p>'

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1.0">
  <title>🚖 {driver.name} · Taxi</title>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
  <style>
    *{{box-sizing:border-box;margin:0;padding:0}}
    body{{font-family:'Inter',sans-serif;background:#0f172a;min-height:100vh;display:flex;align-items:center;justify-content:center;padding:1rem}}
    .card{{background:#1e293b;border-radius:1.5rem;padding:2rem;max-width:380px;width:100%;text-align:center;box-shadow:0 25px 50px rgba(0,0,0,.5)}}
    .avatar{{width:80px;height:80px;background:#334155;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:2.5rem;margin:0 auto 1rem}}
    .badge{{display:inline-block;padding:.25rem .75rem;border-radius:9999px;font-size:.75rem;font-weight:600;margin-bottom:.75rem}}
    .online{{background:#064e3b;color:#34d399}}.offline{{background:#1f2937;color:#9ca3af}}
    h1{{color:#f1f5f9;font-size:1.5rem;font-weight:700;margin-bottom:.25rem}}
    .group{{color:#64748b;font-size:.8rem;margin-bottom:.75rem}}
    .vehicle{{color:#94a3b8;font-size:.875rem;margin-bottom:.75rem}}
    .rating{{color:#fbbf24;font-size:1.1rem;margin-bottom:.75rem}}
    .plates{{display:inline-block;background:#0f172a;border:1px solid #334155;border-radius:.5rem;padding:.25rem .75rem;color:#e2e8f0;font-family:monospace;font-size:1rem;font-weight:700;letter-spacing:2px;margin-bottom:1.5rem}}
    .btn-wa{{display:block;background:#25D366;color:white;text-decoration:none;padding:1rem 1.5rem;border-radius:1rem;font-size:1rem;font-weight:700;transition:transform .15s,box-shadow .15s}}
    .btn-wa:hover{{transform:translateY(-2px);box-shadow:0 8px 25px rgba(37,211,102,.4)}}
    .footer{{color:#475569;font-size:.75rem;margin-top:1.5rem}}
  </style>
</head>
<body>
  <div class="card">
    <div class="avatar">🚖</div>
    <span class="badge {online_cls}">{online_txt}</span>
    <h1>{driver.name}</h1>
    <p class="group">{group_name}</p>
    <p class="vehicle">{vehicle}</p>
    <div class="rating">{stars} {rating:.1f}</div>
    <div class="plates">{plates}</div>
    {wa_btn}
    <p class="footer">Escanea el QR en el taxi para conectar</p>
  </div>
</body>
</html>"""


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/u/{driver_code}", response_class=HTMLResponse, include_in_schema=False)
def driver_landing(driver_code: str, db: Session = Depends(get_db)):
    driver = db.query(Driver).filter(Driver.driver_code == driver_code).first()
    if not driver or not driver.is_active:
        raise HTTPException(404, "Conductor no encontrado")
    return HTMLResponse(content=_landing_html(driver))


@router.get("/u/{driver_code}/qr", tags=["QR"])
def driver_qr(driver_code: str, db: Session = Depends(get_db)):
    """Devuelve imagen PNG del código QR para la landing del conductor."""
    driver = db.query(Driver).filter(Driver.driver_code == driver_code).first()
    if not driver or not driver.is_active:
        raise HTTPException(404, "Conductor no encontrado")
    try:
        import qrcode
    except ImportError:
        raise HTTPException(500, "qrcode not installed")

    url = f"{settings.PUBLIC_URL}/u/{driver_code}"
    qr  = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return Response(content=buf.read(), media_type="image/png",
                    headers={"Content-Disposition": f'inline; filename="{driver_code}-qr.png"'})


# ── Group management (sin schema, uso interno) ────────────────────────────────

@router.post("/api/v1/groups", include_in_schema=False)
def create_group(payload: dict, db: Session = Depends(get_db)):
    name   = (payload.get("name") or "").strip()
    number = (payload.get("whatsapp_number") or "").strip()
    if not name or not number:
        raise HTTPException(400, "name y whatsapp_number son requeridos")
    group = TaxiGroup(name=name, whatsapp_number=number)
    db.add(group)
    db.commit()
    db.refresh(group)
    return {"id": group.id, "name": group.name, "whatsapp_number": group.whatsapp_number}


@router.get("/api/v1/groups", include_in_schema=False)
def list_groups(db: Session = Depends(get_db)):
    groups = db.query(TaxiGroup).filter(TaxiGroup.is_active == True).all()
    return [{"id": g.id, "name": g.name, "whatsapp_number": g.whatsapp_number} for g in groups]


@router.post("/api/v1/driver/{driver_id}/assign-group", include_in_schema=False)
def assign_group(driver_id: int, payload: dict, db: Session = Depends(get_db)):
    driver = db.query(Driver).filter(Driver.id == driver_id).first()
    if not driver:
        raise HTTPException(404, "Conductor no encontrado")
    group_id = payload.get("group_id")
    if group_id and not db.query(TaxiGroup).filter(TaxiGroup.id == group_id).first():
        raise HTTPException(404, "Grupo no encontrado")
    driver.group_id = group_id
    if payload.get("driver_code"):
        driver.driver_code = payload["driver_code"]
    db.commit()
    return {"driver_id": driver.id, "group_id": driver.group_id, "driver_code": driver.driver_code}
