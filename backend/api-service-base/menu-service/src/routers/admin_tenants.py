"""
================================================================================
ADMIN TENANTS ROUTER - Gestión de Tenants
================================================================================
Endpoints de administración para crear y gestionar tenants (tiendas)
================================================================================
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import logging
import os
import uuid

from ..database import get_db
from ..models.tenant import Tenant
from ..models.user import User
from ..models.role import Role
from ..schemas.tenant import TenantCreate, TenantUpdate, TenantResponse
from ..auth.permissions import require_admin, require_super_admin, verify_tenant_admin

logger = logging.getLogger(__name__)

router = APIRouter()

# Directorio para logos de tenants
LOGO_DIR = "uploads/tenants/logos"
os.makedirs(LOGO_DIR, exist_ok=True)


# ==============================================================================
# CREATE TENANT (SUPER ADMIN ONLY)
# ==============================================================================

@router.post(
    "",
    response_model=TenantResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear nuevo tenant (Solo Super Admin)"
)
async def create_tenant(
    data: TenantCreate,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """
    Crear un nuevo tenant (tienda).

    Solo super administradores pueden crear tenants.
    """
    logger.info(f"Super admin {current_user.id} creando nuevo tenant: {data.tenant_id}")

    # Verificar que no exista el tenant_id
    existing = db.query(Tenant).filter(Tenant.tenant_id == data.tenant_id).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ya existe un tenant con ID '{data.tenant_id}'"
        )

    # Crear tenant
    new_tenant = Tenant(
        tenant_id=data.tenant_id,
        name=data.name,
        description=data.description,
        logo_url=data.logo_url,
        primary_color=data.primary_color,
        phone=data.phone,
        email=data.email,
        address=data.address,
        settings=data.settings,
        is_active=data.is_active
    )

    db.add(new_tenant)
    db.commit()
    db.refresh(new_tenant)

    logger.info(f"Tenant creado exitosamente: {new_tenant.tenant_id}")

    return new_tenant


# ==============================================================================
# UPDATE TENANT
# ==============================================================================

@router.put(
    "/{tenant_id}",
    response_model=TenantResponse,
    summary="Actualizar tenant"
)
async def update_tenant(
    tenant_id: str,
    data: TenantUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Actualizar información de un tenant.

    - Super admin puede actualizar cualquier tenant
    - Admin solo puede actualizar su propio tenant
    """
    logger.info(f"Usuario {current_user.id} actualizando tenant: {tenant_id}")

    # Verificar permisos
    verify_tenant_admin(current_user, tenant_id)

    # Buscar tenant
    tenant = db.query(Tenant).filter(Tenant.tenant_id == tenant_id).first()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant '{tenant_id}' no encontrado"
        )

    # Actualizar campos
    update_data = data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(tenant, field, value)

    db.commit()
    db.refresh(tenant)

    logger.info(f"Tenant {tenant_id} actualizado exitosamente")

    return tenant


# ==============================================================================
# UPDATE TENANT SETTINGS
# ==============================================================================

@router.put(
    "/{tenant_id}/settings",
    response_model=TenantResponse,
    summary="Actualizar configuración del tenant"
)
async def update_tenant_settings(
    tenant_id: str,
    settings: dict,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Actualizar la configuración (settings) del tenant.

    Settings pueden incluir:
    - business_hours: Horarios de operación
    - delivery_zones: Zonas de entrega
    - payment_methods: Métodos de pago habilitados
    - etc.
    """
    logger.info(f"Actualizando settings del tenant: {tenant_id}")

    # Verificar permisos
    verify_tenant_admin(current_user, tenant_id)

    # Buscar tenant
    tenant = db.query(Tenant).filter(Tenant.tenant_id == tenant_id).first()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant '{tenant_id}' no encontrado"
        )

    # Actualizar settings (merge con existentes)
    current_settings = tenant.settings or {}
    current_settings.update(settings)
    tenant.settings = current_settings

    db.commit()
    db.refresh(tenant)

    logger.info(f"Settings del tenant {tenant_id} actualizados")

    return tenant


# ==============================================================================
# UPLOAD TENANT LOGO
# ==============================================================================

@router.post(
    "/{tenant_id}/logo",
    summary="Subir logo del tenant"
)
async def upload_tenant_logo(
    tenant_id: str,
    file: UploadFile = File(...),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Subir logo del tenant.

    Formatos permitidos: PNG, JPG, JPEG
    Tamaño máximo: 2MB
    """
    logger.info(f"Subiendo logo para tenant: {tenant_id}")

    # Verificar permisos
    verify_tenant_admin(current_user, tenant_id)

    # Buscar tenant
    tenant = db.query(Tenant).filter(Tenant.tenant_id == tenant_id).first()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant '{tenant_id}' no encontrado"
        )

    # Validar tipo de archivo
    allowed_types = ["image/png", "image/jpg", "image/jpeg"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tipo de archivo no permitido. Use PNG o JPG"
        )

    # Validar tamaño (2MB)
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)

    if file_size > 2 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo es demasiado grande. Máximo 2MB"
        )

    # Generar nombre único
    file_extension = file.filename.split(".")[-1]
    unique_filename = f"{tenant_id}_{uuid.uuid4()}.{file_extension}"
    file_path = os.path.join(LOGO_DIR, unique_filename)

    # Guardar archivo
    try:
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)

        # Actualizar URL en tenant
        logo_url = f"/uploads/tenants/logos/{unique_filename}"
        tenant.logo_url = logo_url

        db.commit()
        db.refresh(tenant)

        logger.info(f"Logo subido exitosamente: {file_path}")

        return {
            "success": True,
            "logo_url": logo_url,
            "message": "Logo subido exitosamente"
        }

    except Exception as e:
        logger.error(f"Error al subir logo: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al guardar el logo"
        )


# ==============================================================================
# LIST ALL TENANTS (SUPER ADMIN ONLY)
# ==============================================================================

@router.get(
    "",
    response_model=List[TenantResponse],
    summary="Listar todos los tenants (Solo Super Admin)"
)
async def list_all_tenants(
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    is_active: Optional[bool] = Query(default=None)
):
    """
    Listar todos los tenants del sistema.

    Solo super administradores pueden ver todos los tenants.
    """
    logger.info(f"Listando tenants (super admin {current_user.id})")

    query = db.query(Tenant)

    if is_active is not None:
        query = query.filter(Tenant.is_active == is_active)

    tenants = query.order_by(Tenant.created_at.desc()).offset(skip).limit(limit).all()

    logger.info(f"Encontrados {len(tenants)} tenants")

    return tenants


# ==============================================================================
# DELETE TENANT (SOFT DELETE - SUPER ADMIN ONLY)
# ==============================================================================

@router.delete(
    "/{tenant_id}",
    summary="Desactivar tenant (Solo Super Admin)"
)
async def deactivate_tenant(
    tenant_id: str,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """
    Desactivar un tenant (soft delete).

    Solo super administradores pueden desactivar tenants.
    """
    logger.info(f"Desactivando tenant: {tenant_id}")

    tenant = db.query(Tenant).filter(Tenant.tenant_id == tenant_id).first()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant '{tenant_id}' no encontrado"
        )

    tenant.is_active = False
    db.commit()

    logger.info(f"Tenant {tenant_id} desactivado")

    return {
        "success": True,
        "message": f"Tenant '{tenant_id}' desactivado exitosamente"
    }


# ==============================================================================
# ACTIVATE TENANT (SUPER ADMIN ONLY)
# ==============================================================================

@router.post(
    "/{tenant_id}/activate",
    summary="Activar tenant (Solo Super Admin)"
)
async def activate_tenant(
    tenant_id: str,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """
    Activar un tenant desactivado.

    Solo super administradores pueden activar tenants.
    """
    logger.info(f"Activando tenant: {tenant_id}")

    tenant = db.query(Tenant).filter(Tenant.tenant_id == tenant_id).first()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant '{tenant_id}' no encontrado"
        )

    tenant.is_active = True
    db.commit()

    logger.info(f"Tenant {tenant_id} activado")

    return {
        "success": True,
        "message": f"Tenant '{tenant_id}' activado exitosamente"
    }
