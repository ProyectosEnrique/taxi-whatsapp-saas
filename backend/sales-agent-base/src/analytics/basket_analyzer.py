"""
================================================================================
BASKET ANALYSIS ENGINE - FASE 2
================================================================================
Motor de análisis de canasta que identifica:
- Productos frecuentemente ordenados juntos (association rules)
- Combos naturales basados en datos históricos
- Oportunidades de cross-selling
================================================================================
"""

import logging
from collections import defaultdict
from typing import Dict, List, Optional, Tuple
import asyncpg

logger = logging.getLogger(__name__)


class BasketAnalyzer:
    """
    Analiza patrones de compra para identificar productos
    que se compran frecuentemente juntos
    """

    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or self._build_database_url()
        self._pool = None

        # Cache de asociaciones (product_id -> [(related_id, confidence)])
        self._associations: Dict[int, List[Tuple[int, float]]] = {}
        self._last_analysis = None
        self._cache_hours = 6  # Refrescar cada 6 horas

        # Parámetros de análisis
        self.min_support = 0.01  # Mínimo 1% de órdenes
        self.min_confidence = 0.1  # Mínimo 10% de confianza

        logger.info("BasketAnalyzer inicializado")

    def _build_database_url(self) -> str:
        """Construir URL de conexión"""
        return "postgresql://restaurant:restaurant_2025_prod@postgres:5432/restaurant_db"

    async def connect(self):
        """Establecer conexión a BD"""
        try:
            self._pool = await asyncpg.create_pool(
                self.database_url,
                min_size=1,
                max_size=3
            )
            logger.info("BasketAnalyzer conectado a BD")
        except Exception as e:
            logger.error(f"Error conectando BasketAnalyzer: {e}")
            self._pool = None

    async def disconnect(self):
        """Cerrar conexión"""
        if self._pool:
            await self._pool.close()

    async def analyze_baskets(self) -> bool:
        """
        Analizar órdenes históricas para encontrar asociaciones

        Usa un algoritmo simplificado de association rules:
        - Para cada par de productos (A, B)
        - Calcula: confidence(A -> B) = support(A,B) / support(A)
        """
        if not self._pool:
            await self.connect()

        if not self._pool:
            logger.warning("No hay conexión a BD para análisis de canastas")
            return False

        try:
            async with self._pool.acquire() as conn:
                # 1. Obtener total de órdenes (para calcular support)
                total_orders = await conn.fetchval("""
                    SELECT COUNT(DISTINCT order_id) FROM order_items
                """)

                if not total_orders or total_orders < 10:
                    logger.warning(f"Pocas órdenes para análisis: {total_orders}")
                    return False

                # 2. Obtener frecuencia de cada producto (support individual)
                product_support = {}
                rows = await conn.fetch("""
                    SELECT product_id, COUNT(DISTINCT order_id) as order_count
                    FROM order_items
                    GROUP BY product_id
                """)

                for row in rows:
                    product_support[row['product_id']] = row['order_count'] / total_orders

                # 3. Obtener pares de productos en la misma orden
                pair_counts = defaultdict(int)
                pair_rows = await conn.fetch("""
                    SELECT
                        a.product_id as product_a,
                        b.product_id as product_b,
                        COUNT(DISTINCT a.order_id) as pair_count
                    FROM order_items a
                    JOIN order_items b ON a.order_id = b.order_id AND a.product_id < b.product_id
                    GROUP BY a.product_id, b.product_id
                    HAVING COUNT(DISTINCT a.order_id) >= 2
                """)

                for row in pair_rows:
                    pair_support = row['pair_count'] / total_orders
                    if pair_support >= self.min_support:
                        pair_counts[(row['product_a'], row['product_b'])] = row['pair_count']

                # 4. Calcular confidence y construir asociaciones
                self._associations = defaultdict(list)

                for (prod_a, prod_b), pair_count in pair_counts.items():
                    # Confidence A -> B
                    support_a = product_support.get(prod_a, 0)
                    if support_a > 0:
                        confidence_ab = (pair_count / total_orders) / support_a
                        if confidence_ab >= self.min_confidence:
                            self._associations[prod_a].append((prod_b, confidence_ab))

                    # Confidence B -> A
                    support_b = product_support.get(prod_b, 0)
                    if support_b > 0:
                        confidence_ba = (pair_count / total_orders) / support_b
                        if confidence_ba >= self.min_confidence:
                            self._associations[prod_b].append((prod_a, confidence_ba))

                # Ordenar asociaciones por confianza
                for prod_id in self._associations:
                    self._associations[prod_id].sort(key=lambda x: x[1], reverse=True)

                from datetime import datetime
                self._last_analysis = datetime.now()

                logger.info(
                    f"Análisis de canastas completado: {len(self._associations)} productos "
                    f"con asociaciones, {sum(len(v) for v in self._associations.values())} reglas"
                )
                return True

        except Exception as e:
            logger.error(f"Error en análisis de canastas: {e}")
            return False

    async def get_related_products(
        self,
        product_id: int,
        limit: int = 3
    ) -> List[Tuple[int, float]]:
        """
        Obtener productos relacionados a uno dado

        Args:
            product_id: ID del producto base
            limit: Máximo de relacionados a retornar

        Returns:
            Lista de tuplas (product_id, confidence)
        """
        # Verificar si necesita re-análisis
        from datetime import datetime
        if not self._last_analysis:
            await self.analyze_baskets()
        else:
            hours_elapsed = (datetime.now() - self._last_analysis).total_seconds() / 3600
            if hours_elapsed > self._cache_hours:
                await self.analyze_baskets()

        return self._associations.get(product_id, [])[:limit]

    async def get_cross_sell_suggestions(
        self,
        cart_items: List[int],
        menu: List[Dict],
        limit: int = 2
    ) -> List[Dict]:
        """
        Obtener sugerencias de cross-selling basadas en el carrito actual

        Args:
            cart_items: Lista de product_ids en el carrito
            menu: Menú completo para mapear IDs a productos
            limit: Máximo de sugerencias

        Returns:
            Lista de productos sugeridos con metadata
        """
        if not cart_items:
            return []

        # Obtener todas las asociaciones de productos en el carrito
        candidate_scores = defaultdict(float)

        for cart_item_id in cart_items:
            related = await self.get_related_products(cart_item_id, limit=5)
            for related_id, confidence in related:
                # No sugerir productos ya en el carrito
                if related_id not in cart_items:
                    candidate_scores[related_id] += confidence

        if not candidate_scores:
            return []

        # Ordenar por score combinado
        sorted_candidates = sorted(
            candidate_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )

        # Mapear a productos del menú
        suggestions = []
        menu_dict = {p['id']: p for p in menu}

        for prod_id, score in sorted_candidates[:limit]:
            if prod_id in menu_dict:
                product = menu_dict[prod_id]
                suggestions.append({
                    'product': product,
                    'confidence': score,
                    'reason': 'frequently_bought_together'
                })

        return suggestions

    async def get_combo_suggestions(
        self,
        menu: List[Dict],
        min_products: int = 2,
        max_products: int = 3
    ) -> List[Dict]:
        """
        Identificar combos naturales basados en patrones de compra

        Returns:
            Lista de combos sugeridos con productos y frecuencia
        """
        if not self._pool:
            await self.connect()

        if not self._pool:
            return []

        try:
            async with self._pool.acquire() as conn:
                # Obtener combinaciones más frecuentes de 2-3 productos
                rows = await conn.fetch("""
                    WITH order_products AS (
                        SELECT
                            order_id,
                            array_agg(product_id ORDER BY product_id) as products
                        FROM order_items
                        GROUP BY order_id
                        HAVING COUNT(*) BETWEEN $1 AND $2
                    )
                    SELECT
                        products,
                        COUNT(*) as frequency
                    FROM order_products
                    GROUP BY products
                    HAVING COUNT(*) >= 3
                    ORDER BY COUNT(*) DESC
                    LIMIT 10
                """, min_products, max_products)

                menu_dict = {p['id']: p for p in menu}
                combos = []

                for row in rows:
                    product_ids = row['products']
                    products = []

                    for pid in product_ids:
                        if pid in menu_dict:
                            products.append(menu_dict[pid])

                    if len(products) == len(product_ids):
                        total_price = sum(float(p.get('price', 0)) for p in products)
                        combos.append({
                            'products': products,
                            'frequency': row['frequency'],
                            'total_price': total_price,
                            'suggested_discount': 0.1  # 10% sugerido
                        })

                logger.info(f"Combos identificados: {len(combos)}")
                return combos

        except Exception as e:
            logger.error(f"Error identificando combos: {e}")
            return []


# Instancia global
_basket_analyzer: Optional[BasketAnalyzer] = None


async def get_basket_analyzer() -> BasketAnalyzer:
    """Obtener instancia global del BasketAnalyzer"""
    global _basket_analyzer
    if _basket_analyzer is None:
        _basket_analyzer = BasketAnalyzer()
        await _basket_analyzer.connect()
        await _basket_analyzer.analyze_baskets()
    return _basket_analyzer
