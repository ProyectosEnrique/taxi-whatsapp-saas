#!/usr/bin/env python3
"""
Script Maestro - Ejecutar TODAS las pruebas de Multi-Tenant
Ejecuta las pruebas de los 3 tenants de manera secuencial
"""

import subprocess
import sys
import time
from datetime import datetime

# Colores para terminal
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    END = '\033[0m'

def print_header(text):
    print(f"\n{Colors.CYAN}{'='*70}{Colors.END}")
    print(f"{Colors.CYAN}{text.center(70)}{Colors.END}")
    print(f"{Colors.CYAN}{'='*70}{Colors.END}\n")

def print_success(text):
    print(f"{Colors.GREEN}✅ {text}{Colors.END}")

def print_error(text):
    print(f"{Colors.RED}❌ {text}{Colors.END}")

def print_info(text):
    print(f"{Colors.YELLOW}ℹ️  {text}{Colors.END}")

def print_tenant_header(tenant_name):
    print(f"\n{Colors.MAGENTA}{'*'*70}")
    print(f"  EJECUTANDO PRUEBAS: {tenant_name}")
    print(f"{'*'*70}{Colors.END}\n")

def run_test_script(script_name, tenant_name):
    """
    Ejecuta un script de prueba y captura el resultado
    """
    print_tenant_header(tenant_name)
    print_info(f"Ejecutando: {script_name}")
    print_info(f"Hora de inicio: {datetime.now().strftime('%H:%M:%S')}")
    print()

    try:
        # Ejecutar el script
        result = subprocess.run(
            [sys.executable, script_name],
            capture_output=True,
            text=True,
            timeout=120  # Timeout de 2 minutos
        )

        # Mostrar salida
        print(result.stdout)

        if result.stderr:
            print_error("Errores detectados:")
            print(result.stderr)

        # Verificar si pasó o falló
        if result.returncode == 0:
            print_success(f"✓ Script {script_name} ejecutado exitosamente")
            return True
        else:
            print_error(f"✗ Script {script_name} falló (código {result.returncode})")
            return False

    except subprocess.TimeoutExpired:
        print_error(f"✗ Script {script_name} excedió el timeout (2 minutos)")
        return False
    except Exception as e:
        print_error(f"✗ Error ejecutando {script_name}: {str(e)}")
        return False

def main():
    """
    Función principal que ejecuta todos los tests
    """
    print_header("SUITE COMPLETA DE PRUEBAS MULTI-TENANT")
    print_info(f"Fecha: {datetime.now().strftime('%Y-%m-%d')}")
    print_info(f"Hora de inicio: {datetime.now().strftime('%H:%M:%S')}")
    print()

    print(f"{Colors.YELLOW}Esta suite ejecutará pruebas para los 3 tenants:{Colors.END}")
    print("  1️⃣  Demo Restaurant (tenant: default)")
    print("  2️⃣  Farmacia Santa Fe (tenant: tenant_pharmacy_001)")
    print("  3️⃣  Vinetería Don Juan (tenant: tenant_wine_001)")
    print()

    print(f"{Colors.YELLOW}Cada suite incluye múltiples tests:{Colors.END}")
    print("  ✓ Detección de tenant")
    print("  ✓ Consulta de productos")
    print("  ✓ Agregar al carrito")
    print("  ✓ Derivación a web")
    print("  ✓ Verificar tono de respuestas")
    print("  ✓ Reglas de negocio específicas")
    print()

    # Verificar que los scripts existen
    test_scripts = [
        ("test_tenant_restaurant.py", "Demo Restaurant"),
        ("test_tenant_pharmacy.py", "Farmacia Santa Fe"),
        ("test_tenant_wine.py", "Vinetería Don Juan")
    ]

    print_info("Verificando que todos los scripts de prueba existen...")
    all_exist = True
    for script, _ in test_scripts:
        try:
            with open(script, 'r'):
                print_success(f"✓ {script}")
        except FileNotFoundError:
            print_error(f"✗ {script} NO ENCONTRADO")
            all_exist = False

    if not all_exist:
        print_error("\nFaltan scripts de prueba. Por favor verifica que todos los archivos existan.")
        return

    print()
    input(f"{Colors.YELLOW}Presiona ENTER para comenzar la suite completa de pruebas...{Colors.END}")

    # Ejecutar cada test
    results = []
    start_time = datetime.now()

    for script, tenant_name in test_scripts:
        print_info(f"\nPreparando pruebas de: {tenant_name}")
        time.sleep(2)  # Pequeña pausa entre suites

        result = run_test_script(script, tenant_name)
        results.append((tenant_name, result))

        print_info(f"Completado: {tenant_name}")
        print()

    end_time = datetime.now()
    duration = end_time - start_time

    # Resumen final
    print_header("RESUMEN FINAL DE TODAS LAS PRUEBAS")

    for tenant_name, result in results:
        if result:
            print_success(f"{tenant_name}: PASÓ ✅")
        else:
            print_error(f"{tenant_name}: FALLÓ ❌")

    print(f"\n{Colors.CYAN}{'='*70}{Colors.END}")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    print(f"{Colors.BLUE}Tenants probados: {total}{Colors.END}")
    print(f"{Colors.GREEN}Tenants exitosos: {passed}{Colors.END}")
    print(f"{Colors.RED}Tenants fallidos: {total - passed}{Colors.END}")
    print(f"{Colors.YELLOW}Duración total: {duration}{Colors.END}")

    print(f"{Colors.CYAN}{'='*70}{Colors.END}\n")

    if passed == total:
        print_success("🎉 ¡TODAS LAS PRUEBAS PASARON EXITOSAMENTE! 🎉")
        print()
        print(f"{Colors.GREEN}El sistema multi-tenant está funcionando correctamente.{Colors.END}")
        print(f"{Colors.GREEN}Los 3 tenants pueden operar independientemente sin mezclarse.{Colors.END}")
        return 0
    else:
        print_error(f"⚠️  {total - passed} tenant(s) tienen problemas")
        print()
        print(f"{Colors.YELLOW}Revisa los logs de arriba para identificar los problemas.{Colors.END}")
        return 1

if __name__ == "__main__":
    print(f"\n{Colors.CYAN}{'='*70}")
    print(f"  SUITE MAESTRA DE PRUEBAS MULTI-TENANT")
    print(f"  Sistema de Ventas por WhatsApp - 3 Tiendas")
    print(f"{'='*70}{Colors.END}\n")

    exit_code = main()
    sys.exit(exit_code)
