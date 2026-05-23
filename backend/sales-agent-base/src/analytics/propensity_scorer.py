"""
================================================================================
PROPENSITY SCORING SYSTEM - FASE 2
================================================================================
Sistema de scoring que predice la probabilidad de que un cliente
acepte una recomendación basado en múltiples factores
================================================================================
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class CustomerSegment(Enum):
    """Segmentos de cliente basados en comportamiento"""
    NEW = "new"  # Primera visita
    RETURNING = "returning"  # Ha visitado antes
    FREQUENT = "frequent"  # Visita frecuentemente
    HIGH_VALUE = "high_value"  # Gasta más que el promedio


@dataclass
class CustomerProfile:
    """Perfil del cliente para scoring"""
    segment: CustomerSegment
    avg_order_value: float
    total_orders: int
    preferred_categories: List[str]
    last_order_items: List[int]
    acceptance_rate: float  # Tasa de aceptación de upselling


class PropensityScorer:
    """
    Calcula la probabilidad de aceptación de recomendaciones
    usando múltiples señales contextuales
    """

    def __init__(self):
        # Pesos para cada factor (suman 1.0)
        self.weights = {
            'product_popularity': 0.20,
            'price_fit': 0.20,
            'category_affinity': 0.15,
            'time_relevance': 0.15,
            'basket_complementarity': 0.15,
            'customer_segment': 0.15
        }

        # Umbrales de precio por segmento
        self.price_thresholds = {
            CustomerSegment.NEW: 150,
            CustomerSegment.RETURNING: 200,
            CustomerSegment.FREQUENT: 250,
            CustomerSegment.HIGH_VALUE: 400
        }

        # Multiplicadores por segmento
        self.segment_multipliers = {
            CustomerSegment.NEW: 0.7,  # Más cauteloso con nuevos
            CustomerSegment.RETURNING: 0.9,
            CustomerSegment.FREQUENT: 1.1,
            CustomerSegment.HIGH_VALUE: 1.3
        }

        logger.info("PropensityScorer inicializado")

    def calculate_propensity(
        self,
        product: Dict,
        customer_profile: Optional[CustomerProfile],
        cart_items: List[Dict],
        menu_stats: Dict[int, Dict],
        current_hour: int
    ) -> Tuple[float, Dict[str, float]]:
        """
        Calcular probabilidad de aceptación de un producto

        Args:
            product: Producto a evaluar
            customer_profile: Perfil del cliente (opcional)
            cart_items: Items actuales en el carrito
            menu_stats: Estadísticas de popularidad del menú
            current_hour: Hora actual del día

        Returns:
            Tupla (score_total, breakdown_por_factor)
        """
        scores = {}
        product_id = product.get('id')
        product_price = float(product.get('price', 0))
        product_category = product.get('category', {}).get('name', '').lower()

        # 1. Popularidad del producto (0-1)
        if product_id in menu_stats:
            times_ordered = menu_stats[product_id].get('times_ordered', 0)
            # Normalizar: 100+ órdenes = score 1.0
            scores['product_popularity'] = min(1.0, times_ordered / 100)
        else:
            scores['product_popularity'] = 0.5  # Neutral

        # 2. Ajuste de precio (0-1)
        if customer_profile:
            threshold = self.price_thresholds.get(customer_profile.segment, 200)
            if product_price <= threshold * 0.5:
                scores['price_fit'] = 1.0  # Muy accesible
            elif product_price <= threshold:
                scores['price_fit'] = 0.8  # Accesible
            elif product_price <= threshold * 1.5:
                scores['price_fit'] = 0.5  # Moderado
            else:
                scores['price_fit'] = 0.3  # Caro para el segmento
        else:
            # Sin perfil, usar precio promedio ($150)
            if product_price <= 100:
                scores['price_fit'] = 1.0
            elif product_price <= 200:
                scores['price_fit'] = 0.7
            else:
                scores['price_fit'] = 0.4

        # 3. Afinidad de categoría (0-1)
        if customer_profile and customer_profile.preferred_categories:
            if product_category in customer_profile.preferred_categories:
                scores['category_affinity'] = 1.0
            else:
                scores['category_affinity'] = 0.4
        else:
            scores['category_affinity'] = 0.5  # Neutral

        # 4. Relevancia por horario (0-1)
        scores['time_relevance'] = self._calculate_time_relevance(
            product_category, current_hour
        )

        # 5. Complementariedad con carrito (0-1)
        scores['basket_complementarity'] = self._calculate_basket_fit(
            product, cart_items
        )

        # 6. Factor de segmento de cliente (0-1)
        if customer_profile:
            multiplier = self.segment_multipliers.get(customer_profile.segment, 1.0)
            scores['customer_segment'] = min(1.0, multiplier * 0.7)
        else:
            scores['customer_segment'] = 0.5  # Neutral

        # Calcular score total ponderado
        total_score = sum(
            scores[factor] * self.weights[factor]
            for factor in scores
        )

        # Ajustar por tasa de aceptación histórica si existe
        if customer_profile and customer_profile.acceptance_rate > 0:
            total_score = total_score * 0.8 + customer_profile.acceptance_rate * 0.2

        return total_score, scores

    def _calculate_time_relevance(self, category: str, hour: int) -> float:
        """Calcular relevancia de una categoría según la hora"""

        # Mapeo de categorías a horarios óptimos
        time_category_map = {
            'desayuno': (6, 11),
            'bebidas calientes': (6, 10),
            'jugos': (7, 12),
            'platos fuertes': (12, 22),
            'entradas': (11, 21),
            'postres': (13, 22),
            'bebidas': (11, 23),
            'antojitos': (18, 23)
        }

        for cat_keyword, (start, end) in time_category_map.items():
            if cat_keyword in category:
                if start <= hour <= end:
                    return 1.0
                elif abs(hour - start) <= 2 or abs(hour - end) <= 2:
                    return 0.6
                else:
                    return 0.3

        return 0.5  # Neutral para categorías no mapeadas

    def _calculate_basket_fit(
        self,
        product: Dict,
        cart_items: List[Dict]
    ) -> float:
        """Calcular qué tan bien complementa el producto al carrito"""

        if not cart_items:
            return 0.7  # Carrito vacío, moderadamente bueno

        product_category = product.get('category', {}).get('name', '').lower()
        cart_categories = set()

        for item in cart_items:
            cat = item.get('category', {}).get('name', '').lower()
            if cat:
                cart_categories.add(cat)

        # Reglas de complementariedad
        complement_rules = {
            ('platos fuertes', 'bebidas'): 1.0,
            ('entradas', 'bebidas'): 0.9,
            ('platos fuertes', 'postres'): 0.8,
            ('entradas', 'platos fuertes'): 0.9,
            ('antojitos', 'bebidas'): 1.0,
        }

        best_score = 0.3  # Mínimo si no hay complemento

        for (cat1, cat2), score in complement_rules.items():
            if (product_category == cat2 and cat1 in cart_categories) or \
               (product_category == cat1 and cat2 in cart_categories):
                best_score = max(best_score, score)

        # Penalizar si ya hay producto de la misma categoría
        if product_category in cart_categories:
            best_score *= 0.5

        return best_score

    def rank_recommendations(
        self,
        candidates: List[Dict],
        customer_profile: Optional[CustomerProfile],
        cart_items: List[Dict],
        menu_stats: Dict[int, Dict],
        limit: int = 3
    ) -> List[Tuple[Dict, float, Dict]]:
        """
        Rankear una lista de productos candidatos por propensión

        Returns:
            Lista de tuplas (producto, score, breakdown)
        """
        current_hour = datetime.now().hour
        scored_candidates = []

        for product in candidates:
            score, breakdown = self.calculate_propensity(
                product=product,
                customer_profile=customer_profile,
                cart_items=cart_items,
                menu_stats=menu_stats,
                current_hour=current_hour
            )
            scored_candidates.append((product, score, breakdown))

        # Ordenar por score descendente
        scored_candidates.sort(key=lambda x: x[1], reverse=True)

        return scored_candidates[:limit]

    def should_recommend(
        self,
        score: float,
        customer_profile: Optional[CustomerProfile]
    ) -> bool:
        """
        Decidir si se debe hacer la recomendación basado en el score

        Args:
            score: Score de propensión calculado
            customer_profile: Perfil del cliente

        Returns:
            True si se debe recomendar
        """
        # Umbrales por segmento
        if customer_profile:
            segment_thresholds = {
                CustomerSegment.NEW: 0.5,  # Más selectivo con nuevos
                CustomerSegment.RETURNING: 0.45,
                CustomerSegment.FREQUENT: 0.4,
                CustomerSegment.HIGH_VALUE: 0.35  # Más agresivo con high value
            }
            threshold = segment_thresholds.get(customer_profile.segment, 0.45)
        else:
            threshold = 0.45  # Default

        return score >= threshold

    def get_pitch_intensity(self, score: float) -> str:
        """
        Determinar la intensidad del pitch de venta según el score

        Returns:
            'soft', 'medium', o 'strong'
        """
        if score >= 0.7:
            return 'strong'  # Pitch agresivo
        elif score >= 0.5:
            return 'medium'  # Pitch moderado
        else:
            return 'soft'  # Pitch suave


# Instancia global
_propensity_scorer: Optional[PropensityScorer] = None


def get_propensity_scorer() -> PropensityScorer:
    """Obtener instancia global del PropensityScorer"""
    global _propensity_scorer
    if _propensity_scorer is None:
        _propensity_scorer = PropensityScorer()
    return _propensity_scorer
