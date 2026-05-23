# ============================================================
# SEMANTIC SEARCH - Búsqueda Semántica de Productos
# ============================================================
# Usa embeddings para encontrar productos por significado
# "hamburguesa con salsa ahumada" → "Hamburguesa BBQ"
# ============================================================

import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import numpy as np

logger = logging.getLogger(__name__)

# Intentar importar sentence-transformers
try:
    from sentence_transformers import SentenceTransformer
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    logger.warning("[SEMANTIC] sentence-transformers no disponible")


@dataclass
class SemanticMatch:
    """Resultado de búsqueda semántica"""
    product: Dict
    similarity: float
    description_match: bool  # True si matcheó por descripción


class ProductSemanticSearch:
    """
    Búsqueda semántica de productos usando embeddings.

    Ventajas:
    - Encuentra productos por descripción, no solo nombre
    - "con salsa ahumada" → encuentra "BBQ"
    - "algo ligero" → encuentra ensaladas
    - Maneja sinónimos automáticamente
    """

    def __init__(self, menu: List[Dict] = None, model_name: str = "all-MiniLM-L6-v2"):
        self.menu = menu or []
        self.model_name = model_name
        self.model = None
        self.product_embeddings: Dict[int, np.ndarray] = {}
        self.is_ready = False

        if menu:
            self._initialize()

    def _initialize(self):
        """Inicializa modelo y genera embeddings de productos"""
        if not TRANSFORMERS_AVAILABLE:
            return

        try:
            logger.info(f"[SEMANTIC] Cargando modelo: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)

            self._build_embeddings()
            self.is_ready = True
            logger.info(f"[SEMANTIC] Listo con {len(self.product_embeddings)} productos")

        except Exception as e:
            logger.error(f"[SEMANTIC] Error inicializando: {e}")

    def _build_embeddings(self):
        """Genera embeddings para cada producto"""
        if not self.model:
            return

        for product in self.menu:
            product_id = product.get('id')
            if not product_id:
                continue

            # Crear texto rico para el embedding
            # Combina nombre + descripción + categoría
            text_parts = []

            name = product.get('name', '')
            text_parts.append(name)

            description = product.get('description', '')
            if description:
                text_parts.append(description)

            category = product.get('category', {})
            if isinstance(category, dict):
                cat_name = category.get('name', '')
                if cat_name:
                    text_parts.append(cat_name)

            # Tags si existen
            tags = product.get('tags', [])
            if tags:
                text_parts.extend(tags)

            # Generar embedding
            full_text = ' '.join(text_parts)
            embedding = self.model.encode([full_text])[0]
            self.product_embeddings[product_id] = embedding

    def update_menu(self, menu: List[Dict]):
        """Actualiza menú y regenera embeddings"""
        self.menu = menu
        if TRANSFORMERS_AVAILABLE and self.model:
            self._build_embeddings()

    def search(
        self,
        query: str,
        top_k: int = 5,
        min_similarity: float = 0.3,
        category_filter: str = None
    ) -> List[SemanticMatch]:
        """
        Busca productos semánticamente similares a la consulta.

        Args:
            query: Texto de búsqueda del usuario
            top_k: Número máximo de resultados
            min_similarity: Similitud mínima (0-1)
            category_filter: Filtrar por categoría específica

        Returns:
            Lista de SemanticMatch ordenados por similitud
        """
        if not self.is_ready or not self.model:
            return []

        try:
            # Generar embedding de la consulta
            query_embedding = self.model.encode([query.lower()])[0]

            # Calcular similitud con cada producto
            results = []
            for product in self.menu:
                product_id = product.get('id')
                if product_id not in self.product_embeddings:
                    continue

                # Filtrar por categoría si se especificó
                if category_filter:
                    cat = product.get('category', {})
                    cat_name = cat.get('name', '') if isinstance(cat, dict) else ''
                    if category_filter.lower() not in cat_name.lower():
                        continue

                # Calcular similitud coseno
                product_emb = self.product_embeddings[product_id]
                similarity = self._cosine_similarity(query_embedding, product_emb)

                if similarity >= min_similarity:
                    # Determinar si matcheó más por nombre o descripción
                    name_sim = self._text_similarity(query, product.get('name', ''))
                    desc_match = similarity > name_sim + 0.1

                    results.append(SemanticMatch(
                        product=product,
                        similarity=float(similarity),
                        description_match=desc_match
                    ))

            # Ordenar por similitud
            results.sort(key=lambda x: x.similarity, reverse=True)

            return results[:top_k]

        except Exception as e:
            logger.error(f"[SEMANTIC] Error en búsqueda: {e}")
            return []

    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Similitud coseno entre dos vectores"""
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

    def _text_similarity(self, text1: str, text2: str) -> float:
        """Similitud directa entre dos textos"""
        if not self.model:
            return 0.0
        emb1 = self.model.encode([text1.lower()])[0]
        emb2 = self.model.encode([text2.lower()])[0]
        return self._cosine_similarity(emb1, emb2)

    def find_similar_products(
        self,
        product_id: int,
        top_k: int = 3
    ) -> List[SemanticMatch]:
        """
        Encuentra productos similares a uno dado.
        Útil para recomendaciones y sugerencias.
        """
        if product_id not in self.product_embeddings:
            return []

        target_emb = self.product_embeddings[product_id]
        results = []

        for product in self.menu:
            pid = product.get('id')
            if pid == product_id or pid not in self.product_embeddings:
                continue

            similarity = self._cosine_similarity(target_emb, self.product_embeddings[pid])
            results.append(SemanticMatch(
                product=product,
                similarity=float(similarity),
                description_match=False
            ))

        results.sort(key=lambda x: x.similarity, reverse=True)
        return results[:top_k]


# Singleton
_semantic_search: Optional[ProductSemanticSearch] = None


def get_semantic_search(menu: List[Dict] = None) -> ProductSemanticSearch:
    """Obtiene instancia singleton de búsqueda semántica"""
    global _semantic_search
    if _semantic_search is None:
        _semantic_search = ProductSemanticSearch(menu)
    elif menu:
        _semantic_search.update_menu(menu)
    return _semantic_search
