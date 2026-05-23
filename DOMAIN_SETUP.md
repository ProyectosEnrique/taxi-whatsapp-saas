# Guía de Configuración de Dominio

## Opción 1: Cloudflare (Recomendado - Más Fácil)

### Ventajas
- ✅ SSL gratis automático
- ✅ CDN global incluido
- ✅ DDoS protection gratis
- ✅ Cache inteligente
- ✅ No necesitas configurar nginx
- ✅ Muy fácil de configurar

### Pasos

1. **Comprar dominio** (o usar uno existente)
   - GoDaddy: ~$10/año
   - Namecheap: ~$8/año
   - Google Domains: ~$12/año

2. **Agregar dominio a Cloudflare**
   - Ve a https://dash.cloudflare.com/
   - Click "Add Site"
   - Ingresa tu dominio: `taxisystem.com`
   - Selecciona plan FREE

3. **Cambiar Nameservers**
   - Cloudflare te dará 2 nameservers:
     ```
     alan.ns.cloudflare.com
     june.ns.cloudflare.com
     ```
   - Ve a tu proveedor de dominios (GoDaddy, Namecheap, etc.)
   - En la configuración del dominio, cambia los nameservers
   - **Espera 24-48 horas** para propagación

4. **Configurar DNS Records en Cloudflare**

   Ve a DNS → Records y agrega:

   | Type | Name | Content | Proxy Status | TTL |
   |------|------|---------|--------------|-----|
   | A | driver | TU_IP_SERVIDOR | Proxied ☁️ | Auto |
   | A | customer | TU_IP_SERVIDOR | Proxied ☁️ | Auto |
   | A | admin | TU_IP_SERVIDOR | Proxied ☁️ | Auto |
   | A | api | TU_IP_SERVIDOR | Proxied ☁️ | Auto |
   | A | @ | TU_IP_SERVIDOR | Proxied ☁️ | Auto |

   **Resultado:**
   - `driver.taxisystem.com` → Driver App
   - `customer.taxisystem.com` → Customer App
   - `admin.taxisystem.com` → Admin Panel
   - `api.taxisystem.com` → Backend API
   - `taxisystem.com` → Landing page

5. **Configurar SSL/TLS**
   - Ve a SSL/TLS → Overview
   - Selecciona **"Full"** (no "Full strict" por ahora)
   - Espera 5-10 minutos para que se active

6. **Configurar Page Rules (Cache)**
   - Ve a Rules → Page Rules
   - Crear regla para `*.taxisystem.com/*.js`
     - Cache Level: Standard
     - Browser TTL: 1 month
   - Crear regla para `*.taxisystem.com/*.css`
     - Cache Level: Standard
     - Browser TTL: 1 month
   - Crear regla para `api.taxisystem.com/*`
     - Cache Level: Bypass

7. **Actualizar .env.production**

   Editar archivos:

   **frontend/driver-app/.env.production**:
   ```env
   VITE_API_BASE_URL=https://api.taxisystem.com/api/v1
   VITE_TENANT_ID=tenant_taxi_001
   ```

   **frontend/taxi-customer-app/.env.production**:
   ```env
   VITE_API_BASE_URL=https://api.taxisystem.com/api/v1
   VITE_GOOGLE_MAPS_KEY=tu_key_de_google_maps
   VITE_TENANT_ID=tenant_taxi_001
   ```

   **frontend/admin-panel/.env.production**:
   ```env
   VITE_API_BASE_URL=https://api.taxisystem.com/api/v1
   VITE_TENANT_ID=tenant_taxi_001
   ```

   **backend/sales-agent-base/.env.production**:
   ```env
   CORS_ORIGINS=https://driver.taxisystem.com,https://customer.taxisystem.com,https://admin.taxisystem.com
   ```

8. **Rebuild y redeploy**
   ```bash
   docker-compose -f docker-compose.prod.yml down
   docker-compose -f docker-compose.prod.yml build --no-cache
   docker-compose -f docker-compose.prod.yml up -d
   ```

9. **Verificar**
   - Abre https://driver.taxisystem.com
   - Abre https://customer.taxisystem.com
   - Abre https://admin.taxisystem.com
   - Verifica el candado SSL en el navegador

---

## Opción 2: Let's Encrypt + Nginx (Avanzado)

### Ventajas
- ✅ Control total
- ✅ Sin intermediarios
- ✅ Gratis

### Desventajas
- ❌ Más complejo de configurar
- ❌ Renovación manual cada 90 días
- ❌ Sin CDN

### Pasos

1. **Instalar Certbot**
   ```bash
   sudo apt-get update
   sudo apt-get install certbot python3-certbot-nginx
   ```

2. **Obtener certificados**
   ```bash
   sudo certbot --nginx -d driver.taxisystem.com
   sudo certbot --nginx -d customer.taxisystem.com
   sudo certbot --nginx -d admin.taxisystem.com
   sudo certbot --nginx -d api.taxisystem.com
   ```

3. **Configurar auto-renovación**
   ```bash
   sudo crontab -e
   # Agregar:
   0 0 1 * * certbot renew --quiet
   ```

4. **Configurar Nginx**

   Ver archivo completo en `DEPLOYMENT.md` sección "Configuración de Dominio y SSL"

---

## Opción 3: Railway/Render (Deploy Automático)

### Railway

1. **Push código a GitHub**
2. **Conectar Railway a GitHub**
3. **Deploy automático**
   - Railway asigna subdominios:
     - `driver-app-production.up.railway.app`
     - `customer-app-production.up.railway.app`
     - `admin-panel-production.up.railway.app`

4. **Configurar dominio custom**
   - Settings → Domains → Add Custom Domain
   - Agregar `driver.taxisystem.com`
   - Configurar DNS CNAME en tu proveedor

### Render

Similar a Railway pero con interfaz diferente.

---

## Verificación Final

Una vez configurado el dominio, verifica:

1. **SSL activo**: Candado verde en el navegador
2. **HTTPS redirect**: http:// redirige a https://
3. **CORS funcionando**: Frontend puede llamar al backend
4. **PWA manifest**: Chrome DevTools → Application → Manifest
5. **Service Worker registrado**: Chrome DevTools → Application → Service Workers
6. **Instalación PWA**: Botón de instalación aparece en Chrome

---

## Dominios Gratuitos (Para Pruebas)

Si solo quieres probar:

1. **FreeDNS**: https://freedns.afraid.org/
   - Subdominios gratis: `tuapp.mooo.com`

2. **Cloudflare Pages**
   - Deploy directo desde GitHub
   - Dominio gratis: `tuapp.pages.dev`

3. **Vercel**
   - Deploy automático
   - Dominio gratis: `tuapp.vercel.app`

---

## Costos Aproximados

| Servicio | Costo Mensual |
|----------|---------------|
| Dominio (.com) | ~$1/mes ($12/año) |
| Cloudflare Free | $0 |
| Let's Encrypt | $0 |
| Railway (Hobby) | $5/mes |
| Render (Free tier) | $0 |
| VPS Digital Ocean | $6/mes |

**Recomendación para empezar**:
- Dominio en Namecheap: $8/año
- Cloudflare Free: $0
- **Total: ~$0.70/mes**
