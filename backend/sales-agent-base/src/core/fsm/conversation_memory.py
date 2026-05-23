# ============================================================
# CONVERSATION MEMORY - FSM
# ============================================================
# Sistema de memoria y resumen contextual de conversaciones
# Mantiene historial relevante sin saturar el contexto
# ============================================================

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque
import json

logger = logging.getLogger(__name__)


@dataclass
class ConversationTurn:
    """Representa un turno de conversación"""
    role: str  # 'user' o 'assistant'
    content: str
    timestamp: datetime
    intent: Optional[str] = None
    state: Optional[str] = None
    entities: Dict = field(default_factory=dict)
    importance: float = 1.0  # 0.0 - 1.0, para filtrar turnos importantes


@dataclass
class ConversationSummary:
    """Resumen de la conversación"""
    key_topics: List[str]
    mentioned_products: List[str]
    customer_preferences: Dict[str, Any]
    order_items: List[str]
    current_intent: str
    last_category: Optional[str]
    sentiment: str  # positive, neutral, negative
    summary_text: str


class ConversationMemory:
    """
    Sistema de memoria de conversación con resumen contextual.

    Características:
    1. Almacena historial completo pero limita el contexto activo
    2. Genera resúmenes automáticos para conversaciones largas
    3. Detecta y prioriza información importante
    4. Mantiene preferencias del cliente entre turnos
    """

    def __init__(self, config: Dict = None):
        """
        Inicializa el sistema de memoria.

        Args:
            config: Configuración opcional
        """
        self.config = config or {}

        # Configuración
        self.max_active_turns = self.config.get('max_active_turns', 10)
        self.summary_threshold = self.config.get('summary_threshold', 8)
        self.importance_decay = self.config.get('importance_decay', 0.9)

        # Historial completo
        self.full_history: List[ConversationTurn] = []

        # Ventana activa de contexto (las más recientes)
        self.active_window: deque = deque(maxlen=self.max_active_turns)

        # Resumen acumulado
        self.accumulated_summary: Optional[ConversationSummary] = None

        # Información extraída
        self.mentioned_products: List[str] = []
        self.customer_preferences: Dict[str, Any] = {}
        self.topics_discussed: List[str] = []

        # Timestamps
        self.session_start: datetime = datetime.now()
        self.last_interaction: datetime = datetime.now()

        logger.info("[MEMORY] Sistema de memoria inicializado")

    def add_turn(
        self,
        role: str,
        content: str,
        intent: str = None,
        state: str = None,
        entities: Dict = None
    ) -> None:
        """
        Agrega un turno a la memoria.

        Args:
            role: 'user' o 'assistant'
            content: Contenido del mensaje
            intent: Intención detectada
            state: Estado actual del FSM
            entities: Entidades extraídas
        """
        # Calcular importancia del turno
        importance = self._calculate_importance(role, content, intent, entities)

        turn = ConversationTurn(
            role=role,
            content=content,
            timestamp=datetime.now(),
            intent=intent,
            state=state,
            entities=entities or {},
            importance=importance
        )

        # Agregar al historial completo
        self.full_history.append(turn)

        # Agregar a la ventana activa
        self.active_window.append(turn)

        # Extraer información importante
        self._extract_information(turn)

        # Actualizar timestamp
        self.last_interaction = datetime.now()

        # Generar resumen si es necesario
        if len(self.full_history) >= self.summary_threshold and \
           len(self.full_history) % self.summary_threshold == 0:
            self._generate_summary()

        logger.debug(f"[MEMORY] Turno agregado: {role} | {intent} | importancia: {importance:.2f}")

    def _calculate_importance(
        self,
        role: str,
        content: str,
        intent: str,
        entities: Dict
    ) -> float:
        """
        Calcula la importancia de un turno para el contexto.

        Factores:
        - Turnos del usuario son más importantes
        - Intenciones de pedido/confirmación son importantes
        - Menciones de productos específicos aumentan importancia
        - Preguntas son importantes (terminan en ?)
        """
        importance = 0.5  # Base

        # Turnos del usuario ligeramente más importantes
        if role == 'user':
            importance += 0.1

        # Intenciones críticas
        critical_intents = {
            'add_to_order': 0.3,
            'confirm_order': 0.3,
            'accept_suggestion': 0.2,
            'reject_suggestion': 0.2,
            'view_category': 0.15,
            'get_recommendation': 0.1
        }

        if intent in critical_intents:
            importance += critical_intents[intent]

        # Entidades mencionadas
        if entities:
            if 'mentioned_product' in entities:
                importance += 0.2
            if 'quantity' in entities:
                importance += 0.1
            if 'category' in entities:
                importance += 0.1

        # Preguntas del usuario
        if role == 'user' and content.strip().endswith('?'):
            importance += 0.1

        # Mensajes largos tienden a ser más informativos
        word_count = len(content.split())
        if word_count > 10:
            importance += 0.1

        return min(importance, 1.0)

    def _extract_information(self, turn: ConversationTurn) -> None:
        """Extrae información importante del turno"""

        content_lower = turn.content.lower()

        # Extraer productos mencionados
        if turn.entities.get('mentioned_product'):
            product = turn.entities['mentioned_product']
            if product not in self.mentioned_products:
                self.mentioned_products.append(product)

        # Extraer preferencias del cliente
        preference_patterns = {
            'sin_picante': ['sin picante', 'no picante', 'nada picoso'],
            'vegetariano': ['vegetariano', 'sin carne', 'vegano'],
            'saludable': ['saludable', 'ligero', 'bajo en calorías'],
            'económico': ['económico', 'barato', 'no tan caro'],
            'rápido': ['rápido', 'que sea rápido', 'tengo prisa']
        }

        for pref_key, patterns in preference_patterns.items():
            if any(p in content_lower for p in patterns):
                self.customer_preferences[pref_key] = True

        # Extraer temas discutidos
        topic_keywords = {
            'hamburguesas': ['hamburguesa', 'burger'],
            'tacos': ['taco', 'taquito'],
            'bebidas': ['bebida', 'tomar', 'refresco', 'agua'],
            'postres': ['postre', 'dulce'],
            'precios': ['precio', 'cuesta', 'vale', 'cuánto'],
            'ingredientes': ['ingrediente', 'lleva', 'tiene'],
            'recomendaciones': ['recomienda', 'sugieres', 'mejor']
        }

        for topic, keywords in topic_keywords.items():
            if any(kw in content_lower for kw in keywords):
                if topic not in self.topics_discussed:
                    self.topics_discussed.append(topic)

    def _generate_summary(self) -> None:
        """Genera un resumen de la conversación hasta ahora"""

        # Tomar turnos que no están en la ventana activa
        older_turns = self.full_history[:-self.max_active_turns]

        if not older_turns:
            return

        # Construir resumen
        key_intents = []
        products_mentioned = []
        states_visited = []

        for turn in older_turns:
            if turn.intent and turn.intent not in key_intents:
                key_intents.append(turn.intent)
            if turn.entities.get('mentioned_product'):
                products_mentioned.append(turn.entities['mentioned_product'])
            if turn.state and turn.state not in states_visited:
                states_visited.append(turn.state)

        # Determinar sentimiento general
        positive_words = ['sí', 'perfecto', 'excelente', 'bueno', 'gracias']
        negative_words = ['no', 'malo', 'caro', 'feo']

        positive_count = sum(1 for t in older_turns if any(w in t.content.lower() for w in positive_words))
        negative_count = sum(1 for t in older_turns if any(w in t.content.lower() for w in negative_words))

        if positive_count > negative_count * 2:
            sentiment = 'positive'
        elif negative_count > positive_count * 2:
            sentiment = 'negative'
        else:
            sentiment = 'neutral'

        # Generar texto de resumen
        summary_parts = []

        if products_mentioned:
            unique_products = list(set(products_mentioned))[:5]
            summary_parts.append(f"Productos mencionados: {', '.join(unique_products)}")

        if self.customer_preferences:
            prefs = ', '.join(self.customer_preferences.keys())
            summary_parts.append(f"Preferencias: {prefs}")

        if self.topics_discussed:
            summary_parts.append(f"Temas: {', '.join(self.topics_discussed[:5])}")

        self.accumulated_summary = ConversationSummary(
            key_topics=self.topics_discussed[:5],
            mentioned_products=list(set(products_mentioned))[:5],
            customer_preferences=self.customer_preferences.copy(),
            order_items=[],  # Se llena desde el contexto
            current_intent=key_intents[-1] if key_intents else 'unknown',
            last_category=None,
            sentiment=sentiment,
            summary_text=' | '.join(summary_parts)
        )

        logger.info(f"[MEMORY] Resumen generado: {self.accumulated_summary.summary_text}")

    def get_context_for_llm(self, max_chars: int = 2000) -> str:
        """
        Obtiene contexto optimizado para enviar al LLM.

        Args:
            max_chars: Máximo de caracteres permitidos

        Returns:
            String con el contexto formateado
        """
        parts = []

        # Incluir resumen si existe
        if self.accumulated_summary:
            parts.append(f"[RESUMEN PREVIO] {self.accumulated_summary.summary_text}")

        # Incluir preferencias del cliente
        if self.customer_preferences:
            prefs = ', '.join(f"{k}={v}" for k, v in self.customer_preferences.items())
            parts.append(f"[PREFERENCIAS] {prefs}")

        # Incluir productos mencionados
        if self.mentioned_products:
            parts.append(f"[PRODUCTOS MENCIONADOS] {', '.join(self.mentioned_products[-5:])}")

        # Incluir últimos turnos (más recientes primero en importancia)
        parts.append("[CONVERSACIÓN RECIENTE]")

        for turn in self.active_window:
            role_label = "Cliente" if turn.role == 'user' else "Asistente"
            intent_label = f" ({turn.intent})" if turn.intent else ""
            parts.append(f"{role_label}{intent_label}: {turn.content}")

        context = '\n'.join(parts)

        # Truncar si es necesario
        if len(context) > max_chars:
            # Mantener resumen y preferencias, truncar conversación
            essential = '\n'.join(parts[:3])
            remaining = max_chars - len(essential) - 50
            conversation = '\n'.join(parts[3:])
            context = essential + '\n' + conversation[-remaining:] + '\n[...truncado...]'

        return context

    def get_conversation_history(
        self,
        last_n: int = None,
        min_importance: float = 0.0
    ) -> List[Dict]:
        """
        Obtiene historial de conversación en formato dict.

        Args:
            last_n: Últimos N turnos (None = todos)
            min_importance: Filtrar por importancia mínima

        Returns:
            Lista de dicts con el historial
        """
        turns = list(self.active_window) if last_n is None else list(self.active_window)[-last_n:]

        # Filtrar por importancia
        if min_importance > 0:
            turns = [t for t in turns if t.importance >= min_importance]

        return [
            {
                'role': t.role,
                'content': t.content,
                'timestamp': t.timestamp.isoformat(),
                'intent': t.intent,
                'state': t.state,
                'importance': t.importance
            }
            for t in turns
        ]

    def get_customer_profile(self) -> Dict[str, Any]:
        """
        Obtiene perfil del cliente basado en la conversación.

        Returns:
            Dict con el perfil detectado
        """
        return {
            'preferences': self.customer_preferences,
            'products_interested': self.mentioned_products,
            'topics_discussed': self.topics_discussed,
            'interaction_count': len(self.full_history),
            'session_duration': (datetime.now() - self.session_start).total_seconds(),
            'sentiment': self.accumulated_summary.sentiment if self.accumulated_summary else 'neutral'
        }

    def get_relevant_context(self, current_intent: str) -> Dict[str, Any]:
        """
        Obtiene contexto relevante para la intención actual.

        Args:
            current_intent: Intención que se está procesando

        Returns:
            Dict con contexto relevante
        """
        context = {
            'last_user_message': None,
            'last_assistant_response': None,
            'related_products': [],
            'customer_preferences': self.customer_preferences,
            'conversation_summary': None
        }

        # Obtener últimos mensajes
        for turn in reversed(list(self.active_window)):
            if turn.role == 'user' and context['last_user_message'] is None:
                context['last_user_message'] = turn.content
            elif turn.role == 'assistant' and context['last_assistant_response'] is None:
                context['last_assistant_response'] = turn.content

            if context['last_user_message'] and context['last_assistant_response']:
                break

        # Productos relacionados con la intención
        if current_intent == 'get_recommendation':
            context['related_products'] = self.mentioned_products[-3:]
        elif current_intent in ['add_to_order', 'view_category']:
            context['related_products'] = self.mentioned_products[-5:]

        # Resumen si existe
        if self.accumulated_summary:
            context['conversation_summary'] = self.accumulated_summary.summary_text

        return context

    def reset(self) -> None:
        """Reinicia la memoria para una nueva conversación"""
        self.full_history = []
        self.active_window.clear()
        self.accumulated_summary = None
        self.mentioned_products = []
        self.customer_preferences = {}
        self.topics_discussed = []
        self.session_start = datetime.now()
        self.last_interaction = datetime.now()

        logger.info("[MEMORY] Memoria reiniciada")

    def to_dict(self) -> Dict:
        """Serializa la memoria a diccionario"""
        return {
            'full_history_count': len(self.full_history),
            'active_window_count': len(self.active_window),
            'mentioned_products': self.mentioned_products,
            'customer_preferences': self.customer_preferences,
            'topics_discussed': self.topics_discussed,
            'session_duration': (datetime.now() - self.session_start).total_seconds(),
            'has_summary': self.accumulated_summary is not None
        }


# Instancia por sesión (se debe crear una por cada sesión)
def create_conversation_memory(config: Dict = None) -> ConversationMemory:
    """Crea una nueva instancia de memoria de conversación"""
    return ConversationMemory(config=config)
