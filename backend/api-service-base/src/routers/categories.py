"""
================================================================================
CATEGORIES ROUTER - Menu Service
================================================================================
Endpoints para gestión de categorías de productos
================================================================================
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List
import logging

from ..database import get_db
from ..models import Category
from ..schemas import (
    CategoryCreate,
    CategoryUpdate,
    CategoryResponse,
    CategoryWithProducts,
    ErrorResponse
)

logger = logging.getLogger(__name__)

router = APIRouter()

# ==============================================================================
# GET ALL CATEGORIES
# ==============================================================================

@router.get(
    "",
    response_model=List[CategoryResponse],
    summary="Obtener todas las categorías",
    description="Retorna lista de categorías ordenadas por display_order"
)
async def get_categories(
    active_only: bool = Query(default=False, description="Solo categorías activas"),
    db: Session = Depends(get_db)
):
    """Obtener lista de categorías"""

    logger.info(f"Fetching categories: active_only={active_only}")

    query = db.query(Category)

    if active_only:
        query = query.filter(Category.is_active == True)

    categories = query.order_by(Category.display_order).all()

    logger.info(f"Found {len(categories)} categories")

    return categories


# ==============================================================================
# GET CATEGORY BY ID
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
    db: Session = Depends(get_db)
):
    """Obtener una categoría específica por ID"""

    logger.info(f"Fetching category with ID: {category_id}")

    category = db.query(Category).filter(Category.id == category_id).first()

    if not category:
        logger.warning(f"Category {category_id} not found")
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
    available_only: bool = Query(default=False, description="Solo productos disponibles"),
    db: Session = Depends(get_db)
):
    """Obtener categoría con todos sus productos"""

    logger.info(f"Fetching category {category_id} with products")

    category = db.query(Category).filter(Category.id == category_id).first()

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
# CREATE CATEGORY
# ==============================================================================

@router.post(
    "",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear nueva categoría",
    responses={
        400: {"model": ErrorResponse, "description": "Categoría ya existe"}
    }
)
async def create_category(
    category: CategoryCreate,
    db: Session = Depends(get_db)
):
    """Crear una nueva categoría"""

    logger.info(f"Creating category: {category.name}")

    # Verificar que no exista categoría con el mismo nombre
    existing = db.query(Category).filter(Category.name == category.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Category with name '{category.name}' already exists"
        )

    # Crear categoría
    db_category = Category(**category.model_dump())
    db.add(db_category)
    db.commit()
    db.refresh(db_category)

    logger.info(f"Category created successfully with ID: {db_category.id}")

    return db_category


# ==============================================================================
# UPDATE CATEGORY
# ==============================================================================

@router.put(
    "/{category_id}",
    response_model=CategoryResponse,
    summary="Actualizar categoría",
    responses={
        404: {"model": ErrorResponse, "description": "Categoría no encontrada"}
    }
)
async def update_category(
    category_id: int,
    category_update: CategoryUpdate,
    db: Session = Depends(get_db)
):
    """Actualizar una categoría existente"""

    logger.info(f"Updating category ID: {category_id}")

    # Buscar categoría
    db_category = db.query(Category).filter(Category.id == category_id).first()

    if not db_category:
        logger.warning(f"Category {category_id} not found for update")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Category with ID {category_id} not found"
        )

    # Verificar nombre único si se está actualizando
    if category_update.name:
        existing = db.query(Category).filter(
            Category.name == category_update.name,
            Category.id != category_id
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Category with name '{category_update.name}' already exists"
            )

    # Actualizar solo campos proporcionados
    update_data = category_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_category, field, value)

    db.commit()
    db.refresh(db_category)

    logger.info(f"Category {category_id} updated successfully")

    return db_category


# ==============================================================================
# DELETE CATEGORY
# ==============================================================================

@router.delete(
    "/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar categoría",
    responses={
        404: {"model": ErrorResponse, "description": "Categoría no encontrada"}
    }
)
async def delete_category(
    category_id: int,
    db: Session = Depends(get_db)
):
    """Eliminar una categoría"""

    logger.info(f"Deleting category ID: {category_id}")

    db_category = db.query(Category).filter(Category.id == category_id).first()

    if not db_category:
        logger.warning(f"Category {category_id} not found for deletion")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Category with ID {category_id} not found"
        )

    db.delete(db_category)
    db.commit()

    logger.info(f"Category {category_id} deleted successfully")

    return None
