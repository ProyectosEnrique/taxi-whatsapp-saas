"""
================================================================================
ANALYTICS MODULE - SISTEMA COMPLETO DE INTELIGENCIA DE VENTAS
================================================================================
Módulo de análisis de datos para recomendaciones inteligentes

FASE 1 - Inteligencia básica:
  - SalesIntelligence: Datos reales de popularidad, historial, reglas por horario

FASE 2 - Análisis avanzado:
  - BasketAnalyzer: Productos frecuentemente comprados juntos
  - PropensityScorer: Probabilidad de aceptación de recomendaciones
  - SmartRejectionHandler: Manejo inteligente de rechazos
  - SalesMetricsTracker: Dashboard de métricas en tiempo real

FASE 3 - Machine Learning:
  - CollaborativeFilter: "Usuarios que ordenaron X también ordenaron Y"
  - DynamicRanker: Ranking multi-factor con momentum
  - SeasonalityAnalyzer: Patrones por día/hora/eventos
================================================================================
"""

# FASE 1 - Inteligencia de ventas básica
from .sales_intelligence import SalesIntelligence, get_sales_intelligence

# FASE 2 - Análisis avanzado
from .basket_analyzer import BasketAnalyzer, get_basket_analyzer
from .propensity_scorer import PropensityScorer, get_propensity_scorer, CustomerProfile, CustomerSegment
from .rejection_handler import SmartRejectionHandler, get_rejection_handler, RejectionType
from .sales_metrics import SalesMetricsTracker, get_metrics_tracker, SalesMetricsSnapshot

# FASE 3 - Machine Learning
from .collaborative_filter import CollaborativeFilter, get_collaborative_filter
from .dynamic_ranker import DynamicRanker, get_dynamic_ranker, RankingFactors
from .seasonality_analyzer import SeasonalityAnalyzer, get_seasonality_analyzer, SeasonalPattern

__all__ = [
    # FASE 1
    'SalesIntelligence',
    'get_sales_intelligence',
    # FASE 2
    'BasketAnalyzer',
    'get_basket_analyzer',
    'PropensityScorer',
    'get_propensity_scorer',
    'CustomerProfile',
    'CustomerSegment',
    'SmartRejectionHandler',
    'get_rejection_handler',
    'RejectionType',
    'SalesMetricsTracker',
    'get_metrics_tracker',
    'SalesMetricsSnapshot',
    # FASE 3
    'CollaborativeFilter',
    'get_collaborative_filter',
    'DynamicRanker',
    'get_dynamic_ranker',
    'RankingFactors',
    'SeasonalityAnalyzer',
    'get_seasonality_analyzer',
    'SeasonalPattern'
]
