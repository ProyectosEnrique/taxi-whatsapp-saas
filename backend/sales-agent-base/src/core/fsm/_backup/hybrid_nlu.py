"""
================================================================================
HYBRID NLU - CLASIFICADOR DE INTENCIONES LLM-FIRST
================================================================================
Sistema híbrido que usa LLM (Cerebras) como clasificador principal de intenciones,
con regex como apoyo para validación y modo offline.

Arquitectura:
┌─────────────────────────────────────────────────────────────────┐
│                      MODO ONLINE                                │
│  Usuario → Cerebras (clasificación) → FSM → Respuesta           │
│                 ↓                                               │
│         [Registra patrón exitoso]                               │
│                 ↓                                               │
│         PatternLearner → Base de patrones                       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      MODO OFFLINE                               │
│  Usuario → Regex Aprendido → FSM → Respuesta                    │
│         (funciona sin internet)                                 │
└─────────────────────────────────────────────────────────────────┘

v1.0 - Diciembre 2024
================================================================================
"""

import re
import json
import logging
import time
import asyncio
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import threading

logger = logging.getLogger(__name__)

# Importar LoRA Training Collector (para guardar conversaciones)
try:
    from ...learning import get_lora_collector, record_cerebras_success, InteractionType
    LORA_COLLECTOR_AVAILABLE = True
except ImportError:
    LORA_COLLECTOR_AVAILABLE = False
    logger.warning("[HYBRID_NLU] LoRA Collector no disponible")


class ConnectionStatus(Enum):
    """Estado de conectividad"""
    ONLINE = "online"
    OFFLINE = "offline"
    DEGRADED = "degraded"  # Conexión lenta o inestable


@dataclass
class NLUResult:
    """Resultado de clasificación NLU"""
    intent: str
    confidence: float
    entities: Dict[str, Any] = field(default_factory=dict)
    source: str = "unknown"  # "llm", "regex", "fallback"
    latency_ms: float = 0.0
    raw_response: Optional[str] = None
    # NUEVO: Respuesta directa del LLM para intents conversacionales
    llm_response: Optional[str] = None  # Si el LLM generó respuesta directa
    has_direct_response: bool = False   # True si llm_response debe usarse
    # NUEVO v2: Productos extraídos para pedidos (evita llamar a Gemini)
    extracted_products: List[Dict] = field(default_factory=list)  # [{name, quantity, price}]
    has_extracted_products: bool = False  # True si Cerebras extrajo productos


@dataclass
class LearnedIntent:
    """Patrón de intent aprendido del LLM"""
    intent: str
    patterns: List[str]  # Patrones regex generados
    examples: List[str]  # Ejemplos que matchearon
    confidence_threshold: float = 0.8
    times_used: int = 0
    success_rate: float = 1.0
    last_used: datetime = field(default_factory=datetime.now)


class HybridNLU:
    """
    Clasificador de intenciones híbrido LLM-first.

    Flujo:
    1. Verificar conectividad
    2. Si ONLINE → usar LLM (Cerebras) para clasificar
    3. Si OFFLINE → usar regex aprendido
    4. Registrar patrones exitosos para aprendizaje

    Características:
    - LLM como cerebro principal (más preciso)
    - Regex como respaldo offline (gratis, rápido)
    - Aprendizaje continuo de patrones
    - Cambio automático online/offline
    """

    # Intents soportados por el sistema (DEBEN coincidir con decision_tree.Intent)
    SUPPORTED_INTENTS = [
        # Navegación
        'greeting',              # Saludo inicial
        'view_menu',             # Ver menú completo
        'view_category',         # Ver categoría específica
        'view_product_details',  # Ver detalles de producto

        # Recomendaciones
        'get_recommendation',    # Pedir recomendación
        'ask_opinion',           # Preguntar opinión
        'complex_recommendation',# Recomendación compleja (LLM)

        # Pedido
        'add_to_order',          # Agregar producto al pedido
        'remove_from_order',     # Quitar producto del pedido
        'modify_order',          # Modificar cantidad o producto
        'confirm_order',         # Confirmar pedido
        'special_request',       # Solicitud especial (LLM)

        # Respuestas a ofertas
        'accept_suggestion',     # Sí, ok, claro (afirmativo)
        'reject_suggestion',     # No, gracias (negativo)

        # Preguntas
        'ask_price',             # Preguntar precio
        'ask_ingredients',       # Preguntar ingredientes
        'ask_spicy',             # Preguntar picante
        'ask_size',              # Preguntar tamaño

        # Cierre
        'finish_order',          # Es todo, finalizar
        'goodbye',               # Despedida

        # Objeciones
        'handle_objection',      # "Es muy caro"
        'negotiate',             # "¿Descuento?"
        'complaint',             # Queja

        # Solicitudes de servicio
        'service_request',       # "Más salsa", "Servilletas"
        'request_waiter',        # "Mesero!"
        'request_bill',          # "La cuenta"

        # Otros
        'unknown',               # No clasificado
        'need_clarification'     # Necesita aclaración
    ]

    # Mapeo de sinónimos a intents canónicos
    INTENT_ALIASES = {
        'affirmative': 'accept_suggestion',
        'negative': 'reject_suggestion',
        'ask_recommendation': 'get_recommendation',
        'view_order': 'finish_order',
        'cancel_order': 'remove_from_order',
        'help': 'unknown',
        'thanks': 'goodbye',
        'ask_allergens': 'ask_ingredients',
    }

    # Patrones regex base (siempre disponibles offline)
    BASE_PATTERNS = {
        'greeting': [
            r'^(hola|buenas?\s*(tardes?|noches?|dias?)|que\s*tal|hey|ey)\b',
            r'^(buenos?\s*dias?|buenas\s*(tardes?|noches?))\b',
        ],
        'add_to_order': [
            r'\b(quiero|dame|ponme|traeme|sirve|pido|agrega|añade)\b.*\b(una?|dos|tres|\d+)?\s*\w+',
            r'\b(una?|dos|tres|\d+)\s*(hamburguesa|taco|coca|agua|refresco|orden|papas)',
        ],
        'remove_from_order': [
            r'\b(quita|quitame|quítame|elimina|borra|retira|ya no)\b',
            r'\bno\s+(quiero|va)\b.*\b(hamburguesa|taco|coca|agua|refresco)',
        ],
        'finish_order': [
            r'\b(que\s*llevo|mi\s*pedido|mi\s*orden|cuanto\s*(es|llevo|va))\b',
            r'\b(ver|mostrar|enseña)\s*(mi\s*)?(pedido|orden)\b',
            r'\b(eso\s*es\s*todo|seria\s*todo|nada\s*mas|es\s*todo)\b',
        ],
        'confirm_order': [
            r'\b(confirmar?|listo|confirmo)\b',
            r'^(si|sí|ok)[\s,]*(confirma|listo|todo)?\b',
        ],
        'view_menu': [
            r'\b(menu|carta|que\s*tienen|que\s*hay|opciones)\b',
        ],
        'view_category': [
            r'\b(hamburguesas?|tacos?|bebidas?|postres?|entradas?|ensaladas?|complementos?)\b',
        ],
        'get_recommendation': [
            r'\b(recomiend|sugier|que\s*me\s*recomiendas?|que\s*(hay|tienes)\s*bueno)\b',
            r'\b(cual\s*es\s*(el|la)\s*mejor|mas\s*pedido|mas\s*popular)\b',
        ],
        'accept_suggestion': [
            r'^(si|sí|ok|okey|vale|claro|por\s*supuesto|correcto|exacto|eso|dale|perfecto)\b',
            r'^(si\s*por\s*favor|claro\s*que\s*si|va|vamos)\b',
        ],
        'reject_suggestion': [
            r'^(no|nel|nop|nope|para\s*nada|negativo)\b',
            r'^(no\s*gracias|no\s*quiero|mejor\s*no|asi\s*esta\s*bien)\b',
        ],
        'goodbye': [
            r'\b(adios|bye|hasta\s*luego|nos\s*vemos|chao|me\s*voy|gracias)\b',
        ],
        'ask_price': [
            r'\b(cuanto\s*(cuesta|vale|es)|precio|a\s*como)\b',
        ],
        'ask_ingredients': [
            r'\b(ingredientes?|que\s*lleva|que\s*tiene|de\s*que\s*es)\b',
        ],
        'service_request': [
            r'\b(mas\s*(salsa|limones?|servilletas?|tortillas?|chile|agua|hielo))\b',
            r'\b(traeme|trae|sirve)\s*(mas\s*)?(salsa|limones?|servilletas?)\b',
        ],
        'request_waiter': [
            r'\b(mesero|mesera|camarero|atencion|disculpa)\b',
        ],
        'request_bill': [
            r'\b(la\s*cuenta|quiero\s*pagar|cobrar|factura)\b',
        ],
        'complaint': [
            r'\b(queja|problema|mal|frio|tardado|espero|molest)\b',
        ],
        'handle_objection': [
            r'\b(muy\s*caro|caro|costoso|no\s*me\s*gusta|no\s*quiero)\b',
        ],
    }

    def __init__(
        self,
        llm_provider=None,
        config: Dict = None,
        enable_learning: bool = True,
        menu: List[Dict] = None
    ):
        """
        Inicializa el clasificador híbrido.

        Args:
            llm_provider: Proveedor LLM (Cerebras recomendado)
            config: Configuración personalizada
            enable_learning: Si habilitar aprendizaje de patrones
            menu: Lista de productos del menú (para respuestas directas)
        """
        self.llm_provider = llm_provider
        self.config = config or {}
        self.enable_learning = enable_learning
        self.menu = menu or []

        # Estado de conectividad
        self.connection_status = ConnectionStatus.ONLINE
        self._last_connectivity_check = 0
        self._connectivity_check_interval = 30  # segundos

        # Patrones aprendidos (se cargan de disco)
        self.learned_intents: Dict[str, LearnedIntent] = {}
        self._load_learned_patterns()

        # Métricas
        self.stats = {
            'total_classifications': 0,
            'llm_classifications': 0,
            'regex_classifications': 0,
            'fallback_classifications': 0,
            'patterns_learned': 0,
            'avg_latency_ms': 0.0
        }

        # Lock para thread safety
        self._lock = threading.Lock()

        # Compilar patrones base
        self._compiled_patterns = self._compile_patterns(self.BASE_PATTERNS)

        logger.info(f"[HYBRID_NLU] Inicializado | LLM: {'Sí' if llm_provider else 'No'} | "
                   f"Patrones aprendidos: {len(self.learned_intents)}")

    def _compile_patterns(self, patterns_dict: Dict[str, List[str]]) -> Dict[str, List]:
        """Compila patrones regex para eficiencia"""
        compiled = {}
        for intent, patterns in patterns_dict.items():
            compiled[intent] = []
            for pattern in patterns:
                try:
                    compiled[intent].append(re.compile(pattern, re.IGNORECASE))
                except re.error as e:
                    logger.warning(f"[HYBRID_NLU] Patrón inválido para {intent}: {e}")
        return compiled

    def _load_learned_patterns(self):
        """Carga patrones aprendidos del disco"""
        import os
        patterns_path = self.config.get('patterns_path', '/app/data/learning/learned_intents.json')

        try:
            if os.path.exists(patterns_path):
                with open(patterns_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for intent, info in data.items():
                        self.learned_intents[intent] = LearnedIntent(
                            intent=intent,
                            patterns=info.get('patterns', []),
                            examples=info.get('examples', []),
                            confidence_threshold=info.get('confidence_threshold', 0.8),
                            times_used=info.get('times_used', 0),
                            success_rate=info.get('success_rate', 1.0)
                        )
                logger.info(f"[HYBRID_NLU] Cargados {len(self.learned_intents)} intents aprendidos")
        except Exception as e:
            logger.warning(f"[HYBRID_NLU] Error cargando patrones: {e}")

    def _save_learned_patterns(self):
        """Guarda patrones aprendidos al disco"""
        import os
        patterns_path = self.config.get('patterns_path', '/app/data/learning/learned_intents.json')

        try:
            os.makedirs(os.path.dirname(patterns_path), exist_ok=True)
            data = {}
            for intent, learned in self.learned_intents.items():
                data[intent] = {
                    'patterns': learned.patterns,
                    'examples': learned.examples[-100:],  # Últimos 100 ejemplos
                    'confidence_threshold': learned.confidence_threshold,
                    'times_used': learned.times_used,
                    'success_rate': learned.success_rate
                }

            with open(patterns_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

        except Exception as e:
            logger.error(f"[HYBRID_NLU] Error guardando patrones: {e}")

    def _check_connectivity(self) -> ConnectionStatus:
        """Verifica conectividad con el LLM"""
        current_time = time.time()

        # No verificar demasiado frecuentemente
        if current_time - self._last_connectivity_check < self._connectivity_check_interval:
            return self.connection_status

        self._last_connectivity_check = current_time

        if not self.llm_provider:
            self.connection_status = ConnectionStatus.OFFLINE
            return self.connection_status

        try:
            # Verificar si el provider está disponible
            if hasattr(self.llm_provider, 'is_available') and self.llm_provider.is_available():
                self.connection_status = ConnectionStatus.ONLINE
            else:
                self.connection_status = ConnectionStatus.OFFLINE
        except Exception:
            self.connection_status = ConnectionStatus.OFFLINE

        return self.connection_status

    def classify(self, text: str, context: Dict = None) -> NLUResult:
        """
        Clasifica la intención del texto.

        Flujo:
        1. Si ONLINE → LLM (Cerebras)
        2. Si OFFLINE → Regex aprendido + base
        3. Registrar para aprendizaje

        Args:
            text: Texto a clasificar
            context: Contexto adicional (estado actual, carrito, etc.)

        Returns:
            NLUResult con intent, confidence y entities
        """
        start_time = time.time()
        self.stats['total_classifications'] += 1

        # Normalizar texto
        text_clean = text.strip().lower()

        # Verificar conectividad
        status = self._check_connectivity()

        result = None

        # PASO 1: Intentar con LLM si está online
        if status == ConnectionStatus.ONLINE and self.llm_provider:
            result = self._classify_with_llm(text_clean, context)

            if result and result.confidence >= 0.7:
                self.stats['llm_classifications'] += 1

                # Registrar para aprendizaje
                if self.enable_learning:
                    self._register_successful_classification(text_clean, result)

        # PASO 2: Si LLM no disponible o falló, usar regex
        if not result or result.confidence < 0.5:
            regex_result = self._classify_with_regex(text_clean)

            if regex_result:
                # Si teníamos resultado LLM con baja confianza, comparar
                if result and result.confidence >= regex_result.confidence:
                    pass  # Mantener resultado LLM
                else:
                    result = regex_result
                    self.stats['regex_classifications'] += 1

        # PASO 3: Fallback a 'unknown' si nada funcionó
        if not result:
            result = NLUResult(
                intent='unknown',
                confidence=0.0,
                source='fallback'
            )
            self.stats['fallback_classifications'] += 1

        # Calcular latencia
        result.latency_ms = (time.time() - start_time) * 1000

        # Actualizar promedio de latencia
        total = self.stats['total_classifications']
        avg = self.stats['avg_latency_ms']
        self.stats['avg_latency_ms'] = ((avg * (total - 1)) + result.latency_ms) / total

        logger.debug(f"[HYBRID_NLU] '{text_clean[:30]}...' → {result.intent} "
                    f"({result.confidence:.2f}, {result.source}, {result.latency_ms:.0f}ms)")

        return result

    # Intents que son conversacionales (requieren respuesta con menú)
    CONVERSATIONAL_INTENTS = [
        'view_menu', 'view_category', 'ask_size', 'ask_price',
        'ask_ingredients', 'ask_spicy', 'get_recommendation', 'view_product_details'
    ]

    def _classify_with_llm(self, text: str, context: Dict = None) -> Optional[NLUResult]:
        """
        Clasifica usando LLM (Cerebras) - VERSIÓN OPTIMIZADA

        Para intents conversacionales: Clasifica Y responde en UNA SOLA LLAMADA.
        Para intents de acción: Solo clasifica (FSM maneja la acción).

        Esto elimina la redundancia de llamar a Cerebras dos veces.
        """
        if not self.llm_provider:
            return None

        try:
            # Construir contexto del carrito
            cart_context = ""
            if context:
                if context.get('cart_items'):
                    cart_items = context['cart_items']
                    cart_context = f"\nCARRITO ACTUAL: {len(cart_items)} productos"
                    if cart_items:
                        cart_context += f" ({', '.join(cart_items[:3])})"
                if context.get('current_state'):
                    cart_context += f"\nEstado: {context['current_state']}"

            # Construir resumen del menú para el LLM
            menu_summary = self._build_menu_summary()

            # === PROMPT UNIFICADO: Clasificar + Responder + Extraer Pedidos ===
            prompt = f"""Eres un mesero experto en un restaurante mexicano. Conoces TODO el menú.

MENÚ COMPLETO:
{menu_summary}
{cart_context}

TEXTO DEL CLIENTE: "{text}"

ANALIZA y responde con este JSON:

{{
  "intent_type": "explorar_categoria | ver_producto | preguntar_info | hacer_pedido | modificar_pedido | saludo | despedida | confirmar | rechazar | otro",
  "category": "categoría mencionada o null",
  "product": "producto específico o null",
  "quantity": "cantidad o null",
  "is_question": true/false,
  "question_type": "precio | tamaño | ingredientes | disponibilidad | picante | null",
  "confidence": 0.0-1.0,
  "response": "Tu respuesta como mesero (2-3 oraciones)",
  "order_items": [
    {{"name": "nombre EXACTO del producto del menú", "quantity": 1, "price": 45.00}}
  ],
  "modification": {{
    "action": "replace | remove | add_more",
    "original_product": "nombre EXACTO del producto a modificar (del carrito/menú)",
    "new_product": "nombre EXACTO del producto nuevo (del menú) o null si es remove",
    "quantity": 1
  }}
}}

REGLAS CRÍTICAS:
1. intent_type="hacer_pedido": SOLO para productos NUEVOS
   - order_items SOLO debe contener lo que el cliente ACABA de pedir
   - NUNCA incluyas productos que ya están en el carrito

2. intent_type="modificar_pedido": Para cambios/sustituciones/eliminaciones
   - SIEMPRE incluye el objeto "modification" con datos NORMALIZADOS
   - "cámbiame la coca por limonada" → modification: {{"action": "replace", "original_product": "Coca-Cola", "new_product": "Limonada Mineral"}}
   - "quita la hamburguesa" → modification: {{"action": "remove", "original_product": "Hamburguesa Clásica", "new_product": null}}
   - "dame otra coca más" → modification: {{"action": "add_more", "original_product": "Coca-Cola", "new_product": null, "quantity": 1}}
   - IMPORTANTE: Usa nombres EXACTOS del menú, no lo que dijo el cliente

3. Si es pregunta informativa: response con la info, order_items vacío []

4. Si es saludo/despedida: response amigable, order_items vacío []

EJEMPLOS:
- "quiero 2 tacos de asada" → hacer_pedido, order_items: [{{"name": "Taco de Carne Asada", "quantity": 2}}]
- "cámbiame la coca por una limonada" → modificar_pedido, modification: {{"action": "replace", "original_product": "Coca-Cola", "new_product": "Limonada Mineral"}}
- "quiero limonada en lugar de coca" → modificar_pedido, modification: {{"action": "replace", "original_product": "Coca-Cola", "new_product": "Limonada Mineral"}}
- "quita la hamburguesa" → modificar_pedido, modification: {{"action": "remove", "original_product": "Hamburguesa Clásica"}}

IMPORTANTE:
- Responde SOLO el JSON, sin markdown
- En modificar_pedido, NORMALIZA los nombres al menú real (coca → Coca-Cola, limonada → Limonada Mineral)"""

            # Llamar al LLM UNA SOLA VEZ
            response = self.llm_provider.generate(
                prompt=prompt,
                messages=[{"role": "user", "content": text}],
                temperature=0.5,
                max_tokens=350
            )

            response_text = response.get('response_text', '').strip()

            # Limpiar markdown si existe
            if response_text.startswith('```'):
                response_text = re.sub(r'^```\w*\n?', '', response_text)
                response_text = re.sub(r'\n?```$', '', response_text)

            # Parsear JSON
            parsed = json.loads(response_text)

            # Extraer datos
            intent_type = parsed.get('intent_type', 'otro')
            category = parsed.get('category')
            product = parsed.get('product')
            quantity = parsed.get('quantity')
            is_question = parsed.get('is_question', False)
            question_type = parsed.get('question_type')
            confidence = float(parsed.get('confidence', 0.7))
            llm_response = parsed.get('response', '')
            order_items = parsed.get('order_items', [])

            # Mapear a intent del sistema
            intent = self._map_semantic_to_intent(
                intent_type=intent_type,
                category=category,
                product=product,
                is_question=is_question,
                question_type=question_type
            )

            # Construir entidades
            entities = {}
            if category:
                entities['category'] = category
                entities['menu_category'] = category
            if product:
                entities['product'] = product
                entities['mentioned_product'] = product
            if quantity:
                try:
                    entities['quantity'] = int(quantity)
                except (ValueError, TypeError):
                    entities['quantity'] = 1

            # === NUEVO: Procesar productos extraídos para pedidos ===
            extracted_products = []
            has_extracted_products = False

            if intent == 'add_to_order' and order_items:
                # Validar y normalizar productos extraídos
                for item in order_items:
                    if isinstance(item, dict) and item.get('name'):
                        # Buscar producto en el menú para validar
                        matched_product = self._match_product_to_menu(item.get('name', ''))
                        if matched_product:
                            extracted_products.append({
                                'name': matched_product.get('name'),
                                'quantity': int(item.get('quantity', 1)),
                                'price': float(matched_product.get('price', 0)),
                                'product_id': matched_product.get('id'),
                                'category': matched_product.get('category', {}).get('name', '')
                            })
                        else:
                            # Producto no encontrado en menú, usar lo que dijo Cerebras
                            logger.warning(f"[HYBRID_NLU] Producto no encontrado en menú: {item.get('name')}")
                            extracted_products.append({
                                'name': item.get('name'),
                                'quantity': int(item.get('quantity', 1)),
                                'price': float(item.get('price', 0)),
                                'product_id': None,
                                'category': ''
                            })

                has_extracted_products = len(extracted_products) > 0
                if has_extracted_products:
                    logger.info(f"[HYBRID_NLU] Productos extraídos: {len(extracted_products)} items")
                    for p in extracted_products:
                        logger.info(f"  - {p['quantity']}x {p['name']} (${p['price']})")

            # === NUEVO: Procesar datos de modificación ===
            modification_data = None
            if intent == 'modify_order' and parsed.get('modification'):
                mod = parsed.get('modification')
                action = mod.get('action', 'replace')
                original_name = mod.get('original_product')
                new_name = mod.get('new_product')

                # Normalizar nombres de productos usando el menú
                original_matched = self._match_product_to_menu(original_name) if original_name else None
                new_matched = self._match_product_to_menu(new_name) if new_name else None

                modification_data = {
                    'action': action,
                    'original_product': original_matched.get('name') if original_matched else original_name,
                    'original_product_id': original_matched.get('id') if original_matched else None,
                    'new_product': new_matched.get('name') if new_matched else new_name,
                    'new_product_id': new_matched.get('id') if new_matched else None,
                    'new_product_price': float(new_matched.get('price', 0)) if new_matched else 0,
                    'quantity': int(mod.get('quantity', 1))
                }

                logger.info(f"[HYBRID_NLU] Modificación extraída: {action} | "
                           f"'{modification_data['original_product']}' → '{modification_data['new_product']}'")

                # Guardar en entities para que FSM lo use
                entities['_modification_data'] = modification_data
                entities['_has_modification_data'] = True

            # Determinar si usar respuesta directa
            has_direct_response = (
                intent in self.CONVERSATIONAL_INTENTS and
                llm_response and
                llm_response != "PEDIDO" and
                len(llm_response) > 10
            )

            logger.info(f"[HYBRID_NLU] {intent_type} → {intent} | "
                       f"Respuesta directa: {'Sí' if has_direct_response else 'No'} | "
                       f"Productos: {len(extracted_products)}")

            # === GUARDAR PARA ENTRENAMIENTO DE LORA ===
            if LORA_COLLECTOR_AVAILABLE and confidence >= 0.8:
                try:
                    record_cerebras_success(
                        user_input=text,
                        intent=intent,
                        response=llm_response if llm_response else "",
                        products=extracted_products if extracted_products else [],
                        entities=entities,
                        confidence=confidence,
                        context=context
                    )
                    logger.debug(f"[HYBRID_NLU] Conversación guardada para LoRA training")
                except Exception as e:
                    logger.warning(f"[HYBRID_NLU] Error guardando para LoRA: {e}")

            return NLUResult(
                intent=intent,
                confidence=confidence,
                entities=entities,
                source='llm',
                raw_response=response_text,
                llm_response=llm_response if has_direct_response else None,
                has_direct_response=has_direct_response,
                extracted_products=extracted_products,
                has_extracted_products=has_extracted_products
            )

        except json.JSONDecodeError as e:
            logger.warning(f"[HYBRID_NLU] Error parseando respuesta LLM: {e}")
            return self._classify_with_llm_legacy(text, context)
        except Exception as e:
            logger.error(f"[HYBRID_NLU] Error en clasificación LLM: {e}")
            return None

    def _build_menu_summary(self) -> str:
        """Construye resumen del menú para el prompt"""
        if not self.menu:
            return "Menú no disponible"

        # Agrupar por categoría
        categories = {}
        for product in self.menu:
            cat_name = product.get('category', {}).get('name', 'Otros')
            if cat_name not in categories:
                categories[cat_name] = []
            categories[cat_name].append(product)

        # Construir resumen compacto
        lines = []
        for cat_name, products in categories.items():
            items = []
            for p in products[:6]:  # Máximo 6 por categoría
                name = p.get('name', 'Sin nombre')
                price = p.get('price', '0')
                items.append(f"{name} ${price}")
            lines.append(f"{cat_name}: {', '.join(items)}")

        return "\n".join(lines)

    def set_menu(self, menu: List[Dict]):
        """Actualiza el menú (para sincronizar con FSM)"""
        self.menu = menu or []
        logger.info(f"[HYBRID_NLU] Menú actualizado: {len(self.menu)} productos")

    def _match_product_to_menu(self, product_name: str) -> Optional[Dict]:
        """
        Busca un producto en el menú por nombre (fuzzy matching).
        Retorna el producto del menú si encuentra match, None si no.
        """
        if not self.menu or not product_name:
            return None

        product_name_lower = product_name.lower().strip()

        # 1. Búsqueda exacta
        for product in self.menu:
            if product.get('name', '').lower() == product_name_lower:
                return product

        # 2. Búsqueda por contenido (el nombre del menú contiene lo buscado)
        for product in self.menu:
            menu_name = product.get('name', '').lower()
            if product_name_lower in menu_name or menu_name in product_name_lower:
                return product

        # 3. Búsqueda por palabras clave
        search_words = set(product_name_lower.split())
        best_match = None
        best_score = 0

        for product in self.menu:
            menu_name = product.get('name', '').lower()
            menu_words = set(menu_name.split())

            # Contar palabras en común
            common_words = search_words & menu_words
            if len(common_words) > best_score:
                best_score = len(common_words)
                best_match = product

        # Solo retornar si hay al menos 1 palabra en común
        if best_score >= 1:
            return best_match

        return None

    def _map_semantic_to_intent(
        self,
        intent_type: str,
        category: str = None,
        product: str = None,
        is_question: bool = False,
        question_type: str = None
    ) -> str:
        """
        Mapea el análisis semántico de Cerebras a los intents del sistema.
        Esta es la "traducción" entre la libertad del LLM y la estructura del FSM.
        """
        intent_type = intent_type.lower() if intent_type else 'otro'

        # Saludos y despedidas
        if intent_type == 'saludo':
            return 'greeting'
        if intent_type == 'despedida':
            return 'goodbye'

        # Confirmaciones y rechazos
        if intent_type == 'confirmar':
            return 'accept_suggestion'
        if intent_type == 'rechazar':
            return 'reject_suggestion'

        # Preguntas informativas
        if is_question and question_type:
            question_map = {
                'precio': 'ask_price',
                'tamaño': 'ask_size',
                'ingredientes': 'ask_ingredients',
                'disponibilidad': 'view_category',  # "tienen X?" es explorar
                'picante': 'ask_spicy',
            }
            if question_type in question_map:
                return question_map[question_type]

        # Explorar categoría vs ver producto específico
        if intent_type == 'explorar_categoria':
            return 'view_category'

        if intent_type == 'ver_producto':
            # Solo es view_product_details si hay un producto ESPECÍFICO
            if product and len(product) > 3:
                return 'view_product_details'
            # Si solo hay categoría, es explorar
            if category:
                return 'view_category'
            return 'view_menu'

        # Hacer pedido
        if intent_type == 'hacer_pedido':
            return 'add_to_order'

        # Modificar pedido (cambiar, quitar, sustituir)
        if intent_type == 'modificar_pedido':
            return 'modify_order'

        # Preguntar info general
        if intent_type == 'preguntar_info':
            # Normalizar question_type
            qt = question_type.lower() if question_type else ''

            if qt in ['precio', 'costo', 'cuanto', 'cuánto']:
                return 'ask_price'
            if qt in ['tamaño', 'tamano', 'cantidad', 'porciones', 'porción', 'cuantos', 'cuántos']:
                return 'ask_size'
            if qt in ['ingredientes', 'lleva', 'contiene', 'tiene']:
                return 'ask_ingredients'
            if qt in ['picante', 'picoso', 'enchilado']:
                return 'ask_spicy'

            # Si pregunta por disponibilidad de categoría
            if category:
                return 'view_category'
            return 'get_recommendation'

        # Default: si hay categoría Y es pregunta, probablemente quiere info
        # Si solo hay categoría sin pregunta, es explorar
        if category:
            if is_question:
                # Preguntas como "cuántos tacos trae?" van a ask_size
                return 'ask_size' if question_type in ['tamaño', 'cantidad', None] else 'view_category'
            return 'view_category'

        return 'view_menu'

    # =========================================================================
    # OPCIÓN A (LEGACY) - Clasificación con intents predefinidos
    # Mantener comentado por si necesitamos revertir
    # =========================================================================
    def _classify_with_llm_legacy(self, text: str, context: Dict = None) -> Optional[NLUResult]:
        """
        [LEGACY] Clasificación con intents predefinidos.
        Usar como fallback si la Opción B falla.
        """
        if not self.llm_provider:
            return None

        try:
            intents_list = ", ".join(self.SUPPORTED_INTENTS)

            context_info = ""
            if context:
                if context.get('cart_items'):
                    context_info += f"\nCarrito actual: {len(context['cart_items'])} items"
                if context.get('current_state'):
                    context_info += f"\nEstado: {context['current_state']}"

            prompt = f"""Eres un clasificador de intenciones para un restaurante mexicano.

INTENCIONES VÁLIDAS: {intents_list}

TEXTO DEL CLIENTE: "{text}"
{context_info}

REGLAS IMPORTANTES:
- view_category: Cuando pregunta por una CATEGORÍA de productos (tacos, hamburguesas, bebidas, ensaladas, postres, etc.)
  Ejemplos: "tienes tacos?", "qué hamburguesas tienen?", "tienen ensaladas?", "qué bebidas hay?"

- view_product_details: SOLO cuando menciona un PRODUCTO ESPECÍFICO por nombre completo
  Ejemplos: "cuéntame del Taco al Pastor", "detalles de la Hamburguesa Clásica"

- ask_size: Cuando pregunta por tamaño, cantidad o porciones
  Ejemplos: "cuántos tacos trae la orden?", "de qué tamaño es?", "cuántas piezas son?"

- add_to_order: Cuando quiere AGREGAR algo al pedido
  Ejemplos: "quiero unos tacos", "dame una hamburguesa", "ponme 2 refrescos"

INSTRUCCIONES:
1. Clasifica el texto en UNA de las intenciones válidas
2. Extrae entidades: category (tacos, hamburguesas, etc.), product (nombre específico), quantity
3. Responde SOLO con JSON válido

FORMATO (sin markdown):
{{"intent": "nombre_intent", "confidence": 0.95, "entities": {{"category": "tacos", "product": "...", "quantity": 1}}}}

Si no estás seguro, usa confidence bajo (0.5-0.7).
"""

            response = self.llm_provider.generate(
                prompt=prompt,
                messages=[{"role": "user", "content": text}],
                temperature=0.1,
                max_tokens=150
            )

            response_text = response.get('response_text', '').strip()

            if response_text.startswith('```'):
                response_text = re.sub(r'^```\w*\n?', '', response_text)
                response_text = re.sub(r'\n?```$', '', response_text)

            parsed = json.loads(response_text)

            intent = parsed.get('intent', 'unknown')
            confidence = float(parsed.get('confidence', 0.5))
            entities = parsed.get('entities', {})

            if intent in self.INTENT_ALIASES:
                intent = self.INTENT_ALIASES[intent]

            if intent not in self.SUPPORTED_INTENTS:
                logger.warning(f"[HYBRID_NLU] Intent desconocido del LLM: {intent}")
                intent = 'unknown'
                confidence = 0.3

            return NLUResult(
                intent=intent,
                confidence=confidence,
                entities=entities,
                source='llm_legacy',
                raw_response=response_text
            )

        except Exception as e:
            logger.error(f"[HYBRID_NLU] Error en clasificación legacy: {e}")
            return None

    def _classify_with_regex(self, text: str) -> Optional[NLUResult]:
        """Clasifica usando patrones regex (base + aprendidos)"""
        best_match = None
        best_confidence = 0.0

        # Primero buscar en patrones aprendidos (más específicos)
        for intent, learned in self.learned_intents.items():
            for pattern in learned.patterns:
                try:
                    if re.search(pattern, text, re.IGNORECASE):
                        # Confianza basada en historial
                        confidence = 0.8 * learned.success_rate
                        if confidence > best_confidence:
                            best_confidence = confidence
                            best_match = intent
                            learned.times_used += 1
                except re.error:
                    continue

        # Luego buscar en patrones base
        for intent, patterns in self._compiled_patterns.items():
            for pattern in patterns:
                if pattern.search(text):
                    confidence = 0.75  # Confianza fija para patrones base
                    if confidence > best_confidence:
                        best_confidence = confidence
                        best_match = intent

        if best_match:
            # Extraer entidades básicas con regex (pasando el intent para contexto)
            entities = self._extract_entities_regex(text, best_match)

            return NLUResult(
                intent=best_match,
                confidence=best_confidence,
                entities=entities,
                source='regex'
            )

        return None

    def _extract_entities_regex(self, text: str, intent: str = None) -> Dict[str, Any]:
        """Extrae entidades usando regex"""
        entities = {}

        # Extraer cantidad
        qty_match = re.search(r'\b(\d+|una?|dos|tres|cuatro|cinco)\b', text)
        if qty_match:
            qty_word = qty_match.group(1)
            qty_map = {'un': 1, 'uno': 1, 'una': 1, 'dos': 2, 'tres': 3, 'cuatro': 4, 'cinco': 5}
            entities['quantity'] = qty_map.get(qty_word, int(qty_word) if qty_word.isdigit() else 1)

        # Extraer categoría (CRÍTICO para view_category)
        category_map = {
            'hamburguesas': 'hamburguesas',
            'hamburguesa': 'hamburguesas',
            'tacos': 'tacos',
            'taco': 'tacos',
            'bebidas': 'bebidas',
            'bebida': 'bebidas',
            'refrescos': 'bebidas',
            'refresco': 'bebidas',
            'postres': 'postres',
            'postre': 'postres',
            'entradas': 'entradas',
            'entrada': 'entradas',
            'ensaladas': 'ensaladas',
            'ensalada': 'ensaladas',
            'complementos': 'complementos',
            'complemento': 'complementos',
            'papas': 'complementos',
            'extras': 'complementos',
            'desayunos': 'desayunos',
            'desayuno': 'desayunos',
            'combos': 'combos',
            'combo': 'combos',
            'promociones': 'promociones',
            'promocion': 'promociones',
        }

        for keyword, category in category_map.items():
            if keyword in text:
                entities['category'] = category
                entities['menu_category'] = category
                break

        # Extraer producto (palabras clave)
        products = ['hamburguesa', 'taco', 'coca', 'agua', 'refresco', 'papas', 'ensalada', 'postre']
        for product in products:
            if product in text:
                entities['product_keyword'] = product
                break

        # Extraer modificadores
        modifiers = []
        if re.search(r'\bsin\s+(\w+)', text):
            modifiers.append(re.search(r'\bsin\s+(\w+)', text).group(0))
        if re.search(r'\bextra\s+(\w+)', text):
            modifiers.append(re.search(r'\bextra\s+(\w+)', text).group(0))
        if re.search(r'\bcon\s+(\w+)', text):
            modifiers.append(re.search(r'\bcon\s+(\w+)', text).group(0))

        if modifiers:
            entities['modifiers'] = modifiers

        return entities

    def _register_successful_classification(self, text: str, result: NLUResult):
        """Registra clasificación exitosa para aprendizaje"""
        if result.source != 'llm' or result.confidence < 0.8:
            return

        with self._lock:
            intent = result.intent

            if intent not in self.learned_intents:
                self.learned_intents[intent] = LearnedIntent(
                    intent=intent,
                    patterns=[],
                    examples=[]
                )

            learned = self.learned_intents[intent]

            # Agregar ejemplo
            if text not in learned.examples:
                learned.examples.append(text)
                logger.debug(f"[HYBRID_NLU] Ejemplo aprendido para '{intent}': {len(learned.examples)} ejemplos")

                # Cada 5 ejemplos, generar nuevo patrón (antes era 10)
                if len(learned.examples) % 5 == 0:
                    self._generate_pattern_from_examples(learned)

            # Guardar frecuentemente - cada 3 nuevos ejemplos o cada nuevo patrón
            total_examples = sum(len(l.examples) for l in self.learned_intents.values())
            if total_examples % 3 == 0 or self.stats['patterns_learned'] > 0:
                self._save_learned_patterns()
                logger.debug(f"[HYBRID_NLU] Patrones guardados ({total_examples} ejemplos, {self.stats['patterns_learned']} patrones)")

    def _generate_pattern_from_examples(self, learned: LearnedIntent):
        """Genera patrón regex a partir de ejemplos (simplificado)"""
        if len(learned.examples) < 5:
            return

        # Encontrar palabras comunes en los ejemplos
        word_counts = {}
        for example in learned.examples[-20:]:
            words = example.lower().split()
            for word in words:
                if len(word) > 2:
                    word_counts[word] = word_counts.get(word, 0) + 1

        # Palabras que aparecen en más del 30% de ejemplos
        threshold = len(learned.examples[-20:]) * 0.3
        common_words = [w for w, c in word_counts.items() if c >= threshold]

        if common_words:
            # Crear patrón simple
            pattern = r'\b(' + '|'.join(re.escape(w) for w in common_words[:5]) + r')\b'

            if pattern not in learned.patterns:
                learned.patterns.append(pattern)
                self.stats['patterns_learned'] += 1
                logger.info(f"[HYBRID_NLU] Nuevo patrón para '{learned.intent}': {pattern[:50]}...")

    def get_stats(self) -> Dict[str, Any]:
        """Retorna estadísticas del clasificador"""
        return {
            **self.stats,
            'connection_status': self.connection_status.value,
            'learned_intents_count': len(self.learned_intents),
            'total_learned_patterns': sum(len(l.patterns) for l in self.learned_intents.values()),
            'llm_available': self.llm_provider.is_available() if self.llm_provider else False
        }

    def force_offline_mode(self):
        """Fuerza modo offline (para testing)"""
        self.connection_status = ConnectionStatus.OFFLINE
        logger.info("[HYBRID_NLU] Modo offline forzado")

    def force_online_mode(self):
        """Fuerza modo online (para testing)"""
        self.connection_status = ConnectionStatus.ONLINE
        self._last_connectivity_check = 0
        logger.info("[HYBRID_NLU] Modo online forzado")

    def export_patterns_for_review(self) -> str:
        """Exporta patrones aprendidos para revisión humana"""
        output = "# Patrones NLU Aprendidos\n"
        output += f"# Generado: {datetime.now().isoformat()}\n\n"

        for intent, learned in self.learned_intents.items():
            output += f"## {intent}\n"
            output += f"- Usos: {learned.times_used}\n"
            output += f"- Success rate: {learned.success_rate:.1%}\n"
            output += f"- Patrones: {len(learned.patterns)}\n"
            output += f"- Ejemplos: {len(learned.examples)}\n\n"

            if learned.patterns:
                output += "Patrones:\n"
                for p in learned.patterns[:5]:
                    output += f"  - {p}\n"

            if learned.examples:
                output += "Últimos ejemplos:\n"
                for e in learned.examples[-5:]:
                    output += f"  - \"{e}\"\n"

            output += "\n"

        return output


# Instancia global (singleton)
_hybrid_nlu: Optional[HybridNLU] = None


def get_hybrid_nlu(llm_provider=None, config: Dict = None, menu: List[Dict] = None) -> HybridNLU:
    """Obtiene la instancia global del HybridNLU"""
    global _hybrid_nlu

    if _hybrid_nlu is None:
        _hybrid_nlu = HybridNLU(llm_provider=llm_provider, config=config, menu=menu)

    return _hybrid_nlu


def init_hybrid_nlu(llm_provider, config: Dict = None, menu: List[Dict] = None) -> HybridNLU:
    """Inicializa el HybridNLU con configuración específica"""
    global _hybrid_nlu
    _hybrid_nlu = HybridNLU(llm_provider=llm_provider, config=config, menu=menu)
    return _hybrid_nlu
