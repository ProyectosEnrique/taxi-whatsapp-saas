# Build stage
FROM node:18-alpine as build

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy source code
COPY . .

# Build app
RUN npm run build

# Production stage
FROM nginx:alpine

# Copy built app to nginx
COPY --from=build /app/dist /usr/share/nginx/html

# Copy nginx config (optional, para routing con Vue Router)
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
