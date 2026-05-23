# ============================================================
# FEEDBACK API - Endpoints para el Sistema de Feedback
# ============================================================
# API REST independiente para gestionar feedback
# ============================================================

import logging
from flask import Blueprint, request, jsonify
from datetime import datetime

from .models import FeedbackEntry, FeedbackRating, ErrorType
from .storage import get_feedback_storage
from .collector import get_feedback_collector
from .analyzer import get_feedback_analyzer

logger = logging.getLogger(__name__)

# Crear Blueprint para los endpoints de feedback
feedback_bp = Blueprint('feedback', __name__, url_prefix='/api/feedback')


# ============================================================
# ENDPOINTS DE CONSULTA
# ============================================================

@feedback_bp.route('/stats', methods=['GET'])
def get_stats():
    """
    Obtiene estadísticas generales del feedback.

    Query params:
    - days: Número de días a incluir (default: 7)
    """
    days = request.args.get('days', 7, type=int)
    storage = get_feedback_storage()
    stats = storage.calculate_stats(days)

    return jsonify({
        'success': True,
        'period_days': days,
        'stats': stats.to_dict()
    })


@feedback_bp.route('/analysis', methods=['GET'])
def get_analysis():
    """
    Obtiene análisis completo del feedback.

    Query params:
    - days: Número de días a analizar (default: 7)
    """
    days = request.args.get('days', 7, type=int)
    analyzer = get_feedback_analyzer()
    analysis = analyzer.analyze(days)

    return jsonify({
        'success': True,
        'analysis': analysis
    })


@feedback_bp.route('/recommendations', methods=['GET'])
def get_recommendations():
    """
    Obtiene lista priorizada de recomendaciones de mejora.

    Query params:
    - days: Número de días a analizar (default: 7)
    """
    days = request.args.get('days', 7, type=int)
    analyzer = get_feedback_analyzer()
    priorities = analyzer.get_improvement_priority_list(days)

    return jsonify({
        'success': True,
        'recommendations': priorities
    })


@feedback_bp.route('/pending', methods=['GET'])
def get_pending():
    """
    Obtiene entradas pendientes de revisar.

    Query params:
    - limit: Máximo de entradas (default: 50)
    """
    limit = request.args.get('limit', 50, type=int)
    storage = get_feedback_storage()
    pending = storage.get_pending(limit)

    return jsonify({
        'success': True,
        'count': len(pending),
        'entries': [e.to_dict() for e in pending]
    })


@feedback_bp.route('/entries', methods=['GET'])
def get_entries():
    """
    Obtiene entradas de feedback con filtros.

    Query params:
    - days: Días hacia atrás (default: 7)
    - rating: Filtrar por rating (correct, partial, incorrect, pending)
    - error_type: Filtrar por tipo de error
    - limit: Máximo de resultados (default: 100)
    """
    days = request.args.get('days', 7, type=int)
    rating = request.args.get('rating')
    error_type = request.args.get('error_type')
    limit = request.args.get('limit', 100, type=int)

    storage = get_feedback_storage()

    if rating:
        try:
            rating_enum = FeedbackRating(rating)
            entries = storage.get_by_rating(rating_enum, days, limit)
        except ValueError:
            return jsonify({'success': False, 'error': f'Rating inválido: {rating}'}), 400
    elif error_type:
        try:
            error_enum = ErrorType(error_type)
            entries = storage.get_by_error_type(error_enum, days, limit)
        except ValueError:
            return jsonify({'success': False, 'error': f'Error type inválido: {error_type}'}), 400
    else:
        entries = storage.get_all(days)[:limit]

    return jsonify({
        'success': True,
        'count': len(entries),
        'entries': [e.to_dict() for e in entries]
    })


@feedback_bp.route('/entry/<entry_id>', methods=['GET'])
def get_entry(entry_id: str):
    """Obtiene una entrada específica por ID"""
    storage = get_feedback_storage()
    entry = storage.get(entry_id)

    if not entry:
        return jsonify({'success': False, 'error': 'Entrada no encontrada'}), 404

    return jsonify({
        'success': True,
        'entry': entry.to_dict()
    })


@feedback_bp.route('/session/<session_id>', methods=['GET'])
def get_session(session_id: str):
    """Obtiene todas las entradas de una sesión"""
    collector = get_feedback_collector()
    summary = collector.get_session_summary(session_id)

    if 'error' in summary:
        return jsonify({'success': False, 'error': summary['error']}), 404

    return jsonify({
        'success': True,
        'session': summary
    })


# ============================================================
# ENDPOINTS DE REVISIÓN
# ============================================================

@feedback_bp.route('/entry/<entry_id>/review', methods=['POST'])
def review_entry(entry_id: str):
    """
    Revisa y califica una entrada de feedback.

    Body JSON:
    {
        "rating": "correct|partial|incorrect",
        "error_types": ["wrong_intent", "lost_context", ...],
        "expected_response": "La respuesta correcta debería ser...",
        "reviewer_notes": "Notas adicionales",
        "reviewer": "nombre_revisor"
    }
    """
    storage = get_feedback_storage()
    entry = storage.get(entry_id)

    if not entry:
        return jsonify({'success': False, 'error': 'Entrada no encontrada'}), 404

    data = request.get_json() or {}

    # Actualizar rating
    if 'rating' in data:
        try:
            entry.rating = FeedbackRating(data['rating'])
        except ValueError:
            return jsonify({'success': False, 'error': 'Rating inválido'}), 400

    # Actualizar tipos de error
    if 'error_types' in data:
        try:
            entry.error_types = [ErrorType(e) for e in data['error_types']]
        except ValueError as e:
            return jsonify({'success': False, 'error': f'Error type inválido: {e}'}), 400

    # Actualizar campos de texto
    if 'expected_response' in data:
        entry.expected_response = data['expected_response']

    if 'reviewer_notes' in data:
        entry.reviewer_notes = data['reviewer_notes']

    # Metadata de revisión
    entry.reviewed_by = data.get('reviewer', 'anonymous')
    entry.reviewed_at = datetime.now()

    # Guardar
    if storage.update(entry):
        logger.info(f"[FEEDBACK_API] Entrada {entry_id} revisada por {entry.reviewed_by}")
        return jsonify({
            'success': True,
            'message': 'Entrada actualizada',
            'entry': entry.to_dict()
        })

    return jsonify({'success': False, 'error': 'Error al actualizar'}), 500


@feedback_bp.route('/entry/<entry_id>/reaction', methods=['POST'])
def record_reaction(entry_id: str):
    """
    Registra la reacción del usuario a una respuesta.

    Body JSON:
    {
        "accepted": true|false,
        "next_action": "descripción de lo que hizo después"
    }
    """
    data = request.get_json() or {}

    if 'accepted' not in data:
        return jsonify({'success': False, 'error': 'Campo "accepted" requerido'}), 400

    collector = get_feedback_collector()
    success = collector.record_user_reaction(
        entry_id=entry_id,
        accepted=data['accepted'],
        next_action=data.get('next_action')
    )

    if success:
        return jsonify({'success': True, 'message': 'Reacción registrada'})

    return jsonify({'success': False, 'error': 'Entrada no encontrada'}), 404


@feedback_bp.route('/session/<session_id>/conversion', methods=['POST'])
def record_conversion(session_id: str):
    """
    Registra si la sesión terminó en conversión (compra).

    Body JSON:
    {
        "converted": true|false
    }
    """
    data = request.get_json() or {}

    if 'converted' not in data:
        return jsonify({'success': False, 'error': 'Campo "converted" requerido'}), 400

    collector = get_feedback_collector()
    updated = collector.record_conversion(session_id, data['converted'])

    return jsonify({
        'success': True,
        'message': f'Conversión registrada para {updated} entradas'
    })


# ============================================================
# ENDPOINTS DE EXPORTACIÓN
# ============================================================

@feedback_bp.route('/export', methods=['POST'])
def export_data():
    """
    Exporta datos de feedback para análisis externo.

    Body JSON:
    {
        "days": 30,
        "format": "training"  # solo training por ahora
    }
    """
    data = request.get_json() or {}
    days = data.get('days', 30)

    storage = get_feedback_storage()

    # Generar nombre de archivo único
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_path = f'./feedback_data/exports/training_data_{timestamp}.json'

    try:
        count = storage.export_for_training(output_path, days)
        return jsonify({
            'success': True,
            'message': f'Exportados {count} entradas',
            'file': output_path
        })
    except Exception as e:
        logger.error(f"[FEEDBACK_API] Error exportando: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# ENDPOINTS DE UTILIDAD
# ============================================================

@feedback_bp.route('/error-types', methods=['GET'])
def get_error_types():
    """Lista todos los tipos de error disponibles"""
    return jsonify({
        'success': True,
        'error_types': [
            {'value': e.value, 'name': e.name}
            for e in ErrorType
        ]
    })


@feedback_bp.route('/ratings', methods=['GET'])
def get_ratings():
    """Lista todos los ratings disponibles"""
    return jsonify({
        'success': True,
        'ratings': [
            {'value': r.value, 'name': r.name}
            for r in FeedbackRating
        ]
    })


@feedback_bp.route('/health', methods=['GET'])
def health():
    """Health check del sistema de feedback"""
    storage = get_feedback_storage()

    return jsonify({
        'success': True,
        'status': 'healthy',
        'storage_path': str(storage.base_path),
        'version': '1.0.0'
    })
