"""
================================================================================
LOYALTY MODELS - Sistema de Puntos de Fidelidad
================================================================================
Modelos de datos para gestión de puntos, niveles y recompensas
================================================================================
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class TierLevel(str, Enum):
    """Niveles de membresía"""
    BRONCE = "bronce"
    PLATA = "plata"
    ORO = "oro"
    PLATINO = "platino"


class TransactionType(str, Enum):
    """Tipos de transacciones de puntos"""
    EARN = "earn"          # Ganar puntos por compra
    REDEEM = "redeem"      # Canjear puntos por descuento
    BONUS = "bonus"        # Puntos bonus (cumpleaños, referidos, etc)
    EXPIRE = "expire"      # Puntos expirados
    ADJUSTMENT = "adjustment"  # Ajuste manual por admin


# ==============================================================================
# CONFIGURACIÓN DE LOYALTY (Por Restaurante/Tienda)
# ==============================================================================

class LoyaltyConfig(BaseModel):
    """
    Configuración del sistema de puntos para cada restaurante/tienda.
    El dueño configura esto desde su dashboard.
    """
    restaurant_id: str

    # Sistema de puntos
    enabled: bool = True
    points_per_currency: float = Field(default=0.1, description="Puntos por cada peso gastado (0.1 = 1 punto por cada $10)")
    currency_per_point: float = Field(default=0.5, description="Pesos de descuento por punto (0.5 = $0.50 por punto)")
    min_points_to_redeem: int = Field(default=100, description="Mínimo de puntos para canjear")
    max_redeem_percentage: float = Field(default=50.0, description="Máximo % del total que se puede pagar con puntos")

    # Expiración de puntos
    points_expire_days: Optional[int] = Field(default=365, description="Días hasta que expiran los puntos (null = nunca)")

    # Sistema de niveles/tiers
    tiers_enabled: bool = True
    tier_thresholds: Dict[str, int] = Field(default={
        "bronce": 0,
        "plata": 1000,
        "oro": 2500,
        "platino": 5000
    })

    # Multiplicadores por tier
    tier_multipliers: Dict[str, float] = Field(default={
        "bronce": 1.0,
        "plata": 1.5,
        "oro": 2.0,
        "platino": 3.0
    })

    # Beneficios por tier
    tier_benefits: Dict[str, Dict[str, Any]] = Field(default={
        "bronce": {"discount": 0, "free_shipping": False},
        "plata": {"discount": 0, "free_shipping": True},
        "oro": {"discount": 5, "free_shipping": True},
        "platino": {"discount": 10, "free_shipping": True}
    })

    # Bonos especiales
    birthday_bonus: int = Field(default=100, description="Puntos bonus en cumpleaños")
    referral_bonus: int = Field(default=50, description="Puntos por referir amigo")
    first_purchase_bonus: int = Field(default=50, description="Puntos en primera compra")

    # Notificaciones
    notify_points_earned: bool = True
    notify_tier_upgrade: bool = True
    notify_points_expiring: bool = True

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ==============================================================================
# LOYALTY DEL CLIENTE
# ==============================================================================

class CustomerLoyalty(BaseModel):
    """
    Datos de puntos y fidelidad de cada cliente.
    Se crea automáticamente en la primera compra.
    """
    customer_phone: str
    restaurant_id: str

    # Puntos
    total_points: int = 0
    available_points: int = 0  # Puntos disponibles para usar
    lifetime_points: int = 0   # Total histórico ganado

    # Estadísticas
    total_spent: float = 0.0
    total_orders: int = 0
    average_order_value: float = 0.0

    # Nivel
    current_tier: TierLevel = TierLevel.BRONCE

    # Datos personales (para bonos)
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    birthday: Optional[str] = None  # Format: "MM-DD"

    # Referidos
    referred_by: Optional[str] = None  # Phone del referidor
    referrals_count: int = 0

    # Fechas
    first_purchase_date: Optional[datetime] = None
    last_purchase_date: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def calculate_tier(self, config: LoyaltyConfig) -> TierLevel:
        """Calcular tier basado en puntos lifetime"""
        if not config.tiers_enabled:
            return TierLevel.BRONCE

        thresholds = config.tier_thresholds
        if self.lifetime_points >= thresholds.get("platino", 5000):
            return TierLevel.PLATINO
        elif self.lifetime_points >= thresholds.get("oro", 2500):
            return TierLevel.ORO
        elif self.lifetime_points >= thresholds.get("plata", 1000):
            return TierLevel.PLATA
        else:
            return TierLevel.BRONCE

    def get_multiplier(self, config: LoyaltyConfig) -> float:
        """Obtener multiplicador de puntos según tier"""
        return config.tier_multipliers.get(self.current_tier.value, 1.0)


# ==============================================================================
# TRANSACCIONES DE PUNTOS
# ==============================================================================

class LoyaltyTransaction(BaseModel):
    """
    Registro de cada movimiento de puntos.
    """
    transaction_id: str
    customer_phone: str
    restaurant_id: str

    # Tipo de transacción
    transaction_type: TransactionType

    # Puntos
    points_change: int  # Positivo = ganados, Negativo = canjeados
    points_balance_after: int

    # Relacionado con orden
    order_id: Optional[str] = None
    order_total: Optional[float] = None

    # Descripción
    description: str

    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)

    created_at: datetime = Field(default_factory=datetime.utcnow)


# ==============================================================================
# REQUEST/RESPONSE MODELS
# ==============================================================================

class EarnPointsRequest(BaseModel):
    """Request para otorgar puntos por compra"""
    customer_phone: str
    restaurant_id: str
    order_id: str
    order_total: float
    customer_name: Optional[str] = None


class RedeemPointsRequest(BaseModel):
    """Request para canjear puntos"""
    customer_phone: str
    restaurant_id: str
    points_to_redeem: int
    order_total: float


class RedeemPointsResponse(BaseModel):
    """Response de canje de puntos"""
    success: bool
    discount_amount: float
    points_redeemed: int
    points_remaining: int
    message: str


class LoyaltyBalanceResponse(BaseModel):
    """Response de balance de puntos"""
    customer_phone: str
    restaurant_id: str
    available_points: int
    lifetime_points: int
    current_tier: str
    tier_benefits: Dict[str, Any]
    points_value_in_currency: float
    total_spent: float
    total_orders: int
    next_tier: Optional[str] = None
    points_to_next_tier: Optional[int] = None


class UpdateLoyaltyConfigRequest(BaseModel):
    """Request para actualizar configuración"""
    restaurant_id: str
    enabled: Optional[bool] = None
    points_per_currency: Optional[float] = None
    currency_per_point: Optional[float] = None
    min_points_to_redeem: Optional[int] = None
    max_redeem_percentage: Optional[float] = None
    points_expire_days: Optional[int] = None
    tiers_enabled: Optional[bool] = None
    birthday_bonus: Optional[int] = None
    referral_bonus: Optional[int] = None
    first_purchase_bonus: Optional[int] = None
