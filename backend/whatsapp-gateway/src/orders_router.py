# ============================================================================
# ORDERS ROUTER - Endpoints para Gestión de Órdenes
# ============================================================================

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List, Optional
from datetime import datetime, timedelta

from src.database import get_db
from src.orm_models import OrderORM, RestaurantORM, CustomerORM
from src.models_multitenant import (
    Order, OrderUpdate, OrderStatus,
    SuccessResponse
)
from src.auth import check_restaurant_access, allow_all_staff

router = APIRouter(prefix="/api/v1/restaurants/{restaurant_id}/orders", tags=["Orders"])


# ============================================================================
# GET ALL ORDERS
# ============================================================================

@router.get("", response_model=List[Order])
async def get_orders(
    restaurant_id: str,
    status: Optional[OrderStatus] = None,
    customer_phone: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    skip: int = 0,
    limit: int = 100,
    restaurant: RestaurantORM = Depends(check_restaurant_access),
    current_user = Depends(allow_all_staff),
    db: Session = Depends(get_db)
):
    """
    Listar órdenes del restaurante.

    Filtros opcionales:
    - status: Filtrar por estado
    - customer_phone: Filtrar por cliente
    - date_from: Desde fecha
    - date_to: Hasta fecha
    """
    query = db.query(OrderORM).filter(
        OrderORM.restaurant_id == restaurant_id
    )

    if status:
        query = query.filter(OrderORM.status == status.value)

    if customer_phone:
        query = query.filter(OrderORM.customer_phone == customer_phone)

    if date_from:
        query = query.filter(OrderORM.created_at >= date_from)

    if date_to:
        query = query.filter(OrderORM.created_at <= date_to)

    orders = query.order_by(desc(OrderORM.created_at)).offset(skip).limit(limit).all()

    return [Order.from_orm(o) for o in orders]


# ============================================================================
# GET ORDER BY ID
# ============================================================================

@router.get("/{order_id}", response_model=Order)
async def get_order(
    restaurant_id: str,
    order_id: str,
    restaurant: RestaurantORM = Depends(check_restaurant_access),
    current_user = Depends(allow_all_staff),
    db: Session = Depends(get_db)
):
    """
    Obtener detalles de una orden específica.
    """
    order = db.query(OrderORM).filter(
        OrderORM.restaurant_id == restaurant_id,
        OrderORM.order_id == order_id
    ).first()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )

    return Order.from_orm(order)


# ============================================================================
# UPDATE ORDER STATUS
# ============================================================================

@router.patch("/{order_id}", response_model=Order)
async def update_order(
    restaurant_id: str,
    order_id: str,
    order_update: OrderUpdate,
    restaurant: RestaurantORM = Depends(check_restaurant_access),
    current_user = Depends(allow_all_staff),
    db: Session = Depends(get_db)
):
    """
    Actualizar estado de la orden.

    Estados posibles:
    - pending: Pendiente
    - confirmed: Confirmada
    - preparing: En preparación
    - ready: Lista
    - completed: Completada
    - cancelled: Cancelada
    """
    order = db.query(OrderORM).filter(
        OrderORM.restaurant_id == restaurant_id,
        OrderORM.order_id == order_id
    ).first()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )

    # Actualizar campos
    update_data = order_update.dict(exclude_unset=True)

    for field, value in update_data.items():
        if hasattr(order, field):
            # Convertir enum a string si es necesario
            if field == "status" and hasattr(value, "value"):
                value = value.value
            elif field == "payment_status" and hasattr(value, "value"):
                value = value.value

            setattr(order, field, value)

            # Actualizar timestamps automáticos
            if field == "status":
                if value == "completed":
                    order.completed_at = datetime.utcnow()
                elif value == "cancelled":
                    order.cancelled_at = datetime.utcnow()
                elif value == "confirmed" and not order.confirmed_at:
                    order.confirmed_at = datetime.utcnow()

    db.commit()
    db.refresh(order)

    # TODO: Enviar notificación por WhatsApp al cliente
    # if order.status in ["ready", "completed"]:
    #     send_whatsapp_notification(order)

    return Order.from_orm(order)


# ============================================================================
# GET ORDERS STATS
# ============================================================================

@router.get("/-/stats")
async def get_orders_stats(
    restaurant_id: str,
    period: str = Query("today", regex="^(today|week|month|year)$"),
    restaurant: RestaurantORM = Depends(check_restaurant_access),
    current_user = Depends(allow_all_staff),
    db: Session = Depends(get_db)
):
    """
    Obtener estadísticas de órdenes.

    Períodos disponibles:
    - today: Hoy
    - week: Última semana
    - month: Último mes
    - year: Último año
    """
    # Calcular fecha de inicio según período
    now = datetime.utcnow()
    if period == "today":
        date_from = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "week":
        date_from = now - timedelta(days=7)
    elif period == "month":
        date_from = now - timedelta(days=30)
    else:  # year
        date_from = now - timedelta(days=365)

    # Total de órdenes
    total_orders = db.query(func.count(OrderORM.id)).filter(
        OrderORM.restaurant_id == restaurant_id,
        OrderORM.created_at >= date_from
    ).scalar()

    # Ventas totales (solo completed)
    total_sales = db.query(func.sum(OrderORM.total)).filter(
        OrderORM.restaurant_id == restaurant_id,
        OrderORM.status == "completed",
        OrderORM.created_at >= date_from
    ).scalar() or 0

    # Ticket promedio
    avg_ticket = db.query(func.avg(OrderORM.total)).filter(
        OrderORM.restaurant_id == restaurant_id,
        OrderORM.status == "completed",
        OrderORM.created_at >= date_from
    ).scalar() or 0

    # Órdenes por estado
    orders_by_status = {}
    for order_status in ["pending", "confirmed", "preparing", "ready", "completed", "cancelled"]:
        count = db.query(func.count(OrderORM.id)).filter(
            OrderORM.restaurant_id == restaurant_id,
            OrderORM.status == order_status,
            OrderORM.created_at >= date_from
        ).scalar()
        orders_by_status[order_status] = count

    return {
        "success": True,
        "period": period,
        "date_from": date_from.isoformat(),
        "date_to": now.isoformat(),
        "stats": {
            "total_orders": total_orders,
            "total_sales": float(total_sales),
            "avg_ticket": float(avg_ticket),
            "orders_by_status": orders_by_status
        }
    }


# ============================================================================
# GET TOP PRODUCTS
# ============================================================================

@router.get("/-/top-products")
async def get_top_products(
    restaurant_id: str,
    limit: int = 10,
    period: str = Query("month", regex="^(week|month|year|all)$"),
    restaurant: RestaurantORM = Depends(check_restaurant_access),
    current_user = Depends(allow_all_staff),
    db: Session = Depends(get_db)
):
    """
    Obtener productos más vendidos.
    """
    # TODO: Implementar análisis de items JSONB para contar productos
    # Por ahora retornar estructura vacía

    return {
        "success": True,
        "period": period,
        "top_products": []
    }


# ============================================================================
# CANCEL ORDER
# ============================================================================

@router.post("/{order_id}/cancel", response_model=SuccessResponse)
async def cancel_order(
    restaurant_id: str,
    order_id: str,
    reason: Optional[str] = None,
    restaurant: RestaurantORM = Depends(check_restaurant_access),
    current_user = Depends(allow_all_staff),
    db: Session = Depends(get_db)
):
    """
    Cancelar orden.

    Solo se pueden cancelar órdenes en estado pending o confirmed.
    """
    order = db.query(OrderORM).filter(
        OrderORM.restaurant_id == restaurant_id,
        OrderORM.order_id == order_id
    ).first()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )

    if order.status not in ["pending", "confirmed"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel order in status: {order.status}"
        )

    order.status = "cancelled"
    order.cancelled_at = datetime.utcnow()
    if reason:
        order.internal_notes = f"Cancelled: {reason}"

    db.commit()

    # TODO: Notificar al cliente por WhatsApp

    return SuccessResponse(
        success=True,
        message="Order cancelled successfully",
        data={"order_id": order_id}
    )
