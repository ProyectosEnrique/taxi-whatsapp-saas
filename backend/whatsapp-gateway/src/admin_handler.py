"""
================================================================================
ADMIN HANDLER - WhatsApp Gateway
================================================================================
Maneja mensajes de administradores por WhatsApp.

Permite a los administradores:
- Consultar métricas desde WhatsApp
- Crear y gestionar promociones
- Enviar broadcasts a clientes
- Ejecutar acciones administrativas

Los administradores son identificados por números autorizados en .env
================================================================================
"""

import logging
import aiohttp
import os
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class AdminHandler:
    """
    Handler de mensajes para administradores por WhatsApp.

    Verifica que el número esté autorizado y rutea al AdminAgent.
    """

    def __init__(self):
        # URL del voice-assistant (donde está el AdminAgent)
        self.voice_assistant_url = os.getenv(
            "VOICE_ASSISTANT_URL",
            "http://voice-assistant:8000"
        )

        # Números autorizados
        authorized_numbers = os.getenv('WHATSAPP_ADMIN_NUMBERS', '')
        self.authorized_numbers = [
            n.strip() for n in authorized_numbers.split(',') if n.strip()
        ]

        # Modo desarrollo (permite todos los números si no hay autorizados)
        if not self.authorized_numbers:
            logger.warning("[AdminHandler] No hay números autorizados. Modo desarrollo activado.")
            self.dev_mode = True
        else:
            self.dev_mode = False
            logger.info(f"[AdminHandler] {len(self.authorized_numbers)} números autorizados")

        self.timeout = aiohttp.ClientTimeout(total=60)

    def is_admin(self, phone: str) -> bool:
        """
        Verifica si un número de teléfono pertenece a un administrador.

        Args:
            phone: Número de teléfono en formato internacional

        Returns:
            True si es admin, False si no
        """
        if not phone:
            return False

        # Normalizar número (quitar espacios, guiones, +)
        normalized = phone.replace('+', '').replace(' ', '').replace('-', '')

        for authorized in self.authorized_numbers:
            auth_normalized = authorized.replace('+', '').replace(' ', '').replace('-', '')
            if normalized == auth_normalized or normalized.endswith(auth_normalized):
                return True

        return False

    async def process_admin_message(
        self,
        phone: str,
        message: str,
        customer_name: str = "Admin"
    ) -> Dict[str, Any]:
        """
        Procesa un mensaje del administrador.

        Args:
            phone: Número del admin
            message: Mensaje de texto
            customer_name: Nombre del admin (opcional)

        Returns:
            Respuesta del AdminAgent formateada para WhatsApp
        """
        # Generar session_id único para este admin
        session_id = f"admin_{phone.replace('+', '').replace(' ', '')}"

        logger.info(f"[AdminHandler] Mensaje de admin {phone}: {message[:50]}...")

        try:
            # Llamar al AdminAgent via el endpoint de admin/whatsapp
            url = f"{self.voice_assistant_url}/api/admin/whatsapp/message"

            payload = {
                "session_id": session_id,
                "message": message,
                "context": {
                    "phone": phone,
                    "admin_name": customer_name,
                    "channel": "whatsapp"
                }
            }

            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()

                        return {
                            "success": True,
                            "text": data.get("response", data.get("text", "")),
                            "buttons": data.get("buttons"),
                            "visual_data": data.get("visual_data")
                        }
                    else:
                        error_text = await response.text()
                        logger.error(f"[AdminHandler] Error del AdminAgent: {error_text}")

                        return {
                            "success": False,
                            "text": "Lo siento, tuve un problema procesando tu solicitud. ¿Podrías intentar de nuevo?",
                            "error": error_text
                        }

        except aiohttp.ClientError as e:
            logger.error(f"[AdminHandler] Error conectando a AdminAgent: {e}")

            # Fallback cuando el AdminAgent no está disponible
            return {
                "success": False,
                "text": (
                    "⚠️ El sistema administrativo no está disponible en este momento.\n\n"
                    "Por favor, intenta de nuevo en unos minutos o accede al dashboard web."
                )
            }

        except Exception as e:
            logger.error(f"[AdminHandler] Error procesando mensaje admin: {e}", exc_info=True)

            return {
                "success": False,
                "text": "Ocurrió un error inesperado. Por favor, contacta al soporte técnico."
            }

    def get_welcome_message(self) -> str:
        """
        Mensaje de bienvenida para admins.

        Returns:
            Mensaje de bienvenida
        """
        return (
            "👋 Bienvenido al *Panel de Administración* por WhatsApp\n\n"
            "Puedes consultar métricas, gestionar promociones y más.\n\n"
            "*Ejemplos de comandos:*\n"
            "• ¿Cuántas ventas llevamos hoy?\n"
            "• ¿Cuál es el producto más vendido?\n"
            "• Crea una promoción 2x1 en hamburguesas\n"
            "• Envía promo a clientes frecuentes\n\n"
            "Escribe lo que necesites y te ayudaré."
        )


# Singleton
_admin_handler = None


def get_admin_handler() -> AdminHandler:
    """Obtiene instancia singleton del AdminHandler"""
    global _admin_handler
    if _admin_handler is None:
        _admin_handler = AdminHandler()
    return _admin_handler
