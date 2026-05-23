"""
================================================================================
ADMIN DASHBOARD ROUTER - Estadísticas y Panel de Control
================================================================================
Endpoints para el dashboard de administración con estadísticas
================================================================================
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from datetime import datetime, timedelta
import logging

from ..database import get_db
from ..models import Product, Category
from ..models.order import Order, OrderStatus, OrderItem
from ..models.user import User
from ..models.review import Review
from ..auth.permissions import require_staff

logger = logging.getLogger(__name__)

router = APIRouter()


# ==============================================================================
# DASHBOARD OVERVIEW
# ==============================================================================

@router.get(
    "/overview",
    summary="Resumen general del dashboard"
)
async def get_dashboard_overview(
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db)
):
    """
    Obtener resumen general para el dashboard del admin.

    Incluye:
    - Total de pedidos (hoy, semana, mes)
    - Ingresos (hoy, semana, mes)
    - Productos activos/inactivos
    - Pedidos pendientes
    """
    logger.info(f"Obteniendo overview del dashboard para tenant {current_user.tenant_id}")

    tenant_id = current_user.tenant_id

    # Fechas de referencia
    now = datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=now.weekday())
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Query base
    orders_query = db.query(Order)
    if not current_user.is_super_admin():
        orders_query = orders_query.filter(Order.tenant_id == tenant_id)

    # Pedidos hoy
    orders_today = orders_query.filter(Order.created_at >= today_start).all()
    total_today = sum(float(o.total) for o in orders_today if o.status == OrderStatus.DELIVERED)

    # Pedidos semana
    orders_week = orders_query.filter(Order.created_at >= week_start).all()
    total_week = sum(float(o.total) for o in orders_week if o.status == OrderStatus.DELIVERED)

    # Pedidos mes
    orders_month = orders_query.filter(Order.created_at >= month_start).all()
    total_month = sum(float(o.total) for o in orders_month if o.status == OrderStatus.DELIVERED)

    # Pedidos pendientes
    pending_count = orders_query.filter(Order.status == OrderStatus.PENDING).count()

    # Productos
    products_query = db.query(Product)
    if not current_user.is_super_admin():
        products_query = products_query.filter(Product.tenant_id == tenant_id)

    total_products = products_query.count()
    active_products = products_query.filter(Product.is_available == True).count()
    inactive_products = total_products - active_products

    # Rating promedio
    reviews_query = db.query(Review).join(Order).filter(Order.tenant_id == tenant_id)
    avg_rating = db.query(func.avg(Review.rating)).join(Order).filter(
        Order.tenant_id == tenant_id
    ).scalar()

    return {
        "orders": {
            "today": {
                "count": len(orders_today),
                "revenue": round(total_today, 2)
            },
            "week": {
                "count": len(orders_week),
                "revenue": round(total_week, 2)
            },
            "month": {
                "count": len(orders_month),
                "revenue": round(total_month, 2)
            },
            "pending": pending_count
        },
        "products": {
            "total": total_products,
            "active": active_products,
            "inactive": inactive_products
        },
        "rating": {
            "average": round(float(avg_rating), 2) if avg_rating else 0.0
        },
        "timestamp": now.isoformat()
    }


# ==============================================================================
# SALES CHART
# ==============================================================================

@router.get(
    "/sales",
    summary="Datos de ventas para gráficas"
)
async def get_sales_data(
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db),
    period: str = Query(default="week", description="day, week, month, year"),
    date_from: Optional[datetime] = Query(default=None),
    date_to: Optional[datetime] = Query(default=None)
):
    """
    Obtener datos de ventas para gráficas.

    Retorna ventas agrupadas por día, semana o mes.
    """
    logger.info(f"Obteniendo datos de ventas: {period}")

    tenant_id = current_user.tenant_id

    # Determinar rango de fechas
    if not date_from:
        if period == "day":
            date_from = datetime.now() - timedelta(days=7)
        elif period == "week":
            date_from = datetime.now() - timedelta(weeks=4)
        elif period == "month":
            date_from = datetime.now() - timedelta(days=90)
        else:  # year
            date_from = datetime.now() - timedelta(days=365)

    if not date_to:
        date_to = datetime.now()

    # Query pedidos
    query = db.query(Order).filter(
        Order.created_at >= date_from,
        Order.created_at <= date_to,
        Order.status == OrderStatus.DELIVERED
    )

    if not current_user.is_super_admin():
        query = query.filter(Order.tenant_id == tenant_id)

    orders = query.all()

    # Agrupar por período
    sales_by_period = {}

    for order in orders:
        if period == "day":
            key = order.created_at.strftime("%Y-%m-%d")
        elif period == "week":
            key = order.created_at.strftime("%Y-W%W")
        elif period == "month":
            key = order.created_at.strftime("%Y-%m")
        else:  # year
            key = order.created_at.strftime("%Y")

        if key not in sales_by_period:
            sales_by_period[key] = {
                "period": key,
                "count": 0,
                "revenue": 0.0
            }

        sales_by_period[key]["count"] += 1
        sales_by_period[key]["revenue"] += float(order.total)

    # Convertir a lista y ordenar
    sales_data = sorted(sales_by_period.values(), key=lambda x: x["period"])

    # Redondear revenues
    for item in sales_data:
        item["revenue"] = round(item["revenue"], 2)

    return {
        "period": period,
        "date_from": date_from.isoformat(),
        "date_to": date_to.isoformat(),
        "data": sales_data
    }


# ==============================================================================
# TOP PRODUCTS
# ==============================================================================

@router.get(
    "/top-products",
    summary="Productos más vendidos"
)
async def get_top_products(
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db),
    limit: int = Query(default=10, ge=1, le=50),
    date_from: Optional[datetime] = Query(default=None),
    date_to: Optional[datetime] = Query(default=None)
):
    """
    Obtener los productos más vendidos.
    """
    logger.info(f"Obteniendo top {limit} productos")

    tenant_id = current_user.tenant_id

    # Query de order items con joins
    query = db.query(
        OrderItem.product_id,
        Product.name,
        Product.price,
        func.sum(OrderItem.quantity).label('total_quantity'),
        func.sum(OrderItem.subtotal).label('total_revenue')
    ).join(Product).join(Order).filter(
        Order.status == OrderStatus.DELIVERED
    )

    if not current_user.is_super_admin():
        query = query.filter(Product.tenant_id == tenant_id)

    if date_from:
        query = query.filter(Order.created_at >= date_from)
    if date_to:
        query = query.filter(Order.created_at <= date_to)

    results = query.group_by(
        OrderItem.product_id,
        Product.name,
        Product.price
    ).order_by(
        func.sum(OrderItem.quantity).desc()
    ).limit(limit).all()

    top_products = []
    for product_id, name, price, quantity, revenue in results:
        top_products.append({
            "product_id": product_id,
            "name": name,
            "price": float(price),
            "quantity_sold": int(quantity),
            "total_revenue": round(float(revenue), 2)
        })

    return {
        "top_products": top_products,
        "date_from": date_from.isoformat() if date_from else None,
        "date_to": date_to.isoformat() if date_to else None
    }


# ==============================================================================
# REVIEWS SUMMARY
# ==============================================================================

@router.get(
    "/reviews-summary",
    summary="Resumen de reseñas"
)
async def get_reviews_summary(
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db)
):
    """
    Obtener resumen de reseñas del tenant.
    """
    logger.info(f"Obteniendo resumen de reseñas")

    tenant_id = current_user.tenant_id

    # Query reseñas
    query = db.query(Review).join(Order).filter(Order.tenant_id == tenant_id)

    total_reviews = query.count()

    if total_reviews == 0:
        return {
            "total_reviews": 0,
            "average_rating": 0.0,
            "rating_distribution": {
                "5": 0, "4": 0, "3": 0, "2": 0, "1": 0
            },
            "averages_by_category": {
                "food_quality": 0.0,
                "delivery_time": 0.0,
                "service": 0.0
            }
        }

    # Promedio general
    avg_rating = db.query(func.avg(Review.rating)).join(Order).filter(
        Order.tenant_id == tenant_id
    ).scalar()

    # Promedios por categoría
    avg_food = db.query(func.avg(Review.food_quality)).join(Order).filter(
        Order.tenant_id == tenant_id
    ).scalar()

    avg_delivery = db.query(func.avg(Review.delivery_time)).join(Order).filter(
        Order.tenant_id == tenant_id
    ).scalar()

    avg_service = db.query(func.avg(Review.service)).join(Order).filter(
        Order.tenant_id == tenant_id
    ).scalar()

    # Distribución de ratings
    reviews = query.all()
    distribution = {"5": 0, "4": 0, "3": 0, "2": 0, "1": 0}

    for review in reviews:
        rounded_rating = round(review.rating)
        distribution[str(rounded_rating)] += 1

    return {
        "total_reviews": total_reviews,
        "average_rating": round(float(avg_rating), 2),
        "rating_distribution": distribution,
        "averages_by_category": {
            "food_quality": round(float(avg_food), 2),
            "delivery_time": round(float(avg_delivery), 2),
            "service": round(float(avg_service), 2)
        }
    }


# ==============================================================================
# RECENT ACTIVITY
# ==============================================================================

@router.get(
    "/recent-activity",
    summary="Actividad reciente"
)
async def get_recent_activity(
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db),
    limit: int = Query(default=20, ge=1, le=100)
):
    """
    Obtener actividad reciente del tenant.

    Incluye pedidos recientes, reseñas recientes, etc.
    """
    logger.info(f"Obteniendo actividad reciente")

    tenant_id = current_user.tenant_id

    # Pedidos recientes
    orders_query = db.query(Order)
    if not current_user.is_super_admin():
        orders_query = orders_query.filter(Order.tenant_id == tenant_id)

    recent_orders = orders_query.order_by(Order.created_at.desc()).limit(limit).all()

    # Reseñas recientes
    reviews_query = db.query(Review).join(Order)
    if not current_user.is_super_admin():
        reviews_query = reviews_query.filter(Order.tenant_id == tenant_id)

    recent_reviews = reviews_query.order_by(Review.created_at.desc()).limit(10).all()

    return {
        "recent_orders": [
            {
                "order_id": o.order_id,
                "customer_name": o.customer_name,
                "total": float(o.total),
                "status": o.status.value,
                "created_at": o.created_at.isoformat()
            }
            for o in recent_orders
        ],
        "recent_reviews": [
            {
                "id": r.id,
                "order_id": r.order_id,
                "rating": r.rating,
                "comment": r.comment[:100] if r.comment else None,  # Primeros 100 chars
                "created_at": r.created_at.isoformat()
            }
            for r in recent_reviews
        ]
    }
