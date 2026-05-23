# ============================================================
# EVENT BUS - Sistema de Eventos con Redis Pub/Sub
# ============================================================
# Desacopla servicios usando mensajería asíncrona
# Fallback a memoria si Redis no está disponible
# ============================================================

import asyncio
import json
import logging
import threading
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)

# Intentar importar Redis
try:
    import redis
    from redis import asyncio as aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("[EVENT_BUS] Redis no disponible, usando fallback en memoria")


class EventType(Enum):
    """Tipos de eventos del sistema"""
    # Conversación
    CONVERSATION_STARTED = "conversation.started"
    CONVERSATION_ENDED = "conversation.ended"
    MESSAGE_RECEIVED = "message.received"
    MESSAGE_SENT = "message.sent"

    # Intent/NLU
    INTENT_CLASSIFIED = "intent.classified"
    INTENT_UNKNOWN = "intent.unknown"
    INTENT_REQUIRES_LLM = "intent.requires_llm"

    # Productos
    PRODUCT_FOUND = "product.found"
    PRODUCT_NOT_FOUND = "product.not_found"
    PRODUCT_ADDED = "product.added"
    PRODUCT_REMOVED = "product.removed"

    # Orden
    ORDER_CREATED = "order.created"
    ORDER_UPDATED = "order.updated"
    ORDER_CONFIRMED = "order.confirmed"
    ORDER_CANCELLED = "order.cancelled"

    # Upselling
    UPSELL_OFFERED = "upsell.offered"
    UPSELL_ACCEPTED = "upsell.accepted"
    UPSELL_REJECTED = "upsell.rejected"

    # Errores y Feedback
    ERROR_OCCURRED = "error.occurred"
    FEEDBACK_POSITIVE = "feedback.positive"
    FEEDBACK_NEGATIVE = "feedback.negative"

    # Sistema
    SYSTEM_HEALTH = "system.health"
    METRICS_UPDATED = "metrics.updated"


@dataclass
class Event:
    """Estructura de un evento"""
    type: EventType
    data: Dict[str, Any]
    session_id: str = ""
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    event_id: str = field(default_factory=lambda: str(uuid4()))
    source: str = "voice-assistant"

    def to_dict(self) -> Dict:
        """Convierte evento a diccionario"""
        return {
            "event_id": self.event_id,
            "type": self.type.value if isinstance(self.type, EventType) else self.type,
            "data": self.data,
            "session_id": self.session_id,
            "timestamp": self.timestamp,
            "source": self.source
        }

    def to_json(self) -> str:
        """Serializa evento a JSON"""
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: Dict) -> 'Event':
        """Crea evento desde diccionario"""
        event_type = data.get("type", "")
        # Convertir string a EventType si es posible
        try:
            event_type = EventType(event_type)
        except ValueError:
            pass

        return cls(
            type=event_type,
            data=data.get("data", {}),
            session_id=data.get("session_id", ""),
            timestamp=data.get("timestamp", datetime.utcnow().isoformat()),
            event_id=data.get("event_id", str(uuid4())),
            source=data.get("source", "unknown")
        )


class InMemoryEventBus:
    """Event Bus en memoria (fallback cuando Redis no está disponible)"""

    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}
        self._event_history: List[Event] = []
        self._max_history = 1000
        self._lock: Optional[asyncio.Lock] = None
        self._sync_lock = threading.Lock()  # Para operaciones síncronas

    def _get_lock(self) -> asyncio.Lock:
        """Obtiene o crea el lock asyncio en el event loop actual"""
        if self._lock is None:
            try:
                # Solo crear lock si hay un event loop
                asyncio.get_running_loop()
                self._lock = asyncio.Lock()
            except RuntimeError:
                # No hay event loop, usaremos sync_lock
                pass
        return self._lock

    async def publish(self, event: Event) -> bool:
        """Publica evento a todos los suscriptores"""
        try:
            event_type = event.type.value if isinstance(event.type, EventType) else str(event.type)

            # Usar lock asyncio si está disponible, sino sync_lock
            lock = self._get_lock()
            if lock:
                async with lock:
                    # Guardar en historial
                    self._event_history.append(event)
                    if len(self._event_history) > self._max_history:
                        self._event_history = self._event_history[-self._max_history:]

                    # Notificar suscriptores
                    handlers = list(self._subscribers.get(event_type, []))
                    handlers += list(self._subscribers.get("*", []))  # Wildcard subscribers
            else:
                # Fallback a threading.Lock
                with self._sync_lock:
                    self._event_history.append(event)
                    if len(self._event_history) > self._max_history:
                        self._event_history = self._event_history[-self._max_history:]
                    handlers = list(self._subscribers.get(event_type, []))
                    handlers += list(self._subscribers.get("*", []))

            for handler in handlers:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(event)
                    else:
                        handler(event)
                except Exception as e:
                    logger.error(f"[EVENT_BUS] Error en handler: {e}")

            logger.debug(f"[EVENT_BUS] Publicado: {event_type} ({len(handlers)} handlers)")
            return True

        except Exception as e:
            logger.error(f"[EVENT_BUS] Error publicando evento: {e}")
            return False

    def subscribe(self, event_type: str, handler: Callable) -> bool:
        """Suscribe handler a un tipo de evento"""
        with self._sync_lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            self._subscribers[event_type].append(handler)
            logger.info(f"[EVENT_BUS] Suscrito a: {event_type}")
            return True

    def unsubscribe(self, event_type: str, handler: Callable) -> bool:
        """Desuscribe handler de un tipo de evento"""
        with self._sync_lock:
            if event_type in self._subscribers:
                try:
                    self._subscribers[event_type].remove(handler)
                    return True
                except ValueError:
                    pass
            return False

    def get_history(self, event_type: Optional[str] = None, limit: int = 100) -> List[Event]:
        """Obtiene historial de eventos"""
        with self._sync_lock:
            if event_type:
                filtered = [e for e in self._event_history
                           if (e.type.value if isinstance(e.type, EventType) else e.type) == event_type]
                return filtered[-limit:]
            return self._event_history[-limit:]


class RedisEventBus:
    """Event Bus usando Redis Pub/Sub"""

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self._redis: Optional[redis.Redis] = None
        self._async_redis = None
        self._subscribers: Dict[str, List[Callable]] = {}
        self._pubsub = None
        self._listener_task = None
        self._running = False
        self._channel_prefix = "restaurant:events:"

    async def connect(self) -> bool:
        """Conecta a Redis"""
        try:
            self._async_redis = await aioredis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            await self._async_redis.ping()
            self._running = True
            logger.info(f"[EVENT_BUS] Conectado a Redis: {self.redis_url}")
            return True
        except Exception as e:
            logger.error(f"[EVENT_BUS] Error conectando a Redis: {e}")
            return False

    async def disconnect(self):
        """Desconecta de Redis"""
        self._running = False
        if self._listener_task:
            self._listener_task.cancel()
        if self._pubsub:
            await self._pubsub.close()
        if self._async_redis:
            await self._async_redis.close()
        logger.info("[EVENT_BUS] Desconectado de Redis")

    async def publish(self, event: Event) -> bool:
        """Publica evento a Redis"""
        try:
            event_type = event.type.value if isinstance(event.type, EventType) else str(event.type)
            channel = f"{self._channel_prefix}{event_type}"

            # Intentar publicar a Redis (puede fallar si el event loop cambió)
            try:
                if self._async_redis:
                    await self._async_redis.publish(channel, event.to_json())

                    # También guardar en lista para historial
                    await self._async_redis.lpush(
                        f"{self._channel_prefix}history:{event_type}",
                        event.to_json()
                    )
                    await self._async_redis.ltrim(
                        f"{self._channel_prefix}history:{event_type}",
                        0, 999  # Mantener últimos 1000
                    )
            except RuntimeError as re:
                # Event loop cambió - reconectar silenciosamente
                logger.debug(f"[EVENT_BUS] Redis event loop issue, skipping: {re}")
                pass

            # Notificar handlers locales (siempre funciona)
            handlers = list(self._subscribers.get(event_type, []))
            handlers += list(self._subscribers.get("*", []))

            for handler in handlers:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(event)
                    else:
                        handler(event)
                except Exception as e:
                    logger.error(f"[EVENT_BUS] Error en handler local: {e}")

            logger.debug(f"[EVENT_BUS] Publicado: {event_type}")
            return True

        except Exception as e:
            logger.error(f"[EVENT_BUS] Error publicando a Redis: {e}")
            return False

    def subscribe(self, event_type: str, handler: Callable) -> bool:
        """Suscribe handler a un tipo de evento"""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)
        logger.info(f"[EVENT_BUS] Suscrito a: {event_type}")
        return True

    async def get_history(self, event_type: str, limit: int = 100) -> List[Event]:
        """Obtiene historial de eventos desde Redis"""
        try:
            key = f"{self._channel_prefix}history:{event_type}"
            events_json = await self._async_redis.lrange(key, 0, limit - 1)
            return [Event.from_dict(json.loads(e)) for e in events_json]
        except Exception as e:
            logger.error(f"[EVENT_BUS] Error obteniendo historial: {e}")
            return []


class EventBus:
    """
    Event Bus híbrido - usa Redis si está disponible, sino memoria.

    Uso:
        bus = get_event_bus()

        # Publicar evento
        await bus.publish(Event(
            type=EventType.ORDER_CREATED,
            data={"order_id": "123", "items": [...]},
            session_id="sess_abc"
        ))

        # Suscribirse a eventos
        bus.subscribe("order.created", handle_order)
    """

    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url
        self._backend: Optional[Any] = None
        self._initialized = False

    async def initialize(self) -> bool:
        """Inicializa el event bus"""
        if self._initialized:
            return True

        # Intentar conectar a Redis
        if REDIS_AVAILABLE and self.redis_url:
            redis_bus = RedisEventBus(self.redis_url)
            if await redis_bus.connect():
                self._backend = redis_bus
                self._initialized = True
                logger.info("[EVENT_BUS] Usando Redis backend")
                return True

        # Fallback a memoria
        self._backend = InMemoryEventBus()
        self._initialized = True
        logger.info("[EVENT_BUS] Usando InMemory backend (fallback)")
        return True

    async def publish(self, event: Event) -> bool:
        """Publica un evento"""
        if not self._initialized:
            await self.initialize()
        return await self._backend.publish(event)

    def subscribe(self, event_type: str, handler: Callable) -> bool:
        """Suscribe un handler a un tipo de evento"""
        if not self._backend:
            self._backend = InMemoryEventBus()
            self._initialized = True
        return self._backend.subscribe(event_type, handler)

    async def emit(self, event_type: EventType, data: Dict, session_id: str = "") -> bool:
        """Método conveniente para emitir eventos"""
        event = Event(
            type=event_type,
            data=data,
            session_id=session_id
        )
        return await self.publish(event)

    def get_stats(self) -> Dict:
        """Obtiene estadísticas del event bus"""
        backend_type = "redis" if isinstance(self._backend, RedisEventBus) else "memory"
        return {
            "backend": backend_type,
            "initialized": self._initialized,
            "redis_available": REDIS_AVAILABLE
        }


# Singleton global
_event_bus: Optional[EventBus] = None


def get_event_bus(redis_url: Optional[str] = None) -> EventBus:
    """Obtiene la instancia global del Event Bus"""
    global _event_bus
    if _event_bus is None:
        import os
        url = redis_url or os.environ.get("REDIS_URL", "redis://redis:6379")
        _event_bus = EventBus(redis_url=url)
    return _event_bus


# Decorador para emitir eventos automáticamente
def emit_event(event_type: EventType, extract_data: Callable = None):
    """
    Decorador para emitir eventos después de ejecutar una función.

    Uso:
        @emit_event(EventType.ORDER_CREATED, lambda result: {"order_id": result.id})
        async def create_order(items):
            ...
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            result = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)

            try:
                bus = get_event_bus()
                data = extract_data(result) if extract_data else {"result": str(result)}
                await bus.emit(event_type, data)
            except Exception as e:
                logger.error(f"[EVENT_BUS] Error emitiendo evento desde decorador: {e}")

            return result
        return wrapper
    return decorator
