"""
================================================================================
HYBRID FLOW HANDLER - Orquestador Principal
================================================================================
Orquesta el flujo completo WhatsApp ↔ Web ↔ WhatsApp
================================================================================
"""

from typing import Dict, Any, Optional, Tuple, List
import logging
import os

from .hybrid_session import (
    HybridCustomerSession,
    ConversationIntent,
    DerivarReason,
    SessionChannel
)
from .intent_detector import IntentDetector
from .url_generator import SecureURLGenerator, ConversionTracker
from .message_builder import MessageBuilder, WhatsAppMessage, MetaWhatsAppFormatter, InteractiveButton
from .agent_connector import AgentConnector

logger = logging.getLogger(__name__)


class HybridFlowHandler:
    """
    Orquestador principal del flujo híbrido.

    Este componente integra todos los subsistemas y decide:
    1. Cuándo derivar a web
    2. Qué mensajes enviar
    3. Cómo manejar el retorno desde web
    4. Tracking de conversiones
    5. Conectar con el mesero virtual (AgentConnector)
    """

    def __init__(self, agent_connector: Optional[AgentConnector] = None):
        self.intent_detector = IntentDetector()
        self.url_generator = SecureURLGenerator()
        self.message_builder = MessageBuilder()
        self.meta_formatter = MetaWhatsAppFormatter()
        self.tracker = ConversionTracker()

        # AgentConnector para el mesero virtual
        self.agent_connector = agent_connector or AgentConnector()

        # Config
        self.auto_derivar_enabled = os.getenv("AUTO_DERIVAR_WEB", "true").lower() == "true"
        self.min_messages_before_derivar = int(os.getenv("MIN_MESSAGES_DERIVAR", "3"))

        # LLM-First Mode Config
        self.llm_first_mode = os.getenv("LLM_FIRST_MODE", "always").lower()
        self.use_fsm_templates = os.getenv("USE_FSM_TEMPLATES", "false").lower() == "true"
        self.record_all_conversations = os.getenv("RECORD_ALL_CONVERSATIONS", "true").lower() == "true"

        logger.info(f"[HybridFlow] LLM-First Mode: {self.llm_first_mode}")
        logger.info(f"[HybridFlow] Use FSM Templates: {self.use_fsm_templates}")
        logger.info(f"[HybridFlow] Record Conversations: {self.record_all_conversations}")

    # ==========================================================================
    # PROCESAMIENTO DE MENSAJES
    # ==========================================================================

    async def process_message(
        self,
        session: HybridCustomerSession,
        message: str
    ) -> Tuple[WhatsAppMessage, HybridCustomerSession]:
        """
        Procesar mensaje del usuario y determinar respuesta.

        Args:
            session: Sesión actual del cliente
            message: Mensaje recibido

        Returns:
            (mensaje_respuesta, sesion_actualizada)
        """
        # 1. Detectar intención
        intent, confidence = self.intent_detector.detect_intent(
            message,
            conversation_history=[msg.content for msg in session.conversation_history]
        )

        # 2. Agregar mensaje al historial
        session.add_message(role="user", content=message, intent=intent)

        logger.info(
            f"[HybridFlow] Mensaje procesado: intent={intent}, "
            f"confidence={confidence:.2f}, messages={session.message_count}"
        )

        # 3. Decidir si derivar a web (pasando el mensaje para detección explícita)
        should_derivar, reason = self._should_derivar_to_web(
            session=session,
            intent=intent,
            confidence=confidence,
            message=message  # NUEVO: pasar mensaje para detección explícita
        )

        # 4. Generar respuesta apropiada
        if should_derivar and self.auto_derivar_enabled:
            response_message = await self._handle_derivar_to_web(session, reason)
        else:
            response_message = await self._handle_whatsapp_response(session, intent, message)

        # 5. Agregar respuesta al historial
        session.add_message(role="assistant", content=response_message.text)

        return response_message, session

    # ==========================================================================
    # DERIVACIÓN A WEB
    # ==========================================================================

    def _should_derivar_to_web(
        self,
        session: HybridCustomerSession,
        intent: ConversationIntent,
        confidence: float,
        message: str = ""
    ) -> Tuple[bool, Optional[DerivarReason]]:
        """
        Decidir si derivar a web.

        Considera:
        - Intención detectada
        - Historial de conversación
        - Tamaño del carrito
        - Configuración del sistema
        - Mensaje explícito del usuario (NUEVO)
        """
        # Si usuario ya fue derivado y volvió, ser menos agresivo
        if session.web_redirection_count > 0 and session.message_count < 10:
            return False, None

        # Usar lógica del intent detector (ahora con mensaje para detección explícita)
        should_redirect, reason = self.intent_detector.should_redirect_to_web(
            intent=intent,
            message_count=session.message_count,
            cart_size=len(session.cart),
            confidence=confidence,
            user_message=message  # NUEVO: pasar mensaje para detección explícita
        )

        # Verificar mínimo de mensajes antes de derivar
        if should_redirect and session.message_count < self.min_messages_before_derivar:
            logger.info(
                f"[HybridFlow] Derivación pospuesta: solo {session.message_count} "
                f"mensajes (mínimo: {self.min_messages_before_derivar})"
            )
            return False, None

        # Verificar lógica adicional de la sesión
        if should_redirect:
            session_should, session_reason = session.should_derivar_to_web()
            if session_should and not reason:
                reason = session_reason

        return should_redirect, reason

    async def _handle_derivar_to_web(
        self,
        session: HybridCustomerSession,
        reason: DerivarReason
    ) -> WhatsAppMessage:
        """
        Manejar derivación a web.

        Genera URL trackeada y mensaje con botón.
        """
        # Generar URL segura
        web_url = self.url_generator.generate_web_url(
            session_id=session.session_id,
            phone=session.phone,
            reason=reason.value if reason else "browsing",
            cart=session.cart,
            table_id=session.table_id,
            preferences=session.preferences.dict()
        )

        # Actualizar sesión
        session.initiate_web_session(
            session_token=web_url.split("st=")[1].split("&")[0] if "st=" in web_url else "",
            reason=reason
        )
        session.last_web_url = web_url

        # Track analytics
        self.tracker.track_redirect_to_web(
            session_id=session.session_id,
            reason=reason.value if reason else "unknown",
            cart_size=len(session.cart)
        )

        # Generar mensaje
        message = self.message_builder.build_redirect_to_web_message(
            reason=reason,
            web_url=web_url,
            cart_size=len(session.cart)
        )

        logger.info(f"[HybridFlow] Usuario derivado a web: {reason}")

        return message

    # ==========================================================================
    # RESPUESTAS EN WHATSAPP
    # ==========================================================================

    async def _handle_whatsapp_response(
        self,
        session: HybridCustomerSession,
        intent: ConversationIntent,
        message: str
    ) -> WhatsAppMessage:
        """
        Generar respuesta dentro de WhatsApp usando el mesero virtual (AgentConnector).

        MODO LLM-FIRST:
        - Si llm_first_mode == "always": TODO pasa por el agente (LLM)
        - Si llm_first_mode == "hybrid": Algunos casos usan templates, otros LLM
        - Si llm_first_mode == "fallback": Templates primero, LLM como backup

        FLUJO TRADICIONAL (solo si NO es modo "always"):
        1. Si es PRIMER mensaje (saludo) → mostrar recomendaciones + promociones
        2. Si pregunta "qué me recomiendas" → mostrar opciones CON botones
        3. Si pide "ver menú con fotos" → derivar a web (se maneja antes de llegar aquí)
        4. Otros casos → usar mesero virtual (AgentConnector)
        """
        message_lower = message.lower().strip()

        # ======================================================================
        # MODO LLM-FIRST: Saltar mensajes hardcoded, ir directo al agente
        # ======================================================================
        if self.llm_first_mode == "always":
            logger.info("[HybridFlow] LLM-First Mode ALWAYS: Usando agente para TODO")

            # Ir DIRECTO al agente (LLM), sin mensajes hardcoded
            try:
                context = {
                    "phone": session.phone,
                    "customer_name": session.customer_name,
                    "cart": session.cart,
                    "table_id": session.table_id,
                    "restaurant_id": session.restaurant_id,
                    "tenant_id": session.restaurant_id,
                    "preferences": session.preferences.dict() if session.preferences else {},
                    "message_count": session.message_count,
                    "is_first_message": session.message_count <= 2
                }

                agent_response = await self.agent_connector.send_message(
                    session_id=session.session_id,
                    message=message,
                    context=context
                )

                # Convertir respuesta del agente al formato WhatsAppMessage
                buttons_list = None
                if agent_response.get("buttons"):
                    buttons_list = [
                        InteractiveButton(id=btn["id"], title=btn["title"])
                        for btn in agent_response.get("buttons", [])
                    ]

                return WhatsAppMessage(
                    text=agent_response.get("text", agent_response.get("response", "")),
                    buttons=buttons_list
                )

            except Exception as e:
                logger.error(f"[HybridFlow] Error en agente (LLM-First): {e}")
                # Fallback a mensaje genérico
                return WhatsAppMessage(
                    text="Disculpa, tuve un problema. ¿Podrías repetir tu mensaje?"
                )

        # ======================================================================
        # FLUJO TRADICIONAL (solo si NO es modo "always")
        # ======================================================================

        # NIVEL 1: Primer mensaje de bienvenida (mensaje 1 o 2)
        if session.message_count <= 2:
            is_greeting = any(word in message_lower for word in ["hola", "buenas", "hey", "buenos", "qué tal"])

            if is_greeting:
                logger.info("[HybridFlow] Enviando mensaje inicial con recomendaciones")

                # Obtener promociones y recomendaciones del chef (según tenant)
                promotions, chef_recs = await self._get_promotions_and_recommendations(
                    restaurant_id=session.restaurant_id or "default"
                )

                return self.message_builder.build_initial_message_with_recommendations(
                    customer_name=session.customer_name or "",
                    is_returning=session.web_redirection_count > 0,
                    promotions=promotions,
                    chef_recommendations=chef_recs
                )

        # NIVEL 2: Usuario pregunta "qué me recomiendas"
        recommend_keywords = [
            "qué me recomiendas", "que me recomiendas",
            "qué recomiendas", "que recomiendas",
            "recomienda", "recomendacion", "recomendación",
            "qué me das", "que me das"
        ]
        if any(keyword in message_lower for keyword in recommend_keywords):
            logger.info("[HybridFlow] Usuario pregunta qué recomendar")

            # Obtener datos (según tenant)
            promotions, chef_recs = await self._get_promotions_and_recommendations(
                restaurant_id=session.restaurant_id or "default"
            )

            return self.message_builder.build_what_do_you_recommend_response(
                promotions=promotions,
                chef_recommendations=chef_recs,
                popular_items=[]  # TODO: obtener de menu-service
            )

        # NIVEL 3: Clicks en botones específicos
        button_handlers = {
            "ver_promos": self._handle_promotions,
            "ver_promociones": self._handle_promotions,
            "hacer_pedido": lambda s: self._build_help_message(s),
            "ayuda_pedido": lambda s: self._build_help_message(s),
        }

        # Si el mensaje es un ID de botón, ejecutar handler
        if message in button_handlers:
            handler = button_handlers[message]
            return await handler(session)

        # NIVEL 4: Usar mesero virtual (AgentConnector) para todo lo demás
        try:
            # Preparar contexto para el agente
            context = {
                "phone": session.phone,
                "customer_name": session.customer_name,
                "cart": session.cart,
                "table_id": session.table_id,
                "restaurant_id": session.restaurant_id,  # IMPORTANTE: Pasar tenant_id
                "tenant_id": session.restaurant_id,  # Alias por compatibilidad
                "preferences": session.preferences.dict() if session.preferences else {}
            }

            # Llamar al método correcto: send_message
            agent_response = await self.agent_connector.send_message(
                session_id=session.session_id,
                message=message,
                context=context
            )

            # Convertir respuesta del agent al formato WhatsAppMessage
            buttons_list = None
            if agent_response.get("buttons"):
                buttons_list = [
                    InteractiveButton(id=btn["id"], title=btn["title"])
                    for btn in agent_response.get("buttons", [])
                ]

            return WhatsAppMessage(
                text=agent_response.get("text", "¿En qué puedo ayudarte?"),
                buttons=buttons_list
            )

        except Exception as e:
            logger.error(f"[HybridFlow] Error al conectar con mesero virtual: {e}")
            # Fallback: mensaje de ayuda
            return self._build_help_message(session)

    async def _handle_quick_order(
        self,
        session: HybridCustomerSession,
        message: str
    ) -> WhatsAppMessage:
        """Manejar pedido rápido"""
        # Extraer productos mencionados
        products = self.intent_detector.extract_product_mentions(message)

        if products:
            # TODO: Consultar base de datos para obtener info completa
            # Por ahora, respuesta simple
            text = f"¡Perfecto! Detecté:\n"
            for p in products:
                text += f"• {p['text']}\n"
            text += "\n¿Es correcto?"

            return WhatsAppMessage(
                text=text,
                buttons=[
                    InteractiveButton(id="confirm", title="✅ Sí"),
                    InteractiveButton(id="edit", title="✏️ Cambiar")
                ]
            )

        # No pudo detectar productos específicos
        text = (
            "Claro! Dime exactamente qué quieres pedir.\n\n"
            "Ejemplo: '2 tacos al pastor y una coca'"
        )
        return WhatsAppMessage(text=text)

    async def _handle_repeat_order(
        self,
        session: HybridCustomerSession
    ) -> WhatsAppMessage:
        """Manejar pedido repetido (cliente regular)"""
        if session.preferences.usual_order:
            # Tiene pedido usual guardado
            usual = session.preferences.usual_order
            cart = usual.get("items", [])
            total = usual.get("total", 0)

            return self.message_builder.build_quick_order_confirmation(
                cart=cart,
                total=total
            )

        # No tiene pedido usual
        text = (
            "¡Me encantaría traerte lo de siempre!\n\n"
            "Pero es la primera vez que platicamos 😊\n"
            "¿Qué te gustaría ordenar hoy?"
        )
        return WhatsAppMessage(text=text)

    async def _handle_promotions(
        self,
        session: HybridCustomerSession
    ) -> WhatsAppMessage:
        """Mostrar promociones"""
        # TODO: Obtener promociones reales de la base de datos
        # Por ahora, ejemplos
        promos = [
            {"name": "Tacos al Pastor 3x$99", "price": 99.0, "original_price": 135.0},
            {"name": "Combo Hamburguesa", "price": 145.0, "discount_percent": 20},
        ]

        return self.message_builder.build_promotions_message(promos)

    async def _handle_consultation(
        self,
        session: HybridCustomerSession,
        message: str
    ) -> WhatsAppMessage:
        """Manejar consulta"""
        # TODO: Procesar consulta específica
        # Por ahora, respuesta genérica
        text = (
            "Buena pregunta! 🤔\n\n"
            "Para darte info precisa de ingredientes y opciones,\n"
            "¿quieres que te muestre el menú completo?\n\n"
            "Ahí puedes ver detalles de cada platillo"
        )
        return WhatsAppMessage(
            text=text,
            buttons=[
                InteractiveButton(id="see_menu", title="📋 Ver Menú"),
                InteractiveButton(id="talk_to_human", title="💬 Hablar con Mesero")
            ]
        )

    async def _get_promotions_and_recommendations(
        self,
        restaurant_id: str = "default"
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Obtener promociones activas y recomendaciones del chef.

        Args:
            restaurant_id: ID del tenant/tienda

        TODO: Integrar con menu-service para obtener datos reales:
        - GET /api/v1/promotions/active?restaurant_id={restaurant_id}
        - GET /api/v1/menu/chef-recommendations?restaurant_id={restaurant_id}

        Por ahora retorna datos de ejemplo según el tenant.

        Returns:
            (promociones, recomendaciones_chef)
        """
        # TODO: Reemplazar con llamada a menu-service
        # Ejemplo de cómo debería verse:
        # async with aiohttp.ClientSession() as session:
        #     async with session.get(f"http://menu-service:8001/api/v1/promotions/active?restaurant_id={restaurant_id}") as resp:
        #         promotions = await resp.json()
        #     async with session.get(f"http://menu-service:8001/api/v1/menu/chef-recommendations?restaurant_id={restaurant_id}") as resp:
        #         chef_recs = await resp.json()
        #     return promotions, chef_recs

        # Datos de ejemplo (hardcoded) según tenant
        if restaurant_id == "tenant_pharmacy_001":
            promotions = [
                {
                    "name": "Aspirina 500mg x20 tabletas",
                    "price": 45.0,
                    "original_price": 60.0
                },
                {
                    "name": "Paracetamol 500mg x30 tabletas",
                    "price": 35.0,
                    "original_price": 50.0
                },
            ]
            chef_recs = [
                {
                    "name": "Vitamina C 1000mg",
                    "price": 120.0,
                    "description": "Fortalece tu sistema inmune"
                }
            ]
        elif restaurant_id == "tenant_butchery_001":
            promotions = [
                {
                    "name": "Arrachera Premium 1kg",
                    "price": 180.0,
                    "original_price": 220.0
                },
                {
                    "name": "Pechuga de Pollo 1kg",
                    "price": 75.0,
                    "original_price": 95.0
                },
            ]
            chef_recs = [
                {
                    "name": "Rib Eye USDA Prime",
                    "price": 450.0,
                    "description": "El mejor corte de la casa"
                }
            ]
        else:  # default - restaurant
            promotions = [
                {
                    "name": "Tacos al Pastor 3x$99",
                    "price": 99.0,
                    "original_price": 135.0
                },
                {
                    "name": "Combo Hamburguesa + Refresco",
                    "price": 145.0,
                    "original_price": 180.0
                }
            ]
            chef_recs = [
                {
                    "name": "Hamburguesa Deluxe",
                    "price": 185.0,
                    "description": "Doble carne, queso, bacon, huevo - ¡Nuestra favorita!"
                }
            ]

        return promotions, chef_recs

    def _build_help_message(self, session: HybridCustomerSession) -> WhatsAppMessage:
        """Mensaje de ayuda genérico"""
        text = (
            "¿En qué te puedo ayudar? 😊\n\n"
            "Puedes:\n"
            "• Hacer un pedido rápido\n"
            "• Ver el menú completo con fotos\n"
            "• Preguntar por promociones\n"
            "• Consultar ingredientes\n\n"
            "Solo dime qué necesitas"
        )
        return WhatsAppMessage(text=text)

    # ==========================================================================
    # RETORNO DESDE WEB
    # ==========================================================================

    async def handle_return_from_web(
        self,
        session: HybridCustomerSession,
        web_cart: list[Dict[str, Any]],
        total: float
    ) -> Tuple[WhatsAppMessage, HybridCustomerSession]:
        """
        Manejar retorno del usuario desde web.

        Args:
            session: Sesión actual
            web_cart: Carrito actualizado desde web
            total: Total del pedido

        Returns:
            (mensaje_bienvenida, sesion_actualizada)
        """
        # Calcular tiempo en web
        time_on_web = 0
        if session.web_session:
            from datetime import datetime
            time_on_web = int(
                (datetime.utcnow() - session.web_session.visited_at).total_seconds()
            )

        # Actualizar sesión
        cart_before = len(session.cart)
        session.sync_cart_from_web(web_cart)
        session.mark_return_from_web()
        cart_after = len(session.cart)

        # Track analytics
        self.tracker.track_return_from_web(
            session_id=session.session_id,
            time_on_web_seconds=time_on_web,
            cart_updated=cart_before != cart_after,
            cart_size_before=cart_before,
            cart_size_after=cart_after
        )

        # Generar mensaje de bienvenida
        message = self.message_builder.build_welcome_back_message(
            cart=web_cart,
            total=total,
            time_on_web_seconds=time_on_web
        )

        logger.info(
            f"[HybridFlow] Usuario regresó de web: "
            f"tiempo={time_on_web}s, cart={cart_before}→{cart_after}"
        )

        return message, session

    # ==========================================================================
    # FORMATEO PARA META
    # ==========================================================================

    def format_for_meta(self, message: WhatsAppMessage) -> Dict[str, Any]:
        """
        Formatear mensaje para Meta WhatsApp Business API.

        Returns:
            Payload listo para enviar a Meta API
        """
        if message.url_button:
            return self.meta_formatter.format_url_button(message)
        elif message.buttons:
            return self.meta_formatter.format_interactive_buttons(message)
        else:
            return {"type": "text", "text": {"body": message.text}}


# ==============================================================================
# EJEMPLO DE USO
# ==============================================================================

if __name__ == "__main__":
    import asyncio

    async def test_flow():
        # Crear handler
        handler = HybridFlowHandler()

        # Simular sesión
        session = HybridCustomerSession(
            phone="+5215551234567",
            customer_name="Juan"
        )

        # Simular conversación
        messages_from_user = [
            "Hola",
            "Qué tienen?",
            "Qué tipos de tacos?",
            "Tienen fotos del menú?",
        ]

        print("=" * 80)
        print("SIMULACIÓN DE FLUJO HÍBRIDO")
        print("=" * 80)

        for msg in messages_from_user:
            print(f"\n👤 Usuario: {msg}")

            # Procesar
            response, session = await handler.process_message(session, msg)

            print(f"🤖 Bot: {response.text[:100]}...")

            if response.url_button:
                print(f"   🔗 Botón URL: {response.url_button['text']}")
                print(f"      → {response.url_button['url'][:60]}...")

            if response.buttons:
                print(f"   🔘 Botones: {[b.title for b in response.buttons]}")

            # Verificar si se derivó
            if session.should_redirect_to_web:
                print(f"\n   ⚠️ DERIVADO A WEB: {session.redirect_reason}")
                break

    asyncio.run(test_flow())
