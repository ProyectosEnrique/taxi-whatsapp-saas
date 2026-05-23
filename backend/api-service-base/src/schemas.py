"""
================================================================================
SCHEMAS - Menu Service
================================================================================
Schemas Pydantic para validacion y serializacion
================================================================================
"""

from __future__ import annotations

from pydantic import BaseModel, Field, ConfigDict, field_serializer, field_validator
from typing import Optional, Any, Literal, List
from datetime import datetime, time
from decimal import Decimal
from uuid import UUID

# ==============================================================================
# CATEGORY SCHEMAS
# ==============================================================================

class CategoryBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Nombre de la categoria")
    description: Optional[str] = Field(None, description="Descripcion de la categoria")
    display_order: int = Field(default=0, description="Orden de visualizacion")
    is_active: bool = Field(default=True, description="Si la categoria esta activa")
    is_beverage: bool = Field(default=False, description="Si es categoria de bebidas")


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    display_order: Optional[int] = None
    is_active: Optional[bool] = None
    is_beverage: Optional[bool] = None


class CategoryResponse(CategoryBase):
    id: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class CategoryWithProducts(CategoryResponse):
    products: list["ProductResponse"] = []
    model_config = ConfigDict(from_attributes=True)


# ==============================================================================
# PRODUCT SCHEMAS
# ==============================================================================

class ProductBase(BaseModel):
    category_id: Optional[int] = Field(None, description="ID de la categoria")
    name: str = Field(..., min_length=1, max_length=255, description="Nombre del producto")
    description: Optional[str] = Field(None, description="Descripcion del producto")
    price: Decimal = Field(..., gt=0, description="Precio del producto")
    image_url: Optional[str] = Field(None, max_length=500, description="URL de la imagen")
    video_url: Optional[str] = Field(None, max_length=500, description="URL del video")
    is_available: bool = Field(default=True, description="Si el producto esta disponible")
    ingredients: Optional[str] = Field(None, description="Ingredientes principales")
    spice_level: int = Field(default=0, ge=0, le=3, description="Nivel de picante: 0-3")
    preparation_time_minutes: int = Field(default=15, ge=0, description="Tiempo de preparacion")
    popularity: int = Field(default=3, ge=1, le=5, description="Popularidad: 1-5")
    profitability: str = Field(default="media", description="Rentabilidad: alta/media/baja")
    cost: Optional[Decimal] = Field(None, ge=0, description="Costo del platillo")
    menu_classification: Optional[str] = Field(None, description="estrella/caballo/perro/rompecabezas")


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    category_id: Optional[int] = None
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    price: Optional[Decimal] = Field(None, gt=0)
    image_url: Optional[str] = Field(None, max_length=500)
    video_url: Optional[str] = Field(None, max_length=500)
    is_available: Optional[bool] = None
    ingredients: Optional[str] = None
    spice_level: Optional[int] = Field(None, ge=0, le=3)
    preparation_time_minutes: Optional[int] = Field(None, ge=0)
    popularity: Optional[int] = Field(None, ge=1, le=5)
    profitability: Optional[str] = None
    cost: Optional[Decimal] = Field(None, ge=0)
    menu_classification: Optional[str] = None


class ProductResponse(ProductBase):
    id: int
    uuid: str
    created_at: datetime
    updated_at: datetime
    category: Optional[CategoryResponse] = None
    model_config = ConfigDict(from_attributes=True)

    @field_validator("uuid", mode="before")
    @classmethod
    def convert_uuid_to_str(cls, value: Any) -> str:
        if isinstance(value, UUID):
            return str(value)
        return value


class ProductSummaryForAgent(BaseModel):
    id: int
    name: str
    price: Decimal
    description: Optional[str] = None
    ingredients: Optional[str] = None
    spice_level: int = 0
    preparation_time_minutes: int = 15
    is_available: bool = True
    popularity: int = 3
    profitability: str = "media"
    menu_classification: Optional[str] = None
    category_name: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


# ==============================================================================
# META COMMERCE CATALOG SCHEMAS
# ==============================================================================

class ProductMetaSync(BaseModel):
    """Schema para actualizar campos de sincronizacion con Meta Commerce"""
    product_retailer_id: Optional[str] = Field(None, max_length=100, description="ID del producto en catalogo Meta")
    meta_image_id: Optional[str] = Field(None, max_length=100, description="ID de imagen en Meta")
    meta_sync_status: Optional[str] = Field(None, description="Estado: pending, synced, error")
    meta_sync_error: Optional[str] = Field(None, description="Ultimo error de sincronizacion")


class ProductResponseWithMeta(ProductResponse):
    """Respuesta de producto incluyendo campos de Meta Commerce"""
    product_retailer_id: Optional[str] = None
    meta_image_id: Optional[str] = None
    meta_sync_status: str = "pending"
    meta_last_sync: Optional[datetime] = None
    meta_sync_error: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class MetaSyncStatusResponse(BaseModel):
    """Estado de sincronizacion con Meta Commerce"""
    stats: dict = Field(..., description="Estadisticas por estado: {pending: N, synced: N, error: N}")
    recent_errors: List[dict] = Field(default=[], description="Errores recientes")


class ProductForCatalog(BaseModel):
    """Producto formateado para sincronizacion con catalogo Meta"""
    id: int
    product_retailer_id: str
    name: str
    description: Optional[str] = None
    price: Decimal
    currency: str = "MXN"
    image_url: Optional[str] = None
    is_available: bool = True
    category_name: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


# ==============================================================================
# PAGINATION SCHEMAS
# ==============================================================================

class PaginationParams(BaseModel):
    skip: int = Field(default=0, ge=0, description="Numero de registros a saltar")
    limit: int = Field(default=100, ge=1, le=500, description="Numero de registros a retornar")


class PaginatedResponse(BaseModel):
    total: int = Field(..., description="Total de registros")
    skip: int = Field(..., description="Registros saltados")
    limit: int = Field(..., description="Limite de registros")
    items: list = Field(..., description="Items de la pagina")


# ==============================================================================
# ERROR SCHEMAS
# ==============================================================================

class ErrorResponse(BaseModel):
    error: str = Field(..., description="Tipo de error")
    message: str = Field(..., description="Mensaje de error")
    details: Optional[dict] = Field(None, description="Detalles adicionales del error")
    correlation_id: Optional[str] = Field(None, description="ID de correlacion")


# ==============================================================================
# HEALTH CHECK SCHEMA
# ==============================================================================

class HealthResponse(BaseModel):
    status: str = Field(..., description="Estado del servicio")
    service: str = Field(..., description="Nombre del servicio")
    version: Optional[str] = Field(None, description="Version del servicio")
    timestamp: datetime = Field(..., description="Timestamp del health check")


# ==============================================================================
# PROMOTION SCHEMAS
# ==============================================================================

class PromotionBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Nombre de la promocion")
    description: Optional[str] = Field(None, description="Descripcion de la promocion")
    promotion_type: str = Field(
        default="percentage",
        description="Tipo: percentage, fixed, 2x1, combo, buy_x_get_y"
    )
    discount_value: Optional[Decimal] = Field(None, ge=0, description="Valor del descuento")
    buy_quantity: int = Field(default=1, ge=1, description="Cantidad a comprar (para buy_x_get_y)")
    get_quantity: int = Field(default=1, ge=1, description="Cantidad que recibe (para buy_x_get_y)")
    special_price: Optional[Decimal] = Field(None, ge=0, description="Precio especial para combos")
    start_date: Optional[datetime] = Field(None, description="Fecha de inicio")
    end_date: Optional[datetime] = Field(None, description="Fecha de fin")
    start_time: Optional[time] = Field(None, description="Hora de inicio (ej: 14:00)")
    end_time: Optional[time] = Field(None, description="Hora de fin (ej: 18:00)")
    days_of_week: Optional[str] = Field(None, description="Dias: lunes,martes,miercoles...")
    is_active: bool = Field(default=True, description="Si la promocion esta activa")
    voice_pitch: Optional[str] = Field(None, description="Frase para el agente de ventas")
    priority: int = Field(default=1, ge=1, le=5, description="Prioridad 1-5")


class PromotionCreate(PromotionBase):
    product_ids: Optional[List[int]] = Field(None, description="IDs de productos aplicables")


class PromotionUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    promotion_type: Optional[str] = None
    discount_value: Optional[Decimal] = Field(None, ge=0)
    buy_quantity: Optional[int] = Field(None, ge=1)
    get_quantity: Optional[int] = Field(None, ge=1)
    special_price: Optional[Decimal] = Field(None, ge=0)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    days_of_week: Optional[str] = None
    is_active: Optional[bool] = None
    voice_pitch: Optional[str] = None
    priority: Optional[int] = Field(None, ge=1, le=5)
    product_ids: Optional[List[int]] = None


class ProductSummary(BaseModel):
    """Resumen de producto para incluir en promocion"""
    id: int
    name: str
    price: Decimal
    model_config = ConfigDict(from_attributes=True)


class PromotionResponse(PromotionBase):
    id: int
    times_used: int = 0
    created_at: datetime
    updated_at: datetime
    products: List[ProductSummary] = []
    model_config = ConfigDict(from_attributes=True)


class PromotionForAgent(BaseModel):
    """Promocion formateada para el agente de ventas"""
    id: int
    name: str
    description: Optional[str] = None
    promotion_type: str
    discount_value: Optional[Decimal] = None
    special_price: Optional[Decimal] = None
    voice_pitch: Optional[str] = None
    product_names: List[str] = []
    model_config = ConfigDict(from_attributes=True)


# Rebuild models to resolve forward references
CategoryWithProducts.model_rebuild()
ProductResponse.model_rebuild()
ProductResponseWithMeta.model_rebuild()
PromotionResponse.model_rebuild()
