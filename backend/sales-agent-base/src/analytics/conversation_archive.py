#!/usr/bin/env python3
"""
================================================================================
CONVERSATION ARCHIVE - Archivo de Conversaciones Finalizadas
================================================================================
Guarda conversaciones completas cuando el cliente paga la cuenta.

Usos:
1. Métricas del administrador (ventas, satisfacción, tiempos)
2. Datos para entrenamiento de LoRA (destilación)
3. Análisis de patrones de consumo
4. Auditoría y debugging

Estructura de archivos:
    conversation_archive/
    ├── 2024-01/
    │   ├── 2024-01-15/
    │   │   ├── session_abc123_mesa5_14-30-00.json
    │   │   └── session_def456_mesa3_15-45-00.json
    │   └── daily_summary_2024-01-15.json
    └── monthly_summary_2024-01.json
================================================================================
"""

import os
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
import hashlib

logger = logging.getLogger(__name__)


@dataclass
class ConversationMetrics:
    """Métricas extraídas de una conversación"""
    # Identificación
    session_id: str
    table_id: int
    table_number: Optional[int] = None

    # Tiempos
    start_time: str = ""
    end_time: str = ""
    duration_seconds: float = 0.0

    # Conversación
    total_turns: int = 0
    user_messages: int = 0
    assistant_messages: int = 0
    avg_response_length: float = 0.0

    # Intents detectados
    intents_detected: Dict[str, int] = field(default_factory=dict)

    # Ventas
    items_ordered: int = 0
    order_total: float = 0.0
    items_list: List[str] = field(default_factory=list)

    # Upsell/Cross-sell
    upsell_attempts: int = 0
    upsell_accepted: int = 0
    crosssell_attempts: int = 0
    crosssell_accepted: int = 0

    # Satisfacción (inferida)
    rejections: int = 0
    complaints: int = 0
    positive_responses: int = 0
    sentiment_score: float = 0.5  # 0.0 = negativo, 1.0 = positivo

    # LLM
    providers_used: Dict[str, int] = field(default_factory=dict)
    total_tokens: int = 0
    avg_latency_ms: float = 0.0
    fallback_to_template: int = 0


@dataclass
class ArchivedConversation:
    """Conversación archivada completa"""
    # Metadata
    archive_id: str
    archived_at: str

    # Sesión
    session_id: str
    table_id: int
    table_number: Optional[int] = None

    # Tiempos
    session_start: str = ""
    session_end: str = ""
    duration_minutes: float = 0.0

    # Historial completo
    conversation_history: List[Dict] = field(default_factory=list)

    # Contexto final
    final_order: List[Dict] = field(default_factory=list)
    order_total: float = 0.0

    # Preferencias detectadas
    customer_preferences: Dict[str, Any] = field(default_factory=dict)
    products_mentioned: List[str] = field(default_factory=list)

    # Métricas calculadas
    metrics: Optional[ConversationMetrics] = None

    def to_dict(self) -> Dict:
        data = asdict(self)
        if self.metrics:
            data['metrics'] = asdict(self.metrics)
        return data


class ConversationArchive:
    """
    Sistema de archivo de conversaciones finalizadas.

    Guarda conversaciones cuando el cliente paga y extrae métricas
    útiles para el administrador y para entrenamiento de LoRA.
    """

    def __init__(self, base_path: str = None, config: Dict = None):
        """
        Args:
            base_path: Directorio base para el archivo
            config: Configuración opcional
        """
        if base_path is None:
            base_path = os.environ.get(
                'CONVERSATION_ARCHIVE_PATH',
                './conversation_archive'
            )

        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

        self.config = config or {}

        # Configuración
        self.retention_days = self.config.get('retention_days', 90)
        self.compress_after_days = self.config.get('compress_after_days', 7)

        logger.info(f"[ARCHIVE] Inicializado en {self.base_path}")

    def archive_conversation(
        self,
        session_id: str,
        table_id: int,
        table_number: int = None,
        conversation_history: List[Dict] = None,
        order_items: List[Dict] = None,
        order_total: float = 0.0,
        customer_preferences: Dict = None,
        products_mentioned: List[str] = None,
        session_start: datetime = None,
        fsm_context: Any = None,
        memory_context: Any = None
    ) -> ArchivedConversation:
        """
        Archiva una conversación finalizada.

        Args:
            session_id: ID de la sesión
            table_id: ID de la mesa
            table_number: Número de la mesa
            conversation_history: Historial de mensajes
            order_items: Items del pedido final
            order_total: Total del pedido
            customer_preferences: Preferencias detectadas
            products_mentioned: Productos mencionados
            session_start: Inicio de la sesión
            fsm_context: Contexto del FSM (StateContext)
            memory_context: Contexto de memoria (ConversationMemory)

        Returns:
            ArchivedConversation con métricas calculadas
        """
        now = datetime.now()

        # Generar ID único
        archive_id = f"{session_id}_{now.strftime('%Y%m%d_%H%M%S')}"

        # Extraer datos del contexto FSM si está disponible
        if fsm_context:
            if not order_items and hasattr(fsm_context, 'order_items'):
                order_items = [
                    {
                        'product_id': item.product_id,
                        'product_name': item.product_name,
                        'quantity': item.quantity,
                        'unit_price': item.unit_price,
                        'subtotal': item.subtotal,
                        'notes': item.notes
                    }
                    for item in fsm_context.order_items
                ]
            if order_total == 0 and hasattr(fsm_context, 'order_total'):
                order_total = fsm_context.order_total

        # Extraer datos de memoria si está disponible
        if memory_context:
            if not customer_preferences and hasattr(memory_context, 'customer_preferences'):
                customer_preferences = memory_context.customer_preferences
            if not products_mentioned and hasattr(memory_context, 'mentioned_products'):
                products_mentioned = memory_context.mentioned_products
            if not conversation_history and hasattr(memory_context, 'full_history'):
                conversation_history = [
                    {
                        'role': turn.role,
                        'content': turn.content,
                        'timestamp': turn.timestamp.isoformat(),
                        'intent': turn.intent,
                        'state': turn.state,
                        'importance': turn.importance
                    }
                    for turn in memory_context.full_history
                ]
            if not session_start and hasattr(memory_context, 'session_start'):
                session_start = memory_context.session_start

        # Calcular duración
        if session_start:
            duration = (now - session_start).total_seconds() / 60
        else:
            duration = 0.0

        # Crear objeto de conversación archivada
        archived = ArchivedConversation(
            archive_id=archive_id,
            archived_at=now.isoformat(),
            session_id=session_id,
            table_id=table_id,
            table_number=table_number,
            session_start=session_start.isoformat() if session_start else "",
            session_end=now.isoformat(),
            duration_minutes=duration,
            conversation_history=conversation_history or [],
            final_order=order_items or [],
            order_total=order_total,
            customer_preferences=customer_preferences or {},
            products_mentioned=products_mentioned or []
        )

        # Calcular métricas
        archived.metrics = self._calculate_metrics(archived)

        # Guardar archivo
        self._save_archive(archived)

        # Actualizar resumen diario
        self._update_daily_summary(archived)

        logger.info(
            f"[ARCHIVE] Conversación archivada: {archive_id} | "
            f"Mesa {table_number} | {archived.metrics.total_turns} turnos | "
            f"${order_total:.2f}"
        )

        return archived

    def _calculate_metrics(self, archived: ArchivedConversation) -> ConversationMetrics:
        """Calcula métricas de la conversación"""
        history = archived.conversation_history

        metrics = ConversationMetrics(
            session_id=archived.session_id,
            table_id=archived.table_id,
            table_number=archived.table_number,
            start_time=archived.session_start,
            end_time=archived.session_end,
            duration_seconds=archived.duration_minutes * 60
        )

        if not history:
            return metrics

        # Conteos básicos
        metrics.total_turns = len(history)
        metrics.user_messages = sum(1 for m in history if m.get('role') == 'user')
        metrics.assistant_messages = sum(1 for m in history if m.get('role') == 'assistant')

        # Longitud promedio de respuestas
        assistant_lengths = [
            len(m.get('content', ''))
            for m in history
            if m.get('role') == 'assistant'
        ]
        if assistant_lengths:
            metrics.avg_response_length = sum(assistant_lengths) / len(assistant_lengths)

        # Intents detectados
        for msg in history:
            intent = msg.get('intent')
            if intent:
                metrics.intents_detected[intent] = metrics.intents_detected.get(intent, 0) + 1

        # Métricas de pedido
        metrics.items_ordered = len(archived.final_order)
        metrics.order_total = archived.order_total
        metrics.items_list = [
            f"{item.get('quantity', 1)}x {item.get('product_name', 'Producto')}"
            for item in archived.final_order
        ]

        # Upsell/Cross-sell (basado en intents)
        metrics.upsell_attempts = metrics.intents_detected.get('upsell', 0)
        metrics.crosssell_attempts = metrics.intents_detected.get('crosssell', 0)

        # Aceptaciones (aproximadas por accept_suggestion después de upsell/crosssell)
        accepts = metrics.intents_detected.get('accept_suggestion', 0)
        rejects = metrics.intents_detected.get('reject_suggestion', 0)

        if metrics.upsell_attempts + metrics.crosssell_attempts > 0:
            # Distribuir aceptaciones proporcionalmente
            total_offers = metrics.upsell_attempts + metrics.crosssell_attempts
            if total_offers > 0 and accepts > 0:
                metrics.upsell_accepted = int(accepts * metrics.upsell_attempts / total_offers)
                metrics.crosssell_accepted = accepts - metrics.upsell_accepted

        # Rechazos y quejas
        metrics.rejections = rejects
        metrics.complaints = metrics.intents_detected.get('complaint', 0)

        # Respuestas positivas
        positive_intents = ['accept_suggestion', 'confirm_order', 'greeting']
        metrics.positive_responses = sum(
            metrics.intents_detected.get(intent, 0)
            for intent in positive_intents
        )

        # Sentiment score
        total_interactions = metrics.positive_responses + metrics.rejections + metrics.complaints
        if total_interactions > 0:
            negative = metrics.rejections + (metrics.complaints * 2)  # Quejas pesan más
            metrics.sentiment_score = max(0.0, min(1.0,
                1.0 - (negative / (total_interactions + negative))
            ))

        return metrics

    def _get_archive_path(self, date: datetime = None) -> Path:
        """Obtiene el path para archivar por fecha"""
        if date is None:
            date = datetime.now()

        month_dir = self.base_path / date.strftime('%Y-%m')
        day_dir = month_dir / date.strftime('%Y-%m-%d')
        day_dir.mkdir(parents=True, exist_ok=True)

        return day_dir

    def _save_archive(self, archived: ArchivedConversation):
        """Guarda el archivo de conversación"""
        archive_dir = self._get_archive_path()

        # Nombre del archivo
        table_str = f"mesa{archived.table_number}" if archived.table_number else f"table{archived.table_id}"
        time_str = datetime.now().strftime('%H-%M-%S')
        filename = f"session_{archived.session_id[:8]}_{table_str}_{time_str}.json"

        filepath = archive_dir / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(archived.to_dict(), f, ensure_ascii=False, indent=2)

        logger.debug(f"[ARCHIVE] Guardado: {filepath}")

    def _update_daily_summary(self, archived: ArchivedConversation):
        """Actualiza el resumen diario con la nueva conversación"""
        archive_dir = self._get_archive_path()
        summary_file = archive_dir / "daily_summary.json"

        # Cargar resumen existente o crear nuevo
        if summary_file.exists():
            with open(summary_file, 'r', encoding='utf-8') as f:
                summary = json.load(f)
        else:
            summary = {
                "date": datetime.now().strftime('%Y-%m-%d'),
                "total_conversations": 0,
                "total_revenue": 0.0,
                "total_items_sold": 0,
                "avg_order_value": 0.0,
                "avg_conversation_duration": 0.0,
                "avg_sentiment": 0.0,
                "upsell_success_rate": 0.0,
                "crosssell_success_rate": 0.0,
                "intents_summary": {},
                "top_products": {},
                "tables_served": [],
                "hourly_distribution": {str(h): 0 for h in range(24)},
                "conversations": []
            }

        # Actualizar métricas
        metrics = archived.metrics
        n = summary["total_conversations"]

        summary["total_conversations"] += 1
        summary["total_revenue"] += archived.order_total
        summary["total_items_sold"] += metrics.items_ordered

        # Promedios actualizados incrementalmente
        new_n = n + 1
        summary["avg_order_value"] = (
            (summary["avg_order_value"] * n + archived.order_total) / new_n
        )
        summary["avg_conversation_duration"] = (
            (summary["avg_conversation_duration"] * n + archived.duration_minutes) / new_n
        )
        summary["avg_sentiment"] = (
            (summary["avg_sentiment"] * n + metrics.sentiment_score) / new_n
        )

        # Tasas de éxito
        total_upsell = sum(1 for c in summary.get("conversations", [])
                          if c.get("upsell_attempts", 0) > 0)
        total_crosssell = sum(1 for c in summary.get("conversations", [])
                              if c.get("crosssell_attempts", 0) > 0)

        if metrics.upsell_attempts > 0:
            accepted_upsells = sum(c.get("upsell_accepted", 0) for c in summary.get("conversations", []))
            attempted_upsells = sum(c.get("upsell_attempts", 0) for c in summary.get("conversations", []))
            if attempted_upsells > 0:
                summary["upsell_success_rate"] = (
                    (accepted_upsells + metrics.upsell_accepted) /
                    (attempted_upsells + metrics.upsell_attempts)
                )

        # Intents
        for intent, count in metrics.intents_detected.items():
            summary["intents_summary"][intent] = summary["intents_summary"].get(intent, 0) + count

        # Productos
        for item in archived.final_order:
            product_name = item.get('product_name', 'Desconocido')
            summary["top_products"][product_name] = summary["top_products"].get(product_name, 0) + 1

        # Mesas
        if archived.table_number and archived.table_number not in summary["tables_served"]:
            summary["tables_served"].append(archived.table_number)

        # Distribución horaria
        hour = datetime.now().hour
        summary["hourly_distribution"][str(hour)] = summary["hourly_distribution"].get(str(hour), 0) + 1

        # Agregar referencia a la conversación
        summary["conversations"].append({
            "archive_id": archived.archive_id,
            "session_id": archived.session_id,
            "table": archived.table_number,
            "order_total": archived.order_total,
            "duration_minutes": archived.duration_minutes,
            "sentiment": metrics.sentiment_score,
            "upsell_attempts": metrics.upsell_attempts,
            "upsell_accepted": metrics.upsell_accepted,
            "crosssell_attempts": metrics.crosssell_attempts,
            "crosssell_accepted": metrics.crosssell_accepted,
            "time": datetime.now().strftime('%H:%M')
        })

        # Guardar
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)

    def get_daily_summary(self, date: datetime = None) -> Dict:
        """Obtiene el resumen del día"""
        archive_dir = self._get_archive_path(date)
        summary_file = archive_dir / "daily_summary.json"

        if summary_file.exists():
            with open(summary_file, 'r', encoding='utf-8') as f:
                return json.load(f)

        return {"error": "No hay datos para esta fecha"}

    def get_conversation(self, archive_id: str) -> Optional[Dict]:
        """Obtiene una conversación archivada por ID"""
        # Buscar en los últimos 30 días
        for days_ago in range(30):
            date = datetime.now() - timedelta(days=days_ago)
            archive_dir = self._get_archive_path(date)

            for filepath in archive_dir.glob(f"*{archive_id[:8]}*.json"):
                if filepath.name != "daily_summary.json":
                    with open(filepath, 'r', encoding='utf-8') as f:
                        return json.load(f)

        return None

    def get_metrics_for_admin(self, days: int = 7) -> Dict:
        """
        Obtiene métricas agregadas para el dashboard del administrador.

        Args:
            days: Número de días a analizar

        Returns:
            Dict con métricas agregadas
        """
        metrics = {
            "period": f"Últimos {days} días",
            "generated_at": datetime.now().isoformat(),

            # Totales
            "total_conversations": 0,
            "total_revenue": 0.0,
            "total_items_sold": 0,

            # Promedios
            "avg_order_value": 0.0,
            "avg_conversation_duration": 0.0,
            "avg_sentiment": 0.0,

            # Tasas
            "upsell_success_rate": 0.0,
            "crosssell_success_rate": 0.0,

            # Distribuciones
            "daily_revenue": {},
            "hourly_distribution": {str(h): 0 for h in range(24)},
            "top_products": {},
            "intents_summary": {},

            # Por día
            "daily_summaries": []
        }

        upsell_attempts_total = 0
        upsell_accepted_total = 0
        crosssell_attempts_total = 0
        crosssell_accepted_total = 0

        for days_ago in range(days):
            date = datetime.now() - timedelta(days=days_ago)
            summary = self.get_daily_summary(date)

            if "error" not in summary:
                date_str = date.strftime('%Y-%m-%d')

                metrics["total_conversations"] += summary.get("total_conversations", 0)
                metrics["total_revenue"] += summary.get("total_revenue", 0)
                metrics["total_items_sold"] += summary.get("total_items_sold", 0)

                metrics["daily_revenue"][date_str] = summary.get("total_revenue", 0)

                # Acumular distribución horaria
                for hour, count in summary.get("hourly_distribution", {}).items():
                    metrics["hourly_distribution"][hour] = metrics["hourly_distribution"].get(hour, 0) + count

                # Acumular productos
                for product, count in summary.get("top_products", {}).items():
                    metrics["top_products"][product] = metrics["top_products"].get(product, 0) + count

                # Acumular intents
                for intent, count in summary.get("intents_summary", {}).items():
                    metrics["intents_summary"][intent] = metrics["intents_summary"].get(intent, 0) + count

                # Upsell/crosssell
                for conv in summary.get("conversations", []):
                    upsell_attempts_total += conv.get("upsell_attempts", 0)
                    upsell_accepted_total += conv.get("upsell_accepted", 0)
                    crosssell_attempts_total += conv.get("crosssell_attempts", 0)
                    crosssell_accepted_total += conv.get("crosssell_accepted", 0)

                metrics["daily_summaries"].append({
                    "date": date_str,
                    "conversations": summary.get("total_conversations", 0),
                    "revenue": summary.get("total_revenue", 0),
                    "avg_sentiment": summary.get("avg_sentiment", 0)
                })

        # Calcular promedios
        if metrics["total_conversations"] > 0:
            metrics["avg_order_value"] = metrics["total_revenue"] / metrics["total_conversations"]

        if upsell_attempts_total > 0:
            metrics["upsell_success_rate"] = upsell_accepted_total / upsell_attempts_total

        if crosssell_attempts_total > 0:
            metrics["crosssell_success_rate"] = crosssell_accepted_total / crosssell_attempts_total

        # Ordenar top productos
        metrics["top_products"] = dict(
            sorted(metrics["top_products"].items(), key=lambda x: -x[1])[:10]
        )

        return metrics

    def cleanup_old_archives(self, days: int = None) -> int:
        """Limpia archivos más antiguos que retention_days"""
        days = days or self.retention_days
        cutoff = datetime.now() - timedelta(days=days)
        deleted = 0

        for month_dir in self.base_path.iterdir():
            if not month_dir.is_dir():
                continue

            for day_dir in month_dir.iterdir():
                if not day_dir.is_dir():
                    continue

                try:
                    dir_date = datetime.strptime(day_dir.name, '%Y-%m-%d')
                    if dir_date < cutoff:
                        import shutil
                        shutil.rmtree(str(day_dir))
                        deleted += 1
                        logger.info(f"[ARCHIVE] Eliminado directorio antiguo: {day_dir}")
                except ValueError:
                    continue

        return deleted


# Singleton global
_archive_instance: Optional[ConversationArchive] = None


def get_conversation_archive(config: Dict = None) -> ConversationArchive:
    """Obtiene instancia global del archivo de conversaciones"""
    global _archive_instance
    if _archive_instance is None:
        _archive_instance = ConversationArchive(config=config)
    return _archive_instance
