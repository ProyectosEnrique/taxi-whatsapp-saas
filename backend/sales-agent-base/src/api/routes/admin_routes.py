"""
================================================================================
ADMIN AGENT API ROUTES
================================================================================
Endpoints REST para el Asistente Administrativo.

Endpoints:
- POST /api/admin/session - Crear sesion
- POST /api/admin/message - Procesar mensaje de texto
- POST /api/admin/voice - Procesar mensaje de voz
- GET  /api/admin/session/<id> - Obtener estado de sesion
- DELETE /api/admin/session/<id> - Cerrar sesion
================================================================================
"""

import os
import asyncio
import logging
from pathlib import Path
from flask import Blueprint, request, jsonify, current_app


# ==============================================================================
# HELPER PARA EJECUTAR CORUTINAS ASYNC EN FLASK
# ==============================================================================
def run_async(coro):
    """
    Ejecuta una corutina de forma segura en Flask.

    Flask >= 2.0 soporta async pero puede haber problemas con el event loop.
    Esta función garantiza que las corutinas se ejecuten correctamente.
    """
    try:
        # Intentar obtener el event loop actual
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Si ya hay un loop corriendo, crear uno nuevo en un thread
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, coro)
                return future.result(timeout=60)
        else:
            return loop.run_until_complete(coro)
    except RuntimeError:
        # No hay event loop, crear uno nuevo
        return asyncio.run(coro)

# Importar agente admin
try:
    from src.agents.admin_agent import AdminAgent, get_admin_agent
    ADMIN_AGENT_AVAILABLE = True
except ImportError as e:
    ADMIN_AGENT_AVAILABLE = False
    import_error = str(e)

# Importar handlers de voz
try:
    from src.voice.stt_handler import get_stt_handler
    from src.voice.tts_handler import get_tts_handler
    VOICE_HANDLERS_AVAILABLE = True
except ImportError:
    VOICE_HANDLERS_AVAILABLE = False

# IoT client eliminado - No usado en sistema de ventas

logger = logging.getLogger(__name__)

# Blueprint
admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')

# Admin Agent instance (lazy loading)
_admin_agent = None


def get_agent():
    """Obtener instancia del Admin Agent"""
    global _admin_agent

    if not ADMIN_AGENT_AVAILABLE:
        return None

    if _admin_agent is None:
        _admin_agent = get_admin_agent()

    return _admin_agent


# ==============================================================================
# ENDPOINTS
# ==============================================================================

@admin_bp.route('/health', methods=['GET'])
def health():
    """Health check del Admin Agent"""
    agent = get_agent()

    return jsonify({
        'status': 'healthy' if agent else 'unavailable',
        'admin_agent_available': ADMIN_AGENT_AVAILABLE,
        'voice_handlers_available': VOICE_HANDLERS_AVAILABLE,
        'error': import_error if not ADMIN_AGENT_AVAILABLE else None
    })


@admin_bp.route('/session', methods=['POST'])
def create_session():
    """
    Crear nueva sesion de administrador.

    Request Body (opcional):
        {
            "admin_name": "string",
            "tenant_id": "string"
        }

    Response:
        {
            "success": true,
            "session_id": "uuid",
            "message": "string"
        }
    """
    agent = get_agent()

    if not agent:
        return jsonify({
            'success': False,
            'error': 'Admin Agent no disponible'
        }), 503

    try:
        # Manejar caso donde no hay JSON o es invalido
        try:
            data = request.get_json(force=True, silent=True) or {}
        except Exception:
            data = {}

        admin_name = data.get('admin_name')
        tenant_id = data.get('tenant_id', 'default')

        # Crear sesion
        import uuid
        session_id = str(uuid.uuid4())

        # Inicializar contexto de sesion
        session = agent.get_or_create_session(session_id)

        # Guardar metadata
        session['admin_name'] = admin_name
        session['tenant_id'] = tenant_id

        logger.info(f"[AdminAPI] Nueva sesion: {session_id}")

        return jsonify({
            'success': True,
            'session_id': session_id,
            'message': f'Sesion creada para {admin_name or "administrador"}'
        })

    except Exception as e:
        logger.error(f"[AdminAPI] Error creando sesion: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@admin_bp.route('/message', methods=['POST'])
def process_message():
    """
    Procesar mensaje de texto del administrador.

    Request Body:
        {
            "session_id": "uuid",
            "message": "string",
            "voice_response": true/false (opcional, default false),
            "dashboard_context": {...} (opcional, contexto del dashboard)
        }

    Response:
        {
            "success": true,
            "text": "string",
            "intent": "string",
            "requires_confirmation": bool,
            "confirmation_message": "string" (opcional),
            "visual_data": {...} (opcional),
            "audio_url": "string" (opcional, si voice_response=true)
        }
    """
    agent = get_agent()

    if not agent:
        return jsonify({
            'success': False,
            'error': 'Admin Agent no disponible'
        }), 503

    try:
        data = request.get_json() or {}
        session_id = data.get('session_id')
        message = data.get('message', '').strip()
        voice_response = data.get('voice_response', False)
        dashboard_context = data.get('dashboard_context')  # NUEVO: Contexto del dashboard

        if not session_id:
            return jsonify({
                'success': False,
                'error': 'session_id requerido'
            }), 400

        if not message:
            return jsonify({
                'success': False,
                'error': 'message requerido'
            }), 400

        logger.info(f"[AdminAPI] [{session_id}] Mensaje: {message[:50]}...")

        # Log si hay contexto del dashboard
        if dashboard_context:
            logger.debug(f"[AdminAPI] [{session_id}] Dashboard context recibido con {len(dashboard_context)} keys")

        # Procesar mensaje con contexto del dashboard usando run_async
        response = run_async(agent.process_message(
            session_id=session_id,
            message=message,
            context={'dashboard_context': dashboard_context} if dashboard_context else None
        ))

        # Construir respuesta
        result = {
            'success': True,
            'text': response.text,
            'intent': response.intent,
            'requires_confirmation': response.requires_confirmation
        }

        if response.requires_confirmation:
            result['confirmation_message'] = response.confirmation_message
            result['pending_action'] = response.metadata.get('pending_action') if response.metadata else None

        if response.visual_data:
            result['visual_data'] = response.visual_data

        if response.metadata:
            result['metadata'] = response.metadata

        # Generar audio si se solicita
        if voice_response and VOICE_HANDLERS_AVAILABLE:
            try:
                tts_handler = get_tts_handler()
                upload_folder = Path(current_app.config.get('UPLOAD_FOLDER', '/app/temp'))
                upload_folder.mkdir(exist_ok=True)

                audio_filename = f"admin_response_{session_id}.mp3"
                audio_path = upload_folder / audio_filename

                run_async(tts_handler.synthesize_to_file(response.text, audio_path))
                result['audio_url'] = f"/audio/{audio_filename}"

                logger.info(f"[AdminAPI] [{session_id}] Audio generado")
            except Exception as tts_error:
                logger.warning(f"[AdminAPI] Error generando audio: {tts_error}")

        logger.info(f"[AdminAPI] [{session_id}] Intent: {response.intent}")

        return jsonify(result)

    except Exception as e:
        logger.error(f"[AdminAPI] Error procesando mensaje: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@admin_bp.route('/voice', methods=['POST'])
def process_voice():
    """
    Procesar mensaje de voz del administrador.

    Request (multipart/form-data):
        - audio: archivo de audio (webm, wav, mp3)
        - session_id: string

    Response:
        {
            "success": true,
            "transcription": "string",
            "response": "string",
            "intent": "string",
            "requires_confirmation": bool,
            "audio_url": "string"
        }
    """
    agent = get_agent()

    if not agent:
        return jsonify({
            'success': False,
            'error': 'Admin Agent no disponible'
        }), 503

    if not VOICE_HANDLERS_AVAILABLE:
        return jsonify({
            'success': False,
            'error': 'Voice handlers no disponibles'
        }), 503

    try:
        session_id = request.form.get('session_id')

        if not session_id:
            return jsonify({
                'success': False,
                'error': 'session_id requerido'
            }), 400

        if 'audio' not in request.files:
            return jsonify({
                'success': False,
                'error': 'audio requerido'
            }), 400

        audio_file = request.files['audio']
        audio_data = audio_file.read()

        logger.info(f"[AdminAPI] [{session_id}] Audio recibido: {len(audio_data)} bytes")

        # 1. Transcribir audio
        stt_handler = get_stt_handler()
        transcription = run_async(stt_handler.transcribe_bytes(
            audio_data,
            convert_to_wav=False
        ))

        if not transcription or not transcription.strip():
            return jsonify({
                'success': False,
                'error': 'No se pudo transcribir el audio'
            }), 400

        logger.info(f"[AdminAPI] [{session_id}] Transcripcion: {transcription}")

        # 2. Procesar con Admin Agent
        response = run_async(agent.process_message(
            session_id=session_id,
            message=transcription
        ))

        # 3. Generar audio de respuesta
        tts_handler = get_tts_handler()
        upload_folder = Path(current_app.config.get('UPLOAD_FOLDER', '/app/temp'))
        upload_folder.mkdir(exist_ok=True)

        audio_filename = f"admin_voice_response_{session_id}.mp3"
        audio_path = upload_folder / audio_filename

        run_async(tts_handler.synthesize_to_file(response.text, audio_path))

        # 4. Construir respuesta
        result = {
            'success': True,
            'transcription': transcription,
            'response': response.text,
            'intent': response.intent,
            'requires_confirmation': response.requires_confirmation,
            'audio_url': f"/audio/{audio_filename}"
        }

        if response.requires_confirmation:
            result['confirmation_message'] = response.confirmation_message

        if response.visual_data:
            result['visual_data'] = response.visual_data

        logger.info(f"[AdminAPI] [{session_id}] Voice procesado - Intent: {response.intent}")

        return jsonify(result)

    except Exception as e:
        logger.error(f"[AdminAPI] Error procesando voz: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@admin_bp.route('/session/<session_id>', methods=['GET'])
def get_session(session_id: str):
    """
    Obtener estado de sesion del administrador.

    Response:
        {
            "success": true,
            "session": {
                "id": "string",
                "state": "string",
                "history_length": int,
                "metrics": {...}
            }
        }
    """
    agent = get_agent()

    if not agent:
        return jsonify({
            'success': False,
            'error': 'Admin Agent no disponible'
        }), 503

    try:
        session = agent.get_session(session_id)

        if not session:
            return jsonify({
                'success': False,
                'error': 'Sesion no encontrada'
            }), 404

        # Obtener historial
        history = agent.get_conversation_history(session_id)

        return jsonify({
            'success': True,
            'session': {
                'id': session_id,
                'state': session.get('state', 'idle'),
                'history_length': len(history),
                'admin_name': session.get('admin_name'),
                'created_at': session.get('created_at'),
                'last_activity': session.get('last_activity')
            }
        })

    except Exception as e:
        logger.error(f"[AdminAPI] Error obteniendo sesion: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@admin_bp.route('/session/<session_id>', methods=['DELETE'])
def close_session(session_id: str):
    """
    Cerrar sesion del administrador.

    Response:
        {
            "success": true,
            "message": "string"
        }
    """
    agent = get_agent()

    if not agent:
        return jsonify({
            'success': False,
            'error': 'Admin Agent no disponible'
        }), 503

    try:
        # Limpiar sesion
        if hasattr(agent, 'sessions') and session_id in agent.sessions:
            del agent.sessions[session_id]

        if hasattr(agent, 'conversation_history') and session_id in agent.conversation_history:
            del agent.conversation_history[session_id]

        logger.info(f"[AdminAPI] Sesion cerrada: {session_id}")

        return jsonify({
            'success': True,
            'message': 'Sesion cerrada exitosamente'
        })

    except Exception as e:
        logger.error(f"[AdminAPI] Error cerrando sesion: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@admin_bp.route('/metrics', methods=['GET'])
def get_metrics():
    """
    Obtener metricas del Admin Agent.

    Response:
        {
            "success": true,
            "metrics": {
                "total_requests": int,
                "successful_requests": int,
                "failed_requests": int,
                "avg_response_time_ms": float,
                "actions_executed": int,
                "active_sessions": int
            }
        }
    """
    agent = get_agent()

    if not agent:
        return jsonify({
            'success': False,
            'error': 'Admin Agent no disponible'
        }), 503

    try:
        metrics = agent.get_metrics()

        # Agregar sesiones activas
        metrics['active_sessions'] = len(agent.sessions) if hasattr(agent, 'sessions') else 0

        return jsonify({
            'success': True,
            'metrics': metrics
        })

    except Exception as e:
        logger.error(f"[AdminAPI] Error obteniendo metricas: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ==============================================================================
# IOT SECURITY ENDPOINTS - ELIMINADOS
# ==============================================================================
# Estos endpoints fueron eliminados ya que el sistema es solo para ventas
# por WhatsApp/Web, no incluye funcionalidad de IoT/ESP32/Seguridad


# ==============================================================================
# WHATSAPP CHANNEL
# ==============================================================================

@admin_bp.route('/whatsapp/message', methods=['POST'])
def process_whatsapp_message():
    """
    Procesar mensaje del admin desde WhatsApp.

    Este endpoint es llamado por el WhatsApp Gateway cuando detecta
    un mensaje de un número autorizado como administrador.

    Request Body (JSON):
        {
            "session_id": "admin_5255512345",
            "message": "¿Cuántas ventas llevamos hoy?",
            "context": {
                "phone": "+5255512345",
                "admin_name": "Admin",
                "channel": "whatsapp"
            }
        }

    Response:
        {
            "success": true,
            "response": "string",
            "text": "string",  # Alias de response
            "buttons": [...],  # Opcional
            "visual_data": {...}  # Opcional (no usado en WhatsApp)
        }
    """
    agent = get_agent()

    if not agent:
        return jsonify({
            'success': False,
            'error': 'Admin Agent no disponible'
        }), 503

    try:
        data = request.get_json() or {}

        session_id = data.get('session_id')
        message = data.get('message', '')
        context = data.get('context', {})

        if not session_id:
            return jsonify({
                'success': False,
                'error': 'session_id requerido'
            }), 400

        if not message:
            return jsonify({
                'success': False,
                'error': 'message requerido'
            }), 400

        phone = context.get('phone', 'unknown')
        admin_name = context.get('admin_name', 'Admin')

        logger.info(f"[AdminAPI:WhatsApp] Mensaje de {phone}: {message[:50]}...")

        # Procesar con AdminAgent usando el canal de WhatsApp
        from src.agents.admin_agent.channels import AdminChannelManager

        channel_manager = AdminChannelManager(agent)

        response = run_async(channel_manager.route_message(
            channel='whatsapp',
            message=message,
            session_id=session_id,
            context=context
        ))

        # Formatear respuesta
        result = {
            'success': True,
            'response': response.text,
            'text': response.text,  # Alias para compatibilidad
        }

        if response.buttons:
            result['buttons'] = response.buttons

        if response.visual_data:
            result['visual_data'] = response.visual_data

        logger.info(f"[AdminAPI:WhatsApp] Respuesta enviada a {phone}")

        return jsonify(result)

    except Exception as e:
        logger.error(f"[AdminAPI:WhatsApp] Error procesando mensaje: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'text': 'Lo siento, tuve un problema procesando tu mensaje. Intenta de nuevo.'
        }), 500


@admin_bp.route('/whatsapp/preview-audience', methods=['POST'])
def preview_whatsapp_audience():
    """
    Previsualizar cantidad de clientes en un segmento.

    Request Body:
        {
            "segment": "all|frequent|inactive|new|vip"
        }

    Response:
        {
            "success": true,
            "count": int,
            "segment": "string",
            "description": "string"
        }
    """
    try:
        data = request.get_json() or {}
        segment = data.get('segment', 'all')

        # Importar segmentador
        from src.whatsapp.customer_segmentation import get_customer_segmenter

        segmenter = get_customer_segmenter()

        # Obtener clientes del segmento
        customers = run_async(segmenter.get_customers({'segment': segment}))

        # Descripciones de segmentos
        segment_descriptions = {
            'all': 'Todos los clientes con WhatsApp',
            'frequent': 'Clientes con 3+ órdenes',
            'inactive': 'Sin ordenar en 30+ días',
            'new': 'Clientes con 1-2 órdenes',
            'vip': 'Gasto total > $1000'
        }

        return jsonify({
            'success': True,
            'count': len(customers),
            'segment': segment,
            'description': segment_descriptions.get(segment, 'Segmento personalizado')
        })

    except Exception as e:
        logger.error(f"[AdminAPI:WhatsApp] Error previewing audience: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@admin_bp.route('/whatsapp/broadcast', methods=['POST'])
def send_whatsapp_broadcast():
    """
    Enviar broadcast de promoción a clientes segmentados.

    Request Body:
        {
            "promotion_id": "string",
            "custom_message": "string" (opcional),
            "audience_filter": {
                "segment": "all|frequent|inactive|new|vip"
            },
            "personalize": true/false
        }

    Response:
        {
            "success": true,
            "total_sent": int,
            "successful": int,
            "failed": int,
            "success_rate": float
        }
    """
    agent = get_agent()

    if not agent:
        return jsonify({
            'success': False,
            'error': 'Admin Agent no disponible'
        }), 503

    try:
        data = request.get_json() or {}

        promotion_id = data.get('promotion_id')
        custom_message = data.get('custom_message')
        audience_filter = data.get('audience_filter', {})
        personalize = data.get('personalize', True)

        if not promotion_id:
            return jsonify({
                'success': False,
                'error': 'promotion_id requerido'
            }), 400

        logger.info(f"[AdminAPI:WhatsApp] Broadcast solicitado para promoción {promotion_id}")

        # Importar broadcast manager
        from src.whatsapp.broadcast_manager import get_broadcast_manager

        broadcast_manager = get_broadcast_manager()

        # Enviar promoción
        result = run_async(broadcast_manager.send_promotion(
            promotion_id=promotion_id,
            audience_filter=audience_filter,
            custom_message=custom_message,
            personalize=personalize
        ))

        # Calcular tasa de éxito
        success_rate = 0
        if result.total_sent > 0:
            success_rate = round((result.successful / result.total_sent) * 100, 1)

        logger.info(f"[AdminAPI:WhatsApp] Broadcast completado: {result.successful}/{result.total_sent} exitosos")

        return jsonify({
            'success': True,
            'total_sent': result.total_sent,
            'successful': result.successful,
            'failed': result.failed,
            'success_rate': success_rate,
            'errors': result.errors[:5] if result.errors else []  # Solo primeros 5 errores
        })

    except Exception as e:
        logger.error(f"[AdminAPI:WhatsApp] Error enviando broadcast: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ==============================================================================
# ANALYTICS ENDPOINTS
# ==============================================================================

@admin_bp.route('/analytics/whatsapp/metrics', methods=['GET'])
def get_whatsapp_metrics():
    """
    Obtener métricas generales del canal WhatsApp.

    Response:
        {
            "success": true,
            "total_conversations": int,
            "total_orders": int,
            "conversion_rate": float,
            "avg_ticket": float,
            "active_conversations": int,
            "pending_responses": int
        }
    """
    try:
        # Importar analytics manager
        from src.whatsapp.analytics import get_analytics_manager

        analytics = get_analytics_manager()

        # Obtener métricas desde AnalyticsManager
        metrics = run_async(analytics.get_channel_metrics())

        return jsonify({
            'success': True,
            **metrics
        })

    except Exception as e:
        logger.error(f"[AdminAPI:Analytics] Error obteniendo métricas WhatsApp: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@admin_bp.route('/analytics/whatsapp/campaigns', methods=['GET'])
def get_whatsapp_campaigns():
    """
    Obtener historial de campañas broadcast.

    Response:
        {
            "success": true,
            "campaigns": [
                {
                    "id": "string",
                    "name": "string",
                    "date": "ISO timestamp",
                    "segment": "string",
                    "total_sent": int,
                    "successful": int,
                    "failed": int,
                    "read_count": int,
                    "orders_generated": int,
                    "revenue": float
                }
            ]
        }
    """
    try:
        # Importar analytics manager
        from src.whatsapp.analytics import get_analytics_manager

        analytics = get_analytics_manager()

        # Obtener campañas
        campaigns = run_async(analytics.get_campaign_history())

        return jsonify({
            'success': True,
            'campaigns': campaigns
        })

    except Exception as e:
        logger.error(f"[AdminAPI:Analytics] Error obteniendo campañas: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@admin_bp.route('/whatsapp/conversations/active', methods=['GET'])
def get_active_whatsapp_conversations():
    """
    Obtener conversaciones activas de WhatsApp.

    Response:
        {
            "success": true,
            "conversations": [
                {
                    "id": "string",
                    "customer_name": "string",
                    "phone": "string",
                    "state": "string",
                    "last_message": "string",
                    "last_message_time": "ISO timestamp",
                    "order_total": float
                }
            ]
        }
    """
    try:
        # Importar analytics manager
        from src.whatsapp.analytics import get_analytics_manager

        analytics = get_analytics_manager()

        # Obtener conversaciones activas
        conversations = run_async(analytics.get_active_conversations())

        return jsonify({
            'success': True,
            'conversations': conversations
        })

    except Exception as e:
        logger.error(f"[AdminAPI:Analytics] Error obteniendo conversaciones: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@admin_bp.route('/analytics/whatsapp/top-products', methods=['GET'])
def get_whatsapp_top_products():
    """
    Obtener productos más vendidos por WhatsApp.

    Response:
        {
            "success": true,
            "products": [
                {
                    "name": "string",
                    "orders": int,
                    "revenue": float
                }
            ]
        }
    """
    try:
        # Importar analytics manager
        from src.whatsapp.analytics import get_analytics_manager

        analytics = get_analytics_manager()

        # Obtener top products
        products = run_async(analytics.get_top_products())

        return jsonify({
            'success': True,
            'products': products
        })

    except Exception as e:
        logger.error(f"[AdminAPI:Analytics] Error obteniendo top products: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@admin_bp.route('/analytics/whatsapp/peak-hours', methods=['GET'])
def get_whatsapp_peak_hours():
    """
    Obtener horarios pico de pedidos por WhatsApp.

    Response:
        {
            "success": true,
            "peak_hours": [
                {
                    "hour": "HH:MM",
                    "orders": int,
                    "percentage": int
                }
            ]
        }
    """
    try:
        # Importar analytics manager
        from src.whatsapp.analytics import get_analytics_manager

        analytics = get_analytics_manager()

        # Obtener peak hours
        peak_hours = run_async(analytics.get_peak_hours())

        return jsonify({
            'success': True,
            'peak_hours': peak_hours
        })

    except Exception as e:
        logger.error(f"[AdminAPI:Analytics] Error obteniendo peak hours: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

def register_admin_routes(app):
    """
    Registrar rutas del Admin Agent en la aplicacion Flask.

    Args:
        app: Flask application instance
    """
    app.register_blueprint(admin_bp)
    logger.info("[AdminAPI] Rutas registradas en /api/admin/*")
