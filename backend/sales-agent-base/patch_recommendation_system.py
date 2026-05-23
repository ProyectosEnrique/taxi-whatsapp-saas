"""
Script para aplicar el sistema de recomendaciones inteligentes
Modifica app.py para integrar el nuevo motor de recomendaciones
"""

import re

# Leer archivo original
with open('src/api/app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Agregar imports
import_section = """# Importar módulos del proyecto
from ..core.config import settings
from ..core.session_manager import get_session_manager
from ..restaurant.api_client import get_restaurant_client
from ..restaurant.stats_client import get_stats_client
from ..nlp.intent_recognizer import get_intent_recognizer, Intent
from ..nlp.recommendation_engine import get_recommendation_engine
from ..voice.stt_handler import get_stt_handler
from ..voice.tts_handler import get_tts_handler"""

content = re.sub(
    r'# Importar módulos del proyecto\n.*?from \.\.voice\.tts_handler import get_tts_handler',
    import_section,
    content,
    flags=re.DOTALL
)

# 2. Agregar import de datetime al inicio si no existe
if 'from datetime import datetime' not in content:
    content = re.sub(
        r'(import tempfile)',
        r'\1\nfrom datetime import datetime',
        content
    )

# 3. Agregar inicialización del recommendation_engine
if 'recommendation_engine = get_recommendation_engine()' not in content:
    content = re.sub(
        r'(intent_recognizer = get_intent_recognizer\(\))',
        r'\1\nrecommendation_engine = get_recommendation_engine()',
        content
    )

# 4. Reemplazar lógica de GET_RECOMMENDATION
new_recommendation_logic = '''elif detected_intent == Intent.GET_RECOMMENDATION:
            # SISTEMA DE RECOMENDACIONES INTELIGENTE v2.0
            import asyncio

            # 1. Obtener estadísticas de popularidad
            stats_client = await get_stats_client()
            popularity_stats = await stats_client.get_product_stats()

            # 2. Obtener historial del usuario/mesa
            table_id = session_data.get('table_id')
            order_history = []
            if table_id:
                order_history = await stats_client.get_user_order_history(table_id=table_id)

            # 3. Construir contexto completo
            recommendation_context = {
                'dietary_preference': entities.get('dietary_preference', ''),
                'meal_type': entities.get('meal_type', ''),
                'budget': entities.get('budget', ''),
                'current_time': datetime.now().time(),
                'order_history': order_history,
                'quick_service': False
            }

            # 4. Generar recomendaciones inteligentes
            result = await recommendation_engine.generate_recommendation_response(
                products=menu,
                context=recommendation_context,
                popularity_stats=popularity_stats
            )

            # 5. Usar respuesta generada
            response_text = result['response_text']
            order_data = {"visual_data": result['visual_data']}

            logger.info(
                f"Recomendaciones inteligentes: "
                f"{[p['name'] for p in result['recommendations']]}"
            )'''

# Buscar y reemplazar el bloque completo de GET_RECOMMENDATION
pattern = r'elif detected_intent == Intent\.GET_RECOMMENDATION:.*?(?=\n        elif detected_intent|$)'
content = re.sub(pattern, new_recommendation_logic, content, flags=re.DOTALL)

# Guardar archivo modificado
with open('src/api/app.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Sistema de recomendaciones inteligentes aplicado exitosamente")
print("📝 Archivo app.py actualizado")
print("🔄 Recuerda reiniciar el contenedor: docker restart restaurant_voice_assistant")
