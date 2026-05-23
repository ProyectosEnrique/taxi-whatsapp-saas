"""
================================================================================
TENANT MODEL
================================================================================
Modelo para configuración multi-tenant (tiendas)
================================================================================
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, JSON, Text
from sqlalchemy.sql import func
from ..database import Base


class Tenant(Base):
    """Configuración de tienda (tenant)"""

    __tablename__ = "tenants"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(100), unique=True, nullable=False, index=True)

    # Información básica
    name = Column(String(200), nullable=False)
    business_name = Column(String(200), nullable=True)  # Razón social
    description = Column(Text, nullable=True)
    slogan = Column(String(300), nullable=True)

    # Branding
    logo_url = Column(String(500), nullable=True)
    primary_color = Column(String(7), default="#3b82f6")  # Hex color
    secondary_color = Column(String(7), default="#1d4ed8")

    # Contacto
    phone = Column(String(20), nullable=False)
    email = Column(String(200), nullable=False)
    whatsapp_number = Column(String(20), nullable=True)

    # Dirección
    address = Column(JSON, nullable=True)  # {street, city, state, zip}

    # Configuración de la tienda
    settings = Column(JSON, nullable=True)  # {
    #   "currency": "MXN",
    #   "min_order_amount": 100,
    #   "delivery_zones": [...],
    #   "business_hours": {...},
    #   "payment_methods": ["cash", "card", "transfer"]
    # }

    # Redes sociales
    social_media = Column(JSON, nullable=True)  # {facebook, instagram, twitter}

    # Estado
    is_active = Column(Boolean, default=True)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<Tenant {self.tenant_id}: {self.name}>"

    def to_dict(self):
        """Convertir a diccionario"""
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "name": self.name,
            "business_name": self.business_name,
            "description": self.description,
            "slogan": self.slogan,
            "logo_url": self.logo_url,
            "primary_color": self.primary_color,
            "secondary_color": self.secondary_color,
            "phone": self.phone,
            "email": self.email,
            "whatsapp_number": self.whatsapp_number,
            "address": self.address,
            "settings": self.settings,
            "social_media": self.social_media,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
