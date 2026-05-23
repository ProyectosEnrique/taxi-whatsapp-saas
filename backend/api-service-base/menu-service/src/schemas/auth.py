"""
================================================================================
AUTH SCHEMAS
================================================================================
Schemas Pydantic para autenticación
================================================================================
"""

from pydantic import BaseModel, EmailStr, validator
from typing import Optional
from datetime import datetime


class RegisterRequest(BaseModel):
    """Request para registro de usuario"""
    tenant_id: str
    name: str
    email: EmailStr
    phone: str
    password: str
    confirm_password: str

    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('La contraseña debe tener al menos 8 caracteres')
        return v

    @validator('confirm_password')
    def passwords_match(cls, v, values):
        if 'password' in values and v != values['password']:
            raise ValueError('Las contraseñas no coinciden')
        return v

    @validator('phone')
    def validate_phone(cls, v):
        # Remover espacios y caracteres especiales
        phone = v.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
        if not phone.startswith('+'):
            phone = '+' + phone
        return phone


class LoginRequest(BaseModel):
    """Request para login"""
    email: EmailStr
    password: str
    tenant_id: Optional[str] = None  # Opcional si se detecta automáticamente


class LoginResponse(BaseModel):
    """Response de login exitoso"""
    success: bool
    access_token: str
    token_type: str = "bearer"
    user: dict


class UserResponse(BaseModel):
    """Response con información del usuario"""
    id: int
    tenant_id: str
    name: str
    email: str
    phone: str
    is_active: bool
    is_verified: bool
    created_at: Optional[datetime]
    last_login: Optional[datetime]

    class Config:
        from_attributes = True


class UpdateProfileRequest(BaseModel):
    """Request para actualizar perfil"""
    name: Optional[str] = None
    phone: Optional[str] = None


class ChangePasswordRequest(BaseModel):
    """Request para cambiar contraseña"""
    current_password: str
    new_password: str
    confirm_password: str

    @validator('new_password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('La contraseña debe tener al menos 8 caracteres')
        return v

    @validator('confirm_password')
    def passwords_match(cls, v, values):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Las contraseñas no coinciden')
        return v
