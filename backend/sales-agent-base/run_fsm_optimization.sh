#!/bin/bash
# ============================================================================
# OPTIMIZACIÓN SEMANAL DE FSM
# ============================================================================
# Sistema de mejora continua que analiza conversaciones archivadas y optimiza
# automáticamente la FSM sin necesidad de GPU.
#
# Ejecutar domingos a las 3 AM via cron:
#   0 3 * * 0 /path/to/run_fsm_optimization.sh
#
# Uso manual:
#   ./run_fsm_optimization.sh [--dry-run] [--days N]
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$SCRIPT_DIR/optimization_logs"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$LOG_DIR/fsm_optimization_$TIMESTAMP.log"

# Crear directorio de logs si no existe
mkdir -p "$LOG_DIR"

# Banner
echo "============================================================================" | tee -a "$LOG_FILE"
echo "🧠 OPTIMIZACIÓN SEMANAL DE FSM" | tee -a "$LOG_FILE"
echo "============================================================================" | tee -a "$LOG_FILE"
echo "Timestamp: $TIMESTAMP" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# Activar entorno virtual si existe
if [ -d "$SCRIPT_DIR/venv" ]; then
    echo "🔧 Activando entorno virtual..." | tee -a "$LOG_FILE"
    source "$SCRIPT_DIR/venv/bin/activate"
elif [ -d "$SCRIPT_DIR/.venv" ]; then
    echo "🔧 Activando entorno virtual..." | tee -a "$LOG_FILE"
    source "$SCRIPT_DIR/.venv/bin/activate"
fi

# Cambiar al directorio del proyecto
cd "$SCRIPT_DIR"

# Parsear argumentos
DRY_RUN=""
DAYS=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN="--dry-run"
            echo "🔍 Modo DRY RUN activado (solo preview)" | tee -a "$LOG_FILE"
            shift
            ;;
        --days)
            DAYS="--days $2"
            echo "📅 Analizando últimos $2 días" | tee -a "$LOG_FILE"
            shift 2
            ;;
        *)
            echo "❌ Argumento desconocido: $1" | tee -a "$LOG_FILE"
            echo "Uso: $0 [--dry-run] [--days N]" | tee -a "$LOG_FILE"
            exit 1
            ;;
    esac
done

# Ejecutar optimización
echo "" | tee -a "$LOG_FILE"
echo "🚀 Iniciando análisis de conversaciones..." | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

python -m src.learning.fsm_optimizer $DRY_RUN $DAYS >> "$LOG_FILE" 2>&1
EXIT_CODE=$?

echo "" | tee -a "$LOG_FILE"

if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ Optimización completada exitosamente" | tee -a "$LOG_FILE"

    # Si no es dry-run, considerar recargar el servicio
    if [ -z "$DRY_RUN" ]; then
        echo "" | tee -a "$LOG_FILE"
        echo "🔄 Para aplicar cambios, considerar recargar el servicio:" | tee -a "$LOG_FILE"
        echo "   - Cloud Run: gcloud run services update sales-agent-base --region=REGION" | tee -a "$LOG_FILE"
        echo "   - Docker: docker-compose restart sales-agent-base" | tee -a "$LOG_FILE"
        echo "   - Systemd: sudo systemctl reload sales-agent" | tee -a "$LOG_FILE"
    fi

else
    echo "❌ Optimización falló (código de error: $EXIT_CODE)" | tee -a "$LOG_FILE"
    echo "   Revisar log en: $LOG_FILE" | tee -a "$LOG_FILE"
fi

echo "" | tee -a "$LOG_FILE"
echo "============================================================================" | tee -a "$LOG_FILE"
echo "📊 RESUMEN" | tee -a "$LOG_FILE"
echo "============================================================================" | tee -a "$LOG_FILE"
echo "  Log completo: $LOG_FILE" | tee -a "$LOG_FILE"
echo "  Exit code: $EXIT_CODE" | tee -a "$LOG_FILE"
echo "  Timestamp: $(date)" | tee -a "$LOG_FILE"
echo "============================================================================" | tee -a "$LOG_FILE"

exit $EXIT_CODE
