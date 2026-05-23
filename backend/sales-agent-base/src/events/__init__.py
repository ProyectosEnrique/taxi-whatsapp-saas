# ============================================================
# EVENTS MODULE - Event Bus para Mensajería Desacoplada
# ============================================================
# Implementa patrón Publisher/Subscriber usando Redis
# Permite comunicación asíncrona entre componentes
# ============================================================

from .event_bus import EventBus, get_event_bus, Event, EventType
from .event_handlers import register_default_handlers

__all__ = [
    'EventBus',
    'get_event_bus',
    'Event',
    'EventType',
    'register_default_handlers'
]
