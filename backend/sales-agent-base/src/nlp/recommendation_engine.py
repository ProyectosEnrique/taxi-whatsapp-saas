"""
================================================================================
SISTEMA DE RECOMENDACIONES INTELIGENTE
================================================================================
Motor de recomendaciones que simula "aprendizaje" mediante:
- Memoria contextual (historial de pedidos)
- Datos reales de popularidad y ventas
- Reglas adaptativas según contexto
- Personalización con LLM
================================================================================
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, time
from groq import Groq

logger = logging.getLogger(__name__)


class RecommendationEngine:
    """
    Motor de recomendaciones inteligente que combina:
    1. Datos históricos (popularidad, ventas)
    2. Contexto del usuario (preferencias, historial)
    3. Reglas de negocio (momento del día, presupuesto)
    4. LLM para personalización
    """

    def __init__(self, groq_api_key: str, model: str = "llama-3.1-8b-instant"):
        self.client = Groq(api_key=groq_api_key)
        self.model = model
        logger.info("RecommendationEngine inicializado")

    def calculate_product_score(
        self,
        product: Dict,
        context: Dict,
        popularity_data: Optional[Dict] = None
    ) -> float:
        """
        Calcular puntuación del producto basada en múltiples factores

        Args:
            product: Datos del producto
            context: Contexto del usuario (preferencias, historial, momento)
            popularity_data: Datos de popularidad del producto

        Returns:
            Score de 0 a 100
        """
        score = 50.0  # Base score

        # 1. POPULARIDAD (peso 30%)
        if popularity_data:
            times_ordered = popularity_data.get('times_ordered', 0)
            if times_ordered > 100:
                score += 30
            elif times_ordered > 50:
                score += 20
            elif times_ordered > 20:
                score += 10
            elif times_ordered > 5:
                score += 5

        # 2. PRECIO vs PRESUPUESTO (peso 20%)
        budget = context.get('budget', '').lower()
        price = float(product.get('price', 0))

        if budget:
            if 'económico' in budget or 'barato' in budget:
                if price <= 100:
                    score += 20
                elif price <= 150:
                    score += 10
                else:
                    score -= 15
            elif 'premium' in budget or 'caro' in budget:
                if price >= 150:
                    score += 20
                elif price >= 100:
                    score += 10
                else:
                    score -= 10

        # 3. PREFERENCIAS DIETÉTICAS (peso 25%)
        dietary_pref = context.get('dietary_preference', '').lower()
        product_tags = product.get('tags', [])

        if dietary_pref:
            if 'sin picante' in dietary_pref and 'sin_picante' in product_tags:
                score += 25
            elif 'vegetariano' in dietary_pref and 'vegetariano' in product_tags:
                score += 25
            elif 'saludable' in dietary_pref and 'saludable' in product_tags:
                score += 25
            elif 'picante' in dietary_pref and 'picante' in product_tags:
                score += 25

        # 4. MOMENTO DEL DÍA (peso 15%)
        current_time = context.get('current_time', datetime.now().time())
        category_id = product.get('category_id')

        if isinstance(current_time, time):
            hour = current_time.hour
        else:
            hour = datetime.now().hour

        # Desayuno (6-11am)
        if 6 <= hour < 11:
            if category_id == 3:  # Bebidas (café, jugos)
                score += 15
        # Comida (12-4pm)
        elif 12 <= hour < 16:
            if category_id in [1, 2]:  # Entradas o platos fuertes
                score += 15
        # Cena (6-10pm)
        elif 18 <= hour < 22:
            if category_id == 2:  # Platos fuertes
                score += 15
        # Postre (después de comida/cena)
        if hour in [14, 15, 20, 21, 22]:
            if category_id == 4:  # Postres
                score += 10

        # 5. TIEMPO DE PREPARACIÓN (peso 10%)
        prep_time = product.get('preparation_time_minutes', 20)
        if context.get('quick_service'):
            if prep_time <= 10:
                score += 10
            elif prep_time <= 15:
                score += 5
            else:
                score -= 10

        # 6. HISTORIAL DEL USUARIO (peso extra)
        user_history = context.get('order_history', [])
        product_id = product.get('id')

        # Si ya lo ordenó antes, pequeño boost
        if product_id in user_history:
            score += 5

        # Evitar repetir si ordenó muy recientemente (últimos 2 pedidos)
        if user_history and product_id in user_history[-2:]:
            score -= 15

        # Limitar score entre 0 y 100
        return max(0, min(100, score))

    def get_top_recommendations(
        self,
        products: List[Dict],
        context: Dict,
        popularity_stats: Optional[Dict] = None,
        limit: int = 3
    ) -> List[Dict]:
        """
        Obtener top recomendaciones ordenadas por score

        Args:
            products: Lista de productos disponibles
            context: Contexto del usuario
            popularity_stats: Estadísticas de popularidad {product_id: {times_ordered, revenue}}
            limit: Número máximo de recomendaciones

        Returns:
            Lista de productos ordenados por score
        """
        scored_products = []

        for product in products:
            # Obtener datos de popularidad del producto
            pop_data = None
            if popularity_stats:
                product_id = product.get('id')
                pop_data = popularity_stats.get(product_id)

            # Calcular score
            score = self.calculate_product_score(product, context, pop_data)

            # Agregar a lista con score
            product_with_score = product.copy()
            product_with_score['recommendation_score'] = score
            scored_products.append(product_with_score)

        # Ordenar por score descendente
        scored_products.sort(key=lambda x: x['recommendation_score'], reverse=True)

        # Retornar top N
        top_products = scored_products[:limit]

        logger.info(
            f"Top {limit} recomendaciones generadas. "
            f"Scores: {[p['recommendation_score'] for p in top_products]}"
        )

        return top_products

    async def generate_personalized_pitch(
        self,
        product: Dict,
        context: Dict,
        score: float
    ) -> str:
        """
        Generar descripción personalizada usando LLM

        Args:
            product: Datos del producto
            context: Contexto del usuario
            score: Score de recomendación

        Returns:
            Pitch personalizado
        """
        try:
            # Construir prompt contextualizado
            user_prefs = []
            if context.get('dietary_preference'):
                user_prefs.append(f"prefiere {context['dietary_preference']}")
            if context.get('budget'):
                user_prefs.append(f"busca algo {context['budget']}")

            context_str = ", ".join(user_prefs) if user_prefs else "busca una buena opción"

            prompt = f"""Eres un mesero profesional recomendando un producto.

PRODUCTO:
- Nombre: {product['name']}
- Descripción: {product.get('description', '')}
- Precio: ${product.get('price', 0)}

CONTEXTO DEL CLIENTE:
- {context_str}
- Score de coincidencia: {score}/100

TAREA:
Genera UNA frase de recomendación (máximo 2 oraciones) que sea:
1. Natural y conversacional (como mesero experto)
2. Destaque por qué es buena opción para este cliente
3. Mencione precio de forma sutil
4. Sea persuasiva pero no exagerada

RESPONDE SOLO LA FRASE, sin comillas ni etiquetas."""

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Eres un mesero experto en recomendaciones."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=150
            )

            pitch = response.choices[0].message.content.strip()

            # Remover comillas si las agregó
            pitch = pitch.strip('"').strip("'")

            logger.debug(f"Pitch personalizado generado para {product['name']}")
            return pitch

        except Exception as e:
            logger.error(f"Error generando pitch personalizado: {e}")
            # Fallback: usar descripción del producto
            return f"Te recomiendo {product['name']}, ${product.get('price', 0)}. {product.get('description', '')[:100]}"

    async def generate_recommendation_response(
        self,
        products: List[Dict],
        context: Dict,
        popularity_stats: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Generar respuesta completa de recomendación

        Args:
            products: Lista de productos disponibles
            context: Contexto del usuario
            popularity_stats: Estadísticas de popularidad

        Returns:
            Dict con {recommendations, response_text, visual_data}
        """
        # 1. Filtrar productos según preferencias básicas
        filtered = self._apply_basic_filters(products, context)

        if not filtered:
            filtered = products  # Si no hay matches, usar todos

        # 2. Obtener top recomendaciones con scores
        top_recommendations = self.get_top_recommendations(
            filtered,
            context,
            popularity_stats,
            limit=3
        )

        # 3. Generar pitch personalizado para cada una
        recommendations_with_pitch = []
        for product in top_recommendations:
            pitch = await self.generate_personalized_pitch(
                product,
                context,
                product['recommendation_score']
            )
            product['personalized_pitch'] = pitch
            recommendations_with_pitch.append(product)

        # 4. Construir respuesta de voz
        response_text = self._build_voice_response(recommendations_with_pitch, context)

        # 5. Preparar datos visuales
        visual_data = {
            "type": "product_list",
            "category": "Recomendaciones Personalizadas",
            "products": [
                {
                    "id": p['id'],
                    "name": p['name'],
                    "description": p.get('description', ''),
                    "price": float(p.get('price', 0)),
                    "image_url": p.get('image_url'),
                    "preparation_time": p.get('preparation_time_minutes', 0),
                    "recommendation_score": p['recommendation_score'],
                    "pitch": p['personalized_pitch']
                }
                for p in recommendations_with_pitch
            ]
        }

        return {
            "recommendations": recommendations_with_pitch,
            "response_text": response_text,
            "visual_data": visual_data
        }

    def _apply_basic_filters(self, products: List[Dict], context: Dict) -> List[Dict]:
        """Aplicar filtros básicos antes del scoring"""
        filtered = products.copy()

        # Filtro dietético
        dietary_pref = context.get('dietary_preference', '').lower()
        if dietary_pref:
            if 'sin picante' in dietary_pref:
                filtered = [p for p in filtered if 'sin_picante' in p.get('tags', [])]
            elif 'vegetariano' in dietary_pref:
                filtered = [p for p in filtered if 'vegetariano' in p.get('tags', [])]
            elif 'saludable' in dietary_pref:
                filtered = [p for p in filtered if 'saludable' in p.get('tags', [])]

        # Filtro de categoría
        meal_type = context.get('meal_type', '').lower()
        if meal_type:
            if 'postre' in meal_type:
                filtered = [p for p in filtered if p.get('category_id') == 4]
            elif 'bebida' in meal_type:
                filtered = [p for p in filtered if p.get('category_id') == 3]
            elif 'entrada' in meal_type:
                filtered = [p for p in filtered if p.get('category_id') == 1]
            elif 'plato' in meal_type:
                filtered = [p for p in filtered if p.get('category_id') == 2]

        # Filtro de presupuesto
        budget = context.get('budget', '').lower()
        if budget:
            if 'económico' in budget:
                filtered = [p for p in filtered if float(p.get('price', 0)) <= 100]
            elif 'premium' in budget:
                filtered = [p for p in filtered if float(p.get('price', 0)) >= 150]

        return filtered

    def _build_voice_response(self, recommendations: List[Dict], context: Dict) -> str:
        """Construir respuesta de voz natural"""
        if not recommendations:
            return "Déjame mostrarte nuestro menú completo para que elijas lo que más te guste."

        if len(recommendations) == 1:
            pitch = recommendations[0]['personalized_pitch']
            return f"{pitch} ¿Te gustaría ordenarlo?"

        elif len(recommendations) == 2:
            return (
                f"{recommendations[0]['personalized_pitch']} "
                f"También tenemos {recommendations[1]['name']} por ${recommendations[1]['price']}. "
                "¿Cuál prefieres?"
            )

        else:  # 3 o más
            return (
                f"{recommendations[0]['personalized_pitch']} "
                f"También están {recommendations[1]['name']} y {recommendations[2]['name']}. "
                "¿Te cuento más de alguno?"
            )


# Instancia global (Singleton)
_recommendation_engine: Optional[RecommendationEngine] = None


def get_recommendation_engine() -> RecommendationEngine:
    """Obtener instancia global del RecommendationEngine"""
    global _recommendation_engine
    if _recommendation_engine is None:
        from ..core.config import settings
        _recommendation_engine = RecommendationEngine(
            groq_api_key=settings.GROQ_API_KEY,
            model=settings.GROQ_MODEL
        )
    return _recommendation_engine
