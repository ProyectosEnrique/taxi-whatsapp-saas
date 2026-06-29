"""
================================================================================
MODELS - Menu Service
================================================================================
Modelos SQLAlchemy para categorias y productos
================================================================================
"""

from sqlalchemy import Column, Integer, String, Text, Numeric, Boolean, DateTime, ForeignKey, Time, Table, Enum as SAEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import enum
import uuid

from .database import Base


# ==============================================================================
# ASSOCIATION TABLE: PROMOTION <-> PRODUCT (Many-to-Many)
# ==============================================================================

promotion_products = Table(
    'promotion_products',
    Base.metadata,
    Column('promotion_id', Integer, ForeignKey('promotions.id', ondelete='CASCADE'), primary_key=True),
    Column('product_id', Integer, ForeignKey('products.id', ondelete='CASCADE'), primary_key=True)
)

# ==============================================================================
# CATEGORY MODEL
# ==============================================================================

class Category(Base):
    """Modelo de categoria de productos"""

    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text)
    display_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True, index=True)
    is_beverage = Column(Boolean, default=False, index=True)  # Para separar bebidas de comidas

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    products = relationship("Product", back_populates="category")

    def __repr__(self):
        return f"<Category(id={self.id}, name='{self.name}')>"


# ==============================================================================
# PRODUCT MODEL
# ==============================================================================

class Product(Base):
    """Modelo de producto del menu"""

    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String(36), unique=True, nullable=False, index=True, default=lambda: str(uuid.uuid4()))
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="SET NULL"))

    # Informacion basica
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text)
    price = Column(Numeric(10, 2), nullable=False)
    image_url = Column(String(500))
    video_url = Column(String(500))  # Video para platillos estrella
    is_available = Column(Boolean, default=True, index=True)

    # Informacion para el agente de ventas
    ingredients = Column(Text)  # Ingredientes principales (para alergias/preferencias)
    spice_level = Column(Integer, default=0)  # 0=nada, 1=bajo, 2=medio, 3=alto
    preparation_time_minutes = Column(Integer, default=15)

    # Ingenieria del menu
    popularity = Column(Integer, default=3)  # 1-5 (1=poco pedido, 5=muy pedido)
    profitability = Column(String(10), default='media')  # alta, media, baja
    cost = Column(Numeric(10, 2))  # Costo del platillo
    menu_classification = Column(String(20))  # estrella, caballo, perro, rompecabezas

    # Integracion con Meta Commerce (WhatsApp Catalog)
    product_retailer_id = Column(String(100), unique=True, nullable=True, index=True)  # ID unico en catalogo Meta
    meta_image_id = Column(String(100), nullable=True)  # ID de imagen subida a Meta
    meta_sync_status = Column(String(20), default='pending', index=True)  # pending, synced, error
    meta_last_sync = Column(DateTime(timezone=True), nullable=True)  # Ultima sincronizacion
    meta_sync_error = Column(Text, nullable=True)  # Ultimo error de sincronizacion

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    category = relationship("Category", back_populates="products")

    def __repr__(self):
        return f"<Product(id={self.id}, name='{self.name}', price={self.price})>"


# ==============================================================================
# PROMOTION MODEL
# ==============================================================================

class Promotion(Base):
    """Modelo de promocion del restaurante"""

    __tablename__ = "promotions"

    id = Column(Integer, primary_key=True, index=True)

    # Informacion basica
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text)

    # Tipo de promocion
    # - percentage: Descuento porcentual (ej: 20% de descuento)
    # - fixed: Descuento fijo (ej: $50 pesos de descuento)
    # - 2x1: Dos por uno
    # - combo: Precio especial de combo
    # - buy_x_get_y: Compra X y lleva Y gratis/con descuento
    promotion_type = Column(String(20), nullable=False, default='percentage')

    # Valor del descuento (segun tipo)
    discount_value = Column(Numeric(10, 2))  # Porcentaje o cantidad fija

    # Para promociones tipo buy_x_get_y
    buy_quantity = Column(Integer, default=1)  # Cantidad a comprar
    get_quantity = Column(Integer, default=1)  # Cantidad que recibe

    # Precio especial para combos
    special_price = Column(Numeric(10, 2))

    # Vigencia por fecha
    start_date = Column(DateTime(timezone=True))
    end_date = Column(DateTime(timezone=True))

    # Horario de aplicacion (opcional)
    # Permite definir promociones solo en ciertos horarios
    start_time = Column(Time)  # Hora de inicio (ej: 14:00)
    end_time = Column(Time)    # Hora de fin (ej: 18:00)

    # Dias de la semana (comma-separated: "lunes,martes,miercoles")
    # Si es NULL, aplica todos los dias
    days_of_week = Column(String(100))

    # Estado
    is_active = Column(Boolean, default=True, index=True)

    # Para el agente de ventas
    voice_pitch = Column(Text)  # Frase sugerida para el agente (ej: "Hoy tenemos 2x1 en hamburguesas!")
    priority = Column(Integer, default=1)  # 1-5, mayor prioridad = mencionar primero

    # Estadisticas
    times_used = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    products = relationship("Product", secondary=promotion_products, backref="promotions")

    def __repr__(self):
        return f"<Promotion(id={self.id}, name='{self.name}', type='{self.promotion_type}')>"


# ==============================================================================
# PRODUCT ALIAS MODEL - Para reconocimiento de voz
# ==============================================================================

class ProductAlias(Base):
    """
    Modelo de aliases de productos para reconocimiento de voz.

    Permite que el agente de ventas reconozca múltiples formas de referirse
    a un mismo producto. Los aliases pueden ser:
    - Generados automáticamente (is_auto_generated=True)
    - Configurados manualmente (is_auto_generated=False)

    Ejemplos:
    - "Taco de Suadero" -> aliases: "suadero", "tacos de suadero", "taco suadero"
    - "Hamburguesa Clásica" -> aliases: "hamburguesa", "clasica", "hamburguesas"
    """

    __tablename__ = "product_aliases"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)

    # El alias normalizado (lowercase, sin acentos)
    alias = Column(String(100), nullable=False, index=True)

    # Alias original (con acentos y mayúsculas originales)
    alias_original = Column(String(100))

    # Tipo de alias para priorización
    # - exact: Coincidencia exacta del nombre
    # - partial: Parte del nombre (ej: "suadero" de "Taco de Suadero")
    # - colloquial: Forma coloquial (ej: "clasica" para "Hamburguesa Clásica")
    # - abbreviation: Abreviatura (ej: "bbq" para "BBQ")
    alias_type = Column(String(20), default='colloquial')

    # Prioridad para desambiguación (mayor = más preferido)
    priority = Column(Integer, default=1)

    # Si fue generado automáticamente
    is_auto_generated = Column(Boolean, default=True)

    # Activo/inactivo
    is_active = Column(Boolean, default=True, index=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationship
    product = relationship("Product", backref="aliases")

    def __repr__(self):
        return f"<ProductAlias(alias='{self.alias}', product_id={self.product_id})>"


# ==============================================================================
# TAXI GROUP MODEL — Flota / empresa de taxis
# ==============================================================================

class TaxiGroup(Base):
    __tablename__ = "taxi_groups"

    id              = Column(Integer, primary_key=True, index=True)
    name            = Column(String(150), nullable=False)
    whatsapp_number = Column(String(30), nullable=False)   # e.g. "+15551234567"
    is_active       = Column(Boolean, default=True)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())

    drivers = relationship("Driver", back_populates="group")

    def __repr__(self):
        return f"<TaxiGroup(id={self.id}, name='{self.name}')>"


# ==============================================================================
# TRIP MODEL — Viajes de taxi con soporte de pago MercadoPago
# ==============================================================================

class TripStatus(str, enum.Enum):
    SCHEDULED        = "scheduled"
    DRIVER_RELEASED  = "driver_released"
    REQUESTED        = "requested"
    CONFIRMED        = "confirmed"
    DRIVER_ARRIVED   = "driver_arrived"
    IN_PROGRESS      = "in_progress"
    COMPLETED        = "completed"
    CANCELLED        = "cancelled"


class Trip(Base):
    __tablename__ = "trips"

    id         = Column(Integer, primary_key=True, index=True)
    trip_id    = Column(String(50), unique=True, nullable=False, index=True,
                        default=lambda: f"TRIP-{uuid.uuid4().hex[:8].upper()}")

    # Pasajero
    customer_phone = Column(String(30), nullable=False, index=True)
    customer_name  = Column(String(150))

    # Ruta
    origin_address      = Column(String(500))
    destination_address = Column(String(500))
    origin_lat          = Column(Numeric(10, 7))
    origin_lng          = Column(Numeric(10, 7))
    destination_lat     = Column(Numeric(10, 7))
    destination_lng     = Column(Numeric(10, 7))

    # Tarifa
    fare        = Column(Numeric(10, 2), nullable=False, default=0)
    distance_km = Column(Numeric(8, 2))

    # Pago
    payment_method   = Column(String(20), default="cash")   # cash | card
    payment_status   = Column(String(30), default="pending") # pending | pending_payment | paid | failed
    mp_preference_id = Column(String(255))
    mp_payment_id    = Column(String(100))

    # Viaje programado
    scheduled_at           = Column(DateTime(timezone=True), nullable=True)
    preferred_driver_phone = Column(String(30),  nullable=True)
    preferred_driver_name  = Column(String(150), nullable=True)
    driver_released_at     = Column(DateTime(timezone=True), nullable=True)
    last_notified_at       = Column(DateTime(timezone=True), nullable=True)   # ride timeout monitor

    # Estado del viaje
    status             = Column(SAEnum(TripStatus), default=TripStatus.REQUESTED, index=True)
    cancellation_reason = Column(Text)
    cancelled_at       = Column(DateTime(timezone=True))

    # Conductor asignado (opcional — puede ser None hasta asignación)
    driver_id   = Column(Integer)
    driver_name = Column(String(150))
    driver_phone = Column(String(30))

    # Calificación del cliente (1-5)
    customer_rating = Column(Integer, nullable=True)

    # Timestamps
    created_at   = Column(DateTime(timezone=True), server_default=func.now())
    updated_at   = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True))

    def __repr__(self):
        return f"<Trip(trip_id='{self.trip_id}', status='{self.status}', fare={self.fare})>"


# ==============================================================================
# CUSTOMER MODEL
# ==============================================================================

class Customer(Base):
    __tablename__ = "customers"

    id           = Column(Integer, primary_key=True, index=True)
    phone        = Column(String(30), unique=True, nullable=False, index=True)
    name         = Column(String(150))
    email        = Column(String(150))
    password_hash       = Column(String(255), nullable=False)
    is_active           = Column(Boolean, default=True)
    preferred_driver_id = Column(Integer, ForeignKey("drivers.id"), nullable=True)

    # Contacto de emergencia
    emergency_contact_name        = Column(String(150), nullable=True)
    emergency_contact_phone       = Column(String(30),  nullable=True)
    emergency_contact_telegram_id = Column(String(50),  nullable=True)  # chat_id de Telegram

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<Customer(phone='{self.phone}', name='{self.name}')>"


# ==============================================================================
# DRIVER MODEL
# ==============================================================================

class Driver(Base):
    __tablename__ = "drivers"

    id           = Column(Integer, primary_key=True, index=True)
    phone        = Column(String(30), unique=True, nullable=False, index=True)
    name         = Column(String(150), nullable=False)
    password_hash = Column(String(255), nullable=False)
    is_active    = Column(Boolean, default=True)
    is_online    = Column(Boolean, default=False, index=True)

    # Ubicación en tiempo real
    current_lat  = Column(Numeric(10, 7))
    current_lng  = Column(Numeric(10, 7))

    # Vehículo
    vehicle_brand     = Column(String(100))
    vehicle_model     = Column(String(100))
    vehicle_plates    = Column(String(20))
    vehicle_color     = Column(String(50))
    vehicle_year      = Column(Integer)
    vehicle_photo_url = Column(String(255), nullable=True)

    # Estadísticas
    rating         = Column(Numeric(3, 2), default=5.00)
    total_trips    = Column(Integer, default=0)
    total_earnings = Column(Numeric(10, 2), default=0)

    # QR / flota
    driver_code = Column(String(30), unique=True, index=True)  # slug para URL: "carlos-a1b2"
    group_id    = Column(Integer, ForeignKey("taxi_groups.id"), nullable=True)
    group       = relationship("TaxiGroup", back_populates="drivers")

    # Contacto de emergencia
    emergency_contact_name        = Column(String(150), nullable=True)
    emergency_contact_phone       = Column(String(30),  nullable=True)
    emergency_contact_telegram_id = Column(String(50),  nullable=True)

    # Propio Telegram del chofer — para notificaciones de viajes y aceptar vía bot
    telegram_chat_id = Column(String(50), nullable=True, index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<Driver(phone='{self.phone}', name='{self.name}', online={self.is_online})>"


# ==============================================================================
# TRIP RATING MODEL
# ==============================================================================

class Incident(Base):
    __tablename__ = "incidents"

    id             = Column(Integer, primary_key=True, index=True)
    incident_id    = Column(String(50), unique=True, nullable=False, index=True,
                            default=lambda: f"INC-{uuid.uuid4().hex[:8].upper()}")
    trip_id        = Column(String(50), nullable=True)
    reporter_type  = Column(String(20), nullable=False)   # "driver" | "customer"
    reporter_phone = Column(String(30), nullable=False)
    reporter_name  = Column(String(150))
    lat            = Column(Numeric(10, 7), nullable=True)
    lng            = Column(Numeric(10, 7), nullable=True)
    notes          = Column(Text, nullable=True)
    status         = Column(String(20), default="active")  # active | resolved

    # Mejoras SOS
    audio_url           = Column(String(500), nullable=True)   # ruta al audio grabado
    escalated           = Column(Boolean, default=False)       # si ya se escaló (dead man's switch)
    last_location_lat   = Column(Numeric(10, 7), nullable=True)  # GPS en vivo
    last_location_lng   = Column(Numeric(10, 7), nullable=True)
    last_location_at    = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<Incident(incident_id='{self.incident_id}', reporter='{self.reporter_phone}')>"


# ==============================================================================
# FARE CONFIG MODEL — fila única (id=1), configurable desde panel admin
# ==============================================================================

class FareConfig(Base):
    __tablename__ = "fare_config"

    id              = Column(Integer, primary_key=True, default=1)

    # Tarifas base
    base_fare       = Column(Numeric(10, 2), default=50.0)
    per_km_rate     = Column(Numeric(10, 2), default=8.0)
    per_minute_rate = Column(Numeric(10, 2), default=2.0)
    minimum_fare    = Column(Numeric(10, 2), default=70.0)

    # Surge pricing
    surge_enabled          = Column(Boolean, default=False)
    surge_peak_multiplier  = Column(Numeric(4, 2), default=1.3)  # 7-9am, 6-9pm
    surge_night_multiplier = Column(Numeric(4, 2), default=1.5)  # 11pm-5am
    surge_weekend_multiplier = Column(Numeric(4, 2), default=1.2)

    # Recargos especiales
    charge_airport_pickup  = Column(Numeric(10, 2), default=30.0)
    charge_airport_dropoff = Column(Numeric(10, 2), default=30.0)
    charge_extra_passenger = Column(Numeric(10, 2), default=10.0)
    charge_luggage         = Column(Numeric(10, 2), default=5.0)

    # Descuentos (fracción: 0.10 = 10%)
    discount_frequent_rider = Column(Numeric(4, 3), default=0.10)
    discount_corporate      = Column(Numeric(4, 3), default=0.15)

    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<FareConfig(base={self.base_fare}, per_km={self.per_km_rate})>"


class PromoCode(Base):
    __tablename__ = "promo_codes"

    id           = Column(Integer, primary_key=True, index=True)
    code         = Column(String(50), unique=True, nullable=False, index=True)
    discount_pct = Column(Numeric(4, 3), default=0.10)   # 0.0 – 1.0
    description  = Column(String(200), default="")
    is_active    = Column(Boolean, default=True)
    max_uses     = Column(Integer, default=0)             # 0 = ilimitado
    used_count   = Column(Integer, default=0)
    expires_at   = Column(DateTime(timezone=True), nullable=True)
    created_at   = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<PromoCode(code='{self.code}', discount={self.discount_pct})>"


class TripRating(Base):
    __tablename__ = "trip_ratings"

    id        = Column(Integer, primary_key=True, index=True)
    trip_id   = Column(String(50), ForeignKey("trips.trip_id"), unique=True, nullable=False)
    stars     = Column(Integer, nullable=False)  # 1-5
    comment   = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<TripRating(trip_id='{self.trip_id}', stars={self.stars})>"


# ==============================================================================
# LOCAL POI MODEL
# ==============================================================================

class LocalPOI(Base):
    """Lugares locales agregados por conductores/admin que Google Maps no conoce."""
    __tablename__ = "local_pois"

    id         = Column(Integer, primary_key=True, index=True)
    name       = Column(String(200), nullable=False, index=True)   # "El Arco", "La Feria"
    address    = Column(String(500))
    lat        = Column(Numeric(10, 7), nullable=False)
    lng        = Column(Numeric(10, 7), nullable=False)
    added_by   = Column(String(50), default="admin")               # "driver" | "admin"
    is_active  = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<LocalPOI(name='{self.name}', lat={self.lat}, lng={self.lng})>"
