# ================================================================================
# WHATSAPP GATEWAY - Dockerfile
# ================================================================================
# Gateway para integración con WhatsApp via Twilio o Meta Cloud API
# ================================================================================

FROM python:3.11-slim

# Metadata
LABEL maintainer="Restaurant Voice System"
LABEL description="WhatsApp Gateway Service"
LABEL version="1.0.0"

# Variables de entorno
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Directorio de trabajo
WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements primero (para cache de Docker)
COPY requirements.txt .

# Instalar dependencias de Python
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copiar código fuente
COPY src/ ./src/

# Cloud Run expone el puerto dinámicamente via $PORT
ENV PORT=8000

# Puerto de la aplicación (informativo, Cloud Run usa $PORT)
EXPOSE ${PORT}

# Healthcheck dinámico
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Comando de inicio con puerto dinámico para Cloud Run
CMD exec uvicorn src.main_taxi:app --host 0.0.0.0 --port ${PORT}
