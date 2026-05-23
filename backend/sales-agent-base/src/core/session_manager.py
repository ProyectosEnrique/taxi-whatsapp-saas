"""
================================================================================
VOICE RESTAURANT ASSISTANT - SESSION MANAGER
================================================================================
Gestión de sesiones de usuario/mesa para mantener contexto
================================================================================
"""

import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
import json
import logging

logger = logging.getLogger(__name__)


@dataclass
class ConversationMessage:
    """Mensaje de conversación"""
    timestamp: datetime
    role: str  # 'user' o 'assistant'
    content: str
    intent: Optional[str] = None
    entities: Optional[Dict] = None


@dataclass
class Session:
    """Sesión de usuario/mesa"""
    session_id: str
    table_id: int
    table_number: Optional[int] = None
    user_id: Optional[int] = None
    user_name: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    expires_at: datetime = field(default=None)
    conversation_history: List[ConversationMessage] = field(default_factory=list)
    current_order_draft: Dict[str, Any] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)
    is_active: bool = True

    def __post_init__(self):
        if self.expires_at is None:
            # Expira en 6 horas por defecto (tiempo máximo de una comida completa)
            # La sesión se limpiará manualmente cuando el cliente pague la cuenta
            self.expires_at = self.created_at + timedelta(hours=6)

    def is_expired(self) -> bool:
        """Verificar si la sesión ha expirado"""
        return datetime.now() > self.expires_at

    def add_message(self, role: str, content: str, intent: Optional[str] = None, entities: Optional[Dict] = None):
        """Agregar mensaje al historial"""
        message = ConversationMessage(
            timestamp=datetime.now(),
            role=role,
            content=content,
            intent=intent,
            entities=entities
        )
        self.conversation_history.append(message)
        self.last_activity = datetime.now()

    def get_recent_history(self, limit: int = 10) -> List[ConversationMessage]:
        """Obtener historial reciente"""
        return self.conversation_history[-limit:]

    def update_order_draft(self, items: List[Dict]):
        """Actualizar borrador de orden actual"""
        self.current_order_draft = {
            "items": items,
            "updated_at": datetime.now().isoformat()
        }

    def clear_order_draft(self):
        """Limpiar borrador de orden"""
        self.current_order_draft = {}

    def end_customer_session(self, archive: bool = True) -> Optional[Dict]:
        """
        Finalizar sesión del cliente (cuando paga la cuenta)

        1. Archiva la conversación para métricas y entrenamiento
        2. Limpia el historial de conversación
        3. Resetea el contexto
        4. Mantiene la sesión activa para futuros clientes en la misma mesa

        Args:
            archive: Si debe archivar la conversación antes de limpiar

        Returns:
            Dict con datos archivados si archive=True, None si no
        """
        archived_data = None

        if archive and self.conversation_history:
            try:
                from ..analytics.conversation_archive import get_conversation_archive

                archive_service = get_conversation_archive()
                archived = archive_service.archive_conversation(
                    session_id=self.session_id,
                    table_id=self.table_id,
                    table_number=self.table_number,
                    conversation_history=[
                        {
                            'timestamp': msg.timestamp.isoformat(),
                            'role': msg.role,
                            'content': msg.content,
                            'intent': msg.intent,
                            'entities': msg.entities
                        }
                        for msg in self.conversation_history
                    ],
                    order_items=self.current_order_draft.get('items', []),
                    order_total=self.context.get('order_total', 0.0),
                    customer_preferences=self.context.get('customer_preferences', {}),
                    session_start=self.created_at
                )

                archived_data = {
                    'archive_id': archived.archive_id,
                    'duration_minutes': archived.duration_minutes,
                    'order_total': archived.order_total,
                    'metrics': archived.metrics.sentiment_score if archived.metrics else 0.5
                }

                logger.info(
                    f"[SESSION] Conversación archivada: {archived.archive_id} | "
                    f"Mesa {self.table_number} | ${archived.order_total:.2f}"
                )

            except Exception as e:
                logger.error(f"[SESSION] Error archivando conversación: {e}")

        # Limpiar datos del cliente
        self.conversation_history.clear()
        self.current_order_draft = {}
        self.context = {}
        self.last_activity = datetime.now()

        logger.info(f"[SESSION] Sesión del cliente finalizada - Mesa {self.table_number}")

        return archived_data

    def set_context(self, key: str, value: Any):
        """Establecer valor de contexto"""
        self.context[key] = value

    def get_context(self, key: str, default: Any = None) -> Any:
        """Obtener valor de contexto"""
        return self.context.get(key, default)

    def to_dict(self) -> Dict:
        """Convertir a diccionario"""
        data = asdict(self)
        # Convertir datetimes a string
        data['created_at'] = self.created_at.isoformat()
        data['last_activity'] = self.last_activity.isoformat()
        data['expires_at'] = self.expires_at.isoformat()
        # Convertir mensajes
        data['conversation_history'] = [
            {
                'timestamp': msg.timestamp.isoformat(),
                'role': msg.role,
                'content': msg.content,
                'intent': msg.intent,
                'entities': msg.entities
            }
            for msg in self.conversation_history
        ]
        return data


class SessionManager:
    """
    Gestor de sesiones para el asistente de voz

    Mantiene el contexto de conversación por mesa/usuario
    """

    def __init__(self, session_expire_minutes: int = 120):
        self.sessions: Dict[str, Session] = {}
        self.session_expire_minutes = session_expire_minutes
        logger.info(f"SessionManager inicializado (expire: {session_expire_minutes} min)")

    def create_session(
        self,
        table_id: int,
        table_number: Optional[int] = None,
        user_id: Optional[int] = None,
        user_name: Optional[str] = None
    ) -> Session:
        """
        Crear nueva sesión

        Args:
            table_id: ID de la mesa
            table_number: Número de la mesa (opcional)
            user_id: ID del usuario (opcional)
            user_name: Nombre del usuario (opcional)

        Returns:
            Session creada
        """
        session_id = str(uuid.uuid4())

        expires_at = datetime.now() + timedelta(minutes=self.session_expire_minutes)

        session = Session(
            session_id=session_id,
            table_id=table_id,
            table_number=table_number,
            user_id=user_id,
            user_name=user_name,
            expires_at=expires_at
        )

        self.sessions[session_id] = session

        logger.info(
            f"Sesión creada: {session_id} "
            f"(mesa: {table_id}/{table_number}, usuario: {user_id}/{user_name})"
        )

        return session

    def get_session(self, session_id: str) -> Optional[Session]:
        """
        Obtener sesión por ID

        Args:
            session_id: ID de la sesión

        Returns:
            Session si existe y no ha expirado, None si no
        """
        session = self.sessions.get(session_id)

        if session is None:
            logger.warning(f"Sesión {session_id} no encontrada")
            return None

        if session.is_expired():
            logger.warning(f"Sesión {session_id} expirada")
            self.delete_session(session_id)
            return None

        return session

    def update_session_activity(self, session_id: str):
        """Actualizar timestamp de última actividad"""
        session = self.sessions.get(session_id)
        if session:
            session.last_activity = datetime.now()

    def delete_session(self, session_id: str) -> bool:
        """
        Eliminar sesión

        Args:
            session_id: ID de la sesión

        Returns:
            True si se eliminó, False si no existía
        """
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"Sesión {session_id} eliminada")
            return True
        return False

    def get_sessions_by_table(self, table_id: int) -> List[Session]:
        """Obtener todas las sesiones activas de una mesa"""
        return [
            session for session in self.sessions.values()
            if session.table_id == table_id and session.is_active and not session.is_expired()
        ]

    def cleanup_expired_sessions(self) -> int:
        """
        Limpiar sesiones expiradas

        Returns:
            Número de sesiones eliminadas
        """
        expired_ids = [
            session_id for session_id, session in self.sessions.items()
            if session.is_expired()
        ]

        for session_id in expired_ids:
            self.delete_session(session_id)

        if expired_ids:
            logger.info(f"Limpiadas {len(expired_ids)} sesiones expiradas")

        return len(expired_ids)

    def get_active_sessions_count(self) -> int:
        """Obtener número de sesiones activas"""
        return len([
            s for s in self.sessions.values()
            if s.is_active and not s.is_expired()
        ])

    def get_all_sessions(self) -> List[Session]:
        """Obtener todas las sesiones activas"""
        return [
            session for session in self.sessions.values()
            if session.is_active and not session.is_expired()
        ]


# Instancia global del gestor de sesiones
_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """Obtener instancia global del SessionManager (Singleton)"""
    global _session_manager
    if _session_manager is None:
        from .config import settings
        _session_manager = SessionManager(
            session_expire_minutes=settings.SESSION_EXPIRE_MINUTES
        )
    return _session_manager
