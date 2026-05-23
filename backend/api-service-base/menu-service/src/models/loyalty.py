"""
================================================================================
LOYALTY MODELS
================================================================================
Modelos para sistema de puntos y recompensas
================================================================================
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..database import Base
import enum


class LoyaltyLevel(str, enum.Enum):
    """Niveles de lealtad del cliente"""
    BRONZE = "bronze"      # 0-499 puntos
    SILVER = "silver"      # 500-999 puntos
    GOLD = "gold"          # 1000-2499 puntos
    PLATINUM = "platinum"  # 2500+ puntos


class TransactionType(str, enum.Enum):
    """Tipos de transacciones de puntos"""
    EARNED = "earned"          # Puntos ganados (por compra)
    REDEEMED = "redeemed"      # Puntos canjeados (por recompensa)
    BONUS = "bonus"            # Puntos de bonificación
    EXPIRED = "expired"        # Puntos expirados
    ADJUSTED = "adjusted"      # Ajuste manual (admin)


class LoyaltyAccount(Base):
    """Cuenta de puntos de lealtad del usuario"""

    __tablename__ = "loyalty_accounts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    tenant_id = Column(String(100), nullable=False, index=True)

    # Puntos actuales
    points = Column(Integer, default=0, nullable=False)

    # Nivel actual
    level = Column(Enum(LoyaltyLevel), default=LoyaltyLevel.BRONZE, nullable=False)

    # Estadísticas
    total_points_earned = Column(Integer, default=0)  # Total histórico ganado
    total_points_redeemed = Column(Integer, default=0)  # Total canjeado

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relaciones
    user = relationship("User", back_populates="loyalty_account")
    transactions = relationship("LoyaltyTransaction", back_populates="account")

    def __repr__(self):
        return f"<LoyaltyAccount User#{self.user_id} - {self.points} pts - {self.level.value}>"

    def calculate_level(self):
        """Calcular nivel según puntos actuales"""
        if self.points >= 2500:
            return LoyaltyLevel.PLATINUM
        elif self.points >= 1000:
            return LoyaltyLevel.GOLD
        elif self.points >= 500:
            return LoyaltyLevel.SILVER
        else:
            return LoyaltyLevel.BRONZE

    def update_level(self):
        """Actualizar nivel automáticamente"""
        new_level = self.calculate_level()
        if new_level != self.level:
            old_level = self.level
            self.level = new_level
            return {"level_changed": True, "old_level": old_level, "new_level": new_level}
        return {"level_changed": False}

    def to_dict(self):
        """Convertir a diccionario"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "tenant_id": self.tenant_id,
            "points": self.points,
            "level": self.level.value,
            "total_points_earned": self.total_points_earned,
            "total_points_redeemed": self.total_points_redeemed,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class Reward(Base):
    """Recompensa disponible para canjear"""

    __tablename__ = "rewards"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(100), nullable=False, index=True)

    # Información de la recompensa
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    image_url = Column(String(500), nullable=True)

    # Costo en puntos
    points_cost = Column(Integer, nullable=False)

    # Tipo de recompensa
    reward_type = Column(String(50), nullable=False)  # discount_percentage, discount_fixed, free_product, free_shipping

    # Valor de la recompensa
    value = Column(Float, nullable=True)  # Porcentaje de descuento o monto
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)  # Si es producto gratis

    # Nivel mínimo requerido
    min_level = Column(Enum(LoyaltyLevel), default=LoyaltyLevel.BRONZE)

    # Disponibilidad
    is_active = Column(Boolean, default=True)
    stock = Column(Integer, nullable=True)  # None = ilimitado

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relaciones
    product = relationship("Product")
    transactions = relationship("LoyaltyTransaction", back_populates="reward")

    def __repr__(self):
        return f"<Reward {self.name} - {self.points_cost} pts>"

    def to_dict(self):
        """Convertir a diccionario"""
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "name": self.name,
            "description": self.description,
            "image_url": self.image_url,
            "points_cost": self.points_cost,
            "reward_type": self.reward_type,
            "value": self.value,
            "product_id": self.product_id,
            "min_level": self.min_level.value,
            "is_active": self.is_active,
            "stock": self.stock,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class LoyaltyTransaction(Base):
    """Historial de transacciones de puntos"""

    __tablename__ = "loyalty_transactions"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("loyalty_accounts.id"), nullable=False)

    # Tipo de transacción
    transaction_type = Column(Enum(TransactionType), nullable=False)

    # Puntos (positivo = ganado, negativo = gastado)
    points = Column(Integer, nullable=False)

    # Referencias opcionales
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)  # Si es por compra
    reward_id = Column(Integer, ForeignKey("rewards.id"), nullable=True)  # Si es canje

    # Descripción
    description = Column(Text, nullable=True)

    # Balance después de transacción
    balance_after = Column(Integer, nullable=False)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relaciones
    account = relationship("LoyaltyAccount", back_populates="transactions")
    order = relationship("Order")
    reward = relationship("Reward", back_populates="transactions")

    def __repr__(self):
        return f"<LoyaltyTransaction {self.transaction_type.value} {self.points:+d} pts>"

    def to_dict(self):
        """Convertir a diccionario"""
        return {
            "id": self.id,
            "account_id": self.account_id,
            "transaction_type": self.transaction_type.value,
            "points": self.points,
            "order_id": self.order_id,
            "reward_id": self.reward_id,
            "description": self.description,
            "balance_after": self.balance_after,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
