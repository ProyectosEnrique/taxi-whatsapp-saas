"""
================================================================================
CATALOG MODULE - WhatsApp Gateway
================================================================================
Modulo de sincronizacion con Meta Commerce Catalog para WhatsApp Business API.

Componentes:
- MetaCatalogClient: Cliente para API de Meta Commerce
- MetaImageUploader: Subida de imagenes a Meta Media API
- CatalogSyncService: Servicio de sincronizacion de productos

Uso:
    from .catalog import CatalogSyncService, get_catalog_service

    # Obtener instancia del servicio
    sync_service = get_catalog_service()

    # Sincronizar un producto
    result = await sync_service.sync_product(product_data)

    # Sincronizar todos los productos pendientes
    results = await sync_service.sync_all_products()
================================================================================
"""

from .meta_catalog_client import MetaCatalogClient
from .image_uploader import MetaImageUploader
from .catalog_sync import CatalogSyncService, get_catalog_service

__all__ = [
    "MetaCatalogClient",
    "MetaImageUploader",
    "CatalogSyncService",
    "get_catalog_service"
]
