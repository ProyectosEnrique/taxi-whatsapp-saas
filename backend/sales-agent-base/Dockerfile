# ================================================================================
# SALES AGENT - DOCKERFILE
# ================================================================================

FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

COPY requirements-light.txt .
RUN pip install --no-cache-dir -r requirements-light.txt

COPY src/ ./src/
COPY run_v2.py .
COPY run_auto.py .

RUN mkdir -p templates static config temp logs data/learning optimization_logs conversation_archive backups
COPY templates/ ./templates/
COPY static/ ./static/
COPY config/ ./config/

ENV PYTHONUNBUFFERED=1
ENV PYTHONIOENCODING=utf-8
ENV FLASK_HOST=0.0.0.0
ENV PORT=5000

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 CMD curl -f http://localhost:5000/api/health || exit 1

CMD ["sh", "-c", "python -c 'from src.setup_auto import setup_proyecto; setup_proyecto(silent=True)' 2>/dev/null; gunicorn --bind 0.0.0.0:5000 --workers 2 --timeout 120 --preload src.api.app_v2:app"]
