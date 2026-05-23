#!/usr/bin/env python3
"""
Script de prueba para FSM Optimizer

Crea conversaciones de ejemplo en el archivo y ejecuta el optimizador
para verificar que todo funciona correctamente.
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timedelta
from src.learning.fsm_optimizer import FSMOptimizer


def create_sample_conversations():
    """
    Crea conversaciones de ejemplo para probar el optimizador
    """
    print("📝 Creando conversaciones de ejemplo...")

    archive_path = Path("conversation_archive")

    # Crear estructura de directorios
    today = datetime.now()
    month_dir = archive_path / today.strftime('%Y-%m')
    day_dir = month_dir / today.strftime('%Y-%m-%d')
    day_dir.mkdir(parents=True, exist_ok=True)

    # Conversación de ejemplo 1 - Pedido exitoso con nuevos patrones
    conv1 = {
        "archive_id": "test_session_001_20250103_120000",
        "archived_at": today.isoformat(),
        "session_id": "test_session_001",
        "table_id": 1,
        "table_number": 5,
        "session_start": (today - timedelta(minutes=15)).isoformat(),
        "session_end": today.isoformat(),
        "duration_minutes": 15.0,
        "conversation_history": [
            {
                "role": "user",
                "content": "me traes 2 tacos",
                "timestamp": (today - timedelta(minutes=14)).isoformat(),
                "intent": "ADD_TO_ORDER",
                "confidence": 0.95,
                "success": True,
                "products_matched": [
                    {
                        "id": "taco_pastor",
                        "name": "Taco de Pastor",
                        "quantity": 2
                    }
                ]
            },
            {
                "role": "assistant",
                "content": "Perfecto, 2 tacos de pastor agregados. ¿Algo más?",
                "timestamp": (today - timedelta(minutes=14)).isoformat()
            },
            {
                "role": "user",
                "content": "ponme una coca",
                "timestamp": (today - timedelta(minutes=13)).isoformat(),
                "intent": "ADD_TO_ORDER",
                "confidence": 0.92,
                "success": True,
                "products_matched": [
                    {
                        "id": "coca_cola",
                        "name": "Coca Cola",
                        "quantity": 1
                    }
                ]
            },
            {
                "role": "assistant",
                "content": "Agregada 1 Coca Cola. Tu pedido: 2 Tacos de Pastor, 1 Coca Cola. Total: $85",
                "timestamp": (today - timedelta(minutes=13)).isoformat()
            },
            {
                "role": "user",
                "content": "así está bien",
                "timestamp": (today - timedelta(minutes=12)).isoformat(),
                "intent": "CONFIRM_ORDER",
                "confidence": 0.98,
                "success": True
            }
        ],
        "final_order": [
            {
                "product_id": "taco_pastor",
                "product_name": "Taco de Pastor",
                "quantity": 2,
                "unit_price": 25.0,
                "subtotal": 50.0
            },
            {
                "product_id": "coca_cola",
                "product_name": "Coca Cola",
                "quantity": 1,
                "unit_price": 35.0,
                "subtotal": 35.0
            }
        ],
        "order_total": 85.0,
        "quality_score": 0.95,
        "metrics": {
            "sentiment_score": 0.9,
            "total_turns": 5,
            "intents_detected": {
                "ADD_TO_ORDER": 2,
                "CONFIRM_ORDER": 1
            }
        }
    }

    # Conversación de ejemplo 2 - Con alias nuevo "burger"
    conv2 = {
        "archive_id": "test_session_002_20250103_130000",
        "archived_at": today.isoformat(),
        "session_id": "test_session_002",
        "table_id": 2,
        "table_number": 3,
        "session_start": (today - timedelta(minutes=20)).isoformat(),
        "session_end": today.isoformat(),
        "duration_minutes": 20.0,
        "conversation_history": [
            {
                "role": "user",
                "content": "quiero una burger",
                "timestamp": (today - timedelta(minutes=19)).isoformat(),
                "intent": "ADD_TO_ORDER",
                "confidence": 0.94,
                "success": True,
                "products_matched": [
                    {
                        "id": "hamburguesa_clasica",
                        "name": "Hamburguesa Clásica",
                        "quantity": 1
                    }
                ]
            },
            {
                "role": "assistant",
                "content": "¡Perfecto! 1 Hamburguesa Clásica agregada.",
                "timestamp": (today - timedelta(minutes=19)).isoformat()
            },
            {
                "role": "user",
                "content": "échale un refresco",
                "timestamp": (today - timedelta(minutes=18)).isoformat(),
                "intent": "ADD_TO_ORDER",
                "confidence": 0.91,
                "success": True,
                "products_matched": [
                    {
                        "id": "refresco",
                        "name": "Refresco",
                        "quantity": 1
                    }
                ]
            }
        ],
        "final_order": [
            {
                "product_id": "hamburguesa_clasica",
                "product_name": "Hamburguesa Clásica",
                "quantity": 1,
                "unit_price": 75.0,
                "subtotal": 75.0
            },
            {
                "product_id": "refresco",
                "product_name": "Refresco",
                "quantity": 1,
                "unit_price": 30.0,
                "subtotal": 30.0
            }
        ],
        "order_total": 105.0,
        "quality_score": 0.93,
        "metrics": {
            "sentiment_score": 0.95,
            "total_turns": 4,
            "intents_detected": {
                "ADD_TO_ORDER": 2
            }
        }
    }

    # Conversación 3 - Con typo común
    conv3 = {
        "archive_id": "test_session_003_20250103_140000",
        "archived_at": today.isoformat(),
        "session_id": "test_session_003",
        "table_id": 3,
        "table_number": 7,
        "session_start": (today - timedelta(minutes=10)).isoformat(),
        "session_end": today.isoformat(),
        "duration_minutes": 10.0,
        "conversation_history": [
            {
                "role": "user",
                "content": "dame una hamburgesa",
                "timestamp": (today - timedelta(minutes=9)).isoformat(),
                "intent": "ADD_TO_ORDER",
                "confidence": 0.89,
                "success": True,
                "fuzzy_correction": {
                    "original": "hamburgesa",
                    "corrected": "hamburguesa"
                },
                "products_matched": [
                    {
                        "id": "hamburguesa_clasica",
                        "name": "Hamburguesa Clásica",
                        "quantity": 1
                    }
                ]
            }
        ],
        "final_order": [
            {
                "product_id": "hamburguesa_clasica",
                "product_name": "Hamburguesa Clásica",
                "quantity": 1,
                "unit_price": 75.0,
                "subtotal": 75.0
            }
        ],
        "order_total": 75.0,
        "quality_score": 0.85,
        "metrics": {
            "sentiment_score": 0.8,
            "total_turns": 2,
            "intents_detected": {
                "ADD_TO_ORDER": 1
            }
        }
    }

    # Guardar conversaciones
    conversations = [conv1, conv2, conv3]

    for i, conv in enumerate(conversations, 1):
        filename = f"session_test_{i:03d}_mesa{conv['table_number']}.json"
        filepath = day_dir / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(conv, f, indent=2, ensure_ascii=False)

        print(f"  ✅ {filename}")

    # Crear más conversaciones con los mismos patrones para que se detecten
    for j in range(4, 8):
        conv_extra = {
            **conv1,
            "archive_id": f"test_session_{j:03d}_{today.strftime('%Y%m%d_%H%M%S')}",
            "session_id": f"test_session_{j:03d}",
            "table_id": j,
            "table_number": j + 2
        }

        filename = f"session_test_{j:03d}_mesa{j+2}.json"
        filepath = day_dir / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(conv_extra, f, indent=2, ensure_ascii=False)

    print(f"\n✅ {len(conversations) + 4} conversaciones creadas en {day_dir}")
    return day_dir


def test_optimizer():
    """
    Prueba el optimizador con las conversaciones de ejemplo
    """
    print("\n" + "=" * 70)
    print("🧪 PRUEBA DE FSM OPTIMIZER")
    print("=" * 70)

    # Crear conversaciones de ejemplo
    archive_dir = create_sample_conversations()

    # Crear optimizer
    print("\n🔧 Inicializando FSM Optimizer...")
    optimizer = FSMOptimizer(
        archive_path="conversation_archive",
        min_quality_score=0.7,
        min_pattern_frequency=3
    )

    # Analizar conversaciones
    print("\n🔍 Analizando conversaciones...\n")
    report = optimizer.analyze_weekly_conversations(days_back=1)

    # Mostrar resultados
    print("\n" + "=" * 70)
    print("📊 RESULTADOS")
    print("=" * 70)
    print(f"\nConversaciones analizadas: {report['total_conversations']}")
    print(f"Conversaciones de calidad: {report['quality_conversations']}")
    print(f"\nMejoras detectadas: {report['improvements']['total']}")
    print(f"  • Nuevos patrones: {sum(len(p) for p in report['improvements']['new_patterns'].values())}")
    print(f"  • Nuevos aliases: {sum(len(a) for a in report['improvements']['new_aliases'].values())}")
    print(f"  • Correcciones typo: {len(report['improvements']['typo_corrections'])}")

    # Preview
    optimizer.show_preview(report)

    # Guardar reporte
    report_path = Path("test_optimization_report.json")
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"\n📝 Reporte guardado en: {report_path}")

    print("\n" + "=" * 70)
    print("✅ PRUEBA COMPLETADA")
    print("=" * 70)
    print("\nPara limpiar archivos de prueba:")
    print(f"  rm -rf {archive_dir}")
    print(f"  rm {report_path}")

    return report


if __name__ == "__main__":
    try:
        report = test_optimizer()
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error durante la prueba: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
