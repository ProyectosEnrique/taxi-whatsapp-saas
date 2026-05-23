#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de prueba para Pharmacy RAG

Demuestra:
1. Indexación de productos farmacéuticos
2. Búsqueda por síntomas
3. Búsqueda de genéricos
4. Filtrado por metadata (receta, edad)
"""

import sys
from pathlib import Path

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from services.pharmacy_rag import PharmacyRAGService
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================
# PRODUCTOS DE EJEMPLO
# ============================================================

SAMPLE_PRODUCTS = [
    {
        "id": "1",
        "name": "Paracetamol 500mg",
        "description": "Analgésico y antipirético para dolor leve a moderado y fiebre",
        "price": 45.00,
        "category": "Analgésicos",
        "generic_name": "Paracetamol",
        "brand_name": None,
        "active_ingredient": "Paracetamol",
        "dosage": "500mg",
        "presentation": "Caja con 20 tabletas",
        "requires_prescription": False,
        "controlled_substance": False,
        "min_age": 12,
        "symptoms": ["dolor de cabeza", "fiebre", "dolor muscular", "malestar general"],
        "contraindications": ["enfermedad hepática severa"],
        "side_effects": ["náusea (raro)", "reacciones alérgicas (muy raro)"],
        "stock": 150,
        "available": True
    },
    {
        "id": "2",
        "name": "Tempra 500mg",
        "description": "Marca comercial de paracetamol, analgésico y antipirético",
        "price": 85.00,
        "category": "Analgésicos",
        "generic_name": "Paracetamol",
        "brand_name": "Tempra",
        "active_ingredient": "Paracetamol",
        "dosage": "500mg",
        "presentation": "Caja con 10 tabletas",
        "requires_prescription": False,
        "controlled_substance": False,
        "min_age": 12,
        "symptoms": ["dolor de cabeza", "fiebre", "dolor dental", "dolor de garganta"],
        "contraindications": ["enfermedad hepática"],
        "side_effects": ["náusea leve"],
        "stock": 80,
        "available": True
    },
    {
        "id": "3",
        "name": "Ibuprofeno 400mg",
        "description": "Antiinflamatorio no esteroideo para dolor e inflamación",
        "price": 65.00,
        "category": "Antiinflamatorios",
        "generic_name": "Ibuprofeno",
        "brand_name": None,
        "active_ingredient": "Ibuprofeno",
        "dosage": "400mg",
        "presentation": "Caja con 20 tabletas",
        "requires_prescription": False,
        "controlled_substance": False,
        "min_age": 18,
        "symptoms": ["dolor muscular", "inflamación", "dolor articular", "fiebre alta", "dolor menstrual"],
        "contraindications": ["úlcera gástrica activa", "enfermedad renal severa", "embarazo tercer trimestre"],
        "side_effects": ["malestar estomacal", "náusea", "dolor de cabeza (raro)"],
        "interactions": ["anticoagulantes", "aspirina", "corticosteroides"],
        "stock": 120,
        "available": True
    },
    {
        "id": "4",
        "name": "Loratadina 10mg",
        "description": "Antihistamínico para alergias estacionales y síntomas de alergia",
        "price": 55.00,
        "category": "Antihistamínicos",
        "generic_name": "Loratadina",
        "brand_name": None,
        "active_ingredient": "Loratadina",
        "dosage": "10mg",
        "presentation": "Caja con 10 tabletas",
        "requires_prescription": False,
        "controlled_substance": False,
        "min_age": 6,
        "symptoms": ["alergia", "comezón", "estornudos", "rinitis alérgica", "urticaria", "ojos llorosos"],
        "contraindications": ["hipersensibilidad a loratadina"],
        "side_effects": ["somnolencia leve", "boca seca", "dolor de cabeza"],
        "stock": 90,
        "available": True
    },
    {
        "id": "5",
        "name": "Omeprazol 20mg",
        "description": "Inhibidor de bomba de protones para acidez y úlceras gástricas",
        "price": 120.00,
        "category": "Gastroprotectores",
        "generic_name": "Omeprazol",
        "brand_name": None,
        "active_ingredient": "Omeprazol",
        "dosage": "20mg",
        "presentation": "Caja con 14 cápsulas",
        "requires_prescription": True,
        "controlled_substance": False,
        "min_age": 18,
        "symptoms": ["acidez estomacal", "reflujo", "gastritis", "úlcera gástrica", "ardor de estómago"],
        "contraindications": ["alergia a omeprazol"],
        "side_effects": ["dolor de cabeza", "náusea", "diarrea", "dolor abdominal"],
        "interactions": ["clopidogrel", "warfarina"],
        "stock": 60,
        "available": True
    },
    {
        "id": "6",
        "name": "Amoxicilina 500mg",
        "description": "Antibiótico de amplio espectro para infecciones bacterianas",
        "price": 180.00,
        "category": "Antibióticos",
        "generic_name": "Amoxicilina",
        "brand_name": None,
        "active_ingredient": "Amoxicilina",
        "dosage": "500mg",
        "presentation": "Caja con 12 cápsulas",
        "requires_prescription": True,
        "controlled_substance": False,
        "min_age": 12,
        "symptoms": ["infección respiratoria", "infección de oído", "infección urinaria", "sinusitis", "faringitis"],
        "contraindications": ["alergia a penicilinas", "mononucleosis"],
        "side_effects": ["diarrea", "náusea", "sarpullido alérgico"],
        "interactions": ["anticonceptivos orales", "warfarina"],
        "stock": 45,
        "available": True
    },
    {
        "id": "7",
        "name": "Losartán 50mg",
        "description": "Antihipertensivo para control de presión arterial alta",
        "price": 95.00,
        "category": "Antihipertensivos",
        "generic_name": "Losartán",
        "brand_name": None,
        "active_ingredient": "Losartán potásico",
        "dosage": "50mg",
        "presentation": "Caja con 30 tabletas",
        "requires_prescription": True,
        "controlled_substance": False,
        "min_age": 18,
        "symptoms": ["presión arterial alta", "hipertensión"],
        "contraindications": ["embarazo", "hiperpotasemia severa"],
        "side_effects": ["mareo", "fatiga", "hipotensión"],
        "interactions": ["potasio", "AINEs", "diuréticos"],
        "stock": 70,
        "available": True
    },
    {
        "id": "8",
        "name": "Metformina 850mg",
        "description": "Antidiabético oral para control de diabetes tipo 2",
        "price": 110.00,
        "category": "Antidiabéticos",
        "generic_name": "Metformina",
        "brand_name": None,
        "active_ingredient": "Metformina clorhidrato",
        "dosage": "850mg",
        "presentation": "Caja con 30 tabletas",
        "requires_prescription": True,
        "controlled_substance": False,
        "min_age": 18,
        "symptoms": ["diabetes tipo 2", "glucosa alta"],
        "contraindications": ["insuficiencia renal", "insuficiencia hepática", "acidosis metabólica"],
        "side_effects": ["diarrea", "náusea", "dolor abdominal", "sabor metálico"],
        "interactions": ["alcohol", "contraste yodado"],
        "stock": 55,
        "available": True
    },
    {
        "id": "9",
        "name": "Clonazepam 2mg",
        "description": "Ansiolítico y anticonvulsivo para trastornos de ansiedad",
        "price": 220.00,
        "category": "Ansiolíticos",
        "generic_name": "Clonazepam",
        "brand_name": None,
        "active_ingredient": "Clonazepam",
        "dosage": "2mg",
        "presentation": "Caja con 20 tabletas",
        "requires_prescription": True,
        "controlled_substance": True,
        "min_age": 18,
        "symptoms": ["ansiedad", "ataques de pánico", "convulsiones", "insomnio severo"],
        "contraindications": ["insuficiencia respiratoria severa", "glaucoma de ángulo estrecho"],
        "side_effects": ["somnolencia", "mareo", "fatiga", "dependencia (uso prolongado)"],
        "interactions": ["alcohol", "otros depresores del SNC"],
        "stock": 30,
        "available": True
    },
    {
        "id": "10",
        "name": "Dipirona 500mg",
        "description": "Analgésico y antipirético potente para dolor moderado a severo",
        "price": 38.00,
        "category": "Analgésicos",
        "generic_name": "Dipirona (Metamizol)",
        "brand_name": None,
        "active_ingredient": "Metamizol sódico",
        "dosage": "500mg",
        "presentation": "Caja con 10 tabletas",
        "requires_prescription": False,
        "controlled_substance": False,
        "min_age": 15,
        "symptoms": ["dolor intenso", "fiebre alta", "dolor postoperatorio", "cólico"],
        "contraindications": ["porfiria aguda", "deficiencia de G6PD", "embarazo primer trimestre"],
        "side_effects": ["reacción alérgica", "agranulocitosis (muy raro)"],
        "stock": 100,
        "available": True
    }
]


def test_indexing():
    """Prueba indexación de productos"""
    logger.info("=" * 60)
    logger.info("TEST 1: INDEXACIÓN DE PRODUCTOS")
    logger.info("=" * 60)

    rag = PharmacyRAGService(tenant_id="tenant_pharmacy_001")

    if not rag.is_ready:
        logger.error("❌ RAG no está listo. Verificar instalación de chromadb y sentence-transformers")
        return None

    # Limpiar colección anterior
    logger.info("Limpiando colección anterior...")
    rag.clear_collection()

    # Indexar productos
    logger.info(f"Indexando {len(SAMPLE_PRODUCTS)} productos...")
    count = rag.index_products(SAMPLE_PRODUCTS)

    logger.info(f"✅ Indexados {count} productos")
    logger.info(f"Estadísticas: {rag.get_stats()}")

    return rag


def test_search_by_symptom(rag: PharmacyRAGService):
    """Prueba búsqueda por síntoma"""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 2: BÚSQUEDA POR SÍNTOMA")
    logger.info("=" * 60)

    test_queries = [
        "me duele la cabeza",
        "tengo fiebre alta",
        "tengo alergia y comezón",
        "dolor de estómago y acidez",
        "infección de garganta"
    ]

    for query in test_queries:
        logger.info(f"\n🔍 Búsqueda: '{query}'")
        results = rag.search_by_symptom(query, top_k=3)

        if results:
            for i, result in enumerate(results[:3], 1):
                logger.info(f"  {i}. {result.product.name} - ${result.product.price:.2f}")
                logger.info(f"     Similitud: {result.similarity_score:.3f}")
                logger.info(f"     Para: {', '.join(result.product.symptoms[:3])}")
                if result.product.requires_prescription:
                    logger.info("     ⚠️ Requiere receta")
        else:
            logger.info("  ❌ No se encontraron resultados")


def test_search_generics(rag: PharmacyRAGService):
    """Prueba búsqueda de genéricos"""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 3: BÚSQUEDA DE GENÉRICOS")
    logger.info("=" * 60)

    logger.info("\n🔍 Buscando genérico de 'Tempra'")
    results = rag.find_generic_alternatives("Tempra", top_k=3)

    if results:
        for i, result in enumerate(results, 1):
            logger.info(f"  {i}. {result.product.name} - ${result.product.price:.2f}")
            logger.info(f"     Genérico: {result.product.generic_name}")
            logger.info(f"     Ahorro: ${85.00 - result.product.price:.2f}")
    else:
        logger.info("  ❌ No se encontraron alternativas genéricas")


def test_advanced_search(rag: PharmacyRAGService):
    """Prueba búsquedas avanzadas con filtros"""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 4: BÚSQUEDA AVANZADA CON FILTROS")
    logger.info("=" * 60)

    # Búsqueda 1: Medicamentos sin receta para dolor
    logger.info("\n🔍 Medicamentos SIN receta para dolor")
    results = rag.search(
        query="dolor",
        top_k=5,
        filters={"requires_prescription": False}
    )

    if results:
        for i, result in enumerate(results[:3], 1):
            logger.info(f"  {i}. {result.product.name} - ${result.product.price:.2f}")
            logger.info(f"     Sin receta ✅")

    # Búsqueda 2: Medicamentos para adultos mayores (sin sustancias controladas)
    logger.info("\n🔍 Medicamentos seguros (sin sustancias controladas)")
    results = rag.search(
        query="dolor muscular",
        top_k=5,
        filters={"controlled_substance": False}
    )

    if results:
        for i, result in enumerate(results[:3], 1):
            logger.info(f"  {i}. {result.product.name}")
            logger.info(f"     No controlado ✅")


def test_age_restrictions(rag: PharmacyRAGService):
    """Prueba restricciones de edad"""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 5: RESTRICCIONES DE EDAD")
    logger.info("=" * 60)

    # Paciente de 10 años con fiebre
    logger.info("\n🔍 Medicamentos para fiebre - Paciente 10 años")
    results = rag.search_with_age_restriction(
        query="fiebre",
        age=10,
        top_k=5
    )

    if results:
        for i, result in enumerate(results, 1):
            logger.info(f"  {i}. {result.product.name}")
            logger.info(f"     Edad mínima: {result.product.min_age} años ✅")


def test_complex_query(rag: PharmacyRAGService):
    """Prueba consultas complejas"""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 6: CONSULTAS COMPLEJAS")
    logger.info("=" * 60)

    complex_queries = [
        "necesito algo para el dolor de cabeza pero tengo gastritis",
        "tengo infección pero soy alérgico a la penicilina",
        "algo para la alergia que no me dé sueño"
    ]

    for query in complex_queries:
        logger.info(f"\n🔍 '{query}'")
        results = rag.search(query, top_k=3)

        if results:
            for i, result in enumerate(results[:2], 1):
                logger.info(f"  {i}. {result.product.name}")
                logger.info(f"     Contraind: {', '.join(result.product.contraindications[:2])}")


def main():
    """Ejecuta todos los tests"""
    logger.info("\n" + "🧪" * 30)
    logger.info("PHARMACY RAG - SUITE DE PRUEBAS")
    logger.info("🧪" * 30 + "\n")

    # 1. Indexar productos
    rag = test_indexing()

    if not rag:
        logger.error("❌ No se pudo inicializar RAG. Abortando tests.")
        return

    # 2. Búsqueda por síntoma
    test_search_by_symptom(rag)

    # 3. Búsqueda de genéricos
    test_search_generics(rag)

    # 4. Búsqueda avanzada con filtros
    test_advanced_search(rag)

    # 5. Restricciones de edad
    test_age_restrictions(rag)

    # 6. Consultas complejas
    test_complex_query(rag)

    logger.info("\n" + "=" * 60)
    logger.info("✅ TODOS LOS TESTS COMPLETADOS")
    logger.info("=" * 60)

    # Mostrar estadísticas finales
    stats = rag.get_stats()
    logger.info(f"\n📊 Estadísticas finales:")
    logger.info(f"   Total productos: {stats.get('total_products', 0)}")
    logger.info(f"   Colección: {stats.get('collection_name', '')}")
    logger.info(f"   Directorio: {stats.get('persist_directory', '')}")


if __name__ == "__main__":
    main()
