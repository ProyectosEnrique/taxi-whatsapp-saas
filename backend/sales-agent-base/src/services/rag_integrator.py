#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RAG Integrator - Integra RAG con FSM para farmacia

Responsable de:
1. Detectar si el tenant debe usar RAG
2. Conectar búsquedas del FSM con el servicio RAG
3. Generar respuestas inteligentes con LLM + contexto RAG
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

try:
    from .pharmacy_rag import get_pharmacy_rag, RAGSearchResult, PharmacyProduct
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False
    logger.warning("⚠️ PharmacyRAG no disponible")


@dataclass
class RAGResponse:
    """Respuesta mejorada con RAG"""
    products: List[Dict[str, Any]]
    llm_response: str
    metadata: Dict[str, Any]


class RAGIntegrator:
    """
    Integra RAG con el FSM

    Decisión de cuándo usar RAG:
    - Búsquedas por síntomas → RAG
    - Búsquedas por nombre exacto → Decision Tree tradicional
    - Preguntas sobre contraindicaciones → RAG
    - Búsqueda de genéricos → RAG
    """

    def __init__(self, tenant_id: str, tenant_config: Dict[str, Any]):
        """
        Inicializa el integrador

        Args:
            tenant_id: ID del tenant
            tenant_config: Configuración del tenant (de tenants.json)
        """
        self.tenant_id = tenant_id
        self.tenant_config = tenant_config
        self.rag_service = None
        self.is_enabled = False

        # Verificar si debe usar RAG
        fsm_config = tenant_config.get('fsm_config', {})
        business_type = tenant_config.get('business_info', {}).get('type', '')

        # Habilitar RAG si:
        # 1. Es farmacia
        # 2. Tiene semantic_search_enabled: true
        # 3. RAG está disponible
        if (RAG_AVAILABLE and
            business_type == 'pharmacy' and
            fsm_config.get('semantic_search_enabled', False)):

            try:
                self.rag_service = get_pharmacy_rag(tenant_id)
                if self.rag_service and self.rag_service.is_ready:
                    self.is_enabled = True
                    logger.info(f"✅ RAG habilitado para {tenant_id}")
                else:
                    logger.warning(f"⚠️ RAG no pudo inicializarse para {tenant_id}")
            except Exception as e:
                logger.error(f"❌ Error habilitando RAG: {e}")

    def should_use_rag(self, user_query: str, context: Dict[str, Any]) -> bool:
        """
        Decide si usar RAG para esta consulta

        Args:
            user_query: Consulta del usuario
            context: Contexto de la conversación

        Returns:
            True si debe usar RAG
        """
        if not self.is_enabled:
            return False

        query_lower = user_query.lower()

        # Usar RAG para:
        # 1. Búsquedas por síntomas
        symptom_keywords = [
            'dolor', 'duele', 'tengo', 'siento', 'malestar',
            'fiebre', 'tos', 'gripa', 'alergia', 'infección',
            'inflamación', 'náusea', 'mareo', 'diarrea'
        ]
        if any(keyword in query_lower for keyword in symptom_keywords):
            return True

        # 2. Preguntas sobre medicamentos
        question_keywords = [
            'qué puedo tomar', 'qué me recomiendas', 'qué sirve',
            'algo para', 'necesito algo', 'tienes algo',
            'contraindicaciones', 'efectos secundarios', 'interacciones'
        ]
        if any(keyword in query_lower for keyword in question_keywords):
            return True

        # 3. Búsqueda de alternativas
        alternative_keywords = [
            'genérico', 'alternativa', 'similar', 'parecido',
            'más barato', 'otra opción'
        ]
        if any(keyword in query_lower for keyword in alternative_keywords):
            return True

        # 4. Si el usuario menciona múltiples condiciones
        if any(word in query_lower for word in ['pero', 'aunque', 'sin embargo']):
            return True

        return False

    def search_products(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Busca productos usando RAG

        Args:
            query: Consulta del usuario
            top_k: Número de resultados
            filters: Filtros adicionales
            context: Contexto de conversación

        Returns:
            Lista de productos encontrados
        """
        if not self.is_enabled or not self.rag_service:
            return []

        try:
            # Buscar con RAG
            results = self.rag_service.search(
                query=query,
                top_k=top_k,
                filters=filters
            )

            # Convertir a formato estándar
            products = []
            for result in results:
                product_dict = result.product.to_dict()
                product_dict['_similarity_score'] = result.similarity_score
                product_dict['_matched_by'] = result.matched_by
                products.append(product_dict)

            logger.info(f"[RAG] Encontrados {len(products)} productos")
            return products

        except Exception as e:
            logger.error(f"❌ Error en búsqueda RAG: {e}")
            return []

    def search_by_symptom(self, symptom: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Búsqueda específica por síntoma"""
        if not self.is_enabled or not self.rag_service:
            return []

        try:
            results = self.rag_service.search_by_symptom(symptom, top_k=top_k)
            return [r.product.to_dict() for r in results]
        except Exception as e:
            logger.error(f"❌ Error buscando por síntoma: {e}")
            return []

    def find_alternatives(self, product_name: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Encuentra alternativas genéricas"""
        if not self.is_enabled or not self.rag_service:
            return []

        try:
            results = self.rag_service.find_generic_alternatives(product_name, top_k=top_k)
            return [r.product.to_dict() for r in results]
        except Exception as e:
            logger.error(f"❌ Error buscando alternativas: {e}")
            return []

    def generate_response_with_context(
        self,
        query: str,
        products: List[Dict[str, Any]],
        llm_client: Any = None
    ) -> str:
        """
        Genera respuesta usando LLM con contexto de productos encontrados

        Args:
            query: Pregunta del usuario
            products: Productos encontrados por RAG
            llm_client: Cliente LLM (opcional)

        Returns:
            Respuesta generada
        """
        if not products:
            return "No encontré productos que coincidan con tu búsqueda."

        # Si no hay LLM, generar respuesta simple
        if not llm_client:
            return self._generate_simple_response(query, products)

        try:
            # Construir contexto para LLM
            context = self._build_llm_context(products)

            # Prompt para LLM
            prompt = f"""Eres un asistente farmacéutico profesional. Un cliente pregunta:
"{query}"

Productos encontrados:
{context}

Genera una respuesta profesional y útil que:
1. Recomiende los productos más relevantes
2. Mencione información importante (receta, edad, contraindicaciones si aplica)
3. Sea clara y concisa (2-3 oraciones)
4. Use tono profesional pero amigable

Respuesta:"""

            # Llamar LLM (aquí iría la integración con Cerebras/Gemini/Ollama)
            # Por ahora retornamos respuesta simple
            return self._generate_simple_response(query, products)

        except Exception as e:
            logger.error(f"❌ Error generando respuesta con LLM: {e}")
            return self._generate_simple_response(query, products)

    def _generate_simple_response(self, query: str, products: List[Dict[str, Any]]) -> str:
        """Genera respuesta simple sin LLM"""
        if len(products) == 1:
            p = products[0]
            response = f"Tenemos {p['name']} - {p['description']}. Precio: ${p['price']:.2f}"

            if p.get('requires_prescription'):
                response += "\n⚠️ Requiere receta médica."

            return response
        else:
            names = [p['name'] for p in products[:3]]
            response = f"Encontré estas opciones: {', '.join(names)}"

            if any(p.get('requires_prescription') for p in products[:3]):
                response += "\n\n⚠️ Algunos requieren receta médica."

            return response

    def _build_llm_context(self, products: List[Dict[str, Any]]) -> str:
        """Construye contexto de productos para LLM"""
        context_parts = []

        for i, p in enumerate(products[:3], 1):
            parts = [f"{i}. {p['name']} - ${p['price']:.2f}"]

            if p.get('description'):
                parts.append(f"   Descripción: {p['description']}")

            if p.get('requires_prescription'):
                parts.append("   ⚠️ Requiere receta")

            if p.get('generic_name'):
                parts.append(f"   Genérico: {p['generic_name']}")

            if p.get('symptoms'):
                parts.append(f"   Para: {', '.join(p['symptoms'][:3])}")

            context_parts.append('\n'.join(parts))

        return '\n\n'.join(context_parts)

    def index_products(self, products: List[Dict[str, Any]]) -> bool:
        """
        Indexa productos en RAG

        Args:
            products: Lista de productos a indexar

        Returns:
            True si se indexó correctamente
        """
        if not self.is_enabled or not self.rag_service:
            logger.warning("⚠️ RAG no habilitado, no se pueden indexar productos")
            return False

        try:
            count = self.rag_service.index_products(products)
            logger.info(f"✅ Indexados {count} productos en RAG")
            return count > 0
        except Exception as e:
            logger.error(f"❌ Error indexando productos: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del RAG"""
        if not self.is_enabled or not self.rag_service:
            return {'enabled': False}

        stats = self.rag_service.get_stats()
        stats['enabled'] = True
        return stats


# ============================================================
# FACTORY FUNCTION
# ============================================================

def create_rag_integrator(
    tenant_id: str,
    tenant_config: Dict[str, Any]
) -> Optional[RAGIntegrator]:
    """
    Crea integrador RAG si corresponde

    Args:
        tenant_id: ID del tenant
        tenant_config: Configuración del tenant

    Returns:
        RAGIntegrator o None si no aplica
    """
    try:
        integrator = RAGIntegrator(tenant_id, tenant_config)
        if integrator.is_enabled:
            return integrator
        else:
            return None
    except Exception as e:
        logger.error(f"❌ Error creando RAG integrator: {e}")
        return None
