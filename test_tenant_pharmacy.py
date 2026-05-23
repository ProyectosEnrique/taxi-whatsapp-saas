#!/usr/bin/env python3
"""
Script de Prueba Automatizada - Farmacia Santa Fe (Tenant: tenant_pharmacy_001)
Prueba la funcionalidad del tenant de farmacia
"""

import requests
import json
import time
from datetime import datetime

# Configuración
WHATSAPP_GATEWAY_URL = "https://hong-constitute-adaptive-ambassador.trycloudflare.com"
TEST_PHONE = "+5215500000002"  # Número de prueba diferente
TENANT_ID = "tenant_pharmacy_001"

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
    TEST 1: Verificar detección correcta del tenant de farmacia
    """
    print_header("TEST 1: Detección de Tenant Farmacia")
    print_info(f"Enviando mensaje con keyword: 'farmacia-hola'")

    success, response = send_whatsapp_message("farmacia-hola")

    if success:
        print_success("Mensaje enviado correctamente")
        print_info(f"Respuesta: {response[:100]}...")

        # Verificar que la respuesta contiene el mensaje de bienvenida de farmacia
        if "Farmacia Santa Fe" in response or "farmacia" in response.lower():
            print_success("✓ Tenant detectado correctamente: Farmacia Santa Fe")
            return True
        else:
            print_error("✗ Respuesta no contiene mensaje personalizado de farmacia")
            return False
    else:
        print_error(f"Error enviando mensaje: {response}")
        return False

def test_medicine_query():
    """
    TEST 2: Consultar medicamentos
    """
    print_header("TEST 2: Consulta de Medicamentos")
    print_info("Enviando: 'Tienen paracetamol?'")

    time.sleep(2)

    success, response = send_whatsapp_message("Tienen paracetamol?")

    if success:
        print_success("Mensaje enviado correctamente")
        print_info(f"Respuesta: {response[:150]}...")

        # Verificar que la respuesta habla de medicamentos
        medicine_keywords = ["paracetamol", "tabletas", "medicamento", "mg", "presentación"]
        if any(keyword in response.lower() for keyword in medicine_keywords):
            print_success("✓ Respuesta contiene información de medicamentos")
            return True
        else:
            print_error("✗ Respuesta no contiene información de farmacia")
            return False
    else:
        print_error(f"Error enviando mensaje: {response}")
        return False

def test_add_to_cart():
    """
    TEST 3: Agregar productos farmacéuticos al carrito
    """
    print_header("TEST 3: Agregar Medicamentos al Carrito")
    print_info("Enviando: 'Quiero 2 cajas de paracetamol 500mg'")

    time.sleep(2)

    success, response = send_whatsapp_message("Quiero 2 cajas de paracetamol 500mg")

    if success:
        print_success("Mensaje enviado correctamente")
        print_info(f"Respuesta: {response[:150]}...")

        # Verificar confirmación
        confirm_keywords = ["agregado", "carrito", "pedido", "confirmar", "receta"]
        if any(keyword in response.lower() for keyword in confirm_keywords):
            print_success("✓ Productos agregados al carrito")
            return True
        else:
            print_error("✗ No se confirma agregar al carrito")
            return False
    else:
        print_error(f"Error enviando mensaje: {response}")
        return False

def test_pharmacy_products():
    """
    TEST 4: Consultar productos específicos de farmacia
    """
    print_header("TEST 4: Productos Específicos de Farmacia")

    products = [
        "Tienen vitamina C?",
        "Tienen gel antibacterial?",
        "Tienen termómetros digitales?"
    ]

    all_passed = True

    for product_query in products:
        print_info(f"Consultando: {product_query}")
        time.sleep(2)

        success, response = send_whatsapp_message(product_query)

        if success:
            print_success(f"  ✓ Respuesta recibida")

            # Verificar que NO menciona productos de restaurante o vinetería
            wrong_keywords = ["taco", "comida", "vino", "licor", "bebida alcohólica"]
            has_wrong = any(keyword in response.lower() for keyword in wrong_keywords)

            if has_wrong:
                print_error(f"  ✗ Respuesta contiene productos de otro tenant!")
                all_passed = False
            else:
                print_success(f"  ✓ Respuesta apropiada para farmacia")
        else:
            print_error(f"  ✗ Error: {response}")
            all_passed = False

    if all_passed:
        print_success("✓ TODOS los productos consultados son de farmacia")
    else:
        print_error("✗ Se detectó mezcla con otros tenants")

    return all_passed

def test_derivation_by_keyword():
    """
    TEST 5: Derivación por keyword "fotos"
    """
    print_header("TEST 5: Derivación por Keyword (Farmacia)")
    print_info("Enviando: 'Quiero ver el catálogo completo con fotos'")

    time.sleep(2)

    success, response = send_whatsapp_message("Quiero ver el catálogo completo con fotos")

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

def test_professional_tone():
    """
    TEST 6: Verificar tono profesional
    """
    print_header("TEST 6: Tono Profesional")
    print_info("Verificando que el tono es profesional, no amigable")

    time.sleep(2)

    success, response = send_whatsapp_message("Qué me recomiendas para el dolor de cabeza?")

    if success:
        print_success("Mensaje enviado correctamente")
        print_info(f"Respuesta: {response[:150]}...")

        # Tono profesional: menciona consultar médico, receta, etc
        professional_keywords = ["consultar", "médico", "receta", "profesional", "recomendamos"]

        # Tono muy informal (no debería tener)
        informal_keywords = ["we", "brother", "amigo", "compa"]

        has_professional = any(keyword in response.lower() for keyword in professional_keywords)
        has_informal = any(keyword in response.lower() for keyword in informal_keywords)

        if has_professional or not has_informal:
            print_success("✓ Tono apropiado para farmacia (profesional)")
            return True
        else:
            print_error("✗ Tono demasiado informal para farmacia")
            return False
    else:
        print_error(f"Error enviando mensaje: {response}")
        return False

def test_prescription_verification():
    """
    TEST 7: Verificación de receta
    """
    print_header("TEST 7: Verificación de Receta")
    print_info("Consultando medicamento que requiere receta")

    time.sleep(2)

    success, response = send_whatsapp_message("Tienen antibióticos?")

    if success:
        print_success("Mensaje enviado correctamente")
        print_info(f"Respuesta: {response[:150]}...")

        # Debería mencionar receta médica
        prescription_keywords = ["receta", "médica", "prescripción", "doctor"]

        if any(keyword in response.lower() for keyword in prescription_keywords):
            print_success("✓ Sistema solicita receta médica")
            return True
        else:
            print_error("✗ No se menciona verificación de receta")
            return False
    else:
        print_error(f"Error enviando mensaje: {response}")
        return False

def run_all_tests():
    """
    Ejecuta todos los tests del tenant de farmacia
    """
    print_header("INICIO DE PRUEBAS - FARMACIA SANTA FE")
    print_info(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print_info(f"Gateway URL: {WHATSAPP_GATEWAY_URL}")
    print_info(f"Test Phone: {TEST_PHONE}")
    print_info(f"Tenant ID: {TENANT_ID}")

    results = []

    # Ejecutar tests
    tests = [
        ("Detección de Tenant Farmacia", test_tenant_detection),
        ("Consulta de Medicamentos", test_medicine_query),
        ("Agregar al Carrito", test_add_to_cart),
        ("Productos Específicos de Farmacia", test_pharmacy_products),
        ("Derivación por Keyword", test_derivation_by_keyword),
        ("Tono Profesional", test_professional_tone),
        ("Verificación de Receta", test_prescription_verification)
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
    print(f"  SCRIPT DE PRUEBA - FARMACIA SANTA FE")
    print(f"{'='*60}{Colors.END}\n")

    print_info("Este script probará:")
    print("  1. Detección de tenant con keyword 'farmacia'")
    print("  2. Consulta de medicamentos")
    print("  3. Agregar productos al carrito")
    print("  4. Productos específicos de farmacia (sin mezcla)")
    print("  5. Derivación por keyword 'fotos'")
    print("  6. Tono profesional en respuestas")
    print("  7. Verificación de receta médica")

    input(f"\n{Colors.YELLOW}Presiona ENTER para comenzar las pruebas...{Colors.END}")

    run_all_tests()
