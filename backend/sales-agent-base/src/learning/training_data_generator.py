# ============================================================
# TRAINING DATA GENERATOR - Generador de Datos de Entrenamiento
# ============================================================
# Genera ejemplos de entrenamiento a partir de feedback
# Augmenta datos usando variaciones
# Exporta en formatos compatibles con NLU
# ============================================================

import json
import logging
import random
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class TrainingExample:
    """Ejemplo de entrenamiento"""
    text: str
    intent: str
    entities: Dict = None
    source: str = "generated"
    confidence: float = 1.0


class TrainingDataGenerator:
    """
    Generador de datos de entrenamiento para NLU.

    Funcionalidades:
    1. Extrae ejemplos de conversaciones exitosas
    2. Genera variaciones usando augmentación
    3. Balancea clases de intents
    4. Exporta en múltiples formatos
    """

    # Variaciones para augmentación
    AUGMENTATION_PATTERNS = {
        "prefixes": [
            "", "oye ", "mira ", "por favor ", "este ", "bueno ",
            "a ver ", "mmm ", "eh ", "pues ", "entonces "
        ],
        "suffixes": [
            "", " por favor", " porfa", " gracias", " plis",
            " ¿no?", " va", " ¿sí?"
        ],
        "typo_chars": {
            'a': ['a', 'á', 's', 'q'],
            'e': ['e', 'é', 'w', 'r'],
            'i': ['i', 'í', 'o', 'u'],
            'o': ['o', 'ó', 'p', 'i'],
            'u': ['u', 'ú', 'i', 'y'],
            'n': ['n', 'ñ', 'm', 'b'],
            's': ['s', 'z', 'c', 'a'],
            'c': ['c', 's', 'k', 'z'],
            'b': ['b', 'v', 'n'],
            'v': ['v', 'b'],
        },
        "synonyms": {
            "quiero": ["dame", "ponme", "me das", "necesito", "me pones"],
            "hamburguesa": ["hamburgesa", "burger", "hamburgueza", "amburguesa"],
            "cuánto": ["cuanto", "qué precio", "a cuánto", "precio de"],
            "cuesta": ["vale", "es", "sale", "está"],
            "gracias": ["thank you", "thx", "grax", "grasias"],
            "está bien": ["ok", "okey", "sale", "va", "órale"],
            "no gracias": ["no", "nel", "nop", "no quiero", "así está bien"],
            "sí": ["si", "simón", "claro", "por supuesto", "órale"],
            "el menú": ["la carta", "los platillos", "que tienen", "que hay"],
        }
    }

    def __init__(self, feedback_loop=None):
        self.feedback_loop = feedback_loop
        self._examples: List[TrainingExample] = []

    def add_example(self, text: str, intent: str, entities: Dict = None):
        """Agrega ejemplo de entrenamiento"""
        self._examples.append(TrainingExample(
            text=text.strip().lower(),
            intent=intent,
            entities=entities or {}
        ))

    def add_examples_from_feedback(self, min_confidence: float = 0.85):
        """Agrega ejemplos desde el feedback loop"""
        if not self.feedback_loop:
            from .feedback_loop import get_feedback_loop
            self.feedback_loop = get_feedback_loop()

        examples = self.feedback_loop.generate_training_examples()
        for ex in examples:
            if ex.get("confidence", 0) >= min_confidence:
                self.add_example(
                    text=ex["text"],
                    intent=ex["intent"]
                )

        logger.info(f"[TRAINING] Agregados {len(examples)} ejemplos desde feedback")

    def augment_example(self, text: str, num_variations: int = 3) -> List[str]:
        """Genera variaciones de un ejemplo"""
        variations = [text]

        for _ in range(num_variations):
            variant = text

            # Agregar prefijo aleatorio
            if random.random() < 0.3:
                prefix = random.choice(self.AUGMENTATION_PATTERNS["prefixes"])
                variant = prefix + variant

            # Agregar sufijo aleatorio
            if random.random() < 0.3:
                suffix = random.choice(self.AUGMENTATION_PATTERNS["suffixes"])
                variant = variant + suffix

            # Introducir typos ocasionales
            if random.random() < 0.2:
                variant = self._introduce_typo(variant)

            # Reemplazar sinónimos
            if random.random() < 0.3:
                variant = self._apply_synonyms(variant)

            if variant != text and variant not in variations:
                variations.append(variant)

        return variations

    def _introduce_typo(self, text: str) -> str:
        """Introduce un typo aleatorio"""
        if len(text) < 5:
            return text

        chars = list(text)
        idx = random.randint(0, len(chars) - 1)
        char = chars[idx].lower()

        if char in self.AUGMENTATION_PATTERNS["typo_chars"]:
            chars[idx] = random.choice(self.AUGMENTATION_PATTERNS["typo_chars"][char])

        return ''.join(chars)

    def _apply_synonyms(self, text: str) -> str:
        """Reemplaza palabras con sinónimos"""
        for word, synonyms in self.AUGMENTATION_PATTERNS["synonyms"].items():
            if word in text.lower():
                replacement = random.choice(synonyms)
                text = re.sub(word, replacement, text, flags=re.IGNORECASE)
                break  # Solo un reemplazo por vez
        return text

    def generate_augmented_dataset(self, augmentation_factor: int = 3) -> List[TrainingExample]:
        """Genera dataset aumentado"""
        augmented = []

        for example in self._examples:
            # Agregar original
            augmented.append(example)

            # Generar variaciones
            variations = self.augment_example(example.text, augmentation_factor)
            for variant in variations[1:]:  # Excluir original
                augmented.append(TrainingExample(
                    text=variant,
                    intent=example.intent,
                    entities=example.entities,
                    source="augmented"
                ))

        logger.info(
            f"[TRAINING] Dataset aumentado: {len(self._examples)} → {len(augmented)} ejemplos"
        )
        return augmented

    def balance_classes(self, examples: List[TrainingExample], target_per_class: int = 50) -> List[TrainingExample]:
        """Balancea clases para evitar desbalance"""
        # Agrupar por intent
        by_intent: Dict[str, List[TrainingExample]] = {}
        for ex in examples:
            if ex.intent not in by_intent:
                by_intent[ex.intent] = []
            by_intent[ex.intent].append(ex)

        balanced = []
        for intent, intent_examples in by_intent.items():
            if len(intent_examples) >= target_per_class:
                # Subsamplear si hay demasiados
                sampled = random.sample(intent_examples, target_per_class)
            else:
                # Oversamplear si hay muy pocos
                sampled = intent_examples.copy()
                while len(sampled) < target_per_class:
                    sampled.append(random.choice(intent_examples))

            balanced.extend(sampled)

        random.shuffle(balanced)
        logger.info(f"[TRAINING] Dataset balanceado: {len(balanced)} ejemplos")
        return balanced

    def export_json(self, output_path: str, augment: bool = True, balance: bool = True) -> str:
        """Exporta dataset en formato JSON"""
        examples = self._examples

        if augment:
            examples = self.generate_augmented_dataset()

        if balance:
            examples = self.balance_classes(examples)

        data = {
            "metadata": {
                "generated_at": datetime.utcnow().isoformat(),
                "total_examples": len(examples),
                "intents": list(set(ex.intent for ex in examples)),
                "augmented": augment,
                "balanced": balance
            },
            "examples": [
                {
                    "text": ex.text,
                    "intent": ex.intent,
                    "entities": ex.entities,
                    "source": ex.source
                }
                for ex in examples
            ]
        }

        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(f"[TRAINING] Exportado a {output_file}")
        return str(output_file)

    def export_rasa_format(self, output_path: str) -> str:
        """Exporta en formato compatible con Rasa NLU"""
        examples = self.generate_augmented_dataset()

        # Agrupar por intent
        by_intent: Dict[str, List[str]] = {}
        for ex in examples:
            if ex.intent not in by_intent:
                by_intent[ex.intent] = []
            by_intent[ex.intent].append(ex.text)

        # Generar formato YAML de Rasa
        lines = ["version: '3.1'", "nlu:"]
        for intent, texts in by_intent.items():
            lines.append(f"- intent: {intent}")
            lines.append("  examples: |")
            for text in texts:
                lines.append(f"    - {text}")
            lines.append("")

        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

        logger.info(f"[TRAINING] Exportado formato Rasa a {output_file}")
        return str(output_file)

    def export_sentence_transformers_format(self, output_path: str) -> str:
        """Exporta en formato para fine-tuning de Sentence Transformers"""
        examples = self.generate_augmented_dataset()

        # Formato: texto | intent
        lines = []
        for ex in examples:
            lines.append(f"{ex.text}\t{ex.intent}")

        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

        logger.info(f"[TRAINING] Exportado formato ST a {output_file}")
        return str(output_file)

    def get_statistics(self) -> Dict:
        """Obtiene estadísticas del dataset"""
        if not self._examples:
            return {"total": 0}

        # Contar por intent
        intent_counts: Dict[str, int] = {}
        for ex in self._examples:
            intent_counts[ex.intent] = intent_counts.get(ex.intent, 0) + 1

        return {
            "total_examples": len(self._examples),
            "unique_intents": len(intent_counts),
            "intent_distribution": intent_counts,
            "avg_text_length": sum(len(ex.text) for ex in self._examples) / len(self._examples)
        }


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def generate_training_examples(
    output_path: str = "/app/data/training/nlu_data.json",
    min_confidence: float = 0.85,
    augment: bool = True,
    balance: bool = True
) -> str:
    """
    Genera ejemplos de entrenamiento desde el feedback loop.

    Args:
        output_path: Ruta de salida
        min_confidence: Confianza mínima para incluir ejemplos
        augment: Si se debe hacer augmentación
        balance: Si se deben balancear las clases

    Returns:
        Ruta del archivo generado
    """
    generator = TrainingDataGenerator()
    generator.add_examples_from_feedback(min_confidence)

    if len(generator._examples) == 0:
        logger.warning("[TRAINING] No hay ejemplos suficientes en el feedback")
        return ""

    return generator.export_json(output_path, augment=augment, balance=balance)


def add_base_training_examples(generator: TrainingDataGenerator):
    """Agrega ejemplos base de entrenamiento"""
    base_examples = {
        "greeting": [
            "hola", "buenas tardes", "buenas noches", "buenos días",
            "qué tal", "hola buenas", "hey"
        ],
        "view_category": [
            "qué hamburguesas tienen", "quiero ver los tacos",
            "muéstrame las bebidas", "qué hay de postres"
        ],
        "add_to_order": [
            "quiero una hamburguesa", "dame dos tacos",
            "ponme una coca", "me das unas papas"
        ],
        "ask_price": [
            "cuánto cuesta", "qué precio tiene",
            "a cuánto está", "cuánto sale"
        ],
        "ask_ingredients": [
            "qué lleva", "de qué es", "qué tiene",
            "cuáles son los ingredientes"
        ],
        "finish_order": [
            "es todo", "ya es todo", "nada más",
            "solo eso", "así está bien"
        ],
        "accept_suggestion": [
            "sí", "va", "órale", "claro", "está bien"
        ],
        "reject_suggestion": [
            "no", "no gracias", "así está bien", "no quiero"
        ],
        "goodbye": [
            "gracias", "adiós", "hasta luego", "nos vemos"
        ]
    }

    for intent, examples in base_examples.items():
        for text in examples:
            generator.add_example(text, intent)
