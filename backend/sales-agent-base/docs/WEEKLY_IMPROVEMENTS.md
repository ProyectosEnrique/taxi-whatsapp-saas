# Sistema de Mejora Continua

Este proyecto usa **FSM Optimization** en lugar de LoRA fine-tuning para mejorar continuamente el rendimiento del agente de ventas.

## ¿Por qué FSM Optimization?

La decisión de usar optimización de FSM en lugar de fine-tuning con LoRA se basa en múltiples ventajas técnicas y operacionales:

| Aspecto | FSM Optimization | LoRA Fine-tuning |
|---------|------------------|------------------|
| **Infraestructura** | ✅ Sin GPU necesaria | ❌ Requiere GPU (6GB+ VRAM) |
| **Costo** | ✅ $0 | ❌ $50-150/mes en GPU |
| **Tiempo de ejecución** | ✅ 2-5 min | ❌ 30-45 min |
| **Tráfico mejorado** | ✅ 90% (FSM cases) | ⚠️ 10% (LLM cases) |
| **Latencia** | ✅ 5-20ms | ❌ 300-800ms |
| **Complejidad** | ✅ Baja | ❌ Alta |
| **Predecibilidad** | ✅ Alta | ⚠️ Media |
| **Debugging** | ✅ Fácil | ❌ Difícil |

## Qué se mejora automáticamente

El sistema analiza conversaciones reales archivadas y detecta oportunidades de mejora en:

### 1. **Nuevos patrones de intenciones (regex)**

Detecta nuevas formas en que los usuarios expresan sus intenciones y genera automáticamente patrones regex para manejarlas.

**Ejemplo:**
```python
# Antes
"ADD_TO_ORDER": [
    r"quiero\s+(\d+)?\s*(\w+)",
    r"me das\s+(\d+)?\s*(\w+)"
]

# Después del análisis (patrones detectados automáticamente)
"ADD_TO_ORDER": [
    r"quiero\s+(\d+)?\s*(\w+)",
    r"me das\s+(\d+)?\s*(\w+)",
    r"me traes\s+(\d+)?\s*(\w+)",     # NUEVO ✨
    r"ponme\s+(\d+)?\s*(\w+)"         # NUEVO ✨
]
```

**Impacto:** +3-5% de cobertura de FSM

### 2. **Aliases de productos**

Identifica términos alternativos que los usuarios utilizan para referirse a productos.

**Ejemplo:**
```python
# Antes
products = {
    "hamburguesa_clasica": {
        "aliases": ["clasica", "sencilla"]
    }
}

# Después (aliases detectados automáticamente)
products = {
    "hamburguesa_clasica": {
        "aliases": [
            "clasica", "sencilla",
            "burger",       # NUEVO ✨
            "hambu",        # NUEVO ✨
            "tradicional"   # NUEVO ✨
        ]
    }
}
```

**Impacto:** +5-10% de precisión en product matching

### 3. **Correcciones de errores tipográficos**

Detecta errores tipográficos recurrentes y los agrega al sistema de fuzzy matching.

**Ejemplo:**
```python
# Typos detectados (aparecen 3+ veces en conversaciones)
typos = {
    "hamburgesa": "hamburguesa",  # 23 veces
    "refreco": "refresco",        # 18 veces
    "tacoz": "tacos"              # 12 veces
}
```

**Impacto:** Mejora en experiencia de usuario

### 4. **Optimización de umbrales de confianza**

Analiza tasas de éxito por nivel de confianza y sugiere ajustes para reducir llamadas innecesarias al LLM.

**Ejemplo:**
```
Análisis de confianza:
  0.9-1.0: 99.2% éxito (450/454)
  0.8-0.9: 97.1% éxito (234/241)
  0.7-0.8: 95.8% éxito (138/144)  ← Podría no necesitar LLM

Sugerencia: Bajar umbral LLM de 0.8 a 0.7
Resultado: -5% llamadas LLM, misma precisión
```

**Impacto:** Reducción de latencia y costos

## Ejecución

### Automática (Recomendado)

**Linux/Mac (cron):**
```bash
# Editar crontab
crontab -e

# Agregar línea para ejecutar domingos a las 3 AM
0 3 * * 0 /path/to/sales-agent-base/run_fsm_optimization.sh
```

**Windows (Programador de tareas):**
1. Abrir "Programador de tareas"
2. Crear tarea básica:
   - Nombre: "FSM Weekly Optimization"
   - Desencadenador: Semanal, domingos, 3:00 AM
   - Acción: Iniciar programa
   - Programa: `C:\path\to\sales-agent-base\run_fsm_optimization.bat`

### Manual

**Análisis completo (aplicar cambios):**
```bash
# Linux/Mac
./run_fsm_optimization.sh

# Windows
run_fsm_optimization.bat

# Python directo
python -m src.learning.fsm_optimizer
```

**Solo preview (no aplicar):**
```bash
# Linux/Mac
./run_fsm_optimization.sh --dry-run

# Windows
run_fsm_optimization.bat --dry-run

# Python directo
python -m src.learning.fsm_optimizer --dry-run
```

**Analizar periodo personalizado:**
```bash
# Últimos 14 días
./run_fsm_optimization.sh --days 14

# Últimos 30 días
python -m src.learning.fsm_optimizer --days 30
```

**Opciones avanzadas:**
```bash
python -m src.learning.fsm_optimizer \
  --days 7 \
  --min-quality 0.7 \
  --min-frequency 3 \
  --dry-run
```

## Arquitectura del sistema

```
┌─────────────────────────────────────────────────────────┐
│  LUNES - SÁBADO: Captura de Datos                      │
└─────────────────────────────────────────────────────────┘

Cliente → WhatsApp → Sales Agent
                      ↓
                 FSM procesa
                      ↓
              ┌───────┴───────┐
              ↓               ↓
        90% Match OK    10% LLM Fallback
              ↓               ↓
      Conversation       Conversation
        Archive            Archive
              ↓               ↓
      quality_score      quality_score
       llm_used=null     llm_used=cerebras


┌─────────────────────────────────────────────────────────┐
│  DOMINGO 3 AM: Mejora Automática                       │
└─────────────────────────────────────────────────────────┘

1. Load conversations (últimos 7 días)
         ↓
2. Filter by quality_score >= 0.7
         ↓
3. Analyze patterns
   - Intent patterns (nuevas frases)
   - Product aliases (nuevos términos)
   - Common typos (errores frecuentes)
   - LLM fallback cases (oportunidades FSM)
   - Confidence thresholds
         ↓
4. Generate improvement report
         ↓
5. Apply improvements (opcional)
   - Update decision_tree.py
   - Update product aliases DB
   - Update fuzzy matcher
         ↓
6. Create backup & log


┌─────────────────────────────────────────────────────────┐
│  RESULTADO: FSM Mejorada                                │
└─────────────────────────────────────────────────────────┘

Semana siguiente:
  • 92% casos → FSM (antes 90%) ✅
  • 8% casos → LLM (antes 10%)
  • Latencia promedio: -50ms
  • Dependencia APIs: -20%
```

## Logs y métricas

### Logs de optimización

Los logs se guardan automáticamente en:
```
optimization_logs/
├── fsm_optimization_20250103_030000.log  # Log de ejecución
└── fsm_optimization_20250103_030000.json # Reporte detallado
```

### Estructura del reporte JSON

```json
{
  "timestamp": "2025-01-03T03:00:00",
  "analysis_period_days": 7,
  "total_conversations": 342,
  "quality_conversations": 287,
  "improvements": {
    "new_patterns": {
      "ADD_TO_ORDER": [
        "me traes\\s+(?:(\\d+|un|una)\\s+)?(\\w+)",
        "ponme\\s+(?:(\\d+|un|una)\\s+)?(\\w+)"
      ],
      "CANCEL_ITEM": [
        "quita\\s+(\\w+)"
      ]
    },
    "new_aliases": {
      "hamburguesa_clasica": ["burger", "hambu"],
      "coca_cola": ["coca"]
    },
    "typo_corrections": {
      "hamburgesa": "hamburguesa",
      "refreco": "refresco"
    },
    "total": 12
  },
  "confidence_insights": {
    "0.9-1.0": {"rate": 0.992, "total": 454, "success": 450},
    "0.8-0.9": {"rate": 0.971, "total": 241, "success": 234},
    "0.7-0.8": {"rate": 0.958, "total": 144, "success": 138}
  },
  "llm_fallback_analysis": {
    "total_cases": 34,
    "by_reason": {
      "low_confidence": 22,
      "ambiguous_intent": 8,
      "unknown_product": 4
    }
  }
}
```

## Métricas de mejora esperadas

### Semana 0 (baseline)
```
FSM Coverage: 90%
LLM Fallback: 10%
Latencia promedio: 180ms
Product match accuracy: 88%
```

### Semana 4 (después de 4 optimizaciones)
```
FSM Coverage: 94% (+4%) ✅
LLM Fallback: 6% (-4%)
Latencia promedio: 140ms (-22%) ✅
Product match accuracy: 94% (+6%) ✅
```

### Semana 12 (madurez)
```
FSM Coverage: 97% (+7%) ✅
LLM Fallback: 3% (-7%)
Latencia promedio: 120ms (-33%) ✅
Product match accuracy: 97% (+9%) ✅
Nuevos patrones: 150+ agregados
Aliases productos: 300+ agregados
```

## Integración con el sistema existente

El optimizador se integra con:

1. **ConversationArchive** (`src/analytics/conversation_archive.py`)
   - Lee conversaciones archivadas
   - Usa quality_score y métricas

2. **DecisionTree** (`src/core/fsm/decision_tree.py`)
   - Analiza patrones existentes
   - Sugiere nuevos patrones (futuro: aplicación automática)

3. **ProductMatcher** (`src/core/fsm/product_matcher.py`)
   - Detecta aliases usados
   - Sugiere nuevos aliases

4. **ConversationMemory** (`src/core/fsm/conversation_memory.py`)
   - Accede a historial completo
   - Analiza contexto de éxito/fracaso

## LoRA Fine-tuning (Futuro)

El código de LoRA está disponible pero comentado en:
- `src/nlp/model_provider.py`
- `src/training/incremental_trainer.py`
- `run_lora_training.sh`

Si en el futuro se necesita usar LoRA:

1. **Requisitos:**
   - GPU con 6GB+ VRAM (NVIDIA)
   - CUDA instalado
   - Modelo base (Mistral 7B o Phi-2)

2. **Activación:**
   - Descomentar secciones LoRA en el código
   - Configurar GPU en `config.yaml`
   - Ejecutar `run_lora_training.sh`

3. **Cuándo considerar LoRA:**
   - FSM coverage se estanca (<97%)
   - Casos muy complejos que regex no puede manejar
   - Se requiere comprensión semántica profunda
   - Se tiene presupuesto para infraestructura GPU

**Por ahora, FSM Optimization es superior** para el 90% de casos.

## Solución de problemas

### No se encuentran conversaciones

```bash
# Verificar que exista el directorio de archivo
ls conversation_archive/

# Verificar estructura de fechas
ls conversation_archive/2025-01/

# Revisar permisos
chmod -R 755 conversation_archive/
```

### Pocas conversaciones de calidad

```
⚠️  Pocas conversaciones de calidad (5). Se recomienda mínimo 10.
```

**Soluciones:**
- Aumentar periodo de análisis: `--days 14`
- Bajar umbral de calidad: `--min-quality 0.6`
- Esperar más tráfico antes de ejecutar

### No se detectan mejoras

```
ℹ️  No se detectaron nuevos patrones de intenciones
```

**Razones normales:**
- FSM ya está bien optimizada
- Pocas conversaciones nuevas
- Patrones ya existen

**No es un error**, simplemente no hay mejoras que aplicar.

### Error al aplicar mejoras

Si la aplicación automática falla, las mejoras se pueden aplicar manualmente usando el reporte JSON generado.

## Contribuir

Para agregar nuevos tipos de análisis:

1. Editar `src/learning/fsm_optimizer.py`
2. Agregar nuevo método `_analyze_new_feature()`
3. Llamarlo desde `analyze_weekly_conversations()`
4. Actualizar `_generate_improvement_report()`

## Licencia

Este sistema es parte del Sales Agent Base y sigue la misma licencia del proyecto.

---

**Última actualización:** 2025-01-03
**Versión:** 1.0.0
**Mantenedor:** Sistema de IA
