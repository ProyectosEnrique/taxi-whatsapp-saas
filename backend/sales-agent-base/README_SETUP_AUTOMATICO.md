# Setup Automático - Sales Agent FSM v2.0

**Estado:** Completamente implementado
**Fecha:** 2026-01-04
**Versión:** 1.0

---

## ¿Qué es esto?

Este proyecto incluye un **sistema de configuración 100% automático** que:

1. Se ejecuta automáticamente la primera vez que inicias el proyecto
2. Configura TODO sin necesidad de intervención manual
3. Crea directorios, instala dependencias y configura automatización
4. Solo necesitas ejecutar UN archivo para iniciar todo

**NO necesitas seguir tutoriales complicados. Todo es automático.**

---

## Inicio Rápido (3 segundos)

### Opción 1: Windows (Recomendado)

```batch
# Doble click en:
iniciar_proyecto.bat
```

**Eso es todo.** El resto es automático.

### Opción 2: Python

```bash
python run_auto.py
```

**Eso es todo.** El resto es automático.

### Opción 3: Docker

```bash
docker-compose up sales-agent
```

**Eso es todo.** El resto es automático.

---

## ¿Qué pasa en la primera ejecución?

Cuando ejecutas el proyecto por primera vez, el sistema:

```
[1/7] ✅ Verifica Python instalado
[2/7] ✅ Instala dependencias (requirements.txt)
[3/7] ✅ Crea directorios necesarios
      - optimization_logs/
      - conversation_archive/
      - backups/
      - logs/
      - temp/
[4/7] ✅ Configura variables de entorno (.env)
[5/7] ✅ Prueba FSM Optimizer
[6/7] ✅ Configura tarea programada (Domingos 3:00 AM)
[7/7] ✅ Marca setup como completado (.setup_completed)

🎉 ¡Listo! El servidor inicia automáticamente
```

**Tiempo total:** 30-60 segundos

**Ejecuciones siguientes:** 2-3 segundos (solo inicia el servidor)

---

## Archivos del Sistema de Setup

### Archivos principales (usuarios)

| Archivo | Para qué |
|---------|----------|
| **`iniciar_proyecto.bat`** | **INICIO PRINCIPAL** - Doble click para iniciar todo |
| **`run_auto.py`** | Inicio alternativo con Python |
| `setup_proyecto.bat` | Setup manual (si quieres reconfigurar) |
| `.setup_completed` | Flag que marca setup completado |

### Archivos internos (sistema)

| Archivo | Propósito |
|---------|-----------|
| `src/setup_auto.py` | Módulo Python de configuración automática |
| `run_v2.py` | Runner básico (sin auto-setup) |
| `configurar_automatizacion.bat` | Configurador de tarea programada |
| `run_fsm_optimization.bat` | Script de optimización semanal |

---

## Características del Setup Automático

### 1. Detección de primera ejecución

El sistema detecta automáticamente si es la primera vez que ejecutas el proyecto:

```python
# src/setup_auto.py
class AutoSetup:
    def __init__(self):
        self.setup_flag = self.base_dir / '.setup_completed'
        self.first_run = not self.setup_flag.exists()

    def run(self, silent=False):
        if self.first_run:
            # Ejecutar configuración completa
            self._create_directories()
            self._configure_automation()
            self._mark_setup_complete()
        else:
            # Solo verificar que todo esté OK
            print("✅ Proyecto ya configurado")
```

### 2. Configuración de automatización

El sistema configura automáticamente la tarea programada de Windows:

```batch
# Tarea programada en Task Scheduler
Nombre: FSM_Optimizer_Semanal
Frecuencia: Semanal (Domingos)
Hora: 03:00 AM
Script: run_fsm_optimization.bat
Usuario: SYSTEM (no requiere login)
```

**Sin intervención manual.** Si requiere permisos de administrador, lo indica pero continúa.

### 3. Creación de directorios

Crea automáticamente todos los directorios necesarios:

```
backend/sales-agent-base/
├── optimization_logs/      # Logs del FSM Optimizer
├── conversation_archive/   # Conversaciones archivadas
├── backups/               # Backups automáticos
├── logs/                  # Logs del servidor
└── temp/                  # Archivos temporales
```

### 4. Variables de entorno

Crea archivo `.env` con configuración por defecto:

```env
# .env (creado automáticamente)
PYTHONIOENCODING=utf-8
CONVERSATION_ARCHIVE_PATH=./conversation_archive
OPTIMIZATION_LOGS_PATH=./optimization_logs
FSM_OPTIMIZER_ENABLED=true
FSM_OPTIMIZER_SCHEDULE=weekly
```

---

## Modos de Inicio

Cuando ejecutas `iniciar_proyecto.bat`, verás un menú:

```
¿Cómo deseas iniciar el proyecto?

[1] Modo SERVIDOR (API REST) - Puerto 5000
[2] Modo DESARROLLO (con debug)
[3] Ejecutar OPTIMIZACIÓN AHORA (test)
[4] Ver LOGS de optimización
[5] Salir
```

### Opción 1: Modo Servidor (Producción)

```batch
🚀 Servidor: http://localhost:5000
📡 API disponible
🔒 Debug desactivado
```

**Uso:** Producción local, pruebas finales

### Opción 2: Modo Desarrollo

```batch
🛠️ Servidor: http://localhost:5000
🔄 Auto-reload activado
🐛 Stack traces detallados
⚠️ NO usar en producción
```

**Uso:** Desarrollo, debugging

### Opción 3: Optimización Manual

```batch
🧠 Ejecuta FSM Optimizer ahora
📊 Analiza últimos 7 días
📁 Genera reporte en optimization_logs/
```

**Uso:** Probar optimización sin esperar al domingo

### Opción 4: Ver Logs

```batch
📊 Lista últimos logs generados
📄 Muestra contenido del último log
```

**Uso:** Revisar resultados de optimización

---

## Verificación del Setup

### Verificar que el setup se ejecutó correctamente

```batch
# 1. Verificar flag de setup
dir .setup_completed

# 2. Verificar directorios creados
dir optimization_logs conversation_archive backups logs temp

# 3. Verificar tarea programada
schtasks /query /tn "FSM_Optimizer_Semanal"

# 4. Verificar variables de entorno
type .env
```

### Verificar automatización

```batch
# Ver estado de la tarea
schtasks /query /tn "FSM_Optimizer_Semanal" /fo list

# Ver próxima ejecución
schtasks /query /tn "FSM_Optimizer_Semanal" /fo list | findstr "Próxima"

# Ejecutar tarea manualmente (test)
schtasks /run /tn "FSM_Optimizer_Semanal"
```

---

## Reconfigurar el Setup

Si quieres volver a ejecutar el setup (por ejemplo, después de cambios):

### Método 1: Eliminar flag

```batch
# Eliminar archivo de flag
del .setup_completed

# Ejecutar proyecto normalmente
iniciar_proyecto.bat
```

El setup se ejecutará de nuevo automáticamente.

### Método 2: Ejecutar setup manual

```batch
# Ejecutar setup directamente
setup_proyecto.bat
```

### Método 3: Python

```bash
# Ejecutar desde Python
python -c "from src.setup_auto import setup_proyecto; setup_proyecto(silent=False)"
```

---

## Uso en Docker

El Dockerfile incluye el setup automático integrado:

```dockerfile
# Dockerfile
ENV PYTHONIOENCODING=utf-8

# Crea directorios automáticamente
RUN mkdir -p optimization_logs conversation_archive backups

# Usa run_auto.py que ejecuta setup en primera ejecución
CMD ["python", "run_auto.py"]
```

### Ejecutar con Docker:

```bash
# Build
docker build -t sales-agent .

# Run
docker run -p 5000:5000 sales-agent
```

El setup se ejecuta automáticamente dentro del contenedor.

### Ejecutar con Docker Compose:

```bash
docker-compose up sales-agent
```

---

## Troubleshooting

### "Setup no se ejecutó automáticamente"

**Causa:** El flag `.setup_completed` ya existe de una ejecución anterior

**Solución:**
```batch
del .setup_completed
iniciar_proyecto.bat
```

### "No se pudo crear tarea programada"

**Causa:** Requiere permisos de administrador

**Solución 1 (Recomendada):**
```batch
# Ejecutar como Administrador
configurar_automatizacion.bat
```

**Solución 2 (Manual):**
1. `Win + R` → `taskschd.msc`
2. Crear tarea básica
3. Script: `run_fsm_optimization.bat`
4. Frecuencia: Semanal, Domingo, 03:00

### "Python no encontrado"

**Causa:** Python no está en PATH

**Solución:**
1. Descargar Python: https://www.python.org/downloads/
2. Reinstalar marcando "Add Python to PATH"
3. Ejecutar `setup_proyecto.bat` de nuevo

### "Error al importar módulos"

**Causa:** Dependencias no instaladas

**Solución:**
```bash
pip install -r requirements.txt
```

O ejecutar:
```batch
setup_proyecto.bat
```

---

## Arquitectura del Setup Automático

### Flujo de ejecución

```
Usuario ejecuta: iniciar_proyecto.bat
    ↓
¿Existe .setup_completed?
    ↓ NO
setup_proyecto.bat (setup automático)
    ↓
1. Verificar Python
2. Instalar dependencias
3. Crear directorios
4. Crear .env
5. Probar FSM Optimizer
6. Configurar tarea programada
7. Crear .setup_completed
    ↓
Iniciar servidor (run_auto.py)
    ↓
    ↓ SÍ
Iniciar servidor directamente
```

### Componentes

```
Setup Automático
├── Detección de primera ejecución
│   └── Archivo flag: .setup_completed
├── Verificaciones
│   ├── Python instalado
│   ├── Módulos disponibles
│   └── Permisos de escritura
├── Configuración
│   ├── Directorios
│   ├── Variables de entorno
│   └── Tarea programada
└── Inicio del servidor
    ├── Inicialización FSM
    └── Flask app
```

---

## Integración con CI/CD

### GitHub Actions

```yaml
# .github/workflows/deploy.yml
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Run auto setup
        run: |
          cd backend/sales-agent-base
          python run_auto.py &
          sleep 10
          curl http://localhost:5000/api/health
```

### GitLab CI

```yaml
# .gitlab-ci.yml
test:
  script:
    - cd backend/sales-agent-base
    - python run_auto.py &
    - sleep 10
    - curl http://localhost:5000/api/health
```

---

## Preguntas Frecuentes

### ¿Necesito configurar algo manualmente?

**No.** Todo es automático. Solo ejecuta `iniciar_proyecto.bat`.

### ¿Qué pasa si ejecuto el setup dos veces?

El sistema detecta que ya está configurado y no hace nada.

### ¿Puedo desactivar el setup automático?

Sí, usa `run_v2.py` en lugar de `run_auto.py`:

```bash
python run_v2.py
```

### ¿Funciona en Linux/Mac?

Sí, pero la configuración de tarea programada requiere cron:

```bash
# Agregar a crontab
0 3 * * 0 /path/to/run_fsm_optimization.sh
```

El resto del setup funciona igual.

### ¿Cuánto espacio ocupa?

```
Directorios creados: ~1-5 MB (inicial)
Logs (por semana): ~100-500 KB
Total después de 1 mes: ~5-10 MB
```

### ¿Puedo cambiar el horario de optimización?

Sí:

1. `Win + R` → `taskschd.msc`
2. Click derecho en "FSM_Optimizer_Semanal"
3. Propiedades → Desencadenadores
4. Cambiar horario

O ejecutar:
```batch
configurar_automatizacion.bat
```

---

## Archivos Generados

Después del primer setup, verás:

```
backend/sales-agent-base/
├── .setup_completed          # Flag de setup completado
├── .env                      # Variables de entorno
├── optimization_logs/        # Logs de optimización
├── conversation_archive/     # Conversaciones archivadas
├── backups/                  # Backups automáticos
├── logs/                     # Logs del servidor
└── temp/                     # Archivos temporales
```

**NO elimines `.setup_completed` a menos que quieras reconfigurar.**

---

## Monitoreo del Setup

### Ver estado del sistema

```batch
# Ejecutar desde CMD
python -c "from src.setup_auto import verificar_automatizacion; verificar_automatizacion()"
```

Salida:
```
════════════════════════════════════════════════════════════════════
  📅 ESTADO DE AUTOMATIZACIÓN
════════════════════════════════════════════════════════════════════

✅ Automatización CONFIGURADA
   Tarea: FSM_Optimizer_Semanal
   Próxima ejecución: 05/01/2026 03:00

   El FSM Optimizer se ejecutará automáticamente
   cada domingo a las 3:00 AM.

════════════════════════════════════════════════════════════════════
```

### Logs del setup

El setup guarda información en `.setup_completed`:

```
Setup completado: 04/01/2026 15:30
Python: Python 3.11.0
Platform: Windows-10-10.0.19045-SP0
```

---

## Próximos Pasos

Una vez configurado el setup automático:

1. **Ejecutar el proyecto:** `iniciar_proyecto.bat`
2. **Probar optimización:** Opción [3] en el menú
3. **Ver resultados:** Opción [4] en el menú
4. **Esperar al domingo:** La optimización se ejecutará automáticamente

### Documentación adicional

- `CONFIGURACION_AUTOMATIZACION_COMPLETADA.md` - Guía de automatización
- `GUIA_AUTOMATIZACION.md` - Configuración manual detallada
- `WEEKLY_IMPROVEMENTS.md` - Sistema de mejora continua
- `ARQUITECTURA_MULTI_TENANT.md` - Multi-tenant (siguiente paso)

---

## Resumen

**✅ Setup 100% automático**
**✅ Sin pasos manuales**
**✅ Funciona en Windows/Linux/Mac/Docker**
**✅ Configuración en 30-60 segundos**
**✅ Listo para producción**

**Comando único:**
```batch
iniciar_proyecto.bat
```

**Eso es todo.** El sistema hace el resto.

---

**Versión:** 1.0
**Última actualización:** 2026-01-04
**Mantenedor:** Sales Agent FSM Team
