# Guía de Deployment - Sistema de Taxi

Esta guía describe cómo hacer deploy del sistema completo a producción.

## Tabla de Contenidos

- [Requisitos del Servidor](#requisitos-del-servidor)
- [Configuración Inicial](#configuración-inicial)
- [Deployment con Docker Compose](#deployment-con-docker-compose)
- [Configuración de Dominio y SSL](#configuración-de-dominio-y-ssl)
- [Backup y Restauración](#backup-y-restauración)
- [Troubleshooting](#troubleshooting)
- [Monitoreo](#monitoreo)

---

## Requisitos del Servidor

### Mínimo Recomendado

- **CPU**: 2 cores
- **RAM**: 4 GB
- **Almacenamiento**: 20 GB SSD
- **Sistema Operativo**: Ubuntu 22.04 LTS o superior
- **Red**: IP pública con puertos 80 y 443 abiertos

### Software Necesario

```bash
# Docker y Docker Compose
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo apt-get install docker-compose-plugin

# Git (para actualizar código)
sudo apt-get install git

# Nginx (opcional, para proxy reverso)
sudo apt-get install nginx
```

---

## Configuración Inicial

### 1. Clonar el Repositorio

```bash
cd /opt
git clone https://github.com/tu-usuario/sistema-taxi.git
cd sistema-taxi
```

### 2. Configurar Variables de Entorno

#### Backend (.env.production)

Editar `backend/sales-agent-base/.env.production`:

```env
# Base de datos
DATABASE_URL=postgresql://postgres:TU_PASSWORD_SEGURO@db:5432/taxi_system

# Redis
REDIS_URL=redis://redis:6379/0

# Seguridad
SECRET_KEY=GENERA_UN_KEY_SEGURO_AQUI

# Twilio (WhatsApp)
TWILIO_ACCOUNT_SID=tu_twilio_sid
TWILIO_AUTH_TOKEN=tu_twilio_token
TWILIO_PHONE_NUMBER=+1234567890

# Google Maps
GOOGLE_MAPS_API_KEY=tu_google_maps_key

# Anthropic (IA)
ANTHROPIC_API_KEY=tu_anthropic_key

# Entorno
ENVIRONMENT=production
DEBUG=False
LOG_LEVEL=INFO

# CORS (ajustar con tus dominios reales)
CORS_ORIGINS=https://driver.tudominio.com,https://customer.tudominio.com,https://admin.tudominio.com
```

#### Frontends (.env.production)

**Driver App**:
```env
VITE_API_BASE_URL=https://api.tudominio.com/api/v1
VITE_TENANT_ID=tenant_taxi_001
```

**Customer App**:
```env
VITE_API_BASE_URL=https://api.tudominio.com/api/v1
VITE_GOOGLE_MAPS_KEY=tu_google_maps_key
VITE_TENANT_ID=tenant_taxi_001
```

**Admin Panel**:
```env
VITE_API_BASE_URL=https://api.tudominio.com/api/v1
VITE_TENANT_ID=tenant_taxi_001
```

### 3. Configurar Docker Compose

Crear archivo `.env` en la raíz del proyecto:

```env
DB_USER=postgres
DB_PASSWORD=TU_PASSWORD_SEGURO
```

---

## Deployment con Docker Compose

### 1. Build de las Imágenes

```bash
docker-compose -f docker-compose.prod.yml build --no-cache
```

### 2. Iniciar los Servicios

```bash
# Crear carpeta de backups
mkdir -p backups

# Iniciar servicios
docker-compose -f docker-compose.prod.yml up -d
```

### 3. Verificar el Estado

```bash
# Ver logs
docker-compose -f docker-compose.prod.yml logs -f

# Ver estado de contenedores
docker-compose -f docker-compose.prod.yml ps

# Health checks individuales
curl http://localhost/api/health
curl http://localhost/driver
curl http://localhost/customer
curl http://localhost/admin
```

### 4. Inicializar Base de Datos

```bash
# Crear tablas
docker-compose -f docker-compose.prod.yml exec backend python -c \
  "from src.models.taxi_models import create_tables; \
   from src.database.connection import get_engine; \
   create_tables(get_engine())"

# Seed data inicial (opcional)
docker-compose -f docker-compose.prod.yml exec backend python scripts/seed_data.py
```

### 5. Usar el Script Automático

```bash
# Hacer ejecutable
chmod +x scripts/deploy.sh

# Ejecutar
./scripts/deploy.sh
```

---

## Configuración de Dominio y SSL

### Opción 1: Nginx + Let's Encrypt (Recomendado)

#### 1. Instalar Certbot

```bash
sudo apt-get install certbot python3-certbot-nginx
```

#### 2. Obtener Certificados

```bash
sudo certbot --nginx -d driver.tudominio.com
sudo certbot --nginx -d customer.tudominio.com
sudo certbot --nginx -d admin.tudominio.com
sudo certbot --nginx -d api.tudominio.com
```

#### 3. Configurar Nginx

Crear `/etc/nginx/sites-available/taxi-system`:

```nginx
# Backend API
upstream backend_api {
    server localhost:8000;
}

# Frontend Apps
upstream driver_app {
    server localhost:3002;
}

upstream customer_app {
    server localhost:3004;
}

upstream admin_panel {
    server localhost:8083;
}

# Driver App
server {
    listen 443 ssl http2;
    server_name driver.tudominio.com;

    ssl_certificate /etc/letsencrypt/live/driver.tudominio.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/driver.tudominio.com/privkey.pem;

    location / {
        proxy_pass http://driver_app;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}

# Customer App
server {
    listen 443 ssl http2;
    server_name customer.tudominio.com;

    ssl_certificate /etc/letsencrypt/live/customer.tudominio.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/customer.tudominio.com/privkey.pem;

    location / {
        proxy_pass http://customer_app;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}

# Admin Panel
server {
    listen 443 ssl http2;
    server_name admin.tudominio.com;

    ssl_certificate /etc/letsencrypt/live/admin.tudominio.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/admin.tudominio.com/privkey.pem;

    location / {
        proxy_pass http://admin_panel;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}

# Backend API
server {
    listen 443 ssl http2;
    server_name api.tudominio.com;

    ssl_certificate /etc/letsencrypt/live/api.tudominio.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.tudominio.com/privkey.pem;

    location / {
        proxy_pass http://backend_api;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }
}

# HTTP to HTTPS redirect
server {
    listen 80;
    server_name driver.tudominio.com customer.tudominio.com admin.tudominio.com api.tudominio.com;
    return 301 https://$server_name$request_uri;
}
```

Activar configuración:

```bash
sudo ln -s /etc/nginx/sites-available/taxi-system /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### Opción 2: Cloudflare (Más Simple)

1. Agregar dominio a Cloudflare
2. Configurar DNS records:
   - `driver.tudominio.com` → IP del servidor
   - `customer.tudominio.com` → IP del servidor
   - `admin.tudominio.com` → IP del servidor
   - `api.tudominio.com` → IP del servidor
3. Activar SSL/TLS en modo "Full"
4. Configurar Page Rules para cache

---

## Backup y Restauración

### Backup Manual

```bash
# Backup de base de datos
docker exec taxi_db pg_dump -U postgres taxi_system > backup_$(date +%Y%m%d).sql

# Backup de volúmenes Docker
docker run --rm -v taxi_postgres_data:/data -v $(pwd):/backup alpine \
  tar czf /backup/postgres_backup_$(date +%Y%m%d).tar.gz /data
```

### Backup Automático (Cron)

```bash
# Editar crontab
crontab -e

# Agregar backup diario a las 2 AM
0 2 * * * /opt/sistema-taxi/scripts/backup.sh
```

Crear `scripts/backup.sh`:

```bash
#!/bin/bash
BACKUP_DIR="/opt/backups/taxi-system"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup DB
docker exec taxi_db pg_dump -U postgres taxi_system > $BACKUP_DIR/db_$DATE.sql

# Comprimir y mantener solo últimos 7 días
gzip $BACKUP_DIR/db_$DATE.sql
find $BACKUP_DIR -name "*.sql.gz" -mtime +7 -delete
```

### Restauración

```bash
# Restaurar base de datos
gunzip < backup_20260128.sql.gz | docker exec -i taxi_db psql -U postgres taxi_system
```

---

## Troubleshooting

### Logs

```bash
# Ver todos los logs
docker-compose -f docker-compose.prod.yml logs -f

# Logs de un servicio específico
docker-compose -f docker-compose.prod.yml logs -f backend
docker-compose -f docker-compose.prod.yml logs -f db

# Logs de nginx
sudo tail -f /var/log/nginx/error.log
sudo tail -f /var/log/nginx/access.log
```

### Problemas Comunes

#### Backend no inicia

```bash
# Verificar variables de entorno
docker-compose -f docker-compose.prod.yml config

# Verificar conexión a DB
docker-compose -f docker-compose.prod.yml exec backend python -c \
  "from src.database.connection import get_session; print(get_session())"
```

#### Frontend no carga

```bash
# Reconstruir imagen
docker-compose -f docker-compose.prod.yml build --no-cache driver_app

# Verificar variables de entorno en build
docker-compose -f docker-compose.prod.yml exec driver_app env | grep VITE
```

#### Base de datos lenta

```bash
# Ver conexiones activas
docker exec taxi_db psql -U postgres -c "SELECT * FROM pg_stat_activity;"

# Reindexar
docker exec taxi_db psql -U postgres taxi_system -c "REINDEX DATABASE taxi_system;"
```

---

## Monitoreo

### Herramientas Recomendadas

1. **Prometheus + Grafana**: Métricas de sistema
2. **Sentry**: Tracking de errores
3. **Uptime Robot**: Monitoreo de disponibilidad
4. **Google Analytics**: Estadísticas de uso

### Métricas Clave

- CPU y RAM de contenedores: `docker stats`
- Tamaño de DB: `docker exec taxi_db psql -U postgres -c "\l+"`
- Requests por segundo: Ver logs de nginx
- Errores 5xx: `grep "HTTP/1.1\" 5" /var/log/nginx/access.log | wc -l`

---

## Actualización

```bash
# 1. Pull cambios
git pull origin main

# 2. Ejecutar script de deploy
./scripts/deploy.sh
```

---

## Rollback

```bash
# Volver a versión anterior
git reset --hard HEAD~1
./scripts/deploy.sh
```

---

## Contacto y Soporte

- **Documentación**: `/docs`
- **Issues**: GitHub Issues
- **Email**: support@taxisystem.com
