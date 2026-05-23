"""
================================================================================
VOICE RESTAURANT ASSISTANT - INTENT RECOGNIZER
================================================================================
Reconocimiento de intenciones y extracción de entidades del usuario
================================================================================
"""

import re
import json
from typing import Dict, List, Optional, Any
from enum import Enum
import logging
from groq import Groq

logger = logging.getLogger(__name__)


class Intent(str, Enum):
    """Intenciones soportadas"""
    CREATE_ORDER = "create_order"
    ADD_ITEM = "add_item"
    REMOVE_ITEM = "remove_item"
    VIEW_MENU = "view_menu"
    VIEW_CATEGORY = "view_category"
    SHOW_PRODUCT_DETAILS = "show_product_details"
    VIEW_FULL_MENU = "view_full_menu"
    VIEW_ORDER = "view_order"
    REQUEST_BILL = "request_bill"
    CALL_WAITER = "call_waiter"
    MODIFY_ORDER = "modify_order"
    CANCEL_ORDER = "cancel_order"
    GET_RECOMMENDATION = "get_recommendation"  # NUEVO
    VIEW_PROMOTIONS = "view_promotions"        # NUEVO
    GENERAL_QUESTION = "general_question"
    GREETING = "greeting"
    GOODBYE = "goodbye"
    UNKNOWN = "unknown"


class IntentRecognizer:
    """
    Reconocedor de intenciones OPTIMIZADO para velocidad

    Usa clasificador local rápido para casos comunes + LLM solo cuando necesario
    """

    def __init__(self, groq_api_key: str, model: str = "llama-3.1-8b-instant"):
        self.client = Groq(api_key=groq_api_key)
        self.model = model
        self._warmed_up = False

        # ================================================================
        # CLASIFICADOR LOCAL RÁPIDO - Evita llamar a LLM en casos obvios
        # ================================================================
        self.quick_patterns = {
            Intent.GREETING: ['hola', 'buenas', 'buenos días', 'buenas tardes', 'buenas noches', 'qué tal', 'hey'],
            Intent.GOODBYE: ['adiós', 'adios', 'hasta luego', 'nos vemos', 'chao', 'bye', 'gracias por todo'],
            Intent.REQUEST_BILL: ['cuenta', 'pagar', 'cobrar', 'cuánto es', 'cuanto es', 'total'],
            Intent.CALL_WAITER: ['mesero', 'mesera', 'waiter', 'ayuda', 'disculpe', 'por favor venga'],
            Intent.VIEW_ORDER: ['mi pedido', 'mi orden', 'qué pedí', 'que pedí', 'qué llevo', 'que llevo'],
            Intent.VIEW_FULL_MENU: ['menú completo', 'menu completo', 'todo el menú', 'todo el menu', 'ver todo'],
            Intent.VIEW_PROMOTIONS: ['promoción', 'promocion', 'oferta', 'descuento', 'especial del día'],
        }

        # Patrones para GET_RECOMMENDATION (embudo de ventas)
        self.recommendation_patterns = {
            'meal_type': {
                'entrada': ['ligero', 'botana', 'botanear', 'entrada', 'antojo', 'snack', 'picar'],
                'plato_fuerte': ['llenador', 'fuerte', 'plato', 'comida', 'comer', 'hambre', 'completo'],
                'bebida': ['tomar', 'beber', 'bebida', 'fresco', 'sed', 'refresco', 'agua'],
                'postre': ['postre', 'dulce', 'algo dulce', 'endulzar'],
            },
            'dietary_preference': {
                'vegetariano': ['vegano', 'vegana', 'vegetariano', 'vegetariana', 'sin carne', 'verduras', 'plantas'],
                'sin_picante': ['sin picante', 'no picante', 'suave', 'nada picante', 'poco picante', 'no pica'],
                'carne': ['carne', 'res', 'asada', 'bistec'],
                'pollo': ['pollo', 'pechuga', 'gallina'],
                'cerdo': ['cerdo', 'pastor', 'carnitas', 'puerco'],
                'mariscos': ['mariscos', 'pescado', 'camarón', 'camarones', 'atún'],
            }
        }

        # Patrones para categorías
        self.category_patterns = {
            'hamburguesa': ['hamburguesa', 'hamburguesas', 'burger', 'burgers'],
            'tacos': ['taco', 'tacos', 'taquito', 'taquitos'],
            'bebidas': ['bebida', 'bebidas', 'refresco', 'refrescos', 'agua', 'jugos'],
            'postres': ['postre', 'postres', 'dulce', 'dulces'],
            'entradas': ['entrada', 'entradas', 'botana', 'botanas', 'aperitivo'],
        }

        # System prompt COMPACTO pero claro
        self.system_prompt = """Clasificador de intenciones para restaurante. Responde SOLO JSON.

INTENCIONES:
- create_order/add_item: Pide producto+cantidad ("quiero 2 tacos", "dame una coca", "te encargo", "ponme", "tráeme", "me das")
- view_category: Pregunta GENERAL por categoría SIN producto específico ("qué hamburguesas tienen", "muéstrame las bebidas")
- show_product_details: Pregunta por UN producto ESPECÍFICO ("qué tiene la hamburguesa tocino", "ingredientes del pozole", "qué lleva la pizza margarita")
  IMPORTANTE: Si menciona nombre de producto específico (tocino, mexicana, doble, pastor, etc.) → show_product_details con "product" en entities
- get_recommendation: Pide sugerencia ("recomiéndame", "qué me sugieres")
- view_menu: Pregunta genérica ("qué tienen", "el menú")
- unknown: No se entiende

REGLA CLAVE:
- "¿Qué hamburguesas tienen?" → view_category (pregunta general)
- "¿Qué tiene la hamburguesa tocino?" → show_product_details (producto específico: "hamburguesa tocino")
- "¿Qué lleva la mexicana?" → show_product_details (producto específico: "mexicana")

RESPONDE JSON:
{"intent":"X","confidence":0.9,"entities":{"product":"nombre del producto","category":"Y"}}

Si es show_product_details, SIEMPRE incluir "product" con el nombre del producto mencionado."""

        logger.info(f"IntentRecognizer OPTIMIZADO inicializado (model: {self.model})")

    async def warmup(self):
        """Precalentar el modelo con una llamada dummy"""
        if self._warmed_up:
            return
        try:
            self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "hi"}],
                max_tokens=5
            )
            self._warmed_up = True
            logger.info("[WARMUP] Modelo Groq precalentado")
        except Exception as e:
            logger.warning(f"[WARMUP] Error precalentando: {e}")

    def _quick_classify(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Clasificador LOCAL rápido - evita llamar a LLM para casos obvios
        Retorna None si necesita LLM, o el resultado si puede clasificar localmente

        IMPORTANTE: El orden de detección es crítico:
        1. Patrones exactos (saludo, despedida, cuenta, etc.)
        2. Preguntas sobre detalles de producto ("qué lleva", "qué tiene", "ingredientes")
        3. Preguntas sobre categorías ("qué bebidas tienes", "de qué hamburguesas")
        4. SOLO si no es pregunta → detectar preferencias para recomendaciones
        """
        text_lower = text.lower().strip()

        # 1. Verificar patrones exactos simples (siempre primero)
        for intent, patterns in self.quick_patterns.items():
            for pattern in patterns:
                if pattern in text_lower:
                    logger.info(f"[QUICK] Clasificado localmente: {intent}")
                    return {
                        "intent": intent,
                        "confidence": 0.95,
                        "entities": {},
                        "reasoning": f"Clasificación rápida: {pattern}"
                    }

        # 2. DETECTAR PREGUNTAS SOBRE DETALLES DE PRODUCTO (ANTES de categorías)
        # "¿Qué lleva la hamburguesa vegetariana?" → SHOW_PRODUCT_DETAILS
        detail_keywords = ['qué lleva', 'que lleva', 'qué tiene', 'que tiene',
                          'ingredientes', 'contiene', 'cómo es', 'como es',
                          'de qué está', 'de que esta', 'qué trae', 'que trae']
        if any(kw in text_lower for kw in detail_keywords):
            logger.info("[QUICK] Pregunta de detalles detectada → usar LLM")
            return None  # Dejar que el LLM extraiga el producto específico

        # 3. DETECTAR PREGUNTAS SOBRE CATEGORÍAS (ANTES de preferencias)
        # "De bebidas qué tienes" → VIEW_CATEGORY, no GET_RECOMMENDATION
        # "¿Qué hamburguesas tienen?" → VIEW_CATEGORY
        category_question_patterns = [
            'qué', 'que', 'tienes', 'tienen', 'hay', 'muestra', 'ver', 'mostrar',
            'cuáles', 'cuales', 'opciones', 'de qué', 'de que'
        ]
        is_category_question = any(q in text_lower for q in category_question_patterns)

        if is_category_question:
            for category, patterns in self.category_patterns.items():
                for pattern in patterns:
                    if pattern in text_lower:
                        logger.info(f"[QUICK] Categoría detectada: {category}")
                        return {
                            "intent": Intent.VIEW_CATEGORY,
                            "confidence": 0.90,
                            "entities": {"category": category},
                            "reasoning": f"Pregunta por categoría {category}"
                        }

        # 4. Detectar view_menu genérico
        menu_triggers = ['qué tienen', 'que tienen', 'el menú', 'el menu', 'carta', 'opciones']
        if any(trigger in text_lower for trigger in menu_triggers):
            has_category = any(cat in text_lower for cats in self.category_patterns.values() for cat in cats)
            if not has_category:
                logger.info("[QUICK] View menu genérico")
                return {
                    "intent": Intent.VIEW_MENU,
                    "confidence": 0.85,
                    "entities": {},
                    "reasoning": "Pregunta genérica por menú"
                }

        # 5. Detectar preguntas de recomendación EXPLÍCITAS
        recommendation_triggers = ['recomienda', 'sugieres', 'sugiere', 'aconsejas', 'qué me', 'que me']
        if any(trigger in text_lower for trigger in recommendation_triggers):
            # Extraer preferencia si la hay
            entities = {}
            for pref_type, pref_dict in self.recommendation_patterns.items():
                for pref_value, keywords in pref_dict.items():
                    for keyword in keywords:
                        if keyword in text_lower:
                            entities[pref_type] = pref_value
                            break
            logger.info(f"[QUICK] Recomendación explícita detectada: {entities}")
            return {
                "intent": Intent.GET_RECOMMENDATION,
                "confidence": 0.90,
                "entities": entities,
                "reasoning": "Solicitud de recomendación"
            }

        # 6. SOLO detectar preferencias si es una respuesta corta a un embudo
        # (menos de 5 palabras y contiene palabra de preferencia)
        word_count = len(text_lower.split())
        if word_count <= 5:  # Respuesta corta como "vegetariano", "algo ligero", "carne"
            for pref_type, pref_dict in self.recommendation_patterns.items():
                for pref_value, keywords in pref_dict.items():
                    for keyword in keywords:
                        if keyword in text_lower:
                            entities = {pref_type: pref_value}
                            logger.info(f"[QUICK] Respuesta a embudo: {pref_type}={pref_value}")
                            return {
                                "intent": Intent.GET_RECOMMENDATION,
                                "confidence": 0.85,
                                "entities": entities,
                                "reasoning": f"Respuesta corta de embudo: {keyword}"
                            }

        # No se pudo clasificar localmente, necesita LLM
        return None

    def _correct_transcription(self, text: str) -> str:
        """Corregir errores comunes de transcripción STT"""
        corrections = {
            "implicantes": "sin picante",
            "complicantes": "sin picante",
            "sin picate": "sin picante",
            "amburgesas": "hamburguesas",
            "hamburgesa": "hamburguesa",
            "bevidas": "bebidas",
        }
        corrected = text.lower()
        for error, fix in corrections.items():
            if error in corrected:
                corrected = corrected.replace(error, fix)
                logger.info(f"[STT-FIX] '{error}' → '{fix}'")
        return corrected if corrected != text.lower() else text

    async def recognize(self, text: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Reconocer intención - OPTIMIZADO con clasificador rápido local
        """
        try:
            # 1. Corregir transcripción
            corrected_text = self._correct_transcription(text)

            # 2. INTENTAR CLASIFICACIÓN LOCAL RÁPIDA (sin LLM)
            quick_result = self._quick_classify(corrected_text)
            if quick_result:
                logger.info(f"[FAST] Intent local: {quick_result['intent']} (sin LLM)")
                return quick_result

            # 3. Solo si no se pudo clasificar localmente, usar LLM
            logger.info("[LLM] Clasificación local no exitosa, usando Groq...")

            # Construir prompt minimalista
            user_prompt = f'"{corrected_text}"'

            # Solo agregar contexto mínimo si es necesario
            if context and context.get('conversation_history'):
                history = context['conversation_history'][-2:]  # Solo últimos 2 mensajes
                if history:
                    ctx = " | ".join([f"{m['role']}: {m['content'][:50]}" for m in history])
                    user_prompt = f'Contexto: {ctx}\nCliente: "{corrected_text}"'

            # Llamar a Groq con tokens limitados
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2,
                max_tokens=150  # Reducido de 500
            )

            result = self._extract_json(response.choices[0].message.content.strip())
            logger.info(f"[LLM] Intent: {result['intent']} (confidence: {result.get('confidence', 0):.2f})")
            return result

        except Exception as e:
            logger.error(f"Error reconociendo intención: {e}")
            return {"intent": Intent.UNKNOWN, "confidence": 0.0, "entities": {}, "error": str(e)}

    def _extract_json(self, text: str) -> Dict:
        """Extraer JSON de respuesta de Groq"""
        try:
            # Buscar JSON en la respuesta
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                return json.loads(json_str)
            else:
                # Si no hay JSON, intentar parsear todo
                return json.loads(text)
        except json.JSONDecodeError:
            logger.warning(f"No se pudo parsear JSON de: {text}")
            return {
                "intent": Intent.UNKNOWN,
                "confidence": 0.0,
                "entities": {},
                "raw_response": text
            }

    # Mapa de precios para extras (debe coincidir con customer-app)
    EXTRA_PRICES = {
        'queso': 15,
        'aguacate': 20,
        'guacamole': 25,
        'carne': 30,
        'pollo': 25,
        'camarón': 35,
        'camaron': 35,
        'chorizo': 20,
        'tocino': 15,
        'crema': 10,
        'huevo': 12
    }

    async def extract_products_and_quantities(self, text: str, available_products: List[Dict], conversation_history: List[Dict] = None) -> List[Dict]:
        """
        Extraer productos, cantidades y MODIFICADORES ESTRUCTURADOS del texto

        Args:
            text: Texto del usuario
            available_products: Lista de productos del menú
            conversation_history: Historial de conversación para inferir productos del contexto

        Returns:
            Lista de items extraídos con product_id, quantity, modifiers (estructurados), notes
        """
        try:
            # Crear lista de nombres de productos para ayudar a Groq
            product_names = [p['name'] for p in available_products]

            prompt = f"""Dado este menú: {', '.join(product_names)}

Y este texto del cliente: "{text}"

"""

            # Agregar contexto de conversación si está disponible
            if conversation_history:
                prompt += "\nCONTEXTO DE CONVERSACIÓN RECIENTE:\n"
                for msg in conversation_history:
                    role_label = "Cliente" if msg['role'] == 'user' else "Asistente"
                    prompt += f"{role_label}: {msg['content']}\n"
                prompt += "\nIMPORTANTE: Si el cliente dice 'sí', 'claro', 'por favor', etc. después de que el asistente le ofreció UN producto específico, extrae ESE producto del contexto.\n\n"

            prompt += """Extrae los productos mencionados, cantidades y MODIFICADORES.

REGLAS CRÍTICAS:
1. SOLO extrae productos que el cliente mencione EXPLÍCITAMENTE
2. Si el cliente dice "sí"/"claro"/"por favor" Y el asistente acaba de ofrecer UN producto → extrae ESE producto
3. Si el texto es confuso o no menciona productos → devuelve {"items": []}
4. EXTRAE MODIFICADORES como arrays separados:
   - "sin_ingredients": ingredientes que NO quiere (sin cebolla, sin jitomate, etc.)
   - "extra_ingredients": ingredientes EXTRA que quiere (extra queso, con tocino, etc.)

Responde SOLO con JSON:
{
  "items": [
    {
      "product_name": "hamburguesa doble",
      "quantity": 1,
      "sin_ingredients": ["cebolla", "jitomate"],
      "extra_ingredients": ["queso", "tocino"],
      "notes": ""
    }
  ]
}

EJEMPLOS:
- "dame una hamburguesa sin cebolla y sin jitomate" →
  {"items": [{"product_name": "hamburguesa", "quantity": 1, "sin_ingredients": ["cebolla", "jitomate"], "extra_ingredients": [], "notes": ""}]}

- "quiero tacos al pastor con extra cilantro sin cebolla" →
  {"items": [{"product_name": "tacos al pastor", "quantity": 1, "sin_ingredients": ["cebolla"], "extra_ingredients": ["cilantro"], "notes": ""}]}

- "dos coca colas" →
  {"items": [{"product_name": "coca cola", "quantity": 2, "sin_ingredients": [], "extra_ingredients": [], "notes": ""}]}

Si no se menciona cantidad, asume 1.
Si no hay modificadores, deja los arrays vacíos.
"""

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Eres un experto extrayendo pedidos de restaurante con modificadores."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=400
            )

            result_text = response.choices[0].message.content.strip()
            result = self._extract_json(result_text)

            # Mapear nombres a product_ids y estructurar modificadores
            items_with_ids = []
            for item in result.get('items', []):
                product_name = item['product_name'].lower()

                # Buscar producto en el menú
                matched_product = None
                for product in available_products:
                    if product_name in product['name'].lower():
                        matched_product = product
                        break

                if matched_product:
                    # Construir modificadores estructurados (igual que customer-app)
                    modifiers = []

                    # Procesar "sin" ingredientes
                    for ing in item.get('sin_ingredients', []):
                        ing_lower = ing.lower().strip()
                        modifiers.append({
                            "id": f"sin_{ing_lower}",
                            "name": f"Sin {ing_lower}",
                            "price": 0
                        })

                    # Procesar "extra" ingredientes (con precios)
                    for ing in item.get('extra_ingredients', []):
                        ing_lower = ing.lower().strip()
                        # Buscar precio del extra
                        extra_price = 0
                        for key, price in self.EXTRA_PRICES.items():
                            if key in ing_lower:
                                extra_price = price
                                break
                        modifiers.append({
                            "id": f"extra_{ing_lower}",
                            "name": f"Extra {ing_lower}",
                            "price": extra_price
                        })

                    # Calcular precio total con extras
                    base_price = float(matched_product.get('price', 0))
                    modifiers_price = sum(m['price'] for m in modifiers)
                    total_price = base_price + modifiers_price

                    # Crear descripción de notas legible
                    notes_parts = []
                    if item.get('sin_ingredients'):
                        notes_parts.extend([f"Sin {ing}" for ing in item['sin_ingredients']])
                    if item.get('extra_ingredients'):
                        notes_parts.extend([f"Extra {ing}" for ing in item['extra_ingredients']])
                    if item.get('notes'):
                        notes_parts.append(item['notes'])

                    notes_text = ", ".join(notes_parts)

                    items_with_ids.append({
                        "product_id": matched_product['id'],
                        "product_name": matched_product['name'],
                        "quantity": item.get('quantity', 1),
                        "base_price": base_price,
                        "modifiers": modifiers,
                        "modifiers_price": modifiers_price,
                        "total_price": total_price,
                        "notes": notes_text  # Para compatibilidad con backend actual
                    })
                else:
                    logger.warning(f"Producto '{product_name}' no encontrado en menú")

            logger.info(f"Productos extraídos: {len(items_with_ids)} con modificadores estructurados")
            return items_with_ids

        except Exception as e:
            logger.error(f"Error extrayendo productos: {e}")
            return []


# Instancia global
_intent_recognizer: Optional[IntentRecognizer] = None


def get_intent_recognizer() -> IntentRecognizer:
    """Obtener instancia global del IntentRecognizer (Singleton)"""
    global _intent_recognizer
    if _intent_recognizer is None:
        from ..core.config import settings
        _intent_recognizer = IntentRecognizer(
            groq_api_key=settings.GROQ_API_KEY,
            model=settings.GROQ_MODEL
        )
    return _intent_recognizer
