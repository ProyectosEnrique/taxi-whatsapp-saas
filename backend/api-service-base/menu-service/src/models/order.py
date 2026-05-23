"""
================================================================================
ORDER MODEL
================================================================================
Modelos para gestión de pedidos
================================================================================
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Text, JSON, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
from ..database import Base


class OrderStatus(str, enum.Enum):
    """Estados del pedido"""
    PENDING = "pending"              # Pedido recibido
    CONFIRMED = "confirmed"          # Confirmado por tienda
    PREPARING = "preparing"          # En preparación
    READY = "ready"                  # Listo para envío
    IN_TRANSIT = "in_transit"        # En camino
    DELIVERED = "delivered"          # Entregado
    CANCELLED = "cancelled"          # Cancelado


class PaymentMethod(str, enum.Enum):
    """Métodos de pago"""
    CASH = "cash"                    # Efectivo
    CARD = "card"                    # Tarjeta
    TRANSFER = "transfer"            # Transferencia


class Order(Base):
    """Pedido del cliente"""

    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(String(100), unique=True, nullable=False, index=True)  # ORD-XXXXXX
    tenant_id = Column(String(100), nullable=False, index=True)

    # Cliente
    customer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    customer_name = Column(String(200), nullable=False)
    customer_phone = Column(String(20), nullable=False)
    customer_email = Column(String(200), nullable=True)

    # Dirección de entrega
    delivery_address = Column(JSON, nullable=False)  # {street, neighborhood, city, etc.}

    # Items del pedido (se guardan en OrderItem)
    # Ver relación items abajo

    # Montos
    subtotal = Column(Float, nullable=False)
    discount = Column(Float, default=0.0)
    delivery_fee = Column(Float, default=0.0)
    total = Column(Float, nullable=False)

    # Pago
    payment_method = Column(Enum(PaymentMethod), nullable=False)
    payment_status = Column(String(50), default="pending")  # pending, paid, failed

    # Estado del pedido
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING, nullable=False, index=True)

    # Promoción aplicada
    promo_code = Column(String(50), nullable=True)

    # Notas adicionales
    notes = Column(Text, nullable=True)

    # Tracking info
    estimated_delivery_time = Column(DateTime(timezone=True), nullable=True)
    driver_name = Column(String(200), nullable=True)
    driver_phone = Column(String(20), nullable=True)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    cancellation_reason = Column(Text, nullable=True)

    # Relaciones
    customer = relationship("User", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    review = relationship("Review", back_populates="order", uselist=False)

    def __repr__(self):
        return f"<Order {self.order_id}>"

    def to_dict(self):
        """Convertir a diccionario"""
        return {
            "id": self.id,
            "order_id": self.order_id,
            "tenant_id": self.tenant_id,
            "customer_id": self.customer_id,
            "customer_name": self.customer_name,
            "customer_phone": self.customer_phone,
            "customer_email": self.customer_email,
            "delivery_address": self.delivery_address,
            "items": [item.to_dict() for item in self.items] if self.items else [],
            "subtotal": self.subtotal,
            "discount": self.discount,
            "delivery_fee": self.delivery_fee,
            "total": self.total,
            "payment_method": self.payment_method.value if self.payment_method else None,
            "payment_status": self.payment_status,
            "status": self.status.value if self.status else None,
            "promo_code": self.promo_code,
            "notes": self.notes,
            "estimated_delivery_time": self.estimated_delivery_time.isoformat() if self.estimated_delivery_time else None,
            "driver_name": self.driver_name,
            "driver_phone": self.driver_phone,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "delivered_at": self.delivered_at.isoformat() if self.delivered_at else None,
            "cancelled_at": self.cancelled_at.isoformat() if self.cancelled_at else None,
            "cancellation_reason": self.cancellation_reason
        }


class OrderItem(Base):
    """Item individual de un pedido"""

    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)

    # Producto
    product_id = Column(Integer, nullable=False)
    product_name = Column(String(200), nullable=False)
    product_image = Column(String(500), nullable=True)

    # Cantidad y precio
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)
    subtotal = Column(Float, nullable=False)  # quantity * unit_price

    # Customizaciones (ej: sin cebolla, extra queso)
    customizations = Column(JSON, nullable=True)

    # Notas especiales para este item
    notes = Column(Text, nullable=True)

    # Relaciones
    order = relationship("Order", back_populates="items")

    def __repr__(self):
        return f"<OrderItem {self.product_name} x{self.quantity}>"

    def to_dict(self):
        """Convertir a diccionario"""
        return {
            "id": self.id,
            "product_id": self.product_id,
            "product_name": self.product_name,
            "product_image": self.product_image,
            "quantity": self.quantity,
            "unit_price": self.unit_price,
            "subtotal": self.subtotal,
            "customizations": self.customizations,
            "notes": self.notes
        }
