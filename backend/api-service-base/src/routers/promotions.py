"""
================================================================================
PROMOTIONS ROUTER - Menu Service
================================================================================
Endpoints para gestión de promociones del restaurante
================================================================================
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, time
import logging

from ..database import get_db
from ..models import Promotion, Product
from ..schemas import (
    PromotionCreate,
    PromotionUpdate,
    PromotionResponse,
    PromotionForAgent,
    ErrorResponse
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ==============================================================================
# GET ALL PROMOTIONS
# ==============================================================================

@router.get(
    "",
    response_model=List[PromotionResponse],
    summary="Obtener todas las promociones",
    description="Retorna lista de promociones con filtros opcionales"
)
async def get_promotions(
    skip: int = Query(default=0, ge=0, description="Registros a saltar"),
    limit: int = Query(default=100, ge=1, le=500, description="Limite de registros"),
    active_only: bool = Query(default=False, description="Solo promociones activas"),
    promotion_type: Optional[str] = Query(default=None, description="Filtrar por tipo"),
    db: Session = Depends(get_db)
):
    """Obtener lista de promociones con filtros"""

    logger.info(f"Fetching promotions: skip={skip}, limit={limit}, active_only={active_only}")

    query = db.query(Promotion)

    if active_only:
        query = query.filter(Promotion.is_active == True)

    if promotion_type:
        query = query.filter(Promotion.promotion_type == promotion_type)

    # Ordenar por prioridad (mayor primero) y fecha de creacion
    query = query.order_by(Promotion.priority.desc(), Promotion.created_at.desc())

    promotions = query.offset(skip).limit(limit).all()

    logger.info(f"Found {len(promotions)} promotions")

    return promotions


# ==============================================================================
# GET ACTIVE PROMOTIONS (FOR VOICE AGENT)
# ==============================================================================

@router.get(
    "/active",
    response_model=List[PromotionForAgent],
    summary="Obtener promociones activas ahora",
    description="Retorna promociones que aplican en este momento (fecha y hora actuales)"
)
async def get_active_promotions(
    product_ids: Optional[str] = Query(
        default=None,
        description="IDs de productos separados por coma para filtrar"
    ),
    db: Session = Depends(get_db)
):
    """
    Obtener promociones activas en este momento.

    Considera:
    - Promocion activa (is_active=True)
    - Dentro del rango de fechas (start_date <= now <= end_date)
    - Dentro del horario (start_time <= current_time <= end_time)
    - Dia de la semana actual incluido en days_of_week

    Optimizado para el agente de ventas.
    """

    logger.info(f"Fetching active promotions, product_ids filter: {product_ids}")

    now = datetime.now()
    current_time = now.time()
    current_day = _get_day_name_spanish(now.weekday())

    query = db.query(Promotion).filter(Promotion.is_active == True)

    promotions = query.order_by(Promotion.priority.desc()).all()

    # Filtrar por fecha, hora y dia
    active_promotions = []
    for promo in promotions:
        if not _is_promotion_valid_now(promo, now, current_time, current_day):
            continue
        active_promotions.append(promo)

    # Si se especifican product_ids, filtrar solo las que aplican a esos productos
    if product_ids:
        target_ids = [int(pid.strip()) for pid in product_ids.split(",")]
        filtered = []
        for promo in active_promotions:
            promo_product_ids = [p.id for p in promo.products]
            # Si la promocion no tiene productos asignados, aplica a todo
            if not promo_product_ids or any(pid in promo_product_ids for pid in target_ids):
                filtered.append(promo)
        active_promotions = filtered

    # Formatear para el agente
    result = []
    for promo in active_promotions:
        result.append(PromotionForAgent(
            id=promo.id,
            name=promo.name,
            description=promo.description,
            promotion_type=promo.promotion_type,
            discount_value=promo.discount_value,
            special_price=promo.special_price,
            voice_pitch=promo.voice_pitch,
            product_names=[p.name for p in promo.products]
        ))

    logger.info(f"Found {len(result)} active promotions")

    return result


# ==============================================================================
# GET PROMOTION BY ID
# ==============================================================================

@router.get(
    "/{promotion_id}",
    response_model=PromotionResponse,
    summary="Obtener promocion por ID",
    responses={
        404: {"model": ErrorResponse, "description": "Promocion no encontrada"}
    }
)
async def get_promotion(
    promotion_id: int,
    db: Session = Depends(get_db)
):
    """Obtener una promocion especifica por ID"""

    logger.info(f"Fetching promotion with ID: {promotion_id}")

    promotion = db.query(Promotion).filter(Promotion.id == promotion_id).first()

    if not promotion:
        logger.warning(f"Promotion {promotion_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Promotion with ID {promotion_id} not found"
        )

    return promotion


# ==============================================================================
# CREATE PROMOTION
# ==============================================================================

@router.post(
    "",
    response_model=PromotionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear nueva promocion",
    responses={
        400: {"model": ErrorResponse, "description": "Datos invalidos"}
    }
)
async def create_promotion(
    promotion: PromotionCreate,
    db: Session = Depends(get_db)
):
    """Crear una nueva promocion"""

    logger.info(f"Creating promotion: {promotion.name}")

    # Extraer product_ids antes de crear el modelo
    product_ids = promotion.product_ids
    promo_data = promotion.model_dump(exclude={'product_ids'})

    # Crear promocion
    db_promotion = Promotion(**promo_data)

    # Agregar productos si se especificaron
    if product_ids:
        products = db.query(Product).filter(Product.id.in_(product_ids)).all()
        if len(products) != len(product_ids):
            found_ids = [p.id for p in products]
            missing = set(product_ids) - set(found_ids)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Products not found: {list(missing)}"
            )
        db_promotion.products = products

    db.add(db_promotion)
    db.commit()
    db.refresh(db_promotion)

    logger.info(f"Promotion created successfully with ID: {db_promotion.id}")

    return db_promotion


# ==============================================================================
# UPDATE PROMOTION
# ==============================================================================

@router.put(
    "/{promotion_id}",
    response_model=PromotionResponse,
    summary="Actualizar promocion",
    responses={
        404: {"model": ErrorResponse, "description": "Promocion no encontrada"}
    }
)
async def update_promotion(
    promotion_id: int,
    promotion_update: PromotionUpdate,
    db: Session = Depends(get_db)
):
    """Actualizar una promocion existente"""

    logger.info(f"Updating promotion ID: {promotion_id}")

    db_promotion = db.query(Promotion).filter(Promotion.id == promotion_id).first()

    if not db_promotion:
        logger.warning(f"Promotion {promotion_id} not found for update")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Promotion with ID {promotion_id} not found"
        )

    # Extraer product_ids antes de actualizar
    product_ids = promotion_update.product_ids
    update_data = promotion_update.model_dump(exclude_unset=True, exclude={'product_ids'})

    # Actualizar campos
    for field, value in update_data.items():
        setattr(db_promotion, field, value)

    # Actualizar productos si se especificaron
    if product_ids is not None:
        products = db.query(Product).filter(Product.id.in_(product_ids)).all()
        if len(products) != len(product_ids):
            found_ids = [p.id for p in products]
            missing = set(product_ids) - set(found_ids)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Products not found: {list(missing)}"
            )
        db_promotion.products = products

    db.commit()
    db.refresh(db_promotion)

    logger.info(f"Promotion {promotion_id} updated successfully")

    return db_promotion


# ==============================================================================
# DELETE PROMOTION
# ==============================================================================

@router.delete(
    "/{promotion_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar promocion",
    responses={
        404: {"model": ErrorResponse, "description": "Promocion no encontrada"}
    }
)
async def delete_promotion(
    promotion_id: int,
    db: Session = Depends(get_db)
):
    """Eliminar una promocion"""

    logger.info(f"Deleting promotion ID: {promotion_id}")

    db_promotion = db.query(Promotion).filter(Promotion.id == promotion_id).first()

    if not db_promotion:
        logger.warning(f"Promotion {promotion_id} not found for deletion")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Promotion with ID {promotion_id} not found"
        )

    db.delete(db_promotion)
    db.commit()

    logger.info(f"Promotion {promotion_id} deleted successfully")

    return None


# ==============================================================================
# TOGGLE ACTIVE STATUS
# ==============================================================================

@router.patch(
    "/{promotion_id}/toggle",
    response_model=PromotionResponse,
    summary="Activar/Desactivar promocion"
)
async def toggle_promotion(
    promotion_id: int,
    is_active: bool = Query(..., description="Nuevo estado"),
    db: Session = Depends(get_db)
):
    """Cambiar el estado activo de una promocion"""

    logger.info(f"Toggling promotion {promotion_id} to {is_active}")

    db_promotion = db.query(Promotion).filter(Promotion.id == promotion_id).first()

    if not db_promotion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Promotion with ID {promotion_id} not found"
        )

    db_promotion.is_active = is_active
    db.commit()
    db.refresh(db_promotion)

    logger.info(f"Promotion {promotion_id} is_active updated to {is_active}")

    return db_promotion


# ==============================================================================
# INCREMENT USAGE COUNT
# ==============================================================================

@router.post(
    "/{promotion_id}/used",
    response_model=PromotionResponse,
    summary="Registrar uso de promocion"
)
async def record_promotion_usage(
    promotion_id: int,
    db: Session = Depends(get_db)
):
    """Incrementar contador de uso de promocion (llamar cuando se aplica)"""

    logger.info(f"Recording usage for promotion {promotion_id}")

    db_promotion = db.query(Promotion).filter(Promotion.id == promotion_id).first()

    if not db_promotion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Promotion with ID {promotion_id} not found"
        )

    db_promotion.times_used += 1
    db.commit()
    db.refresh(db_promotion)

    logger.info(f"Promotion {promotion_id} usage count: {db_promotion.times_used}")

    return db_promotion


# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

def _get_day_name_spanish(weekday: int) -> str:
    """Convertir dia de la semana (0-6) a nombre en espanol"""
    days = ['lunes', 'martes', 'miercoles', 'jueves', 'viernes', 'sabado', 'domingo']
    return days[weekday]


def _is_promotion_valid_now(
    promo: Promotion,
    now: datetime,
    current_time: time,
    current_day: str
) -> bool:
    """Verificar si una promocion es valida en el momento actual"""

    # Verificar fecha de inicio
    if promo.start_date and now < promo.start_date:
        return False

    # Verificar fecha de fin
    if promo.end_date and now > promo.end_date:
        return False

    # Verificar horario
    if promo.start_time and promo.end_time:
        if not (promo.start_time <= current_time <= promo.end_time):
            return False

    # Verificar dia de la semana
    if promo.days_of_week:
        valid_days = [d.strip().lower() for d in promo.days_of_week.split(',')]
        if current_day not in valid_days:
            return False

    return True
