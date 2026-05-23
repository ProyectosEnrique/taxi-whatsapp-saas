# ============================================================
# LORA TRAINING COLLECTOR - Recolector de Datos para LoRA
# ============================================================
# Guarda conversaciones exitosas de Cerebras para entrenar LoRA.
# Cuando Cerebras funciona bien, guardamos el ejemplo para que
# LoRA pueda aprender a responder igual en modo offline.
# ============================================================

import json
import logging
import os
import threading
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from enum import Enum

logger = logging.getLogger(__name__)


class InteractionType(Enum):
    """Tipos de interacción guardados"""
    CLASSIFICATION = "classification"      # Clasificación de intent
    CONVERSATION = "conversation"          # Respuesta conversacional
    ORDER_EXTRACTION = "order_extraction"  # Extracción de pedidos
    FULL_TURN = "full_turn"               # Turno completo (input → output)


@dataclass
class LoRATrainingExample:
    """Ejemplo de entrenamiento para LoRA"""
    # Input
    user_input: str
    context: Dict[str, Any]  # Estado, carrito, etc.

    # Output de Cerebras (lo que queremos que LoRA aprenda)
    intent: str
    response: str
    extracted_products: List[Dict] = None
    entities: Dict[str, Any] = None

    # Metadata
    interaction_type: str = "full_turn"
    confidence: float = 1.0
    timestamp: str = ""
    session_id: str = ""

    # Para fine-tuning
    system_prompt: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()
        if self.extracted_products is None:
            self.extracted_products = []
        if self.entities is None:
            self.entities = {}

    def to_training_format(self) -> Dict:
        """
        Convierte a formato de entrenamiento para LoRA.
        Formato compatible con Hugging Face / Unsloth.
        """
        # Construir el prompt como lo haría Cerebras
        context_str = ""
        if self.context:
            if self.context.get('cart_items'):
                context_str += f"\nCarrito: {', '.join(self.context['cart_items'][:3])}"
            if self.context.get('current_state'):
                context_str += f"\nEstado: {self.context['current_state']}"

        # Formato Alpaca/Llama
        return {
            "instruction": self.system_prompt or "Eres un mesero experto en un restaurante mexicano.",
            "input": f"Cliente: {self.user_input}{context_str}",
            "output": json.dumps({
                "intent": self.intent,
                "response": self.response,
                "products": self.extracted_products,
                "entities": self.entities
            }, ensure_ascii=False),
            "metadata": {
                "confidence": self.confidence,
                "interaction_type": self.interaction_type,
                "timestamp": self.timestamp
            }
        }

    def to_chat_format(self) -> Dict:
        """
        Convierte a formato de chat (messages) para fine-tuning.
        Compatible con formato ChatML / OpenAI.
        """
        return {
            "messages": [
                {
                    "role": "system",
                    "content": self.system_prompt or "Eres un mesero experto en un restaurante mexicano."
                },
                {
                    "role": "user",
                    "content": self.user_input
                },
                {
                    "role": "assistant",
                    "content": self.response
                }
            ],
            "metadata": {
                "intent": self.intent,
                "products": self.extracted_products,
                "confidence": self.confidence,
                "timestamp": self.timestamp
            }
        }


class LoRATrainingCollector:
    """
    Recolector de datos de entrenamiento para LoRA.

    Guarda automáticamente las interacciones exitosas con Cerebras
    para poder entrenar LoRA y funcionar offline.

    Uso:
        collector = get_lora_collector()

        # Después de una respuesta exitosa de Cerebras:
        collector.record_successful_interaction(
            user_input="quiero 2 tacos",
            intent="add_to_order",
            response="¡Perfecto! Te agrego 2 tacos...",
            extracted_products=[{"name": "Taco al Pastor", "quantity": 2}],
            confidence=0.95
        )
    """

    def __init__(
        self,
        storage_path: str = "/app/data/learning/lora_training",
        min_confidence: float = 0.8,
        auto_save_interval: int = 10,  # Guardar cada N ejemplos
        max_examples_per_file: int = 1000
    ):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.min_confidence = min_confidence
        self.auto_save_interval = auto_save_interval
        self.max_examples_per_file = max_examples_per_file

        # Buffer en memoria
        self._buffer: List[LoRATrainingExample] = []
        self._lock = threading.Lock()

        # Estadísticas
        self.stats = {
            "total_recorded": 0,
            "total_saved": 0,
            "by_intent": {},
            "by_type": {}
        }

        # Cargar estadísticas existentes
        self._load_stats()

        logger.info(f"[LORA_COLLECTOR] Inicializado en {self.storage_path}")

    def _load_stats(self):
        """Carga estadísticas de sesiones anteriores"""
        stats_file = self.storage_path / "stats.json"
        if stats_file.exists():
            try:
                with open(stats_file, 'r', encoding='utf-8') as f:
                    self.stats = json.load(f)
                logger.info(f"[LORA_COLLECTOR] Estadísticas cargadas: {self.stats['total_saved']} ejemplos previos")
            except Exception as e:
                logger.warning(f"[LORA_COLLECTOR] Error cargando stats: {e}")

    def _save_stats(self):
        """Guarda estadísticas"""
        stats_file = self.storage_path / "stats.json"
        try:
            with open(stats_file, 'w', encoding='utf-8') as f:
                json.dump(self.stats, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"[LORA_COLLECTOR] Error guardando stats: {e}")

    def record_successful_interaction(
        self,
        user_input: str,
        intent: str,
        response: str,
        extracted_products: List[Dict] = None,
        entities: Dict = None,
        context: Dict = None,
        confidence: float = 1.0,
        interaction_type: InteractionType = InteractionType.FULL_TURN,
        session_id: str = "",
        system_prompt: str = ""
    ) -> bool:
        """
        Registra una interacción exitosa para entrenamiento.

        Args:
            user_input: Lo que dijo el usuario
            intent: Intent clasificado
            response: Respuesta generada por Cerebras
            extracted_products: Productos extraídos (para pedidos)
            entities: Entidades extraídas
            context: Contexto de la conversación
            confidence: Confianza de la clasificación
            interaction_type: Tipo de interacción
            session_id: ID de sesión
            system_prompt: Prompt del sistema usado

        Returns:
            True si se guardó, False si no pasó el filtro
        """
        # Filtrar por confianza
        if confidence < self.min_confidence:
            logger.debug(f"[LORA_COLLECTOR] Ejemplo descartado por baja confianza: {confidence:.2f}")
            return False

        # Filtrar respuestas muy cortas o vacías
        if not response or len(response) < 10:
            logger.debug(f"[LORA_COLLECTOR] Ejemplo descartado por respuesta corta")
            return False

        # Crear ejemplo
        example = LoRATrainingExample(
            user_input=user_input,
            context=context or {},
            intent=intent,
            response=response,
            extracted_products=extracted_products or [],
            entities=entities or {},
            interaction_type=interaction_type.value if isinstance(interaction_type, InteractionType) else interaction_type,
            confidence=confidence,
            session_id=session_id,
            system_prompt=system_prompt
        )

        with self._lock:
            self._buffer.append(example)
            self.stats["total_recorded"] += 1

            # Actualizar estadísticas por intent
            if intent not in self.stats["by_intent"]:
                self.stats["by_intent"][intent] = 0
            self.stats["by_intent"][intent] += 1

            # Actualizar estadísticas por tipo
            type_key = example.interaction_type
            if type_key not in self.stats["by_type"]:
                self.stats["by_type"][type_key] = 0
            self.stats["by_type"][type_key] += 1

        logger.debug(f"[LORA_COLLECTOR] Ejemplo registrado: {intent} ({confidence:.2f})")

        # Auto-guardar si alcanzamos el intervalo
        if len(self._buffer) >= self.auto_save_interval:
            self._flush_to_disk()

        return True

    def _flush_to_disk(self):
        """Guarda buffer a disco"""
        with self._lock:
            if not self._buffer:
                return

            # Determinar archivo de salida
            timestamp = datetime.utcnow().strftime("%Y%m%d")

            # Formato JSONL (un JSON por línea - eficiente para entrenamiento)
            jsonl_file = self.storage_path / f"training_{timestamp}.jsonl"

            # Formato chat (para fine-tuning con formato de mensajes)
            chat_file = self.storage_path / f"chat_{timestamp}.jsonl"

            try:
                # Guardar formato Alpaca/Llama
                with open(jsonl_file, 'a', encoding='utf-8') as f:
                    for example in self._buffer:
                        f.write(json.dumps(example.to_training_format(), ensure_ascii=False) + '\n')

                # Guardar formato Chat
                with open(chat_file, 'a', encoding='utf-8') as f:
                    for example in self._buffer:
                        f.write(json.dumps(example.to_chat_format(), ensure_ascii=False) + '\n')

                saved_count = len(self._buffer)
                self.stats["total_saved"] += saved_count
                self._buffer.clear()

                self._save_stats()

                logger.info(f"[LORA_COLLECTOR] Guardados {saved_count} ejemplos → {jsonl_file.name}")

            except Exception as e:
                logger.error(f"[LORA_COLLECTOR] Error guardando a disco: {e}")

    def force_flush(self):
        """Fuerza guardado inmediato del buffer"""
        self._flush_to_disk()

    def get_stats(self) -> Dict:
        """Retorna estadísticas del collector"""
        return {
            **self.stats,
            "buffer_size": len(self._buffer),
            "storage_path": str(self.storage_path)
        }

    def get_training_files(self) -> List[str]:
        """Lista archivos de entrenamiento disponibles"""
        files = []
        for f in self.storage_path.glob("*.jsonl"):
            files.append(str(f))
        return sorted(files)

    def export_combined_dataset(
        self,
        output_path: str = None,
        format: str = "alpaca"  # "alpaca" o "chat"
    ) -> str:
        """
        Combina todos los archivos de entrenamiento en uno solo.

        Args:
            output_path: Ruta de salida (opcional)
            format: Formato de salida ("alpaca" o "chat")

        Returns:
            Ruta del archivo combinado
        """
        if not output_path:
            output_path = self.storage_path / f"combined_{format}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.jsonl"

        output_path = Path(output_path)

        # Determinar patrón de archivos según formato
        pattern = f"{'training' if format == 'alpaca' else 'chat'}_*.jsonl"

        examples = []
        for f in self.storage_path.glob(pattern):
            try:
                with open(f, 'r', encoding='utf-8') as file:
                    for line in file:
                        if line.strip():
                            examples.append(json.loads(line))
            except Exception as e:
                logger.warning(f"[LORA_COLLECTOR] Error leyendo {f}: {e}")

        # Guardar combinado
        with open(output_path, 'w', encoding='utf-8') as f:
            for ex in examples:
                f.write(json.dumps(ex, ensure_ascii=False) + '\n')

        logger.info(f"[LORA_COLLECTOR] Dataset combinado: {len(examples)} ejemplos → {output_path}")
        return str(output_path)


# ============================================================
# SINGLETON Y HELPERS
# ============================================================

_lora_collector: Optional[LoRATrainingCollector] = None


def get_lora_collector(
    storage_path: str = None,
    min_confidence: float = 0.8
) -> LoRATrainingCollector:
    """Obtiene instancia global del collector"""
    global _lora_collector

    if _lora_collector is None:
        path = storage_path or os.environ.get(
            'LORA_TRAINING_PATH',
            '/app/data/learning/lora_training'
        )
        _lora_collector = LoRATrainingCollector(
            storage_path=path,
            min_confidence=min_confidence
        )

    return _lora_collector


def record_cerebras_success(
    user_input: str,
    intent: str,
    response: str,
    products: List[Dict] = None,
    entities: Dict = None,
    confidence: float = 1.0,
    context: Dict = None
) -> bool:
    """
    Helper para registrar éxito de Cerebras.
    Llamar después de cada interacción exitosa.
    """
    collector = get_lora_collector()
    return collector.record_successful_interaction(
        user_input=user_input,
        intent=intent,
        response=response,
        extracted_products=products,
        entities=entities,
        confidence=confidence,
        context=context,
        interaction_type=InteractionType.FULL_TURN
    )
