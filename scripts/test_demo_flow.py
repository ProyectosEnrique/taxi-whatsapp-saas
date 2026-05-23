#!/usr/bin/env python3
"""
================================================================================
TEST DEL FLUJO COMPLETO DE DEMO - Simulación de Conversación
================================================================================
Simula una conversación completa de usuario con el sistema demo:
1. Usuario nuevo → Recibe bienvenida y menú
2. Selecciona industria → Recibe confirmación
3. Interactúa con la tienda → Sistema usa tenant correcto
4. Cambia de industria → Sistema actualiza contexto
================================================================================
"""

import requests
import json
from typing import Dict, Any
from datetime import datetime

# Configuración
BASE_URL = "http://localhost:8096"
TEST_PHONE = "whatsapp:+5215512345678"  # Formato Twilio

# Colores para terminal
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    MAGENTA = '\033[95m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_success(message: str):
    print(f"{Colors.GREEN}[OK] {message}{Colors.RESET}")

def print_error(message: str):
    print(f"{Colors.RED}[ERROR] {message}{Colors.RESET}")

def print_info(message: str):
    print(f"{Colors.BLUE}[INFO] {message}{Colors.RESET}")

def print_user_message(message: str):
    print(f"\n{Colors.CYAN}[USUARIO] {message}{Colors.RESET}")

def print_bot_response(message: str):
    print(f"{Colors.MAGENTA}[BOT] {message}{Colors.RESET}\n")

def print_header(message: str):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*80}{Colors.RESET}")
    print(f"{Colors.BOLD}{message}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*80}{Colors.RESET}\n")


def simulate_webhook(phone: str, message: str) -> Dict[str, Any]:
    """
    Simula el webhook de Twilio enviando un mensaje al sistema.

    Returns:
        Response del sistema (normalmente vacío, el mensaje se envía por separado)
    """
    try:
        url = f"{BASE_URL}/webhook/twilio"
        data = {
            "From": phone,
            "To": "whatsapp:+14155238886",  # Número de Twilio sandbox
            "Body": message,
            "MessageSid": f"TEST{datetime.now().timestamp()}",
            "AccountSid": "TEST_ACCOUNT",
            "MessagingServiceSid": "TEST_SERVICE"
        }

        response = requests.post(url, data=data, timeout=30)

        return {
            "status_code": response.status_code,
            "success": response.status_code == 200,
            "response": response.text
        }
    except Exception as e:
        return {
            "status_code": 0,
            "success": False,
            "error": str(e)
        }


def check_prospect_state(phone: str) -> Dict[str, Any]:
    """
    Verifica el estado actual del prospecto leyendo el archivo de prospectos.
    """
    try:
        filepath = "backend/whatsapp-gateway/data/demo/prospects.json"
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            phone_clean = phone.replace("whatsapp:", "")
            return data.get(phone_clean, {})
    except Exception as e:
        return {"error": str(e)}


def test_conversation_flow():
    """Probar el flujo completo de conversación"""

    print_header("TEST DE FLUJO COMPLETO - Conversación Demo")

    # Limpiar estado anterior (eliminar prospecto de prueba)
    try:
        filepath = "backend/whatsapp-gateway/data/demo/prospects.json"
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        phone_clean = TEST_PHONE.replace("whatsapp:", "")
        if phone_clean in data:
            del data[phone_clean]
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print_info(f"Estado anterior limpiado para {phone_clean}")
    except Exception as e:
        print_info(f"No hay estado anterior: {e}")

    print()

    # =========================================================================
    # ESCENARIO 1: Usuario nuevo - Primera interacción
    # =========================================================================
    print_header("ESCENARIO 1: Usuario Nuevo - Primera Interaccion")

    print_user_message("Hola")
    result = simulate_webhook(TEST_PHONE, "Hola")

    if result["success"]:
        print_success("Webhook procesado correctamente")
        print_info("El bot debería haber enviado mensaje de bienvenida con menu de industrias")

        # Verificar estado del prospecto
        state = check_prospect_state(TEST_PHONE)
        if state and not state.get("error"):
            print_success(f"Prospecto creado: {state.get('phone')}")
            print_info(f"Industria actual: {state.get('current_industry', 'None')}")
            print_info(f"Industrias exploradas: {len(state.get('industries_explored', []))}")
        else:
            print_error("No se pudo verificar estado del prospecto")
    else:
        print_error(f"Webhook falló: {result.get('error', 'Unknown')}")
        return False

    # =========================================================================
    # ESCENARIO 2: Selección de industria (Restaurante)
    # =========================================================================
    print_header("ESCENARIO 2: Seleccion de Industria (Restaurante)")

    print_user_message("1")
    result = simulate_webhook(TEST_PHONE, "1")

    if result["success"]:
        print_success("Seleccion procesada correctamente")
        print_info("El bot debería confirmar seleccion de restaurante y otorgar puntos")

        # Verificar estado actualizado
        state = check_prospect_state(TEST_PHONE)
        if state and not state.get("error"):
            print_success(f"Industria asignada: {state.get('current_industry')}")
            print_success(f"Puntos iniciales otorgados: {state.get('initial_points_granted')}")
            print_info(f"Industrias exploradas: {state.get('industries_explored')}")
        else:
            print_error("No se pudo verificar actualizacion de estado")
    else:
        print_error(f"Seleccion fallida: {result.get('error', 'Unknown')}")
        return False

    # =========================================================================
    # ESCENARIO 3: Interacción dentro de la tienda
    # =========================================================================
    print_header("ESCENARIO 3: Interaccion con la Tienda")

    print_user_message("Quiero ver el menu")
    result = simulate_webhook(TEST_PHONE, "Quiero ver el menu")

    if result["success"]:
        print_success("Mensaje procesado correctamente")
        print_info("El bot debería responder con el menu del restaurante")

        # El sistema debería usar tenant_id = demo_restaurant
        state = check_prospect_state(TEST_PHONE)
        if state.get("current_industry") == "demo_restaurant":
            print_success("Sistema usando el tenant correcto (demo_restaurant)")
        else:
            print_error(f"Tenant incorrecto: {state.get('current_industry')}")
    else:
        print_error(f"Interaccion fallida: {result.get('error', 'Unknown')}")

    # =========================================================================
    # ESCENARIO 4: Comando especial (cambiar de industria)
    # =========================================================================
    print_header("ESCENARIO 4: Comando 'cambiar' - Cambiar de Industria")

    print_user_message("cambiar")
    result = simulate_webhook(TEST_PHONE, "cambiar")

    if result["success"]:
        print_success("Comando procesado correctamente")
        print_info("El bot debería mostrar el menu de industrias nuevamente")

        state = check_prospect_state(TEST_PHONE)
        if state.get("current_industry") is None:
            print_success("Industria actual reseteada correctamente (None)")
        else:
            print_error(f"Industria no se reseteo: {state.get('current_industry')}")
    else:
        print_error(f"Comando fallido: {result.get('error', 'Unknown')}")

    # =========================================================================
    # ESCENARIO 5: Selección de otra industria (Retail)
    # =========================================================================
    print_header("ESCENARIO 5: Seleccionar otra Industria (Retail)")

    print_user_message("2")
    result = simulate_webhook(TEST_PHONE, "2")

    if result["success"]:
        print_success("Nueva seleccion procesada")
        print_info("El bot debería confirmar cambio a tienda de ropa")

        state = check_prospect_state(TEST_PHONE)
        if state.get("current_industry") == "demo_retail":
            print_success("Industria cambiada correctamente a demo_retail")
            industries_explored = state.get("industries_explored", [])
            if "demo_restaurant" in industries_explored and "demo_retail" in industries_explored:
                print_success(f"Historial de exploracion correcto: {industries_explored}")
            else:
                print_error(f"Historial incorrecto: {industries_explored}")
        else:
            print_error(f"Cambio de industria fallo: {state.get('current_industry')}")
    else:
        print_error(f"Seleccion fallida: {result.get('error', 'Unknown')}")

    # =========================================================================
    # ESCENARIO 6: Comando "info" (solicitar información de precios)
    # =========================================================================
    print_header("ESCENARIO 6: Comando 'info' - Solicitar Precios")

    print_user_message("info")
    result = simulate_webhook(TEST_PHONE, "info")

    if result["success"]:
        print_success("Comando 'info' procesado")
        print_info("El bot debería enviar información de planes y precios")

        state = check_prospect_state(TEST_PHONE)
        if state.get("requested_info"):
            print_success("Flag 'requested_info' marcado correctamente")
        else:
            print_error("Flag 'requested_info' no se marco")
    else:
        print_error(f"Comando fallido: {result.get('error', 'Unknown')}")

    # =========================================================================
    # RESUMEN FINAL
    # =========================================================================
    print_header("RESUMEN DEL TEST")

    state = check_prospect_state(TEST_PHONE)

    print(f"Prospecto: {state.get('phone', 'N/A')}")
    print(f"Industria actual: {state.get('current_industry', 'N/A')}")
    print(f"Industrias exploradas: {state.get('industries_explored', [])}")
    print(f"Puntos iniciales otorgados: {state.get('initial_points_granted', False)}")
    print(f"Checkout completado: {state.get('completed_checkout', False)}")
    print(f"Solicito informacion: {state.get('requested_info', False)}")
    print(f"Creado: {state.get('created_at', 'N/A')}")
    print(f"Ultima interaccion: {state.get('last_interaction', 'N/A')}")

    print()

    # Verificación final
    all_checks = [
        state.get("current_industry") == "demo_retail",
        len(state.get("industries_explored", [])) == 2,
        state.get("initial_points_granted") == True,
        state.get("requested_info") == True
    ]

    if all(all_checks):
        print_success("\n¡TODOS LOS TESTS PASARON CORRECTAMENTE!")
        print_info("El flujo de demo esta funcionando como se esperaba")
        return True
    else:
        print_error("\nALGUNOS TESTS FALLARON")
        print_info("Revisa los detalles anteriores para identificar problemas")
        return False


# ==============================================================================
# MAIN
# ==============================================================================

if __name__ == "__main__":
    import sys
    success = test_conversation_flow()
    sys.exit(0 if success else 1)
