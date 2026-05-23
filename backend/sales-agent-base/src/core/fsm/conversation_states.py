# ============================================================
# ESTADOS DE CONVERSACIÓN - FSM
# ============================================================
# Define los estados posibles del agente de ventas
# ============================================================

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ConversationState(Enum):
    """Estados posibles de la conversación"""

    # Estados principales
    INICIO = "inicio"
    BIENVENIDA = "bienvenida"
    EXPLORACION = "exploracion"
    MICRO_EMBUDO = "micro_embudo"
    PRODUCTO_SELECCIONADO = "producto_seleccionado"
    UPSELL = "upsell"
    CROSS_SELL = "cross_sell"
    CONFIRMACION = "confirmacion"
    CIERRE = "cierre"

    # Estados auxiliares
    PREGUNTA_DETALLE = "pregunta_detalle"
    MODIFICACION_PEDIDO = "modificacion_pedido"
    ERROR = "error"

    # Estados de servicio (solicitudes al mesero)
    SERVICE_REQUESTED = "service_requested"


@dataclass
class ProductSelection:
    """Representa un producto seleccionado"""
    product_id: int
    name: str
    price: float
    quantity: int = 1
    extras: List[str] = field(default_factory=list)
    notes: str = ""

    @property
    def total(self) -> float:
        return self.price * self.quantity


@dataclass
class StateContext:
    """Contexto completo del estado de la conversación"""

    # Estado actual
    state: ConversationState = ConversationState.INICIO
    previous_state: Optional[ConversationState] = None

    # Contexto de categoría (micro-embudo)
    active_category: Optional[str] = None
    active_category_products: List[Dict] = field(default_factory=list)
    category_timestamp: Optional[datetime] = None

    # Producto mencionado por el cliente
    mentioned_product: Optional[str] = None
    mentioned_product_data: Optional[Dict] = None

    # Pedido actual
    order_items: List[ProductSelection] = field(default_factory=list)
    order_total: float = 0.0

    # Contadores de intentos
    upsell_attempts: int = 0
    crosssell_attempts: int = 0
    clarification_attempts: int = 0

    # Flags de upsell/crosssell
    upsell_offered: bool = False
    crosssell_offered: bool = False

    # Último upsell/crosssell ofrecido (para no repetir)
    last_upsell_offered: Optional[str] = None
    last_crosssell_offered: Optional[str] = None

    # Preferencias detectadas del cliente
    detected_preferences: Dict[str, Any] = field(default_factory=dict)
    rejected_suggestions: List[str] = field(default_factory=list)

    # Historial de la conversación
    conversation_history: List[Dict] = field(default_factory=list)

    # Solicitudes de servicio pendientes (más salsa, servilletas, etc.)
    pending_service_requests: List[Dict] = field(default_factory=list)

    # Timestamps
    session_start: datetime = field(default_factory=datetime.now)
    last_interaction: datetime = field(default_factory=datetime.now)

    # Métrica de la conversación
    metrics: Dict[str, Any] = field(default_factory=lambda: {
        'upsells_offered': 0,
        'upsells_accepted': 0,
        'crosssells_offered': 0,
        'crosssells_accepted': 0,
        'total_interactions': 0
    })

    def set_state(self, new_state: ConversationState) -> None:
        """Cambia el estado guardando el anterior"""
        self.previous_state = self.state
        self.state = new_state
        logger.info(f"[FSM] Estado: {self.previous_state.value} → {new_state.value}")

    def set_active_category(self, category: str, products: List[Dict]) -> None:
        """Establece la categoría activa (entra al micro-embudo)"""
        self.active_category = category
        self.active_category_products = products
        self.category_timestamp = datetime.now()
        logger.info(f"[FSM] Micro-embudo activo: {category} ({len(products)} productos)")

    def clear_active_category(self) -> None:
        """Limpia la categoría activa (sale del micro-embudo)"""
        old_category = self.active_category
        self.active_category = None
        self.active_category_products = []
        self.category_timestamp = None
        self.mentioned_product = None
        self.mentioned_product_data = None
        if old_category:
            logger.info(f"[FSM] Saliendo de micro-embudo: {old_category}")

    def is_category_active(self, max_age_seconds: int = 300) -> bool:
        """Verifica si hay una categoría activa y no ha expirado"""
        if not self.active_category or not self.category_timestamp:
            return False

        age = (datetime.now() - self.category_timestamp).total_seconds()
        if age > max_age_seconds:
            logger.info(f"[FSM] Categoría expirada: {self.active_category} (edad: {age}s)")
            self.clear_active_category()
            return False

        return True

    def set_mentioned_product(self, product_name: str, product_data: Dict) -> None:
        """Establece el producto mencionado por el cliente"""
        self.mentioned_product = product_name
        self.mentioned_product_data = product_data
        logger.info(f"[FSM] Producto mencionado: {product_name}")

    def add_to_order(self, product: ProductSelection) -> None:
        """Agrega un producto al pedido"""
        self.order_items.append(product)
        self.order_total = sum(item.total for item in self.order_items)
        logger.info(f"[FSM] Agregado al pedido: {product.name} x{product.quantity} (Total: ${self.order_total})")

    def remove_from_order(self, product_name: str) -> bool:
        """Elimina un producto del pedido"""
        for i, item in enumerate(self.order_items):
            if item.name.lower() == product_name.lower():
                removed = self.order_items.pop(i)
                self.order_total = sum(item.total for item in self.order_items)
                logger.info(f"[FSM] Eliminado del pedido: {removed.name}")
                return True
        return False

    def increment_upsell_attempts(self) -> int:
        """Incrementa contador de intentos de upsell"""
        self.upsell_attempts += 1
        self.metrics['upsells_offered'] += 1
        return self.upsell_attempts

    def increment_crosssell_attempts(self) -> int:
        """Incrementa contador de intentos de cross-sell"""
        self.crosssell_attempts += 1
        self.metrics['crosssells_offered'] += 1
        return self.crosssell_attempts

    def record_upsell_accepted(self) -> None:
        """Registra upsell aceptado"""
        self.metrics['upsells_accepted'] += 1

    def record_crosssell_accepted(self) -> None:
        """Registra cross-sell aceptado"""
        self.metrics['crosssells_accepted'] += 1

    def add_rejected_suggestion(self, suggestion: str) -> None:
        """Agrega una sugerencia rechazada"""
        if suggestion not in self.rejected_suggestions:
            self.rejected_suggestions.append(suggestion)

    def add_service_request(self, request_type: str, description: str, table_id: int = None) -> Dict:
        """Agrega una solicitud de servicio (más salsa, servilletas, etc.)"""
        service_request = {
            'id': len(self.pending_service_requests) + 1,
            'type': request_type,
            'description': description,
            'table_id': table_id,
            'status': 'pending',
            'created_at': datetime.now().isoformat()
        }
        self.pending_service_requests.append(service_request)
        logger.info(f"[FSM] Solicitud de servicio agregada: {request_type} - {description}")
        return service_request

    def add_to_history(self, role: str, message: str, intent: str = None) -> None:
        """Agrega mensaje al historial"""
        self.conversation_history.append({
            'role': role,
            'message': message,
            'intent': intent,
            'timestamp': datetime.now().isoformat(),
            'state': self.state.value
        })
        self.last_interaction = datetime.now()
        self.metrics['total_interactions'] += 1

    def has_beverage(self) -> bool:
        """Verifica si el pedido tiene bebida"""
        beverage_keywords = ['agua', 'refresco', 'coca', 'limonada', 'cerveza', 'jamaica', 'horchata', 'margarita', 'michelada']
        for item in self.order_items:
            if any(kw in item.name.lower() for kw in beverage_keywords):
                return True
        return False

    def has_main_dish(self) -> bool:
        """Verifica si el pedido tiene plato principal"""
        main_keywords = ['hamburguesa', 'taco', 'enchilada', 'costilla', 'arrachera', 'pechuga']
        for item in self.order_items:
            if any(kw in item.name.lower() for kw in main_keywords):
                return True
        return False

    def has_side(self) -> bool:
        """Verifica si el pedido tiene complemento"""
        side_keywords = ['papas', 'aros', 'elote', 'guacamole', 'arroz', 'frijoles']
        for item in self.order_items:
            if any(kw in item.name.lower() for kw in side_keywords):
                return True
        return False

    def get_order_summary(self) -> str:
        """Obtiene resumen del pedido"""
        if not self.order_items:
            return "Pedido vacío"

        items_str = ", ".join([f"{item.quantity}x {item.name}" for item in self.order_items])
        return f"{items_str}. Total: ${self.order_total:.2f}"

    def reset_for_new_order(self) -> None:
        """Reinicia el contexto para un nuevo pedido"""
        self.state = ConversationState.INICIO
        self.previous_state = None
        self.clear_active_category()
        self.order_items = []
        self.order_total = 0.0
        self.upsell_attempts = 0
        self.crosssell_attempts = 0
        self.clarification_attempts = 0
        self.upsell_offered = False
        self.crosssell_offered = False
        self.last_upsell_offered = None
        self.last_crosssell_offered = None
        self.rejected_suggestions = []
        self.conversation_history = []
        logger.info("[FSM] Contexto reiniciado para nuevo pedido")

    def to_dict(self) -> Dict:
        """Convierte el contexto a diccionario (para serialización)"""
        return {
            'state': self.state.value,
            'active_category': self.active_category,
            'order_items': [
                {
                    'name': item.name,
                    'price': item.price,
                    'quantity': item.quantity,
                    'total': item.total
                }
                for item in self.order_items
            ],
            'order_total': self.order_total,
            'upsell_attempts': self.upsell_attempts,
            'crosssell_attempts': self.crosssell_attempts,
            'metrics': self.metrics
        }
