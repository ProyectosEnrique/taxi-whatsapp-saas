#!/usr/bin/env python3
"""
================================================================================
TEST DE TIENDAS DEMO - Verificación Automatizada
================================================================================
Prueba que cada tienda demo funciona correctamente:
1. Menú disponible
2. Configuración de loyalty
3. Productos cargados
4. Categorías correctas
================================================================================
"""

import requests
import json
from typing import Dict, Any
from datetime import datetime

# Configuración
BASE_URL = "http://localhost:8096"  # URL del gateway
TEST_PHONE = "5215512345678"

# Colores para terminal
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_success(message: str):
    print(f"{Colors.GREEN}[OK] {message}{Colors.RESET}")

def print_error(message: str):
    print(f"{Colors.RED}[ERROR] {message}{Colors.RESET}")

def print_info(message: str):
    print(f"{Colors.BLUE}[INFO] {message}{Colors.RESET}")

def print_warning(message: str):
    print(f"{Colors.YELLOW}[WARN] {message}{Colors.RESET}")

def print_header(message: str):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*80}{Colors.RESET}")
    print(f"{Colors.BOLD}{message}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*80}{Colors.RESET}\n")


# ==============================================================================
# TESTS
# ==============================================================================

def test_health_check() -> bool:
    """Verificar que el gateway está funcionando"""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print_success(f"Gateway funcionando - Provider: {data.get('provider', 'unknown')}")
            return True
        else:
            print_error(f"Gateway no responde correctamente (Status: {response.status_code})")
            return False
    except Exception as e:
        print_error(f"No se puede conectar al gateway: {e}")
        return False


def test_store_menu(store_id: str, expected_name: str) -> Dict[str, Any]:
    """
    Verificar que el menú de una tienda funciona correctamente

    Returns:
        Dict con resultados del test
    """
    result = {
        "store_id": store_id,
        "store_name": expected_name,
        "menu_available": False,
        "products_count": 0,
        "categories_count": 0,
        "errors": []
    }

    try:
        # 1. Obtener menú
        url = f"{BASE_URL}/api/v1/restaurants/{store_id}/menu"
        response = requests.get(url, timeout=10)

        if response.status_code != 200:
            result["errors"].append(f"Menú no disponible (HTTP {response.status_code})")
            return result

        data = response.json()

        # 2. Verificar estructura
        if not data.get("success"):
            result["errors"].append("Response no tiene 'success': True")
            return result

        result["menu_available"] = True

        # 3. Verificar productos
        products = data.get("products", [])
        result["products_count"] = len(products)

        if len(products) == 0:
            result["errors"].append("No hay productos en el catálogo")

        # 4. Verificar categorías
        categories = data.get("categories", [])
        result["categories_count"] = len(categories)

        if len(categories) == 0:
            result["errors"].append("No hay categorías definidas")

        # 5. Verificar que los productos tengan la estructura correcta
        for product in products[:3]:  # Verificar solo los primeros 3
            required_fields = ["id", "name", "price", "category"]
            missing = [f for f in required_fields if f not in product]
            if missing:
                result["errors"].append(f"Producto {product.get('id', '?')} falta campos: {missing}")

        return result

    except Exception as e:
        result["errors"].append(f"Error obteniendo menú: {str(e)}")
        return result


def test_loyalty_config(store_id: str) -> Dict[str, Any]:
    """
    Verificar configuración de loyalty para una tienda

    Returns:
        Dict con resultados del test
    """
    result = {
        "store_id": store_id,
        "config_available": False,
        "enabled": False,
        "tiers_enabled": False,
        "errors": []
    }

    try:
        url = f"{BASE_URL}/api/v1/loyalty/config/{store_id}"
        response = requests.get(url, timeout=10)

        if response.status_code != 200:
            result["errors"].append(f"Config no disponible (HTTP {response.status_code})")
            return result

        data = response.json()

        if not data.get("success"):
            result["errors"].append("Response no tiene 'success': True")
            return result

        result["config_available"] = True

        config = data.get("config", {})
        result["enabled"] = config.get("enabled", False)
        result["tiers_enabled"] = config.get("tiers_enabled", False)
        result["points_per_currency"] = config.get("points_per_currency", 0)

        # Verificar que tenga los campos básicos
        required_fields = [
            "points_per_currency",
            "currency_per_point",
            "min_points_to_redeem"
        ]

        missing = [f for f in required_fields if f not in config]
        if missing:
            result["errors"].append(f"Faltan campos en config: {missing}")

        return result

    except Exception as e:
        result["errors"].append(f"Error obteniendo config: {str(e)}")
        return result


def run_all_tests():
    """Ejecutar todos los tests para todas las tiendas"""

    print_header("TEST DE TIENDAS DEMO - Sistema Multi-Industria")

    # 1. Health check
    print_info("Verificando estado del gateway...")
    if not test_health_check():
        print_error("Gateway no está disponible. Abortando tests.")
        return

    print()

    # 2. Definir tiendas a probar
    stores = [
        ("demo_restaurant", "Taqueria El Buen Sabor", "RESTAURANT"),
        ("demo_retail", "Boutique Fashion Point", "RETAIL"),
        ("demo_pharmacy", "Farmacia Salud Plus", "PHARMACY"),
        ("demo_grocery", "Super Abarrotes La Esquina", "GROCERY"),
        ("demo_services", "Salon Bella Imagen", "SERVICES"),
        ("demo_pets", "PetShop Huellitas Felices", "PETS"),
    ]

    # 3. Ejecutar tests para cada tienda
    all_passed = True
    results = []

    for store_id, store_name, icon in stores:
        print_header(f"{icon} {store_name} ({store_id})")

        # Test menú
        print_info("Probando menú...")
        menu_result = test_store_menu(store_id, store_name)

        if menu_result["menu_available"]:
            print_success(f"Menú disponible - {menu_result['products_count']} productos, {menu_result['categories_count']} categorías")
        else:
            print_error("Menú NO disponible")
            all_passed = False

        for error in menu_result["errors"]:
            print_error(f"  {error}")

        # Test loyalty
        print_info("Probando sistema de loyalty...")
        loyalty_result = test_loyalty_config(store_id)

        if loyalty_result["config_available"]:
            status = "Habilitado" if loyalty_result["enabled"] else "Deshabilitado"
            tiers = "Con niveles" if loyalty_result["tiers_enabled"] else "Sin niveles"
            print_success(f"Loyalty configurado - {status}, {tiers}")
        else:
            print_error("Loyalty NO configurado")
            all_passed = False

        for error in loyalty_result["errors"]:
            print_error(f"  {error}")

        results.append({
            "store_id": store_id,
            "store_name": store_name,
            "icon": icon,
            "menu": menu_result,
            "loyalty": loyalty_result
        })

        print()

    # 4. Resumen final
    print_header("RESUMEN DE RESULTADOS")

    for result in results:
        store_name = result["store_name"]
        icon = result["icon"]
        menu_ok = result["menu"]["menu_available"] and len(result["menu"]["errors"]) == 0
        loyalty_ok = result["loyalty"]["config_available"] and len(result["loyalty"]["errors"]) == 0

        status_icon = "[OK]" if (menu_ok and loyalty_ok) else "[ERROR]"
        color = Colors.GREEN if (menu_ok and loyalty_ok) else Colors.RED

        print(f"{color}{status_icon} {icon} {store_name}{Colors.RESET}")
        print(f"   Menú: {result['menu']['products_count']} productos")
        print(f"   Loyalty: {'OK' if loyalty_ok else 'ERROR'}")
        print()

    # 5. Resultado final
    if all_passed:
        print_success(f"\n{Colors.BOLD}¡TODAS LAS TIENDAS FUNCIONAN CORRECTAMENTE!{Colors.RESET}")
        print_info("Las 6 tiendas demo están listas para ser probadas por WhatsApp")
        print_info(f"Envía un mensaje a Twilio sandbox desde {TEST_PHONE}")
        return 0
    else:
        print_error(f"\n{Colors.BOLD}ALGUNAS TIENDAS TIENEN PROBLEMAS{Colors.RESET}")
        print_warning("Revisa los errores anteriores y corrige las configuraciones")
        return 1


# ==============================================================================
# MAIN
# ==============================================================================

if __name__ == "__main__":
    import sys
    exit_code = run_all_tests()
    sys.exit(exit_code)
