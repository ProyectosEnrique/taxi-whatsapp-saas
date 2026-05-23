"""
================================================================================
ORDERS ROUTER - Gestión de Pedidos
================================================================================
Endpoints para crear, listar, rastrear y cancelar pedidos
================================================================================
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
from datetime import datetime, timedelta
import logging
import random
import string

from ..database import get_db
from ..models.order import Order, OrderItem, OrderStatus, PaymentMethod
from ..models.user import User
from ..models.product import Product
from ..schemas.order import (
    CreateOrderRequest,
    OrderResponse,
    OrderSummaryResponse,
    CancelOrderRequest,
    OrderTrackingResponse
)
from ..routers.auth import get_current_user
from ..socketio_server import broadcast_new_order

logger = logging.getLogger(__name__)

router = APIRouter()


# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

def generate_order_id() -> str:
    """Generar ID único de pedido (ORD-XXXXXX)"""
    random_part = ''.join(random.choices(string.digits, k=6))
    return f"ORD-{random_part}"


def calculate_delivery_fee(subtotal: float, tenant_id: str) -> float:
    """
    Calcular costo de envío basado en subtotal.

    TODO: Hacer esto configurable por tenant
    """
    if subtotal >= 300:
        return 0.0  # Envío gratis sobre $300
    elif subtotal >= 200:
        return 30.0  # $30 entre $200-$300
    else:
        return 50.0  # $50 bajo $200


def calculate_estimated_delivery(tenant_id: str) -> datetime:
    """
    Calcular tiempo estimado de entrega.

    TODO: Hacer esto dinámico basado en ubicación y hora
    """
    # Por ahora: 45 minutos desde ahora
    return datetime.utcnow() + timedelta(minutes=45)


# ==============================================================================
# ENDPOINTS
# ==============================================================================

@router.post(
    "",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear nuevo pedido"
)
async def create_order(
    data: CreateOrderRequest,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    Crear un nuevo pedido.

    Si el usuario está autenticado, usa su información.
    Si no, requiere customer_name, customer_phone en el request.
    """
    logger.info(f"Creando pedido para tenant: {data.tenant_id}")

    # Determinar información del cliente
    if current_user:
        customer_id = current_user.id
        customer_name = current_user.name
        customer_phone = current_user.phone
        customer_email = current_user.email
    else:
        # Cliente no autenticado (guest checkout)
        if not data.customer_name or not data.customer_phone:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Se requiere customer_name y customer_phone para checkout sin cuenta"
            )

        customer_id = None  # NULL para guests
        customer_name = data.customer_name
        customer_phone = data.customer_phone
        customer_email = data.customer_email

    # Validar y calcular items
    subtotal = 0.0
    order_items_data = []

    for item_data in data.items:
        # Buscar producto
        product = db.query(Product).filter(
            Product.id == item_data.product_id,
            Product.tenant_id == data.tenant_id
        ).first()

        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Producto {item_data.product_id} no encontrado"
            )

        if not product.is_available:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Producto '{product.name}' no está disponible"
            )

        # Calcular subtotal del item
        item_subtotal = product.price * item_data.quantity
        subtotal += item_subtotal

        order_items_data.append({
            "product": product,
            "quantity": item_data.quantity,
            "unit_price": product.price,
            "subtotal": item_subtotal,
            "customizations": item_data.customizations,
            "notes": item_data.notes
        })

    # Aplicar descuento si hay promo code
    discount = 0.0
    if data.promo_code:
        # TODO: Validar promo code real desde tabla promotions
        # Por ahora, descuento fijo del 10%
        discount = subtotal * 0.10

    # Calcular delivery fee
    delivery_fee = calculate_delivery_fee(subtotal, data.tenant_id)

    # Calcular total
    total = subtotal - discount + delivery_fee

    # Generar order ID único
    order_id = generate_order_id()
    while db.query(Order).filter(Order.order_id == order_id).first():
        order_id = generate_order_id()

    # Crear pedido
    new_order = Order(
        order_id=order_id,
        tenant_id=data.tenant_id,
        customer_id=customer_id,
        customer_name=customer_name,
        customer_phone=customer_phone,
        customer_email=customer_email,
        delivery_address=data.delivery_address.dict(),
        subtotal=subtotal,
        discount=discount,
        delivery_fee=delivery_fee,
        total=total,
        payment_method=PaymentMethod(data.payment_method),
        payment_status="pending",
        status=OrderStatus.PENDING,
        promo_code=data.promo_code,
        notes=data.notes,
        estimated_delivery_time=calculate_estimated_delivery(data.tenant_id)
    )

    db.add(new_order)
    db.flush()  # Para obtener el ID

    # Crear order items
    for item_data in order_items_data:
        order_item = OrderItem(
            order_id=new_order.id,
            product_id=item_data["product"].id,
            product_name=item_data["product"].name,
            product_image=item_data["product"].image_url,
            quantity=item_data["quantity"],
            unit_price=item_data["unit_price"],
            subtotal=item_data["subtotal"],
            customizations=item_data["customizations"],
            notes=item_data["notes"]
        )
        db.add(order_item)

    db.commit()
    db.refresh(new_order)

    logger.info(f"Pedido creado: {new_order.order_id} - Total: ${total}")

    # Notificar a admins del tenant vía Socket.IO
    try:
        await broadcast_new_order(
            data.tenant_id,
            {
                "order_id": new_order.order_id,
                "customer_name": customer_name,
                "total": total,
                "items_count": len(order_items_data),
                "created_at": new_order.created_at.isoformat() if new_order.created_at else datetime.utcnow().isoformat()
            }
        )
    except Exception as e:
        logger.error(f"Error al emitir evento Socket.IO: {e}")

    # TODO: Enviar notificación por WhatsApp al cliente

    return OrderResponse.from_orm(new_order)


@router.get(
    "",
    response_model=List[OrderSummaryResponse],
    summary="Listar pedidos del usuario"
)
async def get_orders(
    status_filter: Optional[str] = Query(None, description="Filtrar por estado"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Obtener lista de pedidos del usuario autenticado.

    Puede filtrar por estado: pending, confirmed, preparing, in_transit, delivered, cancelled
    """
    logger.info(f"Listando pedidos de usuario: {current_user.id}")

    # Query base
    query = db.query(Order).filter(Order.customer_id == current_user.id)

    # Filtrar por estado si se proporciona
    if status_filter:
        try:
            status_enum = OrderStatus(status_filter)
            query = query.filter(Order.status == status_enum)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Estado inválido: {status_filter}"
            )

    # Ordenar por más reciente primero
    query = query.order_by(desc(Order.created_at))

    # Paginación
    orders = query.offset(offset).limit(limit).all()

    # Convertir a response con items_count
    results = []
    for order in orders:
        order_dict = order.to_dict()
        order_dict["items_count"] = len(order.items)
        results.append(OrderSummaryResponse(**order_dict))

    logger.info(f"Encontrados {len(results)} pedidos")

    return results


@router.get(
    "/{order_id}",
    response_model=OrderResponse,
    summary="Obtener detalle de un pedido"
)
async def get_order(
    order_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obtener información completa de un pedido específico"""

    logger.info(f"Consultando pedido: {order_id}")

    order = db.query(Order).filter(
        Order.order_id == order_id,
        Order.customer_id == current_user.id,
        Order.tenant_id == current_user.tenant_id  # SECURITY: Verificar tenant
    ).first()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pedido no encontrado"
        )

    return OrderResponse.from_orm(order)


@router.put(
    "/{order_id}/cancel",
    summary="Cancelar un pedido"
)
async def cancel_order(
    order_id: str,
    data: CancelOrderRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Cancelar un pedido.

    Solo se puede cancelar si está en estado PENDING o CONFIRMED.
    """
    logger.info(f"Cancelando pedido: {order_id}")

    order = db.query(Order).filter(
        Order.order_id == order_id,
        Order.customer_id == current_user.id,
        Order.tenant_id == current_user.tenant_id  # SECURITY: Verificar tenant
    ).first()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pedido no encontrado"
        )

    # Verificar que se pueda cancelar
    if order.status not in [OrderStatus.PENDING, OrderStatus.CONFIRMED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se puede cancelar un pedido en estado '{order.status.value}'"
        )

    # Cancelar
    order.status = OrderStatus.CANCELLED
    order.cancelled_at = datetime.utcnow()
    order.cancellation_reason = data.reason or "Cancelado por el cliente"

    db.commit()

    logger.info(f"Pedido cancelado: {order_id}")

    # TODO: Notificar a la tienda de la cancelación

    return {
        "success": True,
        "message": "Pedido cancelado exitosamente",
        "order_id": order_id
    }


@router.get(
    "/{order_id}/track",
    response_model=OrderTrackingResponse,
    summary="Rastrear pedido en tiempo real"
)
async def track_order(
    order_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Obtener información de tracking del pedido.

    Incluye estado actual, historial de cambios, y ubicación del repartidor.
    """
    logger.info(f"Tracking pedido: {order_id}")

    order = db.query(Order).filter(
        Order.order_id == order_id,
        Order.customer_id == current_user.id,
        Order.tenant_id == current_user.tenant_id  # SECURITY: Verificar tenant
    ).first()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pedido no encontrado"
        )

    # Construir historial de estados
    # TODO: Implementar tabla de order_status_history para tracking real
    status_history = [
        {
            "status": OrderStatus.PENDING.value,
            "timestamp": order.created_at.isoformat(),
            "description": "Pedido recibido"
        }
    ]

    if order.status in [OrderStatus.CONFIRMED, OrderStatus.PREPARING, OrderStatus.READY,
                        OrderStatus.IN_TRANSIT, OrderStatus.DELIVERED]:
        status_history.append({
            "status": OrderStatus.CONFIRMED.value,
            "timestamp": order.created_at.isoformat(),
            "description": "Pedido confirmado"
        })

    if order.status in [OrderStatus.PREPARING, OrderStatus.READY,
                        OrderStatus.IN_TRANSIT, OrderStatus.DELIVERED]:
        status_history.append({
            "status": OrderStatus.PREPARING.value,
            "timestamp": order.updated_at.isoformat() if order.updated_at else order.created_at.isoformat(),
            "description": "Preparando tu pedido"
        })

    if order.status in [OrderStatus.IN_TRANSIT, OrderStatus.DELIVERED]:
        status_history.append({
            "status": OrderStatus.IN_TRANSIT.value,
            "timestamp": order.updated_at.isoformat() if order.updated_at else order.created_at.isoformat(),
            "description": "En camino"
        })

    if order.status == OrderStatus.DELIVERED:
        status_history.append({
            "status": OrderStatus.DELIVERED.value,
            "timestamp": order.delivered_at.isoformat() if order.delivered_at else order.updated_at.isoformat(),
            "description": "Entregado"
        })

    return OrderTrackingResponse(
        order_id=order.order_id,
        status=order.status.value,
        status_history=status_history,
        estimated_delivery_time=order.estimated_delivery_time,
        driver_name=order.driver_name,
        driver_phone=order.driver_phone,
        current_location=None  # TODO: Implementar GPS del repartidor
    )
