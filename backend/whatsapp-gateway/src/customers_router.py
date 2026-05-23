# ============================================================================
# CUSTOMERS ROUTER - Endpoints para Gestión de Clientes
# ============================================================================

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional

from src.database import get_db
from src.orm_models import CustomerORM, RestaurantORM, OrderORM, LoyaltyAccountORM
from src.models_multitenant import (
    Customer, CustomerUpdate,
    SuccessResponse
)
from src.auth import check_restaurant_access, allow_all_staff

router = APIRouter(prefix="/api/v1/restaurants/{restaurant_id}/customers", tags=["Customers"])


# ============================================================================
# GET ALL CUSTOMERS
# ============================================================================

@router.get("", response_model=List[Customer])
async def get_customers(
    restaurant_id: str,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    restaurant: RestaurantORM = Depends(check_restaurant_access),
    current_user = Depends(allow_all_staff),
    db: Session = Depends(get_db)
):
    """
    Listar clientes del restaurante.

    Filtros opcionales:
    - search: Buscar por nombre o teléfono
    """
    query = db.query(CustomerORM).filter(
        CustomerORM.restaurant_id == restaurant_id
    )

    if search:
        query = query.filter(
            (CustomerORM.name.ilike(f"%{search}%")) |
            (CustomerORM.phone.ilike(f"%{search}%")) |
            (CustomerORM.email.ilike(f"%{search}%"))
        )

    customers = query.order_by(desc(CustomerORM.last_order_at)).offset(skip).limit(limit).all()

    return [Customer.from_orm(c) for c in customers]


# ============================================================================
# GET CUSTOMER BY PHONE
# ============================================================================

@router.get("/{phone}", response_model=Customer)
async def get_customer(
    restaurant_id: str,
    phone: str,
    restaurant: RestaurantORM = Depends(check_restaurant_access),
    current_user = Depends(allow_all_staff),
    db: Session = Depends(get_db)
):
    """
    Obtener detalles de un cliente específico por teléfono.
    """
    customer = db.query(CustomerORM).filter(
        CustomerORM.restaurant_id == restaurant_id,
        CustomerORM.phone == phone
    ).first()

    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )

    return Customer.from_orm(customer)


# ============================================================================
# UPDATE CUSTOMER
# ============================================================================

@router.patch("/{phone}", response_model=Customer)
async def update_customer(
    restaurant_id: str,
    phone: str,
    customer_update: CustomerUpdate,
    restaurant: RestaurantORM = Depends(check_restaurant_access),
    current_user = Depends(allow_all_staff),
    db: Session = Depends(get_db)
):
    """
    Actualizar información del cliente.
    """
    customer = db.query(CustomerORM).filter(
        CustomerORM.restaurant_id == restaurant_id,
        CustomerORM.phone == phone
    ).first()

    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )

    # Actualizar campos
    update_data = customer_update.dict(exclude_unset=True)

    for field, value in update_data.items():
        if hasattr(customer, field):
            setattr(customer, field, value)

    db.commit()
    db.refresh(customer)

    return Customer.from_orm(customer)


# ============================================================================
# GET CUSTOMER ORDERS
# ============================================================================

@router.get("/{phone}/orders")
async def get_customer_orders(
    restaurant_id: str,
    phone: str,
    skip: int = 0,
    limit: int = 50,
    restaurant: RestaurantORM = Depends(check_restaurant_access),
    current_user = Depends(allow_all_staff),
    db: Session = Depends(get_db)
):
    """
    Obtener historial de órdenes del cliente.
    """
    # Verificar que el cliente existe
    customer = db.query(CustomerORM).filter(
        CustomerORM.restaurant_id == restaurant_id,
        CustomerORM.phone == phone
    ).first()

    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )

    # Obtener órdenes
    orders = db.query(OrderORM).filter(
        OrderORM.restaurant_id == restaurant_id,
        OrderORM.customer_phone == phone
    ).order_by(desc(OrderORM.created_at)).offset(skip).limit(limit).all()

    from src.models_multitenant import Order
    return {
        "success": True,
        "customer_phone": phone,
        "total_orders": customer.total_orders,
        "orders": [Order.from_orm(o) for o in orders]
    }


# ============================================================================
# GET CUSTOMER LOYALTY
# ============================================================================

@router.get("/{phone}/loyalty")
async def get_customer_loyalty(
    restaurant_id: str,
    phone: str,
    restaurant: RestaurantORM = Depends(check_restaurant_access),
    current_user = Depends(allow_all_staff),
    db: Session = Depends(get_db)
):
    """
    Obtener puntos de fidelidad del cliente.
    """
    # Buscar cuenta de loyalty
    loyalty_account = db.query(LoyaltyAccountORM).filter(
        LoyaltyAccountORM.restaurant_id == restaurant_id,
        LoyaltyAccountORM.customer_phone == phone
    ).first()

    if not loyalty_account:
        return {
            "success": True,
            "customer_phone": phone,
            "has_loyalty_account": False,
            "message": "Customer does not have a loyalty account yet"
        }

    return {
        "success": True,
        "customer_phone": phone,
        "has_loyalty_account": True,
        "loyalty": {
            "points_balance": loyalty_account.points_balance,
            "points_lifetime": loyalty_account.points_lifetime,
            "points_redeemed": loyalty_account.points_redeemed,
            "tier_level": loyalty_account.tier_level,
            "total_spent": float(loyalty_account.total_spent),
            "total_orders": loyalty_account.total_orders,
            "last_earned_at": loyalty_account.last_earned_at,
            "last_redeemed_at": loyalty_account.last_redeemed_at
        }
    }


# ============================================================================
# GET CUSTOMERS STATS
# ============================================================================

@router.get("/-/stats")
async def get_customers_stats(
    restaurant_id: str,
    restaurant: RestaurantORM = Depends(check_restaurant_access),
    current_user = Depends(allow_all_staff),
    db: Session = Depends(get_db)
):
    """
    Obtener estadísticas de clientes.
    """
    from sqlalchemy import func

    # Total de clientes
    total_customers = db.query(func.count(CustomerORM.id)).filter(
        CustomerORM.restaurant_id == restaurant_id
    ).scalar()

    # Nuevos clientes este mes
    from datetime import datetime, timedelta
    month_ago = datetime.utcnow() - timedelta(days=30)

    new_customers = db.query(func.count(CustomerORM.id)).filter(
        CustomerORM.restaurant_id == restaurant_id,
        CustomerORM.created_at >= month_ago
    ).scalar()

    # Cliente más frecuente
    top_customer = db.query(CustomerORM).filter(
        CustomerORM.restaurant_id == restaurant_id
    ).order_by(desc(CustomerORM.total_orders)).first()

    # Cliente con más gasto
    top_spender = db.query(CustomerORM).filter(
        CustomerORM.restaurant_id == restaurant_id
    ).order_by(desc(CustomerORM.total_spent)).first()

    return {
        "success": True,
        "stats": {
            "total_customers": total_customers,
            "new_customers_last_30_days": new_customers,
            "top_customer": {
                "phone": top_customer.phone,
                "name": top_customer.name,
                "total_orders": top_customer.total_orders
            } if top_customer else None,
            "top_spender": {
                "phone": top_spender.phone,
                "name": top_spender.name,
                "total_spent": float(top_spender.total_spent)
            } if top_spender else None
        }
    }


# ============================================================================
# DELETE CUSTOMER
# ============================================================================

@router.delete("/{phone}", response_model=SuccessResponse)
async def delete_customer(
    restaurant_id: str,
    phone: str,
    restaurant: RestaurantORM = Depends(check_restaurant_access),
    current_user = Depends(allow_all_staff),
    db: Session = Depends(get_db)
):
    """
    Eliminar cliente.

    CUIDADO: También elimina sus órdenes y puntos de fidelidad.
    """
    customer = db.query(CustomerORM).filter(
        CustomerORM.restaurant_id == restaurant_id,
        CustomerORM.phone == phone
    ).first()

    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )

    # Eliminar (cascade eliminará órdenes y loyalty)
    db.delete(customer)
    db.commit()

    return SuccessResponse(
        success=True,
        message="Customer deleted successfully",
        data={"phone": phone}
    )
