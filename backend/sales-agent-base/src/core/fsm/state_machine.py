# ============================================================
# MÁQUINA DE ESTADOS - FSM
# ============================================================
# Orquestador principal del agente de ventas
# Versión: 2.2.0 - Con NLU, Event Bus, Metrics y Feedback Loop
# ============================================================

import logging
import time
import asyncio
import re
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

from .conversation_states import ConversationState, StateContext, ProductSelection
from .decision_tree import IntentDecisionTree, Intent, IntentResult
from .response_generator import ResponseGenerator, ResponseResult
from .llm_fallback import LLMFallbackHandler, get_fallback_handler, FallbackStrategy
from .product_matcher import ProductMatcher, get_product_matcher
from .conversation_memory import ConversationMemory, create_conversation_memory

# === NUEVAS INTEGRACIONES v2.2 ===
# Enhanced Classifier (NLU + Regex híbrido)
try:
    from .enhanced_classifier import create_enhanced_classifier, EnhancedClassifier
    ENHANCED_CLASSIFIER_AVAILABLE = True
except ImportError:
    ENHANCED_CLASSIFIER_AVAILABLE = False

# Product Validator (validación de existencia)
try:
    from .product_validator import ProductValidator, ProductStatus, create_product_validator
    PRODUCT_VALIDATOR_AVAILABLE = True
except ImportError:
    PRODUCT_VALIDATOR_AVAILABLE = False

# Semantic Search (búsqueda por significado)
try:
    from .semantic_search import get_semantic_search, ProductSemanticSearch
    SEMANTIC_SEARCH_AVAILABLE = True
except ImportError:
    SEMANTIC_SEARCH_AVAILABLE = False

# Event Bus (mensajería desacoplada)
try:
    from ...events import get_event_bus, Event, EventType, register_default_handlers
    EVENT_BUS_AVAILABLE = True
except ImportError:
    EVENT_BUS_AVAILABLE = False

# Feedback Loop (aprendizaje continuo)
try:
    from ...learning import get_feedback_loop, FeedbackType, record_successful_interaction, record_failed_interaction
    FEEDBACK_LOOP_AVAILABLE = True
except ImportError:
    FEEDBACK_LOOP_AVAILABLE = False

# Prometheus Metrics
try:
    from ...monitoring import (
        get_metrics, track_intent, track_order, track_upsell,
        track_product_search, track_conversation_start, track_conversation_end,
        track_error
    )
    METRICS_AVAILABLE = True
except ImportError:
    METRICS_AVAILABLE = False

# Multi-Order Parser (pedidos complejos con Gemini)
try:
    from .multi_order_parser import MultiOrderParser, OrderComplexity, ParsedOrderItem
    MULTI_ORDER_PARSER_AVAILABLE = True
except ImportError:
    MULTI_ORDER_PARSER_AVAILABLE = False

# Pattern Learner (auto-aprendizaje de patrones regex)
try:
    from .pattern_learner import init_pattern_learner, get_pattern_learner
    PATTERN_LEARNER_AVAILABLE = True
except ImportError:
    PATTERN_LEARNER_AVAILABLE = False

# Hybrid NLU (LLM-first con regex como fallback)
try:
    from .hybrid_nlu import HybridNLU, init_hybrid_nlu, get_hybrid_nlu, NLUResult, ConnectionStatus
    HYBRID_NLU_AVAILABLE = True
except ImportError:
    HYBRID_NLU_AVAILABLE = False

# LLM Provider (para Gemini, Cerebras y Cascade)
try:
    from ...nlp.model_provider import GeminiProvider, CerebrasProvider, CascadeProvider
    import os
    GEMINI_AVAILABLE = bool(os.getenv('GOOGLE_API_KEY'))
    CEREBRAS_AVAILABLE = bool(os.getenv('CEREBRAS_API_KEY'))
    CASCADE_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    CEREBRAS_AVAILABLE = False
    CASCADE_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class ProcessResult:
    """Resultado del procesamiento de un mensaje"""
    response_text: str
    intent: str
    new_state: ConversationState
    visual_data: Optional[Dict] = None
    order_updated: bool = False
    requires_llm_fallback: bool = False
    service_request: Optional[Dict] = None  # Para solicitudes de servicio
    order_confirmed: bool = False  # True cuando el pedido debe enviarse a cocina
    order_data: Optional[Dict] = None  # Datos del pedido para enviar a cocina
    cart_action: Optional[Dict] = None  # Acción para sincronizar carrito del frontend


class SalesAgentFSM:
    """
    Máquina de Estados Finitos para el Agente de Ventas.

    Maneja todo el flujo de conversación de manera determinística,
    usando el LLM solo cuando es estrictamente necesario.
    """

    def __init__(self, menu: List[Dict] = None, config: Dict = None, decision_tree=None, tenant_id: str = None):
        """
        Inicializa la máquina de estados.

        Args:
            menu: Lista de productos del menú
            config: Configuración opcional
            decision_tree: Árbol de decisión personalizado (opcional, para multi-tenant)
            tenant_id: ID del tenant (opcional, para multi-tenant)
        """
        self.menu = menu or []
        self.config = config or {}
        self.tenant_id = tenant_id or "default"

        # Componentes principales
        self.decision_tree = decision_tree if decision_tree is not None else IntentDecisionTree(menu)
        self.response_generator = ResponseGenerator(config)

        # Nuevos componentes v2.1
        self.product_matcher = get_product_matcher(menu, config)
        self.fallback_handler = get_fallback_handler(config)

        # === NUEVOS COMPONENTES v2.2 ===

        # Enhanced Classifier (NLU + Regex híbrido)
        self.enhanced_classifier = None
        if ENHANCED_CLASSIFIER_AVAILABLE:
            try:
                self.enhanced_classifier = create_enhanced_classifier(self.decision_tree)
                logger.info("[FSM] Enhanced Classifier (NLU) habilitado")
            except Exception as e:
                logger.warning(f"[FSM] Enhanced Classifier no disponible: {e}")

        # Semantic Search (búsqueda por significado)
        self.semantic_search = None
        if SEMANTIC_SEARCH_AVAILABLE and menu:
            try:
                self.semantic_search = get_semantic_search(menu)
                logger.info("[FSM] Semantic Search habilitado")
            except Exception as e:
                logger.warning(f"[FSM] Semantic Search no disponible: {e}")

        # Product Validator (validación de existencia)
        self.product_validator = None
        if PRODUCT_VALIDATOR_AVAILABLE:
            try:
                self.product_validator = create_product_validator(
                    self.product_matcher,
                    self.semantic_search
                )
                logger.info("[FSM] Product Validator habilitado")
            except Exception as e:
                logger.warning(f"[FSM] Product Validator no disponible: {e}")

        # Event Bus (mensajería)
        self.event_bus = None
        if EVENT_BUS_AVAILABLE:
            try:
                self.event_bus = get_event_bus()
                register_default_handlers()
                logger.info("[FSM] Event Bus habilitado")
            except Exception as e:
                logger.warning(f"[FSM] Event Bus no disponible: {e}")

        # Feedback Loop (aprendizaje)
        self.feedback_loop = None
        if FEEDBACK_LOOP_AVAILABLE:
            try:
                self.feedback_loop = get_feedback_loop()
                logger.info("[FSM] Feedback Loop habilitado")
            except Exception as e:
                logger.warning(f"[FSM] Feedback Loop no disponible: {e}")

        # Metrics (Prometheus)
        self.metrics = None
        if METRICS_AVAILABLE:
            try:
                self.metrics = get_metrics()
                logger.info("[FSM] Prometheus Metrics habilitado")
            except Exception as e:
                logger.warning(f"[FSM] Metrics no disponible: {e}")

        # === MULTI-ORDER PARSER v2.5 (Pedidos complejos con Gemini) ===
        self.multi_order_parser = None
        self.gemini_provider = None
        if MULTI_ORDER_PARSER_AVAILABLE:
            try:
                # Inicializar Gemini Provider si está disponible
                if GEMINI_AVAILABLE:
                    import os
                    api_key = os.getenv('GOOGLE_API_KEY')
                    if api_key:
                        # Usar gemini-2.0-flash-exp (gratis y disponible)
                        # gemini-1.5-pro da error 404
                        gemini_model = os.getenv('GEMINI_MODEL', 'gemini-2.0-flash-exp')
                        self.gemini_provider = GeminiProvider(
                            api_key=api_key,
                            model=gemini_model
                        )
                        logger.info(f"[FSM] Gemini Provider inicializado ({gemini_model})")

                # Crear parser con o sin Gemini
                self.multi_order_parser = MultiOrderParser(
                    menu=menu,
                    llm_provider=self.gemini_provider,
                    config=config
                )
                logger.info(f"[FSM] Multi-Order Parser habilitado (LLM: {'Gemini' if self.gemini_provider else 'No'})")

                # v4.0: Inicializar PatternLearner para auto-aprendizaje
                # Usar cualquier LLM disponible (Gemini, Groq, OpenAI, etc.)
                learner_llm = self.gemini_provider
                if not learner_llm and hasattr(self, 'response_generator') and self.response_generator:
                    learner_llm = getattr(self.response_generator, 'llm_provider', None)

                if PATTERN_LEARNER_AVAILABLE:
                    try:
                        learner_config = {
                            'min_cases_for_analysis': 5,
                            'analysis_interval_hours': 12,
                            'min_validation_score': 0.8,
                            'data_dir': '/app/data/learning'
                        }
                        init_pattern_learner(
                            llm_provider=learner_llm,  # Puede ser None, se inicializará después
                            config=learner_config
                        )
                        logger.info(f"[FSM] PatternLearner habilitado (auto-aprendizaje: 5 casos / 12h) | LLM: {'Sí' if learner_llm else 'Diferido'}")
                    except Exception as e:
                        logger.warning(f"[FSM] PatternLearner no inicializado: {e}")
            except Exception as e:
                logger.warning(f"[FSM] Multi-Order Parser no disponible: {e}")

        # === HYBRID NLU v3.0 (con CascadeProvider: Cerebras → Gemini → Regex) ===
        self.hybrid_nlu = None
        self.cascade_nlu_provider = None  # CascadeProvider para NLU
        if HYBRID_NLU_AVAILABLE:
            try:
                import os
                providers_list = []

                # Inicializar Cerebras si está disponible
                if CEREBRAS_AVAILABLE:
                    cerebras_key = os.getenv('CEREBRAS_API_KEY')
                    if cerebras_key:
                        cerebras_prov = CerebrasProvider(
                            api_key=cerebras_key,
                            model="llama-3.3-70b"
                        )
                        providers_list.append(cerebras_prov)
                        logger.info("[FSM] Cerebras agregado al cascade NLU")

                # Inicializar Gemini si está disponible (fallback)
                if GEMINI_AVAILABLE:
                    gemini_key = os.getenv('GOOGLE_API_KEY')
                    if gemini_key:
                        gemini_prov = GeminiProvider(
                            api_key=gemini_key,
                            model="gemini-2.0-flash-exp"
                        )
                        providers_list.append(gemini_prov)
                        logger.info("[FSM] Gemini agregado al cascade NLU (fallback)")

                # Crear CascadeProvider si hay providers disponibles
                if providers_list and CASCADE_AVAILABLE:
                    self.cascade_nlu_provider = CascadeProvider(providers_list)
                    logger.info(f"[FSM] CascadeProvider NLU creado: {[p.provider_name for p in providers_list]}")

                # Crear HybridNLU con el CascadeProvider
                nlu_config = {
                    'patterns_path': '/app/data/learning/learned_intents.json',
                    'connectivity_check_interval': 30
                }
                self.hybrid_nlu = init_hybrid_nlu(
                    llm_provider=self.cascade_nlu_provider,  # Cascade en lugar de solo Cerebras
                    config=nlu_config,
                    menu=self.menu
                )
                mode = f"Cascade({len(providers_list)})+Regex" if self.cascade_nlu_provider else 'Solo Regex'
                logger.info(f"[FSM] HybridNLU habilitado | Modo: {mode} | Menú: {len(self.menu)} productos")
            except Exception as e:
                logger.warning(f"[FSM] HybridNLU no disponible: {e}")
                self.hybrid_nlu = None

        # Sesiones activas (session_id -> StateContext)
        self.sessions: Dict[str, StateContext] = {}

        # Memoria de conversación por sesión
        self.session_memories: Dict[str, ConversationMemory] = {}

        # Tiempos de inicio de sesión (para métricas)
        self.session_start_times: Dict[str, float] = {}

        # Configuración de límites
        limits_config = config.get('limits', {}) if config else {}
        self.max_upsell_attempts = limits_config.get('max_upsell_attempts', 2)
        self.max_crosssell_attempts = limits_config.get('max_crosssell_attempts', 1)

        # Log de componentes habilitados
        components = []
        if self.hybrid_nlu: components.append("HybridNLU(Cerebras)")
        if self.enhanced_classifier: components.append("EnhancedClassifier")
        if self.semantic_search: components.append("SemanticSearch")
        if self.product_validator: components.append("ProductValidator")
        if self.event_bus: components.append("EventBus")
        if self.feedback_loop: components.append("FeedbackLoop")
        if self.metrics: components.append("Metrics")
        if self.multi_order_parser: components.append("MultiOrderParser")
        if PATTERN_LEARNER_AVAILABLE:
            learner = get_pattern_learner() if 'get_pattern_learner' in dir() else None
            if learner:
                components.append("PatternLearner")

        logger.info(f"[FSM] Máquina de estados v3.0 inicializada | Componentes: {', '.join(components) or 'básicos'}")

    def update_menu(self, menu: List[Dict]):
        """Actualiza el menú"""
        self.menu = menu
        self.decision_tree.update_menu(menu)
        self.product_matcher.update_menu(menu)
        if self.multi_order_parser:
            self.multi_order_parser.update_menu(menu)
        logger.info(f"[FSM] Menú actualizado: {len(menu)} productos")

    def get_or_create_session(self, session_id: str) -> StateContext:
        """Obtiene o crea el contexto de una sesión"""
        if session_id not in self.sessions:
            self.sessions[session_id] = StateContext()
            # Crear memoria de conversación para la sesión
            self.session_memories[session_id] = create_conversation_memory(self.config)
            # Registrar tiempo de inicio para métricas
            self.session_start_times[session_id] = time.time()

            # Track metrics
            if METRICS_AVAILABLE:
                track_conversation_start()

            # Emit event
            self._emit_event(EventType.CONVERSATION_STARTED, {
                "session_id": session_id,
                "timestamp": time.time()
            }, session_id)

            logger.info(f"[FSM] Nueva sesión creada: {session_id}")
        return self.sessions[session_id]

    def get_session_memory(self, session_id: str) -> Optional[ConversationMemory]:
        """Obtiene la memoria de conversación de una sesión"""
        return self.session_memories.get(session_id)

    def process(
        self,
        session_id: str,
        user_input: str,
        force_intent: Intent = None
    ) -> ProcessResult:
        """
        Procesa un mensaje del usuario.

        Args:
            session_id: ID de la sesión
            user_input: Texto del usuario
            force_intent: Intent forzado (para bypass del árbol de decisión)

        Returns:
            ProcessResult con la respuesta y metadatos
        """
        process_start_time = time.time()
        context = self.get_or_create_session(session_id)
        memory = self.get_session_memory(session_id)

        # Agregar a historial y memoria
        context.add_to_history('user', user_input)

        logger.info(f"[FSM] Procesando: '{user_input}' | Estado: {context.state.value}")

        # === EMIT EVENT: Message Received ===
        self._emit_event(EventType.MESSAGE_RECEIVED, {
            "text": user_input,
            "state": context.state.value
        }, session_id)

        # 1. Clasificar intención - PRIORIDAD: HybridNLU (Cerebras) > Enhanced > DecisionTree
        classification_method = "regex"
        if force_intent:
            intent_result = IntentResult(
                intent=force_intent,
                confidence=1.0,
                entities={},
                reason="Intent forzado"
            )
            classification_method = "forced"
        elif self.hybrid_nlu:
            # === v3.0: USAR HYBRID NLU (Cerebras LLM-first) ===
            nlu_context = {
                'cart_items': [item.name for item in context.order_items],
                'current_state': context.state.value,
                'active_category': context.active_category
            }
            nlu_result = self.hybrid_nlu.classify(user_input, nlu_context)

            # === OPTIMIZACIÓN: Si HybridNLU ya generó respuesta, usarla directamente ===
            if nlu_result.has_direct_response and nlu_result.llm_response:
                logger.info(f"[FSM] Respuesta directa de Cerebras (sin segunda llamada)")

                # Construir visual_data basado en entidades
                visual_data = self._build_visual_data_for_conversation(
                    nlu_result.entities,
                    nlu_result.entities.get('category')
                )

                result = ProcessResult(
                    response_text=nlu_result.llm_response,
                    intent=nlu_result.intent,
                    new_state=context.state,
                    visual_data=visual_data
                )

                # Guardar en historial
                context.add_to_history('user', user_input, nlu_result.intent)
                context.add_to_history('assistant', result.response_text, nlu_result.intent)

                if memory:
                    memory.add_turn('user', user_input, nlu_result.intent, context.state.value)
                    memory.add_turn('assistant', result.response_text, nlu_result.intent, context.state.value)

                return result

            # Si no hay respuesta directa, continuar con el flujo normal
            # Convertir NLUResult a IntentResult
            try:
                intent_enum = Intent(nlu_result.intent)
            except ValueError:
                # Intent no reconocido, mapear a UNKNOWN
                intent_enum = Intent.UNKNOWN if hasattr(Intent, 'UNKNOWN') else Intent.VIEW_MENU
                logger.warning(f"[FSM] Intent '{nlu_result.intent}' no mapeado a enum")

            # === OPTIMIZACIÓN: Incluir productos extraídos en entities ===
            entities_with_products = nlu_result.entities.copy()
            if nlu_result.has_extracted_products and nlu_result.extracted_products:
                entities_with_products['_extracted_products'] = nlu_result.extracted_products
                entities_with_products['_has_extracted_products'] = True
                entities_with_products['_nlu_confidence'] = nlu_result.confidence  # Pasar confianza para validación
                logger.info(f"[FSM] Productos de Cerebras: {len(nlu_result.extracted_products)} items (confianza: {nlu_result.confidence:.2f})")

            intent_result = IntentResult(
                intent=intent_enum,
                confidence=nlu_result.confidence,
                entities=entities_with_products,
                reason=f"HybridNLU ({nlu_result.source})",
                requires_llm=False  # HybridNLU ya usó el LLM
            )
            classification_method = f"hybrid_nlu_{nlu_result.source}"
            logger.info(f"[FSM] HybridNLU: {nlu_result.intent} ({nlu_result.source}, {nlu_result.confidence:.2f}, {nlu_result.latency_ms:.0f}ms)")
        elif self.enhanced_classifier:
            # Fallback a Enhanced Classifier (NLU + Regex)
            enhanced_result = self.enhanced_classifier.classify(user_input, context)
            intent_result = IntentResult(
                intent=enhanced_result.intent,
                confidence=enhanced_result.confidence,
                entities=enhanced_result.entities,
                reason=enhanced_result.reason,
                requires_llm=enhanced_result.requires_llm
            )
            classification_method = enhanced_result.method
            logger.info(f"[FSM] Enhanced Classifier usado: {classification_method}")
        else:
            # Fallback final a Decision Tree (solo regex)
            intent_result = self.decision_tree.classify(user_input, context)

        logger.info(f"[FSM] Intent: {intent_result.intent.value} (conf: {intent_result.confidence:.2f}) via {classification_method}")

        # === TRACK METRICS: Intent Classification ===
        if METRICS_AVAILABLE:
            track_intent(intent_result.intent.value, intent_result.confidence, classification_method)

        # === EMIT EVENT: Intent Classified ===
        self._emit_event(EventType.INTENT_CLASSIFIED, {
            "intent": intent_result.intent.value,
            "confidence": intent_result.confidence,
            "method": classification_method,
            "entities": intent_result.entities
        }, session_id)

        # 2. Si requiere LLM, usar el fallback handler inteligente
        if intent_result.requires_llm:
            # Pasar el intent detectado para que CascadeProvider use GPT-4o si es premium
            fallback_result = self.fallback_handler.handle_fallback(
                user_input=user_input,
                context=context,
                menu=self.menu,
                detected_intent=intent_result.intent.value  # Para cascade con GPT-4o
            )

            logger.info(f"[FSM] Fallback usado: {fallback_result.strategy_used.value} | "
                       f"Intent inferido: {fallback_result.inferred_intent}")

            # Si el fallback infirió una intención válida, procesarla
            if fallback_result.should_transition and fallback_result.inferred_intent:
                # Convertir intent string a enum
                try:
                    inferred_intent = Intent(fallback_result.inferred_intent)
                    intent_result = IntentResult(
                        intent=inferred_intent,
                        confidence=fallback_result.confidence,
                        entities=fallback_result.entities,
                        reason=f"Fallback: {fallback_result.strategy_used.value}"
                    )
                except ValueError:
                    # Intent no reconocido, usar la respuesta del fallback directamente
                    result = ProcessResult(
                        response_text=fallback_result.response_text,
                        intent=fallback_result.inferred_intent or 'fallback',
                        new_state=context.state,
                        requires_llm_fallback=False
                    )

                    # Guardar en historial y memoria
                    context.add_to_history('assistant', result.response_text, 'fallback')
                    if memory:
                        memory.add_turn('user', user_input, 'unknown', context.state.value)
                        memory.add_turn('assistant', result.response_text, 'fallback', context.state.value)

                    return result
            else:
                # Usar respuesta del fallback directamente
                result = ProcessResult(
                    response_text=fallback_result.response_text,
                    intent=fallback_result.inferred_intent or 'fallback',
                    new_state=context.state,
                    requires_llm_fallback=False
                )

                context.add_to_history('assistant', result.response_text, 'fallback')
                if memory:
                    memory.add_turn('user', user_input, 'unknown', context.state.value)
                    memory.add_turn('assistant', result.response_text, 'fallback', context.state.value)

                return result

        # 3. Procesar según el estado actual y la intención
        result = self._process_by_state(context, intent_result, user_input)

        # 4. Guardar en historial y memoria
        context.add_to_history('assistant', result.response_text, intent_result.intent.value)
        if memory:
            memory.add_turn(
                'user', user_input, intent_result.intent.value,
                context.state.value, intent_result.entities
            )
            memory.add_turn(
                'assistant', result.response_text, intent_result.intent.value,
                result.new_state.value
            )

        return result

    def _process_by_state(
        self,
        context: StateContext,
        intent_result: IntentResult,
        user_input: str
    ) -> ProcessResult:
        """Procesa según el estado actual"""

        intent = intent_result.intent
        entities = intent_result.entities

        # ============================================================
        # NIVEL 0: SOLICITUDES DE SERVICIO (máxima prioridad)
        # Se procesan ANTES que cualquier flujo de venta
        # El pedido actual NO se interrumpe
        # ============================================================

        if intent == Intent.SERVICE_REQUEST:
            return self._handle_service_request(context, entities, user_input)

        if intent == Intent.REQUEST_WAITER:
            return self._handle_request_waiter(context, user_input)

        if intent == Intent.REQUEST_BILL:
            return self._handle_request_bill(context, user_input)

        # ============================================================
        # MANEJO DE INTENCIONES GLOBALES (cualquier estado)
        # ============================================================

        if intent == Intent.GREETING:
            return self._handle_greeting(context, user_input)

        if intent == Intent.GOODBYE:
            return self._handle_goodbye(context, user_input)

        if intent == Intent.FINISH_ORDER:
            return self._handle_finish_order(context, user_input)

        if intent == Intent.MODIFY_ORDER:
            return self._handle_modify_order(context, entities, user_input)

        # ============================================================
        # MODO HÍBRIDO v2: RESPUESTA DIRECTA YA MANEJADA ARRIBA
        # La respuesta directa de Cerebras ahora se genera en HybridNLU
        # y se procesa inmediatamente después de classify().
        # Este bloque ahora es solo fallback si Cerebras no pudo responder.
        # ============================================================
        # NOTA: El flujo optimizado ya retornó arriba si había respuesta directa.
        # Si llegamos aquí con un intent conversacional, usamos el FSM normal.

        # ============================================================
        # MANEJO POR ESTADO
        # ============================================================

        state = context.state

        # INICIO / BIENVENIDA
        if state in [ConversationState.INICIO, ConversationState.BIENVENIDA]:
            return self._handle_initial_state(context, intent, entities, user_input)

        # EXPLORACIÓN
        if state == ConversationState.EXPLORACION:
            return self._handle_exploration_state(context, intent, entities, user_input)

        # MICRO-EMBUDO
        if state == ConversationState.MICRO_EMBUDO:
            return self._handle_micro_funnel_state(context, intent, entities, user_input)

        # PRODUCTO SELECCIONADO
        if state == ConversationState.PRODUCTO_SELECCIONADO:
            return self._handle_product_selected_state(context, intent, entities)

        # UPSELL
        if state == ConversationState.UPSELL:
            return self._handle_upsell_state(context, intent, entities, user_input)

        # CROSS-SELL
        if state == ConversationState.CROSS_SELL:
            return self._handle_crosssell_state(context, intent, entities, user_input)

        # CONFIRMACIÓN
        if state == ConversationState.CONFIRMACION:
            return self._handle_confirmation_state(context, intent, entities, user_input)

        # Estado no manejado - intentar manejar por intent
        return self._handle_by_intent(context, intent, entities, user_input)

    # ============================================================
    # HANDLERS DE INTENCIONES GLOBALES
    # ============================================================

    def _handle_greeting(self, context: StateContext, user_input: str = "") -> ProcessResult:
        """Maneja saludo"""
        context.set_state(ConversationState.BIENVENIDA)

        # Encontrar producto destacado
        popular = self._get_popular_product()
        producto_destacado = popular['name'] if popular else "nuestros platillos"

        # Obtener historial para LLM
        conversation_history = self._get_conversation_history(context)

        response = self.response_generator.generate(
            state=ConversationState.BIENVENIDA,
            context=context,
            user_input=user_input or "Hola",
            intent='greeting',
            extra_context={'producto_destacado': popular} if popular else None,
            conversation_history=conversation_history,
            variables={'producto_destacado': producto_destacado}
        )

        # Log del provider usado
        logger.info(f"[FSM] Provider: {response.provider_used} | Fallback: {response.fallback_to_template}")

        return ProcessResult(
            response_text=response.text,
            intent=Intent.GREETING.value,
            new_state=context.state,
            visual_data=response.visual_data
        )

    def _handle_goodbye(self, context: StateContext, user_input: str = "") -> ProcessResult:
        """Maneja despedida"""
        context.set_state(ConversationState.CIERRE)

        conversation_history = self._get_conversation_history(context)
        response = self.response_generator.generate_closing(
            context,
            user_input=user_input or "Gracias, hasta luego",
            conversation_history=conversation_history
        )

        logger.info(f"[FSM] Provider: {response.provider_used} | Fallback: {response.fallback_to_template}")

        return ProcessResult(
            response_text=response.text,
            intent=Intent.GOODBYE.value,
            new_state=context.state
        )

    def _handle_view_menu(self, context: StateContext, user_input: str = "") -> ProcessResult:
        """Maneja solicitud de ver menú usando LLM"""
        context.set_state(ConversationState.EXPLORACION)

        # Obtener categorías disponibles
        categories = self._get_available_categories()
        popular = self._get_popular_product()
        conversation_history = self._get_conversation_history(context)

        extra_context = {
            'categories': categories,
            'popular_product': popular
        }

        response = self.response_generator.generate(
            state=ConversationState.EXPLORACION,
            context=context,
            user_input=user_input or "Quiero ver el menú",
            intent='view_menu',
            extra_context=extra_context,
            conversation_history=conversation_history,
            variables={
                'categorias': ', '.join(categories[:5]),
                'producto_popular': popular['name'] if popular else 'todo'
            }
        )

        logger.info(f"[FSM] Provider: {response.provider_used} | Fallback: {response.fallback_to_template}")

        return ProcessResult(
            response_text=response.text,
            intent=Intent.VIEW_MENU.value,
            new_state=context.state
        )

    def _handle_finish_order(self, context: StateContext, user_input: str = "") -> ProcessResult:
        """Maneja señal de cierre - SIEMPRE pasa por cross-sell antes de confirmar"""
        if not context.order_items:
            return ProcessResult(
                response_text="Tu pedido está vacío. ¿Qué te gustaría ordenar?",
                intent=Intent.FINISH_ORDER.value,
                new_state=context.state
            )

        # CROSS-SELL OBLIGATORIO: Si no ha pasado por cross-sell, ofrecer ahora
        if not context.crosssell_offered:
            context.crosssell_offered = True
            return self._offer_crosssell(context, user_input)

        # Ya pasó por cross-sell, ir a confirmación
        context.set_state(ConversationState.CONFIRMACION)
        conversation_history = self._get_conversation_history(context)
        response = self.response_generator.generate_confirmation(
            context,
            is_final=True,
            user_input=user_input or "Es todo, confirmar pedido",
            conversation_history=conversation_history
        )

        logger.info(f"[FSM] Provider: {response.provider_used} | Fallback: {response.fallback_to_template}")

        return ProcessResult(
            response_text=response.text,
            intent=Intent.FINISH_ORDER.value,
            new_state=context.state
        )

    # ============================================================
    # HANDLERS POR ESTADO
    # ============================================================

    def _handle_initial_state(
        self,
        context: StateContext,
        intent: Intent,
        entities: Dict,
        user_input: str
    ) -> ProcessResult:
        """Maneja estados iniciales"""

        if intent == Intent.VIEW_CATEGORY:
            return self._enter_micro_funnel(context, entities)

        if intent == Intent.GET_RECOMMENDATION:
            # Sin categoría activa, iniciar embudo de recomendación
            return self._start_recommendation_funnel(context)

        if intent == Intent.ADD_TO_ORDER:
            # Intenta agregar directamente
            return self._handle_add_to_order(context, entities, user_input)

        if intent == Intent.REMOVE_FROM_ORDER:
            # Quitar producto del pedido
            return self._handle_remove_from_order(context, entities, user_input)

        # PREGUNTAS SOBRE PRODUCTO (precio, ingredientes, etc.)
        if intent in [Intent.ASK_PRICE, Intent.ASK_INGREDIENTS, Intent.ASK_SPICY, Intent.ASK_SIZE]:
            return self._handle_product_question(context, intent, entities, user_input)

        # VER DETALLES DE PRODUCTO ESPECÍFICO (abre modal en UI)
        if intent == Intent.VIEW_PRODUCT_DETAILS:
            return self._handle_view_product_details(context, entities, user_input)

        # Por defecto, preguntar qué desea
        return ProcessResult(
            response_text="¿Qué te gustaría ordenar? Tenemos hamburguesas, tacos, bebidas y más.",
            intent=intent.value,
            new_state=context.state
        )

    def _handle_exploration_state(
        self,
        context: StateContext,
        intent: Intent,
        entities: Dict,
        user_input: str
    ) -> ProcessResult:
        """Maneja estado de exploración"""

        if intent == Intent.VIEW_CATEGORY:
            return self._enter_micro_funnel(context, entities)

        if intent == Intent.GET_RECOMMENDATION:
            return self._start_recommendation_funnel(context)

        return self._handle_by_intent(context, intent, entities, user_input)

    def _handle_micro_funnel_state(
        self,
        context: StateContext,
        intent: Intent,
        entities: Dict,
        user_input: str
    ) -> ProcessResult:
        """
        Maneja estado de micro-embudo (categoría activa).
        REGLA CRÍTICA: Permanecer en el contexto de la categoría activa.
        """

        # Verificar si hay categoría activa
        if not context.is_category_active():
            # Si expiró, ir a exploración
            context.set_state(ConversationState.EXPLORACION)
            return self._handle_exploration_state(context, intent, entities, user_input)

        # CAMBIO DE CATEGORÍA: Si menciona otra categoría
        if intent == Intent.VIEW_CATEGORY:
            new_category = entities.get('category')
            if new_category and new_category != context.active_category:
                return self._enter_micro_funnel(context, entities)

        # RECOMENDACIÓN DENTRO DEL MICRO-EMBUDO
        if intent == Intent.GET_RECOMMENDATION:
            return self._recommend_in_category(context, entities, user_input)

        # AGREGAR AL PEDIDO
        if intent == Intent.ADD_TO_ORDER:
            return self._handle_add_to_order(context, entities, user_input)

        # ACEPTAR SUGERENCIA
        if intent == Intent.ACCEPT_SUGGESTION:
            return self._handle_accept_in_funnel(context)

        # PREGUNTAS SOBRE PRODUCTO (permanecer en embudo)
        if intent in [Intent.ASK_PRICE, Intent.ASK_INGREDIENTS, Intent.ASK_SPICY, Intent.ASK_SIZE]:
            return self._handle_product_question(context, intent, entities, user_input)

        # VER DETALLES DE PRODUCTO ESPECÍFICO (abre modal en UI)
        if intent == Intent.VIEW_PRODUCT_DETAILS:
            return self._handle_view_product_details(context, entities, user_input)

        # Por defecto, mantener en el embudo
        return self._recommend_in_category(context, entities, user_input)

    def _handle_product_selected_state(
        self,
        context: StateContext,
        intent: Intent,
        entities: Dict
    ) -> ProcessResult:
        """Maneja estado de producto seleccionado"""

        # Transición automática a upsell
        context.set_state(ConversationState.UPSELL)
        return self._offer_upsell(context)

    def _handle_upsell_state(
        self,
        context: StateContext,
        intent: Intent,
        entities: Dict,
        user_input: str = ""
    ) -> ProcessResult:
        """Maneja estado de upsell"""

        if intent == Intent.ACCEPT_SUGGESTION:
            context.record_upsell_accepted()
            # Agregar el upsell al pedido
            # TODO: Agregar lógica específica de qué se aceptó

            # === EMIT EVENT & TRACK: Upsell Accepted ===
            self._emit_event(EventType.UPSELL_ACCEPTED, {
                "upsell_item": context.last_upsell_offered,
                "attempt": context.upsell_attempts
            })
            if METRICS_AVAILABLE:
                track_upsell("accepted", 0)

            context.set_state(ConversationState.CROSS_SELL)
            return self._offer_crosssell(context, user_input)

        if intent == Intent.REJECT_SUGGESTION:
            context.increment_upsell_attempts()
            context.add_rejected_suggestion(context.last_upsell_offered or "upsell")

            # === EMIT EVENT & TRACK: Upsell Rejected ===
            self._emit_event(EventType.UPSELL_REJECTED, {
                "upsell_item": context.last_upsell_offered,
                "attempt": context.upsell_attempts
            })
            if METRICS_AVAILABLE:
                track_upsell("rejected", 0)

            # CORREGIDO: Después de max intentos, pasar directamente a cross-sell
            # max_upsell_attempts = 2 significa: 1 oferta inicial + 1 alternativa = 2 intentos
            if context.upsell_attempts >= self.max_upsell_attempts:
                # Máximo intentos, ir a cross-sell
                context.set_state(ConversationState.CROSS_SELL)
                return self._offer_crosssell(context, user_input)
            else:
                # Ofrecer alternativa menor (solo una vez)
                return self._offer_upsell_alternative(context, user_input)

        # Si el usuario quiere algo diferente (añadir al pedido, ver menú, etc.)
        if intent in [Intent.ADD_TO_ORDER, Intent.VIEW_MENU, Intent.VIEW_CATEGORY, Intent.FINISH_ORDER, Intent.REMOVE_FROM_ORDER]:
            return self._handle_by_intent(context, intent, entities, user_input)

        # Para cualquier otra intención, respetar la decisión del cliente y avanzar
        # Esto evita loops infinitos de upsell
        context.set_state(ConversationState.CROSS_SELL)
        return self._offer_crosssell(context, user_input)

    def _handle_crosssell_state(
        self,
        context: StateContext,
        intent: Intent,
        entities: Dict,
        user_input: str = ""
    ) -> ProcessResult:
        """Maneja estado de cross-sell"""

        if intent == Intent.ACCEPT_SUGGESTION:
            context.record_crosssell_accepted()
            # Ir al micro-embudo de la nueva categoría
            # TODO: Determinar qué categoría se aceptó
            context.set_state(ConversationState.CONFIRMACION)
            return self._generate_confirmation(context, user_input)

        if intent == Intent.REJECT_SUGGESTION:
            context.set_state(ConversationState.CONFIRMACION)
            return self._generate_confirmation(context, user_input)

        return self._handle_by_intent(context, intent, entities, user_input)

    def _handle_confirmation_state(
        self,
        context: StateContext,
        intent: Intent,
        entities: Dict,
        user_input: str = ""
    ) -> ProcessResult:
        """Maneja estado de confirmación"""

        # Cerrar pedido con aceptación, confirmación o finish
        if intent in [Intent.ACCEPT_SUGGESTION, Intent.FINISH_ORDER, Intent.CONFIRM_ORDER]:
            context.set_state(ConversationState.CIERRE)

            # Preparar datos del pedido para enviar a cocina
            order_items_data = []
            for item in context.order_items:
                item_data = {
                    "product_id": item.product_id,
                    "name": item.name,
                    "quantity": item.quantity,
                    "price": item.price
                }
                if hasattr(item, 'notes') and item.notes:
                    item_data["notes"] = item.notes
                if hasattr(item, 'extras') and item.extras:
                    item_data["extras"] = item.extras
                order_items_data.append(item_data)

            order_data = {
                "items": order_items_data,
                "total": context.order_total,
                "summary": context.get_order_summary() if hasattr(context, 'get_order_summary') else ""
            }

            # === EMIT EVENT & TRACK: Order Confirmed ===
            self._emit_event(EventType.ORDER_CONFIRMED, {
                "order_total": context.order_total,
                "items_count": len(context.order_items),
                "items": [{"name": item.name, "quantity": item.quantity, "price": item.price}
                          for item in context.order_items]
            })
            if METRICS_AVAILABLE:
                track_order("confirmed", context.order_total, len(context.order_items))

            # Generar despedida con LLM
            conversation_history = self._get_conversation_history(context)
            response = self.response_generator.generate_closing(
                context,
                user_input=user_input,
                conversation_history=conversation_history
            )

            # Agregar total al texto si no está incluido
            response_text = response.text
            if f"${context.order_total:.2f}" not in response_text and context.order_total > 0:
                response_text = f"{response_text} Total: ${context.order_total:.2f}."

            logger.info(f"[FSM] Pedido confirmado: {len(order_items_data)} items, total ${context.order_total:.2f}")

            return ProcessResult(
                response_text=response_text,
                intent=Intent.CONFIRM_ORDER.value,
                new_state=context.state,
                order_confirmed=True,  # Indica que debe enviarse a cocina
                order_data=order_data  # Datos del pedido
            )

        if intent == Intent.VIEW_CATEGORY:
            # Quiere agregar más
            return self._enter_micro_funnel(context, entities)

        # Si rechaza, preguntar qué quiere hacer
        if intent == Intent.REJECT_SUGGESTION:
            return ProcessResult(
                response_text="¿Quieres agregar algo más al pedido o lo dejamos así?",
                intent=intent.value,
                new_state=context.state
            )

        return self._generate_confirmation(context, user_input)

    # ============================================================
    # FUNCIONES DE MICRO-EMBUDO
    # ============================================================

    def _enter_micro_funnel(
        self,
        context: StateContext,
        entities: Dict
    ) -> ProcessResult:
        """Entra al micro-embudo de una categoría"""

        category = entities.get('category', '')
        menu_category = entities.get('menu_category', category)

        # Obtener productos de la categoría
        products = self.decision_tree.get_products_by_category(category)

        if not products:
            return ProcessResult(
                response_text=f"No tenemos {category} disponibles. ¿Te interesa otra cosa?",
                intent=Intent.VIEW_CATEGORY.value,
                new_state=context.state
            )

        # Actualizar contexto
        context.set_active_category(category, products)
        context.set_state(ConversationState.MICRO_EMBUDO)

        # Generar respuesta de listado
        response = self.response_generator.generate_category_list(category, products, context)

        logger.info(f"[FSM] Entrando a micro-embudo: {category} ({len(products)} productos)")

        return ProcessResult(
            response_text=response.text,
            intent=Intent.VIEW_CATEGORY.value,
            new_state=context.state,
            visual_data=response.visual_data
        )

    def _recommend_in_category(
        self,
        context: StateContext,
        entities: Dict,
        user_input: str
    ) -> ProcessResult:
        """
        Recomienda un producto DENTRO de la categoría activa.
        REGLA: Si el usuario menciona un producto específico, recomendar ESE producto.
        Usa fuzzy matching para detectar productos mencionados.
        """

        if not context.active_category_products:
            return self._enter_micro_funnel(context, {'category': context.active_category})

        user_lower = user_input.lower()

        # 0. DETECTAR BÚSQUEDA POR PRECIO (más barato/más caro)
        price_preference = self._detect_price_preference(user_lower)
        if price_preference:
            return self._recommend_by_price(context, price_preference)

        # 1. Usar ProductMatcher para detectar producto mencionado (fuzzy matching)
        matches = self.product_matcher.find_product(
            user_input,
            category_products=context.active_category_products,
            top_n=1
        )

        if matches and matches[0].confidence >= 0.6:
            product = matches[0].product
            context.set_mentioned_product(product['name'], product)

            logger.info(f"[FSM] Producto detectado: {product['name']} "
                       f"(match: {matches[0].match_type}, conf: {matches[0].confidence:.2f})")

            response = self.response_generator.generate_recommendation(product, context, is_mentioned=True)

            return ProcessResult(
                response_text=response.text,
                intent=Intent.GET_RECOMMENDATION.value,
                new_state=context.state,
                visual_data=response.visual_data
            )

        # 2. Fallback: Detectar con método original del decision_tree
        mentioned = self.decision_tree._detect_mentioned_product(user_input, context)

        if mentioned:
            for p in context.active_category_products:
                if p['name'].lower() == mentioned.lower():
                    context.set_mentioned_product(mentioned, p)
                    response = self.response_generator.generate_recommendation(p, context, is_mentioned=True)

                    logger.info(f"[FSM] Recomendando producto mencionado (fallback): {p['name']}")

                    return ProcessResult(
                        response_text=response.text,
                        intent=Intent.GET_RECOMMENDATION.value,
                        new_state=context.state,
                        visual_data=response.visual_data
                    )

        # 3. Si no mencionó producto específico, recomendar el popular
        popular = self.decision_tree.get_popular_product(context.active_category_products)

        if popular:
            response = self.response_generator.generate_recommendation(popular, context, is_mentioned=False)

            logger.info(f"[FSM] Recomendando producto popular: {popular['name']}")

            return ProcessResult(
                response_text=response.text,
                intent=Intent.GET_RECOMMENDATION.value,
                new_state=context.state,
                visual_data=response.visual_data
            )

        return ProcessResult(
            response_text="¿Cuál te gustaría probar?",
            intent=Intent.GET_RECOMMENDATION.value,
            new_state=context.state
        )

    def _detect_price_preference(self, user_input: str) -> Optional[str]:
        """
        Detecta si el usuario está pidiendo por precio.

        Returns:
            'cheapest' si pide el más barato
            'expensive' si pide el más caro
            None si no menciona precio
        """
        import re

        # Patrones para "más barato" / "económico"
        cheap_patterns = [
            r'\bmás barat[oa]\b',
            r'\bla barat[oa]\b',
            r'\bel barat[oa]\b',
            r'\bmenos car[oa]\b',
            r'\beconómic[oa]\b',
            r'\bm[áa]s económic[oa]\b',
            r'\bprecio bajo\b',
            r'\bmenor precio\b',
            r'\bm[áa]s accesible\b',
        ]

        # Patrones para "más caro" / "premium"
        expensive_patterns = [
            r'\bmás car[oa]\b',
            r'\bla car[oa]\b',
            r'\bel car[oa]\b',
            r'\bpremium\b',
            r'\bde lujo\b',
            r'\bla mejor\b',
            r'\bel mejor\b',
            r'\bmayor precio\b',
        ]

        for pattern in cheap_patterns:
            if re.search(pattern, user_input):
                return 'cheapest'

        for pattern in expensive_patterns:
            if re.search(pattern, user_input):
                return 'expensive'

        return None

    def _recommend_by_price(self, context: StateContext, preference: str) -> ProcessResult:
        """
        Recomienda producto ordenando por precio.

        Args:
            context: Contexto de la conversación
            preference: 'cheapest' o 'expensive'
        """
        products = context.active_category_products

        if not products:
            return ProcessResult(
                response_text="No tengo productos en esta categoría.",
                intent=Intent.GET_RECOMMENDATION.value,
                new_state=context.state
            )

        # Ordenar por precio
        try:
            sorted_products = sorted(
                products,
                key=lambda p: float(p.get('price', 0)),
                reverse=(preference == 'expensive')
            )
        except (ValueError, TypeError):
            sorted_products = products

        # Tomar el primero (más barato o más caro según preferencia)
        product = sorted_products[0]
        context.set_mentioned_product(product['name'], product)

        price = float(product.get('price', 0))
        product_name = product.get('name', 'este producto')

        if preference == 'cheapest':
            response_text = f"La opción más económica es {product_name} a ${price:.0f}. ¿Te lo preparo?"
            logger.info(f"[FSM] Recomendando producto MÁS BARATO: {product_name} (${price})")
        else:
            response_text = f"Nuestra mejor opción es {product_name} a ${price:.0f}. ¿Te lo preparo?"
            logger.info(f"[FSM] Recomendando producto MÁS CARO: {product_name} (${price})")

        # Generar visual_data
        visual_data = {
            "type": "product_recommendation",
            "product": {
                "id": product.get('id'),
                "name": product_name,
                "price": price,
                "description": product.get('description', ''),
                "image": product.get('image')
            },
            "reason": "price_preference"
        }

        return ProcessResult(
            response_text=response_text,
            intent=Intent.GET_RECOMMENDATION.value,
            new_state=context.state,
            visual_data=visual_data
        )

    def _handle_accept_in_funnel(self, context: StateContext) -> ProcessResult:
        """Maneja aceptación dentro del micro-embudo"""

        # Agregar último producto mencionado/recomendado al pedido
        if context.mentioned_product_data:
            product_data = context.mentioned_product_data
        elif context.active_category_products:
            product_data = self.decision_tree.get_popular_product(context.active_category_products)
        else:
            return ProcessResult(
                response_text="¿Cuál te gustaría?",
                intent=Intent.ACCEPT_SUGGESTION.value,
                new_state=context.state
            )

        if product_data:
            selection = ProductSelection(
                product_id=product_data.get('id', 0),
                name=product_data['name'],
                price=float(product_data.get('price', 0)),
                quantity=1
            )
            context.add_to_order(selection)

            # Ir a upsell
            context.set_state(ConversationState.UPSELL)
            return self._offer_upsell(context)

        return ProcessResult(
            response_text="¡Agregado! ¿Algo más?",
            intent=Intent.ACCEPT_SUGGESTION.value,
            new_state=context.state,
            order_updated=True
        )

    # ============================================================
    # FUNCIONES DE UPSELL/CROSS-SELL
    # ============================================================

    def _offer_upsell(self, context: StateContext, user_input: str = "") -> ProcessResult:
        """
        Ofrece upsell basado en el pedido actual usando datos reales del menú.

        LÓGICA v2.5 CORREGIDA:
        1. Si tiene comida pero NO bebida → ofrecer bebida
        2. Si tiene comida y bebida pero NO complemento → ofrecer complemento
        3. Si ya tiene todo → cross-sell (postre, etc.)

        NOTA: NO ofrecer comida si solo tiene bebida - el cliente
        puede estar empezando y la hamburguesa ya está en el carrito.
        """

        conversation_history = self._get_conversation_history(context)

        # Buscar productos reales en el menú
        complementos = self._get_complementos_from_menu()
        bebidas = self._get_bebidas_from_menu()

        # Obtener último producto agregado para contexto
        last_item = context.order_items[-1] if context.order_items else None
        last_item_name = last_item.name if last_item else "tu pedido"

        # Verificar qué tiene el cliente
        tiene_bebida = context.has_beverage()
        tiene_comida = context.has_main_dish()
        tiene_complemento = context.has_side()

        # Log para debug
        logger.debug(f"[UPSELL] Estado: comida={tiene_comida}, bebida={tiene_bebida}, complemento={tiene_complemento}")
        logger.debug(f"[UPSELL] Items en carrito: {[item.name for item in context.order_items]}")

        # === CASO 1: Tiene comida pero NO bebida → ofrecer bebida ===
        if tiene_comida and not tiene_bebida and bebidas:
            bebida = bebidas[0]
            response = self.response_generator.generate_upsell(
                'extra',
                context,
                user_input=user_input,
                conversation_history=conversation_history,
                extra=bebida['name'],
                benefit="para acompañar",
                price=float(bebida.get('price', 0))
            )
            context.last_upsell_offered = bebida['name']
            logger.info(f"[UPSELL] Ofreciendo bebida: {bebida['name']}")

        # === CASO 2: Tiene comida y bebida, pero NO complemento → ofrecer complemento ===
        elif tiene_comida and tiene_bebida and not tiene_complemento and complementos:
            complemento = complementos[0]
            response = self.response_generator.generate_upsell(
                'extra',
                context,
                user_input=user_input,
                conversation_history=conversation_history,
                extra=complemento['name'],
                benefit=f"va perfecto con {last_item_name}",
                price=float(complemento.get('price', 0))
            )
            context.last_upsell_offered = complemento['name']
            logger.info(f"[UPSELL] Ofreciendo complemento: {complemento['name']}")

        # === CASO 3: Tiene comida pero NO complemento (sin importar bebida) ===
        elif tiene_comida and not tiene_complemento and complementos:
            complemento = complementos[0]
            response = self.response_generator.generate_upsell(
                'extra',
                context,
                user_input=user_input,
                conversation_history=conversation_history,
                extra=complemento['name'],
                benefit=f"va perfecto con {last_item_name}",
                price=float(complemento.get('price', 0))
            )
            context.last_upsell_offered = complemento['name']
            logger.info(f"[UPSELL] Ofreciendo complemento (alt): {complemento['name']}")

        else:
            # Si ya tiene todo o no aplica ningún caso → cross-sell
            logger.info("[UPSELL] Pasando a cross-sell")
            return self._offer_crosssell(context, user_input)

        return ProcessResult(
            response_text=response.text,
            intent='upsell_offer',
            new_state=context.state
        )

    def _offer_upsell_alternative(self, context: StateContext, user_input: str = "") -> ProcessResult:
        """Ofrece alternativa de upsell menor usando datos reales"""

        conversation_history = self._get_conversation_history(context)

        # Buscar alternativa real que NO sea la ya rechazada
        rejected = context.rejected_suggestions or []
        complementos = self._get_complementos_from_menu()
        bebidas = self._get_bebidas_from_menu()

        # Filtrar los ya rechazados
        alt_complementos = [c for c in complementos if c['name'] not in rejected]
        alt_bebidas = [b for b in bebidas if b['name'] not in rejected]

        if alt_complementos:
            alt = alt_complementos[0]
            response = self.response_generator.generate_upsell(
                'alternativa',
                context,
                user_input=user_input,
                conversation_history=conversation_history,
                alternative=alt['name'],
                description=alt.get('description', 'muy bueno'),
                price=float(alt.get('price', 0))
            )
            context.last_upsell_offered = alt['name']
        elif alt_bebidas:
            alt = alt_bebidas[0]
            response = self.response_generator.generate_upsell(
                'alternativa',
                context,
                user_input=user_input,
                conversation_history=conversation_history,
                alternative=alt['name'],
                description='para acompañar',
                price=float(alt.get('price', 0))
            )
            context.last_upsell_offered = alt['name']
        else:
            # Sin alternativas, ir a cross-sell
            return self._offer_crosssell(context, user_input)

        return ProcessResult(
            response_text=response.text,
            intent='upsell_alternative',
            new_state=context.state
        )

    def _offer_crosssell(self, context: StateContext, user_input: str = "") -> ProcessResult:
        """Ofrece cross-sell basado en lo que falta usando datos reales del menú"""

        context.set_state(ConversationState.CROSS_SELL)
        conversation_history = self._get_conversation_history(context)

        # Buscar bebidas y postres reales en el menú
        bebidas = self._get_bebidas_from_menu()
        postres = self._get_postres_from_menu()

        if not context.has_beverage() and bebidas:
            bebida = bebidas[0]
            response = self.response_generator.generate_crosssell(
                'beverage',
                context,
                user_input=user_input,
                conversation_history=conversation_history,
                beverage=bebida['name'],
                state=bebida.get('description', 'muy buena')[:30],
                price=float(bebida.get('price', 0))
            )
            context.last_crosssell_offered = bebida['name']
        elif postres:
            postre = postres[0]
            response = self.response_generator.generate_crosssell(
                'dessert',
                context,
                user_input=user_input,
                conversation_history=conversation_history,
                dessert=postre['name'],
                state=postre.get('description', 'delicioso')[:30]
            )
            context.last_crosssell_offered = postre['name']
        else:
            # Sin opciones de cross-sell, ir directo a confirmación
            context.set_state(ConversationState.CONFIRMACION)
            return self._generate_confirmation(context, user_input)

        return ProcessResult(
            response_text=response.text,
            intent='crosssell_offer',
            new_state=context.state
        )

    # ============================================================
    # HANDLERS DE SOLICITUDES DE SERVICIO
    # ============================================================

    def _handle_service_request(
        self,
        context: StateContext,
        entities: Dict,
        user_input: str
    ) -> ProcessResult:
        """
        Maneja solicitudes de servicio (más salsa, servilletas, limones, etc.)
        IMPORTANTE: No interrumpe el flujo de venta, solo registra y confirma.
        """
        service_item = entities.get('service_item', 'lo solicitado')

        # Registrar la solicitud de servicio
        service_request = context.add_service_request(
            request_type='service_item',
            description=f"Cliente solicita: {service_item}",
            table_id=None  # Se asignará desde la sesión/orden
        )

        # Generar respuesta de confirmación natural
        responses = {
            'salsa': "¡Claro! Enseguida te traigo más salsa.",
            'limón': "Por supuesto, ya te traen más limones.",
            'servilletas': "Listo, en un momento te traen servilletas.",
            'tortillas': "¡Claro! Ya te traen más tortillas calientitas.",
            'chile': "Perfecto, ya te traen más chile.",
            'agua': "Enseguida te traen más agua.",
            'hielo': "Claro, ya te traen hielo.",
            'cubiertos': "Por supuesto, enseguida te traen cubiertos.",
            'sal': "Listo, ya te traen la sal.",
            'pimienta': "Perfecto, ya te traen la pimienta."
        }

        response_text = responses.get(
            service_item,
            f"¡Claro! Ya pedí que te traigan {service_item}."
        )

        # Si hay pedido en curso, agregar continuidad
        if context.order_items:
            response_text += " ¿Algo más para tu pedido?"

        logger.info(f"[FSM] Solicitud de servicio procesada: {service_item}")

        return ProcessResult(
            response_text=response_text,
            intent=Intent.SERVICE_REQUEST.value,
            new_state=context.state,  # NO cambia el estado, mantiene flujo de venta
            service_request=service_request
        )

    def _handle_request_waiter(
        self,
        context: StateContext,
        user_input: str
    ) -> ProcessResult:
        """
        Maneja llamadas al mesero.
        """
        # Registrar la solicitud
        service_request = context.add_service_request(
            request_type='waiter_call',
            description='Cliente solicita atención del mesero',
            table_id=None
        )

        response_text = "El mesero viene en camino. ¿Hay algo en lo que pueda ayudarte mientras tanto?"

        logger.info("[FSM] Llamada a mesero procesada")

        return ProcessResult(
            response_text=response_text,
            intent=Intent.REQUEST_WAITER.value,
            new_state=context.state,  # NO cambia el estado
            service_request=service_request
        )

    def _handle_request_bill(
        self,
        context: StateContext,
        user_input: str
    ) -> ProcessResult:
        """
        Maneja solicitudes de cuenta.
        """
        # Registrar la solicitud
        service_request = context.add_service_request(
            request_type='bill_request',
            description='Cliente solicita la cuenta',
            table_id=None
        )

        # Generar resumen si hay pedido
        if context.order_items:
            order_summary = context.get_order_summary()
            response_text = f"¡Por supuesto! Tu pedido fue: {order_summary}. El mesero te trae la cuenta enseguida."
            context.set_state(ConversationState.CIERRE)
        else:
            response_text = "Enseguida te traen la cuenta. ¡Gracias por tu visita!"
            context.set_state(ConversationState.CIERRE)

        logger.info("[FSM] Solicitud de cuenta procesada")

        return ProcessResult(
            response_text=response_text,
            intent=Intent.REQUEST_BILL.value,
            new_state=context.state,
            service_request=service_request
        )

    # ============================================================
    # FUNCIONES AUXILIARES
    # ============================================================

    def _start_recommendation_funnel(self, context: StateContext) -> ProcessResult:
        """Inicia embudo de recomendación general"""

        response_text = "¿Buscas algo ligero para botanear, algo más llenador como plato fuerte, o algo fresco para tomar?"

        context.set_state(ConversationState.EXPLORACION)

        return ProcessResult(
            response_text=response_text,
            intent=Intent.GET_RECOMMENDATION.value,
            new_state=context.state
        )

    def _handle_add_to_order(
        self,
        context: StateContext,
        entities: Dict,
        user_input: str
    ) -> ProcessResult:
        """
        Maneja agregar producto(s) al pedido CON VALIDACIÓN ESTRICTA.

        ARQUITECTURA CORRECTA:
        - Cerebras SUGIERE productos
        - FSM VALIDA contra el menú real
        - FSM FILTRA productos ya existentes en carrito
        - FSM EJECUTA solo lo validado
        """

        # === PROCESAMIENTO DE PRODUCTOS SUGERIDOS POR CEREBRAS ===
        # FILOSOFÍA: Cerebras es un LLM inteligente que entiende contexto y variantes.
        # Si Cerebras dice que "cocas" = "Coca-Cola", CONFIAMOS en esa interpretación.
        # Solo validamos que el producto EXISTA en el menú real.

        if entities.get('_has_extracted_products') and entities.get('_extracted_products'):
            extracted_products = entities['_extracted_products']
            nlu_confidence = entities.get('_nlu_confidence', 0.9)  # Confianza del NLU

            logger.info(f"[FSM] Cerebras sugirió {len(extracted_products)} productos (confianza: {nlu_confidence:.2f})")

            # Obtener nombres de productos ya en el carrito
            existing_in_cart = set()
            for item in context.order_items:
                existing_in_cart.add(item.name.lower())

            added_items = []
            rejected_items = []

            for item in extracted_products:
                suggested_name = item.get('name', '')
                quantity = item.get('quantity', 1)

                # === VALIDACIÓN ÚNICA: Producto debe existir en menú ===
                product = self._find_product_by_name(suggested_name)

                if not product:
                    # Producto NO existe en el menú - esto SÍ es un error real
                    rejected_items.append(f"{suggested_name} (no existe en menú)")
                    logger.warning(f"[FSM] RECHAZADO: '{suggested_name}' no existe en el menú")
                    continue

                real_name = product.get('name')
                real_price = float(product.get('price', 0))
                product_id = product.get('id', 0)

                # === VALIDACIÓN 2: No duplicar productos ya en carrito ===
                # Esta validación SÍ es necesaria para evitar duplicados accidentales
                if real_name.lower() in existing_in_cart:
                    # En lugar de rechazar, podríamos incrementar cantidad
                    # Pero por ahora solo informamos
                    logger.info(f"[FSM] '{real_name}' ya está en el carrito - considerando como intención de agregar más")
                    # Buscar el item existente y actualizar cantidad
                    for existing_item in context.order_items:
                        if existing_item.name.lower() == real_name.lower():
                            existing_item.quantity += quantity
                            added_items.append(f"+{quantity}x {real_name} (ahora {existing_item.quantity} total)")
                            logger.info(f"[FSM] Cantidad actualizada: {real_name} ahora tiene {existing_item.quantity}")
                            break
                    continue

                # === CEREBRAS INTERPRETÓ CORRECTAMENTE - CONFIAR Y AGREGAR ===
                # Si Cerebras dijo que "cocas" = "Coca-Cola", confiamos en esa interpretación
                # No necesitamos validar si el usuario literalmente dijo "coca-cola"

                selection = ProductSelection(
                    product_id=product_id,
                    name=real_name,
                    price=real_price,
                    quantity=quantity,
                    extras=[],
                    notes=""
                )
                context.add_to_order(selection)
                existing_in_cart.add(real_name.lower())
                added_items.append(f"{quantity}x {real_name}")

                logger.info(f"[FSM] CONFIANDO EN CEREBRAS: {quantity}x {real_name} (${real_price})")

                # Emit event
                self._emit_event(EventType.PRODUCT_ADDED, {
                    "product_name": real_name,
                    "product_id": product_id,
                    "quantity": quantity,
                    "price": real_price,
                    "parsing_method": "cerebras_trusted"
                })

            # Log de resumen
            if rejected_items:
                logger.info(f"[FSM] Productos rechazados por validación: {rejected_items}")

            if added_items:
                logger.info(f"[FSM] Productos agregados después de validación: {len(added_items)}")

                # Generar respuesta
                if len(added_items) == 1:
                    response_text = f"¡Listo! Te agrego {added_items[0]}."
                else:
                    items_text = ", ".join(added_items[:-1]) + f" y {added_items[-1]}"
                    response_text = f"¡Perfecto! Te agrego {items_text}."

                response_text += f" Tu cuenta va en ${context.order_total:.0f}."

                # Ofrecer upsell
                context.set_state(ConversationState.UPSELL)
                upsell = self._offer_upsell(context)

                cart_action = self._build_cart_action(context)

                return ProcessResult(
                    response_text=response_text + " " + upsell.response_text,
                    intent=Intent.ADD_TO_ORDER.value,
                    new_state=context.state,
                    order_updated=True,
                    cart_action=cart_action
                )
            elif rejected_items:
                # Todos los productos fueron rechazados - pedir aclaración
                return ProcessResult(
                    response_text="No encontré ese producto en nuestro menú. ¿Podrías decirme específicamente qué te gustaría ordenar?",
                    intent=Intent.ADD_TO_ORDER.value,
                    new_state=context.state
                )

        # === FALLBACK: MultiOrderParser (Gemini) si Cerebras no extrajo productos ===
        if self.multi_order_parser:
            parse_result = self.multi_order_parser.parse(user_input)

            if parse_result.items and len(parse_result.items) > 0:
                # Si necesita aclaración, preguntar
                if parse_result.needs_clarification and parse_result.clarification_question:
                    return ProcessResult(
                        response_text=parse_result.clarification_question,
                        intent=Intent.ADD_TO_ORDER.value,
                        new_state=context.state
                    )

                # Procesar cada item parseado
                added_items = []
                for parsed_item in parse_result.items:
                    product = self._find_product_for_parsed_item(parsed_item)

                    if product:
                        # Extraer modificadores
                        modifiers_text = ' '.join(parsed_item.modifiers) if parsed_item.modifiers else ''
                        modifiers = self.product_matcher.extract_modifiers(modifiers_text or user_input)
                        notes = self.product_matcher.modifiers_to_notes(modifiers)

                        # Agregar notas de los modificadores parseados
                        if parsed_item.modifiers and not notes:
                            notes = ', '.join(parsed_item.modifiers)

                        # Calcular precio
                        base_price = float(product.get('price', 0))
                        extra_price = modifiers.get('total_extra_price', 0)
                        total_price = base_price + extra_price

                        # Crear selección
                        extras_list = []
                        for extra in modifiers.get('extras', []):
                            if isinstance(extra, dict):
                                extras_list.append(extra['name'])
                            else:
                                extras_list.append(extra)
                        extras_list.extend(modifiers.get('without', []))

                        selection = ProductSelection(
                            product_id=product.get('id', 0),
                            name=product['name'],
                            price=total_price,
                            quantity=parsed_item.quantity,
                            extras=extras_list,
                            notes=notes
                        )
                        context.add_to_order(selection)
                        added_items.append(f"{parsed_item.quantity}x {product['name']}")

                        # Emit event
                        self._emit_event(EventType.PRODUCT_ADDED, {
                            "product_name": product['name'],
                            "product_id": product.get('id', 0),
                            "quantity": parsed_item.quantity,
                            "price": total_price,
                            "parsing_method": parse_result.parsing_method
                        })

                if added_items:
                    logger.info(f"[FSM] Multi-order: {len(added_items)} items agregados via {parse_result.parsing_method}")

                    # Generar respuesta
                    if len(added_items) == 1:
                        response_text = f"¡Listo! Te agrego {added_items[0]}."
                    else:
                        items_text = ", ".join(added_items[:-1]) + f" y {added_items[-1]}"
                        response_text = f"¡Perfecto! Te agrego {items_text}."

                    # Agregar total
                    response_text += f" Tu cuenta va en ${context.order_total:.0f}."

                    # Ofrecer algo más o upsell
                    context.set_state(ConversationState.UPSELL)
                    upsell = self._offer_upsell(context)

                    # Crear cart_action para sincronizar con frontend
                    cart_action = self._build_cart_action(context)

                    return ProcessResult(
                        response_text=response_text + " " + upsell.response_text,
                        intent=Intent.ADD_TO_ORDER.value,
                        new_state=context.state,
                        order_updated=True,
                        cart_action=cart_action
                    )

        # === FALLBACK: Método original para productos individuales ===
        mentioned = entities.get('mentioned_product')
        if not mentioned:
            mentioned = self.decision_tree._detect_mentioned_product(user_input, context)

        # Si no encontró producto explícito, intentar búsqueda semántica
        if not mentioned and self.semantic_search:
            semantic_results = self._search_product_semantic(user_input, top_k=1)
            if semantic_results:
                mentioned = semantic_results[0].get('name')
                logger.info(f"[FSM] Producto encontrado por búsqueda semántica: {mentioned}")

        if mentioned:
            # VALIDAR que el producto existe antes de procesarlo
            exists, validated_product, validation_msg = self._validate_product(
                mentioned,
                context.active_category_products
            )

            if not exists and validation_msg:
                # Producto no encontrado - responder con mensaje de validación
                self._emit_event(EventType.PRODUCT_NOT_FOUND, {
                    "query": mentioned,
                    "user_input": user_input
                })
                return ProcessResult(
                    response_text=validation_msg,
                    intent=Intent.ADD_TO_ORDER.value,
                    new_state=context.state
                )

            # Usar producto validado si está disponible
            product = validated_product or self.decision_tree.find_product_by_name(mentioned)
            if product:
                quantity = entities.get('quantity', 1)

                # EXTRAER MODIFICADORES del texto del usuario
                modifiers = self.product_matcher.extract_modifiers(user_input)
                notes = self.product_matcher.modifiers_to_notes(modifiers)

                # Calcular precio con extras
                base_price = float(product.get('price', 0))
                extra_price = modifiers.get('total_extra_price', 0)
                total_price = base_price + extra_price

                # Crear selección con modificadores
                extras_list = []
                for extra in modifiers.get('extras', []):
                    if isinstance(extra, dict):
                        extras_list.append(extra['name'])
                    else:
                        extras_list.append(extra)
                extras_list.extend(modifiers.get('without', []))

                selection = ProductSelection(
                    product_id=product.get('id', 0),
                    name=product['name'],
                    price=total_price,  # Precio con extras incluidos
                    quantity=quantity,
                    extras=extras_list,
                    notes=notes
                )
                context.add_to_order(selection)

                # Log para debug
                if notes:
                    logger.info(f"[FSM] Producto agregado con modificadores: {product['name']} - {notes} (${total_price})")

                # === EMIT EVENT: Product Added ===
                self._emit_event(EventType.PRODUCT_ADDED, {
                    "product_name": product['name'],
                    "product_id": product.get('id', 0),
                    "quantity": quantity,
                    "price": total_price,
                    "extras": extras_list,
                    "notes": notes
                })

                # === RECORD FEEDBACK: Successful product addition ===
                self._record_feedback(
                    user_input=user_input,
                    intent=Intent.ADD_TO_ORDER.value,
                    confidence=1.0,
                    method="product_match",
                    success=True
                )

                context.set_state(ConversationState.UPSELL)
                upsell_result = self._offer_upsell(context)

                # Agregar cart_action al resultado del upsell
                cart_action = self._build_cart_action(context)
                return ProcessResult(
                    response_text=upsell_result.response_text,
                    intent=Intent.ADD_TO_ORDER.value,
                    new_state=upsell_result.new_state,
                    visual_data=upsell_result.visual_data,
                    order_updated=True,
                    cart_action=cart_action
                )

        # No encontró producto específico - verificar si mencionó una categoría
        detected_category = self._detect_category_in_text(user_input)
        if detected_category:
            logger.info(f"[FSM] Categoría detectada en ADD_TO_ORDER: {detected_category}")
            return self._enter_micro_funnel(context, {'category': detected_category})

    def _handle_modify_order(
        self,
        context: StateContext,
        entities: Dict,
        user_input: str
    ) -> ProcessResult:
        """
        Maneja MODIFICAR producto(s) en el pedido.

        ARQUITECTURA v2.0 - CEREBRAS PRIMERO:
        1. Cerebras extrae datos normalizados (original_product, new_product, action)
        2. FSM solo valida y ejecuta
        3. Regex como fallback si Cerebras no envió datos
        """
        logger.info(f"[FSM] Procesando MODIFY_ORDER: '{user_input}'")

        # Si el carrito está vacío, no hay nada que modificar
        if not context.order_items:
            return ProcessResult(
                response_text="Tu pedido está vacío. ¿Qué te gustaría ordenar?",
                intent=Intent.MODIFY_ORDER.value,
                new_state=context.state
            )

        # === OPCIÓN 1: USAR DATOS DE CEREBRAS (preferido) ===
        if entities.get('_has_modification_data') and entities.get('_modification_data'):
            mod_data = entities['_modification_data']
            action = mod_data.get('action', 'replace')
            original_product = mod_data.get('original_product')
            new_product_name = mod_data.get('new_product')
            new_product_price = mod_data.get('new_product_price', 0)

            logger.info(f"[FSM] Usando datos de Cerebras: {action} | '{original_product}' → '{new_product_name}'")

            # Buscar producto original en el carrito
            item_index, item_to_modify = self._find_item_in_cart(context, original_product)

            if item_to_modify is None:
                cart_items = [f"{item.name}" for item in context.order_items[:5]]
                cart_text = ", ".join(cart_items)
                return ProcessResult(
                    response_text=f"No encontré '{original_product}' en tu pedido. Tienes: {cart_text}.",
                    intent=Intent.MODIFY_ORDER.value,
                    new_state=context.state
                )

            # Ejecutar según la acción
            if action == 'remove':
                return self._execute_remove_item(context, item_index, item_to_modify)
            elif action == 'add_more':
                quantity = mod_data.get('quantity', 1)
                return self._execute_add_more(context, item_to_modify, quantity)
            else:  # replace
                # Validar que el nuevo producto existe
                new_product = self._find_product_by_name(new_product_name)
                if not new_product:
                    return ProcessResult(
                        response_text=f"No encontré '{new_product_name}' en nuestro menú. ¿Por cuál producto te gustaría cambiar?",
                        intent=Intent.MODIFY_ORDER.value,
                        new_state=context.state
                    )
                return self._execute_replace_item(context, item_index, item_to_modify, new_product)

        # === OPCIÓN 2: FALLBACK A REGEX (si Cerebras no envió datos) ===
        logger.info(f"[FSM] Cerebras no envió datos de modificación, usando regex fallback")

        user_input_lower = user_input.lower()
        change_patterns = [
            (r'cambi(?:a|ar?|ame)\s+(?:la\s+|el\s+)?(.+?)\s+por\s+(?:un(?:a)?\s+)?(.+)', 'cambiar'),
            (r'en\s+vez\s+de\s+(?:la\s+|el\s+)?(.+?)\s+(?:dame|quiero|ponme)\s+(?:un(?:a)?\s+)?(.+)', 'en_vez_de'),
            (r'(?:quiero|dame|ponme)\s+(?:un(?:a)?\s+)?(.+?)\s+en\s+lugar\s+de\s+(?:la\s+|el\s+)?(.+)', 'en_lugar_de'),
            (r'(?:sustituy|reemplaz)(?:e|a)\s+(?:la\s+|el\s+)?(.+?)\s+(?:por|con)\s+(?:un(?:a)?\s+)?(.+)', 'sustituir'),
        ]

        original_product = None
        new_product_name = None

        for pattern, pattern_type in change_patterns:
            match = re.search(pattern, user_input_lower)
            if match:
                if pattern_type == 'en_lugar_de':
                    new_product_name = match.group(1).strip()
                    original_product = match.group(2).strip()
                else:
                    original_product = match.group(1).strip()
                    new_product_name = match.group(2).strip()

                # Limpiar puntuación al final
                original_product = re.sub(r'[.,!?]+$', '', original_product).strip()
                new_product_name = re.sub(r'[.,!?]+$', '', new_product_name).strip()

                logger.info(f"[FSM] Patrón regex detectado ({pattern_type}): '{original_product}' → '{new_product_name}'")
                break

        if not original_product or not new_product_name:
            cart_items = [f"{item.name}" for item in context.order_items[:5]]
            cart_text = ", ".join(cart_items)
            return ProcessResult(
                response_text=f"¿Qué cambio quieres hacer? Tienes: {cart_text}. Dime algo como 'cámbiame la coca por limonada'.",
                intent=Intent.MODIFY_ORDER.value,
                new_state=context.state
            )

        # Buscar producto original en el carrito (usando fuzzy matching)
        item_index, item_to_modify = self._find_item_in_cart(context, original_product)

        if item_to_modify is None:
            # El producto original no está en el carrito
            cart_items = [f"{item.name}" for item in context.order_items[:5]]
            cart_text = ", ".join(cart_items)

            return ProcessResult(
                response_text=f"No encontré '{original_product}' en tu pedido. Tienes: {cart_text}.",
                intent=Intent.MODIFY_ORDER.value,
                new_state=context.state
            )

        # === VALIDAR NUEVO PRODUCTO EN EL MENÚ ===
        new_product = self._find_product_by_name(new_product_name)

        if not new_product:
            # El nuevo producto no existe en el menú - sugerir alternativas
            logger.warning(f"[FSM] Producto nuevo no encontrado: '{new_product_name}'")

            # Buscar alternativas similares
            suggestions = []
            if self.semantic_search:
                semantic_results = self._search_product_semantic(new_product_name, top_k=3)
                suggestions = [r.get('name') for r in semantic_results if r.get('name')]

            if suggestions:
                suggestions_text = ", ".join(suggestions[:3])
                return ProcessResult(
                    response_text=f"No tenemos '{new_product_name}'. ¿Te gustaría en cambio: {suggestions_text}?",
                    intent=Intent.MODIFY_ORDER.value,
                    new_state=context.state
                )
            else:
                return ProcessResult(
                    response_text=f"No encontré '{new_product_name}' en nuestro menú. ¿Por cuál producto te gustaría cambiar?",
                    intent=Intent.MODIFY_ORDER.value,
                    new_state=context.state
                )

        # === EJECUTAR EL CAMBIO ===
        old_item_name = item_to_modify.name
        old_quantity = item_to_modify.quantity

        # Remover el producto original
        context.order_items.pop(item_index)

        # Agregar el nuevo producto (manteniendo la cantidad original)
        new_selection = ProductSelection(
            product_id=new_product.get('id', 0),
            name=new_product.get('name'),
            price=float(new_product.get('price', 0)),
            quantity=old_quantity,
            extras=[],
            notes=""
        )
        context.add_to_order(new_selection)

        logger.info(f"[FSM] Modificación ejecutada: '{old_item_name}' → '{new_product.get('name')}'")

        # === EMIT EVENTS ===
        self._emit_event(EventType.PRODUCT_REMOVED, {
            "product_name": old_item_name,
            "reason": "modified"
        })

        self._emit_event(EventType.PRODUCT_ADDED, {
            "product_name": new_product.get('name'),
            "product_id": new_product.get('id', 0),
            "quantity": old_quantity,
            "price": float(new_product.get('price', 0)),
            "parsing_method": "modify_order"
        })

        # Crear cart_action para sincronizar con frontend
        cart_action = self._build_cart_action(context)

        # Generar respuesta
        response_text = f"¡Listo! Te cambié {old_item_name} por {new_product.get('name')}. "
        response_text += f"Tu cuenta va en ${context.order_total:.0f}. ¿Algo más?"

        return ProcessResult(
            response_text=response_text,
            intent=Intent.MODIFY_ORDER.value,
            new_state=context.state,
            order_updated=True,
            cart_action=cart_action
        )

    def _find_item_in_cart(self, context: StateContext, product_name: str) -> Tuple[Optional[int], Optional[ProductSelection]]:
        """
        Busca un producto en el carrito usando fuzzy matching.
        Retorna (índice, item) o (None, None) si no encuentra.
        """
        if not product_name:
            return None, None

        product_name_lower = product_name.lower()

        for idx, item in enumerate(context.order_items):
            item_name_lower = item.name.lower()

            # Coincidencia exacta
            if product_name_lower == item_name_lower:
                return idx, item

            # Coincidencia parcial (el nombre buscado está en el item o viceversa)
            if product_name_lower in item_name_lower or item_name_lower in product_name_lower:
                return idx, item

            # Buscar por palabras clave principales
            keywords = [w for w in product_name_lower.split() if len(w) > 2]
            for keyword in keywords:
                if keyword in item_name_lower:
                    return idx, item

        return None, None

    def _execute_replace_item(
        self,
        context: StateContext,
        item_index: int,
        old_item: ProductSelection,
        new_product: Dict
    ) -> ProcessResult:
        """Ejecuta el reemplazo de un producto por otro."""
        old_item_name = old_item.name
        old_quantity = old_item.quantity

        # Remover el producto original
        context.order_items.pop(item_index)

        # Agregar el nuevo producto
        new_selection = ProductSelection(
            product_id=new_product.get('id', 0),
            name=new_product.get('name'),
            price=float(new_product.get('price', 0)),
            quantity=old_quantity,
            extras=[],
            notes=""
        )
        context.add_to_order(new_selection)

        logger.info(f"[FSM] Reemplazo ejecutado: '{old_item_name}' → '{new_product.get('name')}'")

        # Emit events
        self._emit_event(EventType.PRODUCT_REMOVED, {"product_name": old_item_name, "reason": "replaced"})
        self._emit_event(EventType.PRODUCT_ADDED, {
            "product_name": new_product.get('name'),
            "product_id": new_product.get('id', 0),
            "quantity": old_quantity,
            "price": float(new_product.get('price', 0)),
            "parsing_method": "modify_order_cerebras"
        })

        cart_action = self._build_cart_action(context)
        response_text = f"¡Listo! Te cambié {old_item_name} por {new_product.get('name')}. Tu cuenta va en ${context.order_total:.0f}. ¿Algo más?"

        return ProcessResult(
            response_text=response_text,
            intent=Intent.MODIFY_ORDER.value,
            new_state=context.state,
            order_updated=True,
            cart_action=cart_action
        )

    def _execute_remove_item(
        self,
        context: StateContext,
        item_index: int,
        item: ProductSelection
    ) -> ProcessResult:
        """Ejecuta la eliminación de un producto del carrito."""
        item_name = item.name

        context.order_items.pop(item_index)

        logger.info(f"[FSM] Producto eliminado: '{item_name}'")

        self._emit_event(EventType.PRODUCT_REMOVED, {"product_name": item_name, "reason": "user_request"})

        cart_action = self._build_cart_action(context)

        if context.order_items:
            response_text = f"¡Listo! Quité {item_name} de tu pedido. Tu cuenta va en ${context.order_total:.0f}. ¿Algo más?"
        else:
            response_text = f"Quité {item_name}. Tu pedido está vacío ahora. ¿Qué te gustaría ordenar?"

        return ProcessResult(
            response_text=response_text,
            intent=Intent.MODIFY_ORDER.value,
            new_state=context.state,
            order_updated=True,
            cart_action=cart_action
        )

    def _execute_add_more(
        self,
        context: StateContext,
        item: ProductSelection,
        quantity: int
    ) -> ProcessResult:
        """Ejecuta agregar más cantidad de un producto existente."""
        item.quantity += quantity

        logger.info(f"[FSM] Cantidad incrementada: '{item.name}' ahora tiene {item.quantity}")

        cart_action = self._build_cart_action(context)
        response_text = f"¡Listo! Ahora tienes {item.quantity}x {item.name}. Tu cuenta va en ${context.order_total:.0f}. ¿Algo más?"

        return ProcessResult(
            response_text=response_text,
            intent=Intent.MODIFY_ORDER.value,
            new_state=context.state,
            order_updated=True,
            cart_action=cart_action
        )

    def _handle_remove_from_order(
        self,
        context: StateContext,
        entities: Dict,
        user_input: str
    ) -> ProcessResult:
        """
        Maneja QUITAR producto(s) del pedido.

        v3.0: Nuevo handler para eliminar items del carrito.
        - Busca el producto por nombre o categoría
        - Si hay múltiples coincidencias, pregunta cuál quitar
        - Actualiza el carrito y sincroniza con frontend
        """
        logger.info(f"[FSM] Procesando REMOVE_FROM_ORDER: '{user_input}'")

        # Si el carrito está vacío, no hay nada que quitar
        if not context.order_items:
            return ProcessResult(
                response_text="Tu pedido está vacío, no hay nada que quitar. ¿Qué te gustaría ordenar?",
                intent=Intent.REMOVE_FROM_ORDER.value,
                new_state=context.state
            )

        # Buscar qué producto quiere quitar
        product_to_remove = entities.get('product_to_remove')
        category = entities.get('category')

        # Si no encontró producto específico, buscar en el texto
        if not product_to_remove:
            product_to_remove = self.decision_tree._detect_mentioned_product(user_input, context)

        # Buscar en los items del carrito
        matching_items = []
        for idx, item in enumerate(context.order_items):
            item_name_lower = item.name.lower()

            # Match por nombre específico
            if product_to_remove and product_to_remove.lower() in item_name_lower:
                matching_items.append((idx, item))
            # Match por categoría (hamburguesa, taco, etc.)
            elif category:
                category_lower = category.lower()
                if category_lower in item_name_lower or category_lower.rstrip('s') in item_name_lower:
                    matching_items.append((idx, item))

        # Si no encontró nada, buscar por palabras clave del input
        if not matching_items:
            keywords = ['hamburguesa', 'taco', 'coca', 'agua', 'refresco', 'orden', 'papas', 'ensalada']
            for keyword in keywords:
                if keyword in user_input.lower():
                    for idx, item in enumerate(context.order_items):
                        if keyword in item.name.lower():
                            matching_items.append((idx, item))
                    break

        # Procesar resultado
        if len(matching_items) == 0:
            # No encontró el producto en el carrito
            items_in_cart = ", ".join([f"{item.quantity}x {item.name}" for item in context.order_items])
            return ProcessResult(
                response_text=f"No encontré ese producto en tu pedido. Tienes: {items_in_cart}. ¿Cuál quieres quitar?",
                intent=Intent.REMOVE_FROM_ORDER.value,
                new_state=context.state
            )

        elif len(matching_items) == 1:
            # Encontró exactamente uno - quitarlo
            idx, item_to_remove = matching_items[0]
            removed_name = item_to_remove.name
            removed_qty = item_to_remove.quantity

            # Remover del carrito
            context.order_items.pop(idx)

            logger.info(f"[FSM] Producto eliminado: {removed_qty}x {removed_name}")

            # Construir respuesta
            if context.order_items:
                response_text = f"Listo, quité {removed_qty}x {removed_name} de tu pedido. Tu cuenta va en ${context.order_total:.0f}."
                response_text += " ¿Algo más que quieras modificar?"
            else:
                response_text = f"Listo, quité {removed_qty}x {removed_name}. Tu pedido está vacío ahora. ¿Qué te gustaría ordenar?"
                context.set_state(ConversationState.INICIO)

            # Crear cart_action para sincronizar con frontend
            cart_action = self._build_cart_action(context)

            return ProcessResult(
                response_text=response_text,
                intent=Intent.REMOVE_FROM_ORDER.value,
                new_state=context.state,
                order_updated=True,
                cart_action=cart_action
            )

        else:
            # Encontró múltiples - preguntar cuál
            options = [f"{item.quantity}x {item.name}" for _, item in matching_items]
            options_text = ", ".join(options)
            return ProcessResult(
                response_text=f"Tengo varios productos similares: {options_text}. ¿Cuál quieres que quite?",
                intent=Intent.REMOVE_FROM_ORDER.value,
                new_state=context.state
            )

    def _find_product_for_parsed_item(self, parsed_item) -> Optional[Dict]:
        """Encuentra el producto del menú para un item parseado"""
        product_name = parsed_item.product_name

        # 1. Buscar por nombre exacto
        for product in self.menu:
            if product.get('name', '').lower() == product_name.lower():
                return product

        # 2. Buscar por nombre normalizado
        product_normalized = self._normalize_text(product_name)
        for product in self.menu:
            menu_normalized = self._normalize_text(product.get('name', ''))
            if menu_normalized == product_normalized:
                return product

        # 3. Usar product_matcher para búsqueda fuzzy
        if self.product_matcher:
            matches = self.product_matcher.find_product(product_name, top_n=1)
            if matches and matches[0].confidence >= 0.7:
                return matches[0].product

        # 4. Buscar en aliases del multi_order_parser
        if self.multi_order_parser and product_name.lower() in self.multi_order_parser.product_aliases:
            alias_name = self.multi_order_parser.product_aliases[product_name.lower()]
            for product in self.menu:
                if product.get('name', '').lower() == alias_name.lower():
                    return product

        logger.warning(f"[FSM] Producto no encontrado en menú: {product_name}")
        return None

    def _normalize_text(self, text: str) -> str:
        """Normaliza texto quitando acentos"""
        replacements = {
            'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u',
            'ñ': 'n', 'ü': 'u'
        }
        result = text.lower()
        for accented, plain in replacements.items():
            result = result.replace(accented, plain)
        return result

    def _find_product_by_name(self, product_name: str) -> Optional[Dict]:
        """
        Busca un producto en el menú por nombre.
        Usa múltiples estrategias de búsqueda.
        """
        if not product_name:
            return None

        product_name_lower = product_name.lower().strip()
        product_normalized = self._normalize_text(product_name)

        # 1. Búsqueda exacta
        for product in self.menu:
            if product.get('name', '').lower() == product_name_lower:
                return product

        # 2. Búsqueda normalizada (sin acentos)
        for product in self.menu:
            menu_normalized = self._normalize_text(product.get('name', ''))
            if menu_normalized == product_normalized:
                return product

        # 3. Búsqueda por contenido parcial
        for product in self.menu:
            menu_name = product.get('name', '').lower()
            if product_name_lower in menu_name or menu_name in product_name_lower:
                return product

        # 4. Usar product_matcher para búsqueda fuzzy
        if self.product_matcher:
            matches = self.product_matcher.find_product(product_name, top_n=1)
            if matches and matches[0].confidence >= 0.75:
                return matches[0].product

        return None

    def _extract_product_keywords(self, product_name: str) -> List[str]:
        """
        Extrae palabras clave de un nombre de producto para validación.
        Ej: "Hamburguesa Doble con Queso" → ["hamburguesa", "doble", "queso"]
        """
        if not product_name:
            return []

        # Normalizar y dividir
        normalized = self._normalize_text(product_name)

        # Palabras a ignorar (stopwords)
        stopwords = {'de', 'con', 'al', 'la', 'el', 'los', 'las', 'y', 'o', 'en', 'a'}

        # Extraer palabras significativas
        words = normalized.split()
        keywords = [w for w in words if w not in stopwords and len(w) > 2]

        return keywords

    def _build_cart_action(self, context: StateContext) -> Dict:
        """
        Construye la acción de carrito para sincronizar con el frontend.

        Devuelve un diccionario con:
        - action: 'sync' para sincronizar todo el carrito
        - items: Lista de items con toda la información necesaria
        - total: Total actual del pedido
        """
        items = []
        for item in context.order_items:
            item_data = {
                'id': item.product_id,
                'product_id': item.product_id,
                'name': item.name,
                'price': float(item.price),
                'quantity': item.quantity,
                'modifiers': [],
                'specialNotes': ''
            }

            # Agregar extras/modificadores si existen
            if hasattr(item, 'extras') and item.extras:
                item_data['modifiers'] = [
                    {'id': i, 'name': extra, 'price': 0}
                    for i, extra in enumerate(item.extras)
                ]

            # Agregar notas especiales
            if hasattr(item, 'notes') and item.notes:
                item_data['specialNotes'] = item.notes

            items.append(item_data)

        return {
            'action': 'sync',
            'items': items,
            'total': context.order_total
        }

    def _handle_product_question(
        self,
        context: StateContext,
        intent: Intent,
        entities: Dict,
        user_input: str
    ) -> ProcessResult:
        """Maneja preguntas sobre productos"""

        mentioned = entities.get('mentioned_product')
        if not mentioned:
            mentioned = self.decision_tree._detect_mentioned_product(user_input, context)

        if mentioned:
            product = self.decision_tree.find_product_by_name(mentioned)
            if product:
                response = self.response_generator.generate_product_details(product, context)
                return ProcessResult(
                    response_text=response.text,
                    intent=intent.value,
                    new_state=context.state,
                    visual_data=response.visual_data
                )

        return ProcessResult(
            response_text="¿De cuál producto quieres saber?",
            intent=intent.value,
            new_state=context.state
        )

    # =========================================================================
    # MODO HÍBRIDO: Cerebras responde con menú completo
    # =========================================================================

    def _handle_conversational_with_llm(
        self,
        context: StateContext,
        intent: Intent,
        entities: Dict,
        user_input: str
    ) -> Optional[ProcessResult]:
        """
        MODO HÍBRIDO: Cerebras VE el menú completo y responde directamente.

        Similar a como lo haría un mesero experto que conoce todo el menú.
        El LLM tiene libertad de responder naturalmente, pero el FSM
        sigue controlando las acciones de pedido.

        Returns:
            ProcessResult si el LLM respondió exitosamente
            None si falló (para que FSM use fallback)
        """
        if not self.cascade_nlu_provider:
            logger.debug("[FSM] Modo híbrido: CascadeProvider no disponible, usando fallback")
            return None

        try:
            # 1. Construir resumen del menú para el LLM
            menu_summary = self._build_menu_summary_for_llm()

            # 2. Construir contexto del carrito actual
            cart_context = self._build_cart_context(context)

            # 3. Extraer categoría mencionada si existe
            mentioned_category = entities.get('category') or entities.get('menu_category')

            # 4. Prompt del sistema - El LLM es un mesero experto
            system_prompt = f"""Eres un mesero experto y amigable en un restaurante mexicano. Conoces TODO el menú perfectamente.

MENÚ COMPLETO DEL RESTAURANTE:
{menu_summary}

{cart_context}

INSTRUCCIONES:
1. Responde de forma natural, amigable y conversacional en español
2. Si preguntan por una categoría (tacos, hamburguesas, etc.), muestra las opciones disponibles con precios
3. Si preguntan por un producto específico, da detalles y sugiere complementos
4. Si preguntan por tamaños, porciones o ingredientes, responde con la información del menú
5. Siempre intenta cerrar con una pregunta o sugerencia para vender
6. Sé breve pero informativo (2-4 oraciones máximo)
7. Usa precios en formato $XX.00

IMPORTANTE: NO inventes productos. Solo menciona lo que está en el menú."""

            user_message = f"Cliente: {user_input}"

            # 5. Llamar al CascadeProvider (Cerebras → Gemini)
            logger.info(f"[FSM] Modo híbrido: Consultando LLM con menú completo")
            response = self.cascade_nlu_provider.generate(
                prompt=system_prompt,
                messages=[{"role": "user", "content": user_message}],
                max_tokens=300,
                temperature=0.7
            )

            response_text = response.get('response_text', '').strip()

            if response_text:
                logger.info(f"[FSM] Modo híbrido - Respuesta: '{response_text[:100]}...'")

                # 6. Construir visual_data basado en la categoría/producto mencionado
                visual_data = self._build_visual_data_for_conversation(entities, mentioned_category)

                return ProcessResult(
                    response_text=response_text,
                    intent=intent.value,
                    new_state=context.state,
                    visual_data=visual_data
                )

        except Exception as e:
            logger.warning(f"[FSM] Modo híbrido falló: {e}")

        return None

    def _build_menu_summary_for_llm(self) -> str:
        """
        Construye un resumen del menú optimizado para el LLM.
        Agrupa por categorías y muestra info esencial.
        """
        if not self.menu:
            return "Menú no disponible"

        # Agrupar productos por categoría
        categories = {}
        for product in self.menu:
            cat_name = product.get('category', {}).get('name', 'Otros')
            if cat_name not in categories:
                categories[cat_name] = []
            categories[cat_name].append(product)

        # Construir resumen
        lines = []
        for cat_name, products in categories.items():
            lines.append(f"\n📁 {cat_name.upper()}:")
            for p in products:
                name = p.get('name', 'Sin nombre')
                price = p.get('price', '0')
                desc = p.get('description', '')
                # Truncar descripción
                if desc and len(desc) > 60:
                    desc = desc[:60] + "..."

                line = f"  • {name} - ${price}"
                if desc:
                    line += f" ({desc})"
                lines.append(line)

        return "\n".join(lines)

    def _build_cart_context(self, context: StateContext) -> str:
        """Construye contexto del carrito para el LLM"""
        if not context.order_items:
            return "CARRITO: Vacío (el cliente aún no ha pedido nada)"

        items_str = []
        for item in context.order_items:
            items_str.append(f"  • {item.quantity}x {item.name} (${item.price})")

        total = context.order_total if hasattr(context, 'order_total') else 0
        return f"CARRITO ACTUAL:\n" + "\n".join(items_str) + f"\n  Total: ${total}"

    def _build_visual_data_for_conversation(
        self,
        entities: Dict,
        mentioned_category: Optional[str]
    ) -> Optional[Dict]:
        """Construye visual_data para mostrar productos relevantes en el frontend"""

        # Si hay categoría mencionada, mostrar productos de esa categoría
        if mentioned_category:
            category_products = [
                p for p in self.menu
                if mentioned_category.lower() in p.get('category', {}).get('name', '').lower()
            ]
            if category_products:
                return {
                    'type': 'product_list',
                    'category': mentioned_category,
                    'products': category_products[:6]  # Máximo 6 productos
                }

        # Si hay producto específico
        product_name = entities.get('product') or entities.get('mentioned_product')
        if product_name:
            for p in self.menu:
                if product_name.lower() in p.get('name', '').lower():
                    return {
                        'type': 'product_highlight',
                        'product': p
                    }

        return None

    def _handle_informative_question(
        self,
        context: StateContext,
        intent: Intent,
        entities: Dict,
        user_input: str
    ) -> ProcessResult:
        """
        Maneja preguntas informativas (ASK_SIZE, ASK_PRICE, ASK_INGREDIENTS, ASK_SPICY)
        usando Cerebras/LLM para generar respuestas inteligentes basadas en el menú.

        Esta función permite que el LLM responda preguntas complejas que requieren
        comprensión semántica del contexto y los productos.
        """
        logger.info(f"[FSM] Procesando pregunta informativa: {intent.value} | Input: '{user_input}'")

        # 1. Extraer producto mencionado de las entidades o detectarlo
        mentioned_product = entities.get('product') or entities.get('mentioned_product')
        mentioned_category = entities.get('category') or entities.get('menu_category')

        if not mentioned_product:
            mentioned_product = self.decision_tree._detect_mentioned_product(user_input, context)

        # 2. Buscar información del producto/categoría
        product_info = None
        category_products = []

        if mentioned_product:
            product_info = self.decision_tree.find_product_by_name(mentioned_product)

        if mentioned_category:
            # Buscar productos de la categoría
            category_products = [
                p for p in self.menu
                if p.get('category', {}).get('name', '').lower() == mentioned_category.lower()
            ]

        # 3. Usar CascadeProvider (Cerebras → Gemini) para generar respuesta inteligente
        if self.cascade_nlu_provider:
            try:
                # Construir contexto para el LLM
                menu_context = self._build_menu_context_for_question(
                    intent,
                    product_info,
                    category_products,
                    mentioned_category
                )

                # Prompt del sistema para preguntas informativas
                system_prompt = f"""Eres un asistente de ventas amigable para un restaurante de comida rápida.
Tu objetivo es responder preguntas sobre el menú de forma clara, concisa y útil.
Responde en español de manera natural y conversacional.
Si no tienes información específica, ofrece alternativas o sugiere preguntar por otro producto.
IMPORTANTE: Sé breve (1-3 oraciones máximo) y directo.

Información del menú disponible:
{menu_context}"""

                user_message = f"Pregunta del cliente: {user_input}"

                # Llamar al CascadeProvider (Cerebras → Gemini)
                response = self.cascade_nlu_provider.generate(
                    prompt=system_prompt,
                    messages=[{"role": "user", "content": user_message}],
                    max_tokens=150,
                    temperature=0.7
                )

                response_text = response.get('response_text', '')
                if response_text:
                    provider_used = response.get('fallback_chain', ['unknown'])[-1]
                    logger.info(f"[FSM] Respuesta generada por {provider_used}: '{response_text[:100]}...'")
                    return ProcessResult(
                        response_text=response_text.strip(),
                        intent=intent.value,
                        new_state=context.state,
                        visual_data=self._build_visual_data_for_question(product_info, category_products)
                    )

            except Exception as e:
                logger.warning(f"[FSM] Error usando LLM para pregunta: {e}")

        # 4. Fallback: Respuesta basada en datos del menú sin LLM
        response_text = self._generate_fallback_question_response(
            intent,
            product_info,
            category_products,
            mentioned_product,
            mentioned_category,
            user_input
        )

        return ProcessResult(
            response_text=response_text,
            intent=intent.value,
            new_state=context.state,
            visual_data=self._build_visual_data_for_question(product_info, category_products)
        )

    def _build_menu_context_for_question(
        self,
        intent: Intent,
        product_info: Optional[Dict],
        category_products: List[Dict],
        category_name: Optional[str]
    ) -> str:
        """Construye contexto del menú para el LLM"""
        context_parts = []

        if product_info:
            context_parts.append(f"Producto específico: {product_info.get('name')}")
            context_parts.append(f"  - Precio: ${product_info.get('price', 'N/A')}")
            context_parts.append(f"  - Descripción: {product_info.get('description', 'Sin descripción')}")

            # Tamaños/porciones si existen
            sizes = product_info.get('sizes', [])
            if sizes:
                sizes_str = ", ".join([f"{s.get('name', 'N/A')} (${s.get('price', 'N/A')})" for s in sizes])
                context_parts.append(f"  - Tamaños disponibles: {sizes_str}")

            # Porciones (como "orden de 3 tacos")
            portions = product_info.get('portions')
            if portions:
                context_parts.append(f"  - Porción: {portions}")

            # Ingredientes
            ingredients = product_info.get('ingredients', [])
            if ingredients:
                context_parts.append(f"  - Ingredientes: {', '.join(ingredients)}")

            # Picante
            spicy_level = product_info.get('spicy_level') or product_info.get('spicy')
            if spicy_level:
                context_parts.append(f"  - Nivel de picante: {spicy_level}")

        if category_products and category_name:
            context_parts.append(f"\nProductos en categoría '{category_name}':")
            for p in category_products[:5]:  # Limitar a 5 productos
                price = p.get('price', 'N/A')
                portions = p.get('portions', '')
                portions_str = f" ({portions})" if portions else ""
                context_parts.append(f"  - {p.get('name')}: ${price}{portions_str}")

        if not context_parts:
            context_parts.append("No se encontró información específica del producto.")
            # Agregar algunas opciones del menú
            context_parts.append("\nAlgunas opciones populares:")
            for p in self.menu[:3]:
                context_parts.append(f"  - {p.get('name')}: ${p.get('price', 'N/A')}")

        return "\n".join(context_parts)

    def _generate_fallback_question_response(
        self,
        intent: Intent,
        product_info: Optional[Dict],
        category_products: List[Dict],
        mentioned_product: Optional[str],
        mentioned_category: Optional[str],
        user_input: str
    ) -> str:
        """Genera respuesta de fallback cuando no hay LLM disponible"""

        if product_info:
            name = product_info.get('name', 'el producto')

            if intent == Intent.ASK_PRICE:
                price = product_info.get('price', 'consultar')
                return f"{name} tiene un precio de ${price}. ¿Te gustaría ordenarlo?"

            elif intent == Intent.ASK_SIZE:
                sizes = product_info.get('sizes', [])
                portions = product_info.get('portions')
                if sizes:
                    sizes_str = ", ".join([f"{s.get('name')} (${s.get('price')})" for s in sizes])
                    return f"{name} viene en: {sizes_str}. ¿Cuál prefieres?"
                elif portions:
                    return f"{name} viene en {portions}. ¿Te gustaría ordenarlo?"
                else:
                    return f"{name} viene en tamaño único a ${product_info.get('price', 'N/A')}."

            elif intent == Intent.ASK_INGREDIENTS:
                ingredients = product_info.get('ingredients', [])
                if ingredients:
                    return f"{name} lleva: {', '.join(ingredients)}."
                else:
                    return f"No tengo los ingredientes exactos de {name}. ¿Te gustaría ordenarlo?"

            elif intent == Intent.ASK_SPICY:
                spicy = product_info.get('spicy_level') or product_info.get('spicy', 'no especificado')
                return f"El nivel de picante de {name} es: {spicy}."

        elif category_products and mentioned_category:
            if intent == Intent.ASK_SIZE:
                # Responder sobre tamaños de productos en la categoría
                products_with_sizes = [p for p in category_products if p.get('portions')]
                if products_with_sizes:
                    examples = products_with_sizes[:2]
                    examples_str = ", ".join([f"{p.get('name')} ({p.get('portions')})" for p in examples])
                    return f"En {mentioned_category} tenemos: {examples_str}. ¿Cuál te interesa?"

            # Respuesta genérica sobre la categoría
            products_str = ", ".join([p.get('name') for p in category_products[:3]])
            return f"En {mentioned_category} tenemos: {products_str}. ¿Cuál te gustaría saber más?"

        # Sin información específica
        return "¿De cuál producto te gustaría saber? Puedo darte información sobre precios, tamaños o ingredientes."

    def _build_visual_data_for_question(
        self,
        product_info: Optional[Dict],
        category_products: List[Dict]
    ) -> Optional[Dict]:
        """Construye visual_data para mostrar en el frontend"""
        if product_info:
            return {
                'type': 'product_highlight',
                'product': product_info
            }
        elif category_products:
            return {
                'type': 'product_list',
                'products': category_products[:4]
            }
        return None

    def _handle_view_product_details(
        self,
        context: StateContext,
        entities: Dict,
        user_input: str
    ) -> ProcessResult:
        """
        Maneja intent de ver detalles de producto específico.
        Genera visual_data con type='product_detail' para que el frontend abra el modal.
        """
        # Buscar producto mencionado
        mentioned = entities.get('product') or entities.get('mentioned_product')
        if not mentioned:
            mentioned = self.decision_tree._detect_mentioned_product(user_input, context)

        if mentioned:
            product = self.decision_tree.find_product_by_name(mentioned)
            if product:
                # Generar respuesta con detalles del producto
                response = self.response_generator.generate_product_details(product, context)

                logger.info(f"[FSM] VIEW_PRODUCT_DETAILS: {product.get('name')} - visual_data incluido")

                return ProcessResult(
                    response_text=response.text,
                    intent='view_product_details',
                    new_state=context.state,
                    visual_data=response.visual_data  # Incluye type='product_detail' para abrir modal
                )

        # Si no encuentra producto específico
        return ProcessResult(
            response_text="¿De cuál platillo te gustaría ver los detalles?",
            intent='view_product_details',
            new_state=context.state
        )

    def _generate_confirmation(self, context: StateContext, user_input: str = "") -> ProcessResult:
        """Genera confirmación de pedido"""

        conversation_history = self._get_conversation_history(context)
        response = self.response_generator.generate_confirmation(
            context,
            user_input=user_input,
            conversation_history=conversation_history
        )

        return ProcessResult(
            response_text=response.text,
            intent='order_confirmation',
            new_state=context.state
        )

    def _handle_by_intent(
        self,
        context: StateContext,
        intent: Intent,
        entities: Dict,
        user_input: str
    ) -> ProcessResult:
        """Maneja intención sin considerar estado"""

        if intent == Intent.VIEW_CATEGORY:
            return self._enter_micro_funnel(context, entities)

        if intent == Intent.GET_RECOMMENDATION:
            if context.is_category_active():
                return self._recommend_in_category(context, entities, user_input)
            else:
                return self._start_recommendation_funnel(context)

        if intent == Intent.ADD_TO_ORDER:
            return self._handle_add_to_order(context, entities, user_input)

        if intent == Intent.REMOVE_FROM_ORDER:
            return self._handle_remove_from_order(context, entities, user_input)

        # Fallback
        return ProcessResult(
            response_text="¿En qué te puedo ayudar?",
            intent=intent.value,
            new_state=context.state
        )

    def _get_popular_product(self) -> Optional[Dict]:
        """Obtiene producto popular del menú"""
        for p in self.menu:
            if 'popular' in p.get('tags', []):
                return p
        return self.menu[0] if self.menu else None

    def _get_available_categories(self) -> List[str]:
        """Obtiene categorías disponibles"""
        categories = set()
        for p in self.menu:
            cat = p.get('category', {}).get('name')
            if cat:
                categories.add(cat)
        return list(categories)

    def _detect_category_in_text(self, text: str) -> Optional[str]:
        """
        Detecta si el usuario mencionó una categoría del menú.
        Retorna el nombre de la categoría si lo encuentra, None si no.
        """
        text_lower = text.lower()

        # Mapeo de palabras clave a categorías
        category_keywords = {
            'hamburguesa': 'Hamburguesas',
            'hamburguesas': 'Hamburguesas',
            'burger': 'Hamburguesas',
            'taco': 'Tacos',
            'tacos': 'Tacos',
            'taquito': 'Tacos',
            'bebida': 'Bebidas',
            'bebidas': 'Bebidas',
            'refresco': 'Bebidas',
            'refrescos': 'Bebidas',
            'tomar': 'Bebidas',
            'postre': 'Postres',
            'postres': 'Postres',
            'dulce': 'Postres',
            'entrada': 'Entradas',
            'entradas': 'Entradas',
            'botana': 'Entradas',
            'sopa': 'Sopas',
            'sopas': 'Sopas',
            'caldo': 'Sopas',
            'ensalada': 'Ensaladas',
            'ensaladas': 'Ensaladas',
            'plato fuerte': 'Platos Fuertes',
            'platos fuertes': 'Platos Fuertes',
            'complemento': 'Complementos',
            'complementos': 'Complementos',
            'extra': 'Complementos',
            'alcohol': 'Alcohol',
            'cerveza': 'Alcohol',
            'cervezas': 'Alcohol',
            'promocion': 'Promociones',
            'promociones': 'Promociones',
            'combo': 'Promociones',
        }

        # Buscar coincidencia
        for keyword, category in category_keywords.items():
            if keyword in text_lower:
                # Verificar que la categoría existe en el menú
                available = self._get_available_categories()
                if category in available:
                    return category

        return None

    def _get_products_by_category_type(self, category_keywords: List[str], product_keywords: List[str]) -> List[Dict]:
        """
        Método genérico para obtener productos del menú por tipo de categoría.

        Args:
            category_keywords: Palabras clave para buscar en el nombre de la categoría
            product_keywords: Palabras clave para buscar en el nombre del producto o tags

        Returns:
            Lista de productos que coinciden con los criterios
        """
        products = []
        for p in self.menu:
            name_lower = p.get('name', '').lower()
            category = p.get('category', {}).get('name', '').lower()
            tags = [t.lower() for t in p.get('tags', [])]

            # Buscar por categoría, nombre o tags
            if any(kw in category for kw in category_keywords):
                products.append(p)
            elif any(kw in name_lower for kw in product_keywords):
                products.append(p)
            elif any(kw in tags for kw in product_keywords):
                products.append(p)

        return products

    def _get_complementos_from_menu(self) -> List[Dict]:
        """Obtiene complementos/extras del menú real"""
        return self._get_products_by_category_type(
            category_keywords=['complemento', 'extra', 'side', 'acompañamiento'],
            product_keywords=['papas', 'guacamole', 'queso', 'extra', 'complemento', 'side', 'acompañamiento']
        )

    def _get_bebidas_from_menu(self) -> List[Dict]:
        """Obtiene bebidas del menú real"""
        return self._get_products_by_category_type(
            category_keywords=['bebida', 'drink', 'beverage', 'refresco'],
            product_keywords=['refresco', 'agua', 'limonada', 'jugo', 'coca', 'sprite', 'cerveza', 'michelada', 'horchata']
        )

    def _get_postres_from_menu(self) -> List[Dict]:
        """Obtiene postres del menú real"""
        return self._get_products_by_category_type(
            category_keywords=['postre', 'dessert', 'dulce'],
            product_keywords=['flan', 'pastel', 'helado', 'churro', 'postre', 'dulce', 'pay', 'cheesecake', 'brownie']
        )

    def _get_conversation_history(self, context: StateContext) -> List[Dict]:
        """
        Obtiene el historial de conversación formateado para el LLM.
        Retorna los últimos 6 mensajes.
        """
        history = []
        for entry in context.conversation_history[-6:]:
            history.append({
                "role": entry.get("role", "user"),
                "content": entry.get("message", "")
            })
        return history

    def get_session_metrics(self, session_id: str) -> Dict:
        """Obtiene métricas completas de una sesión"""
        metrics = {}

        if session_id in self.sessions:
            context = self.sessions[session_id]
            metrics['fsm'] = context.metrics
            metrics['state'] = context.state.value
            metrics['order_total'] = context.order_total
            metrics['items_count'] = len(context.order_items)

        if session_id in self.session_memories:
            memory = self.session_memories[session_id]
            metrics['memory'] = memory.to_dict()
            metrics['customer_profile'] = memory.get_customer_profile()

        return metrics

    def get_conversation_context(self, session_id: str) -> Optional[str]:
        """Obtiene el contexto de conversación para LLM"""
        if session_id in self.session_memories:
            return self.session_memories[session_id].get_context_for_llm()
        return None

    def clear_session(self, session_id: str):
        """Limpia una sesión"""
        # Emitir evento de fin de conversación con métricas
        if session_id in self.sessions:
            context = self.sessions[session_id]
            duration = time.time() - self.session_start_times.get(session_id, time.time())
            message_count = len(context.conversation_history)

            # Emit event
            self._emit_event(EventType.CONVERSATION_ENDED, {
                "duration_seconds": duration,
                "message_count": message_count,
                "items_ordered": len(context.order_items),
                "order_total": context.order_total,
                "final_state": context.state.value
            }, session_id)

            # Track metrics
            if METRICS_AVAILABLE:
                track_conversation_end(duration, message_count)

            del self.sessions[session_id]

        if session_id in self.session_memories:
            del self.session_memories[session_id]

        if session_id in self.session_start_times:
            del self.session_start_times[session_id]

        logger.info(f"[FSM] Sesión eliminada: {session_id}")

    # ============================================================
    # MÉTODOS DE INTEGRACIÓN v2.2
    # ============================================================

    def _emit_event(self, event_type: EventType, data: Dict, session_id: str = ""):
        """Emite un evento al Event Bus si está disponible"""
        if self.event_bus and EVENT_BUS_AVAILABLE:
            try:
                # Crear evento de forma síncrona
                event = Event(
                    type=event_type,
                    data=data,
                    session_id=session_id
                )
                # Intentar emitir de forma asíncrona si es posible
                try:
                    loop = asyncio.get_running_loop()
                    # Ya estamos en un loop activo, crear task
                    asyncio.create_task(self.event_bus.publish(event))
                except RuntimeError:
                    # No hay event loop activo, intentar crear uno
                    try:
                        loop = asyncio.get_event_loop()
                        if not loop.is_running():
                            loop.run_until_complete(self.event_bus.publish(event))
                        else:
                            # Loop existe pero no podemos usarlo directamente
                            asyncio.create_task(self.event_bus.publish(event))
                    except RuntimeError:
                        # Sin loop, ejecutar de forma síncrona (skip event)
                        logger.debug(f"[FSM] No se pudo emitir evento (sin event loop): {event_type.value}")
            except Exception as e:
                logger.debug(f"[FSM] Error emitiendo evento: {e}")

    def _record_feedback(
        self,
        user_input: str,
        intent: str,
        confidence: float,
        method: str,
        success: bool,
        session_id: str = "",
        expected_intent: str = None
    ):
        """Registra feedback para aprendizaje continuo"""
        if self.feedback_loop and FEEDBACK_LOOP_AVAILABLE:
            try:
                if success:
                    record_successful_interaction(
                        user_input=user_input,
                        intent=intent,
                        confidence=confidence,
                        method=method,
                        session_id=session_id
                    )
                else:
                    record_failed_interaction(
                        user_input=user_input,
                        detected_intent=intent,
                        expected_intent=expected_intent or "unknown",
                        confidence=confidence,
                        method=method,
                        session_id=session_id
                    )
            except Exception as e:
                logger.debug(f"[FSM] Error registrando feedback: {e}")

    def _validate_product(self, query: str, category_products: List[Dict] = None) -> Tuple[bool, Optional[Dict], str]:
        """
        Valida si un producto existe usando el Product Validator.

        Returns:
            Tuple de (existe, producto, mensaje)
        """
        if not self.product_validator or not PRODUCT_VALIDATOR_AVAILABLE:
            # Sin validador, usar comportamiento original
            return True, None, ""

        try:
            result = self.product_validator.validate(query, category_products)

            if result.status == ProductStatus.FOUND:
                # Producto encontrado con certeza
                if METRICS_AVAILABLE:
                    track_product_search("found")
                return True, result.product, ""

            elif result.status == ProductStatus.NEEDS_CONFIRMATION:
                # Necesita confirmación
                if METRICS_AVAILABLE:
                    track_product_search("suggested")
                return False, result.product, result.message

            else:
                # No encontrado
                if METRICS_AVAILABLE:
                    track_product_search("not_found")

                # Emit event
                self._emit_event(EventType.PRODUCT_NOT_FOUND, {
                    "query": query,
                    "suggestions": [s.get("name", "") for s in result.suggestions[:3]]
                })

                return False, None, result.message

        except Exception as e:
            logger.warning(f"[FSM] Error en validación de producto: {e}")
            return True, None, ""

    def _search_product_semantic(self, query: str, top_k: int = 3) -> List[Dict]:
        """
        Busca productos por significado usando Semantic Search.

        Returns:
            Lista de productos encontrados
        """
        if not self.semantic_search or not SEMANTIC_SEARCH_AVAILABLE:
            return []

        try:
            results = self.semantic_search.search(query, top_k=top_k)
            return [r.product for r in results]
        except Exception as e:
            logger.warning(f"[FSM] Error en búsqueda semántica: {e}")
            return []

    def get_system_status(self) -> Dict:
        """Retorna estado de todos los componentes del sistema"""
        status = {
            "version": "3.0.0",
            "components": {
                "hybrid_nlu": self.hybrid_nlu is not None,
                "cascade_nlu_provider": self.cascade_nlu_provider is not None,
                "enhanced_classifier": self.enhanced_classifier is not None,
                "semantic_search": self.semantic_search is not None,
                "product_validator": self.product_validator is not None,
                "event_bus": self.event_bus is not None,
                "feedback_loop": self.feedback_loop is not None,
                "metrics": self.metrics is not None,
                "multi_order_parser": self.multi_order_parser is not None,
            },
            "active_sessions": len(self.sessions),
            "menu_items": len(self.menu),
        }

        # Agregar stats del HybridNLU si está disponible
        if self.hybrid_nlu:
            status["hybrid_nlu_stats"] = self.hybrid_nlu.get_stats()

        return status

    def get_hybrid_nlu_patterns(self) -> str:
        """Exporta los patrones aprendidos por el HybridNLU para revisión"""
        if self.hybrid_nlu:
            return self.hybrid_nlu.export_patterns_for_review()
        return "HybridNLU no disponible"

    def force_offline_mode(self):
        """Fuerza modo offline en el HybridNLU (para testing)"""
        if self.hybrid_nlu:
            self.hybrid_nlu.force_offline_mode()
            logger.info("[FSM] Modo offline forzado")

    def force_online_mode(self):
        """Fuerza modo online en el HybridNLU (para testing)"""
        if self.hybrid_nlu:
            self.hybrid_nlu.force_online_mode()
            logger.info("[FSM] Modo online forzado")
