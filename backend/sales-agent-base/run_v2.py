#!/usr/bin/env python3
# ============================================================
# RUNNER PARA VERSIÓN 2.0 (FSM)
# ============================================================
# Ejecuta la nueva versión del asistente con FSM
# El archivo run.py original sigue usando app.py (v1)
# ============================================================

import os
import sys
import asyncio

# Agregar directorio al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def print_banner():
    print("""
================================================================
  VOICE RESTAURANT ASSISTANT - v2.0 (FSM)
================================================================

  Esta versión usa:
    - Máquina de Estados Finitos (FSM)
    - Árbol de Decisión determinístico
    - Sistema de Micro-embudos
    - Generador de respuestas por plantillas

  Para volver a la versión anterior:
    python run.py (usa app.py)

  Esta versión:
    python run_v2.py (usa app_v2.py)

================================================================
""")

def main():
    print_banner()

    # Importar y ejecutar app_v2
    from src.api.app_v2 import app, initialize_fsm

    # Configuración
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'

    print(f"Iniciando servidor en {host}:{port}")
    print(f"Debug: {debug}")

    # Inicializar FSM
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(initialize_fsm())

    # Arrancar
    app.run(host=host, port=port, debug=debug)

if __name__ == '__main__':
    main()
