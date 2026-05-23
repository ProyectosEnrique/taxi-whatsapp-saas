# ============================================================
# ÁRBOL DE DECISIÓN - FSM v2.0
# ============================================================
# Lógica determinística para clasificar intenciones
# Sin necesidad de LLM para casos comunes
#
# OPTIMIZACIÓN v2.0:
# - Usa ProductMatcher.find_product_unified() en lugar de
#   _detect_mentioned_product() duplicado
# - Eliminado código redundante de aliases y búsqueda
# ============================================================

import re
import logging
from typing import Dict, List, Optional, Tuple, Any, TYPE_CHECKING
from dataclasses import dataclass
from enum import Enum

# Importación lazy para evitar circular imports
if TYPE_CHECKING:
    from .product_matcher import ProductMatcher

logger = logging.getLogger(__name__)


class Intent(Enum):
    """Intenciones posibles del cliente"""

    # Navegación
    GREETING = "greeting"
    VIEW_MENU = "view_menu"
    VIEW_CATEGORY = "view_category"
    VIEW_PRODUCT_DETAILS = "view_product_details"

    # Recomendaciones
    GET_RECOMMENDATION = "get_recommendation"
    ASK_OPINION = "ask_opinion"
    COMPLEX_RECOMMENDATION = "complex_recommendation"  # Requiere GPT-4o

    # Pedido
    ADD_TO_ORDER = "add_to_order"
    REMOVE_FROM_ORDER = "remove_from_order"
    MODIFY_ORDER = "modify_order"
    CONFIRM_ORDER = "confirm_order"
    SPECIAL_REQUEST = "special_request"  # Requiere GPT-4o

    # Respuestas a ofertas
    ACCEPT_SUGGESTION = "accept_suggestion"
    REJECT_SUGGESTION = "reject_suggestion"

    # Preguntas
    ASK_PRICE = "ask_price"
    ASK_INGREDIENTS = "ask_ingredients"
    ASK_SPICY = "ask_spicy"
    ASK_SIZE = "ask_size"

    # Cierre
    FINISH_ORDER = "finish_order"
    GOODBYE = "goodbye"

    # Objeciones y negociación (Requieren GPT-4o)
    HANDLE_OBJECTION = "handle_objection"  # "Es muy caro", "No me gusta"
    NEGOTIATE = "negotiate"                 # "¿Descuento?", "¿Promoción?"
    COMPLAINT = "complaint"                 # Quejas sobre servicio/comida

    # ============================================================
    # SOLICITUDES DE SERVICIO (más salsa, servilletas, limones, etc.)
    # ============================================================
    SERVICE_REQUEST = "service_request"     # "Tráeme más salsa", "Más limones"
    REQUEST_WAITER = "request_waiter"       # "Mesero!", "Llama al mesero"
    REQUEST_BILL = "request_bill"           # "La cuenta", "Quiero pagar"

    # Otros
    UNKNOWN = "unknown"
    NEED_CLARIFICATION = "need_clarification"


# Intenciones que requieren OpenAI (GPT-4o) en modo cascade
PREMIUM_INTENTS = {
    Intent.HANDLE_OBJECTION,
    Intent.NEGOTIATE,
    Intent.COMPLAINT,
    Intent.COMPLEX_RECOMMENDATION,
    Intent.SPECIAL_REQUEST
}


@dataclass
class IntentResult:
    """Resultado del árbol de decisión"""
    intent: Intent
    confidence: float
    entities: Dict[str, Any]
    requires_llm: bool = False
    reason: str = ""


class IntentDecisionTree:
    """
    Árbol de decisión para clasificar intenciones sin LLM.
    Usa reglas determinísticas para casos comunes.

    VERSION 2.0:
    - Usa ProductMatcher.find_product_unified() para detección de productos
    - Eliminado código duplicado de aliases y búsqueda de productos
    """

    def __init__(self, menu: List[Dict] = None):
        self.menu = menu or []
        self._product_matcher = None  # Lazy loading
        self._build_patterns()
        self._build_category_mapping()

    def _get_product_matcher(self):
        """Obtiene el ProductMatcher (lazy loading)"""
        if self._product_matcher is None:
            from .product_matcher import get_product_matcher
            self._product_matcher = get_product_matcher(menu=self.menu)
        return self._product_matcher

    def _build_patterns(self):
        """Construye patrones de reconocimiento"""

        # Patrones de saludo
        self.greeting_patterns = [
            r'\b(hola|buenas|hey|qué tal|buenos días|buenas tardes|buenas noches)\b'
        ]

        # Patrones de categoría
        self.category_patterns = {
            'hamburguesas': [r'\bhamburguesa[s]?\b', r'\bburger[s]?\b'],
            'tacos': [r'\btaco[s]?\b', r'\btaquito[s]?\b'],
            'bebidas': [r'\bbebida[s]?\b', r'\btomar\b', r'\brefresco[s]?\b', r'\bagua\b'],
            'postres': [r'\bpostre[s]?\b', r'\bdulce[s]?\b'],
            'entradas': [r'\bentrada[s]?\b', r'\bbotana[s]?\b'],
            'sopas': [r'\bsopa[s]?\b', r'\bcaldo[s]?\b'],
            'ensaladas': [r'\bensalada[s]?\b'],
            'complementos': [r'\bcomplemento[s]?\b', r'\bpapa[s]?\b', r'\bextra[s]?\b'],
            'platos_fuertes': [r'\bplato[s]? fuerte[s]?\b', r'\bplatillo[s]?\b']
        }

        # Patrones de recomendación
        self.recommendation_patterns = [
            r'\b(recomienda[s]?|recomendación|sugieres|sugiere|sugerencia)\b',
            r'\b(cuál es mejor|cuál es el mejor|cuál me recomiendas)\b',
            r'\b(qué me sugieres|qué me recomiendas)\b',
            r'\b(cuál es más rico|cuál está más rico)\b',
            r'\b(cuál pido|qué pido)\b',
            r'\b(ayúdame a elegir|no sé cuál)\b'
        ]

        # Patrones de navegación/ver categoría (tienen prioridad sobre add_order)
        self.browse_patterns = [
            r'\b(quiero ver|quisiera ver|me gustaría ver)\b',
            r'\b(ver las?|muéstrame|enséñame|muestrame|ensename)\b',
            r'\b(qué|que)\s+(hay de|tienen de)\b',
            r'\b(tienen|hay)\s+\w+\?*$',  # tiene hamburguesas? al final
        ]

        # Patrones para VER DETALLE de producto específico (sin agregar al carrito)
        # "muéstrame la hamburguesa clásica", "enséñame el taco de pastor"
        self.show_product_patterns = [
            r'\b(muéstrame|muestrame|enséñame|ensename|ver)\s+(el|la|los|las)\s+\w+',
            r'\b(muéstrame|muestrame|enséñame|ensename)\s+\w+',  # muéstrame hamburguesa
            r'\b(cómo es|como es|qué es|que es)\s+(el|la|los|las)?\s*\w+',
            r'\b(información|info|detalles?)\s+(de|del|de la)\s+\w+',
        ]

        # Patrones de agregar al pedido
        self.add_order_patterns = [
            r'\b(dame|quiero|ponme|tráeme|me das|me pones|te encargo|encargo|me traes)\b',
            r'\b(voy a querer|voy a pedir|me gustaría|quisiera)\b',
            r'\b(\d+)\s+(de\s+)?(taco|hamburguesa|agua|orden|coca|refresco|aguas?)\b',
            # Patrones con modificadores (sin X, extra Y, con Z)
            r'\b(hamburguesa|taco|orden|plato).*(sin|extra|con)\s+\w+',
            r'\b(sin|extra|con)\s+(cebolla|jitomate|tomate|queso|tocino|lechuga|crema|aguacate|cilantro|picante)\b',
            # Patrones con artículo + producto (una coca, un refresco, etc.)
            r'\b(un|una|uno|unos|unas)\s+\w+',
        ]

        # Patrones de QUITAR del pedido (remove_from_order)
        self.remove_order_patterns = [
            # Quitar/eliminar + producto específico
            r'\b(quita|quitame|quítame|quitale|quítale|elimina|borra|cancela|retira)\b.+\b(hamburguesa|coca|taco|agua|refresco|orden|papas|ensalada|postre)\b',
            # Quitar + artículo + producto
            r'\b(quita|quitame|quítame|elimina|borra|cancela|retira)\b.+\b(el|la|los|las|ese|esa|esos|esas)\b',
            # Ya no quiero + producto
            r'\b(ya no quiero|no quiero|no va|mejor no|quita)\b.+\b(hamburguesa|coca|taco|agua|refresco|orden)\b',
            # Cancela/quita + eso/ese/esa (referencia)
            r'\b(quita|cancela|elimina|borra)\s+(eso|ese|esa|esto|este|esta)\b',
            # Quita/elimina al inicio del mensaje (comando directo)
            r'^(quita|quitame|quítame|elimina|borra|cancela)\s+',
            # No + producto (negación simple)
            r'^no\s+(la|el|los|las)\s+(hamburguesa|coca|taco|agua)\b',
        ]

        # Patrones de aceptación
        self.accept_patterns = [
            r'\b(sí|si|claro|va|dale|órale|ándale|perfecto|está bien|ok|okay)\b',
            r'\b(me parece|suena bien|le entro|va que va)\b'
        ]

        # Patrones de rechazo
        self.reject_patterns = [
            r'\b(no|nel|nop|nope|para nada|ni modo)\b',
            r'\b(así está bien|solo eso|nada más|no gracias)\b',
            r'\b(sin nada más|está bien así)\b',
            r'\b(no quiero|prefiero no|mejor no)\b',
            r'\b(no me interesa|sin eso|no ese|no esa)\b',
            r'^tampoco$',  # "tampoco" como respuesta sola
            r'^paso$',     # "paso" como respuesta sola
            r'\btampoco\b',
            r'\bpaso\b'
        ]

        # Patrones de cierre
        self.finish_patterns = [
            r'\b(eso es todo|es todo|ya|nada más|solo eso)\b',
            r'\b(confirma|confirmar|cerrar|terminar)\b',
            r'\b(ya estuvo|ya quedó|listo)\b'
        ]

        # Patrones de despedida
        self.goodbye_patterns = [
            r'\b(adiós|adios|bye|hasta luego|nos vemos)\b',
            r'^gracias$',  # Solo "gracias" como mensaje completo
            r'\bgracias.{0,10}$'  # "gracias" al final del mensaje (hasta 10 chars después)
        ]

        # Patrones de preguntas sobre producto
        # Nota: Usamos [eé], [aá], etc. para aceptar con/sin acentos
        self.question_patterns = {
            'price': [r'\b(cu[aá]nto cuesta|cu[aá]nto es|cu[aá]nto vale|precio|vale)\b'],
            'ingredients': [r'\b(qu[eé] tiene|qu[eé] lleva|qu[eé] trae|ingredientes|de qu[eé] es|de que es)\b'],
            'spicy': [r'\b(picante|pica|picoso|enchilado|es picante|est[aá] picante)\b'],
            'size': [r'\b(tama[ñn]o|grande|chico|mediano|porci[oó]n|qu[eé] tan grande)\b']
        }

        # Patrones de ver menú
        self.menu_patterns = [
            r'\b(men[uú]|menu|carta|qu[eé] tienen|qu[eé] hay)\b',
            r'\b(qu[eé] me ofreces|qu[eé] opciones hay)\b'
        ]

        # ============================================================
        # PATRONES PREMIUM (requieren GPT-4o para mejor manejo)
        # ============================================================

        # Patrones de objeción (precio, gusto, etc.)
        # Nota: "mejor no", "prefiero no" están en reject_patterns, no aquí
        self.objection_patterns = [
            r'\b(muy caro|está caro|caro|costoso|mucho dinero)\b',
            r'\b(no me gusta|no me late|no me convence)\b',
            r'\b(no sé si|no estoy seguro|lo pienso)\b',
            r'\b(no creo que|no creo)\b',
            r'\b(es mucho|está muy|demasiado)\b'
        ]

        # Patrones de negociación (descuentos, promociones)
        self.negotiate_patterns = [
            r'\b(descuento|rebaja|promoción|promo|oferta)\b',
            r'\b(más barato|menos caro|precio especial)\b',
            r'\b(2x1|dos por uno|gratis)\b',
            r'\b(pueden hacer|me pueden|podrían)\b.*\b(precio|descuento)\b',
            r'\b(si compro|si pido)\b.*\b(descuento|gratis|promoción)\b'
        ]

        # Patrones de queja
        self.complaint_patterns = [
            r'\b(queja|quejarme|reclamo|reclamar)\b',
            r'\b(mal servicio|mala atención|tardó mucho)\b',
            r'\b(estaba frío|estaba fría|frío|fría)\b',
            r'\b(no me gustó|estuvo mal|horrible)\b',
            r'\b(devolución|devolver|reembolso)\b',
            r'\b(manager|gerente|encargado|supervisor)\b'
        ]

        # Patrones de recomendación compleja (múltiples restricciones)
        # NOTA: Estos patrones activan GPT-4o para mejor manejo de recomendaciones personalizadas
        self.complex_recommendation_patterns = [
            # Dietas y preferencias alimenticias (PRIORIDAD ALTA)
            r'\b(dieta|dietético|dietética|a dieta|está a dieta|estoy a dieta)\b',
            r'\b(saludable|sano|sana|nutritivo|nutritiva|fit|fitness)\b',
            r'\b(ligero|ligera|liviano|liviana|poco pesado|no pesado)\b',
            r'\b(bajo en calorías|pocas calorías|light|lite)\b',
            r'\b(bajo en grasa|sin grasa|poca grasa|desgrasado)\b',
            r'\b(bajo en carbohidratos|low carb|keto|cetogénico)\b',
            # Restricciones dietéticas
            r'\b(vegetariano|vegetariana|vegano|vegana)\b',
            r'\b(alergia|alérgico|alérgica|intolerante|intolerancia)\b',
            r'\b(diabético|diabética|diabetes|sin azúcar|sugar free)\b',
            r'\b(sin gluten|gluten free|celíaco|celíaca|celiaco|celiaca)\b',
            r'\b(sin lactosa|intolerancia a la lactosa|lactose free)\b',
            # Preferencias especiales
            r'\b(niño[s]?|pequeño[s]?)\b.*\b(adulto[s]?|grande[s]?)\b',
            r'\b(para \d+ personas|para todos|compartir)\b',
            r'\b(embarazada|embarazo|pregnancy)\b',
            # Combinaciones complejas
            r'\b(vegetariano|vegano)\b.*\b(y|pero|que)\b',
            r'\b(bajo en|sin grasa|light|ligero)\b.*\b(y|pero)\b'
        ]

        # Patrones de pedido especial
        self.special_request_patterns = [
            r'\b(sin|quitar|quita)\b.*\b(y|pero)\b.*\b(agregar|poner|con)\b',
            r'\b(cambiar|sustituir|reemplazar)\b.*\b(por)\b',
            r'\b(mitad|medio|media)\b.*\b(mitad|medio|media)\b',
            r'\b(extra|doble|triple)\b.*\b(extra|doble|sin)\b',
            r'\b(personalizar|a mi gusto|como yo quiera)\b'
        ]

        # ============================================================
        # PATRONES DE SOLICITUDES DE SERVICIO
        # ============================================================

        # Solicitudes de items adicionales (más salsa, servilletas, limones, etc.)
        self.service_request_patterns = [
            # Más + item
            r'\b(más|mas)\s+(salsa|salsas|limón|limones|limon|servilleta|servilletas|tortilla|tortillas|chile|chiles|sal|pimienta)\b',
            r'\b(tráeme|traeme|trae|dame|me traes|me das|necesito|ocupo)\s+(más\s+)?(salsa|salsas|limón|limones|limon|servilleta|servilletas|tortilla|tortillas|chile|chiles|sal|pimienta|agua|hielo|cubiertos|tenedor|cuchara|cuchillo)\b',
            # Faltan items
            r'\b(falta|faltan|no hay|se acabó|se acabaron|necesitamos)\s+(salsa|salsas|limón|limones|servilleta|servilletas|tortilla|tortillas|agua|hielo)\b',
            # Pedir items de servicio
            r'\b(puedes traer|podrías traer|me puedes dar|nos traes)\s+(más\s+)?(salsa|limón|limones|servilleta|servilletas|agua|hielo)\b',
            # Refill / recarga
            r'\b(otro|otra|otros|otras)\s+(vaso|copa|plato|orden)\s+de\s+(agua|refresco)\b',
            r'\b(rellenar|rellenarme|llenar|llenarme)\s+(el\s+)?(vaso|copa)\b',
            # Items de mesa genéricos
            r'\b(palillos|mondadientes|popote|popotes|pajilla)\b'
        ]

        # Llamar al mesero
        # NOTA: Patrones restrictivos para evitar falsos positivos
        # "oye, te encargo hamburguesas" NO debe activar mesero
        self.waiter_patterns = [
            r'\b(mesero|mesera|camarero|camarera|mozo|moza)\b',
            r'\b(llama|llamen|llamar)\s+(al\s+)?(mesero|mesera|camarero)\b',
            r'\b(necesito|ocupo)\s+(al\s+)?(mesero|mesera)\b',
            # Solo "oye/disculpe" cuando es mensaje corto o seguido de llamar a alguien
            r'^(disculpe|disculpa|oiga|oye)[,!]?\s*$',  # Mensaje solo con estas palabras
            r'\b(disculpe|disculpa|oiga|oye)[,!]?\s+(mesero|mesera|joven|señorita|señor|señora)\b',
            r'^(ayuda|auxilio)[!]?\s*$'  # Solo si es el mensaje completo
        ]

        # Pedir la cuenta
        self.bill_patterns = [
            r'\b(la cuenta|mi cuenta|nuestra cuenta)\b',
            r'\b(quiero|queremos)\s+pagar\b',
            r'\b(cobrar|cóbrame|cobranos|cóbrenos)\b',
            r'\b(cuánto (es|fue)|el total)\b',
            r'\b(ticket|recibo|factura)\b',
            r'\b(tarjeta|efectivo|pago)\b'
        ]

    def _build_category_mapping(self):
        """Construye mapeo de categorías del menú"""
        self.category_to_menu_name = {
            'hamburguesas': 'Hamburguesas',
            'hamburguesa': 'Hamburguesas',
            'tacos': 'Tacos',
            'taco': 'Tacos',
            'bebidas': 'Bebidas',
            'bebida': 'Bebidas',
            'refresco': 'Bebidas',
            'tomar': 'Bebidas',
            'postres': 'Postres',
            'postre': 'Postres',
            'entradas': 'Entradas',
            'entrada': 'Entradas',
            'botana': 'Entradas',
            'sopas': 'Sopas',
            'sopa': 'Sopas',
            'caldo': 'Sopas',
            'ensaladas': 'Ensaladas',
            'ensalada': 'Ensaladas',
            'complementos': 'Complementos',
            'complemento': 'Complementos',
            'papas': 'Complementos',
            'platos_fuertes': 'Platos Fuertes',
            'plato fuerte': 'Platos Fuertes'
        }

    def update_menu(self, menu: List[Dict]):
        """Actualiza el menú y sincroniza con ProductMatcher"""
        self.menu = menu
        # Actualizar ProductMatcher si existe
        if self._product_matcher is not None:
            self._product_matcher.update_menu(menu)

    def classify(self, text: str, context: 'StateContext' = None) -> IntentResult:
        """
        Clasifica la intención del texto usando el árbol de decisión.

        Args:
            text: Texto del cliente
            context: Contexto actual de la conversación

        Returns:
            IntentResult con la intención detectada
        """
        text_lower = text.lower().strip()
        entities = {}

        logger.info(f"[DECISION_TREE] Clasificando: '{text_lower}'")

        # ============================================================
        # NIVEL 0.5: SOLICITUDES DE SERVICIO (máxima prioridad)
        # Se detectan ANTES de cualquier flujo de venta
        # ============================================================

        # ¿Pide la cuenta?
        if self._matches_any(text_lower, self.bill_patterns):
            return IntentResult(
                intent=Intent.REQUEST_BILL,
                confidence=0.95,
                entities={'original_text': text},
                requires_llm=False,
                reason="Solicitud de cuenta detectada"
            )

        # ¿Llama al mesero?
        if self._matches_any(text_lower, self.waiter_patterns):
            return IntentResult(
                intent=Intent.REQUEST_WAITER,
                confidence=0.90,
                entities={'original_text': text},
                requires_llm=False,
                reason="Llamada a mesero detectada"
            )

        # ¿Solicita items de servicio? (más salsa, servilletas, limones, etc.)
        if self._matches_any(text_lower, self.service_request_patterns):
            # Extraer el item solicitado
            service_item = self._extract_service_item(text_lower)
            return IntentResult(
                intent=Intent.SERVICE_REQUEST,
                confidence=0.90,
                entities={
                    'original_text': text,
                    'service_item': service_item
                },
                requires_llm=False,
                reason=f"Solicitud de servicio: {service_item}"
            )

        # ============================================================
        # NIVEL 0: Intenciones Premium (requieren GPT-4o)
        # Se detectan primero para asegurar el mejor manejo
        # ============================================================

        # ¿Es una queja?
        if self._matches_any(text_lower, self.complaint_patterns):
            return IntentResult(
                intent=Intent.COMPLAINT,
                confidence=0.90,
                entities={'original_text': text},
                requires_llm=True,  # Requiere LLM para respuesta empática
                reason="Queja detectada - requiere GPT-4o"
            )

        # ¿Es una objeción?
        if self._matches_any(text_lower, self.objection_patterns):
            return IntentResult(
                intent=Intent.HANDLE_OBJECTION,
                confidence=0.85,
                entities={'original_text': text},
                requires_llm=True,
                reason="Objeción detectada - requiere GPT-4o"
            )

        # ¿Está negociando?
        if self._matches_any(text_lower, self.negotiate_patterns):
            return IntentResult(
                intent=Intent.NEGOTIATE,
                confidence=0.85,
                entities={'original_text': text},
                requires_llm=True,
                reason="Negociación detectada - requiere GPT-4o"
            )

        # ¿Recomendación compleja?
        if self._matches_any(text_lower, self.complex_recommendation_patterns):
            return IntentResult(
                intent=Intent.COMPLEX_RECOMMENDATION,
                confidence=0.85,
                entities={'original_text': text},
                requires_llm=True,
                reason="Recomendación compleja - requiere GPT-4o"
            )

        # ¿Pedido especial?
        if self._matches_any(text_lower, self.special_request_patterns):
            return IntentResult(
                intent=Intent.SPECIAL_REQUEST,
                confidence=0.85,
                entities={'original_text': text},
                requires_llm=True,
                reason="Pedido especial - requiere GPT-4o"
            )

        # ============================================================
        # NIVEL 1+: Intenciones regulares (no requieren GPT-4o)
        # ============================================================

        # Nivel 1: ¿Es un saludo?
        if self._matches_any(text_lower, self.greeting_patterns):
            return IntentResult(
                intent=Intent.GREETING,
                confidence=0.95,
                entities={},
                reason="Patrón de saludo detectado"
            )

        # Nivel 1.5: ¿Quiere QUITAR algo del pedido?
        # IMPORTANTE: Detectar ANTES de categoría, porque "quita la hamburguesa"
        # menciona categoría pero la intención es quitar, no ver
        if self._matches_any(text_lower, self.remove_order_patterns):
            # Detectar qué producto quiere quitar
            mentioned_product = self._detect_mentioned_product(text_lower, context)
            if mentioned_product:
                entities['product_to_remove'] = mentioned_product

            # También detectar categoría por si no encontramos producto específico
            detected_category = self._detect_category(text_lower)
            if detected_category:
                entities['category'] = detected_category

            return IntentResult(
                intent=Intent.REMOVE_FROM_ORDER,
                confidence=0.92,
                entities=entities,
                reason="Solicitud de eliminar producto del pedido"
            )

        # Nivel 2: PRIMERO verificar si es pregunta sobre producto específico
        # (qué lleva, cuánto cuesta, etc.) - tiene prioridad sobre ver categoría
        question_type = self._detect_question_type(text_lower)
        if question_type:
            entities['question_type'] = question_type
            mentioned_product = self._detect_mentioned_product(text_lower, context)
            if mentioned_product:
                entities['mentioned_product'] = mentioned_product

            intent_map = {
                'price': Intent.ASK_PRICE,
                'ingredients': Intent.ASK_INGREDIENTS,
                'spicy': Intent.ASK_SPICY,
                'size': Intent.ASK_SIZE
            }
            return IntentResult(
                intent=intent_map.get(question_type, Intent.VIEW_PRODUCT_DETAILS),
                confidence=0.90,
                entities=entities,
                reason=f"Pregunta sobre {question_type}"
            )

        # Nivel 2.5: ¿Es "muéstrame/enséñame [producto específico]"?
        # Esto tiene prioridad sobre VIEW_CATEGORY porque queremos mostrar el detalle
        # sin agregar al carrito
        if self._matches_any(text_lower, self.show_product_patterns):
            mentioned_product = self._detect_mentioned_product(text_lower, context)
            if mentioned_product:
                entities['mentioned_product'] = mentioned_product
                entities['show_only'] = True  # Flag para indicar que solo debe mostrar, no agregar
                logger.info(f"[DECISION_TREE] Detectado 'muéstrame producto': {mentioned_product}")
                return IntentResult(
                    intent=Intent.VIEW_PRODUCT_DETAILS,
                    confidence=0.92,
                    entities=entities,
                    reason=f"Mostrar detalle de producto: {mentioned_product}"
                )

        # Nivel 3: ¿Menciona una categoría?
        detected_category = self._detect_category(text_lower)
        if detected_category:
            entities['category'] = detected_category
            entities['menu_category'] = self.category_to_menu_name.get(detected_category, detected_category)

            # PRIORIDAD: ¿Es navegación? (quiero ver, muéstrame, etc.)
            if self._matches_any(text_lower, self.browse_patterns):
                return IntentResult(
                    intent=Intent.VIEW_CATEGORY,
                    confidence=0.95,
                    entities=entities,
                    reason=f"Navegación a categoría: {detected_category}"
                )
            
            # ¿Es pedido directo? (dame, ponme, quiero una, etc.)
            if self._matches_any(text_lower, self.add_order_patterns):
                # Detectar cantidad
                quantity = self._extract_quantity(text_lower)
                if quantity:
                    entities['quantity'] = quantity
                return IntentResult(
                    intent=Intent.ADD_TO_ORDER,
                    confidence=0.90,
                    entities=entities,
                    reason=f"Pedido de {detected_category}"
                )
            
            # Por defecto, ver categoría
            return IntentResult(
                intent=Intent.VIEW_CATEGORY,
                confidence=0.90,
                entities=entities,
                reason=f"Pregunta sobre categoría: {detected_category}"
            )

        # Nivel 3: ¿Pide recomendación?
        if self._matches_any(text_lower, self.recommendation_patterns):
            # Detectar si menciona un producto específico
            mentioned_product = self._detect_mentioned_product(text_lower, context)
            if mentioned_product:
                entities['mentioned_product'] = mentioned_product

            return IntentResult(
                intent=Intent.GET_RECOMMENDATION,
                confidence=0.90,
                entities=entities,
                reason="Solicitud de recomendación"
            )

        # Nivel 4: ¿Es respuesta a una oferta (sí/no)?
        if self._matches_any(text_lower, self.accept_patterns):
            return IntentResult(
                intent=Intent.ACCEPT_SUGGESTION,
                confidence=0.85,
                entities={},
                reason="Aceptación detectada"
            )

        # Nivel 4b: ¿Quiere terminar? (ANTES de rechazo, para que "no, es todo" sea FINISH)
        if self._matches_any(text_lower, self.finish_patterns):
            return IntentResult(
                intent=Intent.FINISH_ORDER,
                confidence=0.90,
                entities={},
                reason="Señal de cierre detectada"
            )

        # Nivel 5: ¿Rechaza sugerencia? (ANTES de goodbye para capturar "no gracias")
        if self._matches_any(text_lower, self.reject_patterns):
            return IntentResult(
                intent=Intent.REJECT_SUGGESTION,
                confidence=0.85,
                entities={},
                reason="Rechazo detectado"
            )

        if self._matches_any(text_lower, self.goodbye_patterns):
            return IntentResult(
                intent=Intent.GOODBYE,
                confidence=0.90,
                entities={},
                reason="Despedida detectada"
            )

        # Nivel 6: ¿Quiere ver el menú?
        if self._matches_any(text_lower, self.menu_patterns):
            return IntentResult(
                intent=Intent.VIEW_MENU,
                confidence=0.85,
                entities={},
                reason="Solicitud de menú"
            )

        # Nivel 8: ¿Quiere agregar algo al pedido?
        if self._matches_any(text_lower, self.add_order_patterns):
            quantity = self._extract_quantity(text_lower)
            if quantity:
                entities['quantity'] = quantity

            mentioned_product = self._detect_mentioned_product(text_lower, context)
            if mentioned_product:
                entities['mentioned_product'] = mentioned_product
                return IntentResult(
                    intent=Intent.ADD_TO_ORDER,
                    confidence=0.85,
                    entities=entities,
                    reason="Pedido detectado"
                )

        # Nivel 9: No se pudo clasificar localmente → requiere LLM
        logger.info("[DECISION_TREE] No se pudo clasificar localmente, requiere LLM")
        return IntentResult(
            intent=Intent.UNKNOWN,
            confidence=0.0,
            entities=entities,
            requires_llm=True,
            reason="Requiere análisis con LLM"
        )

    def _matches_any(self, text: str, patterns: List[str]) -> bool:
        """Verifica si el texto coincide con algún patrón"""
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False

    def _detect_category(self, text: str) -> Optional[str]:
        """Detecta si el texto menciona una categoría"""
        for category, patterns in self.category_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    return category
        return None

    def _detect_question_type(self, text: str) -> Optional[str]:
        """Detecta el tipo de pregunta"""
        for q_type, patterns in self.question_patterns.items():
            if self._matches_any(text, patterns):
                return q_type
        return None

    def _extract_quantity(self, text: str) -> Optional[int]:
        """Extrae cantidad del texto"""
        # Buscar números
        match = re.search(r'(\d+)', text)
        if match:
            return int(match.group(1))

        # Buscar palabras numéricas
        word_to_num = {
            'un': 1, 'uno': 1, 'una': 1,
            'dos': 2,
            'tres': 3,
            'cuatro': 4,
            'cinco': 5,
            'seis': 6,
            'siete': 7,
            'ocho': 8,
            'nueve': 9,
            'diez': 10
        }
        for word, num in word_to_num.items():
            if re.search(rf'\b{word}\b', text, re.IGNORECASE):
                return num

        return None

    def _extract_service_item(self, text: str) -> str:
        """Extrae el item de servicio solicitado del texto"""
        service_items = {
            'salsa': ['salsa', 'salsas', 'salsita'],
            'limón': ['limón', 'limones', 'limon'],
            'servilletas': ['servilleta', 'servilletas'],
            'tortillas': ['tortilla', 'tortillas'],
            'chile': ['chile', 'chiles'],
            'sal': ['sal'],
            'pimienta': ['pimienta'],
            'agua': ['agua', 'agüita'],
            'hielo': ['hielo', 'hielos'],
            'cubiertos': ['cubiertos', 'tenedor', 'cuchara', 'cuchillo'],
            'popotes': ['popote', 'popotes', 'pajilla', 'pajillas'],
            'palillos': ['palillos', 'mondadientes'],
            'platos': ['plato', 'platos'],
            'vasos': ['vaso', 'vasos', 'copa', 'copas']
        }

        text_lower = text.lower()
        for item_name, patterns in service_items.items():
            for pattern in patterns:
                if pattern in text_lower:
                    return item_name

        # Si no se detecta específicamente, devolver el texto original limpio
        return text.strip()

    def _detect_mentioned_product(self, text: str, context: 'StateContext' = None) -> Optional[str]:
        """
        Detecta si el usuario mencionó un producto específico.
        DELEGADO A ProductMatcher.find_product_unified() para evitar duplicación.

        Args:
            text: Texto del usuario
            context: Contexto de la conversación (opcional)

        Returns:
            Nombre del producto encontrado o None
        """
        # Obtener categoría y productos activos del contexto
        category_name = None
        category_products = None

        if context and context.is_category_active():
            category_name = context.active_category
            category_products = context.active_category_products

        # Delegar a ProductMatcher (que tiene cache y búsqueda avanzada)
        matcher = self._get_product_matcher()
        result = matcher.find_product_unified(
            user_input=text,
            category_name=category_name,
            category_products=category_products
        )

        if result:
            logger.info(f"[DECISION_TREE] Producto detectado via ProductMatcher: {result}")

        return result

    def get_products_by_category(self, category: str) -> List[Dict]:
        """
        Obtiene productos de una categoría.
        Usa el índice de ProductMatcher para mayor eficiencia.
        """
        # Usar ProductMatcher si está disponible (tiene índice por categoría)
        matcher = self._get_product_matcher()
        products = matcher.get_products_by_category(category)

        if products:
            logger.info(f"[DECISION_TREE] Productos en {category}: {len(products)} (via ProductMatcher)")
            return products

        # Fallback: búsqueda directa en menú
        menu_category = self.category_to_menu_name.get(category.lower(), category)
        products = [
            p for p in self.menu
            if p.get('category', {}).get('name', '') == menu_category
        ]

        logger.info(f"[DECISION_TREE] Productos en {menu_category}: {len(products)} (fallback)")
        return products

    def get_popular_product(self, products: List[Dict]) -> Optional[Dict]:
        """Obtiene el producto más popular de una lista"""
        # Primero buscar productos con tag 'popular'
        for p in products:
            if 'popular' in p.get('tags', []):
                return p

        # Si no hay popular, devolver el primero
        return products[0] if products else None

    def find_product_by_name(self, name: str) -> Optional[Dict]:
        """Busca un producto por nombre"""
        name_lower = name.lower()
        for p in self.menu:
            if p.get('name', '').lower() == name_lower:
                return p

        # Búsqueda parcial
        for p in self.menu:
            if name_lower in p.get('name', '').lower():
                return p

        return None
