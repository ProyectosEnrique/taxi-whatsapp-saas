"""
================================================================================
COLLABORATIVE FILTERING - FASE 3
================================================================================
Sistema de filtrado colaborativo para recomendaciones:
- "Usuarios que ordenaron X también ordenaron Y"
- Similitud entre usuarios basada en historial
- Recomendaciones personalizadas por mesa/usuario
================================================================================
"""

import logging
from collections import defaultdict
from typing import Dict, List, Optional, Set, Tuple
from datetime import datetime, timedelta
import asyncpg
import math

logger = logging.getLogger(__name__)


class CollaborativeFilter:
    """
    Sistema de filtrado colaborativo para recomendaciones
    basadas en comportamiento de usuarios similares
    """

    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or self._build_database_url()
        self._pool = None

        # Matrices de usuario-producto
        self._user_product_matrix: Dict[int, Set[int]] = {}  # table_id -> set(product_ids)
        self._product_user_matrix: Dict[int, Set[int]] = {}  # product_id -> set(table_ids)

        # Cache de similitudes
        self._user_similarities: Dict[int, List[Tuple[int, float]]] = {}  # user -> [(similar_user, score)]

        # Configuración
        self.min_common_products = 2  # Mínimo productos en común para considerar similares
        self.max_similar_users = 10  # Máximo usuarios similares a considerar
        self.similarity_decay_days = 30  # Datos más antiguos pesan menos

        self._last_matrix_update: Optional[datetime] = None
        self._matrix_ttl_hours = 2  # Actualizar matriz cada 2 horas

        logger.info("CollaborativeFilter inicializado")

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
            logger.info("CollaborativeFilter conectado a BD")
        except Exception as e:
            logger.error(f"Error conectando CollaborativeFilter: {e}")

    async def disconnect(self):
        """Cerrar conexión"""
        if self._pool:
            await self._pool.close()

    async def build_matrices(self, days_back: int = 90):
        """
        Construir matrices usuario-producto desde datos históricos

        Args:
            days_back: Días hacia atrás para considerar
        """
        if not self._pool:
            await self.connect()

        if not self._pool:
            logger.warning("No hay conexión a BD para construir matrices")
            return

        try:
            async with self._pool.acquire() as conn:
                # Obtener órdenes de los últimos N días
                rows = await conn.fetch("""
                    SELECT DISTINCT
                        o.table_id,
                        oi.product_id,
                        o.created_at
                    FROM orders o
                    JOIN order_items oi ON o.id = oi.order_id
                    WHERE o.created_at >= CURRENT_DATE - $1 * INTERVAL '1 day'
                      AND o.table_id IS NOT NULL
                      AND o.status != 'cancelled'
                    ORDER BY o.table_id, oi.product_id
                """, days_back)

                # Limpiar matrices existentes
                self._user_product_matrix.clear()
                self._product_user_matrix.clear()

                # Construir matrices
                for row in rows:
                    table_id = row['table_id']
                    product_id = row['product_id']

                    if table_id not in self._user_product_matrix:
                        self._user_product_matrix[table_id] = set()
                    self._user_product_matrix[table_id].add(product_id)

                    if product_id not in self._product_user_matrix:
                        self._product_user_matrix[product_id] = set()
                    self._product_user_matrix[product_id].add(table_id)

                self._last_matrix_update = datetime.now()

                logger.info(
                    f"Matrices construidas: {len(self._user_product_matrix)} mesas, "
                    f"{len(self._product_user_matrix)} productos"
                )

        except Exception as e:
            logger.error(f"Error construyendo matrices: {e}")

    async def _ensure_matrices_fresh(self):
        """Asegurar que las matrices estén actualizadas"""
        if not self._last_matrix_update:
            await self.build_matrices()
        else:
            hours_elapsed = (datetime.now() - self._last_matrix_update).total_seconds() / 3600
            if hours_elapsed > self._matrix_ttl_hours:
                await self.build_matrices()

    def calculate_user_similarity(self, user1: int, user2: int) -> float:
        """
        Calcular similitud entre dos usuarios usando Jaccard index

        Args:
            user1: ID de mesa/usuario 1
            user2: ID de mesa/usuario 2

        Returns:
            Score de similitud (0-1)
        """
        products1 = self._user_product_matrix.get(user1, set())
        products2 = self._user_product_matrix.get(user2, set())

        if not products1 or not products2:
            return 0.0

        intersection = len(products1 & products2)
        union = len(products1 | products2)

        if union == 0:
            return 0.0

        return intersection / union

    def calculate_cosine_similarity(self, user1: int, user2: int) -> float:
        """
        Calcular similitud coseno entre dos usuarios

        Args:
            user1: ID de mesa/usuario 1
            user2: ID de mesa/usuario 2

        Returns:
            Score de similitud (0-1)
        """
        products1 = self._user_product_matrix.get(user1, set())
        products2 = self._user_product_matrix.get(user2, set())

        if not products1 or not products2:
            return 0.0

        intersection = len(products1 & products2)

        if intersection < self.min_common_products:
            return 0.0

        magnitude1 = math.sqrt(len(products1))
        magnitude2 = math.sqrt(len(products2))

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return intersection / (magnitude1 * magnitude2)

    async def find_similar_users(
        self,
        target_user: int,
        limit: int = None
    ) -> List[Tuple[int, float]]:
        """
        Encontrar usuarios similares a uno dado

        Args:
            target_user: ID de mesa/usuario objetivo
            limit: Máximo de usuarios a retornar

        Returns:
            Lista de tuplas (user_id, similarity_score)
        """
        await self._ensure_matrices_fresh()

        if target_user not in self._user_product_matrix:
            return []

        limit = limit or self.max_similar_users
        similarities = []

        for other_user in self._user_product_matrix.keys():
            if other_user == target_user:
                continue

            score = self.calculate_cosine_similarity(target_user, other_user)
            if score > 0:
                similarities.append((other_user, score))

        # Ordenar por similitud descendente
        similarities.sort(key=lambda x: x[1], reverse=True)

        return similarities[:limit]

    async def get_collaborative_recommendations(
        self,
        target_user: int,
        already_ordered: Set[int] = None,
        limit: int = 5
    ) -> List[Tuple[int, float]]:
        """
        Obtener recomendaciones colaborativas para un usuario

        Args:
            target_user: ID de mesa/usuario
            already_ordered: Productos ya ordenados para excluir
            limit: Máximo de recomendaciones

        Returns:
            Lista de tuplas (product_id, score)
        """
        await self._ensure_matrices_fresh()

        already_ordered = already_ordered or set()
        user_products = self._user_product_matrix.get(target_user, set())

        # Encontrar usuarios similares
        similar_users = await self.find_similar_users(target_user)

        if not similar_users:
            return []

        # Agregar scores de productos de usuarios similares
        product_scores = defaultdict(float)

        for similar_user, similarity in similar_users:
            similar_products = self._user_product_matrix.get(similar_user, set())

            for product_id in similar_products:
                # No recomendar productos ya ordenados por el usuario objetivo
                if product_id not in user_products and product_id not in already_ordered:
                    product_scores[product_id] += similarity

        if not product_scores:
            return []

        # Ordenar por score y retornar top
        recommendations = sorted(
            product_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )

        return recommendations[:limit]

    async def get_also_ordered(
        self,
        product_id: int,
        exclude_products: Set[int] = None,
        limit: int = 3
    ) -> List[Tuple[int, float]]:
        """
        "Usuarios que ordenaron X también ordenaron Y"

        Args:
            product_id: ID del producto base
            exclude_products: Productos a excluir
            limit: Máximo de resultados

        Returns:
            Lista de tuplas (product_id, frequency_ratio)
        """
        await self._ensure_matrices_fresh()

        exclude_products = exclude_products or set()

        # Usuarios que ordenaron este producto
        users_who_ordered = self._product_user_matrix.get(product_id, set())

        if not users_who_ordered:
            return []

        total_users = len(users_who_ordered)

        # Contar otros productos ordenados por estos usuarios
        co_occurrence = defaultdict(int)

        for user_id in users_who_ordered:
            user_products = self._user_product_matrix.get(user_id, set())
            for other_product in user_products:
                if other_product != product_id and other_product not in exclude_products:
                    co_occurrence[other_product] += 1

        if not co_occurrence:
            return []

        # Calcular ratio y ordenar
        product_ratios = [
            (prod_id, count / total_users)
            for prod_id, count in co_occurrence.items()
        ]

        product_ratios.sort(key=lambda x: x[1], reverse=True)

        return product_ratios[:limit]

    async def get_frequently_bought_together(
        self,
        cart_products: List[int],
        menu: List[Dict],
        limit: int = 2
    ) -> List[Dict]:
        """
        Obtener productos frecuentemente comprados junto con los del carrito

        Args:
            cart_products: Productos en el carrito
            menu: Menú completo
            limit: Máximo de sugerencias

        Returns:
            Lista de productos sugeridos
        """
        if not cart_products:
            return []

        exclude_set = set(cart_products)
        combined_scores = defaultdict(float)

        for product_id in cart_products:
            also_ordered = await self.get_also_ordered(
                product_id,
                exclude_products=exclude_set,
                limit=5
            )

            for related_id, score in also_ordered:
                combined_scores[related_id] += score

        if not combined_scores:
            return []

        # Ordenar y mapear a productos del menú
        sorted_recommendations = sorted(
            combined_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )

        menu_dict = {p['id']: p for p in menu}
        suggestions = []

        for prod_id, score in sorted_recommendations[:limit]:
            if prod_id in menu_dict:
                product = menu_dict[prod_id].copy()
                product['collaborative_score'] = score
                suggestions.append(product)

        return suggestions


# Instancia global
_collaborative_filter: Optional[CollaborativeFilter] = None


async def get_collaborative_filter() -> CollaborativeFilter:
    """Obtener instancia global del CollaborativeFilter"""
    global _collaborative_filter
    if _collaborative_filter is None:
        _collaborative_filter = CollaborativeFilter()
        await _collaborative_filter.connect()
        await _collaborative_filter.build_matrices()
    return _collaborative_filter
