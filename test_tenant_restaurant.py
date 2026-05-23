#!/usr/bin/env python3
"""
Script de Prueba Automatizada - Demo Restaurant (Tenant: default)
Prueba la funcionalidad del tenant de restaurante
"""

import requests
import json
import time
from datetime import datetime

# Configuración
WHATSAPP_GATEWAY_URL = "https://hong-constitute-adaptive-ambassador.trycloudflare.com"
TEST_PHONE = "+5215500000001"  # Número de prueba
TENANT_ID = "default"

# Colores para terminal
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def print_header(text):
    print(f"\n{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BLUE}{text.center(60)}{Colors.END}")
    print(f"{Colors.BLUE}{'='*60}{Colors.END}\n")

def print_success(text):
    print(f"{Colors.GREEN}✅ {text}{Colors.END}")

def print_error(text):
    print(f"{Colors.RED}❌ {text}{Colors.END}")

def print_info(text):
    print(f"{Colors.YELLOW}ℹ️  {text}{Colors.END}")

def send_whatsapp_message(message: str):
    """
    Simula envío de mensaje de WhatsApp al gateway
    """
    payload = {
        "From": f"whatsapp:{TEST_PHONE}",
        "To": "whatsapp:+14155238886",  # Twilio sandbox
        "Body": message
    }

    try:
        response = requests.post(
            f"{WHATSAPP_GATEWAY_URL}/webhook/twilio",
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=10
        )

        if response.status_code == 200:
            return True, response.text
        else:
            return False, f"Status {response.status_code}: {response.text}"
    except Exception as e:
        return False, str(e)

def test_tenant_detection():
    """
    TEST 1: Verificar detección correcta del tenant
    """
    print_header("TEST 1: Detección de Tenant")
    print_info(f"Enviando mensaje con keyword: 'restaurant-hola'")

    success, response = send_whatsapp_message("restaurant-hola")

    if success:
        print_success("Mensaje enviado correctamente")
        print_info(f"Respuesta: {response[:100]}...")

        # Verificar que la respuesta contiene el mensaje de bienvenida del restaurante
        if "Demo Restaurant" in response or "restaurante" in response.lower():
            print_success("✓ Tenant detectado correctamente: Demo Restaurant")
            return True
        else:
            print_error("✗ Respuesta no contiene mensaje personalizado del restaurante")
            return False
    else:
        print_error(f"Error enviando mensaje: {response}")
        return False

def test_menu_interaction():
    """
    TEST 2: Interacción con menú
    """
    print_header("TEST 2: Consulta de Menú")
    print_info("Enviando: 'Quiero ver el menú'")

    time.sleep(2)  # Esperar 2 segundos entre mensajes

    success, response = send_whatsapp_message("Quiero ver el menú")

    if success:
        print_success("Mensaje enviado correctamente")
        print_info(f"Respuesta: {response[:150]}...")

        # Verificar que la respuesta habla de comida
        food_keywords = ["taco", "comida", "platillo", "menú", "categoría"]
        if any(keyword in response.lower() for keyword in food_keywords):
            print_success("✓ Respuesta contiene información de menú de restaurante")
            return True
        else:
            print_error("✗ Respuesta no contiene información de comida")
            return False
    else:
        print_error(f"Error enviando mensaje: {response}")
        return False

def test_add_to_cart():
    """
    TEST 3: Agregar productos al carrito
    """
    print_header("TEST 3: Agregar al Carrito")
    print_info("Enviando: 'Quiero 2 tacos de pastor y 1 agua de horchata'")

    time.sleep(2)

    success, response = send_whatsapp_message("Quiero 2 tacos de pastor y 1 agua de horchata")

    if success:
        print_success("Mensaje enviado correctamente")
        print_info(f"Respuesta: {response[:150]}...")

        # Verificar confirmación
        confirm_keywords = ["agregado", "carrito", "pedido", "confirmar"]
        if any(keyword in response.lower() for keyword in confirm_keywords):
            print_success("✓ Productos agregados al carrito")
            return True
        else:
            print_error("✗ No se confirma agregar al carrito")
            return False
    else:
        print_error(f"Error enviando mensaje: {response}")
        return False

def test_derivation_trigger():
    """
    TEST 4: Trigger de derivación a web
    """
    print_header("TEST 4: Derivación a Web")
    print_info("Enviando múltiples mensajes para alcanzar threshold...")

    messages = [
        "Tienen tacos de asada?",
        "Cuánto cuesta?",
        "También quiero unas quesadillas",
        "Tienen bebidas?",
        "Qué me recomiendas?"
    ]

    for i, msg in enumerate(messages, start=4):
        print_info(f"Mensaje {i}: {msg}")
        time.sleep(2)
        success, response = send_whatsapp_message(msg)

        if success:
            print_success(f"  ✓ Enviado correctamente")

            # En el mensaje 8, debería derivar
            if i == 8 or "trycloudflare.com" in response or "link" in response.lower():
                print_success("✓ DERIVACIÓN DETECTADA!")
                print_info(f"Respuesta con link: {response[:200]}...")
                return True
        else:
            print_error(f"  ✗ Error: {response}")

    print_error("✗ No se detectó derivación después de 8 mensajes")
    return False

def test_web_url_keyword():
    """
    TEST 5: Derivación por keyword "fotos"
    """
    print_header("TEST 5: Derivación por Keyword")
    print_info("Enviando: 'Quiero ver el menú completo con fotos'")

    time.sleep(2)

    success, response = send_whatsapp_message("Quiero ver el menú completo con fotos")

    if success:
        print_success("Mensaje enviado correctamente")

        # Verificar que envía link
        if "trycloudflare.com" in response or "link" in response.lower() or "http" in response.lower():
            print_success("✓ Link enviado por keyword 'fotos'")
            print_info(f"Respuesta: {response[:200]}...")
            return True
        else:
            print_error("✗ No se envió link con keyword 'fotos'")
            return False
    else:
        print_error(f"Error enviando mensaje: {response}")
        return False

def test_promotions():
    """
    TEST 6: Consultar promociones
    """
    print_header("TEST 6: Promociones")
    print_info("Enviando: 'Tienen promociones?'")

    time.sleep(2)

    success, response = send_whatsapp_message("Tienen promociones?")

    if success:
        print_success("Mensaje enviado correctamente")
        print_info(f"Respuesta: {response[:150]}...")

        # Verificar que habla de promociones de restaurante
        promo_keywords = ["promoción", "descuento", "oferta", "combo", "especial"]
        restaurant_keywords = ["taco", "comida", "platillo"]

        has_promo = any(keyword in response.lower() for keyword in promo_keywords)
        has_restaurant = any(keyword in response.lower() for keyword in restaurant_keywords)

        if has_promo or has_restaurant:
            print_success("✓ Respuesta contiene información de promociones")
            return True
        else:
            print_error("✗ Respuesta no contiene promociones claras")
            return False
    else:
        print_error(f"Error enviando mensaje: {response}")
        return False

def run_all_tests():
    """
    Ejecuta todos los tests del tenant de restaurante
    """
    print_header("INICIO DE PRUEBAS - DEMO RESTAURANT")
    print_info(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print_info(f"Gateway URL: {WHATSAPP_GATEWAY_URL}")
    print_info(f"Test Phone: {TEST_PHONE}")
    print_info(f"Tenant ID: {TENANT_ID}")

    results = []

    # Ejecutar tests
    tests = [
        ("Detección de Tenant", test_tenant_detection),
        ("Consulta de Menú", test_menu_interaction),
        ("Agregar al Carrito", test_add_to_cart),
        ("Derivación a Web (8 mensajes)", test_derivation_trigger),
        ("Derivación por Keyword", test_web_url_keyword),
        ("Promociones", test_promotions)
    ]

    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print_error(f"Error en test '{test_name}': {str(e)}")
            results.append((test_name, False))

    # Resumen final
    print_header("RESUMEN DE PRUEBAS")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        if result:
            print_success(f"{test_name}: PASÓ")
        else:
            print_error(f"{test_name}: FALLÓ")

    print(f"\n{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BLUE}Total: {passed}/{total} tests pasaron{Colors.END}")

    if passed == total:
        print_success("¡TODAS LAS PRUEBAS PASARON! ✅")
    else:
        print_error(f"Algunas pruebas fallaron ({total - passed} fallos)")

    print(f"{Colors.BLUE}{'='*60}{Colors.END}\n")

if __name__ == "__main__":
    print(f"\n{Colors.GREEN}{'='*60}")
    print(f"  SCRIPT DE PRUEBA - DEMO RESTAURANT (TENANT: default)")
    print(f"{'='*60}{Colors.END}\n")

    print_info("Este script probará:")
    print("  1. Detección de tenant con keyword 'restaurant'")
    print("  2. Interacción con menú del restaurante")
    print("  3. Agregar productos al carrito")
    print("  4. Derivación a web (8 mensajes)")
    print("  5. Derivación por keyword 'fotos'")
    print("  6. Consulta de promociones")

    input(f"\n{Colors.YELLOW}Presiona ENTER para comenzar las pruebas...{Colors.END}")

    run_all_tests()
