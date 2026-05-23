"""
================================================================================
ROUTERS MODULE - Exports
================================================================================
Exporta todos los routers para facilitar imports en main.py
================================================================================
"""

# Public routers
from . import products
from . import categories
from . import promotions
from . import agent
from . import aliases
from . import upload

# Auth and user routers
from . import auth
from . import orders
from . import tenants
from . import addresses
from . import reviews
from . import loyalty

# Admin routers
from . import admin_tenants
from . import admin_products
from . import admin_categories
from . import admin_orders
from . import admin_dashboard
from . import admin_promotions

# Export all
__all__ = [
    # Public routers
    "products",
    "categories",
    "promotions",
    "agent",
    "aliases",
    "upload",

    # Auth and user routers
    "auth",
    "orders",
    "tenants",
    "addresses",
    "reviews",
    "loyalty",

    # Admin routers
    "admin_tenants",
    "admin_products",
    "admin_categories",
    "admin_orders",
    "admin_dashboard",
    "admin_promotions",
]
