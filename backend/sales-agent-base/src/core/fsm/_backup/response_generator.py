# ============================================================
# GENERADOR DE RESPUESTAS - FSM v3.0
# ============================================================
# Genera respuestas inteligentes usando LLM (CascadeProvider)
# Templates solo como fallback de emergencia
#
# MEJORAS v3.0:
# - Empathy Patterns (Feature #7)
# - Confirmación Implícita mejorada (Feature #8)
# - Small-talk handlers (Feature #6)
# - Cache de prompts optimizado
# ============================================================

import random
import logging
import time
import hashlib
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from collections import OrderedDict
from enum import Enum

from .conversation_states import ConversationState, StateContext

logger = logging.getLogger(__name__)


# ============================================================
# EMPATHY PATTERNS (Feature #7)
# Patrones empáticos para diferentes situaciones
# ============================================================

class EmpathyLevel(Enum):
    """Niveles de empatía según contexto"""
    NEUTRAL = "neutral"      # Transacción normal
    WARM = "warm"            # Saludos, despedidas
    SUPPORTIVE = "supportive"  # Quejas, problemas
    ENTHUSIASTIC = "enthusiastic"  # Ofertas, recomendaciones


# Frases empáticas por nivel
EMPATHY_PHRASES = {
    EmpathyLevel.NEUTRAL: [
        "Con gusto",
        "Permítame",
        "Por supuesto",
    ],
    EmpathyLevel.WARM: [
        "Es un placer atenderle",
        "Bienvenido, qué gusto tenerle aquí",
        "Gracias por visitarnos",
    ],
    EmpathyLevel.SUPPORTIVE: [
        "Entiendo perfectamente su situación",
        "Lamento mucho los inconvenientes",
        "Tiene toda la razón, vamos a solucionarlo",
        "Le ofrezco una sincera disculpa",
    ],
    EmpathyLevel.ENTHUSIASTIC: [
        "¡Excelente elección!",
        "Le va a encantar",
        "Es uno de nuestros favoritos",
        "Magnífica decisión",
    ],
}

# Mapeo de intents a nivel de empatía
INTENT_EMPATHY_MAP = {
    'greeting': EmpathyLevel.WARM,
    'goodbye': EmpathyLevel.WARM,
    'small_talk_how_are_you': EmpathyLevel.WARM,
    'small_talk_thanks': EmpathyLevel.WARM,
    'small_talk_compliment': EmpathyLevel.WARM,
    'complaint': EmpathyLevel.SUPPORTIVE,
    'handle_objection': EmpathyLevel.SUPPORTIVE,
    'accept_suggestion': EmpathyLevel.ENTHUSIASTIC,
    'add_to_order': EmpathyLevel.ENTHUSIASTIC,
    'get_recommendation': EmpathyLevel.ENTHUSIASTIC,
}


def get_empathy_phrase(intent: str = None, level: EmpathyLevel = None) -> str:
    """Obtiene una frase empática según intent o nivel"""
    if level is None:
        level = INTENT_EMPATHY_MAP.get(intent, EmpathyLevel.NEUTRAL)
    phrases = EMPATHY_PHRASES.get(level, EMPATHY_PHRASES[EmpathyLevel.NEUTRAL])
    return random.choice(phrases)


# ============================================================
# SMALL-TALK RESPONSES (Feature #6)
# Respuestas predefinidas para conversación casual
# ============================================================

SMALL_TALK_RESPONSES = {
    'small_talk_how_are_you': [
        "Muy bien, gracias por preguntar. Listo para atenderle. ¿Qué se le antoja hoy?",
        "Excelente, gracias. ¿En qué puedo ayudarle?",
        "De maravilla, siempre es un gusto atender. ¿Qué le preparo?",
    ],
    'small_talk_thanks': [
        "Es un placer. ¿Hay algo más en lo que pueda ayudarle?",
        "Gracias a usted por su preferencia. ¿Desea algo más?",
        "Con mucho gusto. ¿Le puedo ofrecer algo adicional?",
    ],
    'small_talk_name': [
        "Soy el asistente virtual del restaurante, estoy aquí para ayudarle a ordenar. ¿Qué le gustaría?",
        "Me llaman el asistente del restaurante. Es un placer atenderle. ¿Qué se le antoja?",
    ],
    'small_talk_joke': [
        "¿Sabe qué le dijo un taco a otro? ¡No te me deshagas! Ahora sí, ¿qué le preparo?",
        "Mi mejor chiste es nuestro precio, es tan bueno que da risa. ¿Qué le sirvo?",
    ],
    'small_talk_compliment': [
        "Muy amable de su parte. Es un gusto atenderle. ¿En qué le ayudo?",
        "Gracias, usted también es muy agradable. ¿Qué le preparo?",
    ],
    'small_talk_wait': [
        "Por supuesto, tómese su tiempo. Cuando esté listo me avisa.",
        "Claro, sin prisa. Aquí estaré cuando decida.",
    ],
    'small_talk_time': [
        "Estamos abiertos de 8am a 10pm. ¿Puedo mostrarle nuestro menú?",
        "El tiempo de preparación es de 10-15 minutos aproximadamente. ¿Le ayudo a ordenar?",
    ],
    'small_talk_weather': [
        "¡Hace un clima perfecto para disfrutar nuestra comida! ¿Qué se le antoja?",
        "El clima está agradable. ¿Le puedo recomendar algo refrescante?",
    ],
}


def get_small_talk_response(intent: str) -> Optional[str]:
    """Obtiene respuesta para small-talk si aplica"""
    if intent in SMALL_TALK_RESPONSES:
        return random.choice(SMALL_TALK_RESPONSES[intent])
    return None


# ============================================================
# IMPLICIT CONFIRMATION PATTERNS (Feature #8)
# Confirmación implícita natural en vez de preguntar todo
# ============================================================

IMPLICIT_CONFIRMATION_TEMPLATES = {
    'add_single': [
        "Perfecto, {quantity} {product} a su pedido. {next_action}",
        "Listo, le agrego {quantity} {product}. {next_action}",
        "Anotado, {quantity} {product}. {next_action}",
    ],
    'add_with_total': [
        "{quantity} {product}, van ${total} hasta ahora. {next_action}",
        "Agregado. {quantity} {product}, su cuenta va en ${total}. {next_action}",
    ],
    'modification': [
        "Entendido, {modification}. {next_action}",
        "Perfecto, lo preparo {modification}. {next_action}",
    ],
}

NEXT_ACTIONS = {
    'ask_more': ["¿Algo más?", "¿Desea agregar algo más?", "¿Qué más le sirvo?"],
    'suggest_drink': ["¿Le pongo una bebida?", "¿Algo de tomar?"],
    'suggest_side': ["¿Lo acompaño con papas?", "¿Le agrego guarnición?"],
    'confirm_complete': ["¿Cerramos el pedido?", "¿Listo para confirmar?"],
}


def generate_implicit_confirmation(
    product_name: str,
    quantity: int = 1,
    total: float = None,
    has_drink: bool = False,
    has_side: bool = False,
    modification: str = None
) -> str:
    """
    Genera confirmación implícita natural.

    Feature #8: En vez de preguntar "¿Confirmó hamburguesa?",
    dice "Perfecto, una hamburguesa. ¿Algo de tomar?"
    """
    # Elegir template
    if modification:
        template_key = 'modification'
        templates = IMPLICIT_CONFIRMATION_TEMPLATES[template_key]
        base = random.choice(templates).format(modification=modification, next_action='{next_action}')
    elif total and total > 50:
        template_key = 'add_with_total'
        templates = IMPLICIT_CONFIRMATION_TEMPLATES[template_key]
        base = random.choice(templates).format(
            quantity=quantity, product=product_name, total=f"{total:.0f}", next_action='{next_action}'
        )
    else:
        template_key = 'add_single'
        templates = IMPLICIT_CONFIRMATION_TEMPLATES[template_key]
        base = random.choice(templates).format(
            quantity=quantity, product=product_name, next_action='{next_action}'
        )

    # Elegir siguiente acción según contexto
    if not has_drink:
        next_action = random.choice(NEXT_ACTIONS['suggest_drink'])
    elif not has_side:
        next_action = random.choice(NEXT_ACTIONS['suggest_side'])
    else:
        next_action = random.choice(NEXT_ACTIONS['ask_more'])

    return base.format(next_action=next_action)


# ============================================================
# CACHE DE PROMPTS SIMPLES (sin TTL, solo LRU)
# ============================================================

class PromptCache:
    """
    Cache LRU simple para prompts construidos.
    Evita reconstruir el mismo prompt repetidamente.
    """

    def __init__(self, max_size: int = 50):
        self.max_size = max_size
        self._cache: OrderedDict = OrderedDict()
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Optional[str]:
        """Obtiene prompt del cache"""
        if key in self._cache:
            self._cache.move_to_end(key)
            self._hits += 1
            return self._cache[key]
        self._misses += 1
        return None

    def set(self, key: str, value: str):
        """Guarda prompt en cache"""
        if key in self._cache:
            self._cache.move_to_end(key)
        else:
            if len(self._cache) >= self.max_size:
                self._cache.popitem(last=False)
        self._cache[key] = value

    def stats(self) -> Dict:
        """Estadísticas del cache"""
        total = self._hits + self._misses
        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": f"{(self._hits/total*100):.1f}%" if total > 0 else "0%",
            "size": len(self._cache)
        }

# ============================================================
# PROMPTS DEL SISTEMA PARA LLM
# ============================================================

SYSTEM_PROMPT_BASE = """Eres un asesor gastronómico profesional de un restaurante de calidad. Tu estilo es HOSPITALARIO PREMIUM: cálido, atento y refinado.

REGLAS DE COMUNICACIÓN:
1. MÁXIMO 2-3 oraciones. Sé conciso pero elegante.
2. Usa lenguaje profesional: "Con gusto", "Permítame", "Es un placer", "Le recomiendo"
3. Trato de USTED siempre (nunca tutear)
4. Termina con UNA pregunta cortés para guiar la decisión
5. NO emojis, NO jerga informal

TONO HOSPITALARIO:
- Transmite calidez y atención personalizada
- Haz sentir al cliente que es especial
- Usa descripciones apetitosas pero breves
- Muestra conocimiento del menú con confianza

REGLA CRÍTICA - PRODUCTO NO ENCONTRADO:
Si el cliente pide algo que NO está en el menú:
- NO inventes ni adivines
- Infórmele con cortesía que no está disponible
- Sugiera UNA alternativa del menú con descripción breve
- Ejemplo: "Lamentablemente no contamos con esa opción, sin embargo nuestra Hamburguesa Mexicana con guacamole fresco es excelente. ¿Le gustaría probarla?"

EJEMPLOS DE RESPUESTAS:
- "Es un placer atenderle. Nuestros tacos al pastor son la especialidad de la casa. ¿Cuántos le preparo?"
- "Excelente elección. ¿Le gustaría complementar con nuestras papas gourmet por $25 adicionales?"
- "Su pedido suma $110. ¿Desea agregar alguna bebida?"
- "Con gusto le muestro nuestras hamburguesas: la Clásica a $85, la BBQ a $95 y la Mexicana a $90. ¿Cuál le interesa?"

Sé un profesional de la hospitalidad que hace sentir bienvenido a cada cliente."""

STATE_PROMPTS = {
    ConversationState.BIENVENIDA: "SALUDO: Bienvenida cálida, mencione 1 platillo destacado. Ej: 'Bienvenido, es un placer atenderle. Hoy nuestra carne asada está excepcional. ¿En qué puedo servirle?'",
    ConversationState.MICRO_EMBUDO: "MENÚ: Presente máximo 3 opciones con precio, recomiende UNA. Ej: 'Permítame mostrarle: Tacos al pastor $110, de birria $135. Le recomiendo el pastor, es nuestra especialidad. ¿Cuántos le preparo?'",
    ConversationState.UPSELL: "UPSELL: Sugiera UNA mejora con precio y beneficio. Ej: '¿Le gustaría agregar guacamole fresco por $20? Complementa perfectamente su platillo.'",
    ConversationState.CROSS_SELL: "CROSS-SELL: Ofrezca UNA bebida o complemento. Ej: '¿Puedo ofrecerle algo de beber? Nuestra agua de horchata casera está a $25.'",
    ConversationState.CONFIRMACION: "CONFIRMACIÓN: Resuma el total y confirme. Ej: 'Su pedido suma $110. ¿Desea agregar algo más o procedemos?'",
    ConversationState.CIERRE: "CIERRE: Confirme total, tiempo estimado y despedida cordial. Ej: 'Perfecto, son $110. En aproximadamente 10 minutos estará listo. Gracias por su preferencia.'"
}


@dataclass
class ResponseResult:
    """Resultado de generación de respuesta"""
    text: str
    visual_data: Optional[Dict] = None
    next_state: Optional[ConversationState] = None
    action: Optional[str] = None
    # Metadatos del LLM
    provider_used: Optional[str] = None
    tokens_used: int = 0
    latency_ms: float = 0.0
    fallback_to_template: bool = False


class ResponseGenerator:
    """
    Genera respuestas inteligentes usando LLM (CascadeProvider).
    Templates solo como fallback de emergencia.

    VERSION 2.0:
    - Cache de prompts para evitar reconstrucción
    - Pre-compilación de prompts estáticos

    Flujo:
    1. Construye prompt contextual (estado + menú + pedido)
    2. Llama al CascadeProvider (LoRA → Groq → OpenAI)
    3. Si falla, usa template como fallback
    4. Registra métricas de provider usado
    """

    def __init__(self, config: Dict = None):
        self.config = config or {}
        self._llm_provider = None
        self._llm_enabled = True
        self._prompt_cache = PromptCache(max_size=50)
        self._load_templates()
        self._init_llm_provider()

    def _init_llm_provider(self):
        """Inicializa el proveedor LLM (lazy loading)"""
        try:
            from ...nlp.model_provider import get_model_provider
            self._llm_provider = get_model_provider()
            logger.info(f"[RESPONSE_GEN] LLM Provider: {self._llm_provider.provider_name}")
        except Exception as e:
            logger.warning(f"[RESPONSE_GEN] No se pudo inicializar LLM: {e}")
            self._llm_enabled = False

    def _generate_cache_key(
        self,
        state: ConversationState,
        intent: str = None,
        extra_context: Dict = None,
        order_total: float = 0
    ) -> str:
        """
        Genera una clave única para el cache de prompts.
        Solo incluye elementos que afectan el prompt base.
        """
        # Elementos que definen el prompt (sin incluir user_input que siempre cambia)
        key_parts = [
            state.value if state else "none",
            intent or "none",
        ]

        # Hash de productos si existen (para cache de categoría)
        if extra_context:
            if 'products' in extra_context and extra_context['products']:
                product_ids = [p.get('id', p.get('name', ''))[:10] for p in extra_context['products'][:5]]
                key_parts.append(f"prods:{','.join(product_ids)}")
            if 'category' in extra_context:
                key_parts.append(f"cat:{extra_context['category']}")

        # Rango de total (no el valor exacto, para mayor hit rate)
        if order_total > 0:
            total_range = int(order_total // 50) * 50  # Agrupar en rangos de $50
            key_parts.append(f"total:{total_range}")

        return hashlib.md5("|".join(key_parts).encode()).hexdigest()[:16]

    def _build_context_prompt(
        self,
        state: ConversationState,
        context: StateContext,
        user_input: str = "",
        intent: str = None,
        extra_context: Dict = None
    ) -> str:
        """
        Construye el prompt contextual para el LLM.
        USA CACHE para prompts con el mismo estado/categoría.

        Incluye:
        - Prompt base del sistema
        - Prompt específico del estado
        - Información del menú relevante
        - Pedido actual
        - Historial de conversación
        """
        # Generar cache key para el prompt base
        order_total = context.order_total if context else 0
        cache_key = self._generate_cache_key(state, intent, extra_context, order_total)

        # Verificar cache (para prompt base sin el input del usuario)
        cached_base = self._prompt_cache.get(cache_key)

        if cached_base:
            # Cache hit: solo agregar el pedido actual específico
            logger.debug(f"[RESPONSE_GEN] Prompt cache HIT: {cache_key}")
            prompt = cached_base

            # Agregar pedido actual (dinámico, no cacheado)
            if context and context.order_items:
                order_summary = context.get_order_summary()
                prompt += f"\nPedido actual: {order_summary}"
                prompt += f"\nTotal actual: ${context.order_total:.2f}"

            return prompt

        # Cache miss: construir prompt completo
        logger.debug(f"[RESPONSE_GEN] Prompt cache MISS: {cache_key}")

        parts = [SYSTEM_PROMPT_BASE]

        # Prompt del estado actual
        if state in STATE_PROMPTS:
            parts.append(STATE_PROMPTS[state])

        # Contexto del menú
        if extra_context:
            if 'products' in extra_context:
                products = extra_context['products']
                if products:
                    product_list = ", ".join([
                        f"{p.get('name', 'Producto')} (${p.get('price', 0)})"
                        for p in products[:5]
                    ])
                    parts.append(f"\nProductos disponibles: {product_list}")

            if 'category' in extra_context:
                parts.append(f"Categoría: {extra_context['category']}")

            if 'product' in extra_context:
                p = extra_context['product']
                parts.append(f"\nProducto en foco: {p.get('name')} - {p.get('description', '')} - ${p.get('price', 0)}")

        # Intent detectado
        if intent:
            parts.append(f"\nIntención del cliente: {intent}")

        # Guardar base en cache (sin pedido actual que es dinámico)
        base_prompt = "\n".join(parts)
        self._prompt_cache.set(cache_key, base_prompt)

        # Agregar pedido actual
        if context and context.order_items:
            order_summary = context.get_order_summary()
            parts.append(f"\nPedido actual: {order_summary}")
            parts.append(f"Total actual: ${context.order_total:.2f}")

        return "\n".join(parts)

    def _generate_with_llm(
        self,
        state: ConversationState,
        context: StateContext,
        user_input: str,
        intent: str = None,
        extra_context: Dict = None,
        conversation_history: List[Dict] = None
    ) -> Optional[ResponseResult]:
        """
        Genera respuesta usando el LLM.

        Returns:
            ResponseResult si exitoso, None si falla
        """
        if not self._llm_enabled or not self._llm_provider:
            return None

        start_time = time.time()

        try:
            # Construir prompt
            system_prompt = self._build_context_prompt(
                state, context, user_input, intent, extra_context
            )

            # Preparar mensajes
            messages = []
            if conversation_history:
                # Últimos 4 mensajes para contexto
                for msg in conversation_history[-4:]:
                    messages.append({
                        "role": msg.get("role", "user"),
                        "content": msg.get("content", "")
                    })

            # Agregar mensaje actual del usuario
            if user_input:
                messages.append({"role": "user", "content": user_input})

            # Llamar al LLM
            result = self._llm_provider.generate(
                prompt=system_prompt,
                messages=messages,
                temperature=0.7,
                max_tokens=200,
                intent=intent  # Para cascade: decide si usar OpenAI
            )

            latency_ms = (time.time() - start_time) * 1000
            response_text = result.get("response_text", "")

            if not response_text or len(response_text) < 10:
                logger.warning(f"[RESPONSE_GEN] LLM respuesta vacía o muy corta")
                return None

            # Limpiar respuesta
            response_text = self._clean_llm_response(response_text)

            provider_used = result.get("provider", "unknown")
            if result.get("fallback_chain"):
                provider_used = f"{provider_used} (chain: {result['fallback_chain']})"

            logger.info(f"[RESPONSE_GEN] LLM OK - Provider: {result.get('provider')} - {len(response_text)} chars - {latency_ms:.0f}ms")

            return ResponseResult(
                text=response_text,
                provider_used=result.get("provider", "unknown"),
                tokens_used=result.get("tokens_used", 0),
                latency_ms=latency_ms,
                fallback_to_template=False
            )

        except Exception as e:
            logger.error(f"[RESPONSE_GEN] Error LLM: {e}")
            return None

    def _clean_llm_response(self, text: str) -> str:
        """Limpia la respuesta del LLM"""
        text = text.strip()

        # Quitar prefijos comunes
        prefixes = ["Mesero:", "Asistente:", "Bot:", "Agente:", "Respuesta:"]
        for prefix in prefixes:
            if text.startswith(prefix):
                text = text[len(prefix):].strip()

        # Limite más estricto: máximo 150 caracteres para respuestas cortas
        max_len = 200
        if len(text) > max_len:
            # Cortar en el último signo de puntuación antes del límite
            for sep in ["?", ".", "!"]:
                idx = text.rfind(sep, 0, max_len)
                if idx > 50:
                    text = text[:idx+1]
                    break
            else:
                # Si no hay puntuación, cortar y agregar ?
                text = text[:max_len-1] + "?"

        return text

    def _load_templates(self):
        """
        Carga plantillas de respuesta SOLO como fallback de emergencia.
        El LLM es el generador principal - estas plantillas solo se usan si falla.
        """
        self.templates = {
            # BIENVENIDA
            ConversationState.BIENVENIDA: {
                'default': ["Bienvenido, es un placer atenderle. {producto_destacado} está excepcional hoy. ¿En qué puedo servirle?"],
                'variables': {'producto_destacado': ['Nuestra carne asada', 'Nuestros tacos al pastor']}
            },

            # MICRO-EMBUDO (categorías y productos)
            ConversationState.MICRO_EMBUDO: {
                'list_category': ["Le recomiendo {producto_estrella}, es nuestra especialidad. También contamos con {otros_productos}. ¿{cierre}?"],
                'recommend_popular': ["Le recomiendo {producto}, es el favorito de nuestros clientes. ¿Se lo preparo?"],
                'recommend_mentioned': ["Excelente elección, {producto} es una opción muy popular. ¿Se lo preparo?"],
                'product_details': ["{producto}: {descripcion}. ${precio}. ¿Le gustaría probarlo?"],
                'variables': {'cierre': ['Cuántos le preparo', 'Cuál prefiere']}
            },

            # UPSELL
            ConversationState.UPSELL: {
                'upgrade': ["Por ${diferencia} adicionales {upgrade_descripcion}. ¿Le interesa?"],
                'combo': ["En combo con {items_combo} obtiene un ahorro de ${ahorro}. ¿Lo preparamos así?"],
                'extra': ["¿Le gustaría agregar {extra}? {beneficio}. Son ${precio} adicionales."],
                'alternativa_menor': ["También tenemos {alternativa} a ${precio}. ¿Le interesa?"],
                'variables': {'beneficio': ['Complementa perfectamente su platillo', 'Es una excelente adición']}
            },

            # CROSS-SELL
            ConversationState.CROSS_SELL: {
                'beverage': ["¿Puedo ofrecerle algo de beber? {bebida_recomendada} está {estado}. ${precio}."],
                'side': ["¿Le gustaría complementar con {complemento}? {beneficio}. ${precio}."],
                'dessert': ["¿Le interesaría algún postre? {postre} está {estado}."],
                'variables': {'estado': ['delicioso', 'recién preparado']}
            },

            # CONFIRMACIÓN
            ConversationState.CONFIRMACION: {
                'summary': ["Su pedido incluye {resumen_pedido}. El total es ${total}. ¿Desea agregar algo más?"],
                'final': ["Perfecto. Su total es ${total}. Estará listo en aproximadamente 10 minutos."],
                'variables': {}
            },

            # CIERRE
            ConversationState.CIERRE: {
                'default': ["Su total es ${total} pesos. Gracias por su preferencia, que disfrute su comida."],
                'variables': {}
            },

            # AUXILIARES
            'unavailable': ["Lamentablemente no contamos con {producto_solicitado}. Sin embargo, le recomiendo {alternativa_principal}."],
            'clarification': ["Disculpe, ¿podría repetir su solicitud?"]
        }

        self.closings = {
            'quantity': ['¿Cuántos le preparo?'],
            'prepare': ['¿Se lo preparo?'],
            'more': ['¿Desea algo más?'],
            'confirm': ['¿Procedemos con su pedido?']
        }

    def generate(
        self,
        state: ConversationState,
        context: StateContext,
        template_key: str = 'default',
        variables: Dict[str, Any] = None,
        user_input: str = "",
        intent: str = None,
        extra_context: Dict = None,
        conversation_history: List[Dict] = None,
        force_template: bool = False
    ) -> ResponseResult:
        """
        Genera una respuesta inteligente usando LLM o templates.

        Flujo:
        1. Si LLM habilitado y no force_template → intenta LLM
        2. Si LLM falla → usa template como fallback
        3. Registra métricas del provider usado

        Args:
            state: Estado actual
            context: Contexto de la conversación
            template_key: Clave de plantilla a usar (para fallback)
            variables: Variables para reemplazar en la plantilla
            user_input: Input del usuario (para LLM)
            intent: Intención detectada (para cascade)
            extra_context: Contexto adicional (productos, categoría, etc.)
            conversation_history: Historial de mensajes
            force_template: Forzar uso de template (skip LLM)

        Returns:
            ResponseResult con el texto generado y métricas
        """
        variables = variables or {}

        # ============================================================
        # INTENTO 1: Generar con LLM
        # ============================================================
        if not force_template and self._llm_enabled:
            llm_result = self._generate_with_llm(
                state=state,
                context=context,
                user_input=user_input,
                intent=intent,
                extra_context=extra_context,
                conversation_history=conversation_history
            )

            if llm_result and llm_result.text:
                return llm_result

            logger.warning(f"[RESPONSE] LLM falló, usando template como fallback")

        # ============================================================
        # FALLBACK: Generar con template
        # ============================================================
        return self._generate_with_template(state, context, template_key, variables)

    def _generate_with_template(
        self,
        state: ConversationState,
        context: StateContext,
        template_key: str = 'default',
        variables: Dict[str, Any] = None
    ) -> ResponseResult:
        """
        Genera respuesta usando templates (fallback).
        """
        variables = variables or {}

        # Obtener plantillas del estado
        state_templates = self.templates.get(state, {})

        if isinstance(state_templates, dict):
            templates = state_templates.get(template_key, state_templates.get('default', []))
            state_variables = state_templates.get('variables', {})
        else:
            templates = state_templates
            state_variables = {}

        if not templates:
            logger.warning(f"[RESPONSE] No hay plantillas para estado={state}, key={template_key}")
            return ResponseResult(
                text="¿En qué te puedo ayudar?",
                fallback_to_template=True,
                provider_used="template_fallback"
            )

        # Seleccionar plantilla aleatoria
        template = random.choice(templates) if isinstance(templates, list) else templates

        # Combinar variables del estado con variables proporcionadas
        all_variables = {}
        for key, options in state_variables.items():
            if key not in variables:
                all_variables[key] = random.choice(options) if isinstance(options, list) else options
        all_variables.update(variables)

        # Reemplazar variables en la plantilla
        try:
            text = template.format(**all_variables)
        except KeyError as e:
            logger.warning(f"[RESPONSE] Variable faltante: {e}")
            text = template

        logger.info(f"[RESPONSE] Template generado: {text[:100]}...")

        return ResponseResult(
            text=text,
            fallback_to_template=True,
            provider_used="template"
        )

    def generate_category_list(
        self,
        category: str,
        products: List[Dict],
        context: StateContext,
        user_input: str = "",
        conversation_history: List[Dict] = None
    ) -> ResponseResult:
        """Genera respuesta para listar una categoría usando LLM"""

        if not products:
            return ResponseResult(
                text=f"No tenemos {category} disponibles en este momento. ¿Te interesa otra cosa?",
                provider_used="hardcoded"
            )

        # Encontrar producto estrella (popular o primero)
        producto_estrella = None
        for p in products:
            if 'popular' in p.get('tags', []):
                producto_estrella = p
                break
        if not producto_estrella:
            producto_estrella = products[0]

        # Intentar con LLM primero
        extra_context = {
            'category': category,
            'products': products,
            'producto_estrella': producto_estrella
        }

        result = self.generate(
            state=ConversationState.MICRO_EMBUDO,
            context=context,
            template_key='list_category',
            user_input=user_input or f"Quiero ver los {category}",
            intent='view_menu',
            extra_context=extra_context,
            conversation_history=conversation_history,
            variables={
                'producto_estrella': producto_estrella['name'],
                'otros_productos': ', '.join([p['name'] for p in products[1:4]]),
                'cierre': "Cuántos te pongo" if 'taco' in category.lower() else "Cuál te preparo"
            }
        )

        # Agregar datos visuales
        result.visual_data = {
            "type": "product_list",
            "category": category,
            "products": [
                {
                    "id": p.get('id'),
                    "name": p.get('name'),
                    "price": p.get('price'),
                    "image_url": p.get('image_url'),
                    "category_id": p.get('category_id') or p.get('category', {}).get('id')
                }
                for p in products
            ],
            "highlighted": producto_estrella['name']
        }

        return result

    def generate_recommendation(
        self,
        product: Dict,
        context: StateContext,
        is_mentioned: bool = False,
        user_input: str = "",
        conversation_history: List[Dict] = None
    ) -> ResponseResult:
        """Genera respuesta de recomendación usando LLM"""

        template_key = 'recommend_mentioned' if is_mentioned else 'recommend_popular'

        # Convertir precio a float (puede venir como string del menú)
        try:
            precio = float(product.get('price', 0))
        except (ValueError, TypeError):
            precio = 0.0

        # Determinar cierre según tipo de producto
        product_name = product.get('name', '').lower()
        if 'taco' in product_name:
            cierre = "Cuántos te pongo"
            accion = "los pongo"
        elif 'agua' in product_name or 'bebida' in product_name:
            cierre = "Te la pongo"
            accion = "la pongo"
        else:
            cierre = "Te lo preparo"
            accion = "lo preparo"

        # Contexto para LLM
        extra_context = {
            'product': product,
            'is_mentioned': is_mentioned
        }

        result = self.generate(
            state=ConversationState.MICRO_EMBUDO,
            context=context,
            template_key=template_key,
            user_input=user_input,
            intent='create_order' if is_mentioned else 'view_menu',
            extra_context=extra_context,
            conversation_history=conversation_history,
            variables={
                'producto': product['name'],
                'precio': f"${precio:.2f}",
                'cierre': cierre,
                'accion': accion
            }
        )

        # Agregar datos visuales
        result.visual_data = {
            "type": "product_detail",
            "product": {
                "id": product.get('id'),
                "name": product.get('name'),
                "description": product.get('description', ''),
                "price": precio,
                "image_url": product.get('image_url'),
                "category": product.get('category', {}).get('name', ''),
                "category_id": product.get('category_id') or product.get('category', {}).get('id'),
                # Campos para personalización de ingredientes
                "ingredients": product.get('ingredients', ''),
                "is_vegetarian": product.get('is_vegetarian', False),
                "is_gluten_free": product.get('is_gluten_free', False),
                "spice_level": product.get('spice_level', 0),
                "preparation_time_minutes": product.get('preparation_time_minutes', 15),
                "is_available": product.get('is_available', True),
                "popularity": product.get('popularity', 3),
                "tags": product.get('tags', []),
                "menu_classification": product.get('menu_classification', '')
            }
        }

        return result

    def generate_upsell(
        self,
        upsell_type: str,
        context: StateContext,
        user_input: str = "",
        conversation_history: List[Dict] = None,
        **kwargs
    ) -> ResponseResult:
        """Genera oferta de upsell usando LLM"""

        if upsell_type == 'upgrade':
            variables = {
                'diferencia': kwargs.get('price_diff', 40),
                'upgrade_descripcion': kwargs.get('description', 'la hacemos DOBLE CARNE'),
                'upgrade_pregunta': kwargs.get('question', 'La hacemos doble'),
                'beneficio': kwargs.get('benefit', 'es otro nivel')
            }
            template_key = 'upgrade'

        elif upsell_type == 'combo':
            variables = {
                'items_combo': kwargs.get('items', 'papas y bebida'),
                'ahorro': kwargs.get('savings', 25),
                'precio_combo': kwargs.get('combo_price', 120),
                'beneficio': kwargs.get('benefit', 'Ahorras y llevas todo')
            }
            template_key = 'combo'

        elif upsell_type == 'extra':
            variables = {
                'extra': kwargs.get('extra', 'TOCINO CRUJIENTE'),
                'beneficio': kwargs.get('benefit', 'Queda espectacular'),
                'precio': kwargs.get('price', 15)
            }
            template_key = 'extra'

        else:
            variables = {
                'alternativa': kwargs.get('alternative', 'las papas'),
                'descripcion': kwargs.get('description', 'Crujientes y recién hechas'),
                'precio': kwargs.get('price', 35)
            }
            template_key = 'alternativa_menor'

        # Contexto para LLM
        extra_context = {
            'upsell_type': upsell_type,
            **kwargs
        }

        return self.generate(
            state=ConversationState.UPSELL,
            context=context,
            template_key=template_key,
            user_input=user_input,
            intent='upsell',
            extra_context=extra_context,
            conversation_history=conversation_history,
            variables=variables
        )

    def generate_crosssell(
        self,
        crosssell_type: str,
        context: StateContext,
        user_input: str = "",
        conversation_history: List[Dict] = None,
        **kwargs
    ) -> ResponseResult:
        """Genera oferta de cross-sell usando LLM"""

        if crosssell_type == 'beverage':
            variables = {
                'bebida_recomendada': kwargs.get('beverage', 'Agua de limón'),
                'estado': kwargs.get('state', 'recién hecha'),
                'precio': kwargs.get('price', 20)
            }
            template_key = 'beverage'

        elif crosssell_type == 'side':
            variables = {
                'complemento': kwargs.get('side', 'papas crujientes'),
                'beneficio': kwargs.get('benefit', 'quedan perfectas'),
                'precio': kwargs.get('price', 35)
            }
            template_key = 'side'

        else:
            variables = {
                'postre': kwargs.get('dessert', 'el flan'),
                'estado': kwargs.get('state', 'buenísimo')
            }
            template_key = 'dessert'

        # Contexto para LLM
        extra_context = {
            'crosssell_type': crosssell_type,
            **kwargs
        }

        return self.generate(
            state=ConversationState.CROSS_SELL,
            context=context,
            template_key=template_key,
            user_input=user_input,
            intent='crosssell',
            extra_context=extra_context,
            conversation_history=conversation_history,
            variables=variables
        )

    def generate_confirmation(
        self,
        context: StateContext,
        is_final: bool = False,
        user_input: str = "",
        conversation_history: List[Dict] = None
    ) -> ResponseResult:
        """Genera confirmación de pedido usando LLM"""

        resumen = context.get_order_summary()

        if is_final:
            variables = {
                'total': f"{context.order_total:.2f}"
            }
            template_key = 'final'
        else:
            # Determinar última oportunidad de venta
            if not context.has_beverage():
                ultima_oportunidad = "¿Agregamos bebida"
            elif not context.has_side():
                ultima_oportunidad = "¿Agregamos papas"
            else:
                ultima_oportunidad = "¿Algo más"

            variables = {
                'resumen_pedido': resumen,
                'total': f"{context.order_total:.2f}",
                'ultima_oportunidad': ultima_oportunidad
            }
            template_key = 'summary'

        # Contexto para LLM
        extra_context = {
            'order_summary': resumen,
            'order_total': context.order_total,
            'is_final': is_final,
            'has_beverage': context.has_beverage(),
            'has_side': context.has_side()
        }

        return self.generate(
            state=ConversationState.CONFIRMACION,
            context=context,
            template_key=template_key,
            user_input=user_input,
            intent='confirm_order' if is_final else 'view_order',
            extra_context=extra_context,
            conversation_history=conversation_history,
            variables=variables
        )

    def generate_closing(
        self,
        context: StateContext,
        user_input: str = "",
        conversation_history: List[Dict] = None
    ) -> ResponseResult:
        """Genera despedida usando LLM"""
        extra_context = {
            'order_summary': context.get_order_summary(),
            'order_total': context.order_total
        }
        return self.generate(
            state=ConversationState.CIERRE,
            context=context,
            user_input=user_input,
            intent='goodbye',
            extra_context=extra_context,
            conversation_history=conversation_history
        )

    def generate_product_details(
        self,
        product: Dict,
        context: StateContext,
        user_input: str = "",
        conversation_history: List[Dict] = None
    ) -> ResponseResult:
        """Genera detalles de un producto usando LLM"""

        # Convertir precio a float (puede venir como string)
        try:
            precio = float(product.get('price', 0))
        except (ValueError, TypeError):
            precio = 0.0

        variables = {
            'producto': product['name'],
            'descripcion': product.get('description', 'Delicioso platillo'),
            'ingredientes': product.get('description', 'ingredientes frescos'),
            'precio': f"{precio:.2f}",
            'cierre': '¿Te lo preparo?',
            'accion': 'lo preparo'
        }

        extra_context = {
            'product': product
        }

        result = self.generate(
            state=ConversationState.MICRO_EMBUDO,
            context=context,
            template_key='product_details',
            user_input=user_input,
            intent='ask_details',
            extra_context=extra_context,
            conversation_history=conversation_history,
            variables=variables
        )

        result.visual_data = {
            "type": "product_detail",
            "product": {
                "id": product.get('id'),
                "name": product.get('name'),
                "description": product.get('description', ''),
                "price": precio,
                "image_url": product.get('image_url'),
                "category": product.get('category', {}).get('name', ''),
                "category_id": product.get('category_id') or product.get('category', {}).get('id'),
                # Campos para personalización de ingredientes
                "ingredients": product.get('ingredients', ''),
                "is_vegetarian": product.get('is_vegetarian', False),
                "is_gluten_free": product.get('is_gluten_free', False),
                "spice_level": product.get('spice_level', 0),
                "preparation_time_minutes": product.get('preparation_time_minutes', 15),
                "is_available": product.get('is_available', True),
                "popularity": product.get('popularity', 3),
                "tags": product.get('tags', []),
                "menu_classification": product.get('menu_classification', '')
            }
        }

        return result

    def generate_error(self, error_type: str = 'general') -> ResponseResult:
        """Genera respuesta de error (siempre usa template)"""

        errors = {
            'general': "Disculpe, no logré comprender su solicitud. ¿Podría repetirla, por favor?",
            'no_product': "No encontré ese producto en nuestro menú. ¿Le gustaría que le muestre nuestras opciones disponibles?",
            'empty_order': "Aún no tiene productos en su pedido. ¿En qué puedo ayudarle?"
        }

        return ResponseResult(
            text=errors.get(error_type, errors['general']),
            provider_used="error_template",
            fallback_to_template=True
        )

    def generate_small_talk(self, intent: str) -> Optional[ResponseResult]:
        """
        Genera respuesta para intents de small-talk.

        Feature #6: Maneja conversaciones casuales para hacer
        al asistente más humano y natural.

        Args:
            intent: Intent de small-talk detectado

        Returns:
            ResponseResult si es small-talk, None si no aplica
        """
        response_text = get_small_talk_response(intent)

        if response_text:
            logger.info(f"[RESPONSE] Small-talk: {intent} → {response_text[:50]}...")
            return ResponseResult(
                text=response_text,
                provider_used="small_talk",
                fallback_to_template=False
            )

        return None

    def generate_with_empathy(
        self,
        intent: str,
        base_response: str,
        level: EmpathyLevel = None
    ) -> str:
        """
        Agrega frase empática a una respuesta base.

        Feature #7: Hace las respuestas más humanas y conectadas
        emocionalmente según el contexto.

        Args:
            intent: Intent actual para determinar nivel
            base_response: Respuesta base a enriquecer
            level: Nivel de empatía (opcional, se infiere del intent)

        Returns:
            Respuesta con frase empática al inicio
        """
        empathy_phrase = get_empathy_phrase(intent, level)

        # Evitar duplicar frases empáticas
        if base_response.lower().startswith(empathy_phrase.lower()[:10]):
            return base_response

        return f"{empathy_phrase}. {base_response}"

    def generate_add_to_order_confirmation(
        self,
        product_name: str,
        quantity: int,
        context: StateContext,
        modification: str = None
    ) -> ResponseResult:
        """
        Genera confirmación implícita al agregar producto.

        Feature #8: Confirma naturalmente sin preguntar
        "¿Seguro que quiere...?". Fluye la conversación.

        Args:
            product_name: Nombre del producto agregado
            quantity: Cantidad
            context: Contexto actual
            modification: Modificación especial (ej: "sin cebolla")

        Returns:
            ResponseResult con confirmación implícita
        """
        # Detectar si tiene bebida o guarnición
        has_drink = context.has_beverage() if context else False
        has_side = context.has_side() if context else False
        total = context.order_total if context else 0

        # Generar confirmación implícita
        response_text = generate_implicit_confirmation(
            product_name=product_name,
            quantity=quantity,
            total=total if total > 50 else None,
            has_drink=has_drink,
            has_side=has_side,
            modification=modification
        )

        logger.info(f"[RESPONSE] Implicit confirmation: {response_text}")

        return ResponseResult(
            text=response_text,
            provider_used="implicit_confirmation",
            fallback_to_template=False
        )

    def get_llm_metrics(self) -> Dict:
        """Retorna métricas del LLM provider"""
        if self._llm_provider and hasattr(self._llm_provider, 'get_metrics_summary'):
            return self._llm_provider.get_metrics_summary()
        return {"status": "LLM no disponible"}

    def set_llm_enabled(self, enabled: bool):
        """Habilita/deshabilita el uso de LLM"""
        self._llm_enabled = enabled
        logger.info(f"[RESPONSE_GEN] LLM {'habilitado' if enabled else 'deshabilitado'}")

    def get_prompt_cache_stats(self) -> Dict:
        """Retorna estadísticas del cache de prompts"""
        return self._prompt_cache.stats()

    def clear_prompt_cache(self):
        """Limpia el cache de prompts"""
        self._prompt_cache = PromptCache(max_size=50)
        logger.info("[RESPONSE_GEN] Cache de prompts limpiado")
