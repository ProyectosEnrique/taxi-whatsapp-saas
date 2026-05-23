@echo off
REM ================================================================================
REM INICIAR PROYECTO_B_WHATSAPP_SAAS - Multi-Tenant System
REM ================================================================================

cd /d "%~dp0"

echo.
echo ================================================================================
echo INICIANDO PROYECTO_B_WHATSAPP_SAAS - Sistema Multi-Tenant
echo ================================================================================
echo.
echo Tenants configurados:
echo  1. restaurante-sabor-sur  (67 productos - Comida mexicana)
echo  2. vineteria-premium      (70 productos - Vinos y licores)
echo  3. farmasalud-24         (62 productos - Farmacia)
echo.
echo ================================================================================
echo.

REM Verificar que Docker este corriendo
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker no esta corriendo
    echo.
    echo Por favor:
    echo 1. Abre Docker Desktop
    echo 2. Espera a que diga "Docker Desktop is running"
    echo 3. Ejecuta este script de nuevo
    echo.
    pause
    exit /b 1
)

echo [OK] Docker esta corriendo
echo.

echo ================================================================================
echo OPCION DE INICIO
echo ================================================================================
echo.
echo Elige como quieres iniciar el proyecto:
echo.
echo 1. LIGERO - Solo WhatsApp (3 servicios, usa ~1 GB RAM) - RECOMENDADO
echo 2. COMPLETO - Todos los servicios (5 servicios, usa ~2 GB RAM)
echo.
set /p OPCION="Ingresa 1 o 2: "

if "%OPCION%"=="1" (
    echo.
    echo ================================================================================
    echo Iniciando MODO LIGERO (WhatsApp Gateway + Sales Agent + API Service)...
    echo ================================================================================
    echo.
    docker-compose up -d whatsapp-gateway sales-agent api-service
) else if "%OPCION%"=="2" (
    echo.
    echo ================================================================================
    echo Iniciando MODO COMPLETO (Todos los servicios)...
    echo ================================================================================
    echo.
    docker-compose up -d
) else (
    echo.
    echo [ERROR] Opcion invalida. Usando MODO LIGERO por defecto...
    echo.
    docker-compose up -d whatsapp-gateway sales-agent api-service
)

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Hubo un problema al iniciar los contenedores
    echo.
    echo Revisa los errores arriba y ejecuta este comando para ver logs:
    echo   docker-compose logs
    echo.
    pause
    exit /b 1
)

echo.
echo ================================================================================
echo Esperando a que los servicios inicien...
echo ================================================================================
timeout /t 10 /nobreak

echo.
echo ================================================================================
echo Verificando estado de los servicios...
echo ================================================================================
echo.
docker-compose ps

echo.
echo ================================================================================
echo SERVICIOS INICIADOS
echo ================================================================================
echo.
echo Servicios disponibles:
echo  - WhatsApp Gateway: http://localhost:8095
echo  - Sales Agent:      http://localhost:5000
echo  - API Service:      http://localhost:5011
echo.
echo Base de datos:
echo  - SQLite: backend\api-service-base\menu-service\menu_service.db
echo  - 3 tenants configurados
echo  - 199 productos cargados
echo.
echo ================================================================================
echo SIGUIENTE PASO: Configurar Webhook de Twilio
echo ================================================================================
echo.
echo 1. Abrir otra ventana de comandos
echo 2. Ejecutar: ngrok http 8095
echo 3. Copiar la URL de ngrok (ejemplo: https://abc123.ngrok.io)
echo 4. Configurar en Twilio:
echo    https://console.twilio.com/us1/develop/sms/settings/whatsapp-sandbox
echo    Webhook URL: https://abc123.ngrok.io/webhook/whatsapp
echo    Metodo: POST
echo.
echo 5. Enviar mensaje desde WhatsApp a: +14155238886
echo.
echo ================================================================================
echo Ver logs en tiempo real:
echo   docker-compose logs -f
echo.
echo Detener servicios:
echo   docker-compose down
echo ================================================================================
echo.
pause
