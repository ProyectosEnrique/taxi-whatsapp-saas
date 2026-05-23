# ============================================================
# PROMETHEUS METRICS - Métricas para Voice Assistant
# ============================================================
# Implementa métricas estándar de Prometheus
# Fallback a contadores simples si prometheus_client no está
# ============================================================

import logging
import time
from functools import wraps
from typing import Callable, Dict, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)

# Intentar importar prometheus_client
try:
    from prometheus_client import (
        Counter, Histogram, Gauge, Summary, Info,
        generate_latest, CONTENT_TYPE_LATEST,
        CollectorRegistry, REGISTRY
    )
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    logger.warning("[METRICS] prometheus_client no disponible, usando fallback")


# ============================================================
# FALLBACK METRICS (cuando Prometheus no está disponible)
# ============================================================

@dataclass
class SimpleMetric:
    """Métrica simple cuando Prometheus no está disponible"""
    name: str
    value: float = 0.0
    labels: Dict[str, str] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def inc(self, value: float = 1.0):
        self.value += value
        self.timestamp = datetime.utcnow()

    def dec(self, value: float = 1.0):
        self.value -= value
        self.timestamp = datetime.utcnow()

    def set(self, value: float):
        self.value = value
        self.timestamp = datetime.utcnow()

    def observe(self, value: float):
        # Para histogramas, simplemente promediamos
        self.value = (self.value + value) / 2
        self.timestamp = datetime.utcnow()


class SimpleCounter:
    """Counter simple sin Prometheus"""
    def __init__(self, name: str, description: str, labelnames: list = None):
        self.name = name
        self.description = description
        self.labelnames = labelnames or []
        self._values: Dict[str, float] = {}

    def labels(self, **kwargs) -> 'SimpleCounter':
        key = str(sorted(kwargs.items()))
        if key not in self._values:
            self._values[key] = 0.0
        self._current_key = key
        return self

    def inc(self, value: float = 1.0):
        key = getattr(self, '_current_key', 'default')
        if key not in self._values:
            self._values[key] = 0.0
        self._values[key] += value

    def get_total(self) -> float:
        return sum(self._values.values())


class SimpleHistogram:
    """Histogram simple sin Prometheus"""
    def __init__(self, name: str, description: str, labelnames: list = None, buckets: list = None):
        self.name = name
        self.description = description
        self.labelnames = labelnames or []
        self._values: list = []

    def labels(self, **kwargs) -> 'SimpleHistogram':
        return self

    def observe(self, value: float):
        self._values.append(value)
        if len(self._values) > 1000:
            self._values = self._values[-1000:]

    def get_avg(self) -> float:
        if not self._values:
            return 0.0
        return sum(self._values) / len(self._values)


class SimpleGauge:
    """Gauge simple sin Prometheus"""
    def __init__(self, name: str, description: str, labelnames: list = None):
        self.name = name
        self.description = description
        self.labelnames = labelnames or []
        self._value = 0.0

    def labels(self, **kwargs) -> 'SimpleGauge':
        return self

    def set(self, value: float):
        self._value = value

    def inc(self, value: float = 1.0):
        self._value += value

    def dec(self, value: float = 1.0):
        self._value -= value

    def get(self) -> float:
        return self._value


# ============================================================
# VOICE ASSISTANT METRICS
# ============================================================

class VoiceAssistantMetrics:
    """
    Colección de métricas para el Voice Assistant.

    Métricas disponibles:
    - Requests: total, latencia, errores
    - Intents: clasificaciones por tipo y método
    - LLM: llamadas, latencia, tokens
    - Órdenes: creadas, confirmadas, valor
    - Upselling: ofrecidos, aceptados
    - TTS/STT: latencia
    """

    def __init__(self, registry=None):
        self.registry = registry

        if PROMETHEUS_AVAILABLE:
            self._init_prometheus_metrics()
        else:
            self._init_simple_metrics()

        logger.info(f"[METRICS] Inicializadas ({'Prometheus' if PROMETHEUS_AVAILABLE else 'Simple'})")

    def _init_prometheus_metrics(self):
        """Inicializa métricas de Prometheus"""
        # === REQUEST METRICS ===
        self.requests_total = Counter(
            'voice_assistant_requests_total',
            'Total de requests procesados',
            ['endpoint', 'status']
        )

        self.request_duration = Histogram(
            'voice_assistant_request_duration_seconds',
            'Duración de requests en segundos',
            ['endpoint'],
            buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
        )

        # === INTENT METRICS ===
        self.intents_total = Counter(
            'voice_assistant_intents_total',
            'Total de intents clasificados',
            ['intent', 'method']
        )

        self.intent_confidence = Histogram(
            'voice_assistant_intent_confidence',
            'Distribución de confianza de intents',
            ['intent'],
            buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
        )

        # === LLM METRICS ===
        self.llm_calls_total = Counter(
            'voice_assistant_llm_calls_total',
            'Total de llamadas a LLM',
            ['provider', 'model', 'intent']
        )

        self.llm_duration = Histogram(
            'voice_assistant_llm_duration_seconds',
            'Duración de llamadas LLM en segundos',
            ['provider'],
            buckets=[0.5, 1.0, 2.0, 3.0, 5.0, 10.0, 30.0]
        )

        self.llm_tokens = Counter(
            'voice_assistant_llm_tokens_total',
            'Total de tokens consumidos',
            ['provider', 'type']  # type: input/output
        )

        # === ORDER METRICS ===
        self.orders_total = Counter(
            'voice_assistant_orders_total',
            'Total de órdenes',
            ['status']  # created, confirmed, cancelled
        )

        self.order_value = Histogram(
            'voice_assistant_order_value_pesos',
            'Valor de órdenes en pesos',
            buckets=[50, 100, 150, 200, 300, 500, 750, 1000]
        )

        self.order_items = Histogram(
            'voice_assistant_order_items',
            'Número de items por orden',
            buckets=[1, 2, 3, 4, 5, 7, 10, 15]
        )

        # === UPSELL METRICS ===
        self.upsells_total = Counter(
            'voice_assistant_upsells_total',
            'Total de upsells',
            ['result']  # offered, accepted, rejected
        )

        self.upsell_value = Counter(
            'voice_assistant_upsell_value_pesos',
            'Valor adicional por upselling en pesos'
        )

        # === PRODUCT METRICS ===
        self.products_searched = Counter(
            'voice_assistant_products_searched_total',
            'Total de búsquedas de productos',
            ['result']  # found, not_found, suggested
        )

        # === CONVERSATION METRICS ===
        self.conversations_active = Gauge(
            'voice_assistant_conversations_active',
            'Conversaciones activas actualmente'
        )

        self.conversation_duration = Histogram(
            'voice_assistant_conversation_duration_seconds',
            'Duración de conversaciones en segundos',
            buckets=[30, 60, 120, 180, 300, 600]
        )

        self.messages_per_conversation = Histogram(
            'voice_assistant_messages_per_conversation',
            'Mensajes por conversación',
            buckets=[2, 4, 6, 8, 10, 15, 20, 30]
        )

        # === TTS/STT METRICS ===
        self.tts_duration = Histogram(
            'voice_assistant_tts_duration_seconds',
            'Duración de síntesis de voz',
            ['provider'],
            buckets=[0.1, 0.25, 0.5, 1.0, 2.0, 5.0]
        )

        self.stt_duration = Histogram(
            'voice_assistant_stt_duration_seconds',
            'Duración de reconocimiento de voz',
            ['provider'],
            buckets=[0.1, 0.25, 0.5, 1.0, 2.0, 5.0]
        )

        # === ERROR METRICS ===
        self.errors_total = Counter(
            'voice_assistant_errors_total',
            'Total de errores',
            ['type', 'component']
        )

        # === SYSTEM METRICS ===
        self.system_info = Info(
            'voice_assistant_info',
            'Información del sistema'
        )
        self.system_info.info({
            'version': '2.0.0',
            'nlu_enabled': 'true',
            'event_bus': 'enabled'
        })

    def _init_simple_metrics(self):
        """Inicializa métricas simples (fallback)"""
        self.requests_total = SimpleCounter('requests_total', 'Total requests')
        self.request_duration = SimpleHistogram('request_duration', 'Request duration')
        self.intents_total = SimpleCounter('intents_total', 'Total intents')
        self.intent_confidence = SimpleHistogram('intent_confidence', 'Intent confidence')
        self.llm_calls_total = SimpleCounter('llm_calls_total', 'LLM calls')
        self.llm_duration = SimpleHistogram('llm_duration', 'LLM duration')
        self.llm_tokens = SimpleCounter('llm_tokens', 'LLM tokens')
        self.orders_total = SimpleCounter('orders_total', 'Total orders')
        self.order_value = SimpleHistogram('order_value', 'Order value')
        self.order_items = SimpleHistogram('order_items', 'Order items')
        self.upsells_total = SimpleCounter('upsells_total', 'Total upsells')
        self.upsell_value = SimpleCounter('upsell_value', 'Upsell value')
        self.products_searched = SimpleCounter('products_searched', 'Products searched')
        self.conversations_active = SimpleGauge('conversations_active', 'Active conversations')
        self.conversation_duration = SimpleHistogram('conversation_duration', 'Conversation duration')
        self.messages_per_conversation = SimpleHistogram('messages_per_conv', 'Messages per conversation')
        self.tts_duration = SimpleHistogram('tts_duration', 'TTS duration')
        self.stt_duration = SimpleHistogram('stt_duration', 'STT duration')
        self.errors_total = SimpleCounter('errors_total', 'Total errors')

    def get_prometheus_metrics(self) -> Optional[bytes]:
        """Genera métricas en formato Prometheus"""
        if PROMETHEUS_AVAILABLE:
            return generate_latest(REGISTRY)
        return None

    def get_content_type(self) -> str:
        """Retorna content type para métricas"""
        if PROMETHEUS_AVAILABLE:
            return CONTENT_TYPE_LATEST
        return "text/plain"


# ============================================================
# SINGLETON Y HELPERS
# ============================================================

_metrics: Optional[VoiceAssistantMetrics] = None


def get_metrics() -> VoiceAssistantMetrics:
    """Obtiene instancia singleton de métricas"""
    global _metrics
    if _metrics is None:
        _metrics = VoiceAssistantMetrics()
    return _metrics


def init_metrics():
    """Inicializa métricas (llamar al startup)"""
    global _metrics
    _metrics = VoiceAssistantMetrics()
    return _metrics


# ============================================================
# DECORADORES Y HELPERS
# ============================================================

def track_request(endpoint: str):
    """Decorador para trackear requests"""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            metrics = get_metrics()
            start_time = time.time()
            status = "success"

            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                status = "error"
                raise
            finally:
                duration = time.time() - start_time
                metrics.requests_total.labels(endpoint=endpoint, status=status).inc()
                metrics.request_duration.labels(endpoint=endpoint).observe(duration)

        return wrapper
    return decorator


def track_intent(intent: str, confidence: float, method: str):
    """Trackea clasificación de intent"""
    metrics = get_metrics()
    metrics.intents_total.labels(intent=intent, method=method).inc()
    metrics.intent_confidence.labels(intent=intent).observe(confidence)


def track_order(status: str, value: float = 0, items: int = 0):
    """Trackea orden"""
    metrics = get_metrics()
    metrics.orders_total.labels(status=status).inc()
    if value > 0:
        metrics.order_value.observe(value)
    if items > 0:
        metrics.order_items.observe(items)


def track_upsell(result: str, value: float = 0):
    """Trackea upsell"""
    metrics = get_metrics()
    metrics.upsells_total.labels(result=result).inc()
    if result == "accepted" and value > 0:
        metrics.upsell_value.inc(value)


def track_llm_call(provider: str, model: str, intent: str, duration: float,
                   input_tokens: int = 0, output_tokens: int = 0):
    """Trackea llamada a LLM"""
    metrics = get_metrics()
    metrics.llm_calls_total.labels(provider=provider, model=model, intent=intent).inc()
    metrics.llm_duration.labels(provider=provider).observe(duration)
    if input_tokens > 0:
        metrics.llm_tokens.labels(provider=provider, type="input").inc(input_tokens)
    if output_tokens > 0:
        metrics.llm_tokens.labels(provider=provider, type="output").inc(output_tokens)


def track_error(error_type: str, component: str):
    """Trackea error"""
    metrics = get_metrics()
    metrics.errors_total.labels(type=error_type, component=component).inc()


def track_product_search(result: str):
    """Trackea búsqueda de producto"""
    metrics = get_metrics()
    metrics.products_searched.labels(result=result).inc()


def track_conversation_start():
    """Trackea inicio de conversación"""
    metrics = get_metrics()
    metrics.conversations_active.inc()


def track_conversation_end(duration_seconds: float, message_count: int):
    """Trackea fin de conversación"""
    metrics = get_metrics()
    metrics.conversations_active.dec()
    metrics.conversation_duration.observe(duration_seconds)
    metrics.messages_per_conversation.observe(message_count)


def track_tts(provider: str, duration: float):
    """Trackea síntesis de voz"""
    metrics = get_metrics()
    metrics.tts_duration.labels(provider=provider).observe(duration)


def track_stt(provider: str, duration: float):
    """Trackea reconocimiento de voz"""
    metrics = get_metrics()
    metrics.stt_duration.labels(provider=provider).observe(duration)
