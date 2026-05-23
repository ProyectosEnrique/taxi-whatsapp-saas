"""
================================================================================
DYNAMIC RANKING SYSTEM - FASE 3
================================================================================
Sistema de ranking dinámico que combina múltiples señales:
- Popularidad histórica
- Tendencias recientes (momentum)
- Margen de ganancia
- Disponibilidad/inventario
- Scores de otros módulos
================================================================================
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict
import asyncpg

logger = logging.getLogger(__name__)


@dataclass
class RankingFactors:
    """Factores que componen el ranking de un producto"""
    product_id: int
    product_name: str

    # Scores individuales (0-100)
    popularity_score: float = 50.0  # Histórico
    momentum_score: float = 50.0  # Tendencia reciente
    margin_score: float = 50.0  # Margen de ganancia
    availability_score: float = 100.0  # Disponibilidad
    time_relevance_score: float = 50.0  # Relevancia por hora
    collaborative_score: float = 50.0  # Del filtro colaborativo

    # Score final combinado
    final_score: float = 50.0


class DynamicRanker:
    """
    Sistema de ranking dinámico que actualiza en tiempo real
    basado en múltiples factores
    """

    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or self._build_database_url()
        self._pool = None

        # Pesos para cada factor (deben sumar 1.0)
        self.weights = {
            'popularity': 0.25,
            'momentum': 0.20,
            'margin': 0.15,
            'availability': 0.15,
            'time_relevance': 0.15,
            'collaborative': 0.10
        }

        # Cache de rankings
        self._product_rankings: Dict[int, RankingFactors] = {}
        self._last_update: Optional[datetime] = None
        self._update_interval_minutes = 15

        # Datos de momentum (órdenes recientes)
        self._recent_orders: Dict[int, int] = {}  # product_id -> count en última hora
        self._hourly_baseline: Dict[int, float] = {}  # product_id -> promedio por hora

        logger.info("DynamicRanker inicializado")

    def _build_database_url(self) -> str:
        return "postgresql://restaurant:restaurant_2025_prod@postgres:5432/restaurant_db"

    async def connect(self):
        """Establecer conexión"""
        try:
            self._pool = await asyncpg.create_pool(
                self.database_url,
                min_size=1,
                max_size=3
            )
            logger.info("DynamicRanker conectado a BD")
        except Exception as e:
            logger.error(f"Error conectando DynamicRanker: {e}")

    async def disconnect(self):
        """Cerrar conexión"""
        if self._pool:
            await self._pool.close()

    async def update_rankings(self, menu: List[Dict]):
        """
        Actualizar rankings de todos los productos

        Args:
            menu: Lista de productos del menú
        """
        if not self._pool:
            await self.connect()

        try:
            # Obtener datos de popularidad histórica
            popularity_data = await self._get_popularity_data()

            # Obtener datos de momentum (última hora vs baseline)
            momentum_data = await self._get_momentum_data()

            # Obtener datos de margen (placeholder - normalmente vendría de otro sistema)
            margin_data = self._get_margin_data(menu)

            # Calcular rankings para cada producto
            for product in menu:
                product_id = product.get('id')
                product_name = product.get('name', '')
                category = product.get('category', {}).get('name', '').lower()

                factors = RankingFactors(
                    product_id=product_id,
                    product_name=product_name
                )

                # 1. Popularidad histórica
                if product_id in popularity_data:
                    factors.popularity_score = min(100, popularity_data[product_id])

                # 2. Momentum
                if product_id in momentum_data:
                    factors.momentum_score = momentum_data[product_id]

                # 3. Margen
                factors.margin_score = margin_data.get(product_id, 50)

                # 4. Disponibilidad (placeholder - 100 = disponible)
                factors.availability_score = 100

                # 5. Relevancia por hora
                factors.time_relevance_score = self._calculate_time_relevance(category)

                # 6. Collaborative (se actualiza externamente)
                factors.collaborative_score = 50

                # Calcular score final
                factors.final_score = self._calculate_final_score(factors)

                self._product_rankings[product_id] = factors

            self._last_update = datetime.now()

            logger.info(f"Rankings actualizados para {len(self._product_rankings)} productos")

        except Exception as e:
            logger.error(f"Error actualizando rankings: {e}")

    async def _get_popularity_data(self) -> Dict[int, float]:
        """Obtener scores de popularidad histórica"""
        if not self._pool:
            return {}

        try:
            async with self._pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT
                        product_id,
                        COUNT(*) as total_orders
                    FROM order_items oi
                    JOIN orders o ON oi.order_id = o.id
                    WHERE o.created_at >= CURRENT_DATE - INTERVAL '30 days'
                      AND o.status != 'cancelled'
                    GROUP BY product_id
                """)

                if not rows:
                    return {}

                # Normalizar a escala 0-100
                max_orders = max(row['total_orders'] for row in rows)

                return {
                    row['product_id']: (row['total_orders'] / max_orders) * 100
                    for row in rows
                }

        except Exception as e:
            logger.error(f"Error obteniendo popularidad: {e}")
            return {}

    async def _get_momentum_data(self) -> Dict[int, float]:
        """
        Calcular momentum: ventas última hora vs promedio

        Momentum > 50 = vendiendo más que promedio (trending up)
        Momentum < 50 = vendiendo menos que promedio (trending down)
        """
        if not self._pool:
            return {}

        try:
            async with self._pool.acquire() as conn:
                # Órdenes en la última hora
                recent_rows = await conn.fetch("""
                    SELECT
                        product_id,
                        COUNT(*) as recent_count
                    FROM order_items oi
                    JOIN orders o ON oi.order_id = o.id
                    WHERE o.created_at >= CURRENT_TIMESTAMP - INTERVAL '1 hour'
                      AND o.status != 'cancelled'
                    GROUP BY product_id
                """)

                recent_counts = {
                    row['product_id']: row['recent_count']
                    for row in recent_rows
                }

                # Promedio por hora en los últimos 7 días
                avg_rows = await conn.fetch("""
                    SELECT
                        product_id,
                        COUNT(*) / 168.0 as avg_per_hour
                    FROM order_items oi
                    JOIN orders o ON oi.order_id = o.id
                    WHERE o.created_at >= CURRENT_DATE - INTERVAL '7 days'
                      AND o.status != 'cancelled'
                    GROUP BY product_id
                """)

                avg_counts = {
                    row['product_id']: row['avg_per_hour']
                    for row in avg_rows
                }

                # Calcular momentum
                momentum = {}
                for product_id in set(recent_counts.keys()) | set(avg_counts.keys()):
                    recent = recent_counts.get(product_id, 0)
                    avg = avg_counts.get(product_id, 0.1)  # Evitar división por cero

                    if avg > 0:
                        ratio = recent / avg
                        # Convertir ratio a escala 0-100 (1.0 = 50, 2.0 = 75, 0.5 = 25)
                        momentum[product_id] = min(100, max(0, 50 + (ratio - 1) * 25))
                    else:
                        momentum[product_id] = 50 if recent == 0 else 75

                return momentum

        except Exception as e:
            logger.error(f"Error calculando momentum: {e}")
            return {}

    def _get_margin_data(self, menu: List[Dict]) -> Dict[int, float]:
        """
        Obtener scores de margen de ganancia (placeholder)
        En producción vendría de sistema de costos
        """
        # Estimación: productos más caros tienen mejor margen
        margin_scores = {}

        if not menu:
            return margin_scores

        prices = [float(p.get('price', 0)) for p in menu]
        if not prices:
            return margin_scores

        max_price = max(prices)
        min_price = min(prices)
        price_range = max_price - min_price if max_price > min_price else 1

        for product in menu:
            price = float(product.get('price', 0))
            # Normalizar precio a 0-100 (asumiendo mayor precio = mayor margen)
            margin_scores[product['id']] = 30 + ((price - min_price) / price_range) * 40

        return margin_scores

    def _calculate_time_relevance(self, category: str) -> float:
        """Calcular relevancia de categoría por hora actual"""
        hour = datetime.now().hour

        time_category_scores = {
            'desayunos': {
                (6, 11): 100,
                (11, 14): 30,
                'default': 10
            },
            'bebidas': {
                (10, 22): 80,
                'default': 50
            },
            'platos fuertes': {
                (12, 15): 100,
                (18, 21): 100,
                'default': 50
            },
            'postres': {
                (13, 16): 80,
                (19, 22): 90,
                'default': 40
            },
            'antojitos': {
                (18, 23): 90,
                'default': 50
            }
        }

        for cat_keyword, scores in time_category_scores.items():
            if cat_keyword in category:
                for time_range, score in scores.items():
                    if time_range == 'default':
                        continue
                    start, end = time_range
                    if start <= hour <= end:
                        return score
                return scores.get('default', 50)

        return 50  # Neutral para categorías no mapeadas

    def _calculate_final_score(self, factors: RankingFactors) -> float:
        """Calcular score final combinando todos los factores"""
        score = (
            factors.popularity_score * self.weights['popularity'] +
            factors.momentum_score * self.weights['momentum'] +
            factors.margin_score * self.weights['margin'] +
            factors.availability_score * self.weights['availability'] +
            factors.time_relevance_score * self.weights['time_relevance'] +
            factors.collaborative_score * self.weights['collaborative']
        )
        return score

    def update_collaborative_score(self, product_id: int, score: float):
        """Actualizar score colaborativo de un producto"""
        if product_id in self._product_rankings:
            self._product_rankings[product_id].collaborative_score = score
            self._product_rankings[product_id].final_score = self._calculate_final_score(
                self._product_rankings[product_id]
            )

    def get_ranked_products(
        self,
        products: List[Dict],
        limit: int = None
    ) -> List[Tuple[Dict, float]]:
        """
        Obtener productos ordenados por ranking

        Args:
            products: Lista de productos a rankear
            limit: Máximo de productos a retornar

        Returns:
            Lista de tuplas (producto, score) ordenados por score descendente
        """
        scored_products = []

        for product in products:
            product_id = product.get('id')
            if product_id in self._product_rankings:
                score = self._product_rankings[product_id].final_score
            else:
                score = 50  # Neutral para productos sin ranking

            scored_products.append((product, score))

        # Ordenar por score descendente
        scored_products.sort(key=lambda x: x[1], reverse=True)

        if limit:
            scored_products = scored_products[:limit]

        return scored_products

    def get_trending_products(self, menu: List[Dict], limit: int = 5) -> List[Dict]:
        """
        Obtener productos con mayor momentum (trending)

        Args:
            menu: Menú completo
            limit: Máximo de productos

        Returns:
            Lista de productos trending
        """
        trending = []
        menu_dict = {p['id']: p for p in menu}

        for product_id, factors in self._product_rankings.items():
            if factors.momentum_score > 60:  # Trending threshold
                if product_id in menu_dict:
                    product = menu_dict[product_id].copy()
                    product['momentum_score'] = factors.momentum_score
                    trending.append(product)

        # Ordenar por momentum
        trending.sort(key=lambda x: x.get('momentum_score', 0), reverse=True)

        return trending[:limit]

    def get_ranking_explanation(self, product_id: int) -> Optional[str]:
        """
        Obtener explicación del ranking de un producto

        Returns:
            String con explicación legible
        """
        if product_id not in self._product_rankings:
            return None

        f = self._product_rankings[product_id]

        explanation = f"""
Ranking de {f.product_name}:
- Popularidad: {f.popularity_score:.1f}/100
- Momentum: {f.momentum_score:.1f}/100 {'📈' if f.momentum_score > 60 else '📉' if f.momentum_score < 40 else '➡️'}
- Margen: {f.margin_score:.1f}/100
- Disponibilidad: {f.availability_score:.1f}/100
- Relevancia hora: {f.time_relevance_score:.1f}/100
- Score colaborativo: {f.collaborative_score:.1f}/100
━━━━━━━━━━━━━━━━━━━━━━━━━
SCORE FINAL: {f.final_score:.1f}/100
"""
        return explanation


# Instancia global
_dynamic_ranker: Optional[DynamicRanker] = None


async def get_dynamic_ranker() -> DynamicRanker:
    """Obtener instancia global del DynamicRanker"""
    global _dynamic_ranker
    if _dynamic_ranker is None:
        _dynamic_ranker = DynamicRanker()
        await _dynamic_ranker.connect()
    return _dynamic_ranker
