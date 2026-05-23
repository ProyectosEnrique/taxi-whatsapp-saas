# 🤖 GUÍA DE AUTOMATIZACIÓN SEMANAL
## FSM Optimizer - Windows

**Objetivo:** Configurar el FSM Optimizer para que se ejecute automáticamente cada domingo a las 3:00 AM

---

## 🚀 Método 1: Configuración Automática (Más Rápido)

### Paso 1: Ejecutar el configurador

```cmd
cd C:\Users\ASUS\Desktop\PROYECTOS_AGENTE_VENTAS\PROYECTO_B_WHATSAPP_SAAS\backend\sales-agent-base

configurar_automatizacion.bat
```

### Paso 2: Seguir las instrucciones en pantalla

El script hará:
1. ✅ Verificar que Python está instalado
2. ✅ Verificar dependencias
3. ✅ Probar el script de optimización
4. ✅ Ofrecer configurar la tarea programada

### Paso 3: Aceptar cuando pregunte

```
¿Configurar tarea programada AHORA con OPCIÓN A? (S/N): S
```

**IMPORTANTE:** Si dice "Acceso denegado", ejecuta `configurar_automatizacion.bat` como **Administrador**:
- Click derecho → "Ejecutar como administrador"

---

## 🛠️ Método 2: Configuración Manual (Más Control)

### Paso 1: Abrir Programador de Tareas

**Opción A - Atajo de teclado:**
1. Presiona `Win + R`
2. Escribe: `taskschd.msc`
3. Presiona `Enter`

**Opción B - Búsqueda:**
1. Click en botón Inicio
2. Escribe: "Programador de tareas"
3. Click en el resultado

### Paso 2: Crear Tarea Básica

En el Programador de Tareas:

1. **Click derecho** en "Biblioteca del Programador de tareas"
2. **Click** en "Crear tarea básica..."

### Paso 3: Configurar Nombre

- **Nombre:** `FSM Optimizer Semanal`
- **Descripción:** `Optimización automática del agente de ventas mediante análisis de conversaciones`
- Click en **Siguiente**

### Paso 4: Configurar Desencadenador

- Seleccionar: **Semanalmente**
- Click en **Siguiente**

### Paso 5: Configurar Día y Hora

- **Repetir cada:** `1 semanas`
- **Días:** Marcar solo **Domingo** ✅
- **Hora:** `03:00:00` (3:00 AM)
- Click en **Siguiente**

### Paso 6: Configurar Acción

- Seleccionar: **Iniciar un programa**
- Click en **Siguiente**

### Paso 7: Especificar Programa

**Programa o script:**
```
C:\Users\ASUS\Desktop\PROYECTOS_AGENTE_VENTAS\PROYECTO_B_WHATSAPP_SAAS\backend\sales-agent-base\run_fsm_optimization.bat
```

**Agregar argumentos (opcional):**
```
--days 7
```

**Iniciar en (opcional):**
```
C:\Users\ASUS\Desktop\PROYECTOS_AGENTE_VENTAS\PROYECTO_B_WHATSAPP_SAAS\backend\sales-agent-base
```

Click en **Siguiente**

### Paso 8: Finalizar

- Marcar ✅ **Abrir el cuadro de diálogo Propiedades al hacer clic en Finalizar**
- Click en **Finalizar**

### Paso 9: Configuración Avanzada (Opcional pero Recomendado)

En la ventana de Propiedades que se abre:

**Pestaña General:**
- Marcar ✅ **Ejecutar con los privilegios más altos**
- Configurar para: **Windows 10**

**Pestaña Condiciones:**
- Desmarcar ❌ **Iniciar la tarea solo si el equipo está conectado a alimentación CA**
  (Para que se ejecute incluso si está en batería)

**Pestaña Configuración:**
- Marcar ✅ **Permitir que se ejecute la tarea a petición**
- Marcar ✅ **Si la tarea en ejecución no finaliza cuando se solicita, forzar su detención**
- **Si la tarea ya se está ejecutando:** "No iniciar una nueva instancia"

Click en **Aceptar**

---

## ✅ Verificar Configuración

### Ver tarea creada:

1. Abrir Programador de Tareas (`Win + R` → `taskschd.msc`)
2. En el panel izquierdo: "Biblioteca del Programador de tareas"
3. Buscar: **"FSM Optimizer Semanal"**
4. Verificar:
   - ✅ Estado: Listo
   - ✅ Próxima ejecución: Domingo próximo a las 03:00

### Probar ejecución manual:

**Método A - Desde Programador de Tareas:**
1. Click derecho en "FSM Optimizer Semanal"
2. Click en **Ejecutar**
3. Ver estado cambia a "En ejecución"

**Método B - Desde línea de comandos:**
```cmd
schtasks /run /tn "FSM_Optimizer_Semanal"
```

### Ver resultado:

**Logs generados en:**
```
optimization_logs\fsm_optimization_YYYYMMDD_HHMMSS.log
optimization_logs\fsm_optimization_YYYYMMDD_HHMMSS.json
```

**Ver último log:**
```cmd
cd optimization_logs
dir /o-d *.log
type fsm_optimization_<ultimo>.log
```

---

## 📊 Monitorear Ejecuciones

### Ver historial de ejecuciones:

1. Abrir Programador de Tareas
2. Click en "FSM Optimizer Semanal"
3. Pestaña **Historial** (abajo)
4. Ver todas las ejecuciones pasadas

### Ver logs semanales:

```cmd
cd C:\Users\ASUS\Desktop\PROYECTOS_AGENTE_VENTAS\PROYECTO_B_WHATSAPP_SAAS\backend\sales-agent-base\optimization_logs

REM Listar todos los logs (más reciente primero)
dir /o-d *.log

REM Ver último log
for /f "delims=" %i in ('dir /b /o-d *.log') do @type "%i" & goto :break
:break
```

### Ver reportes JSON:

```cmd
REM Ver último reporte
for /f "delims=" %i in ('dir /b /o-d *.json') do @python -m json.tool "%i" & goto :break
:break
```

---

## 🔧 Modificar Configuración

### Cambiar horario:

1. Programador de Tareas
2. Click derecho en "FSM Optimizer Semanal"
3. Click en **Propiedades**
4. Pestaña **Desencadenadores**
5. Doble click en el desencadenador
6. Cambiar hora
7. **Aceptar**

### Cambiar frecuencia:

Mismo proceso, pero en "Configuración semanal" cambiar días

### Agregar parámetros:

1. Pestaña **Acciones**
2. Doble click en la acción
3. **Agregar argumentos:**
   - `--dry-run` (solo preview, no aplicar)
   - `--days 14` (analizar últimos 14 días)
   - `--min-quality 0.6` (umbral de calidad)

---

## 🗑️ Desactivar/Eliminar Automatización

### Desactivar temporalmente:

1. Programador de Tareas
2. Click derecho en "FSM Optimizer Semanal"
3. Click en **Deshabilitar**

### Eliminar tarea:

**Método A - Interfaz gráfica:**
1. Programador de Tareas
2. Click derecho en "FSM Optimizer Semanal"
3. Click en **Eliminar**
4. Confirmar

**Método B - Línea de comandos:**
```cmd
schtasks /delete /tn "FSM_Optimizer_Semanal" /f
```

---

## 📧 Notificaciones (Opcional)

### Configurar email cuando falla:

1. Propiedades de la tarea
2. Pestaña **Acciones**
3. Click en **Nueva...**
4. Acción: **Enviar un correo electrónico**
5. Configurar:
   - De: tu_email@gmail.com
   - Para: tu_email@gmail.com
   - Asunto: "FSM Optimizer - Error"
   - Servidor SMTP: smtp.gmail.com

**Nota:** Gmail requiere "Contraseña de aplicación"

---

## 🐛 Solución de Problemas

### Problema: "La tarea no se ejecuta"

**Soluciones:**
1. Verificar que el equipo esté encendido el domingo a las 3 AM
2. En Propiedades → Condiciones:
   - Desmarcar "Iniciar solo si está conectado a AC"
   - Desmarcar "Detener si cambia a batería"

### Problema: "Acceso denegado al crear tarea"

**Solución:**
- Ejecutar `configurar_automatizacion.bat` como Administrador
- O crear la tarea manualmente (no requiere permisos)

### Problema: "No se generan logs"

**Verificar:**
```cmd
cd C:\Users\ASUS\Desktop\PROYECTOS_AGENTE_VENTAS\PROYECTO_B_WHATSAPP_SAAS\backend\sales-agent-base

REM Verificar que existe directorio
dir optimization_logs

REM Si no existe, crearlo
mkdir optimization_logs

REM Probar ejecución manual
run_fsm_optimization.bat --dry-run
```

### Problema: "Error de Python"

**Verificar:**
```cmd
REM Python está en PATH
python --version

REM Dependencias instaladas
cd C:\Users\ASUS\Desktop\PROYECTOS_AGENTE_VENTAS\PROYECTO_B_WHATSAPP_SAAS\backend\sales-agent-base
pip install -r requirements.txt
```

---

## 📈 Métricas de Éxito

Después de configurar, esperar 4 semanas y verificar mejoras:

### Semana 1 (primera ejecución):
```
📊 Mejoras detectadas: ~10-15
  • Nuevos patrones: 5-10
  • Nuevos aliases: 3-5
  • Typos: 0-2
```

### Semana 4 (acumulado):
```
📊 Mejoras acumuladas: ~40-60
FSM Coverage: 90% → 94% (+4%)
Latencia promedio: 180ms → 140ms (-22%)
```

### Semana 12 (madurez):
```
📊 Mejoras acumuladas: 150+
FSM Coverage: 90% → 97% (+7%)
Latencia promedio: 180ms → 120ms (-33%)
```

---

## ✅ Checklist de Configuración

- [ ] Script `configurar_automatizacion.bat` ejecutado
- [ ] Python y dependencias verificadas
- [ ] Test con `--dry-run` exitoso
- [ ] Tarea programada creada
- [ ] Tarea probada manualmente
- [ ] Logs generados correctamente
- [ ] Próxima ejecución programada visible
- [ ] Directorio `optimization_logs` existe

---

## 📞 Soporte

### Ver documentación:
- `WEEKLY_IMPROVEMENTS.md` - Documentación completa
- `FSM_OPTIMIZER_QUICKSTART.md` - Guía rápida
- `RESULTADO_TESTS.md` - Resultados de tests

### Ejecutar manualmente:
```cmd
cd C:\Users\ASUS\Desktop\PROYECTOS_AGENTE_VENTAS\PROYECTO_B_WHATSAPP_SAAS\backend\sales-agent-base

REM Análisis completo
run_fsm_optimization.bat

REM Solo preview
run_fsm_optimization.bat --dry-run

REM Últimos 14 días
run_fsm_optimization.bat --days 14
```

---

**Última actualización:** 2026-01-04
**Estado:** ✅ Listo para configurar
**Próximo paso:** Ejecutar `configurar_automatizacion.bat`
