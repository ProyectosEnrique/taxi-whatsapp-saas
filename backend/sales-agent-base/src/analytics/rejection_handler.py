"""
================================================================================
SMART REJECTION HANDLER - FASE 2
================================================================================
Maneja rechazos de upselling de manera inteligente:
- Detecta el tipo de rechazo (precio, no quiere más, etc.)
- Ofrece alternativas contextuales
- Aprende de los patrones de rechazo
- Limita intentos para no ser molesto
================================================================================
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class RejectionType(Enum):
    """Tipos de rechazo detectados"""
    PRICE = "price"  # "Muy caro", "No tengo tanto"
    QUANTITY = "quantity"  # "Es mucho", "No quiero más"
    PREFERENCE = "preference"  # "No me gusta", "Prefiero otra cosa"
    TIMING = "timing"  # "Después", "Ahorita no"
    DIET = "diet"  # "No puedo comer eso", "Soy alérgico"
    GENERAL = "general"  # "No gracias", rechazo sin razón


@dataclass
class RejectionContext:
    """Contexto de un rechazo para aprender"""
    rejection_type: RejectionType
    product_category: str
    product_price: float
    timestamp: datetime
    session_id: str
    upsell_attempt: int  # Número de intento (1, 2, 3...)


@dataclass
class SessionUpsellState:
    """Estado de upselling por sesión"""
    attempts: int = 0
    max_attempts: int = 3
    rejected_categories: List[str] = field(default_factory=list)
    rejected_price_ceiling: Optional[float] = None
    last_rejection_type: Optional[RejectionType] = None
    cooldown_until: Optional[datetime] = None


class SmartRejectionHandler:
    """
    Maneja rechazos de upselling de manera inteligente
    para maximizar conversiones sin ser molesto
    """

    def __init__(self):
        # Estado de upselling por sesión
        self._session_states: Dict[str, SessionUpsellState] = {}

        # Patrones de detección de rechazo por tipo
        self.rejection_patterns = {
            RejectionType.PRICE: [
                'caro', 'costoso', 'mucho', 'no tengo', 'no traigo',
                'muy caro', 'está caro', 'precio', 'dinero', 'economico',
                'barato', 'más barato', 'algo más barato'
            ],
            RejectionType.QUANTITY: [
                'suficiente', 'es mucho', 'ya es mucho', 'bastante',
                'no más', 'ya no', 'estoy lleno', 'mucha comida',
                'es demasiado', 'ya tengo'
            ],
            RejectionType.PREFERENCE: [
                'no me gusta', 'no me late', 'prefiero', 'otra cosa',
                'no quiero eso', 'no se me antoja', 'paso'
            ],
            RejectionType.TIMING: [
                'después', 'ahorita no', 'luego', 'al rato',
                'más tarde', 'para llevar', 'next'
            ],
            RejectionType.DIET: [
                'alérgico', 'alergia', 'no puedo', 'dieta',
                'vegetariano', 'vegano', 'intolerante', 'no como'
            ],
            RejectionType.GENERAL: [
                'no gracias', 'no', 'nada más', 'está bien así',
                'solo eso', 'ya', 'así está bien', 'nada'
            ]
        }

        # Respuestas alternativas por tipo de rechazo
        self.alternative_responses = {
            RejectionType.PRICE: [
                "¡Entendido! ¿Qué te parece {alternative}? Está a ${price} y es de los favoritos.",
                "Claro, tenemos {alternative} que está muy bien de precio, solo ${price}.",
                "Sin problema. Te recomiendo {alternative}, mejor precio y muy bueno."
            ],
            RejectionType.QUANTITY: [
                "¡Perfecto! Lo que llevas está muy bien. ¿Algo de tomar?",
                "Ok, sin agregar más. ¿Una bebida para acompañar?",
                "Entendido. ¿Necesitas algo más o procedemos?"
            ],
            RejectionType.PREFERENCE: [
                "¡Sale! ¿Y qué te parece {alternative}? Es diferente pero muy bueno.",
                "Claro, hay de todo. ¿Prefieres algo de {category}?",
                "Entendido. Déjame recomendarte {alternative}, es otro estilo."
            ],
            RejectionType.TIMING: [
                "¡Claro! Lo dejamos pendiente. ¿Algo más por ahora?",
                "Perfecto, sin prisa. ¿Necesitas algo más ahorita?",
                "Ok, cuando gustes me avisas. ¿Todo bien con lo que llevas?"
            ],
            RejectionType.DIET: [
                "¡Entendido! Tenemos opciones sin {ingredient}. ¿Te cuento?",
                "Sin problema, hay alternativas. ¿Qué puedes comer?",
                "Claro, tu salud primero. ¿Alguna restricción más que deba saber?"
            ],
            RejectionType.GENERAL: [
                "¡Perfecto! ¿Algo más o cerramos la orden?",
                "Ok, está muy bien. ¿Necesitas algo más?",
                "¡Listo! ¿Procedemos con lo que llevas?"
            ]
        }

        logger.info("SmartRejectionHandler inicializado")

    def get_session_state(self, session_id: str) -> SessionUpsellState:
        """Obtener o crear estado de sesión"""
        if session_id not in self._session_states:
            self._session_states[session_id] = SessionUpsellState()
        return self._session_states[session_id]

    def detect_rejection_type(self, user_response: str) -> RejectionType:
        """
        Detectar el tipo de rechazo basado en la respuesta del usuario

        Args:
            user_response: Texto de respuesta del usuario

        Returns:
            Tipo de rechazo detectado
        """
        response_lower = user_response.lower()

        # Buscar patrones en orden de especificidad
        for rejection_type in [
            RejectionType.PRICE,
            RejectionType.DIET,
            RejectionType.QUANTITY,
            RejectionType.PREFERENCE,
            RejectionType.TIMING,
            RejectionType.GENERAL
        ]:
            patterns = self.rejection_patterns[rejection_type]
            for pattern in patterns:
                if pattern in response_lower:
                    return rejection_type

        return RejectionType.GENERAL

    def should_attempt_upsell(self, session_id: str) -> Tuple[bool, str]:
        """
        Determinar si se debe intentar upselling

        Returns:
            Tupla (puede_intentar, razón)
        """
        state = self.get_session_state(session_id)

        # Verificar cooldown
        if state.cooldown_until:
            if datetime.now() < state.cooldown_until:
                return False, "cooldown_active"

        # Verificar máximo de intentos
        if state.attempts >= state.max_attempts:
            return False, "max_attempts_reached"

        return True, "ok"

    def record_attempt(self, session_id: str) -> int:
        """
        Registrar un intento de upselling

        Returns:
            Número de intento actual
        """
        state = self.get_session_state(session_id)
        state.attempts += 1
        return state.attempts

    def handle_rejection(
        self,
        session_id: str,
        user_response: str,
        rejected_product: Dict,
        menu: List[Dict]
    ) -> Dict:
        """
        Manejar un rechazo y generar respuesta alternativa

        Args:
            session_id: ID de la sesión
            user_response: Respuesta del usuario que rechazó
            rejected_product: Producto que fue rechazado
            menu: Menú completo para buscar alternativas

        Returns:
            Dict con:
            - should_retry: bool
            - response: str
            - alternative_product: Optional[Dict]
        """
        state = self.get_session_state(session_id)
        rejection_type = self.detect_rejection_type(user_response)

        state.last_rejection_type = rejection_type
        rejected_category = rejected_product.get('category', {}).get('name', '').lower()
        rejected_price = float(rejected_product.get('price', 0))

        # Actualizar estado basado en tipo de rechazo
        if rejection_type == RejectionType.PRICE:
            state.rejected_price_ceiling = rejected_price * 0.7  # Buscar 30% más barato

        if rejection_type == RejectionType.PREFERENCE:
            if rejected_category and rejected_category not in state.rejected_categories:
                state.rejected_categories.append(rejected_category)

        # Buscar alternativa si es apropiado
        alternative = None
        should_retry = False

        if rejection_type in [RejectionType.PRICE, RejectionType.PREFERENCE]:
            if state.attempts < state.max_attempts:
                alternative = self._find_alternative(
                    rejected_product=rejected_product,
                    rejection_type=rejection_type,
                    state=state,
                    menu=menu
                )
                should_retry = alternative is not None

        # Generar respuesta
        response = self._generate_response(
            rejection_type=rejection_type,
            alternative=alternative,
            rejected_category=rejected_category
        )

        # Si no hay más intentos o es rechazo definitivo, activar cooldown
        if not should_retry or rejection_type in [RejectionType.QUANTITY, RejectionType.GENERAL]:
            from datetime import timedelta
            state.cooldown_until = datetime.now() + timedelta(minutes=5)

        logger.info(
            f"[REJECTION] Session {session_id}: tipo={rejection_type.value}, "
            f"retry={should_retry}, attempts={state.attempts}"
        )

        return {
            'should_retry': should_retry,
            'response': response,
            'alternative_product': alternative,
            'rejection_type': rejection_type.value
        }

    def _find_alternative(
        self,
        rejected_product: Dict,
        rejection_type: RejectionType,
        state: SessionUpsellState,
        menu: List[Dict]
    ) -> Optional[Dict]:
        """Buscar producto alternativo según el tipo de rechazo"""

        rejected_id = rejected_product.get('id')
        rejected_price = float(rejected_product.get('price', 0))
        rejected_category = rejected_product.get('category', {}).get('name', '').lower()

        candidates = []

        for product in menu:
            product_id = product.get('id')
            product_price = float(product.get('price', 0))
            product_category = product.get('category', {}).get('name', '').lower()

            # No sugerir el mismo producto
            if product_id == rejected_id:
                continue

            # No sugerir categorías ya rechazadas
            if product_category in state.rejected_categories:
                continue

            if rejection_type == RejectionType.PRICE:
                # Buscar más barato
                if state.rejected_price_ceiling:
                    if product_price <= state.rejected_price_ceiling:
                        candidates.append((product, rejected_price - product_price))
                elif product_price < rejected_price * 0.8:
                    candidates.append((product, rejected_price - product_price))

            elif rejection_type == RejectionType.PREFERENCE:
                # Buscar otra categoría
                if product_category != rejected_category:
                    candidates.append((product, 0))

        if not candidates:
            return None

        # Ordenar: por precio más barato (price), o aleatorio (preference)
        if rejection_type == RejectionType.PRICE:
            candidates.sort(key=lambda x: x[1], reverse=True)

        return candidates[0][0] if candidates else None

    def _generate_response(
        self,
        rejection_type: RejectionType,
        alternative: Optional[Dict],
        rejected_category: str
    ) -> str:
        """Generar respuesta contextual"""

        responses = self.alternative_responses.get(rejection_type, self.alternative_responses[RejectionType.GENERAL])

        if alternative:
            alt_name = alternative.get('name', 'este otro')
            alt_price = float(alternative.get('price', 0))
            alt_category = alternative.get('category', {}).get('name', 'otra categoría')

            # Elegir template con placeholder para alternativa
            for template in responses:
                if '{alternative}' in template:
                    return template.format(
                        alternative=alt_name,
                        price=int(alt_price),
                        category=alt_category
                    )

        # Respuesta sin alternativa
        import random
        template = random.choice(responses)
        return template.format(
            alternative='algo diferente',
            price=100,
            category=rejected_category,
            ingredient='eso'
        )

    def reset_session(self, session_id: str):
        """Resetear estado de una sesión (nueva orden)"""
        if session_id in self._session_states:
            del self._session_states[session_id]

    def get_upsell_strategy(self, session_id: str) -> str:
        """
        Obtener estrategia de upselling recomendada para la sesión

        Returns:
            'aggressive', 'moderate', 'cautious', o 'stop'
        """
        state = self.get_session_state(session_id)

        if state.attempts >= state.max_attempts:
            return 'stop'

        if state.cooldown_until and datetime.now() < state.cooldown_until:
            return 'stop'

        if state.last_rejection_type in [RejectionType.QUANTITY, RejectionType.DIET]:
            return 'cautious'

        if state.last_rejection_type == RejectionType.PRICE:
            return 'moderate'  # Ofrecer alternativas económicas

        if state.attempts == 0:
            return 'aggressive'

        return 'moderate'


# Instancia global
_rejection_handler: Optional[SmartRejectionHandler] = None


def get_rejection_handler() -> SmartRejectionHandler:
    """Obtener instancia global del SmartRejectionHandler"""
    global _rejection_handler
    if _rejection_handler is None:
        _rejection_handler = SmartRejectionHandler()
    return _rejection_handler
