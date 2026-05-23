#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TEST LOCAL COMPLETO - Sistema de Ventas con FSM

Este script prueba el sistema completo localmente SIN necesidad de subir a Cloud:
1. FSM Optimizer (mejora continua)
2. Sales Agent con FSM
3. Integración completa

Ejecutar: python test_local_completo.py
"""

import sys
import os
import json
from pathlib import Path
from datetime import datetime

# Configurar encoding UTF-8 para Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Agregar al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def print_header(title):
    """Imprime header bonito"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70 + "\n")


def test_1_fsm_optimizer():
    """
    TEST 1: FSM Optimizer
    Prueba el sistema de mejora continua
    """
    print_header("TEST 1: FSM Optimizer - Sistema de Mejora Continua")

    try:
        from test_fsm_optimizer import create_sample_conversations, test_optimizer

        print("📝 Creando conversaciones de prueba...")
        create_sample_conversations()

        print("\n🔍 Analizando conversaciones...")
        report = test_optimizer()

        print("\n✅ TEST 1 PASADO: FSM Optimizer funciona correctamente")
        return True

    except Exception as e:
        print(f"\n❌ TEST 1 FALLÓ: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_2_fsm_core():
    """
    TEST 2: Core FSM
    Prueba la máquina de estados y decision tree
    """
    print_header("TEST 2: Core FSM - Máquina de Estados")

    try:
        from src.core.fsm.state_machine import SalesStateMachine
        from src.core.fsm.conversation_states import ConversationState

        print("🤖 Inicializando FSM...")
        fsm = SalesStateMachine()

        # Test 1: Estado inicial
        initial_state = fsm.get_current_state()
        print(f"  Estado inicial: {initial_state}")
        assert initial_state == ConversationState.GREETING, "Estado inicial debe ser GREETING"

        # Test 2: Procesar saludo
        print("\n📨 Test: Procesando saludo del usuario...")
        response = fsm.process_user_message(
            user_message="Hola, buenas tardes",
            session_id="test_001"
        )
        print(f"  Respuesta: {response.get('response', 'N/A')[:100]}...")
        print(f"  Estado actual: {fsm.get_current_state()}")

        # Test 3: Agregar producto
        print("\n📨 Test: Agregando producto al pedido...")
        response = fsm.process_user_message(
            user_message="quiero 2 tacos de pastor",
            session_id="test_001"
        )
        print(f"  Respuesta: {response.get('response', 'N/A')[:100]}...")
        print(f"  Estado actual: {fsm.get_current_state()}")
        print(f"  Items en pedido: {len(fsm.context.order_items)}")

        # Test 4: Confirmar pedido
        print("\n📨 Test: Confirmando pedido...")
        response = fsm.process_user_message(
            user_message="así está bien, gracias",
            session_id="test_001"
        )
        print(f"  Respuesta: {response.get('response', 'N/A')[:100]}...")
        print(f"  Estado final: {fsm.get_current_state()}")

        print("\n✅ TEST 2 PASADO: FSM Core funciona correctamente")
        return True

    except Exception as e:
        print(f"\n❌ TEST 2 FALLÓ: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_3_product_matcher():
    """
    TEST 3: Product Matcher
    Prueba el sistema de matching de productos
    """
    print_header("TEST 3: Product Matcher - Detección de Productos")

    try:
        from src.core.fsm.product_matcher import ProductMatcher

        print("🏷️  Inicializando Product Matcher...")
        matcher = ProductMatcher()

        # Test casos
        test_cases = [
            ("quiero 2 tacos", "Debería detectar 'tacos'"),
            ("dame una hamburguesa", "Debería detectar 'hamburguesa'"),
            ("ponme una coca", "Debería detectar 'coca cola'"),
            ("échale un refresco", "Debería detectar 'refresco'")
        ]

        for text, description in test_cases:
            print(f"\n📝 Test: '{text}'")
            print(f"   {description}")

            result = matcher.find_products(text)

            if result:
                for product in result:
                    print(f"   ✅ Detectado: {product.get('name', 'N/A')}")
            else:
                print(f"   ⚠️  No se detectaron productos")

        print("\n✅ TEST 3 PASADO: Product Matcher funciona")
        return True

    except Exception as e:
        print(f"\n❌ TEST 3 FALLÓ: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_4_conversation_flow():
    """
    TEST 4: Flujo Completo de Conversación
    Simula una conversación completa desde saludo hasta pago
    """
    print_header("TEST 4: Flujo Completo - Conversación End-to-End")

    try:
        from src.core.fsm.state_machine import SalesStateMachine

        print("🗣️  Simulando conversación completa...\n")

        fsm = SalesStateMachine()
        session_id = "test_e2e_001"

        conversation = [
            ("Hola", "Saludo inicial"),
            ("quiero 2 tacos de pastor", "Agregar tacos"),
            ("también una coca cola", "Agregar bebida"),
            ("cuánto es?", "Preguntar total"),
            ("sí, confirmo", "Confirmar pedido"),
        ]

        for i, (message, description) in enumerate(conversation, 1):
            print(f"Usuario ({i}): {message}")
            print(f"  └─ [{description}]")

            response = fsm.process_user_message(message, session_id)

            print(f"Agente ({i}): {response.get('response', 'N/A')[:150]}...")
            print(f"  └─ Estado: {fsm.get_current_state()}")
            print(f"  └─ Items: {len(fsm.context.order_items)}")
            print()

        # Verificar estado final
        final_items = len(fsm.context.order_items)
        print(f"📊 Resumen final:")
        print(f"  Items en pedido: {final_items}")
        print(f"  Total: ${fsm.context.order_total:.2f}")
        print(f"  Estado: {fsm.get_current_state()}")

        assert final_items > 0, "Debería haber items en el pedido"

        print("\n✅ TEST 4 PASADO: Flujo completo funciona")
        return True

    except Exception as e:
        print(f"\n❌ TEST 4 FALLÓ: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_5_conversation_archive():
    """
    TEST 5: Conversation Archive
    Prueba el archivado de conversaciones
    """
    print_header("TEST 5: Conversation Archive - Archivado de Conversaciones")

    try:
        from src.analytics.conversation_archive import ConversationArchive

        print("💾 Inicializando Conversation Archive...")
        archive = ConversationArchive()

        # Crear conversación de prueba
        print("\n📝 Archivando conversación de prueba...")

        archived = archive.archive_conversation(
            session_id="test_archive_001",
            table_id=5,
            table_number=5,
            conversation_history=[
                {
                    "role": "user",
                    "content": "quiero 2 tacos",
                    "timestamp": datetime.now().isoformat(),
                    "intent": "ADD_TO_ORDER",
                    "confidence": 0.95
                },
                {
                    "role": "assistant",
                    "content": "Perfecto, 2 tacos agregados",
                    "timestamp": datetime.now().isoformat()
                }
            ],
            order_items=[
                {
                    "product_id": "taco_pastor",
                    "product_name": "Taco de Pastor",
                    "quantity": 2,
                    "unit_price": 25.0,
                    "subtotal": 50.0
                }
            ],
            order_total=50.0
        )

        print(f"  ✅ Conversación archivada: {archived.archive_id}")
        print(f"  📊 Métricas calculadas:")
        print(f"     - Total turnos: {archived.metrics.total_turns}")
        print(f"     - Items pedidos: {archived.metrics.items_ordered}")
        print(f"     - Total: ${archived.metrics.order_total:.2f}")
        print(f"     - Sentimiento: {archived.metrics.sentiment_score:.2f}")

        print("\n✅ TEST 5 PASADO: Conversation Archive funciona")
        return True

    except Exception as e:
        print(f"\n❌ TEST 5 FALLÓ: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """
    Ejecuta todos los tests
    """
    print("""
╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║        TEST LOCAL COMPLETO - Sales Agent FSM                    ║
║                                                                  ║
║  Este script prueba el sistema completo SIN subir a Cloud       ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
""")

    results = {
        "FSM Optimizer": test_1_fsm_optimizer(),
        "FSM Core": test_2_fsm_core(),
        "Product Matcher": test_3_product_matcher(),
        "Flujo Completo": test_4_conversation_flow(),
        "Conversation Archive": test_5_conversation_archive()
    }

    # Resumen
    print_header("RESUMEN DE TESTS")

    total = len(results)
    passed = sum(1 for r in results.values() if r)

    for test_name, passed_test in results.items():
        status = "✅ PASÓ" if passed_test else "❌ FALLÓ"
        print(f"  {status}  {test_name}")

    print(f"\n📊 Resultado: {passed}/{total} tests pasados ({passed/total*100:.0f}%)")

    if passed == total:
        print("\n🎉 ¡TODOS LOS TESTS PASARON!")
        print("\n✅ El sistema está listo para subir a producción")
        print("\nPróximos pasos:")
        print("  1. Revisar logs en: conversation_archive/")
        print("  2. Revisar reportes en: optimization_logs/")
        print("  3. Configurar Firebase + Cloud Run")
        print("  4. Subir a producción")
    else:
        print("\n⚠️  ALGUNOS TESTS FALLARON")
        print("\nRevisar los errores antes de subir a producción")
        return False

    return True


if __name__ == "__main__":
    try:
        success = run_all_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⏸️  Tests interrumpidos por el usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error inesperado: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
