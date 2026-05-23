"""
================================================================================
TENANTS ROUTER - Configuración de Tiendas
================================================================================
Endpoints para obtener información y configuración de tenants
================================================================================
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import logging

from ..database import get_db
from ..models.tenant import Tenant
from ..models.product import Product
from ..schemas.tenant import TenantResponse, TenantSettingsResponse
from ..schemas.product import ProductResponse

logger = logging.getLogger(__name__)

router = APIRouter()


# ==============================================================================
# ENDPOINTS
# ==============================================================================

@router.get(
    "/{tenant_id}",
    response_model=TenantResponse,
    summary="Obtener información del tenant"
)
async def get_tenant(
    tenant_id: str,
    db: Session = Depends(get_db)
):
    """
    Obtener información completa del tenant (tienda).

    Incluye: nombre, logo, colores, contacto, dirección, settings, etc.
    """
    logger.info(f"Consultando tenant: {tenant_id}")

    tenant = db.query(Tenant).filter(Tenant.tenant_id == tenant_id).first()

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant '{tenant_id}' no encontrado"
        )

    if not tenant.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Este tenant no está activo"
        )

    return TenantResponse.from_orm(tenant)


@router.get(
    "/{tenant_id}/settings",
    response_model=TenantSettingsResponse,
    summary="Obtener configuración del tenant"
)
async def get_tenant_settings(
    tenant_id: str,
    db: Session = Depends(get_db)
):
    """
    Obtener solo la configuración operativa del tenant.

    Incluye: horarios, zonas de entrega, métodos de pago, monto mínimo, etc.
    """
    logger.info(f"Consultando settings de tenant: {tenant_id}")

    tenant = db.query(Tenant).filter(Tenant.tenant_id == tenant_id).first()

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant '{tenant_id}' no encontrado"
        )

    # Extraer configuraciones específicas
    settings = tenant.settings or {}

    return TenantSettingsResponse(
        tenant_id=tenant.tenant_id,
        name=tenant.name,
        settings=settings,
        business_hours=settings.get("business_hours"),
        delivery_zones=settings.get("delivery_zones"),
        payment_methods=settings.get("payment_methods", ["cash", "card"]),
        min_order_amount=settings.get("min_order_amount", 100.0)
    )


@router.get(
    "/{tenant_id}/products",
    response_model=List[ProductResponse],
    summary="Obtener productos del tenant"
)
async def get_tenant_products(
    tenant_id: str,
    category: Optional[str] = Query(None, description="Filtrar por categoría"),
    available_only: bool = Query(True, description="Solo productos disponibles"),
    search: Optional[str] = Query(None, description="Buscar por nombre"),
    db: Session = Depends(get_db)
):
    """
    Obtener catálogo de productos del tenant.

    Filtros disponibles:
    - category: Filtrar por categoría específica
    - available_only: Solo productos disponibles (default: true)
    - search: Buscar por nombre del producto
    """
    logger.info(f"Consultando productos de tenant: {tenant_id}")

    # Verificar que el tenant existe
    tenant = db.query(Tenant).filter(Tenant.tenant_id == tenant_id).first()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant '{tenant_id}' no encontrado"
        )

    # Query base
    query = db.query(Product).filter(Product.tenant_id == tenant_id)

    # Aplicar filtros
    if category:
        query = query.filter(Product.category == category)

    if available_only:
        query = query.filter(Product.is_available == True)

    if search:
        query = query.filter(Product.name.ilike(f"%{search}%"))

    # Ordenar por nombre
    products = query.order_by(Product.name).all()

    logger.info(f"Encontrados {len(products)} productos")

    return [ProductResponse.from_orm(p) for p in products]
