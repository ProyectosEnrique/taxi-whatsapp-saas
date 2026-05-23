#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pharmacy RAG Service - Retrieval Augmented Generation para Farmacia

Sistema RAG completo que combina:
1. ChromaDB para almacenamiento vectorial persistente
2. Sentence Transformers para embeddings multilingües
3. LLM cascade para generación de respuestas
4. Metadata filtering para prescripciones y sustancias controladas
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from pathlib import Path
import json

logger = logging.getLogger(__name__)

# ChromaDB
try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    logger.warning("⚠️ chromadb no disponible. Instalar: pip install chromadb")

# Sentence Transformers
try:
    from sentence_transformers import SentenceTransformer
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    logger.warning("⚠️ sentence-transformers no disponible")


@dataclass
class PharmacyProduct:
    """Producto farmacéutico con metadata completa"""
    id: str
    name: str
    description: str
    price: float
    category: str

    # Metadata farmacéutica
    requires_prescription: bool = False
    controlled_substance: bool = False
    min_age: int = 0
    generic_name: Optional[str] = None
    brand_name: Optional[str] = None
    dosage: Optional[str] = None
    presentation: Optional[str] = None
    active_ingredient: Optional[str] = None
    contraindications: Optional[List[str]] = None
    side_effects: Optional[List[str]] = None
    interactions: Optional[List[str]] = None
    symptoms: Optional[List[str]] = None  # Para qué síntomas sirve

    # Stock
    stock: int = 0
    available: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'price': self.price,
            'category': self.category,
            'requires_prescription': self.requires_prescription,
            'controlled_substance': self.controlled_substance,
            'min_age': self.min_age,
            'generic_name': self.generic_name,
            'brand_name': self.brand_name,
            'dosage': self.dosage,
            'presentation': self.presentation,
            'active_ingredient': self.active_ingredient,
            'contraindications': self.contraindications or [],
            'side_effects': self.side_effects or [],
            'interactions': self.interactions or [],
            'symptoms': self.symptoms or [],
            'stock': self.stock,
            'available': self.available
        }


@dataclass
class RAGSearchResult:
    """Resultado de búsqueda RAG"""
    product: PharmacyProduct
    similarity_score: float
    matched_by: str  # "name", "description", "symptoms", "active_ingredient"
    llm_recommendation: Optional[str] = None  # Respuesta generada por LLM


class PharmacyRAGService:
    """
    Servicio RAG completo para farmacia

    Features:
    - Almacenamiento persistente con ChromaDB
    - Embeddings multilingües (español médico)
    - Búsqueda por síntomas, nombres comerciales, genéricos
    - Filtrado por metadata (receta, edad, sustancias controladas)
    - Generación de respuestas con LLM
    """

    def __init__(
        self,
        tenant_id: str,
        persist_directory: Optional[str] = None,
        model_name: str = "paraphrase-multilingual-MiniLM-L12-v2",
        collection_name: Optional[str] = None
    ):
        """
        Inicializa el servicio RAG

        Args:
            tenant_id: ID del tenant (farmacia)
            persist_directory: Directorio para persistir ChromaDB
            model_name: Modelo de sentence-transformers
            collection_name: Nombre de la colección (default: pharmacy_{tenant_id})
        """
        self.tenant_id = tenant_id
        self.model_name = model_name
        self.collection_name = collection_name or f"pharmacy_{tenant_id}"

        # Directorio de persistencia
        if persist_directory is None:
            base_dir = Path(__file__).parent.parent.parent / 'data' / 'chroma'
            persist_directory = str(base_dir / tenant_id)

        self.persist_directory = persist_directory
        Path(persist_directory).mkdir(parents=True, exist_ok=True)

        # Inicializar componentes
        self.chroma_client = None
        self.collection = None
        self.embedding_model = None
        self.is_ready = False

        self._initialize()

    def _initialize(self):
        """Inicializa ChromaDB y modelo de embeddings"""
        if not CHROMADB_AVAILABLE or not TRANSFORMERS_AVAILABLE:
            logger.error("❌ RAG no disponible: falta chromadb o sentence-transformers")
            return

        try:
            # 1. Inicializar ChromaDB
            logger.info(f"[RAG] Inicializando ChromaDB en {self.persist_directory}")
            self.chroma_client = chromadb.PersistentClient(
                path=self.persist_directory,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )

            # 2. Cargar o crear colección
            try:
                self.collection = self.chroma_client.get_collection(self.collection_name)
                count = self.collection.count()
                logger.info(f"✅ Colección '{self.collection_name}' cargada con {count} productos")
            except Exception:
                self.collection = self.chroma_client.create_collection(
                    name=self.collection_name,
                    metadata={
                        "description": f"Productos farmacéuticos para {self.tenant_id}",
                        "hnsw:space": "cosine"  # Usar cosine similarity para búsqueda semántica
                    }
                )
                logger.info(f"✅ Colección '{self.collection_name}' creada con cosine similarity")

            # 3. Cargar modelo de embeddings
            logger.info(f"[RAG] Cargando modelo: {self.model_name}")
            self.embedding_model = SentenceTransformer(self.model_name)

            self.is_ready = True
            logger.info("✅ PharmacyRAG inicializado correctamente")

        except Exception as e:
            logger.error(f"❌ Error inicializando RAG: {e}")
            self.is_ready = False

    def index_products(self, products: List[Dict[str, Any]]) -> int:
        """
        Indexa productos en ChromaDB

        Args:
            products: Lista de productos (diccionarios)

        Returns:
            Número de productos indexados
        """
        if not self.is_ready:
            logger.error("❌ RAG no está listo")
            return 0

        try:
            indexed = 0
            batch_size = 100

            for i in range(0, len(products), batch_size):
                batch = products[i:i + batch_size]

                documents = []
                metadatas = []
                ids = []
                embeddings = []

                for product in batch:
                    # Crear PharmacyProduct
                    p = self._dict_to_pharmacy_product(product)

                    # Crear documento rico para embeddings
                    doc = self._create_document_text(p)
                    documents.append(doc)

                    # Metadata para filtering
                    metadata = {
                        'name': p.name,
                        'category': p.category,
                        'price': p.price,
                        'requires_prescription': p.requires_prescription,
                        'controlled_substance': p.controlled_substance,
                        'min_age': p.min_age,
                        'generic_name': p.generic_name or "",
                        'brand_name': p.brand_name or "",
                        'active_ingredient': p.active_ingredient or "",
                        'available': p.available,
                        'stock': p.stock,
                        'product_json': json.dumps(p.to_dict())  # Producto completo
                    }
                    metadatas.append(metadata)
                    ids.append(str(p.id))

                    # Generar embedding
                    embedding = self.embedding_model.encode(doc)
                    embeddings.append(embedding.tolist())

                # Agregar batch a ChromaDB
                self.collection.add(
                    documents=documents,
                    metadatas=metadatas,
                    ids=ids,
                    embeddings=embeddings
                )

                indexed += len(batch)
                logger.info(f"[RAG] Indexados {indexed}/{len(products)} productos")

            logger.info(f"✅ Indexación completa: {indexed} productos")
            return indexed

        except Exception as e:
            logger.error(f"❌ Error indexando productos: {e}")
            return 0

    def _create_document_text(self, product: PharmacyProduct) -> str:
        """
        Crea texto rico para embedding que incluye toda la información relevante
        """
        parts = []

        # Nombre comercial y genérico
        parts.append(f"Nombre: {product.name}")
        if product.generic_name:
            parts.append(f"Genérico: {product.generic_name}")
        if product.brand_name:
            parts.append(f"Marca: {product.brand_name}")

        # Descripción
        if product.description:
            parts.append(f"Descripción: {product.description}")

        # Ingrediente activo
        if product.active_ingredient:
            parts.append(f"Ingrediente activo: {product.active_ingredient}")

        # Síntomas (muy importante para búsqueda)
        if product.symptoms:
            parts.append(f"Para: {', '.join(product.symptoms)}")

        # Presentación y dosis
        if product.presentation:
            parts.append(f"Presentación: {product.presentation}")
        if product.dosage:
            parts.append(f"Dosis: {product.dosage}")

        # Categoría
        parts.append(f"Categoría: {product.category}")

        return ". ".join(parts)

    def search(
        self,
        query: str,
        top_k: int = 5,
        min_similarity: float = 0.3,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[RAGSearchResult]:
        """
        Búsqueda semántica con filtros

        Args:
            query: Consulta del usuario ("necesito algo para el dolor de cabeza")
            top_k: Número de resultados
            min_similarity: Similitud mínima (0-1)
            filters: Filtros metadata (ej: {"requires_prescription": False})

        Returns:
            Lista de RAGSearchResult
        """
        if not self.is_ready:
            logger.error("❌ RAG no está listo")
            return []

        try:
            # Generar embedding de la consulta
            query_embedding = self.embedding_model.encode(query).tolist()

            # Construir where clause para filtros
            where_clause = {}
            if filters:
                for key, value in filters.items():
                    if isinstance(value, bool):
                        where_clause[key] = value
                    elif isinstance(value, (int, float)):
                        where_clause[key] = value

            # Buscar en ChromaDB
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k * 2,  # Buscar más para filtrar después
                where=where_clause if where_clause else None,
                include=["metadatas", "distances", "documents"]
            )

            # Procesar resultados
            search_results = []

            if results['ids'] and len(results['ids'][0]) > 0:
                for i, (id_, metadata, distance, document) in enumerate(zip(
                    results['ids'][0],
                    results['metadatas'][0],
                    results['distances'][0],
                    results['documents'][0]
                )):
                    # ChromaDB con cosine distance: 0 = idéntico, 2 = opuesto
                    # Convertir a similarity: 1 = idéntico, 0 = no relacionado
                    similarity = 1.0 - (distance / 2.0)

                    if similarity < min_similarity:
                        continue

                    # Reconstruir producto desde metadata
                    product_data = json.loads(metadata['product_json'])
                    product = self._dict_to_pharmacy_product(product_data)

                    # Determinar qué campo matcheó
                    matched_by = self._determine_match_type(query, document)

                    search_results.append(RAGSearchResult(
                        product=product,
                        similarity_score=similarity,
                        matched_by=matched_by,
                        llm_recommendation=None
                    ))

                    if len(search_results) >= top_k:
                        break

            logger.info(f"[RAG] Encontrados {len(search_results)} productos para: '{query}'")
            return search_results

        except Exception as e:
            logger.error(f"❌ Error en búsqueda RAG: {e}")
            return []

    def search_by_symptom(self, symptom: str, top_k: int = 5) -> List[RAGSearchResult]:
        """
        Búsqueda específica por síntoma

        Args:
            symptom: Síntoma ("dolor de cabeza", "tos", "fiebre")
            top_k: Número de resultados
        """
        query = f"medicamento para {symptom}"
        return self.search(query, top_k=top_k, min_similarity=0.4)

    def find_generic_alternatives(self, brand_name: str, top_k: int = 3) -> List[RAGSearchResult]:
        """
        Encuentra alternativas genéricas de un medicamento de marca
        """
        query = f"genérico de {brand_name}"
        results = self.search(query, top_k=top_k * 2, min_similarity=0.5)

        # Filtrar solo genéricos
        generics = [r for r in results if r.product.generic_name and not r.product.brand_name]
        return generics[:top_k]

    def search_with_age_restriction(
        self,
        query: str,
        age: int,
        top_k: int = 5
    ) -> List[RAGSearchResult]:
        """
        Búsqueda considerando restricciones de edad
        """
        # Buscar primero sin filtro
        results = self.search(query, top_k=top_k * 2)

        # Filtrar por edad
        filtered = [r for r in results if r.product.min_age <= age]

        return filtered[:top_k]

    def _determine_match_type(self, query: str, document: str) -> str:
        """Determina qué tipo de campo matcheó mejor"""
        query_lower = query.lower()
        doc_lower = document.lower()

        if "síntoma" in doc_lower or "para:" in doc_lower:
            return "symptoms"
        elif "genérico:" in doc_lower and any(word in query_lower for word in ["genérico", "similar", "alternativa"]):
            return "generic_name"
        elif "ingrediente activo:" in doc_lower:
            return "active_ingredient"
        elif "nombre:" in doc_lower:
            return "name"
        else:
            return "description"

    def _dict_to_pharmacy_product(self, data: Dict[str, Any]) -> PharmacyProduct:
        """Convierte diccionario a PharmacyProduct"""
        return PharmacyProduct(
            id=str(data.get('id', '')),
            name=data.get('name', ''),
            description=data.get('description', ''),
            price=float(data.get('price', 0)),
            category=data.get('category', ''),
            requires_prescription=data.get('requires_prescription', False),
            controlled_substance=data.get('controlled_substance', False),
            min_age=data.get('min_age', 0),
            generic_name=data.get('generic_name'),
            brand_name=data.get('brand_name'),
            dosage=data.get('dosage'),
            presentation=data.get('presentation'),
            active_ingredient=data.get('active_ingredient'),
            contraindications=data.get('contraindications', []),
            side_effects=data.get('side_effects', []),
            interactions=data.get('interactions', []),
            symptoms=data.get('symptoms', []),
            stock=data.get('stock', 0),
            available=data.get('available', True)
        )

    def clear_collection(self):
        """Limpia la colección (útil para reindexar)"""
        if self.collection:
            try:
                self.chroma_client.delete_collection(self.collection_name)
                self.collection = self.chroma_client.create_collection(
                    name=self.collection_name,
                    metadata={
                        "description": f"Productos farmacéuticos para {self.tenant_id}",
                        "hnsw:space": "cosine"  # Usar cosine similarity para búsqueda semántica
                    }
                )
                logger.info(f"✅ Colección '{self.collection_name}' limpiada")
            except Exception as e:
                logger.error(f"❌ Error limpiando colección: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas de la colección"""
        if not self.collection:
            return {}

        try:
            count = self.collection.count()
            return {
                'tenant_id': self.tenant_id,
                'collection_name': self.collection_name,
                'total_products': count,
                'persist_directory': self.persist_directory,
                'model_name': self.model_name,
                'is_ready': self.is_ready
            }
        except Exception as e:
            logger.error(f"❌ Error obteniendo stats: {e}")
            return {}


# ============================================================
# SINGLETON POR TENANT
# ============================================================

_rag_instances: Dict[str, PharmacyRAGService] = {}


def get_pharmacy_rag(tenant_id: str) -> Optional[PharmacyRAGService]:
    """
    Obtiene instancia de RAG para un tenant

    Args:
        tenant_id: ID del tenant

    Returns:
        PharmacyRAGService o None si no está disponible
    """
    global _rag_instances

    if tenant_id not in _rag_instances:
        try:
            _rag_instances[tenant_id] = PharmacyRAGService(tenant_id)
        except Exception as e:
            logger.error(f"❌ Error creando RAG para {tenant_id}: {e}")
            return None

    return _rag_instances[tenant_id]


def clear_rag_cache():
    """Limpia cache de instancias RAG"""
    global _rag_instances
    _rag_instances.clear()
    logger.info("🗑️ Cache de RAG limpiado")
