"""
================================================================================
MENU SERVICE - Main Application
================================================================================
Servicio de gestión de menú y productos para el sistema de restaurante
Versión: 1.0.0
================================================================================
"""

import logging
import sys
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram, generate_latest
from starlette.responses import Response

# Importar routers
from .routers import (
    products,
    categories,
    agent,
    promotions,
    aliases,
    upload,
    auth,
    orders,
    tenants,
    addresses,
    reviews,
    loyalty,
    admin_tenants,
    admin_products,
    admin_categories,
    admin_orders,
    admin_dashboard,
    admin_promotions
)
from .database import engine, Base
from .config import settings
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from .socketio_server import socket_app, sio

# ==============================================================================
# CONFIGURACIÓN DE LOGGING
# ==============================================================================

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper()),
    format='{"timestamp":"%(asctime)s","level":"%(levelname)s","service":"%(name)s","message":"%(message)s"}',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger("menu_service")

# ==============================================================================
# MÉTRICAS PROMETHEUS
# ==============================================================================

request_count = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

request_duration = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration',
    ['method', 'endpoint']
)

# ==============================================================================
# LIFESPAN - Startup/Shutdown Events
# ==============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manejo de eventos de inicio y cierre de la aplicación"""

    # Startup
    logger.info("================================================================================")
    logger.info(f"Starting {settings.SERVICE_NAME} v{settings.VERSION}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Database: {settings.DATABASE_URL.split('@')[1] if '@' in settings.DATABASE_URL else 'configured'}")
    logger.info("================================================================================")

    # Crear tablas si no existen (solo en desarrollo)
    if settings.ENVIRONMENT == "development":
        logger.info("Creating database tables (development mode)...")
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")

    yield

    # Shutdown
    logger.info("================================================================================")
    logger.info(f"Shutting down {settings.SERVICE_NAME}")
    logger.info("================================================================================")

# ==============================================================================
# APLICACIÓN FASTAPI
# ==============================================================================

app = FastAPI(
    title="Menu Service API",
    description="API para gestión de menú y productos del restaurante",
    version=settings.VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# ==============================================================================
# MIDDLEWARE
# ==============================================================================

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware para logging y métricas
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Middleware para logging de requests y métricas"""

    start_time = datetime.now()

    # Generar correlation ID si no existe
    correlation_id = request.headers.get("X-Correlation-ID", f"req-{datetime.now().timestamp()}")

    # Log de request entrante
    logger.info(
        f"Request started",
        extra={
            "correlation_id": correlation_id,
            "method": request.method,
            "path": request.url.path,
            "client_ip": request.client.host if request.client else "unknown"
        }
    )

    # Procesar request
    response = await call_next(request)

    # Calcular duración
    duration = (datetime.now() - start_time).total_seconds()

    # Actualizar métricas
    request_count.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()

    request_duration.labels(
        method=request.method,
        endpoint=request.url.path
    ).observe(duration)

    # Log de response
    logger.info(
        f"Request completed",
        extra={
            "correlation_id": correlation_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_seconds": duration
        }
    )

    # Agregar correlation ID al response
    response.headers["X-Correlation-ID"] = correlation_id

    return response

# ==============================================================================
# EXCEPTION HANDLERS
# ==============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handler global de excepciones"""

    correlation_id = request.headers.get("X-Correlation-ID", "unknown")

    logger.error(
        f"Unhandled exception: {str(exc)}",
        extra={
            "correlation_id": correlation_id,
            "exception_type": type(exc).__name__,
            "path": request.url.path
        },
        exc_info=True
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred",
            "correlation_id": correlation_id
        }
    )

# ==============================================================================
# ROUTERS
# ==============================================================================

app.include_router(
    products.router,
    prefix="/api/v1/products",
    tags=["Products"]
)

app.include_router(
    categories.router,
    prefix="/api/v1/categories",
    tags=["Categories"]
)

app.include_router(
    agent.router,
    prefix="/api/v1/agent",
    tags=["Agent"]
)

app.include_router(
    promotions.router,
    prefix="/api/v1/promotions",
    tags=["Promotions"]
)

app.include_router(
    aliases.router,
    prefix="/api/v1",
    tags=["Aliases"]
)

app.include_router(
    upload.router,
    prefix="/api/v1/upload",
    tags=["Upload"]
)

# Nuevos routers - Sistema de Ventas
app.include_router(
    auth.router,
    prefix="/api/v1/auth",
    tags=["Authentication"]
)

app.include_router(
    orders.router,
    prefix="/api/v1/orders",
    tags=["Orders"]
)

app.include_router(
    tenants.router,
    prefix="/api/v1/tenants",
    tags=["Tenants"]
)

app.include_router(
    addresses.router,
    prefix="/api/v1/addresses",
    tags=["Addresses"]
)

app.include_router(
    reviews.router,
    prefix="/api/v1/reviews",
    tags=["Reviews"]
)

app.include_router(
    loyalty.router,
    prefix="/api/v1/loyalty",
    tags=["Loyalty"]
)

# Admin routers
app.include_router(
    admin_tenants.router,
    prefix="/api/v1/admin/tenants",
    tags=["Admin - Tenants"]
)

app.include_router(
    admin_products.router,
    prefix="/api/v1/admin/products",
    tags=["Admin - Products"]
)

app.include_router(
    admin_categories.router,
    prefix="/api/v1/admin/categories",
    tags=["Admin - Categories"]
)

app.include_router(
    admin_orders.router,
    prefix="/api/v1/admin/orders",
    tags=["Admin - Orders"]
)

app.include_router(
    admin_dashboard.router,
    prefix="/api/v1/admin/dashboard",
    tags=["Admin - Dashboard"]
)

app.include_router(
    admin_promotions.router,
    prefix="/api/v1/admin/promotions",
    tags=["Admin - Promotions"]
)

# ==============================================================================
# SOCKET.IO - Real-time Communication
# ==============================================================================

# Montar aplicación Socket.IO
app.mount("/socket.io", socket_app)

logger.info("Socket.IO mounted at /socket.io")

# ==============================================================================
# ARCHIVOS ESTÁTICOS - Servir imágenes subidas
# ==============================================================================

# Crear directorio si no existe
UPLOAD_DIR = Path("/app/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Montar directorio de uploads para servir imágenes
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")

# ==============================================================================
# HEALTH CHECK
# ==============================================================================

@app.get("/health", tags=["Health"])
async def health_check():
    """Endpoint de health check"""
    return {
        "status": "healthy",
        "service": settings.SERVICE_NAME,
        "version": settings.VERSION,
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/ready", tags=["Health"])
async def readiness_check():
    """Endpoint de readiness check (verifica conexión a DB)"""
    try:
        # TODO: Verificar conexión a database
        return {
            "status": "ready",
            "service": settings.SERVICE_NAME
        }
    except Exception as e:
        logger.error(f"Readiness check failed: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "not_ready",
                "error": str(e)
            }
        )

# ==============================================================================
# METRICS ENDPOINT (Prometheus)
# ==============================================================================

@app.get("/metrics", tags=["Monitoring"])
async def metrics():
    """Endpoint de métricas para Prometheus"""
    return Response(
        generate_latest(),
        media_type="text/plain"
    )

# ==============================================================================
# ROOT ENDPOINT
# ==============================================================================

@app.get("/", tags=["Root"])
async def root():
    """Endpoint raíz con información del servicio"""
    return {
        "service": settings.SERVICE_NAME,
        "version": settings.VERSION,
        "status": "running",
        "docs": "/docs",
        "health": "/health"
    }

# ==============================================================================
# FIN DE ARCHIVO
# ==============================================================================
