# 🎯 Sistema de Puntos de Fidelidad - Documentación Completa

## Índice
1. [Descripción General](#descripción-general)
2. [Características Principales](#características-principales)
3. [Configuración](#configuración)
4. [API Endpoints](#api-endpoints)
5. [Integración con Dashboard](#integración-con-dashboard)
6. [Ejemplos de Uso](#ejemplos-de-uso)
7. [Flujo Automático](#flujo-automático)

---

## Descripción General

Sistema completo de puntos de fidelidad para tiendas/restaurantes que venden por WhatsApp. Permite:
- ✅ Otorgar puntos automáticamente por cada compra
- ✅ Canjear puntos por descuentos
- ✅ Sistema de niveles/tiers (Bronce, Plata, Oro, Platino)
- ✅ Configuración personalizada por cada tienda
- ✅ Bonos especiales (primera compra, cumpleaños, referidos)
- ✅ Notificaciones automáticas por WhatsApp

---

## Características Principales

### 1. Sistema de Puntos Configurable

Cada tienda puede configurar:
- **Tasa de ganancia**: Cuántos puntos por cada peso gastado (ej: 1 punto por cada $10)
- **Valor de canje**: Cuánto vale cada punto en descuento (ej: 1 punto = $0.50)
- **Mínimo para canjear**: Mínimo de puntos necesarios (ej: 100 puntos)
- **Máximo de descuento**: % máximo del total que se puede pagar con puntos (ej: 50%)
- **Expiración**: Días hasta que expiran los puntos (ej: 365 días)

### 2. Sistema de Niveles (Tiers)

| Nivel | Puntos Requeridos | Multiplicador | Beneficios |
|-------|------------------|---------------|------------|
| 🥉 Bronce | 0 - 999 | 1.0x | Estándar |
| 🥈 Plata | 1,000 - 2,499 | 1.5x | +50% puntos + Envío gratis |
| 🥇 Oro | 2,500 - 4,999 | 2.0x | +100% puntos + 5% descuento |
| 💎 Platino | 5,000+ | 3.0x | +200% puntos + 10% descuento |

### 3. Bonos Especiales

- **Primera compra**: Puntos extras en la primera orden
- **Cumpleaños**: Puntos de regalo en el día del cumpleaños
- **Referidos**: Puntos por invitar amigos
- **Promociones**: Bonos manuales por el admin

---

## Configuración

### Configuración por Defecto

Cuando una tienda se registra, se crea automáticamente con esta configuración:

```json
{
  "enabled": true,
  "points_per_currency": 0.1,     // 1 punto por cada $10
  "currency_per_point": 0.5,      // 1 punto = $0.50 descuento
  "min_points_to_redeem": 100,    // Mínimo 100 puntos para canjear
  "max_redeem_percentage": 50.0,  // Máximo 50% del total con puntos
  "points_expire_days": 365,      // Puntos expiran en 1 año
  "tiers_enabled": true,
  "birthday_bonus": 100,          // 100 puntos en cumpleaños
  "referral_bonus": 50,           // 50 puntos por referir
  "first_purchase_bonus": 50      // 50 puntos en primera compra
}
```

### Panel de Configuración para Dashboard Admin

El dueño de la tienda puede modificar todos estos valores desde su dashboard web.

---

## API Endpoints

### 1. Obtener Balance de Puntos

**GET** `/api/v1/loyalty/balance/{customer_phone}?restaurant_id=carniceria`

**Response:**
```json
{
  "success": true,
  "customer_phone": "5215512345678",
  "restaurant_id": "carniceria",
  "available_points": 350,
  "lifetime_points": 1200,
  "current_tier": "plata",
  "tier_benefits": {
    "discount": 0,
    "free_shipping": true
  },
  "points_value_in_currency": 175.00,
  "total_spent": 12000.00,
  "total_orders": 8,
  "next_tier": "oro",
  "points_to_next_tier": 1300
}
```

### 2. Otorgar Puntos (Automático en Checkout)

**POST** `/api/v1/loyalty/earn`

**Request:**
```json
{
  "customer_phone": "5215512345678",
  "restaurant_id": "carniceria",
  "order_id": "WEB-12345",
  "order_total": 500.00,
  "customer_name": "Juan Pérez"
}
```

**Response:**
```json
{
  "success": true,
  "points_earned": 75,
  "total_points": 425,
  "lifetime_points": 1275,
  "current_tier": "plata",
  "tier_upgraded": false,
  "multiplier": 1.5,
  "first_purchase_bonus": 0,
  "total_orders": 9,
  "total_spent": 12500.00
}
```

### 3. Canjear Puntos

**POST** `/api/v1/loyalty/redeem`

**Request:**
```json
{
  "customer_phone": "5215512345678",
  "restaurant_id": "carniceria",
  "points_to_redeem": 200,
  "order_total": 500.00
}
```

**Response:**
```json
{
  "success": true,
  "discount_amount": 100.00,
  "points_redeemed": 200,
  "points_remaining": 225,
  "message": "¡Descuento de $100.00 aplicado!"
}
```

### 4. Obtener Configuración

**GET** `/api/v1/loyalty/config/{restaurant_id}`

**Response:**
```json
{
  "success": true,
  "config": {
    "restaurant_id": "carniceria",
    "enabled": true,
    "points_per_currency": 0.1,
    "currency_per_point": 0.5,
    "min_points_to_redeem": 100,
    "max_redeem_percentage": 50.0,
    "tiers_enabled": true,
    ...
  }
}
```

### 5. Actualizar Configuración (Dashboard Admin)

**PUT** `/api/v1/loyalty/config/{restaurant_id}`

**Request:**
```json
{
  "restaurant_id": "carniceria",
  "points_per_currency": 0.15,
  "currency_per_point": 0.6,
  "birthday_bonus": 150
}
```

**Response:**
```json
{
  "success": true,
  "config": { ... },
  "message": "Configuración actualizada"
}
```

---

## Integración con Dashboard

### Página de Configuración

El dashboard admin debe incluir un formulario con:

```html
<form id="loyalty-config-form">
  <!-- Sistema Habilitado -->
  <label>
    <input type="checkbox" id="enabled" checked>
    Sistema de puntos habilitado
  </label>

  <!-- Tasa de Puntos -->
  <label>
    Puntos por cada peso gastado:
    <input type="number" id="points_per_currency" value="0.1" step="0.01">
    <small>Ejemplo: 0.1 = 1 punto por cada $10</small>
  </label>

  <!-- Valor de Puntos -->
  <label>
    Valor de cada punto en descuento:
    <input type="number" id="currency_per_point" value="0.5" step="0.1">
    <small>Ejemplo: 0.5 = cada punto vale $0.50</small>
  </label>

  <!-- Mínimo para Canjear -->
  <label>
    Puntos mínimos para canjear:
    <input type="number" id="min_points_to_redeem" value="100">
  </label>

  <!-- Máximo Descuento -->
  <label>
    Máximo % pagable con puntos:
    <input type="number" id="max_redeem_percentage" value="50" max="100">
  </label>

  <!-- Bonos -->
  <label>
    Puntos bonus primera compra:
    <input type="number" id="first_purchase_bonus" value="50">
  </label>

  <label>
    Puntos bonus cumpleaños:
    <input type="number" id="birthday_bonus" value="100">
  </label>

  <label>
    Puntos bonus por referir amigo:
    <input type="number" id="referral_bonus" value="50">
  </label>

  <button type="submit">Guardar Configuración</button>
</form>

<script>
document.getElementById('loyalty-config-form').addEventListener('submit', async (e) => {
  e.preventDefault();

  const config = {
    restaurant_id: 'carniceria', // Tu ID de restaurante
    enabled: document.getElementById('enabled').checked,
    points_per_currency: parseFloat(document.getElementById('points_per_currency').value),
    currency_per_point: parseFloat(document.getElementById('currency_per_point').value),
    min_points_to_redeem: parseInt(document.getElementById('min_points_to_redeem').value),
    max_redeem_percentage: parseFloat(document.getElementById('max_redeem_percentage').value),
    first_purchase_bonus: parseInt(document.getElementById('first_purchase_bonus').value),
    birthday_bonus: parseInt(document.getElementById('birthday_bonus').value),
    referral_bonus: parseInt(document.getElementById('referral_bonus').value)
  };

  const response = await fetch(
    `http://localhost:8080/api/v1/loyalty/config/${config.restaurant_id}`,
    {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config)
    }
  );

  const result = await response.json();
  if (result.success) {
    alert('Configuración actualizada correctamente');
  }
});
</script>
```

### Dashboard de Clientes

Mostrar resumen de clientes con más puntos:

```javascript
// Consultar clientes y sus puntos
const customers = await fetch('http://localhost:8080/api/v1/loyalty/customers?restaurant_id=carniceria');

// Mostrar top 10
<table>
  <thead>
    <tr>
      <th>Cliente</th>
      <th>Puntos</th>
      <th>Nivel</th>
      <th>Total Gastado</th>
      <th>Órdenes</th>
    </tr>
  </thead>
  <tbody id="top-customers"></tbody>
</table>
```

---

## Ejemplos de Uso

### Ejemplo 1: Cliente Nuevo - Primera Compra

```
Cliente: Juan (5215512345678)
Compra: $500
Config: 1 punto = $10, bonus primera compra = 50 puntos

Cálculo:
- Puntos base: $500 / $10 = 50 puntos
- Bonus primera compra: +50 puntos
- Total ganado: 100 puntos

Notificación WhatsApp:
"🎉 ¡Pedido Confirmado!
...
⭐ Programa de Fidelidad
Ganaste: +100 puntos
Total acumulado: 100 puntos
Nivel: BRONCE
🎁 ¡Bonus primera compra incluido!
..."
```

### Ejemplo 2: Cliente Frecuente - Nivel Plata

```
Cliente: María (5215587654321)
Compra: $1,000
Nivel actual: Plata (multiplicador 1.5x)
Puntos acumulados: 950

Cálculo:
- Puntos base: $1,000 / $10 = 100 puntos
- Con multiplicador 1.5x: 100 × 1.5 = 150 puntos
- Total ganado: 150 puntos
- Nuevo total: 950 + 150 = 1,100 puntos

Notificación WhatsApp:
"🎉 ¡Pedido Confirmado!
...
⭐ Programa de Fidelidad
Ganaste: +150 puntos
Total acumulado: 1100 puntos
Nivel: PLATA
..."
```

### Ejemplo 3: Canjear Puntos

```
Cliente quiere canjear 200 puntos en compra de $600

Cálculo:
- Valor de 200 puntos: 200 × $0.50 = $100 descuento
- Límite 50% del total: $600 × 50% = $300 máximo
- $100 < $300 ✓ (permitido)

Resultado:
- Total original: $600
- Descuento: -$100
- Total a pagar: $500
- Puntos restantes: cliente.points - 200
```

---

## Flujo Automático

### Flujo Completo de Compra con Puntos

```
1. Cliente inicia chat WhatsApp
   └─> Gateway crea sesión

2. Cliente navega a web (link)
   └─> Frontend consulta balance: GET /api/v1/loyalty/balance/{phone}
   └─> Muestra: "Tienes 350 puntos ($175 disponibles)"

3. Cliente agrega productos al carrito
   └─> Total: $500

4. Cliente puede optar por usar puntos
   └─> Checkbox: "Usar 200 puntos (-$100)"
   └─> Nuevo total: $400

5. Cliente completa checkout
   └─> Si usó puntos:
       POST /api/v1/loyalty/redeem
       { points_to_redeem: 200, order_total: 500 }

   └─> POST /api/v1/web-checkout
       { cart, total, payment_method, ... }

6. Backend procesa automáticamente:
   a) Canjea puntos (si se usaron)
   b) Procesa pago
   c) Otorga nuevos puntos por la compra
      POST /api/v1/loyalty/earn (automático)
      { order_total: 400, ... }
   d) Calcula con multiplicador de tier
   e) Agrega bonos si aplican

7. WhatsApp notifica al cliente:
   "🎉 ¡Pedido Confirmado!
   📋 Orden: #WEB-12345

   💰 Total: $400.00

   ⭐ Programa de Fidelidad
   Ganaste: +60 puntos
   Total acumulado: 210 puntos
   Nivel: BRONCE

   ¡Gracias por tu compra! 😊"
```

---

## Archivos del Sistema

```
backend/whatsapp-gateway/src/
├── loyalty_models.py          # Modelos de datos (Pydantic)
├── loyalty_handler.py         # Lógica de negocio
└── main.py                    # Endpoints API (actualizado)

backend/whatsapp-gateway/data/loyalty/
├── configs/                   # Configuraciones por tienda
│   └── carniceria.json
├── customers/                 # Datos de clientes
│   └── 5215512345678_carniceria.json
└── transactions/              # Historial de transacciones
    └── {transaction_id}.json
```

---

## Testing

### Probar sistema de puntos:

```bash
# 1. Obtener configuración por defecto
curl http://localhost:8080/api/v1/loyalty/config/carniceria

# 2. Simular compra y ganar puntos
curl -X POST http://localhost:8080/api/v1/loyalty/earn \
  -H "Content-Type: application/json" \
  -d '{
    "customer_phone": "5215512345678",
    "restaurant_id": "carniceria",
    "order_id": "TEST-001",
    "order_total": 500.00,
    "customer_name": "Juan Pérez"
  }'

# 3. Consultar balance
curl "http://localhost:8080/api/v1/loyalty/balance/5215512345678?restaurant_id=carniceria"

# 4. Canjear puntos
curl -X POST http://localhost:8080/api/v1/loyalty/redeem \
  -H "Content-Type: application/json" \
  -d '{
    "customer_phone": "5215512345678",
    "restaurant_id": "carniceria",
    "points_to_redeem": 100,
    "order_total": 500.00
  }'

# 5. Actualizar configuración
curl -X PUT http://localhost:8080/api/v1/loyalty/config/carniceria \
  -H "Content-Type: application/json" \
  -d '{
    "restaurant_id": "carniceria",
    "points_per_currency": 0.2,
    "birthday_bonus": 200
  }'
```

---

## Próximas Mejoras

- [ ] Migrar almacenamiento de JSON a base de datos (PostgreSQL/Firestore)
- [ ] Panel analytics de loyalty en dashboard
- [ ] Sistema de cupones personalizados
- [ ] Gamificación: retos y logros
- [ ] Programa de referidos multinivel
- [ ] Notificaciones de puntos por vencer
- [ ] Eventos especiales (doble puntos, etc)

---

**¡Sistema listo para usar! 🎉**

El dueño puede configurar todo desde su dashboard y los puntos se otorgan automáticamente en cada compra.
