"""
================================================================================
LOYALTY ROUTER - Sistema de Puntos y Recompensas
================================================================================
Endpoints para gestión de programa de lealtad
================================================================================
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import logging
from datetime import datetime

from ..database import get_db
from ..models.loyalty import (
    LoyaltyAccount,
    Reward,
    LoyaltyTransaction,
    LoyaltyLevel,
    TransactionType
)
from ..models.user import User
from ..schemas.loyalty import (
    LoyaltyAccountResponse,
    LoyaltyAccountDetail,
    RewardCreate,
    RewardUpdate,
    RewardResponse,
    RewardForCustomer,
    LoyaltyTransactionResponse,
    LoyaltyHistoryResponse,
    RedeemRewardRequest,
    RedeemRewardResponse,
    AddPointsRequest,
    PointsCalculationResponse
)
from ..routers.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()


# ==============================================================================
# CONSTANTS
# ==============================================================================

# Puntos por cada $1 MXN gastado
POINTS_PER_PESO = 1

# Multiplicadores por nivel
LEVEL_MULTIPLIERS = {
    LoyaltyLevel.BRONZE: 1.0,
    LoyaltyLevel.SILVER: 1.25,
    LoyaltyLevel.GOLD: 1.5,
    LoyaltyLevel.PLATINUM: 2.0
}

# Puntos para cada nivel
LEVEL_THRESHOLDS = {
    LoyaltyLevel.BRONZE: 0,
    LoyaltyLevel.SILVER: 500,
    LoyaltyLevel.GOLD: 1000,
    LoyaltyLevel.PLATINUM: 2500
}


# ==============================================================================
# GET LOYALTY ACCOUNT
# ==============================================================================

@router.get(
    "",
    response_model=LoyaltyAccountDetail,
    summary="Obtener cuenta de lealtad"
)
async def get_loyalty_account(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Obtener la cuenta de puntos del usuario actual.

    Si no existe, se crea automáticamente.
    """
    logger.info(f"Consultando cuenta de lealtad para usuario {current_user.id}")

    # Buscar o crear cuenta
    account = db.query(LoyaltyAccount).filter(
        LoyaltyAccount.user_id == current_user.id
    ).first()

    if not account:
        logger.info(f"Creando nueva cuenta de lealtad para usuario {current_user.id}")
        account = LoyaltyAccount(
            user_id=current_user.id,
            tenant_id=current_user.tenant_id,
            points=0,
            level=LoyaltyLevel.BRONZE
        )
        db.add(account)
        db.commit()
        db.refresh(account)

    # Calcular próximo nivel
    next_level = None
    points_to_next = None

    if account.level == LoyaltyLevel.BRONZE:
        next_level = "silver"
        points_to_next = LEVEL_THRESHOLDS[LoyaltyLevel.SILVER] - account.points
    elif account.level == LoyaltyLevel.SILVER:
        next_level = "gold"
        points_to_next = LEVEL_THRESHOLDS[LoyaltyLevel.GOLD] - account.points
    elif account.level == LoyaltyLevel.GOLD:
        next_level = "platinum"
        points_to_next = LEVEL_THRESHOLDS[LoyaltyLevel.PLATINUM] - account.points

    # Beneficios del nivel actual
    level_benefits = _get_level_benefits(account.level)

    return LoyaltyAccountDetail(
        id=account.id,
        user_id=account.user_id,
        tenant_id=account.tenant_id,
        points=account.points,
        level=account.level.value,
        total_points_earned=account.total_points_earned,
        total_points_redeemed=account.total_points_redeemed,
        next_level=next_level,
        points_to_next_level=points_to_next,
        level_benefits=level_benefits
    )


# ==============================================================================
# GET AVAILABLE REWARDS
# ==============================================================================

@router.get(
    "/rewards",
    response_model=List[RewardForCustomer],
    summary="Obtener recompensas disponibles"
)
async def get_available_rewards(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    show_all: bool = Query(default=False, description="Mostrar todas, incluso las no canjeables")
):
    """
    Obtener lista de recompensas disponibles para canjear.

    Incluye información de elegibilidad según puntos y nivel del usuario.
    """
    logger.info(f"Obteniendo recompensas disponibles para usuario {current_user.id}")

    # Obtener cuenta del usuario
    account = db.query(LoyaltyAccount).filter(
        LoyaltyAccount.user_id == current_user.id
    ).first()

    if not account:
        # Crear cuenta si no existe
        account = LoyaltyAccount(
            user_id=current_user.id,
            tenant_id=current_user.tenant_id,
            points=0,
            level=LoyaltyLevel.BRONZE
        )
        db.add(account)
        db.commit()
        db.refresh(account)

    # Obtener recompensas activas del tenant
    rewards = db.query(Reward).filter(
        Reward.tenant_id == current_user.tenant_id,
        Reward.is_active == True
    ).order_by(Reward.points_cost.asc()).all()

    # Formatear respuesta con elegibilidad
    result = []
    for reward in rewards:
        can_redeem, reason = _can_redeem_reward(account, reward)

        # Si show_all=False, solo mostrar canjeables
        if not show_all and not can_redeem:
            continue

        result.append(RewardForCustomer(
            id=reward.id,
            name=reward.name,
            description=reward.description,
            image_url=reward.image_url,
            points_cost=reward.points_cost,
            reward_type=reward.reward_type,
            value=reward.value,
            can_redeem=can_redeem,
            reason_cannot_redeem=reason if not can_redeem else None,
            stock_available=reward.stock is None or reward.stock > 0
        ))

    logger.info(f"Encontradas {len(result)} recompensas")

    return result


# ==============================================================================
# REDEEM REWARD
# ==============================================================================

@router.post(
    "/redeem",
    response_model=RedeemRewardResponse,
    summary="Canjear recompensa"
)
async def redeem_reward(
    data: RedeemRewardRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Canjear una recompensa usando puntos.

    Verifica:
    - Puntos suficientes
    - Nivel requerido
    - Stock disponible
    """
    logger.info(f"Usuario {current_user.id} intentando canjear recompensa {data.reward_id}")

    # Obtener cuenta
    account = db.query(LoyaltyAccount).filter(
        LoyaltyAccount.user_id == current_user.id
    ).first()

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cuenta de lealtad no encontrada"
        )

    # Obtener recompensa
    reward = db.query(Reward).filter(Reward.id == data.reward_id).first()

    if not reward:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recompensa no encontrada"
        )

    if not reward.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Esta recompensa no está disponible"
        )

    # Verificar elegibilidad
    can_redeem, reason = _can_redeem_reward(account, reward)
    if not can_redeem:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=reason
        )

    # Descontar puntos
    account.points -= reward.points_cost
    account.total_points_redeemed += reward.points_cost

    # Actualizar stock si aplica
    if reward.stock is not None:
        reward.stock -= 1

    # Crear transacción
    transaction = LoyaltyTransaction(
        account_id=account.id,
        transaction_type=TransactionType.REDEEMED,
        points=-reward.points_cost,
        reward_id=reward.id,
        description=f"Canjeado: {reward.name}",
        balance_after=account.points
    )
    db.add(transaction)

    # Verificar cambio de nivel
    level_info = account.update_level()

    db.commit()
    db.refresh(account)
    db.refresh(transaction)

    logger.info(f"Recompensa {reward.id} canjeada exitosamente. Puntos restantes: {account.points}")

    return RedeemRewardResponse(
        success=True,
        message=f"Recompensa '{reward.name}' canjeada exitosamente",
        transaction_id=transaction.id,
        points_redeemed=reward.points_cost,
        remaining_points=account.points,
        reward=RewardResponse.from_orm(reward),
        level_changed=level_info["level_changed"],
        new_level=level_info.get("new_level").value if level_info["level_changed"] else None
    )


# ==============================================================================
# GET TRANSACTION HISTORY
# ==============================================================================

@router.get(
    "/history",
    response_model=List[LoyaltyHistoryResponse],
    summary="Obtener historial de puntos"
)
async def get_loyalty_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    transaction_type: Optional[str] = Query(default=None, description="earned, redeemed, bonus, etc.")
):
    """
    Obtener historial de transacciones de puntos del usuario.
    """
    logger.info(f"Consultando historial de lealtad para usuario {current_user.id}")

    # Obtener cuenta
    account = db.query(LoyaltyAccount).filter(
        LoyaltyAccount.user_id == current_user.id
    ).first()

    if not account:
        return []

    # Query transacciones
    query = db.query(LoyaltyTransaction).filter(
        LoyaltyTransaction.account_id == account.id
    )

    if transaction_type:
        query = query.filter(LoyaltyTransaction.transaction_type == transaction_type)

    transactions = query.order_by(
        LoyaltyTransaction.created_at.desc()
    ).offset(skip).limit(limit).all()

    # Formatear respuesta con nombres de recompensas
    result = []
    for trans in transactions:
        reward_name = None
        if trans.reward_id:
            reward = db.query(Reward).filter(Reward.id == trans.reward_id).first()
            reward_name = reward.name if reward else None

        result.append(LoyaltyHistoryResponse(
            id=trans.id,
            transaction_type=trans.transaction_type.value,
            points=trans.points,
            description=trans.description,
            balance_after=trans.balance_after,
            created_at=trans.created_at,
            order_id=trans.order_id,
            reward_name=reward_name
        ))

    return result


# ==============================================================================
# ADD POINTS (AFTER ORDER)
# ==============================================================================

@router.post(
    "/points",
    summary="Agregar puntos por compra"
)
async def add_points_for_order(
    data: AddPointsRequest,
    db: Session = Depends(get_db)
):
    """
    Agregar puntos a un usuario después de completar un pedido.

    Este endpoint es llamado automáticamente por el sistema cuando
    un pedido es completado.
    """
    logger.info(f"Agregando {data.points} puntos al usuario {data.user_id}")

    # Obtener cuenta
    account = db.query(LoyaltyAccount).filter(
        LoyaltyAccount.user_id == data.user_id
    ).first()

    if not account:
        # Crear cuenta si no existe
        user = db.query(User).filter(User.id == data.user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado"
            )

        account = LoyaltyAccount(
            user_id=user.id,
            tenant_id=user.tenant_id,
            points=0,
            level=LoyaltyLevel.BRONZE
        )
        db.add(account)
        db.commit()
        db.refresh(account)

    # Agregar puntos
    account.points += data.points
    account.total_points_earned += data.points

    # Crear transacción
    transaction = LoyaltyTransaction(
        account_id=account.id,
        transaction_type=TransactionType.EARNED,
        points=data.points,
        order_id=data.order_id,
        description=data.description or f"Puntos ganados por compra",
        balance_after=account.points
    )
    db.add(transaction)

    # Verificar cambio de nivel
    level_info = account.update_level()

    db.commit()
    db.refresh(account)

    logger.info(f"Puntos agregados. Balance: {account.points}, Nivel: {account.level.value}")

    return {
        "success": True,
        "points_added": data.points,
        "new_balance": account.points,
        "level": account.level.value,
        "level_changed": level_info["level_changed"],
        "new_level": level_info.get("new_level").value if level_info["level_changed"] else None
    }


# ==============================================================================
# CALCULATE POINTS FOR ORDER
# ==============================================================================

@router.get(
    "/calculate",
    response_model=PointsCalculationResponse,
    summary="Calcular puntos por compra"
)
async def calculate_points(
    order_total: float = Query(..., gt=0, description="Total del pedido"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Calcular cuántos puntos ganará el usuario por una compra.

    Los puntos se calculan según:
    - 1 punto por cada $1 MXN
    - Multiplicador según nivel (Bronze: 1x, Silver: 1.25x, Gold: 1.5x, Platinum: 2x)
    """
    logger.info(f"Calculando puntos para pedido de ${order_total}")

    # Obtener cuenta
    account = db.query(LoyaltyAccount).filter(
        LoyaltyAccount.user_id == current_user.id
    ).first()

    # Si no existe cuenta, usar nivel Bronze
    level = account.level if account else LoyaltyLevel.BRONZE
    multiplier = LEVEL_MULTIPLIERS[level]

    # Calcular puntos base
    base_points = int(order_total * POINTS_PER_PESO)

    # Aplicar multiplicador
    total_points = int(base_points * multiplier)
    bonus_points = total_points - base_points

    return PointsCalculationResponse(
        order_total=order_total,
        points_earned=base_points,
        multiplier=multiplier,
        bonus_points=bonus_points,
        total_points=total_points
    )


# ==============================================================================
# ADMIN: CREATE REWARD
# ==============================================================================

@router.post(
    "/rewards",
    response_model=RewardResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear recompensa (Admin)"
)
async def create_reward(
    data: RewardCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Crear una nueva recompensa (solo administradores).
    """
    logger.info(f"Creando recompensa: {data.name}")

    # TODO: Verificar que el usuario es administrador

    new_reward = Reward(
        tenant_id=current_user.tenant_id,
        name=data.name,
        description=data.description,
        image_url=data.image_url,
        points_cost=data.points_cost,
        reward_type=data.reward_type,
        value=data.value,
        product_id=data.product_id,
        min_level=LoyaltyLevel[data.min_level.upper()],
        is_active=data.is_active,
        stock=data.stock
    )

    db.add(new_reward)
    db.commit()
    db.refresh(new_reward)

    logger.info(f"Recompensa creada: ID {new_reward.id}")

    return new_reward


# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

def _can_redeem_reward(account: LoyaltyAccount, reward: Reward) -> tuple[bool, Optional[str]]:
    """
    Verificar si el usuario puede canjear una recompensa.

    Returns:
        (can_redeem, reason_if_not)
    """
    # Verificar puntos
    if account.points < reward.points_cost:
        return False, f"Necesitas {reward.points_cost - account.points} puntos más"

    # Verificar nivel
    level_order = [LoyaltyLevel.BRONZE, LoyaltyLevel.SILVER, LoyaltyLevel.GOLD, LoyaltyLevel.PLATINUM]
    user_level_index = level_order.index(account.level)
    required_level_index = level_order.index(reward.min_level)

    if user_level_index < required_level_index:
        return False, f"Requiere nivel {reward.min_level.value.capitalize()}"

    # Verificar stock
    if reward.stock is not None and reward.stock <= 0:
        return False, "Sin stock disponible"

    return True, None


def _get_level_benefits(level: LoyaltyLevel) -> List[str]:
    """Obtener lista de beneficios del nivel"""
    benefits = {
        LoyaltyLevel.BRONZE: [
            "1 punto por cada $1 MXN",
            "Acceso a recompensas básicas"
        ],
        LoyaltyLevel.SILVER: [
            "1.25x puntos en cada compra",
            "Acceso a recompensas Silver y Bronze",
            "Descuentos exclusivos"
        ],
        LoyaltyLevel.GOLD: [
            "1.5x puntos en cada compra",
            "Acceso a recompensas Gold, Silver y Bronze",
            "Descuentos exclusivos",
            "Envío gratis en pedidos mayores a $300"
        ],
        LoyaltyLevel.PLATINUM: [
            "2x puntos en cada compra",
            "Acceso a todas las recompensas",
            "Descuentos VIP",
            "Envío gratis en todos los pedidos",
            "Atención prioritaria"
        ]
    }
    return benefits.get(level, [])
