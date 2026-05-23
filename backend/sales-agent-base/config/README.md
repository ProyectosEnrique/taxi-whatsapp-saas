# Configuración del Asistente de Voz con LLM

## Descripción General

Este directorio contiene todos los archivos de configuración necesarios para el funcionamiento del asistente de voz inteligente con LLM del sistema RESTAURANT_VOICE_SYSTEM_2.0.

## Estructura de Archivos

```
config/
├── README.md                    # Este archivo
├── menu_knowledge.json          # Base de conocimiento del menú
├── sales_rules.yaml             # Reglas de venta y comportamiento
├── assistant_prompts.yaml       # Prompts maestros del LLM
└── environment.example.env      # Variables de entorno de ejemplo
```

## Archivos de Configuración

### 1. `menu_knowledge.json`

**Propósito:** Contiene toda la información del menú del restaurante en formato estructurado.

**Estructura:**
- `menu.categories[]`: Categorías de productos (tacos, hamburguesas, bebidas, complementos)
- `menu.combos[]`: Definición de combos y paquetes especiales
- `menu.promotions[]`: Promociones activas o programables
- `metadata`: Información del restaurante (horarios, contacto, impuestos)

**Cómo actualizar:**
```json
{
  "menu": {
    "categories": [
      {
        "id": "categoria_id",
        "name": "Nombre Categoría",
        "products": [
          {
            "id": "producto_id",
            "name": "Nombre Producto",
            "price": 100.00,
            "available": true,
            "popular": true
          }
        ]
      }
    ]
  }
}
```

**Frecuencia de actualización:**
- Precios: Según cambios del restaurante
- Disponibilidad: Diariamente o en tiempo real
- Productos nuevos: Según sea necesario
- Promociones: Semanal o según calendario promocional

---

### 2. `sales_rules.yaml`

**Propósito:** Define las reglas de venta, estrategias de upselling y comportamiento del asistente.

**Secciones principales:**
- `general_interaction_rules`: Reglas generales de interacción
- `sales_rules_by_category`: Reglas específicas por categoría de producto
- `promotion_rules`: Configuración de cómo manejar promociones
- `closing_rules`: Reglas para cierre de ventas
- `time_based_rules`: Estrategias según momento del día
- `personalization_rules`: Reglas de personalización

**Cómo personalizar:**
```yaml
sales_rules_by_category:
  tacos:
    upselling_strategy:
      primary: "Tu estrategia principal"
      secondary: "Estrategia secundaria"
    response_templates:
      recommend: "Template de recomendación"
```

**Frecuencia de actualización:**
- Estrategias de venta: Mensual o según resultados
- Reglas de promoción: Semanal
- Templates de respuesta: Según feedback de clientes

---

### 3. `assistant_prompts.yaml`

**Propósito:** Contiene los prompts maestros que guían el comportamiento del LLM.

**Prompts principales:**
- `master_prompt`: Prompt maestro que define rol y comportamiento general
- `greeting_prompt`: Cómo saludar a los clientes
- `recommendation_prompt`: Cómo hacer recomendaciones
- `order_confirmation_prompt`: Cómo confirmar pedidos
- `upselling_prompt`: Estrategias de venta adicional
- `closing_prompt`: Cómo cerrar la venta

**Cómo ajustar:**
```yaml
system_prompts:
  master_prompt: |
    # TU ROL
    Descripción del rol del asistente...

    # REGLAS FUNDAMENTALES
    1. Regla 1
    2. Regla 2
```

**Frecuencia de actualización:**
- Prompts maestros: Trimestral o según análisis de conversaciones
- Templates: Según feedback continuo
- Configuración de voz: Según preferencias de clientes

---

## Guía de Implementación

### Paso 1: Configuración Inicial del Menú

1. Edita `menu_knowledge.json`
2. Agrega todas las categorías de productos
3. Define productos con todos sus atributos
4. Configura combos y promociones
5. Actualiza metadata del restaurante

### Paso 2: Configuración de Reglas de Venta

1. Abre `sales_rules.yaml`
2. Revisa y ajusta las reglas generales de interacción
3. Personaliza estrategias de upselling por categoría
4. Define reglas contextuales (horario, clima, etc.)
5. Configura límites y restricciones

### Paso 3: Configuración de Prompts

1. Edita `assistant_prompts.yaml`
2. Personaliza el prompt maestro con la identidad de tu restaurante
3. Ajusta los templates de respuesta según tu tono deseado
4. Configura manejo de errores y casos especiales
5. Define configuración de voz (velocidad, tono, etc.)

### Paso 4: Testing

1. Carga las configuraciones en el sistema
2. Realiza pruebas de conversación
3. Verifica que las recomendaciones sean apropiadas
4. Ajusta según sea necesario
5. Documenta cambios

---

## Integración con el Sistema

### Carga de Configuraciones

```python
# Ejemplo de carga en Python
import json
import yaml

# Cargar menú
with open('config/menu_knowledge.json', 'r', encoding='utf-8') as f:
    menu_data = json.load(f)

# Cargar reglas de venta
with open('config/sales_rules.yaml', 'r', encoding='utf-8') as f:
    sales_rules = yaml.safe_load(f)

# Cargar prompts
with open('config/assistant_prompts.yaml', 'r', encoding='utf-8') as f:
    prompts = yaml.safe_load(f)
```

### Uso en el Asistente LLM

```python
# Construir el prompt maestro
master_prompt = prompts['system_prompts']['master_prompt'].format(
    restaurant_name=menu_data['menu']['restaurant_name'],
    menu_knowledge=json.dumps(menu_data['menu'], indent=2),
    sales_rules=yaml.dump(sales_rules['sales_rules_by_category']),
    active_promotions=get_active_promotions(menu_data['menu']['promotions'])
)

# Enviar al LLM
response = llm.generate(
    system_prompt=master_prompt,
    user_input=customer_message,
    context=conversation_history
)
```

---

## Mejores Prácticas

### 1. Mantenimiento del Menú
- ✅ Actualiza `available: false` para productos temporalmente agotados
- ✅ Marca `popular: true` en los productos más vendidos
- ✅ Mantén precios actualizados en tiempo real
- ✅ Revisa y actualiza promociones semanalmente

### 2. Optimización de Reglas
- ✅ Analiza métricas de conversión de sugerencias
- ✅ Ajusta estrategias según productos con mejor margen
- ✅ Prueba diferentes templates de respuesta (A/B testing)
- ✅ Documenta cambios y sus resultados

### 3. Refinamiento de Prompts
- ✅ Lee conversaciones reales para identificar problemas
- ✅ Ajusta el tono según feedback de clientes
- ✅ Mantén prompts concisos pero completos
- ✅ Usa ejemplos específicos de tu restaurante

### 4. Monitoreo Continuo
- ✅ Revisa logs de conversaciones diariamente
- ✅ Identifica respuestas inapropiadas o incorrectas
- ✅ Mide ticket promedio y tasa de upselling
- ✅ Actualiza configuraciones basándote en datos reales

---

## Versionado

Mantén un historial de cambios en las configuraciones:

```
Versión 1.0.0 (2025-11-23)
- Configuración inicial del sistema
- Menú base con tacos y hamburguesas
- Reglas de venta estándar
- Prompts maestros v1

Versión 1.1.0 (fecha)
- [Descripción de cambios]
```

---

## Troubleshooting

### Problema: El asistente recomienda productos que no existen

**Solución:** Verifica que `menu_knowledge.json` esté actualizado y que el prompt maestro esté cargando correctamente la base de conocimiento.

### Problema: Respuestas muy largas

**Solución:** Ajusta `response_length` en `sales_rules.yaml` y enfatiza brevedad en `assistant_prompts.yaml`.

### Problema: No ofrece upselling

**Solución:** Revisa que `sales_rules_by_category` tenga configuradas las estrategias de upselling y que el `recommendation_prompt` sea lo suficientemente específico.

### Problema: Ignora promociones activas

**Solución:** Verifica que las promociones tengan `active: true` en `menu_knowledge.json` y que `promotion_rules.auto_mention.enabled` sea `true` en `sales_rules.yaml`.

---

## Soporte y Recursos

- **Documentación completa:** Ver `docs/GUIA_MAESTRA_ASISTENTE_VOZ_LLM.md`
- **Ejemplos de conversación:** Ver `tests/conversation_examples/`
- **Logs del sistema:** Ver `logs/voice-assistant/`

---

## Contribuciones

Al modificar estas configuraciones:

1. Prueba los cambios en ambiente de desarrollo primero
2. Documenta el propósito de los cambios
3. Actualiza este README si es necesario
4. Incrementa el número de versión
5. Comunica cambios al equipo

---

**Última actualización:** 2025-11-23
**Versión de configuración:** 1.0.0
**Mantenedor:** Equipo de Desarrollo RESTAURANT_VOICE_SYSTEM_2.0
