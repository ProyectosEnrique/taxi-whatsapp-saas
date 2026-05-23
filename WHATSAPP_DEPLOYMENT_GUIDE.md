# 🚀 WHATSAPP SAAS - GUÍA COMPLETA DE DEPLOYMENT

**Proyecto:** WhatsApp Multi-Tenant SAAS (Restaurant, Farmacia, Taxis)
**Plataforma:** Google Cloud Run
**Fecha:** 2026-01-27
**Estado:** ✅ LISTO PARA DEPLOY

---

## 📋 TABLA DE CONTENIDO

1. [Resumen Ejecutivo](#resumen-ejecutivo)
2. [Pre-requisitos](#pre-requisitos)
3. [Infraestructura Necesaria](#infraestructura-necesaria)
4. [Pasos de Deployment](#pasos-de-deployment)
5. [Post-Deployment](#post-deployment)
6. [Arquitectura Multi-Tenant](#arquitectura-multi-tenant)
7. [Troubleshooting](#troubleshooting)
8. [Costos Estimados](#costos-estimados)

---

## 📊 RESUMEN EJECUTIVO

### ¿Qué es este proyecto?

Sistema multi-tenant de ventas por WhatsApp que permite a **3 negocios diferentes** (Restaurant, Farmacia, Taxis) compartir la misma infraestructura.

### Características Principales

- ✅ **Multi-Tenant:** 1 deploy sirve para 3 negocios
- ✅ **Serverless:** Solo pagas por uso real
- ✅ **Auto-escalable:** Soporta de 0 a millones de requests
- ✅ **IA Integrada:** LLMs múltiples (Cerebras, Groq, Gemini, OpenAI)
- ✅ **WhatsApp Business:** Integración Meta + Twilio

### Servicios a Desplegar

| Servicio | Tipo | Descripción |
|----------|------|-------------|
| whatsapp-gateway | Backend | Webhook WhatsApp + enrutamiento |
| sales-agent-service | Backend | Agente IA conversacional |
| api-service | Backend | API REST (menú, pedidos, usuarios) |
| customer-app-saas | Frontend | PWA para clientes |
| admin-panel-saas | Frontend | Panel de administración |

**Total:** 5 servicios
**Tiempo estimado:** 25-30 minutos

---

## ✅ PRE-REQUISITOS

### 1. Infraestructura YA Creada (Compartida con Restaurant System)

- ✅ **Cloud SQL:** `restaurant-voice-system:us-central1:restaurant-db`
- ✅ **Memorystore Redis:** `10.243.62.211:6379`
- ✅ **Artifact Registry:** `us-central1-docker.pkg.dev/restaurant-voice-system/restaurant-services`

### 2. Herramientas Instaladas

```bash
# Verificar instalación
gcloud --version
# Google Cloud SDK 553.0.0

# Autenticarse
gcloud auth login

# Configurar proyecto
gcloud config set project restaurant-voice-system
gcloud config set run/region us-central1
```

### 3. APIs Habilitadas en GCP

```bash
# Habilitar APIs necesarias
gcloud services enable \
  run.googleapis.com \
  sql-component.googleapis.com \
  sqladmin.googleapis.com \
  redis.googleapis.com \
  vpcaccess.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com
```

---

## 🏗️ INFRAESTRUCTURA NECESARIA

### PASO 1: Crear VPC Connector (CRÍTICO para Redis)

```powershell
# Crear VPC Connector para acceso a Memorystore Redis
& "C:\Program Files (x86)\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd" compute networks vpc-access connectors create whatsapp-connector `
  --region=us-central1 `
  --network=default `
  --range=10.8.0.0/28 `
  --min-instances=2 `
  --max-instances=10
```

**⚠️ IMPORTANTE:** Este paso es OBLIGATORIO antes del deploy. Sin el VPC connector, los servicios no podrán conectarse a Redis.

**Verificar creación:**

```powershell
& "C:\Program Files (x86)\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd" compute networks vpc-access connectors list --region=us-central1
```

**Costo:** ~$8/mes

---

## 🚀 PASOS DE DEPLOYMENT

### PASO 1: Verificar Archivos de Configuración

Verificar que existan estos archivos en la raíz del proyecto:

```
✅ env-vars-whatsapp-gateway.yaml
✅ env-vars-sales-agent.yaml
✅ env-vars-api-service.yaml
✅ deploy_to_cloud_run.ps1
```

### PASO 2: Revisar Variables de Entorno

Los archivos `env-vars-*.yaml` ya contienen:
- ✅ API Keys de IA configuradas
- ✅ Credenciales de WhatsApp (Twilio + Meta)
- ✅ Configuración de Redis
- ✅ Configuración de Cloud SQL
- ⚠️ URLs de servicios (se actualizarán post-deploy)

### PASO 3: Ejecutar Deployment

```powershell
# Navegar al proyecto
cd C:\Users\ASUS\Desktop\PROYECTOS_AGENTE_VENTAS\PROYECTO_B_WHATSAPP_SAAS

# Ejecutar script de deployment
powershell.exe -ExecutionPolicy Bypass -File .\deploy_to_cloud_run.ps1
```

**Proceso:**
1. Build de 5 imágenes Docker (~15-20 min)
2. Deploy a Cloud Run (~5-10 min)
3. Generación de URLs en `cloud_run_urls.txt`

**Tiempo total:** 25-30 minutos

### PASO 4: Obtener URLs de Servicios

El script genera automáticamente el archivo `cloud_run_urls.txt`:

```
whatsapp-gateway=https://whatsapp-gateway-XXXXXXX.us-central1.run.app
sales-agent-service=https://sales-agent-service-XXXXXXX.us-central1.run.app
api-service=https://api-service-XXXXXXX.us-central1.run.app
customer-app-saas=https://customer-app-saas-XXXXXXX.us-central1.run.app
admin-panel-saas=https://admin-panel-saas-XXXXXXX.us-central1.run.app
```

---

## 🔧 POST-DEPLOYMENT

### PASO 1: Actualizar URLs en Archivos de Env Vars

Editar los 3 archivos `env-vars-*.yaml` y actualizar las URLs:

#### env-vars-whatsapp-gateway.yaml
```yaml
# Antes
SALES_AGENT_URL: "http://sales-agent-service:5000"
API_SERVICE_URL: "http://api-service:5011"

# Después (URLs reales de Cloud Run)
SALES_AGENT_URL: "https://sales-agent-service-XXXXXXX.us-central1.run.app"
API_SERVICE_URL: "https://api-service-XXXXXXX.us-central1.run.app"
```

#### env-vars-sales-agent.yaml
```yaml
# Actualizar
API_SERVICE_URL: "https://api-service-XXXXXXX.us-central1.run.app"
WHATSAPP_GATEWAY_URL: "https://whatsapp-gateway-XXXXXXX.us-central1.run.app"
```

#### env-vars-api-service.yaml
```yaml
# Actualizar
WHATSAPP_GATEWAY_URL: "https://whatsapp-gateway-XXXXXXX.us-central1.run.app"
SALES_AGENT_URL: "https://sales-agent-service-XXXXXXX.us-central1.run.app"
```

#### Actualizar CORS_ORIGINS en los 3 archivos
```yaml
# Agregar las URLs de los frontends
CORS_ORIGINS: '["https://customer-app-saas-XXXXXXX.us-central1.run.app","https://admin-panel-saas-XXXXXXX.us-central1.run.app","*"]'
```

### PASO 2: Redesplegar Servicios con URLs Actualizadas

```powershell
# Redesplegar solo los backends (sin rebuild)
& "C:\Program Files (x86)\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd" run deploy whatsapp-gateway `
  --image=us-central1-docker.pkg.dev/restaurant-voice-system/restaurant-services/whatsapp-gateway:latest `
  --platform=managed --region=us-central1 --allow-unauthenticated `
  --port=8000 --memory=512Mi --cpu=1 --timeout=300 `
  --min-instances=0 --max-instances=10 `
  --vpc-connector=whatsapp-connector `
  --env-vars-file=env-vars-whatsapp-gateway.yaml --quiet

& "C:\Program Files (x86)\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd" run deploy sales-agent-service `
  --image=us-central1-docker.pkg.dev/restaurant-voice-system/restaurant-services/sales-agent-service:latest `
  --platform=managed --region=us-central1 --allow-unauthenticated `
  --port=5000 --memory=1Gi --cpu=2 --timeout=300 `
  --min-instances=0 --max-instances=10 `
  --vpc-connector=whatsapp-connector `
  --env-vars-file=env-vars-sales-agent.yaml --quiet

& "C:\Program Files (x86)\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd" run deploy api-service `
  --image=us-central1-docker.pkg.dev/restaurant-voice-system/restaurant-services/api-service:latest `
  --platform=managed --region=us-central1 --allow-unauthenticated `
  --port=5011 --memory=512Mi --cpu=1 --timeout=300 `
  --min-instances=0 --max-instances=10 `
  --add-cloudsql-instances=restaurant-voice-system:us-central1:restaurant-db `
  --env-vars-file=env-vars-api-service.yaml --quiet
```

### PASO 3: Configurar Webhooks de WhatsApp

#### Twilio (Development/Testing)

1. Ir a https://console.twilio.com/
2. **Messaging > Try it out > Send a WhatsApp message**
3. **Sandbox Settings**
4. **When a message comes in:**
   ```
   https://whatsapp-gateway-XXXXXXX.us-central1.run.app/webhook/whatsapp
   ```
5. **HTTP POST**
6. **Save**

#### Meta WhatsApp Business (Production)

1. Ir a https://developers.facebook.com/
2. Seleccionar tu App
3. **WhatsApp > Configuration**
4. **Webhook URL:**
   ```
   https://whatsapp-gateway-XXXXXXX.us-central1.run.app/webhook/meta
   ```
5. **Verify Token:** `mi_token_secreto_restaurant_2025`
6. **Verify and Save**
7. **Subscribe to webhooks:** `messages`, `messaging_postbacks`

### PASO 4: Verificar Servicios

```powershell
# Health checks
curl https://whatsapp-gateway-XXXXXXX.us-central1.run.app/health
curl https://sales-agent-service-XXXXXXX.us-central1.run.app/api/health
curl https://api-service-XXXXXXX.us-central1.run.app/health

# Ver logs en tiempo real
& "C:\Program Files (x86)\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd" logging tail "resource.type=cloud_run_revision AND resource.labels.service_name=whatsapp-gateway" --format=json
```

### PASO 5: Probar Flujo Completo

1. **Enviar mensaje de WhatsApp** al número configurado (Twilio Sandbox o Meta)
2. **Verificar logs** del whatsapp-gateway
3. **Verificar respuesta** del bot
4. **Revisar base de datos** para confirmar que se guardó la conversación

---

## 🏢 ARQUITECTURA MULTI-TENANT

### ¿Cómo funciona?

- **1 deployment = 3 tiendas** (Restaurant, Farmacia, Taxis)
- Cada tienda tiene su **propio número de WhatsApp**
- La base de datos usa **tenant_id** para separar datos
- El webhook identifica el tenant via query param

### Configuración de Tenants

#### Tenant 1: Restaurant
```
tenant_id: restaurant
whatsapp_number: +14155238886 (Twilio Sandbox)
webhook: /webhook/whatsapp?tenant=restaurant
```

#### Tenant 2: Farmacia
```
tenant_id: farmacia
whatsapp_number: +52XXXXXXXXXX
webhook: /webhook/meta?tenant=farmacia
```

#### Tenant 3: Taxis
```
tenant_id: taxis
whatsapp_number: +52YYYYYYYYYY
webhook: /webhook/meta?tenant=taxis
```

### Agregar Nuevo Tenant

1. **Crear configuración en base de datos:**
```sql
INSERT INTO tenants (id, name, whatsapp_number, settings)
VALUES ('nuevo_tenant', 'Nombre del Negocio', '+521234567890', '{"theme": "blue", "language": "es"}');
```

2. **Registrar número en Meta Business Platform**

3. **Configurar webhook específico:**
```
https://whatsapp-gateway-XXXXXXX.us-central1.run.app/webhook/meta?tenant=nuevo_tenant
```

---

## 🐛 TROUBLESHOOTING

### Error: VPC Connector not found

**Solución:** Crear el VPC connector (ver PASO 1 de Infraestructura)

```powershell
& "C:\Program Files (x86)\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd" compute networks vpc-access connectors create whatsapp-connector --region=us-central1 --network=default --range=10.8.0.0/28
```

### Error: Cannot connect to Redis

**Causa:** VPC connector no configurado en el deploy

**Solución:** Verificar que el script incluya `--vpc-connector=whatsapp-connector`

### Error: Cannot connect to Cloud SQL

**Causa:** Falta configurar Cloud SQL connection

**Solución:** Verificar que api-service incluya:
```powershell
--add-cloudsql-instances=restaurant-voice-system:us-central1:restaurant-db
```

### Error: Webhook not receiving messages

**Posibles causas:**
1. URL del webhook incorrecta
2. Verify token incorrecto (Meta)
3. Servicio no está corriendo

**Solución:**
```powershell
# Verificar que el servicio esté running
& "C:\Program Files (x86)\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd" run services describe whatsapp-gateway --region=us-central1

# Ver logs
& "C:\Program Files (x86)\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd" logging read "resource.type=cloud_run_revision AND resource.labels.service_name=whatsapp-gateway" --limit=50
```

### Error: Cold start too slow

**Solución:** Configurar min-instances

```powershell
# Configurar 1 instancia siempre activa (evita cold starts)
& "C:\Program Files (x86)\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd" run services update whatsapp-gateway --min-instances=1 --region=us-central1
```

**Nota:** Esto aumenta costos (~$30-50/mes por servicio)

---

## 💰 COSTOS ESTIMADOS

### Escenario: 1000 pedidos/mes por tienda (3000 total)

#### Cloud Run (Pay-per-use)

| Servicio | vCPU | RAM | Requests/mes | Costo/mes |
|----------|------|-----|--------------|-----------|
| whatsapp-gateway | 1 | 512Mi | 6000 | $8 |
| sales-agent-service | 2 | 1Gi | 3000 | $15 |
| api-service | 1 | 512Mi | 6000 | $8 |
| customer-app | 1 | 256Mi | 10000 | $3 |
| admin-panel | 1 | 256Mi | 1000 | $3 |
| **TOTAL Cloud Run** | | | | **$37/mes** |

#### Infraestructura Compartida (con Restaurant System)

| Recurso | Costo/mes | Nota |
|---------|-----------|------|
| Cloud SQL (db-f1-micro) | $10 | Compartido |
| Memorystore Redis (1GB) | $50 | Compartido |
| VPC Connector | $8 | Exclusivo para WhatsApp |
| **TOTAL Infraestructura** | **$68/mes** | |

#### Costo Total Sistema

- **Solo WhatsApp SAAS:** $37/mes (Cloud Run) + $8/mes (VPC Connector) = **$45/mes**
- **WhatsApp + Restaurant compartiendo infra:** $37/mes + $68/mes / 2 = **$71/mes**

#### Por Tenant

- **Costo por tienda:** $71/mes / 3 = **$23.67/mes por tienda**

### Optimización de Costos

1. **Usar free tier:** 2M requests/mes gratis, 360k GB-seconds/mes gratis
2. **min-instances=0:** Solo pagas por uso real (con cold start)
3. **Shared database:** 3 tenants comparten la misma DB
4. **Shared Redis:** 3 tenants comparten la misma instancia

### Escalamiento de Costos

| Pedidos/mes | Cloud Run | Infra | Total |
|-------------|-----------|-------|-------|
| 1,000 | $37 | $68 | $105 |
| 5,000 | $85 | $68 | $153 |
| 10,000 | $150 | $100 | $250 |
| 50,000 | $500 | $200 | $700 |

---

## 📝 CHECKLIST PRE-DEPLOYMENT

- [ ] VPC Connector creado
- [ ] Archivos env-vars-*.yaml verificados
- [ ] API Keys de IA validadas
- [ ] Credenciales WhatsApp configuradas
- [ ] Cloud SQL accessible
- [ ] Redis accessible
- [ ] Script deploy_to_cloud_run.ps1 actualizado

## 📝 CHECKLIST POST-DEPLOYMENT

- [ ] URLs de servicios obtenidas
- [ ] env-vars-*.yaml actualizados con URLs reales
- [ ] Servicios redesplegados con nuevas URLs
- [ ] CORS_ORIGINS actualizado
- [ ] Webhooks configurados (Twilio/Meta)
- [ ] Health checks verificados
- [ ] Prueba de flujo completo (WhatsApp → Bot → DB)
- [ ] Logs monitoreados
- [ ] Alertas configuradas (opcional)

---

## 📞 COMANDOS ÚTILES

### Ver servicios desplegados
```powershell
& "C:\Program Files (x86)\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd" run services list --platform managed --region us-central1
```

### Ver logs en tiempo real
```powershell
& "C:\Program Files (x86)\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd" logging tail "resource.type=cloud_run_revision AND resource.labels.service_name=whatsapp-gateway" --format=json
```

### Eliminar un servicio
```powershell
& "C:\Program Files (x86)\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd" run services delete SERVICIO --region us-central1 --quiet
```

### Ver métricas de uso
```powershell
& "C:\Program Files (x86)\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd" monitoring dashboards list
```

---

**Última actualización:** 2026-01-27
**Estado:** ✅ Listo para deployment
**Documentado por:** Claude Code (Anthropic)
