"""
================================================================================
MODELS - Menu Service
================================================================================
Modelos SQLAlchemy para categorias y productos
================================================================================
"""

from sqlalchemy import Column, Integer, String, Text, Numeric, Boolean, DateTime, ForeignKey, Time, Table
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
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
    tenant_id = Column(String(100), nullable=False, index=True)  # Multi-tenant support
    name = Column(String(100), nullable=False, index=True)  # REMOVIDO unique=True para permitir mismo nombre en diferentes tenants
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
    tenant_id = Column(String(100), nullable=False, index=True)  # Multi-tenant support
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
    tenant_id = Column(String(100), nullable=False, index=True)  # Multi-tenant support

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
