"""
================================================================================
MENU SERVICE - Main Application
================================================================================
Servicio de gestión de menú y productos para el sistema de restaurante
Versión: 1.0.0
================================================================================
"""

import asyncio
import logging
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram, generate_latest
from starlette.responses import Response

# Importar routers
from .routers import products, categories, agent, promotions, aliases, upload
from .routers.payments import router as payments_router, cleanup_expired_pending_payments
from .models import Trip, TripStatus, Incident
from .database import SessionLocal
from .routers.customer_rides import router as customer_router
from .routers.driver_rides import router as driver_router
from .routers.landing import router as landing_router
from .routers.locations import router as locations_router
from .routers.incidents import customer_router as incidents_customer_router
from .routers.incidents import driver_router as incidents_driver_router
from .routers.incidents import admin_router as incidents_admin_router
from .routers.admin import router as admin_router
from .routers.whatsapp import router as whatsapp_router
from .routers.telegram_bot import router as telegram_bot_router
from .database import engine, Base
from .config import settings
from fastapi.staticfiles import StaticFiles
from pathlib import Path

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

async def _dead_mans_switch():
    """
    Cada 2 minutos revisa incidentes activos sin resolver.
    Si llevan más de 5 min sin escalarse → envía alerta de escalación por Telegram.
    """
    from .services.telegram import send_to_operator
    await asyncio.sleep(30)
    while True:
        try:
            db = SessionLocal()
            cutoff = datetime.now(timezone.utc) - timedelta(minutes=5)
            pending = (
                db.query(Incident)
                .filter(
                    Incident.status == "active",
                    Incident.escalated == False,
                    Incident.created_at <= cutoff,
                )
                .all()
            )
            for inc in pending:
                maps = (
                    f"https://maps.google.com/?q={inc.last_location_lat},{inc.last_location_lng}"
                    if inc.last_location_lat else "Sin ubicación"
                )
                track = f"{settings.PUBLIC_URL}/track/{inc.incident_id}"
                tipo = "Conductor" if inc.reporter_type == "driver" else "Cliente"
                msg = (
                    f"⚠️ <b>ESCALACIÓN — SOS sin resolver</b>\n"
                    f"Han pasado +5 minutos sin respuesta.\n"
                    f"Tipo: {tipo} | {inc.reporter_name}\n"
                    f"Tel: {inc.reporter_phone}\n"
                    f"📍 <a href='{maps}'>Última ubicación</a>\n"
                    f"🔗 <a href='{track}'>Rastreo</a>\n"
                    f"⚠️ Considera llamar al {settings.EMERGENCY_PHONE}"
                )
                await send_to_operator(msg)
                inc.escalated = True
                logger.warning(f"[DeadMansSwitch] Escalado: {inc.incident_id}")
            if pending:
                db.commit()
            db.close()
        except Exception as exc:
            logger.error(f"[DeadMansSwitch] Error: {exc}")
        await asyncio.sleep(120)


async def _activate_scheduled_rides():
    """
    Cada minuto:
    - SCHEDULED + driver asignado + <= 15 min → CONFIRMED (el conductor está listo)
    - SCHEDULED + sin driver    + <= 15 min → REQUESTED (abierto al pool)
    - DRIVER_RELEASED + sin respuesta del cliente en 30 min → SCHEDULED sin driver (pool)
    """
    await asyncio.sleep(10)
    while True:
        try:
            db = SessionLocal()
            now = datetime.now(timezone.utc)
            activation_cutoff  = now + timedelta(minutes=15)
            auto_pool_cutoff   = now - timedelta(minutes=30)

            # Activar programados
            scheduled = (
                db.query(Trip)
                .filter(Trip.status == TripStatus.SCHEDULED, Trip.scheduled_at <= activation_cutoff)
                .all()
            )
            for trip in scheduled:
                if trip.driver_phone:
                    trip.status = TripStatus.CONFIRMED
                    logger.info(f"[Scheduler] {trip.trip_id} → CONFIRMED (conductor {trip.driver_name})")
                else:
                    trip.status = TripStatus.REQUESTED
                    logger.info(f"[Scheduler] {trip.trip_id} → REQUESTED (pool)")

            # Auto-reasignar viajes liberados sin respuesta del cliente
            released = (
                db.query(Trip)
                .filter(Trip.status == TripStatus.DRIVER_RELEASED, Trip.driver_released_at <= auto_pool_cutoff)
                .all()
            )
            for trip in released:
                trip.status       = TripStatus.SCHEDULED
                trip.driver_phone = None
                trip.driver_name  = None
                logger.info(f"[Scheduler] {trip.trip_id} → pool (cliente no respondió en 30 min)")

            if scheduled or released:
                db.commit()
            db.close()
        except Exception as exc:
            logger.error(f"[Scheduler] Error: {exc}")
        await asyncio.sleep(60)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manejo de eventos de inicio y cierre de la aplicación"""

    # Startup
    logger.info("================================================================================")
    logger.info(f"Starting {settings.SERVICE_NAME} v{settings.VERSION}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Database: {settings.DATABASE_URL.split('@')[1] if '@' in settings.DATABASE_URL else 'configured'}")
    logger.info("================================================================================")

    # Crear tablas si no existen
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables verified/created")

    # Migraciones en caliente
    _migrations = [
        ("trips",     "scheduled_at",                    "DATETIME"),
        ("trips",     "preferred_driver_phone",           "VARCHAR(30)"),
        ("trips",     "preferred_driver_name",            "VARCHAR(150)"),
        ("trips",     "driver_released_at",               "DATETIME"),
        # Emergency contact — customers
        ("customers", "emergency_contact_name",           "VARCHAR(150)"),
        ("customers", "emergency_contact_phone",          "VARCHAR(30)"),
        ("customers", "emergency_contact_telegram_id",    "VARCHAR(50)"),
        # Emergency contact — drivers
        ("drivers",   "emergency_contact_name",           "VARCHAR(150)"),
        ("drivers",   "emergency_contact_phone",          "VARCHAR(30)"),
        ("drivers",   "emergency_contact_telegram_id",    "VARCHAR(50)"),
        # Incident enhancements
        ("incidents", "audio_url",                        "VARCHAR(500)"),
        ("incidents", "escalated",                        "BOOLEAN DEFAULT 0"),
        ("incidents", "last_location_lat",                "NUMERIC(10,7)"),
        ("incidents", "last_location_lng",                "NUMERIC(10,7)"),
        ("incidents", "last_location_at",                 "DATETIME"),
        # Rating stored on trip row
        ("trips",     "customer_rating",                  "INTEGER"),
        # Telegram bot — propio chat_id del chofer para notificaciones y aceptar viajes
        ("drivers",   "telegram_chat_id",                 "VARCHAR(50)"),
    ]
    # Tablas nuevas (incidents, fare_config) las crea create_all automáticamente
    # Sembrar fare_config fila única si no existe
    try:
        from .models import FareConfig
        with SessionLocal() as _db:
            if not _db.query(FareConfig).filter(FareConfig.id == 1).first():
                _db.add(FareConfig(id=1))
                _db.commit()
                logger.info("fare_config: fila inicial creada")
    except Exception as _fc_err:
        logger.debug(f"fare_config seed: {_fc_err}")

    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            for table, col, col_type in _migrations:
                try:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}"))
                    conn.commit()
                    logger.info(f"Migration: {table}.{col} añadida")
                except Exception:
                    pass  # columna ya existe
    except Exception as _mig_err:
        logger.debug(f"Migration error: {_mig_err}")

    # Background tasks
    asyncio.create_task(cleanup_expired_pending_payments())
    asyncio.create_task(_activate_scheduled_rides())
    asyncio.create_task(_dead_mans_switch())

    # Registrar webhook del bot de Telegram con Telegram API
    if settings.TELEGRAM_BOT_TOKEN and settings.PUBLIC_URL:
        from .services.telegram import set_webhook
        webhook_url = f"{settings.PUBLIC_URL}/api/v1/telegram/webhook"
        asyncio.create_task(set_webhook(webhook_url, settings.TELEGRAM_WEBHOOK_SECRET))

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

app.include_router(payments_router)
app.include_router(customer_router)
app.include_router(driver_router)
app.include_router(landing_router)
app.include_router(locations_router)
app.include_router(incidents_customer_router)
app.include_router(incidents_driver_router)
app.include_router(incidents_admin_router)
app.include_router(admin_router)
app.include_router(whatsapp_router)
app.include_router(telegram_bot_router)

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
