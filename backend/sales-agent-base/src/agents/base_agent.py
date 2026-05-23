"""
================================================================================
BASE AGENT - Clase Base para Agentes
================================================================================
Clase abstracta que define la interfaz comun para todos los agentes.
Proporciona servicios compartidos: STT, TTS, LLM.
================================================================================
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)


# ==============================================================================
# DATA CLASSES
# ==============================================================================

@dataclass
class AgentConfig:
    """Configuracion de un agente"""
    name: str
    description: str
    language: str = "es"
    voice_enabled: bool = True
    tts_voice_id: str = "default"
    max_history: int = 10
    timeout_seconds: int = 30
    require_confirmation: bool = True  # Para acciones criticas
    extra: Dict = field(default_factory=dict)


@dataclass
class AgentResponse:
    """Respuesta de un agente"""
    text: str
    intent: str
    confidence: float = 1.0
    action_executed: Optional[str] = None
    action_result: Optional[Dict] = None
    requires_confirmation: bool = False
    confirmation_message: Optional[str] = None
    audio_url: Optional[str] = None
    visual_data: Optional[Dict] = None
    metadata: Dict = field(default_factory=dict)


class AgentState(Enum):
    """Estados posibles de un agente"""
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    EXECUTING = "executing"
    WAITING_CONFIRMATION = "waiting_confirmation"
    ERROR = "error"


# ==============================================================================
# BASE AGENT CLASS
# ==============================================================================

class BaseAgent(ABC):
    """
    Clase base abstracta para todos los agentes del sistema.

    Proporciona:
    - Acceso a servicios compartidos (STT, TTS, LLM)
    - Manejo de sesiones y contexto
    - Historial de conversacion
    - Logging y metricas
    """

    def __init__(self, config: AgentConfig):
        """
        Inicializar agente base.

        Args:
            config: Configuracion del agente
        """
        self.config = config
        self.state = AgentState.IDLE

        # Servicios compartidos (se inicializan lazy)
        self._stt_handler = None
        self._tts_handler = None
        self._llm_service = None

        # Sesiones activas
        self.sessions: Dict[str, Dict] = {}

        # Metricas
        self.metrics = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "actions_executed": 0,
            "avg_response_time_ms": 0
        }

        logger.info(f"[{self.config.name}] Agente inicializado")

    # ==========================================================================
    # SERVICIOS COMPARTIDOS (Lazy Loading)
    # ==========================================================================

    @property
    def stt_handler(self):
        """Obtener handler de Speech-to-Text"""
        if self._stt_handler is None:
            from ..voice.stt_handler import get_stt_handler
            self._stt_handler = get_stt_handler()
        return self._stt_handler

    @property
    def tts_handler(self):
        """Obtener handler de Text-to-Speech"""
        if self._tts_handler is None:
            from ..voice.tts_handler import get_tts_handler
            self._tts_handler = get_tts_handler()
        return self._tts_handler

    @property
    def llm_service(self):
        """Obtener servicio de LLM"""
        if self._llm_service is None:
            from ..nlp.llm_service import get_llm_service
            self._llm_service = get_llm_service()
        return self._llm_service

    # ==========================================================================
    # METODOS ABSTRACTOS (Implementar en subclases)
    # ==========================================================================

    @abstractmethod
    def get_system_prompt(self) -> str:
        """Obtener el system prompt especifico del agente"""
        pass

    @abstractmethod
    def get_available_tools(self) -> List[Dict]:
        """Obtener lista de herramientas/funciones disponibles"""
        pass

    @abstractmethod
    async def process_message(
        self,
        session_id: str,
        message: str,
        context: Optional[Dict] = None
    ) -> AgentResponse:
        """
        Procesar un mensaje del usuario.

        Args:
            session_id: ID de la sesion
            message: Mensaje del usuario
            context: Contexto adicional

        Returns:
            AgentResponse con la respuesta
        """
        pass

    @abstractmethod
    async def execute_tool(
        self,
        tool_name: str,
        parameters: Dict
    ) -> Dict:
        """
        Ejecutar una herramienta/funcion.

        Args:
            tool_name: Nombre de la herramienta
            parameters: Parametros de la herramienta

        Returns:
            Resultado de la ejecucion
        """
        pass

    # ==========================================================================
    # METODOS COMUNES
    # ==========================================================================

    def get_or_create_session(self, session_id: str) -> Dict:
        """Obtener o crear una sesion"""
        if session_id not in self.sessions:
            self.sessions[session_id] = {
                "id": session_id,
                "created_at": datetime.now().isoformat(),
                "history": [],
                "context": {},
                "pending_confirmation": None,
                "state": AgentState.IDLE.value
            }
            logger.info(f"[{self.config.name}] Nueva sesion creada: {session_id}")
        return self.sessions[session_id]

    def add_to_history(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict] = None
    ):
        """Agregar mensaje al historial de la sesion"""
        session = self.get_or_create_session(session_id)

        entry = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
        if metadata:
            entry["metadata"] = metadata

        session["history"].append(entry)

        # Limitar historial
        if len(session["history"]) > self.config.max_history:
            session["history"] = session["history"][-self.config.max_history:]

    def get_conversation_history(
        self,
        session_id: str,
        limit: int = None
    ) -> List[Dict]:
        """Obtener historial de conversacion"""
        session = self.get_or_create_session(session_id)
        history = session.get("history", [])

        if limit:
            return history[-limit:]
        return history

    def clear_session(self, session_id: str):
        """Limpiar una sesion"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"[{self.config.name}] Sesion eliminada: {session_id}")

    def set_pending_confirmation(
        self,
        session_id: str,
        action: str,
        params: Dict,
        message: str
    ):
        """Establecer una accion pendiente de confirmacion"""
        session = self.get_or_create_session(session_id)
        session["pending_confirmation"] = {
            "action": action,
            "params": params,
            "message": message,
            "created_at": datetime.now().isoformat()
        }
        session["state"] = AgentState.WAITING_CONFIRMATION.value

    def get_pending_confirmation(self, session_id: str) -> Optional[Dict]:
        """Obtener accion pendiente de confirmacion"""
        session = self.get_or_create_session(session_id)
        return session.get("pending_confirmation")

    def clear_pending_confirmation(self, session_id: str):
        """Limpiar accion pendiente"""
        session = self.get_or_create_session(session_id)
        session["pending_confirmation"] = None
        session["state"] = AgentState.IDLE.value

    # ==========================================================================
    # AUDIO PROCESSING
    # ==========================================================================

    async def process_audio(
        self,
        session_id: str,
        audio_data: bytes,
        context: Optional[Dict] = None
    ) -> AgentResponse:
        """
        Procesar audio del usuario (STT -> Process -> TTS).

        Args:
            session_id: ID de la sesion
            audio_data: Datos de audio en bytes
            context: Contexto adicional

        Returns:
            AgentResponse con texto y audio de respuesta
        """
        self.state = AgentState.LISTENING

        try:
            # 1. Speech-to-Text
            transcription = await self.stt_handler.transcribe(audio_data)

            if not transcription or not transcription.get("text"):
                return AgentResponse(
                    text="No pude entender lo que dijiste. ¿Puedes repetirlo?",
                    intent="stt_error",
                    confidence=0.0
                )

            user_text = transcription["text"]
            logger.info(f"[{self.config.name}] STT: {user_text}")

            # 2. Procesar mensaje
            self.state = AgentState.PROCESSING
            response = await self.process_message(session_id, user_text, context)

            # 3. Text-to-Speech (si esta habilitado)
            if self.config.voice_enabled and response.text:
                self.state = AgentState.PROCESSING
                audio_result = await self.tts_handler.synthesize(
                    response.text,
                    voice_id=self.config.tts_voice_id
                )
                response.audio_url = audio_result.get("audio_url")

            self.state = AgentState.IDLE
            return response

        except Exception as e:
            logger.error(f"[{self.config.name}] Error procesando audio: {e}")
            self.state = AgentState.ERROR
            return AgentResponse(
                text="Hubo un error al procesar tu solicitud.",
                intent="error",
                confidence=0.0,
                metadata={"error": str(e)}
            )

    # ==========================================================================
    # METRICAS
    # ==========================================================================

    def record_request(self, success: bool, response_time_ms: float):
        """Registrar una solicitud para metricas"""
        self.metrics["total_requests"] += 1

        if success:
            self.metrics["successful_requests"] += 1
        else:
            self.metrics["failed_requests"] += 1

        # Actualizar promedio de tiempo de respuesta
        total = self.metrics["total_requests"]
        current_avg = self.metrics["avg_response_time_ms"]
        self.metrics["avg_response_time_ms"] = (
            (current_avg * (total - 1) + response_time_ms) / total
        )

    def get_metrics(self) -> Dict:
        """Obtener metricas del agente"""
        return {
            "agent_name": self.config.name,
            "state": self.state.value,
            "active_sessions": len(self.sessions),
            **self.metrics
        }

    # ==========================================================================
    # UTILIDADES
    # ==========================================================================

    def format_tools_for_llm(self) -> str:
        """Formatear herramientas disponibles para el prompt del LLM"""
        tools = self.get_available_tools()

        if not tools:
            return "No hay herramientas disponibles."

        lines = ["HERRAMIENTAS DISPONIBLES:"]
        for tool in tools:
            name = tool.get("name", "unknown")
            desc = tool.get("description", "Sin descripcion")
            params = tool.get("parameters", {})

            lines.append(f"\n- {name}: {desc}")
            if params:
                lines.append(f"  Parametros: {params}")

        return "\n".join(lines)

    def __repr__(self):
        return f"<{self.__class__.__name__}(name={self.config.name}, state={self.state.value})>"
