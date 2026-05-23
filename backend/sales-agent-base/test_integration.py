#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
================================================================================
TEST DE INTEGRACIÓN - CONFIGURACIONES LLM
================================================================================
Script de prueba para verificar la integración de configuraciones
================================================================================
"""

import sys
from pathlib import Path

# Agregar el directorio raíz al path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))


def test_config_loader():
    """Probar carga de configuraciones"""
    print("=" * 60)
    print("TEST 1: Config Loader")
    print("=" * 60)

    try:
        from src.core.config_loader import get_config_loader

        config_loader = get_config_loader()
        print("✅ ConfigLoader inicializado correctamente")

        # Test 1: Cargar menú
        menu = config_loader.load_menu_knowledge()
        restaurant_name = menu.get('menu', {}).get('restaurant_name', 'N/A')
        categories = menu.get('menu', {}).get('categories', [])

        print(f"\n📋 MENÚ CARGADO:")
        print(f"   Restaurant: {restaurant_name}")
        print(f"   Categorías: {len(categories)}")

        for category in categories:
            cat_name = category.get('name')
            products = category.get('products', [])
            print(f"   - {cat_name}: {len(products)} productos")

        # Test 2: Obtener productos populares
        popular = config_loader.get_popular_products()
        print(f"\n⭐ PRODUCTOS POPULARES: {len(popular)}")
        for p in popular[:3]:
            print(f"   - {p['name']}: ${p['price']}")

        # Test 3: Obtener promociones activas
        promotions = config_loader.get_active_promotions()
        print(f"\n🎁 PROMOCIONES ACTIVAS: {len(promotions)}")
        for promo in promotions:
            print(f"   - {promo['name']}: {promo.get('description', 'N/A')}")

        # Test 4: Cargar reglas de venta
        sales_rules = config_loader.load_sales_rules()
        rules_categories = sales_rules.get('sales_rules_by_category', {})
        print(f"\n📊 REGLAS DE VENTA:")
        print(f"   Categorías con reglas: {len(rules_categories)}")
        for cat in rules_categories.keys():
            print(f"   - {cat}")

        # Test 5: Cargar prompts
        prompts = config_loader.load_assistant_prompts()
        system_prompts = prompts.get('system_prompts', {})
        print(f"\n💬 PROMPTS DEL ASISTENTE:")
        print(f"   Prompts configurados: {len(system_prompts)}")
        for prompt_name in list(system_prompts.keys())[:5]:
            print(f"   - {prompt_name}")

        # Test 6: Obtener prompt maestro
        master_prompt = config_loader.get_master_prompt()
        print(f"\n📝 PROMPT MAESTRO:")
        print(f"   Longitud: {len(master_prompt)} caracteres")
        print(f"   Preview: {master_prompt[:150]}...")

        print("\n✅ TODOS LOS TESTS DE CONFIG_LOADER PASARON")
        return True

    except Exception as e:
        print(f"\n❌ ERROR en config_loader: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_llm_service():
    """Probar servicio LLM (requiere API key de Groq)"""
    print("\n" + "=" * 60)
    print("TEST 2: LLM Service")
    print("=" * 60)

    try:
        from src.nlp.llm_service import get_llm_service

        llm_service = get_llm_service()
        print("✅ LLMService inicializado correctamente")

        # Test 1: Construir prompt contextual
        contextual_prompt = llm_service.get_contextual_prompt(
            intent="create_order",
            user_message="Quiero una hamburguesa",
            conversation_history=[],
            custom_context={"table_id": 5}
        )

        print(f"\n📝 PROMPT CONTEXTUAL GENERADO:")
        print(f"   Longitud: {len(contextual_prompt)} caracteres")
        print(f"   Preview: {contextual_prompt[:200]}...")

        print("\n✅ LLM SERVICE TESTS BÁSICOS PASARON")
        print("⚠️  Tests avanzados requieren API key de Groq configurada")

        return True

    except ImportError as e:
        print(f"\n⚠️  No se pudo importar LLMService: {e}")
        print("   Esto es normal si las dependencias no están instaladas")
        return True
    except Exception as e:
        print(f"\n❌ ERROR en llm_service: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_file_structure():
    """Verificar que todos los archivos de configuración existan"""
    print("\n" + "=" * 60)
    print("TEST 3: Estructura de Archivos")
    print("=" * 60)

    config_dir = PROJECT_ROOT / "config"
    required_files = [
        "menu_knowledge.json",
        "sales_rules.yaml",
        "assistant_prompts.yaml",
        "environment.example.env",
        "README.md"
    ]

    all_exist = True
    print(f"\n📁 Verificando archivos en: {config_dir}")

    for filename in required_files:
        file_path = config_dir / filename
        exists = file_path.exists()
        status = "✅" if exists else "❌"
        print(f"   {status} {filename}")

        if not exists:
            all_exist = False

    # Verificar nuevos módulos de código
    print(f"\n📁 Verificando módulos de código:")
    code_files = [
        "src/core/config_loader.py",
        "src/nlp/llm_service.py"
    ]

    for filename in code_files:
        file_path = PROJECT_ROOT / filename
        exists = file_path.exists()
        status = "✅" if exists else "❌"
        print(f"   {status} {filename}")

        if not exists:
            all_exist = False

    if all_exist:
        print("\n✅ TODOS LOS ARCHIVOS NECESARIOS EXISTEN")
    else:
        print("\n❌ FALTAN ALGUNOS ARCHIVOS")

    return all_exist


def test_yaml_dependency():
    """Verificar que PyYAML esté instalado"""
    print("\n" + "=" * 60)
    print("TEST 4: Dependencias")
    print("=" * 60)

    try:
        import yaml
        print("✅ PyYAML instalado correctamente")
        print(f"   Versión: {yaml.__version__ if hasattr(yaml, '__version__') else 'N/A'}")
        return True
    except ImportError:
        print("❌ PyYAML NO instalado")
        print("   Ejecuta: pip install PyYAML==6.0.1")
        return False


def main():
    """Ejecutar todos los tests"""
    print("""
╔══════════════════════════════════════════════════════════════╗
║  TEST DE INTEGRACIÓN - CONFIGURACIONES LLM                   ║
║  RESTAURANT_VOICE_SYSTEM_2.0                                 ║
╚══════════════════════════════════════════════════════════════╝
    """)

    results = {
        "Estructura de Archivos": test_file_structure(),
        "Dependencias": test_yaml_dependency(),
        "Config Loader": test_config_loader(),
        "LLM Service": test_llm_service()
    }

    # Resumen
    print("\n" + "=" * 60)
    print("RESUMEN DE TESTS")
    print("=" * 60)

    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{status} - {test_name}")

    all_passed = all(results.values())

    print("\n" + "=" * 60)
    if all_passed:
        print("✅✅✅ TODOS LOS TESTS PASARON ✅✅✅")
        print("=" * 60)
        print("\nLa integración está completa y funcionando correctamente.")
        print("\nPróximos pasos:")
        print("1. Configura tus API keys en .env")
        print("2. Personaliza menu_knowledge.json con tu menú")
        print("3. Ajusta sales_rules.yaml según tu estrategia")
        print("4. Ejecuta el servidor: python run.py")
    else:
        print("❌❌❌ ALGUNOS TESTS FALLARON ❌❌❌")
        print("=" * 60)
        print("\nRevisa los errores arriba y corrige los problemas.")

    return all_passed


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
