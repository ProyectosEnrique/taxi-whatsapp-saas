"""
================================================================================
AGENT CONNECTOR
================================================================================
Conecta el Gateway con el Agente de Ventas IA existente.
================================================================================
"""

from typing import Dict, Any, Optional
import aiohttp
import logging
import os

logger = logging.getLogger(__name__)


class AgentConnector:
    """
    Conector al Agente de Ventas IA.

    Se conecta con el servicio voice-assistant existente
    para procesar los mensajes y generar respuestas.
    """

    def __init__(self):
        self.agent_url = os.getenv(
            "SALES_AGENT_URL",
            "http://voice-assistant:5000"
        )
        self.middleware_url = os.getenv(
            "POS_MIDDLEWARE_URL",
            "http://pos-middleware:8090"
        )
        self.timeout = aiohttp.ClientTimeout(total=60)

    async def send_message(
        self,
        session_id: str,
        message: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Enviar mensaje al agente de ventas.

        Args:
            session_id: ID de la sesión
            message: Mensaje del cliente
            context: Contexto de la conversación (mesa, carrito, etc.)

        Returns:
            Respuesta del agente con texto y acciones
        """
        try:
            # Intentar conectar con el agente de ventas
            response = await self._call_sales_agent(session_id, message, context)

            if response:
                return response

            # Si falla, usar respuesta de fallback
            return await self._handle_fallback(message, context)

        except Exception as e:
            logger.error(f"[AgentConnector] Error: {e}")
            return await self._handle_fallback(message, context)

    async def _call_sales_agent(
        self,
        session_id: str,
        message: str,
        context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Llamar al servicio de agente de ventas"""
        url = f"{self.agent_url}/api/v1/sales/message"

        payload = {
            "session_id": session_id,
            "message": message,
            "channel": "whatsapp",
            "context": context
        }

        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()

                        return {
                            "text": data.get("response", data.get("text", "")),
                            "buttons": data.get("buttons"),
                            "list": data.get("list"),
                            "image": data.get("image"),
                            "multi_product": data.get("multi_product"),
                            "single_product": data.get("single_product"),
                            "cart_update": data.get("cart"),
                            "new_state": data.get("state"),
                            "order_id": data.get("order_id")
                        }
                    else:
                        logger.warning(f"[AgentConnector] Agent returned {response.status}")
                        return None

        except aiohttp.ClientError as e:
            logger.warning(f"[AgentConnector] No se pudo conectar al agente: {e}")
            return None

    async def _handle_fallback(
        self,
        message: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Manejo de fallback cuando el agente no está disponible.
        Proporciona respuestas básicas.
        """
        table_id = context.get("table_id")
        restaurant_id = context.get("restaurant_id")
        state = context.get("state", "initial")

        # Si es código de mesa
        if context.get("parsed", {}).get("is_table_code"):
            return {
                "text": (
                    f"¡Hola! Bienvenido 🌮\n"
                    f"Estás en la Mesa {table_id}.\n\n"
                    f"¿En qué te puedo ayudar?\n"
                    f"• Ver menú\n"
                    f"• Hacer un pedido\n"
                    f"• Ver promociones"
                ),
                "buttons": [
                    {"id": "menu", "title": "📋 Ver menú"},
                    {"id": "order", "title": "🍽️ Ordenar"},
                    {"id": "promos", "title": "🔥 Promociones"}
                ],
                "new_state": "greeting"
            }

        # Respuestas básicas por estado
        message_lower = message.lower()

        if state == "initial":
            return {
                "text": (
                    "¡Hola! Soy el asistente virtual.\n"
                    "Escanea el código QR de tu mesa para comenzar, "
                    "o dime en qué te puedo ayudar."
                ),
                "new_state": "greeting"
            }

        if "menú" in message_lower or "menu" in message_lower:
            return {
                "text": (
                    "📋 Nuestro menú:\n\n"
                    "🌮 *TACOS*\n"
                    "• Pastor - $25\n"
                    "• Suadero - $25\n"
                    "• Bistec - $28\n\n"
                    "🍔 *HAMBURGUESAS*\n"
                    "• Clásica - $95\n"
                    "• BBQ - $120\n\n"
                    "🥤 *BEBIDAS*\n"
                    "• Refresco - $25\n"
                    "• Agua - $20\n\n"
                    "_Dime qué quieres ordenar_"
                ),
                "new_state": "browsing"
            }

        if "promocion" in message_lower or "promo" in message_lower:
            return {
                "text": (
                    "🔥 *Promociones de hoy:*\n\n"
                    "• 2x1 en cervezas (4-7pm)\n"
                    "• 20% en hamburguesas (martes)\n"
                    "• Postre gratis en combos\n\n"
                    "_¿Te interesa alguna?_"
                ),
                "new_state": "browsing"
            }

        if any(word in message_lower for word in ["gracias", "adios", "bye"]):
            return {
                "text": (
                    "¡Gracias por tu visita! 😊\n"
                    "Esperamos verte pronto.\n"
                    "¡Buen provecho!"
                ),
                "new_state": "completed"
            }

        # Respuesta genérica
        return {
            "text": (
                "Entendido. ¿En qué más te puedo ayudar?\n\n"
                "Puedes:\n"
                "• Ver el menú\n"
                "• Hacer un pedido\n"
                "• Preguntar por promociones"
            ),
            "buttons": [
                {"id": "menu", "title": "📋 Menú"},
                {"id": "help", "title": "❓ Ayuda"}
            ]
        }

    async def send_order_to_pos(
        self,
        order_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Enviar orden al middleware POS.
        """
        url = f"{self.middleware_url}/api/v1/orders"

        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.post(url, json=order_data) as response:
                    result = await response.json()

                    if result.get("success"):
                        logger.info(f"[AgentConnector] Orden enviada: {result.get('order_number')}")
                    else:
                        logger.error(f"[AgentConnector] Error enviando orden: {result.get('error')}")

                    return result

        except Exception as e:
            logger.error(f"[AgentConnector] Error conectando a middleware: {e}")
            return {"success": False, "error": str(e)}

    async def get_menu(self, restaurant_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtener menú del restaurante.
        """
        url = f"{self.middleware_url}/api/v1/restaurants/{restaurant_id}/menu"

        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        return await response.json()
                    return None

        except Exception as e:
            logger.error(f"[AgentConnector] Error obteniendo menú: {e}")
            return None
