# ============================================================================
# CATEGORIES ROUTER - CRUD Endpoints para Categorías
# ============================================================================

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import uuid
from slugify import slugify

from src.database import get_db
from src.orm_models import CategoryORM, RestaurantORM, ProductORM
from src.models_multitenant import (
    Category, CategoryCreate, CategoryUpdate,
    SuccessResponse
)
from src.auth import check_restaurant_access, allow_manager

router = APIRouter(prefix="/api/v1/restaurants/{restaurant_id}/categories", tags=["Categories"])


# ============================================================================
# CREATE CATEGORY
# ============================================================================

@router.post("", response_model=Category, status_code=status.HTTP_201_CREATED)
async def create_category(
    restaurant_id: str,
    category_data: CategoryCreate,
    restaurant: RestaurantORM = Depends(check_restaurant_access),
    current_user = Depends(allow_manager),
    db: Session = Depends(get_db)
):
    """
    Crear nueva categoría.

    Permisos: owner, manager, super_admin
    """
    # Generar IDs
    category_id = f"cat_{uuid.uuid4().hex[:12]}"
    slug = slugify(category_data.name)

    # Crear categoría
    category = CategoryORM(
        category_id=category_id,
        restaurant_id=restaurant_id,
        slug=slug,
        **category_data.dict()
    )

    db.add(category)
    db.commit()
    db.refresh(category)

    return Category.from_orm(category)


# ============================================================================
# GET ALL CATEGORIES
# ============================================================================

@router.get("", response_model=List[Category])
async def get_categories(
    restaurant_id: str,
    is_active: bool = None,
    restaurant: RestaurantORM = Depends(check_restaurant_access),
    db: Session = Depends(get_db)
):
    """
    Listar todas las categorías del restaurante.

    Filtro opcional:
    - is_active: Solo categorías activas
    """
    query = db.query(CategoryORM).filter(
        CategoryORM.restaurant_id == restaurant_id
    )

    if is_active is not None:
        query = query.filter(CategoryORM.is_active == is_active)

    categories = query.order_by(CategoryORM.display_order).all()

    return [Category.from_orm(c) for c in categories]


# ============================================================================
# GET CATEGORY BY ID
# ============================================================================

@router.get("/{category_id}", response_model=Category)
async def get_category(
    restaurant_id: str,
    category_id: str,
    restaurant: RestaurantORM = Depends(check_restaurant_access),
    db: Session = Depends(get_db)
):
    """
    Obtener detalles de una categoría específica.
    """
    category = db.query(CategoryORM).filter(
        CategoryORM.restaurant_id == restaurant_id,
        CategoryORM.category_id == category_id
    ).first()

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )

    return Category.from_orm(category)


# ============================================================================
# UPDATE CATEGORY
# ============================================================================

@router.patch("/{category_id}", response_model=Category)
async def update_category(
    restaurant_id: str,
    category_id: str,
    category_update: CategoryUpdate,
    restaurant: RestaurantORM = Depends(check_restaurant_access),
    current_user = Depends(allow_manager),
    db: Session = Depends(get_db)
):
    """
    Actualizar categoría.

    Permisos: owner, manager, super_admin
    """
    category = db.query(CategoryORM).filter(
        CategoryORM.restaurant_id == restaurant_id,
        CategoryORM.category_id == category_id
    ).first()

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )

    # Actualizar campos
    update_data = category_update.dict(exclude_unset=True)

    # Si cambia el nombre, actualizar slug
    if "name" in update_data and update_data["name"] != category.name:
        update_data["slug"] = slugify(update_data["name"])

    for field, value in update_data.items():
        if hasattr(category, field):
            setattr(category, field, value)

    db.commit()
    db.refresh(category)

    return Category.from_orm(category)


# ============================================================================
# DELETE CATEGORY
# ============================================================================

@router.delete("/{category_id}", response_model=SuccessResponse)
async def delete_category(
    restaurant_id: str,
    category_id: str,
    restaurant: RestaurantORM = Depends(check_restaurant_access),
    current_user = Depends(allow_manager),
    db: Session = Depends(get_db)
):
    """
    Eliminar categoría.

    Los productos asociados quedarán sin categoría (category_id = NULL).

    Permisos: owner, manager, super_admin
    """
    category = db.query(CategoryORM).filter(
        CategoryORM.restaurant_id == restaurant_id,
        CategoryORM.category_id == category_id
    ).first()

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )

    # Contar productos en esta categoría
    products_count = db.query(ProductORM).filter(
        ProductORM.category_id == category_id
    ).count()

    # Eliminar categoría (los productos quedarán con category_id = NULL)
    db.delete(category)
    db.commit()

    return SuccessResponse(
        success=True,
        message="Category deleted successfully",
        data={
            "category_id": category_id,
            "affected_products": products_count
        }
    )


# ============================================================================
# REORDER CATEGORIES
# ============================================================================

@router.post("/reorder", response_model=SuccessResponse)
async def reorder_categories(
    restaurant_id: str,
    category_ids: List[str],
    restaurant: RestaurantORM = Depends(check_restaurant_access),
    current_user = Depends(allow_manager),
    db: Session = Depends(get_db)
):
    """
    Reordenar categorías.

    Parámetros:
    - category_ids: Lista de category_ids en el orden deseado

    Ejemplo:
    ```json
    ["cat_abc123", "cat_def456", "cat_ghi789"]
    ```
    """
    for idx, category_id in enumerate(category_ids):
        category = db.query(CategoryORM).filter(
            CategoryORM.restaurant_id == restaurant_id,
            CategoryORM.category_id == category_id
        ).first()

        if category:
            category.display_order = idx

    db.commit()

    return SuccessResponse(
        success=True,
        message="Categories reordered successfully",
        data={"count": len(category_ids)}
    )
