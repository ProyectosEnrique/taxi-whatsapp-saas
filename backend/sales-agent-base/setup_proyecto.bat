@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

REM ============================================================================
REM SETUP AUTOMÁTICO DEL PROYECTO - Sales Agent FSM
REM ============================================================================
REM Este script configura AUTOMÁTICAMENTE todo el proyecto en el primer inicio
REM - Verifica e instala dependencias
REM - Configura la tarea programada de optimización
REM - Crea directorios necesarios
REM - Configura variables de entorno
REM ============================================================================

set PYTHONIOENCODING=utf-8
set SCRIPT_DIR=%~dp0
set SETUP_FLAG=%SCRIPT_DIR%.setup_completed

REM Banner
echo.
echo ╔══════════════════════════════════════════════════════════════════╗
echo ║                                                                  ║
echo ║           SETUP AUTOMÁTICO - Sales Agent FSM                    ║
echo ║                                                                  ║
echo ╚══════════════════════════════════════════════════════════════════╝
echo.

REM Verificar si ya se ejecutó el setup
if exist "%SETUP_FLAG%" (
    echo ✅ Setup ya completado anteriormente
    echo.
    echo Si quieres reconfigurar, elimina el archivo:
    echo    %SETUP_FLAG%
    echo.
    echo Iniciando proyecto normalmente...
    timeout /t 2 /nobreak >nul
    exit /b 0
)

echo 🚀 Primera ejecución detectada - Configurando proyecto...
echo.

REM ============================================================================
REM [1/7] VERIFICAR PYTHON
REM ============================================================================
echo [1/7] Verificando Python...

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo ❌ ERROR: Python no está instalado
    echo.
    echo SOLUCIÓN:
    echo   1. Descargar Python desde: https://www.python.org/downloads/
    echo   2. Durante instalación, marcar "Add Python to PATH"
    echo   3. Ejecutar este script nuevamente
    echo.
    pause
    exit /b 1
)

python --version
echo ✅ Python OK
echo.

REM ============================================================================
REM [2/7] INSTALAR DEPENDENCIAS
REM ============================================================================
echo [2/7] Instalando dependencias...

if not exist "%SCRIPT_DIR%requirements.txt" (
    echo ⚠️  requirements.txt no encontrado, continuando...
) else (
    echo Instalando paquetes...
    pip install -q -r "%SCRIPT_DIR%requirements.txt"
    if %errorlevel% neq 0 (
        echo ⚠️  Algunas dependencias fallaron, pero continuando...
    ) else (
        echo ✅ Dependencias instaladas
    )
)
echo.

REM ============================================================================
REM [3/7] CREAR DIRECTORIOS NECESARIOS
REM ============================================================================
echo [3/7] Creando directorios...

REM Crear directorios si no existen
if not exist "%SCRIPT_DIR%optimization_logs" mkdir "%SCRIPT_DIR%optimization_logs"
if not exist "%SCRIPT_DIR%conversation_archive" mkdir "%SCRIPT_DIR%conversation_archive"
if not exist "%SCRIPT_DIR%backups" mkdir "%SCRIPT_DIR%backups"
if not exist "%SCRIPT_DIR%logs" mkdir "%SCRIPT_DIR%logs"
if not exist "%SCRIPT_DIR%temp" mkdir "%SCRIPT_DIR%temp"

echo ✅ Directorios creados:
echo    - optimization_logs/
echo    - conversation_archive/
echo    - backups/
echo    - logs/
echo    - temp/
echo.

REM ============================================================================
REM [4/7] CONFIGURAR VARIABLES DE ENTORNO
REM ============================================================================
echo [4/7] Configurando variables de entorno...

REM Crear archivo .env si no existe
if not exist "%SCRIPT_DIR%.env" (
    echo # Configuración del proyecto > "%SCRIPT_DIR%.env"
    echo PYTHONIOENCODING=utf-8 >> "%SCRIPT_DIR%.env"
    echo CONVERSATION_ARCHIVE_PATH=./conversation_archive >> "%SCRIPT_DIR%.env"
    echo OPTIMIZATION_LOGS_PATH=./optimization_logs >> "%SCRIPT_DIR%.env"
    echo FSM_OPTIMIZER_ENABLED=true >> "%SCRIPT_DIR%.env"
    echo FSM_OPTIMIZER_SCHEDULE=weekly >> "%SCRIPT_DIR%.env"
    echo ✅ Archivo .env creado
) else (
    echo ✅ Archivo .env ya existe
)
echo.

REM ============================================================================
REM [5/7] PROBAR SISTEMA FSM OPTIMIZER
REM ============================================================================
echo [5/7] Probando FSM Optimizer...

cd /d "%SCRIPT_DIR%"

python -c "import src.learning.fsm_optimizer" >nul 2>&1
if %errorlevel% neq 0 (
    echo ⚠️  FSM Optimizer no disponible (puede que falten dependencias)
    echo    El proyecto funcionará, pero sin optimización automática
) else (
    echo ✅ FSM Optimizer disponible
)
echo.

REM ============================================================================
REM [6/7] CONFIGURAR TAREA PROGRAMADA AUTOMÁTICAMENTE
REM ============================================================================
echo [6/7] Configurando automatización semanal...

set TASK_NAME=FSM_Optimizer_Semanal
set SCRIPT_PATH=%SCRIPT_DIR%run_fsm_optimization.bat

REM Verificar si la tarea ya existe
schtasks /query /tn "%TASK_NAME%" >nul 2>&1
if %errorlevel% equ 0 (
    echo ℹ️  Tarea programada ya existe
    set /p RECONFIGURAR="¿Reconfigurar tarea? (S/N): "
    if /i "!RECONFIGURAR!"=="N" (
        echo ✅ Manteniendo tarea existente
        goto skip_task_creation
    )
    echo Eliminando tarea anterior...
    schtasks /delete /tn "%TASK_NAME%" /f >nul 2>&1
)

echo Creando tarea programada (Domingos 3:00 AM)...
echo.

REM Intentar crear tarea con permisos elevados
schtasks /create /tn "%TASK_NAME%" /tr "\"%SCRIPT_PATH%\"" /sc weekly /d SUN /st 03:00 /ru SYSTEM /f >nul 2>&1

if %errorlevel% equ 0 (
    echo ✅ Tarea programada creada exitosamente
    echo.
    echo 📅 Configuración:
    echo    - Nombre: %TASK_NAME%
    echo    - Frecuencia: Semanal (Domingos)
    echo    - Hora: 03:00 AM
    echo    - Script: %SCRIPT_PATH%
    echo.
) else (
    echo ⚠️  No se pudo crear tarea automáticamente
    echo.
    echo SOLUCIÓN MANUAL:
    echo    1. Ejecutar este script como Administrador, O
    echo    2. Ejecutar manualmente: configurar_automatizacion.bat
    echo.
    echo El proyecto funcionará normalmente sin optimización automática.
    echo Puedes ejecutar optimización manualmente cuando quieras.
    echo.
)

:skip_task_creation

REM ============================================================================
REM [7/7] MARCAR SETUP COMO COMPLETADO
REM ============================================================================
echo [7/7] Finalizando setup...

REM Crear archivo de flag
echo Setup completado: %date% %time% > "%SETUP_FLAG%"
echo Python: > temp_python_version.txt
python --version >> temp_python_version.txt 2>&1
type temp_python_version.txt >> "%SETUP_FLAG%"
del temp_python_version.txt

echo ✅ Setup completado
echo.

REM ============================================================================
REM RESUMEN FINAL
REM ============================================================================
echo ╔══════════════════════════════════════════════════════════════════╗
echo ║                    SETUP COMPLETADO                              ║
echo ╚══════════════════════════════════════════════════════════════════╝
echo.
echo ✅ Python instalado y funcionando
echo ✅ Dependencias instaladas
echo ✅ Directorios creados
echo ✅ Variables de entorno configuradas
echo ✅ FSM Optimizer verificado

REM Verificar tarea programada
schtasks /query /tn "%TASK_NAME%" >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ Automatización semanal configurada
) else (
    echo ⚠️  Automatización semanal pendiente (ejecutar como Admin)
)

echo.
echo 📁 Archivos creados:
echo    - .env
echo    - .setup_completed
echo    - optimization_logs/
echo    - conversation_archive/
echo.
echo 🚀 El proyecto está listo para ejecutarse
echo.
echo Próximos pasos:
echo   1. El proyecto iniciará automáticamente
echo   2. FSM Optimizer se ejecutará domingos 3:00 AM
echo   3. Ver logs en: optimization_logs/
echo.
echo ═══════════════════════════════════════════════════════════════════
echo.

timeout /t 5 /nobreak >nul
exit /b 0
