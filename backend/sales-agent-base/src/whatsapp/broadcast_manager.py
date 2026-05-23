"""
================================================================================
WHATSAPP BROADCAST MANAGER
================================================================================
Gestiona el envío de mensajes broadcast a clientes por WhatsApp.

Funcionalidades:
- Envío de promociones a segmentos de clientes
- Tracking de entregas y lecturas
- Rate limiting para evitar spam
- Personalización de mensajes
================================================================================
"""

import logging
import asyncio
import aiohttp
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass
import os

logger = logging.getLogger(__name__)


@dataclass
class BroadcastResult:
    """Resultado de un broadcast"""
    campaign_id: str
    total_sent: int
    successful: int
    failed: int
    customer_segment: str
    created_at: datetime
    failed_numbers: List[str]


class WhatsAppBroadcastManager:
    """
    Gestor de broadcasts de WhatsApp.

    Se conecta con el WhatsApp Gateway para enviar mensajes
    a múltiples clientes de forma controlada.
    """

    def __init__(self):
        self.gateway_url = os.getenv(
            "WHATSAPP_GATEWAY_URL",
            "http://whatsapp-gateway:8000"
        )
        self.max_concurrent = 5  # Máximo de mensajes simultáneos
        self.delay_between_messages = 1  # Segundos entre mensajes

        # Stats de broadcasts
        self.campaigns = {}  # campaign_id -> BroadcastResult

    async def send_promotion(
        self,
        promotion_id: str,
        audience_filter: Dict,
        custom_message: Optional[str] = None,
        personalize: bool = True
    ) -> BroadcastResult:
        """
        Envía una promoción a un segmento de clientes.

        Args:
            promotion_id: ID de la promoción a enviar
            audience_filter: Filtro de audiencia (ver CustomerSegmenter)
            custom_message: Mensaje personalizado (opcional)
            personalize: Si debe personalizar el mensaje por cliente

        Returns:
            BroadcastResult con estadísticas del envío
        """
        import uuid
        from .customer_segmentation import get_customer_segmenter
        from .message_personalizer import get_message_personalizer

        campaign_id = str(uuid.uuid4())

        logger.info(f"[Broadcast] Iniciando campaña {campaign_id} para promo {promotion_id}")

        try:
            # 1. Obtener clientes según filtro
            segmenter = get_customer_segmenter()
            customers = await segmenter.get_customers(audience_filter)

            if not customers:
                logger.warning(f"[Broadcast] No hay clientes que cumplan el filtro: {audience_filter}")
                return BroadcastResult(
                    campaign_id=campaign_id,
                    total_sent=0,
                    successful=0,
                    failed=0,
                    customer_segment=audience_filter.get('segment', 'custom'),
                    created_at=datetime.now(),
                    failed_numbers=[]
                )

            # 2. Obtener datos de la promoción
            promotion = await self._get_promotion_data(promotion_id)

            # 3. Preparar mensaje base
            if custom_message:
                message_template = custom_message
            else:
                message_template = self._format_promotion_message(promotion)

            # 4. Enviar a cada cliente
            personalizer = get_message_personalizer()

            successful = 0
            failed = 0
            failed_numbers = []

            # Enviar en lotes para no saturar
            for i in range(0, len(customers), self.max_concurrent):
                batch = customers[i:i + self.max_concurrent]

                tasks = []
                for customer in batch:
                    # Personalizar mensaje si está habilitado
                    if personalize:
                        message = personalizer.personalize(
                            message_template,
                            customer,
                            promotion
                        )
                    else:
                        message = message_template

                    # Agregar botones de acción
                    buttons = [
                        {"id": "order_now", "title": "Ordenar ahora"},
                        {"id": "view_menu", "title": "Ver menú"}
                    ]

                    tasks.append(
                        self._send_to_customer(customer['phone'], message, buttons)
                    )

                # Ejecutar batch
                results = await asyncio.gather(*tasks, return_exceptions=True)

                # Procesar resultados
                for customer, result in zip(batch, results):
                    if isinstance(result, Exception):
                        logger.error(f"[Broadcast] Error enviando a {customer['phone']}: {result}")
                        failed += 1
                        failed_numbers.append(customer['phone'])
                    elif result.get('success'):
                        successful += 1
                    else:
                        failed += 1
                        failed_numbers.append(customer['phone'])

                # Delay entre lotes
                if i + self.max_concurrent < len(customers):
                    await asyncio.sleep(self.delay_between_messages)

            # 5. Registrar campaña
            broadcast_result = BroadcastResult(
                campaign_id=campaign_id,
                total_sent=len(customers),
                successful=successful,
                failed=failed,
                customer_segment=audience_filter.get('segment', 'custom'),
                created_at=datetime.now(),
                failed_numbers=failed_numbers
            )

            self.campaigns[campaign_id] = broadcast_result

            # 6. Guardar analytics
            await self._save_campaign_analytics(campaign_id, broadcast_result, promotion_id)

            logger.info(
                f"[Broadcast] Campaña {campaign_id} completada: "
                f"{successful}/{len(customers)} exitosos"
            )

            return broadcast_result

        except Exception as e:
            logger.error(f"[Broadcast] Error en campaña {campaign_id}: {e}", exc_info=True)
            raise

    async def send_custom_broadcast(
        self,
        message: str,
        audience_filter: Dict,
        buttons: Optional[List[Dict]] = None
    ) -> BroadcastResult:
        """
        Envía un mensaje custom (no promoción) a clientes.

        Args:
            message: Mensaje a enviar
            audience_filter: Filtro de audiencia
            buttons: Botones opcionales

        Returns:
            BroadcastResult con estadísticas
        """
        import uuid
        from .customer_segmentation import get_customer_segmenter

        campaign_id = str(uuid.uuid4())

        logger.info(f"[Broadcast] Iniciando broadcast custom {campaign_id}")

        try:
            # Obtener clientes
            segmenter = get_customer_segmenter()
            customers = await segmenter.get_customers(audience_filter)

            if not customers:
                return BroadcastResult(
                    campaign_id=campaign_id,
                    total_sent=0,
                    successful=0,
                    failed=0,
                    customer_segment=audience_filter.get('segment', 'custom'),
                    created_at=datetime.now(),
                    failed_numbers=[]
                )

            # Enviar a cada cliente
            successful = 0
            failed = 0
            failed_numbers = []

            for i in range(0, len(customers), self.max_concurrent):
                batch = customers[i:i + self.max_concurrent]

                tasks = [
                    self._send_to_customer(customer['phone'], message, buttons)
                    for customer in batch
                ]

                results = await asyncio.gather(*tasks, return_exceptions=True)

                for customer, result in zip(batch, results):
                    if isinstance(result, Exception) or not result.get('success'):
                        failed += 1
                        failed_numbers.append(customer['phone'])
                    else:
                        successful += 1

                if i + self.max_concurrent < len(customers):
                    await asyncio.sleep(self.delay_between_messages)

            broadcast_result = BroadcastResult(
                campaign_id=campaign_id,
                total_sent=len(customers),
                successful=successful,
                failed=failed,
                customer_segment=audience_filter.get('segment', 'custom'),
                created_at=datetime.now(),
                failed_numbers=failed_numbers
            )

            self.campaigns[campaign_id] = broadcast_result

            return broadcast_result

        except Exception as e:
            logger.error(f"[Broadcast] Error en custom broadcast: {e}", exc_info=True)
            raise

    async def _send_to_customer(
        self,
        phone: str,
        message: str,
        buttons: Optional[List[Dict]] = None
    ) -> Dict:
        """Envía mensaje a un cliente individual"""
        url = f"{self.gateway_url}/api/send"

        payload = {
            "to": phone,
            "message": message,
            "buttons": buttons
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result
                    else:
                        error_text = await response.text()
                        logger.error(f"[Broadcast] Error enviando a {phone}: {error_text}")
                        return {"success": False, "error": error_text}
        except Exception as e:
            logger.error(f"[Broadcast] Excepción enviando a {phone}: {e}")
            return {"success": False, "error": str(e)}

    async def _get_promotion_data(self, promotion_id: str) -> Dict:
        """Obtiene datos de una promoción desde la DB"""
        # TODO: Integrar con la DB real de promociones
        # Por ahora retornamos mock
        return {
            "id": promotion_id,
            "name": "Promoción Especial",
            "description": "Oferta limitada",
            "promotion_type": "percentage",
            "discount_value": 20
        }

    def _format_promotion_message(self, promotion: Dict) -> str:
        """Formatea mensaje de promoción"""
        promo_type = promotion.get('promotion_type')
        name = promotion.get('name', 'Promoción especial')
        description = promotion.get('description', '')

        if promo_type == '2x1':
            message = f"🔥 *{name}*\n\n{description}\n\n¡Válido solo por tiempo limitado!"
        elif promo_type == 'percentage':
            discount = promotion.get('discount_value', 0)
            message = f"🔥 *{name}*\n\n{discount}% de descuento\n{description}\n\n¡Aprovecha esta oferta!"
        elif promo_type == 'fixed':
            discount = promotion.get('discount_value', 0)
            message = f"🔥 *{name}*\n\n${discount} de descuento\n{description}\n\n¡No te lo pierdas!"
        else:
            message = f"🔥 *{name}*\n\n{description}"

        return message

    async def _save_campaign_analytics(
        self,
        campaign_id: str,
        result: BroadcastResult,
        promotion_id: Optional[str] = None
    ):
        """Guarda analytics de la campaña"""
        # TODO: Guardar en DB para analytics
        logger.info(
            f"[Broadcast] Analytics - Campaña {campaign_id}: "
            f"Enviados={result.total_sent}, Exitosos={result.successful}, Fallidos={result.failed}"
        )

    def get_campaign_stats(self, campaign_id: str) -> Optional[BroadcastResult]:
        """Obtiene estadísticas de una campaña"""
        return self.campaigns.get(campaign_id)

    def get_all_campaigns(self) -> List[BroadcastResult]:
        """Obtiene todas las campañas"""
        return list(self.campaigns.values())


# Singleton
_broadcast_manager = None


def get_broadcast_manager() -> WhatsAppBroadcastManager:
    """Obtiene instancia singleton del BroadcastManager"""
    global _broadcast_manager
    if _broadcast_manager is None:
        _broadcast_manager = WhatsAppBroadcastManager()
    return _broadcast_manager
