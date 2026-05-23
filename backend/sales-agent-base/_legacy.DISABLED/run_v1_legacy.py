#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Voice Restaurant Assistant - Launcher
======================================
Script de inicio que configura correctamente el PYTHONPATH
"""

import sys
from pathlib import Path

# Agregar el directorio raíz al path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# Ahora importar y ejecutar la app
if __name__ == '__main__':
    from src.api.app import app, settings

    # Configurar salida UTF-8 para Windows
    import sys
    if sys.platform == 'win32':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    print(f"""
================================================================
  VOICE RESTAURANT ASSISTANT
  Servidor iniciado en puerto {settings.FLASK_PORT}
================================================================

Acceso:
   - Local:  http://localhost:{settings.FLASK_PORT}
   - Red:    http://0.0.0.0:{settings.FLASK_PORT}

Health check: http://localhost:{settings.FLASK_PORT}/api/health

Configuracion cargada desde .env

Componentes:
   [OK] STT: Deepgram
   [OK] NLP: Groq
   [OK] TTS: gTTS
   [OK] Restaurant API: {settings.RESTAURANT_API_BASE_URL}

Presiona Ctrl+C para detener el servidor
""")

    app.run(
        host=settings.FLASK_HOST,
        port=settings.FLASK_PORT,
        debug=settings.FLASK_DEBUG
    )
