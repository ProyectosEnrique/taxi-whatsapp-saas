@echo off
REM ================================================================================
REM INICIAR NGROK PARA WEBHOOK DE WHATSAPP
REM ================================================================================

echo.
echo ================================================================================
echo INICIANDO NGROK - Tunnel para WhatsApp Webhook
echo ================================================================================
echo.
echo Este script:
echo 1. Expone el puerto 8095 (WhatsApp Gateway) a internet
echo 2. Genera una URL publica para configurar en Twilio
echo.
echo IMPORTANTE: Deja esta ventana ABIERTA mientras uses WhatsApp
echo ================================================================================
echo.

REM Verificar si ngrok esta instalado
where ngrok >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] ngrok no esta instalado
    echo.
    echo Descargalo en: https://ngrok.com/download
    echo.
    echo Opciones de instalacion:
    echo 1. Con Chocolatey: choco install ngrok
    echo 2. Descargar ZIP y agregar a PATH
    echo.
    pause
    exit /b 1
)

echo [OK] ngrok encontrado
echo.
echo Iniciando tunnel en puerto 8095...
echo.
echo ================================================================================
echo COPIA LA URL QUE APARECE ABAJO (ejemplo: https://abc123.ngrok.io)
echo ================================================================================
echo.
echo Configurala en Twilio:
echo 1. Ve a: https://console.twilio.com/us1/develop/sms/settings/whatsapp-sandbox
echo 2. En "When a message comes in":
echo    URL: https://ABC123.ngrok.io/webhook/whatsapp
echo    Metodo: POST
echo 3. Click SAVE
echo.
echo ================================================================================
echo.

ngrok http 8095
