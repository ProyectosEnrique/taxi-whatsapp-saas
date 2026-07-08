# ============================================================
# TAXI AGENT — API
# ============================================================
# Única responsabilidad en producción: exponer /api/v1/sales/message
# para que whatsapp-gateway (main_taxi.py) hable con el agente de
# taxi (LLM + function calling, src/taxi/agent.py).
#
# Este archivo se llamaba app_v2.py porque originalmente era la v2
# (FSM) de un asistente de ventas multi-tenant (restaurante, farmacia,
# vinetería, taxi). Toda esa maquinaria multi-tenant nunca fue tocada
# por el flujo real de taxi (_handle_taxi_message en sales_routes.py
# hace su propio import de src.taxi.agent y no depende de FSM, tenant
# manager, ni restaurant client) — se quitó de aquí. Ver git history
# de este archivo si se necesita recuperar esa lógica.
# ============================================================

import os
import logging

from flask import Flask, jsonify
from flask_cors import CORS

from src.api.routes.sales_routes import sales_bp

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

app.register_blueprint(sales_bp)


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check — usado por el HEALTHCHECK del Dockerfile."""
    return jsonify({'status': 'healthy', 'service': 'taxi-agent'})


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
