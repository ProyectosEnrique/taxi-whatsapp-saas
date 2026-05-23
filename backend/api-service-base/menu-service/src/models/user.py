"""
================================================================================
USER MODEL
================================================================================
Modelo de usuario para autenticación y gestión de cuentas
================================================================================
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..database import Base


class User(Base):
    """Usuario del sistema multi-tenant"""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(100), nullable=False, index=True)  # Multi-tenant

    # Información personal
    name = Column(String(200), nullable=False)
    email = Column(String(200), unique=True, nullable=False, index=True)
    phone = Column(String(20), unique=True, nullable=False, index=True)

    # Autenticación
    password_hash = Column(String(255), nullable=False)

    # Estados
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)

    # Relaciones
    addresses = relationship("Address", back_populates="user", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="customer")
    reviews = relationship("Review", back_populates="user")
    loyalty_account = relationship("LoyaltyAccount", back_populates="user", uselist=False)
    roles = relationship("Role", secondary="user_roles", back_populates="users")

    def __repr__(self):
        return f"<User {self.email}>"

    def to_dict(self):
        """Convertir a diccionario (sin password)"""
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "is_active": self.is_active,
            "is_verified": self.is_verified,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None
        }

    def has_role(self, role_type: str) -> bool:
        """Verificar si el usuario tiene un rol específico"""
        return any(role.role_type == role_type for role in self.roles)

    def is_admin(self) -> bool:
        """Verificar si el usuario es administrador"""
        return any(role.role_type in ["super_admin", "admin"] for role in self.roles)

    def is_super_admin(self) -> bool:
        """Verificar si el usuario es super administrador"""
        return any(role.role_type == "super_admin" for role in self.roles)

    def is_staff_or_above(self) -> bool:
        """Verificar si el usuario es staff o superior"""
        return any(role.role_type in ["super_admin", "admin", "staff"] for role in self.roles)

    def get_role_types(self) -> list:
        """Obtener lista de tipos de roles del usuario"""
        return [role.role_type for role in self.roles]
