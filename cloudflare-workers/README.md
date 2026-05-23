# Cloudflare Worker - WhatsApp Webhook Proxy

Proxy seguro para webhooks de WhatsApp con protección DDoS y rate limiting.

## Beneficios

- **DDoS Protection**: Protección automática de Cloudflare contra ataques
- **Edge Caching**: Distribución global en más de 200 data centers
- **Rate Limiting**: Control de tráfico integrado
- **Analytics**: Monitoreo en tiempo real de requests
- **Low Latency**: Respuesta ultra-rápida desde edge network

## Setup

### 1. Instalar Wrangler CLI

```bash
npm install -g wrangler
```

### 2. Autenticar con Cloudflare

```bash
wrangler login
```

### 3. Actualizar Backend URL

Editar `whatsapp-proxy.js` y reemplazar:

```javascript
const BACKEND_URL = 'https://whatsapp-gateway-XXXXXXXXXX-uc.a.run.app';
```

Con la URL real de tu servicio Cloud Run.

### 4. (Opcional) Crear KV Namespace para Rate Limiting

```bash
# Crear namespace
wrangler kv:namespace create "RATE_LIMITER"

# Copiar el ID generado y actualizarlo en wrangler.toml
```

### 5. Deploy

```bash
# Development
wrangler dev

# Production
wrangler deploy
```

### 6. Obtener Worker URL

Después del deployment, obtendrás una URL como:

```
https://whatsapp-webhook-proxy.YOUR_SUBDOMAIN.workers.dev
```

### 7. Configurar Webhook en Meta/Twilio

Usar la Worker URL como webhook:

**Meta Cloud API:**
- Webhook URL: `https://whatsapp-webhook-proxy.YOUR_SUBDOMAIN.workers.dev/webhook/meta`
- Verify Token: (el configurado en tu backend)

**Twilio:**
- Webhook URL: `https://whatsapp-webhook-proxy.YOUR_SUBDOMAIN.workers.dev/webhook/twilio`

## Custom Domain (Opcional)

Para usar un dominio personalizado:

### 1. Agregar dominio a Cloudflare

Agregar tu dominio en: https://dash.cloudflare.com/

### 2. Configurar Route en wrangler.toml

```toml
routes = [
  { pattern = "webhook.tu-dominio.com/*", zone_name = "tu-dominio.com" }
]
```

### 3. Deploy

```bash
wrangler deploy
```

Ahora puedes usar: `https://webhook.tu-dominio.com/webhook/meta`

## Monitoreo

### Ver Logs en Tiempo Real

```bash
wrangler tail
```

### Ver Analytics

Dashboard: https://dash.cloudflare.com/ → Workers & Pages → Tu worker → Analytics

## Configuración Avanzada

### Ajustar Rate Limiting

Editar `whatsapp-proxy.js`:

```javascript
const RATE_LIMIT = {
  enabled: true,
  requestsPerMinute: 60,  // Ajustar según necesidades
  burstSize: 10
};
```

### Configurar CORS

Editar `ALLOWED_ORIGINS` en `whatsapp-proxy.js`:

```javascript
const ALLOWED_ORIGINS = [
  'https://tu-dominio.web.app',
  'https://tu-dominio.firebaseapp.com'
];
```

## Costos

**Free Tier:**
- 100,000 requests/day
- Suficiente para empezar

**Paid Plan ($5/month):**
- 10 millones requests/month incluidos
- $0.50 por millón adicional
- KV storage incluido
- Custom domains

## Troubleshooting

### Error: "Service Temporarily Unavailable"

Verificar que `BACKEND_URL` apunte correctamente a tu servicio Cloud Run.

### Rate Limit Issues

Si ves muchos `429 Too Many Requests`, ajustar `requestsPerMinute` en la configuración.

### CORS Errors

Agregar tu dominio a `ALLOWED_ORIGINS` en `whatsapp-proxy.js`.

## Recursos

- [Cloudflare Workers Docs](https://developers.cloudflare.com/workers/)
- [Wrangler CLI Docs](https://developers.cloudflare.com/workers/wrangler/)
- [Workers KV](https://developers.cloudflare.com/workers/runtime-apis/kv/)
