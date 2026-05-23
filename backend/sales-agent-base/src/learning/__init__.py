# ============================================================
# LEARNING MODULE - Feedback Loop para Aprendizaje Continuo
# ============================================================
# Captura interacciones exitosas/fallidas
# Genera ejemplos de entrenamiento automáticamente
# Mejora NLU basado en datos reales
# Entrena LoRA con conversaciones de Cerebras
# ============================================================

from .feedback_loop import (
    FeedbackLoop,
    get_feedback_loop,
    FeedbackType,
    FeedbackEntry,
    record_feedback,
    record_successful_interaction,
    record_failed_interaction
)

from .training_data_generator import (
    TrainingDataGenerator,
    generate_training_examples
)

from .lora_training_collector import (
    LoRATrainingCollector,
    LoRATrainingExample,
    InteractionType,
    get_lora_collector,
    record_cerebras_success
)

__all__ = [
    # Feedback Loop
    'FeedbackLoop',
    'get_feedback_loop',
    'FeedbackType',
    'FeedbackEntry',
    'record_feedback',
    'record_successful_interaction',
    'record_failed_interaction',
    # Training Data Generator
    'TrainingDataGenerator',
    'generate_training_examples',
    # LoRA Training Collector
    'LoRATrainingCollector',
    'LoRATrainingExample',
    'InteractionType',
    'get_lora_collector',
    'record_cerebras_success'
]
