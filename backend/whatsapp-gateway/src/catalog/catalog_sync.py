"""
================================================================================
CATALOG SYNC SERVICE - WhatsApp Gateway
================================================================================
Servicio de sincronizacion de productos con Meta Commerce Catalog.

Responsabilidades:
- Sincronizar productos del menu-service con el catalogo de Meta
- Subir imagenes de productos a Meta
- Actualizar estado de sincronizacion en menu-service
- Manejar errores y reintentos

Uso:
    service = get_catalog_service()
    await service.sync_all_products()
================================================================================
"""

import os
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime

import aiohttp

from .meta_catalog_client import MetaCatalogClient, CatalogProductData
from .image_uploader import MetaImageUploader

logger = logging.getLogger(__name__)


@dataclass
class SyncResult:
    """Resultado de sincronizacion de un producto"""
    product_id: int
    retailer_id: str
    success: bool
    image_uploaded: bool = False
    image_id: Optional[str] = None
    error: Optional[str] = None


class CatalogSyncService:
    """
    Servicio de sincronizacion de catalogo con Meta Commerce.

    Coordina la sincronizacion de productos entre el menu-service
    y el catalogo de Meta para WhatsApp Business.
    """

    def __init__(
        self,
        catalog_client: MetaCatalogClient = None,
        image_uploader: MetaImageUploader = None,
        menu_service_url: str = None
    ):
        """
        Inicializar servicio de sincronizacion.

        Args:
            catalog_client: Cliente de catalogo Meta
            image_uploader: Uploader de imagenes
            menu_service_url: URL del menu-service
        """
        self.catalog_client = catalog_client or MetaCatalogClient()
        self.image_uploader = image_uploader or MetaImageUploader()
        self.menu_service_url = menu_service_url or os.getenv(
            "MENU_SERVICE_URL",
            "http://menu-service:8001"
        )

        # Cache de productos sincronizados (para evitar re-sync innecesario)
        self._sync_cache: Dict[str, datetime] = {}
        self._cache_ttl_seconds = 300  # 5 minutos

    @property
    def is_configured(self) -> bool:
        """Verificar si el servicio esta configurado"""
        return self.catalog_client.is_configured

    async def sync_product(self, product: Dict[str, Any]) -> SyncResult:
        """
        Sincronizar un producto con el catalogo de Meta.

        Proceso:
        1. Generar retailer_id si no existe
        2. Subir imagen si hay URL
        3. Crear/actualizar producto en catalogo
        4. Actualizar estado en menu-service

        Args:
            product: Datos del producto desde menu-service

        Returns:
            Resultado de la sincronizacion
        """
        product_id = product.get("id")
        retailer_id = product.get("product_retailer_id") or f"product_{product_id}"

        result = SyncResult(
            product_id=product_id,
            retailer_id=retailer_id,
            success=False
        )

        if not self.is_configured:
            result.error = "Catalog service not configured"
            await self._update_product_status(product_id, "error", result.error)
            return result

        logger.info(f"[CatalogSync] Syncing product {product_id} ({product.get('name')})")

        try:
            # 1. Subir imagen si hay URL y no hay image_id
            image_id = product.get("meta_image_id")

            if not image_id and product.get("image_url"):
                logger.info(f"[CatalogSync] Uploading image for product {product_id}")
                image_id = await self.image_uploader.upload_from_url(
                    product["image_url"]
                )
                if image_id:
                    result.image_uploaded = True
                    result.image_id = image_id
                    logger.info(f"[CatalogSync] Image uploaded: {image_id}")

            # 2. Preparar datos del producto
            catalog_product = CatalogProductData(
                retailer_id=retailer_id,
                name=product.get("name", "")[:100],
                description=(product.get("description") or product.get("name", ""))[:9999],
                price=float(product.get("price", 0)),
                currency="MXN",
                image_id=image_id,
                image_url=product.get("image_url") if not image_id else None,
                availability="in stock" if product.get("is_available", True) else "out of stock"
            )

            # 3. Crear/actualizar en catalogo Meta
            sync_result = await self.catalog_client.create_or_update_product(catalog_product)

            if not sync_result.get("success"):
                result.error = sync_result.get("error", "Unknown sync error")
                await self._update_product_status(
                    product_id,
                    "error",
                    result.error,
                    retailer_id=retailer_id,
                    image_id=image_id
                )
                return result

            # 4. Actualizar estado en menu-service
            await self._update_product_status(
                product_id,
                "synced",
                None,
                retailer_id=retailer_id,
                image_id=image_id
            )

            result.success = True
            logger.info(f"[CatalogSync] Product {product_id} synced successfully")

        except Exception as e:
            result.error = str(e)
            logger.error(f"[CatalogSync] Error syncing product {product_id}: {e}")
            await self._update_product_status(product_id, "error", str(e))

        return result

    async def sync_all_products(
        self,
        status_filter: str = "pending",
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        Sincronizar todos los productos pendientes.

        Args:
            status_filter: Filtrar por estado (pending, error, None para todos)
            limit: Numero maximo de productos a sincronizar

        Returns:
            Resumen de la sincronizacion
        """
        if not self.is_configured:
            return {
                "success": False,
                "error": "Catalog service not configured",
                "synced": 0,
                "errors": 0
            }

        logger.info(f"[CatalogSync] Starting sync (filter={status_filter}, limit={limit})")

        # Obtener productos del menu-service
        products = await self._get_products_for_sync(status_filter, limit)

        if not products:
            logger.info("[CatalogSync] No products to sync")
            return {
                "success": True,
                "synced": 0,
                "errors": 0,
                "message": "No products to sync"
            }

        results = {
            "success": True,
            "synced": 0,
            "errors": 0,
            "details": []
        }

        for product in products:
            sync_result = await self.sync_product(product)

            if sync_result.success:
                results["synced"] += 1
            else:
                results["errors"] += 1

            results["details"].append({
                "id": sync_result.product_id,
                "retailer_id": sync_result.retailer_id,
                "success": sync_result.success,
                "error": sync_result.error
            })

        logger.info(
            f"[CatalogSync] Sync complete: {results['synced']} synced, "
            f"{results['errors']} errors"
        )

        return results

    async def delete_product(self, retailer_id: str) -> Dict[str, Any]:
        """
        Eliminar producto del catalogo de Meta.

        Args:
            retailer_id: ID del producto en el catalogo

        Returns:
            Resultado de la eliminacion
        """
        if not self.is_configured:
            return {"success": False, "error": "Catalog not configured"}

        logger.info(f"[CatalogSync] Deleting product: {retailer_id}")
        return await self.catalog_client.delete_product(retailer_id)

    async def get_sync_status(self) -> Dict[str, Any]:
        """
        Obtener estado de sincronizacion.

        Returns:
            Estadisticas de sincronizacion
        """
        # Obtener estadisticas del menu-service
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.menu_service_url}/api/v1/products/meta-sync-status"
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    return {
                        "error": f"Menu service error: {response.status}",
                        "stats": {}
                    }
        except Exception as e:
            logger.error(f"[CatalogSync] Error getting status: {e}")
            return {"error": str(e), "stats": {}}

    async def _get_products_for_sync(
        self,
        status_filter: str = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Obtener productos del menu-service para sincronizar"""
        try:
            params = {"limit": limit}
            if status_filter:
                params["status_filter"] = status_filter

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.menu_service_url}/api/v1/products/for-catalog",
                    params=params
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    logger.error(f"[CatalogSync] Menu service error: {response.status}")
                    return []
        except Exception as e:
            logger.error(f"[CatalogSync] Error fetching products: {e}")
            return []

    async def _update_product_status(
        self,
        product_id: int,
        status: str,
        error: str = None,
        retailer_id: str = None,
        image_id: str = None
    ):
        """Actualizar estado de sincronizacion en menu-service"""
        try:
            update_data = {"meta_sync_status": status}

            if error:
                update_data["meta_sync_error"] = error[:500]  # Limitar longitud
            if retailer_id:
                update_data["product_retailer_id"] = retailer_id
            if image_id:
                update_data["meta_image_id"] = image_id

            async with aiohttp.ClientSession() as session:
                async with session.patch(
                    f"{self.menu_service_url}/api/v1/products/{product_id}/meta",
                    json=update_data
                ) as response:
                    if response.status >= 400:
                        logger.error(
                            f"[CatalogSync] Failed to update status for {product_id}: "
                            f"{response.status}"
                        )
        except Exception as e:
            logger.error(f"[CatalogSync] Error updating status: {e}")


# Singleton instance
_catalog_service: Optional[CatalogSyncService] = None


def get_catalog_service() -> CatalogSyncService:
    """
    Obtener instancia del servicio de sincronizacion.

    Returns:
        Instancia singleton del servicio
    """
    global _catalog_service

    if _catalog_service is None:
        _catalog_service = CatalogSyncService()

    return _catalog_service


def reset_catalog_service():
    """Resetear instancia del servicio (para testing)"""
    global _catalog_service
    _catalog_service = None
