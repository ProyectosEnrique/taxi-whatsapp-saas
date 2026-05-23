"""
================================================================================
ADMIN AGENT - Asistente Inteligente para Administrador
================================================================================
Agente especializado para ayudar al administrador del restaurante con:
- Consultas de ventas y metricas
- Gestion de promociones
- Administracion de menu
- Reportes y analytics

Arquitectura:
- Hereda de BaseAgent (servicios compartidos)
- Usa AdminFSM para flujo de conversacion
- Usa AdminTools para ejecutar acciones
- Soporta texto y voz
================================================================================
"""

import logging
import time
from typing import Dict, List, Optional, Any
from datetime import datetime

from ..base_agent import BaseAgent, AgentConfig, AgentResponse, AgentState
from .fsm import AdminFSM, AdminState, AdminIntent
from .tools import AdminTools, get_admin_tools, ADMIN_TOOL_DEFINITIONS
from .prompts import (
    get_admin_system_prompt,
    get_tool_response_prompt,
    HELP_PROMPT,
    ERROR_RECOVERY_PROMPT
)
# ESTRATEGIA 4: RAG - Importar base de conocimiento
from .knowledge_base import get_relevant_knowledge, get_knowledge_retriever

logger = logging.getLogger(__name__)


class AdminAgent(BaseAgent):
    """
    Asistente inteligente para el administrador del restaurante.

    Funcionalidades:
    - Consultar ventas y metricas en tiempo real
    - Crear y gestionar promociones
    - Administrar disponibilidad de productos
    - Actualizar precios
    - Generar reportes

    Soporta interaccion por texto y voz.
    """

    def __init__(self, config: AgentConfig = None):
        """
        Inicializar Admin Agent.

        Args:
            config: Configuracion del agente (opcional)
        """
        # Configuracion por defecto
        if config is None:
            config = AgentConfig(
                name="AdminAgent",
                description="Asistente inteligente para administracion del restaurante",
                language="es",
                voice_enabled=True,
                tts_voice_id="admin_voice",  # Voz mas formal
                max_history=20,
                timeout_seconds=30,
                require_confirmation=True
            )

        super().__init__(config)

        # Componentes especificos
        self.fsm = AdminFSM()
        self.tools = get_admin_tools()

        # Cache de metricas
        self._metrics_cache: Optional[Dict] = None
        self._metrics_cache_time: Optional[datetime] = None
        self._metrics_cache_ttl = 60  # 1 minuto

        # Nombre del restaurante
        self.restaurant_name = "El Restaurante"

        # ESTRATEGIA 2: Context Injection - Cache de contexto del dashboard
        self._dashboard_context: Optional[Dict] = None

        logger.info(f"[AdminAgent] Inicializado")

    # ==========================================================================
    # IMPLEMENTACION DE METODOS ABSTRACTOS
    # ==========================================================================

    def get_system_prompt(self) -> str:
        """Obtener system prompt del Admin Agent"""
        # ESTRATEGIA 2: Context Injection - Incluir contexto del dashboard
        return get_admin_system_prompt(
            restaurant_name=self.restaurant_name,
            current_metrics=self._metrics_cache,
            dashboard_context=self._dashboard_context  # NUEVO: Contexto inyectado
        )

    def get_available_tools(self) -> List[Dict]:
        """Obtener lista de herramientas disponibles"""
        return ADMIN_TOOL_DEFINITIONS

    async def process_message(
        self,
        session_id: str,
        message: str,
        context: Optional[Dict] = None
    ) -> AgentResponse:
        """
        Procesar un mensaje del administrador.

        Args:
            session_id: ID de la sesion
            message: Mensaje del usuario
            context: Contexto adicional (incluye dashboard_context)

        Returns:
            AgentResponse con la respuesta
        """
        start_time = time.time()
        context = context or {}

        # ESTRATEGIA 2: Context Injection - Almacenar contexto del dashboard
        if context.get('dashboard_context'):
            self._dashboard_context = context['dashboard_context']
            logger.debug(f"[AdminAgent] Dashboard context actualizado: {self._dashboard_context.get('resumen_ejecutivo', 'N/A')}")

        try:
            # Obtener/crear sesion
            session = self.get_or_create_session(session_id)

            # Agregar mensaje al historial
            self.add_to_history(session_id, "user", message)

            # Procesar con FSM
            new_state, intent_match, confirmation_msg = self.fsm.process(
                message,
                session
            )

            logger.info(f"[AdminAgent] Intent: {intent_match.intent.value}, State: {new_state.value}")

            # Si requiere confirmacion
            if confirmation_msg:
                self.add_to_history(session_id, "assistant", confirmation_msg)
                return AgentResponse(
                    text=confirmation_msg,
                    intent=intent_match.intent.value,
                    requires_confirmation=True,
                    confirmation_message=confirmation_msg
                )

            # Manejar intents especiales
            if intent_match.intent == AdminIntent.GREETING:
                response = await self._handle_greeting(session_id)

            elif intent_match.intent == AdminIntent.HELP:
                response = AgentResponse(
                    text=HELP_PROMPT,
                    intent="help"
                )

            elif intent_match.intent == AdminIntent.CANCEL:
                response = AgentResponse(
                    text="Entendido, operacion cancelada. ¿En que mas puedo ayudarte?",
                    intent="cancel"
                )

            elif intent_match.intent == AdminIntent.UNKNOWN:
                response = await self._handle_unknown(session_id, message)

            elif intent_match.tool_name:
                # Ejecutar herramienta
                response = await self._execute_and_respond(
                    session_id,
                    intent_match.tool_name,
                    intent_match.tool_params,
                    message
                )

            else:
                response = AgentResponse(
                    text="No estoy seguro de que quieres hacer. ¿Puedes ser mas especifico?",
                    intent="clarification_needed"
                )

            # Agregar respuesta al historial
            self.add_to_history(session_id, "assistant", response.text)

            # Registrar metricas
            response_time = (time.time() - start_time) * 1000
            self.record_request(True, response_time)

            return response

        except Exception as e:
            logger.error(f"[AdminAgent] Error procesando mensaje: {e}", exc_info=True)
            self.record_request(False, 0)

            return AgentResponse(
                text=ERROR_RECOVERY_PROMPT,
                intent="error",
                metadata={"error": str(e)}
            )

    async def execute_tool(
        self,
        tool_name: str,
        parameters: Dict
    ) -> Dict:
        """
        Ejecutar una herramienta administrativa.

        Args:
            tool_name: Nombre de la herramienta
            parameters: Parametros

        Returns:
            Resultado de la ejecucion
        """
        logger.info(f"[AdminAgent] Ejecutando tool: {tool_name} con params: {parameters}")

        result = await self.tools.execute(tool_name, parameters)

        # Actualizar cache de metricas si es relevante
        if tool_name in ["get_sales_report", "generate_daily_report"]:
            self._update_metrics_cache(result)

        self.metrics["actions_executed"] += 1

        return result

    # ==========================================================================
    # HANDLERS ESPECIFICOS
    # ==========================================================================

    async def _handle_greeting(self, session_id: str) -> AgentResponse:
        """Manejar saludo del administrador"""
        # Obtener metricas actuales para contexto
        await self._refresh_metrics_cache()

        hour = datetime.now().hour
        if 5 <= hour < 12:
            greeting = "Buenos dias"
        elif 12 <= hour < 19:
            greeting = "Buenas tardes"
        else:
            greeting = "Buenas noches"

        # Construir respuesta con contexto
        if self._metrics_cache:
            sales = self._metrics_cache.get("total_sales", 0)
            orders = self._metrics_cache.get("order_count", 0)
            pending = self._metrics_cache.get("pending_orders", 0)

            text = f"{greeting}! Soy tu asistente administrativo.\n\n"
            text += f"Resumen del dia: ${sales:,.2f} en ventas, {orders} ordenes"
            if pending > 0:
                text += f", {pending} pendientes"
            text += ".\n\n¿En que puedo ayudarte?"
        else:
            text = f"{greeting}! Soy tu asistente administrativo. ¿En que puedo ayudarte hoy?"

        return AgentResponse(
            text=text,
            intent="greeting",
            metadata={"metrics": self._metrics_cache}
        )

    async def _handle_unknown(self, session_id: str, message: str) -> AgentResponse:
        """Manejar intent no reconocido usando LLM con RAG"""
        try:
            # ESTRATEGIA 4: RAG - Obtener conocimiento relevante
            relevant_knowledge = get_relevant_knowledge(message)

            # Intentar con LLM para mejor comprension
            history = self.get_conversation_history(session_id, limit=5)

            # Construir contexto enriquecido con RAG
            context = {
                "role": "admin_assistant",
                "available_tools": [t["name"] for t in ADMIN_TOOL_DEFINITIONS]
            }

            # Agregar conocimiento de industria si es relevante
            if relevant_knowledge:
                context["industry_knowledge"] = relevant_knowledge
                logger.debug(f"[AdminAgent] RAG: Conocimiento inyectado para query")

            # Agregar contexto del dashboard si existe
            if self._dashboard_context:
                context["dashboard_context"] = self._dashboard_context.get("resumen_ejecutivo", "")

            result = self.llm_service.generate_response(
                user_message=message,
                intent="admin_query",
                conversation_history=history,
                context=context,
                temperature=0.7,
                max_tokens=300  # Aumentado para respuestas mas completas
            )

            response_text = result.get("response_text", "")

            if response_text:
                return AgentResponse(
                    text=response_text,
                    intent="llm_response",
                    metadata={
                        "llm_used": True,
                        "provider": result.get("provider"),
                        "rag_used": bool(relevant_knowledge)
                    }
                )

        except Exception as e:
            logger.warning(f"[AdminAgent] LLM fallback failed: {e}")

        # Fallback
        return AgentResponse(
            text="No entendi tu solicitud. Puedo ayudarte con ventas, promociones y menu. "
                 "Di 'ayuda' para ver las opciones disponibles.",
            intent="unknown"
        )

    async def _execute_and_respond(
        self,
        session_id: str,
        tool_name: str,
        tool_params: Dict,
        original_query: str
    ) -> AgentResponse:
        """
        Ejecutar herramienta y generar respuesta formateada.

        Args:
            session_id: ID de sesion
            tool_name: Nombre de la herramienta
            tool_params: Parametros
            original_query: Pregunta original

        Returns:
            AgentResponse con respuesta formateada
        """
        # Ejecutar herramienta
        result = await self.execute_tool(tool_name, tool_params)

        if not result.get("success", False):
            error_msg = result.get("error", "Error desconocido")
            return AgentResponse(
                text=f"No pude completar la operacion: {error_msg}",
                intent="error",
                action_executed=tool_name,
                action_result=result
            )

        # Formatear respuesta segun el tipo de herramienta
        response_text = self._format_tool_response(tool_name, result, original_query)

        return AgentResponse(
            text=response_text,
            intent=tool_name,
            action_executed=tool_name,
            action_result=result,
            visual_data=self._build_visual_data(tool_name, result)
        )

    def _format_tool_response(
        self,
        tool_name: str,
        result: Dict,
        original_query: str
    ) -> str:
        """Formatear respuesta de herramienta para el usuario"""

        if tool_name == "get_sales_report":
            total = result.get("total_sales", 0)
            orders = result.get("order_count", 0)
            avg = result.get("avg_ticket", 0)
            period = result.get("period", "hoy")

            period_text = {
                "today": "Hoy",
                "yesterday": "Ayer",
                "week": "Esta semana",
                "month": "Este mes"
            }.get(period, period)

            return f"{period_text} llevamos ${total:,.2f} en ventas con {orders} ordenes. " \
                   f"El ticket promedio es ${avg:,.2f}."

        if tool_name == "get_top_products":
            products = result.get("products", [])
            if not products:
                return "No hay datos de productos mas vendidos para este periodo."

            lines = ["Los productos mas vendidos son:"]
            for i, p in enumerate(products[:5], 1):
                lines.append(f"{i}. {p['name']} ({p['quantity']} vendidos)")

            return "\n".join(lines)

        if tool_name == "get_orders_count":
            total = result.get("total", 0)
            pending = result.get("pending", 0)
            completed = result.get("completed", 0)
            period = result.get("period", "hoy")

            text = f"Tenemos {total} ordenes"
            if period == "today":
                text += " hoy"
            if pending > 0:
                text += f", {pending} pendientes"
            if completed > 0:
                text += f", {completed} completadas"
            return text + "."

        if tool_name == "get_hourly_sales":
            peak_hour = result.get("peak_hour", "")
            peak_sales = result.get("peak_sales", 0)

            return f"La hora pico es a las {peak_hour} con ${peak_sales:,.2f} en ventas."

        if tool_name == "get_average_ticket":
            avg = result.get("avg_ticket", 0)
            period = result.get("period", "hoy")

            return f"El ticket promedio es ${avg:,.2f}."

        if tool_name == "generate_daily_report":
            summary = result.get("summary", {})
            top = result.get("top_products", [])
            peak = result.get("peak_hour", "")

            lines = [
                f"**Reporte del dia ({result.get('date', 'hoy')}):**",
                f"- Ventas totales: ${summary.get('total_sales', 0):,.2f}",
                f"- Ordenes: {summary.get('order_count', 0)}",
                f"- Ticket promedio: ${summary.get('avg_ticket', 0):,.2f}",
                f"- Hora pico: {peak}",
            ]

            if top:
                lines.append(f"- Top producto: {top[0].get('name', '')}")

            return "\n".join(lines)

        if tool_name == "create_promotion":
            return result.get("message", "Promocion creada exitosamente.")

        if tool_name == "toggle_promotion":
            return result.get("message", "Estado de promocion actualizado.")

        if tool_name == "list_promotions":
            promos = result.get("promotions", [])
            if not promos:
                return "No hay promociones activas en este momento."

            lines = [f"Hay {len(promos)} promociones activas:"]
            for p in promos:
                status = "activa" if p.get("is_active") else "inactiva"
                lines.append(f"- {p['name']} ({p['type']}) - {status}")

            return "\n".join(lines)

        if tool_name == "toggle_product":
            return result.get("message", "Producto actualizado.")

        if tool_name == "update_product_price":
            return result.get("message", "Precio actualizado.")

        if tool_name == "get_unavailable_products":
            products = result.get("products", [])
            count = result.get("count", 0)

            if count == 0:
                return "Todos los productos estan disponibles."

            lines = [f"Hay {count} productos agotados:"]
            for p in products:
                lines.append(f"- {p['name']}")

            return "\n".join(lines)

        # Default
        return f"Operacion completada: {result.get('message', 'OK')}"

    def _build_visual_data(self, tool_name: str, result: Dict) -> Optional[Dict]:
        """Construir datos visuales para el frontend"""

        if tool_name == "get_sales_report":
            return {
                "type": "sales_summary",
                "data": {
                    "total_sales": result.get("total_sales", 0),
                    "order_count": result.get("order_count", 0),
                    "avg_ticket": result.get("avg_ticket", 0)
                }
            }

        if tool_name == "get_top_products":
            return {
                "type": "top_products_chart",
                "data": result.get("products", [])
            }

        if tool_name == "get_hourly_sales":
            return {
                "type": "hourly_chart",
                "data": result.get("hourly_sales", {})
            }

        if tool_name == "generate_daily_report":
            return {
                "type": "daily_report",
                "data": result
            }

        return None

    # ==========================================================================
    # CACHE DE METRICAS
    # ==========================================================================

    async def _refresh_metrics_cache(self):
        """Refrescar cache de metricas si es necesario"""
        now = datetime.now()

        if self._metrics_cache_time:
            elapsed = (now - self._metrics_cache_time).total_seconds()
            if elapsed < self._metrics_cache_ttl:
                return  # Cache aun valido

        try:
            result = await self.tools.get_sales_report("today")
            if result.get("success"):
                self._metrics_cache = {
                    "total_sales": result.get("total_sales", 0),
                    "order_count": result.get("order_count", 0),
                    "avg_ticket": result.get("avg_ticket", 0)
                }

                # Obtener ordenes pendientes
                orders = await self.tools.get_orders_count("today", "pending")
                if orders.get("success"):
                    self._metrics_cache["pending_orders"] = orders.get("pending", 0)

                self._metrics_cache_time = now
                logger.debug("[AdminAgent] Metrics cache actualizado")

        except Exception as e:
            logger.warning(f"[AdminAgent] Error actualizando metrics cache: {e}")

    def _update_metrics_cache(self, result: Dict):
        """Actualizar cache con resultado de herramienta"""
        if result.get("success"):
            self._metrics_cache = {
                "total_sales": result.get("total_sales", 0),
                "order_count": result.get("order_count", 0),
                "avg_ticket": result.get("avg_ticket", 0)
            }
            self._metrics_cache_time = datetime.now()


# ==============================================================================
# SINGLETON
# ==============================================================================

_admin_agent: Optional[AdminAgent] = None


def get_admin_agent() -> AdminAgent:
    """Obtener instancia singleton del AdminAgent"""
    global _admin_agent
    if _admin_agent is None:
        _admin_agent = AdminAgent()
    return _admin_agent
