@echo off
REM ============================================================
REM LoRA Training Scheduler - Windows Batch Script
REM ============================================================
REM
REM Este script ejecuta el pipeline de entrenamiento de LoRA
REM con datos de destilacion de Cerebras/Gemini.
REM
REM USO:
REM   - Doble click para ejecutar manualmente
REM   - Programar con Task Scheduler para ejecucion automatica
REM
REM REQUISITOS:
REM   - GPU NVIDIA con 8GB+ VRAM
REM   - Python 3.10+
REM   - Dependencias instaladas (pip install -r requirements.txt)
REM
REM ============================================================

echo.
echo ============================================================
echo   LoRA TRAINING - RESTAURANT VOICE ASSISTANT
echo ============================================================
echo.

REM Cambiar al directorio del proyecto
cd /d "%~dp0"

REM Verificar si existe entorno virtual
if exist "venv\Scripts\activate.bat" (
    echo [INFO] Activando entorno virtual...
    call venv\Scripts\activate.bat
) else if exist ".venv\Scripts\activate.bat" (
    echo [INFO] Activando entorno virtual...
    call .venv\Scripts\activate.bat
) else (
    echo [WARN] No se encontro entorno virtual, usando Python global
)

REM Verificar GPU
echo.
echo [INFO] Verificando GPU...
python -c "import torch; print(f'GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"NO DETECTADA\"}')" 2>nul
if errorlevel 1 (
    echo [ERROR] PyTorch no esta instalado o no detecta GPU
    echo [ERROR] El entrenamiento requiere GPU con CUDA
    goto :error
)

REM Ejecutar pipeline
echo.
echo [INFO] Ejecutando pipeline de destilacion...
echo.
python -m src.training.scheduler run-once

if errorlevel 1 (
    goto :error
)

echo.
echo ============================================================
echo   ENTRENAMIENTO COMPLETADO EXITOSAMENTE
echo ============================================================
echo.

REM Si se ejecuto manualmente (no desde Task Scheduler), pausar
if "%1"=="" (
    echo Presiona cualquier tecla para cerrar...
    pause >nul
)
exit /b 0

:error
echo.
echo ============================================================
echo   ERROR EN EL ENTRENAMIENTO
echo ============================================================
echo.
echo Revisa los logs en: scheduler_logs\
echo.
if "%1"=="" (
    echo Presiona cualquier tecla para cerrar...
    pause >nul
)
exit /b 1
