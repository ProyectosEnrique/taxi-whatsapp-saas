# ============================================================
# FEEDBACK COLLECTOR - Colector de Feedback
# ============================================================
# Captura automática de interacciones para revisión
# ============================================================

import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
import uuid

from .models import (
    FeedbackEntry,
    FeedbackRating,
    ErrorType,
    ConversationSnapshot
)
from .storage import FeedbackStorage, get_feedback_storage

logger = logging.getLogger(__name__)


class FeedbackCollector:
    """
    Colector de feedback que captura interacciones automáticamente.

    Características:
    - Captura cada interacción usuario-sistema
    - Detecta automáticamente posibles errores
    - Marca para revisión manual
    - Se integra sin modificar el FSM principal
    """

    def __init__(self, storage: FeedbackStorage = None, config: Dict = None):
        """
        Inicializa el colector.

        Args:
            storage: Almacenamiento de feedback
            config: Configuración opcional
        """
        self.storage = storage or get_feedback_storage()
        self.config = config or {}

        # Configuración
        self.auto_detect_errors = self.config.get('auto_detect_errors', True)
        self.capture_all = self.config.get('capture_all', True)
        self.min_confidence_threshold = self.config.get('min_confidence_threshold', 0.6)

        # Cache de sesiones para detectar patrones
        self._session_cache: Dict[str, List[FeedbackEntry]] = {}

        logger.info("[FEEDBACK_COLLECTOR] Inicializado")

    def capture(
        self,
        session_id: str,
        user_input: str,
        detected_intent: str,
        intent_confidence: float,
        system_response: str,
        context: Any = None,
        recommended_product: str = None,
        response_state: str = None
    ) -> Optional[str]:
        """
        Captura una interacción.

        Args:
            session_id: ID de la sesión
            user_input: Texto del usuario
            detected_intent: Intención detectada
            intent_confidence: Confianza de la detección
            system_response: Respuesta del sistema
            context: Contexto del FSM (StateContext)
            recommended_product: Producto recomendado (si aplica)
            response_state: Estado después de la respuesta

        Returns:
            ID de la entrada de feedback creada
        """
        # Crear snapshot del contexto
        context_snapshot = None
        if context:
            context_snapshot = self._create_context_snapshot(context)

        # Crear entrada de feedback
        entry = FeedbackEntry(
            id=str(uuid.uuid4())[:8],
            session_id=session_id,
            timestamp=datetime.now(),
            user_input=user_input,
            detected_intent=detected_intent,
            intent_confidence=intent_confidence,
            system_response=system_response,
            recommended_product=recommended_product,
            response_state=response_state or (context_snapshot.state if context_snapshot else ''),
            context_snapshot=context_snapshot,
            rating=FeedbackRating.PENDING
        )

        # Auto-detectar posibles errores
        if self.auto_detect_errors:
            detected_errors = self._auto_detect_errors(entry)
            entry.error_types = detected_errors

            # Si hay errores auto-detectados, marcar como posible incorrecto
            if detected_errors and ErrorType.NONE not in detected_errors:
                entry.tags.append('auto_flagged')

        # Guardar en cache de sesión
        if session_id not in self._session_cache:
            self._session_cache[session_id] = []
        self._session_cache[session_id].append(entry)

        # Detectar patrones en la sesión
        session_patterns = self._detect_session_patterns(session_id)
        if session_patterns:
            entry.tags.extend(session_patterns)

        # Guardar
        entry_id = self.storage.save(entry)

        logger.debug(f"[FEEDBACK_COLLECTOR] Capturada interacción {entry_id} "
                    f"(intent: {detected_intent}, conf: {intent_confidence:.2f})")

        return entry_id

    def _create_context_snapshot(self, context) -> ConversationSnapshot:
        """Crea un snapshot del contexto actual"""
        return ConversationSnapshot(
            state=context.state.value if hasattr(context.state, 'value') else str(context.state),
            active_category=context.active_category,
            order_items=[item.name for item in context.order_items] if hasattr(context, 'order_items') else [],
            order_total=context.order_total if hasattr(context, 'order_total') else 0.0,
            upsell_attempts=context.upsell_attempts if hasattr(context, 'upsell_attempts') else 0,
            crosssell_attempts=context.crosssell_attempts if hasattr(context, 'crosssell_attempts') else 0,
            conversation_turn=len(context.conversation_history) if hasattr(context, 'conversation_history') else 0
        )

    def _auto_detect_errors(self, entry: FeedbackEntry) -> List[ErrorType]:
        """
        Auto-detecta posibles errores en la respuesta.

        Heurísticas:
        - Confianza baja → posible error de intención
        - Respuesta muy corta → posible error
        - Respuesta no termina en pregunta → posible error de engagement
        """
        errors = []

        # Confianza baja en la detección de intención
        if entry.intent_confidence < self.min_confidence_threshold:
            errors.append(ErrorType.WRONG_INTENT)

        # Respuesta vacía o muy corta
        if not entry.system_response or len(entry.system_response) < 10:
            errors.append(ErrorType.UNCLEAR_RESPONSE)

        # Detectar si perdió contexto (categoría activa pero respuesta genérica)
        if entry.context_snapshot:
            if entry.context_snapshot.active_category:
                # Si hay categoría activa pero la respuesta no la menciona
                category_lower = entry.context_snapshot.active_category.lower()
                response_lower = entry.system_response.lower()
                if category_lower not in response_lower:
                    # Verificar si es una respuesta de cambio de categoría válida
                    if entry.detected_intent not in ['view_category', 'view_menu']:
                        errors.append(ErrorType.LOST_CONTEXT)

        # Detectar recomendación prematura
        if entry.recommended_product and entry.context_snapshot:
            # Si es la primera interacción en la categoría y ya recomienda específico
            if entry.context_snapshot.conversation_turn <= 2:
                if entry.detected_intent == 'view_category':
                    errors.append(ErrorType.PREMATURE_RECOMMENDATION)

        # Si no se detectaron errores, marcar como sin error
        if not errors:
            errors.append(ErrorType.NONE)

        return errors

    def _detect_session_patterns(self, session_id: str) -> List[str]:
        """
        Detecta patrones problemáticos en la sesión.

        Returns:
            Lista de tags que describen patrones detectados
        """
        patterns = []
        entries = self._session_cache.get(session_id, [])

        if len(entries) < 2:
            return patterns

        # Detectar repetición de sugerencias
        recent_products = [e.recommended_product for e in entries[-5:] if e.recommended_product]
        if len(recent_products) != len(set(recent_products)):
            patterns.append('repeated_suggestions')

        # Detectar múltiples rechazos consecutivos
        recent_intents = [e.detected_intent for e in entries[-3:]]
        if recent_intents.count('reject_suggestion') >= 2:
            patterns.append('multiple_rejections')

        # Detectar conversación muy larga sin orden
        if len(entries) > 10:
            has_order = any(e.context_snapshot and e.context_snapshot.order_items for e in entries)
            if not has_order:
                patterns.append('long_no_conversion')

        # Detectar cambios frecuentes de categoría
        recent_categories = []
        for e in entries[-5:]:
            if e.context_snapshot and e.context_snapshot.active_category:
                recent_categories.append(e.context_snapshot.active_category)

        if len(set(recent_categories)) >= 3:
            patterns.append('category_hopping')

        return patterns

    def record_user_reaction(
        self,
        entry_id: str,
        accepted: bool,
        next_action: str = None
    ) -> bool:
        """
        Registra la reacción del usuario a una respuesta.

        Args:
            entry_id: ID de la entrada
            accepted: Si el usuario aceptó la sugerencia
            next_action: Siguiente acción del usuario

        Returns:
            True si se actualizó correctamente
        """
        entry = self.storage.get(entry_id)
        if not entry:
            return False

        entry.user_accepted = accepted
        entry.user_next_action = next_action or ''

        # Auto-ajustar rating basado en reacción
        if not accepted and entry.rating == FeedbackRating.PENDING:
            entry.tags.append('user_rejected')

        return self.storage.update(entry)

    def record_conversion(self, session_id: str, converted: bool) -> int:
        """
        Registra si la sesión terminó en conversión (compra).

        Args:
            session_id: ID de la sesión
            converted: Si hubo compra

        Returns:
            Número de entradas actualizadas
        """
        entries = self.storage.get_by_session(session_id)
        updated = 0

        for entry in entries:
            entry.conversion_result = converted
            if self.storage.update(entry):
                updated += 1

        logger.info(f"[FEEDBACK_COLLECTOR] Conversión registrada para sesión {session_id}: {converted}")
        return updated

    def get_session_summary(self, session_id: str) -> Dict[str, Any]:
        """
        Obtiene resumen de una sesión para revisión.

        Args:
            session_id: ID de la sesión

        Returns:
            Dict con resumen de la sesión
        """
        entries = self.storage.get_by_session(session_id)

        if not entries:
            return {'error': 'Sesión no encontrada'}

        return {
            'session_id': session_id,
            'total_interactions': len(entries),
            'start_time': entries[0].timestamp.isoformat() if entries else None,
            'end_time': entries[-1].timestamp.isoformat() if entries else None,
            'intents_used': list(set(e.detected_intent for e in entries)),
            'products_mentioned': list(set(e.recommended_product for e in entries if e.recommended_product)),
            'final_order': entries[-1].context_snapshot.order_items if entries[-1].context_snapshot else [],
            'conversion': entries[-1].conversion_result if entries else None,
            'pending_review': sum(1 for e in entries if e.rating == FeedbackRating.PENDING),
            'flagged_issues': list(set(tag for e in entries for tag in e.tags)),
            'interactions': [
                {
                    'id': e.id,
                    'user': e.user_input,
                    'intent': e.detected_intent,
                    'response': e.system_response[:100] + '...' if len(e.system_response) > 100 else e.system_response,
                    'rating': e.rating.value,
                    'errors': [err.value for err in e.error_types]
                }
                for e in entries
            ]
        }

    def clear_session_cache(self, session_id: str = None):
        """Limpia el cache de sesiones"""
        if session_id:
            self._session_cache.pop(session_id, None)
        else:
            self._session_cache.clear()


# Instancia global
_feedback_collector: Optional[FeedbackCollector] = None


def get_feedback_collector(config: Dict = None) -> FeedbackCollector:
    """Obtiene instancia global del collector (Singleton)"""
    global _feedback_collector
    if _feedback_collector is None:
        _feedback_collector = FeedbackCollector(config=config)
    return _feedback_collector
