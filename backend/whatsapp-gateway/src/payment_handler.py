"""
================================================================================
PAYMENT HANDLER - Integración con Pasarelas de Pago
================================================================================
Maneja pagos con Stripe y Mercado Pago para checkout desde web
================================================================================
"""

from typing import Dict, Any, Optional, List
import logging
import os
from enum import Enum

logger = logging.getLogger(__name__)


class PaymentProvider(Enum):
    """Proveedores de pago soportados"""
    STRIPE = "stripe"
    MERCADOPAGO = "mercadopago"
    CASH = "cash"
    TRANSFER = "transfer"


class PaymentStatus(Enum):
    """Estados de pago"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


class PaymentHandler:
    """
    Manejador de pagos multi-provider.

    Soporta:
    - Stripe (tarjetas internacionales)
    - Mercado Pago (México/LATAM)
    - Efectivo (cash on delivery)
    - Transferencia bancaria
    """

    def __init__(self):
        self.stripe_enabled = self._check_stripe_config()
        self.mercadopago_enabled = self._check_mercadopago_config()

    def _check_stripe_config(self) -> bool:
        """Verificar si Stripe está configurado"""
        api_key = os.getenv("STRIPE_SECRET_KEY")
        return api_key is not None and api_key != ""

    def _check_mercadopago_config(self) -> bool:
        """Verificar si Mercado Pago está configurado"""
        access_token = os.getenv("MERCADOPAGO_ACCESS_TOKEN")
        return access_token is not None and access_token != ""

    # ==========================================================================
    # STRIPE INTEGRATION
    # ==========================================================================

    async def create_stripe_payment_intent(
        self,
        amount: float,
        currency: str = "mxn",
        customer_email: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Crear Payment Intent en Stripe.

        Args:
            amount: Monto en pesos (se convierte a centavos)
            currency: Moneda (mxn, usd)
            customer_email: Email del cliente
            metadata: Metadata adicional (order_id, phone, etc.)

        Returns:
            {
                "client_secret": "pi_xxx_secret_xxx",
                "payment_intent_id": "pi_xxx",
                "amount": 50000,
                "currency": "mxn"
            }
        """
        if not self.stripe_enabled:
            raise ValueError("Stripe no está configurado")

        try:
            import stripe
            stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

            # Convertir a centavos
            amount_cents = int(amount * 100)

            # Crear Payment Intent
            intent = stripe.PaymentIntent.create(
                amount=amount_cents,
                currency=currency.lower(),
                receipt_email=customer_email,
                metadata=metadata or {},
                automatic_payment_methods={"enabled": True}
            )

            logger.info(f"[Stripe] Payment Intent creado: {intent.id} - ${amount} {currency.upper()}")

            return {
                "client_secret": intent.client_secret,
                "payment_intent_id": intent.id,
                "amount": amount_cents,
                "currency": currency,
                "status": intent.status
            }

        except Exception as e:
            logger.error(f"[Stripe] Error creando Payment Intent: {e}")
            raise

    async def verify_stripe_payment(
        self,
        payment_intent_id: str
    ) -> Dict[str, Any]:
        """
        Verificar estado de un pago en Stripe.

        Returns:
            {
                "status": "succeeded",
                "amount": 50000,
                "currency": "mxn",
                "metadata": {...}
            }
        """
        if not self.stripe_enabled:
            raise ValueError("Stripe no está configurado")

        try:
            import stripe
            stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

            intent = stripe.PaymentIntent.retrieve(payment_intent_id)

            return {
                "status": intent.status,
                "amount": intent.amount / 100,  # Convertir de centavos
                "currency": intent.currency,
                "metadata": intent.metadata,
                "payment_method": intent.payment_method
            }

        except Exception as e:
            logger.error(f"[Stripe] Error verificando pago: {e}")
            raise

    # ==========================================================================
    # MERCADO PAGO INTEGRATION
    # ==========================================================================

    async def create_mercadopago_preference(
        self,
        title: str,
        amount: float,
        quantity: int = 1,
        back_urls: Optional[Dict[str, str]] = None,
        auto_return: str = "approved",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Crear Preferencia de Pago en Mercado Pago.

        Args:
            title: Título del producto/pedido
            amount: Precio unitario
            quantity: Cantidad
            back_urls: URLs de retorno (success, failure, pending)
            auto_return: Auto-redirección (approved, all)
            metadata: Metadata adicional

        Returns:
            {
                "preference_id": "123456789-xxx",
                "init_point": "https://www.mercadopago.com.mx/checkout/...",
                "sandbox_init_point": "https://sandbox.mercadopago.com.mx/..."
            }
        """
        if not self.mercadopago_enabled:
            raise ValueError("Mercado Pago no está configurado")

        try:
            import mercadopago
            sdk = mercadopago.SDK(os.getenv("MERCADOPAGO_ACCESS_TOKEN"))

            # Preparar item
            preference_data = {
                "items": [
                    {
                        "title": title,
                        "quantity": quantity,
                        "unit_price": float(amount),
                        "currency_id": "MXN"
                    }
                ],
                "auto_return": auto_return,
                "metadata": metadata or {}
            }

            # URLs de retorno
            if back_urls:
                preference_data["back_urls"] = back_urls

            # Crear preferencia
            preference_response = sdk.preference().create(preference_data)
            preference = preference_response["response"]

            logger.info(f"[MercadoPago] Preferencia creada: {preference['id']} - ${amount} MXN")

            return {
                "preference_id": preference["id"],
                "init_point": preference["init_point"],
                "sandbox_init_point": preference.get("sandbox_init_point"),
                "status": "created"
            }

        except Exception as e:
            logger.error(f"[MercadoPago] Error creando preferencia: {e}")
            raise

    async def verify_mercadopago_payment(
        self,
        payment_id: str
    ) -> Dict[str, Any]:
        """
        Verificar estado de un pago en Mercado Pago.

        Returns:
            {
                "status": "approved",
                "status_detail": "accredited",
                "amount": 500.00,
                "currency": "MXN",
                "metadata": {...}
            }
        """
        if not self.mercadopago_enabled:
            raise ValueError("Mercado Pago no está configurado")

        try:
            import mercadopago
            sdk = mercadopago.SDK(os.getenv("MERCADOPAGO_ACCESS_TOKEN"))

            payment_response = sdk.payment().get(payment_id)
            payment = payment_response["response"]

            return {
                "status": payment["status"],
                "status_detail": payment.get("status_detail"),
                "amount": payment["transaction_amount"],
                "currency": payment["currency_id"],
                "metadata": payment.get("metadata", {}),
                "payment_method": payment.get("payment_method_id")
            }

        except Exception as e:
            logger.error(f"[MercadoPago] Error verificando pago: {e}")
            raise

    # ==========================================================================
    # MÉTODOS GENÉRICOS
    # ==========================================================================

    async def process_payment(
        self,
        provider: str,
        amount: float,
        order_id: str,
        customer_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Procesar pago de forma genérica.

        Args:
            provider: "stripe", "mercadopago", "cash", "transfer"
            amount: Monto total
            order_id: ID de la orden
            customer_data: Datos del cliente (phone, email, name)

        Returns:
            {
                "status": "completed",
                "payment_id": "xxx",
                "provider": "stripe",
                "amount": 500.00
            }
        """
        provider = provider.lower()

        # Efectivo - no requiere procesamiento online
        if provider == PaymentProvider.CASH.value:
            return {
                "status": PaymentStatus.PENDING.value,
                "payment_id": f"CASH-{order_id}",
                "provider": provider,
                "amount": amount,
                "message": "Pago en efectivo al recibir"
            }

        # Transferencia - generar datos bancarios
        if provider == PaymentProvider.TRANSFER.value:
            return {
                "status": PaymentStatus.PENDING.value,
                "payment_id": f"TRANSFER-{order_id}",
                "provider": provider,
                "amount": amount,
                "bank_details": {
                    "bank": "BBVA Bancomer",
                    "clabe": "012180001234567890",
                    "reference": order_id
                },
                "message": "Realiza la transferencia y envía comprobante"
            }

        # Stripe
        if provider == PaymentProvider.STRIPE.value:
            result = await self.create_stripe_payment_intent(
                amount=amount,
                customer_email=customer_data.get("email"),
                metadata={
                    "order_id": order_id,
                    "phone": customer_data.get("phone"),
                    "customer_name": customer_data.get("name")
                }
            )
            return {
                "status": PaymentStatus.PROCESSING.value,
                "payment_id": result["payment_intent_id"],
                "provider": provider,
                "amount": amount,
                "client_secret": result["client_secret"]
            }

        # Mercado Pago
        if provider == PaymentProvider.MERCADOPAGO.value:
            result = await self.create_mercadopago_preference(
                title=f"Pedido #{order_id}",
                amount=amount,
                metadata={
                    "order_id": order_id,
                    "phone": customer_data.get("phone")
                }
            )
            return {
                "status": PaymentStatus.PROCESSING.value,
                "payment_id": result["preference_id"],
                "provider": provider,
                "amount": amount,
                "checkout_url": result["init_point"]
            }

        raise ValueError(f"Proveedor de pago no soportado: {provider}")

    def get_available_providers(self, restaurant_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Obtener proveedores de pago disponibles.

        Args:
            restaurant_id: ID del restaurante/tienda (para detectar modo demo)

        Returns:
            [
                {"id": "stripe", "name": "Tarjeta", "enabled": True},
                {"id": "mercadopago", "name": "Mercado Pago", "enabled": True},
                {"id": "cash", "name": "Efectivo", "enabled": True},
                {"id": "transfer", "name": "Transferencia", "enabled": True}
            ]
        """
        # MODO DEMO: Solo mostrar efectivo
        if restaurant_id and restaurant_id.startswith("demo_"):
            return [
                {
                    "id": PaymentProvider.CASH.value,
                    "name": "Pago en Efectivo (DEMO)",
                    "enabled": True,
                    "icon": "💵",
                    "note": "Modo demostración - No se procesarán pagos reales"
                }
            ]

        # MODO NORMAL: Todos los proveedores
        return [
            {
                "id": PaymentProvider.STRIPE.value,
                "name": "Tarjeta de Crédito/Débito",
                "enabled": self.stripe_enabled,
                "icon": "💳"
            },
            {
                "id": PaymentProvider.MERCADOPAGO.value,
                "name": "Mercado Pago",
                "enabled": self.mercadopago_enabled,
                "icon": "💙"
            },
            {
                "id": PaymentProvider.CASH.value,
                "name": "Pago en Efectivo",
                "enabled": True,
                "icon": "💵"
            },
            {
                "id": PaymentProvider.TRANSFER.value,
                "name": "Transferencia Bancaria",
                "enabled": True,
                "icon": "🏦"
            }
        ]


# ==============================================================================
# SINGLETON INSTANCE
# ==============================================================================

_payment_handler_instance = None


def get_payment_handler() -> PaymentHandler:
    """Obtener instancia singleton del payment handler"""
    global _payment_handler_instance
    if _payment_handler_instance is None:
        _payment_handler_instance = PaymentHandler()
    return _payment_handler_instance
