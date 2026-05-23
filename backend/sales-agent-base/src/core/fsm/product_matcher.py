# ============================================================
# PRODUCT MATCHER - FSM v2.0
# ============================================================
# Detección inteligente de productos mencionados
# Usa fuzzy matching, análisis fonético y cache LRU
#
# OPTIMIZACIONES v2.0:
# - Cache LRU para búsquedas repetidas (~3x más rápido)
# - Índice por categoría para búsquedas focalizadas
# - Método unificado find_product_unified() que reemplaza
#   la función duplicada en DecisionTree
# ============================================================

import re
import logging
import hashlib
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from functools import lru_cache
from collections import OrderedDict
import unicodedata

logger = logging.getLogger(__name__)


# ============================================================
# CACHE LRU PERSONALIZADO (con TTL)
# ============================================================

class LRUCacheWithTTL:
    """
    Cache LRU con tiempo de expiración.
    Más eficiente que @lru_cache para objetos Dict.
    """

    def __init__(self, max_size: int = 100, ttl_seconds: int = 300):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: OrderedDict = OrderedDict()
        self._timestamps: Dict[str, float] = {}
        self._hits = 0
        self._misses = 0

    def _generate_key(self, *args, **kwargs) -> str:
        """Genera key única para los argumentos"""
        key_data = str(args) + str(sorted(kwargs.items()))
        return hashlib.md5(key_data.encode()).hexdigest()

    def get(self, key: str) -> Optional[any]:
        """Obtiene valor del cache si existe y no expiró"""
        if key not in self._cache:
            self._misses += 1
            return None

        # Verificar TTL
        if time.time() - self._timestamps[key] > self.ttl_seconds:
            del self._cache[key]
            del self._timestamps[key]
            self._misses += 1
            return None

        # Mover al final (más reciente)
        self._cache.move_to_end(key)
        self._hits += 1
        return self._cache[key]

    def set(self, key: str, value: any):
        """Guarda valor en cache"""
        if key in self._cache:
            self._cache.move_to_end(key)
        else:
            if len(self._cache) >= self.max_size:
                # Eliminar el más antiguo
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
                del self._timestamps[oldest_key]

        self._cache[key] = value
        self._timestamps[key] = time.time()

    def clear(self):
        """Limpia todo el cache"""
        self._cache.clear()
        self._timestamps.clear()

    def stats(self) -> Dict:
        """Retorna estadísticas del cache"""
        total = self._hits + self._misses
        hit_rate = self._hits / total if total > 0 else 0
        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": f"{hit_rate:.1%}",
            "size": len(self._cache),
            "max_size": self.max_size
        }


@dataclass
class ProductMatch:
    """Resultado de una coincidencia de producto"""
    product: Dict
    confidence: float
    match_type: str  # exact, fuzzy, phonetic, keyword
    matched_term: str


class ProductMatcher:
    """
    Detector inteligente de productos mencionados.

    VERSION 2.0 - OPTIMIZADO:
    - Cache LRU con TTL (5 minutos) para búsquedas repetidas
    - Índice por categoría para búsquedas más rápidas
    - Método unificado que reemplaza DecisionTree._detect_mentioned_product()

    Técnicas utilizadas:
    1. Coincidencia exacta
    2. Fuzzy matching (Levenshtein)
    3. Coincidencia fonética (soundex simplificado español)
    4. Coincidencia por palabras clave
    5. Coincidencia por alias/sinónimos
    """

    def __init__(self, menu: List[Dict] = None, config: Dict = None):
        """
        Inicializa el matcher.

        Args:
            menu: Lista de productos del menú
            config: Configuración opcional
        """
        self.menu = menu or []
        self.config = config or {}

        # Configuración
        self.min_fuzzy_ratio = self.config.get('min_fuzzy_ratio', 0.75)
        self.min_keyword_length = self.config.get('min_keyword_length', 4)

        # Cache de índices para búsqueda rápida
        self._product_index = {}
        self._keyword_index = {}
        self._phonetic_index = {}
        self._category_index = {}  # NUEVO: Índice por categoría

        # Cache LRU para búsquedas (max 100 entries, 5 min TTL)
        self._search_cache = LRUCacheWithTTL(
            max_size=self.config.get('cache_max_size', 100),
            ttl_seconds=self.config.get('cache_ttl_seconds', 300)
        )

        # Aliases comunes EXPANDIDOS v2.5 (sincronizado con multi_order_parser)
        self.product_aliases = {
            # ========================================
            # BEBIDAS - Refrescos
            # ========================================
            'coca': 'Coca-Cola',
            'coca cola': 'Coca-Cola',
            'cocacola': 'Coca-Cola',
            'refresco': 'Coca-Cola',
            'una coca': 'Coca-Cola',
            'coquita': 'Coca-Cola',
            'sprite': 'Sprite',
            'fanta': 'Fanta',
            'pepsi': 'Pepsi',
            '7up': '7-Up',
            'sidral': 'Sidral Mundet',
            'manzanita': 'Sidral Mundet',
            'squirt': 'Squirt',
            'fresca': 'Fresca',
            'manzana': 'Sidral Mundet',

            # ========================================
            # BEBIDAS - Aguas Frescas
            # ========================================
            'horchata': 'Agua de Horchata',
            'agua de horchata': 'Agua de Horchata',
            'jamaica': 'Agua de Jamaica',
            'agua de jamaica': 'Agua de Jamaica',
            'limon': 'Agua de Limon',
            'agua de limon': 'Agua de Limon',
            'limonada': 'Limonada Mineral',
            'tamarindo': 'Agua de Tamarindo',
            'sandia': 'Agua de Sandia',
            'melon': 'Agua de Melon',
            'naranja': 'Jugo de Naranja',
            'agua natural': 'Agua Natural',
            'agua simple': 'Agua Natural',
            'agua sola': 'Agua Natural',
            'agua mineral': 'Agua Mineral',
            'agua con gas': 'Agua Mineral',

            # ========================================
            # BEBIDAS - Café y otros
            # ========================================
            'cafe': 'Cafe Americano',
            'café': 'Cafe Americano',
            'cafecito': 'Cafe Americano',
            'capuchino': 'Capuchino',
            'americano': 'Cafe Americano',
            'te': 'Te',
            'té': 'Te',
            'cerveza': 'Cerveza',
            'chela': 'Cerveza',
            'cheve': 'Cerveza',

            # ========================================
            # TACOS
            # ========================================
            'pastor': 'Tacos al Pastor',
            'tacos al pastor': 'Tacos al Pastor',
            'taco al pastor': 'Tacos al Pastor',
            'de pastor': 'Tacos al Pastor',
            'al pastor': 'Tacos al Pastor',
            'asada': 'Tacos de Carne Asada',
            'carne asada': 'Tacos de Carne Asada',
            'tacos de asada': 'Tacos de Carne Asada',
            'taco de asada': 'Tacos de Carne Asada',
            'tacos de carne asada': 'Tacos de Carne Asada',
            'birria': 'Tacos de Birria',
            'tacos de birria': 'Tacos de Birria',
            'taco de birria': 'Tacos de Birria',
            'carnitas': 'Tacos de Carnitas',
            'tacos de carnitas': 'Tacos de Carnitas',
            'taco de carnitas': 'Tacos de Carnitas',
            'suadero': 'Tacos de Suadero',
            'tacos de suadero': 'Tacos de Suadero',
            'chorizo': 'Tacos de Chorizo',
            'tacos de chorizo': 'Tacos de Chorizo',
            'campechanos': 'Tacos Campechanos',
            'tacos campechanos': 'Tacos Campechanos',
            'tripa': 'Tacos de Tripa',
            'tripas': 'Tacos de Tripa',
            'lengua': 'Tacos de Lengua',
            'cabeza': 'Tacos de Cabeza',
            'bistec': 'Tacos de Bistec',

            # ========================================
            # HAMBURGUESAS
            # ========================================
            'hamburguesa': 'Hamburguesa Clasica',
            'hamburgesa': 'Hamburguesa Clasica',
            'burger': 'Hamburguesa Clasica',
            'clasica': 'Hamburguesa Clasica',
            'clásica': 'Hamburguesa Clasica',
            'hamburguesa sencilla': 'Hamburguesa Clasica',
            'sencilla': 'Hamburguesa Clasica',
            'doble': 'Hamburguesa Doble',
            'hamburguesa doble': 'Hamburguesa Doble',
            'doble carne': 'Hamburguesa Doble',
            'hamburguesa doble carne': 'Hamburguesa Doble',
            'tocino': 'Hamburguesa Tocino',
            'hamburguesa con tocino': 'Hamburguesa Tocino',
            'con tocino': 'Hamburguesa Tocino',
            'bacon': 'Hamburguesa Tocino',
            'mexicana': 'Hamburguesa Mexicana',
            'hamburguesa mexicana': 'Hamburguesa Mexicana',
            'vegetariana': 'Hamburguesa Vegetariana',
            'hamburguesa vegetariana': 'Hamburguesa Vegetariana',
            'veggie': 'Hamburguesa Vegetariana',
            'bbq': 'Hamburguesa BBQ',
            'hamburguesa bbq': 'Hamburguesa BBQ',
            'barbacoa': 'Hamburguesa BBQ',

            # ========================================
            # COMPLEMENTOS / ENTRADAS
            # ========================================
            'papas': 'Papas a la Francesa',
            'papas fritas': 'Papas a la Francesa',
            'papitas': 'Papas a la Francesa',
            'francesa': 'Papas a la Francesa',
            'francesas': 'Papas a la Francesa',
            'guacamole': 'Guacamole',
            'guaca': 'Guacamole',
            'queso fundido': 'Queso Fundido',
            'queso': 'Queso Fundido',
            'quesadilla': 'Quesadilla',
            'quesadillas': 'Quesadilla',
            'nachos': 'Nachos',
            'nachitos': 'Nachos',
            'alitas': 'Alitas de Pollo',
            'alitas de pollo': 'Alitas de Pollo',
            'wings': 'Alitas de Pollo',
            'elotes': 'Elotes',
            'elote': 'Elotes',
            'esquites': 'Esquites',
            'totopos': 'Totopos con Salsa',

            # ========================================
            # POSTRES
            # ========================================
            'flan': 'Flan Napolitano',
            'pastel': 'Pastel del Dia',
            'helado': 'Helado',
            'nieve': 'Helado',
            'churros': 'Churros',
            'churro': 'Churros',
            'chocoflan': 'Chocoflan',
            'arroz con leche': 'Arroz con Leche',

            # ========================================
            # PLATOS PRINCIPALES
            # ========================================
            'torta': 'Torta',
            'tortas': 'Torta',
            'sincronizada': 'Sincronizada',
            'sincronizadas': 'Sincronizada',
            'enchiladas': 'Enchiladas',
            'enchilada': 'Enchiladas',
            'chilaquiles': 'Chilaquiles',
            'burritos': 'Burrito',
            'burrito': 'Burrito',
            'pozole': 'Pozole',
            'sopa': 'Sopa del Dia',
            'caldo': 'Caldo de Pollo',
            'ensalada': 'Ensalada',
        }

        # Palabras a ignorar
        self.stop_words = {
            'el', 'la', 'los', 'las', 'un', 'una', 'unos', 'unas',
            'de', 'del', 'al', 'con', 'sin', 'para', 'por',
            'me', 'te', 'se', 'nos', 'les',
            'quiero', 'dame', 'ponme', 'tráeme', 'deme',
            'recomiendas', 'recomienda', 'sugieres', 'sugiere',
            'qué', 'cuál', 'cómo', 'cuánto', 'cuántos',
            'muy', 'más', 'menos', 'mucho', 'poco',
            'y', 'o', 'pero', 'que', 'porque'
        }

        # Sinónimos comunes
        self.synonyms = {
            'hamburguesa': ['burger', 'hamburgesa', 'hamburgueza', 'amburguesa'],
            'taco': ['takito', 'taquito'],
            'agua': ['agüita', 'aguita'],
            'refresco': ['soda', 'coca', 'pepsi'],
            'papas': ['papitas', 'papas fritas', 'french fries'],
            'pollo': ['pollito', 'chicken'],
            'carne': ['carnita', 'res', 'bistec'],
            'pastor': ['al pastor', 'alpastor'],
            'carnitas': ['carnita', 'carnitas de puerco'],
            'asada': ['carne asada', 'asadita'],
            'queso': ['quesito', 'cheese'],
            'doble': ['doble carne', '2x'],
            'chico': ['pequeño', 'small', 'chiquito'],
            'grande': ['large', 'grandote', 'familiar'],
        }

        # Construir índices
        if menu:
            self._build_indices()

    def update_menu(self, menu: List[Dict]):
        """Actualiza el menú y reconstruye índices"""
        self.menu = menu
        self._build_indices()
        # Limpiar cache al actualizar menú
        self._search_cache.clear()
        logger.info("[MATCHER] Cache limpiado por actualización de menú")

    def _build_indices(self):
        """Construye índices para búsqueda eficiente"""

        self._product_index = {}
        self._keyword_index = {}
        self._phonetic_index = {}
        self._category_index = {}  # NUEVO

        for product in self.menu:
            name = product.get('name', '')
            name_normalized = self._normalize_text(name)

            # Índice por nombre exacto
            self._product_index[name_normalized] = product

            # Índice por palabras clave
            keywords = self._extract_keywords(name)
            for keyword in keywords:
                if keyword not in self._keyword_index:
                    self._keyword_index[keyword] = []
                self._keyword_index[keyword].append(product)

            # Índice fonético
            phonetic = self._spanish_soundex(name_normalized)
            if phonetic not in self._phonetic_index:
                self._phonetic_index[phonetic] = []
            self._phonetic_index[phonetic].append(product)

            # NUEVO: Índice por categoría
            category = product.get('category', {}).get('name', 'Sin categoría')
            if category not in self._category_index:
                self._category_index[category] = []
            self._category_index[category].append(product)

        logger.info(f"[MATCHER] Índices construidos: {len(self._product_index)} productos, "
                   f"{len(self._keyword_index)} keywords, {len(self._phonetic_index)} fonéticos, "
                   f"{len(self._category_index)} categorías")

    def _normalize_text(self, text: str) -> str:
        """
        Normaliza texto para comparación.
        Remueve acentos, convierte a minúsculas, limpia espacios.
        """
        # Convertir a minúsculas
        text = text.lower().strip()

        # Remover acentos
        text = unicodedata.normalize('NFD', text)
        text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')

        # Normalizar espacios
        text = re.sub(r'\s+', ' ', text)

        return text

    def _extract_keywords(self, text: str) -> List[str]:
        """Extrae palabras clave significativas del texto"""
        normalized = self._normalize_text(text)
        words = normalized.split()

        keywords = []
        for word in words:
            if word not in self.stop_words and len(word) >= self.min_keyword_length:
                keywords.append(word)

        return keywords

    def _spanish_soundex(self, text: str) -> str:
        """
        Implementación simplificada de soundex para español.
        Agrupa letras con sonido similar.
        """
        if not text:
            return ""

        text = self._normalize_text(text)

        # Mapeo de letras a códigos fonéticos
        # Letras con sonido similar tienen el mismo código
        phonetic_map = {
            'b': '1', 'v': '1', 'p': '1', 'f': '1',
            'c': '2', 'k': '2', 'q': '2', 's': '2', 'z': '2', 'x': '2',
            'd': '3', 't': '3',
            'l': '4',
            'm': '5', 'n': '5', 'ñ': '5',
            'r': '6',
            'g': '7', 'j': '7', 'h': '7',
            'y': '8', 'i': '8',
            'a': '0', 'e': '0', 'o': '0', 'u': '0'
        }

        # Mantener primera letra y convertir el resto
        result = text[0] if text else ''
        prev_code = ''

        for char in text[1:]:
            code = phonetic_map.get(char, '')
            # Evitar códigos consecutivos iguales
            if code and code != prev_code:
                result += code
                prev_code = code

        # Limitar longitud
        return result[:6]

    def _fuzzy_ratio(self, s1: str, s2: str) -> float:
        """Calcula similitud entre dos strings usando SequenceMatcher"""
        return SequenceMatcher(None, s1, s2).ratio()

    def get_products_by_category(self, category_name: str) -> List[Dict]:
        """
        Obtiene productos de una categoría usando el índice.
        Más eficiente que iterar sobre todo el menú.
        """
        # Mapeo de nombres coloquiales a nombres de categoría
        category_mapping = {
            'hamburguesas': 'Hamburguesas',
            'hamburguesa': 'Hamburguesas',
            'tacos': 'Tacos',
            'taco': 'Tacos',
            'bebidas': 'Bebidas',
            'bebida': 'Bebidas',
            'postres': 'Postres',
            'postre': 'Postres',
            'entradas': 'Entradas',
            'entrada': 'Entradas',
            'complementos': 'Complementos',
            'complemento': 'Complementos',
        }

        normalized_category = category_mapping.get(category_name.lower(), category_name)
        return self._category_index.get(normalized_category, [])

    def find_product_unified(
        self,
        user_input: str,
        category_name: str = None,
        category_products: List[Dict] = None
    ) -> Optional[str]:
        """
        MÉTODO UNIFICADO - Reemplaza DecisionTree._detect_mentioned_product()

        Detecta si el usuario mencionó un producto específico.
        Usa cache para búsquedas repetidas.

        Args:
            user_input: Texto del usuario
            category_name: Nombre de categoría activa (opcional)
            category_products: Lista de productos de categoría activa (opcional)

        Returns:
            Nombre del producto encontrado o None
        """
        user_normalized = self._normalize_text(user_input)

        # Generar cache key
        cache_key = hashlib.md5(
            f"{user_normalized}:{category_name or 'all'}".encode()
        ).hexdigest()

        # Verificar cache
        cached_result = self._search_cache.get(cache_key)
        if cached_result is not None:
            logger.debug(f"[MATCHER] Cache HIT para: '{user_input[:30]}...'")
            return cached_result if cached_result != '__NONE__' else None

        # PASO 1: Buscar en aliases (más rápido)
        for alias, product_name in self.product_aliases.items():
            if alias in user_normalized:
                logger.info(f"[MATCHER] Producto por alias: {product_name} (alias: {alias})")
                self._search_cache.set(cache_key, product_name)
                return product_name

        # PASO 2: Búsqueda completa con find_product
        products_to_search = category_products
        if products_to_search is None and category_name:
            products_to_search = self.get_products_by_category(category_name)

        matches = self.find_product(
            user_input,
            category_products=products_to_search,
            top_n=1
        )

        if matches and matches[0].confidence >= 0.70:
            product_name = matches[0].product.get('name', '')
            logger.info(f"[MATCHER] Producto encontrado: {product_name} "
                       f"(conf: {matches[0].confidence:.2f}, tipo: {matches[0].match_type})")
            self._search_cache.set(cache_key, product_name)
            return product_name

        # No encontrado - guardar en cache para evitar rebúsqueda
        self._search_cache.set(cache_key, '__NONE__')
        return None

    def find_product(
        self,
        user_input: str,
        category_products: List[Dict] = None,
        top_n: int = 1
    ) -> List[ProductMatch]:
        """
        Busca productos que coincidan con el input del usuario.

        Args:
            user_input: Texto del usuario
            category_products: Lista de productos a buscar (si None, busca en todo el menú)
            top_n: Número máximo de resultados

        Returns:
            Lista de ProductMatch ordenados por confianza
        """
        user_normalized = self._normalize_text(user_input)

        # Generar cache key para esta búsqueda específica
        category_hash = hashlib.md5(
            str([p.get('id', p.get('name', '')) for p in (category_products or [])]).encode()
        ).hexdigest()[:8] if category_products else 'all'

        cache_key = f"fp:{hashlib.md5(user_normalized.encode()).hexdigest()[:12]}:{category_hash}:{top_n}"

        # Verificar cache
        cached_result = self._search_cache.get(cache_key)
        if cached_result is not None:
            logger.debug(f"[MATCHER] Cache HIT find_product: '{user_input[:20]}...'")
            return cached_result

        user_keywords = self._extract_keywords(user_input)
        user_phonetic = self._spanish_soundex(user_normalized)

        products_to_search = category_products if category_products else self.menu
        matches = []

        for product in products_to_search:
            product_name = product.get('name', '')
            product_normalized = self._normalize_text(product_name)
            product_keywords = self._extract_keywords(product_name)

            # 1. Coincidencia exacta
            if product_normalized == user_normalized:
                matches.append(ProductMatch(
                    product=product,
                    confidence=1.0,
                    match_type='exact',
                    matched_term=product_name
                ))
                continue

            # 2. Coincidencia exacta de palabras clave
            keyword_matches = set(user_keywords) & set(product_keywords)
            if keyword_matches:
                # Calcular confianza basada en proporción de keywords que coinciden
                confidence = len(keyword_matches) / max(len(user_keywords), len(product_keywords))
                # Bonus si la keyword es significativa (más de 5 caracteres)
                if any(len(k) > 5 for k in keyword_matches):
                    confidence = min(confidence + 0.15, 0.95)

                matches.append(ProductMatch(
                    product=product,
                    confidence=confidence,
                    match_type='keyword',
                    matched_term=', '.join(keyword_matches)
                ))
                continue

            # 3. Fuzzy matching
            fuzzy_score = self._fuzzy_ratio(user_normalized, product_normalized)
            if fuzzy_score >= self.min_fuzzy_ratio:
                matches.append(ProductMatch(
                    product=product,
                    confidence=fuzzy_score,
                    match_type='fuzzy',
                    matched_term=product_name
                ))
                continue

            # 4. Fuzzy matching en palabras clave individuales
            for user_kw in user_keywords:
                for prod_kw in product_keywords:
                    kw_fuzzy = self._fuzzy_ratio(user_kw, prod_kw)
                    if kw_fuzzy >= 0.8:  # Umbral más alto para keywords individuales
                        matches.append(ProductMatch(
                            product=product,
                            confidence=kw_fuzzy * 0.85,  # Reducir un poco por ser match parcial
                            match_type='fuzzy_keyword',
                            matched_term=f"{user_kw} ~ {prod_kw}"
                        ))
                        break
                else:
                    continue
                break

            # 5. Coincidencia fonética
            product_phonetic = self._spanish_soundex(product_normalized)
            if user_phonetic and product_phonetic:
                phonetic_ratio = self._fuzzy_ratio(user_phonetic, product_phonetic)
                if phonetic_ratio >= 0.7:
                    matches.append(ProductMatch(
                        product=product,
                        confidence=phonetic_ratio * 0.7,  # Menor confianza para fonético
                        match_type='phonetic',
                        matched_term=product_name
                    ))

        # 6. Buscar por sinónimos
        synonym_matches = self._search_by_synonyms(user_normalized, products_to_search)
        matches.extend(synonym_matches)

        # Ordenar por confianza y eliminar duplicados
        matches = self._deduplicate_matches(matches)
        matches.sort(key=lambda x: x.confidence, reverse=True)

        # Filtrar matches con confianza muy baja
        matches = [m for m in matches if m.confidence >= 0.5]

        result = matches[:top_n]

        # Guardar en cache
        self._search_cache.set(cache_key, result)

        return result

    def _search_by_synonyms(
        self,
        user_text: str,
        products: List[Dict]
    ) -> List[ProductMatch]:
        """Busca coincidencias usando sinónimos"""

        matches = []

        for synonym_key, synonym_list in self.synonyms.items():
            # Verificar si el usuario usó algún sinónimo
            for synonym in synonym_list:
                if synonym in user_text:
                    # Buscar productos que contengan la palabra clave original
                    for product in products:
                        product_normalized = self._normalize_text(product.get('name', ''))
                        if synonym_key in product_normalized:
                            matches.append(ProductMatch(
                                product=product,
                                confidence=0.75,
                                match_type='synonym',
                                matched_term=f"{synonym} → {synonym_key}"
                            ))

        return matches

    def _deduplicate_matches(self, matches: List[ProductMatch]) -> List[ProductMatch]:
        """Elimina matches duplicados, manteniendo el de mayor confianza"""
        seen = {}
        for match in matches:
            product_id = match.product.get('id') or match.product.get('name')
            if product_id not in seen or match.confidence > seen[product_id].confidence:
                seen[product_id] = match

        return list(seen.values())

    def detect_quantity(self, text: str) -> Tuple[Optional[int], str]:
        """
        Detecta cantidad mencionada en el texto.

        Returns:
            Tupla (cantidad, texto_sin_cantidad)
        """
        text_lower = text.lower()

        # Números escritos
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
            'diez': 10,
            'media': 0.5,
            'medio': 0.5,
            'doble': 2,
            'triple': 3
        }

        # Buscar números
        num_match = re.search(r'\b(\d+)\b', text_lower)
        if num_match:
            quantity = int(num_match.group(1))
            text_clean = text_lower.replace(num_match.group(0), '').strip()
            return (quantity, text_clean)

        # Buscar palabras numéricas
        for word, num in word_to_num.items():
            if re.search(rf'\b{word}\b', text_lower):
                text_clean = re.sub(rf'\b{word}\b', '', text_lower).strip()
                return (int(num) if num >= 1 else 1, text_clean)

        return (None, text)

    # Precios de extras (debe coincidir con customer-app)
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

    def extract_modifiers(self, text: str) -> Dict[str, any]:
        """
        Extrae modificadores del pedido (sin cebolla, extra queso, etc.)

        Returns:
            Dict con modificadores detectados incluyendo precios
        """
        text_lower = text.lower()
        modifiers = {
            'extras': [],       # Lista de dicts: {name, price}
            'without': [],      # Lista de strings
            'size': None,
            'cooking': None,
            'total_extra_price': 0
        }

        # Lista ampliada de ingredientes
        all_ingredients = [
            'queso', 'tocino', 'cebolla', 'aguacate', 'jalapeño', 'jalapeno',
            'jitomate', 'tomate', 'lechuga', 'crema', 'cilantro', 'salsa',
            'chile', 'guacamole', 'carne', 'pollo', 'chorizo', 'huevo',
            'frijoles', 'arroz', 'limón', 'limon', 'piña', 'pina', 'champiñon',
            'champiñones', 'nopal', 'pepino', 'mayonesa', 'mostaza', 'catsup',
            'picante', 'papas', 'elote', 'camaron', 'camarón'
        ]

        ingredients_pattern = '|'.join(all_ingredients)

        # Patrones para "sin" (quitar ingrediente)
        sin_pattern = rf'sin\s+({ingredients_pattern})'
        sin_matches = re.findall(sin_pattern, text_lower)
        for ingredient in sin_matches:
            if ingredient not in modifiers['without']:
                modifiers['without'].append(ingredient)

        # Patrones para "extra" o "con" (agregar ingrediente)
        extra_pattern = rf'(?:extra|con|doble)\s+({ingredients_pattern})'
        extra_matches = re.findall(extra_pattern, text_lower)
        for ingredient in extra_matches:
            # Buscar precio del extra
            extra_price = 0
            for key, price in self.EXTRA_PRICES.items():
                if key in ingredient:
                    extra_price = price
                    break

            # Evitar duplicados
            existing = [e['name'] for e in modifiers['extras']]
            if ingredient not in existing:
                modifiers['extras'].append({
                    'name': ingredient,
                    'price': extra_price
                })
                modifiers['total_extra_price'] += extra_price

        # Tamaño
        size_patterns = {
            'chico': ['chico', 'pequeño', 'small', 'chiquito'],
            'mediano': ['mediano', 'regular', 'normal'],
            'grande': ['grande', 'large', 'familiar', 'xl']
        }

        for size, patterns in size_patterns.items():
            if any(p in text_lower for p in patterns):
                modifiers['size'] = size
                break

        # Término de cocción (para carnes)
        cooking_patterns = {
            'bien_cocido': ['bien cocido', 'well done', 'muy cocido'],
            'termino_medio': ['termino medio', 'medium', 'al punto'],
            'poco_cocido': ['poco cocido', 'rojo', 'tres cuartos']
        }

        for cooking, patterns in cooking_patterns.items():
            if any(p in text_lower for p in patterns):
                modifiers['cooking'] = cooking
                break

        return modifiers

    def modifiers_to_notes(self, modifiers: Dict) -> str:
        """Convierte modificadores a texto de notas para el pedido"""
        notes_parts = []

        for ingredient in modifiers.get('without', []):
            notes_parts.append(f"Sin {ingredient}")

        for extra in modifiers.get('extras', []):
            if isinstance(extra, dict):
                note = f"Extra {extra['name']}"
                if extra.get('price', 0) > 0:
                    note += f" (+${extra['price']})"
                notes_parts.append(note)
            else:
                notes_parts.append(f"Extra {extra}")

        if modifiers.get('size'):
            notes_parts.append(f"Tamaño: {modifiers['size']}")

        if modifiers.get('cooking'):
            notes_parts.append(f"Cocción: {modifiers['cooking']}")

        return ", ".join(notes_parts)

    def get_cache_stats(self) -> Dict:
        """Retorna estadísticas del cache de búsquedas"""
        return self._search_cache.stats()

    def clear_cache(self):
        """Limpia el cache de búsquedas"""
        self._search_cache.clear()
        logger.info("[MATCHER] Cache de búsquedas limpiado manualmente")


# Instancia global
_product_matcher: Optional[ProductMatcher] = None


def get_product_matcher(menu: List[Dict] = None, config: Dict = None) -> ProductMatcher:
    """Obtiene instancia global del matcher (Singleton)"""
    global _product_matcher
    if _product_matcher is None:
        _product_matcher = ProductMatcher(menu=menu, config=config)
    elif menu:
        _product_matcher.update_menu(menu)
    return _product_matcher
