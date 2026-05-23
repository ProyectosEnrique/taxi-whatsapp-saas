#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para eliminar colección con L2 y recrear con cosine similarity
"""

import sys
from pathlib import Path

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

import chromadb
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_collection():
    """Elimina colección antigua y recrea con cosine similarity"""
    try:
        # Conectar a ChromaDB
        persist_dir = Path(__file__).parent.parent / 'data' / 'chroma' / 'tenant_pharmacy_001'
        client = chromadb.PersistentClient(path=str(persist_dir))

        collection_name = "pharmacy_tenant_pharmacy_001"

        # Eliminar colección existente
        logger.info(f"Eliminando colección '{collection_name}'...")
        try:
            client.delete_collection(collection_name)
            logger.info("✅ Colección eliminada")
        except Exception as e:
            logger.info(f"Colección no existía: {e}")

        # Crear nueva colección con cosine similarity
        logger.info("Creando nueva colección con cosine similarity...")
        collection = client.create_collection(
            name=collection_name,
            metadata={
                "description": "Productos farmacéuticos para tenant_pharmacy_001",
                "hnsw:space": "cosine"
            }
        )
        logger.info("✅ Colección creada con cosine similarity")

        # Verificar configuración
        metadata = collection.metadata
        logger.info(f"Metadata: {metadata}")

        logger.info("\n✅ Listo para reindexar")

    except Exception as e:
        logger.error(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    fix_collection()
