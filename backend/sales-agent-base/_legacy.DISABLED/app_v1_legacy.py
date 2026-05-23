"""
================================================================================
VOICE RESTAURANT ASSISTANT - MAIN APPLICATION
================================================================================
Servidor Flask que integra voz con sistema de restaurante
================================================================================
"""

import asyncio
import logging
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
import tempfile
import yaml

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Importar módulos del proyecto
from ..core.config import settings
from ..core.session_manager import get_session_manager
from ..restaurant.api_client import get_restaurant_client
from ..nlp.intent_recognizer import get_intent_recognizer, Intent
from ..voice.stt_handler import get_stt_handler
from ..voice.tts_handler import get_tts_handler
from ..analytics.sales_intelligence import get_sales_intelligence

# Crear app Flask
app = Flask(__name__,
            template_folder=str(settings.PROJECT_ROOT / "templates"),
            static_folder=str(settings.PROJECT_ROOT / "static"))

app.config['MAX_CONTENT_LENGTH'] = settings.MAX_AUDIO_SIZE_MB * 1024 * 1024

# Habilitar CORS
CORS(app)

# Configurar carpeta temporal
UPLOAD_FOLDER = settings.TEMP_DIR
UPLOAD_FOLDER.mkdir(exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Inicializar componentes
session_manager = get_session_manager()
restaurant_client = get_restaurant_client()
intent_recognizer = get_intent_recognizer()
stt_handler = get_stt_handler()
tts_handler = get_tts_handler()

# Variable global para SalesIntelligence (se inicializa lazy)
sales_intelligence = None

async def get_sales_intel():
    """Obtener instancia de SalesIntelligence (lazy initialization)"""
    global sales_intelligence
    if sales_intelligence is None:
        try:
            sales_intelligence = await get_sales_intelligence()
            logger.info("SalesIntelligence inicializado correctamente")
        except Exception as e:
            logger.warning(f"No se pudo inicializar SalesIntelligence: {e}")
    return sales_intelligence

# Cargar información de porciones
PORTION_INFO = {}
try:
    portion_file = settings.PROJECT_ROOT / "config" / "portion_info.yaml"
    if portion_file.exists():
        with open(portion_file, 'r', encoding='utf-8') as f:
            PORTION_INFO = yaml.safe_load(f)
        logger.info(f"Información de porciones cargada: {len(PORTION_INFO.get('portions', {}))} productos")
except Exception as e:
    logger.warning(f"No se pudo cargar portion_info.yaml: {e}")

# Variable para recordar último producto mencionado por sesión
LAST_PRODUCT_CONTEXT = {}

# Variable para recordar la categoría activa por sesión (MICRO-EMBUDO)
ACTIVE_CATEGORY_CONTEXT = {}

def get_portion_info(product_name: str) -> dict:
    """Obtener información de porciones para un producto"""
    product_lower = product_name.lower()
    for portion_type, info in PORTION_INFO.get('portions', {}).items():
        for keyword in info.get('keywords', []):
            if keyword in product_lower:
                return info
    return None

def is_portion_question(text: str) -> bool:
    """Detectar si es una pregunta sobre porciones/cantidades"""
    text_lower = text.lower()
    keywords = PORTION_INFO.get('portion_question_keywords', [])
    return any(kw in text_lower for kw in keywords)

def build_portion_response(product_name: str, price: float) -> str:
    """Construir respuesta vendedora sobre porciones"""
    info = get_portion_info(product_name)
    if not info:
        return f"La orden de {product_name} cuesta {price}. ¿Te la preparo?"

    qty = info['default_quantity']
    unit = info['unit_name']
    unit_singular = info['unit_name_singular']
    extra_price = info.get('price_per_extra', 0)
    upsell_qty = info.get('upsell_suggestion', qty)

    if extra_price > 0:
        extra_for_upsell = (upsell_qty - qty) * extra_price
        response = f"¡La orden de {product_name} trae {qty} {unit} por {price}! "
        response += f"Cada {unit_singular} extra son {extra_price}. "
        response += f"Por {extra_for_upsell} más te pongo {upsell_qty} en total. ¿Cuántos van a ser?"
    elif info.get('has_upgrade'):
        upgrade_name = info.get('upgrade_name', 'versión premium')
        upgrade_price = info.get('upgrade_price', 0)
        response = f"¡La orden de {product_name} viene por {price}! "
        response += f"Por solo {upgrade_price} más la hacemos {upgrade_name}. ¿Le entramos?"
    elif info.get('is_shareable'):
        response = f"¡{product_name} es una porción generosa para compartir por {price}! ¿Te lo preparo?"
    else:
        response = f"¡La orden de {product_name} trae {qty} {unit} por {price}! ¿Te la preparo?"

    return response

logger.info("=" * 60)
logger.info("VOICE RESTAURANT ASSISTANT - INICIADO")
logger.info("=" * 60)

# ============================================================================
# WARMUP - Precalentar modelos para reducir latencia en primera petición
# ============================================================================
async def warmup_models():
    """Precalentar modelos LLM para reducir latencia"""
    try:
        await intent_recognizer.warmup()
        logger.info("[WARMUP] Modelos precalentados correctamente")
    except Exception as e:
        logger.warning(f"[WARMUP] Error precalentando: {e}")

# Ejecutar warmup al inicio
import threading
def _run_warmup():
    import asyncio
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(warmup_models())
    except Exception as e:
        logger.warning(f"[WARMUP] Error en thread: {e}")

warmup_thread = threading.Thread(target=_run_warmup, daemon=True)
warmup_thread.start()
logger.info("[WARMUP] Iniciando precalentamiento en background...")


def allowed_file(filename):
    """Verificar si el archivo tiene una extensión permitida"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in settings.allowed_audio_extensions


# ============================================================================
# RUTAS - PÁGINAS WEB
# ============================================================================

@app.route('/')
def index():
    """Página principal"""
    return render_template('index.html')


@app.route('/static/<path:filename>')
def serve_static(filename):
    """Servir archivos estáticos"""
    return send_from_directory('static', filename)


@app.route('/audio/<filename>')
def serve_audio(filename):
    """Servir archivos de audio generados"""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


# ============================================================================
# API - SESIONES
# ============================================================================

@app.route('/api/session/init', methods=['POST'])
async def init_session():
    """
    Inicializar sesión de usuario con mesa

    Body:
    {
        "table_id": 5,
        "table_number": 5  // opcional
    }
    """
    try:
        data = request.json
        table_id = data.get('table_id')

        if not table_id:
            return jsonify({'error': 'table_id requerido'}), 400

        # Obtener información de la mesa
        table_info = await restaurant_client.get_table(table_id)
        table_number = table_info.get('table_number') if table_info else None

        # Crear sesión
        session = session_manager.create_session(
            table_id=table_id,
            table_number=table_number
        )

        logger.info(f"Sesión iniciada: {session.session_id} (mesa {table_id})")

        return jsonify({
            'success': True,
            'session_id': session.session_id,
            'table_id': table_id,
            'table_number': table_number,
            'message': f'Sesión iniciada para mesa {table_number or table_id}'
        })

    except Exception as e:
        logger.error(f"Error iniciando sesión: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/session/<session_id>', methods=['GET'])
def get_session_info(session_id):
    """Obtener información de una sesión"""
    try:
        session = session_manager.get_session(session_id)

        if not session:
            return jsonify({'error': 'Sesión no encontrada o expirada'}), 404

        return jsonify(session.to_dict())

    except Exception as e:
        logger.error(f"Error obteniendo sesión: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================================================
# API - PROCESAMIENTO DE VOZ
# ============================================================================

@app.route('/api/voice/process', methods=['POST'])
async def process_voice():
    """
    Procesar audio del usuario y ejecutar acción en restaurante

    ESTRATEGIA HÍBRIDA:
    - Genera TTS solo cuando el usuario interactúa por voz (ahorro 70-85%)
    - Si force_audio=false, solo responde con texto
    - Acciones críticas siempre generan audio para confirmación

    Form Data:
        - audio: Archivo de audio
        - session_id: ID de sesión (requerido)
        - force_audio: "true" o "false" (opcional, default: true)

    Returns:
        {
            "success": true,
            "transcription": "Quiero una pizza margarita",
            "intent": "create_order",
            "response": "Perfecto, he ordenado una pizza margarita...",
            "audio_url": "/audio/response_xxx.mp3",  // solo si se generó audio
            "order_id": 123  // si se creó orden
        }
    """
    try:
        # Verificar sesión
        session_id = request.form.get('session_id')
        if not session_id:
            return jsonify({'error': 'session_id requerido'}), 400

        session = session_manager.get_session(session_id)
        if not session:
            return jsonify({'error': 'Sesión no encontrada o expirada'}), 401

        # Verificar archivo de audio
        if 'audio' not in request.files:
            return jsonify({'error': 'No audio file provided'}), 400

        audio_file = request.files['audio']

        if audio_file.filename == '' or not allowed_file(audio_file.filename):
            return jsonify({'error': 'Invalid audio file'}), 400

        # Guardar archivo temporalmente
        filename = secure_filename(audio_file.filename)
        temp_input_path = app.config['UPLOAD_FOLDER'] / filename
        audio_file.save(str(temp_input_path))

        # Leer audio
        with open(temp_input_path, 'rb') as f:
            audio_data = f.read()

        logger.info(f"[Sesión {session_id}] Audio recibido: {len(audio_data)} bytes")

        # 1. TRANSCRIBIR (STT)
        logger.info("[1/5] Transcribiendo...")
        transcription = await stt_handler.transcribe_bytes(audio_data, convert_to_wav=False)

        if not transcription or not transcription.strip():
            logger.warning("Transcripción vacía")
            return jsonify({'error': 'No se detectó voz clara'}), 400

        logger.info(f"[✓] Transcripción: '{transcription}'")

        # Agregar a historial de conversación
        session.add_message('user', transcription)

        # PRE-CHECK: Detectar preguntas de porción/cantidad
        # Esto tiene prioridad sobre la detección de intención normal
        if is_portion_question(transcription):
            logger.info("[PORCIÓN] Detectada pregunta sobre cantidad/porciones")

            # Obtener menú para buscar el producto
            menu = await restaurant_client.get_menu()

            # Buscar producto en la transcripción o usar contexto
            found_product = None
            transcription_lower = transcription.lower()

            # Primero buscar en la transcripción actual
            for p in menu:
                portion_info = get_portion_info(p['name'])
                if p['name'].lower() in transcription_lower:
                    found_product = p
                    break
                elif portion_info:
                    keywords = portion_info.get('keywords', [])
                    if any(keyword in transcription_lower for keyword in keywords):
                        found_product = p
                        break

            # Si no encontró, usar el último producto del contexto
            if not found_product and session_id in LAST_PRODUCT_CONTEXT:
                last_product_name = LAST_PRODUCT_CONTEXT[session_id]
                for p in menu:
                    if p['name'].lower() == last_product_name.lower():
                        found_product = p
                        break

            if found_product:
                response_text = build_portion_response(found_product['name'], float(found_product.get('price', 0)))
                logger.info(f"[📝] Respuesta de porción: {response_text}")

                # Generar audio y responder
                logger.info("[4/5] Generando audio (estrategia híbrida activada)...")
                audio_filename = f"response_{session_id}_voice.mp3"
                audio_path = app.config['UPLOAD_FOLDER'] / audio_filename

                success = await tts_handler.synthesize_to_file(response_text, audio_path)

                if success:
                    logger.info("[✓] Audio generado")
                    session.add_message('assistant', response_text)

                    return jsonify({
                        'success': True,
                        'transcription': transcription,
                        'intent': 'portion_inquiry',
                        'response': response_text,
                        'audio_url': f"/audio/{audio_filename}"
                    })
            # Si no encontró producto, continuar con flujo normal

        # 2. RECONOCER INTENCIÓN
        logger.info("[2/5] Reconociendo intención...")

        # Obtener menú para contexto
        menu = await restaurant_client.get_menu()
        menu_names = [p['name'] for p in menu]

        # Preparar contexto con historial de conversación
        recent_history = session.get_recent_history(limit=5)
        conversation_context = [
            {"role": msg.role, "content": msg.content}
            for msg in recent_history[:-1]  # Excluir el mensaje actual que acabamos de agregar
        ]

        context = {
            'has_active_order': bool(session.current_order_draft),
            'menu_items': menu_names[:20],  # Top 20 para no saturar
            'conversation_history': conversation_context
        }

        intent_result = await intent_recognizer.recognize(transcription, context=context)
        detected_intent = intent_result.get('intent')
        entities = intent_result.get('entities', {})

        logger.info(f"[✓] Intención: {detected_intent}")

        # 3. EJECUTAR ACCIÓN SEGÚN INTENCIÓN
        logger.info("[3/5] Ejecutando acción...")
        response_text = ""
        order_data = None

        if detected_intent == Intent.CREATE_ORDER or detected_intent == Intent.ADD_ITEM:
            # Extraer productos mencionados
            items = await intent_recognizer.extract_products_and_quantities(
                transcription,
                menu,
                conversation_history=conversation_context  # Pasar historial para inferir productos del contexto
            )

            if items:
                # Crear orden en el restaurante CON PRECIO INCLUYENDO MODIFICADORES
                order_items = []
                for item in items:
                    # Calcular precio unitario con modificadores
                    unit_price = item.get('total_price', item.get('base_price', 0))

                    # Construir notas con todos los modificadores
                    notes_parts = []
                    for mod in item.get('modifiers', []):
                        mod_text = mod['name']
                        if mod.get('price', 0) > 0:
                            mod_text += f" (+${mod['price']})"
                        notes_parts.append(mod_text)

                    # Agregar notas adicionales si existen
                    if item.get('notes') and not any(item['notes'] in p for p in notes_parts):
                        notes_parts.append(item['notes'])

                    order_items.append({
                        "product_id": item['product_id'],
                        "quantity": item['quantity'],
                        "price": unit_price,  # Precio con modificadores
                        "notes": ", ".join(notes_parts) if notes_parts else ""
                    })

                order = await restaurant_client.create_order(
                    table_id=session.table_id,
                    items=order_items,
                    notes=f"Orden por voz - Sesión {session_id}"
                )

                order_data = order

                # Generar respuesta (TONO PROFESIONAL) CON MODIFICACIONES Y PRECIOS
                items_descriptions = []
                for item in items:
                    desc = f"{item['quantity']} {item['product_name']}"

                    # Agregar modificaciones si existen
                    modifiers = item.get('modifiers', [])
                    if modifiers:
                        mod_texts = []
                        for mod in modifiers:
                            mod_text = mod['name']
                            if mod.get('price', 0) > 0:
                                mod_text += f" (+${mod['price']})"
                            mod_texts.append(mod_text)
                        desc += f" ({', '.join(mod_texts)})"

                    # Mostrar precio si tiene modificadores con costo
                    modifiers_price = item.get('modifiers_price', 0)
                    if modifiers_price > 0:
                        desc += f" - ${item['total_price']:.0f}"

                    items_descriptions.append(desc)

                items_text = ", ".join(items_descriptions)

                # MEJORA: Upselling inteligente con SalesIntelligence
                recommendation = ""
                intel = await get_sales_intel()

                if intel:
                    try:
                        # Preparar items ordenados para análisis
                        ordered_items_for_intel = []
                        for item in items:
                            for p in menu:
                                if p['id'] == item['product_id']:
                                    ordered_items_for_intel.append({
                                        'product_id': p['id'],
                                        'name': p['name'],
                                        'category': p.get('category', {}).get('name', '')
                                    })
                                    break

                        # Obtener sugerencias de upselling inteligentes
                        upsell_suggestions = await intel.get_upsell_suggestions(
                            ordered_items=ordered_items_for_intel,
                            menu=menu
                        )

                        if upsell_suggestions:
                            # Usar el primer pitch de upselling
                            _, pitch = upsell_suggestions[0]
                            recommendation = f" {pitch}"
                            logger.info(f"[INTEL] Upsell suggestion: {pitch}")

                    except Exception as e:
                        logger.warning(f"Error en upsell intelligence: {e}")

                # Fallback: upselling manual si no hay sugerencia inteligente
                if not recommendation:
                    ordered_categories = set()
                    for item in items:
                        for p in menu:
                            if p['id'] == item['product_id']:
                                cat_name = p.get('category', {}).get('name', '').lower()
                                ordered_categories.add(cat_name)
                                break

                    if 'platos fuertes' in ordered_categories or 'entradas' in ordered_categories:
                        bebidas = [p for p in menu if 'bebida' in p.get('category', {}).get('name', '').lower()]
                        if bebidas:
                            recommendation = f" ¿Y para tomar? La limonada está recién hecha."
                    elif 'bebidas' in ordered_categories:
                        platos = [p for p in menu if 'platos fuertes' in p.get('category', {}).get('name', '').lower()]
                        if platos:
                            popular_plato = [p for p in platos if 'popular' in p.get('tags', [])]
                            if popular_plato:
                                recommendation = f" ¿Algo para acompañar? {popular_plato[0]['name']} está volando."
                            else:
                                recommendation = f" ¿Algo para acompañar?"

                response_text = f"¡Excelente elección! {items_text} anotados.{recommendation}"

            else:
                response_text = "Disculpa, no logré identificar el producto. ¿Podrías repetirlo o te ayudo a ver el menú?"

        elif detected_intent == Intent.VIEW_MENU:
            # Mostrar categorías del menú (MÁXIMO 2-3 OPCIONES con razón)
            categories_dict = {}
            for p in menu:
                cat_name = p.get('category', {}).get('name', 'General')
                if cat_name not in categories_dict:
                    categories_dict[cat_name] = []
                categories_dict[cat_name].append(p)

            # Dar máximo 3 categorías con estilo vendedor
            categories_list = list(categories_dict.keys())[:3]
            popular = [p for p in menu if 'popular' in p.get('tags', [])][:1]
            popular_name = popular[0]['name'] if popular else "nuestros platillos estrella"

            if len(categories_list) <= 2:
                response_text = f"¡Tenemos de todo! {' y '.join(categories_list)}. {popular_name} está volando, ¿te lo preparo?"
            else:
                response_text = f"¡Tenemos {categories_list[0]}, {categories_list[1]} y {categories_list[2]}! Te recomiendo {popular_name}. ¿Te lo preparo?"

        elif detected_intent == Intent.VIEW_CATEGORY:
            # Mostrar productos de una categoría específica O buscar por nombre de producto
            search_term = entities.get('category', '').lower()

            # ============================================================
            # MICRO-EMBUDO: Guardar categoría activa para contexto
            # ============================================================
            # Esto permite que preguntas como "¿cuál me recomiendas?"
            # se respondan dentro de esta categoría
            if search_term:
                ACTIVE_CATEGORY_CONTEXT[session_id] = {
                    'category': search_term,
                    'timestamp': __import__('time').time()
                }
                logger.info(f"[MICRO-EMBUDO] Categoría activa guardada: {search_term}")

            # MEJORA: Mapeo de sinónimos comunes
            synonym_map = {
                'refresco': 'bebida',
                'refrescos': 'bebida',
                'soda': 'bebida',
                'gaseosa': 'bebida',
                'pocas': 'papas',
                'papitas': 'papas',
                'papas fritas': 'papas',
                'cerveza': 'bebida',
                'alcohol': 'bebida',
                'vino': 'bebida',
                'chela': 'bebida',
                'coca': 'coca-cola',
                'pepsi': 'coca-cola',
                'hamburguesas': 'hamburguesa',
                'burger': 'hamburguesa',
                'burgers': 'hamburguesa',
                'tacos': 'taco',
                'taquito': 'taco',
                'taquitos': 'taco',
                'postre': 'postres',
                'dulce': 'postres',
                'dulces': 'postres',
                'entrada': 'entradas',
                'botana': 'entradas',
                'botanas': 'entradas'
            }

            # Aplicar sinónimo si existe
            original_search = search_term
            search_term = synonym_map.get(search_term, search_term)

            # ============================================================
            # DETECCIÓN INTELIGENTE DE PRODUCTO ESPECÍFICO
            # ============================================================
            # Busca en el menú usando palabras clave distintivas de la transcripción
            # Tolera errores de transcripción (STT) usando variantes conocidas
            transcription_lower = transcription.lower()
            exact_product_match = None

            # Palabras clave que identifican variantes de productos
            # Incluye variantes por errores comunes de Deepgram STT
            # IMPORTANTE: Las keywords deben ser específicas para evitar falsos positivos
            product_keywords = {
                # === TACOS (ID 15-18) ===
                'pastor': ['pastor', 'pastol', 'pastos', 'al pastor'],
                'asada': ['carne asada', 'asada', 'azada'],
                'chorizo': ['chorizo', 'chorizzo', 'choriz'],
                'suadero': ['suadero', 'suadera', 'asadero', 'zuadero', 'suader', 'zuader'],
                # === HAMBURGUESAS (ID 19-22) ===
                'clásica': ['clásica', 'clasica', 'hamburguesa clasica', 'hamburguesa clásica'],
                'doble': ['doble carne', 'doble', 'dobles'],
                'bbq': ['bbq', 'barbacoa', 'barbeque', 'barbecue', 'barbiquiu'],
                'tocino': ['tocino', 'bacon', 'tocino especial'],
                # === ENTRADAS (ID 11-14) ===
                'guacamole': ['guacamole', 'guaca', 'wakamole'],
                'alitas': ['alitas', 'alas', 'bufalo', 'búfalo', 'buffalo'],
                'nachos': ['nachos', 'nacho', 'supreme'],
                'quesadilla': ['quesadilla', 'quesadillas'],
                # === PLATOS FUERTES ===
                'verdes': ['enchiladas verdes', 'verdes'],
                'rojas': ['enchiladas rojas', 'rojas'],
                'costillas': ['costillas', 'costilla', 'ribs'],
                'pechuga': ['pechuga', 'parrilla', 'pollo a la parrilla'],
                'pozole': ['pozole', 'posole', 'pozole rojo', 'pozole verde', 'un pozole'],
                'mole': ['mole', 'pollo con mole', 'mole poblano'],
                'chilaquiles': ['chilaquiles', 'chilaquil'],
                'birria': ['birria', 'consomé', 'consome'],
                'carnitas': ['carnitas', 'carnita'],
                'barbacoa': ['barbacoa', 'barbacha'],
                # === BEBIDAS ===
                'limón': ['agua de limón', 'limon', 'limón'],
                'jamaica': ['jamaica', 'agua de jamaica'],
                'horchata': ['horchata', 'orchata', 'agua de horchata'],
                'coca': ['coca', 'coca-cola', 'cocacola', 'cola'],
                'corona': ['corona', 'cerveza corona'],
                'limonada': ['limonada mineral', 'limonada'],
                # === POSTRES (ID 33-36) ===
                'chocolate': ['pastel de chocolate', 'pastel chocolate'],
                'flan': ['flan', 'napolitano', 'flan napolitano'],
                'churros': ['churros', 'churro'],
                'helado': ['helado', 'nieve', 'helado artesanal'],
                # === COMPLEMENTOS (ID 37-40) ===
                'papas': ['papas fritas', 'papas'],
                'aros': ['aros de cebolla', 'aros', 'onion rings'],
                'elote': ['elote asado', 'elote'],
            }

            # Buscar palabra clave de variante en la transcripción
            found_keyword = None
            for keyword, variants in product_keywords.items():
                for variant in variants:
                    if variant in transcription_lower:
                        found_keyword = keyword
                        logger.info(f"[🔍] Palabra clave detectada: '{variant}' -> keyword '{keyword}'")
                        break
                if found_keyword:
                    break

            # Si encontramos palabra clave, buscar producto que la contenga
            if found_keyword:
                for p in menu:
                    product_name_lower = p['name'].lower()
                    if found_keyword in product_name_lower:
                        exact_product_match = p
                        logger.info(f"[🎯] Producto encontrado por keyword: '{found_keyword}' -> {p['name']} (ID: {p['id']})")
                        break

            if exact_product_match:
                visual_data = {
                    "type": "product_detail",
                    "product": {
                        "id": exact_product_match['id'], "name": exact_product_match['name'],
                        "description": exact_product_match.get('description', ''),
                        "price": float(exact_product_match.get('price', 0)),
                        "image_url": exact_product_match.get('image_url'),
                        "preparation_time": exact_product_match.get('preparation_time_minutes', 0),
                        "category": exact_product_match.get('category', {}).get('name', ''),
                        "category_id": exact_product_match.get('category_id') or exact_product_match.get('category', {}).get('id')
                    }
                }
                order_data = {"visual_data": visual_data}
                LAST_PRODUCT_CONTEXT[session_id] = exact_product_match['name']
                desc = exact_product_match.get('description', '')
                price = exact_product_match.get('price', 0)
                short_desc = desc.split('.')[0] if desc else 'Delicioso'
                response_text = f"¡{exact_product_match['name']}! {short_desc}. Solo {price} pesos. ¿Te lo preparo?"
            else:
                category_products = [
                    p for p in menu
                    if search_term in p.get('category', {}).get('name', '').lower()
                ]
                if not category_products:
                    category_products = [
                        p for p in menu
                        if search_term in p['name'].lower()
                    ]

            if exact_product_match:
                # Ya se generó respuesta arriba, no hacer nada más
                pass
            elif category_products:
                # Preparar datos visuales
                display_name = category_products[0].get('category', {}).get('name', search_term) if len(category_products) > 1 else category_products[0]['name']

                visual_data = {
                    "type": "product_list",
                    "category": display_name,
                    "products": [
                        {
                            "id": p['id'],
                            "name": p['name'],
                            "description": p.get('description', ''),
                            "price": float(p.get('price', 0)),
                            "image_url": p.get('image_url'),
                            "preparation_time": p.get('preparation_time_minutes', 0)
                        }
                        for p in category_products[:10]  # Max 10 productos
                    ]
                }
                order_data = {"visual_data": visual_data}

                # Guardar contexto del producto para preguntas de seguimiento
                LAST_PRODUCT_CONTEXT[session_id] = category_products[0]['name']

                if len(category_products) == 1:
                    # Respuesta vendedora - producto único
                    prod = category_products[0]
                    response_text = f"¡{prod['name']} es excelente! Solo {prod.get('price', 0)} pesos. ¿Te lo preparo?"
                elif len(category_products) == 2:
                    # Dos opciones - destacar la premium primero
                    p1, p2 = category_products[0], category_products[1]
                    response_text = f"¡Te recomiendo {p1['name']}! Es de los favoritos. También tenemos {p2['name']}. ¿Cuál te preparo?"
                else:
                    # 3+ opciones - estilo vendedor con producto estrella
                    product_names = [p['name'] for p in category_products]
                    star_product = product_names[0]  # El primero como estrella
                    if len(product_names) <= 6:
                        others = ', '.join(product_names[1:-1]) + f" y {product_names[-1]}"
                        response_text = f"¡{star_product} es el favorito! También tenemos {others}. ¿Cuántos te pongo?"
                    else:
                        others = ', '.join(product_names[1:4])
                        remaining = len(product_names) - 4
                        response_text = f"¡{star_product} está volando hoy! También {others} y {remaining} más. ¿Con cuál empezamos?"
            else:
                # No encontrado - Ofrecer alternativa vendedora
                if 'cerveza' in original_search or 'alcohol' in original_search or 'vino' in original_search or 'chela' in original_search:
                    response_text = "¡Eso no lo manejamos, pero la Limonada Natural está recién hecha y queda perfecta! ¿Te pongo una?"
                elif 'bebida' in search_term or 'refresco' in original_search or 'soda' in original_search:
                    response_text = "¡La Limonada Natural es la favorita! También Coca-Cola y Agua de Jamaica. ¿Cuál te sirvo?"
                elif 'postre' in search_term:
                    response_text = "¡El Pastel de Chocolate es espectacular! También el Flan Napolitano. ¿Cuál te pongo?"
                else:
                    # Buscar producto similar en el menú en lugar de hardcodear
                    popular_products = [p for p in menu if 'popular' in p.get('tags', [])][:2]
                    if popular_products:
                        response_text = f"Eso no lo tenemos, pero te recomiendo {popular_products[0]['name']}, ¡está volando! ¿Te lo preparo?"
                    else:
                        response_text = f"Eso no lo tenemos en el menú. ¿Quieres que te muestre lo que tenemos disponible?"

        elif detected_intent == Intent.SHOW_PRODUCT_DETAILS:
            # Mostrar detalles de un producto específico
            product_query = entities.get('product', '').lower()
            transcription_lower = transcription.lower()

            logger.info(f"[DETAILS] Buscando producto: query='{product_query}', transcripción='{transcription_lower}'")

            # MEJORA: Detectar si el usuario pregunta sobre detalles/ingredientes
            detail_keywords = [
                'ingredientes', 'tiene', 'contiene', 'cómo es', 'qué trae',
                'pica', 'picante', 'spicy', 'preparado', 'hecho', 'lleva',
                'qué es', 'de qué', 'salsa', 'guarnición', 'acompañamiento'
            ]
            asking_details = any(keyword in transcription_lower for keyword in detail_keywords)

            # Buscar producto - MEJORADO con múltiples estrategias
            found_product = None

            # Estrategia 1: Buscar por entity del LLM
            if product_query:
                for p in menu:
                    if product_query in p['name'].lower():
                        found_product = p
                        logger.info(f"[DETAILS] Encontrado por entity: {p['name']}")
                        break

            # Estrategia 2: Buscar por palabras clave de producto en la transcripción
            if not found_product:
                # Usar el mismo mapa de keywords que VIEW_CATEGORY
                product_keywords = {
                    'pastor': 'pastor', 'asada': 'asada', 'chorizo': 'chorizo', 'suadero': 'suadero',
                    'clásica': 'clasica', 'clasica': 'clasica', 'doble': 'doble', 'bbq': 'bbq',
                    'tocino': 'tocino', 'bacon': 'tocino', 'vegetariana': 'vegetariana',
                    'mexicana': 'mexicana', 'guacamole': 'guacamole', 'alitas': 'alitas',
                    'nachos': 'nachos', 'quesadilla': 'quesadilla', 'enchiladas': 'enchiladas',
                    'verdes': 'verdes', 'rojas': 'rojas', 'costillas': 'costillas',
                    'pechuga': 'pechuga', 'pozole': 'pozole', 'flan': 'flan',
                    'churros': 'churros', 'chocolate': 'chocolate', 'helado': 'helado',
                    'limonada': 'limonada', 'jamaica': 'jamaica', 'horchata': 'horchata',
                    'coca': 'coca', 'corona': 'corona', 'papas': 'papas', 'aros': 'aros'
                }

                for keyword, search_term in product_keywords.items():
                    if keyword in transcription_lower:
                        # Buscar producto que contenga este término
                        for p in menu:
                            if search_term in p['name'].lower():
                                found_product = p
                                logger.info(f"[DETAILS] Encontrado por keyword '{keyword}': {p['name']}")
                                break
                        if found_product:
                            break

            # Estrategia 3: Buscar coincidencia parcial con cualquier palabra del menú
            if not found_product:
                for p in menu:
                    product_name_lower = p['name'].lower()
                    # Verificar si alguna palabra del nombre del producto está en la transcripción
                    product_words = product_name_lower.split()
                    for word in product_words:
                        if len(word) > 3 and word in transcription_lower:  # Palabras de más de 3 letras
                            found_product = p
                            logger.info(f"[DETAILS] Encontrado por coincidencia parcial '{word}': {p['name']}")
                            break
                    if found_product:
                        break

            if found_product:
                visual_data = {
                    "type": "product_detail",
                    "product": {
                        "id": found_product['id'],
                        "name": found_product['name'],
                        "description": found_product.get('description', ''),
                        "price": float(found_product.get('price', 0)),
                        "image_url": found_product.get('image_url'),
                        "preparation_time": found_product.get('preparation_time_minutes', 0),
                        "category": found_product.get('category', {}).get('name', ''),
                        "category_id": found_product.get('category_id') or found_product.get('category', {}).get('id')
                    }
                }
                order_data = {"visual_data": visual_data}

                # MEJORA: Responder con descripción vendedora
                if asking_details:
                    desc = found_product.get('description', 'Un platillo delicioso')
                    price = found_product.get('price', 0)
                    response_text = f"¡Excelente elección! La {found_product['name']} lleva {desc.lower()}. Solo {price} pesos y es de los más pedidos. ¿Te la preparo?"
                else:
                    price = found_product.get('price', 0)
                    response_text = f"¡{found_product['name']} es buenísima! {price} pesos. Es de las favoritas. ¿Te la pongo?"
            else:
                # Buscar alternativa dinámica
                popular_products = [p for p in menu if 'popular' in p.get('tags', [])][:2]
                if popular_products:
                    response_text = f"Ese no lo tengo registrado. ¿Te gustaría probar {popular_products[0]['name']}? Es de los favoritos."
                else:
                    response_text = f"Ese no lo tengo registrado. ¿Quieres que te muestre el menú?"

        elif detected_intent == Intent.VIEW_FULL_MENU:
            # Mostrar menú completo con imágenes
            # Agrupar por categorías
            categories_dict = {}
            for p in menu:
                cat_name = p.get('category', {}).get('name', 'General')
                if cat_name not in categories_dict:
                    categories_dict[cat_name] = []
                categories_dict[cat_name].append({
                    "id": p['id'],
                    "name": p['name'],
                    "description": p.get('description', ''),
                    "price": float(p.get('price', 0)),
                    "image_url": p.get('image_url')
                })

            visual_data = {
                "type": "full_menu",
                "categories": categories_dict
            }
            order_data = {"visual_data": visual_data}
            response_text = f"Con gusto, aquí está nuestro menú completo. ¿Te gustaría que te recomiende algo?"

        elif detected_intent == Intent.VIEW_ORDER:
            # Mostrar orden actual
            orders = await restaurant_client.get_table_orders(session.table_id, active_only=True)
            if orders:
                response_text = f"Tienes {len(orders)} pedido activo. ¿Te gustaría agregar algo más?"
            else:
                response_text = "Aún no tienes pedidos. ¿Qué te gustaría probar hoy?"

        elif detected_intent == Intent.REQUEST_BILL:
            response_text = "Perfecto, en un momento traigo tu cuenta. Gracias por visitarnos."

            # Limpiar la sesión del cliente ya que está por pagar y marcharse
            session.end_customer_session()
            logger.info(f"[💳] Cuenta solicitada - Sesión del cliente limpiada")

        elif detected_intent == Intent.CALL_WAITER:
            response_text = "Con gusto, el mesero estará contigo en un momento."

        elif detected_intent == Intent.GREETING:
            response_text = f"Bienvenido. Estoy aquí para ayudarte. ¿Qué te gustaría ordenar?"

        elif detected_intent == Intent.GOODBYE:
            response_text = "Gracias por tu visita. Que tengas un excelente día."

        elif detected_intent == Intent.GET_RECOMMENDATION:
            # ================================================================
            # SISTEMA DE RECOMENDACIONES CON MICRO-EMBUDOS INTELIGENTES
            # ================================================================
            # NUEVO: Primero verificar si hay una categoría activa (micro-embudo)
            # Si el usuario estaba preguntando sobre tacos/hamburguesas/etc,
            # la recomendación debe ser DENTRO de esa categoría
            # ================================================================

            dietary_pref = entities.get('dietary_preference', '').lower()
            meal_type = entities.get('meal_type', '').lower()
            budget = entities.get('budget', '').lower()

            # ================================================================
            # MICRO-EMBUDO: Verificar si hay categoría activa
            # ================================================================
            active_category_data = ACTIVE_CATEGORY_CONTEXT.get(session_id)
            has_active_category = False
            active_category = None

            if active_category_data:
                # Verificar que la categoría no haya expirado (5 minutos)
                import time
                if time.time() - active_category_data.get('timestamp', 0) < 300:
                    has_active_category = True
                    active_category = active_category_data.get('category', '')
                    logger.info(f"[MICRO-EMBUDO] Categoría activa detectada: {active_category}")
                else:
                    # Limpiar categoría expirada
                    del ACTIVE_CATEGORY_CONTEXT[session_id]
                    logger.info("[MICRO-EMBUDO] Categoría expirada, limpiando contexto")

            # ================================================================
            # SI HAY CATEGORÍA ACTIVA: Recomendar DENTRO de esa categoría
            # ================================================================
            if has_active_category and active_category:
                logger.info(f"[MICRO-EMBUDO] Recomendando dentro de: {active_category}")

                # Buscar productos de esa categoría
                category_products = []

                # Mapeo de términos de búsqueda a nombres de categoría del menú
                # IMPORTANTE: Buscar por CATEGORÍA, no por nombre de producto
                category_mapping = {
                    # Términos que el usuario puede decir -> Nombre exacto de categoría en el menú
                    'hamburguesa': 'Hamburguesas',
                    'hamburguesas': 'Hamburguesas',
                    'burger': 'Hamburguesas',
                    'taco': 'Tacos',
                    'tacos': 'Tacos',
                    'bebida': 'Bebidas',
                    'bebidas': 'Bebidas',
                    'refresco': 'Bebidas',
                    'tomar': 'Bebidas',
                    'postre': 'Postres',
                    'postres': 'Postres',
                    'dulce': 'Postres',
                    'entrada': 'Entradas',
                    'entradas': 'Entradas',
                    'botana': 'Entradas',
                    'sopa': 'Sopas',
                    'sopas': 'Sopas',
                    'caldo': 'Sopas',
                    'ensalada': 'Ensaladas',
                    'ensaladas': 'Ensaladas',
                    'plato fuerte': 'Platos Fuertes',
                    'platos fuertes': 'Platos Fuertes',
                    'complemento': 'Complementos',
                    'complementos': 'Complementos',
                    'extra': 'Complementos',
                }

                # Obtener el nombre exacto de la categoría del menú
                target_category = category_mapping.get(active_category.lower())

                if target_category:
                    # Buscar SOLO por categoría del menú (no por nombre de producto)
                    for p in menu:
                        cat_name = p.get('category', {}).get('name', '')
                        if cat_name == target_category:
                            category_products.append(p)
                    logger.info(f"[MICRO-EMBUDO] Buscando en categoría: {target_category} - Encontrados: {len(category_products)}")
                else:
                    # Fallback: buscar categoría que contenga el término
                    for p in menu:
                        cat_name = p.get('category', {}).get('name', '').lower()
                        if active_category.lower() in cat_name:
                            category_products.append(p)
                    logger.info(f"[MICRO-EMBUDO] Búsqueda fallback por: {active_category} - Encontrados: {len(category_products)}")

                if category_products:
                    # ============================================================
                    # DETECTAR SI EL USUARIO MENCIONÓ UN PRODUCTO ESPECÍFICO
                    # ============================================================
                    # Si el usuario dice "¿me recomiendas los tacos de carnitas?"
                    # debemos responder sobre CARNITAS, no sobre el más popular
                    transcription_lower = transcription.lower()

                    # Buscar si algún producto de la categoría fue mencionado
                    mentioned_product = None
                    for p in category_products:
                        product_name = p.get('name', '').lower()
                        # Extraer palabras clave del nombre del producto
                        # Ej: "Tacos de Carnitas" -> buscar "carnitas"
                        product_keywords = product_name.replace('tacos de ', '').replace('taco de ', '')
                        product_keywords = product_keywords.replace('hamburguesa ', '').replace('agua de ', '')

                        # También buscar palabras individuales del nombre
                        name_words = [w for w in product_name.split() if len(w) > 3]

                        # Verificar si alguna palabra clave está en la transcripción
                        if product_keywords in transcription_lower:
                            mentioned_product = p
                            logger.info(f"[MICRO-EMBUDO] Producto específico detectado: {p['name']} (keyword: {product_keywords})")
                            break

                        # Buscar palabras individuales (ej: "carnitas", "pastor", "asada")
                        for word in name_words:
                            if word.lower() in transcription_lower and word.lower() not in ['tacos', 'taco', 'hamburguesa', 'agua']:
                                mentioned_product = p
                                logger.info(f"[MICRO-EMBUDO] Producto específico detectado: {p['name']} (word: {word})")
                                break
                        if mentioned_product:
                            break

                    # Si se mencionó un producto específico, usar ese
                    if mentioned_product:
                        best_product = mentioned_product
                        logger.info(f"[MICRO-EMBUDO] Usando producto mencionado: {best_product['name']}")
                    else:
                        # Si no, ordenar por popularidad y tomar el primero
                        popular_first = sorted(
                            category_products,
                            key=lambda x: 1 if 'popular' in x.get('tags', []) else 0,
                            reverse=True
                        )
                        best_product = popular_first[0]
                        logger.info(f"[MICRO-EMBUDO] Usando producto más popular: {best_product['name']}")

                    # Preparar datos visuales
                    visual_data = {
                        "type": "product_detail",
                        "product": {
                            "id": best_product['id'],
                            "name": best_product['name'],
                            "description": best_product.get('description', ''),
                            "price": float(best_product.get('price', 0)),
                            "image_url": best_product.get('image_url'),
                            "category": best_product.get('category', {}).get('name', ''),
                            "category_id": best_product.get('category_id') or best_product.get('category', {}).get('id')
                        }
                    }
                    order_data = {"visual_data": visual_data}

                    # Guardar contexto del producto
                    LAST_PRODUCT_CONTEXT[session_id] = best_product['name']

                    # Generar respuesta vendedora DENTRO del micro-embudo
                    price = best_product.get('price', 0)
                    response_text = f"¡Te recomiendo {best_product['name']}! Es de los favoritos, solo ${price}. ¿Te lo preparo?"

                    logger.info(f"[MICRO-EMBUDO] Recomendación: {best_product['name']}")

                else:
                    # No hay productos en esa categoría, dar respuesta genérica
                    response_text = f"Déjame mostrarte las mejores opciones. ¿Qué tipo de platillo prefieres?"

                # Saltar el resto del embudo global
                logger.info(f"[✓] Acción ejecutada: {detected_intent} (micro-embudo)")
                logger.info(f"[📝] Respuesta generada: {response_text}")

                # Agregar respuesta al historial y continuar al audio
                session.add_message('assistant', response_text, intent=detected_intent, entities=entities)

                # Generar audio
                force_audio = request.form.get('force_audio', 'true').lower() == 'true'
                audio_url = None
                if force_audio:
                    logger.info("[4/5] Generando audio (micro-embudo)...")
                    audio_filename = f"response_{session_id}_voice.mp3"
                    audio_path = app.config['UPLOAD_FOLDER'] / audio_filename
                    await tts_handler.synthesize_to_file(response_text, audio_path)
                    audio_url = f"/audio/{audio_filename}"
                    logger.info("[✓] Audio generado")

                logger.info("[5/5] Enviando respuesta")
                logger.info("[✓✓✓] Procesamiento completado exitosamente")

                result = {
                    'success': True,
                    'transcription': transcription,
                    'intent': detected_intent,
                    'response': response_text,
                    'audio_generated': force_audio
                }
                if audio_url:
                    result['audio_url'] = audio_url
                if order_data:
                    if 'visual_data' in order_data:
                        result['visual_data'] = order_data['visual_data']

                temp_input_path.unlink(missing_ok=True)
                return jsonify(result)

            # ================================================================
            # EMBUDO GLOBAL: Si NO hay categoría activa, usar embudo normal
            # ================================================================

            # Obtener estado actual del embudo de recomendaciones
            funnel_state = session.get_context('recommendation_funnel_state')
            funnel_data = session.get_context('recommendation_funnel_data', {})

            logger.info(f"[EMBUDO] Estado: {funnel_state}, Data: {funnel_data}, Prefs: dietary={dietary_pref}, meal={meal_type}, budget={budget}")

            # ================================================================
            # LÓGICA DEL EMBUDO DE VENTAS GLOBAL
            # ================================================================

            # Si el cliente YA especificó preferencias en su mensaje, saltar embudo
            has_explicit_preferences = bool(dietary_pref or meal_type or budget)

            if not has_explicit_preferences and not funnel_state:
                # ============================================================
                # PASO 1: Primera pregunta - Tipo de comida (Situación)
                # ============================================================
                # Técnica "Limited Choice" + "Suggestive Selling"
                session.set_context('recommendation_funnel_state', 'waiting_meal_type')
                session.set_context('recommendation_funnel_data', {})

                response_text = "¿Buscas algo ligero para botanear, algo más llenador como plato fuerte, o algo fresco para tomar?"
                logger.info("[EMBUDO] Iniciado - Pregunta 1: Tipo de comida")

            elif funnel_state == 'waiting_meal_type':
                # ============================================================
                # PASO 2: Procesar tipo y preguntar preferencia (Preferencia)
                # ============================================================
                transcription_lower = transcription.lower()

                # Detectar tipo de comida de la respuesta
                detected_meal_type = None
                if any(word in transcription_lower for word in ['ligero', 'botana', 'botanear', 'entrada', 'antojo', 'snack']):
                    detected_meal_type = 'entrada'
                elif any(word in transcription_lower for word in ['llenador', 'fuerte', 'plato', 'comida', 'comer', 'hambre']):
                    detected_meal_type = 'plato_fuerte'
                elif any(word in transcription_lower for word in ['tomar', 'beber', 'bebida', 'fresco', 'sed', 'refresco']):
                    detected_meal_type = 'bebida'
                elif any(word in transcription_lower for word in ['postre', 'dulce', 'algo dulce']):
                    detected_meal_type = 'postre'

                if detected_meal_type:
                    funnel_data['meal_type'] = detected_meal_type
                    session.set_context('recommendation_funnel_data', funnel_data)
                    session.set_context('recommendation_funnel_state', 'waiting_preference')

                    # Técnica "Assumptive Close" - preguntar preferencia según tipo
                    if detected_meal_type == 'entrada':
                        response_text = "¡Perfecto! ¿Te gustan más las alitas, nachos, o algo más fresco como guacamole?"
                    elif detected_meal_type == 'plato_fuerte':
                        response_text = "¡Buena elección! ¿Prefieres carne, pollo, o algo vegetariano?"
                    elif detected_meal_type == 'bebida':
                        response_text = "¿Algo refrescante como limonada, agua fresca, o prefieres refresco?"
                    elif detected_meal_type == 'postre':
                        response_text = "¡Excelente! ¿Chocolate, algo frutal, o algo más ligero como flan?"

                    logger.info(f"[EMBUDO] Tipo detectado: {detected_meal_type} - Pregunta 2: Preferencia")
                else:
                    # No se entendió, dar opciones más claras
                    response_text = "Disculpa, ¿buscas una entrada, un plato fuerte, o algo para tomar?"
                    logger.info("[EMBUDO] Tipo no detectado - Repitiendo pregunta 1")

            elif funnel_state == 'waiting_preference':
                # ============================================================
                # PASO 3: Procesar preferencia y DAR RECOMENDACIÓN FINAL
                # ============================================================
                transcription_lower = transcription.lower()

                # Detectar preferencia/restricción de la respuesta
                detected_preference = None

                # Restricciones dietéticas
                if any(word in transcription_lower for word in ['vegano', 'vegana', 'vegetariano', 'vegetariana', 'sin carne', 'verduras']):
                    detected_preference = 'vegetariano'
                elif any(word in transcription_lower for word in ['sin picante', 'no picante', 'suave', 'nada picante', 'poco picante']):
                    detected_preference = 'sin_picante'
                # Proteínas
                elif any(word in transcription_lower for word in ['carne', 'res', 'asada']):
                    detected_preference = 'carne'
                elif any(word in transcription_lower for word in ['pollo', 'pechuga']):
                    detected_preference = 'pollo'
                elif any(word in transcription_lower for word in ['cerdo', 'pastor', 'carnitas']):
                    detected_preference = 'cerdo'
                elif any(word in transcription_lower for word in ['mariscos', 'pescado', 'camarón', 'camarones']):
                    detected_preference = 'mariscos'
                # Entradas específicas
                elif any(word in transcription_lower for word in ['alitas', 'alas', 'wings']):
                    detected_preference = 'alitas'
                elif any(word in transcription_lower for word in ['nachos', 'nacho']):
                    detected_preference = 'nachos'
                elif any(word in transcription_lower for word in ['guacamole', 'guaca']):
                    detected_preference = 'guacamole'
                elif any(word in transcription_lower for word in ['quesadilla', 'queso']):
                    detected_preference = 'quesadilla'
                # Bebidas específicas
                elif any(word in transcription_lower for word in ['limonada', 'limón']):
                    detected_preference = 'limonada'
                elif any(word in transcription_lower for word in ['refresco', 'coca', 'soda']):
                    detected_preference = 'refresco'
                elif any(word in transcription_lower for word in ['agua', 'fresca', 'jamaica', 'horchata']):
                    detected_preference = 'agua_fresca'
                # Postres específicos
                elif any(word in transcription_lower for word in ['chocolate', 'pastel']):
                    detected_preference = 'chocolate'
                elif any(word in transcription_lower for word in ['flan', 'ligero']):
                    detected_preference = 'flan'
                elif any(word in transcription_lower for word in ['churro', 'churros']):
                    detected_preference = 'churros'
                elif any(word in transcription_lower for word in ['fruta', 'frutal', 'helado']):
                    detected_preference = 'frutal'

                if detected_preference:
                    funnel_data['preference'] = detected_preference

                # ============================================================
                # GENERAR RECOMENDACIÓN FINAL BASADA EN EMBUDO
                # ============================================================
                session.set_context('recommendation_funnel_state', None)  # Limpiar estado
                session.set_context('recommendation_funnel_data', {})

                meal_type = funnel_data.get('meal_type', '')
                preference = funnel_data.get('preference', detected_preference or '')

                logger.info(f"[EMBUDO] Generando recomendación - Tipo: {meal_type}, Preferencia: {preference}")

                # Filtrar productos según embudo
                filtered_products = menu.copy()

                # Filtro por tipo de comida
                if meal_type == 'entrada':
                    filtered_products = [p for p in filtered_products if p.get('category_id') == 1 or 'entrada' in str(p.get('category', {})).lower()]
                elif meal_type == 'plato_fuerte':
                    filtered_products = [p for p in filtered_products if p.get('category_id') == 2 or 'plato' in str(p.get('category', {})).lower() or 'taco' in str(p.get('category', {})).lower()]
                elif meal_type == 'bebida':
                    filtered_products = [p for p in filtered_products if p.get('category_id') == 3 or 'bebida' in str(p.get('category', {})).lower()]
                elif meal_type == 'postre':
                    filtered_products = [p for p in filtered_products if p.get('category_id') == 4 or 'postre' in str(p.get('category', {})).lower()]

                # Filtro por preferencia
                if preference == 'vegetariano':
                    filtered_products = [p for p in filtered_products if 'vegetariano' in p.get('tags', []) or 'vegano' in p.get('tags', [])]
                elif preference == 'sin_picante':
                    filtered_products = [p for p in filtered_products if 'sin_picante' in p.get('tags', []) or 'suave' in p.get('tags', [])]
                elif preference in ['carne', 'pollo', 'cerdo', 'mariscos']:
                    filtered_products = [p for p in filtered_products if preference in p.get('name', '').lower() or preference in p.get('description', '').lower()]
                elif preference in ['alitas', 'nachos', 'guacamole', 'quesadilla', 'limonada', 'chocolate', 'flan', 'churros']:
                    filtered_products = [p for p in filtered_products if preference in p.get('name', '').lower()]

                # Si no hay productos, usar recomendaciones inteligentes
                if not filtered_products:
                    intel = await get_sales_intel()
                    if intel:
                        try:
                            filtered_products = await intel.get_smart_recommendations(
                                menu=menu,
                                table_id=session.table_id,
                                current_cart=[],
                                limit=3
                            )
                        except Exception as e:
                            logger.warning(f"Error en smart recommendations: {e}")

                # Fallback: productos populares
                if not filtered_products:
                    filtered_products = [p for p in menu if 'popular' in p.get('tags', [])][:3]

                recommendations = filtered_products[:2]  # Técnica "Limited Choice": máximo 2

                if recommendations:
                    visual_data = {
                        "type": "product_list",
                        "category": "Recomendaciones para ti",
                        "products": [
                            {
                                "id": p['id'],
                                "name": p['name'],
                                "description": p.get('description', ''),
                                "price": float(p.get('price', 0)),
                                "image_url": p.get('image_url'),
                                "preparation_time": p.get('preparation_time_minutes', 0)
                            }
                            for p in recommendations
                        ]
                    }
                    order_data = {"visual_data": visual_data}

                    # Técnica "Assumptive Close" - asumir que SÍ quiere
                    if len(recommendations) == 1:
                        prod = recommendations[0]
                        response_text = f"¡Perfecto! Te recomiendo {prod['name']} por ${prod.get('price', 0)}. Es de los favoritos. ¿Te lo preparo?"
                    else:
                        # Técnica "Bracketing" - dar 2 opciones
                        response_text = f"¡Te van a encantar! Te sugiero {recommendations[0]['name']} por ${recommendations[0].get('price', 0)}, o {recommendations[1]['name']} por ${recommendations[1].get('price', 0)}. ¿Cuál te preparo?"
                else:
                    response_text = "Déjame mostrarte nuestro menú para que elijas lo que más te guste."

                logger.info(f"[EMBUDO] Recomendación final: {[p['name'] for p in recommendations]}")

            else:
                # ============================================================
                # CLIENTE YA ESPECIFICÓ PREFERENCIAS - RECOMENDAR DIRECTO
                # ============================================================
                # Limpiar cualquier estado de embudo previo
                session.set_context('recommendation_funnel_state', None)
                session.set_context('recommendation_funnel_data', {})

                # Obtener SalesIntelligence para recomendaciones basadas en datos
                intel = await get_sales_intel()

                # Intentar obtener recomendaciones inteligentes primero
                smart_recommendations = []
                if intel:
                    try:
                        current_cart = []
                        if session.current_order_draft:
                            current_cart = [item.get('product_id') for item in session.current_order_draft.get('items', [])]

                        smart_recommendations = await intel.get_smart_recommendations(
                            menu=menu,
                            table_id=session.table_id,
                            current_cart=current_cart,
                            limit=5
                        )
                        logger.info(f"[INTEL] Recomendaciones inteligentes: {len(smart_recommendations)} productos")
                    except Exception as e:
                        logger.warning(f"Error en smart recommendations: {e}")

                if smart_recommendations:
                    filtered_products = smart_recommendations
                else:
                    filtered_products = menu.copy()

                # Aplicar filtros del usuario
                if dietary_pref:
                    if 'sin picante' in dietary_pref or 'no picante' in dietary_pref:
                        tag_filter = 'sin_picante'
                    elif 'vegetariano' in dietary_pref or 'vegano' in dietary_pref:
                        tag_filter = 'vegetariano'
                    elif 'saludable' in dietary_pref or 'ligero' in dietary_pref:
                        tag_filter = 'saludable'
                    else:
                        tag_filter = dietary_pref

                    filtered_products = [
                        p for p in filtered_products
                        if tag_filter in p.get('tags', [])
                    ]

                if meal_type:
                    if 'postre' in meal_type or 'dulce' in meal_type:
                        filtered_products = [p for p in filtered_products if 'postre' in p.get('tags', []) or p.get('category_id') == 4]
                    elif 'bebida' in meal_type:
                        filtered_products = [p for p in filtered_products if 'bebida' in p.get('tags', []) or p.get('category_id') == 3]
                    elif 'entrada' in meal_type:
                        filtered_products = [p for p in filtered_products if p.get('category_id') == 1]
                    elif 'plato' in meal_type or 'fuerte' in meal_type:
                        filtered_products = [p for p in filtered_products if p.get('category_id') == 2]

                if budget:
                    if 'económico' in budget or 'barato' in budget:
                        filtered_products = [p for p in filtered_products if float(p.get('price', 999)) <= 100]
                    elif 'premium' in budget or 'caro' in budget:
                        filtered_products = [p for p in filtered_products if float(p.get('price', 0)) >= 100]

                # Si el filtro dejó vacío, buscar directamente en menú por la categoría solicitada
                if not filtered_products:
                    logger.info(f"[RECO] Filtro vacío, buscando directamente en menú. meal_type={meal_type}, dietary={dietary_pref}")
                    # Buscar directamente en el menú por categoría
                    if meal_type:
                        if 'bebida' in meal_type:
                            filtered_products = [p for p in menu if 'bebida' in p.get('category', {}).get('name', '').lower()]
                        elif 'postre' in meal_type:
                            filtered_products = [p for p in menu if 'postre' in p.get('category', {}).get('name', '').lower()]
                        elif 'entrada' in meal_type:
                            filtered_products = [p for p in menu if 'entrada' in p.get('category', {}).get('name', '').lower()]
                        elif 'plato' in meal_type:
                            filtered_products = [p for p in menu if 'plato' in p.get('category', {}).get('name', '').lower()]

                    # Si aún está vacío, buscar por preferencia dietética
                    if not filtered_products and dietary_pref:
                        if 'vegetariano' in dietary_pref:
                            filtered_products = [p for p in menu if 'vegetariano' in p.get('tags', []) or 'vegano' in p.get('tags', [])]

                # Fallback: time suggestion o populares
                if not filtered_products and intel:
                    time_suggestion = intel.get_time_based_suggestion(menu)
                    if time_suggestion:
                        filtered_products = [time_suggestion]

                if not filtered_products:
                    filtered_products = [p for p in menu if 'popular' in p.get('tags', [])][:3]

                recommendations = filtered_products[:2]  # Técnica "Limited Choice"

                if recommendations:
                    visual_data = {
                        "type": "product_list",
                        "category": "Recomendaciones para ti",
                        "products": [
                            {
                                "id": p['id'],
                                "name": p['name'],
                                "description": p.get('description', ''),
                                "price": float(p.get('price', 0)),
                                "image_url": p.get('image_url'),
                                "preparation_time": p.get('preparation_time_minutes', 0)
                            }
                            for p in recommendations
                        ]
                    }
                    order_data = {"visual_data": visual_data}

                    # Respuesta con técnica "Assumptive Close"
                    if len(recommendations) == 1:
                        prod = recommendations[0]
                        response_text = f"¡{prod['name']} es perfecto para ti! Solo ${prod.get('price', 0)}. ¿Te lo preparo?"
                    else:
                        response_text = f"Para ti te sugiero {recommendations[0]['name']} o {recommendations[1]['name']}. ¿Cuál te preparo?"
                else:
                    # Respuesta dinámica basada en lo que pidió
                    if meal_type:
                        response_text = f"Déjame mostrarte las opciones de {meal_type}. ¿Qué te gustaría ver?"
                    else:
                        response_text = "¿Qué tipo de platillo te gustaría? ¿Algo para comer, tomar, o un postre?"

        elif detected_intent == Intent.VIEW_PROMOTIONS:
            # PROMOCIONES - Usar datos reales de productos populares
            intel = await get_sales_intel()

            if intel:
                try:
                    # Obtener los 3 productos más populares
                    top_product_ids = await intel.get_top_products(limit=3)

                    if top_product_ids:
                        # Mapear IDs a nombres
                        top_products = []
                        for pid in top_product_ids:
                            for p in menu:
                                if p['id'] == pid:
                                    top_products.append(p)
                                    break

                        if len(top_products) >= 2:
                            visual_data = {
                                "type": "product_list",
                                "category": "Los más pedidos",
                                "products": [
                                    {
                                        "id": p['id'],
                                        "name": p['name'],
                                        "description": p.get('description', ''),
                                        "price": float(p.get('price', 0)),
                                        "image_url": p.get('image_url')
                                    }
                                    for p in top_products
                                ]
                            }
                            order_data = {"visual_data": visual_data}

                            response_text = f"¡Los favoritos de hoy son {top_products[0]['name']} y {top_products[1]['name']}! Están volando. ¿Cuál te preparo?"
                            logger.info(f"[INTEL] Promociones basadas en datos: {[p['name'] for p in top_products]}")
                        else:
                            # Usar productos populares del menú
                            popular = [p for p in menu if 'popular' in p.get('tags', [])][:2]
                            if popular:
                                response_text = f"¡Te recomiendo {popular[0]['name']}, es de los favoritos! ¿Te lo preparo?"
                            else:
                                response_text = "¡Todo está buenísimo! ¿Quieres que te muestre las opciones?"
                    else:
                        popular = [p for p in menu if 'popular' in p.get('tags', [])][:2]
                        if len(popular) >= 2:
                            response_text = f"¡Todo está buenísimo! {popular[0]['name']} y {popular[1]['name']} son los favoritos. ¿Con cuál empezamos?"
                        else:
                            response_text = "¡Todo está buenísimo! ¿Qué se te antoja?"

                except Exception as e:
                    logger.warning(f"Error obteniendo promociones inteligentes: {e}")
                    response_text = "¡Tenemos muchas opciones deliciosas! ¿Qué tipo de platillo te gustaría?"
            else:
                response_text = "¡Tenemos muchas opciones deliciosas! ¿Quieres ver el menú o te recomiendo algo?"

        else:
            # Si hay contexto de producto previo, sugerir ese producto
            if session_id in LAST_PRODUCT_CONTEXT:
                last_product = LAST_PRODUCT_CONTEXT[session_id]
                response_text = f"¿Te preparo los {last_product}? Son de los favoritos."
            else:
                # Usar recomendación dinámica basada en el menú
                popular = [p for p in menu if 'popular' in p.get('tags', [])][:2]
                if len(popular) >= 2:
                    response_text = f"¡Te recomiendo {popular[0]['name']} o {popular[1]['name']}! Son de los favoritos. ¿Cuál te preparo?"
                elif popular:
                    response_text = f"¡Te recomiendo {popular[0]['name']}! Es de los favoritos. ¿Te lo preparo?"
                else:
                    response_text = "¿En qué te puedo ayudar? Puedo mostrarte el menú o recomendarte algo."

        logger.info(f"[✓] Acción ejecutada: {detected_intent}")
        logger.info(f"[📝] Respuesta generada: {response_text}")

        # Agregar respuesta al historial
        session.add_message('assistant', response_text, intent=detected_intent, entities=entities)

        # 4. DECIDIR SI GENERAR AUDIO (ESTRATEGIA HÍBRIDA)
        # Obtener parámetro force_audio (default: true porque viene de voz)
        force_audio = request.form.get('force_audio', 'true').lower() == 'true'

        # Definir intenciones críticas que SIEMPRE requieren confirmación por voz
        CRITICAL_INTENTS = [
            Intent.CREATE_ORDER,
            Intent.ADD_ITEM,
            Intent.REQUEST_BILL,
            Intent.CALL_WAITER
        ]

        # Decidir si generar audio
        should_generate_audio = force_audio or (detected_intent in CRITICAL_INTENTS)

        audio_url = None
        if should_generate_audio:
            logger.info("[4/5] Generando audio (estrategia híbrida activada)...")
            output_audio_path = app.config['UPLOAD_FOLDER'] / f'response_{session_id}_{filename.rsplit(".", 1)[0]}.mp3'
            await tts_handler.synthesize_to_file(response_text, output_audio_path)
            audio_url = f'/audio/{output_audio_path.name}'
            logger.info("[✓] Audio generado")
        else:
            logger.info("[4/5] Audio omitido (solo texto - ahorro TTS)")

        # 5. DEVOLVER RESPUESTA
        logger.info("[5/5] Enviando respuesta")

        result = {
            'success': True,
            'transcription': transcription,
            'intent': detected_intent,
            'response': response_text,
            'audio_generated': should_generate_audio
        }

        # Solo incluir audio_url si se generó
        if audio_url:
            result['audio_url'] = audio_url

        if order_data:
            if 'id' in order_data:
                result['order_id'] = order_data.get('id')
                result['order_total'] = float(order_data.get('total_amount', 0))
            if 'visual_data' in order_data:
                result['visual_data'] = order_data['visual_data']

        # Limpiar archivo de entrada
        temp_input_path.unlink(missing_ok=True)

        logger.info(f"[✓✓✓] Procesamiento completado exitosamente")

        return jsonify(result)

    except Exception as e:
        logger.error(f"Error procesando voz: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/text/process', methods=['POST'])
async def process_text():
    """
    Procesar texto del usuario (interacción táctil) sin generar audio

    ESTRATEGIA DE AHORRO:
    - Solo procesa NLP y ejecuta acciones
    - NO genera TTS (ahorro 100% en esta interacción)
    - Ideal para navegación visual del menú

    JSON Body:
        {
            "session_id": "xxx-xxx-xxx",
            "text": "Quiero ver el menú de bebidas"
        }

    Returns:
        {
            "success": true,
            "intent": "view_category",
            "response": "Aquí están nuestras bebidas...",
            "visual_data": {...}  // si aplica
        }
    """
    try:
        data = request.json
        session_id = data.get('session_id')
        text = data.get('text', '').strip()

        if not session_id:
            return jsonify({'error': 'session_id requerido'}), 400

        if not text:
            return jsonify({'error': 'text requerido'}), 400

        session = session_manager.get_session(session_id)
        if not session:
            return jsonify({'error': 'Sesión no encontrada o expirada'}), 401

        logger.info(f"[Sesión {session_id}] Texto recibido (táctil): '{text}'")

        # Agregar a historial
        session.add_message('user', text)

        # 1. RECONOCER INTENCIÓN
        logger.info("[1/3] Reconociendo intención...")

        menu = await restaurant_client.get_menu()
        menu_names = [p['name'] for p in menu]

        context = {
            'has_active_order': bool(session.current_order_draft),
            'menu_items': menu_names[:20]
        }

        intent_result = await intent_recognizer.recognize(text, context=context)
        detected_intent = intent_result.get('intent')
        entities = intent_result.get('entities', {})

        logger.info(f"[✓] Intención: {detected_intent}")

        # 2. EJECUTAR ACCIÓN (reutilizar la misma lógica del endpoint de voz)
        logger.info("[2/3] Ejecutando acción...")
        response_text = ""
        order_data = None

        # Aquí va la misma lógica de intenciones (simplificada para el ejemplo)
        if detected_intent == Intent.VIEW_MENU:
            categories_dict = {}
            for p in menu:
                cat_name = p.get('category', {}).get('name', 'General')
                if cat_name not in categories_dict:
                    categories_dict[cat_name] = []
                categories_dict[cat_name].append(p)

            response_text = f"Tenemos {len(categories_dict)} categorías disponibles."

        elif detected_intent == Intent.VIEW_CATEGORY:
            category_name = entities.get('category', '').lower()
            
            # Detección inteligente de producto específico
            text_lower = text.lower()
            exact_product_match = None
            # Palabras clave que identifican variantes de productos
            product_keywords = {
                # === TACOS (ID 15-18) ===
                'pastor': ['pastor', 'pastol', 'pastos', 'al pastor'],
                'asada': ['carne asada', 'asada', 'azada'],
                'chorizo': ['chorizo', 'chorizzo', 'choriz'],
                'suadero': ['suadero', 'suadera', 'asadero', 'zuadero', 'suader', 'zuader'],
                # === HAMBURGUESAS (ID 19-22) ===
                'clásica': ['clásica', 'clasica', 'hamburguesa clasica', 'hamburguesa clásica'],
                'doble': ['doble carne', 'doble', 'dobles'],
                'bbq': ['bbq', 'barbacoa', 'barbeque', 'barbecue', 'barbiquiu'],
                'tocino': ['tocino', 'bacon', 'tocino especial'],
                # === ENTRADAS (ID 11-14) ===
                'guacamole': ['guacamole', 'guaca', 'wakamole'],
                'alitas': ['alitas', 'alas', 'bufalo', 'búfalo', 'buffalo'],
                'nachos': ['nachos', 'nacho', 'supreme'],
                'quesadilla': ['quesadilla', 'quesadillas'],
                # === PLATOS FUERTES ===
                'verdes': ['enchiladas verdes', 'verdes'],
                'rojas': ['enchiladas rojas', 'rojas'],
                'costillas': ['costillas', 'costilla', 'ribs'],
                'pechuga': ['pechuga', 'parrilla', 'pollo a la parrilla'],
                'pozole': ['pozole', 'posole', 'pozole rojo', 'pozole verde', 'un pozole'],
                'mole': ['mole', 'pollo con mole', 'mole poblano'],
                'chilaquiles': ['chilaquiles', 'chilaquil'],
                'birria': ['birria', 'consomé', 'consome'],
                'carnitas': ['carnitas', 'carnita'],
                'barbacoa': ['barbacoa', 'barbacha'],
                # === BEBIDAS ===
                'limón': ['agua de limón', 'limon', 'limón'],
                'jamaica': ['jamaica', 'agua de jamaica'],
                'horchata': ['horchata', 'orchata', 'agua de horchata'],
                'coca': ['coca', 'coca-cola', 'cocacola', 'cola'],
                'corona': ['corona', 'cerveza corona'],
                'limonada': ['limonada mineral', 'limonada'],
                # === POSTRES (ID 33-36) ===
                'chocolate': ['pastel de chocolate', 'pastel chocolate'],
                'flan': ['flan', 'napolitano', 'flan napolitano'],
                'churros': ['churros', 'churro'],
                'helado': ['helado', 'nieve', 'helado artesanal'],
                # === COMPLEMENTOS (ID 37-40) ===
                'papas': ['papas fritas', 'papas'],
                'aros': ['aros de cebolla', 'aros', 'onion rings'],
                'elote': ['elote asado', 'elote'],
            }
            found_keyword = None
            for keyword, variants in product_keywords.items():
                for variant in variants:
                    if variant in text_lower:
                        found_keyword = keyword
                        break
                if found_keyword:
                    break
            if found_keyword:
                for p in menu:
                    if found_keyword in p['name'].lower():
                        exact_product_match = p
                        logger.info(f"[🎯] Producto (text): {p['name']}")
                        break

            if exact_product_match:
                visual_data = {
                    "type": "product_detail",
                    "product": {
                        "id": exact_product_match['id'], "name": exact_product_match['name'],
                        "description": exact_product_match.get('description', ''),
                        "price": float(exact_product_match.get('price', 0)),
                        "image_url": exact_product_match.get('image_url'),
                        "category": exact_product_match.get('category', {}).get('name', ''),
                        "category_id": exact_product_match.get('category_id') or exact_product_match.get('category', {}).get('id')
                    }
                }
                order_data = {"visual_data": visual_data}
                desc = exact_product_match.get('description', '')
                price = exact_product_match.get('price', 0)
                short_desc = desc.split('.')[0] if desc else 'Delicioso'
                response_text = f"¡{exact_product_match['name']}! {short_desc}. Solo {price} pesos. ¿Te lo preparo?"
            else:
                category_products = [
                    p for p in menu
                    if category_name in p.get('category', {}).get('name', '').lower()
                ]

            if exact_product_match:
                # Ya se generó respuesta arriba
                pass
            elif category_products:
                visual_data = {
                    "type": "product_list",
                    "category": category_name,
                    "products": [
                        {
                            "id": p['id'],
                            "name": p['name'],
                            "description": p.get('description', ''),
                            "price": float(p.get('price', 0)),
                            "image_url": p.get('image_url'),
                            "preparation_time": p.get('preparation_time_minutes', 0)
                        }
                        for p in category_products[:10]
                    ]
                }
                order_data = {"visual_data": visual_data}
                response_text = f"Mostrando {len(category_products)} productos de {category_name}."
            else:
                response_text = f"No se encontraron productos en '{category_name}'."

        else:
            response_text = "Usa el menú visual o pregunta por voz para ayudarte mejor."

        logger.info(f"[✓] Acción ejecutada: {detected_intent}")

        # Agregar respuesta al historial
        session.add_message('assistant', response_text, intent=detected_intent, entities=entities)

        # 3. DEVOLVER RESPUESTA (SIN AUDIO)
        logger.info("[3/3] Enviando respuesta (modo texto - SIN TTS)")

        result = {
            'success': True,
            'intent': detected_intent,
            'response': response_text,
            'audio_generated': False  # Indicador de ahorro
        }

        if order_data and 'visual_data' in order_data:
            result['visual_data'] = order_data['visual_data']

        logger.info(f"[✓✓✓] Procesamiento completado (ahorro TTS)")

        return jsonify(result)

    except Exception as e:
        logger.error(f"Error procesando texto: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


# ============================================================================
# API - UTILIDADES
# ============================================================================

@app.route('/api/health', methods=['GET'])
async def health():
    """Health check del servicio"""
    try:
        # Verificar servicios del restaurante
        restaurant_health = await restaurant_client.health_check()

        return jsonify({
            'status': 'ok',
            'services': restaurant_health,
            'active_sessions': session_manager.get_active_sessions_count()
        })
    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)}), 500


@app.route('/api/test', methods=['GET'])
def test():
    """Endpoint de prueba"""
    return jsonify({
        'status': 'ok',
        'message': 'Voice Restaurant Assistant API is running',
        'version': '1.0.0'
    })


# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║  VOICE RESTAURANT ASSISTANT                                  ║
║  Servidor iniciado en puerto {settings.FLASK_PORT}                         ║
╚══════════════════════════════════════════════════════════════╝

📱 Acceso:
   - Local:  http://localhost:{settings.FLASK_PORT}
   - Red:    http://0.0.0.0:{settings.FLASK_PORT}

📊 Health check: http://localhost:{settings.FLASK_PORT}/api/health

⚙️  Configuración cargada desde .env

🔧 Componentes:
   ✓ STT: Deepgram
   ✓ NLP: Groq
   ✓ TTS: gTTS
   ✓ Restaurant API: {settings.RESTAURANT_API_BASE_URL}

""")

    app.run(
        host=settings.FLASK_HOST,
        port=settings.FLASK_PORT,
        debug=settings.FLASK_DEBUG
    )
