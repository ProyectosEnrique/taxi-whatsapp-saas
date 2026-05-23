"""
================================================================================
SALES AGENT - RESTAURANT API CLIENT (Multi-Tenant)
================================================================================
Cliente simplificado para comunicarse con el api-service del sistema multi-tenant
================================================================================
"""

import httpx
import os
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class RestaurantAPIClient:
    """
    Cliente HTTP para comunicarse con el api-service del sistema multi-tenant

    Servicios soportados:
    - Menu Service (productos, categorías, promociones)
    """

    def __init__(
        self,
        menu_service_url: str = None,
        timeout: float = 10.0
    ):
        # Si no se proporciona URL, usar variable de entorno o default
        if menu_service_url is None:
            menu_service_url = os.getenv('MENU_SERVICE_URL', 'http://api-service:5011')

        self.menu_service_url = menu_service_url.rstrip('/')
        self.timeout = timeout

        # Cache para reducir llamadas repetidas al menú
        self._menu_cache: List[Dict] = []
        self._menu_cache_time: Optional[datetime] = None
        self._menu_cache_ttl = timedelta(minutes=5)  # Cache válido por 5 minutos

        logger.info(f"RestaurantAPIClient inicializado (con cache de menú)")
        logger.info(f"  - Menu Service: {self.menu_service_url}")

    # ========================================
    # MENU SERVICE
    # ========================================

    async def get_menu(self, category: Optional[str] = None, force_refresh: bool = False, tenant_id: Optional[str] = None) -> List[Dict]:
        """
        Obtener menú completo o por categoría (CON CACHE)

        Args:
            category: Categoría opcional (appetizers, mains, desserts, drinks)
            force_refresh: Forzar recarga del cache
            tenant_id: ID del tenant (multi-tenant)

        Returns:
            Lista de productos
        """
        try:
            # Verificar si el cache es válido (solo para menú completo sin categoría)
            if not category and not force_refresh and not tenant_id:
                if self._menu_cache and self._menu_cache_time:
                    cache_age = datetime.now() - self._menu_cache_time
                    if cache_age < self._menu_cache_ttl:
                        logger.debug(f"[CACHE HIT] Menú desde cache ({len(self._menu_cache)} productos)")
                        return self._menu_cache

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                url = f"{self.menu_service_url}/api/v1/products"
                params = {}
                headers = {}

                if category:
                    params['category'] = category

                if tenant_id:
                    headers['X-Tenant-ID'] = tenant_id

                response = await client.get(url, params=params, headers=headers)
                response.raise_for_status()

                products = response.json()

                # Guardar en cache si es menú completo sin tenant
                if not category and not tenant_id:
                    self._menu_cache = products
                    self._menu_cache_time = datetime.now()
                    logger.debug(f"[CACHE REFRESH] Menú guardado en cache ({len(products)} productos)")

                return products

        except httpx.HTTPStatusError as e:
            logger.error(f"Error HTTP al obtener menú: {e.response.status_code}")
            return []
        except Exception as e:
            logger.error(f"Error al obtener menú: {str(e)}")
            return []

    async def search_products(self, query: str, tenant_id: Optional[str] = None) -> List[Dict]:
        """
        Buscar productos por nombre o descripción

        Args:
            query: Texto a buscar
            tenant_id: ID del tenant (multi-tenant)

        Returns:
            Lista de productos que coinciden
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                url = f"{self.menu_service_url}/api/v1/products/search"
                params = {'q': query}
                headers = {}

                if tenant_id:
                    headers['X-Tenant-ID'] = tenant_id

                response = await client.get(url, params=params, headers=headers)
                response.raise_for_status()

                return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Error HTTP al buscar productos: {e.response.status_code}")
            return []
        except Exception as e:
            logger.error(f"Error al buscar productos: {str(e)}")
            return []

    async def get_categories(self, tenant_id: Optional[str] = None) -> List[Dict]:
        """
        Obtener lista de categorías

        Args:
            tenant_id: ID del tenant (multi-tenant)

        Returns:
            Lista de categorías
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                url = f"{self.menu_service_url}/api/v1/categories"
                headers = {}

                if tenant_id:
                    headers['X-Tenant-ID'] = tenant_id

                response = await client.get(url, headers=headers)
                response.raise_for_status()

                return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Error HTTP al obtener categorías: {e.response.status_code}")
            return []
        except Exception as e:
            logger.error(f"Error al obtener categorías: {str(e)}")
            return []

    async def get_promotions(self, tenant_id: Optional[str] = None) -> List[Dict]:
        """
        Obtener promociones activas

        Args:
            tenant_id: ID del tenant (multi-tenant)

        Returns:
            Lista de promociones
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                url = f"{self.menu_service_url}/api/v1/promotions"
                headers = {}

                if tenant_id:
                    headers['X-Tenant-ID'] = tenant_id

                response = await client.get(url, headers=headers)
                response.raise_for_status()

                return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Error HTTP al obtener promociones: {e.response.status_code}")
            return []
        except Exception as e:
            logger.error(f"Error al obtener promociones: {str(e)}")
            return []

    # ========================================
    # ORDERS (Stubs - No implementado en este proyecto)
    # ========================================

    async def create_order(self, table_id: int, items: List[Dict], **kwargs) -> bool:
        """
        Stub para crear orden (no implementado en este proyecto)
        """
        logger.warning("create_order no está implementado en este proyecto multi-tenant")
        return True  # Simular éxito para evitar errores

    async def create_service_request(self, table_id: int, request_type: str, **kwargs) -> bool:
        """
        Stub para crear solicitud de servicio (no implementado en este proyecto)
        """
        logger.warning("create_service_request no está implementado en este proyecto multi-tenant")
        return True  # Simular éxito para evitar errores

    # ========================================
    # HEALTH CHECK
    # ========================================

    async def health_check(self) -> Dict[str, Any]:
        """
        Verificar estado del api-service

        Returns:
            Diccionario con estado de salud
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                url = f"{self.menu_service_url}/health"
                response = await client.get(url)
                response.raise_for_status()

                return {
                    'menu_service': 'healthy',
                    'status': 'ok'
                }

        except Exception as e:
            logger.error(f"Error en health check: {str(e)}")
            return {
                'menu_service': 'unhealthy',
                'status': 'error',
                'error': str(e)
            }


# ========================================
# SINGLETON
# ========================================

_client_instance = None


def get_restaurant_client() -> RestaurantAPIClient:
    """
    Obtener instancia singleton del cliente

    Returns:
        RestaurantAPIClient instance
    """
    global _client_instance
    if _client_instance is None:
        _client_instance = RestaurantAPIClient()
    return _client_instance
