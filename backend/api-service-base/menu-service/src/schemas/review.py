"""
================================================================================
REVIEW SCHEMAS
================================================================================
Schemas Pydantic para reseñas y calificaciones
================================================================================
"""

from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime


class ReviewCreate(BaseModel):
    """Request para crear reseña"""
    order_id: int
    food_quality: int = Field(..., ge=1, le=5, description="Calificación de comida (1-5)")
    delivery_time: int = Field(..., ge=1, le=5, description="Calificación de tiempo (1-5)")
    service: int = Field(..., ge=1, le=5, description="Calificación de servicio (1-5)")
    comment: Optional[str] = Field(None, max_length=1000, description="Comentario opcional")
    image_url: Optional[str] = None

    @validator('food_quality', 'delivery_time', 'service')
    def validate_rating(cls, v):
        if v < 1 or v > 5:
            raise ValueError('La calificación debe estar entre 1 y 5')
        return v


class ReviewResponse(BaseModel):
    """Response de reseña"""
    id: int
    order_id: int
    user_id: int
    food_quality: int
    delivery_time: int
    service: int
    rating: float
    comment: Optional[str]
    image_url: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class ReviewWithUser(BaseModel):
    """Reseña con información del usuario (para mostrar en productos)"""
    id: int
    user_name: str
    user_id: int
    rating: float
    food_quality: int
    delivery_time: int
    service: int
    comment: Optional[str]
    image_url: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class UploadImageResponse(BaseModel):
    """Response de subida de imagen"""
    success: bool
    image_url: str
    message: str
