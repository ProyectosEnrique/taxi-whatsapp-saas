# ============================================================
# LLM FALLBACK HANDLER - FSM
# ============================================================
# Maneja casos que el árbol de decisión no puede clasificar
# Usa LLM de forma inteligente y controlada
# ============================================================

import logging
import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class FallbackStrategy(Enum):
    """Estrategias de fallback disponibles"""
    CLARIFY = "clarify"          # Pedir aclaración al usuario
    INFER_INTENT = "infer"       # Usar LLM para inferir intención
    CONTEXT_GUESS = "context"    # Adivinar basado en contexto
    DEFAULT_RESPONSE = "default" # Respuesta genérica segura


@dataclass
class FallbackResult:
    """Resultado del fallback"""
    strategy_used: FallbackStrategy
    inferred_intent: Optional[str]
    response_text: str
    confidence: float
    should_transition: bool = False
    suggested_state: Optional[str] = None
    entities: Dict = None

    def __post_init__(self):
        if self.entities is None:
            self.entities = {}


class LLMFallbackHandler:
    """
    Manejador de fallback inteligente usando LLM.

    Estrategia jerárquica:
    1. Intentar inferir del contexto sin LLM
    2. Si el texto es muy corto/ambiguo, pedir aclaración
    3. Si hay suficiente contexto, usar LLM para clasificar
    4. Último recurso: respuesta segura por defecto
    """

    def __init__(self, llm_service=None, config: Dict = None):
        """
        Inicializa el handler de fallback.

        Args:
            llm_service: Servicio LLM (se carga lazy si no se proporciona)
            config: Configuración opcional
        """
        self._llm_service = llm_service
        self.config = config or {}

        # Configuración de fallback
        self.min_text_length_for_llm = self.config.get('min_text_length_for_llm', 5)
        self.max_clarification_attempts = self.config.get('max_clarification_attempts', 2)
        self.llm_confidence_threshold = self.config.get('llm_confidence_threshold', 0.7)

        # Patrones para inferencia contextual rápida
        self._build_contextual_patterns()

        logger.info("[FALLBACK] Handler inicializado")

    @property
    def llm_service(self):
        """Carga lazy del servicio LLM"""
        if self._llm_service is None:
            try:
                from src.nlp.llm_service import get_llm_service
                self._llm_service = get_llm_service()
            except Exception as e:
                logger.warning(f"[FALLBACK] No se pudo cargar LLM service: {e}")
        return self._llm_service

    def _build_contextual_patterns(self):
        """Construye patrones para inferencia contextual"""

        # Patrones de afirmación implícita
        self.implicit_yes_patterns = [
            r'^(ese|eso|esa)$',
            r'^(el|la|lo) (primero|segundo|último)$',
            r'^(bueno|pues|entonces)$',
            r'^(está|esta) bien$',
            r'^sale$',
            r'^va$',
            r'^listo$'
        ]

        # Patrones de negación implícita
        self.implicit_no_patterns = [
            r'^(mejor no|luego|después|ahorita no)$',
            r'^(déjame pensar|lo pienso)$',
            r'^(mmm|hmm)$'
        ]

        # Patrones de pregunta implícita
        self.implicit_question_patterns = [
            r'\?$',
            r'^(y |a ver |oye )',
            r'^(cómo|cuándo|dónde|por qué)'
        ]

        # Patrones que indican continuar en el mismo contexto
        self.continuation_patterns = [
            r'^(también|además|y también|otra cosa)$',
            r'^(qué más|algo más)$',
            r'^(otro|otra|otros|otras)$'
        ]

        # Respuestas cortas que probablemente son afirmación
        self.short_affirmative = {'si', 'sí', 'ok', 'va', 'dale', 'sale', 'ese', 'eso', 'esa'}

    def handle_fallback(
        self,
        user_input: str,
        context: 'StateContext',
        menu: List[Dict] = None,
        detected_intent: str = None
    ) -> FallbackResult:
        """
        Maneja un caso que no pudo ser clasificado.

        Args:
            user_input: Texto del usuario
            context: Contexto actual de la conversación
            menu: Lista de productos del menú
            detected_intent: Intención detectada previamente (para cascade con GPT-4o)

        Returns:
            FallbackResult con la estrategia usada y respuesta
        """
        text_lower = user_input.lower().strip()

        logger.info(f"[FALLBACK] Procesando: '{text_lower}' | Estado: {context.state.value} | Intent: {detected_intent}")

        # Si ya tenemos un intent premium detectado, ir directo al LLM
        if detected_intent and detected_intent in {
            'handle_objection', 'negotiate', 'complaint',
            'complex_recommendation', 'special_request'
        }:
            logger.info(f"[FALLBACK] Intent premium detectado, usando LLM directamente")
            if self.llm_service:
                llm_result = self._use_llm_for_classification(
                    text_lower, context, menu, detected_intent
                )
                if llm_result:
                    return llm_result

        # Estrategia 1: Inferencia contextual rápida (sin LLM)
        contextual_result = self._try_contextual_inference(text_lower, context)
        if contextual_result:
            return contextual_result

        # Estrategia 2: Texto muy corto → pedir aclaración
        if len(text_lower) < self.min_text_length_for_llm:
            return self._request_clarification(text_lower, context)

        # Estrategia 3: Usar LLM para clasificar
        if self.llm_service:
            llm_result = self._use_llm_for_classification(
                text_lower, context, menu, detected_intent
            )
            if llm_result and llm_result.confidence >= self.llm_confidence_threshold:
                return llm_result

        # Estrategia 4: Respuesta por defecto basada en estado
        return self._generate_default_response(context)

    def _try_contextual_inference(
        self,
        text: str,
        context: 'StateContext'
    ) -> Optional[FallbackResult]:
        """
        Intenta inferir la intención basándose en el contexto.
        No usa LLM, solo patrones y estado actual.
        """

        # Si estamos esperando respuesta sí/no (después de upsell/crosssell)
        if context.state.value in ['upsell', 'cross_sell', 'confirmacion']:
            # Verificar afirmación implícita
            if text in self.short_affirmative:
                return FallbackResult(
                    strategy_used=FallbackStrategy.CONTEXT_GUESS,
                    inferred_intent='accept_suggestion',
                    response_text="",  # Se generará en el FSM
                    confidence=0.85,
                    should_transition=True
                )

            # Verificar patrones de afirmación implícita
            for pattern in self.implicit_yes_patterns:
                if re.match(pattern, text, re.IGNORECASE):
                    return FallbackResult(
                        strategy_used=FallbackStrategy.CONTEXT_GUESS,
                        inferred_intent='accept_suggestion',
                        response_text="",
                        confidence=0.75,
                        should_transition=True
                    )

            # Verificar patrones de negación implícita
            for pattern in self.implicit_no_patterns:
                if re.match(pattern, text, re.IGNORECASE):
                    return FallbackResult(
                        strategy_used=FallbackStrategy.CONTEXT_GUESS,
                        inferred_intent='reject_suggestion',
                        response_text="",
                        confidence=0.75,
                        should_transition=True
                    )

        # Si estamos en micro-embudo y el texto parece continuación
        if context.state.value == 'micro_embudo':
            for pattern in self.continuation_patterns:
                if re.match(pattern, text, re.IGNORECASE):
                    return FallbackResult(
                        strategy_used=FallbackStrategy.CONTEXT_GUESS,
                        inferred_intent='get_recommendation',
                        response_text="",
                        confidence=0.70,
                        should_transition=False
                    )

        # Si mencionó un producto del contexto activo
        if context.is_category_active() and context.active_category_products:
            for product in context.active_category_products:
                product_name = product.get('name', '').lower()
                # Buscar coincidencia parcial del nombre
                keywords = [w for w in product_name.split() if len(w) > 3]
                for keyword in keywords:
                    if keyword in text:
                        return FallbackResult(
                            strategy_used=FallbackStrategy.CONTEXT_GUESS,
                            inferred_intent='add_to_order',
                            response_text="",
                            confidence=0.80,
                            should_transition=True,
                            entities={'mentioned_product': product['name']}
                        )

        return None

    def _request_clarification(
        self,
        text: str,
        context: 'StateContext'
    ) -> FallbackResult:
        """
        Genera una solicitud de aclaración basada en el contexto.

        v2.5: Mejorado para ser más natural y ofrecer opciones concretas
        en lugar de solo pedir que repitan.
        """

        # Verificar límite de intentos de clarificación
        # Pero NO bloquear, solo cambiar la estrategia
        is_multiple_attempts = context.clarification_attempts >= self.max_clarification_attempts

        # Generar pregunta de clarificación basada en estado con opciones
        if is_multiple_attempts:
            # Después de varios intentos, ser más directo con opciones
            clarification_templates = {
                'inicio': "Dime: ¿hamburguesa, taco, bebida, o recomendación?",
                'bienvenida': "¿Te muestro hamburguesas, tacos, o bebidas? ¿O prefieres que te recomiende algo?",
                'exploracion': "¿Cuál categoría: hamburguesas, tacos, ensaladas, bebidas o postres?",
                'micro_embudo': f"¿Cuál de {context.active_category or 'estos productos'} te preparo? Dime el nombre.",
                'upsell': "Solo dime 'sí' para agregarlo o 'no' para continuar.",
                'cross_sell': "¿'Sí' a la bebida o 'no' para confirmar tu pedido?",
                'confirmacion': "¿'Confirmar' el pedido o 'agregar' algo más?"
            }
        else:
            # Primera clarificación, más natural
            clarification_templates = {
                'inicio': "¿Qué te gustaría? Tenemos hamburguesas, tacos, bebidas y más.",
                'bienvenida': "¿Qué se te antoja? Te puedo recomendar algo rico.",
                'exploracion': "¿Qué te llama más: hamburguesas, tacos, o algo fresco para tomar?",
                'micro_embudo': f"¿Te preparo algo de {context.active_category or 'aquí'}? Te recomiendo el más popular.",
                'upsell': "¿Le entramos? Es muy buena opción. Dime sí o no.",
                'cross_sell': "¿Agregamos algo de tomar? Dime sí o no.",
                'confirmacion': "¿Todo bien con el pedido o agregamos algo?"
            }

        response = clarification_templates.get(
            context.state.value,
            "¿Qué te gustaría? Puedo mostrarte el menú, recomendarte algo, o tomar tu pedido."
        )

        return FallbackResult(
            strategy_used=FallbackStrategy.CLARIFY,
            inferred_intent='need_clarification',
            response_text=response,
            confidence=1.0,
            should_transition=False
        )

    def _use_llm_for_classification(
        self,
        text: str,
        context: 'StateContext',
        menu: List[Dict] = None,
        detected_intent: str = None
    ) -> Optional[FallbackResult]:
        """
        Usa el LLM para clasificar la intención del usuario.

        Args:
            text: Texto del usuario
            context: Contexto de la conversación
            menu: Menú disponible
            detected_intent: Intención detectada previamente (para cascade)
        """

        if not self.llm_service:
            return None

        try:
            # Construir contexto para el LLM
            classification_prompt = self._build_classification_prompt(text, context, menu)

            # Llamar al LLM con el intent detectado (CascadeProvider lo usará)
            result = self.llm_service.generate_response(
                user_message=text,
                intent=detected_intent or "classify_intent",
                context={
                    "current_state": context.state.value,
                    "active_category": context.active_category,
                    "order_items": [item.name for item in context.order_items],
                    "task": "Clasifica la intención del usuario y genera una respuesta apropiada."
                },
                conversation_history=context.conversation_history[-5:],
                temperature=0.3,  # Baja temperatura para clasificación
                max_tokens=200
            )

            response_text = result.get('response_text', '')

            # Parsear la respuesta del LLM
            parsed = self._parse_llm_classification(response_text, context)

            if parsed:
                return FallbackResult(
                    strategy_used=FallbackStrategy.INFER_INTENT,
                    inferred_intent=parsed.get('intent', 'unknown'),
                    response_text=parsed.get('response', response_text),
                    confidence=parsed.get('confidence', 0.6),
                    should_transition=parsed.get('should_transition', False),
                    entities=parsed.get('entities', {})
                )

            # Si no se pudo parsear, usar la respuesta directa
            return FallbackResult(
                strategy_used=FallbackStrategy.INFER_INTENT,
                inferred_intent='llm_generated',
                response_text=response_text,
                confidence=0.6,
                should_transition=False
            )

        except Exception as e:
            logger.error(f"[FALLBACK] Error usando LLM: {e}")
            return None

    def _build_classification_prompt(
        self,
        text: str,
        context: 'StateContext',
        menu: List[Dict] = None
    ) -> str:
        """Construye el prompt para clasificación con LLM"""

        # Obtener categorías del menú
        categories = set()
        if menu:
            for p in menu:
                cat = p.get('category', {}).get('name', '')
                if cat:
                    categories.add(cat)

        prompt = f"""
Eres un asistente de clasificación de intenciones para un restaurante.
El cliente dijo: "{text}"

Estado actual: {context.state.value}
Categoría activa: {context.active_category or 'Ninguna'}
Productos en pedido: {len(context.order_items)}
Categorías disponibles: {', '.join(categories) if categories else 'hamburguesas, tacos, bebidas, postres'}

Clasifica la intención del cliente en una de estas categorías:
- view_category: Quiere ver productos de una categoría
- get_recommendation: Pide una recomendación
- add_to_order: Quiere agregar algo al pedido
- accept_suggestion: Acepta una sugerencia
- reject_suggestion: Rechaza una sugerencia
- finish_order: Quiere terminar
- ask_question: Tiene una pregunta sobre el menú

Responde con la intención más probable y genera una respuesta corta y amigable (máximo 2 oraciones).
"""
        return prompt

    def _parse_llm_classification(
        self,
        llm_response: str,
        context: 'StateContext'
    ) -> Optional[Dict]:
        """
        Parsea la respuesta del LLM para extraer intención.
        """

        response_lower = llm_response.lower()

        # Detectar intención en la respuesta
        intent_keywords = {
            'view_category': ['categoría', 'mostrar', 'ver'],
            'get_recommendation': ['recomiend', 'suger'],
            'add_to_order': ['agregar', 'pedido', 'orden'],
            'accept_suggestion': ['acepta', 'sí', 'confirma'],
            'reject_suggestion': ['rechaza', 'no quiere'],
            'finish_order': ['terminar', 'finalizar', 'cerrar'],
            'ask_question': ['pregunta', 'duda', 'información']
        }

        detected_intent = 'unknown'
        for intent, keywords in intent_keywords.items():
            if any(kw in response_lower for kw in keywords):
                detected_intent = intent
                break

        return {
            'intent': detected_intent,
            'response': llm_response,
            'confidence': 0.7 if detected_intent != 'unknown' else 0.4,
            'should_transition': detected_intent in ['accept_suggestion', 'reject_suggestion', 'add_to_order'],
            'entities': {}
        }

    def _generate_default_response(self, context: 'StateContext') -> FallbackResult:
        """
        Genera una respuesta por defecto segura basada en el estado.

        v2.5: Mejorado para ofrecer opciones concretas y reconectar
        con el flujo de conversación cuando el agente no entiende.
        """

        # Respuestas mejoradas con opciones concretas para reconectar
        default_responses = {
            'inicio': "¿Qué te gustaría? Puedo ayudarte a: 1) Ver el menú, 2) Darte una recomendación, o 3) Tomar tu pedido directamente.",
            'bienvenida': "¿Qué se te antoja? Dime qué categoría te interesa: hamburguesas, tacos, bebidas... o pídeme una recomendación.",
            'exploracion': "¿Qué prefieres? Puedo mostrarte hamburguesas, tacos, ensaladas, bebidas o postres. ¿O te doy una recomendación?",
            'micro_embudo': f"¿Cuál te preparo de {context.active_category or 'esta categoría'}? Dime el nombre o te recomiendo el más pedido.",
            'producto_seleccionado': "¡Buena elección! ¿Lo agregamos al pedido? Solo dime 'sí' o 'va'.",
            'upsell': "¿Le entramos o lo dejamos así? Solo dime 'sí' o 'no' y seguimos.",
            'cross_sell': "¿Agregamos la bebida o pasamos a confirmar? Dime 'sí' o 'no'.",
            'confirmacion': f"Tu pedido: {context.get_order_summary()}. ¿Confirmamos o quieres agregar algo más?",
            'cierre': "¡Gracias! Tu pedido está en camino. ¿Necesitas algo más?"
        }

        # Generar respuesta basada en estado
        response = default_responses.get(context.state.value)

        # Si no hay respuesta específica, crear una contextual
        if not response:
            if context.order_items:
                # Si ya tiene items, ofrecer continuar o confirmar
                response = f"Llevas {len(context.order_items)} producto(s). ¿Agregamos algo más o confirmamos tu pedido?"
            elif context.active_category:
                # Si hay categoría activa, reconectar con ella
                response = f"¿Te preparo algo de {context.active_category}? Dime cuál o te recomiendo uno."
            else:
                # Respuesta general con opciones claras
                response = "¿En qué te ayudo? Puedo: mostrarte el menú, darte recomendaciones, o tomar tu pedido."

        logger.info(f"[FALLBACK] Respuesta por defecto para estado '{context.state.value}'")

        return FallbackResult(
            strategy_used=FallbackStrategy.DEFAULT_RESPONSE,
            inferred_intent='default',
            response_text=response,
            confidence=0.5,
            should_transition=False
        )


# Instancia global
_fallback_handler: Optional[LLMFallbackHandler] = None


def get_fallback_handler(config: Dict = None) -> LLMFallbackHandler:
    """Obtiene instancia global del handler (Singleton)"""
    global _fallback_handler
    if _fallback_handler is None:
        _fallback_handler = LLMFallbackHandler(config=config)
    return _fallback_handler
