# Deploy a Google Cloud Run - PROYECTO_B_WHATSAPP_SAAS

## Resumen

Este documento describe cómo hacer deploy del proyecto PROYECTO_B_WHATSAPP_SAAS a Google Cloud Run.

**Estado de preparación:** ✅ **95% LISTO**

## ¿Qué se ha corregido?

### ✅ Dockerfiles Actualizados (Puerto Dinámico)

Todos los Dockerfiles han sido actualizados para usar puerto dinámico de Cloud Run:

1. **backend/whatsapp-gateway/Dockerfile**
   - ✅ ENV PORT=8000
   - ✅ CMD exec uvicorn... --port ${PORT}

2. **backend/sales-agent-base/Dockerfile**
   - ✅ ENV PORT=5000
   - ✅ run_auto.py lee PORT dinámicamente

3. **backend/api-service-base/Dockerfile**
   - ✅ ENV PORT=5011
   - ✅ CMD exec uvicorn... --port ${PORT}

4. **frontend/customer-app/Dockerfile**
   - ✅ ENV PORT=80
   - ✅ docker-entrypoint.sh para nginx dinámico

5. **frontend/admin-panel/Dockerfile**
   - ✅ ENV PORT=80
   - ✅ docker-entrypoint.sh para nginx dinámico

### ✅ Script de Deploy Automatizado

- **Archivo:** `deploy_to_cloud_run.ps1`
- **Servicios:** 5 totales (3 backend, 2 frontend)
- **Tiempo estimado:** 25-30 minutos

### ✅ Configuración de Producción

- **Archivo:** `.env.production`
- DATABASE_URL configurado para Cloud SQL (PostgreSQL)
- REDIS_URL configurado para Memorystore
- Todas las API keys presentes
- SERVICE_URLS marcados como PLACEHOLDER (actualizar post-deploy)

---

## Pre-requisitos

### 1. Infraestructura GCP (Ya creada ✅)

Estos recursos ya están creados y compartidos con RESTAURANT_VOICE_SYSTEM:

- ✅ **Cloud SQL:** restaurant-voice-system:us-central1:restaurant-db
- ✅ **Memorystore Redis:** 10.243.62.211:6379
- ✅ **Artifact Registry:** us-central1-docker.pkg.dev/restaurant-voice-system

### 2. Infraestructura Adicional (Crear)

#### VPC Connector (para Redis)

```bash
gcloud compute networks vpc-access connectors create whatsapp-connector \
  --region=us-central1 \
  --network=default \
  --range=10.8.0.0/28
```

#### Artifact Registry Repository (Opcional - si quieres separar)

```bash
gcloud artifacts repositories create whatsapp-saas \
  --repository-format=docker \
  --location=us-central1 \
  --description="WhatsApp SAAS Multi-tenant Services"
```

---

## Pasos para Deploy

### PASO 1: Verificar Autenticación

```bash
# Autenticarse con GCP
gcloud auth login

# Configurar proyecto
gcloud config set project restaurant-voice-system

# Configurar región
gcloud config set run/region us-central1
```

### PASO 2: Crear VPC Connector (Solo primera vez)

```bash
gcloud compute networks vpc-access connectors create whatsapp-connector \
  --region=us-central1 \
  --network=default \
  --range=10.8.0.0/28
```

### PASO 3: Ejecutar Deploy

```powershell
# Desde la raíz del proyecto PROYECTO_B_WHATSAPP_SAAS
.\deploy_to_cloud_run.ps1
```

Este script:
- Construye las imágenes Docker con Cloud Build
- Despliega 5 servicios a Cloud Run
- Configura Cloud SQL y VPC Connector
- Guarda las URLs en `cloud_run_urls.txt`

**Tiempo estimado:** 25-30 minutos

### PASO 4: Obtener URLs de Servicios

```bash
# Listar todos los servicios
gcloud run services list --platform managed --region us-central1

# O leer el archivo generado
cat cloud_run_urls.txt
```

Ejemplo de salida:
```
whatsapp-gateway=https://whatsapp-gateway-abc123-uc.a.run.app
sales-agent-service=https://sales-agent-service-abc123-uc.a.run.app
api-service=https://api-service-abc123-uc.a.run.app
customer-app-saas=https://customer-app-saas-abc123-uc.a.run.app
admin-panel-saas=https://admin-panel-saas-abc123-uc.a.run.app
```

### PASO 5: Actualizar .env.production

Editar `.env.production` y reemplazar los PLACEHOLDER con URLs reales:

```bash
# Antes
WHATSAPP_GATEWAY_URL=https://whatsapp-gateway-PLACEHOLDER.a.run.app

# Después (ejemplo)
WHATSAPP_GATEWAY_URL=https://whatsapp-gateway-abc123-uc.a.run.app
```

Actualizar:
- WHATSAPP_GATEWAY_URL
- SALES_AGENT_URL
- API_SERVICE_URL
- CUSTOMER_APP_URL
- ADMIN_PANEL_URL
- CORS_ORIGINS

### PASO 6: Configurar Webhooks

#### Twilio (Development)

1. Ir a https://console.twilio.com/
2. WhatsApp > Sandbox Settings
3. Webhook URL: `https://whatsapp-gateway-abc123-uc.a.run.app/webhook/whatsapp`

#### Meta (Production)

1. Ir a https://developers.facebook.com/
2. Tu App > WhatsApp > Configuration
3. Webhook URL: `https://whatsapp-gateway-abc123-uc.a.run.app/webhook/meta`
4. Verify Token: `mi_token_secreto_restaurant_2025`
5. Suscribir a eventos: messages, messaging_postbacks

### PASO 7: Verificar Servicios

```bash
# Health check de cada servicio
curl https://whatsapp-gateway-abc123-uc.a.run.app/health
curl https://sales-agent-service-abc123-uc.a.run.app/api/health
curl https://api-service-abc123-uc.a.run.app/health

# Verificar logs
gcloud run services logs read whatsapp-gateway --region us-central1 --limit 50
```

---

## Arquitectura Multi-Tenant

Este deploy sirve para **3 tiendas diferentes**:

1. **Restaurant** (tenant_id: restaurant)
2. **Farmacia** (tenant_id: farmacia)
3. **Taxis** (tenant_id: taxis)

### ¿Cómo funciona?

- **1 deploy = 3 tiendas**
- Cada tienda tiene su propio número de WhatsApp
- La base de datos usa `tenant_id` para separar datos
- El webhook identifica el tenant via query param: `/webhook?tenant=restaurant`

### Configurar Nuevo Tenant

1. Agregar configuración en base de datos:
```sql
INSERT INTO tenants (id, name, whatsapp_number, settings)
VALUES ('farmacia', 'Farmacia Central', '+521234567890', '{"theme": "green"}');
```

2. Registrar número en Meta Business

3. Configurar webhook específico:
```
https://whatsapp-gateway-abc123-uc.a.run.app/webhook/meta?tenant=farmacia
```

---

## Costos Estimados

### Cloud Run (Pay-per-use)

**Escenario: 1000 pedidos/mes por tienda (3000 total)**

| Servicio | vCPU | RAM | Costo/mes |
|----------|------|-----|-----------|
| whatsapp-gateway | 1 | 512Mi | ~$8 |
| sales-agent-service | 2 | 1Gi | ~$15 |
| api-service | 1 | 512Mi | ~$8 |
| customer-app | 1 | 256Mi | ~$3 |
| admin-panel | 1 | 256Mi | ~$3 |
| **TOTAL** | | | **~$37/mes** |

### Infraestructura Compartida

- Cloud SQL (db-f1-micro): ~$10/mes
- Redis (1GB): ~$50/mes
- VPC Connector: ~$8/mes

**Total Sistema Completo:** ~$105/mes (sirve 3 tiendas)

---

## Troubleshooting

### Error: Container failed to start

**Causa:** Puerto hardcoded en Dockerfile

**Solución:** Verificar que todos los Dockerfiles usen `ENV PORT` y `${PORT}`

### Error: Cannot connect to Cloud SQL

**Causa:** Falta configurar Cloud SQL en deploy

**Solución:** Verificar que el script incluya:
```bash
--add-cloudsql-instances=restaurant-voice-system:us-central1:restaurant-db
```

### Error: Cannot connect to Redis

**Causa:** Falta VPC Connector

**Solución:** Crear VPC Connector y agregar al deploy:
```bash
--vpc-connector=whatsapp-connector
```

### Error: 403 Forbidden from Cloud Build

**Causa:** Permisos insuficientes

**Solución:**
```bash
gcloud projects add-iam-policy-binding restaurant-voice-system \
  --member=serviceAccount:PROJECT_NUMBER@cloudbuild.gserviceaccount.com \
  --role=roles/run.admin
```

---

## Siguientes Pasos Post-Deploy

1. ✅ Verificar health checks
2. ✅ Configurar webhooks Twilio/Meta
3. ✅ Probar flujo completo WhatsApp → Backend → DB
4. ✅ Configurar monitoreo en Cloud Logging
5. ✅ Configurar alertas en Cloud Monitoring
6. ⚠️ Generar token PERMANENTE de Meta (System User)
7. ⚠️ Configurar dominio personalizado (opcional)

---

## Diferencias con RESTAURANT_VOICE_SYSTEM

| Aspecto | Restaurant | PROYECTO_B | Ventaja |
|---------|-----------|------------|---------|
| Servicios | 18 | 5 | 72% menos |
| Tiempo deploy | 1.5-2 hrs | 25-30 min | 4x más rápido |
| Multi-tenant | No | Sí (3 tiendas) | 1 deploy = 3 apps |
| Costo/mes | ~$150 | ~$37 | 75% más barato |

---

## Soporte

Si encuentras problemas:

1. Revisar logs: `gcloud run services logs read SERVICE_NAME`
2. Verificar health checks: `curl SERVICE_URL/health`
3. Revisar este documento
4. Revisar documentación de Cloud Run: https://cloud.google.com/run/docs

---

**Última actualización:** 2026-01-27
**Estado:** Listo para deploy
