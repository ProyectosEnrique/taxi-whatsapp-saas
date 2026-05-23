"""
================================================================================
ADMIN AGENT MODULE
================================================================================
Asistente inteligente para el administrador del restaurante.

Capacidades:
- Consultar ventas y metricas
- Crear/gestionar promociones
- Administrar menu (activar/desactivar productos)
- Generar reportes
- Control por voz y texto

Arquitectura:
- AdminAgent: Agente principal
- AdminTools: Function calling para acciones
- AdminFSM: Maquina de estados para conversacion
- AdminPrompts: System prompts especializados
================================================================================
"""

from .agent import AdminAgent, get_admin_agent
from .tools import AdminTools, ADMIN_TOOL_DEFINITIONS
from .fsm import AdminFSM, AdminState
from .prompts import get_admin_system_prompt
# ESTRATEGIA 4: RAG - Base de conocimiento
from .knowledge_base import (
    KnowledgeRetriever,
    get_knowledge_retriever,
    get_relevant_knowledge,
    get_topic_recommendations
)

__all__ = [
    'AdminAgent',
    'get_admin_agent',
    'AdminTools',
    'ADMIN_TOOL_DEFINITIONS',
    'AdminFSM',
    'AdminState',
    'get_admin_system_prompt',
    # RAG exports
    'KnowledgeRetriever',
    'get_knowledge_retriever',
    'get_relevant_knowledge',
    'get_topic_recommendations'
]
