"""
================================================================================
ADMIN CATEGORIES ROUTER - Gestión de Categorías
================================================================================
Endpoints de administración para crear y gestionar categorías
================================================================================
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import logging

from ..database import get_db
from ..models import Category
from ..models.user import User
from ..schemas import CategoryCreate, CategoryUpdate, CategoryResponse
from ..auth.permissions import require_admin

logger = logging.getLogger(__name__)

router = APIRouter()


# ==============================================================================
# CREATE CATEGORY
# ==============================================================================

@router.post(
    "",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear nueva categoría"
)
async def create_category(
    data: CategoryCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Crear una nueva categoría para el tenant.

    Solo administradores pueden crear categorías.
    """
    logger.info(f"Admin {current_user.id} creando categoría: {data.name}")

    tenant_id = current_user.tenant_id

    # Verificar que no exista otra categoría con el mismo nombre en este tenant
    existing = db.query(Category).filter(
        Category.tenant_id == tenant_id,
        Category.name == data.name
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ya existe una categoría con el nombre '{data.name}' en este tenant"
        )

    # Crear categoría
    new_category = Category(
        tenant_id=tenant_id,
        name=data.name,
        description=data.description,
        display_order=data.display_order if data.display_order is not None else 0,
        is_active=data.is_active if data.is_active is not None else True,
        is_beverage=data.is_beverage if data.is_beverage is not None else False
    )

    db.add(new_category)
    db.commit()
    db.refresh(new_category)

    logger.info(f"Categoría creada: {new_category.id} - {new_category.name}")

    return new_category


# ==============================================================================
# UPDATE CATEGORY
# ==============================================================================

@router.put(
    "/{category_id}",
    response_model=CategoryResponse,
    summary="Actualizar categoría"
)
async def update_category(
    category_id: int,
    data: CategoryUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Actualizar una categoría existente.
    """
    logger.info(f"Actualizando categoría: {category_id}")

    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Categoría no encontrada"
        )

    # Verificar permisos
    if category.tenant_id != current_user.tenant_id and not current_user.is_super_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para modificar esta categoría"
        )

    # Actualizar campos
    update_data = data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(category, field, value)

    db.commit()
    db.refresh(category)

    logger.info(f"Categoría {category_id} actualizada")

    return category


# ==============================================================================
# DELETE CATEGORY
# ==============================================================================

@router.delete(
    "/{category_id}",
    summary="Eliminar categoría"
)
async def delete_category(
    category_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Eliminar una categoría.

    Los productos en esta categoría quedarán sin categoría (category_id = NULL).
    """
    logger.info(f"Eliminando categoría: {category_id}")

    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Categoría no encontrada"
        )

    # Verificar permisos
    if category.tenant_id != current_user.tenant_id and not current_user.is_super_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para eliminar esta categoría"
        )

    db.delete(category)
    db.commit()

    logger.info(f"Categoría {category_id} eliminada")

    return {
        "success": True,
        "message": "Categoría eliminada exitosamente"
    }


# ==============================================================================
# LIST CATEGORIES (ADMIN)
# ==============================================================================

@router.get(
    "",
    response_model=List[CategoryResponse],
    summary="Listar categorías (Admin)"
)
async def list_categories_admin(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
    tenant_id: Optional[str] = Query(default=None),
    is_active: Optional[bool] = Query(default=None)
):
    """
    Listar todas las categorías del tenant.
    """
    logger.info(f"Admin {current_user.id} listando categorías")

    query = db.query(Category)

    # Filtrar por tenant
    if tenant_id:
        if not current_user.is_super_admin():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo super admin puede filtrar por otros tenants"
            )
        query = query.filter(Category.tenant_id == tenant_id)
    else:
        if not current_user.is_super_admin():
            query = query.filter(Category.tenant_id == current_user.tenant_id)

    if is_active is not None:
        query = query.filter(Category.is_active == is_active)

    categories = query.order_by(Category.display_order.asc(), Category.name.asc()).all()

    return categories
