"""
================================================================================
MULTI-ORDER PARSER - PARSING HÍBRIDO DE PEDIDOS COMPLEJOS
================================================================================
Implementa un enfoque híbrido para procesar pedidos:
- Pedidos simples: Regex + Reglas (rápido, gratis)
- Pedidos complejos: LLM (Gemini/Groq/Cerebras) para parsing inteligente

Ejemplo de pedido complejo:
"dame 2 hamburguesas una doble carne, la otra sencilla,
 una orden de tacos, 2 cocas y un agua natural"

→ Se detecta como complejo y se envía a LLM para parsing estructurado.

v3.0 - FALLBACK INTELIGENTE:
- Regex SIEMPRE se ejecuta primero (gratis, rápido)
- Detección de parsing incompleto (referencias anafóricas, items faltantes)
- LLM como fallback SOLO cuando regex falla parcialmente
- Métricas de aprendizaje para mejorar patrones con el tiempo
================================================================================
"""

import re
import json
import logging
import os
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)

# Import del sistema de auto-aprendizaje (lazy para evitar circular imports)
_pattern_learner = None

def _get_pattern_learner():
    """Obtiene el PatternLearner de forma lazy"""
    global _pattern_learner
    if _pattern_learner is None:
        try:
            from .pattern_learner import get_pattern_learner
            _pattern_learner = get_pattern_learner()
        except Exception as e:
            logger.warning(f"[PARSER] PatternLearner no disponible: {e}")
    return _pattern_learner

# Obtener URL del menu-service desde variable de entorno
# Remover /api/v1 si ya está incluido para evitar duplicación
_raw_menu_url = os.getenv("MENU_SERVICE_URL", "http://menu-service:5011")
_MENU_SERVICE_BASE_URL = _raw_menu_url.rstrip("/").removesuffix("/api/v1")


class OrderComplexity(Enum):
    """Nivel de complejidad del pedido"""
    SIMPLE = "simple"           # Un producto, sin modificadores complejos
    MODERATE = "moderate"       # 2-3 productos o modificadores simples
    COMPLEX = "complex"         # Múltiples productos con modificadores


@dataclass
class ParsedOrderItem:
    """Un item parseado del pedido"""
    product_name: str           # Nombre del producto (como está en el menú)
    quantity: int = 1           # Cantidad
    modifiers: List[str] = field(default_factory=list)  # ["sin cebolla", "extra queso"]
    notes: str = ""             # Notas adicionales
    confidence: float = 1.0     # Confianza del parsing
    matched_from: str = ""      # Texto original que generó este item


@dataclass
class MultiOrderParseResult:
    """Resultado del parsing de un pedido múltiple"""
    items: List[ParsedOrderItem]
    complexity: OrderComplexity
    parsing_method: str         # "regex", "llm", o "regex+llm_fallback"
    needs_clarification: bool = False
    clarification_question: Optional[str] = None
    original_text: str = ""
    parse_time_ms: float = 0.0
    used_llm_fallback: bool = False  # v3.0: Indica si se usó LLM como fallback
    fallback_reason: str = ""        # v3.0: Razón del fallback (para métricas)


class MultiOrderParser:
    """
    Parser híbrido para pedidos de restaurante.

    Flujo:
    1. Analiza la complejidad del pedido
    2. Si es simple → usa regex/reglas
    3. Si es complejo → usa Gemini para parsing estructurado

    v2.1: Aliases dinámicos desde la API del menu-service
    """

    # URL base del menu-service (desde variable de entorno)
    MENU_SERVICE_URL = f"{_MENU_SERVICE_BASE_URL}/api/v1"

    def __init__(self, menu: List[Dict] = None, llm_provider=None, config: Dict = None):
        """
        Inicializa el parser.

        Args:
            menu: Lista de productos del menú
            llm_provider: Proveedor LLM (GeminiProvider) para pedidos complejos
            config: Configuración opcional
        """
        self.menu = menu or []
        self.llm_provider = llm_provider
        self.config = config or {}

        # Construir lookup de productos
        self._product_lookup = {}
        self._build_product_lookup()

        # Aliases dinámicos - se cargan desde la API
        self.product_aliases = {}
        self._aliases_loaded = False
        self._load_aliases_from_api()

        # Patrones de cantidad
        self.quantity_words = {
            'un': 1, 'uno': 1, 'una': 1,
            'dos': 2, 'doble': 2,
            'tres': 3, 'triple': 3,
            'cuatro': 4,
            'cinco': 5,
            'seis': 6,
            'media': 1,  # "media orden"
            'orden': 1,
        }

        # Modificadores conocidos
        self.modifier_patterns = {
            'sin': ['cebolla', 'jitomate', 'tomate', 'lechuga', 'crema', 'queso',
                   'cilantro', 'salsa', 'chile', 'picante', 'mayonesa', 'mostaza'],
            'extra': ['queso', 'carne', 'tocino', 'aguacate', 'guacamole',
                     'crema', 'salsa', 'chile', 'jalapeño'],
            'con': ['queso', 'tocino', 'aguacate', 'guacamole', 'crema']
        }

        # Estadísticas v3.0: Métricas extendidas para aprendizaje
        self.stats = {
            'total_parses': 0,
            'regex_parses': 0,
            'llm_parses': 0,
            'llm_fallback_parses': 0,      # v3.0: Veces que LLM rescató a regex
            'successful_parses': 0,
            'failed_parses': 0,
            'partial_parses': 0,           # v3.0: Parsing incompleto detectado
            'fallback_reasons': {}         # v3.0: Conteo por razón de fallback
        }

        # v3.0: Aliases de variantes comunes (no generados del menú)
        # Estos cubren términos coloquiales que no están en nombres de productos
        self._variant_aliases = {
            # Hamburguesas
            'sencilla': 'Hamburguesa Clasica',
            'simple': 'Hamburguesa Clasica',
            'normal': 'Hamburguesa Clasica',
            'basica': 'Hamburguesa Clasica',
            'básica': 'Hamburguesa Clasica',
            'chica': 'Hamburguesa Clasica',
            'grande': 'Hamburguesa Doble',
            # Tacos
            'trompo': 'Tacos al Pastor',
            'adobada': 'Tacos al Pastor',
            'res': 'Tacos de Carne Asada',
            # Bebidas
            'coca': 'Coca-Cola',
            'cocacola': 'Coca-Cola',
            'refresco': 'Coca-Cola',
            'agua': 'Agua Natural',
            'agua simple': 'Agua Natural',
        }

    def _build_product_lookup(self):
        """Construye índice de productos para búsqueda rápida"""
        for product in self.menu:
            name = product.get('name', '').lower()
            self._product_lookup[name] = product

            # También indexar versiones sin acentos
            name_normalized = self._normalize_text(name)
            self._product_lookup[name_normalized] = product

    def _load_aliases_from_api(self):
        """
        Carga aliases dinámicamente desde el menu-service.

        Primero intenta cargar desde la API.
        Si falla, genera aliases de fallback desde el menú local.
        """
        import httpx

        try:
            # Intentar cargar desde API
            with httpx.Client(timeout=5.0) as client:
                response = client.get(f"{self.MENU_SERVICE_URL}/aliases/map")

                if response.status_code == 200:
                    data = response.json()
                    self.product_aliases = data.get('aliases', {})
                    self._aliases_loaded = True
                    logger.info(f"[PARSER] Aliases cargados desde API: {len(self.product_aliases)} aliases")
                    return
                else:
                    logger.warning(f"[PARSER] API de aliases retornó {response.status_code}")

        except Exception as e:
            logger.warning(f"[PARSER] Error cargando aliases desde API: {e}")

        # Fallback: Generar aliases básicos desde el menú local
        self._generate_fallback_aliases()

    def _generate_fallback_aliases(self):
        """
        Genera aliases básicos de fallback cuando la API no está disponible.
        """
        logger.info("[PARSER] Generando aliases de fallback desde menú local")
        self.product_aliases = {}

        for product in self.menu:
            name = product.get('name', '')
            name_lower = name.lower()
            name_normalized = self._normalize_text(name)

            # Alias exacto
            self.product_aliases[name_lower] = name
            self.product_aliases[name_normalized] = name

            # Extraer palabras significativas
            words = name_lower.split()
            stop_words = {'de', 'la', 'el', 'los', 'las', 'con', 'sin', 'y', 'a'}

            for word in words:
                word_clean = self._normalize_text(word)
                if word_clean not in stop_words and len(word_clean) > 2:
                    # Solo agregar si no existe o es más específico
                    if word_clean not in self.product_aliases:
                        self.product_aliases[word_clean] = name

        self._aliases_loaded = True
        logger.info(f"[PARSER] Aliases fallback generados: {len(self.product_aliases)}")

    def reload_aliases(self):
        """Recarga aliases desde la API (para uso externo)"""
        self._load_aliases_from_api()
        return len(self.product_aliases)

    def _normalize_text(self, text: str) -> str:
        """Normaliza texto para comparación"""
        # Quitar acentos
        replacements = {
            'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u',
            'ñ': 'n', 'ü': 'u'
        }
        result = text.lower()
        for accented, plain in replacements.items():
            result = result.replace(accented, plain)
        return result

    def update_menu(self, menu: List[Dict]):
        """Actualiza el menú"""
        self.menu = menu
        self._build_product_lookup()
        logger.info(f"[PARSER] Menú actualizado: {len(menu)} productos")

    def analyze_complexity(self, text: str) -> Tuple[OrderComplexity, List[str]]:
        """
        Analiza la complejidad del pedido.

        Returns:
            Tupla (complejidad, razones)
        """
        text_lower = text.lower()
        reasons = []

        # Indicadores de complejidad
        complexity_score = 0

        # 1. Múltiples números
        numbers = re.findall(r'\b(\d+)\b', text_lower)
        number_words = sum(1 for word in self.quantity_words if re.search(rf'\b{word}\b', text_lower))
        total_quantities = len(numbers) + number_words

        if total_quantities > 2:
            complexity_score += 2
            reasons.append(f"múltiples cantidades ({total_quantities})")
        elif total_quantities > 1:
            complexity_score += 1
            reasons.append(f"{total_quantities} cantidades")

        # 2. Múltiples conectores "y"
        y_count = len(re.findall(r'\by\b', text_lower))
        if y_count >= 2:
            complexity_score += 2
            reasons.append(f"múltiples conectores 'y' ({y_count})")

        # 3. Múltiples comas
        comma_count = text.count(',')
        if comma_count >= 2:
            complexity_score += 1
            reasons.append(f"múltiples comas ({comma_count})")

        # 4. Patrones de diferenciación ("una... la otra", "el primero... el segundo")
        diff_patterns = [
            r'\buna\b.*\b(la )?otra\b',
            r'\buno\b.*\b(el )?otro\b',
            r'\bprimer[oa]?\b.*\bsegund[oa]?\b',
            r'\besta\b.*\besa\b',
        ]
        for pattern in diff_patterns:
            if re.search(pattern, text_lower):
                complexity_score += 2
                reasons.append("diferenciación entre items")
                break

        # 5. Palabras clave de adición
        addition_words = ['también', 'además', 'aparte', 'incluy']
        for word in addition_words:
            if word in text_lower:
                complexity_score += 1
                reasons.append(f"palabra de adición: '{word}'")

        # 6. Longitud del texto
        word_count = len(text.split())
        if word_count > 15:
            complexity_score += 2
            reasons.append(f"texto largo ({word_count} palabras)")
        elif word_count > 10:
            complexity_score += 1
            reasons.append(f"texto moderado ({word_count} palabras)")

        # 7. Múltiples modificadores
        modifier_count = len(re.findall(r'\b(sin|extra|con)\s+\w+', text_lower))
        if modifier_count > 2:
            complexity_score += 1
            reasons.append(f"múltiples modificadores ({modifier_count})")

        # Determinar complejidad
        if complexity_score >= 4:
            return (OrderComplexity.COMPLEX, reasons)
        elif complexity_score >= 2:
            return (OrderComplexity.MODERATE, reasons)
        else:
            return (OrderComplexity.SIMPLE, reasons)

    def parse(self, text: str, table_id: int = None) -> MultiOrderParseResult:
        """
        Parsea un pedido y retorna los items estructurados.

        v3.0 - FLUJO DE PARSING INTELIGENTE:
        1. SIEMPRE ejecutar regex primero (gratis, rápido)
        2. Validar si el parsing fue completo
        3. Si fue incompleto → fallback a LLM
        4. Registrar métricas para aprendizaje

        Args:
            text: Texto del pedido del cliente
            table_id: ID de la mesa (opcional)

        Returns:
            MultiOrderParseResult con los items parseados
        """
        import time
        start_time = time.time()

        self.stats['total_parses'] += 1

        # 1. Analizar complejidad
        complexity, reasons = self.analyze_complexity(text)
        logger.info(f"[PARSER] Complejidad: {complexity.value} | Razones: {reasons}")

        # 2. SIEMPRE intentar regex primero (es gratis y rápido)
        result = self._parse_with_regex(text)
        result.parsing_method = "regex"
        self.stats['regex_parses'] += 1

        # 3. v3.0: Detectar si el parsing fue incompleto
        is_incomplete, fallback_reason = self._is_parsing_incomplete(text, result, reasons)

        if is_incomplete:
            self.stats['partial_parses'] += 1
            logger.info(f"[PARSER] Parsing incompleto detectado: {fallback_reason}")

            # 4. Intentar fallback a LLM si está disponible
            if self.llm_provider and self.llm_provider.is_available():
                logger.info("[PARSER] Activando fallback a LLM...")
                llm_result = self._parse_with_llm(text)

                # Solo usar resultado de LLM si es mejor que regex
                if len(llm_result.items) > len(result.items):
                    # v4.0: Registrar caso para aprendizaje automático
                    self._register_learning_case(
                        original_text=text,
                        llm_items=llm_result.items,
                        regex_items=result.items,
                        fallback_reason=fallback_reason
                    )

                    result = llm_result
                    result.parsing_method = "regex+llm_fallback"
                    result.used_llm_fallback = True
                    result.fallback_reason = fallback_reason
                    self.stats['llm_fallback_parses'] += 1

                    # Registrar razón para aprendizaje
                    self.stats['fallback_reasons'][fallback_reason] = \
                        self.stats['fallback_reasons'].get(fallback_reason, 0) + 1

                    logger.info(f"[PARSER] LLM fallback exitoso: {len(result.items)} items (vs {len(llm_result.items)} de regex)")
                else:
                    logger.info(f"[PARSER] LLM no mejoró resultado, manteniendo regex")
            else:
                logger.warning("[PARSER] LLM no disponible para fallback")

        # 5. Solo para pedidos MUY complejos, ir directo a LLM
        elif complexity == OrderComplexity.COMPLEX and self.llm_provider and self.llm_provider.is_available():
            # Pedido muy complejo, usar LLM directamente
            result = self._parse_with_llm(text)
            result.parsing_method = "llm"
            self.stats['llm_parses'] += 1

        result.complexity = complexity
        result.original_text = text
        result.parse_time_ms = (time.time() - start_time) * 1000

        if result.items:
            self.stats['successful_parses'] += 1
        else:
            self.stats['failed_parses'] += 1

        logger.info(f"[PARSER] Resultado: {len(result.items)} items en {result.parse_time_ms:.0f}ms ({result.parsing_method})")

        return result

    def _is_parsing_incomplete(
        self,
        text: str,
        result: MultiOrderParseResult,
        complexity_reasons: List[str]
    ) -> Tuple[bool, str]:
        """
        v3.0: Detecta si el parsing regex fue incompleto y necesita ayuda de LLM.

        Casos de parsing incompleto:
        1. Detectamos diferenciación ("una X y otra Y") pero solo encontramos 1 item
        2. Detectamos N cantidades pero encontramos menos de N items
        3. Hay referencias anafóricas sin resolver ("otra", "el otro")
        4. Hay segmentos que no produjeron ningún producto

        Returns:
            Tuple (is_incomplete: bool, reason: str)
        """
        text_lower = text.lower()

        # Caso 1: Diferenciación detectada pero items insuficientes
        if 'diferenciación entre items' in complexity_reasons:
            if len(result.items) < 2:
                return True, "diferenciacion_un_item"

        # Caso 2: Múltiples cantidades pero pocos items
        for reason in complexity_reasons:
            if 'cantidades' in reason:
                # Extraer número esperado: "2 cantidades" → 2
                match = re.search(r'(\d+)\s+cantidades', reason)
                if match:
                    expected = int(match.group(1))
                    if len(result.items) < expected:
                        return True, f"cantidades_esperadas_{expected}_encontradas_{len(result.items)}"

        # Caso 3: Referencias anafóricas sin resolver
        anaphoric_patterns = [
            (r'\botra\s+(\w+)', 'otra'),      # "otra sencilla"
            (r'\botro\s+(\w+)', 'otro'),      # "otro doble"
            (r'\bla\s+otra\b', 'la_otra'),    # "la otra"
            (r'\bel\s+otro\b', 'el_otro'),    # "el otro"
        ]

        for pattern, ref_type in anaphoric_patterns:
            match = re.search(pattern, text_lower)
            if match:
                # Verificar si algún item tiene esta referencia resuelta
                ref_text = match.group(0)
                item_resolved = any(
                    ref_text in (item.matched_from or '').lower()
                    for item in result.items
                )
                if not item_resolved:
                    # Verificar si la palabra después de "otra/otro" es una variante conocida
                    if len(match.groups()) > 0:
                        variant = match.group(1) if match.lastindex else ''
                        if variant in self._variant_aliases or variant in self._resolve_product_variant('hamburguesa', variant) or '':
                            return True, f"referencia_anaforica_{ref_type}"

        # Caso 4: Segmentos sin producto (split produjo fragmentos huérfanos)
        segments = self._split_into_segments(text_lower)
        unmatched_segments = []

        for segment in segments:
            segment = segment.strip()
            if len(segment) < 3:
                continue

            # Verificar si este segmento produjo algún item
            segment_matched = any(
                segment in (item.matched_from or '').lower() or
                (item.matched_from or '').lower() in segment
                for item in result.items
            )

            if not segment_matched:
                # Verificar si el segmento tiene palabras de variante
                has_variant_word = any(
                    variant in segment
                    for variant in self._variant_aliases.keys()
                )
                if has_variant_word:
                    unmatched_segments.append(segment)

        if unmatched_segments:
            return True, f"segmentos_huerfanos_{len(unmatched_segments)}"

        return False, ""

    def _parse_with_learned_patterns(self, text: str) -> List[ParsedOrderItem]:
        """
        v4.0: Intenta parsear usando patrones aprendidos automáticamente.

        Los patrones aprendidos son generados por el PatternLearner cuando
        detecta casos donde regex falló y LLM tuvo éxito.

        Returns:
            Lista de items parseados, vacía si no hay matches
        """
        items = []
        learned_patterns = self._get_learned_patterns()

        if not learned_patterns:
            return items

        for pattern_info in learned_patterns:
            try:
                pattern = pattern_info.get('pattern', '')
                category = pattern_info.get('category', 'general')

                if not pattern:
                    continue

                compiled = re.compile(pattern, re.IGNORECASE)
                match = compiled.search(text)

                if match:
                    groups = match.groups()

                    # Interpretar grupos según categoría
                    if category == 'differentiation' and len(groups) >= 2:
                        # Patrón de diferenciación: producto1, producto2
                        for i, group in enumerate(groups):
                            if group:
                                product = self._find_product_in_segment(group)
                                if product:
                                    items.append(ParsedOrderItem(
                                        product_name=product,
                                        quantity=1,
                                        confidence=0.85,
                                        matched_from=f"learned_pattern:{pattern_info.get('description', 'auto')}"
                                    ))

                    elif category == 'quantity' and len(groups) >= 2:
                        # Patrón de cantidad: cantidad, producto
                        qty = self._word_to_number(groups[0]) if groups[0] else 1
                        product = self._find_product_in_segment(groups[1]) if len(groups) > 1 else None

                        if product:
                            items.append(ParsedOrderItem(
                                product_name=product,
                                quantity=qty,
                                confidence=0.85,
                                matched_from=f"learned_pattern:{pattern_info.get('description', 'auto')}"
                            ))

                    else:
                        # Patrón general: intentar extraer producto de cualquier grupo
                        for group in groups:
                            if group:
                                product = self._find_product_in_segment(group)
                                if product:
                                    items.append(ParsedOrderItem(
                                        product_name=product,
                                        quantity=1,
                                        confidence=0.80,
                                        matched_from=f"learned_pattern:{pattern_info.get('description', 'auto')}"
                                    ))
                                    break  # Solo un producto por patrón general

                    if items:
                        logger.info(f"[PARSER] Patrón aprendido '{pattern[:30]}...' encontró {len(items)} items")

            except re.error as e:
                logger.warning(f"[PARSER] Patrón aprendido inválido: {e}")
                continue
            except Exception as e:
                logger.error(f"[PARSER] Error aplicando patrón aprendido: {e}")
                continue

        return items

    def _parse_with_regex(self, text: str) -> MultiOrderParseResult:
        """
        Parsea el pedido usando regex y reglas MEJORADO v4.0.

        Optimizado para funcionar OFFLINE con pedidos complejos.
        Maneja casos como: "2 hamburguesas una doble, la otra sencilla"

        v4.0: Incluye patrones aprendidos automáticamente
        """
        items = []
        text_lower = text.lower()
        needs_clarification = False
        clarification_question = None

        # === FASE 0 (v4.0): Intentar con patrones aprendidos ===
        learned_items = self._parse_with_learned_patterns(text_lower)
        if learned_items:
            logger.info(f"[PARSER] Patrones aprendidos encontraron {len(learned_items)} items")
            items.extend(learned_items)

        # === FASE 1: Detectar patrones especiales de diferenciación ===
        # "2 hamburguesas una doble, la otra sencilla"
        # Solo si FASE 0 no encontró nada
        if not items:
            diff_items = self._parse_differentiated_items(text_lower)
            if diff_items:
                items.extend(diff_items)

        # === FASE 2: Parsing estándar por segmentos ===
        # Solo ejecutar si FASE 1 no encontró nada
        # v3.0: Si ya encontramos items en diferenciación, no procesar segmentos
        # para evitar duplicados
        if not items:
            segments = self._split_into_segments(text_lower)

            for segment in segments:
                segment = segment.strip()
                if not segment or len(segment) < 3:
                    continue

                # Verificar si este segmento ya fue procesado
                already_processed = any(
                    item.matched_from and (
                        segment in item.matched_from or
                        item.matched_from in segment
                    )
                    for item in items
                )
                if already_processed:
                    continue

                # Extraer cantidad
                quantity = self._extract_quantity(segment)

                # Extraer producto
                product_name = self._find_product_in_segment(segment)

                if product_name:
                    # Extraer modificadores
                    modifiers = self._extract_modifiers(segment)

                    item = ParsedOrderItem(
                        product_name=product_name,
                        quantity=quantity,
                        modifiers=modifiers,
                        confidence=0.9 if product_name in [p.get('name') for p in self.menu] else 0.7,
                        matched_from=segment
                    )
                    items.append(item)

        # === FASE 3: Modo guiado si no parseamos bien offline ===
        # Si el texto es complejo pero no encontramos suficientes items
        complexity, _ = self.analyze_complexity(text)
        if complexity == OrderComplexity.COMPLEX and len(items) < 2:
            needs_clarification = True
            clarification_question = self._generate_guided_question(text_lower, items)

        return MultiOrderParseResult(
            items=items,
            complexity=OrderComplexity.SIMPLE,
            parsing_method="regex",
            needs_clarification=needs_clarification,
            clarification_question=clarification_question
        )

    def _parse_differentiated_items(self, text: str) -> List[ParsedOrderItem]:
        """
        Parsea patrones de diferenciación entre items del mismo tipo.

        v3.0 - Patrones mejorados:
        - "2 hamburguesas una doble, la otra sencilla"
        - "2 hamburguesas una doble carne y una clasica"
        - "3 tacos, 2 de pastor y uno de asada"
        - "dame 2 cocas y un agua"
        - "una hamburguesa doble y otra sencilla"  ← NUEVO v3.0
        - "una coca y otra de naranja"             ← NUEVO v3.0
        """
        items = []

        # === PATRÓN 0 (NUEVO v3.0): "una [producto] [variante1] y otra [variante2]" ===
        # Este patrón captura el caso más común en español mexicano
        # Ejemplo: "una hamburguesa doble y otra sencilla"
        pattern_una_y_otra = r'(?:dame\s+|quiero\s+|te\s+encargo\s+|ponme\s+)?una\s+(hamburguesas?|tacos?|ordenes?|cocas?|refrescos?|aguas?|pizzas?)\s+(\w+)\s+y\s+otra\s+(\w+)'

        match = re.search(pattern_una_y_otra, text)
        if match:
            base_product = match.group(1)
            variant1 = match.group(2)
            variant2 = match.group(3)

            logger.info(f"[PARSER] Patrón 'una X y otra Y' detectado: {base_product} -> {variant1}, {variant2}")

            # Mapear variantes a productos específicos
            product1 = self._resolve_product_variant(base_product, variant1)
            product2 = self._resolve_product_variant(base_product, variant2)

            if product1:
                items.append(ParsedOrderItem(
                    product_name=product1,
                    quantity=1,
                    modifiers=self._extract_modifiers(variant1),
                    confidence=0.90,
                    matched_from=f"una {base_product} {variant1}"
                ))

            if product2:
                items.append(ParsedOrderItem(
                    product_name=product2,
                    quantity=1,
                    modifiers=self._extract_modifiers(variant2),
                    confidence=0.90,
                    matched_from=f"otra {variant2}"
                ))

            if items:
                return items

        # === PATRÓN 0b (NUEVO v3.0): "una [variante1] y otra [variante2]" (sin producto explícito) ===
        # Ejemplo: "una doble y otra sencilla" (contexto implícito de hamburguesa)
        pattern_variantes_solas = r'(?:dame\s+|quiero\s+|te\s+encargo\s+|ponme\s+)?una\s+(doble|sencilla|simple|clasica|clásica|normal|grande|chica)\s+y\s+otra\s+(doble|sencilla|simple|clasica|clásica|normal|grande|chica)'

        match = re.search(pattern_variantes_solas, text)
        if match:
            variant1 = match.group(1)
            variant2 = match.group(2)

            # Detectar contexto del producto
            context = self._detect_product_context(text)
            if context == 'general':
                context = 'hamburguesa'  # Default para variantes como doble/sencilla

            logger.info(f"[PARSER] Patrón variantes implícitas: contexto={context} -> {variant1}, {variant2}")

            product1 = self._resolve_product_variant(context, variant1)
            product2 = self._resolve_product_variant(context, variant2)

            if product1:
                items.append(ParsedOrderItem(
                    product_name=product1,
                    quantity=1,
                    confidence=0.85,
                    matched_from=f"una {variant1}"
                ))

            if product2:
                items.append(ParsedOrderItem(
                    product_name=product2,
                    quantity=1,
                    confidence=0.85,
                    matched_from=f"otra {variant2}"
                ))

            if items:
                return items

        # Patrón 1: "N producto una/uno X, la otra/el otro Y"
        diff_pattern = r'(\d+|dos|tres|cuatro)\s+(hamburguesas?|tacos?|ordenes?|refrescos?|cocas?|aguas?)\s+(?:una?|uno)\s+(\w+(?:\s+\w+)?)[,\s]+(?:la otra|el otro|otra?)\s+(\w+(?:\s+\w+)?)'

        match = re.search(diff_pattern, text)
        if match:
            total_qty = self._word_to_number(match.group(1))
            base_product = match.group(2)
            variant1 = match.group(3)
            variant2 = match.group(4)

            # Mapear variantes a productos específicos
            product1 = self._resolve_product_variant(base_product, variant1)
            product2 = self._resolve_product_variant(base_product, variant2)

            if product1:
                items.append(ParsedOrderItem(
                    product_name=product1,
                    quantity=1,
                    modifiers=self._extract_modifiers(variant1),
                    confidence=0.85,
                    matched_from=f"{base_product} {variant1}"
                ))

            if product2:
                qty2 = max(1, total_qty - 1) if total_qty > 1 else 1
                items.append(ParsedOrderItem(
                    product_name=product2,
                    quantity=qty2,
                    modifiers=self._extract_modifiers(variant2),
                    confidence=0.85,
                    matched_from=f"{base_product} {variant2}"
                ))

            return items

        # Patrón 2: "N producto una/uno X y una/uno Y" (variante con "y una" en lugar de "la otra")
        diff_pattern2 = r'(\d+|dos|tres|cuatro)\s+(hamburguesas?|tacos?|ordenes?)\s+(?:una?|uno)\s+(\w+(?:\s+\w+)?)\s+y\s+(?:una?|uno)\s+(\w+(?:\s+\w+)?)'

        match = re.search(diff_pattern2, text)
        if match:
            total_qty = self._word_to_number(match.group(1))
            base_product = match.group(2)
            variant1 = match.group(3)
            variant2 = match.group(4)

            # Mapear variantes a productos específicos
            product1 = self._resolve_product_variant(base_product, variant1)
            product2 = self._resolve_product_variant(base_product, variant2)

            if product1:
                items.append(ParsedOrderItem(
                    product_name=product1,
                    quantity=1,
                    modifiers=self._extract_modifiers(variant1),
                    confidence=0.85,
                    matched_from=f"{base_product} {variant1}"
                ))

            if product2:
                qty2 = max(1, total_qty - 1) if total_qty > 1 else 1
                items.append(ParsedOrderItem(
                    product_name=product2,
                    quantity=qty2,
                    modifiers=self._extract_modifiers(variant2),
                    confidence=0.85,
                    matched_from=f"{base_product} {variant2}"
                ))

            return items

        # Patrón 3: "N de X y M de Y" (para tacos especialmente)
        split_pattern = r'(\d+|una?|dos|tres)\s+(?:de\s+)?(\w+)\s+y\s+(\d+|una?|dos|tres)\s+(?:de\s+)?(\w+)'

        match = re.search(split_pattern, text)
        if match:
            qty1 = self._word_to_number(match.group(1))
            type1 = match.group(2)
            qty2 = self._word_to_number(match.group(3))
            type2 = match.group(4)

            # Detectar contexto (tacos, bebidas, etc.)
            context = self._detect_product_context(text)

            product1 = self._resolve_product_variant(context, type1)
            product2 = self._resolve_product_variant(context, type2)

            if product1:
                items.append(ParsedOrderItem(
                    product_name=product1,
                    quantity=qty1,
                    confidence=0.8,
                    matched_from=f"{qty1} de {type1}"
                ))

            if product2:
                items.append(ParsedOrderItem(
                    product_name=product2,
                    quantity=qty2,
                    confidence=0.8,
                    matched_from=f"{qty2} de {type2}"
                ))

        return items

    def _resolve_product_variant(self, base_product: str, variant: str) -> Optional[str]:
        """
        Resuelve una variante de producto al nombre real del menú.

        Ej: base="hamburguesa", variant="doble" → "Hamburguesa Doble"
        """
        base_lower = base_product.lower().rstrip('s')  # quitar plural
        variant_lower = variant.lower()

        # Mapeo de variantes para hamburguesas
        hamburger_variants = {
            'doble': 'Hamburguesa Doble',
            'doble carne': 'Hamburguesa Doble',
            'sencilla': 'Hamburguesa Clasica',
            'simple': 'Hamburguesa Clasica',
            'clasica': 'Hamburguesa Clasica',
            'clásica': 'Hamburguesa Clasica',
            'normal': 'Hamburguesa Clasica',
            'tocino': 'Hamburguesa Tocino',
            'bacon': 'Hamburguesa Tocino',
            'mexicana': 'Hamburguesa Mexicana',
            'bbq': 'Hamburguesa BBQ',
            'vegetariana': 'Hamburguesa Vegetariana',
        }

        # Mapeo de variantes para tacos
        taco_variants = {
            'pastor': 'Tacos al Pastor',
            'al pastor': 'Tacos al Pastor',
            'asada': 'Tacos de Carne Asada',
            'carne asada': 'Tacos de Carne Asada',
            'birria': 'Tacos de Birria',
            'carnitas': 'Tacos de Carnitas',
            'suadero': 'Tacos de Suadero',
            'chorizo': 'Tacos de Chorizo',
            'campechano': 'Tacos Campechanos',
            'campechanos': 'Tacos Campechanos',
        }

        # Mapeo de variantes para bebidas
        drink_variants = {
            'coca': 'Coca-Cola',
            'sprite': 'Sprite',
            'fanta': 'Fanta',
            'natural': 'Agua Natural',
            'agua natural': 'Agua Natural',
            'mineral': 'Agua Mineral',
            'horchata': 'Agua de Horchata',
            'jamaica': 'Agua de Jamaica',
        }

        # Seleccionar mapeo según base
        if 'hamburguesa' in base_lower or 'burger' in base_lower:
            return hamburger_variants.get(variant_lower)
        elif 'taco' in base_lower:
            return taco_variants.get(variant_lower)
        elif any(b in base_lower for b in ['refresco', 'coca', 'agua', 'bebida']):
            return drink_variants.get(variant_lower)

        # Fallback: buscar en aliases generales
        return self.product_aliases.get(variant_lower)

    def _detect_product_context(self, text: str) -> str:
        """Detecta el contexto/categoría del producto mencionado"""
        text_lower = text.lower()

        if any(w in text_lower for w in ['taco', 'pastor', 'asada', 'birria', 'carnitas']):
            return 'taco'
        elif any(w in text_lower for w in ['hamburguesa', 'burger', 'doble', 'sencilla']):
            return 'hamburguesa'
        elif any(w in text_lower for w in ['coca', 'refresco', 'agua', 'bebida', 'sprite']):
            return 'bebida'

        return 'general'

    def _word_to_number(self, word: str) -> int:
        """Convierte palabra o número string a int"""
        if word.isdigit():
            return int(word)
        return self.quantity_words.get(word.lower(), 1)

    def _generate_guided_question(self, text: str, partial_items: List[ParsedOrderItem]) -> str:
        """
        Genera una pregunta guiada cuando no podemos parsear completamente offline.

        En lugar de fallar, guiamos al cliente paso a paso.
        """
        # Si encontramos algunos items, confirmarlos y preguntar por el resto
        if partial_items:
            found_text = ", ".join([
                f"{item.quantity}x {item.product_name}"
                for item in partial_items
            ])
            return f"Entendí: {found_text}. ¿Qué más te agrego?"

        # Si detectamos categoría pero no producto específico
        context = self._detect_product_context(text)

        if context == 'hamburguesa':
            return "¿Qué tipo de hamburguesa te preparo? Tenemos clásica, doble, con tocino, mexicana y BBQ."
        elif context == 'taco':
            return "¿De qué van a ser los tacos? Tenemos pastor, asada, birria, carnitas y más."
        elif context == 'bebida':
            return "¿Qué te sirvo de tomar? Tenemos refrescos, aguas frescas y café."

        # Pregunta genérica
        return "Disculpa, no capté bien. ¿Me puedes decir uno por uno qué te sirvo?"

    def _split_into_segments(self, text: str) -> List[str]:
        """Divide el texto en segmentos por producto"""
        # Primero, reemplazar conectores con un delimitador especial
        delimiters = [' y ', ', ', ' también ', ' además ', ' aparte ']

        result = text
        for delim in delimiters:
            result = result.replace(delim, '|||')

        segments = result.split('|||')
        return [s.strip() for s in segments if s.strip()]

    def _extract_quantity(self, text: str) -> int:
        """Extrae la cantidad de un segmento de texto"""
        text_lower = text.lower()

        # Buscar números primero
        match = re.search(r'\b(\d+)\b', text_lower)
        if match:
            return int(match.group(1))

        # Buscar palabras de cantidad
        for word, num in self.quantity_words.items():
            if re.search(rf'\b{word}\b', text_lower):
                return num

        return 1  # Default

    def _find_product_in_segment(self, segment: str) -> Optional[str]:
        """
        Encuentra el producto en un segmento de texto.

        v3.0: Mejorado para buscar también en aliases de variantes coloquiales.
        """
        segment_lower = segment.lower()
        segment_normalized = self._normalize_text(segment)

        # 0. v3.0: Buscar primero en aliases de variantes (términos coloquiales)
        # Esto permite resolver "sencilla" → "Hamburguesa Clasica" aunque
        # el segmento sea solo "otra sencilla" sin contexto de producto
        for variant, product_name in self._variant_aliases.items():
            if variant in segment_lower:
                logger.info(f"[PARSER] Variante encontrada: '{variant}' → {product_name}")
                return product_name

        # 1. Buscar en aliases del menú (del más específico al menos)
        # Ordenar aliases por longitud descendente para matchear frases más largas primero
        sorted_aliases = sorted(self.product_aliases.items(), key=lambda x: len(x[0]), reverse=True)

        for alias, product_name in sorted_aliases:
            if alias in segment_lower or alias in segment_normalized:
                return product_name

        # 2. Buscar coincidencia directa en menú
        for product in self.menu:
            product_name = product.get('name', '').lower()
            if product_name in segment_lower:
                return product.get('name')

        # 3. Buscar coincidencia parcial
        for product in self.menu:
            product_name = product.get('name', '').lower()
            # Buscar palabras clave del producto
            keywords = product_name.split()
            for keyword in keywords:
                if len(keyword) > 3 and keyword in segment_lower:
                    return product.get('name')

        return None

    def _extract_modifiers(self, text: str) -> List[str]:
        """Extrae modificadores del texto"""
        modifiers = []
        text_lower = text.lower()

        # Patrones de modificadores
        patterns = [
            (r'sin\s+(\w+)', 'sin'),
            (r'extra\s+(\w+)', 'extra'),
            (r'con\s+(\w+)', 'con'),
            (r'doble\s+(\w+)', 'doble'),
        ]

        for pattern, prefix in patterns:
            matches = re.findall(pattern, text_lower)
            for match in matches:
                # Verificar que es un ingrediente válido
                if match in self.modifier_patterns.get(prefix, []) or prefix == 'sin':
                    modifiers.append(f"{prefix} {match}")

        return modifiers

    def _parse_with_llm(self, text: str) -> MultiOrderParseResult:
        """
        Parsea el pedido usando Gemini (para pedidos complejos).
        """
        if not self.llm_provider or not self.llm_provider.is_available():
            logger.warning("[PARSER] LLM no disponible, fallback a regex")
            return self._parse_with_regex(text)

        try:
            # Construir lista de productos del menú
            menu_list = "\n".join([
                f"- {p.get('name')} (${p.get('price', 0)})"
                for p in self.menu[:50]  # Limitar para no exceder contexto
            ])

            # Prompt para parsing estructurado
            prompt = f"""Eres un parser de pedidos de restaurante mexicano.
Tu tarea es extraer los productos del pedido del cliente.

MENÚ DISPONIBLE:
{menu_list}

PEDIDO DEL CLIENTE:
"{text}"

INSTRUCCIONES:
1. Identifica TODOS los productos mencionados
2. Extrae la cantidad de cada uno (default 1)
3. Extrae modificadores (sin cebolla, extra queso, etc.)
4. Usa los nombres EXACTOS del menú cuando sea posible
5. Si dicen "sencilla" o "simple" para hamburguesa, usa "Hamburguesa Clasica"
6. Si dicen "doble" para hamburguesa, usa "Hamburguesa Doble"
7. Si dicen "tacos" sin especificar, usa "Tacos al Pastor"
8. Si dicen "coca" o "refresco", usa "Coca-Cola"
9. Si dicen "agua natural" o solo "agua", usa "Agua Natural"

Responde ÚNICAMENTE con JSON válido, sin explicaciones ni markdown:
{{"items": [{{"product": "nombre exacto", "quantity": 1, "modifiers": ["sin cebolla"]}}, ...], "needs_clarification": false, "clarification_question": null}}

Si algo no está claro y necesitas preguntar, pon needs_clarification=true y escribe la pregunta en clarification_question."""

            # Llamar a Gemini
            response = self.llm_provider.generate(
                prompt=prompt,
                messages=[],
                temperature=0.1,  # Baja temperatura para respuestas consistentes
                max_tokens=500
            )

            response_text = response.get('response_text', '')

            # Limpiar respuesta (quitar markdown si existe)
            response_text = response_text.strip()
            if response_text.startswith('```'):
                response_text = re.sub(r'^```\w*\n?', '', response_text)
                response_text = re.sub(r'\n?```$', '', response_text)

            # Parsear JSON
            try:
                parsed = json.loads(response_text)
            except json.JSONDecodeError as e:
                logger.error(f"[PARSER] Error parseando JSON de Gemini: {e}")
                logger.error(f"[PARSER] Respuesta recibida: {response_text[:500]}")
                return self._parse_with_regex(text)

            # Construir items
            items = []
            for item_data in parsed.get('items', []):
                # Validar y normalizar nombre del producto
                product_name = item_data.get('product', '')

                # Intentar encontrar coincidencia en el menú
                matched_product = self._match_product_to_menu(product_name)

                item = ParsedOrderItem(
                    product_name=matched_product or product_name,
                    quantity=item_data.get('quantity', 1),
                    modifiers=item_data.get('modifiers', []),
                    confidence=0.95 if matched_product else 0.7,
                    matched_from=text
                )
                items.append(item)

            logger.info(f"[PARSER] Gemini parseó {len(items)} items")

            return MultiOrderParseResult(
                items=items,
                complexity=OrderComplexity.COMPLEX,
                parsing_method="llm",
                needs_clarification=parsed.get('needs_clarification', False),
                clarification_question=parsed.get('clarification_question')
            )

        except Exception as e:
            logger.error(f"[PARSER] Error en parsing LLM: {e}", exc_info=True)
            return self._parse_with_regex(text)

    def _register_learning_case(
        self,
        original_text: str,
        llm_items: List[ParsedOrderItem],
        regex_items: List[ParsedOrderItem],
        fallback_reason: str
    ):
        """
        v4.0: Registra un caso para el sistema de auto-aprendizaje.

        Este método se llama cuando LLM tuvo que rescatar un parsing incompleto de regex.
        El PatternLearner usará estos casos para generar nuevos patrones automáticamente.
        """
        learner = _get_pattern_learner()
        if not learner:
            logger.debug("[PARSER] PatternLearner no disponible, caso no registrado")
            return

        try:
            # Convertir ParsedOrderItem a dicts
            llm_dicts = [
                {
                    'product': item.product_name,
                    'quantity': item.quantity,
                    'modifiers': item.modifiers
                }
                for item in llm_items
            ]

            regex_dicts = [
                {
                    'product': item.product_name,
                    'quantity': item.quantity,
                    'modifiers': item.modifiers
                }
                for item in regex_items
            ]

            learner.register_failed_case(
                original_text=original_text,
                llm_items=llm_dicts,
                regex_items=regex_dicts,
                fallback_reason=fallback_reason
            )

            logger.info(f"[PARSER] Caso registrado para aprendizaje: {fallback_reason}")

        except Exception as e:
            logger.error(f"[PARSER] Error registrando caso para aprendizaje: {e}")

    def _get_learned_patterns(self) -> List[Dict]:
        """
        v4.0: Obtiene patrones aprendidos del PatternLearner.

        Returns:
            Lista de patrones con 'pattern', 'category', 'description'
        """
        learner = _get_pattern_learner()
        if not learner:
            return []

        try:
            return learner.get_learned_patterns()
        except Exception as e:
            logger.error(f"[PARSER] Error obteniendo patrones aprendidos: {e}")
            return []

    def _match_product_to_menu(self, product_name: str) -> Optional[str]:
        """Intenta hacer match del nombre del producto con el menú real"""
        if not product_name:
            return None

        product_lower = product_name.lower()
        product_normalized = self._normalize_text(product_name)

        # Match exacto
        for product in self.menu:
            menu_name = product.get('name', '')
            if menu_name.lower() == product_lower:
                return menu_name

        # Match normalizado
        for product in self.menu:
            menu_name = product.get('name', '')
            if self._normalize_text(menu_name) == product_normalized:
                return menu_name

        # Match parcial (contiene)
        for product in self.menu:
            menu_name = product.get('name', '')
            menu_lower = menu_name.lower()
            if product_lower in menu_lower or menu_lower in product_lower:
                return menu_name

        # Usar alias
        if product_lower in self.product_aliases:
            return self.product_aliases[product_lower]

        return None

    def get_stats(self) -> Dict:
        """
        Retorna estadísticas del parser.

        v4.0: Incluye métricas de fallback y aprendizaje automático.
        """
        # Calcular tasas
        total = self.stats['total_parses'] or 1
        fallback_rate = (self.stats['llm_fallback_parses'] / total) * 100
        partial_rate = (self.stats['partial_parses'] / total) * 100

        # v4.0: Obtener stats del PatternLearner
        learner_stats = {}
        learner = _get_pattern_learner()
        if learner:
            try:
                learner_stats = learner.get_learning_stats()
            except Exception as e:
                logger.warning(f"[PARSER] Error obteniendo stats de learner: {e}")

        return {
            **self.stats,
            'llm_available': self.llm_provider.is_available() if self.llm_provider else False,
            'menu_products': len(self.menu),
            'variant_aliases_count': len(self._variant_aliases),
            # v3.0: Métricas de rendimiento
            'fallback_rate_percent': round(fallback_rate, 2),
            'partial_parse_rate_percent': round(partial_rate, 2),
            # v3.0: Top razones de fallback (para optimización)
            'top_fallback_reasons': sorted(
                self.stats['fallback_reasons'].items(),
                key=lambda x: x[1],
                reverse=True
            )[:5],
            # v4.0: Métricas de auto-aprendizaje
            'auto_learning': {
                'enabled': learner is not None,
                'pending_cases': learner_stats.get('pending_cases', 0),
                'learned_patterns': learner_stats.get('learned_patterns', 0),
                'last_analysis': learner_stats.get('last_analysis'),
                'next_analysis': learner_stats.get('next_analysis')
            }
        }

    def get_learning_report(self) -> Dict:
        """
        v3.0: Genera un reporte de aprendizaje para optimización del parser.

        Útil para:
        - Identificar patrones que fallan frecuentemente
        - Decidir qué nuevos patrones regex agregar
        - Evaluar si el LLM está siendo usado eficientemente
        """
        stats = self.get_stats()

        report = {
            'summary': {
                'total_parses': stats['total_parses'],
                'regex_only': stats['regex_parses'] - stats['llm_fallback_parses'],
                'llm_direct': stats['llm_parses'],
                'llm_fallback': stats['llm_fallback_parses'],
                'success_rate': round((stats['successful_parses'] / max(stats['total_parses'], 1)) * 100, 2)
            },
            'efficiency': {
                'regex_coverage': round(((stats['regex_parses'] - stats['llm_fallback_parses']) / max(stats['total_parses'], 1)) * 100, 2),
                'llm_usage': round(((stats['llm_parses'] + stats['llm_fallback_parses']) / max(stats['total_parses'], 1)) * 100, 2)
            },
            'optimization_opportunities': [],
            'fallback_analysis': stats['fallback_reasons']
        }

        # Identificar oportunidades de optimización
        if stats['fallback_rate_percent'] > 10:
            report['optimization_opportunities'].append(
                f"Alto uso de LLM fallback ({stats['fallback_rate_percent']}%). "
                "Considerar agregar más patrones regex."
            )

        for reason, count in stats['top_fallback_reasons']:
            if count > 5:
                report['optimization_opportunities'].append(
                    f"Patrón frecuente: '{reason}' ({count} veces). "
                    "Candidato para nuevo regex."
                )

        return report


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def create_multi_order_parser(menu: List[Dict] = None, llm_provider=None) -> MultiOrderParser:
    """Factory function para crear el parser"""
    return MultiOrderParser(menu=menu, llm_provider=llm_provider)
