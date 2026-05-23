# ============================================================================
# ORM MODELS - SQLAlchemy Models para PostgreSQL
# ============================================================================

from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Date, Time,
    Numeric, Text, ForeignKey, Index, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from src.database import Base
from datetime import datetime


# ============================================================================
# RESTAURANT MODEL
# ============================================================================

class RestaurantORM(Base):
    __tablename__ = "restaurants"

    id = Column(Integer, primary_key=True, index=True)
    restaurant_id = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, nullable=False)

    # Owner info
    owner_name = Column(String(255), nullable=False)
    owner_email = Column(String(255), nullable=False)
    owner_phone = Column(String(20), nullable=False)

    # Business type
    business_type = Column(String(50), nullable=False)
    business_category = Column(String(100))

    # Location
    address = Column(Text)
    city = Column(String(100))
    state = Column(String(100))
    country = Column(String(100), default="México")
    postal_code = Column(String(20))

    # WhatsApp/Twilio
    twilio_number = Column(String(20), unique=True, index=True)
    twilio_sid = Column(String(100))
    whatsapp_business_name = Column(String(255))

    # Subscription
    plan = Column(String(50), default="basic")
    monthly_price = Column(Numeric(10, 2))
    subscription_status = Column(String(50), default="active")
    subscription_started_at = Column(DateTime)
    subscription_expires_at = Column(DateTime)

    # Branding
    logo_url = Column(Text)
    primary_color = Column(String(7), default="#4F46E5")

    # Configuration
    timezone = Column(String(50), default="America/Mexico_City")
    currency = Column(String(3), default="MXN")
    language = Column(String(5), default="es")
    business_hours = Column(JSONB)

    # Status
    status = Column(String(50), default="active", index=True)
    is_demo = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime, nullable=True)

    # Relationships
    users = relationship("UserORM", back_populates="restaurant", cascade="all, delete-orphan")
    categories = relationship("CategoryORM", back_populates="restaurant", cascade="all, delete-orphan")
    products = relationship("ProductORM", back_populates="restaurant", cascade="all, delete-orphan")
    customers = relationship("CustomerORM", back_populates="restaurant", cascade="all, delete-orphan")
    orders = relationship("OrderORM", back_populates="restaurant", cascade="all, delete-orphan")
    loyalty_config = relationship("LoyaltyConfigORM", back_populates="restaurant", uselist=False, cascade="all, delete-orphan")
    sessions = relationship("SessionORM", back_populates="restaurant", cascade="all, delete-orphan")


# ============================================================================
# USER MODEL
# ============================================================================

class UserORM(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(50), unique=True, nullable=False)
    restaurant_id = Column(String(50), ForeignKey("restaurants.restaurant_id", ondelete="CASCADE"), index=True)

    # Authentication
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)

    # Personal info
    full_name = Column(String(255), nullable=False)
    phone = Column(String(20))

    # Role and permissions
    role = Column(String(50), nullable=False, index=True)
    permissions = Column(JSONB)

    # Status
    is_active = Column(Boolean, default=True)
    email_verified = Column(Boolean, default=False)
    email_verification_token = Column(String(255))

    # Password reset
    password_reset_token = Column(String(255))
    password_reset_expires = Column(DateTime)

    # Timestamps
    last_login_at = Column(DateTime)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    restaurant = relationship("RestaurantORM", back_populates="users")


# ============================================================================
# CATEGORY MODEL
# ============================================================================

class CategoryORM(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    category_id = Column(String(50), unique=True, nullable=False)
    restaurant_id = Column(String(50), ForeignKey("restaurants.restaurant_id", ondelete="CASCADE"), nullable=False, index=True)

    name = Column(String(255), nullable=False)
    slug = Column(String(255), nullable=False)
    icon = Column(String(50))
    description = Column(Text)

    display_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    restaurant = relationship("RestaurantORM", back_populates="categories")
    products = relationship("ProductORM", back_populates="category")


# ============================================================================
# PRODUCT MODEL
# ============================================================================

class ProductORM(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(String(50), unique=True, nullable=False)
    restaurant_id = Column(String(50), ForeignKey("restaurants.restaurant_id", ondelete="CASCADE"), nullable=False, index=True)
    category_id = Column(String(50), ForeignKey("categories.category_id", ondelete="SET NULL"), index=True)

    name = Column(String(255), nullable=False)
    slug = Column(String(255), nullable=False)
    description = Column(Text)

    # Pricing
    price = Column(Numeric(10, 2), nullable=False)
    compare_at_price = Column(Numeric(10, 2))
    cost = Column(Numeric(10, 2))

    # Images
    image_url = Column(Text)
    images = Column(JSONB)

    # Inventory
    track_inventory = Column(Boolean, default=False)
    stock_quantity = Column(Integer, default=0)
    low_stock_threshold = Column(Integer, default=10)

    # Availability
    available = Column(Boolean, default=True, index=True)
    available_start_time = Column(Time)
    available_end_time = Column(Time)

    # Variants and modifiers
    has_variants = Column(Boolean, default=False)
    variants = Column(JSONB)
    modifiers = Column(JSONB)

    # Display
    display_order = Column(Integer, default=0)
    is_featured = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime, nullable=True)

    # Relationships
    restaurant = relationship("RestaurantORM", back_populates="products")
    category = relationship("CategoryORM", back_populates="products")


# ============================================================================
# CUSTOMER MODEL
# ============================================================================

class CustomerORM(Base):
    __tablename__ = "customers"
    __table_args__ = (
        UniqueConstraint('restaurant_id', 'phone', name='uq_customer_restaurant_phone'),
    )

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(String(50), unique=True, nullable=False)
    restaurant_id = Column(String(50), ForeignKey("restaurants.restaurant_id", ondelete="CASCADE"), nullable=False, index=True)

    phone = Column(String(20), nullable=False, index=True)
    name = Column(String(255))
    email = Column(String(255))

    birthday = Column(Date)
    address = Column(Text)
    notes = Column(Text)
    tags = Column(JSONB)

    # Statistics
    total_orders = Column(Integer, default=0)
    total_spent = Column(Numeric(10, 2), default=0)
    average_order_value = Column(Numeric(10, 2), default=0)

    # Timestamps
    first_order_at = Column(DateTime)
    last_order_at = Column(DateTime)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    restaurant = relationship("RestaurantORM", back_populates="customers")
    orders = relationship("OrderORM", back_populates="customer")
    loyalty_account = relationship("LoyaltyAccountORM", back_populates="customer", uselist=False)


# ============================================================================
# ORDER MODEL
# ============================================================================

class OrderORM(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(String(50), unique=True, nullable=False)
    restaurant_id = Column(String(50), ForeignKey("restaurants.restaurant_id", ondelete="CASCADE"), nullable=False, index=True)
    customer_id = Column(String(50), ForeignKey("customers.customer_id", ondelete="SET NULL"), index=True)

    customer_phone = Column(String(20), nullable=False)
    customer_name = Column(String(255))

    items = Column(JSONB, nullable=False)

    # Amounts
    subtotal = Column(Numeric(10, 2), nullable=False)
    discount_amount = Column(Numeric(10, 2), default=0)
    loyalty_discount = Column(Numeric(10, 2), default=0)
    tax_amount = Column(Numeric(10, 2), default=0)
    delivery_fee = Column(Numeric(10, 2), default=0)
    total = Column(Numeric(10, 2), nullable=False)

    # Payment
    payment_method = Column(String(50), nullable=False)
    payment_status = Column(String(50), default="pending")
    payment_details = Column(JSONB)

    # Delivery
    delivery_type = Column(String(50), default="pickup")
    delivery_address = Column(Text)
    delivery_notes = Column(Text)

    # Status
    status = Column(String(50), default="pending", index=True)

    # Notes
    customer_notes = Column(Text)
    internal_notes = Column(Text)

    # Loyalty
    loyalty_points_used = Column(Integer, default=0)
    loyalty_points_earned = Column(Integer, default=0)

    # Source
    source = Column(String(50), default="whatsapp")

    # Timestamps
    confirmed_at = Column(DateTime)
    completed_at = Column(DateTime)
    cancelled_at = Column(DateTime)
    created_at = Column(DateTime, default=func.now(), index=True)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    restaurant = relationship("RestaurantORM", back_populates="orders")
    customer = relationship("CustomerORM", back_populates="orders")


# ============================================================================
# LOYALTY CONFIG MODEL
# ============================================================================

class LoyaltyConfigORM(Base):
    __tablename__ = "loyalty_configs"

    id = Column(Integer, primary_key=True, index=True)
    restaurant_id = Column(String(50), ForeignKey("restaurants.restaurant_id", ondelete="CASCADE"), unique=True, nullable=False)

    enabled = Column(Boolean, default=True)

    points_per_currency = Column(Numeric(5, 2), default=0.1)
    currency_per_point = Column(Numeric(5, 2), default=0.5)

    min_points_to_redeem = Column(Integer, default=100)
    max_redeem_percentage = Column(Numeric(5, 2), default=50.0)
    points_expire_days = Column(Integer, default=365)

    tiers_enabled = Column(Boolean, default=True)
    tier_thresholds = Column(JSONB)
    tier_multipliers = Column(JSONB)
    tier_benefits = Column(JSONB)

    birthday_bonus = Column(Integer, default=100)
    referral_bonus = Column(Integer, default=50)
    first_purchase_bonus = Column(Integer, default=50)

    notify_points_earned = Column(Boolean, default=True)
    notify_tier_upgrade = Column(Boolean, default=True)
    notify_points_expiring = Column(Boolean, default=True)

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    restaurant = relationship("RestaurantORM", back_populates="loyalty_config")


# ============================================================================
# LOYALTY ACCOUNT MODEL
# ============================================================================

class LoyaltyAccountORM(Base):
    __tablename__ = "loyalty_accounts"
    __table_args__ = (
        UniqueConstraint('restaurant_id', 'customer_phone', name='uq_loyalty_restaurant_phone'),
    )

    id = Column(Integer, primary_key=True, index=True)
    restaurant_id = Column(String(50), ForeignKey("restaurants.restaurant_id", ondelete="CASCADE"), nullable=False, index=True)
    customer_id = Column(String(50), ForeignKey("customers.customer_id", ondelete="CASCADE"), nullable=False, index=True)
    customer_phone = Column(String(20), nullable=False)

    points_balance = Column(Integer, default=0)
    points_lifetime = Column(Integer, default=0)
    points_redeemed = Column(Integer, default=0)

    tier_level = Column(String(50), default="bronze")
    tier_progress = Column(Integer, default=0)

    total_spent = Column(Numeric(10, 2), default=0)
    total_orders = Column(Integer, default=0)

    last_earned_at = Column(DateTime)
    last_redeemed_at = Column(DateTime)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    customer = relationship("CustomerORM", back_populates="loyalty_account")


# ============================================================================
# LOYALTY TRANSACTION MODEL
# ============================================================================

class LoyaltyTransactionORM(Base):
    __tablename__ = "loyalty_transactions"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(String(50), unique=True, nullable=False)
    restaurant_id = Column(String(50), ForeignKey("restaurants.restaurant_id", ondelete="CASCADE"), nullable=False, index=True)
    customer_id = Column(String(50), ForeignKey("customers.customer_id", ondelete="CASCADE"), nullable=False, index=True)
    order_id = Column(String(50), ForeignKey("orders.order_id", ondelete="SET NULL"))

    transaction_type = Column(String(50), nullable=False)

    points_amount = Column(Integer, nullable=False)
    points_balance_before = Column(Integer, nullable=False)
    points_balance_after = Column(Integer, nullable=False)

    description = Column(Text)
    metadata = Column(JSONB)

    created_at = Column(DateTime, default=func.now(), index=True)


# ============================================================================
# SESSION MODEL
# ============================================================================

class SessionORM(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), unique=True, nullable=False)
    restaurant_id = Column(String(50), ForeignKey("restaurants.restaurant_id", ondelete="CASCADE"), nullable=False, index=True)

    phone = Column(String(20), nullable=False, index=True)

    state = Column(String(50), default="idle")
    context = Column(JSONB)
    cart = Column(JSONB)

    last_activity_at = Column(DateTime, default=func.now())
    expires_at = Column(DateTime, index=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    restaurant = relationship("RestaurantORM", back_populates="sessions")


# ============================================================================
# PAYMENT METHOD MODEL
# ============================================================================

class PaymentMethodORM(Base):
    __tablename__ = "payment_methods"

    id = Column(Integer, primary_key=True, index=True)
    restaurant_id = Column(String(50), ForeignKey("restaurants.restaurant_id", ondelete="CASCADE"), nullable=False, index=True)

    provider = Column(String(50), nullable=False)
    enabled = Column(Boolean, default=True)

    config = Column(JSONB)

    display_name = Column(String(255))
    icon = Column(String(50))
    instructions = Column(Text)

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
