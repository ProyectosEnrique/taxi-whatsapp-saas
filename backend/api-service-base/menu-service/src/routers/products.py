"""
================================================================================
PRODUCTS ROUTER - Menu Service (PUBLIC)
================================================================================
Endpoints PÚBLICOS para consultar productos del menú
NOTA: Para crear/editar productos, usar /api/v1/admin/products
================================================================================
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import logging

from ..database import get_db
from ..models import Product, Category
from ..schemas import ProductResponse, ErrorResponse

logger = logging.getLogger(__name__)

router = APIRouter()


# ==============================================================================
# GET ALL PRODUCTS (FILTERED BY TENANT)
# ==============================================================================

@router.get(
    "",
    response_model=List[ProductResponse],
    summary="Obtener productos del tenant",
    description="Retorna lista de productos disponibles para un tenant específico"
)
async def get_products(
    tenant_id: str = Query(..., description="ID del tenant"),
    skip: int = Query(default=0, ge=0, description="Registros a saltar"),
    limit: int = Query(default=100, ge=1, le=500, description="Límite de registros"),
    category_id: Optional[int] = Query(default=None, description="Filtrar por categoría"),
    available_only: bool = Query(default=True, description="Solo productos disponibles"),
    search: Optional[str] = Query(default=None, description="Buscar por nombre"),
    db: Session = Depends(get_db)
):
    """
    Obtener lista de productos de un tenant específico.

    IMPORTANTE: Este endpoint requiere tenant_id para asegurar aislamiento de datos.
    """

    logger.info(f"Fetching products for tenant: {tenant_id}")

    # Query base - SIEMPRE filtrar por tenant
    query = db.query(Product).filter(Product.tenant_id == tenant_id)

    # Aplicar filtros adicionales
    if category_id:
        query = query.filter(Product.category_id == category_id)

    if available_only:
        query = query.filter(Product.is_available == True)

    if search:
        query = query.filter(Product.name.ilike(f"%{search}%"))

    # Ordenar y paginar
    products = query.order_by(Product.name.asc()).offset(skip).limit(limit).all()

    logger.info(f"Found {len(products)} products for tenant {tenant_id}")

    return products


# ==============================================================================
# GET PRODUCT BY ID (WITH TENANT VERIFICATION)
# ==============================================================================

@router.get(
    "/{product_id}",
    response_model=ProductResponse,
    summary="Obtener producto por ID",
    responses={
        404: {"model": ErrorResponse, "description": "Producto no encontrado"}
    }
)
async def get_product(
    product_id: int,
    tenant_id: str = Query(..., description="ID del tenant"),
    db: Session = Depends(get_db)
):
    """
    Obtener un producto específico por ID.

    Verifica que el producto pertenezca al tenant especificado.
    """

    logger.info(f"Fetching product {product_id} for tenant {tenant_id}")

    product = db.query(Product).filter(
        Product.id == product_id,
        Product.tenant_id == tenant_id
    ).first()

    if not product:
        logger.warning(f"Product {product_id} not found for tenant {tenant_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID {product_id} not found"
        )

    return product


# ==============================================================================
# GET PRODUCTS BY CATEGORY
# ==============================================================================

@router.get(
    "/category/{category_id}/products",
    response_model=List[ProductResponse],
    summary="Obtener productos de una categoría"
)
async def get_products_by_category(
    category_id: int,
    tenant_id: str = Query(..., description="ID del tenant"),
    available_only: bool = Query(default=True, description="Solo disponibles"),
    db: Session = Depends(get_db)
):
    """
    Obtener todos los productos de una categoría específica.

    Verifica que la categoría pertenezca al tenant.
    """

    logger.info(f"Fetching products for category {category_id}, tenant {tenant_id}")

    # Verificar que la categoría existe y pertenece al tenant
    category = db.query(Category).filter(
        Category.id == category_id,
        Category.tenant_id == tenant_id
    ).first()

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Categoría no encontrada"
        )

    # Obtener productos
    query = db.query(Product).filter(
        Product.category_id == category_id,
        Product.tenant_id == tenant_id
    )

    if available_only:
        query = query.filter(Product.is_available == True)

    products = query.order_by(Product.name.asc()).all()

    return products


# ==============================================================================
# SEARCH PRODUCTS
# ==============================================================================

@router.get(
    "/search/query",
    response_model=List[ProductResponse],
    summary="Buscar productos"
)
async def search_products(
    q: str = Query(..., min_length=2, description="Término de búsqueda"),
    tenant_id: str = Query(..., description="ID del tenant"),
    available_only: bool = Query(default=True),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Buscar productos por nombre o descripción.

    Filtrado automático por tenant.
    """

    logger.info(f"Searching products: '{q}' for tenant {tenant_id}")

    query = db.query(Product).filter(
        Product.tenant_id == tenant_id
    ).filter(
        (Product.name.ilike(f"%{q}%")) |
        (Product.description.ilike(f"%{q}%"))
    )

    if available_only:
        query = query.filter(Product.is_available == True)

    products = query.limit(limit).all()

    logger.info(f"Found {len(products)} products matching '{q}'")

    return products


# ==============================================================================
# GET FEATURED/POPULAR PRODUCTS
# ==============================================================================

@router.get(
    "/featured/popular",
    response_model=List[ProductResponse],
    summary="Obtener productos populares"
)
async def get_popular_products(
    tenant_id: str = Query(..., description="ID del tenant"),
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """
    Obtener productos más populares del tenant.

    Ordenados por popularidad descendente.
    """

    logger.info(f"Fetching popular products for tenant {tenant_id}")

    products = db.query(Product).filter(
        Product.tenant_id == tenant_id,
        Product.is_available == True
    ).order_by(
        Product.popularity.desc(),
        Product.name.asc()
    ).limit(limit).all()

    return products


# ==============================================================================
# NOTAS IMPORTANTES
# ==============================================================================

"""
⚠️ SEGURIDAD:

1. Este router es SOLO para lectura (GET)
2. Todos los endpoints REQUIEREN tenant_id
3. Todos los queries filtran por tenant_id
4. No hay endpoints de CREATE/UPDATE/DELETE aquí

Para gestión de productos (crear, editar, eliminar):
→ Usar /api/v1/admin/products (requiere autenticación y permisos de admin)

"""
