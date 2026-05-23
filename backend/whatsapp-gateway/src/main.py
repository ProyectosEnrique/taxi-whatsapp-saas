"""
================================================================================
WHATSAPP GATEWAY - Main Application
================================================================================
Servicio que conecta WhatsApp Business con el Agente de Ventas IA.
Soporta Twilio y Meta Cloud API.
================================================================================
"""

from fastapi import FastAPI, Request, HTTPException, Form, Query
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import logging
import os

from .session_manager import SessionManager
from .whatsapp_client import WhatsAppClient
from .agent_connector import AgentConnector
from .message_parser import MessageParser
from .catalog import get_catalog_service
from .catalog_routes import router as catalog_router
from .admin_handler import get_admin_handler
from .payment_handler import get_payment_handler
from .loyalty_handler import get_loyalty_handler
from .loyalty_models import (
    EarnPointsRequest, RedeemPointsRequest, UpdateLoyaltyConfigRequest
)
from .demo_handler import get_demo_handler

# NUEVO: Flujo Híbrido WhatsApp ↔ Web
from .hybrid_flow_handler import HybridFlowHandler
from .hybrid_session import HybridCustomerSession

# Multi-Tenant: Detección de tiendas
from .tenant_detector import TenantDetector

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Crear aplicación
app = FastAPI(
    title="WhatsApp Gateway",
    description="Gateway para conectar WhatsApp con el Agente de Ventas IA",
    version="1.0.0"
)

# Registrar routers
app.include_router(catalog_router)

# Inicializar componentes
session_manager = SessionManager()
whatsapp_client = WhatsAppClient()
agent_connector = AgentConnector()
message_parser = MessageParser()
admin_handler = get_admin_handler()
payment_handler = get_payment_handler()
loyalty_handler = get_loyalty_handler()
demo_handler = get_demo_handler()

# NUEVO: Inicializar Flujo Híbrido (con AgentConnector para mesero virtual)
hybrid_handler = HybridFlowHandler(agent_connector=agent_connector)

# Storage temporal para sesiones híbridas (en memoria)
# TODO: Migrar a Redis para producción
hybrid_sessions: Dict[str, HybridCustomerSession] = {}


# ==============================================================================
# MODELS
# ==============================================================================

class SendMessageRequest(BaseModel):
    """Request para enviar mensaje"""
    to: str
    message: str
    buttons: Optional[List[Dict[str, str]]] = None


class WebhookResponse(BaseModel):
    """Response del webhook"""
    success: bool
    message_id: Optional[str] = None


class WebCheckoutRequest(BaseModel):
    """Request de checkout completo desde web"""
    session_token: str
    cart: List[Dict[str, Any]]
    total: float
    payment_method: str  # "cash", "card", "transfer", etc.
    payment_status: str  # "pending", "completed", "failed"
    customer_notes: Optional[str] = None
    delivery_address: Optional[str] = None
    delivery_method: str = "pickup"  # "pickup", "delivery"


# ==============================================================================
# HEALTH CHECK
# ==============================================================================

@app.get("/health")
async def health_check():
    """Health check del servicio"""
    return {
        "status": "healthy",
        "service": "whatsapp-gateway",
        "provider": os.getenv("WHATSAPP_PROVIDER", "twilio")
    }


# ==============================================================================
# TWILIO WEBHOOK
# ==============================================================================

@app.post("/webhook/twilio")
async def twilio_webhook(
    From: str = Form(...),
    To: str = Form(...),
    Body: str = Form(""),
    ProfileName: str = Form(None),
    MessageSid: str = Form(None),
    NumMedia: str = Form("0"),
    MediaUrl0: str = Form(None),
    MediaContentType0: str = Form(None)
):
    """
    Webhook que recibe mensajes de Twilio WhatsApp.

    Twilio envía los mensajes como form-urlencoded.
    Ahora soporta notas de voz (Speech-to-Text).
    """
    try:
        # Limpiar número de teléfono
        phone = From.replace("whatsapp:", "").strip()
        customer_name = ProfileName or "Cliente"

        message_text = Body

        # NUEVO: Detectar si es una nota de voz
        if int(NumMedia) > 0 and MediaUrl0 and MediaContentType0:
            if "audio" in MediaContentType0:
                logger.info(f"[Twilio] Nota de voz recibida de {phone}")
                logger.info(f"[Twilio] Media URL: {MediaUrl0}, Type: {MediaContentType0}")

                # Transcribir la nota de voz con STT
                from .stt_client import get_stt_client

                stt_client = get_stt_client()

                if stt_client.is_available:
                    # Twilio requiere autenticación para descargar media
                    twilio_sid = os.getenv("TWILIO_ACCOUNT_SID", "")
                    twilio_token = os.getenv("TWILIO_AUTH_TOKEN", "")
                    auth = (twilio_sid, twilio_token) if twilio_sid and twilio_token else None

                    # Transcribir
                    transcribed_text = await stt_client.transcribe_audio_url(MediaUrl0, auth=auth)

                    if transcribed_text:
                        logger.info(f"[STT] Transcripción exitosa: '{transcribed_text}'")
                        message_text = transcribed_text
                    else:
                        logger.warning("[STT] No se pudo transcribir, usando fallback")
                        message_text = "Lo siento, no pude escuchar tu nota de voz. ¿Puedes escribir tu pedido?"
                else:
                    logger.warning("[STT] STT no disponible (falta DEEPGRAM_API_KEY)")
                    message_text = "Recibí tu nota de voz, pero no tengo habilitada la transcripción. Por favor escribe tu pedido."

        logger.info(f"[Twilio] Mensaje de {phone}: {message_text}")

        # ======================================================================
        # MODO DEMO: Detectar si es un prospecto demo
        # ======================================================================

        # 1. Manejar comandos especiales de demo (cambiar, info, ayuda)
        is_demo_command, demo_response = demo_handler.handle_command(phone, message_text)
        if is_demo_command and demo_response:
            await whatsapp_client.send_message(to=phone, message=demo_response)
            return PlainTextResponse(
                content="<?xml version='1.0' encoding='UTF-8'?><Response></Response>",
                media_type="application/xml"
            )

        # 2. Detectar selección de industria (números 1-6)
        if message_text.strip() in ["1", "2", "3", "4", "5", "6"]:
            success, demo_message, industry = await demo_handler.select_industry(phone, message_text)
            if success:
                await whatsapp_client.send_message(to=phone, message=demo_message)
                return PlainTextResponse(
                    content="<?xml version='1.0' encoding='UTF-8'?><Response></Response>",
                    media_type="application/xml"
                )

        # 3. Verificar si es prospecto nuevo (auto-bienvenida)
        # DESACTIVADO: Sistema demo interactivo - Ahora siempre usa restaurante
        # prospect = demo_handler.get_prospect(phone)
        # if not prospect:
        #     # Nuevo prospecto, enviar bienvenida
        #     prospect, welcome_msg = await demo_handler.handle_new_prospect(phone)
        #     await whatsapp_client.send_message(to=phone, message=welcome_msg)
        #     return PlainTextResponse(
        #         content="<?xml version='1.0' encoding='UTF-8'?><Response></Response>",
        #         media_type="application/xml"
        #     )

        # ======================================================================
        # MULTI-TENANT: Detectar tenant (tienda)
        # ======================================================================
        tenant_id = None

        # DESACTIVADO: Ya no usamos el sistema de industrias demo
        # Si el prospecto ya eligió una industria demo, usar esa
        # if prospect and prospect.current_industry:
        #     tenant_id = prospect.current_industry.value
        #     logger.info(f"[Demo] Usando industria demo: {tenant_id}")

        # 1. Intentar detectar por número de WhatsApp receptor (producción solo si no es demo)
        if not tenant_id:
            tenant_id = TenantDetector.detect_from_phone(To)

        # 2. Si no se detectó (sandbox), detectar por palabra clave
        if not tenant_id:
            tenant_id = TenantDetector.detect_from_message(message_text)

            if tenant_id:
                # Limpiar mensaje (quitar palabra clave)
                message_text = TenantDetector.extract_clean_message(message_text, tenant_id)
                logger.info(f"[Tenant] Detectado '{tenant_id}' por keyword, mensaje limpio: '{message_text}'")

        # 3. Si aún no se detectó, buscar en sesión existente
        if not tenant_id:
            # Verificar si ya existe una sesión con tenant asignado
            tenant_id = get_tenant_from_existing_session(phone)
            if tenant_id:
                logger.info(f"[Tenant] Recuperado de sesión existente: '{tenant_id}'")

        # 4. Si aún no hay tenant, usar Rico Mar por defecto
        if not tenant_id:
            tenant_id = "rico-mar-salvatierra"
            logger.info(f"[Tenant] Usando tenant por defecto: '{tenant_id}'")

        # Procesar el mensaje (ahora puede ser texto original o transcrito)
        response = await process_incoming_message(
            phone=phone,
            message=message_text,
            customer_name=customer_name,
            provider="twilio",
            tenant_id=tenant_id  # NUEVO: Pasar tenant_id
        )

        # Enviar respuesta por WhatsApp (con soporte para imágenes)
        if response.get("image"):
            # Enviar imagen con caption
            img = response["image"]
            await whatsapp_client.send_message(
                to=phone,
                message=img.get("caption", response["text"]),
                image_url=img.get("url")
            )
        else:
            # Enviar texto con botones opcionales
            await whatsapp_client.send_message(
                to=phone,
                message=response["text"],
                buttons=response.get("buttons")
            )

        # Twilio espera TwiML vacío si manejamos la respuesta nosotros
        return PlainTextResponse(
            content="<?xml version='1.0' encoding='UTF-8'?><Response></Response>",
            media_type="application/xml"
        )

    except Exception as e:
        logger.error(f"[Twilio] Error procesando mensaje: {e}")
        return PlainTextResponse(
            content="<?xml version='1.0' encoding='UTF-8'?><Response></Response>",
            media_type="application/xml"
        )


# ==============================================================================
# META CLOUD API WEBHOOK
# ==============================================================================

@app.get("/webhook/meta")
async def meta_webhook_verify(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token")
):
    """
    Verificación del webhook de Meta.
    Meta envía una solicitud GET para verificar el endpoint.
    """
    verify_token = os.getenv("META_VERIFY_TOKEN", "mi_token_secreto")

    if hub_mode == "subscribe" and hub_verify_token == verify_token:
        logger.info("[Meta] Webhook verificado exitosamente")
        return PlainTextResponse(content=hub_challenge)

    raise HTTPException(status_code=403, detail="Verification failed")


@app.post("/webhook/meta")
async def meta_webhook(request: Request):
    """
    Webhook que recibe mensajes de Meta Cloud API.
    """
    try:
        body = await request.json()
        logger.info(f"[Meta] Webhook recibido: {body}")

        # Extraer datos del mensaje
        entry = body.get("entry", [{}])[0]
        changes = entry.get("changes", [{}])[0]
        value = changes.get("value", {})
        messages = value.get("messages", [])

        for message in messages:
            phone = message.get("from")
            message_type = message.get("type")

            # Obtener nombre del contacto
            contacts = value.get("contacts", [{}])
            customer_name = contacts[0].get("profile", {}).get("name", "Cliente") if contacts else "Cliente"

            # NUEVO: Manejar órdenes del carrito nativo de WhatsApp
            if message_type == "order":
                order_data = message.get("order", {})
                await process_cart_order(phone, order_data, customer_name)
                continue

            # Extraer texto del mensaje
            if message_type == "text":
                text = message.get("text", {}).get("body", "")
            elif message_type == "interactive":
                # Respuesta a botones o lista
                interactive = message.get("interactive", {})
                if interactive.get("type") == "button_reply":
                    text = interactive.get("button_reply", {}).get("title", "")
                elif interactive.get("type") == "list_reply":
                    text = interactive.get("list_reply", {}).get("title", "")
                elif interactive.get("type") == "product_list_reply":
                    # Respuesta de Multi-Product Message
                    text = interactive.get("product_list_reply", {}).get("product_retailer_id", "")
                else:
                    text = ""
            else:
                logger.info(f"[Meta] Tipo de mensaje no soportado: {message_type}")
                continue

            if not text:
                continue

            logger.info(f"[Meta] Mensaje de {phone}: {text}")

            # MULTI-TENANT: Detectar tenant (tienda)
            tenant_id = None

            # 1. Detectar por palabra clave
            tenant_id = TenantDetector.detect_from_message(text)

            if tenant_id:
                # Limpiar mensaje (quitar palabra clave)
                text = TenantDetector.extract_clean_message(text, tenant_id)
                logger.info(f"[Tenant] Detectado '{tenant_id}' por keyword, mensaje limpio: '{text}'")

            # 2. Si no se detectó, buscar en sesión existente
            if not tenant_id:
                tenant_id = get_tenant_from_existing_session(phone)
                if tenant_id:
                    logger.info(f"[Tenant] Recuperado de sesión existente: '{tenant_id}'")

            # 3. Si aún no hay tenant, usar Rico Mar por defecto
            if not tenant_id:
                tenant_id = "rico-mar-salvatierra"
                logger.info(f"[Tenant] Usando tenant por defecto: '{tenant_id}'")

            # Procesar el mensaje
            response = await process_incoming_message(
                phone=phone,
                message=text,
                customer_name=customer_name,
                provider="meta",
                tenant_id=tenant_id  # NUEVO: Pasar tenant_id
            )

            # Enviar respuesta apropiada según tipo
            await send_appropriate_response(phone, response)

        return {"status": "ok"}

    except Exception as e:
        logger.error(f"[Meta] Error procesando webhook: {e}")
        return {"status": "error", "message": str(e)}


# ==============================================================================
# HELPER FUNCTIONS - HYBRID SESSIONS
# ==============================================================================

def get_tenant_from_existing_session(phone: str) -> Optional[str]:
    """
    Buscar tenant_id de la sesión más reciente para un teléfono.

    Útil cuando el usuario envía un mensaje sin contexto y queremos
    continuar con la última tienda/industria que estaba explorando.
    """
    for session_key, session in hybrid_sessions.items():
        if session_key.startswith(f"{phone}_"):
            return session.restaurant_id
    return None


async def get_hybrid_session(phone: str, customer_name: str = "Cliente", tenant_id: str = "default") -> HybridCustomerSession:
    """
    Obtener o crear sesión híbrida.

    IMPORTANTE: Cada combinación phone+tenant_id tiene su propia sesión aislada.
    Esto permite que un mismo usuario explore múltiples demos/tiendas sin mezclar contextos.

    Args:
        phone: Número de teléfono del cliente
        customer_name: Nombre del cliente
        tenant_id: ID del tenant/tienda (ej: "demo_restaurant", "demo_pharmacy")
    """
    # Clave única: phone + tenant_id
    session_key = f"{phone}_{tenant_id}"

    if session_key not in hybrid_sessions:
        hybrid_sessions[session_key] = HybridCustomerSession(
            phone=phone,
            customer_name=customer_name,
            restaurant_id=tenant_id  # Asignar tenant_id desde el inicio
        )
        logger.info(f"[HybridSession] Nueva sesión creada: {phone} | Tenant: {tenant_id}")
    else:
        # Refrescar TTL
        hybrid_sessions[session_key].refresh_ttl()

    return hybrid_sessions[session_key]


async def save_hybrid_session(session: HybridCustomerSession):
    """Guardar sesión híbrida usando phone + tenant_id como clave"""
    session_key = f"{session.phone}_{session.restaurant_id or 'default'}"
    hybrid_sessions[session_key] = session
    logger.info(f"[HybridSession] Sesión guardada: {session.phone} | Tenant: {session.restaurant_id}")


def format_hybrid_response(message, provider: str) -> Dict[str, Any]:
    """
    Convertir WhatsAppMessage del hybrid handler al formato esperado.

    Args:
        message: WhatsAppMessage del hybrid handler
        provider: 'twilio' o 'meta'

    Returns:
        Dict con formato compatible con el sistema actual
    """
    response = {
        "text": message.text,
        "buttons": None,
        "list": None,
        "image": None
    }

    # Convertir botones si existen
    if message.buttons:
        if provider == "meta":
            # Meta formato: lista de objetos InteractiveButton
            response["buttons"] = [
                {"id": btn.id, "title": btn.title}
                for btn in message.buttons
            ]
        else:
            # Twilio formato similar
            response["buttons"] = [
                {"id": btn.id, "title": btn.title}
                for btn in message.buttons
            ]

    # Si hay URL button, agregar al texto (workaround)
    if message.url_button:
        button_text = message.url_button["text"]
        url = message.url_button["url"]
        response["text"] += f"\n\n👉 *{button_text}:*\n{url}"

    return response


# ==============================================================================
# PROCESAMIENTO DE MENSAJES
# ==============================================================================

async def process_incoming_message(
    phone: str,
    message: str,
    customer_name: str = "Cliente",
    provider: str = "twilio",
    tenant_id: str = "default"  # NUEVO: tenant_id
) -> Dict[str, Any]:
    """
    Procesa un mensaje entrante y genera la respuesta.

    Detecta si el mensaje viene de un administrador o cliente
    y rutea al handler apropiado:
    - Admin → AdminHandler → AdminAgent
    - Cliente → AgentConnector → SalesAgent

    Returns:
        Respuesta formateada para WhatsApp
    """
    try:
        # NUEVO: Detectar si es administrador
        if admin_handler.is_admin(phone):
            logger.info(f"[Gateway] Mensaje de ADMIN detectado: {phone}")

            # Rutear al AdminHandler
            admin_response = await admin_handler.process_admin_message(
                phone=phone,
                message=message,
                customer_name=customer_name
            )

            if not admin_response.get("success"):
                # Error en AdminHandler, retornar mensaje de error
                return {
                    "text": admin_response.get("text", "Error procesando solicitud de admin"),
                    "buttons": None
                }

            # Retornar respuesta del admin
            return {
                "text": admin_response.get("text"),
                "buttons": admin_response.get("buttons")
            }

        # FLUJO HÍBRIDO: Procesar como cliente con detección inteligente
        logger.info(f"[Gateway] Mensaje de CLIENTE: {phone} | Tenant: {tenant_id}")

        # 1. Obtener o crear sesión híbrida (con tenant_id para aislar contextos)
        hybrid_session = await get_hybrid_session(phone, customer_name, tenant_id)

        # 2. Procesar mensaje con el hybrid handler
        response_message, updated_session = await hybrid_handler.process_message(
            session=hybrid_session,
            message=message
        )

        # 3. Guardar sesión actualizada
        await save_hybrid_session(updated_session)

        logger.info(
            f"[Gateway] Procesado - Intent: {updated_session.current_intent}, "
            f"Messages: {updated_session.message_count}, "
            f"Cart: {len(updated_session.cart)} items"
        )

        # 4. Formatear respuesta según provider
        return format_hybrid_response(response_message, provider)

    except Exception as e:
        logger.error(f"[Gateway] Error procesando mensaje: {e}")
        return {
            "text": "Disculpa, tuve un problema. ¿Podrías repetir tu mensaje?"
        }


# ==============================================================================
# CARRITO NATIVO DE WHATSAPP
# ==============================================================================

async def process_cart_order(
    phone: str,
    order_data: Dict[str, Any],
    customer_name: str = "Cliente"
):
    """
    Procesa un pedido del carrito nativo de WhatsApp.

    Cuando el cliente usa Multi-Product Messages y agrega productos al carrito,
    WhatsApp envia un mensaje tipo "order" con los productos seleccionados.

    Args:
        phone: Numero de telefono del cliente
        order_data: Datos del pedido de WhatsApp
            - catalog_id: ID del catalogo
            - product_items: Lista de productos
                - product_retailer_id: ID del producto
                - quantity: Cantidad
                - item_price: Precio unitario
                - currency: Moneda
        customer_name: Nombre del cliente
    """
    try:
        product_items = order_data.get("product_items", [])

        if not product_items:
            logger.warning(f"[Cart] Orden vacia de {phone}")
            await whatsapp_client.send_message(
                to=phone,
                message="No encontre productos en tu carrito. ¿Te gustaria ver el menu?"
            )
            return

        logger.info(f"[Cart] Procesando orden de {phone}: {len(product_items)} productos")

        # Obtener o crear sesion
        session = await session_manager.get_or_create_session(
            phone=phone,
            customer_name=customer_name
        )

        # Construir lista de items para el carrito de la sesion
        cart_items = []
        order_summary = []
        total = 0.0

        for item in product_items:
            retailer_id = item.get("product_retailer_id", "")
            quantity = int(item.get("quantity", 1))
            item_price = float(item.get("item_price", 0))
            currency = item.get("currency", "MXN")

            # Obtener nombre del producto (por ahora usar retailer_id)
            product_name = retailer_id.replace("product_", "").replace("_", " ").title()

            cart_items.append({
                "product_retailer_id": retailer_id,
                "name": product_name,
                "quantity": quantity,
                "price": item_price,
                "currency": currency
            })

            subtotal = item_price * quantity
            total += subtotal
            order_summary.append(f"• {quantity}x {product_name} - ${subtotal:.2f}")

        # Actualizar carrito en sesion
        session.cart = cart_items
        session.state = "confirming"
        await session_manager.update_session(session)

        # Construir mensaje de confirmacion
        summary_text = "\n".join(order_summary)
        confirmation_message = (
            f"He recibido tu pedido:\n\n"
            f"{summary_text}\n\n"
            f"*Total: ${total:.2f} {currency}*\n\n"
            f"¿Confirmas tu pedido?"
        )

        # Enviar mensaje de confirmacion con botones
        await whatsapp_client.send_message(
            to=phone,
            message=confirmation_message,
            buttons=[
                {"id": "confirm_order", "title": "Confirmar"},
                {"id": "modify_order", "title": "Modificar"},
                {"id": "cancel_order", "title": "Cancelar"}
            ]
        )

        logger.info(f"[Cart] Confirmacion enviada a {phone}, total: ${total:.2f}")

    except Exception as e:
        logger.error(f"[Cart] Error procesando orden: {e}")
        await whatsapp_client.send_message(
            to=phone,
            message="Tuve un problema procesando tu pedido. ¿Podrias intentar de nuevo?"
        )


async def send_appropriate_response(phone: str, response: Dict[str, Any]):
    """
    Envia la respuesta apropiada segun el tipo de contenido.

    Prioridad:
    1. Multi-Product Message (si hay catalogo y productos)
    2. Single Product Message (para recomendaciones)
    3. Imagen con caption
    4. Lista interactiva
    5. Botones
    6. Mensaje de texto simple

    Args:
        phone: Numero de telefono del destinatario
        response: Respuesta del agente con posibles campos:
            - text: Texto del mensaje
            - multi_product: Datos para Multi-Product Message
            - single_product: Datos para Single Product Message
            - image: Datos de imagen
            - list: Datos de lista interactiva
            - buttons: Botones interactivos
    """
    try:
        text = response.get("text", "")

        # 1. Multi-Product Message
        if response.get("multi_product") and whatsapp_client.has_catalog:
            mpm = response["multi_product"]
            result = await whatsapp_client.send_multi_product_message(
                to=phone,
                header_text=mpm.get("header", "Nuestro Menu"),
                body_text=mpm.get("body", text),
                sections=mpm.get("sections", [])
            )
            if result.get("success"):
                logger.info(f"[Response] MPM enviado a {phone}")
                return

        # 2. Single Product Message
        if response.get("single_product") and whatsapp_client.has_catalog:
            spm = response["single_product"]
            result = await whatsapp_client.send_single_product_message(
                to=phone,
                body_text=spm.get("body", text),
                product_retailer_id=spm.get("product_retailer_id", "")
            )
            if result.get("success"):
                logger.info(f"[Response] SPM enviado a {phone}")
                return

        # 3. Imagen con caption
        if response.get("image"):
            img = response["image"]
            result = await whatsapp_client.send_image(
                to=phone,
                image_url=img.get("url", ""),
                caption=img.get("caption", text)
            )
            if result.get("success"):
                logger.info(f"[Response] Imagen enviada a {phone}")
                return

        # 4. Lista interactiva
        if response.get("list"):
            await whatsapp_client.send_list(
                to=phone,
                message=text,
                sections=response["list"]
            )
            logger.info(f"[Response] Lista enviada a {phone}")
            return

        # 5. Botones
        if response.get("buttons"):
            await whatsapp_client.send_message(
                to=phone,
                message=text,
                buttons=response["buttons"]
            )
            logger.info(f"[Response] Botones enviados a {phone}")
            return

        # 6. Mensaje simple
        await whatsapp_client.send_message(to=phone, message=text)
        logger.info(f"[Response] Texto enviado a {phone}")

    except Exception as e:
        logger.error(f"[Response] Error enviando respuesta: {e}")
        # Fallback a mensaje simple
        await whatsapp_client.send_message(
            to=phone,
            message=response.get("text", "Lo siento, ocurrio un error.")
        )


# ==============================================================================
# API INTERNA
# ==============================================================================

@app.post("/api/send")
async def send_message(request: SendMessageRequest):
    """
    Endpoint interno para enviar mensajes.
    Usado por otros servicios (notificaciones, alertas).
    """
    try:
        result = await whatsapp_client.send_message(
            to=request.to,
            message=request.message,
            buttons=request.buttons
        )

        return {"success": True, "message_id": result.get("message_id")}

    except Exception as e:
        logger.error(f"Error enviando mensaje: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sessions/{phone}")
async def get_session(phone: str):
    """Obtener sesión activa de un cliente"""
    session = await session_manager.get_session(phone)

    if not session:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")

    return {
        "session_id": session.session_id,
        "phone": session.phone,
        "state": session.state,
        "table_id": session.table_id,
        "restaurant_id": session.restaurant_id,
        "cart": session.cart,
        "created_at": session.created_at.isoformat()
    }


@app.delete("/api/sessions/{phone}")
async def delete_session(phone: str):
    """Eliminar sesión de un cliente"""
    await session_manager.delete_session(phone)
    return {"success": True}


# ==============================================================================
# API - WEB RETURN (FLUJO HÍBRIDO)
# ==============================================================================

class WebReturnRequest(BaseModel):
    """Request cuando usuario regresa desde web"""
    session_token: str
    cart: List[Dict[str, Any]]
    total: float


@app.post("/api/v1/web-return")
async def handle_web_return(request: WebReturnRequest):
    """
    Endpoint que la Customer App llama cuando el usuario
    termina de armar su pedido en web y quiere volver a WhatsApp.

    Flow:
    1. Verificar token de sesión
    2. Recuperar sesión híbrida
    3. Sincronizar carrito desde web
    4. Enviar mensaje de bienvenida de regreso
    5. Usuario confirma en WhatsApp
    """
    try:
        # 1. Verificar token
        token_data = hybrid_handler.url_generator.verify_session_token(
            request.session_token
        )

        if not token_data:
            raise HTTPException(
                status_code=400,
                detail="Token inválido o expirado"
            )

        session_id = token_data["session_id"]
        logger.info(f"[WebReturn] Token válido: {session_id}")

        # 2. Buscar sesión por session_id
        session = None
        for session_key, sess in hybrid_sessions.items():
            if sess.session_id == session_id:
                session = sess
                break

        if not session:
            raise HTTPException(
                status_code=404,
                detail="Sesión no encontrada"
            )

        logger.info(f"[WebReturn] Sesión encontrada: {session.phone}")

        # 3. Procesar retorno desde web
        welcome_msg, updated_session = await hybrid_handler.handle_return_from_web(
            session=session,
            web_cart=request.cart,
            total=request.total
        )

        # 4. Guardar sesión actualizada
        await save_hybrid_session(updated_session)

        # 5. Enviar mensaje de bienvenida por WhatsApp
        provider = os.getenv("WHATSAPP_PROVIDER", "twilio")
        response_data = format_hybrid_response(welcome_msg, provider)

        await whatsapp_client.send_message(
            to=session.phone,
            message=response_data["text"],
            buttons=response_data.get("buttons")
        )

        logger.info(f"[WebReturn] Mensaje de bienvenida enviado a {session.phone}")

        return {
            "success": True,
            "message": "Usuario re-enganchado en WhatsApp",
            "phone": session.phone
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[WebReturn] Error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error procesando retorno: {str(e)}"
        )


# ==============================================================================
# API ENDPOINTS - INTEGRACION CATALOGO
# ==============================================================================

@app.get("/api/v1/session/{session_token}")
async def get_session_data(session_token: str):
    """
    Obtener datos de sesión actual con carrito.

    Returns:
        {
            "session_id": "abc123",
            "phone": "+525512345678",
            "customer_name": "Juan Pérez",
            "restaurant_id": "carniceria",
            "cart": [...],
            "cart_total": 360.00
        }
    """
    try:
        # Verificar token
        token_data = hybrid_handler.url_generator.verify_session_token(session_token)
        if not token_data:
            raise HTTPException(
                status_code=401,
                detail="Token de sesión inválido o expirado"
            )

        session_id = token_data["session_id"]
        logger.info(f"[SessionAPI] Token verificado: {session_id}")

        # Buscar sesión
        session = None
        for session_key, sess in hybrid_sessions.items():
            if sess.session_id == session_id:
                session = sess
                break

        if not session:
            raise HTTPException(
                status_code=404,
                detail="Sesión no encontrada"
            )

        logger.info(f"[SessionAPI] Sesión encontrada: {session.phone} - Cart: {len(session.cart)} items")

        return {
            "success": True,
            "session_id": session.session_id,
            "phone": session.phone,
            "customer_name": session.customer_name,
            "restaurant_id": session.restaurant_id,
            "cart": session.cart,
            "cart_total": session.cart_total
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[SessionAPI] Error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo sesión: {str(e)}"
        )


@app.get("/api/v1/restaurants/{restaurant_id}/menu")
async def get_restaurant_menu(restaurant_id: str, category: Optional[str] = None):
    """
    Obtener menú completo de un restaurante/tienda desde el menu-service.
    Si es una tienda DEMO, sirve catálogo desde demo_config.

    Returns:
        {
            "restaurant_id": "carniceria",
            "restaurant_name": "Carnicería Premium",
            "categories": [...],
            "products": [...]
        }
    """
    try:
        logger.info(f"[MenuAPI] Obteniendo menú de {restaurant_id}")

        # ==================================================================
        # DETECTAR SI ES UNA TIENDA DEMO
        # ==================================================================
        if restaurant_id.startswith("demo_"):
            from .demo_config import get_demo_catalog, DemoIndustry

            try:
                industry = DemoIndustry(restaurant_id)
                catalog = get_demo_catalog(industry)

                # Filtrar por categoría si se especifica
                products = catalog["products"]
                if category:
                    products = [p for p in products if p["category"] == category]

                logger.info(f"[MenuAPI] Sirviendo catálogo DEMO: {catalog['name']}")

                return {
                    "success": True,
                    "restaurant_id": restaurant_id,
                    "restaurant_name": catalog["name"],
                    "description": catalog["description"],
                    "categories": catalog["categories"],
                    "products": products,
                    "is_demo": True
                }
            except ValueError:
                logger.warning(f"[MenuAPI] Demo inválido: {restaurant_id}")

        # ==================================================================
        # FLUJO NORMAL: Consultar menu-service
        # ==================================================================
        menu_service_url = os.getenv("MENU_SERVICE_URL", "http://menu-service:8001")
        params = {}
        if category:
            params["category"] = category

        import aiohttp

        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{menu_service_url}/api/v1/restaurants/{restaurant_id}/menu",
                params=params
            ) as response:
                if response.status == 404:
                    return {
                        "success": True,
                        "restaurant_id": restaurant_id,
                        "restaurant_name": restaurant_id.title(),
                        "categories": [],
                        "products": []
                    }

                if response.status != 200:
                    raise Exception(f"Menu service error: {response.status}")

                data = await response.json()

                logger.info(f"[MenuAPI] Retornando {len(data.get('products', []))} productos")

                return {
                    "success": True,
                    "restaurant_id": restaurant_id,
                    "restaurant_name": data.get("restaurant_name", restaurant_id.title()),
                    "categories": data.get("categories", []),
                    "products": data.get("products", [])
                }

    except Exception as e:
        logger.error(f"[MenuAPI] Error: {e}")
        raise HTTPException(status_code=500, detail=f"Error cargando menú: {str(e)}")


@app.post("/api/v1/web-checkout")
async def handle_web_checkout(request: WebCheckoutRequest):
    """
    Endpoint para CHECKOUT COMPLETO desde web.
    El cliente completa TODO en la web y NO regresa a WhatsApp.
    """
    try:
        logger.info(f"[WebCheckout] Recibido - Total: ${request.total}")

        # Verificar token
        token_data = hybrid_handler.url_generator.verify_session_token(request.session_token)
        if not token_data:
            raise HTTPException(status_code=400, detail="Token inválido")

        session_id = token_data["session_id"]

        # Buscar sesión
        session = None
        for session_key, sess in hybrid_sessions.items():
            if sess.session_id == session_id:
                session = sess
                break

        if not session:
            raise HTTPException(status_code=404, detail="Sesión no encontrada")

        # Actualizar sesión
        session.cart = request.cart
        session.cart_total = request.total

        # Crear orden
        order_id = f"WEB-{session_id[:8]}"
        logger.info(f"[WebCheckout] Orden creada: {order_id}")

        # NUEVO: Otorgar puntos de fidelidad automáticamente
        loyalty_result = None
        if request.payment_status == "completed" or request.payment_method in ["cash", "transfer"]:
            try:
                earn_request = EarnPointsRequest(
                    customer_phone=session.phone,
                    restaurant_id=session.restaurant_id,
                    order_id=order_id,
                    order_total=request.total,
                    customer_name=session.customer_name
                )
                loyalty_result = await loyalty_handler.earn_points(earn_request)
                logger.info(f"[WebCheckout] Puntos otorgados: {loyalty_result.get('points_earned', 0)}")
            except Exception as e:
                logger.error(f"[WebCheckout] Error otorgando puntos: {e}")
                # No fallar el checkout si falla loyalty

        # Enviar confirmación por WhatsApp
        confirmation_message = _build_order_confirmation_message(
            order_id=order_id,
            cart=request.cart,
            total=request.total,
            payment_method=request.payment_method,
            payment_status=request.payment_status,
            delivery_method=request.delivery_method,
            delivery_address=request.delivery_address,
            loyalty_result=loyalty_result,
            restaurant_id=session.restaurant_id  # Para detectar modo demo
        )

        await whatsapp_client.send_message(to=session.phone, message=confirmation_message)
        logger.info(f"[WebCheckout] Confirmación enviada a {session.phone}")

        # DEMO: Marcar checkout completado
        if session.restaurant_id and session.restaurant_id.startswith("demo_"):
            demo_handler.mark_checkout_completed(session.phone)

        await save_hybrid_session(session)

        return {
            "success": True,
            "order_id": order_id,
            "message": "Pedido procesado exitosamente",
            "phone": session.phone,
            "loyalty": loyalty_result
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[WebCheckout] Error: {e}")
        raise HTTPException(status_code=500, detail=f"Error procesando checkout: {str(e)}")


def _build_order_confirmation_message(
    order_id: str,
    cart: List[Dict[str, Any]],
    total: float,
    payment_method: str,
    payment_status: str,
    delivery_method: str,
    delivery_address: Optional[str] = None,
    loyalty_result: Optional[Dict[str, Any]] = None,
    restaurant_id: Optional[str] = None
) -> str:
    """Construir mensaje de confirmación de pedido"""

    # Detectar si es MODO DEMO
    is_demo = restaurant_id and restaurant_id.startswith("demo_")

    if payment_status == "completed":
        message = f"🎉 *¡Pedido Confirmado!*\n\n"
        message += f"📋 Orden: #{order_id}\n"
        message += f"✅ Pago: {payment_method.upper()} - Aprobado\n\n"
    else:
        message = f"📝 *Pedido Recibido*\n\n"
        message += f"📋 Orden: #{order_id}\n"
        message += f"⏳ Pago: {payment_method.upper()} - Pendiente\n\n"

    message += "*Tu pedido:*\n"
    for item in cart:
        name = item.get("name", "Producto")
        quantity = item.get("quantity", 1)
        price = item.get("price", 0)
        subtotal = quantity * price
        message += f"• {quantity}x {name} - ${subtotal:.2f}\n"
        if item.get("notes"):
            message += f"  _{item['notes']}_\n"

    message += f"\n💰 *Total: ${total:.2f}*\n\n"

    # NUEVO: Agregar información de puntos
    if loyalty_result and loyalty_result.get("success"):
        points_earned = loyalty_result.get("points_earned", 0)
        total_points = loyalty_result.get("total_points", 0)
        current_tier = loyalty_result.get("current_tier", "bronce")

        message += "⭐ *Programa de Fidelidad*\n"
        message += f"Ganaste: +{points_earned} puntos\n"
        message += f"Total acumulado: {total_points} puntos\n"
        message += f"Nivel: {current_tier.upper()}\n"

        # Si subió de nivel
        if loyalty_result.get("tier_upgraded"):
            message += f"\n🎊 ¡Felicidades! Subiste a nivel {loyalty_result.get('new_tier', '').upper()}!\n"

        # Bonus primera compra
        if loyalty_result.get("first_purchase_bonus", 0) > 0:
            message += f"\n🎁 ¡Bonus primera compra incluido!\n"

        message += "\n"

    if delivery_method == "delivery":
        message += f"🛵 *Envío a domicilio*\n"
        if delivery_address:
            message += f"📍 {delivery_address}\n"
        message += "\nTu pedido llegará en 30-45 minutos.\n"
    else:
        message += f"🏪 *Recoger en tienda*\n"
        message += "\nTu pedido estará listo en 15-20 minutos.\n"

    message += "\n¡Gracias por tu compra! 😊"

    # BANNER DE MODO DEMO
    if is_demo:
        from .demo_config import DEMO_MODE_IDENTIFIER, get_demo_info_message

        message += f"\n\n{'━'*40}\n"
        message += f"{DEMO_MODE_IDENTIFIER}\n"
        message += f"{'━'*40}\n"
        message += "Este fue un pedido de demostración.\n"
        message += "NO procesamos pagos reales.\n\n"
        message += "¿Quieres ver cómo funciona para otro negocio?\n"
        message += "Escribe *cambiar* para explorar otras industrias.\n\n"
        message += "¿Listo para implementarlo en TU negocio?\n"
        message += "Escribe *info* para planes y precios.\n"
        message += f"{'━'*40}"

    return message


@app.post("/api/v1/payment/init")
async def init_payment(session_token: str, provider: str, amount: float):
    """Iniciar proceso de pago desde web."""
    try:
        token_data = hybrid_handler.url_generator.verify_session_token(session_token)
        if not token_data:
            raise HTTPException(status_code=400, detail="Token inválido")

        session = None
        for session_key, sess in hybrid_sessions.items():
            if sess.session_id == token_data["session_id"]:
                session = sess
                break

        if not session:
            raise HTTPException(status_code=404, detail="Sesión no encontrada")

        order_id = f"ORD-{session.session_id[:8]}"
        customer_data = {
            "phone": session.phone,
            "name": session.customer_name,
            "email": f"{session.phone}@whatsapp.user"
        }

        payment_result = await payment_handler.process_payment(
            provider=provider,
            amount=amount,
            order_id=order_id,
            customer_data=customer_data
        )

        return {"success": True, **payment_result}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[PaymentInit] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/payment/providers")
async def get_payment_providers(restaurant_id: Optional[str] = Query(None)):
    """
    Obtener métodos de pago disponibles.

    Args:
        restaurant_id: ID del restaurante (opcional, para detectar modo demo)
    """
    providers = payment_handler.get_available_providers(restaurant_id)
    return {"providers": providers}


# ==============================================================================
# LOYALTY/PUNTOS DE FIDELIDAD
# ==============================================================================

@app.get("/api/v1/loyalty/balance/{customer_phone}")
async def get_loyalty_balance(
    customer_phone: str,
    restaurant_id: str = Query(..., description="ID del restaurante")
):
    """
    Obtener balance de puntos de un cliente.

    Uso:
    GET /api/v1/loyalty/balance/5215512345678?restaurant_id=carniceria
    """
    try:
        balance = await loyalty_handler.get_balance(customer_phone, restaurant_id)
        return {"success": True, **balance.dict()}
    except Exception as e:
        logger.error(f"[LoyaltyAPI] Error obteniendo balance: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/loyalty/earn")
async def earn_loyalty_points(request: EarnPointsRequest):
    """
    Otorgar puntos por una compra.

    Request:
    {
        "customer_phone": "5215512345678",
        "restaurant_id": "carniceria",
        "order_id": "WEB-12345",
        "order_total": 500.00,
        "customer_name": "Juan Pérez"
    }

    Response:
    {
        "success": true,
        "points_earned": 50,
        "total_points": 350,
        "current_tier": "plata",
        "tier_upgraded": false,
        "multiplier": 1.5
    }
    """
    try:
        result = await loyalty_handler.earn_points(request)
        return result
    except Exception as e:
        logger.error(f"[LoyaltyAPI] Error otorgando puntos: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/loyalty/redeem")
async def redeem_loyalty_points(request: RedeemPointsRequest):
    """
    Canjear puntos por descuento.

    Request:
    {
        "customer_phone": "5215512345678",
        "restaurant_id": "carniceria",
        "points_to_redeem": 100,
        "order_total": 500.00
    }

    Response:
    {
        "success": true,
        "discount_amount": 50.00,
        "points_redeemed": 100,
        "points_remaining": 250,
        "message": "¡Descuento de $50.00 aplicado!"
    }
    """
    try:
        result = await loyalty_handler.redeem_points(request)
        return result.dict()
    except Exception as e:
        logger.error(f"[LoyaltyAPI] Error canjeando puntos: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/loyalty/config/{restaurant_id}")
async def get_loyalty_config(restaurant_id: str):
    """
    Obtener configuración de loyalty de un restaurante.

    Uso: GET /api/v1/loyalty/config/carniceria
    """
    try:
        config = loyalty_handler.get_config(restaurant_id)
        return {"success": True, "config": config.dict()}
    except Exception as e:
        logger.error(f"[LoyaltyAPI] Error obteniendo config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/v1/loyalty/config/{restaurant_id}")
async def update_loyalty_config(restaurant_id: str, request: UpdateLoyaltyConfigRequest):
    """
    Actualizar configuración de loyalty (para dashboard admin).

    Request:
    {
        "restaurant_id": "carniceria",
        "enabled": true,
        "points_per_currency": 0.1,
        "currency_per_point": 0.5,
        "min_points_to_redeem": 100,
        "max_redeem_percentage": 50,
        "birthday_bonus": 100,
        "referral_bonus": 50
    }
    """
    try:
        updates = request.dict(exclude_unset=True, exclude_none=True)
        updates.pop("restaurant_id", None)  # No actualizar el ID

        config = loyalty_handler.update_config(restaurant_id, updates)
        return {"success": True, "config": config.dict(), "message": "Configuración actualizada"}
    except Exception as e:
        logger.error(f"[LoyaltyAPI] Error actualizando config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==============================================================================
# DEBUG ENDPOINTS (TEMPORAL - PARA PRUEBAS)
# ==============================================================================

@app.get("/api/debug/sessions")
async def debug_sessions():
    """Ver todas las sesiones activas (DEBUG)"""
    sessions_info = []
    for session_key, session in hybrid_sessions.items():
        sessions_info.append({
            "session_key": session_key,
            "phone": session.phone,
            "tenant_id": session.restaurant_id,
            "messages": session.message_count,
            "cart_items": len(session.cart),
            "created_at": session.created_at.isoformat()
        })

    return {
        "total_sessions": len(hybrid_sessions),
        "sessions": sessions_info
    }


# ==============================================================================
# STARTUP/SHUTDOWN
# ==============================================================================

@app.on_event("startup")
async def startup():
    """Inicialización"""
    # session_manager se inicializa automáticamente, no requiere connect()
    logger.info("🚀 WhatsApp Gateway iniciado")


@app.on_event("shutdown")
async def shutdown():
    """Limpieza"""
    # session_manager no requiere disconnect() explícito
    logger.info("👋 WhatsApp Gateway cerrado")
