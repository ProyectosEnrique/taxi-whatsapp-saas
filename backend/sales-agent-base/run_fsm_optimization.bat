@echo off
chcp 65001 >nul
REM ============================================================================
REM OPTIMIZACIÓN SEMANAL DE FSM (Windows)
REM ============================================================================
REM Sistema de mejora continua que analiza conversaciones archivadas y optimiza
REM automáticamente la FSM sin necesidad de GPU.
REM
REM Ejecutar con Programador de Tareas de Windows:
REM   - Crear tarea que se ejecute domingos a las 3 AM
REM   - Ejecutar: C:\path\to\run_fsm_optimization.bat
REM
REM Uso manual:
REM   run_fsm_optimization.bat [--dry-run] [--days N]
REM ============================================================================

setlocal enabledelayedexpansion

REM Configurar UTF-8 para evitar problemas de encoding
set PYTHONIOENCODING=utf-8

REM Obtener directorio del script
set SCRIPT_DIR=%~dp0
set LOG_DIR=%SCRIPT_DIR%optimization_logs

REM Crear directorio de logs si no existe
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

REM Timestamp
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set datetime=%%I
set TIMESTAMP=%datetime:~0,8%_%datetime:~8,6%
set LOG_FILE=%LOG_DIR%\fsm_optimization_%TIMESTAMP%.log

REM Banner
echo ============================================================================ > "%LOG_FILE%"
echo 🧠 OPTIMIZACIÓN SEMANAL DE FSM >> "%LOG_FILE%"
echo ============================================================================ >> "%LOG_FILE%"
echo Timestamp: %TIMESTAMP% >> "%LOG_FILE%"
echo. >> "%LOG_FILE%"

echo ============================================================================
echo 🧠 OPTIMIZACIÓN SEMANAL DE FSM
echo ============================================================================
echo Timestamp: %TIMESTAMP%
echo.

REM Activar entorno virtual si existe
if exist "%SCRIPT_DIR%venv\Scripts\activate.bat" (
    echo 🔧 Activando entorno virtual... >> "%LOG_FILE%"
    echo 🔧 Activando entorno virtual...
    call "%SCRIPT_DIR%venv\Scripts\activate.bat"
) else if exist "%SCRIPT_DIR%.venv\Scripts\activate.bat" (
    echo 🔧 Activando entorno virtual... >> "%LOG_FILE%"
    echo 🔧 Activando entorno virtual...
    call "%SCRIPT_DIR%.venv\Scripts\activate.bat"
)

REM Cambiar al directorio del proyecto
cd /d "%SCRIPT_DIR%"

REM Construir comando con argumentos
set ARGS=
set DRY_RUN=0

:parse_args
if "%~1"=="" goto end_parse
if /i "%~1"=="--dry-run" (
    set ARGS=%ARGS% --dry-run
    set DRY_RUN=1
    echo 🔍 Modo DRY RUN activado (solo preview) >> "%LOG_FILE%"
    echo 🔍 Modo DRY RUN activado (solo preview)
    shift
    goto parse_args
)
if /i "%~1"=="--days" (
    set ARGS=%ARGS% --days %~2
    echo 📅 Analizando últimos %~2 días >> "%LOG_FILE%"
    echo 📅 Analizando últimos %~2 días
    shift
    shift
    goto parse_args
)
echo ❌ Argumento desconocido: %~1 >> "%LOG_FILE%"
echo ❌ Argumento desconocido: %~1
echo Uso: %~nx0 [--dry-run] [--days N]
exit /b 1

:end_parse

REM Ejecutar optimización
echo. >> "%LOG_FILE%"
echo 🚀 Iniciando análisis de conversaciones... >> "%LOG_FILE%"
echo 🚀 Iniciando análisis de conversaciones...
echo. >> "%LOG_FILE%"
echo.

python -m src.learning.fsm_optimizer %ARGS% >> "%LOG_FILE%" 2>&1
set EXIT_CODE=%ERRORLEVEL%

echo. >> "%LOG_FILE%"
echo.

if %EXIT_CODE%==0 (
    echo ✅ Optimización completada exitosamente >> "%LOG_FILE%"
    echo ✅ Optimización completada exitosamente

    REM Si no es dry-run, mostrar instrucciones
    if %DRY_RUN%==0 (
        echo. >> "%LOG_FILE%"
        echo 🔄 Para aplicar cambios, considerar recargar el servicio: >> "%LOG_FILE%"
        echo    - Cloud Run: gcloud run services update sales-agent-base --region=REGION >> "%LOG_FILE%"
        echo    - Docker: docker-compose restart sales-agent-base >> "%LOG_FILE%"
        echo.
        echo 🔄 Para aplicar cambios, considerar recargar el servicio:
        echo    - Cloud Run: gcloud run services update sales-agent-base --region=REGION
        echo    - Docker: docker-compose restart sales-agent-base
    )
) else (
    echo ❌ Optimización falló (código de error: %EXIT_CODE%) >> "%LOG_FILE%"
    echo    Revisar log en: %LOG_FILE% >> "%LOG_FILE%"
    echo ❌ Optimización falló (código de error: %EXIT_CODE%)
    echo    Revisar log en: %LOG_FILE%
)

echo. >> "%LOG_FILE%"
echo ============================================================================ >> "%LOG_FILE%"
echo 📊 RESUMEN >> "%LOG_FILE%"
echo ============================================================================ >> "%LOG_FILE%"
echo   Log completo: %LOG_FILE% >> "%LOG_FILE%"
echo   Exit code: %EXIT_CODE% >> "%LOG_FILE%"
echo   Timestamp: %date% %time% >> "%LOG_FILE%"
echo ============================================================================ >> "%LOG_FILE%"

echo.
echo ============================================================================
echo 📊 RESUMEN
echo ============================================================================
echo   Log completo: %LOG_FILE%
echo   Exit code: %EXIT_CODE%
echo   Timestamp: %date% %time%
echo ============================================================================

exit /b %EXIT_CODE%
