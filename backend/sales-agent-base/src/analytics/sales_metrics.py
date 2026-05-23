"""
================================================================================
SALES METRICS DASHBOARD - FASE 2
================================================================================
Sistema de métricas para tracking de efectividad de ventas:
- Tasa de conversión de upselling
- Revenue incremental por sugerencias
- Análisis de qué sugerencias funcionan mejor
- Métricas en tiempo real
================================================================================
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from collections import defaultdict
import asyncpg

logger = logging.getLogger(__name__)


@dataclass
class UpsellEvent:
    """Evento de upselling para tracking"""
    timestamp: datetime
    session_id: str
    suggested_product_id: int
    suggested_product_name: str
    suggested_product_price: float
    suggestion_type: str  # 'upsell', 'cross_sell', 'addon'
    trigger_product_id: Optional[int]  # Producto que disparó la sugerencia
    accepted: bool
    rejection_reason: Optional[str] = None


@dataclass
class SalesMetricsSnapshot:
    """Snapshot de métricas de ventas"""
    timestamp: datetime
    period: str  # 'hourly', 'daily', 'weekly'

    # Métricas de upselling
    total_suggestions: int = 0
    accepted_suggestions: int = 0
    conversion_rate: float = 0.0

    # Revenue
    incremental_revenue: float = 0.0
    avg_order_value: float = 0.0
    avg_order_value_with_upsell: float = 0.0

    # Por tipo de sugerencia
    by_suggestion_type: Dict[str, Dict] = field(default_factory=dict)

    # Por producto
    top_performing_products: List[Dict] = field(default_factory=list)
    worst_performing_products: List[Dict] = field(default_factory=list)

    # Por hora del día
    by_hour: Dict[int, Dict] = field(default_factory=dict)


class SalesMetricsTracker:
    """
    Tracker de métricas de ventas en tiempo real
    """

    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or self._build_database_url()
        self._pool = None

        # Eventos en memoria (último período)
        self._events: List[UpsellEvent] = []
        self._events_max_age_hours = 24

        # Cache de métricas
        self._metrics_cache: Optional[SalesMetricsSnapshot] = None
        self._cache_timestamp: Optional[datetime] = None
        self._cache_ttl_minutes = 5

        # Contadores en tiempo real
        self._realtime_counters = {
            'suggestions_today': 0,
            'accepted_today': 0,
            'revenue_today': 0.0
        }

        logger.info("SalesMetricsTracker inicializado")

    def _build_database_url(self) -> str:
        return "postgresql://restaurant:restaurant_2025_prod@postgres:5432/restaurant_db"

    async def connect(self):
        """Conectar a la base de datos"""
        try:
            self._pool = await asyncpg.create_pool(
                self.database_url,
                min_size=1,
                max_size=3
            )
            logger.info("SalesMetricsTracker conectado a BD")
        except Exception as e:
            logger.error(f"Error conectando SalesMetricsTracker: {e}")

    async def disconnect(self):
        """Desconectar de la base de datos"""
        if self._pool:
            await self._pool.close()

    def track_suggestion(
        self,
        session_id: str,
        product: Dict,
        suggestion_type: str,
        trigger_product_id: Optional[int] = None
    ):
        """
        Registrar una sugerencia de upselling

        Args:
            session_id: ID de la sesión
            product: Producto sugerido
            suggestion_type: Tipo de sugerencia
            trigger_product_id: Producto que disparó la sugerencia
        """
        event = UpsellEvent(
            timestamp=datetime.now(),
            session_id=session_id,
            suggested_product_id=product.get('id'),
            suggested_product_name=product.get('name', ''),
            suggested_product_price=float(product.get('price', 0)),
            suggestion_type=suggestion_type,
            trigger_product_id=trigger_product_id,
            accepted=False  # Pendiente hasta que se confirme
        )

        self._events.append(event)
        self._realtime_counters['suggestions_today'] += 1
        self._cleanup_old_events()

        logger.debug(f"[METRICS] Sugerencia registrada: {product.get('name')} ({suggestion_type})")

    def track_acceptance(
        self,
        session_id: str,
        product_id: int,
        accepted: bool,
        rejection_reason: Optional[str] = None
    ):
        """
        Registrar si una sugerencia fue aceptada o rechazada

        Args:
            session_id: ID de la sesión
            product_id: ID del producto sugerido
            accepted: Si fue aceptado
            rejection_reason: Razón de rechazo (si aplica)
        """
        # Buscar el evento más reciente para esta sesión/producto
        for event in reversed(self._events):
            if (event.session_id == session_id and
                event.suggested_product_id == product_id and
                not event.accepted):

                event.accepted = accepted
                event.rejection_reason = rejection_reason

                if accepted:
                    self._realtime_counters['accepted_today'] += 1
                    self._realtime_counters['revenue_today'] += event.suggested_product_price

                logger.debug(
                    f"[METRICS] Respuesta registrada: {event.suggested_product_name} "
                    f"- {'ACEPTADO' if accepted else 'RECHAZADO'}"
                )
                break

    def _cleanup_old_events(self):
        """Limpiar eventos antiguos"""
        cutoff = datetime.now() - timedelta(hours=self._events_max_age_hours)
        self._events = [e for e in self._events if e.timestamp > cutoff]

    def get_realtime_metrics(self) -> Dict:
        """
        Obtener métricas en tiempo real

        Returns:
            Dict con métricas actuales
        """
        total = self._realtime_counters['suggestions_today']
        accepted = self._realtime_counters['accepted_today']

        return {
            'suggestions_today': total,
            'accepted_today': accepted,
            'conversion_rate': (accepted / total * 100) if total > 0 else 0,
            'incremental_revenue_today': self._realtime_counters['revenue_today'],
            'events_in_memory': len(self._events)
        }

    async def get_metrics_snapshot(
        self,
        period: str = 'daily'
    ) -> SalesMetricsSnapshot:
        """
        Obtener snapshot completo de métricas

        Args:
            period: 'hourly', 'daily', 'weekly'

        Returns:
            SalesMetricsSnapshot con todas las métricas
        """
        # Verificar cache
        if self._metrics_cache and self._cache_timestamp:
            cache_age = (datetime.now() - self._cache_timestamp).total_seconds() / 60
            if cache_age < self._cache_ttl_minutes:
                return self._metrics_cache

        snapshot = SalesMetricsSnapshot(
            timestamp=datetime.now(),
            period=period
        )

        # Calcular desde eventos en memoria
        self._calculate_from_events(snapshot)

        # Obtener datos históricos de BD si está disponible
        if self._pool:
            await self._enrich_from_database(snapshot, period)

        # Actualizar cache
        self._metrics_cache = snapshot
        self._cache_timestamp = datetime.now()

        return snapshot

    def _calculate_from_events(self, snapshot: SalesMetricsSnapshot):
        """Calcular métricas desde eventos en memoria"""

        if not self._events:
            return

        snapshot.total_suggestions = len(self._events)
        snapshot.accepted_suggestions = sum(1 for e in self._events if e.accepted)

        if snapshot.total_suggestions > 0:
            snapshot.conversion_rate = snapshot.accepted_suggestions / snapshot.total_suggestions

        # Revenue incremental
        snapshot.incremental_revenue = sum(
            e.suggested_product_price for e in self._events if e.accepted
        )

        # Por tipo de sugerencia
        by_type = defaultdict(lambda: {'total': 0, 'accepted': 0, 'revenue': 0})
        for event in self._events:
            by_type[event.suggestion_type]['total'] += 1
            if event.accepted:
                by_type[event.suggestion_type]['accepted'] += 1
                by_type[event.suggestion_type]['revenue'] += event.suggested_product_price

        for stype, data in by_type.items():
            data['conversion_rate'] = data['accepted'] / data['total'] if data['total'] > 0 else 0
            snapshot.by_suggestion_type[stype] = dict(data)

        # Por hora
        by_hour = defaultdict(lambda: {'total': 0, 'accepted': 0})
        for event in self._events:
            hour = event.timestamp.hour
            by_hour[hour]['total'] += 1
            if event.accepted:
                by_hour[hour]['accepted'] += 1

        for hour, data in by_hour.items():
            data['conversion_rate'] = data['accepted'] / data['total'] if data['total'] > 0 else 0
            snapshot.by_hour[hour] = dict(data)

        # Top productos
        product_performance = defaultdict(lambda: {'total': 0, 'accepted': 0, 'name': ''})
        for event in self._events:
            pid = event.suggested_product_id
            product_performance[pid]['total'] += 1
            product_performance[pid]['name'] = event.suggested_product_name
            if event.accepted:
                product_performance[pid]['accepted'] += 1

        # Calcular tasas y ordenar
        products_with_rate = []
        for pid, data in product_performance.items():
            if data['total'] >= 3:  # Mínimo 3 sugerencias para contar
                rate = data['accepted'] / data['total']
                products_with_rate.append({
                    'product_id': pid,
                    'name': data['name'],
                    'total': data['total'],
                    'accepted': data['accepted'],
                    'conversion_rate': rate
                })

        products_with_rate.sort(key=lambda x: x['conversion_rate'], reverse=True)
        snapshot.top_performing_products = products_with_rate[:5]
        snapshot.worst_performing_products = products_with_rate[-5:][::-1]

    async def _enrich_from_database(self, snapshot: SalesMetricsSnapshot, period: str):
        """Enriquecer métricas con datos de BD"""

        if not self._pool:
            return

        try:
            async with self._pool.acquire() as conn:
                # Obtener valor promedio de orden
                if period == 'daily':
                    time_filter = "created_at >= CURRENT_DATE"
                elif period == 'weekly':
                    time_filter = "created_at >= CURRENT_DATE - INTERVAL '7 days'"
                else:
                    time_filter = "created_at >= CURRENT_TIMESTAMP - INTERVAL '1 hour'"

                avg_order = await conn.fetchval(f"""
                    SELECT AVG(total_amount)
                    FROM orders
                    WHERE {time_filter} AND status != 'cancelled'
                """)

                if avg_order:
                    snapshot.avg_order_value = float(avg_order)

        except Exception as e:
            logger.error(f"Error enriqueciendo métricas desde BD: {e}")

    def reset_daily_counters(self):
        """Resetear contadores diarios (llamar a medianoche)"""
        self._realtime_counters = {
            'suggestions_today': 0,
            'accepted_today': 0,
            'revenue_today': 0.0
        }
        logger.info("Contadores diarios reseteados")

    def get_performance_report(self) -> str:
        """
        Generar reporte de rendimiento legible

        Returns:
            String con reporte formateado
        """
        metrics = self.get_realtime_metrics()

        report = f"""
=== SALES METRICS REPORT ===
Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')}

📊 MÉTRICAS DE HOY:
- Sugerencias totales: {metrics['suggestions_today']}
- Sugerencias aceptadas: {metrics['accepted_today']}
- Tasa de conversión: {metrics['conversion_rate']:.1f}%
- Revenue incremental: ${metrics['incremental_revenue_today']:.2f}

📈 EVENTOS EN MEMORIA: {metrics['events_in_memory']}
================================
"""
        return report


# Instancia global
_metrics_tracker: Optional[SalesMetricsTracker] = None


async def get_metrics_tracker() -> SalesMetricsTracker:
    """Obtener instancia global del SalesMetricsTracker"""
    global _metrics_tracker
    if _metrics_tracker is None:
        _metrics_tracker = SalesMetricsTracker()
        await _metrics_tracker.connect()
    return _metrics_tracker
