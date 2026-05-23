# ============================================================================
# MAIN MULTI-TENANT - WhatsApp Gateway con Sistema Multi-Tenant
# ============================================================================

from fastapi import FastAPI, Depends, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from contextlib import asynccontextmanager
from sqlalchemy.orm import Session
import logging

# Database
from src.database import init_db, check_db_connection, get_db
from src.orm_models import RestaurantORM

# Routers
from src.auth_router import router as auth_router
from src.restaurants_router import router as restaurants_router
from src.products_router import router as products_router
from src.categories_router import router as categories_router
from src.orders_router import router as orders_router
from src.customers_router import router as customers_router

# WhatsApp
from src.whatsapp_client import WhatsAppClient
from src.demo_handler import get_demo_handler

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# WhatsApp client singleton
whatsapp_client = WhatsAppClient()


# ============================================================================
# LIFESPAN - Startup y Shutdown
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan events para startup y shutdown.
    """
    # Startup
    logger.info("Starting WhatsApp Gateway Multi-Tenant...")

    # Inicializar base de datos
    try:
        init_db()
        if check_db_connection():
            logger.info("✅ Database connection successful")
        else:
            logger.error("❌ Database connection failed")
    except Exception as e:
        logger.error(f"❌ Database initialization error: {e}")

    logger.info("✅ WhatsApp Gateway Multi-Tenant started successfully")

    yield

    # Shutdown
    logger.info("Shutting down WhatsApp Gateway Multi-Tenant...")


# ============================================================================
# CREATE APP
# ============================================================================

app = FastAPI(
    title="WhatsApp SAAS Gateway - Multi-Tenant",
    description="Sistema multi-tenant para tiendas/restaurantes con WhatsApp + Web",
    version="2.0.0",
    lifespan=lifespan
)


# ============================================================================
# CORS
# ============================================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción: ["https://tudominio.com"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# INCLUDE ROUTERS
# ============================================================================

# Auth
app.include_router(auth_router)

# Restaurants
app.include_router(restaurants_router)

# Products
app.include_router(products_router)

# Categories
app.include_router(categories_router)

# Orders
app.include_router(orders_router)

# Customers
app.include_router(customers_router)


# ============================================================================
# ROOT ENDPOINT
# ============================================================================

@app.get("/")
async def root():
    """
    Root endpoint con información del sistema.
    """
    return {
        "service": "WhatsApp SAAS Gateway - Multi-Tenant",
        "version": "2.0.0",
        "status": "running",
        "endpoints": {
            "docs": "/docs",
            "health": "/health",
            "auth": "/api/v1/auth/login",
            "restaurants": "/api/v1/restaurants"
        }
    }


# ============================================================================
# HEALTH CHECK
# ============================================================================

@app.get("/health")
async def health_check():
    """
    Health check para monitoreo.
    """
    db_status = "healthy" if check_db_connection() else "unhealthy"

    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "service": "whatsapp-gateway-multitenant",
        "database": db_status,
        "version": "2.0.0"
    }


# ============================================================================
# WHATSAPP WEBHOOK (Multi-Tenant)
# ============================================================================

@app.post("/webhook/whatsapp/{restaurant_id}")
async def whatsapp_webhook_multitenant(
    restaurant_id: str,
    Body: str = Form(...),
    From: str = Form(...),
    ProfileName: str = Form(default=""),
    MessageSid: str = Form(default=""),
    db: Session = Depends(get_db)
):
    """
    Webhook de WhatsApp para un restaurante específico.

    URL: /webhook/whatsapp/{restaurant_id}

    Soporta:
    - Tiendas demo (is_demo=TRUE): Usa demo_handler
    - Tiendas reales (is_demo=FALSE): Lógica normal de pedidos

    Parámetros de Twilio:
    - Body: Texto del mensaje
    - From: Número de WhatsApp del cliente (formato: whatsapp:+521234567890)
    - ProfileName: Nombre del perfil del cliente
    - MessageSid: ID del mensaje
    """
    try:
        # 1. Cargar configuración del restaurante desde DB
        restaurant = db.query(RestaurantORM).filter(
            RestaurantORM.restaurant_id == restaurant_id
        ).first()

        if not restaurant:
            logger.error(f"[Webhook] Restaurant not found: {restaurant_id}")
            return PlainTextResponse("Restaurant not found", status_code=404)

        if restaurant.status != "active":
            logger.warning(f"[Webhook] Restaurant not active: {restaurant_id}")
            return PlainTextResponse("Restaurant not active", status_code=403)

        # Extraer número de teléfono (remover "whatsapp:" prefix)
        phone = From.replace("whatsapp:", "")
        message_text = Body.strip()

        logger.info(
            f"[Webhook] {restaurant_id} | From: {phone} | Message: {message_text[:50]}..."
        )

        # ========================================================================
        # MODO DEMO: Usar demo_handler
        # ========================================================================
        if restaurant.is_demo:
            demo_handler = get_demo_handler()

            # 1. Verificar comandos especiales (cambiar, info, ayuda)
            is_command, response = demo_handler.handle_command(phone, message_text)
            if is_command and response:
                await whatsapp_client.send_message(phone, response)
                return PlainTextResponse("OK")

            # 2. Detectar selección de industria (1-6)
            if message_text in ["1", "2", "3", "4", "5", "6"]:
                success, response, industry = await demo_handler.select_industry(
                    phone, message_text
                )
                await whatsapp_client.send_message(phone, response)
                return PlainTextResponse("OK")

            # 3. Auto-bienvenida para nuevos prospectos o prospectos sin industria
            prospect = demo_handler.get_prospect(phone)
            if not prospect or not prospect.current_industry:
                prospect, welcome_msg = await demo_handler.handle_new_prospect(phone)
                await whatsapp_client.send_message(phone, welcome_msg)
                return PlainTextResponse("OK")

            # 4. Mensaje dentro de una industria demo
            # TODO: Implementar lógica de conversación y pedidos para demo
            # Por ahora, responder con mensaje genérico
            demo_response = f"""🎯 MODO DEMO - {restaurant.name}

Has escrito: "{message_text}"

En el sistema real, aquí procesaríamos tu pedido.

Comandos disponibles:
• *cambiar* - Explorar otro negocio
• *info* - Ver planes y precios
• *ayuda* - Ver ayuda

O prueba seleccionar productos del catálogo web
que te enviamos anteriormente."""

            await whatsapp_client.send_message(phone, demo_response)
            return PlainTextResponse("OK")

        # ========================================================================
        # MODO TIENDA REAL: Lógica de pedidos normal
        # ========================================================================
        else:
            # TODO: Implementar lógica completa de tienda real
            # - State machine de conversación
            # - Envío de catálogo
            # - Gestión de carrito
            # - Checkout
            # - Confirmación de pedido

            real_response = f"""👋 ¡Hola! Bienvenido a {restaurant.name}

Gracias por escribirnos. Estoy procesando tu mensaje.

_(Sistema en desarrollo - Próximamente disponible)_"""

            await whatsapp_client.send_message(phone, real_response)
            return PlainTextResponse("OK")

    except Exception as e:
        logger.error(f"[Webhook] Error processing message: {e}", exc_info=True)
        return PlainTextResponse("Error processing message", status_code=500)


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.exception_handler(404)
async def not_found_handler(request, exc):
    return {
        "success": False,
        "error": "Not found",
        "detail": "The requested resource was not found"
    }


@app.exception_handler(500)
async def internal_error_handler(request, exc):
    logger.error(f"Internal server error: {exc}")
    return {
        "success": False,
        "error": "Internal server error",
        "detail": "An unexpected error occurred"
    }


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main_multitenant:app",
        host="0.0.0.0",
        port=8080,
        reload=True,
        log_level="info"
    )
