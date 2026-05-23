# 🚀 Demo Interactiva - Inicio Rápido

## ✅ Todo ya está configurado

Ya tienes Twilio configurado con el número sandbox:
- **Número**: +1 415 523 8886
- **Proveedor**: Twilio Sandbox
- **Estado**: ✅ Listo para usar

---

## 📱 Paso 1: Unirse al Sandbox (si aún no lo has hecho)

1. **Abre WhatsApp**
2. **Envía mensaje** a: `+1 415 523 8886`
3. **Escribe**: `join <palabra-que-te-den>`
   - Ejemplo: `join example-word`
4. **Recibirás confirmación** de Twilio

> ⚠️ Solo necesitas hacer esto UNA VEZ. Si ya lo hiciste antes, salta al Paso 2.

---

## 🚀 Paso 2: Iniciar el Sistema

```bash
# Opción 1: Inicio Simple (Recomendado - Sin Docker)
iniciar_demo_simple.bat

# Opción 2: Con Docker (usa más memoria)
iniciar_demo.bat
```

Verás:
```
================================================================================
  GATEWAY INICIADO
================================================================================
Servicios disponibles:
  - WhatsApp Gateway:  http://localhost:8080/health
```

---

## 🎮 Paso 3: Probar la Demo

### A. Desde WhatsApp

1. **Envía cualquier mensaje** al número: `+1 415 523 8886`

2. **Recibirás el menú de bienvenida:**
```
👋 ¡Bienvenido a la DEMO INTERACTIVA!

🎮 ¿Qué tipo de negocio quieres explorar?

1️⃣ 🍔 RESTAURANTE / TAQUERÍA
2️⃣ 🛍️ TIENDA / BOUTIQUE
3️⃣ 💊 FARMACIA / SALUD
4️⃣ 🛒 ABARROTES / SUPERMERCADO
5️⃣ 💇 SERVICIOS / SALÓN
6️⃣ 🐶 TIENDA DE MASCOTAS

Escribe el número de tu elección (ej: 1)
```

3. **Responde con un número** (ej: `1`)

4. **Recibirás el contexto de la industria:**
```
🎉 ¡Perfecto! Ahora eres cliente de:

🌮 TAQUERÍA EL BUEN SABOR
...
✅ 500 puntos de fidelidad (para probar el canje)
...

¿Qué te gustaría hacer?
1️⃣ Ver menú completo en web
2️⃣ Hacer un pedido
3️⃣ Ver mis puntos de fidelidad
```

5. **Responde `1`** para ver el menú web

6. **Recibirás un link:**
```
📱 ¡Aquí está nuestro menú digital completo!

🌐 http://localhost:8080/demo_restaurant/abc123

🎁 TIENES: 500 puntos = $250 de descuento disponible
```

7. **HAZ CLIC EN EL LINK** (se abrirá en tu navegador)

### B. En la Página Web

1. **Verás el catálogo** con fotos de productos
2. **Agrega productos al carrito**
3. **Ve al checkout**
4. **Usa tus 500 puntos** para obtener descuento
5. **Selecciona método de pago**: Efectivo (única opción en demo)
6. **Confirma el pedido**

### C. Confirmación Automática

Recibirás en WhatsApp:
```
🎉 ¡Pedido Confirmado!

📋 Orden: #DEMO-12345
⏳ Pago: CASH - Pendiente

*Tu pedido:*
• 3x Tacos al Pastor - $90.00
...

💰 *Total: $90.00*

⭐ *Programa de Fidelidad*
Ganaste: +9 puntos
Total acumulado: 509 puntos
Nivel: BRONCE

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 MODO DEMO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Este fue un pedido de demostración.
NO procesamos pagos reales.

¿Quieres ver cómo funciona para otro negocio?
Escribe cambiar para explorar otras industrias.

¿Listo para implementarlo en TU negocio?
Escribe info para planes y precios.
```

---

## 🎯 Comandos Especiales en WhatsApp

Puedes escribir en cualquier momento:

| Comando | Descripción |
|---------|-------------|
| `cambiar` | Explorar otra industria |
| `info` | Ver planes y precios |
| `ayuda` | Menú de ayuda |

---

## 🔍 Verificar que Todo Funciona

### 1. Gateway Activo
```bash
curl http://localhost:8080/health
```

Respuesta esperada:
```json
{
  "status": "healthy",
  "service": "whatsapp-gateway",
  "provider": "twilio"
}
```

### 2. Endpoint de Catálogo Demo
```bash
curl http://localhost:8080/api/v1/restaurants/demo_restaurant/menu
```

Deberías ver JSON con productos del restaurante.

### 3. Sistema de Puntos
```bash
curl "http://localhost:8080/api/v1/loyalty/config/demo_restaurant"
```

Deberías ver la configuración de loyalty.

---

## 📊 Ver Analytics de la Demo

Los datos de prospectos se guardan en:
```
backend/whatsapp-gateway/data/demo/prospects.json
```

Ejemplo:
```json
{
  "5215512345678": {
    "phone": "5215512345678",
    "industries_explored": ["demo_restaurant"],
    "completed_checkout": true,
    "requested_info": false,
    "created_at": "2025-01-07T22:30:00"
  }
}
```

---

## ⚠️ Limitaciones del Sandbox

| Limitación | Detalles |
|------------|----------|
| Solo tú puedes probar | Otros necesitan hacer "join" primero |
| Mensajes limitados | ~50-100 por día |
| Prefijo "join" | Todos deben hacer join antes |

**Para producción**, necesitarías:
- Comprar número de Twilio (~$2 USD/mes)
- Aprobar plantillas de mensajes con Meta
- Configurar Cloudflare Tunnel

---

## 🐛 Troubleshooting

### "No recibo mensajes"

1. Verifica que hiciste el "join" al sandbox
2. Verifica que el gateway esté corriendo:
   ```bash
   curl http://localhost:8080/health
   ```

### "El link no abre la web"

- En modo local, el link será `http://localhost:8080/...`
- Solo funcionará en tu misma PC
- Para que funcione en tu móvil, necesitas Cloudflare Tunnel

### "Error al importar demo_config"

```bash
cd backend/whatsapp-gateway
pip install -r requirements.txt
```

---

## ✅ Checklist de Funcionamiento

- [ ] Gateway corriendo en puerto 8080
- [ ] Hice "join" al sandbox de Twilio
- [ ] Envié mensaje al +1 415 523 8886
- [ ] Recibí menú de industrias
- [ ] Seleccioné una industria (1-6)
- [ ] Recibí link al catálogo
- [ ] Abrí link en navegador
- [ ] Agregué productos al carrito
- [ ] Completé checkout
- [ ] Recibí confirmación por WhatsApp con puntos

---

## 🚀 Próximo Nivel

Una vez que funcione en local, puedes:

1. **Configurar Cloudflare Tunnel** (ver `SETUP_DEMO_TWILIO_CLOUDFLARE.md`)
   - Link funcionará en cualquier dispositivo
   - URL permanente
   - Gratis

2. **Comprar número de Twilio**
   - Cualquier persona puede probar
   - Sin límite de mensajes
   - ~$2-5 USD/mes

3. **Promocionar la demo**
   - Generar QR code
   - Publicar en redes sociales
   - Captar clientes reales

---

**¡Todo está listo!** 🎉

Solo ejecuta `iniciar_demo_simple.bat` y envía un mensaje al sandbox de Twilio.
