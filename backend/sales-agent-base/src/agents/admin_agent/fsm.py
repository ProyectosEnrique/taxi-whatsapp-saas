"""
================================================================================
ADMIN FSM - Maquina de Estados para Admin Agent
================================================================================
Maneja el flujo de conversacion del asistente administrativo.
Incluye estados para confirmacion de acciones criticas.
================================================================================
"""

import logging
import re
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any

logger = logging.getLogger(__name__)


# ==============================================================================
# ESTADOS
# ==============================================================================

class AdminState(Enum):
    """Estados del Admin FSM"""
    IDLE = "idle"                           # Esperando comando
    PROCESSING = "processing"               # Procesando solicitud
    WAITING_CONFIRMATION = "waiting_confirmation"  # Esperando confirmacion
    EXECUTING = "executing"                 # Ejecutando accion
    REPORTING = "reporting"                 # Mostrando reporte
    ERROR = "error"                         # Estado de error


class AdminIntent(Enum):
    """Intenciones del administrador"""
    # Consultas
    QUERY_SALES = "query_sales"
    QUERY_ORDERS = "query_orders"
    QUERY_TOP_PRODUCTS = "query_top_products"
    QUERY_HOURLY = "query_hourly"
    QUERY_TICKET = "query_ticket"
    GENERATE_REPORT = "generate_report"

    # Promociones
    CREATE_PROMOTION = "create_promotion"
    LIST_PROMOTIONS = "list_promotions"
    TOGGLE_PROMOTION = "toggle_promotion"

    # Productos
    TOGGLE_PRODUCT = "toggle_product"
    UPDATE_PRICE = "update_price"
    QUERY_UNAVAILABLE = "query_unavailable"

    # Control
    CONFIRM = "confirm"
    CANCEL = "cancel"
    HELP = "help"
    GREETING = "greeting"
    UNKNOWN = "unknown"


# ==============================================================================
# CLASIFICADOR DE INTENTS
# ==============================================================================

@dataclass
class IntentMatch:
    """Resultado de clasificacion de intent"""
    intent: AdminIntent
    confidence: float
    entities: Dict = field(default_factory=dict)
    tool_name: Optional[str] = None
    tool_params: Dict = field(default_factory=dict)


class AdminIntentClassifier:
    """Clasificador de intenciones para comandos administrativos"""

    def __init__(self):
        # Patrones para cada intent
        self.patterns = {
            AdminIntent.QUERY_SALES: [
                r'(?:cu[aá]nto|qu[eé])\s*(?:se\s*)?(?:vendi[oó]|vendimos|ventas)',
                r'ventas\s*(?:de|del)?\s*(?:hoy|ayer|semana|mes)',
                r'reporte\s*(?:de\s*)?ventas',
                r'ingresos\s*(?:de|del)?\s*(?:d[ií]a|hoy|ayer)',
                r'(?:total|dinero)\s*(?:de|del)?\s*(?:d[ií]a|hoy)',
            ],
            AdminIntent.QUERY_ORDERS: [
                r'(?:cu[aá]ntas?|qu[eé])\s*(?:[oó]rdenes|pedidos)',
                r'(?:n[uú]mero|cantidad)\s*(?:de\s*)?(?:[oó]rdenes|pedidos)',
                r'(?:[oó]rdenes|pedidos)\s*(?:de|del)?\s*(?:hoy|ayer|semana)',
                r'(?:pendientes|completad[oa]s)',
            ],
            AdminIntent.QUERY_TOP_PRODUCTS: [
                r'm[aá]s\s*vendid[oa]s?',
                r'(?:top|mejor(?:es)?)\s*(?:productos?|platillos?)',
                r'(?:qu[eé]|cu[aá]les?)\s*(?:se\s*)?vende(?:n)?\s*m[aá]s',
                r'productos?\s*(?:m[aá]s\s*)?popular(?:es)?',
            ],
            AdminIntent.QUERY_HOURLY: [
                r'(?:ventas?\s*)?(?:por\s*)?hora',
                r'horas?\s*(?:pico|fuerte)',
                r'(?:a\s*qu[eé]\s*hora|cu[aá]ndo)\s*(?:se\s*)?vende(?:mos)?\s*m[aá]s',
                r'horario\s*(?:de\s*)?ventas',
            ],
            AdminIntent.QUERY_TICKET: [
                r'ticket\s*(?:promedio|medio)',
                r'promedio\s*(?:de\s*)?(?:venta|compra|orden)',
                r'(?:cu[aá]nto|qu[eé])\s*(?:gasta|compra)\s*(?:en\s*)?promedio',
            ],
            AdminIntent.GENERATE_REPORT: [
                r'(?:dame|genera|hazme|env[ií]a)\s*(?:el\s*)?reporte',
                r'reporte\s*(?:del\s*)?d[ií]a',
                r'resumen\s*(?:del\s*)?(?:d[ií]a|diario)',
            ],
            AdminIntent.CREATE_PROMOTION: [
                r'(?:crea|crear|nueva|agregar?)\s*(?:una?\s*)?promoci[oó]n',
                r'(?:crea|crear|nueva|agregar?)\s*(?:un?\s*)?(?:descuento|oferta|2x1)',
                r'(?:poner?|activar?)\s*(?:un?\s*)?(?:descuento|promoci[oó]n)',
                r'(?:hacer|poner)\s*2\s*(?:x|por)\s*1',
            ],
            AdminIntent.LIST_PROMOTIONS: [
                r'(?:qu[eé]|cu[aá]les?)\s*promoci[oó]n(?:es)?',
                r'(?:lista(?:r)?|ver|muestra)\s*promoci[oó]n(?:es)?',
                r'promoci[oó]n(?:es)?\s*activ[ao]s?',
            ],
            AdminIntent.TOGGLE_PROMOTION: [
                r'(?:desactivar?|activar?|quitar?)\s*(?:la\s*)?promoci[oó]n',
                r'(?:apagar?|prender?|encender?)\s*(?:la\s*)?promoci[oó]n',
            ],
            AdminIntent.TOGGLE_PRODUCT: [
                r'(?:desactivar?|activar?)\s*(?:el\s*)?(?:producto|platillo)',
                r'(?:marcar?|poner?)\s*(?:como\s*)?(?:agotado|disponible)',
                r'(?:ya\s*)?no\s*(?:hay|tenemos)\s*\w+',
                r'(?:se\s*)?acab[oó]\s*(?:el|la)?\s*\w+',
            ],
            AdminIntent.UPDATE_PRICE: [
                r'(?:cambiar?|actualizar?|modificar?)\s*(?:el\s*)?precio',
                r'(?:subir?|bajar?)\s*(?:el\s*)?precio',
                r'(?:poner?|dejar?)\s*(?:el\s*)?\w+\s*(?:a|en)\s*\$?\d+',
            ],
            AdminIntent.QUERY_UNAVAILABLE: [
                r'(?:qu[eé]|cu[aá]les?)\s*(?:productos?|platillos?)?\s*(?:est[aá]n?\s*)?agotad[oa]s?',
                r'(?:productos?|platillos?)\s*(?:no\s*)?disponibles?',
                r'(?:falta|faltan)\s*(?:productos?|platillos?)',
            ],
            AdminIntent.CONFIRM: [
                r'^(?:s[ií]|ok|confirmo?|dale|adelante|correcto|exacto|afirmativo)$',
                r'^(?:s[ií]\s*(?:por\s*favor|please))$',
                r'^(?:eso\s*es|as[ií]\s*es)$',
            ],
            AdminIntent.CANCEL: [
                r'^(?:no|cancelar?|olvid[aá]lo|dejalo|nada)$',
                r'^(?:no\s*(?:gracias|quiero))$',
                r'^(?:mejor\s*no|ya\s*no)$',
            ],
            AdminIntent.HELP: [
                r'(?:ayuda|help)',
                r'(?:qu[eé]\s*)?(?:puedo|puedes)\s*(?:hacer|decir)',
                r'(?:c[oó]mo\s*)?(?:funciona|uso)',
                r'(?:comandos?|opciones?)\s*disponibles?',
            ],
            AdminIntent.GREETING: [
                r'^(?:hola|buenas?|hey|buenos?\s*d[ií]as?|buenas?\s*(?:tardes?|noches?))$',
                r'^(?:qu[eé]\s*tal|c[oó]mo\s*est[aá]s?)$',
            ],
        }

        # Mapeo de intent a tool
        self.intent_to_tool = {
            AdminIntent.QUERY_SALES: "get_sales_report",
            AdminIntent.QUERY_ORDERS: "get_orders_count",
            AdminIntent.QUERY_TOP_PRODUCTS: "get_top_products",
            AdminIntent.QUERY_HOURLY: "get_hourly_sales",
            AdminIntent.QUERY_TICKET: "get_average_ticket",
            AdminIntent.GENERATE_REPORT: "generate_daily_report",
            AdminIntent.CREATE_PROMOTION: "create_promotion",
            AdminIntent.LIST_PROMOTIONS: "list_promotions",
            AdminIntent.TOGGLE_PROMOTION: "toggle_promotion",
            AdminIntent.TOGGLE_PRODUCT: "toggle_product",
            AdminIntent.UPDATE_PRICE: "update_product_price",
            AdminIntent.QUERY_UNAVAILABLE: "get_unavailable_products",
        }

    def classify(self, text: str) -> IntentMatch:
        """
        Clasificar un texto en un intent.

        Args:
            text: Texto del usuario

        Returns:
            IntentMatch con el intent detectado
        """
        text_lower = text.lower().strip()

        best_match = None
        best_confidence = 0.0

        for intent, patterns in self.patterns.items():
            for pattern in patterns:
                if re.search(pattern, text_lower, re.IGNORECASE):
                    # Calcular confianza basada en longitud del match
                    match = re.search(pattern, text_lower, re.IGNORECASE)
                    match_ratio = len(match.group()) / len(text_lower) if match else 0
                    confidence = 0.6 + (0.4 * match_ratio)

                    if confidence > best_confidence:
                        best_confidence = confidence
                        entities = self._extract_entities(text_lower, intent)
                        tool_name = self.intent_to_tool.get(intent)
                        tool_params = self._build_tool_params(intent, entities, text_lower)

                        best_match = IntentMatch(
                            intent=intent,
                            confidence=confidence,
                            entities=entities,
                            tool_name=tool_name,
                            tool_params=tool_params
                        )
                    break  # Solo necesitamos un match por intent

        if best_match:
            return best_match

        # No match encontrado
        return IntentMatch(
            intent=AdminIntent.UNKNOWN,
            confidence=0.0,
            entities={}
        )

    def _extract_entities(self, text: str, intent: AdminIntent) -> Dict:
        """Extraer entidades del texto"""
        entities = {}

        # Periodo de tiempo
        period_patterns = {
            "today": r'\b(?:hoy|d[ií]a)\b',
            "yesterday": r'\b(?:ayer)\b',
            "week": r'\b(?:semana|semanal)\b',
            "month": r'\b(?:mes|mensual)\b',
        }

        for period, pattern in period_patterns.items():
            if re.search(pattern, text):
                entities["period"] = period
                break

        # Cantidad/numero
        number_match = re.search(r'\b(\d+)\b', text)
        if number_match:
            entities["number"] = int(number_match.group(1))

        # Precio
        price_match = re.search(r'\$?\s*(\d+(?:\.\d{2})?)\s*(?:pesos)?', text)
        if price_match:
            entities["price"] = float(price_match.group(1))

        # Nombre de producto (despues de ciertos verbos)
        product_patterns = [
            r'(?:desactivar?|activar?|agotado|disponible)\s+(?:el\s+|la\s+)?(\w+(?:\s+\w+)?)',
            r'(?:precio\s+(?:de|del))\s+(\w+(?:\s+\w+)?)',
            r'(?:se\s*acab[oó]|no\s*hay)\s+(?:el\s+|la\s+)?(\w+(?:\s+\w+)?)',
        ]

        for pattern in product_patterns:
            match = re.search(pattern, text)
            if match:
                entities["product_name"] = match.group(1).strip()
                break

        # Tipo de promocion
        if "2x1" in text or "2 x 1" in text or "dos por uno" in text:
            entities["promotion_type"] = "2x1"
        elif re.search(r'(\d+)\s*%', text):
            entities["promotion_type"] = "percentage"
            entities["discount_value"] = int(re.search(r'(\d+)\s*%', text).group(1))
        elif re.search(r'\$\s*(\d+)', text):
            entities["promotion_type"] = "fixed"
            entities["discount_value"] = float(re.search(r'\$\s*(\d+)', text).group(1))

        # Nombre de promocion
        promo_match = re.search(r'promoci[oó]n\s+(?:de\s+)?["\']?(\w+(?:\s+\w+)*)["\']?', text)
        if promo_match:
            entities["promotion_name"] = promo_match.group(1)

        return entities

    def _build_tool_params(
        self,
        intent: AdminIntent,
        entities: Dict,
        text: str
    ) -> Dict:
        """Construir parametros para la herramienta"""
        params = {}

        # Parametros segun intent
        if intent in [AdminIntent.QUERY_SALES, AdminIntent.QUERY_ORDERS,
                      AdminIntent.QUERY_TICKET, AdminIntent.QUERY_TOP_PRODUCTS]:
            params["period"] = entities.get("period", "today")

        if intent == AdminIntent.QUERY_TOP_PRODUCTS:
            params["limit"] = entities.get("number", 5)

        if intent == AdminIntent.TOGGLE_PRODUCT:
            params["product_name"] = entities.get("product_name", "")
            # Determinar si activar o desactivar
            if any(word in text for word in ["desactivar", "agotado", "acabó", "no hay"]):
                params["available"] = False
            else:
                params["available"] = True

        if intent == AdminIntent.UPDATE_PRICE:
            params["product_name"] = entities.get("product_name", "")
            params["new_price"] = entities.get("price", 0)

        if intent == AdminIntent.CREATE_PROMOTION:
            params["promotion_type"] = entities.get("promotion_type", "percentage")
            if "discount_value" in entities:
                params["discount_value"] = entities["discount_value"]

        if intent == AdminIntent.TOGGLE_PROMOTION:
            params["promotion_name"] = entities.get("promotion_name", "")
            if any(word in text for word in ["desactivar", "quitar", "apagar"]):
                params["active"] = False
            else:
                params["active"] = True

        return params


# ==============================================================================
# ADMIN FSM
# ==============================================================================

class AdminFSM:
    """
    Maquina de estados para el asistente administrativo.

    Maneja:
    - Clasificacion de comandos
    - Confirmacion de acciones criticas
    - Flujo de conversacion
    """

    def __init__(self):
        self.classifier = AdminIntentClassifier()
        self.state = AdminState.IDLE

        # Acciones que requieren confirmacion
        self.requires_confirmation = {
            "create_promotion",
            "toggle_promotion",
            "toggle_product",
            "update_product_price"
        }

        # Accion pendiente de confirmacion
        self.pending_action: Optional[Dict] = None

        logger.info("[AdminFSM] Inicializado")

    def process(self, text: str, session_context: Dict = None) -> Tuple[AdminState, IntentMatch, Optional[str]]:
        """
        Procesar entrada del usuario.

        Args:
            text: Texto del usuario
            session_context: Contexto de la sesion

        Returns:
            Tuple de (nuevo_estado, intent_match, mensaje_confirmacion)
        """
        session_context = session_context or {}

        # Si estamos esperando confirmacion
        if self.state == AdminState.WAITING_CONFIRMATION:
            return self._handle_confirmation(text)

        # Clasificar intent
        intent_match = self.classifier.classify(text)

        logger.info(f"[AdminFSM] Intent: {intent_match.intent.value} (conf: {intent_match.confidence:.2f})")

        # Manejar casos especiales
        if intent_match.intent == AdminIntent.GREETING:
            self.state = AdminState.IDLE
            return (self.state, intent_match, None)

        if intent_match.intent == AdminIntent.HELP:
            self.state = AdminState.IDLE
            return (self.state, intent_match, None)

        if intent_match.intent == AdminIntent.UNKNOWN:
            self.state = AdminState.IDLE
            return (self.state, intent_match, None)

        # Verificar si requiere confirmacion
        if intent_match.tool_name in self.requires_confirmation:
            self.pending_action = {
                "tool_name": intent_match.tool_name,
                "tool_params": intent_match.tool_params,
                "intent": intent_match.intent
            }
            self.state = AdminState.WAITING_CONFIRMATION

            confirmation_msg = self._generate_confirmation_message(intent_match)
            return (self.state, intent_match, confirmation_msg)

        # Accion directa (consultas)
        self.state = AdminState.EXECUTING
        return (self.state, intent_match, None)

    def _handle_confirmation(self, text: str) -> Tuple[AdminState, IntentMatch, Optional[str]]:
        """Manejar respuesta a solicitud de confirmacion"""
        intent_match = self.classifier.classify(text)

        if intent_match.intent == AdminIntent.CONFIRM:
            # Usuario confirmo
            if self.pending_action:
                # Crear IntentMatch con la accion pendiente
                confirmed_match = IntentMatch(
                    intent=self.pending_action["intent"],
                    confidence=1.0,
                    tool_name=self.pending_action["tool_name"],
                    tool_params=self.pending_action["tool_params"]
                )
                self.pending_action = None
                self.state = AdminState.EXECUTING
                return (self.state, confirmed_match, None)

        elif intent_match.intent == AdminIntent.CANCEL:
            # Usuario cancelo
            self.pending_action = None
            self.state = AdminState.IDLE
            cancel_match = IntentMatch(
                intent=AdminIntent.CANCEL,
                confidence=1.0
            )
            return (self.state, cancel_match, "Operacion cancelada.")

        else:
            # Respuesta no clara, pedir confirmacion de nuevo
            confirmation_msg = "Por favor, confirma con 'si' o 'no'. " + self._generate_confirmation_message(
                IntentMatch(
                    intent=self.pending_action["intent"],
                    confidence=0.0,
                    tool_name=self.pending_action["tool_name"],
                    tool_params=self.pending_action["tool_params"]
                )
            )
            return (AdminState.WAITING_CONFIRMATION, intent_match, confirmation_msg)

    def _generate_confirmation_message(self, intent_match: IntentMatch) -> str:
        """Generar mensaje de confirmacion para una accion"""
        tool_name = intent_match.tool_name
        params = intent_match.tool_params

        if tool_name == "create_promotion":
            promo_type = params.get("promotion_type", "")
            discount = params.get("discount_value", "")
            return f"¿Confirmas crear una promocion tipo {promo_type}" + \
                   (f" con {discount}% de descuento" if discount else "") + "?"

        if tool_name == "toggle_promotion":
            name = params.get("promotion_name", "")
            active = params.get("active", True)
            action = "activar" if active else "desactivar"
            return f"¿Confirmas {action} la promocion '{name}'?"

        if tool_name == "toggle_product":
            name = params.get("product_name", "")
            available = params.get("available", True)
            status = "disponible" if available else "agotado"
            return f"¿Confirmas marcar '{name}' como {status}?"

        if tool_name == "update_product_price":
            name = params.get("product_name", "")
            price = params.get("new_price", 0)
            return f"¿Confirmas cambiar el precio de '{name}' a ${price}?"

        return "¿Confirmas esta accion?"

    def reset(self):
        """Resetear estado del FSM"""
        self.state = AdminState.IDLE
        self.pending_action = None

    def get_help_text(self) -> str:
        """Obtener texto de ayuda con comandos disponibles"""
        return """
Puedo ayudarte con:

**CONSULTAS:**
- "¿Cuanto vendimos hoy/ayer/esta semana?"
- "¿Cual es el producto mas vendido?"
- "¿Cuantas ordenes hay pendientes?"
- "¿A que hora vendemos mas?"
- "Dame el reporte del dia"

**PROMOCIONES:**
- "Crea promocion 2x1 en hamburguesas"
- "Activa descuento 20% en pizzas"
- "¿Que promociones tenemos activas?"
- "Desactiva la promocion de tacos"

**MENU:**
- "Desactiva la hamburguesa clasica" (marcar agotado)
- "Activa las papas" (marcar disponible)
- "Cambia el precio de tacos a $45"
- "¿Que productos estan agotados?"
"""
