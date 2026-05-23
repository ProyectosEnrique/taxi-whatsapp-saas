"""
================================================================================
PRODUCTS ROUTER - Menu Service
================================================================================
Endpoints para gestión de productos del menú
================================================================================
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import datetime
import logging

from ..database import get_db
from ..models import Product, Category
from ..schemas import (
    ProductCreate,
    ProductUpdate,
    ProductResponse,
    ProductResponseWithMeta,
    ProductMetaSync,
    MetaSyncStatusResponse,
    ProductForCatalog,
    ErrorResponse,
    PaginatedResponse
)

logger = logging.getLogger(__name__)

router = APIRouter()

# ==============================================================================
# GET ALL PRODUCTS
# ==============================================================================

@router.get(
    "",
    response_model=List[ProductResponse],
    summary="Obtener todos los productos",
    description="Retorna lista de productos con filtros opcionales"
)
async def get_products(
    skip: int = Query(default=0, ge=0, description="Registros a saltar"),
    limit: int = Query(default=100, ge=1, le=500, description="Límite de registros"),
    category_id: Optional[int] = Query(default=None, description="Filtrar por categoría"),
    available_only: bool = Query(default=False, description="Solo productos disponibles"),
    search: Optional[str] = Query(default=None, description="Buscar por nombre"),
    db: Session = Depends(get_db)
):
    """Obtener lista de productos con filtros"""

    logger.info(f"Fetching products: skip={skip}, limit={limit}, category_id={category_id}")

    # Query base
    query = db.query(Product)

    # Aplicar filtros
    if category_id:
        query = query.filter(Product.category_id == category_id)

    if available_only:
        query = query.filter(Product.is_available == True)

    if search:
        query = query.filter(Product.name.ilike(f"%{search}%"))

    # Paginación
    products = query.offset(skip).limit(limit).all()

    logger.info(f"Found {len(products)} products")

    return products


# ==============================================================================
# GET PRODUCT BY ID
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
    db: Session = Depends(get_db)
):
    """Obtener un producto específico por ID"""

    logger.info(f"Fetching product with ID: {product_id}")

    product = db.query(Product).filter(Product.id == product_id).first()

    if not product:
        logger.warning(f"Product {product_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID {product_id} not found"
        )

    return product


# ==============================================================================
# CREATE PRODUCT
# ==============================================================================

@router.post(
    "",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear nuevo producto",
    responses={
        400: {"model": ErrorResponse, "description": "Datos inválidos"}
    }
)
async def create_product(
    product: ProductCreate,
    db: Session = Depends(get_db)
):
    """Crear un nuevo producto en el menú"""

    logger.info(f"Creating product: {product.name}")

    # Verificar que la categoría existe si se proporciona
    if product.category_id:
        category = db.query(Category).filter(Category.id == product.category_id).first()
        if not category:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Category with ID {product.category_id} not found"
            )

    # Crear producto
    db_product = Product(**product.model_dump())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)

    logger.info(f"Product created successfully with ID: {db_product.id}")

    return db_product


# ==============================================================================
# UPDATE PRODUCT
# ==============================================================================

@router.put(
    "/{product_id}",
    response_model=ProductResponse,
    summary="Actualizar producto",
    responses={
        404: {"model": ErrorResponse, "description": "Producto no encontrado"}
    }
)
async def update_product(
    product_id: int,
    product_update: ProductUpdate,
    db: Session = Depends(get_db)
):
    """Actualizar un producto existente"""

    logger.info(f"Updating product ID: {product_id}")

    # Buscar producto
    db_product = db.query(Product).filter(Product.id == product_id).first()

    if not db_product:
        logger.warning(f"Product {product_id} not found for update")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID {product_id} not found"
        )

    # Verificar categoría si se está actualizando
    if product_update.category_id:
        category = db.query(Category).filter(Category.id == product_update.category_id).first()
        if not category:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Category with ID {product_update.category_id} not found"
            )

    # Actualizar solo campos proporcionados
    update_data = product_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_product, field, value)

    db.commit()
    db.refresh(db_product)

    logger.info(f"Product {product_id} updated successfully")

    return db_product


# ==============================================================================
# DELETE PRODUCT
# ==============================================================================

@router.delete(
    "/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar producto",
    responses={
        404: {"model": ErrorResponse, "description": "Producto no encontrado"}
    }
)
async def delete_product(
    product_id: int,
    db: Session = Depends(get_db)
):
    """Eliminar un producto del menú"""

    logger.info(f"Deleting product ID: {product_id}")

    db_product = db.query(Product).filter(Product.id == product_id).first()

    if not db_product:
        logger.warning(f"Product {product_id} not found for deletion")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID {product_id} not found"
        )

    db.delete(db_product)
    db.commit()

    logger.info(f"Product {product_id} deleted successfully")

    return None


# ==============================================================================
# TOGGLE AVAILABILITY
# ==============================================================================

@router.patch(
    "/{product_id}/availability",
    response_model=ProductResponse,
    summary="Cambiar disponibilidad del producto"
)
async def toggle_availability(
    product_id: int,
    is_available: bool = Query(..., description="Nueva disponibilidad"),
    db: Session = Depends(get_db)
):
    """Cambiar la disponibilidad de un producto"""

    logger.info(f"Toggling availability for product {product_id} to {is_available}")

    db_product = db.query(Product).filter(Product.id == product_id).first()

    if not db_product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID {product_id} not found"
        )

    db_product.is_available = is_available
    db.commit()
    db.refresh(db_product)

    logger.info(f"Product {product_id} availability updated to {is_available}")

    return db_product


# ==============================================================================
# CHECK AVAILABILITY (FOR VOICE AGENT)
# ==============================================================================

@router.get(
    "/check-availability",
    summary="Verificar disponibilidad de productos (para agente de voz)",
    description="Endpoint optimizado para el agente de ventas por voz"
)
async def check_availability(
    product_names: Optional[str] = Query(
        default=None,
        description="Nombres de productos separados por coma"
    ),
    db: Session = Depends(get_db)
):
    """
    Verificar disponibilidad de productos.

    Si se proporcionan nombres, busca esos productos especificos.
    Si no se proporcionan, retorna todos los productos no disponibles (agotados).

    Respuesta optimizada para el agente de voz:
    - available: lista de productos disponibles solicitados
    - unavailable: lista de productos no disponibles (agotados)
    - not_found: productos que no existen en el menu
    """

    logger.info(f"Check availability request: {product_names}")

    if product_names:
        # Buscar productos especificos
        names = [n.strip().lower() for n in product_names.split(",")]

        available = []
        unavailable = []
        not_found = []

        for name in names:
            product = db.query(Product).filter(
                Product.name.ilike(f"%{name}%")
            ).first()

            if not product:
                not_found.append(name)
            elif product.is_available:
                available.append({
                    "id": product.id,
                    "name": product.name,
                    "price": float(product.price) if product.price else None
                })
            else:
                unavailable.append({
                    "id": product.id,
                    "name": product.name,
                    "reason": "agotado"
                })

        return {
            "available": available,
            "unavailable": unavailable,
            "not_found": not_found,
            "message": _build_availability_message(available, unavailable, not_found)
        }

    else:
        # Retornar todos los productos agotados
        unavailable_products = db.query(Product).filter(
            Product.is_available == False
        ).all()

        return {
            "unavailable_count": len(unavailable_products),
            "unavailable": [
                {"id": p.id, "name": p.name}
                for p in unavailable_products
            ],
            "message": f"Hay {len(unavailable_products)} productos agotados" if unavailable_products else "Todos los productos estan disponibles"
        }


def _build_availability_message(available, unavailable, not_found):
    """Construir mensaje legible para el agente de voz"""
    parts = []

    if unavailable:
        names = ", ".join([p["name"] for p in unavailable])
        parts.append(f"Lo siento, {names} no esta disponible en este momento")

    if not_found:
        names = ", ".join(not_found)
        parts.append(f"No encontre {names} en el menu")

    if available and not unavailable and not not_found:
        return "Todos los productos solicitados estan disponibles"

    if available:
        names = ", ".join([p["name"] for p in available])
        parts.append(f"Si tenemos disponible: {names}")

    return ". ".join(parts) if parts else "Productos verificados"


# ==============================================================================
# META COMMERCE CATALOG ENDPOINTS
# ==============================================================================

@router.patch(
    "/{product_id}/meta",
    response_model=ProductResponseWithMeta,
    summary="Actualizar campos Meta del producto",
    description="Actualiza campos de sincronizacion con Meta Commerce Catalog"
)
async def update_product_meta(
    product_id: int,
    meta_update: ProductMetaSync,
    db: Session = Depends(get_db)
):
    """
    Actualizar campos de sincronizacion con Meta Commerce.

    Este endpoint es usado por el servicio de sincronizacion del catalogo
    para actualizar el estado de cada producto.
    """
    logger.info(f"Updating Meta fields for product {product_id}")

    db_product = db.query(Product).filter(Product.id == product_id).first()

    if not db_product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID {product_id} not found"
        )

    # Actualizar solo campos proporcionados
    update_data = meta_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_product, field, value)

    # Actualizar timestamp de sincronizacion
    if meta_update.meta_sync_status == "synced":
        db_product.meta_last_sync = datetime.utcnow()

    db.commit()
    db.refresh(db_product)

    logger.info(f"Product {product_id} Meta fields updated: {update_data}")

    return db_product


@router.get(
    "/by-retailer-id/{retailer_id}",
    response_model=ProductResponseWithMeta,
    summary="Obtener producto por retailer_id de Meta",
    responses={
        404: {"model": ErrorResponse, "description": "Producto no encontrado"}
    }
)
async def get_product_by_retailer_id(
    retailer_id: str,
    db: Session = Depends(get_db)
):
    """
    Obtener producto por su ID en el catalogo de Meta.

    Usado para resolver productos cuando el cliente usa el carrito nativo de WhatsApp.
    """
    logger.info(f"Fetching product by retailer_id: {retailer_id}")

    product = db.query(Product).filter(
        Product.product_retailer_id == retailer_id
    ).first()

    if not product:
        logger.warning(f"Product with retailer_id {retailer_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with retailer_id {retailer_id} not found"
        )

    return product


@router.post(
    "/sync-all-meta",
    summary="Disparar sincronizacion de todos los productos con Meta",
    description="Marca todos los productos como pendientes de sincronizacion"
)
async def trigger_meta_sync(
    force: bool = Query(default=False, description="Forzar re-sincronizacion de todos"),
    db: Session = Depends(get_db)
):
    """
    Dispara sincronizacion de productos con Meta Catalog.

    - Si force=False: Solo marca productos sin product_retailer_id como pendientes
    - Si force=True: Marca TODOS los productos como pendientes

    El servicio whatsapp-gateway debe escuchar este evento y realizar la sincronizacion.
    """
    logger.info(f"Triggering Meta sync (force={force})")

    if force:
        # Marcar todos como pendientes
        updated = db.query(Product).update({
            Product.meta_sync_status: "pending",
            Product.meta_sync_error: None
        })
    else:
        # Solo productos sin retailer_id
        updated = db.query(Product).filter(
            Product.product_retailer_id == None
        ).update({
            Product.meta_sync_status: "pending"
        })

    db.commit()

    logger.info(f"Marked {updated} products for Meta sync")

    return {
        "message": "Sync triggered",
        "products_marked": updated,
        "force": force
    }


@router.get(
    "/meta-sync-status",
    response_model=MetaSyncStatusResponse,
    summary="Ver estado de sincronizacion con Meta"
)
async def get_meta_sync_status(db: Session = Depends(get_db)):
    """
    Obtener estadisticas de sincronizacion con Meta Commerce.

    Retorna:
    - Conteo de productos por estado (pending, synced, error)
    - Lista de productos con errores recientes
    """
    logger.info("Fetching Meta sync status")

    # Estadisticas por estado
    stats_query = db.query(
        Product.meta_sync_status,
        func.count(Product.id)
    ).group_by(Product.meta_sync_status).all()

    stats = {status or "pending": count for status, count in stats_query}

    # Productos con errores recientes
    errors = db.query(Product).filter(
        Product.meta_sync_status == "error"
    ).order_by(Product.updated_at.desc()).limit(10).all()

    recent_errors = [
        {
            "id": p.id,
            "name": p.name,
            "retailer_id": p.product_retailer_id,
            "error": p.meta_sync_error,
            "updated_at": p.updated_at.isoformat() if p.updated_at else None
        }
        for p in errors
    ]

    return {
        "stats": stats,
        "recent_errors": recent_errors
    }


@router.get(
    "/for-catalog",
    response_model=List[ProductForCatalog],
    summary="Obtener productos formateados para catalogo Meta",
    description="Retorna productos con formato listo para sincronizar con Meta Commerce"
)
async def get_products_for_catalog(
    status_filter: Optional[str] = Query(
        default=None,
        description="Filtrar por estado: pending, synced, error"
    ),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """
    Obtener productos formateados para sincronizacion con Meta Catalog.

    Este endpoint es usado por el servicio de sincronizacion para obtener
    los productos que necesitan ser sincronizados.
    """
    logger.info(f"Fetching products for catalog sync (status={status_filter})")

    query = db.query(Product).filter(Product.is_available == True)

    if status_filter:
        query = query.filter(Product.meta_sync_status == status_filter)

    products = query.limit(limit).all()

    result = []
    for p in products:
        # Generar retailer_id si no existe
        retailer_id = p.product_retailer_id or f"product_{p.id}"

        result.append({
            "id": p.id,
            "product_retailer_id": retailer_id,
            "name": p.name[:100],  # Max 100 chars para Meta
            "description": (p.description or p.name)[:9999],  # Max 9999 chars
            "price": p.price,
            "currency": "MXN",
            "image_url": p.image_url,
            "is_available": p.is_available,
            "category_name": p.category.name if p.category else None
        })

    logger.info(f"Returning {len(result)} products for catalog sync")

    return result
