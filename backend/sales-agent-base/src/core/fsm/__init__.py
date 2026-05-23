# ============================================================
# FSM - MÁQUINA DE ESTADOS PARA AGENTE DE VENTAS
# ============================================================
# Sistema profesional de gestión de conversaciones
# Versión: 2.1.0
# ============================================================

from .conversation_states import ConversationState, StateContext
from .state_machine import SalesAgentFSM
from .decision_tree import IntentDecisionTree, Intent, IntentResult
from .response_generator import ResponseGenerator
from .llm_fallback import LLMFallbackHandler, get_fallback_handler, FallbackResult
from .product_matcher import ProductMatcher, get_product_matcher, ProductMatch
from .conversation_memory import ConversationMemory, create_conversation_memory
from .tenant_fsm_factory import TenantFSMFactory

__all__ = [
    # Estados y contexto
    'ConversationState',
    'StateContext',

    # FSM principal
    'SalesAgentFSM',

    # Clasificación de intenciones
    'IntentDecisionTree',
    'Intent',
    'IntentResult',

    # Generación de respuestas
    'ResponseGenerator',

    # LLM Fallback (v2.1)
    'LLMFallbackHandler',
    'get_fallback_handler',
    'FallbackResult',

    # Product Matcher (v2.1)
    'ProductMatcher',
    'get_product_matcher',
    'ProductMatch',

    # Memoria de conversación (v2.1)
    'ConversationMemory',
    'create_conversation_memory',

    # Multi-tenant (v2.2)
    'TenantFSMFactory',
]
