"""
================================================================================
ADDRESS SCHEMAS
================================================================================
Schemas Pydantic para direcciones
================================================================================
"""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class AddressCreate(BaseModel):
    """Request para crear dirección"""
    label: str
    street: str
    neighborhood: str
    city: str
    state: str
    zip_code: Optional[str] = None
    country: str = "México"
    reference: Optional[str] = None
    latitude: Optional[str] = None
    longitude: Optional[str] = None
    is_default: bool = False


class AddressUpdate(BaseModel):
    """Request para actualizar dirección"""
    label: Optional[str] = None
    street: Optional[str] = None
    neighborhood: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    country: Optional[str] = None
    reference: Optional[str] = None
    latitude: Optional[str] = None
    longitude: Optional[str] = None


class AddressResponse(BaseModel):
    """Response de dirección"""
    id: int
    user_id: int
    label: str
    street: str
    neighborhood: str
    city: str
    state: str
    zip_code: Optional[str]
    country: str
    reference: Optional[str]
    latitude: Optional[str]
    longitude: Optional[str]
    is_default: bool
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True
