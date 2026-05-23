# ⚡ INSTRUCCIONES RÁPIDAS - Automatización Semanal

## 🎯 Objetivo
Configurar el FSM Optimizer para que se ejecute automáticamente **cada domingo a las 3:00 AM**

---

## 🚀 OPCIÓN 1: Configuración Automática (5 minutos)

### Paso 1: Abrir CMD como Administrador

1. Presiona `Win + X`
2. Click en **"Windows PowerShell (Administrador)"** o **"Símbolo del sistema (Administrador)"**
3. Si aparece ventana de permisos, click en **Sí**

### Paso 2: Navegar al directorio

```cmd
cd C:\Users\ASUS\Desktop\PROYECTOS_AGENTE_VENTAS\PROYECTO_B_WHATSAPP_SAAS\backend\sales-agent-base
```

### Paso 3: Ejecutar el configurador

```cmd
configurar_automatizacion.bat
```

### Paso 4: Seguir las instrucciones en pantalla

El script hará:
- ✅ Verificar Python
- ✅ Verificar dependencias
- ✅ Probar el sistema
- ✅ Preguntarte si quieres configurar ahora

Cuando pregunte:
```
¿Configurar tarea programada AHORA con OPCIÓN A? (S/N):
```

Escribe: **S** y presiona Enter

**¡Listo!** La tarea programada está configurada ✅

---

## 🛠️ OPCIÓN 2: Configuración Manual (10 minutos)

Si prefieres configurar manualmente o si la OPCIÓN 1 falla:

### Paso 1: Abrir Programador de Tareas

- Presiona `Win + R`
- Escribe: `taskschd.msc`
- Presiona `Enter`

### Paso 2: Crear Tarea

1. Click derecho en "Biblioteca del Programador de tareas"
2. Click en **"Crear tarea básica..."**

### Paso 3: Configurar

**Nombre:**
```
FSM Optimizer Semanal
```

**Desencadenador:**
- Semanalmente
- Domingo
- 03:00 AM

**Acción:**
- Iniciar un programa

**Programa:**
```
C:\Users\ASUS\Desktop\PROYECTOS_AGENTE_VENTAS\PROYECTO_B_WHATSAPP_SAAS\backend\sales-agent-base\run_fsm_optimization.bat
```

**Finalizar**

---

## ✅ Verificar que Funciona

### Probar ejecución manual:

**Opción A - Desde Programador de Tareas:**
1. Abrir `taskschd.msc`
2. Buscar "FSM Optimizer Semanal"
3. Click derecho → **Ejecutar**

**Opción B - Desde CMD:**
```cmd
cd C:\Users\ASUS\Desktop\PROYECTOS_AGENTE_VENTAS\PROYECTO_B_WHATSAPP_SAAS\backend\sales-agent-base

run_fsm_optimization.bat --dry-run
```

### Ver resultados:

**Logs en:**
```
optimization_logs\fsm_optimization_*.log
optimization_logs\fsm_optimization_*.json
```

**Ver último log:**
```cmd
cd optimization_logs
dir /o-d *.log
```

---

## 📊 ¿Qué pasará cada domingo?

A las 3:00 AM, el sistema:

1. **Carga conversaciones** de la semana pasada
2. **Analiza patrones** de lenguaje
3. **Detecta mejoras:**
   - Nuevos patrones de intenciones
   - Nuevos aliases de productos
   - Typos comunes
4. **Genera reporte** en `optimization_logs/`

**Resultado esperado por semana:**
```
Semana 1: ~10-15 mejoras detectadas
Semana 4: FSM Coverage 90% → 94% (+4%)
Semana 12: FSM Coverage 90% → 97% (+7%)
```

---

## 🔧 Cambiar Configuración

### Cambiar horario:

1. `taskschd.msc`
2. Click derecho en "FSM Optimizer Semanal"
3. Propiedades → Desencadenadores
4. Cambiar hora

### Cambiar frecuencia:

Mismos pasos, cambiar de "Domingo" a otro día

### Ejecutar más seguido:

Duplicar la tarea con diferentes nombres:
- "FSM Optimizer - Miércoles"
- "FSM Optimizer - Domingo"

---

## 🐛 Solución de Problemas

### "No puedo ejecutar como Administrador"

**Solución:** Usa OPCIÓN 2 (configuración manual) - No requiere permisos admin

### "El script no hace nada"

**Verificar:**
```cmd
cd C:\Users\ASUS\Desktop\PROYECTOS_AGENTE_VENTAS\PROYECTO_B_WHATSAPP_SAAS\backend\sales-agent-base

REM Probar Python
python --version

REM Probar script directamente
python -m src.learning.fsm_optimizer --dry-run
```

### "No se generan logs"

**Crear directorio:**
```cmd
cd C:\Users\ASUS\Desktop\PROYECTOS_AGENTE_VENTAS\PROYECTO_B_WHATSAPP_SAAS\backend\sales-agent-base
mkdir optimization_logs
```

---

## 📚 Documentación Completa

Para más detalles:
- **`GUIA_AUTOMATIZACION.md`** ← Guía completa paso a paso
- **`WEEKLY_IMPROVEMENTS.md`** ← Documentación técnica
- **`FSM_OPTIMIZER_QUICKSTART.md`** ← Guía rápida

---

## 🎉 ¿Todo Listo?

**Checklist:**
- [ ] Ejecuté `configurar_automatizacion.bat`
- [ ] La tarea programada se creó
- [ ] Probé ejecución manual
- [ ] Se generaron logs
- [ ] Veo "Próxima ejecución: Domingo 03:00"

**Si todo está ✅, ¡Listo! El sistema mejorará automáticamente cada semana** 🚀

---

**Próximo paso:** Esperar al domingo a las 3 AM, o ejecutar manualmente para probar
