"""
================================================================================
LOYALTY SCHEMAS
================================================================================
Schemas Pydantic para sistema de puntos y recompensas
================================================================================
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ==============================================================================
# LOYALTY ACCOUNT SCHEMAS
# ==============================================================================

class LoyaltyAccountResponse(BaseModel):
    """Response de cuenta de lealtad"""
    id: int
    user_id: int
    tenant_id: str
    points: int
    level: str
    total_points_earned: int
    total_points_redeemed: int
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class LoyaltyAccountDetail(BaseModel):
    """Detalle completo de cuenta con beneficios"""
    id: int
    user_id: int
    tenant_id: str
    points: int
    level: str
    total_points_earned: int
    total_points_redeemed: int
    next_level: Optional[str]
    points_to_next_level: Optional[int]
    level_benefits: List[str]


# ==============================================================================
# REWARD SCHEMAS
# ==============================================================================

class RewardCreate(BaseModel):
    """Request para crear recompensa"""
    name: str = Field(..., max_length=200)
    description: Optional[str] = None
    image_url: Optional[str] = None
    points_cost: int = Field(..., gt=0)
    reward_type: str = Field(..., description="discount_percentage, discount_fixed, free_product, free_shipping")
    value: Optional[float] = None
    product_id: Optional[int] = None
    min_level: str = Field(default="bronze", description="bronze, silver, gold, platinum")
    is_active: bool = True
    stock: Optional[int] = None


class RewardUpdate(BaseModel):
    """Request para actualizar recompensa"""
    name: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    points_cost: Optional[int] = None
    reward_type: Optional[str] = None
    value: Optional[float] = None
    product_id: Optional[int] = None
    min_level: Optional[str] = None
    is_active: Optional[bool] = None
    stock: Optional[int] = None


class RewardResponse(BaseModel):
    """Response de recompensa"""
    id: int
    tenant_id: str
    name: str
    description: Optional[str]
    image_url: Optional[str]
    points_cost: int
    reward_type: str
    value: Optional[float]
    product_id: Optional[int]
    min_level: str
    is_active: bool
    stock: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True


class RewardForCustomer(BaseModel):
    """Recompensa vista desde el cliente (con elegibilidad)"""
    id: int
    name: str
    description: Optional[str]
    image_url: Optional[str]
    points_cost: int
    reward_type: str
    value: Optional[float]
    can_redeem: bool
    reason_cannot_redeem: Optional[str]
    stock_available: bool


# ==============================================================================
# TRANSACTION SCHEMAS
# ==============================================================================

class LoyaltyTransactionResponse(BaseModel):
    """Response de transacción de puntos"""
    id: int
    account_id: int
    transaction_type: str
    points: int
    order_id: Optional[int]
    reward_id: Optional[int]
    description: Optional[str]
    balance_after: int
    created_at: datetime

    class Config:
        from_attributes = True


class LoyaltyHistoryResponse(BaseModel):
    """Historial de transacciones con detalles"""
    id: int
    transaction_type: str
    points: int
    description: Optional[str]
    balance_after: int
    created_at: datetime
    order_id: Optional[int]
    reward_name: Optional[str]


# ==============================================================================
# REDEMPTION SCHEMAS
# ==============================================================================

class RedeemRewardRequest(BaseModel):
    """Request para canjear recompensa"""
    reward_id: int


class RedeemRewardResponse(BaseModel):
    """Response de canje exitoso"""
    success: bool
    message: str
    transaction_id: int
    points_redeemed: int
    remaining_points: int
    reward: RewardResponse
    level_changed: bool
    new_level: Optional[str]


# ==============================================================================
# POINTS SCHEMAS
# ==============================================================================

class AddPointsRequest(BaseModel):
    """Request para agregar puntos (admin/sistema)"""
    user_id: int
    points: int = Field(..., description="Puntos a agregar (positivo o negativo)")
    description: Optional[str] = None
    order_id: Optional[int] = None


class PointsCalculationResponse(BaseModel):
    """Response de cálculo de puntos por compra"""
    order_total: float
    points_earned: int
    multiplier: float
    bonus_points: int
    total_points: int
