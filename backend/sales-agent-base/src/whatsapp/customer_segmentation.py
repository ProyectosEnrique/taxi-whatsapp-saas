"""
================================================================================
CUSTOMER SEGMENTATION
================================================================================
Segmentación de clientes para campañas de WhatsApp.

Segmentos disponibles:
- all: Todos los clientes
- frequent: Clientes frecuentes (>= 3 órdenes)
- inactive: Clientes inactivos (sin órdenes en 30+ días)
- new: Clientes nuevos (1-2 órdenes)
- vip: Clientes VIP (alto valor de vida)
================================================================================
"""

import logging
import os
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Customer:
    """Modelo de cliente para segmentación"""
    id: str
    phone: str
    name: str
    order_count: int
    last_order_date: Optional[datetime]
    total_spent: float
    created_at: datetime
    preferences: Dict  # Productos favoritos, etc.


class CustomerSegmenter:
    """
    Segmentador de clientes para campañas de WhatsApp.

    Permite filtrar clientes según diferentes criterios para
    enviar broadcasts personalizados.
    """

    def __init__(self):
        self.db_url = os.getenv("DATABASE_URL", "postgresql://restaurant:restaurant_2025_prod@postgres:5432/restaurant_db")

    async def get_customers(self, filter_criteria: Dict) -> List[Dict]:
        """
        Obtiene clientes que cumplen con los criterios de filtrado.

        Args:
            filter_criteria: Criterios de filtrado
                - segment: 'all' | 'frequent' | 'inactive' | 'new' | 'vip' | 'custom'
                - min_orders: Mínimo de órdenes (opcional)
                - max_orders: Máximo de órdenes (opcional)
                - last_order_days: Días desde última orden (opcional)
                - min_spent: Gasto mínimo total (opcional)
                - favorite_products: Lista de IDs de productos (opcional)

        Returns:
            Lista de clientes que cumplen los criterios
        """
        segment = filter_criteria.get('segment', 'all')

        logger.info(f"[Segmentation] Obteniendo clientes para segmento: {segment}")

        # Por ahora usamos datos mockeados
        # TODO: Integrar con DB real
        all_customers = await self._get_all_customers_from_db()

        # Aplicar filtro según segmento
        if segment == 'all':
            filtered = all_customers
        elif segment == 'frequent':
            min_orders = filter_criteria.get('min_orders', 3)
            filtered = [c for c in all_customers if c['order_count'] >= min_orders]
        elif segment == 'inactive':
            days_threshold = filter_criteria.get('last_order_days', 30)
            cutoff_date = datetime.now() - timedelta(days=days_threshold)
            filtered = [
                c for c in all_customers
                if c.get('last_order_date') and c['last_order_date'] < cutoff_date
            ]
        elif segment == 'new':
            max_orders = filter_criteria.get('max_orders', 2)
            filtered = [
                c for c in all_customers
                if c['order_count'] > 0 and c['order_count'] <= max_orders
            ]
        elif segment == 'vip':
            min_spent = filter_criteria.get('min_spent', 1000)
            filtered = [c for c in all_customers if c['total_spent'] >= min_spent]
        elif segment == 'custom':
            # Aplicar filtros custom
            filtered = self._apply_custom_filters(all_customers, filter_criteria)
        else:
            logger.warning(f"[Segmentation] Segmento desconocido: {segment}")
            filtered = []

        logger.info(f"[Segmentation] {len(filtered)} clientes encontrados para segmento '{segment}'")

        return filtered

    def _apply_custom_filters(self, customers: List[Dict], criteria: Dict) -> List[Dict]:
        """Aplica filtros personalizados"""
        filtered = customers

        # Filtro por cantidad de órdenes
        if 'min_orders' in criteria:
            min_orders = criteria['min_orders']
            filtered = [c for c in filtered if c['order_count'] >= min_orders]

        if 'max_orders' in criteria:
            max_orders = criteria['max_orders']
            filtered = [c for c in filtered if c['order_count'] <= max_orders]

        # Filtro por días desde última orden
        if 'last_order_days' in criteria:
            days = criteria['last_order_days']
            cutoff_date = datetime.now() - timedelta(days=days)
            filtered = [
                c for c in filtered
                if c.get('last_order_date') and c['last_order_date'] >= cutoff_date
            ]

        # Filtro por gasto
        if 'min_spent' in criteria:
            min_spent = criteria['min_spent']
            filtered = [c for c in filtered if c['total_spent'] >= min_spent]

        if 'max_spent' in criteria:
            max_spent = criteria['max_spent']
            filtered = [c for c in filtered if c['total_spent'] <= max_spent]

        # Filtro por productos favoritos
        if 'favorite_products' in criteria:
            favorite_products = criteria['favorite_products']
            filtered = [
                c for c in filtered
                if any(p in c.get('preferences', {}).get('favorite_products', []) for p in favorite_products)
            ]

        return filtered

    async def _get_all_customers_from_db(self) -> List[Dict]:
        """
        Obtiene todos los clientes de la DB con sus datos de WhatsApp.

        TODO: Implementar query real a la DB.
        """
        # Mock data por ahora
        mock_customers = [
            {
                'id': '1',
                'phone': '+525551234567',
                'name': 'María García',
                'order_count': 5,
                'last_order_date': datetime.now() - timedelta(days=2),
                'total_spent': 750.0,
                'created_at': datetime.now() - timedelta(days=60),
                'preferences': {
                    'favorite_products': ['hamburguesa_bbq', 'cerveza']
                }
            },
            {
                'id': '2',
                'phone': '+525559876543',
                'name': 'Juan Pérez',
                'order_count': 12,
                'last_order_date': datetime.now() - timedelta(days=1),
                'total_spent': 1800.0,
                'created_at': datetime.now() - timedelta(days=120),
                'preferences': {
                    'favorite_products': ['tacos_pastor', 'refresco']
                }
            },
            {
                'id': '3',
                'phone': '+525555555555',
                'name': 'Ana López',
                'order_count': 1,
                'last_order_date': datetime.now() - timedelta(days=5),
                'total_spent': 150.0,
                'created_at': datetime.now() - timedelta(days=7),
                'preferences': {
                    'favorite_products': ['ensalada', 'agua']
                }
            },
            {
                'id': '4',
                'phone': '+525556666666',
                'name': 'Carlos Ramírez',
                'order_count': 8,
                'last_order_date': datetime.now() - timedelta(days=45),
                'total_spent': 1200.0,
                'created_at': datetime.now() - timedelta(days=180),
                'preferences': {
                    'favorite_products': ['pizza', 'cerveza']
                }
            },
            {
                'id': '5',
                'phone': '+525557777777',
                'name': 'Laura Fernández',
                'order_count': 15,
                'last_order_date': datetime.now() - timedelta(hours=3),
                'total_spent': 2500.0,
                'created_at': datetime.now() - timedelta(days=200),
                'preferences': {
                    'favorite_products': ['hamburguesa_bbq', 'papas', 'cerveza']
                }
            }
        ]

        return mock_customers

    def get_segment_description(self, segment: str) -> str:
        """Obtiene descripción de un segmento"""
        descriptions = {
            'all': 'Todos los clientes con WhatsApp',
            'frequent': 'Clientes frecuentes (3+ órdenes)',
            'inactive': 'Clientes inactivos (30+ días sin ordenar)',
            'new': 'Clientes nuevos (1-2 órdenes)',
            'vip': 'Clientes VIP (alto valor)',
            'custom': 'Segmento personalizado'
        }
        return descriptions.get(segment, 'Segmento desconocido')

    async def get_segment_count(self, filter_criteria: Dict) -> int:
        """Obtiene cantidad de clientes en un segmento sin cargar todos los datos"""
        customers = await self.get_customers(filter_criteria)
        return len(customers)


# Singleton
_customer_segmenter = None


def get_customer_segmenter() -> CustomerSegmenter:
    """Obtiene instancia singleton del CustomerSegmenter"""
    global _customer_segmenter
    if _customer_segmenter is None:
        _customer_segmenter = CustomerSegmenter()
    return _customer_segmenter
