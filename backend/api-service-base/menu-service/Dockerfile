# ================================================================================
# DOCKERFILE - MENU SERVICE
# ================================================================================
# Multi-stage build para optimizar tamaño de imagen
# ================================================================================

# ==============================================================================
# STAGE 1: Builder
# ==============================================================================
FROM python:3.11-slim as builder

WORKDIR /app

# Instalar dependencias de sistema necesarias para compilar
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copiar solo requirements para aprovechar cache de Docker
COPY requirements.txt .

# Crear virtualenv y instalar dependencias
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ==============================================================================
# STAGE 2: Runtime
# ==============================================================================
FROM python:3.11-slim

WORKDIR /app

# Instalar solo runtime dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar virtualenv desde builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copiar código de la aplicación
COPY src/ /app/src/
RUN mkdir -p /app/config
COPY config/ /app/config/

# Copiar common (código compartido) - COMENTADO: directorio no existe
# COPY --from=builder /app/common /app/common 2>/dev/null || true

# Crear usuario no-root para seguridad
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:5011/health || exit 1

# Exponer puerto
EXPOSE 5011

# Comando por defecto (development)
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "5011", "--reload"]

# Para producción, usar (en docker-compose.prod.yml):
# CMD ["gunicorn", "src.main:app", "--workers", "4", "--worker-class", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:5011"]
