"""
================================================================================
INTENT DETECTOR
================================================================================
Detecta intenciones del usuario y determina el mejor flujo (WhatsApp vs Web)
================================================================================
"""

import re
from typing import Optional, Tuple, List
from dataclasses import dataclass
import logging

from .hybrid_session import ConversationIntent, DerivarReason

logger = logging.getLogger(__name__)


# ==============================================================================
# PATTERNS
# ==============================================================================

@dataclass
class IntentPattern:
    """Patrón para detectar intención"""
    intent: ConversationIntent
    keywords: List[str]
    phrases: List[str]
    priority: int  # Mayor = más específico


# Patrones ordenados por prioridad (más específico primero)
INTENT_PATTERNS = [
    # PEDIDO RÁPIDO - Usuario sabe qué quiere
    IntentPattern(
        intent=ConversationIntent.QUICK_ORDER,
        keywords=["dame", "quiero", "pido", "ordeno", "me das", "trae"],
        phrases=[
            r"(?:dame|quiero|pido)\s+\d+",  # "dame 2", "quiero 3"
            r"lo\s+de\s+siempre",  # "lo de siempre"
            r"(?:el|la)\s+mismo",  # "el mismo", "la misma"
        ],
        priority=10
    ),

    # PEDIDO REPETIDO - Cliente regular
    IntentPattern(
        intent=ConversationIntent.REPEAT_ORDER,
        keywords=["siempre", "mismo", "misma", "usual", "habitual"],
        phrases=[
            r"lo\s+(?:de\s+)?siempre",
            r"(?:el|la)\s+(?:de\s+)?siempre",
            r"mi\s+(?:pedido\s+)?(?:usual|habitual)"
        ],
        priority=9
    ),

    # BROWSING - Usuario quiere explorar
    IntentPattern(
        intent=ConversationIntent.BROWSING,
        keywords=[
            "qué tienen", "qué hay", "opciones", "variedades",
            "tipos", "cuáles", "mostrar", "ver todos"
        ],
        phrases=[
            r"qu[eé]\s+(?:tienen|hay|venden|ofrecen)",
            r"cu[aá]les\s+(?:son|tienen)",
            r"qu[ée]\s+(?:tipo|clase)s?\s+de",
            r"mostrar(?:me)?\s+(?:todo|opciones|el men[uú])",
            r"ver\s+(?:todo|opciones|el men[uú]|fotos)"
        ],
        priority=8
    ),

    # UNDECIDED - Usuario indeciso
    IntentPattern(
        intent=ConversationIntent.UNDECIDED,
        keywords=[
            "no sé", "nose", "indeciso", "recomienda", "sugieres",
            "ayuda", "qué me das", "sorpresa"
        ],
        phrases=[
            r"no\s+s[eé]\s+qu[eé]",
            r"qu[eé]\s+(?:me\s+)?(?:recomiendas|sugieres|aconsejas)",
            r"(?:ayuda|ayúdame)\s+a\s+(?:elegir|escoger|decidir)",
            r"qu[eé]\s+(?:es|ser[íi]a)\s+bueno"
        ],
        priority=7
    ),

    # PROMOCIONES
    IntentPattern(
        intent=ConversationIntent.PROMOTION_INQUIRY,
        keywords=[
            "promoción", "promo", "oferta", "descuento", "especial",
            "2x1", "gratis", "barato"
        ],
        phrases=[
            r"(?:hay|tienen)\s+(?:alguna?\s+)?(?:promo|oferta|descuento)",
            r"qu[eé]\s+(?:promociones|ofertas|especiales)",
            r"algo\s+(?:en\s+)?(?:promo|oferta|descuento)"
        ],
        priority=6
    ),

    # CONSULTA - Pregunta específica
    IntentPattern(
        intent=ConversationIntent.CONSULTATION,
        keywords=[
            "sin gluten", "vegetariano", "vegano", "alérgico",
            "ingredientes", "calorías", "picante", "sin chile"
        ],
        phrases=[
            r"(?:es|son)\s+(?:sin\s+gluten|vegetarian[oa]|vegan[oa])",
            r"tiene\s+(?:gluten|lácteos|nueces|mariscos)",
            r"qu[eé]\s+(?:lleva|tiene|contiene|trae)",
            r"sin\s+(?:chile|picante|cebolla|ajo)"
        ],
        priority=5
    ),

    # PEDIDO COMPLEJO - Múltiples items o personalización
    IntentPattern(
        intent=ConversationIntent.COMPLEX_ORDER,
        keywords=["y también", "además", "agregar", "extra", "sin", "con"],
        phrases=[
            r"(?:y|,)\s+(?:tambi[eé]n|adem[aá]s)",
            r"(?:sin|con)\s+\w+\s+(?:y|,)",  # "sin chile y cebolla"
            r"\d+\s+\w+\s+(?:y|,)\s+\d+\s+\w+"  # "2 tacos y 3 hamburguesas"
        ],
        priority=4
    ),
]


# ==============================================================================
# DETECTOR
# ==============================================================================

class IntentDetector:
    """
    Detecta intenciones del usuario basado en su mensaje.

    Usa patrones de keywords y regex para identificar qué quiere hacer
    el usuario y si necesita derivarse a web.
    """

    def __init__(self):
        self.patterns = sorted(INTENT_PATTERNS, key=lambda x: x.priority, reverse=True)

    def detect_intent(
        self,
        message: str,
        conversation_history: List[str] = None
    ) -> Tuple[ConversationIntent, float]:
        """
        Detectar intención del mensaje.

        Args:
            message: Mensaje del usuario
            conversation_history: Historial de mensajes previos

        Returns:
            (intent, confidence)
        """
        message_lower = message.lower().strip()

        # Buscar coincidencias en patrones
        best_match = None
        best_confidence = 0.0

        for pattern in self.patterns:
            confidence = self._match_pattern(message_lower, pattern)

            if confidence > best_confidence:
                best_confidence = confidence
                best_match = pattern.intent

        # Si no hay match claro, usar browsing como default
        if not best_match or best_confidence < 0.3:
            best_match = ConversationIntent.BROWSING
            best_confidence = 0.5

        logger.info(f"[IntentDetector] '{message[:30]}...' → {best_match} ({best_confidence:.2f})")

        return best_match, best_confidence

    def _match_pattern(self, message: str, pattern: IntentPattern) -> float:
        """
        Calcular confianza de match con un patrón.

        Returns:
            Confidence score (0.0 - 1.0)
        """
        score = 0.0
        matches = 0
        total_checks = 0

        # Revisar keywords
        for keyword in pattern.keywords:
            total_checks += 1
            if keyword.lower() in message:
                matches += 1
                score += 0.3

        # Revisar frases (regex)
        for phrase_pattern in pattern.phrases:
            total_checks += 1
            if re.search(phrase_pattern, message, re.IGNORECASE):
                matches += 1
                score += 0.5

        # Normalizar score
        if total_checks > 0:
            confidence = min(score / total_checks, 1.0)
        else:
            confidence = 0.0

        # Boost por prioridad
        confidence *= (pattern.priority / 10)

        return confidence

    def should_redirect_to_web(
        self,
        intent: ConversationIntent,
        message_count: int,
        cart_size: int,
        confidence: float,
        user_message: str = ""
    ) -> Tuple[bool, Optional[DerivarReason]]:
        """
        Determinar si se debe redirigir a web.

        ESTRATEGIA NUEVA (menos agresiva):
        - Solo derivar cuando el usuario PIDE explícitamente ver menú con fotos
        - O cuando el carrito es muy grande (5+ items)
        - O cuando la conversación es MUY larga sin progreso (8+ mensajes)
        - Casos como "qué me recomiendas" o "qué hamburguesas tienen"
          se manejan CONVERSACIONALMENTE (no se deriva)

        Args:
            intent: Intención detectada
            message_count: Cantidad de mensajes en la conversación
            cart_size: Cantidad de items en el carrito
            confidence: Confianza en la detección
            user_message: Mensaje original del usuario (para detección explícita)

        Returns:
            (should_redirect, reason)
        """
        message_lower = user_message.lower() if user_message else ""

        # Casos que NUNCA van a web (deben resolverse en WhatsApp)
        if intent in [
            ConversationIntent.QUICK_ORDER,
            ConversationIntent.REPEAT_ORDER,
            ConversationIntent.PROMOTION_INQUIRY,
            ConversationIntent.CONSULTATION
        ]:
            return False, None

        # NIVEL 1: Usuario pide EXPLÍCITAMENTE ver menú WEB (muy restrictivo)
        # Solo enviar link cuando pida explícitamente ver "el menú web" o "la página"
        # NO derivar por solo decir "qué tienen", "muéstrame", etc.
        explicit_web_menu_keywords = [
            "ver el menú web", "ver la página", "ver el menú en la página",
            "mostrar la página web", "abrir el sitio", "ver el sitio web",
            "quiero ver el menú completo en línea", "dame el link del menú",
            "envíame el menú", "mándame el menú", "link del menú"
        ]

        if any(keyword in message_lower for keyword in explicit_web_menu_keywords):
            return True, DerivarReason.USER_REQUESTED

        # Verificación adicional: Solo si dice "menú" + ("web" o "página" o "link" o "envía")
        if "menú" in message_lower or "menu" in message_lower:
            if any(word in message_lower for word in ["web", "página", "pagina", "link", "enlace", "envía", "envia", "manda", "sitio"]):
                return True, DerivarReason.USER_REQUESTED

        # NIVEL 2: Carrito EXTREMADAMENTE grande (aumentado de 5 a 10)
        # El mesero virtual puede manejar pedidos grandes conversacionalmente
        if cart_size >= 10:
            return True, DerivarReason.COMPLEX_ORDER

        # NIVEL 3: Conversación EXTREMADAMENTE larga sin progreso (aumentado de 8 a 15)
        # Dar mucha más oportunidad a la conversación antes de derivar
        if message_count >= 15 and cart_size == 0:
            if intent in [ConversationIntent.BROWSING, ConversationIntent.UNDECIDED]:
                return True, DerivarReason.CONVERSATION_TOO_LONG

        # NIVEL 4: Customización EXTREMADAMENTE compleja (aumentado de 3 a 6)
        # El mesero virtual puede manejar customizaciones complejas
        if intent == ConversationIntent.COMPLEX_ORDER:
            customization_count = message_lower.count("sin ") + message_lower.count("con ")
            if customization_count >= 6 and message_count > 5:
                return True, DerivarReason.CUSTOMIZATION_NEEDED

        # DEFAULT: NO derivar - manejar conversacionalmente
        # Esto incluye casos como:
        # - "qué me recomiendas?" → mesero responde con recomendaciones
        # - "qué hamburguesas tienen?" → mesero lista hamburguesas
        # - "no sé qué pedir" → mesero ayuda a decidir
        return False, None

    def extract_product_mentions(self, message: str) -> List[str]:
        """
        Extraer menciones de productos del mensaje.

        Útil para quick orders: "2 tacos al pastor y una coca"
        """
        # Productos comunes
        products = []

        # Patrones simples (puedes expandir con ML/NER)
        patterns = {
            r"\d+\s+(?:taco|tacos)(?:\s+(?:de|al)\s+(\w+))?": "tacos",
            r"\d+\s+(?:hamburguesa|hamburguesas)(?:\s+(\w+))?": "hamburguesas",
            r"\d+\s+(?:refresco|refrescos|coca|pepsi)": "bebidas",
            r"\d+\s+(?:orden|ordenes)\s+de\s+(\w+)": "orden",
        }

        for pattern, product_type in patterns.items():
            matches = re.finditer(pattern, message.lower())
            for match in matches:
                products.append({
                    "type": product_type,
                    "text": match.group(0),
                    "variant": match.group(1) if match.lastindex else None
                })

        return products


# ==============================================================================
# EXAMPLE USAGE
# ==============================================================================

if __name__ == "__main__":
    detector = IntentDetector()

    # Test cases
    test_messages = [
        "Hola, qué tienen de tacos?",
        "Dame 3 tacos al pastor",
        "No sé qué pedir, qué me recomiendas?",
        "Tienen promociones hoy?",
        "Lo de siempre por favor",
        "Quiero ver el menú completo con fotos",
        "2 hamburguesas sin cebolla y 3 refrescos",
        "Es vegetariano el pozole?",
    ]

    print("=" * 80)
    print("INTENT DETECTION TESTS")
    print("=" * 80)

    for msg in test_messages:
        intent, confidence = detector.detect_intent(msg)
        should_redirect, reason = detector.should_redirect_to_web(
            intent=intent,
            message_count=1,
            cart_size=0,
            confidence=confidence
        )

        print(f"\nMensaje: {msg}")
        print(f"  → Intent: {intent} ({confidence:.2f})")
        print(f"  → Redirect: {should_redirect} ({reason})")

        # Extraer productos mencionados
        products = detector.extract_product_mentions(msg)
        if products:
            print(f"  → Productos: {products}")
