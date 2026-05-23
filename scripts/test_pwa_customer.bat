@echo off
echo ========================================
echo TESTING PWA - CUSTOMER APP
echo ========================================
echo.
echo Este script va a:
echo 1. Hacer build de produccion
echo 2. Servir la app
echo 3. Abrir Chrome para testing PWA
echo.
echo Presiona Ctrl+C para cancelar...
timeout /t 3

cd /d "%~dp0\..\frontend\taxi-customer-app"

echo.
echo [1/3] Building para produccion...
call npm run build

if errorlevel 1 (
    echo.
    echo ERROR: El build fallo
    pause
    exit /b 1
)

echo.
echo [2/3] Sirviendo la aplicacion...
echo.
echo Abre Chrome DevTools y ve a:
echo   - Application -^> Manifest
echo   - Lighthouse -^> Progressive Web App
echo.
echo La app estara disponible en: http://localhost:4173
echo.
echo Presiona Ctrl+C para detener el servidor
echo.

call npm run preview
