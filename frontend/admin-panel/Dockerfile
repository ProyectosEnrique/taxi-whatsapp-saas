# ================================================================================
# DOCKERFILE - CUSTOMER APP (Frontend)
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
RUN npm install

# Copiar código fuente
COPY . .

# Build para producción
RUN npm run build

# ==============================================================================
# STAGE 2: Production
# ==============================================================================
FROM nginx:alpine

# Copiar archivos build
COPY --from=builder /app/dist /usr/share/nginx/html

# Copiar configuración nginx personalizada
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copiar y configurar entrypoint para Cloud Run
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Cloud Run expone el puerto dinámicamente via $PORT
ENV PORT=80

# Exponer puerto (informativo, Cloud Run usa $PORT)
EXPOSE ${PORT}

# Health check dinámico
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget --quiet --tries=1 --spider http://localhost:${PORT}/ || exit 1

# Comando de inicio con entrypoint dinámico
CMD ["/docker-entrypoint.sh"]
