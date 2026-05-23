"""
================================================================================
TENANT SCHEMAS
================================================================================
Schemas Pydantic para tenants (tiendas)
================================================================================
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


class TenantCreate(BaseModel):
    """Schema para crear un nuevo tenant"""
    tenant_id: str = Field(..., min_length=3, max_length=100, description="ID único del tenant (slug)")
    name: str = Field(..., min_length=1, max_length=200, description="Nombre de la tienda")
    business_name: Optional[str] = None
    description: Optional[str] = None
    slogan: Optional[str] = None
    logo_url: Optional[str] = None
    primary_color: str = "#3b82f6"
    secondary_color: str = "#10b981"
    phone: str
    email: str
    whatsapp_number: Optional[str] = None
    address: Optional[Dict[str, Any]] = None
    settings: Optional[Dict[str, Any]] = None
    social_media: Optional[Dict[str, Any]] = None
    is_active: bool = True


class TenantUpdate(BaseModel):
    """Schema para actualizar un tenant"""
    name: Optional[str] = None
    business_name: Optional[str] = None
    description: Optional[str] = None
    slogan: Optional[str] = None
    logo_url: Optional[str] = None
    primary_color: Optional[str] = None
    secondary_color: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    whatsapp_number: Optional[str] = None
    address: Optional[Dict[str, Any]] = None
    settings: Optional[Dict[str, Any]] = None
    social_media: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class TenantResponse(BaseModel):
    """Response con información del tenant"""
    id: int
    tenant_id: str
    name: str
    business_name: Optional[str]
    description: Optional[str]
    slogan: Optional[str]
    logo_url: Optional[str]
    primary_color: str
    secondary_color: str
    phone: str
    email: str
    whatsapp_number: Optional[str]
    address: Optional[Dict[str, Any]]
    settings: Optional[Dict[str, Any]]
    social_media: Optional[Dict[str, Any]]
    is_active: bool
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class TenantSettingsResponse(BaseModel):
    """Response solo con settings del tenant"""
    tenant_id: str
    name: str
    settings: Dict[str, Any]
    business_hours: Optional[Dict[str, Any]]
    delivery_zones: Optional[list]
    payment_methods: Optional[list]
    min_order_amount: Optional[float]

    class Config:
        from_attributes = True
