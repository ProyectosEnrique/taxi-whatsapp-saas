# 🚀 Guía Rápida de Deploy - 5 Minutos

Esta guía te llevará paso a paso para hacer deploy de tu sistema de taxis en producción.

---

## 📋 Pre-requisitos

- [ ] Servidor Ubuntu 22.04 con:
  - 4 GB RAM mínimo
  - 20 GB espacio
  - IP pública
  - Acceso SSH root
- [ ] Dominio comprado (opcional pero recomendado)
- [ ] Credenciales de Twilio
- [ ] API Key de Google Maps
- [ ] API Key de Anthropic/Groq

---

## 🎯 OPCIÓN 1: Deploy Rápido con Docker (Recomendado)

### Paso 1: Conectar al Servidor

```bash
# Desde tu PC
ssh root@TU_IP_SERVIDOR

# O si tienes usuario diferente
ssh usuario@TU_IP_SERVIDOR
```

### Paso 2: Instalar Docker

```bash
# Actualizar sistema
sudo apt-get update
sudo apt-get upgrade -y

# Instalar Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Instalar Docker Compose
sudo apt-get install docker-compose-plugin -y

# Verificar instalación
docker --version
docker compose version
```

### Paso 3: Clonar el Proyecto

```bash
# Ir a directorio de aplicaciones
cd /opt

# Clonar (reemplaza con tu repo)
git clone https://github.com/TU_USUARIO/sistema-taxi.git

# O subir archivos con SCP desde tu PC:
# scp -r C:\Users\ASUS\Desktop\PROYECTOS_AGENTE_VENTAS\PROYECTO_B_WHATSAPP_SAAS root@TU_IP:/opt/sistema-taxi

cd sistema-taxi
```

### Paso 4: Configurar Variables de Entorno

```bash
# Crear .env principal
nano .env
```

Pegar:
```env
DB_USER=postgres
DB_PASSWORD=TU_PASSWORD_SUPER_SEGURO
```

Guardar: `Ctrl+X`, `Y`, `Enter`

```bash
# Configurar backend
nano backend/sales-agent-base/.env.production
```

Pegar y modificar con tus datos:
```env
DATABASE_URL=postgresql://postgres:TU_PASSWORD_SUPER_SEGURO@db:5432/taxi_system
REDIS_URL=redis://redis:6379/0
SECRET_KEY=GENERA_UN_KEY_SEGURO_AQUI_CON_NUMEROS_Y_LETRAS

# Twilio
TWILIO_ACCOUNT_SID=tu_account_sid_de_twilio
TWILIO_AUTH_TOKEN=tu_auth_token_de_twilio
TWILIO_PHONE_NUMBER=+14155238886

# Google Maps
GOOGLE_MAPS_API_KEY=tu_key_de_google_maps

# IA
ANTHROPIC_API_KEY=tu_key_de_anthropic
GROQ_API_KEY=tu_key_de_groq

# Producción
ENVIRONMENT=production
DEBUG=False
LOG_LEVEL=INFO

# CORS (reemplaza con tus dominios reales, o deja localhost para pruebas)
CORS_ORIGINS=http://TU_IP:3002,http://TU_IP:3004,http://TU_IP:8083
```

Guardar: `Ctrl+X`, `Y`, `Enter`

```bash
# Configurar frontends (reemplazar TU_IP con la IP real de tu servidor)
echo "VITE_API_BASE_URL=http://TU_IP:8000/api/v1
VITE_TENANT_ID=tenant_taxi_001" > frontend/driver-app/.env.production

echo "VITE_API_BASE_URL=http://TU_IP:8000/api/v1
VITE_GOOGLE_MAPS_KEY=tu_key_de_google_maps
VITE_TENANT_ID=tenant_taxi_001" > frontend/taxi-customer-app/.env.production

echo "VITE_API_BASE_URL=http://TU_IP:8000/api/v1
VITE_TENANT_ID=tenant_taxi_001" > frontend/admin-panel/.env.production
```

### Paso 5: Deploy con Docker Compose

```bash
# Crear carpeta de backups
mkdir -p backups

# Build de imágenes (toma 5-10 minutos)
docker compose -f docker-compose.prod.yml build

# Iniciar servicios
docker compose -f docker-compose.prod.yml up -d

# Ver logs
docker compose -f docker-compose.prod.yml logs -f
```

**Espera a ver**: `✅ All taxi tables created successfully`

Presiona `Ctrl+C` para salir de los logs.

### Paso 6: Verificar que Funciona

```bash
# Health check del backend
curl http://localhost:8000/health

# Deberías ver: {"status":"healthy"}

# Ver contenedores corriendo
docker compose -f docker-compose.prod.yml ps
```

Deberías ver algo como:
```
NAME                STATUS              PORTS
taxi_db             Up 2 minutes        5432/tcp
taxi_redis          Up 2 minutes        6379/tcp
taxi_backend        Up 2 minutes        0.0.0.0:8000->8000/tcp
taxi_driver_app     Up 2 minutes        0.0.0.0:3002->80/tcp
taxi_customer_app   Up 2 minutes        0.0.0.0:3004->80/tcp
taxi_admin_panel    Up 2 minutes        0.0.0.0:8083->80/tcp
```

### Paso 7: Abrir Puertos en Firewall

```bash
# UFW (Ubuntu Firewall)
sudo ufw allow 22    # SSH
sudo ufw allow 80    # HTTP
sudo ufw allow 443   # HTTPS
sudo ufw allow 8000  # Backend API
sudo ufw allow 3002  # Driver App
sudo ufw allow 3004  # Customer App
sudo ufw allow 8083  # Admin Panel
sudo ufw enable
```

### Paso 8: Acceder desde tu Navegador

Abre en tu navegador:

- **Driver App**: http://TU_IP:3002
- **Customer App**: http://TU_IP:3004
- **Admin Panel**: http://TU_IP:8083
- **Backend API**: http://TU_IP:8000/docs (Swagger)

**Reemplaza `TU_IP` con la IP pública de tu servidor**

---

## 🎯 OPCIÓN 2: Deploy en Railway (Sin Servidor)

### Ventajas
- ✅ No necesitas servidor
- ✅ Deploy automático desde GitHub
- ✅ SSL gratis
- ✅ Subdominios gratis
- ✅ Logs y métricas incluidos

### Pasos

1. **Subir código a GitHub**
   ```bash
   cd C:\Users\ASUS\Desktop\PROYECTOS_AGENTE_VENTAS\PROYECTO_B_WHATSAPP_SAAS
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/TU_USUARIO/sistema-taxi.git
   git push -u origin main
   ```

2. **Crear cuenta en Railway**
   - Ve a https://railway.app/
   - Login con GitHub
   - Conecta tu repositorio

3. **Deploy servicios**

   Railway detectará automáticamente:
   - Backend (Python)
   - 3 Frontends (Node.js)
   - PostgreSQL (añadir desde Marketplace)
   - Redis (añadir desde Marketplace)

4. **Configurar variables de entorno**

   En cada servicio, añade las variables de `.env.production`

5. **Deploy**

   Railway hace deploy automático cuando pusheas a `main`

6. **Obtener URLs**

   Railway te dará URLs tipo:
   - `driver-app-production.up.railway.app`
   - `customer-app-production.up.railway.app`
   - `admin-panel-production.up.railway.app`
   - `backend-production.up.railway.app`

**Costo**: $5/mes (incluye todo)

---

## 🎯 OPCIÓN 3: Deploy en Render (Gratis)

### Ventajas
- ✅ Tier gratis disponible
- ✅ No necesitas servidor
- ✅ SSL gratis
- ✅ Deploy automático

### Pasos

1. **Subir a GitHub** (igual que Railway)

2. **Crear cuenta en Render**
   - Ve a https://render.com/
   - Login con GitHub

3. **Crear servicios**

   Crear 7 servicios:

   **Web Service: Backend**
   - Name: `taxi-backend`
   - Root Directory: `backend/sales-agent-base`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn run_v2:app --host 0.0.0.0 --port $PORT`
   - Instance Type: Free

   **Static Site: Driver App**
   - Name: `taxi-driver-app`
   - Root Directory: `frontend/driver-app`
   - Build Command: `npm install && npm run build`
   - Publish Directory: `dist`

   **Static Site: Customer App** (igual que driver)

   **Static Site: Admin Panel** (igual que driver)

   **PostgreSQL**
   - Crear desde Dashboard
   - Copiar URL de conexión

   **Redis**
   - Crear desde Dashboard
   - Copiar URL de conexión

4. **Variables de entorno**

   Configurar en cada servicio

5. **Deploy**

   Render hace deploy automático

**Costo**: $0 (tier gratis con limitaciones)

---

## 📊 Comparación de Opciones

| Característica | Docker (VPS) | Railway | Render Free |
|----------------|--------------|---------|-------------|
| Costo | $6/mes | $5/mes | $0 |
| Control | Total | Medio | Bajo |
| Facilidad | Media | Alta | Alta |
| Escalabilidad | Manual | Automática | Limitada |
| SSL | Manual | Automático | Automático |
| Deploy | Manual | Auto (Git) | Auto (Git) |

---

## ✅ Checklist Post-Deploy

- [ ] Todos los servicios corriendo
- [ ] Health checks pasando
- [ ] Frontend carga correctamente
- [ ] Login funciona
- [ ] Backend responde a API calls
- [ ] Base de datos tiene datos de prueba
- [ ] PWA se puede instalar
- [ ] Service Worker registrado
- [ ] SSL activo (candado verde)
- [ ] Logs configurados
- [ ] Backup automático configurado
- [ ] Dominio apuntando (si tienes)
- [ ] Cloudflare configurado (si usas)

---

## 🆘 Troubleshooting Común

### Frontend no carga
```bash
# Verificar logs
docker compose -f docker-compose.prod.yml logs driver_app

# Reconstruir
docker compose -f docker-compose.prod.yml build --no-cache driver_app
docker compose -f docker-compose.prod.yml up -d
```

### Backend da error 500
```bash
# Ver logs detallados
docker compose -f docker-compose.prod.yml logs backend

# Verificar variables de entorno
docker compose -f docker-compose.prod.yml exec backend env | grep DATABASE_URL
```

### Base de datos no conecta
```bash
# Verificar que PostgreSQL está corriendo
docker compose -f docker-compose.prod.yml ps db

# Probar conexión manual
docker compose -f docker-compose.prod.yml exec db psql -U postgres
```

### PWA no se instala
1. Verifica que tienes iconos en `public/icons/`
2. Rebuild: `npm run build`
3. Verifica manifest en Chrome DevTools

---

## 📞 Siguiente Paso

Una vez deployado, ve a **DOMAIN_SETUP.md** para configurar tu dominio personalizado.

---

## 🎉 ¡Felicidades!

Tu sistema de taxis está en producción. Ahora puedes:
- Registrar conductores
- Registrar clientes
- Probar el flujo completo
- Configurar WhatsApp
- Agregar tu logo y colores

**¿Necesitas ayuda?** Revisa `DEPLOYMENT.md` para troubleshooting avanzado.
