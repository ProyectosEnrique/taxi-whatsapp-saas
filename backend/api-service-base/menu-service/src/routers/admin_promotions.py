"""
================================================================================
ADMIN PROMOTIONS ROUTER - Gestión de Promociones
================================================================================
Endpoints de administración para crear y gestionar promociones
================================================================================
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import logging

from ..database import get_db
from ..models import Promotion, Product
from ..models.user import User
from ..schemas import PromotionCreate, PromotionUpdate, PromotionResponse
from ..auth.permissions import require_admin, verify_tenant_admin

logger = logging.getLogger(__name__)

router = APIRouter()


# ==============================================================================
# CREATE PROMOTION
# ==============================================================================

@router.post(
    "",
    response_model=PromotionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear nueva promoción"
)
async def create_promotion(
    data: PromotionCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Crear una nueva promoción para el tenant.

    Solo administradores pueden crear promociones para su tenant.
    """
    logger.info(f"Admin {current_user.id} creando promoción: {data.name}")

    # La promoción se crea para el tenant del usuario actual
    tenant_id = current_user.tenant_id

    # Verificar que los productos pertenecen al tenant (si se especifican)
    if data.product_ids:
        products = db.query(Product).filter(Product.id.in_(data.product_ids)).all()

        if len(products) != len(data.product_ids):
            found_ids = [p.id for p in products]
            missing = set(data.product_ids) - set(found_ids)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Productos no encontrados: {list(missing)}"
            )

        # Verificar que todos los productos pertenecen al tenant
        for product in products:
            if product.tenant_id != tenant_id and not current_user.is_super_admin():
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"El producto {product.name} no pertenece a tu tenant"
                )

    # Extraer product_ids antes de crear el modelo
    product_ids = data.product_ids
    promo_data = data.model_dump(exclude={'product_ids'})

    # Crear promoción
    new_promotion = Promotion(
        tenant_id=tenant_id,
        **promo_data
    )

    # Agregar productos si se especificaron
    if product_ids:
        products = db.query(Product).filter(Product.id.in_(product_ids)).all()
        new_promotion.products = products

    db.add(new_promotion)
    db.commit()
    db.refresh(new_promotion)

    logger.info(f"Promoción creada: {new_promotion.id} - {new_promotion.name}")

    return new_promotion


# ==============================================================================
# UPDATE PROMOTION
# ==============================================================================

@router.put(
    "/{promotion_id}",
    response_model=PromotionResponse,
    summary="Actualizar promoción"
)
async def update_promotion(
    promotion_id: int,
    data: PromotionUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Actualizar una promoción existente.

    Solo puede actualizar promociones de su tenant.
    """
    logger.info(f"Admin {current_user.id} actualizando promoción {promotion_id}")

    # Buscar promoción
    promotion = db.query(Promotion).filter(Promotion.id == promotion_id).first()

    if not promotion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Promoción no encontrada"
        )

    # Verificar que pertenece al tenant del admin
    verify_tenant_admin(current_user, promotion.tenant_id)

    # Verificar productos si se actualizan
    if data.product_ids is not None:
        products = db.query(Product).filter(Product.id.in_(data.product_ids)).all()

        if len(products) != len(data.product_ids):
            found_ids = [p.id for p in products]
            missing = set(data.product_ids) - set(found_ids)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Productos no encontrados: {list(missing)}"
            )

        # Verificar que todos los productos pertenecen al tenant
        for product in products:
            if product.tenant_id != promotion.tenant_id and not current_user.is_super_admin():
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"El producto {product.name} no pertenece a tu tenant"
                )

    # Extraer product_ids antes de actualizar
    product_ids = data.product_ids
    update_data = data.model_dump(exclude_unset=True, exclude={'product_ids'})

    # Actualizar campos
    for field, value in update_data.items():
        setattr(promotion, field, value)

    # Actualizar productos si se especificaron
    if product_ids is not None:
        products = db.query(Product).filter(Product.id.in_(product_ids)).all()
        promotion.products = products

    db.commit()
    db.refresh(promotion)

    logger.info(f"Promoción {promotion_id} actualizada")

    return promotion


# ==============================================================================
# DELETE PROMOTION
# ==============================================================================

@router.delete(
    "/{promotion_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar promoción"
)
async def delete_promotion(
    promotion_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Eliminar una promoción.

    Solo puede eliminar promociones de su tenant.
    """
    logger.info(f"Admin {current_user.id} eliminando promoción {promotion_id}")

    promotion = db.query(Promotion).filter(Promotion.id == promotion_id).first()

    if not promotion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Promoción no encontrada"
        )

    # Verificar que pertenece al tenant del admin
    verify_tenant_admin(current_user, promotion.tenant_id)

    db.delete(promotion)
    db.commit()

    logger.info(f"Promoción {promotion_id} eliminada")

    return None


# ==============================================================================
# GET ALL PROMOTIONS (ADMIN)
# ==============================================================================

@router.get(
    "",
    response_model=List[PromotionResponse],
    summary="Listar promociones del tenant"
)
async def list_promotions(
    current_user: User = Depends(require_admin),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    active_only: bool = Query(default=False),
    db: Session = Depends(get_db)
):
    """
    Listar todas las promociones del tenant del admin.

    Super admin puede ver todas especificando tenant_id.
    """
    logger.info(f"Admin {current_user.id} listando promociones")

    # Filtrar por tenant del admin
    query = db.query(Promotion).filter(Promotion.tenant_id == current_user.tenant_id)

    if active_only:
        query = query.filter(Promotion.is_active == True)

    promotions = query.order_by(
        Promotion.priority.desc(),
        Promotion.created_at.desc()
    ).offset(skip).limit(limit).all()

    logger.info(f"Encontradas {len(promotions)} promociones")

    return promotions


# ==============================================================================
# TOGGLE ACTIVE STATUS
# ==============================================================================

@router.patch(
    "/{promotion_id}/toggle",
    response_model=PromotionResponse,
    summary="Activar/Desactivar promoción"
)
async def toggle_promotion(
    promotion_id: int,
    is_active: bool = Query(..., description="Nuevo estado"),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Cambiar el estado activo de una promoción.

    Solo puede modificar promociones de su tenant.
    """
    logger.info(f"Admin {current_user.id} cambiando estado de promoción {promotion_id} a {is_active}")

    promotion = db.query(Promotion).filter(Promotion.id == promotion_id).first()

    if not promotion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Promoción no encontrada"
        )

    # Verificar que pertenece al tenant del admin
    verify_tenant_admin(current_user, promotion.tenant_id)

    promotion.is_active = is_active
    db.commit()
    db.refresh(promotion)

    logger.info(f"Promoción {promotion_id} is_active = {is_active}")

    return promotion


# ==============================================================================
# GET PROMOTION STATS
# ==============================================================================

@router.get(
    "/{promotion_id}/stats",
    summary="Obtener estadísticas de promoción"
)
async def get_promotion_stats(
    promotion_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Obtener estadísticas de uso de una promoción.

    Solo puede ver promociones de su tenant.
    """
    logger.info(f"Admin {current_user.id} obteniendo stats de promoción {promotion_id}")

    promotion = db.query(Promotion).filter(Promotion.id == promotion_id).first()

    if not promotion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Promoción no encontrada"
        )

    # Verificar que pertenece al tenant del admin
    verify_tenant_admin(current_user, promotion.tenant_id)

    return {
        "promotion_id": promotion.id,
        "name": promotion.name,
        "times_used": promotion.times_used,
        "is_active": promotion.is_active,
        "start_date": promotion.start_date,
        "end_date": promotion.end_date,
        "discount_value": promotion.discount_value,
        "discount_type": promotion.discount_type,
        "products_count": len(promotion.products)
    }
