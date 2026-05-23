# ============================================================
# VOICE ASSISTANT API - VERSIÓN 2.0 (FSM)
# ============================================================
# Nueva implementación usando Máquina de Estados Finitos
# El archivo app.py original se mantiene como backup
# ============================================================

import os
import asyncio
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict

import yaml
from flask import Flask, request, jsonify, send_file, render_template
from flask_cors import CORS
from werkzeug.utils import secure_filename

# Importar sistema FSM
from src.core.fsm import SalesAgentFSM, ConversationState, StateContext
from src.core.fsm.decision_tree import Intent
from src.core.fsm.tenant_fsm_factory import TenantFSMFactory

# Importar sistema multi-tenant
from src.core.tenant_manager import get_tenant_manager, TenantConfig

# Importar componentes existentes (reutilizables)
from src.voice.stt_handler import get_stt_handler
from src.voice.tts_handler import get_tts_handler, get_tts_status
from src.restaurant.api_client import get_restaurant_client
from src.core.session_manager import get_session_manager

# Importar sistema de feedback
from src.feedback import get_feedback_collector
from src.feedback.api import feedback_bp

# Importar sistema de training - con fallback si no está disponible
try:
    from src.training.flask_api import training_bp
    TRAINING_AVAILABLE = True
except ImportError:
    TRAINING_AVAILABLE = False

# Importar rutas del Admin Agent - con fallback si no está disponible
try:
    from src.api.routes.admin_routes import admin_bp, register_admin_routes
    ADMIN_AGENT_AVAILABLE = True
except ImportError:
    ADMIN_AGENT_AVAILABLE = False

# Importar rutas del Security Agent - con fallback si no está disponible
try:
    from src.api.routes.security_routes import security_bp, register_security_routes
    SECURITY_AGENT_AVAILABLE = True
except ImportError:
    SECURITY_AGENT_AVAILABLE = False

# Importar rutas de Sales (WhatsApp, etc.) - con fallback si no está disponible
try:
    from src.api.routes.sales_routes import sales_bp, register_sales_routes
    SALES_ROUTES_AVAILABLE = True
except ImportError:
    SALES_ROUTES_AVAILABLE = False

# Importar rutas de Driver Schedule - con fallback si no está disponible
try:
    from src.api.routes.driver_schedule import driver_schedule_bp, register_driver_schedule_routes
    DRIVER_SCHEDULE_AVAILABLE = True
except ImportError:
    DRIVER_SCHEDULE_AVAILABLE = False

# Importar sistema de métricas (Prometheus) - con fallback si no está disponible
try:
    from src.monitoring import get_metrics, init_metrics
    from src.monitoring.health import HealthChecker
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    METRICS_AVAILABLE = True
except ImportError:
    METRICS_AVAILABLE = False
    logger_temp = None  # placeholder

# Importar Event Bus - con fallback si no está disponible
try:
    from src.events import get_event_bus, register_default_handlers
    EVENT_BUS_AVAILABLE = True
except ImportError:
    EVENT_BUS_AVAILABLE = False

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================
# INICIALIZACIÓN DE FLASK
# ============================================================

app = Flask(__name__, template_folder='../../templates')
CORS(app)

# Registrar Blueprint de feedback
app.register_blueprint(feedback_bp)

# Registrar Blueprint de training (si está disponible)
if TRAINING_AVAILABLE:
    app.register_blueprint(training_bp)

# Registrar Blueprint del Admin Agent (si está disponible)
if ADMIN_AGENT_AVAILABLE:
    app.register_blueprint(admin_bp)

# Registrar Blueprint del Security Agent (si está disponible)
if SECURITY_AGENT_AVAILABLE:
    app.register_blueprint(security_bp)

# Registrar Blueprint de Sales/WhatsApp (si está disponible)
if SALES_ROUTES_AVAILABLE:
    app.register_blueprint(sales_bp)

# Registrar Blueprint de Driver Schedule (si está disponible)
if DRIVER_SCHEDULE_AVAILABLE:
    app.register_blueprint(driver_schedule_bp)

# Configuración - Usar ruta absoluta para evitar problemas de path
app.config['UPLOAD_FOLDER'] = Path('/app/temp')
app.config['UPLOAD_FOLDER'].mkdir(exist_ok=True)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

# ============================================================
# INICIALIZACIÓN DE COMPONENTES
# ============================================================

# Cargar configuración FSM
def load_fsm_config():
    config_path = Path('./config/fsm_config.yaml')
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    return {}

FSM_CONFIG = load_fsm_config()

# Componentes de voz
stt_handler = get_stt_handler()
tts_handler = get_tts_handler()

# Cliente del restaurante
restaurant_client = get_restaurant_client()

# Gestor de sesiones
session_manager = get_session_manager()

# Colector de feedback
feedback_collector = get_feedback_collector()

# Gestor de tenants (Multi-tenant v2.2)
tenant_manager = get_tenant_manager()

# Máquina de estados (se inicializa después de cargar el menú)
# En modo multi-tenant, cada tenant tiene su propio FSM
fsm: Optional[SalesAgentFSM] = None  # FSM por defecto (compatibilidad)
fsm_cache: Dict[str, SalesAgentFSM] = {}  # Cache de FSM por tenant_id

# Cache del menú
MENU_CACHE = []
MENU_LAST_UPDATE = None


async def initialize_fsm():
    """Inicializa la máquina de estados con el menú y componentes v2.2 + Multi-tenant"""
    global fsm, fsm_cache, MENU_CACHE, MENU_LAST_UPDATE, tenant_manager

    try:
        # Inicializar Event Bus si está disponible
        if EVENT_BUS_AVAILABLE:
            try:
                event_bus = get_event_bus()
                await event_bus.initialize()
                register_default_handlers()
                logger.info("[INIT] Event Bus inicializado")
            except Exception as eb_error:
                logger.warning(f"[INIT] Event Bus no disponible: {eb_error}")

        # Inicializar Metrics si está disponible
        if METRICS_AVAILABLE:
            try:
                init_metrics()
                logger.info("[INIT] Prometheus Metrics inicializadas")
            except Exception as m_error:
                logger.warning(f"[INIT] Metrics no disponibles: {m_error}")

        # Cargar menú (para compatibilidad con modo single-tenant)
        menu = await restaurant_client.get_menu()
        MENU_CACHE = menu
        MENU_LAST_UPDATE = datetime.now()

        # Inicializar FSM para cada tenant activo
        tenants = tenant_manager.list_tenants()

        if tenants:
            logger.info(f"[MULTI-TENANT] Inicializando FSM para {len(tenants)} tenant(s)")
            logger.info(f"[MULTI-TENANT] Tenants activos: {[(t.tenant_id, t.name, t.type) for t in tenants]}")

            for tenant_config in tenants:
                try:
                    # Crear FSM personalizado para el tenant
                    tenant_fsm = TenantFSMFactory.create_fsm(tenant_config)
                    fsm_cache[tenant_config.tenant_id] = tenant_fsm

                    logger.info(f"[MULTI-TENANT] ✅ FSM creado para '{tenant_config.name}' (tipo: {tenant_config.type})")
                except Exception as tenant_error:
                    logger.error(f"[MULTI-TENANT] ❌ Error creando FSM para {tenant_config.tenant_id}: {tenant_error}")

            # Usar el primer tenant como FSM por defecto (compatibilidad)
            if fsm_cache:
                default_tenant_id = list(fsm_cache.keys())[0]
                fsm = fsm_cache[default_tenant_id]
                logger.info(f"[MULTI-TENANT] FSM por defecto: {default_tenant_id}")
        else:
            # Modo single-tenant (compatibilidad legacy)
            logger.info("[SINGLE-TENANT] No se encontraron tenants, usando FSM legacy")
            fsm = SalesAgentFSM(menu=menu, config=FSM_CONFIG)
        
        # Log de componentes activos
        components = []
        if hasattr(fsm, 'hybrid_nlu') and fsm.hybrid_nlu:
            components.append('HybridNLU(Cerebras)')
        if hasattr(fsm, 'enhanced_classifier') and fsm.enhanced_classifier:
            components.append('EnhancedClassifier')
        if hasattr(fsm, 'semantic_search') and fsm.semantic_search:
            components.append('SemanticSearch')
        if hasattr(fsm, 'product_validator') and fsm.product_validator:
            components.append('ProductValidator')
        if hasattr(fsm, 'event_bus') and fsm.event_bus:
            components.append('EventBus')
        if hasattr(fsm, 'feedback_loop') and fsm.feedback_loop:
            components.append('FeedbackLoop')
        if hasattr(fsm, 'metrics') and fsm.metrics:
            components.append('Metrics')
        if hasattr(fsm, 'multi_order_parser') and fsm.multi_order_parser:
            components.append('MultiOrderParser')

        logger.info(f"[FSM] v3.0 Inicializado con {len(menu)} productos | Componentes: {', '.join(components) or 'Basic'}")

        # Registrar rutas de Sales con dependencias
        if SALES_ROUTES_AVAILABLE:
            register_sales_routes(fsm, session_manager, restaurant_client)
            logger.info("[INIT] Sales Routes registradas (WhatsApp/Web)")

    except Exception as e:
        logger.error(f"[FSM] Error al inicializar: {e}")
        fsm = SalesAgentFSM(menu=[], config=FSM_CONFIG)


def get_fsm_for_tenant(tenant_id: str) -> Optional[SalesAgentFSM]:
    """
    Obtiene el FSM para un tenant específico

    Args:
        tenant_id: ID del tenant

    Returns:
        SalesAgentFSM o None si no existe
    """
    global fsm_cache, fsm

    # Buscar en cache
    if tenant_id in fsm_cache:
        return fsm_cache[tenant_id]

    # Si no existe, intentar crearlo
    tenant_config = tenant_manager.get_tenant(tenant_id)

    if tenant_config and tenant_config.active:
        try:
            tenant_fsm = TenantFSMFactory.create_fsm(tenant_config)
            fsm_cache[tenant_id] = tenant_fsm
            logger.info(f"[MULTI-TENANT] FSM creado para tenant {tenant_id}")
            return tenant_fsm
        except Exception as e:
            logger.error(f"[MULTI-TENANT] Error creando FSM para {tenant_id}: {e}")

    # Fallback al FSM por defecto
    logger.warning(f"[MULTI-TENANT] Tenant {tenant_id} no encontrado, usando FSM por defecto")
    return fsm


def get_fsm_by_phone(phone: str) -> tuple[Optional[SalesAgentFSM], Optional[str]]:
    """
    Obtiene el FSM basándose en el número de teléfono del negocio

    Args:
        phone: Número de WhatsApp del negocio

    Returns:
        Tupla (FSM, tenant_id) o (None, None) si no se encuentra
    """
    global fsm

    # Buscar tenant por teléfono
    tenant_config = tenant_manager.get_tenant_by_phone(phone)

    if tenant_config:
        tenant_fsm = get_fsm_for_tenant(tenant_config.tenant_id)
        return tenant_fsm, tenant_config.tenant_id

    # Fallback al FSM por defecto
    logger.warning(f"[MULTI-TENANT] No se encontró tenant para teléfono {phone}, usando FSM por defecto")
    return fsm, 'default'


async def refresh_menu_if_needed():
    """Actualiza el menú si es necesario"""
    global MENU_CACHE, MENU_LAST_UPDATE

    if MENU_LAST_UPDATE is None:
        await initialize_fsm()
        return

    # Refrescar cada 5 minutos
    age = (datetime.now() - MENU_LAST_UPDATE).total_seconds()
    if age > 300:
        try:
            menu = await restaurant_client.get_menu()
            MENU_CACHE = menu
            MENU_LAST_UPDATE = datetime.now()
            if fsm:
                fsm.update_menu(menu)
            logger.info(f"[FSM] Menú actualizado: {len(menu)} productos")
        except Exception as e:
            logger.warning(f"[FSM] Error al actualizar menú: {e}")


# ============================================================
# ENDPOINTS
# ============================================================

@app.route('/')
def index():
    """Interfaz web del asistente de voz"""
    return render_template('index.html')


@app.route('/api/health', methods=['GET'])
async def health_check():
    """Health check endpoint con información extendida v2.2 + Multi-tenant"""
    services_health = await restaurant_client.health_check()

    # Información básica
    response = {
        'status': 'healthy',
        'version': '2.3.0-multi-tenant',
        'services': services_health,
        'fsm_initialized': fsm is not None,
        'menu_products': len(MENU_CACHE)
    }

    # Agregar estado de componentes v2.3
    response['components'] = {
        'metrics': METRICS_AVAILABLE,
        'event_bus': EVENT_BUS_AVAILABLE,
        'training_pipeline': TRAINING_AVAILABLE,
        'admin_agent': ADMIN_AGENT_AVAILABLE,
        'security_agent': SECURITY_AGENT_AVAILABLE,
        'sales_routes': SALES_ROUTES_AVAILABLE
    }

    # Estado multi-tenant
    tenants = tenant_manager.list_tenants()
    response['multi_tenant'] = {
        'enabled': True,
        'tenants_active': len(tenants),
        'fsm_instances': len(fsm_cache)
    }

    # Estado del FSM si está disponible
    if fsm and hasattr(fsm, 'get_system_status'):
        response['fsm_status'] = fsm.get_system_status()

    return jsonify(response)


@app.route('/api/metrics', methods=['GET'])
def prometheus_metrics():
    """Endpoint para métricas de Prometheus"""
    if not METRICS_AVAILABLE:
        return jsonify({
            'error': 'Metrics not available',
            'message': 'prometheus-client not installed'
        }), 503
    
    try:
        from flask import Response
        metrics_output = generate_latest()
        return Response(metrics_output, mimetype=CONTENT_TYPE_LATEST)
    except Exception as e:
        logger.error(f'Error generating metrics: {e}')
        return jsonify({'error': str(e)}), 500


@app.route('/api/fsm/status', methods=['GET'])
async def fsm_status():
    """Estado detallado del FSM y sus componentes"""
    if not fsm:
        return jsonify({'error': 'FSM not initialized'}), 503

    status = {
        'initialized': True,
        'version': '3.0.0',
        'sessions_active': len(fsm.sessions) if hasattr(fsm, 'sessions') else 0,
        'menu_products': len(MENU_CACHE)
    }

    # Agregar estado de componentes si están disponibles
    if hasattr(fsm, 'get_system_status'):
        status['components'] = fsm.get_system_status()

    return jsonify(status)


@app.route('/api/tts/status', methods=['GET'])
async def tts_status():
    """
    Estado del sistema TTS con metricas de latencia.

    Retorna:
    - preferred_provider: Proveedor configurado
    - cartesia_available: Si Cartesia Sonic esta disponible
    - latency_stats: Estadisticas de latencia por proveedor
    """
    try:
        status = get_tts_status()
        return jsonify({
            'success': True,
            **status
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/nlu/patterns', methods=['GET'])
async def nlu_patterns():
    """
    Exporta los patrones aprendidos por el HybridNLU.
    Útil para revisión humana y debugging.
    """
    if not fsm:
        return jsonify({'error': 'FSM not initialized'}), 503

    if hasattr(fsm, 'get_hybrid_nlu_patterns'):
        patterns_text = fsm.get_hybrid_nlu_patterns()
        return patterns_text, 200, {'Content-Type': 'text/plain; charset=utf-8'}
    else:
        return jsonify({'error': 'HybridNLU not available'}), 404


@app.route('/api/nlu/stats', methods=['GET'])
async def nlu_stats():
    """
    Retorna estadísticas del HybridNLU.
    """
    if not fsm:
        return jsonify({'error': 'FSM not initialized'}), 503

    if hasattr(fsm, 'hybrid_nlu') and fsm.hybrid_nlu:
        stats = fsm.hybrid_nlu.get_stats()
        return jsonify(stats)
    else:
        return jsonify({'error': 'HybridNLU not available'}), 404


@app.route('/api/nlu/mode', methods=['POST'])
async def nlu_mode():
    """
    Cambia el modo del HybridNLU (online/offline).
    Útil para testing.

    Body JSON:
    - mode: "online" | "offline"
    """
    if not fsm:
        return jsonify({'error': 'FSM not initialized'}), 503

    data = request.get_json() or {}
    mode = data.get('mode', 'online')

    if mode == 'offline':
        if hasattr(fsm, 'force_offline_mode'):
            fsm.force_offline_mode()
            return jsonify({'status': 'ok', 'mode': 'offline'})
    else:
        if hasattr(fsm, 'force_online_mode'):
            fsm.force_online_mode()
            return jsonify({'status': 'ok', 'mode': 'online'})

    return jsonify({'error': 'HybridNLU not available'}), 404


@app.route('/api/session/init', methods=['POST'])
async def init_session():
    """Inicializa una nueva sesión"""
    data = request.get_json() or {}
    table_id = data.get('table_id', 1)

    # Crear sesión
    session = session_manager.create_session(table_id=table_id)

    # Asegurar que FSM esté inicializado
    if not fsm:
        await initialize_fsm()

    logger.info(f"[SESSION] Nueva sesión: {session.session_id} (mesa {table_id})")

    return jsonify({
        'success': True,
        'session_id': session.session_id,
        'table_id': table_id
    })


@app.route('/api/voice/process', methods=['POST'])
async def process_voice():
    """
    Procesa audio de voz usando el sistema FSM.

    Flow:
    1. Recibir audio
    2. Transcribir (STT)
    3. Clasificar intención (Decision Tree)
    4. Procesar con FSM
    5. Generar respuesta
    6. Sintetizar audio (TTS)
    7. Retornar resultado
    """
    # Verificar sesión
    session_id = request.form.get('session_id')
    if not session_id:
        return jsonify({'success': False, 'error': 'session_id requerido'}), 400

    session = session_manager.get_session(session_id)
    if not session:
        return jsonify({'success': False, 'error': 'Sesión no encontrada'}), 404

    # Verificar audio
    if 'audio' not in request.files:
        return jsonify({'success': False, 'error': 'Audio requerido'}), 400

    audio_file = request.files['audio']

    try:
        # Leer audio como bytes
        audio_data = audio_file.read()

        logger.info(f"[{session_id}] Audio recibido: {len(audio_data)} bytes")

        # 1. TRANSCRIPCIÓN
        logger.info(f"[{session_id}] [1/5] Transcribiendo...")
        transcription = await stt_handler.transcribe_bytes(audio_data, convert_to_wav=False)

        if not transcription or not transcription.strip():
            logger.warning(f"[{session_id}] Transcripción vacía")
            return jsonify({
                'success': False,
                'error': 'No se pudo transcribir el audio'
            }), 400

        logger.info(f"[{session_id}] Transcripción: '{transcription}'")

        # 2. ACTUALIZAR MENÚ SI ES NECESARIO
        await refresh_menu_if_needed()

        # 3. PROCESAR CON FSM
        logger.info(f"[{session_id}] [2/5] Procesando con FSM...")

        if not fsm:
            await initialize_fsm()

        result = fsm.process(session_id, transcription)

        logger.info(f"[{session_id}] Intent: {result.intent} | Estado: {result.new_state.value}")

        # 4. SI REQUIERE LLM FALLBACK
        if result.requires_llm_fallback:
            logger.info(f"[{session_id}] [3/5] Usando LLM fallback...")
            # TODO: Implementar fallback a LLM para casos complejos
            # Por ahora, dar respuesta genérica
            response_text = "¿En qué te puedo ayudar? Tenemos hamburguesas, tacos, bebidas y más."
        else:
            response_text = result.response_text

        logger.info(f"[{session_id}] [3/5] Respuesta: {response_text[:100]}...")

        # 4.5 CAPTURAR FEEDBACK (independiente del flujo principal)
        try:
            context = fsm.sessions.get(session_id)
            feedback_collector.capture(
                session_id=session_id,
                user_input=transcription,
                detected_intent=result.intent,
                intent_confidence=result.intent_confidence if hasattr(result, 'intent_confidence') else 0.8,
                system_response=response_text,
                context=context,
                recommended_product=result.recommended_product if hasattr(result, 'recommended_product') else None,
                response_state=result.new_state.value
            )
        except Exception as fe:
            logger.warning(f"[{session_id}] Error capturando feedback: {fe}")

        # 4.6 ENVIAR PEDIDO A COCINA SI ESTÁ CONFIRMADO
        order_sent = None
        if hasattr(result, 'order_confirmed') and result.order_confirmed:
            try:
                logger.info(f"[{session_id}] 🍳 Enviando pedido a cocina...")
                context = fsm.sessions.get(session_id)

                if context and context.order_items:
                    # Preparar items para el API de orders-service
                    items = []
                    for item in context.order_items:
                        order_item = {
                            "product_id": item.product_id,
                            "quantity": item.quantity
                        }
                        if hasattr(item, 'notes') and item.notes:
                            order_item["notes"] = item.notes
                        items.append(order_item)

                    # Obtener table_id de la sesión
                    session_data = session_manager.get_session(session_id)
                    table_id = session_data.table_id if session_data else 1

                    # Preparar notas del pedido
                    order_notes = f"Pedido por voz - Sesión: {session_id}"

                    # Enviar al orders-service
                    order_sent = await restaurant_client.create_order(
                        table_id=table_id,
                        items=items,
                        notes=order_notes
                    )

                    logger.info(f"[{session_id}] ✅ Pedido #{order_sent.get('id')} enviado a cocina (Total: ${order_sent.get('total_amount')})")

                    # Limpiar el carrito después de enviar exitosamente
                    context.order_items = []
                    context.order_total = 0.0
                else:
                    logger.warning(f"[{session_id}] Pedido confirmado pero carrito vacío")

            except Exception as oe:
                logger.error(f"[{session_id}] ❌ Error enviando pedido a cocina: {oe}", exc_info=True)
                # No fallar la respuesta si falla el envío a cocina

        # 4.7 ENVIAR SOLICITUD DE SERVICIO SI HAY UNA (más salsa, limones, mesero, etc.)
        service_request_sent = None
        if hasattr(result, 'service_request') and result.service_request:
            try:
                logger.info(f"[{session_id}] 🍋 Enviando solicitud de servicio...")
                sr = result.service_request

                # Obtener table_id de la sesión
                session_data = session_manager.get_session(session_id)
                table_id = session_data.table_id if session_data else 1

                # Determinar el item solicitado del texto
                item_requested = sr.get('description', '').replace('Cliente solicita: ', '')

                # Enviar al orders-service
                service_request_sent = await restaurant_client.create_service_request(
                    table_id=table_id,
                    request_type=sr.get('request_type', 'service_item'),
                    description=sr.get('description', 'Solicitud de servicio'),
                    item_requested=item_requested,
                    priority=sr.get('priority', 2)
                )

                logger.info(f"[{session_id}] ✅ Solicitud de servicio #{service_request_sent.get('id')} enviada a meseros")

            except Exception as se:
                logger.error(f"[{session_id}] ❌ Error enviando solicitud de servicio: {se}", exc_info=True)
                # No fallar la respuesta si falla el envío

        # 5. GENERAR AUDIO
        logger.info(f"[{session_id}] [4/5] Generando audio...")

        force_audio = request.form.get('force_audio', 'true').lower() == 'true'
        audio_url = None

        if force_audio and response_text:
            audio_filename = f"response_{session_id}_voice.mp3"
            audio_path = app.config['UPLOAD_FOLDER'] / audio_filename

            await tts_handler.synthesize_to_file(response_text, audio_path)
            audio_url = f"/audio/{audio_filename}"

            logger.info(f"[{session_id}] Audio generado: {audio_filename}")

        # 6. PREPARAR RESPUESTA
        logger.info(f"[{session_id}] [5/5] Enviando respuesta")

        response_data = {
            'success': True,
            'transcription': transcription,
            'intent': result.intent,
            'response': response_text,
            'state': result.new_state.value,
            'audio_generated': force_audio
        }

        if audio_url:
            response_data['audio_url'] = audio_url

        if result.visual_data:
            response_data['visual_data'] = result.visual_data
            logger.info(f"[{session_id}] visual_data incluido: type={result.visual_data.get('type')}")

        # Incluir cart_action para sincronizar carrito del frontend
        if result.cart_action:
            response_data['cart_action'] = result.cart_action
            logger.info(f"[{session_id}] cart_action incluido: {len(result.cart_action.get('items', []))} items")

        # Incluir información del pedido enviado a cocina
        if order_sent:
            response_data['order_sent'] = True
            response_data['order'] = {
                'id': order_sent.get('id'),
                'uuid': order_sent.get('uuid'),
                'total_amount': order_sent.get('total_amount'),
                'status': order_sent.get('status')
            }
            logger.info(f"[{session_id}] 🍳 Pedido incluido en respuesta: #{order_sent.get('id')}")

        # Incluir información de la solicitud de servicio enviada
        if service_request_sent:
            response_data['service_request_sent'] = True
            response_data['service_request'] = {
                'id': service_request_sent.get('id'),
                'request_type': service_request_sent.get('request_type'),
                'description': service_request_sent.get('description'),
                'status': service_request_sent.get('status')
            }
            logger.info(f"[{session_id}] 🍋 Solicitud de servicio incluida: #{service_request_sent.get('id')}")

        logger.info(f"[{session_id}] Procesamiento completado")

        return jsonify(response_data)

    except Exception as e:
        logger.error(f"[{session_id}] Error: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/text/process', methods=['POST'])
async def process_text():
    """
    Procesa texto directamente (sin audio).
    Útil para testing y debug.
    """
    data = request.get_json() or {}
    session_id = data.get('session_id')
    text = data.get('text', '')

    if not session_id:
        return jsonify({'success': False, 'error': 'session_id requerido'}), 400

    if not text:
        return jsonify({'success': False, 'error': 'text requerido'}), 400

    try:
        # Asegurar FSM inicializado
        if not fsm:
            await initialize_fsm()

        # Procesar
        result = fsm.process(session_id, text)

        # Capturar feedback
        try:
            context = fsm.sessions.get(session_id)
            feedback_collector.capture(
                session_id=session_id,
                user_input=text,
                detected_intent=result.intent,
                intent_confidence=result.intent_confidence if hasattr(result, 'intent_confidence') else 0.8,
                system_response=result.response_text,
                context=context,
                recommended_product=result.recommended_product if hasattr(result, 'recommended_product') else None,
                response_state=result.new_state.value
            )
        except Exception as fe:
            logger.warning(f"[{session_id}] Error capturando feedback: {fe}")

        # ENVIAR PEDIDO A COCINA SI ESTÁ CONFIRMADO
        order_sent = None
        if hasattr(result, 'order_confirmed') and result.order_confirmed:
            try:
                logger.info(f"[{session_id}] 🍳 Enviando pedido a cocina (text)...")
                context = fsm.sessions.get(session_id)

                if context and context.order_items:
                    # Preparar items para el API de orders-service
                    items = []
                    for item in context.order_items:
                        order_item = {
                            "product_id": item.product_id,
                            "quantity": item.quantity
                        }
                        if hasattr(item, 'notes') and item.notes:
                            order_item["notes"] = item.notes
                        items.append(order_item)

                    # Obtener table_id de la sesión
                    session_data = session_manager.get_session(session_id)
                    table_id = data.get('table_id') or (session_data.table_id if session_data else 1)

                    # Enviar al orders-service
                    order_sent = await restaurant_client.create_order(
                        table_id=table_id,
                        items=items,
                        notes=f"Pedido por texto - Sesión: {session_id}"
                    )

                    logger.info(f"[{session_id}] ✅ Pedido #{order_sent.get('id')} enviado a cocina")

                    # Limpiar el carrito
                    context.order_items = []
                    context.order_total = 0.0

            except Exception as oe:
                logger.error(f"[{session_id}] ❌ Error enviando pedido: {oe}", exc_info=True)

        # ENVIAR SOLICITUD DE SERVICIO SI HAY UNA (más salsa, limones, mesero, etc.)
        service_request_sent = None
        if hasattr(result, 'service_request') and result.service_request:
            try:
                logger.info(f"[{session_id}] 🍋 Enviando solicitud de servicio (text)...")
                sr = result.service_request

                # Obtener table_id de la sesión
                session_data = session_manager.get_session(session_id)
                table_id = data.get('table_id') or (session_data.table_id if session_data else 1)

                # Determinar el item solicitado
                item_requested = sr.get('description', '').replace('Cliente solicita: ', '')

                # Enviar al orders-service
                service_request_sent = await restaurant_client.create_service_request(
                    table_id=table_id,
                    request_type=sr.get('request_type', 'service_item'),
                    description=sr.get('description', 'Solicitud de servicio'),
                    item_requested=item_requested,
                    priority=sr.get('priority', 2)
                )

                logger.info(f"[{session_id}] ✅ Solicitud de servicio #{service_request_sent.get('id')} enviada")

            except Exception as se:
                logger.error(f"[{session_id}] ❌ Error enviando solicitud de servicio: {se}", exc_info=True)

        response_data = {
            'success': True,
            'input': text,
            'intent': result.intent,
            'response': result.response_text,
            'state': result.new_state.value,
            'visual_data': result.visual_data
        }

        # Incluir cart_action para sincronizar carrito del frontend
        if result.cart_action:
            response_data['cart_action'] = result.cart_action
            logger.info(f"[{session_id}] cart_action incluido: {len(result.cart_action.get('items', []))} items")

        # Incluir información del pedido enviado
        if order_sent:
            response_data['order_sent'] = True
            response_data['order'] = {
                'id': order_sent.get('id'),
                'uuid': order_sent.get('uuid'),
                'total_amount': order_sent.get('total_amount'),
                'status': order_sent.get('status')
            }

        # Incluir información de la solicitud de servicio
        if service_request_sent:
            response_data['service_request_sent'] = True
            response_data['service_request'] = {
                'id': service_request_sent.get('id'),
                'request_type': service_request_sent.get('request_type'),
                'description': service_request_sent.get('description'),
                'status': service_request_sent.get('status')
            }

        return jsonify(response_data)

    except Exception as e:
        logger.error(f"Error procesando texto: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/session/<session_id>/context', methods=['GET'])
async def get_session_context(session_id: str):
    """Obtiene el contexto actual de una sesión (para debug)"""
    if not fsm:
        return jsonify({'error': 'FSM no inicializado'}), 500

    if session_id in fsm.sessions:
        context = fsm.sessions[session_id]
        return jsonify({
            'success': True,
            'context': context.to_dict()
        })

    return jsonify({'success': False, 'error': 'Sesión no encontrada'}), 404


@app.route('/api/session/<session_id>/metrics', methods=['GET'])
async def get_session_metrics(session_id: str):
    """Obtiene métricas de una sesión"""
    if not fsm:
        return jsonify({'error': 'FSM no inicializado'}), 500

    metrics = fsm.get_session_metrics(session_id)

    return jsonify({
        'success': True,
        'metrics': metrics
    })


@app.route('/audio/<filename>', methods=['GET'])
def serve_audio(filename: str):
    """Sirve archivos de audio generados"""
    audio_path = app.config['UPLOAD_FOLDER'] / secure_filename(filename)

    if audio_path.exists():
        return send_file(audio_path, mimetype='audio/mpeg')

    return jsonify({'error': 'Audio no encontrado'}), 404


@app.route('/api/fsm/reset/<session_id>', methods=['POST'])
async def reset_session(session_id: str):
    """Reinicia una sesión FSM"""
    if fsm and session_id in fsm.sessions:
        fsm.sessions[session_id].reset_for_new_order()
        return jsonify({'success': True, 'message': 'Sesión reiniciada'})

    return jsonify({'success': False, 'error': 'Sesión no encontrada'}), 404


# ============================================================
# FINALIZACIÓN DE SESIÓN DEL CLIENTE
# ============================================================

@app.route('/api/session/end-customer', methods=['POST'])
async def end_customer_session():
    """
    Finaliza la sesión del cliente cuando paga la cuenta.

    Este endpoint debe llamarse cuando el cliente paga. Realiza:
    1. Archiva la conversación completa para métricas y entrenamiento
    2. Limpia el historial de conversación
    3. Resetea el contexto del pedido
    4. Mantiene la sesión de mesa activa para el siguiente cliente

    Body JSON:
        - session_id: ID de la sesión a finalizar
        - order_total: (opcional) Total final del pedido
        - payment_method: (opcional) Método de pago usado

    Returns:
        - success: True si se finalizó correctamente
        - archived: Datos del archivo creado (para referencia)
        - message: Mensaje de confirmación
    """
    data = request.get_json() or {}
    session_id = data.get('session_id')
    order_total = data.get('order_total', 0.0)
    payment_method = data.get('payment_method', 'unknown')

    if not session_id:
        return jsonify({'success': False, 'error': 'session_id requerido'}), 400

    # Buscar sesión en SessionManager
    session = session_manager.get_session(session_id)

    # También actualizar contexto FSM si existe
    fsm_context = None
    if fsm and session_id in fsm.sessions:
        fsm_context = fsm.sessions[session_id]

        # Actualizar total si se proporciona
        if order_total > 0:
            fsm_context.order_total = order_total

    if session:
        # Actualizar contexto con total y método de pago
        if order_total > 0:
            session.set_context('order_total', order_total)
        session.set_context('payment_method', payment_method)
        session.set_context('payment_time', datetime.now().isoformat())

        # Archivar y limpiar
        archived_data = session.end_customer_session(archive=True)

        # También limpiar FSM context
        if fsm_context:
            fsm_context.reset_for_new_order()

        logger.info(
            f"[API] Sesión de cliente finalizada: {session_id} | "
            f"Mesa {session.table_number} | ${order_total:.2f} | {payment_method}"
        )

        return jsonify({
            'success': True,
            'message': 'Sesión del cliente finalizada correctamente',
            'archived': archived_data,
            'table_number': session.table_number,
            'ready_for_next_customer': True
        })

    elif fsm_context:
        # Solo hay contexto FSM, no sesión completa
        try:
            from .analytics.conversation_archive import get_conversation_archive

            archive_service = get_conversation_archive()
            archived = archive_service.archive_conversation(
                session_id=session_id,
                table_id=1,  # Default
                order_total=fsm_context.order_total or order_total,
                fsm_context=fsm_context
            )

            fsm_context.reset_for_new_order()

            return jsonify({
                'success': True,
                'message': 'Sesión FSM finalizada y archivada',
                'archived': {
                    'archive_id': archived.archive_id,
                    'duration_minutes': archived.duration_minutes
                },
                'ready_for_next_customer': True
            })

        except Exception as e:
            logger.error(f"[API] Error archivando sesión FSM: {e}")
            fsm_context.reset_for_new_order()

            return jsonify({
                'success': True,
                'message': 'Sesión finalizada (sin archivar)',
                'ready_for_next_customer': True
            })

    return jsonify({'success': False, 'error': 'Sesión no encontrada'}), 404


@app.route('/api/session/metrics', methods=['GET'])
async def get_admin_session_metrics():
    """
    Obtiene métricas de conversaciones para el administrador.

    Query params:
        - days: Número de días a analizar (default: 7)

    Returns:
        - Métricas agregadas de conversaciones
        - Totales de ventas, items, etc.
        - Tasas de éxito de upsell/crosssell
        - Productos más vendidos
    """
    try:
        from ..analytics.conversation_archive import get_conversation_archive

        days = request.args.get('days', 7, type=int)
        archive = get_conversation_archive()
        metrics = archive.get_metrics_for_admin(days=days)

        return jsonify({
            'success': True,
            'metrics': metrics
        })

    except Exception as e:
        logger.error(f"[API] Error obteniendo métricas: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/session/daily-summary', methods=['GET'])
async def get_daily_summary():
    """
    Obtiene el resumen del día actual o una fecha específica.

    Query params:
        - date: Fecha en formato YYYY-MM-DD (default: hoy)

    Returns:
        - Resumen del día con conversaciones, ventas, etc.
    """
    try:
        from ..analytics.conversation_archive import get_conversation_archive

        date_str = request.args.get('date')
        if date_str:
            from datetime import datetime
            date = datetime.strptime(date_str, '%Y-%m-%d')
        else:
            date = None

        archive = get_conversation_archive()
        summary = archive.get_daily_summary(date)

        return jsonify({
            'success': True,
            'summary': summary
        })

    except Exception as e:
        logger.error(f"[API] Error obteniendo resumen diario: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================================
# ENVÍO DE PEDIDO A COCINA
# ============================================================

@app.route('/api/order/submit', methods=['POST'])
async def submit_order_to_kitchen():
    """
    Envía el pedido confirmado al orders-service para que llegue a cocina.

    Este endpoint debe llamarse cuando el cliente confirma su pedido.
    Toma los items del carrito (context.order_items) y los envía al
    orders-service, que a su vez publica el evento MQTT para cocina.

    Body JSON:
        - session_id: ID de la sesión con el pedido
        - table_id: (opcional) ID de la mesa, default 1

    Returns:
        - order: Orden creada con ID y detalles
        - success: True si se creó correctamente
    """
    data = request.get_json() or {}
    session_id = data.get('session_id')

    if not session_id:
        return jsonify({'success': False, 'error': 'session_id requerido'}), 400

    if not fsm or session_id not in fsm.sessions:
        return jsonify({'success': False, 'error': 'Sesión no encontrada'}), 404

    context = fsm.sessions[session_id]

    # Verificar que hay items en el pedido
    if not context.order_items:
        return jsonify({'success': False, 'error': 'El pedido está vacío'}), 400

    try:
        # Preparar items para el API de orders-service
        items = []
        for item in context.order_items:
            order_item = {
                "product_id": item.product_id,
                "quantity": item.quantity
            }
            # Agregar notas si hay modificadores
            if item.notes:
                order_item["notes"] = item.notes
            items.append(order_item)

        # Obtener table_id de la sesión o del request
        session = session_manager.get_session(session_id)
        table_id = data.get('table_id') or (session.table_id if session else 1)

        # Preparar notas del pedido
        order_notes = f"Pedido por voz - Sesión: {session_id}"
        if context.get_order_summary():
            order_notes += f" | {context.get_order_summary()}"

        logger.info(f"[{session_id}] Enviando pedido a cocina: {len(items)} items, mesa {table_id}")

        # Enviar al orders-service
        order = await restaurant_client.create_order(
            table_id=table_id,
            items=items,
            notes=order_notes
        )

        logger.info(f"[{session_id}] ✅ Pedido creado: ID={order.get('id')}, Total=${order.get('total_amount')}")

        # Limpiar el carrito después de enviar exitosamente
        context.order_items = []
        context.order_total = 0.0

        return jsonify({
            'success': True,
            'order': order,
            'message': f"Pedido #{order.get('id')} enviado a cocina"
        })

    except Exception as e:
        logger.error(f"[{session_id}] Error enviando pedido a cocina: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/order/cart/<session_id>', methods=['GET'])
async def get_cart(session_id: str):
    """
    Obtiene el contenido actual del carrito de una sesión.

    Útil para mostrar el resumen antes de confirmar.
    """
    if not fsm or session_id not in fsm.sessions:
        return jsonify({'success': False, 'error': 'Sesión no encontrada'}), 404

    context = fsm.sessions[session_id]

    items = []
    for item in context.order_items:
        items.append({
            'product_id': item.product_id,
            'name': item.name,
            'quantity': item.quantity,
            'price': item.price,
            'extras': item.extras if hasattr(item, 'extras') else [],
            'notes': item.notes if hasattr(item, 'notes') else None
        })

    return jsonify({
        'success': True,
        'session_id': session_id,
        'items': items,
        'total': context.order_total,
        'item_count': len(items)
    })


# ============================================================
# PANEL DE FEEDBACK
# ============================================================

@app.route('/feedback', methods=['GET'])
def feedback_panel():
    """Sirve el panel de revisión de feedback"""
    return render_template('feedback_panel.html')


# ============================================================
# INICIALIZACIÓN
# ============================================================

def print_startup_banner():
    """Imprime banner de inicio"""
    components = []
    if METRICS_AVAILABLE:
        components.append('Prometheus Metrics')
    if EVENT_BUS_AVAILABLE:
        components.append('Redis Event Bus')
    if TRAINING_AVAILABLE:
        components.append('Training Pipeline')
    if ADMIN_AGENT_AVAILABLE:
        components.append('Admin Agent')
    if SECURITY_AGENT_AVAILABLE:
        components.append('Security Agent')

    components_str = ', '.join(components) if components else 'Basic'

    # Información multi-tenant
    tenants = tenant_manager.list_tenants()
    tenant_info = f"{len(tenants)} tenant(s) activo(s)" if tenants else "Modo single-tenant"

    print(f"""
================================================================
  SALES AGENT FSM - v2.3 (Multi-Tenant + Auto-Setup)
  Sistema con Máquina de Estados Finitos + Soporte Multi-Tenant
================================================================

  Componentes Activos: {components_str}

  ✅ NUEVO: Multi-Tenant System
    - Múltiples tiendas en una instancia
    - FSM personalizado por tipo de negocio
    - Configuración independiente por tenant
    - {tenant_info}

  Características v2.3:
    - Enhanced Classifier (NLU + Regex híbrido)
    - Product Validator con búsqueda semántica
    - Semantic Search para productos
    - Redis Event Bus para comunicación
    - Prometheus Metrics para monitoreo
    - Feedback Loop para aprendizaje continuo
    - Training Pipeline para reentrenamiento automático
    - Admin Agent con voz y texto para administradores
    - ✅ Envío automático de pedidos a cocina
    - ✅ Setup automático integrado
    - ✅ Mejora continua semanal (FSM Optimizer)

  Endpoints Principales:
    - POST /api/voice/process - Procesar audio (envía a cocina al confirmar)
    - POST /api/text/process - Procesar texto (envía a cocina al confirmar)
    - GET  /api/session/{{id}}/context - Ver contexto
    - GET  /api/session/{{id}}/metrics - Ver métricas
    - GET  /api/fsm/status - Estado del FSM

  Endpoints de Pedidos (NUEVO):
    - POST /api/order/submit - Enviar pedido manualmente a cocina
    - GET  /api/order/cart/{{id}} - Ver carrito de una sesión

  Endpoints de Monitoreo:
    - GET  /api/health - Health check extendido
    - GET  /api/metrics - Métricas Prometheus

  Endpoints de Feedback:
    - GET  /feedback - Panel de revisión
    - GET  /api/feedback/stats - Estadísticas
    - GET  /api/feedback/pending - Pendientes

  Endpoints de Training:
    - POST /api/training/start - Iniciar reentrenamiento
    - GET  /api/training/status - Estado del pipeline
    - GET  /api/training/stats - Estadísticas de datos
    - GET  /api/training/config - Configuración actual

  Endpoints de Admin Agent:
    - POST /api/admin/session - Crear sesión admin
    - POST /api/admin/message - Procesar mensaje texto
    - POST /api/admin/voice - Procesar mensaje voz
    - GET  /api/admin/session/{{id}} - Estado sesión
    - GET  /api/admin/metrics - Métricas del agente

  Endpoints Multi-Tenant (NUEVO):
    - GET  /api/tenants - Listar todos los tenants activos
    - GET  /api/tenants/{{id}} - Información de un tenant
    - GET  /api/tenants/{{id}}/products - Productos de un tenant
    - GET  /api/tenants/by-phone/{{phone}} - Buscar tenant por teléfono

================================================================
""")


# ============================================================
# ENDPOINTS MULTI-TENANT (v2.2)
# ============================================================

@app.route('/api/tenants', methods=['GET'])
def list_tenants():
    """
    Lista todos los tenants activos

    Returns:
        JSON con lista de tenants
    """
    try:
        tenants = tenant_manager.list_tenants()

        tenants_data = []
        for tenant in tenants:
            tenants_data.append({
                'tenant_id': tenant.tenant_id,
                'name': tenant.name,
                'type': tenant.type,
                'phone': tenant.phone,
                'active': tenant.active
            })

        return jsonify({
            'success': True,
            'count': len(tenants_data),
            'tenants': tenants_data
        })

    except Exception as e:
        logger.error(f"[MULTI-TENANT] Error listando tenants: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/tenants/<tenant_id>', methods=['GET'])
def get_tenant_info(tenant_id: str):
    """
    Obtiene información de un tenant específico

    Args:
        tenant_id: ID del tenant

    Returns:
        JSON con información del tenant
    """
    try:
        tenant_config = tenant_manager.get_tenant(tenant_id)

        if not tenant_config:
            return jsonify({
                'success': False,
                'error': f'Tenant {tenant_id} not found'
            }), 404

        return jsonify({
            'success': True,
            'tenant': {
                'tenant_id': tenant_config.tenant_id,
                'name': tenant_config.name,
                'type': tenant_config.type,
                'phone': tenant_config.phone,
                'active': tenant_config.active,
                'fsm_config': tenant_config.fsm_config,
                'business_rules': tenant_config.business_rules,
                'branding': tenant_config.branding
            }
        })

    except Exception as e:
        logger.error(f"[MULTI-TENANT] Error obteniendo tenant {tenant_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/tenants/<tenant_id>/products', methods=['GET'])
def get_tenant_products(tenant_id: str):
    """
    Obtiene productos de un tenant

    Args:
        tenant_id: ID del tenant

    Query params:
        category: Categoría opcional para filtrar

    Returns:
        JSON con lista de productos
    """
    try:
        category = request.args.get('category')

        products = tenant_manager.get_products(tenant_id, category)

        return jsonify({
            'success': True,
            'tenant_id': tenant_id,
            'count': len(products),
            'products': products
        })

    except Exception as e:
        logger.error(f"[MULTI-TENANT] Error obteniendo productos de {tenant_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/tenants/by-phone/<phone>', methods=['GET'])
def get_tenant_by_phone(phone: str):
    """
    Identifica tenant por número de teléfono

    Args:
        phone: Número de teléfono del negocio

    Returns:
        JSON con información del tenant
    """
    try:
        tenant_config = tenant_manager.get_tenant_by_phone(phone)

        if not tenant_config:
            return jsonify({
                'success': False,
                'error': f'No tenant found for phone {phone}'
            }), 404

        return jsonify({
            'success': True,
            'tenant': {
                'tenant_id': tenant_config.tenant_id,
                'name': tenant_config.name,
                'type': tenant_config.type,
                'phone': tenant_config.phone
            }
        })

    except Exception as e:
        logger.error(f"[MULTI-TENANT] Error buscando tenant por teléfono {phone}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================================
# ENDPOINTS DE CATEGORÍAS MULTI-TENANT (v2.3)
# ============================================================

@app.route('/api/v1/categories', methods=['GET'])
def get_categories():
    """
    Obtiene categorías para un tenant específico.
    Multi-tenant ready desde el inicio.

    Query params:
        tenant_id: ID del tenant (requerido)
        parent: Nombre de categoría padre para obtener subcategorías (opcional)

    Returns:
        JSON con categorías principales o subcategorías
    """
    try:
        tenant_id = request.args.get('tenant_id')

        if not tenant_id:
            return jsonify({
                'success': False,
                'error': 'tenant_id is required'
            }), 400

        # Verificar que el tenant existe
        tenant_config = tenant_manager.get_tenant(tenant_id)
        if not tenant_config:
            return jsonify({
                'success': False,
                'error': f'Tenant {tenant_id} not found'
            }), 404

        # Obtener categorías del tenant
        categories = tenant_manager.get_categories(tenant_id)

        # Filtrar por parent si se especifica
        parent = request.args.get('parent')
        if parent:
            # Buscar la categoría padre por nombre
            main_cat = next(
                (c for c in categories.get("main_categories", [])
                 if c.get("name", "").lower() == parent.lower() or
                    c.get("slug", "").lower() == parent.lower()),
                None
            )

            if main_cat:
                # Retornar subcategorías de esta categoría
                subcats = [
                    c for c in categories.get("subcategories", [])
                    if c.get("parent_id") == main_cat.get("id")
                ]
                return jsonify({
                    'success': True,
                    'tenant_id': tenant_id,
                    'parent_category': main_cat,
                    'count': len(subcats),
                    'subcategories': subcats
                })
            else:
                return jsonify({
                    'success': False,
                    'error': f'Category {parent} not found'
                }), 404

        # Retornar categorías principales
        return jsonify({
            'success': True,
            'tenant_id': tenant_id,
            'business_type': tenant_config.type,
            'count': len(categories.get("main_categories", [])),
            'main_categories': categories.get("main_categories", []),
            'subcategories_count': len(categories.get("subcategories", []))
        })

    except Exception as e:
        logger.error(f"[CATEGORIES] Error obteniendo categorías: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/v1/products', methods=['GET'])
def get_products_v1():
    """
    Obtiene productos con filtros avanzados.
    Multi-tenant ready desde el inicio.

    Query params:
        tenant_id: ID del tenant (requerido)
        category_id: ID de categoría principal para filtrar (opcional)
        subcategory_id: ID de subcategoría para filtrar (opcional)
        search: Término de búsqueda en nombre/descripción (opcional)
        limit: Límite de resultados (default: 50)
        offset: Offset para paginación (default: 0)

    Returns:
        JSON con lista de productos filtrados
    """
    try:
        tenant_id = request.args.get('tenant_id')

        if not tenant_id:
            return jsonify({
                'success': False,
                'error': 'tenant_id is required'
            }), 400

        # Verificar que el tenant existe
        tenant_config = tenant_manager.get_tenant(tenant_id)
        if not tenant_config:
            return jsonify({
                'success': False,
                'error': f'Tenant {tenant_id} not found'
            }), 404

        # Obtener todos los productos del tenant
        all_products = tenant_manager.get_products(tenant_id)

        # Aplicar filtros
        filtered_products = all_products

        # Filtrar por categoría principal
        category_id = request.args.get('category_id', type=int)
        if category_id:
            filtered_products = [
                p for p in filtered_products
                if p.get('main_category_id') == category_id
            ]

        # Filtrar por subcategoría
        subcategory_id = request.args.get('subcategory_id', type=int)
        if subcategory_id:
            filtered_products = [
                p for p in filtered_products
                if p.get('subcategory_id') == subcategory_id
            ]

        # Filtrar por búsqueda
        search = request.args.get('search', '').lower().strip()
        if search:
            filtered_products = [
                p for p in filtered_products
                if search in p.get('name', '').lower() or
                   search in p.get('description', '').lower() or
                   search in p.get('generic_name', '').lower() or
                   search in p.get('active_ingredient', '').lower()
            ]

        # Paginación
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)

        total_count = len(filtered_products)
        paginated_products = filtered_products[offset:offset + limit]

        return jsonify({
            'success': True,
            'tenant_id': tenant_id,
            'total_count': total_count,
            'count': len(paginated_products),
            'limit': limit,
            'offset': offset,
            'has_more': (offset + limit) < total_count,
            'products': paginated_products
        })

    except Exception as e:
        logger.error(f"[PRODUCTS] Error obteniendo productos: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/v1/tenant/<tenant_id>/settings', methods=['GET'])
def get_tenant_settings(tenant_id: str):
    """
    Obtiene la configuración/settings de un tenant específico.

    Args:
        tenant_id: ID del tenant

    Returns:
        JSON con configuración del tenant (branding, business_rules, features)
    """
    try:
        # Obtener settings del tenant
        settings = tenant_manager.get_tenant_settings(tenant_id)

        if not settings:
            return jsonify({
                'success': False,
                'error': f'Tenant {tenant_id} not found'
            }), 404

        return jsonify({
            'success': True,
            'tenant_id': tenant_id,
            'settings': settings
        })

    except Exception as e:
        logger.error(f"[SETTINGS] Error obteniendo settings de {tenant_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================================
# INICIALIZACIÓN
# ============================================================

# Inicializar al arrancar
@app.before_request
async def ensure_initialized():
    """Asegura que FSM esté inicializado"""
    if fsm is None:
        await initialize_fsm()


if __name__ == '__main__':
    print_startup_banner()

    # Configuración desde variables de entorno
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'

    # Inicializar FSM
    asyncio.get_event_loop().run_until_complete(initialize_fsm())

    # Arrancar servidor
    app.run(host=host, port=port, debug=debug)
