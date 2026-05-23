# ============================================================================
# MODELOS PYDANTIC - Sistema Multi-Tenant
# ============================================================================
# Modelos para el sistema multi-tenant con números dedicados
# ============================================================================

from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime, date, time
from enum import Enum
from decimal import Decimal


# ============================================================================
# ENUMS
# ============================================================================

class BusinessType(str, Enum):
    RESTAURANT = "restaurant"
    RETAIL = "retail"
    PHARMACY = "pharmacy"
    GROCERY = "grocery"
    SERVICES = "services"
    PET_SHOP = "pet_shop"
    OTHER = "other"


class SubscriptionPlan(str, Enum):
    BASIC = "basic"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class SubscriptionStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    CANCELLED = "cancelled"
    TRIAL = "trial"


class UserRole(str, Enum):
    SUPER_ADMIN = "super_admin"
    OWNER = "owner"
    MANAGER = "manager"
    EMPLOYEE = "employee"


class OrderStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PREPARING = "preparing"
    READY = "ready"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class PaymentStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


# ============================================================================
# RESTAURANT MODELS
# ============================================================================

class BusinessHours(BaseModel):
    """Horario de un día específico"""
    open: Optional[str] = None  # "09:00"
    close: Optional[str] = None  # "21:00"
    is_closed: bool = False


class RestaurantBusinessHours(BaseModel):
    """Horarios semanales del negocio"""
    monday: Optional[BusinessHours] = None
    tuesday: Optional[BusinessHours] = None
    wednesday: Optional[BusinessHours] = None
    thursday: Optional[BusinessHours] = None
    friday: Optional[BusinessHours] = None
    saturday: Optional[BusinessHours] = None
    sunday: Optional[BusinessHours] = None


class RestaurantBase(BaseModel):
    """Base model para Restaurant"""
    name: str = Field(..., min_length=1, max_length=255)
    owner_name: str = Field(..., min_length=1, max_length=255)
    owner_email: EmailStr
    owner_phone: str = Field(..., min_length=10, max_length=20)
    business_type: BusinessType
    business_category: Optional[str] = None

    # Ubicación
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: str = "México"
    postal_code: Optional[str] = None

    # Configuración
    timezone: str = "America/Mexico_City"
    currency: str = "MXN"
    language: str = "es"
    business_hours: Optional[Dict[str, Any]] = None

    # Branding
    logo_url: Optional[str] = None
    primary_color: str = "#4F46E5"

    # Plan
    plan: SubscriptionPlan = SubscriptionPlan.BASIC
    monthly_price: Optional[Decimal] = None


class RestaurantCreate(RestaurantBase):
    """Modelo para crear un restaurante"""
    pass


class RestaurantUpdate(BaseModel):
    """Modelo para actualizar un restaurante"""
    name: Optional[str] = None
    owner_name: Optional[str] = None
    owner_email: Optional[EmailStr] = None
    owner_phone: Optional[str] = None
    business_category: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None
    timezone: Optional[str] = None
    currency: Optional[str] = None
    language: Optional[str] = None
    business_hours: Optional[Dict[str, Any]] = None
    logo_url: Optional[str] = None
    primary_color: Optional[str] = None
    plan: Optional[SubscriptionPlan] = None
    monthly_price: Optional[Decimal] = None
    subscription_status: Optional[SubscriptionStatus] = None


class Restaurant(RestaurantBase):
    """Modelo completo de Restaurant"""
    id: int
    restaurant_id: str
    slug: str

    twilio_number: Optional[str] = None
    twilio_sid: Optional[str] = None
    whatsapp_business_name: Optional[str] = None

    subscription_status: SubscriptionStatus = SubscriptionStatus.ACTIVE
    subscription_started_at: Optional[datetime] = None
    subscription_expires_at: Optional[datetime] = None

    status: str = "active"
    is_demo: bool = False

    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============================================================================
# USER MODELS
# ============================================================================

class UserBase(BaseModel):
    """Base model para User"""
    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=255)
    phone: Optional[str] = None
    role: UserRole
    restaurant_id: Optional[str] = None  # NULL para super_admin


class UserCreate(UserBase):
    """Modelo para crear usuario"""
    password: str = Field(..., min_length=8)


class UserLogin(BaseModel):
    """Modelo para login"""
    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    """Modelo para actualizar usuario"""
    full_name: Optional[str] = None
    phone: Optional[str] = None
    is_active: Optional[bool] = None


class UserPasswordChange(BaseModel):
    """Modelo para cambio de contraseña"""
    current_password: str
    new_password: str = Field(..., min_length=8)


class User(UserBase):
    """Modelo completo de User"""
    id: int
    user_id: str
    is_active: bool = True
    email_verified: bool = False
    last_login_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TokenData(BaseModel):
    """Datos del JWT token"""
    user_id: str
    restaurant_id: Optional[str] = None
    role: UserRole
    exp: datetime


class TokenResponse(BaseModel):
    """Respuesta de autenticación"""
    access_token: str
    token_type: str = "bearer"
    user: User


# ============================================================================
# CATEGORY MODELS
# ============================================================================

class CategoryBase(BaseModel):
    """Base model para Category"""
    name: str = Field(..., min_length=1, max_length=255)
    icon: Optional[str] = None
    description: Optional[str] = None
    display_order: int = 0
    is_active: bool = True


class CategoryCreate(CategoryBase):
    """Modelo para crear categoría"""
    pass


class CategoryUpdate(BaseModel):
    """Modelo para actualizar categoría"""
    name: Optional[str] = None
    icon: Optional[str] = None
    description: Optional[str] = None
    display_order: Optional[int] = None
    is_active: Optional[bool] = None


class Category(CategoryBase):
    """Modelo completo de Category"""
    id: int
    category_id: str
    restaurant_id: str
    slug: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# PRODUCT MODELS
# ============================================================================

class ProductVariant(BaseModel):
    """Variante de producto"""
    name: str  # "Tamaño"
    options: List[str]  # ["Chico", "Mediano", "Grande"]
    price_modifier: Optional[Dict[str, Decimal]] = None  # {"Grande": 10.00}


class ProductModifier(BaseModel):
    """Modificador de producto"""
    id: str
    name: str
    price: Decimal
    max_quantity: int = 1


class ProductBase(BaseModel):
    """Base model para Product"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    price: Decimal = Field(..., ge=0)
    category_id: Optional[str] = None

    image_url: Optional[str] = None
    images: Optional[List[str]] = None

    compare_at_price: Optional[Decimal] = None
    cost: Optional[Decimal] = None

    track_inventory: bool = False
    stock_quantity: int = 0
    low_stock_threshold: int = 10

    available: bool = True
    available_start_time: Optional[time] = None
    available_end_time: Optional[time] = None

    has_variants: bool = False
    variants: Optional[List[ProductVariant]] = None
    modifiers: Optional[List[ProductModifier]] = None

    display_order: int = 0
    is_featured: bool = False


class ProductCreate(ProductBase):
    """Modelo para crear producto"""
    pass


class ProductUpdate(BaseModel):
    """Modelo para actualizar producto"""
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[Decimal] = None
    category_id: Optional[str] = None
    image_url: Optional[str] = None
    images: Optional[List[str]] = None
    compare_at_price: Optional[Decimal] = None
    cost: Optional[Decimal] = None
    track_inventory: Optional[bool] = None
    stock_quantity: Optional[int] = None
    available: Optional[bool] = None
    has_variants: Optional[bool] = None
    variants: Optional[List[ProductVariant]] = None
    modifiers: Optional[List[ProductModifier]] = None
    display_order: Optional[int] = None
    is_featured: Optional[bool] = None


class Product(ProductBase):
    """Modelo completo de Product"""
    id: int
    product_id: str
    restaurant_id: str
    slug: str
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============================================================================
# CUSTOMER MODELS
# ============================================================================

class CustomerBase(BaseModel):
    """Base model para Customer"""
    phone: str = Field(..., min_length=10, max_length=20)
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    birthday: Optional[date] = None
    address: Optional[str] = None
    notes: Optional[str] = None
    tags: Optional[List[str]] = None


class CustomerCreate(CustomerBase):
    """Modelo para crear cliente"""
    pass


class CustomerUpdate(BaseModel):
    """Modelo para actualizar cliente"""
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    birthday: Optional[date] = None
    address: Optional[str] = None
    notes: Optional[str] = None
    tags: Optional[List[str]] = None


class Customer(CustomerBase):
    """Modelo completo de Customer"""
    id: int
    customer_id: str
    restaurant_id: str
    total_orders: int = 0
    total_spent: Decimal = Decimal("0.00")
    average_order_value: Decimal = Decimal("0.00")
    first_order_at: Optional[datetime] = None
    last_order_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# ORDER MODELS
# ============================================================================

class OrderItem(BaseModel):
    """Item de un pedido"""
    product_id: str
    name: str
    quantity: int = Field(..., ge=1)
    price: Decimal
    subtotal: Decimal
    modifiers: Optional[List[Dict[str, Any]]] = None
    notes: Optional[str] = None


class OrderBase(BaseModel):
    """Base model para Order"""
    customer_phone: str = Field(..., min_length=10, max_length=20)
    customer_name: Optional[str] = None
    items: List[OrderItem]

    subtotal: Decimal
    discount_amount: Decimal = Decimal("0.00")
    loyalty_discount: Decimal = Decimal("0.00")
    tax_amount: Decimal = Decimal("0.00")
    delivery_fee: Decimal = Decimal("0.00")
    total: Decimal

    payment_method: str
    payment_status: PaymentStatus = PaymentStatus.PENDING

    delivery_type: str = "pickup"
    delivery_address: Optional[str] = None
    delivery_notes: Optional[str] = None

    customer_notes: Optional[str] = None

    loyalty_points_used: int = 0

    source: str = "whatsapp"


class OrderCreate(OrderBase):
    """Modelo para crear pedido"""
    pass


class OrderUpdate(BaseModel):
    """Modelo para actualizar pedido"""
    status: Optional[OrderStatus] = None
    payment_status: Optional[PaymentStatus] = None
    internal_notes: Optional[str] = None


class Order(OrderBase):
    """Modelo completo de Order"""
    id: int
    order_id: str
    restaurant_id: str
    customer_id: Optional[str] = None

    status: OrderStatus = OrderStatus.PENDING
    loyalty_points_earned: int = 0

    confirmed_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# RESPONSE MODELS
# ============================================================================

class PaginatedResponse(BaseModel):
    """Respuesta paginada genérica"""
    items: List[Any]
    total: int
    page: int
    page_size: int
    total_pages: int


class SuccessResponse(BaseModel):
    """Respuesta exitosa genérica"""
    success: bool = True
    message: str
    data: Optional[Any] = None


class ErrorResponse(BaseModel):
    """Respuesta de error"""
    success: bool = False
    error: str
    details: Optional[Any] = None
