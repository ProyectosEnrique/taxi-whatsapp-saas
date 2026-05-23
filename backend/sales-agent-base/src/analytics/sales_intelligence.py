"""
================================================================================
SALES INTELLIGENCE MODULE - FASE 1
================================================================================
Motor de inteligencia de ventas que integra:
- Datos reales de popularidad desde PostgreSQL
- Historial de usuario/mesa
- Reglas por horario
- Sistema de scoring para recomendaciones
- Promociones activas desde menu-service
================================================================================
"""

import logging
import os
import aiohttp
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# Stats client eliminado - No usado en sistema de ventas
# Si se requiere estadísticas de productos, implementar un nuevo cliente
# from ..restaurant.stats_client import get_stats_client, StatsClient

logger = logging.getLogger(__name__)


class SalesIntelligence:
    """
    Motor de inteligencia de ventas que usa datos reales
    para hacer recomendaciones personalizadas y efectivas
    """

    def __init__(self):
        self._stats_client = None  # Stats client deshabilitado
        self._product_stats: Dict[int, Dict] = {}
        self._last_stats_update: Optional[datetime] = None
        self._stats_cache_minutes = 15  # Refrescar stats cada 15 min

        # Menu Service URL para consultar promociones
        # Remover /api/v1 si está incluido para evitar duplicación
        _raw_menu_url = os.getenv('MENU_SERVICE_URL', 'http://menu-service:5011')
        self._menu_service_url = _raw_menu_url.rstrip("/").removesuffix("/api/v1")

        # Cache de promociones activas
        self._active_promotions: List[Dict] = []
        self._last_promotions_update: Optional[datetime] = None
        self._promotions_cache_minutes = 5  # Refrescar cada 5 min

        # Configuración de reglas por horario
        self.time_rules = {
            # Desayuno (7-11)
            'breakfast': {
                'hours': range(7, 12),
                'boost_categories': ['desayunos', 'bebidas calientes', 'jugos'],
                'boost_keywords': ['huevo', 'pan', 'café', 'jugo', 'fruta'],
                'suggested_combos': [
                    {'main': 'huevos', 'addon': 'café'},
                    {'main': 'hotcakes', 'addon': 'jugo'}
                ]
            },
            # Comida (12-16)
            'lunch': {
                'hours': range(12, 17),
                'boost_categories': ['platos fuertes', 'sopas', 'bebidas'],
                'boost_keywords': ['taco', 'hamburguesa', 'sopa', 'ensalada'],
                'suggested_combos': [
                    {'main': 'tacos', 'addon': 'refresco'},
                    {'main': 'hamburguesa', 'addon': 'papas'}
                ]
            },
            # Cena (17-22)
            'dinner': {
                'hours': range(17, 23),
                'boost_categories': ['platos fuertes', 'postres', 'bebidas'],
                'boost_keywords': ['cena', 'especial', 'postre'],
                'suggested_combos': [
                    {'main': 'plato fuerte', 'addon': 'postre'},
                    {'main': 'entrada', 'addon': 'bebida'}
                ]
            },
            # Noche/Late (22-7)
            'late_night': {
                'hours': list(range(22, 24)) + list(range(0, 7)),
                'boost_categories': ['antojitos', 'bebidas'],
                'boost_keywords': ['antojo', 'snack', 'botana'],
                'suggested_combos': []
            }
        }

        logger.info("SalesIntelligence inicializado")

    async def initialize(self):
        """Inicializar conexión a base de datos y cargar stats"""
        # Stats client deshabilitado - funcionalidad no requerida para ventas
        logger.info("SalesIntelligence inicializado (stats deshabilitados)")

    async def _refresh_stats(self):
        """Refrescar estadísticas de productos desde BD"""
        if not self._stats_client:
            return

        # Verificar si necesita refrescar
        if self._last_stats_update:
            elapsed = (datetime.now() - self._last_stats_update).total_seconds() / 60
            if elapsed < self._stats_cache_minutes:
                return

        try:
            self._product_stats = await self._stats_client.get_product_stats()
            self._last_stats_update = datetime.now()
            logger.info(f"Stats refrescadas: {len(self._product_stats)} productos con datos")
        except Exception as e:
            logger.error(f"Error refrescando stats: {e}")

    async def _refresh_promotions(self):
        """Refrescar promociones activas desde menu-service"""
        # Verificar si necesita refrescar
        if self._last_promotions_update:
            elapsed = (datetime.now() - self._last_promotions_update).total_seconds() / 60
            if elapsed < self._promotions_cache_minutes:
                return

        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self._menu_service_url}/api/v1/promotions/active"
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    if response.status == 200:
                        self._active_promotions = await response.json()
                        self._last_promotions_update = datetime.now()
                        logger.info(f"Promociones refrescadas: {len(self._active_promotions)} activas")
                    else:
                        logger.warning(f"Error obteniendo promociones: HTTP {response.status}")
        except aiohttp.ClientError as e:
            logger.error(f"Error conectando a menu-service para promociones: {e}")
        except Exception as e:
            logger.error(f"Error refrescando promociones: {e}")

    async def get_active_promotions(
        self,
        product_ids: List[int] = None
    ) -> List[Dict]:
        """
        Obtener promociones activas en este momento.

        Args:
            product_ids: Lista de IDs de productos para filtrar (opcional)

        Returns:
            Lista de promociones activas formateadas para el agente
        """
        await self._refresh_promotions()

        if not self._active_promotions:
            return []

        # Si no hay filtro, retornar todas
        if not product_ids:
            return self._active_promotions

        # Filtrar por productos
        filtered = []
        for promo in self._active_promotions:
            promo_products = promo.get('product_names', [])
            # Si la promo no tiene productos asignados, aplica a todo
            if not promo_products:
                filtered.append(promo)
                continue
            # Verificar si algún producto del pedido está en la promo
            # (Aquí comparamos por nombre ya que el agente trabaja con nombres)
            filtered.append(promo)

        return filtered

    async def get_promotion_pitch(
        self,
        ordered_items: List[Dict] = None
    ) -> Optional[str]:
        """
        Obtener la mejor frase de promoción para mencionar al cliente.

        Args:
            ordered_items: Items que el cliente ha ordenado (opcional)

        Returns:
            Frase para el agente de ventas o None
        """
        await self._refresh_promotions()

        if not self._active_promotions:
            return None

        # Ordenar por prioridad (mayor primero)
        sorted_promos = sorted(
            self._active_promotions,
            key=lambda x: x.get('priority', 1),
            reverse=True
        )

        # Si hay items ordenados, buscar promo que aplique
        if ordered_items:
            ordered_names = [item.get('name', '').lower() for item in ordered_items]

            for promo in sorted_promos:
                promo_products = [p.lower() for p in promo.get('product_names', [])]

                # Verificar si la promo aplica a algo ordenado
                if promo_products:
                    for ordered in ordered_names:
                        for promo_prod in promo_products:
                            if promo_prod in ordered or ordered in promo_prod:
                                pitch = promo.get('voice_pitch')
                                if pitch:
                                    return pitch
                                # Generar pitch por defecto
                                return self._generate_promotion_pitch(promo)

        # Retornar la promoción de mayor prioridad
        top_promo = sorted_promos[0] if sorted_promos else None
        if top_promo:
            pitch = top_promo.get('voice_pitch')
            if pitch:
                return pitch
            return self._generate_promotion_pitch(top_promo)

        return None

    def _generate_promotion_pitch(self, promo: Dict) -> str:
        """Generar frase de venta para una promoción"""
        promo_type = promo.get('promotion_type', '')
        name = promo.get('name', 'promocion especial')
        discount = promo.get('discount_value')
        special_price = promo.get('special_price')

        if promo_type == 'percentage' and discount:
            return f"Hoy tenemos {name} con {int(discount)}% de descuento. Te interesa?"

        if promo_type == 'fixed' and discount:
            return f"Tenemos {name}, te ahorrarias ${int(discount)} pesos. Quieres aprovecharlo?"

        if promo_type == '2x1':
            return f"Aprovecha nuestro {name}, llevate dos por el precio de uno."

        if promo_type == 'combo' and special_price:
            return f"El {name} esta a solo ${int(special_price)} pesos. Es una excelente opcion."

        if promo_type == 'buy_x_get_y':
            buy = promo.get('buy_quantity', 2)
            get = promo.get('get_quantity', 1)
            return f"Con la promocion {name}, compras {buy} y te llevas {get} gratis."

        return f"Tenemos {name} disponible hoy. Te gustaria aprovecharlo?"

    async def get_promotions_for_context(self) -> str:
        """
        Obtener resumen de promociones activas para incluir en contexto del LLM.

        Returns:
            String con las promociones formateadas para el system prompt
        """
        await self._refresh_promotions()

        if not self._active_promotions:
            return "No hay promociones activas en este momento."

        lines = ["PROMOCIONES ACTIVAS:"]
        for promo in self._active_promotions[:5]:  # Máximo 5 promociones en contexto
            name = promo.get('name', '')
            desc = promo.get('description', '')
            promo_type = promo.get('promotion_type', '')
            products = promo.get('product_names', [])

            line = f"- {name}"
            if desc:
                line += f": {desc}"
            if products:
                line += f" (aplica a: {', '.join(products[:3])})"

            lines.append(line)

        return "\n".join(lines)

    def get_current_time_slot(self) -> str:
        """Obtener el slot de tiempo actual"""
        current_hour = datetime.now().hour

        for slot_name, config in self.time_rules.items():
            if current_hour in config['hours']:
                return slot_name

        return 'lunch'  # Default

    async def get_popularity_score(self, product_id: int) -> float:
        """
        Obtener score de popularidad de un producto (0-100)
        Basado en datos reales de ventas
        """
        await self._refresh_stats()

        if product_id not in self._product_stats:
            return 50.0  # Score neutral para productos sin datos

        stats = self._product_stats[product_id]
        times_ordered = stats.get('times_ordered', 0)

        # Normalizar: max 100 órdenes = score 100
        score = min(100, (times_ordered / 100) * 100)

        return score

    async def get_top_products(self, limit: int = 5, category: Optional[str] = None) -> List[int]:
        """
        Obtener IDs de los productos más populares

        Args:
            limit: Cantidad de productos a retornar
            category: Filtrar por categoría (opcional)

        Returns:
            Lista de product_ids ordenados por popularidad
        """
        await self._refresh_stats()

        if not self._product_stats:
            return []

        # Ordenar por times_ordered descendente
        sorted_products = sorted(
            self._product_stats.items(),
            key=lambda x: x[1].get('times_ordered', 0),
            reverse=True
        )

        return [pid for pid, _ in sorted_products[:limit]]

    async def get_user_recommendations(
        self,
        user_id: Optional[int] = None,
        table_id: Optional[int] = None,
        current_cart: List[int] = None
    ) -> List[int]:
        """
        Obtener recomendaciones personalizadas para un usuario/mesa

        Args:
            user_id: ID del usuario (opcional)
            table_id: ID de la mesa (opcional)
            current_cart: Productos ya en el carrito

        Returns:
            Lista de product_ids recomendados
        """
        if not self._stats_client:
            return await self.get_top_products(5)

        recommendations = []
        current_cart = current_cart or []

        try:
            # 1. Obtener historial del usuario/mesa
            history = await self._stats_client.get_user_order_history(
                user_id=user_id,
                table_id=table_id
            )

            # 2. Obtener productos populares por hora actual
            current_hour = datetime.now().hour
            time_popular = await self._stats_client.get_popular_products_by_time(current_hour)

            # 3. Combinar recomendaciones
            # Prioridad: historial del usuario > popular por hora > general popular

            # Productos del historial que no están en el carrito actual
            for pid in history:
                if pid not in current_cart and pid not in recommendations:
                    recommendations.append(pid)
                    if len(recommendations) >= 3:
                        break

            # Productos populares por hora
            for pid in time_popular:
                if pid not in current_cart and pid not in recommendations:
                    recommendations.append(pid)
                    if len(recommendations) >= 5:
                        break

            # Completar con productos más populares globales
            if len(recommendations) < 5:
                top_products = await self.get_top_products(10)
                for pid in top_products:
                    if pid not in current_cart and pid not in recommendations:
                        recommendations.append(pid)
                        if len(recommendations) >= 5:
                            break

            logger.debug(f"Recomendaciones generadas: {recommendations}")
            return recommendations

        except Exception as e:
            logger.error(f"Error generando recomendaciones: {e}")
            return await self.get_top_products(5)

    def get_time_based_suggestion(self, menu: List[Dict]) -> Optional[Dict]:
        """
        Obtener sugerencia basada en la hora del día

        Args:
            menu: Lista de productos del menú

        Returns:
            Producto sugerido o None
        """
        time_slot = self.get_current_time_slot()
        rules = self.time_rules.get(time_slot, {})

        boost_keywords = rules.get('boost_keywords', [])

        # Buscar producto que coincida con keywords del horario
        for product in menu:
            product_name = product.get('name', '').lower()
            for keyword in boost_keywords:
                if keyword in product_name:
                    return product

        return None

    async def get_upsell_suggestions(
        self,
        ordered_items: List[Dict],
        menu: List[Dict]
    ) -> List[Tuple[Dict, str]]:
        """
        Obtener sugerencias de upselling basadas en lo que ordenó el cliente

        Args:
            ordered_items: Items que el cliente ya ordenó
            menu: Menú completo

        Returns:
            Lista de tuplas (producto_sugerido, pitch_de_venta)
        """
        suggestions = []
        ordered_categories = set()
        ordered_ids = set()

        # Identificar categorías ordenadas
        for item in ordered_items:
            ordered_ids.add(item.get('product_id'))
            cat_name = item.get('category', '').lower()
            if cat_name:
                ordered_categories.add(cat_name)

        # Reglas de upselling
        upsell_rules = [
            {
                'if_ordered': ['platos fuertes', 'entradas', 'antojitos'],
                'suggest': 'bebidas',
                'pitch': "¿Y para tomar? La limonada natural está recién hecha."
            },
            {
                'if_ordered': ['bebidas'],
                'suggest': 'entradas',
                'pitch': "¿Unas alitas para acompañar? Están en su punto."
            },
            {
                'if_ordered': ['platos fuertes'],
                'suggest': 'postres',
                'pitch': "¿Dejamos espacio para el postre? El pastel de chocolate es espectacular."
            },
            {
                'if_ordered': ['tacos', 'antojitos'],
                'suggest': 'extras',
                'pitch': "¿Le ponemos guacamole? Queda perfecto."
            }
        ]

        for rule in upsell_rules:
            # Verificar si aplica la regla
            if any(cat in ordered_categories for cat in rule['if_ordered']):
                # Buscar producto de la categoría sugerida
                suggest_cat = rule['suggest'].lower()

                for product in menu:
                    prod_cat = product.get('category', {}).get('name', '').lower()
                    if suggest_cat in prod_cat and product['id'] not in ordered_ids:
                        suggestions.append((product, rule['pitch']))
                        break

        return suggestions[:2]  # Máximo 2 sugerencias

    async def score_product_for_recommendation(
        self,
        product: Dict,
        user_history: List[int] = None,
        current_cart: List[int] = None,
        time_boost: bool = True
    ) -> float:
        """
        Calcular score total de un producto para recomendación

        Factores:
        - Popularidad global (30%)
        - Historial del usuario (25%)
        - Relevancia por horario (20%)
        - No está en carrito (15%)
        - Margen de ganancia (10%) - futuro

        Returns:
            Score de 0 a 100
        """
        score = 0.0
        product_id = product.get('id')

        # 1. Popularidad global (30%)
        popularity = await self.get_popularity_score(product_id)
        score += popularity * 0.30

        # 2. Historial del usuario (25%)
        if user_history and product_id in user_history:
            score += 25.0

        # 3. Relevancia por horario (20%)
        if time_boost:
            time_slot = self.get_current_time_slot()
            rules = self.time_rules.get(time_slot, {})
            boost_keywords = rules.get('boost_keywords', [])

            product_name = product.get('name', '').lower()
            if any(kw in product_name for kw in boost_keywords):
                score += 20.0

        # 4. No está en carrito (15%)
        current_cart = current_cart or []
        if product_id not in current_cart:
            score += 15.0

        # 5. Margen de ganancia (10%) - placeholder para futuro
        score += 5.0  # Valor neutral por ahora

        return min(100.0, score)

    async def get_smart_recommendations(
        self,
        menu: List[Dict],
        user_id: Optional[int] = None,
        table_id: Optional[int] = None,
        current_cart: List[int] = None,
        limit: int = 3
    ) -> List[Dict]:
        """
        Obtener recomendaciones inteligentes con scoring completo

        Returns:
            Lista de productos ordenados por score de recomendación
        """
        current_cart = current_cart or []
        user_history = []

        # Obtener historial si hay usuario/mesa
        if self._stats_client and (user_id or table_id):
            try:
                user_history = await self._stats_client.get_user_order_history(
                    user_id=user_id,
                    table_id=table_id
                )
            except Exception as e:
                logger.warning(f"No se pudo obtener historial: {e}")

        # Calcular score para cada producto
        scored_products = []
        for product in menu:
            if product['id'] not in current_cart:
                score = await self.score_product_for_recommendation(
                    product=product,
                    user_history=user_history,
                    current_cart=current_cart,
                    time_boost=True
                )
                scored_products.append((product, score))

        # Ordenar por score descendente
        scored_products.sort(key=lambda x: x[1], reverse=True)

        # Retornar top productos
        recommendations = [prod for prod, score in scored_products[:limit]]

        logger.info(f"Smart recommendations: {[p['name'] for p in recommendations]}")
        return recommendations


# Instancia global
_sales_intelligence: Optional[SalesIntelligence] = None


async def get_sales_intelligence() -> SalesIntelligence:
    """Obtener instancia global de SalesIntelligence"""
    global _sales_intelligence
    if _sales_intelligence is None:
        _sales_intelligence = SalesIntelligence()
        await _sales_intelligence.initialize()
    return _sales_intelligence
