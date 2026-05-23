# ============================================================
# FEEDBACK LOOP - Sistema de Retroalimentación y Aprendizaje
# ============================================================
# Captura interacciones para mejorar el sistema
# Identifica patrones de éxito y fallo
# Genera datos de entrenamiento automáticamente
# ============================================================

import json
import logging
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any
from collections import defaultdict

logger = logging.getLogger(__name__)


class FeedbackType(Enum):
    """Tipos de feedback"""
    # Éxitos
    INTENT_CORRECT = "intent_correct"          # Intent clasificado correctamente
    PRODUCT_FOUND = "product_found"            # Producto encontrado correctamente
    ORDER_COMPLETED = "order_completed"        # Orden completada exitosamente
    UPSELL_ACCEPTED = "upsell_accepted"        # Upsell aceptado

    # Fallos
    INTENT_INCORRECT = "intent_incorrect"      # Intent mal clasificado
    PRODUCT_NOT_FOUND = "product_not_found"    # Producto no encontrado
    ORDER_ABANDONED = "order_abandoned"        # Orden abandonada
    USER_FRUSTRATED = "user_frustrated"        # Usuario frustrado
    LLM_FALLBACK = "llm_fallback"              # Tuvo que usar LLM (regex falló)

    # Neutro
    CLARIFICATION_NEEDED = "clarification"     # Se necesitó aclaración
    SUGGESTION_GIVEN = "suggestion_given"      # Se dieron sugerencias


@dataclass
class FeedbackEntry:
    """Entrada de feedback individual"""
    feedback_type: FeedbackType
    user_input: str
    detected_intent: str
    expected_intent: Optional[str] = None
    confidence: float = 0.0
    method: str = ""  # regex, nlu, llm
    context: Dict[str, Any] = field(default_factory=dict)
    session_id: str = ""
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    # Datos adicionales para aprendizaje
    entities: Dict[str, Any] = field(default_factory=dict)
    response_given: str = ""
    user_reaction: Optional[str] = None  # positive, negative, neutral

    def to_dict(self) -> Dict:
        """Convierte a diccionario"""
        data = asdict(self)
        data['feedback_type'] = self.feedback_type.value
        return data

    @classmethod
    def from_dict(cls, data: Dict) -> 'FeedbackEntry':
        """Crea desde diccionario"""
        data['feedback_type'] = FeedbackType(data['feedback_type'])
        return cls(**data)


class FeedbackLoop:
    """
    Sistema de Feedback Loop para aprendizaje continuo.

    Funcionalidades:
    1. Captura interacciones exitosas y fallidas
    2. Identifica patrones problemáticos
    3. Genera ejemplos de entrenamiento
    4. Sugiere mejoras al NLU

    Uso:
        loop = get_feedback_loop()

        # Registrar éxito
        loop.record(FeedbackEntry(
            feedback_type=FeedbackType.INTENT_CORRECT,
            user_input="quiero una hamburguesa",
            detected_intent="add_to_order",
            confidence=0.92,
            method="nlu"
        ))

        # Obtener estadísticas
        stats = loop.get_statistics()

        # Generar ejemplos de entrenamiento
        examples = loop.generate_training_examples()
    """

    def __init__(self, storage_path: Optional[str] = None):
        self.storage_path = Path(storage_path or "/app/data/feedback")
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self._entries: List[FeedbackEntry] = []
        self._max_entries = 10000
        self._intent_stats: Dict[str, Dict] = defaultdict(lambda: {
            "correct": 0,
            "incorrect": 0,
            "total": 0,
            "avg_confidence": 0.0
        })

        # Cargar datos existentes
        self._load_existing_data()

        logger.info(f"[FEEDBACK] Inicializado con {len(self._entries)} entradas existentes")

    def _load_existing_data(self):
        """Carga datos de feedback existentes"""
        try:
            feedback_file = self.storage_path / "feedback_log.jsonl"
            if feedback_file.exists():
                with open(feedback_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        try:
                            entry = FeedbackEntry.from_dict(json.loads(line))
                            self._entries.append(entry)
                        except Exception as e:
                            logger.warning(f"Error parsing feedback entry: {e}")

                # Mantener solo las últimas N entradas
                if len(self._entries) > self._max_entries:
                    self._entries = self._entries[-self._max_entries:]

        except Exception as e:
            logger.error(f"[FEEDBACK] Error cargando datos: {e}")

    def _save_entry(self, entry: FeedbackEntry):
        """Guarda entrada de feedback a disco"""
        try:
            feedback_file = self.storage_path / "feedback_log.jsonl"
            with open(feedback_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(entry.to_dict(), ensure_ascii=False) + '\n')
        except Exception as e:
            logger.error(f"[FEEDBACK] Error guardando entrada: {e}")

    def record(self, entry: FeedbackEntry):
        """Registra una entrada de feedback"""
        self._entries.append(entry)
        self._save_entry(entry)
        self._update_stats(entry)

        logger.debug(
            f"[FEEDBACK] {entry.feedback_type.value}: "
            f"'{entry.user_input[:30]}...' → {entry.detected_intent}"
        )

        # Mantener límite de memoria
        if len(self._entries) > self._max_entries:
            self._entries = self._entries[-self._max_entries:]

    def _update_stats(self, entry: FeedbackEntry):
        """Actualiza estadísticas por intent"""
        intent = entry.detected_intent
        stats = self._intent_stats[intent]
        stats["total"] += 1

        if entry.feedback_type in [FeedbackType.INTENT_CORRECT, FeedbackType.ORDER_COMPLETED]:
            stats["correct"] += 1
        elif entry.feedback_type in [FeedbackType.INTENT_INCORRECT, FeedbackType.LLM_FALLBACK]:
            stats["incorrect"] += 1

        # Actualizar promedio de confianza
        n = stats["total"]
        stats["avg_confidence"] = (
            (stats["avg_confidence"] * (n - 1) + entry.confidence) / n
        )

    def record_success(
        self,
        user_input: str,
        intent: str,
        confidence: float,
        method: str,
        entities: Dict = None,
        session_id: str = ""
    ):
        """Método conveniente para registrar éxito"""
        self.record(FeedbackEntry(
            feedback_type=FeedbackType.INTENT_CORRECT,
            user_input=user_input,
            detected_intent=intent,
            confidence=confidence,
            method=method,
            entities=entities or {},
            session_id=session_id,
            user_reaction="positive"
        ))

    def record_failure(
        self,
        user_input: str,
        detected_intent: str,
        expected_intent: str,
        confidence: float,
        method: str,
        session_id: str = ""
    ):
        """Método conveniente para registrar fallo"""
        self.record(FeedbackEntry(
            feedback_type=FeedbackType.INTENT_INCORRECT,
            user_input=user_input,
            detected_intent=detected_intent,
            expected_intent=expected_intent,
            confidence=confidence,
            method=method,
            session_id=session_id,
            user_reaction="negative"
        ))

    def record_llm_fallback(
        self,
        user_input: str,
        original_intent: str,
        llm_response: str,
        session_id: str = ""
    ):
        """Registra cuando el sistema tuvo que usar LLM como fallback"""
        self.record(FeedbackEntry(
            feedback_type=FeedbackType.LLM_FALLBACK,
            user_input=user_input,
            detected_intent=original_intent,
            method="llm_fallback",
            response_given=llm_response,
            session_id=session_id
        ))

    def get_statistics(self) -> Dict[str, Any]:
        """Obtiene estadísticas de feedback"""
        total = len(self._entries)
        if total == 0:
            return {"total_entries": 0, "intents": {}}

        # Contar por tipo
        type_counts = defaultdict(int)
        for entry in self._entries:
            type_counts[entry.feedback_type.value] += 1

        # Calcular tasas
        correct = type_counts.get("intent_correct", 0)
        incorrect = type_counts.get("intent_incorrect", 0)
        fallbacks = type_counts.get("llm_fallback", 0)

        intent_accuracy = correct / (correct + incorrect) * 100 if (correct + incorrect) > 0 else 0
        fallback_rate = fallbacks / total * 100 if total > 0 else 0

        return {
            "total_entries": total,
            "type_distribution": dict(type_counts),
            "intent_accuracy": f"{intent_accuracy:.1f}%",
            "llm_fallback_rate": f"{fallback_rate:.1f}%",
            "intents": dict(self._intent_stats),
        }

    def get_problematic_patterns(self, min_failures: int = 3) -> List[Dict]:
        """Identifica patrones problemáticos que necesitan mejora"""
        patterns = defaultdict(lambda: {
            "examples": [],
            "failure_count": 0,
            "success_count": 0,
            "avg_confidence": 0.0
        })

        for entry in self._entries:
            # Agrupar por intent detectado
            key = entry.detected_intent
            pattern = patterns[key]

            if entry.feedback_type in [FeedbackType.INTENT_INCORRECT, FeedbackType.LLM_FALLBACK]:
                pattern["failure_count"] += 1
                pattern["examples"].append({
                    "input": entry.user_input,
                    "expected": entry.expected_intent,
                    "detected": entry.detected_intent,
                    "confidence": entry.confidence
                })
            elif entry.feedback_type == FeedbackType.INTENT_CORRECT:
                pattern["success_count"] += 1

        # Filtrar patrones con suficientes fallos
        problematic = []
        for intent, data in patterns.items():
            if data["failure_count"] >= min_failures:
                total = data["failure_count"] + data["success_count"]
                failure_rate = data["failure_count"] / total * 100 if total > 0 else 0
                problematic.append({
                    "intent": intent,
                    "failure_count": data["failure_count"],
                    "failure_rate": f"{failure_rate:.1f}%",
                    "examples": data["examples"][-5]  # Últimos 5 ejemplos
                })

        return sorted(problematic, key=lambda x: x["failure_count"], reverse=True)

    def generate_training_examples(self, intent: Optional[str] = None) -> List[Dict]:
        """
        Genera ejemplos de entrenamiento basados en interacciones exitosas.

        Returns:
            Lista de ejemplos formato {'text': str, 'intent': str}
        """
        examples = []

        for entry in self._entries:
            # Solo usar éxitos con alta confianza
            if entry.feedback_type == FeedbackType.INTENT_CORRECT and entry.confidence >= 0.85:
                if intent is None or entry.detected_intent == intent:
                    examples.append({
                        "text": entry.user_input,
                        "intent": entry.detected_intent,
                        "confidence": entry.confidence,
                        "source": "feedback_loop"
                    })

        # Eliminar duplicados
        seen = set()
        unique_examples = []
        for ex in examples:
            key = (ex["text"].lower(), ex["intent"])
            if key not in seen:
                seen.add(key)
                unique_examples.append(ex)

        return unique_examples

    def export_training_data(self, output_path: Optional[str] = None) -> str:
        """Exporta datos de entrenamiento a archivo"""
        examples = self.generate_training_examples()

        output_file = Path(output_path or self.storage_path / "training_data.json")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                "generated_at": datetime.utcnow().isoformat(),
                "total_examples": len(examples),
                "examples": examples
            }, f, ensure_ascii=False, indent=2)

        logger.info(f"[FEEDBACK] Exportados {len(examples)} ejemplos a {output_file}")
        return str(output_file)

    def get_improvement_suggestions(self) -> List[Dict]:
        """Genera sugerencias de mejora basadas en el feedback"""
        suggestions = []

        # Analizar patrones problemáticos
        problems = self.get_problematic_patterns()
        for problem in problems[:5]:  # Top 5 problemas
            suggestions.append({
                "type": "add_training_examples",
                "priority": "high" if problem["failure_count"] > 10 else "medium",
                "intent": problem["intent"],
                "description": f"Intent '{problem['intent']}' tiene {problem['failure_rate']} de fallos",
                "action": f"Agregar más ejemplos de entrenamiento para variaciones",
                "examples_needed": min(problem["failure_count"], 20)
            })

        # Analizar confianza promedio baja
        for intent, stats in self._intent_stats.items():
            if stats["avg_confidence"] < 0.7 and stats["total"] > 5:
                suggestions.append({
                    "type": "improve_patterns",
                    "priority": "medium",
                    "intent": intent,
                    "description": f"Intent '{intent}' tiene confianza promedio baja ({stats['avg_confidence']:.2f})",
                    "action": "Revisar patrones regex o agregar ejemplos NLU"
                })

        # Analizar tasa de fallback
        stats = self.get_statistics()
        if "llm_fallback_rate" in stats:
            rate = float(stats["llm_fallback_rate"].replace("%", ""))
            if rate > 15:
                suggestions.append({
                    "type": "reduce_fallback",
                    "priority": "high",
                    "description": f"Tasa de fallback a LLM alta ({rate:.1f}%)",
                    "action": "Agregar más patrones regex o ejemplos NLU para casos comunes"
                })

        return suggestions


# ============================================================
# SINGLETON Y HELPERS
# ============================================================

_feedback_loop: Optional[FeedbackLoop] = None


def get_feedback_loop() -> FeedbackLoop:
    """Obtiene instancia singleton del FeedbackLoop"""
    global _feedback_loop
    if _feedback_loop is None:
        storage_path = os.environ.get("FEEDBACK_STORAGE_PATH", "/app/data/feedback")
        _feedback_loop = FeedbackLoop(storage_path)
    return _feedback_loop


def record_feedback(entry: FeedbackEntry):
    """Helper para registrar feedback rápidamente"""
    get_feedback_loop().record(entry)


def record_successful_interaction(
    user_input: str,
    intent: str,
    confidence: float,
    method: str = "unknown",
    entities: Dict = None,
    session_id: str = ""
):
    """Helper para registrar interacción exitosa"""
    get_feedback_loop().record_success(
        user_input=user_input,
        intent=intent,
        confidence=confidence,
        method=method,
        entities=entities,
        session_id=session_id
    )


def record_failed_interaction(
    user_input: str,
    detected_intent: str,
    expected_intent: str,
    confidence: float,
    method: str = "unknown",
    session_id: str = ""
):
    """Helper para registrar interacción fallida"""
    get_feedback_loop().record_failure(
        user_input=user_input,
        detected_intent=detected_intent,
        expected_intent=expected_intent,
        confidence=confidence,
        method=method,
        session_id=session_id
    )
