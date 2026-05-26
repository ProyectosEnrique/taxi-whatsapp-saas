# ==============================================================================
# NGINX — Multi-stage build: compila los 3 frontends y los sirve con nginx
# ==============================================================================

# ── Stage 1: Admin Panel ──────────────────────────────────────────────────────
FROM node:20-alpine AS build-admin
WORKDIR /app
COPY frontend/admin-panel/package*.json ./
RUN npm install --legacy-peer-deps
COPY frontend/admin-panel/ ./
RUN npm run build -- --base=/admin/

# ── Stage 2: Driver App ───────────────────────────────────────────────────────
FROM node:20-alpine AS build-driver
WORKDIR /app
COPY frontend/driver-app/package*.json ./
RUN npm install --legacy-peer-deps
COPY frontend/driver-app/ ./
RUN npm run build -- --base=/driver/

# ── Stage 3: Taxi Customer App ────────────────────────────────────────────────
FROM node:20-alpine AS build-customer
WORKDIR /app
COPY frontend/taxi-customer-app/package*.json ./
RUN npm install --legacy-peer-deps
COPY frontend/taxi-customer-app/ ./
RUN npm run build

# ── Stage 4: nginx ────────────────────────────────────────────────────────────
FROM nginx:alpine

# Copiar los 3 builds
COPY --from=build-admin    /app/dist /usr/share/nginx/html/admin
COPY --from=build-driver   /app/dist /usr/share/nginx/html/driver
COPY --from=build-customer /app/dist /usr/share/nginx/html/cliente

# Configuración nginx
COPY vps/nginx/nginx.conf /etc/nginx/conf.d/default.conf
RUN rm -f /etc/nginx/conf.d/default.conf.default

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
