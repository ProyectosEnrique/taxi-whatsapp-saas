# ============================================================
# FEEDBACK SYSTEM - Sistema de Retroalimentación
# ============================================================
# Módulo independiente para capturar, analizar y mejorar
# las respuestas del agente de ventas
# Versión: 1.0.0
# ============================================================

from .models import (
    FeedbackEntry,
    FeedbackRating,
    ErrorType,
    ConversationSnapshot
)
from .collector import FeedbackCollector, get_feedback_collector
from .analyzer import FeedbackAnalyzer, get_feedback_analyzer
from .storage import FeedbackStorage, get_feedback_storage

__all__ = [
    # Modelos
    'FeedbackEntry',
    'FeedbackRating',
    'ErrorType',
    'ConversationSnapshot',

    # Colector
    'FeedbackCollector',
    'get_feedback_collector',

    # Analizador
    'FeedbackAnalyzer',
    'get_feedback_analyzer',

    # Almacenamiento
    'FeedbackStorage',
    'get_feedback_storage',
]
