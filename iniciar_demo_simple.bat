@echo off
echo ================================================================================
echo   DEMO INTERACTIVA - Inicio Rapido (Sin Docker)
echo ================================================================================
echo.
echo Este script inicia solo el WhatsApp Gateway con Python
echo (Ahorra memoria vs Docker)
echo.
echo Tu numero de Twilio Sandbox: +1 415 523 8886
echo.
echo IMPORTANTE: Recuerda haber enviado el "join" al sandbox antes
echo.

pause

echo.
echo [1/2] Verificando dependencias...
cd backend\whatsapp-gateway
pip install -q -r requirements.txt

echo.
echo [2/2] Iniciando WhatsApp Gateway en puerto 8080...
echo.
echo ================================================================================
echo   GATEWAY INICIADO
echo ================================================================================
echo.
echo Servicios disponibles:
echo   - WhatsApp Gateway:  http://localhost:8080/health
echo   - API Docs:          http://localhost:8080/docs
echo.
echo Para probar la demo:
echo   1. Envia un mensaje al WhatsApp Sandbox: +1 415 523 8886
echo   2. Recibiras el menu de industrias (1-6)
echo   3. Selecciona un numero (ej: 1)
echo   4. Abre el link que te envia el bot
echo   5. Completa una compra en la web
echo   6. Recibe confirmacion automatica con puntos
echo.
echo Comandos disponibles en WhatsApp:
echo   - cambiar: Explorar otra industria
echo   - info: Ver planes y precios
echo   - ayuda: Menu de ayuda
echo.
echo Presiona Ctrl+C para detener
echo ================================================================================
echo.

python -m uvicorn src.main:app --host 0.0.0.0 --port 8080 --reload
