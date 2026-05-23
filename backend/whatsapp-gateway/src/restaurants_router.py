# ============================================================================
# RESTAURANTS ROUTER - CRUD Endpoints para Restaurantes
# ============================================================================

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid
from slugify import slugify

from src.database import get_db
from src.orm_models import RestaurantORM, UserORM, LoyaltyConfigORM, CategoryORM
from src.models_multitenant import (
    Restaurant, RestaurantCreate, RestaurantUpdate,
    SuccessResponse, UserRole
)
from src.auth import (
    get_current_user,
    allow_super_admin,
    check_restaurant_access,
    hash_password,
    generate_user_id,
    generate_restaurant_id
)

router = APIRouter(prefix="/api/v1/restaurants", tags=["Restaurants"])


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def create_slug(name: str, db: Session) -> str:
    """
    Crear slug único para el restaurante
    """
    base_slug = slugify(name)
    slug = base_slug
    counter = 1

    while db.query(RestaurantORM).filter(RestaurantORM.slug == slug).first():
        slug = f"{base_slug}-{counter}"
        counter += 1

    return slug


# ============================================================================
# CREATE RESTAURANT (Solo Super Admin)
# ============================================================================

@router.post("", response_model=SuccessResponse, status_code=status.HTTP_201_CREATED)
async def create_restaurant(
    restaurant_data: RestaurantCreate,
    db: Session = Depends(get_db),
    current_user: UserORM = Depends(allow_super_admin)
):
    """
    Crear nuevo restaurante/tienda.

    Solo super admin puede crear restaurantes.

    Proceso:
    1. Crea registro de restaurante
    2. Genera restaurant_id y slug únicos
    3. Crea usuario owner con credenciales temporales
    4. Crea configuración de loyalty por defecto
    5. Crea categorías por defecto
    6. (TODO) Compra número de Twilio
    7. (TODO) Envía email de bienvenida

    **Nota:** El número de Twilio debe configurarse manualmente o mediante
    endpoint separado de provisión.
    """

    # Verificar que no exista email duplicado
    existing_email = db.query(RestaurantORM).filter(
        RestaurantORM.owner_email == restaurant_data.owner_email
    ).first()

    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Owner email already registered"
        )

    # Generar IDs únicos
    restaurant_id = generate_restaurant_id()
    slug = create_slug(restaurant_data.name, db)

    # Crear restaurante
    restaurant = RestaurantORM(
        restaurant_id=restaurant_id,
        name=restaurant_data.name,
        slug=slug,
        owner_name=restaurant_data.owner_name,
        owner_email=restaurant_data.owner_email,
        owner_phone=restaurant_data.owner_phone,
        business_type=restaurant_data.business_type.value,
        business_category=restaurant_data.business_category,
        address=restaurant_data.address,
        city=restaurant_data.city,
        state=restaurant_data.state,
        country=restaurant_data.country,
        postal_code=restaurant_data.postal_code,
        timezone=restaurant_data.timezone,
        currency=restaurant_data.currency,
        language=restaurant_data.language,
        business_hours=restaurant_data.business_hours,
        logo_url=restaurant_data.logo_url,
        primary_color=restaurant_data.primary_color,
        plan=restaurant_data.plan.value,
        monthly_price=restaurant_data.monthly_price,
        subscription_status="active",
        status="active"
    )

    db.add(restaurant)
    db.flush()  # Para obtener el ID

    # Crear usuario owner
    temp_password = f"temp_{uuid.uuid4().hex[:8]}"  # Password temporal
    user_id = generate_user_id()

    owner_user = UserORM(
        user_id=user_id,
        restaurant_id=restaurant_id,
        email=restaurant_data.owner_email,
        password_hash=hash_password(temp_password),
        full_name=restaurant_data.owner_name,
        phone=restaurant_data.owner_phone,
        role=UserRole.OWNER.value,
        is_active=True,
        email_verified=False
    )

    db.add(owner_user)

    # Crear configuración de loyalty por defecto
    loyalty_config = LoyaltyConfigORM(
        restaurant_id=restaurant_id,
        enabled=True,
        points_per_currency=0.1,
        currency_per_point=0.5,
        min_points_to_redeem=100,
        max_redeem_percentage=50.0,
        tier_thresholds={
            "bronce": 0,
            "plata": 1000,
            "oro": 2500,
            "platino": 5000
        },
        tier_multipliers={
            "bronce": 1.0,
            "plata": 1.5,
            "oro": 2.0,
            "platino": 3.0
        },
        tier_benefits={}
    )

    db.add(loyalty_config)

    # Crear categorías por defecto según business_type
    default_categories = get_default_categories(restaurant_data.business_type.value)

    for idx, cat in enumerate(default_categories):
        category_id = f"cat_{uuid.uuid4().hex[:12]}"
        category = CategoryORM(
            category_id=category_id,
            restaurant_id=restaurant_id,
            name=cat["name"],
            slug=slugify(cat["name"]),
            icon=cat.get("icon"),
            display_order=idx,
            is_active=True
        )
        db.add(category)

    db.commit()
    db.refresh(restaurant)

    return SuccessResponse(
        success=True,
        message="Restaurant created successfully",
        data={
            "restaurant_id": restaurant_id,
            "slug": slug,
            "owner_email": restaurant_data.owner_email,
            "temp_password": temp_password,  # Enviar por email en producción
            "next_steps": [
                "Configure Twilio number",
                "Setup payment methods",
                "Add products",
                "Test WhatsApp flow"
            ]
        }
    )


def get_default_categories(business_type: str) -> List[dict]:
    """
    Retorna categorías por defecto según tipo de negocio
    """
    categories_map = {
        "restaurant": [
            {"name": "Entradas", "icon": "🍽️"},
            {"name": "Platos Principales", "icon": "🍛"},
            {"name": "Bebidas", "icon": "🥤"},
            {"name": "Postres", "icon": "🍰"},
        ],
        "retail": [
            {"name": "Ropa", "icon": "👕"},
            {"name": "Accesorios", "icon": "👜"},
            {"name": "Calzado", "icon": "👟"},
        ],
        "pharmacy": [
            {"name": "Medicamentos", "icon": "💊"},
            {"name": "Cuidado Personal", "icon": "🧴"},
            {"name": "Vitaminas", "icon": "💪"},
        ],
        "grocery": [
            {"name": "Frutas y Verduras", "icon": "🥕"},
            {"name": "Lácteos", "icon": "🥛"},
            {"name": "Despensa", "icon": "🥫"},
        ],
        "services": [
            {"name": "Servicios", "icon": "✂️"},
        ],
        "pet_shop": [
            {"name": "Alimento", "icon": "🦴"},
            {"name": "Accesorios", "icon": "🐾"},
            {"name": "Juguetes", "icon": "🎾"},
        ]
    }

    return categories_map.get(business_type, [{"name": "General", "icon": "📦"}])


# ============================================================================
# GET ALL RESTAURANTS (Solo Super Admin)
# ============================================================================

@router.get("", response_model=List[Restaurant])
async def get_all_restaurants(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: UserORM = Depends(allow_super_admin)
):
    """
    Listar todos los restaurantes.

    Solo super admin puede ver todos los restaurantes.
    """
    query = db.query(RestaurantORM)

    if status:
        query = query.filter(RestaurantORM.status == status)

    restaurants = query.order_by(RestaurantORM.created_at.desc()).offset(skip).limit(limit).all()

    return restaurants


# ============================================================================
# GET RESTAURANT BY ID
# ============================================================================

@router.get("/{restaurant_id}", response_model=Restaurant)
async def get_restaurant(
    restaurant_id: str,
    restaurant: RestaurantORM = Depends(check_restaurant_access),
    db: Session = Depends(get_db)
):
    """
    Obtener detalles de un restaurante específico.

    - Super admin: puede ver cualquier restaurante
    - Owner/Manager: solo su propio restaurante
    """
    return restaurant


# ============================================================================
# UPDATE RESTAURANT
# ============================================================================

@router.patch("/{restaurant_id}", response_model=Restaurant)
async def update_restaurant(
    restaurant_id: str,
    restaurant_update: RestaurantUpdate,
    restaurant: RestaurantORM = Depends(check_restaurant_access),
    db: Session = Depends(get_db),
    current_user: UserORM = Depends(get_current_user)
):
    """
    Actualizar información del restaurante.

    - Super admin: puede actualizar cualquier restaurante
    - Owner: solo su propio restaurante
    """

    # Solo owner y super admin pueden actualizar
    if current_user.role not in [UserRole.OWNER.value, UserRole.SUPER_ADMIN.value]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owners can update restaurant information"
        )

    # Actualizar campos
    update_data = restaurant_update.dict(exclude_unset=True)

    for field, value in update_data.items():
        if hasattr(restaurant, field):
            setattr(restaurant, field, value)

    db.commit()
    db.refresh(restaurant)

    return restaurant


# ============================================================================
# DELETE RESTAURANT (Solo Super Admin)
# ============================================================================

@router.delete("/{restaurant_id}", response_model=SuccessResponse)
async def delete_restaurant(
    restaurant_id: str,
    db: Session = Depends(get_db),
    current_user: UserORM = Depends(allow_super_admin)
):
    """
    Eliminar (soft delete) un restaurante.

    Solo super admin puede eliminar restaurantes.
    """
    restaurant = db.query(RestaurantORM).filter(
        RestaurantORM.restaurant_id == restaurant_id
    ).first()

    if not restaurant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Restaurant not found"
        )

    # Soft delete
    from datetime import datetime
    restaurant.deleted_at = datetime.now()
    restaurant.status = "deleted"

    db.commit()

    return SuccessResponse(
        success=True,
        message="Restaurant deleted successfully",
        data={"restaurant_id": restaurant_id}
    )


# ============================================================================
# GET RESTAURANT STATS
# ============================================================================

@router.get("/{restaurant_id}/stats")
async def get_restaurant_stats(
    restaurant_id: str,
    restaurant: RestaurantORM = Depends(check_restaurant_access),
    db: Session = Depends(get_db)
):
    """
    Obtener estadísticas del restaurante.
    """
    from src.orm_models import OrderORM, CustomerORM, ProductORM
    from sqlalchemy import func

    # Total de pedidos
    total_orders = db.query(func.count(OrderORM.id)).filter(
        OrderORM.restaurant_id == restaurant_id
    ).scalar()

    # Total de clientes
    total_customers = db.query(func.count(CustomerORM.id)).filter(
        CustomerORM.restaurant_id == restaurant_id
    ).scalar()

    # Total de productos
    total_products = db.query(func.count(ProductORM.id)).filter(
        ProductORM.restaurant_id == restaurant_id,
        ProductORM.deleted_at == None
    ).scalar()

    # Ventas totales
    total_sales = db.query(func.sum(OrderORM.total)).filter(
        OrderORM.restaurant_id == restaurant_id,
        OrderORM.status == "completed"
    ).scalar() or 0

    return {
        "success": True,
        "restaurant_id": restaurant_id,
        "stats": {
            "total_orders": total_orders,
            "total_customers": total_customers,
            "total_products": total_products,
            "total_sales": float(total_sales),
        }
    }
