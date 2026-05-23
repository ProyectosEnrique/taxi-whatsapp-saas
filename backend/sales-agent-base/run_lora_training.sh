#!/bin/bash
# ============================================================
# LoRA Training Scheduler - Linux/Mac Bash Script
# ============================================================
#
# Este script ejecuta el pipeline de entrenamiento de LoRA
# con datos de destilacion de Cerebras/Gemini.
#
# USO:
#   ./run_lora_training.sh           # Ejecutar manualmente
#   crontab -e                       # Programar ejecucion
#
# CRON (ejemplo para domingos a las 3 AM):
#   0 3 * * 0 /path/to/run_lora_training.sh >> /path/to/cron.log 2>&1
#
# REQUISITOS:
#   - GPU NVIDIA con 8GB+ VRAM
#   - Python 3.10+
#   - CUDA toolkit instalado
#   - Dependencias instaladas
#
# ============================================================

set -e  # Salir si hay error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$SCRIPT_DIR/scheduler_logs"
LOG_FILE="$LOG_DIR/training_$(date +%Y%m%d_%H%M%S).log"

# Crear directorio de logs si no existe
mkdir -p "$LOG_DIR"

echo ""
echo "============================================================"
echo "  LoRA TRAINING - RESTAURANT VOICE ASSISTANT"
echo "  $(date)"
echo "============================================================"
echo ""

# Cambiar al directorio del proyecto
cd "$SCRIPT_DIR"

# Activar entorno virtual si existe
if [ -f "venv/bin/activate" ]; then
    echo "[INFO] Activando entorno virtual (venv)..."
    source venv/bin/activate
elif [ -f ".venv/bin/activate" ]; then
    echo "[INFO] Activando entorno virtual (.venv)..."
    source .venv/bin/activate
else
    echo "[WARN] No se encontro entorno virtual, usando Python global"
fi

# Verificar GPU
echo ""
echo "[INFO] Verificando GPU..."
python -c "
import torch
if torch.cuda.is_available():
    print(f'GPU: {torch.cuda.get_device_name(0)}')
    print(f'VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB')
else:
    print('GPU: NO DETECTADA')
    exit(1)
" || {
    echo "[ERROR] GPU no disponible o PyTorch no instalado"
    exit 1
}

# Ejecutar pipeline
echo ""
echo "[INFO] Ejecutando pipeline de destilacion..."
echo ""

python -m src.training.scheduler run-once 2>&1 | tee "$LOG_FILE"
RESULT=${PIPESTATUS[0]}

echo ""
if [ $RESULT -eq 0 ]; then
    echo "============================================================"
    echo "  ENTRENAMIENTO COMPLETADO EXITOSAMENTE"
    echo "============================================================"
else
    echo "============================================================"
    echo "  ERROR EN EL ENTRENAMIENTO"
    echo "============================================================"
    echo ""
    echo "Revisa los logs en: $LOG_FILE"
fi

echo ""
echo "Log guardado en: $LOG_FILE"
echo ""

exit $RESULT
