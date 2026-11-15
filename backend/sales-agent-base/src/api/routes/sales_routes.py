"""
================================================================================
SALES ROUTES - mensajes de WhatsApp hacia el agente de taxi
================================================================================
POST /api/v1/sales/message — lo llama whatsapp-gateway (main_taxi.py) con
context.tenant_id = "taxi". Responde con el TaxiAgent (LLM + function calling,
src/taxi/agent.py).

Antes este archivo también tenía el FSM del restaurante (mesas, carrito, menú,
envío a cocina); nunca se usó en TaxiCerca y se quitó (ver git history).
================================================================================
"""

from flask import Blueprint, request, jsonify
import logging

logger = logging.getLogger(__name__)

sales_bp = Blueprint('sales', __name__, url_prefix='/api/v1/sales')


@sales_bp.route('/message', methods=['POST'])
async def process_sales_message():
    """Body JSON: session_id, message, channel, context (phone, customer_name, tenant_id).
    Devuelve response/text y state."""
    data = request.get_json() or {}

    session_id = data.get('session_id')
    message = data.get('message', '')
    channel = data.get('channel', 'unknown')

    if not session_id:
        return jsonify({'error': 'session_id requerido'}), 400

    if not message:
        return jsonify({'error': 'message requerido'}), 400

    logger.info(f"[Sales:{channel}] Mensaje de {session_id}: {message[:50]}...")
    return await _handle_taxi_message(session_id, message)


async def _handle_taxi_message(session_id: str, message: str):
    """Procesa mensajes del canal de taxis usando TaxiAgent (LLM + function calling)."""
    try:
        from src.taxi.agent import get_taxi_agent
        agent = get_taxi_agent()
        result = agent.process(session_id, message)
        return jsonify({
            'response': result.response_text,
            'text': result.response_text,
            'state': result.new_state.value,
            'intent': result.intent,
        })
    except Exception as e:
        logger.error(f"[Taxi] Error: {e}", exc_info=True)
        return jsonify({
            'response': 'El servicio de taxi está temporalmente no disponible. Intenta de nuevo.',
            'text': 'El servicio de taxi está temporalmente no disponible. Intenta de nuevo.',
            'state': 'error',
        }), 500
