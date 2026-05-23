# ============================================================
# PRODUCT VALIDATOR - Validación de Existencia de Productos
# ============================================================
# Valida si un producto existe antes de procesarlo
# Evita respuestas incorrectas sobre productos inexistentes
# ============================================================

import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ProductStatus(Enum):
    """Estado de búsqueda de producto"""
    FOUND = "found"                    # Producto encontrado con certeza
    NEEDS_CONFIRMATION = "confirm"     # Posible match, necesita confirmación
    NOT_FOUND = "not_found"            # Producto no existe
    AMBIGUOUS = "ambiguous"            # Múltiples productos posibles


@dataclass
class ProductValidationResult:
    """Resultado de validación de producto"""
    status: ProductStatus
    confidence: float
    product: Optional[Dict]            # Producto encontrado (si aplica)
    suggestions: List[Dict]            # Sugerencias alternativas
    message: str                       # Mensaje para el usuario
    original_query: str                # Query original del usuario


class ProductValidator:
    """
    Valida existencia de productos antes de procesarlos.

    Umbrales de confianza:
    - >= 0.85: Producto encontrado con certeza
    - 0.70 - 0.84: Necesita confirmación ("¿Te refieres a X?")
    - 0.50 - 0.69: Sugerir alternativas
    - < 0.50: Producto no encontrado

    Ejemplo:
    - "hamburguesa BBQ" → FOUND (0.95)
    - "hamburguesa verde" → NOT_FOUND + suggestions
    - "hamburguesa" → AMBIGUOUS (múltiples opciones)
    """

    # Umbrales de confianza
    THRESHOLD_FOUND = 0.85
    THRESHOLD_CONFIRM = 0.70
    THRESHOLD_SUGGEST = 0.50

    def __init__(self, product_matcher=None, semantic_search=None):
        """
        Args:
            product_matcher: Instancia de ProductMatcher
            semantic_search: Instancia de ProductSemanticSearch (opcional)
        """
        self.product_matcher = product_matcher
        self.semantic_search = semantic_search

    def validate(
        self,
        query: str,
        category_products: List[Dict] = None,
        context: any = None
    ) -> ProductValidationResult:
        """
        Valida si el producto mencionado existe.

        Args:
            query: Texto del usuario mencionando el producto
            category_products: Productos de la categoría activa (si aplica)
            context: Contexto de conversación

        Returns:
            ProductValidationResult con estado y sugerencias
        """
        if not self.product_matcher:
            return ProductValidationResult(
                status=ProductStatus.NOT_FOUND,
                confidence=0.0,
                product=None,
                suggestions=[],
                message="Sistema de búsqueda no disponible",
                original_query=query
            )

        # Buscar con ProductMatcher
        matches = self.product_matcher.find_product(
            query,
            category_products=category_products,
            top_n=5
        )

        if not matches:
            # Intentar búsqueda semántica si está disponible
            if self.semantic_search:
                semantic_matches = self.semantic_search.search(query, top_k=3)
                if semantic_matches:
                    suggestions = [m.product for m in semantic_matches]
                    return ProductValidationResult(
                        status=ProductStatus.NOT_FOUND,
                        confidence=0.0,
                        product=None,
                        suggestions=suggestions,
                        message=self._build_not_found_message(query, suggestions),
                        original_query=query
                    )

            return ProductValidationResult(
                status=ProductStatus.NOT_FOUND,
                confidence=0.0,
                product=None,
                suggestions=[],
                message=f"No encontré '{query}' en el menú. ¿Qué te gustaría ordenar?",
                original_query=query
            )

        best_match = matches[0]
        confidence = best_match.confidence

        # CASO 1: Encontrado con certeza
        if confidence >= self.THRESHOLD_FOUND:
            logger.info(f"[VALIDATOR] FOUND: '{query}' → {best_match.product['name']} ({confidence:.2f})")
            return ProductValidationResult(
                status=ProductStatus.FOUND,
                confidence=confidence,
                product=best_match.product,
                suggestions=[],
                message="",
                original_query=query
            )

        # CASO 2: Necesita confirmación
        if confidence >= self.THRESHOLD_CONFIRM:
            logger.info(f"[VALIDATOR] CONFIRM: '{query}' → {best_match.product['name']}? ({confidence:.2f})")
            return ProductValidationResult(
                status=ProductStatus.NEEDS_CONFIRMATION,
                confidence=confidence,
                product=best_match.product,
                suggestions=[m.product for m in matches[1:3]],
                message=f"¿Te refieres a {best_match.product['name']}?",
                original_query=query
            )

        # CASO 3: Sugerir alternativas
        if confidence >= self.THRESHOLD_SUGGEST:
            suggestions = [m.product for m in matches[:3]]
            logger.info(f"[VALIDATOR] SUGGEST: '{query}' → {len(suggestions)} opciones")
            return ProductValidationResult(
                status=ProductStatus.NOT_FOUND,
                confidence=confidence,
                product=None,
                suggestions=suggestions,
                message=self._build_not_found_message(query, suggestions),
                original_query=query
            )

        # CASO 4: No encontrado
        # Intentar obtener sugerencias de la misma categoría
        suggestions = self._get_category_suggestions(query, category_products)
        logger.info(f"[VALIDATOR] NOT_FOUND: '{query}'")
        return ProductValidationResult(
            status=ProductStatus.NOT_FOUND,
            confidence=0.0,
            product=None,
            suggestions=suggestions,
            message=self._build_not_found_message(query, suggestions),
            original_query=query
        )

    def validate_multiple(
        self,
        queries: List[str],
        category_products: List[Dict] = None
    ) -> List[ProductValidationResult]:
        """Valida múltiples productos a la vez"""
        return [self.validate(q, category_products) for q in queries]

    def _build_not_found_message(
        self,
        query: str,
        suggestions: List[Dict]
    ) -> str:
        """Construye mensaje amigable para producto no encontrado"""
        if not suggestions:
            return f"No tenemos '{query}'. ¿Qué te gustaría ordenar?"

        if len(suggestions) == 1:
            return f"No tenemos '{query}', pero te puedo ofrecer {suggestions[0]['name']}. ¿Te late?"

        names = [s['name'] for s in suggestions[:3]]
        options = ", ".join(names[:-1]) + f" o {names[-1]}"
        return f"No tenemos '{query}'. Te recomiendo: {options}. ¿Cuál prefieres?"

    def _get_category_suggestions(
        self,
        query: str,
        category_products: List[Dict] = None
    ) -> List[Dict]:
        """Obtiene sugerencias de la misma categoría"""
        if category_products and len(category_products) > 0:
            # Retornar los primeros 3 productos de la categoría
            return category_products[:3]

        # Si no hay categoría, buscar productos populares
        if self.product_matcher and self.product_matcher.menu:
            popular = [p for p in self.product_matcher.menu if 'popular' in p.get('tags', [])]
            if popular:
                return popular[:3]
            return self.product_matcher.menu[:3]

        return []

    def check_product_exists(self, product_name: str) -> bool:
        """
        Verificación rápida de existencia de producto.
        Útil para validaciones simples.
        """
        result = self.validate(product_name)
        return result.status == ProductStatus.FOUND

    def get_exact_product(self, product_name: str) -> Optional[Dict]:
        """
        Obtiene producto solo si hay match exacto o muy alto.
        Retorna None si no hay certeza.
        """
        result = self.validate(product_name)
        if result.status == ProductStatus.FOUND:
            return result.product
        return None


# Factory function
def create_product_validator(product_matcher=None, semantic_search=None) -> ProductValidator:
    """Crea instancia de ProductValidator con dependencias"""
    return ProductValidator(
        product_matcher=product_matcher,
        semantic_search=semantic_search
    )
