"""
================================================================================
ROLE MODEL
================================================================================
Modelo para roles y permisos de usuarios
================================================================================
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Table, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..database import Base
import enum


class RoleType(str, enum.Enum):
    """Tipos de roles en el sistema"""
    SUPER_ADMIN = "super_admin"  # Administrador global (puede ver todos los tenants)
    ADMIN = "admin"              # Administrador de tenant (gestiona su tienda)
    STAFF = "staff"              # Personal del tenant (puede ver pedidos)
    CUSTOMER = "customer"        # Cliente normal


# Tabla de asociación muchos a muchos entre User y Role
user_roles = Table(
    'user_roles',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
    Column('role_id', Integer, ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True),
    Column('created_at', DateTime(timezone=True), server_default=func.now())
)


class Role(Base):
    """Rol de usuario"""

    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False, index=True)
    role_type = Column(String(20), nullable=False)  # super_admin, admin, staff, customer
    description = Column(String(200), nullable=True)

    # Permisos específicos (JSON)
    # Ejemplo: {"can_edit_products": true, "can_view_analytics": true}
    # permissions = Column(JSON, nullable=True)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relaciones
    users = relationship("User", secondary=user_roles, back_populates="roles")

    def __repr__(self):
        return f"<Role {self.name} ({self.role_type})>"

    def to_dict(self):
        """Convertir a diccionario"""
        return {
            "id": self.id,
            "name": self.name,
            "role_type": self.role_type,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

    @staticmethod
    def is_admin_role(role_type: str) -> bool:
        """Verificar si un rol es de administrador"""
        return role_type in [RoleType.SUPER_ADMIN.value, RoleType.ADMIN.value]

    @staticmethod
    def is_staff_or_above(role_type: str) -> bool:
        """Verificar si un rol es staff o superior"""
        return role_type in [RoleType.SUPER_ADMIN.value, RoleType.ADMIN.value, RoleType.STAFF.value]
