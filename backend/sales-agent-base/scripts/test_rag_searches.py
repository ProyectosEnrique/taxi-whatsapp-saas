#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de pruebas RAG - 20 busquedas reales de clientes

Simula consultas reales que llegarian por WhatsApp
"""

import sys
from pathlib import Path
import time

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from services.pharmacy_rag import get_pharmacy_rag
import logging

# Configurar logging
logging.basicConfig(
    level=logging.WARNING,
    format='%(message)s'
)

# 20 busquedas reales que haria un cliente
TEST_QUERIES = [
    # Busquedas por sintomas (10)
    "me duele la cabeza",
    "tengo fiebre alta",
    "me duele el estomago",
    "tengo tos seca",
    "tengo gripa",
    "me siento mareado",
    "tengo diarrea",
    "me duelen los musculos",
    "tengo alergia y comezon",
    "tengo dolor de garganta",

    # Busquedas por nombre de medicamento (5)
    "necesito paracetamol",
    "tienes ibuprofeno",
    "busco amoxicilina",
    "hay omeprazol",
    "me das loratadina",

    # Busquedas complejas (3)
    "algo para el dolor de cabeza pero tengo gastritis",
    "necesito algo para la gripa sin azucar",
    "tienes vitaminas para adultos mayores",

    # Busquedas especificas (2)
    "necesito antibiotico para infeccion",
    "algo para bajar la fiebre para ninos"
]


def format_result(idx, product, score):
    """Formatea un resultado para display"""
    rec = "[!] REQUIERE RECETA" if product.get('requires_prescription') else "[OK] Sin receta"
    ctrl = " [CONTROLADA]" if product.get('controlled_substance') else ""
    stock_status = f"Stock: {product.get('stock', 0)}" if product.get('stock', 0) > 0 else "[X] Sin stock"

    return f"""
  {idx}. {product.get('name')}
     Precio: ${product.get('price', 0):.2f}
     Score: {score:.3f}
     Categoria: {product.get('category')}
     {rec}{ctrl}
     {stock_status}
"""


def test_single_query(rag, query, query_num):
    """Prueba una sola busqueda"""
    print("\n" + "="*70)
    print(f"[BUSQUEDA #{query_num}]: \"{query}\"")
    print("="*70)

    start_time = time.time()

    # Buscar (threshold bajo para capturar más resultados)
    results = rag.search(query, top_k=3, min_similarity=0.15)

    elapsed = (time.time() - start_time) * 1000  # ms

    if results:
        print(f"\n[OK] Encontrados {len(results)} resultados en {elapsed:.0f}ms:")

        for idx, result in enumerate(results, 1):
            print(format_result(idx, result.product.to_dict(), result.similarity_score))
    else:
        print(f"\n[X] No se encontraron resultados ({elapsed:.0f}ms)")


def test_all_queries():
    """Ejecuta todas las pruebas"""
    print("\n" + "="*70)
    print("RAG PHARMACY - 20 BUSQUEDAS DE PRUEBA")
    print("="*70 + "\n")

    # Inicializar RAG
    print("[*] Inicializando RAG con 1,335 productos...")
    rag = get_pharmacy_rag("tenant_pharmacy_001")

    if not rag or not rag.is_ready:
        print("[X] Error: RAG no esta listo")
        return

    stats = rag.get_stats()
    print(f"[OK] RAG listo: {stats.get('total_products', 0)} productos indexados")
    print(f"[*] Coleccion: {stats.get('collection_name', '')}")

    # Ejecutar todas las busquedas
    total_start = time.time()

    for i, query in enumerate(TEST_QUERIES, 1):
        test_single_query(rag, query, i)
        time.sleep(0.5)  # Pausa para legibilidad

    # Resumen final
    total_elapsed = time.time() - total_start

    print("\n" + "="*70)
    print("RESUMEN DE PRUEBAS")
    print("="*70)
    print(f"[OK] Total busquedas: {len(TEST_QUERIES)}")
    print(f"[*] Tiempo total: {total_elapsed:.2f}s")
    print(f"[*] Promedio por busqueda: {(total_elapsed / len(TEST_QUERIES)):.2f}s")
    print("="*70 + "\n")


def test_special_cases():
    """Prueba casos especiales (filtros, edad, etc.)"""
    print("\n" + "="*70)
    print("PRUEBAS ESPECIALES - FILTROS Y RESTRICCIONES")
    print("="*70 + "\n")

    rag = get_pharmacy_rag("tenant_pharmacy_001")

    if not rag or not rag.is_ready:
        print("[X] RAG no disponible")
        return

    # Test 1: Solo medicamentos sin receta
    print("\n" + "="*70)
    print("[TEST ESPECIAL 1]: Medicamentos SIN receta para dolor")
    print("="*70)

    results = rag.search(
        "dolor",
        top_k=5,
        filters={"requires_prescription": False}
    )

    if results:
        print(f"\n[OK] Encontrados {len(results)} medicamentos sin receta:")
        for idx, result in enumerate(results[:3], 1):
            print(format_result(idx, result.product.to_dict(), result.similarity_score))

    # Test 2: Busqueda con restriccion de edad
    print("\n" + "="*70)
    print("[TEST ESPECIAL 2]: Medicamentos para fiebre - Paciente 8 anos")
    print("="*70)

    results = rag.search_with_age_restriction(
        query="fiebre",
        age=8,
        top_k=5
    )

    if results:
        print(f"\n[OK] Encontrados {len(results)} medicamentos apropiados:")
        for idx, result in enumerate(results[:3], 1):
            product = result.product.to_dict()
            print(format_result(idx, product, result.similarity_score))
            print(f"     [OK] Edad minima: {product.get('min_age', 0)} anos")

    # Test 3: Busqueda de genericos
    print("\n" + "="*70)
    print("[TEST ESPECIAL 3]: Alternativas genericas")
    print("="*70)

    results = rag.find_generic_alternatives("Tempra", top_k=3)

    if results:
        print(f"\n[OK] Encontradas {len(results)} alternativas genericas:")
        for idx, result in enumerate(results, 1):
            product = result.product.to_dict()
            print(format_result(idx, product, result.similarity_score))
            print(f"     [*] Generico: {product.get('generic_name', 'N/A')}")
    else:
        print("\n[!] No se encontraron alternativas genericas especificas")


def main():
    """Ejecuta todas las pruebas"""
    try:
        # Pruebas normales (20 busquedas)
        test_all_queries()

        # Pruebas especiales (filtros)
        test_special_cases()

        print("\n" + "="*70)
        print("TODAS LAS PRUEBAS COMPLETADAS")
        print("="*70 + "\n")

    except KeyboardInterrupt:
        print("\n\n[!] Pruebas interrumpidas por el usuario")
    except Exception as e:
        print(f"\n\n[X] Error durante las pruebas: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
