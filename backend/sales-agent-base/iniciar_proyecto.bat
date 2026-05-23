@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

REM ============================================================================
REM INICIAR PROYECTO - Sales Agent FSM
REM ============================================================================
REM Este es el ÚNICO archivo que necesitas ejecutar para iniciar el proyecto
REM Se encarga de:
REM   1. Ejecutar setup automático (solo primera vez)
REM   2. Verificar que todo esté configurado
REM   3. Iniciar el servidor
REM ============================================================================

set PYTHONIOENCODING=utf-8
set SCRIPT_DIR=%~dp0
set SETUP_FLAG=%SCRIPT_DIR%.setup_completed

REM Banner inicial
cls
echo.
echo ╔══════════════════════════════════════════════════════════════════╗
echo ║                                                                  ║
echo ║              SALES AGENT FSM - Inicio del Proyecto              ║
echo ║                                                                  ║
echo ╚══════════════════════════════════════════════════════════════════╝
echo.

REM ============================================================================
REM VERIFICAR Y EJECUTAR SETUP SI ES NECESARIO
REM ============================================================================

if not exist "%SETUP_FLAG%" (
    echo 🔧 Primera ejecución detectada...
    echo.
    echo Ejecutando configuración automática del proyecto...
    echo Esto solo sucede UNA VEZ.
    echo.

    REM Ejecutar setup automático
    call "%SCRIPT_DIR%setup_proyecto.bat"

    if %errorlevel% neq 0 (
        echo.
        echo ❌ ERROR: Setup falló
        echo.
        pause
        exit /b 1
    )

    echo.
    echo ═══════════════════════════════════════════════════════════════════
    echo.
    echo ✅ Configuración completada
    echo.
    echo Continuando con inicio del proyecto...
    timeout /t 3 /nobreak >nul
    cls
) else (
    echo ✅ Proyecto ya configurado
    echo.
)

REM ============================================================================
REM VERIFICAR PYTHON
REM ============================================================================

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ ERROR: Python no encontrado
    echo.
    echo Ejecuta setup_proyecto.bat primero
    pause
    exit /b 1
)

REM ============================================================================
REM VERIFICAR DIRECTORIOS
REM ============================================================================

if not exist "%SCRIPT_DIR%optimization_logs" mkdir "%SCRIPT_DIR%optimization_logs"
if not exist "%SCRIPT_DIR%conversation_archive" mkdir "%SCRIPT_DIR%conversation_archive"
if not exist "%SCRIPT_DIR%logs" mkdir "%SCRIPT_DIR%logs"

REM ============================================================================
REM MOSTRAR ESTADO DE AUTOMATIZACIÓN
REM ============================================================================

echo 📊 Estado del sistema:
echo.

REM Verificar tarea programada
schtasks /query /tn "FSM_Optimizer_Semanal" >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ Automatización semanal: ACTIVA

    REM Obtener próxima ejecución
    for /f "tokens=3,4" %%a in ('schtasks /query /tn "FSM_Optimizer_Semanal" /fo list ^| findstr "Próxima"') do (
        echo    Próxima ejecución: %%a %%b
    )
) else (
    echo ⚠️  Automatización semanal: NO CONFIGURADA
    echo    Para configurar: ejecuta como Administrador
)

echo.
echo ✅ Python:
python --version
echo.

REM ============================================================================
REM MODO DE INICIO
REM ============================================================================

echo.
echo ¿Cómo deseas iniciar el proyecto?
echo.
echo [1] Modo SERVIDOR (API REST) - Puerto 5000
echo [2] Modo DESARROLLO (con debug)
echo [3] Ejecutar OPTIMIZACIÓN AHORA (test)
echo [4] Ver LOGS de optimización
echo [5] Salir
echo.

set /p OPCION="Selecciona una opción (1-5): "

if "%OPCION%"=="1" goto servidor
if "%OPCION%"=="2" goto desarrollo
if "%OPCION%"=="3" goto optimizacion
if "%OPCION%"=="4" goto logs
if "%OPCION%"=="5" goto salir

echo Opción inválida
goto salir

REM ============================================================================
:servidor
REM ============================================================================
echo.
echo 🚀 Iniciando servidor en modo PRODUCCIÓN...
echo.
echo Servidor: http://localhost:5000
echo Documentación: http://localhost:5000/docs (si está configurado)
echo.
echo Presiona Ctrl+C para detener
echo.
echo ═══════════════════════════════════════════════════════════════════
echo.

cd /d "%SCRIPT_DIR%"
python run_v2.py

goto salir

REM ============================================================================
:desarrollo
REM ============================================================================
echo.
echo 🛠️  Iniciando servidor en modo DESARROLLO...
echo.
echo IMPORTANTE: Modo debug activado
echo   - Auto-reload al cambiar código
echo   - Stack traces detallados
echo   - NO usar en producción
echo.
echo Servidor: http://localhost:5000
echo.
echo Presiona Ctrl+C para detener
echo.
echo ═══════════════════════════════════════════════════════════════════
echo.

cd /d "%SCRIPT_DIR%"
set FLASK_DEBUG=true
python run_v2.py

goto salir

REM ============================================================================
:optimizacion
REM ============================================================================
echo.
echo 🧠 Ejecutando FSM Optimizer (modo test)...
echo.

cd /d "%SCRIPT_DIR%"
call run_fsm_optimization.bat --dry-run --days 7

echo.
echo ✅ Optimización completada
echo.
echo Ver reporte en: optimization_logs\
echo.

pause
goto salir

REM ============================================================================
:logs
REM ============================================================================
echo.
echo 📊 Últimos logs de optimización:
echo.

cd /d "%SCRIPT_DIR%optimization_logs"

REM Listar últimos 5 logs
dir /o-d /b *.log 2>nul | head -5

if %errorlevel% neq 0 (
    echo ℹ️  No hay logs todavía
    echo    Ejecuta la optimización primero
) else (
    echo.
    set /p VER_LOG="¿Ver último log completo? (S/N): "

    if /i "!VER_LOG!"=="S" (
        echo.
        echo ═══════════════════════════════════════════════════════════════════
        for /f "delims=" %%i in ('dir /b /o-d *.log 2^>nul') do (
            type "%%i"
            goto break_log
        )
        :break_log
        echo ═══════════════════════════════════════════════════════════════════
    )
)

echo.
pause
goto salir

REM ============================================================================
:salir
REM ============================================================================
echo.
echo 👋 Hasta pronto
echo.

exit /b 0
