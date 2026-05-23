"""
================================================================================
META CATALOG CLIENT - WhatsApp Gateway
================================================================================
Cliente para interactuar con Meta Commerce Catalog API.

Endpoints utilizados:
- POST /{catalog_id}/products - Crear/actualizar productos en batch
- DELETE /{catalog_id}/products - Eliminar productos
- GET /{catalog_id}/products - Listar productos del catalogo

Documentacion:
https://developers.facebook.com/docs/commerce-platform/catalog/
================================================================================
"""

import os
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

import aiohttp

logger = logging.getLogger(__name__)


@dataclass
class CatalogProductData:
    """Datos de producto para el catalogo de Meta"""
    retailer_id: str
    name: str
    description: str
    price: float
    currency: str = "MXN"
    image_id: Optional[str] = None
    image_url: Optional[str] = None
    availability: str = "in stock"
    category: str = "Restaurant Menu"


class MetaCatalogClient:
    """
    Cliente para Meta Commerce Catalog API.

    Permite crear, actualizar y eliminar productos del catalogo vinculado
    a WhatsApp Business para usar Multi-Product Messages.
    """

    BASE_URL = "https://graph.facebook.com/v18.0"

    def __init__(
        self,
        access_token: str = None,
        catalog_id: str = None,
        timeout: int = 30
    ):
        """
        Inicializar cliente de catalogo.

        Args:
            access_token: Token de acceso de Meta (Bearer)
            catalog_id: ID del catalogo en Meta Commerce Manager
            timeout: Timeout para requests HTTP
        """
        self.access_token = access_token or os.getenv("META_ACCESS_TOKEN", "")
        self.catalog_id = catalog_id or os.getenv("META_CATALOG_ID", "")
        self.timeout = aiohttp.ClientTimeout(total=timeout)

        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

        if not self.catalog_id:
            logger.warning("[MetaCatalog] No catalog_id configured - catalog features disabled")

    @property
    def is_configured(self) -> bool:
        """Verificar si el cliente esta configurado correctamente"""
        return bool(self.access_token and self.catalog_id)

    async def create_or_update_product(
        self,
        product: CatalogProductData
    ) -> Dict[str, Any]:
        """
        Crear o actualizar un producto en el catalogo de Meta.

        Args:
            product: Datos del producto

        Returns:
            Resultado de la operacion
        """
        if not self.is_configured:
            return {"success": False, "error": "Catalog not configured"}

        url = f"{self.BASE_URL}/{self.catalog_id}/products"

        # Preparar datos del producto
        product_data = {
            "retailer_id": product.retailer_id,
            "data": {
                "name": product.name[:100],  # Max 100 caracteres
                "description": product.description[:9999],  # Max 9999 caracteres
                "availability": product.availability,
                "price": int(product.price * 100),  # Precio en centavos
                "currency": product.currency,
                "category": product.category,
            }
        }

        # Agregar imagen si esta disponible
        if product.image_id:
            product_data["data"]["image_id"] = product.image_id
        elif product.image_url:
            product_data["data"]["image_url"] = product.image_url

        # Request en formato batch
        payload = {
            "requests": [product_data]
        }

        logger.info(f"[MetaCatalog] Creating/updating product: {product.retailer_id}")

        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.post(
                    url,
                    json=payload,
                    headers=self.headers
                ) as response:
                    result = await response.json()

                    if response.status >= 400:
                        logger.error(f"[MetaCatalog] Error: {result}")
                        return {
                            "success": False,
                            "error": result.get("error", {}).get("message", "Unknown error"),
                            "status_code": response.status
                        }

                    logger.info(f"[MetaCatalog] Product synced: {product.retailer_id}")
                    return {
                        "success": True,
                        "result": result
                    }

        except aiohttp.ClientError as e:
            logger.error(f"[MetaCatalog] Network error: {e}")
            return {"success": False, "error": str(e)}
        except Exception as e:
            logger.error(f"[MetaCatalog] Unexpected error: {e}")
            return {"success": False, "error": str(e)}

    async def create_or_update_batch(
        self,
        products: List[CatalogProductData]
    ) -> Dict[str, Any]:
        """
        Crear o actualizar multiples productos en batch.

        Meta permite hasta 5000 productos por request.

        Args:
            products: Lista de productos

        Returns:
            Resultado de la operacion
        """
        if not self.is_configured:
            return {"success": False, "error": "Catalog not configured"}

        if not products:
            return {"success": True, "synced": 0}

        url = f"{self.BASE_URL}/{self.catalog_id}/products"

        # Preparar datos de todos los productos
        requests_data = []
        for product in products[:5000]:  # Max 5000 por batch
            product_data = {
                "retailer_id": product.retailer_id,
                "data": {
                    "name": product.name[:100],
                    "description": product.description[:9999],
                    "availability": product.availability,
                    "price": int(product.price * 100),
                    "currency": product.currency,
                    "category": product.category,
                }
            }

            if product.image_id:
                product_data["data"]["image_id"] = product.image_id
            elif product.image_url:
                product_data["data"]["image_url"] = product.image_url

            requests_data.append(product_data)

        payload = {"requests": requests_data}

        logger.info(f"[MetaCatalog] Batch syncing {len(requests_data)} products")

        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.post(
                    url,
                    json=payload,
                    headers=self.headers
                ) as response:
                    result = await response.json()

                    if response.status >= 400:
                        logger.error(f"[MetaCatalog] Batch error: {result}")
                        return {
                            "success": False,
                            "error": result.get("error", {}).get("message", "Unknown error"),
                            "status_code": response.status
                        }

                    # Contar resultados
                    handles = result.get("handles", [])
                    errors = result.get("errors", [])

                    logger.info(f"[MetaCatalog] Batch complete: {len(handles)} synced, {len(errors)} errors")

                    return {
                        "success": True,
                        "synced": len(handles),
                        "errors": len(errors),
                        "error_details": errors[:10]  # Primeros 10 errores
                    }

        except Exception as e:
            logger.error(f"[MetaCatalog] Batch error: {e}")
            return {"success": False, "error": str(e)}

    async def delete_product(self, retailer_id: str) -> Dict[str, Any]:
        """
        Eliminar un producto del catalogo.

        Args:
            retailer_id: ID del producto en el catalogo

        Returns:
            Resultado de la operacion
        """
        if not self.is_configured:
            return {"success": False, "error": "Catalog not configured"}

        url = f"{self.BASE_URL}/{self.catalog_id}/products"

        payload = {
            "requests": [
                {
                    "retailer_id": retailer_id,
                    "method": "DELETE"
                }
            ]
        }

        logger.info(f"[MetaCatalog] Deleting product: {retailer_id}")

        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.post(
                    url,
                    json=payload,
                    headers=self.headers
                ) as response:
                    result = await response.json()

                    if response.status >= 400:
                        logger.error(f"[MetaCatalog] Delete error: {result}")
                        return {"success": False, "error": result}

                    logger.info(f"[MetaCatalog] Product deleted: {retailer_id}")
                    return {"success": True, "result": result}

        except Exception as e:
            logger.error(f"[MetaCatalog] Delete error: {e}")
            return {"success": False, "error": str(e)}

    async def get_products(
        self,
        limit: int = 100,
        after: str = None
    ) -> Dict[str, Any]:
        """
        Listar productos del catalogo.

        Args:
            limit: Numero maximo de productos
            after: Cursor para paginacion

        Returns:
            Lista de productos
        """
        if not self.is_configured:
            return {"success": False, "error": "Catalog not configured", "products": []}

        url = f"{self.BASE_URL}/{self.catalog_id}/products"

        params = {
            "fields": "id,retailer_id,name,description,price,currency,availability,image_url",
            "limit": limit
        }

        if after:
            params["after"] = after

        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(
                    url,
                    params=params,
                    headers=self.headers
                ) as response:
                    result = await response.json()

                    if response.status >= 400:
                        logger.error(f"[MetaCatalog] List error: {result}")
                        return {"success": False, "error": result, "products": []}

                    products = result.get("data", [])
                    paging = result.get("paging", {})

                    return {
                        "success": True,
                        "products": products,
                        "next_cursor": paging.get("cursors", {}).get("after")
                    }

        except Exception as e:
            logger.error(f"[MetaCatalog] List error: {e}")
            return {"success": False, "error": str(e), "products": []}

    async def get_catalog_info(self) -> Dict[str, Any]:
        """
        Obtener informacion del catalogo.

        Returns:
            Informacion del catalogo
        """
        if not self.is_configured:
            return {"success": False, "error": "Catalog not configured"}

        url = f"{self.BASE_URL}/{self.catalog_id}"

        params = {
            "fields": "id,name,product_count,vertical"
        }

        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(
                    url,
                    params=params,
                    headers=self.headers
                ) as response:
                    result = await response.json()

                    if response.status >= 400:
                        return {"success": False, "error": result}

                    return {"success": True, "catalog": result}

        except Exception as e:
            logger.error(f"[MetaCatalog] Info error: {e}")
            return {"success": False, "error": str(e)}
