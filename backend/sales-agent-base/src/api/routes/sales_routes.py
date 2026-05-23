"""
================================================================================
SALES ROUTES - API para Canales de Venta (WhatsApp, Web, etc.)
================================================================================
Endpoints para procesar mensajes de texto desde diferentes canales.
Usado por WhatsApp Gateway y otros integradores.
================================================================================
"""

from flask import Blueprint, request, jsonify
import logging
import asyncio
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Blueprint
sales_bp = Blueprint('sales', __name__, url_prefix='/api/v1/sales')

# Referencia al FSM (se inyecta desde app_v2.py)
_fsm = None
_session_manager = None
_restaurant_client = None


def register_sales_routes(fsm, session_manager, restaurant_client):
    """Registra las dependencias necesarias"""
    global _fsm, _session_manager, _restaurant_client
    _fsm = fsm
    _session_manager = session_manager
    _restaurant_client = restaurant_client
    logger.info("[SalesRoutes] Rutas de ventas registradas")


@sales_bp.route('/message', methods=['POST'])
async def process_sales_message():
    """
    Procesa un mensaje de texto desde cualquier canal (WhatsApp, Web, etc.)

    Este endpoint es usado por:
    - WhatsApp Gateway
    - Web chat
    - Otros integradores

    Body JSON:
        - session_id: ID único de la sesión/conversación
        - message: Texto del mensaje del cliente
        - channel: Canal de origen (whatsapp, web, voice)
        - context: Contexto adicional
            - phone: Número de teléfono (WhatsApp)
            - customer_name: Nombre del cliente
            - table_id: ID de mesa (si aplica)
            - restaurant_id: ID del restaurante
            - state: Estado actual de la conversación
            - cart: Carrito actual
            - parsed: Información parseada del mensaje

    Returns:
        - response/text: Texto de respuesta
        - buttons: Botones interactivos (opcional)
        - list: Lista de opciones (opcional)
        - cart: Carrito actualizado (opcional)
        - state: Nuevo estado de la conversación
        - order_id: ID del pedido si se creó uno
    """
    global _fsm, _session_manager, _restaurant_client

    data = request.get_json() or {}

    session_id = data.get('session_id')
    message = data.get('message', '')
    channel = data.get('channel', 'unknown')
    context = data.get('context', {})

    if not session_id:
        return jsonify({'error': 'session_id requerido'}), 400

    if not message:
        return jsonify({'error': 'message requerido'}), 400

    logger.info(f"[Sales:{channel}] Mensaje de {session_id}: {message[:50]}...")

    try:
        # Asegurar FSM inicializado
        if not _fsm:
            logger.warning("[Sales] FSM no inicializado, usando respuesta de fallback")
            return jsonify(await _handle_fallback(message, context))

        # Extraer información del contexto
        table_id = context.get('table_id')
        restaurant_id = context.get('restaurant_id')
        parsed = context.get('parsed', {})

        # Si es código de mesa, crear/actualizar sesión
        if parsed.get('is_table_code') and table_id:
            logger.info(f"[Sales] Mesa {table_id} detectada para sesión {session_id}")

        # Procesar con FSM
        result = _fsm.process(session_id, message)

        logger.info(f"[Sales] Intent: {result.intent}, Estado: {result.new_state.value}")
        logger.info(f"[Sales] Visual Data: {result.visual_data}")

        # Preparar respuesta
        response = {
            'response': result.response_text,
            'text': result.response_text,  # Alias para compatibilidad
            'state': result.new_state.value,
            'intent': result.intent
        }

        # Agregar datos visuales (botones, listas, productos)
        if result.visual_data:
            visual_type = result.visual_data.get('type')

            if visual_type == 'buttons':
                response['buttons'] = [
                    {'id': str(i), 'title': btn}
                    for i, btn in enumerate(result.visual_data.get('options', []), 1)
                ]

            elif visual_type in ('menu', 'product_list'):
                # Intentar convertir a Multi-Product Message
                converted = _convert_to_product_message(result.visual_data)

                if converted.get('type') == 'multi_product':
                    response['multi_product'] = {
                        'header': converted['header'],
                        'body': converted['body'],
                        'sections': converted['sections']
                    }
                elif converted.get('type') == 'single_product':
                    response['single_product'] = {
                        'product_retailer_id': converted['product_retailer_id'],
                        'body': converted['body']
                    }
                else:
                    # Fallback a lista interactiva
                    response['list'] = _convert_menu_to_list(result.visual_data)

                    # Para Twilio: enviar imagen del primer producto destacado
                    products = result.visual_data.get('products', [])
                    if products and products[0].get('image_url'):
                        first_product = products[0]
                        response['image'] = {
                            'url': first_product.get('image_url'),
                            'caption': f"📸 {first_product.get('name', '')}\n{first_product.get('description', '')[:100]}...\nPrecio: ${first_product.get('price', 0)}"
                        }

            elif visual_type == 'product_detail':
                # Single Product Message para recomendaciones
                product = result.visual_data.get('product', {})
                if product.get('product_retailer_id'):
                    response['single_product'] = {
                        'product_retailer_id': product['product_retailer_id'],
                        'body': f"{product.get('name', '')} - ${product.get('price', 0)}"
                    }
                elif product.get('image_url'):
                    response['image'] = {
                        'url': product.get('image_url'),
                        'caption': f"{product.get('name', '')}\n{product.get('description', '')}\nPrecio: ${product.get('price', 0)}"
                    }

            elif visual_type == 'cart':
                response['cart'] = result.visual_data.get('items', [])

        # Agregar carrito actualizado
        if result.cart_action:
            response['cart'] = result.cart_action.get('items', [])

        # Si hay orden confirmada, enviar a cocina
        order_id = None
        if hasattr(result, 'order_confirmed') and result.order_confirmed:
            order_id = await _send_order_to_kitchen(session_id, table_id, context)
            if order_id:
                response['order_id'] = order_id

        return jsonify(response)

    except Exception as e:
        logger.error(f"[Sales] Error procesando mensaje: {e}", exc_info=True)
        return jsonify({
            'response': 'Disculpa, tuve un problema. ¿Podrías repetir tu mensaje?',
            'text': 'Disculpa, tuve un problema. ¿Podrías repetir tu mensaje?',
            'error': str(e)
        }), 500


@sales_bp.route('/session/<session_id>', methods=['GET'])
async def get_sales_session(session_id: str):
    """
    Obtiene el estado de una sesión de ventas.
    """
    global _fsm

    if not _fsm:
        return jsonify({'error': 'FSM no inicializado'}), 503

    if session_id not in _fsm.sessions:
        return jsonify({'error': 'Sesión no encontrada'}), 404

    context = _fsm.sessions[session_id]

    return jsonify({
        'session_id': session_id,
        'state': context.current_state.value if hasattr(context, 'current_state') else 'unknown',
        'cart': [
            {
                'name': item.name,
                'quantity': item.quantity,
                'price': item.price
            }
            for item in (context.order_items or [])
        ],
        'total': context.order_total or 0.0
    })


@sales_bp.route('/cart/<session_id>', methods=['GET'])
async def get_sales_cart(session_id: str):
    """
    Obtiene el carrito de una sesión.
    """
    global _fsm

    if not _fsm or session_id not in _fsm.sessions:
        return jsonify({'items': [], 'total': 0.0})

    context = _fsm.sessions[session_id]

    items = []
    for item in (context.order_items or []):
        items.append({
            'product_id': item.product_id,
            'name': item.name,
            'quantity': item.quantity,
            'price': item.price,
            'subtotal': item.price * item.quantity
        })

    return jsonify({
        'items': items,
        'total': context.order_total or 0.0,
        'item_count': len(items)
    })


@sales_bp.route('/menu', methods=['GET'])
async def get_menu_for_sales():
    """
    Obtiene el menú formateado para canales de venta.
    """
    global _restaurant_client

    try:
        if _restaurant_client:
            menu = await _restaurant_client.get_menu()
        else:
            menu = []

        # Agrupar por categoría
        categories = {}
        for item in menu:
            cat = item.get('category', 'Otros')
            if cat not in categories:
                categories[cat] = []
            categories[cat].append({
                'id': item.get('id'),
                'name': item.get('name'),
                'price': item.get('price'),
                'description': item.get('description', '')[:100]
            })

        return jsonify({
            'categories': categories,
            'total_items': len(menu)
        })

    except Exception as e:
        logger.error(f"[Sales] Error obteniendo menú: {e}")
        return jsonify({'categories': {}, 'total_items': 0}), 500


# ==============================================================================
# HELPERS
# ==============================================================================

def _convert_to_product_message(visual_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convierte datos visuales a formato de Multi-Product o Single Product Message.

    Si los productos tienen product_retailer_id, genera Multi-Product Message.
    Si no, retorna indicador para usar lista interactiva como fallback.

    Args:
        visual_data: Datos visuales del FSM (tipo: menu, product_list, product_detail)

    Returns:
        Dict con tipo de mensaje y datos correspondientes
    """
    visual_type = visual_data.get('type')

    # Caso: product_list (lista de productos de una categoría)
    if visual_type == 'product_list':
        products = visual_data.get('products', [])
        category = visual_data.get('category', 'Menú')

        # Verificar si hay retailer_ids
        has_catalog = any(p.get('product_retailer_id') for p in products)

        if has_catalog:
            # Agrupar por categoría
            sections = [{
                'title': category[:24],
                'product_items': [
                    {'product_retailer_id': p['product_retailer_id']}
                    for p in products
                    if p.get('product_retailer_id')
                ][:30]  # Max 30 productos
            }]

            return {
                'type': 'multi_product',
                'header': category,
                'body': f"Te muestro {len(products)} opciones de {category.lower()}",
                'sections': sections
            }

        # Sin catálogo: fallback
        return {'type': 'list', 'products': products}

    # Caso: menu (menú completo con categorías)
    elif visual_type == 'menu':
        categories = visual_data.get('categories', {})

        # Verificar si hay retailer_ids en algún producto
        has_catalog = False
        for cat_products in categories.values():
            if any(p.get('product_retailer_id') for p in cat_products):
                has_catalog = True
                break

        if has_catalog:
            sections = []
            total_products = 0

            for cat_name, products in categories.items():
                product_items = [
                    {'product_retailer_id': p['product_retailer_id']}
                    for p in products
                    if p.get('product_retailer_id')
                ]

                if product_items:
                    sections.append({
                        'title': cat_name[:24],
                        'product_items': product_items[:10]  # Max 10 por sección
                    })
                    total_products += len(product_items)

                if len(sections) >= 10:  # Max 10 secciones
                    break

            if sections:
                return {
                    'type': 'multi_product',
                    'header': 'Nuestro Menú',
                    'body': f"Te muestro {total_products} opciones disponibles",
                    'sections': sections
                }

        # Sin catálogo: fallback
        return {'type': 'list', 'categories': categories}

    # Caso: product_detail (detalle de un producto)
    elif visual_type == 'product_detail':
        product = visual_data.get('product', {})

        if product.get('product_retailer_id'):
            return {
                'type': 'single_product',
                'product_retailer_id': product['product_retailer_id'],
                'body': f"{product.get('name', '')} - ${product.get('price', 0):.2f}"
            }

        # Sin catálogo
        return {'type': 'detail', 'product': product}

    # Default: no convertible
    return {'type': 'unknown'}


def _convert_menu_to_list(visual_data: Dict[str, Any]) -> list:
    """Convierte datos visuales del menú a formato de lista de WhatsApp"""
    sections = []

    categories = visual_data.get('categories', {})
    for cat_name, items in categories.items():
        section = {
            'title': cat_name[:24],  # Max 24 chars
            'items': [
                {
                    'id': str(item.get('id', i)),
                    'title': item.get('name', '')[:24],
                    'description': f"${item.get('price', 0):.2f}"[:72]
                }
                for i, item in enumerate(items[:10])  # Max 10 items
            ]
        }
        sections.append(section)

    return sections[:10]  # Max 10 sections


async def _send_order_to_kitchen(
    session_id: str,
    table_id: Optional[int],
    context: Dict[str, Any]
) -> Optional[str]:
    """Envía el pedido confirmado a cocina"""
    global _fsm, _restaurant_client

    if not _fsm or session_id not in _fsm.sessions:
        return None

    fsm_context = _fsm.sessions[session_id]

    if not fsm_context.order_items:
        return None

    try:
        items = []
        for item in fsm_context.order_items:
            items.append({
                'product_id': item.product_id,
                'quantity': item.quantity,
                'notes': item.notes if hasattr(item, 'notes') else None
            })

        # Determinar mesa
        final_table_id = table_id or 1

        # Enviar orden
        if _restaurant_client:
            order = await _restaurant_client.create_order(
                table_id=final_table_id,
                items=items,
                notes=f"Pedido por WhatsApp - Sesión: {session_id}"
            )

            # Limpiar carrito
            fsm_context.order_items = []
            fsm_context.order_total = 0.0

            logger.info(f"[Sales] Pedido #{order.get('id')} enviado a cocina")
            return str(order.get('id'))

        return None

    except Exception as e:
        logger.error(f"[Sales] Error enviando a cocina: {e}")
        return None


async def _handle_fallback(message: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Manejo de fallback cuando el FSM no está disponible"""
    message_lower = message.lower()

    # Respuestas básicas
    if any(word in message_lower for word in ['hola', 'buenas', 'buenos']):
        return {
            'response': '¡Hola! Soy el asistente virtual del restaurante. ¿En qué te puedo ayudar?',
            'text': '¡Hola! Soy el asistente virtual del restaurante. ¿En qué te puedo ayudar?',
            'buttons': [
                {'id': 'menu', 'title': 'Ver menú'},
                {'id': 'order', 'title': 'Hacer pedido'},
                {'id': 'promos', 'title': 'Promociones'}
            ],
            'state': 'greeting'
        }

    if any(word in message_lower for word in ['menú', 'menu', 'carta']):
        return {
            'response': 'Tenemos hamburguesas, tacos, bebidas y más. ¿Qué te gustaría ordenar?',
            'text': 'Tenemos hamburguesas, tacos, bebidas y más. ¿Qué te gustaría ordenar?',
            'state': 'browsing'
        }

    if any(word in message_lower for word in ['gracias', 'adios', 'bye']):
        return {
            'response': '¡Gracias por tu visita! Esperamos verte pronto.',
            'text': '¡Gracias por tu visita! Esperamos verte pronto.',
            'state': 'completed'
        }

    return {
        'response': '¿En qué te puedo ayudar? Puedes ver el menú, hacer un pedido o preguntar por promociones.',
        'text': '¿En qué te puedo ayudar? Puedes ver el menú, hacer un pedido o preguntar por promociones.',
        'buttons': [
            {'id': 'menu', 'title': 'Ver menú'},
            {'id': 'help', 'title': 'Ayuda'}
        ],
        'state': 'initial'
    }
