#!/usr/bin/env python3
# ============================================================
# FINE-TUNING SCRIPT - NLU Intent Classifier
# ============================================================
# Script para entrenar el modelo NLU con datos específicos
# del restaurante para mejorar accuracy ~25%
# ============================================================
# Uso:
#   python finetune_nlu.py --data training_data.json
#   python finetune_nlu.py --interactive
# ============================================================

import os
import sys
import json
import logging
import argparse
import random
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from pathlib import Path

# Agregar path del proyecto
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Intentar importar psycopg2 para conexión a PostgreSQL
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    from sentence_transformers import SentenceTransformer, InputExample, losses
    from torch.utils.data import DataLoader
    import torch
    TRAINING_AVAILABLE = True
except ImportError:
    TRAINING_AVAILABLE = False
    logger.error("Instala: pip install sentence-transformers torch")


# Datos de entrenamiento específicos del restaurante
# Formato: (texto, intent)
RESTAURANT_TRAINING_DATA = [
    # ============================================================
    # SALUDOS - Variaciones mexicanas
    # ============================================================
    ("hola buenas tardes", "greeting"),
    ("qué onda", "greeting"),
    ("buenas noches", "greeting"),
    ("hey qué tal", "greeting"),
    ("hola cómo están", "greeting"),

    # ============================================================
    # PREGUNTAS DE PRECIO
    # ============================================================
    ("cuánto cuesta la hamburguesa clásica", "ask_price"),
    ("a cómo está el taco de pastor", "ask_price"),
    ("qué precio tiene la ensalada césar", "ask_price"),
    ("cuánto vale el combo familiar", "ask_price"),
    ("a cuánto me sale todo", "ask_price"),
    ("cuánto es la cuenta", "ask_price"),
    ("me dice el precio de los tacos", "ask_price"),

    # ============================================================
    # PREGUNTAS DE INGREDIENTES
    # ============================================================
    ("qué lleva la hamburguesa especial", "ask_ingredients"),
    ("de qué es el taco campechano", "ask_ingredients"),
    ("qué trae la torta de milanesa", "ask_ingredients"),
    ("con qué viene la ensalada", "ask_ingredients"),
    ("tiene mayonesa la hamburguesa", "ask_ingredients"),
    ("lleva cebolla el taco", "ask_ingredients"),
    ("qué carne usan", "ask_ingredients"),

    # ============================================================
    # PREGUNTAS SOBRE PICANTE
    # ============================================================
    ("es picante el taco de suadero", "ask_spicy"),
    ("pica mucho la salsa", "ask_spicy"),
    ("tienen salsa que no pique", "ask_spicy"),
    ("qué tan picoso está", "ask_spicy"),
    ("lo pueden hacer sin chile", "ask_spicy"),

    # ============================================================
    # VER CATEGORÍAS DEL MENÚ
    # ============================================================
    ("qué hamburguesas tienen", "view_category"),
    ("muéstrame los tacos", "view_category"),
    ("qué bebidas hay", "view_category"),
    ("tienen postres", "view_category"),
    ("qué opciones de ensaladas tienen", "view_category"),
    ("hay algo vegetariano", "view_category"),
    ("qué tienen para niños", "view_category"),
    ("tienen combos", "view_category"),

    # ============================================================
    # AGREGAR AL PEDIDO
    # ============================================================
    ("quiero una hamburguesa doble", "add_to_order"),
    ("dame dos tacos de pastor", "add_to_order"),
    ("ponme una orden de papas", "add_to_order"),
    ("me da una coca cola", "add_to_order"),
    ("agrega una ensalada", "add_to_order"),
    ("también quiero un postre", "add_to_order"),
    ("otro refresco por favor", "add_to_order"),
    ("voy a querer tres hamburguesas", "add_to_order"),

    # ============================================================
    # RECOMENDACIONES - CASOS CRÍTICOS
    # ============================================================
    # Dieta y salud
    ("mi esposa está a dieta qué le recomiendo", "get_recommendation"),
    ("busco algo saludable", "get_recommendation"),
    ("qué tienen bajo en calorías", "get_recommendation"),
    ("algo ligero por favor", "get_recommendation"),
    ("opciones fit que tienen", "get_recommendation"),
    ("comida que no engorde", "get_recommendation"),
    ("algo nutritivo para mi hijo", "get_recommendation"),

    # Restricciones alimenticias
    ("soy vegetariano qué me recomiendas", "get_recommendation"),
    ("no como carne qué hay", "get_recommendation"),
    ("tengo diabetes qué puedo pedir", "get_recommendation"),
    ("opciones sin gluten", "get_recommendation"),
    ("soy intolerante a la lactosa", "get_recommendation"),

    # Generales
    ("qué me recomiendas", "get_recommendation"),
    ("cuál es el mejor platillo", "get_recommendation"),
    ("qué está bueno hoy", "get_recommendation"),
    ("cuál es la especialidad de la casa", "get_recommendation"),
    ("qué es lo más pedido", "get_recommendation"),
    ("ayúdame a elegir algo rico", "get_recommendation"),

    # ============================================================
    # ACEPTAR SUGERENCIA
    # ============================================================
    ("sí eso quiero", "accept_suggestion"),
    ("va dame eso", "accept_suggestion"),
    ("órale sí", "accept_suggestion"),
    ("perfecto así está bien", "accept_suggestion"),
    ("suena delicioso", "accept_suggestion"),
    ("le entro", "accept_suggestion"),
    ("sale", "accept_suggestion"),
    ("ok dame eso", "accept_suggestion"),

    # ============================================================
    # RECHAZAR SUGERENCIA
    # ============================================================
    ("no gracias así estoy bien", "reject_suggestion"),
    ("mejor no", "reject_suggestion"),
    ("paso", "reject_suggestion"),
    ("no me late", "reject_suggestion"),
    ("prefiero otra cosa", "reject_suggestion"),
    ("no se me antoja", "reject_suggestion"),
    ("nel", "reject_suggestion"),

    # ============================================================
    # FINALIZAR PEDIDO
    # ============================================================
    ("es todo gracias", "finish_order"),
    ("ya es todo", "finish_order"),
    ("nada más eso", "finish_order"),
    ("solo eso por favor", "finish_order"),
    ("con eso está bien", "finish_order"),
    ("ya no quiero nada más", "finish_order"),
    ("listo eso sería todo", "finish_order"),

    # ============================================================
    # DESPEDIDA
    # ============================================================
    ("gracias muy amable", "goodbye"),
    ("muchas gracias adiós", "goodbye"),
    ("hasta luego", "goodbye"),
    ("nos vemos", "goodbye"),
    ("bye gracias", "goodbye"),
    ("excelente servicio gracias", "goodbye"),

    # ============================================================
    # OBJECIONES DE PRECIO
    # ============================================================
    ("está muy caro", "handle_objection"),
    ("no me alcanza", "handle_objection"),
    ("hay algo más económico", "handle_objection"),
    ("tienen alguna promoción", "handle_objection"),
    ("hay descuento", "handle_objection"),
    ("está carísimo", "handle_objection"),

    # ============================================================
    # QUEJAS
    # ============================================================
    ("está fría la comida", "complaint"),
    ("esto no es lo que pedí", "complaint"),
    ("tardó mucho mi pedido", "complaint"),
    ("el servicio es muy lento", "complaint"),
    ("quiero hablar con el encargado", "complaint"),

    # ============================================================
    # SOLICITUDES DE SERVICIO
    # ============================================================
    ("me trae más salsa", "request_service"),
    ("necesito servilletas", "request_service"),
    ("puede traer la cuenta", "request_service"),
    ("más agua por favor", "request_service"),
    ("limones por favor", "request_service"),
]


# ============================================================
# EXTRACCIÓN DE DATOS DEL MENÚ REAL
# ============================================================

class MenuDataExtractor:
    """Extrae datos del menú desde PostgreSQL para generar ejemplos"""

    def __init__(self, db_url: str = None):
        self.db_url = db_url or os.getenv(
            'DATABASE_URL',
            'postgresql://restaurant:restaurant_2025@localhost:5432/restaurant_db'
        )
        self.products = []
        self.categories = []

    def extract_all(self) -> Dict:
        """Extrae todos los datos del menú"""
        if not DB_AVAILABLE:
            logger.warning("psycopg2 no disponible. Instalar: pip install psycopg2-binary")
            return {'categories': [], 'products': []}

        logger.info("Conectando a la base de datos...")
        try:
            conn = psycopg2.connect(self.db_url)
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Extraer categorías
                cur.execute("""
                    SELECT id, name, description
                    FROM categories
                    WHERE is_active = true
                    ORDER BY name
                """)
                self.categories = [dict(row) for row in cur.fetchall()]
                logger.info(f"Extraídas {len(self.categories)} categorías")

                # Extraer productos con su categoría
                cur.execute("""
                    SELECT
                        p.id,
                        p.name,
                        p.description,
                        p.price,
                        c.name as category
                    FROM products p
                    JOIN categories c ON p.category_id = c.id
                    WHERE p.is_active = true
                    ORDER BY c.name, p.name
                """)
                self.products = [dict(row) for row in cur.fetchall()]
                logger.info(f"Extraídos {len(self.products)} productos")

            conn.close()
        except Exception as e:
            logger.error(f"Error conectando a DB: {e}")
            return {'categories': [], 'products': []}

        return {
            'categories': self.categories,
            'products': self.products
        }


class MenuExampleGenerator:
    """Genera ejemplos de entrenamiento basados en el menú real"""

    # Templates para generar variaciones
    TEMPLATES = {
        'add_to_order': [
            "quiero {product}",
            "dame {product}",
            "ponme {product}",
            "me da {product}",
            "tráeme {product}",
            "voy a querer {product}",
            "una {product} por favor",
            "dos {product}",
            "{product} para llevar",
        ],
        'ask_price': [
            "cuánto cuesta {product}",
            "cuánto vale {product}",
            "qué precio tiene {product}",
            "a cómo está {product}",
            "cuánto es {product}",
        ],
        'ask_ingredients': [
            "qué lleva {product}",
            "qué ingredientes tiene {product}",
            "de qué está hecho {product}",
            "qué trae {product}",
        ],
        'view_category': [
            "quiero ver {category}",
            "muéstrame {category}",
            "qué {category} tienen",
            "tienen {category}",
            "qué hay de {category}",
        ],
        'get_recommendation': [
            "qué me recomiendas de {category}",
            "cuál es el mejor {category}",
            "qué {category} está bueno",
        ],
    }

    # Variaciones de nombres de productos (jerga mexicana)
    PRODUCT_NICKNAMES = {
        'cerveza': ['chela', 'cheve', 'birra', 'fría'],
        'hamburguesa': ['burger', 'hambur'],
        'coca-cola': ['coca', 'refresco'],
        'margarita': ['marga'],
        'agua': ['agüita'],
    }

    def __init__(self, menu_data: Dict):
        self.products = menu_data.get('products', [])
        self.categories = menu_data.get('categories', [])

    def _get_product_variations(self, product_name: str) -> List[str]:
        """Genera variaciones del nombre del producto"""
        variations = [product_name, product_name.lower()]

        # Agregar apodos conocidos
        for key, nicknames in self.PRODUCT_NICKNAMES.items():
            if key in product_name.lower():
                variations.extend(nicknames)

        # Sin artículos
        for article in ['el ', 'la ', 'los ', 'las ']:
            if product_name.lower().startswith(article):
                variations.append(product_name[len(article):])

        return list(set(variations))[:4]  # Máximo 4 variaciones

    def _get_category_variations(self, category_name: str) -> List[str]:
        """Genera variaciones del nombre de categoría"""
        variations = [category_name, category_name.lower()]

        # Singular/plural
        if category_name.endswith('s'):
            variations.append(category_name[:-1])
        else:
            variations.append(category_name + 's')

        return list(set(variations))[:3]

    def generate_examples(self) -> List[Tuple[str, str]]:
        """Genera ejemplos de entrenamiento basados en el menú"""
        examples = []

        # Generar ejemplos para productos
        for product in self.products:
            product_name = product['name']
            product_vars = self._get_product_variations(product_name)

            for intent, templates in self.TEMPLATES.items():
                if '{product}' in templates[0]:
                    for template in random.sample(templates, min(3, len(templates))):
                        var = random.choice(product_vars)
                        example = template.replace('{product}', var)
                        examples.append((example, intent))

        # Generar ejemplos para categorías
        for category in self.categories:
            category_name = category['name']
            category_vars = self._get_category_variations(category_name)

            for intent, templates in self.TEMPLATES.items():
                if '{category}' in templates[0]:
                    for template in templates:
                        for var in category_vars:
                            example = template.replace('{category}', var)
                            examples.append((example, intent))

        # Eliminar duplicados
        examples = list(set(examples))
        logger.info(f"Generados {len(examples)} ejemplos del menú")
        return examples

    def export_to_json(self, output_path: str) -> str:
        """Exporta ejemplos generados a JSON"""
        examples = self.generate_examples()
        data = [{"text": text, "intent": intent} for text, intent in examples]

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(f"Ejemplos exportados a: {output_path}")
        return output_path


def generate_menu_examples(db_url: str = None, output_path: str = None) -> List[Tuple[str, str]]:
    """
    Función principal para generar ejemplos del menú.

    Args:
        db_url: URL de conexión a PostgreSQL
        output_path: Ruta para exportar JSON (opcional)

    Returns:
        Lista de (texto, intent) generados
    """
    # Extraer datos del menú
    extractor = MenuDataExtractor(db_url)
    menu_data = extractor.extract_all()

    if not menu_data['products']:
        logger.warning("No se pudieron extraer productos del menú")
        return []

    # Generar ejemplos
    generator = MenuExampleGenerator(menu_data)
    examples = generator.generate_examples()

    # Exportar si se especificó ruta
    if output_path:
        generator.export_to_json(output_path)

    return examples


def create_training_pairs(data: List[Tuple[str, str]]) -> List[InputExample]:
    """
    Crea pares de entrenamiento para contrastive learning.

    Estrategia:
    - Textos del mismo intent = similares (label=1.0)
    - Textos de diferente intent = diferentes (label=0.0)
    """
    examples = []

    # Agrupar por intent
    intent_texts: Dict[str, List[str]] = {}
    for text, intent in data:
        if intent not in intent_texts:
            intent_texts[intent] = []
        intent_texts[intent].append(text)

    intents = list(intent_texts.keys())

    # Crear pares positivos (mismo intent)
    for intent, texts in intent_texts.items():
        for i, text1 in enumerate(texts):
            for text2 in texts[i+1:]:
                examples.append(InputExample(texts=[text1, text2], label=1.0))

    # Crear pares negativos (diferente intent)
    import random
    for i, intent1 in enumerate(intents):
        for intent2 in intents[i+1:]:
            texts1 = intent_texts[intent1]
            texts2 = intent_texts[intent2]

            # Seleccionar algunos pares aleatorios
            for _ in range(min(3, len(texts1), len(texts2))):
                t1 = random.choice(texts1)
                t2 = random.choice(texts2)
                examples.append(InputExample(texts=[t1, t2], label=0.0))

    return examples


def finetune_model(
    base_model: str = "paraphrase-multilingual-MiniLM-L12-v2",
    training_data: List[Tuple[str, str]] = None,
    output_path: str = None,
    epochs: int = 3,
    batch_size: int = 16
):
    """
    Fine-tunea el modelo con datos del restaurante.

    Args:
        base_model: Modelo base a usar
        training_data: Lista de (texto, intent)
        output_path: Donde guardar el modelo
        epochs: Épocas de entrenamiento
        batch_size: Tamaño de batch
    """
    if not TRAINING_AVAILABLE:
        logger.error("Dependencias no disponibles")
        return None

    training_data = training_data or RESTAURANT_TRAINING_DATA

    logger.info(f"Cargando modelo base: {base_model}")
    model = SentenceTransformer(base_model)

    logger.info(f"Creando {len(training_data)} ejemplos de entrenamiento...")
    train_examples = create_training_pairs(training_data)
    logger.info(f"Pares de entrenamiento creados: {len(train_examples)}")

    # DataLoader
    train_dataloader = DataLoader(
        train_examples,
        shuffle=True,
        batch_size=batch_size
    )

    # Loss function: CosineSimilarityLoss
    train_loss = losses.CosineSimilarityLoss(model)

    # Output path
    if not output_path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"./models/restaurant-nlu-{timestamp}"

    logger.info(f"Iniciando fine-tuning ({epochs} épocas)...")
    logger.info(f"Modelo se guardará en: {output_path}")

    # Entrenar
    model.fit(
        train_objectives=[(train_dataloader, train_loss)],
        epochs=epochs,
        warmup_steps=100,
        output_path=output_path,
        show_progress_bar=True
    )

    logger.info(f"Fine-tuning completado. Modelo guardado en: {output_path}")
    return output_path


def load_training_data(filepath: str) -> List[Tuple[str, str]]:
    """Carga datos de entrenamiento desde JSON"""
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    examples = []
    for item in data:
        if isinstance(item, dict):
            examples.append((item['text'], item['intent']))
        elif isinstance(item, list) and len(item) == 2:
            examples.append((item[0], item[1]))

    return examples


def export_training_template(filepath: str):
    """Exporta plantilla de datos de entrenamiento"""
    template = [
        {"text": "ejemplo de texto del usuario", "intent": "nombre_del_intent"},
        {"text": "otro ejemplo", "intent": "nombre_del_intent"},
    ]

    # Agregar datos existentes como ejemplo
    existing = [
        {"text": text, "intent": intent}
        for text, intent in RESTAURANT_TRAINING_DATA[:20]
    ]

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)

    logger.info(f"Plantilla exportada a: {filepath}")


def interactive_data_collection():
    """Modo interactivo para recolectar datos de entrenamiento"""
    logger.info("=== Modo Interactivo de Recolección de Datos ===")
    logger.info("Escribe frases y asigna intents. Escribe 'salir' para terminar.")

    intents = [
        'greeting', 'ask_price', 'ask_ingredients', 'ask_spicy',
        'view_category', 'add_to_order', 'get_recommendation',
        'accept_suggestion', 'reject_suggestion', 'finish_order',
        'goodbye', 'handle_objection', 'complaint', 'request_service'
    ]

    collected = []

    while True:
        print("\n" + "="*50)
        text = input("Frase del usuario (o 'salir'): ").strip()

        if text.lower() == 'salir':
            break

        print("\nIntents disponibles:")
        for i, intent in enumerate(intents, 1):
            print(f"  {i}. {intent}")

        try:
            choice = int(input("Número de intent: "))
            if 1 <= choice <= len(intents):
                intent = intents[choice - 1]
                collected.append((text, intent))
                print(f"✓ Agregado: '{text}' -> {intent}")
            else:
                print("Número inválido")
        except ValueError:
            print("Ingresa un número válido")

    if collected:
        # Guardar datos recolectados
        filepath = f"collected_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(
                [{"text": t, "intent": i} for t, i in collected],
                f, ensure_ascii=False, indent=2
            )
        logger.info(f"Datos guardados en: {filepath}")

        # Preguntar si hacer fine-tuning
        if input("\n¿Ejecutar fine-tuning con estos datos? (s/n): ").lower() == 's':
            finetune_model(training_data=collected)

    return collected


def evaluate_model(model_path: str, test_data: List[Tuple[str, str]] = None):
    """Evalúa el modelo fine-tuneado"""
    if not TRAINING_AVAILABLE:
        return

    test_data = test_data or RESTAURANT_TRAINING_DATA[-20:]  # Últimos 20 como test

    logger.info(f"Evaluando modelo: {model_path}")
    model = SentenceTransformer(model_path)

    # Crear embeddings de referencia por intent
    from collections import defaultdict
    import numpy as np

    intent_embeddings = defaultdict(list)
    for text, intent in RESTAURANT_TRAINING_DATA[:-20]:  # Usar resto como referencia
        emb = model.encode(text)
        intent_embeddings[intent].append(emb)

    # Promediar embeddings por intent
    intent_centroids = {
        intent: np.mean(embs, axis=0)
        for intent, embs in intent_embeddings.items()
    }

    # Evaluar
    correct = 0
    total = len(test_data)

    for text, expected_intent in test_data:
        text_emb = model.encode(text)

        # Encontrar intent más cercano
        best_intent = None
        best_sim = -1

        for intent, centroid in intent_centroids.items():
            sim = np.dot(text_emb, centroid) / (
                np.linalg.norm(text_emb) * np.linalg.norm(centroid)
            )
            if sim > best_sim:
                best_sim = sim
                best_intent = intent

        if best_intent == expected_intent:
            correct += 1
            status = "✓"
        else:
            status = "✗"

        logger.info(f"{status} '{text}' -> {best_intent} (esperado: {expected_intent})")

    accuracy = correct / total * 100
    logger.info(f"\nAccuracy: {accuracy:.1f}% ({correct}/{total})")
    return accuracy


def main():
    parser = argparse.ArgumentParser(
        description="Fine-tuning NLU para restaurante",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:

  # Generar ejemplos desde el menú de la DB
  python finetune_nlu.py --from-menu --export-json menu_examples.json

  # Fine-tuning con ejemplos del menú + base
  python finetune_nlu.py --from-menu

  # Fine-tuning con archivo JSON personalizado
  python finetune_nlu.py --data mis_ejemplos.json

  # Modo interactivo para recolectar datos
  python finetune_nlu.py --interactive

  # Evaluar modelo existente
  python finetune_nlu.py --evaluate ./models/restaurant-nlu-20231210
        """
    )
    parser.add_argument('--data', type=str, help='Archivo JSON con datos de entrenamiento')
    parser.add_argument('--output', type=str, help='Directorio de salida para el modelo')
    parser.add_argument('--epochs', type=int, default=3, help='Épocas de entrenamiento')
    parser.add_argument('--batch-size', type=int, default=16, help='Tamaño de batch')
    parser.add_argument('--interactive', action='store_true', help='Modo interactivo')
    parser.add_argument('--export-template', type=str, help='Exportar plantilla de datos')
    parser.add_argument('--evaluate', type=str, help='Evaluar modelo existente')
    parser.add_argument('--base-model', type=str,
                       default='paraphrase-multilingual-MiniLM-L12-v2',
                       help='Modelo base para fine-tuning')
    # NUEVAS OPCIONES PARA MENÚ
    parser.add_argument('--from-menu', action='store_true',
                       help='Generar ejemplos automáticamente desde el menú de la DB')
    parser.add_argument('--db-url', type=str,
                       help='URL de conexión a PostgreSQL',
                       default=os.getenv('DATABASE_URL'))
    parser.add_argument('--export-json', type=str,
                       help='Exportar ejemplos generados del menú a JSON')
    parser.add_argument('--only-generate', action='store_true',
                       help='Solo generar ejemplos, no entrenar')

    args = parser.parse_args()

    print("=" * 60)
    print("FINE-TUNING NLU - Restaurant Voice System")
    print("=" * 60)

    if args.export_template:
        export_training_template(args.export_template)
        return

    if args.interactive:
        interactive_data_collection()
        return

    if args.evaluate:
        evaluate_model(args.evaluate)
        return

    # Fine-tuning
    training_data = list(RESTAURANT_TRAINING_DATA)  # Base de ejemplos

    # Cargar datos de archivo JSON si se especifica
    if args.data:
        json_data = load_training_data(args.data)
        training_data.extend(json_data)
        logger.info(f"Cargados {len(json_data)} ejemplos de {args.data}")

    # Generar ejemplos del menú si se solicita
    if args.from_menu:
        logger.info("\n=== Generando ejemplos del menú ===")
        menu_examples = generate_menu_examples(
            db_url=args.db_url,
            output_path=args.export_json
        )
        if menu_examples:
            training_data.extend(menu_examples)
            logger.info(f"Agregados {len(menu_examples)} ejemplos del menú")

        if args.only_generate:
            logger.info(f"\nTotal de ejemplos generados: {len(training_data)}")
            if args.export_json:
                logger.info(f"Exportados a: {args.export_json}")
            return

    # Eliminar duplicados
    training_data = list(set(training_data))
    logger.info(f"\nTotal de ejemplos de entrenamiento: {len(training_data)}")

    # Entrenar modelo
    model_path = finetune_model(
        base_model=args.base_model,
        training_data=training_data,
        output_path=args.output,
        epochs=args.epochs,
        batch_size=args.batch_size
    )

    if model_path:
        logger.info("\n" + "=" * 60)
        logger.info("FINE-TUNING COMPLETADO")
        logger.info("=" * 60)
        logger.info(f"Modelo guardado en: {model_path}")
        logger.info(f"\nPara usar este modelo, actualiza intent_classifier.py:")
        logger.info(f'  DEFAULT_MODEL = "{model_path}"')

        # Evaluar automáticamente
        try:
            response = input("\n¿Evaluar modelo? (s/n): ")
            if response.lower() == 's':
                evaluate_model(model_path)
        except:
            pass  # En caso de ejecución no interactiva


if __name__ == "__main__":
    main()
