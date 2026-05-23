"""
================================================================================
MODELS MODULE - Exports
================================================================================
Exporta todos los modelos de base de datos para facilitar imports
================================================================================
"""

# Menu models (desde menu_models.py)
from ..menu_models import Category, Product, Promotion, ProductAlias

# User and Role models
from .user import User
from .role import Role, RoleType, user_roles

# Order models
from .order import Order, OrderItem, OrderStatus, PaymentMethod

# Review model
from .review import Review

# Loyalty models
from .loyalty import LoyaltyAccount, Reward

# Address model
from .address import Address

# Tenant model
from .tenant import Tenant

# Export all
__all__ = [
    # Menu models
    "Category",
    "Product",
    "Promotion",
    "ProductAlias",

    # User and Auth
    "User",
    "Role",
    "RoleType",
    "user_roles",

    # Orders
    "Order",
    "OrderItem",
    "OrderStatus",
    "PaymentMethod",

    # Reviews
    "Review",

    # Loyalty
    "LoyaltyAccount",
    "Reward",

    # Address
    "Address",

    # Tenant
    "Tenant",
]
