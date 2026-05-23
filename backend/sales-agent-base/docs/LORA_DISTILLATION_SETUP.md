# Configuración del Sistema de Destilación LoRA

Este documento explica cómo configurar el entrenamiento automático de LoRA usando datos de Cerebras/Gemini (Knowledge Distillation).

## Descripción General

El sistema captura automáticamente las respuestas de Cerebras y Gemini durante la operación normal del asistente. Estos datos se usan para entrenar un modelo LoRA local que puede funcionar **sin internet**.

```
┌─────────────────────────────────────────────────────────────────┐
│                    CON INTERNET (Normal)                        │
│  Cliente → NLU → Cerebras/Gemini → Respuesta + Captura datos   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
                    Entrenamiento semanal
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    SIN INTERNET (Offline)                       │
│  Cliente → NLU → LoRA (entrenado) → Respuesta de calidad       │
└─────────────────────────────────────────────────────────────────┘
```

## Requisitos

### Hardware (PC del Restaurant)
- **GPU NVIDIA** con **8GB+ VRAM** (RTX 3060, 3070, 3080, 4060, etc.)
- **16GB RAM** mínimo
- **50GB** espacio en disco para modelos y datos

### Software
- Windows 10/11 o Ubuntu 20.04+
- Python 3.10+
- CUDA Toolkit 11.8 o 12.x
- Drivers NVIDIA actualizados

## Instalación

### 1. Instalar dependencias de entrenamiento

```bash
cd services/voice-assistant

# Instalar dependencias base
pip install -r requirements.txt

# Instalar dependencias de entrenamiento LoRA
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
pip install transformers>=4.36.0
pip install peft>=0.7.0
pip install trl>=0.7.0
pip install bitsandbytes>=0.41.0
pip install datasets>=2.14.0
pip install accelerate>=0.25.0
```

### 2. Verificar GPU

```bash
python -c "import torch; print(f'GPU: {torch.cuda.get_device_name(0)}')"
```

### 3. Habilitar captura de datos

En el archivo `.env`:

```env
# Habilitar destilación (captura de datos)
ENABLE_DISTILLATION=true

# Directorio de datos (opcional)
DISTILLATION_DATA_PATH=./distillation_data
```

## Uso Manual

### Ver estadísticas de datos capturados

```bash
python -m src.training.distillation_cli stats --days 7
```

### Ver estado del sistema

```bash
python -m src.training.distillation_cli status
```

### Ejecutar entrenamiento manualmente

```bash
# Solo verificar si hay datos suficientes
python -m src.training.distillation_cli run --dry-run

# Entrenar (requiere GPU)
python -m src.training.distillation_cli run --days 14

# Entrenar y promover automáticamente a producción
python -m src.training.distillation_cli run --auto-promote
```

### Promover modelo manualmente

```bash
python -m src.training.distillation_cli promote "models/checkpoints/checkpoint_xxx/final"
```

### Revertir al modelo anterior

```bash
python -m src.training.distillation_cli rollback
```

## Automatización

### Windows (Task Scheduler)

#### Opción 1: Usar el script batch

1. Abre **Task Scheduler** (Programador de tareas)
2. Click en **Create Basic Task**
3. Nombre: `LoRA Training Weekly`
4. Trigger: **Weekly**, Domingo, 3:00 AM
5. Action: **Start a program**
   - Program: `C:\path\to\services\voice-assistant\run_lora_training.bat`
   - Start in: `C:\path\to\services\voice-assistant`
6. Finish

#### Opción 2: Usar el CLI

Abre PowerShell como Administrador:

```powershell
# Instalar tarea programada
python -m src.training.scheduler install-windows --hour 3 --day sunday --install
```

### Linux (Cron)

#### Opción 1: Script bash

```bash
# Dar permisos de ejecución
chmod +x run_lora_training.sh

# Editar crontab
crontab -e

# Añadir esta línea (domingos a las 3 AM):
0 3 * * 0 /path/to/services/voice-assistant/run_lora_training.sh >> /var/log/lora_training.log 2>&1
```

#### Opción 2: Usar el CLI

```bash
# Ver configuración de cron
python -m src.training.scheduler install-cron --hour 3 --day sunday

# Instalar automáticamente
python -m src.training.scheduler install-cron --hour 3 --day sunday --install
```

### Daemon (proceso en background)

```bash
# Iniciar daemon
python -m src.training.scheduler start --hour 3 --day sunday

# Ver estado
python -m src.training.scheduler status

# Detener
python -m src.training.scheduler stop
```

## Configuración Avanzada

### Archivo de configuración

Crea `training_config.yaml` en el directorio del proyecto:

```yaml
distillation:
  # Datos
  min_samples_to_train: 50
  max_samples_per_run: 500
  days_to_collect: 7
  min_quality_score: 0.7

  # Entrenamiento
  num_epochs: 1
  learning_rate: 0.0001
  batch_size: 2

  # Automatización
  auto_promote: true

  # Notificaciones (opcional)
  webhook_url: "https://hooks.slack.com/services/xxx"

scheduler:
  schedule_hour: 3
  schedule_minute: 0
  schedule_day: sunday  # o "daily"
  retry_on_failure: true
  max_retries: 2
```

### Variables de entorno

```env
# Captura de datos
ENABLE_DISTILLATION=true
DISTILLATION_DATA_PATH=./distillation_data

# Modelos
LORA_MODEL_PATH=./models/production

# Notificaciones (opcional)
TRAINING_WEBHOOK_URL=https://hooks.slack.com/services/xxx
TRAINING_EMAIL=admin@restaurant.com
```

## Monitoreo

### Logs de entrenamiento

```bash
# Ver logs recientes
ls -la scheduler_logs/

# Ver último log
cat scheduler_logs/$(ls -t scheduler_logs/ | head -1)
```

### Métricas importantes

- **samples_available**: Datos capturados disponibles
- **samples_used**: Datos usados en entrenamiento
- **training_loss**: Pérdida durante entrenamiento (menor = mejor)
- **improvement_percent**: Mejora vs modelo anterior
- **promoted**: Si el modelo fue promovido a producción

## Solución de Problemas

### Error: "No GPU detected"

```bash
# Verificar CUDA
nvidia-smi

# Verificar PyTorch
python -c "import torch; print(torch.cuda.is_available())"
```

**Solución**: Instalar/actualizar drivers NVIDIA y CUDA toolkit.

### Error: "Insufficient data"

El sistema requiere mínimo 50 muestras para entrenar.

**Solución**: Esperar a que se capturen más datos o usar `--force`:

```bash
python -m src.training.distillation_cli run --force
```

### Error: "Out of memory"

La GPU no tiene suficiente VRAM.

**Solución**: Reducir batch_size en la configuración:

```yaml
distillation:
  batch_size: 1  # Reducir de 2 a 1
```

### El modelo no mejora

Puede que los datos no sean suficientemente diversos.

**Solución**:
1. Recolectar más días de datos
2. Verificar calidad de datos: `python -m src.training.distillation_cli stats`
3. Ajustar `min_quality_score` a un valor más alto (0.8)

## Flujo Recomendado para Restaurant

1. **Semana 1-2**: Operación normal, sistema captura datos automáticamente
2. **Domingo noche**: Entrenamiento automático (3 AM)
3. **Lunes mañana**: Verificar logs, el modelo ya está en producción
4. **Si hay problemas**: Ejecutar `rollback` para volver al modelo anterior

## Comandos Rápidos

```bash
# Estado del sistema
python -m src.training.distillation_cli status

# Estadísticas de datos
python -m src.training.distillation_cli stats

# Entrenar manualmente
python -m src.training.distillation_cli run --auto-promote

# Revertir si hay problemas
python -m src.training.distillation_cli rollback
```

## Soporte

Para problemas o preguntas:
1. Revisar logs en `scheduler_logs/`
2. Verificar GPU con `nvidia-smi`
3. Ejecutar `python -m src.training.distillation_cli status`
