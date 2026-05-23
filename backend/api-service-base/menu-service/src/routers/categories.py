"""
================================================================================
CATEGORIES ROUTER - Menu Service (PUBLIC)
================================================================================
Endpoints PÚBLICOS para consultar categorías de productos
NOTA: Para crear/editar categorías, usar /api/v1/admin/categories
================================================================================
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List
import logging

from ..database import get_db
from ..models import Category
from ..schemas import CategoryResponse, CategoryWithProducts, ErrorResponse

logger = logging.getLogger(__name__)

router = APIRouter()


# ==============================================================================
# GET ALL CATEGORIES (FILTERED BY TENANT)
# ==============================================================================

@router.get(
    "",
    response_model=List[CategoryResponse],
    summary="Obtener categorías del tenant",
    description="Retorna lista de categorías ordenadas por display_order"
)
async def get_categories(
    tenant_id: str = Query(..., description="ID del tenant"),
    active_only: bool = Query(default=True, description="Solo categorías activas"),
    db: Session = Depends(get_db)
):
    """
    Obtener lista de categorías de un tenant específico.

    IMPORTANTE: Requiere tenant_id para asegurar aislamiento de datos.
    """

    logger.info(f"Fetching categories for tenant: {tenant_id}")

    # Query base - SIEMPRE filtrar por tenant
    query = db.query(Category).filter(Category.tenant_id == tenant_id)

    if active_only:
        query = query.filter(Category.is_active == True)

    categories = query.order_by(Category.display_order.asc(), Category.name.asc()).all()

    logger.info(f"Found {len(categories)} categories for tenant {tenant_id}")

    return categories


# ==============================================================================
# GET CATEGORY BY ID (WITH TENANT VERIFICATION)
# ==============================================================================

@router.get(
    "/{category_id}",
    response_model=CategoryResponse,
    summary="Obtener categoría por ID",
    responses={
        404: {"model": ErrorResponse, "description": "Categoría no encontrada"}
    }
)
async def get_category(
    category_id: int,
    tenant_id: str = Query(..., description="ID del tenant"),
    db: Session = Depends(get_db)
):
    """
    Obtener una categoría específica por ID.

    Verifica que la categoría pertenezca al tenant especificado.
    """

    logger.info(f"Fetching category {category_id} for tenant {tenant_id}")

    category = db.query(Category).filter(
        Category.id == category_id,
        Category.tenant_id == tenant_id
    ).first()

    if not category:
        logger.warning(f"Category {category_id} not found for tenant {tenant_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Category with ID {category_id} not found"
        )

    return category


# ==============================================================================
# GET CATEGORY WITH PRODUCTS
# ==============================================================================

@router.get(
    "/{category_id}/products",
    response_model=CategoryWithProducts,
    summary="Obtener categoría con sus productos",
    responses={
        404: {"model": ErrorResponse, "description": "Categoría no encontrada"}
    }
)
async def get_category_with_products(
    category_id: int,
    tenant_id: str = Query(..., description="ID del tenant"),
    available_only: bool = Query(default=True, description="Solo productos disponibles"),
    db: Session = Depends(get_db)
):
    """
    Obtener categoría con todos sus productos.

    Verifica que la categoría pertenezca al tenant.
    """

    logger.info(f"Fetching category {category_id} with products for tenant {tenant_id}")

    category = db.query(Category).filter(
        Category.id == category_id,
        Category.tenant_id == tenant_id
    ).first()

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Category with ID {category_id} not found"
        )

    # Filtrar productos si se requiere solo disponibles
    if available_only:
        category.products = [p for p in category.products if p.is_available]

    return category


# ==============================================================================
# NOTAS IMPORTANTES
# ==============================================================================

"""
⚠️ SEGURIDAD:

1. Este router es SOLO para lectura (GET)
2. Todos los endpoints REQUIEREN tenant_id
3. Todos los queries filtran por tenant_id
4. No hay endpoints de CREATE/UPDATE/DELETE aquí

Para gestión de categorías (crear, editar, eliminar):
→ Usar /api/v1/admin/categories (requiere autenticación y permisos de admin)

"""
