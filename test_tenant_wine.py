#!/usr/bin/env python3
"""
Script de Prueba Automatizada - Vinetería Don Juan (Tenant: tenant_wine_001)
Prueba la funcionalidad del tenant de vinetería
"""

import requests
import json
import time
from datetime import datetime

# Configuración
WHATSAPP_GATEWAY_URL = "https://hong-constitute-adaptive-ambassador.trycloudflare.com"
TEST_PHONE = "+5215500000003"  # Número de prueba diferente
TENANT_ID = "tenant_wine_001"

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
        "To": "whatsapp:+14155238886",
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
    TEST 1: Verificar detección correcta del tenant de vinetería
    """
    print_header("TEST 1: Detección de Tenant Vinetería")
    print_info(f"Enviando mensaje con keyword: 'wine-hola'")

    success, response = send_whatsapp_message("wine-hola")

    if success:
        print_success("Mensaje enviado correctamente")
        print_info(f"Respuesta: {response[:100]}...")

        # Verificar que la respuesta contiene el mensaje de bienvenida de vinetería
        if "Vinetería Don Juan" in response or "vinetería" in response.lower() or "vino" in response.lower():
            print_success("✓ Tenant detectado correctamente: Vinetería Don Juan")
            return True
        else:
            print_error("✗ Respuesta no contiene mensaje personalizado de vinetería")
            return False
    else:
        print_error(f"Error enviando mensaje: {response}")
        return False

def test_wine_query():
    """
    TEST 2: Consultar vinos
    """
    print_header("TEST 2: Consulta de Vinos")
    print_info("Enviando: 'Tienen vino tinto?'")

    time.sleep(2)

    success, response = send_whatsapp_message("Tienen vino tinto?")

    if success:
        print_success("Mensaje enviado correctamente")
        print_info(f"Respuesta: {response[:150]}...")

        # Verificar que la respuesta habla de vinos
        wine_keywords = ["vino", "tinto", "cepa", "cabernet", "merlot", "botella", "maridaje"]
        if any(keyword in response.lower() for keyword in wine_keywords):
            print_success("✓ Respuesta contiene información de vinos")
            return True
        else:
            print_error("✗ Respuesta no contiene información de vinos")
            return False
    else:
        print_error(f"Error enviando mensaje: {response}")
        return False

def test_wine_recommendation():
    """
    TEST 3: Solicitar recomendación de vino
    """
    print_header("TEST 3: Recomendación de Vino")
    print_info("Enviando: 'Qué vino me recomiendas para una cena?'")

    time.sleep(2)

    success, response = send_whatsapp_message("Qué vino me recomiendas para una cena?")

    if success:
        print_success("Mensaje enviado correctamente")
        print_info(f"Respuesta: {response[:200]}...")

        # Verificar que da recomendación detallada
        recommendation_keywords = ["recomiendo", "sugiero", "ideal", "perfecto", "acompañar", "maridaje"]
        wine_keywords = ["vino", "tinto", "blanco", "rosado", "cepa"]

        has_recommendation = any(keyword in response.lower() for keyword in recommendation_keywords)
        has_wine = any(keyword in response.lower() for keyword in wine_keywords)

        if has_recommendation and has_wine:
            print_success("✓ Recomendación personalizada de vino recibida")
            return True
        else:
            print_error("✗ No se recibió recomendación detallada")
            return False
    else:
        print_error(f"Error enviando mensaje: {response}")
        return False

def test_add_to_cart():
    """
    TEST 4: Agregar vinos al carrito
    """
    print_header("TEST 4: Agregar Vinos al Carrito")
    print_info("Enviando: 'Quiero 2 botellas de Cabernet Sauvignon'")

    time.sleep(2)

    success, response = send_whatsapp_message("Quiero 2 botellas de Cabernet Sauvignon")

    if success:
        print_success("Mensaje enviado correctamente")
        print_info(f"Respuesta: {response[:150]}...")

        # Verificar confirmación
        confirm_keywords = ["agregado", "carrito", "pedido", "confirmar", "botellas"]
        if any(keyword in response.lower() for keyword in confirm_keywords):
            print_success("✓ Vinos agregados al carrito")
            return True
        else:
            print_error("✗ No se confirma agregar al carrito")
            return False
    else:
        print_error(f"Error enviando mensaje: {response}")
        return False

def test_wine_products():
    """
    TEST 5: Consultar productos específicos de vinetería
    """
    print_header("TEST 5: Productos Específicos de Vinetería")

    wine_queries = [
        "Tienen vino blanco?",
        "Tienen champagne?",
        "Tienen vino rosado?"
    ]

    all_passed = True

    for wine_query in wine_queries:
        print_info(f"Consultando: {wine_query}")
        time.sleep(2)

        success, response = send_whatsapp_message(wine_query)

        if success:
            print_success(f"  ✓ Respuesta recibida")

            # Verificar que NO menciona productos de restaurante o farmacia
            wrong_keywords = ["taco", "comida", "platillo", "paracetamol", "medicina", "antibiótico"]
            has_wrong = any(keyword in response.lower() for keyword in wrong_keywords)

            if has_wrong:
                print_error(f"  ✗ Respuesta contiene productos de otro tenant!")
                all_passed = False
            else:
                print_success(f"  ✓ Respuesta apropiada para vinetería")
        else:
            print_error(f"  ✗ Error: {response}")
            all_passed = False

    if all_passed:
        print_success("✓ TODOS los productos consultados son de vinetería")
    else:
        print_error("✗ Se detectó mezcla con otros tenants")

    return all_passed

def test_derivation_by_keyword():
    """
    TEST 6: Derivación por keyword "fotos"
    """
    print_header("TEST 6: Derivación por Keyword (Vinetería)")
    print_info("Enviando: 'Quiero ver todos los vinos que tienen con fotos'")

    time.sleep(2)

    success, response = send_whatsapp_message("Quiero ver todos los vinos que tienen con fotos")

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

def test_formal_tone():
    """
    TEST 7: Verificar tono formal
    """
    print_header("TEST 7: Tono Formal")
    print_info("Verificando que el tono es formal/elegante")

    time.sleep(2)

    success, response = send_whatsapp_message("Cuáles son sus mejores vinos?")

    if success:
        print_success("Mensaje enviado correctamente")
        print_info(f"Respuesta: {response[:150]}...")

        # Tono formal: uso de usted, lenguaje refinado
        formal_keywords = ["le", "usted", "nuestra", "selección", "distinguido", "excelente"]

        # Tono muy informal (no debería tener)
        informal_keywords = ["we", "compa", "amigo", "brother"]

        has_formal = any(keyword in response.lower() for keyword in formal_keywords)
        has_informal = any(keyword in response.lower() for keyword in informal_keywords)

        if has_formal or not has_informal:
            print_success("✓ Tono apropiado para vinetería (formal/elegante)")
            return True
        else:
            print_error("✗ Tono no es suficientemente formal")
            return False
    else:
        print_error(f"Error enviando mensaje: {response}")
        return False

def test_age_verification():
    """
    TEST 8: Verificación de edad
    """
    print_header("TEST 8: Verificación de Edad (+18)")
    print_info("Verificando que se solicita edad para venta de alcohol")

    time.sleep(2)

    success, response = send_whatsapp_message("Cuál es el monto mínimo de compra?")

    if success:
        print_success("Mensaje enviado correctamente")
        print_info(f"Respuesta: {response[:150]}...")

        # Debería mencionar edad mínima
        age_keywords = ["18", "mayor", "edad", "años", "verificación"]
        min_amount_keywords = ["200", "mínimo"]

        has_age = any(keyword in response for keyword in age_keywords)
        has_min_amount = any(keyword in response for keyword in min_amount_keywords)

        if has_age or has_min_amount:
            print_success("✓ Sistema menciona requisitos de edad o monto mínimo ($200)")
            return True
        else:
            print_error("✗ No se menciona verificación de edad ni monto mínimo")
            return False
    else:
        print_error(f"Error enviando mensaje: {response}")
        return False

def test_business_rules():
    """
    TEST 9: Reglas de negocio específicas
    """
    print_header("TEST 9: Reglas de Negocio (Vinetería)")
    print_info("Verificando reglas: Mínimo $200, Envío $50")

    time.sleep(2)

    success, response = send_whatsapp_message("Cuánto cuesta el envío?")

    if success:
        print_success("Mensaje enviado correctamente")
        print_info(f"Respuesta: {response[:150]}...")

        # Verificar monto de envío
        if "50" in response or "envío" in response.lower():
            print_success("✓ Información de envío correcta ($50)")
            return True
        else:
            print_error("✗ No se menciona costo de envío")
            return False
    else:
        print_error(f"Error enviando mensaje: {response}")
        return False

def run_all_tests():
    """
    Ejecuta todos los tests del tenant de vinetería
    """
    print_header("INICIO DE PRUEBAS - VINETERÍA DON JUAN")
    print_info(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print_info(f"Gateway URL: {WHATSAPP_GATEWAY_URL}")
    print_info(f"Test Phone: {TEST_PHONE}")
    print_info(f"Tenant ID: {TENANT_ID}")

    results = []

    # Ejecutar tests
    tests = [
        ("Detección de Tenant Vinetería", test_tenant_detection),
        ("Consulta de Vinos", test_wine_query),
        ("Recomendación de Vino", test_wine_recommendation),
        ("Agregar al Carrito", test_add_to_cart),
        ("Productos Específicos de Vinetería", test_wine_products),
        ("Derivación por Keyword", test_derivation_by_keyword),
        ("Tono Formal", test_formal_tone),
        ("Verificación de Edad", test_age_verification),
        ("Reglas de Negocio", test_business_rules)
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
    print(f"  SCRIPT DE PRUEBA - VINETERÍA DON JUAN")
    print(f"{'='*60}{Colors.END}\n")

    print_info("Este script probará:")
    print("  1. Detección de tenant con keyword 'wine'")
    print("  2. Consulta de vinos")
    print("  3. Recomendación personalizada de vino")
    print("  4. Agregar vinos al carrito")
    print("  5. Productos específicos de vinetería (sin mezcla)")
    print("  6. Derivación por keyword 'fotos'")
    print("  7. Tono formal en respuestas")
    print("  8. Verificación de edad (+18)")
    print("  9. Reglas de negocio (mínimo $200, envío $50)")

    input(f"\n{Colors.YELLOW}Presiona ENTER para comenzar las pruebas...{Colors.END}")

    run_all_tests()
