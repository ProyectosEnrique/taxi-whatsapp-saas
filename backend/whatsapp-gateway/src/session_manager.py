"""
================================================================================
SESSION MANAGER - Gestión de Sesiones Multi-Tenant
================================================================================
Gestiona sesiones de clientes en memoria (o Redis en producción)
================================================================================
"""

from typing import Dict, Optional
import logging
from datetime import datetime
import json
import os

from .hybrid_session import HybridCustomerSession, SessionChannel

logger = logging.getLogger(__name__)


class SessionManager:
    """
    Gestor de sesiones de clientes.

    Mantiene sesiones activas en memoria con TTL de 30 minutos.
    En producción, usar Redis para persistencia.
    """

    def __init__(self):
        # sessions: Dict[session_key, HybridCustomerSession]
        # session_key = f"{restaurant_id}:{phone}"
        self._sessions: Dict[str, HybridCustomerSession] = {}

        # Configuración
        self.session_ttl_minutes = int(os.getenv("SESSION_TTL_MINUTES", "30"))
        self.use_redis = os.getenv("USE_REDIS", "false").lower() == "true"

        # TODO: Si use_redis, inicializar cliente Redis
        self.redis_client = None

        logger.info(f"[SessionManager] Initialized (Redis: {self.use_redis})")

    def _make_key(self, restaurant_id: str, phone: str) -> str:
        """Generar clave de sesión"""
        return f"{restaurant_id}:{phone}"

    def get_or_create_session(
        self,
        restaurant_id: str,
        phone: str,
        customer_name: str = "Cliente",
        customer_id: Optional[str] = None
    ) -> HybridCustomerSession:
        """
        Obtener sesión existente o crear nueva.

        Args:
            restaurant_id: ID del restaurante
            phone: Teléfono del cliente
            customer_name: Nombre del cliente
            customer_id: ID del cliente en DB (si existe)

        Returns:
            HybridCustomerSession
        """
        key = self._make_key(restaurant_id, phone)

        # Intentar obtener sesión existente
        session = self._get_session(key)

        if session:
            # Verificar si expiró
            if session.is_expired():
                logger.info(f"[SessionManager] Sesión expirada: {key}")
                self._delete_session(key)
                session = None
            else:
                # Refrescar TTL
                session.refresh_ttl(self.session_ttl_minutes)
                logger.info(f"[SessionManager] Sesión recuperada: {key}")

        # Crear nueva sesión si no existe
        if not session:
            session = HybridCustomerSession(
                phone=phone,
                customer_name=customer_name,
                customer_id=customer_id,
                restaurant_id=restaurant_id,
                current_channel=SessionChannel.WHATSAPP
            )
            session.refresh_ttl(self.session_ttl_minutes)
            self._save_session(key, session)
            logger.info(f"[SessionManager] Nueva sesión creada: {key}")

        return session

    def save_session(
        self,
        restaurant_id: str,
        phone: str,
        session: HybridCustomerSession
    ) -> None:
        """
        Guardar sesión actualizada.

        Args:
            restaurant_id: ID del restaurante
            phone: Teléfono del cliente
            session: Sesión actualizada
        """
        key = self._make_key(restaurant_id, phone)
        session.updated_at = datetime.utcnow()
        self._save_session(key, session)

    def delete_session(self, restaurant_id: str, phone: str) -> None:
        """
        Eliminar sesión.

        Args:
            restaurant_id: ID del restaurante
            phone: Teléfono del cliente
        """
        key = self._make_key(restaurant_id, phone)
        self._delete_session(key)
        logger.info(f"[SessionManager] Sesión eliminada: {key}")

    def cleanup_expired_sessions(self) -> int:
        """
        Limpiar sesiones expiradas.

        Returns:
            Número de sesiones eliminadas
        """
        if self.use_redis:
            # Redis maneja TTL automáticamente
            return 0

        expired_keys = []
        for key, session in self._sessions.items():
            if session.is_expired():
                expired_keys.append(key)

        for key in expired_keys:
            del self._sessions[key]

        if expired_keys:
            logger.info(f"[SessionManager] Limpiadas {len(expired_keys)} sesiones expiradas")

        return len(expired_keys)

    def get_active_sessions_count(self) -> int:
        """Obtener número de sesiones activas"""
        if self.use_redis:
            # TODO: Implementar con Redis
            return 0
        return len(self._sessions)

    def get_stats(self) -> Dict:
        """Obtener estadísticas de sesiones"""
        if self.use_redis:
            return {"message": "Redis stats not implemented"}

        total_sessions = len(self._sessions)
        total_messages = sum(s.message_count for s in self._sessions.values())
        total_cart_items = sum(len(s.cart) for s in self._sessions.values())

        return {
            "total_sessions": total_sessions,
            "total_messages": total_messages,
            "total_cart_items": total_cart_items,
            "avg_messages_per_session": total_messages / total_sessions if total_sessions > 0 else 0
        }

    # ==========================================================================
    # MÉTODOS PRIVADOS (Implementación con Memoria o Redis)
    # ==========================================================================

    def _get_session(self, key: str) -> Optional[HybridCustomerSession]:
        """Obtener sesión desde storage"""
        if self.use_redis and self.redis_client:
            # TODO: Implementar con Redis
            # data = self.redis_client.get(key)
            # if data:
            #     return HybridCustomerSession.parse_raw(data)
            return None
        else:
            return self._sessions.get(key)

    def _save_session(self, key: str, session: HybridCustomerSession) -> None:
        """Guardar sesión en storage"""
        if self.use_redis and self.redis_client:
            # TODO: Implementar con Redis
            # ttl_seconds = self.session_ttl_minutes * 60
            # self.redis_client.setex(
            #     key,
            #     ttl_seconds,
            #     session.json()
            # )
            pass
        else:
            self._sessions[key] = session

    def _delete_session(self, key: str) -> None:
        """Eliminar sesión del storage"""
        if self.use_redis and self.redis_client:
            # TODO: Implementar con Redis
            # self.redis_client.delete(key)
            pass
        else:
            if key in self._sessions:
                del self._sessions[key]


# ==============================================================================
# SINGLETON INSTANCE
# ==============================================================================

_session_manager_instance = None


def get_session_manager() -> SessionManager:
    """Obtener instancia singleton del session manager"""
    global _session_manager_instance
    if _session_manager_instance is None:
        _session_manager_instance = SessionManager()
    return _session_manager_instance
