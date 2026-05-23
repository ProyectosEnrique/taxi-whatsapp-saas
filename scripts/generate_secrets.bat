@echo off
echo ================================================================================
echo   GENERADOR DE SECRETOS - WhatsApp SAAS
echo ================================================================================
echo.
echo Generando secretos seguros para produccion...
echo.

echo Verificando OpenSSL...
where openssl >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: OpenSSL no esta instalado
    echo.
    echo Opciones:
    echo   1. Instalar Git Bash (incluye OpenSSL)
    echo   2. Instalar OpenSSL desde: https://slproweb.com/products/Win32OpenSSL.html
    echo   3. Usar generador online: https://www.random.org/strings/
    echo.
    pause
    exit /b 1
)

echo.
echo JWT_SECRET:
openssl rand -hex 32
echo.

echo SESSION_SECRET_KEY:
openssl rand -hex 32
echo.

echo ================================================================================
echo   IMPORTANTE:
echo ================================================================================
echo   - Copia estos valores a tu .env.production
echo   - NO los compartas con nadie
echo   - NO los subas a Git
echo ================================================================================
echo.

pause
