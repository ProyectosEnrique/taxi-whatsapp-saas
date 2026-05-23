# 🛒 Checkout Completo en Web - Documentación

## 📋 Índice

1. [Visión General](#visión-general)
2. [Flujo Completo](#flujo-completo)
3. [Configuración Backend](#configuración-backend)
4. [Configuración Frontend](#configuración-frontend)
5. [Integración de Pagos](#integración-de-pagos)
6. [Testing](#testing)
7. [Costos](#costos)

---

## 🎯 Visión General

El sistema permite que los clientes:
1. **Inicien conversación en WhatsApp** (cómodo, familiar)
2. **Sean derivados a la web** cuando necesiten ver fotos o explorar
3. **Completen TODO el checkout en la web** (agregar productos, pagar, confirmar)
4. **Reciban confirmación automática por WhatsApp** (sin volver manualmente)

### Ventajas de este flujo:

✅ **Para el cliente:**
- No tiene que regresar a WhatsApp para confirmar
- Checkout más visual y completo
- Múltiples métodos de pago integrados
- Experiencia fluida

✅ **Para el negocio:**
- Menos mensajes de WhatsApp = Menos costo
- Mayor conversión (fotos venden)
- Datos de pago estructurados
- Integración con sistemas de pago

---

## 🔄 Flujo Completo

### **1. Inicio en WhatsApp**

```
Cliente: "Hola, ¿qué tienen?"
Bot: "¡Hola! Tenemos carnes, pollos, pescados...
      ¿Quieres ver el catálogo con fotos?"

Cliente: "Sí, quiero ver fotos"
Bot: "Perfecto! Te muestro TODO el menú con fotos 📸

      En nuestra tienda online puedes:
      ✅ Ver fotos de cada producto
      ✅ Leer ingredientes
      ✅ Filtrar por categoría
      ✅ Armar y pagar tu pedido

      🎉 ¡Completa tu compra directamente ahí!
      Te enviaré confirmación por aquí cuando finalices.

      👇 Toca aquí para abrir:
      https://tutienda.com/menu?st=abc123xyz

      💡 Tip: Completa tu compra directo en la web.
      Te avisaré cuando esté listo."
```

### **2. Cliente navega la web**

```
[Cliente toca el link]
→ Se abre página web con:
  - Catálogo completo con fotos
  - Carrito de compras
  - Filtros por categoría
  - Recomendaciones

[Cliente agrega productos al carrito]
→ 2kg Carne de Res - $360
→ 1kg Pollo Fresco - $85

[Cliente ve total]
→ Subtotal: $445
→ Envío: $30 (si eligió delivery)
→ Total: $475
```

### **3. Checkout en la web**

```
[Cliente completa formulario]
→ Método de entrega: Delivery / Recoger
→ Dirección (si es delivery)
→ Notas especiales
→ Método de pago:
   • Tarjeta (Stripe)
   • Mercado Pago
   • Efectivo
   • Transferencia

[Cliente confirma y paga]
→ Si es tarjeta/MP: Procesa pago inmediatamente
→ Si es efectivo: Marca como pendiente
```

### **4. Confirmación automática por WhatsApp**

```
[Sistema envía mensaje automático]

"🎉 ¡Pedido Confirmado!

📋 Orden: #WEB-abc123
✅ Pago: STRIPE - Aprobado

*Tu pedido:*
• 2x Carne de Res Premium - $360.00
• 1x Pollo Fresco - $85.00

💰 *Total: $475.00*

🛵 *Envío a domicilio*
📍 Calle 5 de Mayo #123, Centro

Tu pedido llegará en 30-45 minutos.

¡Gracias por tu compra! 😊"
```

### **5. Cliente NO tiene que hacer nada más**

✅ Ya pagó en la web
✅ Ya recibió confirmación
✅ Solo espera su pedido

---

## ⚙️ Configuración Backend

### **1. Instalar dependencias**

```bash
# Stripe
pip install stripe

# Mercado Pago
pip install mercadopago
```

### **2. Variables de entorno**

Crear archivo `.env` en `services/whatsapp-gateway/`:

```env
# WhatsApp
WHATSAPP_PROVIDER=meta
META_ACCESS_TOKEN=tu_token_aqui
META_PHONE_NUMBER_ID=tu_phone_id

# Pagos - Stripe
STRIPE_SECRET_KEY=sk_test_xxxxx
STRIPE_PUBLISHABLE_KEY=pk_test_xxxxx

# Pagos - Mercado Pago
MERCADOPAGO_ACCESS_TOKEN=APP_USR-xxxxx

# URLs
WEB_APP_URL=https://tutienda.com
```

### **3. Endpoints disponibles**

#### **GET /api/v1/payment/providers**
Obtener métodos de pago disponibles.

```json
{
  "providers": [
    {"id": "stripe", "name": "Tarjeta", "enabled": true, "icon": "💳"},
    {"id": "mercadopago", "name": "Mercado Pago", "enabled": true, "icon": "💙"},
    {"id": "cash", "name": "Efectivo", "enabled": true, "icon": "💵"},
    {"id": "transfer", "name": "Transferencia", "enabled": true, "icon": "🏦"}
  ]
}
```

#### **POST /api/v1/payment/init**
Iniciar proceso de pago (para Stripe/Mercado Pago).

```json
// Request
{
  "session_token": "abc123xyz",
  "provider": "stripe",
  "amount": 475.00
}

// Response
{
  "success": true,
  "status": "processing",
  "payment_id": "pi_xxxxx",
  "client_secret": "pi_xxxxx_secret_xxxxx",  // Para Stripe
  "checkout_url": "https://..."               // Para Mercado Pago
}
```

#### **POST /api/v1/web-checkout**
Finalizar checkout completo.

```json
// Request
{
  "session_token": "abc123xyz",
  "cart": [
    {
      "id": "1",
      "name": "Carne de Res Premium",
      "quantity": 2,
      "price": 180,
      "notes": "Sin grasa"
    }
  ],
  "total": 475.00,
  "payment_method": "stripe",
  "payment_status": "completed",
  "customer_notes": "Tocar el timbre",
  "delivery_method": "delivery",
  "delivery_address": "Calle 5 de Mayo #123"
}

// Response
{
  "success": true,
  "order_id": "WEB-abc123",
  "message": "Pedido procesado exitosamente",
  "phone": "+525512345678"
}
```

---

## 🎨 Configuración Frontend

### **1. Usar el ejemplo incluido**

El archivo `CHECKOUT_WEB_EXAMPLE.html` incluye:
- ✅ UI completa de checkout
- ✅ Integración con backend
- ✅ Manejo de métodos de pago
- ✅ Validaciones
- ✅ Responsive design

### **2. Personalizar para tu tienda**

```javascript
// Cambiar URL del backend
const API_URL = 'https://tu-backend.com';

// Cargar carrito real desde backend
async function loadCart() {
    const response = await fetch(`${API_URL}/api/v1/cart?st=${sessionToken}`);
    const data = await response.json();
    state.cart = data.cart;
    calculateTotal();
}

// Personalizar colores
:root {
    --primary-color: #667eea;
    --secondary-color: #764ba2;
}
```

### **3. Integración con frameworks**

#### **React/Next.js**

```jsx
import { useState, useEffect } from 'react';
import { loadStripe } from '@stripe/stripe-js';
import { Elements, CardElement, useStripe, useElements } from '@stripe/react-stripe-js';

const stripePromise = loadStripe('pk_test_xxxxx');

function CheckoutPage() {
    const [cart, setCart] = useState([]);
    const [sessionToken, setSessionToken] = useState(null);

    useEffect(() => {
        const params = new URLSearchParams(window.location.search);
        setSessionToken(params.get('st'));
        loadCart();
    }, []);

    async function handleCheckout() {
        const response = await fetch('/api/v1/web-checkout', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_token: sessionToken,
                cart,
                total: calculateTotal(),
                payment_method: 'stripe',
                payment_status: 'completed'
            })
        });

        const result = await response.json();
        if (result.success) {
            // Mostrar éxito
        }
    }

    return (
        <Elements stripe={stripePromise}>
            <CheckoutForm onSubmit={handleCheckout} />
        </Elements>
    );
}
```

#### **Vue.js**

```vue
<template>
  <div class="checkout">
    <div v-for="item in cart" :key="item.id">
      {{ item.name }} x{{ item.quantity }} - ${{ item.price }}
    </div>

    <button @click="handleCheckout">Confirmar Pedido</button>
  </div>
</template>

<script>
export default {
  data() {
    return {
      cart: [],
      sessionToken: null
    }
  },
  mounted() {
    this.sessionToken = new URLSearchParams(window.location.search).get('st');
    this.loadCart();
  },
  methods: {
    async handleCheckout() {
      const response = await fetch('/api/v1/web-checkout', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_token: this.sessionToken,
          cart: this.cart,
          total: this.calculateTotal(),
          payment_method: 'stripe',
          payment_status: 'completed'
        })
      });

      const result = await response.json();
      // Manejar resultado
    }
  }
}
</script>
```

---

## 💳 Integración de Pagos

### **Stripe (Tarjetas)**

#### **1. Obtener API Keys**
- Crear cuenta en https://stripe.com
- Dashboard → Developers → API keys
- Copiar `Secret key` y `Publishable key`

#### **2. Integrar en frontend**

```html
<script src="https://js.stripe.com/v3/"></script>
<script>
const stripe = Stripe('pk_test_xxxxx');

// Iniciar pago
const response = await fetch('/api/v1/payment/init', {
    method: 'POST',
    body: JSON.stringify({
        session_token: sessionToken,
        provider: 'stripe',
        amount: 475
    })
});

const { client_secret } = await response.json();

// Confirmar pago
const result = await stripe.confirmCardPayment(client_secret, {
    payment_method: {
        card: cardElement,
        billing_details: {
            name: 'Juan Pérez'
        }
    }
});

if (result.error) {
    console.error(result.error.message);
} else {
    // Pago exitoso → Llamar a /web-checkout
}
</script>
```

### **Mercado Pago**

#### **1. Obtener Access Token**
- Crear cuenta en https://mercadopago.com.mx
- Credentials → Access token

#### **2. Flujo**

```javascript
// 1. Iniciar preferencia
const response = await fetch('/api/v1/payment/init', {
    method: 'POST',
    body: JSON.stringify({
        session_token: sessionToken,
        provider: 'mercadopago',
        amount: 475
    })
});

const { checkout_url } = await response.json();

// 2. Redirigir al checkout
window.location.href = checkout_url;

// 3. Mercado Pago redirige de vuelta con payment_id
// Tu backend recibe webhook de MP y llama a /web-checkout automáticamente
```

### **Efectivo / Transferencia**

No requiere integración online. Solo marcar como "pending" y el cliente paga al recibir o envía comprobante.

---

## 🧪 Testing

### **1. Probar con Twilio Sandbox**

```bash
# 1. Iniciar servicios
cd services/whatsapp-gateway
python -m uvicorn src.main:app --reload --port 8080

# 2. Exponer con ngrok
ngrok http 8080

# 3. Configurar webhook en Twilio
https://tu-ngrok-url.ngrok.io/webhook/twilio
```

### **2. Flujo de prueba**

```
1. Enviar WhatsApp: "Hola"
   → Bot responde con mensaje de bienvenida

2. Enviar: "Quiero ver fotos"
   → Bot envía URL de la tienda

3. Abrir URL en navegador
   → Ver catálogo con fotos

4. Agregar productos al carrito

5. Ir a checkout

6. Seleccionar "Efectivo" (para no usar tarjeta real)

7. Confirmar pedido

8. Verificar que llegó confirmación por WhatsApp
```

### **3. Testing con Stripe**

```bash
# Tarjetas de prueba
4242 4242 4242 4242  # Éxito
4000 0000 0000 9995  # Declinada

# Fecha: Cualquier fecha futura
# CVV: Cualquier 3 dígitos
```

---

## 💰 Costos

### **Por transacción:**

| Método | Costo Transacción | Notas |
|--------|-------------------|-------|
| **Stripe** | 3.6% + $3 MXN | Tarjetas mexicanas |
| **Mercado Pago** | 3.99% + IVA | En México |
| **Efectivo** | $0 | Sin costo |
| **Transferencia** | $0 | Sin costo |

### **Ejemplo con 100 pedidos/mes:**

```
Ticket promedio: $500 MXN

COSTOS POR MES:
├── 50 pagos con Stripe: 50 × ($18 + $3) = $1,050
├── 30 pagos con Mercado Pago: 30 × $20 = $600
├── 20 pagos en efectivo: $0
└── TOTAL: $1,650/mes en comisiones

INGRESOS: 100 × $500 = $50,000
COMISIONES: $1,650 (3.3%)
```

### **Comparado con el costo anterior:**

```
ANTES (con retorno a WhatsApp):
- Cliente va a web
- Regresa a WhatsApp
- Confirma pedido
- Total: 6-10 mensajes de WhatsApp
- Costo: ~$0.30 por cliente

AHORA (checkout completo):
- Cliente va a web
- Completa TODO en web
- Recibe 1 confirmación por WhatsApp
- Total: 2-3 mensajes
- Costo: ~$0.10 por cliente

AHORRO: $0.20 por cliente
100 clientes/mes: $20 USD/mes de ahorro ✅
```

---

## ✅ Checklist de Implementación

- [ ] Configurar variables de entorno (Stripe/MP)
- [ ] Instalar dependencias Python
- [ ] Probar endpoints de pago
- [ ] Personalizar frontend HTML/CSS
- [ ] Integrar con tu catálogo de productos
- [ ] Configurar webhooks de WhatsApp
- [ ] Testing en sandbox
- [ ] Testing con pagos reales
- [ ] Monitorear confirmaciones
- [ ] Documentar para tu equipo

---

## 🚀 Próximos Pasos

1. **Implementar en producción**
2. **Agregar más métodos de pago** (OXXO, SPEI)
3. **A/B testing** de mensajes
4. **Analytics** de conversión
5. **Notificaciones de estado** (preparando, enviado, entregado)

---

## 📞 Soporte

¿Dudas? Revisa:
- `payment_handler.py` - Integración de pagos
- `main.py` - Endpoints del backend
- `CHECKOUT_WEB_EXAMPLE.html` - Ejemplo de frontend

