# ============================================================
# FEEDBACK STORAGE - Almacenamiento de Feedback
# ============================================================
# Almacenamiento persistente de entradas de feedback
# Usa archivos JSON para simplicidad e independencia
# ============================================================

import os
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from threading import Lock
import uuid

from .models import FeedbackEntry, FeedbackRating, ErrorType, FeedbackStats

logger = logging.getLogger(__name__)


class FeedbackStorage:
    """
    Almacenamiento de feedback en archivos JSON.

    Estructura:
    - feedback/
      - entries/
        - 2025-11-28.json  (entradas por día)
        - 2025-11-29.json
      - reviewed/
        - reviewed_2025-11-28.json
      - stats/
        - daily_stats.json
        - weekly_stats.json
    """

    def __init__(self, base_path: str = None):
        """
        Inicializa el almacenamiento.

        Args:
            base_path: Ruta base para almacenar archivos
        """
        if base_path is None:
            base_path = os.environ.get('FEEDBACK_STORAGE_PATH', './feedback_data')

        self.base_path = Path(base_path)
        self.entries_path = self.base_path / 'entries'
        self.reviewed_path = self.base_path / 'reviewed'
        self.stats_path = self.base_path / 'stats'

        # Crear directorios si no existen
        self.entries_path.mkdir(parents=True, exist_ok=True)
        self.reviewed_path.mkdir(parents=True, exist_ok=True)
        self.stats_path.mkdir(parents=True, exist_ok=True)

        # Lock para escritura thread-safe
        self._write_lock = Lock()

        logger.info(f"[FEEDBACK_STORAGE] Inicializado en {self.base_path}")

    def _get_daily_file(self, date: datetime = None) -> Path:
        """Obtiene el archivo de entradas para una fecha"""
        if date is None:
            date = datetime.now()
        filename = f"{date.strftime('%Y-%m-%d')}.json"
        return self.entries_path / filename

    def _load_daily_entries(self, date: datetime = None) -> List[Dict]:
        """Carga entradas de un día"""
        filepath = self._get_daily_file(date)
        if filepath.exists():
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"[FEEDBACK_STORAGE] Error cargando {filepath}: {e}")
        return []

    def _save_daily_entries(self, entries: List[Dict], date: datetime = None):
        """Guarda entradas de un día"""
        filepath = self._get_daily_file(date)
        with self._write_lock:
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(entries, f, ensure_ascii=False, indent=2)
            except Exception as e:
                logger.error(f"[FEEDBACK_STORAGE] Error guardando {filepath}: {e}")

    def save(self, entry: FeedbackEntry) -> str:
        """
        Guarda una entrada de feedback.

        Args:
            entry: Entrada de feedback a guardar

        Returns:
            ID de la entrada guardada
        """
        # Generar ID si no tiene
        if not entry.id:
            entry.id = str(uuid.uuid4())[:8]

        # Cargar entradas existentes del día
        entries = self._load_daily_entries(entry.timestamp)

        # Agregar nueva entrada
        entries.append(entry.to_dict())

        # Guardar
        self._save_daily_entries(entries, entry.timestamp)

        logger.info(f"[FEEDBACK_STORAGE] Entrada guardada: {entry.id}")
        return entry.id

    def get(self, entry_id: str) -> Optional[FeedbackEntry]:
        """
        Obtiene una entrada por ID.

        Args:
            entry_id: ID de la entrada

        Returns:
            FeedbackEntry o None si no existe
        """
        # Buscar en archivos recientes (últimos 30 días)
        for i in range(30):
            date = datetime.now() - timedelta(days=i)
            entries = self._load_daily_entries(date)

            for entry_dict in entries:
                if entry_dict.get('id') == entry_id:
                    return FeedbackEntry.from_dict(entry_dict)

        return None

    def update(self, entry: FeedbackEntry) -> bool:
        """
        Actualiza una entrada existente.

        Args:
            entry: Entrada con datos actualizados

        Returns:
            True si se actualizó, False si no se encontró
        """
        # Buscar en archivos recientes
        for i in range(30):
            date = datetime.now() - timedelta(days=i)
            entries = self._load_daily_entries(date)

            for idx, entry_dict in enumerate(entries):
                if entry_dict.get('id') == entry.id:
                    entries[idx] = entry.to_dict()
                    self._save_daily_entries(entries, date)
                    logger.info(f"[FEEDBACK_STORAGE] Entrada actualizada: {entry.id}")
                    return True

        return False

    def get_by_session(self, session_id: str, days: int = 7) -> List[FeedbackEntry]:
        """
        Obtiene todas las entradas de una sesión.

        Args:
            session_id: ID de la sesión
            days: Número de días hacia atrás a buscar

        Returns:
            Lista de entradas de esa sesión
        """
        results = []

        for i in range(days):
            date = datetime.now() - timedelta(days=i)
            entries = self._load_daily_entries(date)

            for entry_dict in entries:
                if entry_dict.get('session_id') == session_id:
                    results.append(FeedbackEntry.from_dict(entry_dict))

        return sorted(results, key=lambda x: x.timestamp)

    def get_pending(self, limit: int = 100) -> List[FeedbackEntry]:
        """
        Obtiene entradas pendientes de revisar.

        Args:
            limit: Máximo de entradas a devolver

        Returns:
            Lista de entradas pendientes
        """
        results = []

        for i in range(30):
            if len(results) >= limit:
                break

            date = datetime.now() - timedelta(days=i)
            entries = self._load_daily_entries(date)

            for entry_dict in entries:
                if entry_dict.get('rating') == FeedbackRating.PENDING.value:
                    results.append(FeedbackEntry.from_dict(entry_dict))
                    if len(results) >= limit:
                        break

        return results

    def get_by_rating(
        self,
        rating: FeedbackRating,
        days: int = 7,
        limit: int = 100
    ) -> List[FeedbackEntry]:
        """
        Obtiene entradas por calificación.

        Args:
            rating: Calificación a buscar
            days: Días hacia atrás
            limit: Máximo de resultados

        Returns:
            Lista de entradas
        """
        results = []

        for i in range(days):
            if len(results) >= limit:
                break

            date = datetime.now() - timedelta(days=i)
            entries = self._load_daily_entries(date)

            for entry_dict in entries:
                if entry_dict.get('rating') == rating.value:
                    results.append(FeedbackEntry.from_dict(entry_dict))
                    if len(results) >= limit:
                        break

        return results

    def get_by_error_type(
        self,
        error_type: ErrorType,
        days: int = 7,
        limit: int = 100
    ) -> List[FeedbackEntry]:
        """
        Obtiene entradas por tipo de error.

        Args:
            error_type: Tipo de error a buscar
            days: Días hacia atrás
            limit: Máximo de resultados

        Returns:
            Lista de entradas
        """
        results = []

        for i in range(days):
            if len(results) >= limit:
                break

            date = datetime.now() - timedelta(days=i)
            entries = self._load_daily_entries(date)

            for entry_dict in entries:
                if error_type.value in entry_dict.get('error_types', []):
                    results.append(FeedbackEntry.from_dict(entry_dict))
                    if len(results) >= limit:
                        break

        return results

    def get_all(self, days: int = 7) -> List[FeedbackEntry]:
        """
        Obtiene todas las entradas de los últimos N días.

        Args:
            days: Días hacia atrás

        Returns:
            Lista de entradas
        """
        results = []

        for i in range(days):
            date = datetime.now() - timedelta(days=i)
            entries = self._load_daily_entries(date)

            for entry_dict in entries:
                results.append(FeedbackEntry.from_dict(entry_dict))

        return sorted(results, key=lambda x: x.timestamp, reverse=True)

    def calculate_stats(self, days: int = 7) -> FeedbackStats:
        """
        Calcula estadísticas de feedback.

        Args:
            days: Días a incluir en el cálculo

        Returns:
            FeedbackStats con las estadísticas
        """
        stats = FeedbackStats()
        entries = self.get_all(days)

        stats.total_entries = len(entries)

        # Conteo por rating
        for entry in entries:
            if entry.rating == FeedbackRating.CORRECT:
                stats.correct_count += 1
            elif entry.rating == FeedbackRating.PARTIAL:
                stats.partial_count += 1
            elif entry.rating == FeedbackRating.INCORRECT:
                stats.incorrect_count += 1
            else:
                stats.pending_count += 1

        # Conteo por tipo de error
        error_counts = {}
        for entry in entries:
            for error in entry.error_types:
                error_counts[error.value] = error_counts.get(error.value, 0) + 1
        stats.error_counts = error_counts

        # Precisión por intención
        intent_correct = {}
        intent_total = {}
        for entry in entries:
            intent = entry.detected_intent
            if intent:
                intent_total[intent] = intent_total.get(intent, 0) + 1
                if entry.rating == FeedbackRating.CORRECT:
                    intent_correct[intent] = intent_correct.get(intent, 0) + 1

        stats.intent_accuracy = {
            intent: (intent_correct.get(intent, 0) / total) * 100
            for intent, total in intent_total.items()
            if total > 0
        }

        # Precisión por estado
        state_correct = {}
        state_total = {}
        for entry in entries:
            if entry.context_snapshot:
                state = entry.context_snapshot.state
                state_total[state] = state_total.get(state, 0) + 1
                if entry.rating == FeedbackRating.CORRECT:
                    state_correct[state] = state_correct.get(state, 0) + 1

        stats.state_accuracy = {
            state: (state_correct.get(state, 0) / total) * 100
            for state, total in state_total.items()
            if total > 0
        }

        # Tasa de aceptación
        accepted = sum(1 for e in entries if e.user_accepted is True)
        total_with_result = sum(1 for e in entries if e.user_accepted is not None)
        stats.acceptance_rate = accepted / total_with_result if total_with_result > 0 else 0.0

        # Tasa de conversión
        converted = sum(1 for e in entries if e.conversion_result is True)
        total_with_conversion = sum(1 for e in entries if e.conversion_result is not None)
        stats.conversion_rate = converted / total_with_conversion if total_with_conversion > 0 else 0.0

        return stats

    def export_for_training(self, output_path: str, days: int = 30) -> int:
        """
        Exporta datos para entrenamiento/análisis.

        Args:
            output_path: Ruta del archivo de salida
            days: Días de datos a exportar

        Returns:
            Número de entradas exportadas
        """
        entries = self.get_all(days)

        # Filtrar solo las revisadas (no pending)
        reviewed = [e for e in entries if e.rating != FeedbackRating.PENDING]

        # Convertir a formato de entrenamiento
        training_data = []
        for entry in reviewed:
            training_data.append({
                'input': entry.user_input,
                'detected_intent': entry.detected_intent,
                'context_state': entry.context_snapshot.state if entry.context_snapshot else None,
                'context_category': entry.context_snapshot.active_category if entry.context_snapshot else None,
                'system_response': entry.system_response,
                'expected_response': entry.expected_response,
                'rating': entry.rating.value,
                'error_types': [e.value for e in entry.error_types],
                'user_accepted': entry.user_accepted
            })

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(training_data, f, ensure_ascii=False, indent=2)

        logger.info(f"[FEEDBACK_STORAGE] Exportados {len(training_data)} entradas a {output_path}")
        return len(training_data)


# Instancia global
_feedback_storage: Optional[FeedbackStorage] = None


def get_feedback_storage(base_path: str = None) -> FeedbackStorage:
    """Obtiene instancia global del storage (Singleton)"""
    global _feedback_storage
    if _feedback_storage is None:
        _feedback_storage = FeedbackStorage(base_path)
    return _feedback_storage
