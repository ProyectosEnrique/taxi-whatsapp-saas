@echo off
echo ================================================================================
echo   INICIAR DEMO INTERACTIVA - Sistema de Ventas por WhatsApp
echo ================================================================================
echo.
echo Este script iniciara la demo completa con:
echo   - WhatsApp Gateway (puerto 8080)
echo   - Frontend Web (puerto 3000)
echo   - Admin Panel (puerto 8081)
echo.
echo IMPORTANTE: Asegurate de haber configurado el archivo .env con:
echo   - TWILIO_ACCOUNT_SID
echo   - TWILIO_AUTH_TOKEN
echo   - TWILIO_WHATSAPP_NUMBER
echo   - BASE_URL (tu URL de Cloudflare)
echo.

pause

echo.
echo [1/3] Deteniendo contenedores previos...
docker-compose -f docker-compose.demo.yml down

echo.
echo [2/3] Construyendo imagenes...
docker-compose -f docker-compose.demo.yml build

echo.
echo [3/3] Iniciando servicios...
docker-compose -f docker-compose.demo.yml up -d

echo.
echo ================================================================================
echo   DEMO INICIADA EXITOSAMENTE
echo ================================================================================
echo.
echo Servicios disponibles:
echo   - WhatsApp Gateway:  http://localhost:8080/health
echo   - Frontend Web:      http://localhost:3000
echo   - Admin Panel:       http://localhost:8081
echo.
echo Logs en tiempo real:
echo   docker-compose -f docker-compose.demo.yml logs -f whatsapp-gateway
echo.
echo Para probar la demo:
echo   1. Envia un mensaje al numero de Twilio WhatsApp
echo   2. Recibiras el menu de industrias
echo   3. Selecciona un numero (1-6)
echo   4. Abre el link que te envia el bot
echo   5. Completa una compra en la web
echo   6. Recibe confirmacion automatica con puntos
echo.
echo ================================================================================
echo.

pause
