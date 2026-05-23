# ============================================================
# FEEDBACK MODELS - Modelos de Datos
# ============================================================
# Define las estructuras de datos para el sistema de feedback
# ============================================================

from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
import json


class FeedbackRating(Enum):
    """Calificación de la respuesta"""
    CORRECT = "correct"           # Respuesta correcta y apropiada
    PARTIAL = "partial"           # Parcialmente correcta
    INCORRECT = "incorrect"       # Respuesta incorrecta
    PENDING = "pending"           # Pendiente de revisar


class ErrorType(Enum):
    """Tipos de errores en las respuestas"""
    # Errores de intención
    WRONG_INTENT = "wrong_intent"                    # Detectó intención incorrecta
    MISSED_INTENT = "missed_intent"                  # No detectó la intención real

    # Errores de recomendación
    WRONG_PRODUCT = "wrong_product"                  # Recomendó producto equivocado
    PREMATURE_RECOMMENDATION = "premature_rec"       # Recomendó sin preguntar preferencias
    SHOULD_LIST_OPTIONS = "should_list"              # Debió listar opciones primero
    WRONG_CATEGORY = "wrong_category"                # Producto de categoría incorrecta

    # Errores de contexto
    LOST_CONTEXT = "lost_context"                    # Perdió el contexto de la conversación
    IGNORED_PREFERENCE = "ignored_pref"              # Ignoró preferencia del cliente
    REPEATED_SUGGESTION = "repeated"                 # Repitió sugerencia rechazada

    # Errores de tono/estilo
    TOO_PUSHY = "too_pushy"                          # Demasiado insistente
    TOO_PASSIVE = "too_passive"                      # Muy pasivo, no ofreció opciones
    UNCLEAR_RESPONSE = "unclear"                     # Respuesta confusa

    # Errores de información
    WRONG_PRICE = "wrong_price"                      # Precio incorrecto
    WRONG_INFO = "wrong_info"                        # Información incorrecta del producto
    PRODUCT_UNAVAILABLE = "unavailable"              # Ofreció producto no disponible

    # Otros
    OTHER = "other"                                  # Otro tipo de error
    NONE = "none"                                    # Sin error


@dataclass
class ConversationSnapshot:
    """Captura del estado de la conversación en un momento dado"""
    state: str
    active_category: Optional[str]
    order_items: List[str]
    order_total: float
    upsell_attempts: int
    crosssell_attempts: int
    conversation_turn: int

    def to_dict(self) -> Dict:
        return {
            'state': self.state,
            'active_category': self.active_category,
            'order_items': self.order_items,
            'order_total': self.order_total,
            'upsell_attempts': self.upsell_attempts,
            'crosssell_attempts': self.crosssell_attempts,
            'conversation_turn': self.conversation_turn
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'ConversationSnapshot':
        return cls(
            state=data.get('state', ''),
            active_category=data.get('active_category'),
            order_items=data.get('order_items', []),
            order_total=data.get('order_total', 0.0),
            upsell_attempts=data.get('upsell_attempts', 0),
            crosssell_attempts=data.get('crosssell_attempts', 0),
            conversation_turn=data.get('conversation_turn', 0)
        )


@dataclass
class FeedbackEntry:
    """Entrada de feedback para una interacción"""

    # Identificadores
    id: str = ""
    session_id: str = ""
    timestamp: datetime = field(default_factory=datetime.now)

    # Input del usuario
    user_input: str = ""
    detected_intent: str = ""
    intent_confidence: float = 0.0

    # Respuesta del sistema
    system_response: str = ""
    recommended_product: Optional[str] = None
    response_state: str = ""

    # Contexto de la conversación
    context_snapshot: Optional[ConversationSnapshot] = None

    # Evaluación
    rating: FeedbackRating = FeedbackRating.PENDING
    error_types: List[ErrorType] = field(default_factory=list)
    expected_response: str = ""
    reviewer_notes: str = ""

    # Resultado real (si se conoce)
    user_accepted: Optional[bool] = None
    user_next_action: str = ""
    conversion_result: Optional[bool] = None  # ¿Terminó comprando?

    # Metadata
    reviewed_by: str = ""
    reviewed_at: Optional[datetime] = None
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """Convierte a diccionario para almacenamiento"""
        return {
            'id': self.id,
            'session_id': self.session_id,
            'timestamp': self.timestamp.isoformat(),
            'user_input': self.user_input,
            'detected_intent': self.detected_intent,
            'intent_confidence': self.intent_confidence,
            'system_response': self.system_response,
            'recommended_product': self.recommended_product,
            'response_state': self.response_state,
            'context_snapshot': self.context_snapshot.to_dict() if self.context_snapshot else None,
            'rating': self.rating.value,
            'error_types': [e.value for e in self.error_types],
            'expected_response': self.expected_response,
            'reviewer_notes': self.reviewer_notes,
            'user_accepted': self.user_accepted,
            'user_next_action': self.user_next_action,
            'conversion_result': self.conversion_result,
            'reviewed_by': self.reviewed_by,
            'reviewed_at': self.reviewed_at.isoformat() if self.reviewed_at else None,
            'tags': self.tags
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'FeedbackEntry':
        """Crea instancia desde diccionario"""
        context = None
        if data.get('context_snapshot'):
            context = ConversationSnapshot.from_dict(data['context_snapshot'])

        return cls(
            id=data.get('id', ''),
            session_id=data.get('session_id', ''),
            timestamp=datetime.fromisoformat(data['timestamp']) if data.get('timestamp') else datetime.now(),
            user_input=data.get('user_input', ''),
            detected_intent=data.get('detected_intent', ''),
            intent_confidence=data.get('intent_confidence', 0.0),
            system_response=data.get('system_response', ''),
            recommended_product=data.get('recommended_product'),
            response_state=data.get('response_state', ''),
            context_snapshot=context,
            rating=FeedbackRating(data.get('rating', 'pending')),
            error_types=[ErrorType(e) for e in data.get('error_types', [])],
            expected_response=data.get('expected_response', ''),
            reviewer_notes=data.get('reviewer_notes', ''),
            user_accepted=data.get('user_accepted'),
            user_next_action=data.get('user_next_action', ''),
            conversion_result=data.get('conversion_result'),
            reviewed_by=data.get('reviewed_by', ''),
            reviewed_at=datetime.fromisoformat(data['reviewed_at']) if data.get('reviewed_at') else None,
            tags=data.get('tags', [])
        )

    def to_json(self) -> str:
        """Convierte a JSON string"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> 'FeedbackEntry':
        """Crea instancia desde JSON string"""
        return cls.from_dict(json.loads(json_str))


@dataclass
class FeedbackStats:
    """Estadísticas agregadas de feedback"""
    total_entries: int = 0
    correct_count: int = 0
    partial_count: int = 0
    incorrect_count: int = 0
    pending_count: int = 0

    # Por tipo de error
    error_counts: Dict[str, int] = field(default_factory=dict)

    # Por intención
    intent_accuracy: Dict[str, float] = field(default_factory=dict)

    # Por estado
    state_accuracy: Dict[str, float] = field(default_factory=dict)

    # Métricas de conversión
    acceptance_rate: float = 0.0
    conversion_rate: float = 0.0

    @property
    def accuracy_rate(self) -> float:
        """Tasa de respuestas correctas"""
        reviewed = self.correct_count + self.partial_count + self.incorrect_count
        if reviewed == 0:
            return 0.0
        return self.correct_count / reviewed

    @property
    def partial_rate(self) -> float:
        """Tasa de respuestas parcialmente correctas"""
        reviewed = self.correct_count + self.partial_count + self.incorrect_count
        if reviewed == 0:
            return 0.0
        return self.partial_count / reviewed

    @property
    def error_rate(self) -> float:
        """Tasa de errores"""
        reviewed = self.correct_count + self.partial_count + self.incorrect_count
        if reviewed == 0:
            return 0.0
        return self.incorrect_count / reviewed

    def to_dict(self) -> Dict:
        return {
            'total_entries': self.total_entries,
            'correct_count': self.correct_count,
            'partial_count': self.partial_count,
            'incorrect_count': self.incorrect_count,
            'pending_count': self.pending_count,
            'accuracy_rate': round(self.accuracy_rate * 100, 2),
            'partial_rate': round(self.partial_rate * 100, 2),
            'error_rate': round(self.error_rate * 100, 2),
            'error_counts': self.error_counts,
            'intent_accuracy': self.intent_accuracy,
            'state_accuracy': self.state_accuracy,
            'acceptance_rate': round(self.acceptance_rate * 100, 2),
            'conversion_rate': round(self.conversion_rate * 100, 2)
        }
