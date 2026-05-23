# ============================================================
# EVENT HANDLERS - Manejadores de Eventos del Sistema
# ============================================================
# Handlers predefinidos para eventos comunes
# Integración con métricas y logging
# ============================================================

import logging
from datetime import datetime
from typing import Dict, Any

from .event_bus import Event, EventType, get_event_bus

logger = logging.getLogger(__name__)

# Contadores para métricas (se integrarán con Prometheus)
_metrics = {
    "conversations_started": 0,
    "conversations_ended": 0,
    "messages_received": 0,
    "messages_sent": 0,
    "intents_classified": {},
    "products_found": 0,
    "products_not_found": 0,
    "orders_created": 0,
    "orders_confirmed": 0,
    "upsells_offered": 0,
    "upsells_accepted": 0,
    "upsells_rejected": 0,
    "errors": 0,
    "feedback_positive": 0,
    "feedback_negative": 0,
}


def get_metrics() -> Dict[str, Any]:
    """Retorna métricas actuales"""
    return _metrics.copy()


def reset_metrics():
    """Reinicia métricas"""
    global _metrics
    for key in _metrics:
        if isinstance(_metrics[key], dict):
            _metrics[key] = {}
        else:
            _metrics[key] = 0


# ============================================================
# HANDLERS DE CONVERSACIÓN
# ============================================================

async def handle_conversation_started(event: Event):
    """Handler para inicio de conversación"""
    _metrics["conversations_started"] += 1
    logger.info(f"[EVENT] Conversación iniciada: {event.session_id}")


async def handle_conversation_ended(event: Event):
    """Handler para fin de conversación"""
    _metrics["conversations_ended"] += 1
    duration = event.data.get("duration_seconds", 0)
    items_ordered = event.data.get("items_ordered", 0)
    logger.info(
        f"[EVENT] Conversación terminada: {event.session_id} "
        f"(duración: {duration}s, items: {items_ordered})"
    )


async def handle_message_received(event: Event):
    """Handler para mensaje recibido"""
    _metrics["messages_received"] += 1
    text = event.data.get("text", "")[:50]
    logger.debug(f"[EVENT] Mensaje recibido: '{text}...'")


async def handle_message_sent(event: Event):
    """Handler para mensaje enviado"""
    _metrics["messages_sent"] += 1


# ============================================================
# HANDLERS DE INTENT/NLU
# ============================================================

async def handle_intent_classified(event: Event):
    """Handler para intent clasificado"""
    intent = event.data.get("intent", "unknown")
    confidence = event.data.get("confidence", 0)
    method = event.data.get("method", "unknown")

    # Actualizar contador por intent
    if intent not in _metrics["intents_classified"]:
        _metrics["intents_classified"][intent] = 0
    _metrics["intents_classified"][intent] += 1

    logger.debug(f"[EVENT] Intent: {intent} ({confidence:.2f}) via {method}")


async def handle_intent_unknown(event: Event):
    """Handler para intent no reconocido"""
    text = event.data.get("text", "")
    logger.warning(f"[EVENT] Intent UNKNOWN: '{text}'")


async def handle_intent_requires_llm(event: Event):
    """Handler cuando se requiere LLM"""
    intent = event.data.get("intent", "unknown")
    logger.info(f"[EVENT] LLM requerido para: {intent}")


# ============================================================
# HANDLERS DE PRODUCTOS
# ============================================================

async def handle_product_found(event: Event):
    """Handler para producto encontrado"""
    _metrics["products_found"] += 1
    product = event.data.get("product_name", "unknown")
    confidence = event.data.get("confidence", 0)
    logger.debug(f"[EVENT] Producto encontrado: {product} ({confidence:.2f})")


async def handle_product_not_found(event: Event):
    """Handler para producto no encontrado"""
    _metrics["products_not_found"] += 1
    query = event.data.get("query", "unknown")
    suggestions = event.data.get("suggestions", [])
    logger.info(f"[EVENT] Producto NO encontrado: '{query}' (sugerencias: {len(suggestions)})")


async def handle_product_added(event: Event):
    """Handler para producto agregado al carrito"""
    product = event.data.get("product_name", "unknown")
    quantity = event.data.get("quantity", 1)
    logger.info(f"[EVENT] Producto agregado: {quantity}x {product}")


# ============================================================
# HANDLERS DE ORDEN
# ============================================================

async def handle_order_created(event: Event):
    """Handler para orden creada"""
    _metrics["orders_created"] += 1
    order_id = event.data.get("order_id", "unknown")
    items_count = event.data.get("items_count", 0)
    logger.info(f"[EVENT] Orden creada: {order_id} ({items_count} items)")


async def handle_order_confirmed(event: Event):
    """Handler para orden confirmada"""
    _metrics["orders_confirmed"] += 1
    order_id = event.data.get("order_id", "unknown")
    total = event.data.get("total", 0)
    logger.info(f"[EVENT] Orden confirmada: {order_id} (total: ${total:.2f})")


async def handle_order_cancelled(event: Event):
    """Handler para orden cancelada"""
    order_id = event.data.get("order_id", "unknown")
    reason = event.data.get("reason", "no especificada")
    logger.info(f"[EVENT] Orden cancelada: {order_id} (razón: {reason})")


# ============================================================
# HANDLERS DE UPSELLING
# ============================================================

async def handle_upsell_offered(event: Event):
    """Handler para upsell ofrecido"""
    _metrics["upsells_offered"] += 1
    product = event.data.get("product_name", "unknown")
    logger.debug(f"[EVENT] Upsell ofrecido: {product}")


async def handle_upsell_accepted(event: Event):
    """Handler para upsell aceptado"""
    _metrics["upsells_accepted"] += 1
    product = event.data.get("product_name", "unknown")
    logger.info(f"[EVENT] Upsell ACEPTADO: {product}")


async def handle_upsell_rejected(event: Event):
    """Handler para upsell rechazado"""
    _metrics["upsells_rejected"] += 1
    product = event.data.get("product_name", "unknown")
    logger.debug(f"[EVENT] Upsell rechazado: {product}")


# ============================================================
# HANDLERS DE ERRORES Y FEEDBACK
# ============================================================

async def handle_error(event: Event):
    """Handler para errores"""
    _metrics["errors"] += 1
    error_type = event.data.get("error_type", "unknown")
    message = event.data.get("message", "")
    logger.error(f"[EVENT] ERROR: {error_type} - {message}")


async def handle_feedback_positive(event: Event):
    """Handler para feedback positivo"""
    _metrics["feedback_positive"] += 1
    logger.info(f"[EVENT] Feedback positivo recibido")


async def handle_feedback_negative(event: Event):
    """Handler para feedback negativo"""
    _metrics["feedback_negative"] += 1
    reason = event.data.get("reason", "no especificada")
    logger.warning(f"[EVENT] Feedback negativo: {reason}")


# ============================================================
# REGISTRO DE HANDLERS
# ============================================================

def register_default_handlers():
    """Registra todos los handlers por defecto"""
    bus = get_event_bus()

    # Conversación
    bus.subscribe(EventType.CONVERSATION_STARTED.value, handle_conversation_started)
    bus.subscribe(EventType.CONVERSATION_ENDED.value, handle_conversation_ended)
    bus.subscribe(EventType.MESSAGE_RECEIVED.value, handle_message_received)
    bus.subscribe(EventType.MESSAGE_SENT.value, handle_message_sent)

    # Intent
    bus.subscribe(EventType.INTENT_CLASSIFIED.value, handle_intent_classified)
    bus.subscribe(EventType.INTENT_UNKNOWN.value, handle_intent_unknown)
    bus.subscribe(EventType.INTENT_REQUIRES_LLM.value, handle_intent_requires_llm)

    # Productos
    bus.subscribe(EventType.PRODUCT_FOUND.value, handle_product_found)
    bus.subscribe(EventType.PRODUCT_NOT_FOUND.value, handle_product_not_found)
    bus.subscribe(EventType.PRODUCT_ADDED.value, handle_product_added)

    # Orden
    bus.subscribe(EventType.ORDER_CREATED.value, handle_order_created)
    bus.subscribe(EventType.ORDER_CONFIRMED.value, handle_order_confirmed)
    bus.subscribe(EventType.ORDER_CANCELLED.value, handle_order_cancelled)

    # Upselling
    bus.subscribe(EventType.UPSELL_OFFERED.value, handle_upsell_offered)
    bus.subscribe(EventType.UPSELL_ACCEPTED.value, handle_upsell_accepted)
    bus.subscribe(EventType.UPSELL_REJECTED.value, handle_upsell_rejected)

    # Errores y Feedback
    bus.subscribe(EventType.ERROR_OCCURRED.value, handle_error)
    bus.subscribe(EventType.FEEDBACK_POSITIVE.value, handle_feedback_positive)
    bus.subscribe(EventType.FEEDBACK_NEGATIVE.value, handle_feedback_negative)

    logger.info("[EVENT_BUS] Handlers por defecto registrados")


# ============================================================
# UTILIDADES PARA MÉTRICAS
# ============================================================

def get_upsell_conversion_rate() -> float:
    """Calcula tasa de conversión de upselling"""
    offered = _metrics["upsells_offered"]
    if offered == 0:
        return 0.0
    return _metrics["upsells_accepted"] / offered * 100


def get_order_completion_rate() -> float:
    """Calcula tasa de órdenes completadas"""
    created = _metrics["orders_created"]
    if created == 0:
        return 0.0
    return _metrics["orders_confirmed"] / created * 100


def get_product_find_rate() -> float:
    """Calcula tasa de productos encontrados"""
    total = _metrics["products_found"] + _metrics["products_not_found"]
    if total == 0:
        return 0.0
    return _metrics["products_found"] / total * 100


def get_summary_metrics() -> Dict[str, Any]:
    """Retorna resumen de métricas clave"""
    return {
        "conversations": {
            "started": _metrics["conversations_started"],
            "ended": _metrics["conversations_ended"],
        },
        "messages": {
            "received": _metrics["messages_received"],
            "sent": _metrics["messages_sent"],
        },
        "intents": {
            "distribution": _metrics["intents_classified"],
            "total": sum(_metrics["intents_classified"].values()),
        },
        "products": {
            "found": _metrics["products_found"],
            "not_found": _metrics["products_not_found"],
            "find_rate": f"{get_product_find_rate():.1f}%",
        },
        "orders": {
            "created": _metrics["orders_created"],
            "confirmed": _metrics["orders_confirmed"],
            "completion_rate": f"{get_order_completion_rate():.1f}%",
        },
        "upselling": {
            "offered": _metrics["upsells_offered"],
            "accepted": _metrics["upsells_accepted"],
            "rejected": _metrics["upsells_rejected"],
            "conversion_rate": f"{get_upsell_conversion_rate():.1f}%",
        },
        "feedback": {
            "positive": _metrics["feedback_positive"],
            "negative": _metrics["feedback_negative"],
        },
        "errors": _metrics["errors"],
    }
