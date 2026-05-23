@echo off
REM ============================================================================
REM SCRIPT: Actualizar URLs de Cloudflare Automaticamente (Windows)
REM ============================================================================
REM Este script obtiene las URLs actuales de los tuneles Cloudflare y
REM actualiza automaticamente el archivo .env
REM ============================================================================

echo ================================================================================
echo   ACTUALIZADOR DE URLs DE CLOUDFLARE
echo ================================================================================
echo.

REM Obtener URLs de los tuneles
echo Obteniendo URLs de Cloudflare Tunnels...
echo.

REM URL del Customer App
for /f "tokens=*" %%i in ('docker logs proyecto_b_whatsapp_saas_cloudflare_tunnel_customer 2^>^&1 ^| findstr "trycloudflare.com" ^| findstr "https://"') do set CUSTOMER_LINE=%%i

REM URL del Gateway
for /f "tokens=*" %%i in ('docker logs proyecto_b_whatsapp_saas_cloudflare_tunnel 2^>^&1 ^| findstr "trycloudflare.com" ^| findstr "https://"') do set GATEWAY_LINE=%%i

REM Extraer solo la URL (simple extraction)
for /f "tokens=2" %%a in ("%CUSTOMER_LINE%") do set CUSTOMER_APP_URL=%%a
for /f "tokens=2" %%a in ("%GATEWAY_LINE%") do set GATEWAY_URL=%%a

REM Limpiar espacios y caracteres extra
set CUSTOMER_APP_URL=%CUSTOMER_APP_URL: =%
set GATEWAY_URL=%GATEWAY_URL: =%

REM Verificar que se obtuvieron las URLs
if "%CUSTOMER_APP_URL%"=="" (
    echo ERROR: No se pudo obtener la URL del Customer App
    echo Verifica que el tunel este corriendo:
    echo docker ps ^| findstr cloudflare_tunnel_customer
    pause
    exit /b 1
)

if "%GATEWAY_URL%"=="" (
    echo ERROR: No se pudo obtener la URL del Gateway
    echo Verifica que el tunel este corriendo:
    echo docker ps ^| findstr cloudflare_tunnel
    pause
    exit /b 1
)

REM Mostrar URLs encontradas
echo URLs encontradas:
echo.
echo   Customer App:     %CUSTOMER_APP_URL%
echo   WhatsApp Gateway: %GATEWAY_URL%
echo.

REM Preguntar si actualizar .env
set /p CONFIRM="¿Deseas actualizar el archivo .env con estas URLs? (s/n): "
if /i not "%CONFIRM%"=="s" (
    echo Cancelado.
    pause
    exit /b 0
)

REM Crear backup del .env
echo.
echo Creando backup de .env...
copy .env .env.backup.%date:~-4,4%%date:~-7,2%%date:~-10,2%_%time:~0,2%%time:~3,2%%time:~6,2% >nul 2>&1
echo   Backup creado
echo.

REM Actualizar .env usando PowerShell
echo Actualizando .env...
powershell -Command "(Get-Content .env) -replace '^CUSTOMER_APP_URL=.*', 'CUSTOMER_APP_URL=%CUSTOMER_APP_URL%' | Set-Content .env"
powershell -Command "(Get-Content .env) -replace '^BASE_URL=.*', 'BASE_URL=%GATEWAY_URL%' | Set-Content .env"
echo   .env actualizado
echo.

REM Reiniciar whatsapp-gateway
echo Reiniciando whatsapp-gateway para aplicar cambios...
docker-compose restart whatsapp-gateway >nul 2>&1
echo   whatsapp-gateway reiniciado
echo.

REM Esperar que el contenedor este listo
timeout /t 5 /nobreak >nul

echo ================================================================================
echo   URLs actualizadas exitosamente!
echo ================================================================================
echo.
echo Proximos pasos:
echo    1. Envia un mensaje de prueba por WhatsApp
echo    2. Pide 'ver el menu completo con fotos'
echo    3. Haz clic en la URL generada
echo    4. Verifica que la app del menu se carga correctamente
echo.
echo Para monitorear:
echo    docker logs -f proyecto_b_whatsapp_saas-whatsapp-gateway-1
echo.
pause
