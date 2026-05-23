#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RUNNER CON SETUP AUTOMÁTICO - Sales Agent FSM v2.0

Este runner incluye configuración automática del proyecto:
- Primera ejecución: Configura todo automáticamente
- Ejecuciones siguientes: Inicia directamente

Simplemente ejecuta: python run_auto.py
"""

import os
import sys
import asyncio

# Agregar directorio al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ============================================================================
# SETUP AUTOMÁTICO
# ============================================================================

def ejecutar_setup_automatico():
    """Ejecuta el setup automático si es necesario"""
    try:
        from src.setup_auto import setup_proyecto

        # Ejecutar setup (silencioso si ya está configurado)
        setup_proyecto(silent=False)

    except ImportError:
        print("⚠️  Módulo de setup no disponible")
        print("   El proyecto continuará sin configuración automática")

    except Exception as e:
        print(f"⚠️  Error en setup automático: {e}")
        print("   El proyecto continuará de todas formas")


# ============================================================================
# BANNER
# ============================================================================

def print_banner():
    """Muestra banner del proyecto"""
    print("""
╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║         SALES AGENT FSM v2.0 - Con Setup Automático             ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝

  Características:
    ✅ Máquina de Estados Finitos (FSM)
    ✅ Árbol de Decisión determinístico
    ✅ LLM Fallback inteligente
    ✅ Mejora continua automática (domingos 3 AM)

  Sistema de Optimización:
    🧠 FSM Optimizer analiza conversaciones reales
    📈 Detecta nuevos patrones automáticamente
    🚀 Mejora sin necesidad de GPU

══════════════════════════════════════════════════════════════════
""")


# ============================================================================
# VERIFICAR ESTADO DE AUTOMATIZACIÓN
# ============================================================================

def mostrar_estado_automatizacion():
    """Muestra el estado de la automatización al inicio"""
    try:
        from src.setup_auto import AutoSetup

        setup = AutoSetup()
        status = setup.check_automation_status()

        if status['configured']:
            print("✅ Automatización semanal: ACTIVA")

            if status['next_run']:
                print(f"   Próxima ejecución: {status['next_run']}")

            print()
        else:
            print("⚠️  Automatización semanal: NO CONFIGURADA")
            print("   Para configurar: ejecuta configurar_automatizacion.bat como Admin")
            print()

    except Exception:
        pass  # No mostrar errores de verificación


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Función principal con setup automático integrado"""

    # 1. Ejecutar setup automático (solo primera vez)
    ejecutar_setup_automatico()

    # 2. Mostrar banner
    print_banner()

    # 3. Mostrar estado de automatización
    mostrar_estado_automatizacion()

    # 4. Importar y ejecutar app
    try:
        from src.api.app_v2 import app, initialize_fsm

    except ImportError as e:
        print(f"❌ ERROR: No se pudo importar la aplicación")
        print(f"   {e}")
        print()
        print("Verifica que:")
        print("  1. Las dependencias estén instaladas: pip install -r requirements.txt")
        print("  2. Estés en el directorio correcto")
        print()
        sys.exit(1)

    # 5. Configuración
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    # Cloud Run usa PORT, fallback a FLASK_PORT para desarrollo local
    port = int(os.getenv('PORT', os.getenv('FLASK_PORT', 5000)))
    debug = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'

    print(f"🚀 Iniciando servidor...")
    print(f"   Host: {host}")
    print(f"   Puerto: {port}")
    print(f"   Debug: {'Sí' if debug else 'No'}")
    print()

    if debug:
        print("⚠️  MODO DEBUG ACTIVADO")
        print("   - Auto-reload habilitado")
        print("   - Stack traces detallados")
        print("   - NO usar en producción")
        print()

    print("══════════════════════════════════════════════════════════════════")
    print()
    print(f"📡 Servidor disponible en: http://localhost:{port}")
    print()
    print("Presiona Ctrl+C para detener")
    print()
    print("══════════════════════════════════════════════════════════════════")
    print()

    # 6. Inicializar FSM
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(initialize_fsm())

    except Exception as e:
        print(f"⚠️  Advertencia al inicializar FSM: {e}")
        print("   El servidor continuará de todas formas")

    # 7. Arrancar servidor
    try:
        app.run(host=host, port=port, debug=debug)

    except KeyboardInterrupt:
        print("\n\n👋 Servidor detenido por el usuario")

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
