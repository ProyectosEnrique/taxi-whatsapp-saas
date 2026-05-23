"""
================================================================================
ADMIN AGENT CHANNELS
================================================================================
Gestiona múltiples canales de comunicación para el AdminAgent.

Canales soportados:
- web: Dashboard web (interfaz gráfica)
- voice: Asistente de voz (web)
- whatsapp: WhatsApp móvil (nuevo)

Permite al administrador interactuar con el agente desde cualquier canal.
================================================================================
"""

import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ChannelResponse:
    """Respuesta adaptada para un canal específico"""
    text: str
    visual_data: Optional[Dict] = None
    buttons: Optional[list] = None
    requires_confirmation: bool = False


class BaseChannel:
    """Clase base para canales de AdminAgent"""

    def __init__(self, admin_agent):
        self.admin = admin_agent

    async def process(self, message: str, session_id: str, context: Dict = None) -> ChannelResponse:
        """Procesa mensaje del admin"""
        raise NotImplementedError


class WebChannel(BaseChannel):
    """
    Canal Web (Dashboard).

    Soporta UI rica con gráficos, tablas, y componentes interactivos.
    """

    async def process(self, message: str, session_id: str, context: Dict = None) -> ChannelResponse:
        """Procesa mensaje desde el dashboard web"""
        # Procesar con AdminAgent core
        result = await self.admin.process_message(
            session_id=session_id,
            message=message,
            channel='web',
            context=context or {}
        )

        # Para web, retornar con visual_data completo
        return ChannelResponse(
            text=result.response_text,
            visual_data=result.visual_data,
            buttons=None,  # Web usa UI nativa, no botones de WhatsApp
            requires_confirmation=result.requires_confirmation if hasattr(result, 'requires_confirmation') else False
        )


class VoiceChannel(BaseChannel):
    """
    Canal de Voz (Web con micrófono).

    Respuestas optimizadas para audio (cortas y claras).
    """

    async def process(self, message: str, session_id: str, context: Dict = None) -> ChannelResponse:
        """Procesa mensaje de voz"""
        result = await self.admin.process_message(
            session_id=session_id,
            message=message,
            channel='voice',
            context=context or {}
        )

        # Para voz, simplificar respuesta
        simplified_text = self._simplify_for_voice(result.response_text, result.visual_data)

        return ChannelResponse(
            text=simplified_text,
            visual_data=None,  # No visual data en voz
            buttons=None,
            requires_confirmation=result.requires_confirmation if hasattr(result, 'requires_confirmation') else False
        )

    def _simplify_for_voice(self, text: str, visual_data: Optional[Dict]) -> str:
        """Simplifica respuesta para voz"""
        # Si hay visual data, convertir a texto simple
        if visual_data:
            visual_type = visual_data.get('type')

            if visual_type == 'sales_summary':
                data = visual_data.get('data', {})
                text += f" Ventas: ${data.get('total_sales', 0)}. Órdenes: {data.get('order_count', 0)}."

            elif visual_type == 'top_products_chart':
                products = visual_data.get('data', [])[:3]
                if products:
                    text += " Los más vendidos son: "
                    text += ", ".join([p['name'] for p in products])

        return text


class WhatsAppChannel(BaseChannel):
    """
    Canal de WhatsApp (Móvil).

    Permite al admin gestionar el restaurante desde WhatsApp.
    Soporta consultas, creación de promociones y broadcasts.
    """

    def __init__(self, admin_agent):
        super().__init__(admin_agent)

        # Números de teléfono autorizados (admins)
        import os
        authorized_numbers = os.getenv('WHATSAPP_ADMIN_NUMBERS', '')
        self.authorized_numbers = [
            n.strip() for n in authorized_numbers.split(',') if n.strip()
        ]

        # Fallback: permitir cualquier número en desarrollo
        if not self.authorized_numbers:
            logger.warning("[WhatsAppChannel] No hay números autorizados configurados. Modo desarrollo activado.")
            self.dev_mode = True
        else:
            self.dev_mode = False
            logger.info(f"[WhatsAppChannel] Números autorizados: {len(self.authorized_numbers)}")

    async def process(self, message: str, session_id: str, context: Dict = None) -> ChannelResponse:
        """
        Procesa mensaje del admin desde WhatsApp.

        Args:
            message: Mensaje del admin
            session_id: ID de sesión
            context: Contexto adicional (debe incluir 'phone')

        Returns:
            ChannelResponse adaptado para WhatsApp
        """
        context = context or {}
        phone = context.get('phone')

        # Verificar autorización
        if not self._is_authorized(phone):
            logger.warning(f"[WhatsAppChannel] Acceso no autorizado desde {phone}")
            return ChannelResponse(
                text="⚠️ Acceso no autorizado. Este número no está registrado como administrador.",
                visual_data=None,
                buttons=None
            )

        logger.info(f"[WhatsAppChannel] Mensaje de admin {phone}: {message[:50]}...")

        # Procesar con AdminAgent core
        result = await self.admin.process_message(
            session_id=session_id,
            message=message,
            channel='whatsapp',
            context=context
        )

        # Adaptar respuesta para WhatsApp
        formatted = self._format_for_whatsapp(result)

        return formatted

    def _is_authorized(self, phone: Optional[str]) -> bool:
        """Verifica si el número está autorizado"""
        if self.dev_mode:
            return True

        if not phone:
            return False

        # Normalizar número
        normalized = phone.replace('+', '').replace(' ', '').replace('-', '')

        for authorized in self.authorized_numbers:
            auth_normalized = authorized.replace('+', '').replace(' ', '').replace('-', '')
            if normalized == auth_normalized or normalized.endswith(auth_normalized):
                return True

        return False

    def _format_for_whatsapp(self, result) -> ChannelResponse:
        """
        Formatea respuesta del AdminAgent para WhatsApp.

        Convierte visual data en texto formateado y botones.
        """
        text = result.response_text
        buttons = None
        visual_text = ""

        # Convertir visual data a texto formateado
        if result.visual_data:
            visual_text = self._visual_data_to_text(result.visual_data)

        # Combinar texto principal con visual
        if visual_text:
            full_text = f"{text}\n\n{visual_text}"
        else:
            full_text = text

        # Agregar botones si es acción de broadcast
        if hasattr(result, 'action_type') and result.action_type == 'broadcast_confirmation':
            buttons = [
                {"id": "confirm_broadcast", "title": "✅ Enviar"},
                {"id": "cancel_broadcast", "title": "❌ Cancelar"}
            ]

        return ChannelResponse(
            text=full_text,
            visual_data=None,  # WhatsApp usa texto formateado, no visual data
            buttons=buttons,
            requires_confirmation=result.requires_confirmation if hasattr(result, 'requires_confirmation') else False
        )

    def _visual_data_to_text(self, visual_data: Dict) -> str:
        """Convierte visual data a texto formateado para WhatsApp"""
        visual_type = visual_data.get('type')
        data = visual_data.get('data', {})

        if visual_type == 'sales_summary':
            return (
                f"📊 *Resumen de Ventas*\n"
                f"💰 Total: ${data.get('total_sales', 0):,.2f}\n"
                f"📋 Órdenes: {data.get('order_count', 0)}\n"
                f"🧾 Ticket promedio: ${data.get('avg_ticket', 0):,.2f}"
            )

        elif visual_type == 'top_products_chart':
            products = data if isinstance(data, list) else []
            if not products:
                return ""

            text = "🏆 *Productos Más Vendidos*\n\n"
            for i, product in enumerate(products[:5], 1):
                name = product.get('name', 'Producto')
                qty = product.get('quantity', 0)
                text += f"{i}. {name} - {qty} unidades\n"
            return text.rstrip()

        elif visual_type == 'hourly_chart':
            # Simplificar a rango de horas pico
            if isinstance(data, dict):
                hours = sorted(data.items(), key=lambda x: x[1], reverse=True)[:3]
                if hours:
                    text = "⏰ *Horas Pico*\n\n"
                    for hour, value in hours:
                        text += f"• {hour}: ${value:,.2f}\n"
                    return text.rstrip()

        elif visual_type == 'daily_report':
            return (
                f"📅 *Reporte del {data.get('date', 'hoy')}*\n\n"
                f"💰 Ventas: ${data.get('summary', {}).get('total_sales', 0):,.2f}\n"
                f"📋 Órdenes: {data.get('summary', {}).get('order_count', 0)}\n"
                f"🕐 Hora pico: {data.get('peak_hour', 'N/A')}"
            )

        elif visual_type == 'voice_metrics':
            return (
                f"🎙️ *Métricas del Asistente de Voz*\n\n"
                f"💬 Conversaciones: {data.get('total_conversations', 0)}\n"
                f"📈 Tasa upsell: {data.get('upsell_success_rate', 0) * 100:.0f}%\n"
                f"😊 Satisfacción: {data.get('avg_sentiment', 0) * 100:.0f}%"
            )

        return ""


class AdminChannelManager:
    """
    Gestor de canales para AdminAgent.

    Rutea mensajes al canal apropiado y gestiona sesiones multi-canal.
    """

    def __init__(self, admin_agent):
        self.admin = admin_agent
        self.channels = {
            'web': WebChannel(admin_agent),
            'voice': VoiceChannel(admin_agent),
            'whatsapp': WhatsAppChannel(admin_agent)
        }

    async def route_message(
        self,
        channel: str,
        message: str,
        session_id: str,
        context: Dict = None
    ) -> ChannelResponse:
        """
        Rutea mensaje al canal apropiado.

        Args:
            channel: 'web' | 'voice' | 'whatsapp'
            message: Mensaje del admin
            session_id: ID de sesión
            context: Contexto adicional

        Returns:
            ChannelResponse adaptado para el canal
        """
        if channel not in self.channels:
            raise ValueError(f"Canal no soportado: {channel}")

        logger.info(f"[ChannelManager] Ruteando mensaje a canal '{channel}'")

        return await self.channels[channel].process(message, session_id, context)

    def get_channel(self, channel: str) -> BaseChannel:
        """Obtiene instancia de un canal"""
        return self.channels.get(channel)
