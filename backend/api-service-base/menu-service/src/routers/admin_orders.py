"""
================================================================================
ADMIN ORDERS ROUTER - Gestión de Pedidos
================================================================================
Endpoints de administración para ver y gestionar pedidos del tenant
================================================================================
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
import logging

from ..database import get_db
from ..models.order import Order, OrderStatus
from ..models.user import User
from ..schemas.order import OrderResponse, OrderStatusUpdate
from ..auth.permissions import require_staff, verify_resource_tenant
from ..socketio_server import broadcast_order_status_change

logger = logging.getLogger(__name__)

router = APIRouter()


# ==============================================================================
# LIST ALL ORDERS (FOR ADMIN)
# ==============================================================================

@router.get(
    "",
    response_model=List[OrderResponse],
    summary="Listar todos los pedidos del tenant"
)
async def list_all_orders(
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    status: Optional[str] = Query(default=None, description="Filtrar por estado"),
    date_from: Optional[datetime] = Query(default=None, description="Fecha desde"),
    date_to: Optional[datetime] = Query(default=None, description="Fecha hasta"),
    customer_phone: Optional[str] = Query(default=None, description="Teléfono del cliente")
):
    """
    Listar todos los pedidos del tenant (vista de administración).

    Staff y Admin pueden ver todos los pedidos de su tenant.
    """
    logger.info(f"Staff/Admin {current_user.id} listando pedidos")

    query = db.query(Order)

    # Filtrar por tenant (solo su tenant, a menos que sea super admin)
    if not current_user.is_super_admin():
        query = query.filter(Order.tenant_id == current_user.tenant_id)

    # Filtrar por estado
    if status:
        try:
            order_status = OrderStatus(status)
            query = query.filter(Order.status == order_status)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Estado inválido: {status}"
            )

    # Filtrar por fechas
    if date_from:
        query = query.filter(Order.created_at >= date_from)
    if date_to:
        query = query.filter(Order.created_at <= date_to)

    # Filtrar por teléfono de cliente
    if customer_phone:
        query = query.filter(Order.customer_phone.ilike(f"%{customer_phone}%"))

    orders = query.order_by(Order.created_at.desc()).offset(skip).limit(limit).all()

    logger.info(f"Encontrados {len(orders)} pedidos")

    return orders


# ==============================================================================
# GET PENDING ORDERS
# ==============================================================================

@router.get(
    "/pending",
    response_model=List[OrderResponse],
    summary="Obtener pedidos pendientes"
)
async def get_pending_orders(
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db)
):
    """
    Obtener todos los pedidos pendientes de confirmación.

    Útil para panel de administración en tiempo real.
    """
    logger.info(f"Obteniendo pedidos pendientes para tenant {current_user.tenant_id}")

    query = db.query(Order).filter(
        Order.status == OrderStatus.PENDING
    )

    if not current_user.is_super_admin():
        query = query.filter(Order.tenant_id == current_user.tenant_id)

    orders = query.order_by(Order.created_at.asc()).all()

    logger.info(f"Encontrados {len(orders)} pedidos pendientes")

    return orders


# ==============================================================================
# GET TODAY'S ORDERS
# ==============================================================================

@router.get(
    "/today",
    response_model=List[OrderResponse],
    summary="Obtener pedidos del día"
)
async def get_todays_orders(
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db)
):
    """
    Obtener todos los pedidos del día actual.
    """
    logger.info(f"Obteniendo pedidos del día para tenant {current_user.tenant_id}")

    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)

    query = db.query(Order).filter(
        Order.created_at >= today_start,
        Order.created_at < today_end
    )

    if not current_user.is_super_admin():
        query = query.filter(Order.tenant_id == current_user.tenant_id)

    orders = query.order_by(Order.created_at.desc()).all()

    logger.info(f"Encontrados {len(orders)} pedidos del día")

    return orders


# ==============================================================================
# UPDATE ORDER STATUS
# ==============================================================================

@router.put(
    "/{order_id}/status",
    response_model=OrderResponse,
    summary="Actualizar estado del pedido"
)
async def update_order_status(
    order_id: int,
    new_status: str = Query(..., description="Nuevo estado del pedido"),
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db)
):
    """
    Actualizar el estado de un pedido.

    Estados válidos:
    - pending: Pendiente de confirmación
    - confirmed: Confirmado
    - preparing: En preparación
    - ready: Listo para entrega
    - in_transit: En camino
    - delivered: Entregado
    - cancelled: Cancelado
    """
    logger.info(f"Actualizando estado del pedido {order_id} a {new_status}")

    # Buscar pedido
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pedido no encontrado"
        )

    # Verificar que pertenece al tenant
    if not current_user.is_super_admin() and order.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para modificar este pedido"
        )

    # Validar nuevo estado
    try:
        new_status_enum = OrderStatus(new_status)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Estado inválido: {new_status}"
        )

    old_status = order.status.value

    # Actualizar estado
    order.status = new_status_enum
    db.commit()
    db.refresh(order)

    # Emitir evento Socket.IO
    try:
        await broadcast_order_status_change(
            order.order_id,
            old_status,
            new_status,
            {
                "updated_by": current_user.name,
                "updated_at": datetime.now().isoformat()
            }
        )
    except Exception as e:
        logger.error(f"Error al emitir evento Socket.IO: {e}")

    logger.info(f"Pedido {order_id} actualizado de {old_status} a {new_status}")

    return order


# ==============================================================================
# GET ORDER DETAILS (ADMIN VIEW)
# ==============================================================================

@router.get(
    "/{order_id}",
    response_model=OrderResponse,
    summary="Obtener detalle de pedido (Admin)"
)
async def get_order_details_admin(
    order_id: int,
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db)
):
    """
    Obtener detalles completos de un pedido.

    Staff/Admin pueden ver cualquier pedido de su tenant.
    """
    logger.info(f"Admin consultando pedido {order_id}")

    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pedido no encontrado"
        )

    # Verificar permisos
    if not current_user.is_super_admin() and order.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para ver este pedido"
        )

    return order


# ==============================================================================
# CANCEL ORDER (ADMIN)
# ==============================================================================

@router.put(
    "/{order_id}/cancel",
    response_model=OrderResponse,
    summary="Cancelar pedido (Admin)"
)
async def cancel_order_admin(
    order_id: int,
    reason: str = Query(..., description="Razón de cancelación"),
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db)
):
    """
    Cancelar un pedido.

    Solo staff o admin pueden cancelar pedidos.
    """
    logger.info(f"Admin {current_user.id} cancelando pedido {order_id}")

    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pedido no encontrado"
        )

    # Verificar permisos
    if not current_user.is_super_admin() and order.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para cancelar este pedido"
        )

    # Verificar que se puede cancelar
    if order.status in [OrderStatus.DELIVERED, OrderStatus.CANCELLED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se puede cancelar un pedido en estado '{order.status.value}'"
        )

    old_status = order.status.value
    order.status = OrderStatus.CANCELLED

    # Agregar nota de cancelación (podrías tener un campo notes en el modelo Order)
    # order.notes = f"Cancelado por admin. Razón: {reason}"

    db.commit()
    db.refresh(order)

    # Emitir evento Socket.IO
    try:
        await broadcast_order_status_change(
            order.order_id,
            old_status,
            "cancelled",
            {
                "cancelled_by": current_user.name,
                "reason": reason
            }
        )
    except Exception as e:
        logger.error(f"Error al emitir evento Socket.IO: {e}")

    logger.info(f"Pedido {order_id} cancelado. Razón: {reason}")

    return order


# ==============================================================================
# GET ORDER STATISTICS
# ==============================================================================

@router.get(
    "/stats/summary",
    summary="Obtener estadísticas de pedidos"
)
async def get_order_statistics(
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db),
    date_from: Optional[datetime] = Query(default=None),
    date_to: Optional[datetime] = Query(default=None)
):
    """
    Obtener estadísticas de pedidos del tenant.

    Retorna:
    - Total de pedidos
    - Pedidos por estado
    - Ingresos totales
    - Promedio de pedido
    """
    logger.info(f"Obteniendo estadísticas de pedidos para tenant {current_user.tenant_id}")

    query = db.query(Order)

    if not current_user.is_super_admin():
        query = query.filter(Order.tenant_id == current_user.tenant_id)

    if date_from:
        query = query.filter(Order.created_at >= date_from)
    if date_to:
        query = query.filter(Order.created_at <= date_to)

    orders = query.all()

    # Calcular estadísticas
    total_orders = len(orders)
    orders_by_status = {}
    total_revenue = 0.0

    for order in orders:
        # Contar por estado
        status_key = order.status.value
        orders_by_status[status_key] = orders_by_status.get(status_key, 0) + 1

        # Sumar ingresos (solo pedidos completados)
        if order.status == OrderStatus.DELIVERED:
            total_revenue += float(order.total)

    average_order = total_revenue / total_orders if total_orders > 0 else 0

    return {
        "total_orders": total_orders,
        "orders_by_status": orders_by_status,
        "total_revenue": round(total_revenue, 2),
        "average_order_value": round(average_order, 2),
        "date_from": date_from.isoformat() if date_from else None,
        "date_to": date_to.isoformat() if date_to else None
    }
