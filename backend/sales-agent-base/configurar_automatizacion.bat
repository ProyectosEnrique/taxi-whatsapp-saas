@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

REM ============================================================================
REM CONFIGURADOR DE AUTOMATIZACIÓN - FSM Optimizer
REM ============================================================================
REM Este script te ayuda a configurar la ejecución automática semanal
REM ============================================================================

set PYTHONIOENCODING=utf-8

echo.
echo ╔══════════════════════════════════════════════════════════════════╗
echo ║                                                                  ║
echo ║     CONFIGURACIÓN DE AUTOMATIZACIÓN SEMANAL                     ║
echo ║     FSM Optimizer - Sistema de Mejora Continua                  ║
echo ║                                                                  ║
echo ╚══════════════════════════════════════════════════════════════════╝
echo.
echo.

REM Obtener directorio del script
set SCRIPT_DIR=%~dp0
set SCRIPT_PATH=%SCRIPT_DIR%run_fsm_optimization.bat

echo [1/4] Verificando instalación...
echo.

REM Verificar Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ ERROR: Python no está instalado o no está en PATH
    echo.
    echo Solución:
    echo   1. Instalar Python desde https://www.python.org/downloads/
    echo   2. Agregar Python a PATH durante instalación
    echo.
    pause
    exit /b 1
)

echo ✅ Python instalado correctamente
python --version

echo.
echo [2/4] Verificando dependencias...
echo.

cd /d "%SCRIPT_DIR%"

REM Verificar que existe el módulo
python -c "import src.learning.fsm_optimizer" >nul 2>&1
if %errorlevel% neq 0 (
    echo ⚠️  Módulo FSM Optimizer no encontrado
    echo    Instalando dependencias...

    if exist requirements.txt (
        pip install -r requirements.txt
    ) else (
        echo ❌ requirements.txt no encontrado
        pause
        exit /b 1
    )
)

echo ✅ Dependencias OK

echo.
echo [3/4] Probando script de optimización...
echo.

REM Ejecutar test rápido
echo Ejecutando test con --dry-run...
echo.

call "%SCRIPT_PATH%" --dry-run --days 1

if %errorlevel% neq 0 (
    echo.
    echo ❌ ERROR: El script de optimización falló
    echo    Revisar errores arriba
    echo.
    pause
    exit /b 1
)

echo.
echo ✅ Script funciona correctamente
echo.

echo [4/4] Configurando tarea programada...
echo.
echo Para configurar la ejecución automática semanal (domingos 3:00 AM):
echo.
echo OPCIÓN A - Configuración Automática:
echo ─────────────────────────────────────
echo   Ejecutar como Administrador:
echo   ^> schtasks /create /tn "FSM_Optimizer_Semanal" /tr "\"%SCRIPT_PATH%\"" /sc weekly /d SUN /st 03:00 /ru SYSTEM
echo.
echo OPCIÓN B - Configuración Manual (Recomendado):
echo ────────────────────────────────────────────────
echo   1. Presionar Win + R
echo   2. Escribir: taskschd.msc
echo   3. Click en "Crear tarea básica"
echo   4. Configurar:
echo      - Nombre: FSM Optimizer Semanal
echo      - Desencadenador: Semanal
echo      - Día: Domingo
echo      - Hora: 03:00
echo      - Acción: Iniciar programa
echo      - Programa: %SCRIPT_PATH%
echo.

echo ═══════════════════════════════════════════════════════════════════
echo.
echo ✅ CONFIGURACIÓN COMPLETADA
echo.
echo Próximos pasos:
echo   1. Elegir OPCIÓN A o B para configurar tarea programada
echo   2. Ejecutar manualmente: %SCRIPT_PATH%
echo   3. Revisar logs en: %SCRIPT_DIR%optimization_logs\
echo.
echo ═══════════════════════════════════════════════════════════════════
echo.

REM Preguntar si quiere configurar ahora
set /p RESPUESTA="¿Configurar tarea programada AHORA con OPCIÓN A? (S/N): "

if /i "%RESPUESTA%"=="S" (
    echo.
    echo Configurando tarea programada...
    echo.
    echo IMPORTANTE: Esto requiere permisos de administrador.
    echo Si aparece un error, ejecuta este script como Administrador.
    echo.

    schtasks /create /tn "FSM_Optimizer_Semanal" /tr "\"%SCRIPT_PATH%\"" /sc weekly /d SUN /st 03:00 /ru SYSTEM /f

    if %errorlevel% equ 0 (
        echo.
        echo ✅ Tarea programada creada exitosamente
        echo.
        echo La optimización se ejecutará automáticamente cada domingo a las 3:00 AM
        echo.
        echo Para ver la tarea:
        echo   ^> taskschd.msc
        echo.
        echo Para ejecutar ahora (test):
        echo   ^> schtasks /run /tn "FSM_Optimizer_Semanal"
        echo.
    ) else (
        echo.
        echo ❌ No se pudo crear la tarea automáticamente
        echo    Usa la OPCIÓN B (configuración manual)
        echo.
    )
) else (
    echo.
    echo ℹ️  OK, usa la OPCIÓN B para configurar manualmente
    echo    Las instrucciones están arriba ↑
    echo.
)

echo.
pause
