"""
================================================================================
PERMISSIONS & AUTHORIZATION
================================================================================
Decoradores y funciones para verificar permisos de usuarios
================================================================================
"""

from fastapi import HTTPException, status, Depends
from sqlalchemy.orm import Session
from typing import Callable
from ..models.user import User
from ..routers.auth import get_current_user


# ==============================================================================
# PERMISSION CHECKERS
# ==============================================================================

async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """
    Verificar que el usuario actual es administrador (admin o super_admin).

    Usar como dependencia en endpoints que requieren permisos de admin.
    """
    if not current_user.is_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requieren permisos de administrador"
        )
    return current_user


async def require_super_admin(current_user: User = Depends(get_current_user)) -> User:
    """
    Verificar que el usuario actual es super administrador.

    Usar como dependencia en endpoints que requieren permisos de super admin.
    """
    if not current_user.is_super_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requieren permisos de super administrador"
        )
    return current_user


async def require_staff(current_user: User = Depends(get_current_user)) -> User:
    """
    Verificar que el usuario es staff o superior.

    Usar como dependencia en endpoints que requieren permisos de staff.
    """
    if not current_user.is_staff_or_above():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requieren permisos de staff o superior"
        )
    return current_user


# ==============================================================================
# TENANT VERIFICATION
# ==============================================================================

def verify_tenant_access(user: User, tenant_id: str) -> None:
    """
    Verificar que el usuario tiene acceso al tenant especificado.

    Super admins pueden acceder a todos los tenants.
    Otros usuarios solo pueden acceder a su propio tenant.

    Args:
        user: Usuario actual
        tenant_id: ID del tenant a verificar

    Raises:
        HTTPException: Si el usuario no tiene acceso al tenant
    """
    # Super admin puede ver todos los tenants
    if user.is_super_admin():
        return

    # Otros usuarios solo pueden ver su propio tenant
    if user.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes acceso a este tenant"
        )


def verify_tenant_admin(user: User, tenant_id: str) -> None:
    """
    Verificar que el usuario es admin del tenant especificado.

    Args:
        user: Usuario actual
        tenant_id: ID del tenant a verificar

    Raises:
        HTTPException: Si el usuario no es admin del tenant
    """
    # Super admin puede administrar todos los tenants
    if user.is_super_admin():
        return

    # Verificar que es admin
    if not user.is_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requieren permisos de administrador"
        )

    # Verificar que pertenece al tenant
    if user.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes acceso a administrar este tenant"
        )


# ==============================================================================
# RESOURCE OWNERSHIP
# ==============================================================================

def verify_order_access(user: User, order_customer_id: int, order_tenant_id: str) -> None:
    """
    Verificar que el usuario puede acceder a un pedido.

    - El cliente puede ver sus propios pedidos
    - Staff/Admin del tenant pueden ver todos los pedidos del tenant
    - Super admin puede ver todos los pedidos

    Args:
        user: Usuario actual
        order_customer_id: ID del cliente del pedido
        order_tenant_id: Tenant del pedido
    """
    # Super admin puede ver todos
    if user.is_super_admin():
        return

    # Staff/Admin del tenant pueden ver pedidos del tenant
    if user.is_staff_or_above() and user.tenant_id == order_tenant_id:
        return

    # El cliente puede ver sus propios pedidos
    if user.id == order_customer_id:
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="No tienes acceso a este pedido"
    )


def verify_resource_tenant(user: User, resource_tenant_id: str) -> None:
    """
    Verificar que el usuario puede acceder a un recurso de cierto tenant.

    Args:
        user: Usuario actual
        resource_tenant_id: Tenant del recurso
    """
    if user.is_super_admin():
        return

    if user.tenant_id != resource_tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes acceso a este recurso"
        )
