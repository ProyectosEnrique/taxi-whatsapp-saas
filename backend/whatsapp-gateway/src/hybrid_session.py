"""
================================================================================
HYBRID SESSION MANAGER
================================================================================
Sistema de sesiones avanzado para flujo híbrido WhatsApp ↔ Web ↔ WhatsApp
================================================================================
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
from enum import Enum
import json
import logging
import uuid

logger = logging.getLogger(__name__)


# ==============================================================================
# ENUMS
# ==============================================================================

class SessionChannel(str, Enum):
    """Canal de la sesión"""
    WHATSAPP = "whatsapp"
    WEB = "web"
    HYBRID = "hybrid"  # Usuario está usando ambos


class ConversationIntent(str, Enum):
    """Intención detectada en la conversación"""
    QUICK_ORDER = "quick_order"  # Pedido rápido: "2 tacos al pastor"
    BROWSING = "browsing"  # Explorando: "qué tienen?", "opciones"
    COMPLEX_ORDER = "complex_order"  # Pedido complejo: múltiples items
    CONSULTATION = "consultation"  # Pregunta: "tienen sin gluten?"
    PROMOTION_INQUIRY = "promotion_inquiry"  # Pregunta por promos
    UNDECIDED = "undecided"  # Indeciso, necesita ayuda visual
    REPEAT_ORDER = "repeat_order"  # Cliente regular: "lo de siempre"


class DerivarReason(str, Enum):
    """Razón para derivar a web"""
    CONVERSATION_TOO_LONG = "conversation_too_long"
    BROWSING_DETECTED = "browsing_detected"
    COMPLEX_ORDER = "complex_order"
    USER_REQUESTED = "user_requested"
    NEEDS_VISUAL = "needs_visual"
    CUSTOMIZATION_NEEDED = "customization_needed"


# ==============================================================================
# HYBRID SESSION MODEL
# ==============================================================================

class ConversationMessage(BaseModel):
    """Mensaje en la conversación"""
    timestamp: datetime
    role: str  # 'user' o 'assistant'
    content: str
    intent: Optional[ConversationIntent] = None


class WebActivity(BaseModel):
    """Actividad del usuario en la web"""
    session_token: str
    visited_at: datetime
    pages_viewed: List[str] = []
    products_viewed: List[int] = []
    time_on_site: int = 0  # segundos
    cart_items: List[Dict[str, Any]] = []
    returned_to_whatsapp: bool = False
    return_timestamp: Optional[datetime] = None


class CustomerPreferences(BaseModel):
    """Preferencias del cliente (aprendizaje)"""
    favorite_products: List[int] = []
    dietary_restrictions: List[str] = []  # ["sin gluten", "vegetariano"]
    usual_order: Optional[Dict[str, Any]] = None
    preferred_time: Optional[str] = None  # "almuerzo", "cena"
    average_ticket: float = 0.0


class HybridCustomerSession(BaseModel):
    """
    Sesión híbrida mejorada para flujo WhatsApp ↔ Web
    """
    # Identificadores
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    phone: str
    customer_name: str = "Cliente"
    customer_id: Optional[str] = None  # ID en base de datos si existe

    # Canal y contexto
    current_channel: SessionChannel = SessionChannel.WHATSAPP
    restaurant_id: Optional[str] = None
    table_id: Optional[int] = None

    # Estado de conversación
    state: str = "initial"
    current_intent: Optional[ConversationIntent] = None
    conversation_history: List[ConversationMessage] = []
    message_count: int = 0

    # Carrito (sincronizado entre WhatsApp y Web)
    cart: List[Dict[str, Any]] = []
    cart_total: float = 0.0
    cart_last_updated_channel: Optional[SessionChannel] = None

    # Web tracking
    web_session: Optional[WebActivity] = None
    web_redirection_count: int = 0  # Cuántas veces se derivó a web
    last_web_url: Optional[str] = None

    # Detección de derivación
    should_redirect_to_web: bool = False
    redirect_reason: Optional[DerivarReason] = None
    redirect_url_generated: Optional[str] = None

    # Orden actual
    current_order_id: Optional[str] = None
    pending_confirmation: bool = False

    # Preferencias y aprendizaje
    preferences: CustomerPreferences = Field(default_factory=CustomerPreferences)
    is_returning_customer: bool = False
    previous_orders_count: int = 0

    # Métricas de comportamiento
    avg_response_time: float = 0.0  # Tiempo promedio de respuesta del usuario
    engagement_score: float = 0.0  # Score de engagement (0-100)

    # Promociones y recomendaciones
    promotions_shown: List[str] = []
    recommendations_shown: List[int] = []  # IDs de productos recomendados

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime = Field(
        default_factory=lambda: datetime.utcnow() + timedelta(minutes=30)
    )
    last_message_at: Optional[datetime] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }
        use_enum_values = True

    # ==========================================================================
    # MÉTODOS DE CONVERSACIÓN
    # ==========================================================================

    def add_message(
        self,
        role: str,
        content: str,
        intent: Optional[ConversationIntent] = None
    ) -> None:
        """Agregar mensaje al historial"""
        message = ConversationMessage(
            timestamp=datetime.utcnow(),
            role=role,
            content=content,
            intent=intent
        )
        self.conversation_history.append(message)
        self.message_count += 1
        self.last_message_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

        # Actualizar intención actual
        if intent:
            self.current_intent = intent

    def get_conversation_context(self, last_n: int = 5) -> List[Dict[str, str]]:
        """Obtener últimos N mensajes como contexto"""
        recent = self.conversation_history[-last_n:] if self.conversation_history else []
        return [
            {
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat()
            }
            for msg in recent
        ]

    # ==========================================================================
    # MÉTODOS DE CARRITO
    # ==========================================================================

    def add_to_cart(
        self,
        item: Dict[str, Any],
        from_channel: SessionChannel = SessionChannel.WHATSAPP
    ) -> None:
        """Agregar item al carrito"""
        self.cart.append(item)
        self.cart_total = sum(
            i.get("price", 0) * i.get("quantity", 1)
            for i in self.cart
        )
        self.cart_last_updated_channel = from_channel
        self.updated_at = datetime.utcnow()

    def sync_cart_from_web(self, web_cart: List[Dict[str, Any]]) -> None:
        """Sincronizar carrito desde web"""
        self.cart = web_cart
        self.cart_total = sum(
            i.get("price", 0) * i.get("quantity", 1)
            for i in self.cart
        )
        self.cart_last_updated_channel = SessionChannel.WEB
        self.updated_at = datetime.utcnow()

    def clear_cart(self) -> None:
        """Limpiar carrito"""
        self.cart = []
        self.cart_total = 0.0
        self.updated_at = datetime.utcnow()

    # ==========================================================================
    # MÉTODOS DE WEB TRACKING
    # ==========================================================================

    def initiate_web_session(
        self,
        session_token: str,
        reason: DerivarReason
    ) -> None:
        """Iniciar sesión web"""
        self.web_session = WebActivity(
            session_token=session_token,
            visited_at=datetime.utcnow()
        )
        self.current_channel = SessionChannel.HYBRID
        self.should_redirect_to_web = True
        self.redirect_reason = reason
        self.web_redirection_count += 1
        self.updated_at = datetime.utcnow()

    def update_web_activity(
        self,
        pages_viewed: List[str] = None,
        products_viewed: List[int] = None,
        cart_items: List[Dict[str, Any]] = None
    ) -> None:
        """Actualizar actividad en web"""
        if not self.web_session:
            return

        if pages_viewed:
            self.web_session.pages_viewed.extend(pages_viewed)
        if products_viewed:
            self.web_session.products_viewed.extend(products_viewed)
        if cart_items is not None:
            self.web_session.cart_items = cart_items
            self.sync_cart_from_web(cart_items)

        self.updated_at = datetime.utcnow()

    def mark_return_from_web(self) -> None:
        """Marcar retorno desde web a WhatsApp"""
        if self.web_session:
            self.web_session.returned_to_whatsapp = True
            self.web_session.return_timestamp = datetime.utcnow()
            self.web_session.time_on_site = int(
                (datetime.utcnow() - self.web_session.visited_at).total_seconds()
            )

        self.current_channel = SessionChannel.WHATSAPP
        self.should_redirect_to_web = False
        self.updated_at = datetime.utcnow()

    # ==========================================================================
    # DETECCIÓN DE INTENCIÓN
    # ==========================================================================

    def should_derivar_to_web(self) -> tuple[bool, Optional[DerivarReason]]:
        """
        Determinar si se debe derivar a web.

        Returns:
            (should_redirect, reason)
        """
        # Conversación muy larga (>5 mensajes sin orden)
        if self.message_count > 5 and not self.current_order_id:
            if self.current_intent in [
                ConversationIntent.BROWSING,
                ConversationIntent.UNDECIDED
            ]:
                return True, DerivarReason.CONVERSATION_TOO_LONG

        # Detectado intent de browsing
        if self.current_intent == ConversationIntent.BROWSING:
            return True, DerivarReason.BROWSING_DETECTED

        # Carrito complejo (>3 items distintos)
        if len(self.cart) > 3:
            return True, DerivarReason.COMPLEX_ORDER

        # Usuario indeciso
        if self.current_intent == ConversationIntent.UNDECIDED:
            return True, DerivarReason.NEEDS_VISUAL

        # Usuario solicitó ver menú/fotos
        if self.conversation_history:
            last_msg = self.conversation_history[-1].content.lower()
            if any(word in last_msg for word in ["ver", "mostrar", "foto", "imagen", "menú completo"]):
                return True, DerivarReason.USER_REQUESTED

        return False, None

    # ==========================================================================
    # MÉTRICAS
    # ==========================================================================

    def calculate_engagement_score(self) -> float:
        """
        Calcular score de engagement (0-100)

        Factores:
        - Número de mensajes
        - Tiempo de respuesta
        - Items en carrito
        - Visitas a web
        """
        score = 0.0

        # Mensajes (max 30 puntos)
        score += min(self.message_count * 5, 30)

        # Carrito (max 25 puntos)
        score += min(len(self.cart) * 8, 25)

        # Interacción web (max 20 puntos)
        if self.web_session:
            score += min(len(self.web_session.pages_viewed) * 4, 20)

        # Cliente recurrente (15 puntos)
        if self.is_returning_customer:
            score += 15

        # Orden confirmada (10 puntos)
        if self.current_order_id:
            score += 10

        self.engagement_score = min(score, 100.0)
        return self.engagement_score

    def is_expired(self) -> bool:
        """Verificar si la sesión expiró"""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at

    def refresh_ttl(self, minutes: int = 30) -> None:
        """Refrescar tiempo de expiración"""
        self.updated_at = datetime.utcnow()
        self.expires_at = datetime.utcnow() + timedelta(minutes=minutes)


# ==============================================================================
# EJEMPLO DE USO
# ==============================================================================

if __name__ == "__main__":
    # Crear sesión
    session = HybridCustomerSession(
        phone="+5215551234567",
        customer_name="Juan Pérez"
    )

    # Simular conversación
    session.add_message("user", "Hola, qué tienen?", ConversationIntent.BROWSING)
    session.add_message("assistant", "Tenemos tacos, hamburguesas...")

    # Verificar si derivar
    should_redirect, reason = session.should_derivar_to_web()
    print(f"¿Derivar a web? {should_redirect} - Razón: {reason}")

    # Iniciar sesión web
    if should_redirect:
        session.initiate_web_session(
            session_token="web_abc123",
            reason=reason
        )

    # Usuario regresa de web con carrito
    web_cart = [
        {"product_id": 15, "name": "Tacos al Pastor", "quantity": 3, "price": 110.0}
    ]
    session.sync_cart_from_web(web_cart)
    session.mark_return_from_web()

    # Calcular engagement
    engagement = session.calculate_engagement_score()
    print(f"Engagement: {engagement}%")

    print(f"\nSesión: {session.dict()}")
