"""
================================================================================
ORDER SCHEMAS
================================================================================
Schemas Pydantic para pedidos
================================================================================
"""

from pydantic import BaseModel, validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class OrderStatusEnum(str, Enum):
    """Estados del pedido"""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PREPARING = "preparing"
    READY = "ready"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class PaymentMethodEnum(str, Enum):
    """Métodos de pago"""
    CASH = "cash"
    CARD = "card"
    TRANSFER = "transfer"


class OrderItemCreate(BaseModel):
    """Item del pedido al crear"""
    product_id: int
    quantity: int
    customizations: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None

    @validator('quantity')
    def validate_quantity(cls, v):
        if v < 1:
            raise ValueError('La cantidad debe ser mayor a 0')
        return v


class OrderItemResponse(BaseModel):
    """Response de item del pedido"""
    id: int
    product_id: int
    product_name: str
    product_image: Optional[str]
    quantity: int
    unit_price: float
    subtotal: float
    customizations: Optional[Dict[str, Any]]
    notes: Optional[str]

    class Config:
        from_attributes = True


class DeliveryAddress(BaseModel):
    """Dirección de entrega"""
    street: str
    neighborhood: str
    city: str
    state: str
    zip_code: Optional[str] = None
    reference: Optional[str] = None


class CreateOrderRequest(BaseModel):
    """Request para crear un pedido"""
    tenant_id: str
    items: List[OrderItemCreate]
    delivery_address: DeliveryAddress
    payment_method: PaymentMethodEnum
    promo_code: Optional[str] = None
    notes: Optional[str] = None

    # Info del cliente (si no está autenticado)
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    customer_email: Optional[str] = None

    @validator('items')
    def validate_items(cls, v):
        if not v or len(v) == 0:
            raise ValueError('El pedido debe tener al menos un item')
        return v


class OrderResponse(BaseModel):
    """Response de pedido completo"""
    id: int
    order_id: str
    tenant_id: str
    customer_id: int
    customer_name: str
    customer_phone: str
    customer_email: Optional[str]
    delivery_address: Dict[str, Any]
    items: List[OrderItemResponse]
    subtotal: float
    discount: float
    delivery_fee: float
    total: float
    payment_method: str
    payment_status: str
    status: str
    promo_code: Optional[str]
    notes: Optional[str]
    estimated_delivery_time: Optional[datetime]
    driver_name: Optional[str]
    driver_phone: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    delivered_at: Optional[datetime]
    cancelled_at: Optional[datetime]
    cancellation_reason: Optional[str]

    class Config:
        from_attributes = True


class OrderSummaryResponse(BaseModel):
    """Response resumido de pedido (para listas)"""
    id: int
    order_id: str
    tenant_id: str
    customer_name: str
    status: str
    total: float
    created_at: datetime
    items_count: int

    class Config:
        from_attributes = True


class CancelOrderRequest(BaseModel):
    """Request para cancelar pedido"""
    reason: Optional[str] = None


class OrderTrackingResponse(BaseModel):
    """Response de tracking del pedido"""
    order_id: str
    status: str
    status_history: List[Dict[str, Any]]  # Timeline de cambios de estado
    estimated_delivery_time: Optional[datetime]
    driver_name: Optional[str]
    driver_phone: Optional[str]
    current_location: Optional[Dict[str, Any]] = None  # GPS del repartidor (futuro)

    class Config:
        from_attributes = True
