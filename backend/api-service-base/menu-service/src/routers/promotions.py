"""
================================================================================
PROMOTIONS ROUTER - Menu Service (PUBLIC)
================================================================================
Endpoints PÚBLICOS para consultar promociones
NOTA: Para crear/editar promociones, usar /api/v1/admin/promotions
================================================================================
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, time
import logging

from ..database import get_db
from ..models import Promotion, Product
from ..schemas import PromotionResponse, PromotionForAgent, ErrorResponse

logger = logging.getLogger(__name__)

router = APIRouter()


# ==============================================================================
# GET ALL PROMOTIONS (FILTERED BY TENANT)
# ==============================================================================

@router.get(
    "",
    response_model=List[PromotionResponse],
    summary="Obtener promociones del tenant",
    description="Retorna lista de promociones del tenant especificado"
)
async def get_promotions(
    tenant_id: str = Query(..., description="ID del tenant"),
    skip: int = Query(default=0, ge=0, description="Registros a saltar"),
    limit: int = Query(default=100, ge=1, le=500, description="Limite de registros"),
    active_only: bool = Query(default=False, description="Solo promociones activas"),
    promotion_type: Optional[str] = Query(default=None, description="Filtrar por tipo"),
    db: Session = Depends(get_db)
):
    """
    Obtener lista de promociones de un tenant específico.

    IMPORTANTE: Requiere tenant_id para asegurar aislamiento de datos.
    """

    logger.info(f"Fetching promotions for tenant: {tenant_id}")

    # Query base - SIEMPRE filtrar por tenant
    query = db.query(Promotion).filter(Promotion.tenant_id == tenant_id)

    if active_only:
        query = query.filter(Promotion.is_active == True)

    if promotion_type:
        query = query.filter(Promotion.promotion_type == promotion_type)

    # Ordenar por prioridad (mayor primero) y fecha de creacion
    promotions = query.order_by(
        Promotion.priority.desc(),
        Promotion.created_at.desc()
    ).offset(skip).limit(limit).all()

    logger.info(f"Found {len(promotions)} promotions for tenant {tenant_id}")

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
    tenant_id: str = Query(..., description="ID del tenant"),
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
    - FILTRADO POR TENANT

    Optimizado para el agente de ventas.
    """

    logger.info(f"Fetching active promotions for tenant {tenant_id}, product_ids: {product_ids}")

    now = datetime.now()
    current_time = now.time()
    current_day = _get_day_name_spanish(now.weekday())

    # SIEMPRE filtrar por tenant
    query = db.query(Promotion).filter(
        Promotion.tenant_id == tenant_id,
        Promotion.is_active == True
    )

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

    logger.info(f"Found {len(result)} active promotions for tenant {tenant_id}")

    return result


# ==============================================================================
# GET PROMOTION BY ID (WITH TENANT VERIFICATION)
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
    tenant_id: str = Query(..., description="ID del tenant"),
    db: Session = Depends(get_db)
):
    """
    Obtener una promocion específica por ID.

    Verifica que la promoción pertenezca al tenant especificado.
    """

    logger.info(f"Fetching promotion {promotion_id} for tenant {tenant_id}")

    promotion = db.query(Promotion).filter(
        Promotion.id == promotion_id,
        Promotion.tenant_id == tenant_id
    ).first()

    if not promotion:
        logger.warning(f"Promotion {promotion_id} not found for tenant {tenant_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Promotion with ID {promotion_id} not found"
        )

    return promotion


# ==============================================================================
# VALIDATE PROMO CODE (WITH TENANT)
# ==============================================================================

@router.post(
    "/validate",
    summary="Validar código promocional"
)
async def validate_promo_code(
    code: str = Query(..., description="Código promocional"),
    tenant_id: str = Query(..., description="ID del tenant"),
    subtotal: float = Query(..., description="Subtotal del pedido"),
    db: Session = Depends(get_db)
):
    """
    Validar un código promocional.

    Verifica:
    - Que el código exista EN EL TENANT especificado
    - Que esté activo
    - Que esté dentro del rango de fechas
    - Que el monto mínimo se cumpla
    - Calcula el descuento aplicable
    """
    logger.info(f"Validating promo code: {code} for tenant {tenant_id}")

    # Buscar promoción por código Y tenant
    promo = db.query(Promotion).filter(
        Promotion.code == code.upper(),
        Promotion.tenant_id == tenant_id
    ).first()

    if not promo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Código promocional no válido"
        )

    # Verificar si está activa
    if not promo.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este código promocional no está activo"
        )

    # Verificar fechas
    now = datetime.now()
    if promo.start_date and now < promo.start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este código promocional aún no es válido"
        )

    if promo.end_date and now > promo.end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este código promocional ha expirado"
        )

    # Verificar monto mínimo
    if promo.minimum_purchase and subtotal < promo.minimum_purchase:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El monto mínimo para este código es ${promo.minimum_purchase}"
        )

    # Calcular descuento
    discount_amount = 0.0

    if promo.discount_type == "percentage":
        discount_amount = subtotal * (promo.discount_value / 100)
        if promo.max_discount_amount:
            discount_amount = min(discount_amount, promo.max_discount_amount)
    else:  # fixed
        discount_amount = promo.discount_value

    logger.info(f"Valid code. Discount: ${discount_amount}")

    return {
        "success": True,
        "valid": True,
        "code": promo.code,
        "description": promo.description,
        "discount_type": promo.discount_type,
        "discount_value": promo.discount_value,
        "discount_amount": discount_amount,
        "new_total": max(0, subtotal - discount_amount)
    }


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


# ==============================================================================
# NOTAS IMPORTANTES
# ==============================================================================

"""
⚠️ SEGURIDAD:

1. Este router es SOLO para lectura (GET) y validación
2. Todos los endpoints REQUIEREN tenant_id
3. Todos los queries filtran por tenant_id
4. No hay endpoints de CREATE/UPDATE/DELETE aquí

Para gestión de promociones (crear, editar, eliminar):
→ Usar /api/v1/admin/promotions (requiere autenticación y permisos de admin)

"""
