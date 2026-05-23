"""
================================================================================
SEASONALITY ANALYZER - FASE 3
================================================================================
Analiza patrones estacionales para optimizar recomendaciones:
- Patrones por día de la semana
- Patrones por hora del día
- Eventos especiales (fiestas, días festivos)
- Clima (si se integra con API externa)
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
class SeasonalPattern:
    """Patrón estacional de un producto"""
    product_id: int
    product_name: str

    # Patrones por día (0=Lunes, 6=Domingo)
    day_of_week_scores: Dict[int, float]

    # Patrones por hora (0-23)
    hour_scores: Dict[int, float]

    # Mejor momento
    peak_day: int
    peak_hour: int
    peak_score: float


class SeasonalityAnalyzer:
    """
    Analiza patrones de ventas por tiempo para optimizar
    recomendaciones según el momento
    """

    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or self._build_database_url()
        self._pool = None

        # Cache de patrones estacionales
        self._patterns: Dict[int, SeasonalPattern] = {}
        self._last_analysis: Optional[datetime] = None
        self._analysis_ttl_hours = 24  # Re-analizar cada 24 horas

        # Eventos especiales (placeholder - en producción vendría de un calendario)
        self.special_events = {
            # (mes, día): nombre del evento
            (1, 1): 'año_nuevo',
            (2, 14): 'san_valentin',
            (5, 10): 'dia_madres',
            (9, 15): 'fiestas_patrias',
            (9, 16): 'fiestas_patrias',
            (11, 2): 'dia_muertos',
            (12, 24): 'navidad',
            (12, 25): 'navidad',
            (12, 31): 'año_nuevo'
        }

        # Productos recomendados por evento
        self.event_recommendations = {
            'san_valentin': ['postre', 'vino', 'especial'],
            'fiestas_patrias': ['antojitos', 'mexicano', 'tradicional'],
            'navidad': ['familiar', 'especial', 'postre'],
            'dia_madres': ['especial', 'postre', 'elegante']
        }

        logger.info("SeasonalityAnalyzer inicializado")

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
            logger.info("SeasonalityAnalyzer conectado a BD")
        except Exception as e:
            logger.error(f"Error conectando SeasonalityAnalyzer: {e}")

    async def disconnect(self):
        """Cerrar conexión"""
        if self._pool:
            await self._pool.close()

    async def analyze_patterns(self, days_back: int = 90):
        """
        Analizar patrones estacionales de los últimos N días

        Args:
            days_back: Días hacia atrás para analizar
        """
        if not self._pool:
            await self.connect()

        if not self._pool:
            logger.warning("No hay conexión a BD para análisis estacional")
            return

        try:
            async with self._pool.acquire() as conn:
                # Obtener datos por producto, día de la semana y hora
                rows = await conn.fetch("""
                    SELECT
                        oi.product_id,
                        p.name as product_name,
                        EXTRACT(DOW FROM o.created_at) as day_of_week,
                        EXTRACT(HOUR FROM o.created_at) as hour,
                        COUNT(*) as order_count
                    FROM order_items oi
                    JOIN orders o ON oi.order_id = o.id
                    JOIN products p ON oi.product_id = p.id
                    WHERE o.created_at >= CURRENT_DATE - $1 * INTERVAL '1 day'
                      AND o.status != 'cancelled'
                    GROUP BY oi.product_id, p.name, day_of_week, hour
                    ORDER BY oi.product_id
                """, days_back)

                # Procesar datos
                product_data = defaultdict(lambda: {
                    'name': '',
                    'by_day': defaultdict(int),
                    'by_hour': defaultdict(int),
                    'total': 0
                })

                for row in rows:
                    pid = row['product_id']
                    product_data[pid]['name'] = row['product_name']
                    product_data[pid]['by_day'][int(row['day_of_week'])] += row['order_count']
                    product_data[pid]['by_hour'][int(row['hour'])] += row['order_count']
                    product_data[pid]['total'] += row['order_count']

                # Crear patrones normalizados
                self._patterns.clear()

                for pid, data in product_data.items():
                    if data['total'] < 10:  # Ignorar productos con pocas ventas
                        continue

                    # Normalizar scores por día (0-100)
                    day_scores = {}
                    max_day = max(data['by_day'].values()) if data['by_day'] else 1
                    for day in range(7):
                        day_scores[day] = (data['by_day'].get(day, 0) / max_day) * 100

                    # Normalizar scores por hora (0-100)
                    hour_scores = {}
                    max_hour = max(data['by_hour'].values()) if data['by_hour'] else 1
                    for hour in range(24):
                        hour_scores[hour] = (data['by_hour'].get(hour, 0) / max_hour) * 100

                    # Encontrar picos
                    peak_day = max(day_scores.keys(), key=lambda k: day_scores[k])
                    peak_hour = max(hour_scores.keys(), key=lambda k: hour_scores[k])

                    self._patterns[pid] = SeasonalPattern(
                        product_id=pid,
                        product_name=data['name'],
                        day_of_week_scores=day_scores,
                        hour_scores=hour_scores,
                        peak_day=peak_day,
                        peak_hour=peak_hour,
                        peak_score=hour_scores[peak_hour]
                    )

                self._last_analysis = datetime.now()

                logger.info(f"Patrones estacionales analizados para {len(self._patterns)} productos")

        except Exception as e:
            logger.error(f"Error analizando patrones estacionales: {e}")

    async def _ensure_patterns_fresh(self):
        """Asegurar que los patrones estén actualizados"""
        if not self._last_analysis:
            await self.analyze_patterns()
        else:
            hours_elapsed = (datetime.now() - self._last_analysis).total_seconds() / 3600
            if hours_elapsed > self._analysis_ttl_hours:
                await self.analyze_patterns()

    async def get_seasonal_score(self, product_id: int) -> float:
        """
        Obtener score estacional actual para un producto

        Args:
            product_id: ID del producto

        Returns:
            Score de 0-100 basado en qué tan bueno es este momento para el producto
        """
        await self._ensure_patterns_fresh()

        if product_id not in self._patterns:
            return 50.0  # Neutral

        pattern = self._patterns[product_id]
        now = datetime.now()
        current_day = now.weekday()  # 0=Lunes
        current_hour = now.hour

        # Combinar scores de día y hora
        day_score = pattern.day_of_week_scores.get(current_day, 50)
        hour_score = pattern.hour_scores.get(current_hour, 50)

        # Promedio ponderado (hora pesa más)
        combined_score = day_score * 0.3 + hour_score * 0.7

        return combined_score

    async def get_best_products_now(
        self,
        menu: List[Dict],
        limit: int = 5
    ) -> List[Dict]:
        """
        Obtener los mejores productos para el momento actual

        Args:
            menu: Menú completo
            limit: Máximo de productos

        Returns:
            Lista de productos optimizados para el momento
        """
        await self._ensure_patterns_fresh()

        scored_products = []

        for product in menu:
            pid = product.get('id')
            score = await self.get_seasonal_score(pid)
            scored_products.append((product, score))

        # Ordenar por score
        scored_products.sort(key=lambda x: x[1], reverse=True)

        return [p for p, _ in scored_products[:limit]]

    def get_current_event(self) -> Optional[str]:
        """Obtener evento especial actual si existe"""
        now = datetime.now()
        return self.special_events.get((now.month, now.day))

    def get_event_keywords(self) -> List[str]:
        """
        Obtener keywords para filtrar productos según evento actual

        Returns:
            Lista de keywords para buscar en nombres/tags de productos
        """
        event = self.get_current_event()
        if event:
            return self.event_recommendations.get(event, [])
        return []

    async def get_trending_by_season(
        self,
        menu: List[Dict],
        limit: int = 3
    ) -> List[Dict]:
        """
        Obtener productos que históricamente son populares
        en esta época del año

        Args:
            menu: Menú completo
            limit: Máximo de productos

        Returns:
            Lista de productos estacionalmente populares
        """
        await self._ensure_patterns_fresh()

        now = datetime.now()
        current_day = now.weekday()
        current_hour = now.hour

        # Productos con score alto para día Y hora actual
        trending = []

        for pid, pattern in self._patterns.items():
            day_score = pattern.day_of_week_scores.get(current_day, 0)
            hour_score = pattern.hour_scores.get(current_hour, 0)

            # Solo incluir si está en su "zona óptima" (>70 en ambos)
            if day_score >= 60 and hour_score >= 60:
                for product in menu:
                    if product.get('id') == pid:
                        product_copy = product.copy()
                        product_copy['seasonal_score'] = (day_score + hour_score) / 2
                        trending.append(product_copy)
                        break

        trending.sort(key=lambda x: x.get('seasonal_score', 0), reverse=True)

        return trending[:limit]

    def get_day_name(self, day_num: int) -> str:
        """Convertir número de día a nombre"""
        days = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
        return days[day_num] if 0 <= day_num <= 6 else 'Desconocido'

    def get_pattern_summary(self, product_id: int) -> Optional[str]:
        """
        Obtener resumen legible del patrón de un producto

        Returns:
            String con resumen del patrón
        """
        if product_id not in self._patterns:
            return None

        p = self._patterns[product_id]

        # Encontrar mejores días
        best_days = sorted(
            p.day_of_week_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )[:2]

        # Encontrar mejores horas
        best_hours = sorted(
            p.hour_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )[:2]

        summary = f"""
📊 Patrón de {p.product_name}:

📅 Mejores días:
  - {self.get_day_name(best_days[0][0])}: {best_days[0][1]:.0f}%
  - {self.get_day_name(best_days[1][0])}: {best_days[1][1]:.0f}%

⏰ Mejores horas:
  - {best_hours[0][0]}:00: {best_hours[0][1]:.0f}%
  - {best_hours[1][0]}:00: {best_hours[1][1]:.0f}%

🏆 Momento peak: {self.get_day_name(p.peak_day)} a las {p.peak_hour}:00
"""
        return summary


# Instancia global
_seasonality_analyzer: Optional[SeasonalityAnalyzer] = None


async def get_seasonality_analyzer() -> SeasonalityAnalyzer:
    """Obtener instancia global del SeasonalityAnalyzer"""
    global _seasonality_analyzer
    if _seasonality_analyzer is None:
        _seasonality_analyzer = SeasonalityAnalyzer()
        await _seasonality_analyzer.connect()
        await _seasonality_analyzer.analyze_patterns()
    return _seasonality_analyzer
