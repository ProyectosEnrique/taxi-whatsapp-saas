"""
================================================================================
LOYALTY HANDLER - Sistema de Puntos de Fidelidad
================================================================================
Lógica de negocio para gestión de puntos, niveles y recompensas
================================================================================
"""

from typing import Dict, Any, Optional, List, Tuple
import logging
from datetime import datetime, timedelta
import uuid
import json
import os

from .loyalty_models import (
    LoyaltyConfig, CustomerLoyalty, LoyaltyTransaction,
    TierLevel, TransactionType,
    EarnPointsRequest, RedeemPointsRequest, RedeemPointsResponse,
    LoyaltyBalanceResponse
)

logger = logging.getLogger(__name__)


class LoyaltyHandler:
    """
    Manejador principal del sistema de puntos de fidelidad.

    Funcionalidades:
    - Otorgar puntos por compras
    - Canjear puntos por descuentos
    - Gestionar niveles/tiers
    - Bonos especiales (cumpleaños, referidos, etc)
    - Persistencia en archivos JSON (temporal, migrar a DB)
    """

    def __init__(self, data_dir: str = "data/loyalty"):
        self.data_dir = data_dir
        self._ensure_data_directory()

        # Cache en memoria
        self._configs: Dict[str, LoyaltyConfig] = {}
        self._customers: Dict[str, CustomerLoyalty] = {}
        self._transactions: List[LoyaltyTransaction] = []

        # Cargar datos
        self._load_data()

    def _ensure_data_directory(self):
        """Crear directorio de datos si no existe"""
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(f"{self.data_dir}/configs", exist_ok=True)
        os.makedirs(f"{self.data_dir}/customers", exist_ok=True)
        os.makedirs(f"{self.data_dir}/transactions", exist_ok=True)

    def _load_data(self):
        """Cargar datos desde archivos JSON"""
        try:
            # Cargar configuraciones
            configs_dir = f"{self.data_dir}/configs"
            if os.path.exists(configs_dir):
                for filename in os.listdir(configs_dir):
                    if filename.endswith('.json'):
                        filepath = os.path.join(configs_dir, filename)
                        with open(filepath, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            config = LoyaltyConfig(**data)
                            self._configs[config.restaurant_id] = config

            # Cargar clientes
            customers_dir = f"{self.data_dir}/customers"
            if os.path.exists(customers_dir):
                for filename in os.listdir(customers_dir):
                    if filename.endswith('.json'):
                        filepath = os.path.join(customers_dir, filename)
                        with open(filepath, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            customer = CustomerLoyalty(**data)
                            key = f"{customer.customer_phone}:{customer.restaurant_id}"
                            self._customers[key] = customer

            logger.info(f"[Loyalty] Cargados {len(self._configs)} configs, {len(self._customers)} clientes")

        except Exception as e:
            logger.error(f"[Loyalty] Error cargando datos: {e}")

    def _save_config(self, config: LoyaltyConfig):
        """Guardar configuración en archivo"""
        try:
            filepath = f"{self.data_dir}/configs/{config.restaurant_id}.json"
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(config.dict(), f, indent=2, default=str, ensure_ascii=False)
            self._configs[config.restaurant_id] = config
        except Exception as e:
            logger.error(f"[Loyalty] Error guardando config: {e}")

    def _save_customer(self, customer: CustomerLoyalty):
        """Guardar datos de cliente"""
        try:
            filename = f"{customer.customer_phone}_{customer.restaurant_id}.json"
            filepath = f"{self.data_dir}/customers/{filename}"
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(customer.dict(), f, indent=2, default=str, ensure_ascii=False)

            key = f"{customer.customer_phone}:{customer.restaurant_id}"
            self._customers[key] = customer
        except Exception as e:
            logger.error(f"[Loyalty] Error guardando customer: {e}")

    def _save_transaction(self, transaction: LoyaltyTransaction):
        """Guardar transacción"""
        try:
            filepath = f"{self.data_dir}/transactions/{transaction.transaction_id}.json"
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(transaction.dict(), f, indent=2, default=str, ensure_ascii=False)
            self._transactions.append(transaction)
        except Exception as e:
            logger.error(f"[Loyalty] Error guardando transacción: {e}")

    # ==========================================================================
    # CONFIGURACIÓN
    # ==========================================================================

    def get_config(self, restaurant_id: str) -> LoyaltyConfig:
        """Obtener configuración de loyalty para un restaurante"""
        if restaurant_id not in self._configs:
            # Crear configuración por defecto
            config = LoyaltyConfig(restaurant_id=restaurant_id)
            self._save_config(config)
            return config
        return self._configs[restaurant_id]

    def update_config(self, restaurant_id: str, updates: Dict[str, Any]) -> LoyaltyConfig:
        """Actualizar configuración"""
        config = self.get_config(restaurant_id)

        # Actualizar campos
        for key, value in updates.items():
            if hasattr(config, key) and value is not None:
                setattr(config, key, value)

        config.updated_at = datetime.utcnow()
        self._save_config(config)

        logger.info(f"[Loyalty] Config actualizada para {restaurant_id}")
        return config

    # ==========================================================================
    # GESTIÓN DE CLIENTES
    # ==========================================================================

    def get_customer_loyalty(
        self,
        customer_phone: str,
        restaurant_id: str,
        create_if_missing: bool = True
    ) -> Optional[CustomerLoyalty]:
        """Obtener o crear datos de loyalty de un cliente"""
        key = f"{customer_phone}:{restaurant_id}"

        if key in self._customers:
            return self._customers[key]

        if create_if_missing:
            customer = CustomerLoyalty(
                customer_phone=customer_phone,
                restaurant_id=restaurant_id
            )
            self._save_customer(customer)
            return customer

        return None

    def update_customer_tier(self, customer: CustomerLoyalty, config: LoyaltyConfig) -> Tuple[bool, Optional[str]]:
        """
        Actualizar tier del cliente basado en puntos lifetime.

        Returns:
            (tier_changed, new_tier_name)
        """
        old_tier = customer.current_tier
        new_tier = customer.calculate_tier(config)

        if old_tier != new_tier:
            customer.current_tier = new_tier
            logger.info(f"[Loyalty] {customer.customer_phone} subió de {old_tier.value} a {new_tier.value}")
            return True, new_tier.value

        return False, None

    # ==========================================================================
    # GANAR PUNTOS
    # ==========================================================================

    async def earn_points(
        self,
        request: EarnPointsRequest
    ) -> Dict[str, Any]:
        """
        Otorgar puntos por una compra.

        Returns:
            {
                "points_earned": 50,
                "total_points": 350,
                "current_tier": "plata",
                "tier_upgraded": False,
                "multiplier": 1.5
            }
        """
        try:
            config = self.get_config(request.restaurant_id)

            if not config.enabled:
                return {
                    "points_earned": 0,
                    "message": "Sistema de puntos deshabilitado"
                }

            # Obtener o crear cliente
            customer = self.get_customer_loyalty(
                request.customer_phone,
                request.restaurant_id,
                create_if_missing=True
            )

            # Actualizar datos del cliente
            if request.customer_name and not customer.customer_name:
                customer.customer_name = request.customer_name

            # Calcular puntos base
            points_base = int(request.order_total * config.points_per_currency)

            # Aplicar multiplicador por tier
            multiplier = customer.get_multiplier(config)
            points_earned = int(points_base * multiplier)

            # Bonus primera compra
            first_purchase_bonus = 0
            if customer.total_orders == 0 and config.first_purchase_bonus > 0:
                first_purchase_bonus = config.first_purchase_bonus
                points_earned += first_purchase_bonus

            # Actualizar puntos del cliente
            customer.available_points += points_earned
            customer.total_points += points_earned
            customer.lifetime_points += points_earned

            # Actualizar estadísticas
            customer.total_spent += request.order_total
            customer.total_orders += 1
            customer.average_order_value = customer.total_spent / customer.total_orders

            if not customer.first_purchase_date:
                customer.first_purchase_date = datetime.utcnow()
            customer.last_purchase_date = datetime.utcnow()
            customer.updated_at = datetime.utcnow()

            # Verificar upgrade de tier
            tier_upgraded, new_tier = self.update_customer_tier(customer, config)

            # Guardar cliente
            self._save_customer(customer)

            # Registrar transacción
            transaction = LoyaltyTransaction(
                transaction_id=str(uuid.uuid4()),
                customer_phone=customer.customer_phone,
                restaurant_id=request.restaurant_id,
                transaction_type=TransactionType.EARN,
                points_change=points_earned,
                points_balance_after=customer.available_points,
                order_id=request.order_id,
                order_total=request.order_total,
                description=f"Compra de ${request.order_total:.2f}",
                metadata={
                    "points_base": points_base,
                    "multiplier": multiplier,
                    "first_purchase_bonus": first_purchase_bonus
                }
            )
            self._save_transaction(transaction)

            logger.info(
                f"[Loyalty] {customer.customer_phone} ganó {points_earned} puntos "
                f"(${request.order_total:.2f}) - Total: {customer.available_points}"
            )

            return {
                "success": True,
                "points_earned": points_earned,
                "total_points": customer.available_points,
                "lifetime_points": customer.lifetime_points,
                "current_tier": customer.current_tier.value,
                "tier_upgraded": tier_upgraded,
                "new_tier": new_tier,
                "multiplier": multiplier,
                "first_purchase_bonus": first_purchase_bonus,
                "total_orders": customer.total_orders,
                "total_spent": customer.total_spent
            }

        except Exception as e:
            logger.error(f"[Loyalty] Error otorgando puntos: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    # ==========================================================================
    # CANJEAR PUNTOS
    # ==========================================================================

    async def redeem_points(
        self,
        request: RedeemPointsRequest
    ) -> RedeemPointsResponse:
        """
        Canjear puntos por descuento.

        Returns:
            RedeemPointsResponse con discount_amount, points_redeemed, etc.
        """
        try:
            config = self.get_config(request.restaurant_id)

            if not config.enabled:
                return RedeemPointsResponse(
                    success=False,
                    discount_amount=0,
                    points_redeemed=0,
                    points_remaining=0,
                    message="Sistema de puntos deshabilitado"
                )

            # Obtener cliente
            customer = self.get_customer_loyalty(
                request.customer_phone,
                request.restaurant_id,
                create_if_missing=False
            )

            if not customer:
                return RedeemPointsResponse(
                    success=False,
                    discount_amount=0,
                    points_redeemed=0,
                    points_remaining=0,
                    message="Cliente no encontrado en programa de fidelidad"
                )

            # Validaciones
            if request.points_to_redeem < config.min_points_to_redeem:
                return RedeemPointsResponse(
                    success=False,
                    discount_amount=0,
                    points_redeemed=0,
                    points_remaining=customer.available_points,
                    message=f"Mínimo {config.min_points_to_redeem} puntos para canjear"
                )

            if request.points_to_redeem > customer.available_points:
                return RedeemPointsResponse(
                    success=False,
                    discount_amount=0,
                    points_redeemed=0,
                    points_remaining=customer.available_points,
                    message=f"Puntos insuficientes. Disponibles: {customer.available_points}"
                )

            # Calcular descuento
            discount_amount = request.points_to_redeem * config.currency_per_point

            # Validar límite de descuento
            max_discount = request.order_total * (config.max_redeem_percentage / 100)
            if discount_amount > max_discount:
                # Ajustar puntos a canjear
                discount_amount = max_discount
                request.points_to_redeem = int(discount_amount / config.currency_per_point)

            # Redondear descuento
            discount_amount = round(discount_amount, 2)

            # Aplicar canje
            customer.available_points -= request.points_to_redeem
            customer.total_points -= request.points_to_redeem
            customer.updated_at = datetime.utcnow()

            # Guardar cliente
            self._save_customer(customer)

            # Registrar transacción
            transaction = LoyaltyTransaction(
                transaction_id=str(uuid.uuid4()),
                customer_phone=customer.customer_phone,
                restaurant_id=request.restaurant_id,
                transaction_type=TransactionType.REDEEM,
                points_change=-request.points_to_redeem,
                points_balance_after=customer.available_points,
                order_total=request.order_total,
                description=f"Canje de {request.points_to_redeem} puntos por ${discount_amount:.2f}",
                metadata={
                    "discount_amount": discount_amount,
                    "order_total": request.order_total
                }
            )
            self._save_transaction(transaction)

            logger.info(
                f"[Loyalty] {customer.customer_phone} canjeó {request.points_to_redeem} puntos "
                f"por ${discount_amount:.2f} - Restantes: {customer.available_points}"
            )

            return RedeemPointsResponse(
                success=True,
                discount_amount=discount_amount,
                points_redeemed=request.points_to_redeem,
                points_remaining=customer.available_points,
                message=f"¡Descuento de ${discount_amount:.2f} aplicado!"
            )

        except Exception as e:
            logger.error(f"[Loyalty] Error canjeando puntos: {e}")
            return RedeemPointsResponse(
                success=False,
                discount_amount=0,
                points_redeemed=0,
                points_remaining=0,
                message=f"Error: {str(e)}"
            )

    # ==========================================================================
    # CONSULTAS
    # ==========================================================================

    async def get_balance(
        self,
        customer_phone: str,
        restaurant_id: str
    ) -> LoyaltyBalanceResponse:
        """Obtener balance de puntos y datos de fidelidad"""
        config = self.get_config(restaurant_id)
        customer = self.get_customer_loyalty(customer_phone, restaurant_id, create_if_missing=True)

        # Calcular próximo tier
        next_tier = None
        points_to_next_tier = None

        if config.tiers_enabled:
            tiers_order = [TierLevel.BRONCE, TierLevel.PLATA, TierLevel.ORO, TierLevel.PLATINO]
            current_idx = tiers_order.index(customer.current_tier)

            if current_idx < len(tiers_order) - 1:
                next_tier_level = tiers_order[current_idx + 1]
                next_tier = next_tier_level.value
                threshold = config.tier_thresholds[next_tier]
                points_to_next_tier = threshold - customer.lifetime_points

        # Valor de los puntos en dinero
        points_value = customer.available_points * config.currency_per_point

        return LoyaltyBalanceResponse(
            customer_phone=customer_phone,
            restaurant_id=restaurant_id,
            available_points=customer.available_points,
            lifetime_points=customer.lifetime_points,
            current_tier=customer.current_tier.value,
            tier_benefits=config.tier_benefits.get(customer.current_tier.value, {}),
            points_value_in_currency=points_value,
            total_spent=customer.total_spent,
            total_orders=customer.total_orders,
            next_tier=next_tier,
            points_to_next_tier=points_to_next_tier if points_to_next_tier and points_to_next_tier > 0 else None
        )


# ==============================================================================
# SINGLETON INSTANCE
# ==============================================================================

_loyalty_handler_instance = None


def get_loyalty_handler() -> LoyaltyHandler:
    """Obtener instancia singleton del loyalty handler"""
    global _loyalty_handler_instance
    if _loyalty_handler_instance is None:
        _loyalty_handler_instance = LoyaltyHandler()
    return _loyalty_handler_instance
