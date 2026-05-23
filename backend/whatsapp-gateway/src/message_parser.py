"""
================================================================================
MESSAGE PARSER
================================================================================
Parsea mensajes entrantes para extraer información estructurada.
Detecta códigos de mesa, intenciones, productos mencionados, etc.
================================================================================
"""

from typing import Dict, Any, Optional, List
import re
import logging

logger = logging.getLogger(__name__)


class MessageParser:
    """
    Parser de mensajes de WhatsApp.

    Detecta:
    - Códigos de mesa (QR): MESA-5-R001
    - Intenciones: ordenar, ver menú, promociones
    - Productos mencionados: "3 tacos de pastor"
    - Confirmaciones: sí, confirmar, ok
    - Cancelaciones: no, cancelar
    """

    # Patrones de código de mesa
    TABLE_PATTERNS = [
        r"MESA-(\d+)-([A-Z0-9]+)",           # MESA-5-R001
        r"mesa[:\s]*(\d+)",                   # mesa: 5, mesa 5
        r"table[:\s]*(\d+)",                  # table: 5
        r"M(\d+)R([A-Z0-9]+)",               # M5R001 (compacto)
    ]

    # Intenciones
    INTENTS = {
        "menu": ["menu", "menú", "carta", "ver menu", "que tienen", "qué tienen"],
        "order": ["ordenar", "pedir", "quiero", "dame", "ponme", "me das"],
        "promotions": ["promocion", "promo", "oferta", "descuento", "2x1"],
        "cart": ["carrito", "mi pedido", "que llevo", "qué llevo"],
        "confirm": ["si", "sí", "confirmar", "confirmo", "ok", "dale", "va"],
        "cancel": ["no", "cancelar", "cancela", "quitar", "eliminar"],
        "help": ["ayuda", "help", "como", "cómo"],
        "greeting": ["hola", "buenas", "buen dia", "buenos días"],
        "thanks": ["gracias", "thank", "adios", "adiós", "bye"],
        "bill": ["cuenta", "pagar", "cobrar", "total"],
        "waiter": ["mesero", "mesera", "ayuda personal"],
    }

    # Patrones de productos con cantidad
    PRODUCT_PATTERNS = [
        r"(\d+)\s+(?:de\s+)?(.+)",           # "3 de pastor", "2 cocas"
        r"(?:una?|uno)\s+(.+)",               # "una hamburguesa"
        r"(?:dame|quiero|ponme)\s+(.+)",      # "dame tacos"
    ]

    def parse(
        self,
        message: str,
        session: Any = None
    ) -> Dict[str, Any]:
        """
        Parsear un mensaje y extraer información estructurada.

        Args:
            message: Mensaje del cliente
            session: Sesión actual (opcional, para contexto)

        Returns:
            Dict con información extraída
        """
        result = {
            "original": message,
            "normalized": message.lower().strip(),
            "is_table_code": False,
            "table_id": None,
            "restaurant_id": None,
            "intent": None,
            "products": [],
            "is_confirmation": False,
            "is_cancellation": False,
        }

        normalized = result["normalized"]

        # 1. Detectar código de mesa
        table_info = self._parse_table_code(message)
        if table_info:
            result.update(table_info)
            result["is_table_code"] = True
            logger.info(f"[Parser] Código de mesa detectado: {table_info}")
            return result

        # 2. Detectar intención
        intent = self._detect_intent(normalized)
        result["intent"] = intent

        # 3. Detectar confirmación/cancelación
        if intent == "confirm":
            result["is_confirmation"] = True
        elif intent == "cancel":
            result["is_cancellation"] = True

        # 4. Extraer productos mencionados
        if intent in ["order", None]:
            products = self._extract_products(normalized)
            result["products"] = products

        # 5. Detectar número de respuesta a botones
        button_response = self._detect_button_response(normalized)
        if button_response:
            result["button_response"] = button_response

        logger.debug(f"[Parser] Resultado: {result}")

        return result

    def _parse_table_code(self, message: str) -> Optional[Dict[str, Any]]:
        """Extraer código de mesa del mensaje"""
        message_upper = message.upper().strip()

        # Patrón principal: MESA-5-R001
        match = re.match(r"MESA-(\d+)-([A-Z0-9]+)", message_upper)
        if match:
            return {
                "table_id": int(match.group(1)),
                "restaurant_id": match.group(2)
            }

        # Patrón compacto: M5R001
        match = re.match(r"M(\d+)R([A-Z0-9]+)", message_upper)
        if match:
            return {
                "table_id": int(match.group(1)),
                "restaurant_id": match.group(2)
            }

        # Solo número de mesa
        match = re.match(r"(?:MESA|TABLE)[:\s]*(\d+)", message_upper)
        if match:
            return {
                "table_id": int(match.group(1)),
                "restaurant_id": None
            }

        return None

    def _detect_intent(self, message: str) -> Optional[str]:
        """Detectar la intención del mensaje"""
        for intent, keywords in self.INTENTS.items():
            for keyword in keywords:
                if keyword in message:
                    return intent
        return None

    def _extract_products(self, message: str) -> List[Dict[str, Any]]:
        """Extraer productos mencionados con sus cantidades"""
        products = []

        # Patrón: número + producto
        pattern = r"(\d+)\s+(?:de\s+)?([a-záéíóúñü\s]+?)(?:\s+y\s+|,|$)"
        matches = re.findall(pattern, message, re.IGNORECASE)

        for quantity, product_name in matches:
            product_name = product_name.strip()
            if len(product_name) > 2:  # Evitar matches muy cortos
                products.append({
                    "quantity": int(quantity),
                    "name": product_name,
                    "raw": f"{quantity} {product_name}"
                })

        # Patrón: una/un + producto
        pattern = r"(?:una?|uno)\s+([a-záéíóúñü\s]+?)(?:\s+y\s+|,|$)"
        matches = re.findall(pattern, message, re.IGNORECASE)

        for product_name in matches:
            product_name = product_name.strip()
            if len(product_name) > 2:
                products.append({
                    "quantity": 1,
                    "name": product_name,
                    "raw": f"1 {product_name}"
                })

        return products

    def _detect_button_response(self, message: str) -> Optional[int]:
        """Detectar si es respuesta a botón (1, 2, 3, etc.)"""
        message = message.strip()

        # Solo número
        if message.isdigit() and 1 <= int(message) <= 10:
            return int(message)

        # Número con emoji
        emoji_numbers = {
            "1️⃣": 1, "2️⃣": 2, "3️⃣": 3, "4️⃣": 4, "5️⃣": 5,
            "6️⃣": 6, "7️⃣": 7, "8️⃣": 8, "9️⃣": 9, "🔟": 10
        }
        for emoji, num in emoji_numbers.items():
            if emoji in message:
                return num

        return None

    def extract_modifiers(self, message: str) -> List[str]:
        """Extraer modificadores de productos (sin cebolla, extra queso, etc.)"""
        modifiers = []

        # Patrones de modificadores
        patterns = [
            r"sin\s+([a-záéíóúñü]+)",       # sin cebolla
            r"extra\s+([a-záéíóúñü]+)",     # extra queso
            r"con\s+([a-záéíóúñü]+)",       # con papas
            r"sin\s+mucho?\s+([a-záéíóúñü]+)",  # sin mucha salsa
        ]

        for pattern in patterns:
            matches = re.findall(pattern, message.lower())
            modifiers.extend(matches)

        return modifiers

    def extract_delivery_address(self, message: str) -> Optional[str]:
        """Extraer dirección de entrega del mensaje"""
        # Patrones de dirección
        patterns = [
            r"(?:en(?:viar)?|entregar?|llevar)\s+(?:a|en)\s+(.+)",
            r"dirección[:\s]+(.+)",
            r"calle\s+(.+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, message.lower())
            if match:
                return match.group(1).strip()

        return None
