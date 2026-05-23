# ================================================================================
# VOICE ASSISTANT - DOCKERFILE
# ================================================================================

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements-light.txt .
RUN pip install --no-cache-dir -r requirements-light.txt

# Copy application code
COPY src/ ./src/
# Copy runners (auto setup integrated)
COPY run_v2.py .
COPY run_auto.py .

# Create directories and copy optional content
RUN mkdir -p templates static config temp logs data/learning \
    optimization_logs conversation_archive backups
COPY templates/ ./templates/
COPY static/ ./static/
COPY config/ ./config/

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONIOENCODING=utf-8
ENV FLASK_HOST=0.0.0.0
# Cloud Run expone el puerto dinámicamente via $PORT
ENV PORT=5000

# Expose port (informativo, Cloud Run usa $PORT)
EXPOSE ${PORT}

# Health check dinámico
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT}/api/health || exit 1

# Run the application with automatic setup (v2.0 with FSM + Auto Setup)
# Uses run_auto.py which executes setup_proyecto() on first run
CMD ["python", "run_auto.py"]
