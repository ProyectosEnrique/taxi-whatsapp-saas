"""
================================================================================
AGENTS MODULE
================================================================================
Modulo de agentes especializados para el sistema de restaurante.

Arquitectura hibrida B+C:
- Servicios compartidos: STT, TTS, LLM
- Agentes separados con configuracion propia
- Function calling para acciones
- LoRA fine-tuning por rol

Agentes disponibles:
- SalesAgent: Agente de ventas para clientes (kiosko/mesa)
- AdminAgent: Asistente para administrador del restaurante
================================================================================
"""

from .base_agent import BaseAgent, AgentResponse, AgentConfig
from .admin_agent import AdminAgent, get_admin_agent

__all__ = [
    'BaseAgent',
    'AgentResponse',
    'AgentConfig',
    'AdminAgent',
    'get_admin_agent'
]
