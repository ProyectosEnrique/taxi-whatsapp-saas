# ================================================================================
# DOCKERFILE - FARMACIA PWA (Frontend)
# ================================================================================
# Multi-stage build para aplicación Vue.js 3 + Vite
# ================================================================================

# ==============================================================================
# STAGE 1: Builder
# ==============================================================================
FROM node:18-alpine AS builder

WORKDIR /app

# Copiar package files
COPY package*.json ./

# Instalar dependencias
RUN npm ci --prefer-offline --no-audit

# Asegurar permisos ejecutables en binarios
RUN chmod -R +x node_modules/.bin || true

# Copiar código fuente
COPY src ./src
COPY public ./public
COPY index.html ./
COPY vite.config.js ./
COPY tailwind.config.js ./
COPY postcss.config.js ./
COPY nginx-cloudrun.conf ./

# Build para producción
RUN npm run build && test -d dist || (echo 'ERROR: dist directory not created' && exit 1)

# ==============================================================================
# STAGE 2: Production
# ==============================================================================
FROM nginx:alpine

# Copiar archivos build
COPY --from=builder /app/dist /usr/share/nginx/html

# Copiar configuración nginx (será modificada en runtime)
COPY --from=builder /app/nginx-cloudrun.conf /etc/nginx/conf.d/default.conf.template

# Cloud Run expone el puerto dinámicamente via $PORT
ENV PORT 8080

# Exponer puerto
EXPOSE 8080

# Script simple para configurar puerto y arrancar nginx
CMD sed -i "s/listen 80;/listen $PORT;/g" /etc/nginx/conf.d/default.conf.template && \
    cp /etc/nginx/conf.d/default.conf.template /etc/nginx/conf.d/default.conf && \
    nginx -g "daemon off;"
