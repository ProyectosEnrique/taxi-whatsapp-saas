"""
================================================================================
ADDRESS MODEL
================================================================================
Modelo para direcciones de entrega de usuarios
================================================================================
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..database import Base


class Address(Base):
    """Dirección de entrega del usuario"""

    __tablename__ = "addresses"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Etiqueta personalizada
    label = Column(String(100), nullable=False)  # Casa, Oficina, Casa de mamá, etc.

    # Dirección completa
    street = Column(String(300), nullable=False)
    neighborhood = Column(String(200), nullable=False)
    city = Column(String(100), nullable=False)
    state = Column(String(100), nullable=False)
    zip_code = Column(String(10), nullable=True)
    country = Column(String(100), default="México")

    # Referencia adicional
    reference = Column(Text, nullable=True)  # Entre calles, color de casa, etc.

    # GPS coordinates (para futuro)
    latitude = Column(String(50), nullable=True)
    longitude = Column(String(50), nullable=True)

    # Dirección predeterminada
    is_default = Column(Boolean, default=False)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relaciones
    user = relationship("User", back_populates="addresses")

    def __repr__(self):
        return f"<Address {self.label}: {self.street}>"

    def to_dict(self):
        """Convertir a diccionario"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "label": self.label,
            "street": self.street,
            "neighborhood": self.neighborhood,
            "city": self.city,
            "state": self.state,
            "zip_code": self.zip_code,
            "country": self.country,
            "reference": self.reference,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "is_default": self.is_default,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
