# ============================================================
# FEEDBACK ANALYZER - Analizador de Feedback
# ============================================================
# Analiza patrones de errores y genera recomendaciones
# para mejorar el agente de ventas
# ============================================================

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict

from .models import (
    FeedbackEntry,
    FeedbackRating,
    ErrorType,
    FeedbackStats
)
from .storage import FeedbackStorage, get_feedback_storage

logger = logging.getLogger(__name__)


class FeedbackAnalyzer:
    """
    Analizador de feedback que identifica patrones y genera insights.

    Capacidades:
    - Análisis de errores más comunes
    - Identificación de intenciones problemáticas
    - Detección de patrones de conversación fallidos
    - Generación de recomendaciones de mejora
    - Sugerencias para nuevos patrones de detección
    """

    def __init__(self, storage: FeedbackStorage = None):
        """
        Inicializa el analizador.

        Args:
            storage: Almacenamiento de feedback
        """
        self.storage = storage or get_feedback_storage()
        logger.info("[FEEDBACK_ANALYZER] Inicializado")

    def analyze(self, days: int = 7) -> Dict[str, Any]:
        """
        Análisis completo del feedback.

        Args:
            days: Días de datos a analizar

        Returns:
            Dict con análisis completo
        """
        entries = self.storage.get_all(days)

        if not entries:
            return {'error': 'No hay datos para analizar', 'entries_count': 0}

        return {
            'period': f'Últimos {days} días',
            'total_entries': len(entries),
            'stats': self.storage.calculate_stats(days).to_dict(),
            'error_analysis': self._analyze_errors(entries),
            'intent_analysis': self._analyze_intents(entries),
            'state_analysis': self._analyze_states(entries),
            'pattern_analysis': self._analyze_patterns(entries),
            'recommendations': self._generate_recommendations(entries),
            'training_suggestions': self._generate_training_suggestions(entries)
        }

    def _analyze_errors(self, entries: List[FeedbackEntry]) -> Dict[str, Any]:
        """Analiza los tipos de errores más comunes"""

        error_counts = defaultdict(int)
        error_examples = defaultdict(list)

        for entry in entries:
            for error in entry.error_types:
                if error != ErrorType.NONE:
                    error_counts[error.value] += 1

                    # Guardar ejemplos (máximo 3 por tipo)
                    if len(error_examples[error.value]) < 3:
                        error_examples[error.value].append({
                            'user_input': entry.user_input,
                            'system_response': entry.system_response[:100],
                            'expected': entry.expected_response[:100] if entry.expected_response else None
                        })

        # Ordenar por frecuencia
        sorted_errors = sorted(error_counts.items(), key=lambda x: x[1], reverse=True)

        return {
            'most_common': sorted_errors[:5],
            'total_errors': sum(error_counts.values()),
            'examples': dict(error_examples)
        }

    def _analyze_intents(self, entries: List[FeedbackEntry]) -> Dict[str, Any]:
        """Analiza el rendimiento por intención"""

        intent_stats = defaultdict(lambda: {
            'total': 0,
            'correct': 0,
            'partial': 0,
            'incorrect': 0,
            'avg_confidence': []
        })

        for entry in entries:
            intent = entry.detected_intent or 'unknown'
            stats = intent_stats[intent]

            stats['total'] += 1
            stats['avg_confidence'].append(entry.intent_confidence)

            if entry.rating == FeedbackRating.CORRECT:
                stats['correct'] += 1
            elif entry.rating == FeedbackRating.PARTIAL:
                stats['partial'] += 1
            elif entry.rating == FeedbackRating.INCORRECT:
                stats['incorrect'] += 1

        # Calcular métricas
        result = {}
        for intent, stats in intent_stats.items():
            reviewed = stats['correct'] + stats['partial'] + stats['incorrect']
            accuracy = stats['correct'] / reviewed if reviewed > 0 else 0

            result[intent] = {
                'total': stats['total'],
                'accuracy': round(accuracy * 100, 2),
                'avg_confidence': round(sum(stats['avg_confidence']) / len(stats['avg_confidence']) * 100, 2) if stats['avg_confidence'] else 0,
                'error_rate': round((stats['incorrect'] / reviewed * 100) if reviewed > 0 else 0, 2)
            }

        # Ordenar por tasa de error (peores primero)
        sorted_intents = sorted(result.items(), key=lambda x: x[1]['error_rate'], reverse=True)

        return {
            'by_intent': dict(sorted_intents),
            'problematic_intents': [i for i, s in sorted_intents if s['error_rate'] > 30][:5]
        }

    def _analyze_states(self, entries: List[FeedbackEntry]) -> Dict[str, Any]:
        """Analiza el rendimiento por estado del FSM"""

        state_stats = defaultdict(lambda: {
            'total': 0,
            'correct': 0,
            'errors': []
        })

        for entry in entries:
            if entry.context_snapshot:
                state = entry.context_snapshot.state
                stats = state_stats[state]

                stats['total'] += 1
                if entry.rating == FeedbackRating.CORRECT:
                    stats['correct'] += 1

                for error in entry.error_types:
                    if error != ErrorType.NONE:
                        stats['errors'].append(error.value)

        # Calcular métricas por estado
        result = {}
        for state, stats in state_stats.items():
            accuracy = stats['correct'] / stats['total'] if stats['total'] > 0 else 0

            # Errores más comunes en este estado
            error_counts = defaultdict(int)
            for err in stats['errors']:
                error_counts[err] += 1

            result[state] = {
                'total': stats['total'],
                'accuracy': round(accuracy * 100, 2),
                'common_errors': sorted(error_counts.items(), key=lambda x: x[1], reverse=True)[:3]
            }

        return result

    def _analyze_patterns(self, entries: List[FeedbackEntry]) -> Dict[str, Any]:
        """Analiza patrones de conversación problemáticos"""

        # Agrupar por sesión
        sessions = defaultdict(list)
        for entry in entries:
            sessions[entry.session_id].append(entry)

        patterns = {
            'long_sessions_no_conversion': [],
            'high_rejection_rate': [],
            'context_loss_sessions': [],
            'category_confusion': []
        }

        for session_id, session_entries in sessions.items():
            if len(session_entries) < 2:
                continue

            # Sesiones largas sin conversión
            if len(session_entries) > 8:
                has_order = any(
                    e.context_snapshot and e.context_snapshot.order_items
                    for e in session_entries
                )
                if not has_order:
                    patterns['long_sessions_no_conversion'].append({
                        'session_id': session_id,
                        'turns': len(session_entries),
                        'last_state': session_entries[-1].response_state
                    })

            # Alta tasa de rechazo
            rejections = sum(1 for e in session_entries if e.detected_intent == 'reject_suggestion')
            if rejections >= 3:
                patterns['high_rejection_rate'].append({
                    'session_id': session_id,
                    'rejections': rejections,
                    'total_turns': len(session_entries)
                })

            # Pérdida de contexto
            context_lost = sum(
                1 for e in session_entries
                if ErrorType.LOST_CONTEXT in e.error_types
            )
            if context_lost >= 2:
                patterns['context_loss_sessions'].append({
                    'session_id': session_id,
                    'times_lost': context_lost
                })

            # Confusión de categoría
            wrong_category = sum(
                1 for e in session_entries
                if ErrorType.WRONG_CATEGORY in e.error_types
            )
            if wrong_category >= 1:
                patterns['category_confusion'].append({
                    'session_id': session_id,
                    'times': wrong_category
                })

        return {
            'summary': {
                'long_no_conversion': len(patterns['long_sessions_no_conversion']),
                'high_rejection': len(patterns['high_rejection_rate']),
                'context_loss': len(patterns['context_loss_sessions']),
                'category_confusion': len(patterns['category_confusion'])
            },
            'details': patterns
        }

    def _generate_recommendations(self, entries: List[FeedbackEntry]) -> List[Dict[str, Any]]:
        """Genera recomendaciones de mejora basadas en el análisis"""

        recommendations = []

        # Analizar datos
        error_analysis = self._analyze_errors(entries)
        intent_analysis = self._analyze_intents(entries)
        pattern_analysis = self._analyze_patterns(entries)

        # Recomendaciones basadas en errores comunes
        for error_type, count in error_analysis['most_common'][:3]:
            rec = self._get_recommendation_for_error(error_type, count, len(entries))
            if rec:
                recommendations.append(rec)

        # Recomendaciones basadas en intenciones problemáticas
        for intent in intent_analysis.get('problematic_intents', []):
            recommendations.append({
                'priority': 'high',
                'area': 'intent_detection',
                'issue': f'La intención "{intent}" tiene alta tasa de error',
                'suggestion': f'Revisar los patrones de detección para "{intent}" y agregar más ejemplos',
                'action': 'expand_patterns'
            })

        # Recomendaciones basadas en patrones
        summary = pattern_analysis.get('summary', {})

        if summary.get('long_no_conversion', 0) > 3:
            recommendations.append({
                'priority': 'high',
                'area': 'conversion',
                'issue': 'Muchas sesiones largas sin conversión',
                'suggestion': 'Revisar flujo de upsell/crosssell. Considerar ofrecer ayuda proactiva.',
                'action': 'review_sales_flow'
            })

        if summary.get('high_rejection', 0) > 2:
            recommendations.append({
                'priority': 'medium',
                'area': 'suggestions',
                'issue': 'Alta tasa de rechazo de sugerencias',
                'suggestion': 'Las sugerencias pueden ser muy agresivas o no relevantes. Revisar estrategia de upsell.',
                'action': 'adjust_upsell_strategy'
            })

        if summary.get('context_loss', 0) > 2:
            recommendations.append({
                'priority': 'high',
                'area': 'context_management',
                'issue': 'Pérdida frecuente de contexto',
                'suggestion': 'Revisar la lógica de micro-embudos y persistencia de categoría activa.',
                'action': 'fix_context_logic'
            })

        return recommendations

    def _get_recommendation_for_error(
        self,
        error_type: str,
        count: int,
        total: int
    ) -> Optional[Dict[str, Any]]:
        """Obtiene recomendación específica para un tipo de error"""

        error_rate = count / total if total > 0 else 0

        if error_rate < 0.05:  # Menos del 5%, no es significativo
            return None

        recommendations_map = {
            'wrong_intent': {
                'priority': 'high',
                'area': 'intent_detection',
                'issue': f'Error de intención detectado {count} veces ({error_rate*100:.1f}%)',
                'suggestion': 'Agregar más patrones al árbol de decisión o revisar los existentes',
                'action': 'expand_decision_tree'
            },
            'premature_rec': {
                'priority': 'medium',
                'area': 'recommendation_flow',
                'issue': f'Recomendaciones prematuras: {count} veces',
                'suggestion': 'Antes de recomendar un producto específico, preguntar preferencias o listar opciones',
                'action': 'add_preference_question'
            },
            'should_list': {
                'priority': 'medium',
                'area': 'response_templates',
                'issue': f'Debería listar opciones: {count} veces',
                'suggestion': 'Modificar plantillas para listar opciones antes de recomendar específicamente',
                'action': 'update_templates'
            },
            'lost_context': {
                'priority': 'high',
                'area': 'fsm_logic',
                'issue': f'Pérdida de contexto: {count} veces',
                'suggestion': 'Revisar transiciones de estado y persistencia de categoría activa',
                'action': 'fix_state_transitions'
            },
            'wrong_category': {
                'priority': 'high',
                'area': 'product_matching',
                'issue': f'Producto de categoría incorrecta: {count} veces',
                'suggestion': 'Mejorar el filtrado por categoría en las recomendaciones',
                'action': 'fix_category_filter'
            },
            'too_pushy': {
                'priority': 'medium',
                'area': 'sales_tone',
                'issue': f'Demasiado insistente: {count} veces',
                'suggestion': 'Reducir intentos de upsell o suavizar el tono de las ofertas',
                'action': 'adjust_upsell_limits'
            },
            'repeated': {
                'priority': 'low',
                'area': 'suggestion_logic',
                'issue': f'Sugerencias repetidas: {count} veces',
                'suggestion': 'Implementar tracking de sugerencias rechazadas para no repetir',
                'action': 'track_rejected_suggestions'
            }
        }

        return recommendations_map.get(error_type)

    def _generate_training_suggestions(
        self,
        entries: List[FeedbackEntry]
    ) -> Dict[str, Any]:
        """
        Genera sugerencias para mejorar el entrenamiento/patrones.

        Identifica:
        - Nuevos patrones de intención a agregar
        - Frases que el sistema no entendió bien
        - Productos frecuentemente confundidos
        """

        # Recopilar frases mal clasificadas
        misclassified = []
        for entry in entries:
            if entry.rating == FeedbackRating.INCORRECT:
                if ErrorType.WRONG_INTENT in entry.error_types:
                    misclassified.append({
                        'input': entry.user_input,
                        'detected_as': entry.detected_intent,
                        'expected_response': entry.expected_response
                    })

        # Identificar patrones faltantes
        # Agrupar frases similares que fallaron
        pattern_suggestions = []
        seen_inputs = set()

        for item in misclassified:
            input_lower = item['input'].lower()
            if input_lower not in seen_inputs:
                seen_inputs.add(input_lower)
                pattern_suggestions.append({
                    'phrase': item['input'],
                    'current_detection': item['detected_as'],
                    'suggestion': f'Agregar patrón para: "{item["input"]}"'
                })

        # Productos confundidos
        product_confusions = []
        for entry in entries:
            if ErrorType.WRONG_PRODUCT in entry.error_types and entry.recommended_product:
                product_confusions.append({
                    'user_asked': entry.user_input,
                    'recommended': entry.recommended_product,
                    'context_category': entry.context_snapshot.active_category if entry.context_snapshot else None
                })

        return {
            'new_patterns_needed': len(pattern_suggestions),
            'pattern_suggestions': pattern_suggestions[:10],
            'product_confusions': product_confusions[:5],
            'export_ready': len(misclassified) >= 10  # Suficientes datos para entrenar
        }

    def get_improvement_priority_list(self, days: int = 7) -> List[Dict[str, Any]]:
        """
        Obtiene lista priorizada de mejoras a implementar.

        Returns:
            Lista ordenada por prioridad de mejoras
        """
        analysis = self.analyze(days)

        priorities = []

        # Agregar recomendaciones con scores
        for rec in analysis.get('recommendations', []):
            score = {'high': 3, 'medium': 2, 'low': 1}.get(rec['priority'], 0)
            priorities.append({
                **rec,
                'score': score
            })

        # Ordenar por score
        return sorted(priorities, key=lambda x: x['score'], reverse=True)

    def compare_periods(
        self,
        period1_days: Tuple[int, int],
        period2_days: Tuple[int, int]
    ) -> Dict[str, Any]:
        """
        Compara dos períodos de tiempo.

        Args:
            period1_days: (inicio, fin) del primer período en días desde hoy
            period2_days: (inicio, fin) del segundo período

        Returns:
            Comparación de métricas entre períodos
        """
        # Esta función requeriría modificar storage para filtrar por rangos de fecha
        # Por ahora, retornamos estructura básica
        return {
            'comparison': 'not_implemented',
            'note': 'Requiere implementación de filtro por rango de fechas'
        }


# Instancia global
_feedback_analyzer: Optional[FeedbackAnalyzer] = None


def get_feedback_analyzer() -> FeedbackAnalyzer:
    """Obtiene instancia global del analyzer (Singleton)"""
    global _feedback_analyzer
    if _feedback_analyzer is None:
        _feedback_analyzer = FeedbackAnalyzer()
    return _feedback_analyzer
