# 🔗 Integración Completa de Catálogo - Web Checkout

## 📋 Descripción

Este documento explica la integración completa entre el **backend (WhatsApp Gateway + Menu Service)** y el **frontend (Web Checkout)** para permitir que los clientes compren productos directamente desde la web.

---

## 🔄 Flujo Completo de Datos

```
1. Cliente en WhatsApp
   ↓
2. Bot detecta intención de explorar
   ↓
3. Bot genera URL con session_token
   ↓
4. Cliente abre web en navegador
   ↓
5. Web carga carrito real desde backend
   ↓
6. Cliente navega, agrega productos
   ↓
7. Cliente completa checkout
   ↓
8. Backend procesa y envía confirmación por WhatsApp
```

---

## 🛠️ Endpoints Implementados

### 1. **GET /api/v1/session/{session_token}**

Obtiene los datos de la sesión actual del cliente, incluyendo su carrito.

**Uso:**
```javascript
const response = await fetch(`${API_URL}/api/v1/session/${sessionToken}`);
const data = await response.json();

console.log(data.cart);           // Productos en el carrito
console.log(data.restaurant_id);  // ID de la tienda
console.log(data.customer_name);  // Nombre del cliente
```

**Response:**
```json
{
  "success": true,
  "session_id": "abc123xyz",
  "phone": "+525512345678",
  "customer_name": "Juan Pérez",
  "restaurant_id": "carniceria",
  "cart": [
    {
      "id": "prod_001",
      "name": "Carne de Res Premium",
      "quantity": 2,
      "price": 180.00,
      "notes": ""
    }
  ],
  "cart_total": 360.00
}
```

---

### 2. **GET /api/v1/restaurants/{restaurant_id}/menu**

Obtiene el menú completo de una tienda desde Firestore (vía menu-service).

**Uso:**
```javascript
const response = await fetch(`${API_URL}/api/v1/restaurants/carniceria/menu`);
const data = await response.json();

console.log(data.products);    // Lista de productos
console.log(data.categories);  // Categorías disponibles
```

**Response:**
```json
{
  "success": true,
  "restaurant_id": "carniceria",
  "restaurant_name": "Carnicería Premium",
  "categories": ["Carnes Rojas", "Pollo", "Cerdo"],
  "products": [
    {
      "id": "prod_001",
      "name": "Carne de Res Premium",
      "description": "Corte premium para asar",
      "price": 180.00,
      "category": "Carnes Rojas",
      "image_url": "https://...",
      "available": true,
      "unit": "kg"
    }
  ]
}
```

**Filtrar por categoría:**
```javascript
const response = await fetch(
  `${API_URL}/api/v1/restaurants/carniceria/menu?category=Pollo`
);
```

---

### 3. **POST /api/v1/web-checkout**

Completa el checkout desde la web y envía confirmación automática por WhatsApp.

**Uso:**
```javascript
const response = await fetch(`${API_URL}/api/v1/web-checkout`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    session_token: sessionToken,
    cart: [
      { id: 'prod_001', name: 'Carne de Res', quantity: 2, price: 180 }
    ],
    total: 360.00,
    payment_method: 'stripe',
    payment_status: 'completed',
    delivery_method: 'delivery',
    delivery_address: 'Calle 5 de Mayo #123',
    customer_notes: 'Tocar el timbre'
  })
});

const result = await response.json();
console.log(result.order_id);  // ID de la orden creada
```

**Response:**
```json
{
  "success": true,
  "order_id": "WEB-abc123",
  "message": "Pedido procesado exitosamente",
  "phone": "+525512345678"
}
```

**Nota:** El cliente recibe automáticamente un mensaje de confirmación por WhatsApp. NO tiene que regresar a WhatsApp manualmente.

---

### 4. **GET /api/v1/payment/providers**

Obtiene los métodos de pago disponibles.

**Response:**
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

---

### 5. **POST /api/v1/payment/init**

Inicia el proceso de pago online (Stripe o Mercado Pago).

**Uso:**
```javascript
const response = await fetch(`${API_URL}/api/v1/payment/init`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    session_token: sessionToken,
    provider: 'stripe',
    amount: 360.00
  })
});

const data = await response.json();
console.log(data.client_secret);  // Para confirmar con Stripe
```

---

## 🎨 Frontend: CHECKOUT_WEB_EXAMPLE.html

El archivo `CHECKOUT_WEB_EXAMPLE.html` ahora está **completamente integrado** con el backend.

### Cambios Realizados:

#### **Antes (Hardcoded):**
```javascript
function loadCart() {
    state.cart = [
        { name: 'Carne de Res Premium', quantity: 2, price: 180 }  // ❌ Fake data
    ];
}
```

#### **Ahora (Real API):**
```javascript
async function loadCart() {
    const response = await fetch(`${API_URL}/api/v1/session/${sessionToken}`);
    const data = await response.json();

    state.cart = data.cart;              // ✅ Carrito real
    state.restaurantId = data.restaurant_id;  // ✅ Tienda real

    calculateTotal();
}
```

---

## 🚀 Cómo Usar

### **Paso 1: Configurar Variables de Entorno**

En `services/whatsapp-gateway/.env`:

```env
# WhatsApp
WHATSAPP_PROVIDER=meta
META_ACCESS_TOKEN=tu_token_aqui

# Menu Service
MENU_SERVICE_URL=http://menu-service:8001

# Pagos (opcional)
STRIPE_SECRET_KEY=sk_test_xxxxx
MERCADOPAGO_ACCESS_TOKEN=APP_USR-xxxxx
```

---

### **Paso 2: Iniciar Servicios**

```bash
# Terminal 1: Menu Service
cd services/menu-service
python -m uvicorn src.main:app --reload --port 8001

# Terminal 2: WhatsApp Gateway
cd services/whatsapp-gateway
python -m uvicorn src.main:app --reload --port 8080

# Terminal 3: Servir el HTML (opcional, para desarrollo local)
cd services/whatsapp-gateway
python -m http.server 3000
```

---

### **Paso 3: Probar el Flujo**

#### **Opción A: Desde WhatsApp (Flujo Real)**

1. Enviar mensaje por WhatsApp: `"carniceria-hola"`
2. Bot responde con link a la web
3. Abrir el link en navegador
4. Ver carrito precargado
5. Completar checkout
6. Recibir confirmación automática por WhatsApp

#### **Opción B: Testing Directo (Sin WhatsApp)**

1. Crear una sesión manualmente:
```bash
curl -X POST http://localhost:8080/api/v1/test-session \
  -H "Content-Type: application/json" \
  -d '{"phone": "+525512345678", "restaurant_id": "carniceria"}'
```

2. Obtener el `session_token` de la respuesta

3. Abrir en navegador:
```
http://localhost:3000/CHECKOUT_WEB_EXAMPLE.html?st=<session_token>
```

---

## 🔐 Seguridad del Session Token

El `session_token` en la URL está **encriptado** y tiene:

- ✅ **Firma criptográfica** (HMAC-SHA256)
- ✅ **Expiración** (24 horas por defecto)
- ✅ **Validación** en cada request

**Ejemplo de URL real:**
```
https://tutienda.com/menu?st=eyJzZXNzaW9uX2lkIjoiYWJjMTIzIiwidGltZXN0YW1wIjoxNzM...
```

---

## 📊 Sincronización de Carrito

El carrito se sincroniza **bidireccionalmente**:

1. **WhatsApp → Web:**
   - Cliente agrega productos conversando con el bot
   - Al abrir la web, el carrito ya tiene esos productos
   - Endpoint: `GET /api/v1/session/{token}`

2. **Web → Backend:**
   - Cliente agrega más productos en la web
   - Al hacer checkout, se envían todos los items
   - Endpoint: `POST /api/v1/web-checkout`

3. **Web → WhatsApp:**
   - Cliente completa pago
   - Backend envía confirmación automática por WhatsApp
   - Cliente NO tiene que regresar manualmente

---

## 🧪 Testing de Endpoints

### Test 1: Obtener Sesión
```bash
curl http://localhost:8080/api/v1/session/<SESSION_TOKEN>
```

### Test 2: Obtener Menú
```bash
curl http://localhost:8080/api/v1/restaurants/carniceria/menu
```

### Test 3: Checkout Completo
```bash
curl -X POST http://localhost:8080/api/v1/web-checkout \
  -H "Content-Type: application/json" \
  -d '{
    "session_token": "<TOKEN>",
    "cart": [{"id": "prod_001", "name": "Carne", "quantity": 2, "price": 180}],
    "total": 360,
    "payment_method": "cash",
    "payment_status": "pending",
    "delivery_method": "pickup"
  }'
```

---

## 🎯 Diferencia con el Flujo Anterior

### **ANTES: Retorno a WhatsApp (Flujo Interrumpido)**

```
WhatsApp → Web → WhatsApp (confirmar) → Orden procesada

Mensajes de WhatsApp: 5-6
Costo: ~$0.30 por cliente
Experiencia: Interrumpida
```

### **AHORA: Checkout Completo en Web (Flujo Continuo)**

```
WhatsApp → Web → Checkout completo → Confirmación automática

Mensajes de WhatsApp: 2-3
Costo: ~$0.10 por cliente
Experiencia: Fluida
```

**Ahorro: $0.20 por cliente = $20 USD/mes con 100 clientes**

---

## 📦 Archivos Modificados

### Backend:
1. ✅ `services/whatsapp-gateway/src/main.py`
   - Agregado `GET /api/v1/session/{token}`
   - Agregado `GET /api/v1/restaurants/{id}/menu`
   - Ya existía `POST /api/v1/web-checkout`

### Frontend:
2. ✅ `services/whatsapp-gateway/CHECKOUT_WEB_EXAMPLE.html`
   - Actualizado `loadCart()` para usar API real
   - Agregado `state.restaurantId`

---

## 🐛 Troubleshooting

### **Problema: "Token inválido o expirado"**
- **Causa:** El session_token expiró (>24 horas)
- **Solución:** Solicitar nuevo link por WhatsApp

### **Problema: "Sesión no encontrada"**
- **Causa:** El backend se reinició y perdió las sesiones en memoria
- **Solución:** Migrar a Redis para persistencia

### **Problema: "Carrito vacío"**
- **Causa:** No se agregaron productos vía WhatsApp antes de abrir la web
- **Solución:** Es normal. El cliente puede agregar productos en la web.

### **Problema: "Error cargando menú"**
- **Causa:** Menu-service no está corriendo o no tiene productos
- **Solución:** Verificar que menu-service esté activo y tenga productos en Firestore

---

## 🚧 Próximos Pasos (Opcional)

### **1. Página de Productos (Explorar Catálogo)**

Crear `MENU_WEB_EXAMPLE.html` para que los clientes puedan:
- Ver todos los productos con fotos
- Filtrar por categoría
- Agregar al carrito
- Ir al checkout

### **2. Migrar Sesiones a Redis**

Para producción, reemplazar:
```python
hybrid_sessions: Dict[str, HybridCustomerSession] = {}  # ❌ En memoria
```

Por:
```python
redis_client = redis.Redis(...)  # ✅ Persistente
```

### **3. Webhooks de Pago**

Implementar endpoints para recibir confirmaciones de:
- Stripe: `/webhooks/stripe`
- Mercado Pago: `/webhooks/mercadopago`

---

## ✅ Checklist de Integración Completa

- [x] Endpoint para obtener sesión con carrito
- [x] Endpoint para obtener menú de tienda
- [x] Endpoint para checkout completo
- [x] Frontend carga carrito real desde API
- [x] Frontend envía checkout completo
- [x] Confirmación automática por WhatsApp
- [ ] Página de exploración de productos (opcional)
- [ ] Migración a Redis (producción)
- [ ] Webhooks de pago (producción)

---

## 📞 Soporte

Para más información, revisa:
- `CHECKOUT_COMPLETO_README.md` - Documentación del flujo completo
- `CHECKOUT_WEB_EXAMPLE.html` - Ejemplo de frontend
- `src/main.py` - Endpoints del backend

---

**¡La integración está completa y lista para usarse!** 🎉
