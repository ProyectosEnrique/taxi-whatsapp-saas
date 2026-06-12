"""
================================================================================
VOICE RESTAURANT ASSISTANT - CONFIGURATION
================================================================================
Gestión centralizada de configuración
================================================================================
"""

import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Configuración de la aplicación"""

    # ========================================
    # PROJECT PATHS
    # ========================================
    PROJECT_ROOT: Path = Path(__file__).parent.parent.parent
    LOGS_DIR: Path = PROJECT_ROOT / "logs"
    TEMP_DIR: Path = PROJECT_ROOT / "temp"
    QR_CODES_DIR: Path = PROJECT_ROOT / "qr_codes"

    # ========================================
    # VOICE ASSISTANT APIs
    # ========================================
    DEEPGRAM_API_KEY: str = Field(..., description="Deepgram API key for STT")
    GROQ_API_KEY: str = Field(..., description="Groq API key for NLP")

    # ElevenLabs TTS (v2.0)
    ELEVENLABS_API_KEY: Optional[str] = Field(default=None, description="ElevenLabs API key for ultra-natural TTS")
    ELEVENLABS_VOICE_ID: str = Field(default="21m00Tcm4TlvDq8ikWAM", description="Voice ID (Rachel by default)")
    ELEVENLABS_MODEL: str = Field(default="eleven_multilingual_v2", description="ElevenLabs model")
    ELEVENLABS_STABILITY: float = Field(default=0.5, description="Voice stability (0.0-1.0)")
    ELEVENLABS_SIMILARITY_BOOST: float = Field(default=0.75, description="Similarity boost (0.0-1.0)")

    # ========================================
    # RESTAURANT API
    # ========================================
    RESTAURANT_API_BASE_URL: str = Field(
        default="http://localhost",
        description="Base URL for restaurant services"
    )
    MENU_SERVICE_URL: str = Field(
        default="http://localhost:5011/api/v1",
        description="Menu service URL"
    )
    ORDERS_SERVICE_URL: str = Field(
        default="http://localhost:5012/api/v1",
        description="Orders service URL"
    )
    TABLES_SERVICE_URL: str = Field(
        default="http://localhost:5013/api/v1",
        description="Tables service URL"
    )
    AUTH_SERVICE_URL: str = Field(
        default="http://localhost:5014/api/v1",
        description="Auth service URL"
    )

    # ========================================
    # SESSION CONFIGURATION
    # ========================================
    SESSION_SECRET_KEY: str = Field(
        default="change-this-secret-key-in-production",
        description="Secret key for JWT sessions"
    )
    SESSION_EXPIRE_MINUTES: int = Field(
        default=120,
        description="Session expiration time in minutes"
    )

    # ========================================
    # FLASK CONFIGURATION
    # ========================================
    FLASK_ENV: str = Field(default="development")
    FLASK_DEBUG: bool = Field(default=True)
    FLASK_PORT: int = Field(default=5020)
    FLASK_HOST: str = Field(default="0.0.0.0")

    # ========================================
    # CLOUDFLARE TUNNEL
    # ========================================
    USE_CLOUDFLARE_TUNNEL: bool = Field(default=True)
    QR_BASE_URL: str = Field(
        default="http://localhost:5020",
        description="Base URL for QR codes"
    )

    # ========================================
    # LOGGING
    # ========================================
    LOG_LEVEL: str = Field(default="INFO")
    LOG_FILE: str = Field(default="logs/voice_restaurant.log")

    # ========================================
    # NLP CONFIGURATION
    # ========================================
    GROQ_MODEL: str = Field(default="mixtral-8x7b-32768")
    ASSISTANT_LANGUAGE: str = Field(default="es")
    ASSISTANT_VOICE_LANG: str = Field(default="es")
    ASSISTANT_VOICE_TLD: str = Field(default="es")

    # ========================================
    # LLM PROVIDER CONFIGURATION
    # ========================================
    # Opciones: "cerebras", "groq", "gemini", "openai", "lora", "hybrid", "cascade"
    LLM_PROVIDER: str = Field(
        default="cascade",
        description="LLM provider: cerebras, groq, gemini, openai, lora, hybrid, or cascade"
    )

    # --- Cerebras (Llama 3.3 70B) - GRATIS, ULTRA-RAPIDO (NUEVO) ---
    CEREBRAS_API_KEY: Optional[str] = Field(
        default=None,
        description="Cerebras API key for Llama 3.3 70B (free tier)"
    )
    CEREBRAS_MODEL: str = Field(
        default="llama3.3-70b",
        description="Cerebras model: llama3.3-70b, llama3.1-70b, llama3.1-8b"
    )

    # --- Google Gemini (1.5 Pro) - PREMIUM (NUEVO - reemplaza GPT-4o) ---
    GOOGLE_API_KEY: Optional[str] = Field(
        default=None,
        description="Google API key for Gemini (free tier: 1500 req/day)"
    )
    GEMINI_MODEL: str = Field(
        default="gemini-1.5-pro",
        description="Gemini model: gemini-1.5-pro, gemini-1.5-flash, gemini-2.0-flash-exp"
    )

    # --- OpenAI (GPT-4o) - LEGACY (opcional, solo como fallback) ---
    OPENAI_API_KEY: Optional[str] = Field(
        default=None,
        description="OpenAI API key for GPT-4o (legacy, prefer Gemini)"
    )
    OPENAI_MODEL: str = Field(
        default="gpt-4o",
        description="OpenAI model: gpt-4o, gpt-4o-mini, gpt-4-turbo"
    )

    # --- LoRA (Local) ---
    # Ruta al modelo LoRA entrenado (requerido si LLM_PROVIDER=lora, hybrid, o cascade)
    # Soporta TinyLlama 1.1B o Mistral 7B fine-tuned
    LORA_MODEL_PATH: Optional[str] = Field(
        default=None,
        description="Path to LoRA model directory (TinyLlama or Mistral)"
    )
    # Dispositivo para LoRA: "auto", "cuda", "cpu"
    LORA_DEVICE: str = Field(
        default="auto",
        description="Device for LoRA model: auto, cuda, or cpu"
    )

    # --- Cascade (Híbrido inteligente) ---
    # Flujo: Cerebras → Gemini → Ollama → LoRA
    # Intenciones que siempre usan Gemini (premium)
    CASCADE_PREMIUM_INTENTS: str = Field(
        default="handle_objection,complex_recommendation,negotiate,complaint,special_request",
        description="Comma-separated intents that always use Gemini (premium)"
    )

    # ========================================
    # MODO OFFLINE - Ollama & Whisper
    # ========================================
    # Modo offline: "auto" (detecta internet), "always" (siempre offline), "never" (siempre online)
    OFFLINE_MODE: str = Field(
        default="auto",
        description="Offline mode: auto, always, or never"
    )

    # --- Ollama (LLM Local Server) ---
    OLLAMA_URL: str = Field(
        default="http://ollama:11434",
        description="Ollama server URL"
    )
    OLLAMA_MODEL: str = Field(
        default="mistral:7b-instruct",
        description="Ollama model: mistral:7b-instruct, llama2:7b, etc."
    )

    # --- Whisper (STT Local) ---
    WHISPER_URL: str = Field(
        default="http://whisper:9000",
        description="Whisper ASR server URL"
    )
    WHISPER_MODEL: str = Field(
        default="small",
        description="Whisper model: tiny, base, small, medium, large"
    )

    # --- Piper TTS (Local - Fallback) ---
    PIPER_TTS_URL: str = Field(
        default="http://piper-tts:10200",
        description="Piper TTS Wyoming server URL"
    )

    # ========================================
    # CARTESIA SONIC TTS (Ultra-rapido ~90ms)
    # ========================================
    # Cartesia Sonic 3 - TTS de ultima generacion
    # Latencia: ~90ms (vs 200-1000ms de Piper)
    # Costo: $0.015/1K caracteres (~$1.50 por 1000 respuestas)
    # Documentacion: https://docs.cartesia.ai/
    CARTESIA_API_KEY: Optional[str] = Field(
        default=None,
        description="Cartesia API key for Sonic TTS"
    )
    CARTESIA_VOICE_ID: str = Field(
        default="846d6cb0-2301-48b6-9683-48f5618ea2f6",  # Spanish-speaking Lady
        description="Cartesia voice ID (default: Spanish conversational female)"
    )
    CARTESIA_MODEL: str = Field(
        default="sonic-3",
        description="Cartesia model: sonic-3 (latest)"
    )
    # Voces en espanol disponibles:
    # - a67e0421-22e0-4d5b-b586-bd4a64aee41d: Spanish Narrator Man
    # - 2deb3edf-b9d8-4d06-8db9-5742fb8a3cb2: Spanish Narrator Lady
    # - 846fa30b-6e1a-49b9-b7df-6be47092a09a: Spanish Storyteller Man
    # - 846d6cb0-2301-48b6-9683-48f5618ea2f6: Spanish-speaking Lady (default)
    # - 34dbb662-8e98-413c-a1ef-1a3407675fe7: Spanish-speaking Man
    # - 2695b6b5-5543-4be1-96d9-3967fb5e7fec: Spanish Reporter Man
    # - db832ebd-3cb6-42e7-9d47-912b425adbaa: Young Spanish-speaking Woman

    # ========================================
    # TTS PROVIDER CONFIGURATION
    # ========================================
    # Opciones: "cartesia" (recomendado), "piper", "gtts", "elevenlabs"
    TTS_PROVIDER: str = Field(
        default="cartesia",
        description="TTS provider: cartesia (fastest), piper (free), gtts (fallback), elevenlabs (premium)"
    )

    # ========================================
    # LLM-FIRST MODE CONFIGURATION
    # ========================================
    # Control de cómo se generan las respuestas en el sistema
    # Fase 1 (Mes 1): "always" - TODO usa LLM (entrenamiento)
    # Fase 2 (Mes 2): "hybrid" - FSM para casos comunes, LLM para complejos
    # Fase 3 (Mes 3+): "fallback" - FSM primero, LLM solo si falla

    LLM_FIRST_MODE: str = Field(
        default="always",
        description="LLM-first mode: always (training), hybrid (balanced), fallback (production)"
    )
    # always = Todas las respuestas con LLM, registra TODO
    # hybrid = FSM para intents comunes (>85% confianza), LLM para complejos
    # fallback = FSM primero, LLM solo si FSM no tiene respuesta

    USE_FSM_TEMPLATES: bool = Field(
        default=False,
        description="Use FSM templates for responses (False = always use LLM for responses)"
    )

    RECORD_ALL_CONVERSATIONS: bool = Field(
        default=True,
        description="Record all conversations for training data collection"
    )

    FSM_CONFIDENCE_THRESHOLD: float = Field(
        default=0.85,
        description="Minimum confidence to use FSM templates in hybrid mode (0.0-1.0)"
    )

    # Intenciones que SIEMPRE usan LLM (incluso en modo hybrid/fallback)
    # Estas son intenciones complejas que requieren razonamiento flexible
    ALWAYS_LLM_INTENTS: str = Field(
        default="complex_recommendation,handle_objection,negotiate,complaint,special_request",
        description="Comma-separated intents that always use LLM regardless of mode"
    )

    # Intenciones que pueden usar FSM en modo hybrid
    # Estas son intenciones simples con respuestas predecibles
    FSM_ELIGIBLE_INTENTS: str = Field(
        default="greeting,view_menu,view_category,add_to_order,confirm_order,goodbye",
        description="Comma-separated intents eligible for FSM templates in hybrid mode"
    )

    # ========================================
    # AUDIO CONFIGURATION
    # ========================================
    MAX_AUDIO_SIZE_MB: int = Field(default=16)
    ALLOWED_AUDIO_FORMATS: str = Field(default="webm,wav,mp3,ogg,m4a")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"  # Ignorar variables extra en .env

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Crear directorios necesarios
        self.LOGS_DIR.mkdir(exist_ok=True, parents=True)
        self.TEMP_DIR.mkdir(exist_ok=True, parents=True)
        self.QR_CODES_DIR.mkdir(exist_ok=True, parents=True)

    @property
    def allowed_audio_extensions(self) -> set:
        """Retorna set de extensiones permitidas"""
        return set(self.ALLOWED_AUDIO_FORMATS.split(','))

    @property
    def always_llm_intents(self) -> set:
        """Retorna set de intenciones que siempre usan LLM"""
        return set(self.ALWAYS_LLM_INTENTS.split(','))

    @property
    def fsm_eligible_intents(self) -> set:
        """Retorna set de intenciones que pueden usar FSM templates"""
        return set(self.FSM_ELIGIBLE_INTENTS.split(','))

    def should_use_llm(self, intent: str, confidence: float = 1.0) -> bool:
        """
        Determina si debe usar LLM para generar respuesta.

        Args:
            intent: Intención clasificada
            confidence: Confianza de la clasificación (0.0-1.0)

        Returns:
            True si debe usar LLM, False si puede usar FSM
        """
        # Modo always: siempre LLM
        if self.LLM_FIRST_MODE == "always":
            return True

        # Intenciones que siempre usan LLM
        if intent in self.always_llm_intents:
            return True

        # Modo fallback: FSM primero
        if self.LLM_FIRST_MODE == "fallback":
            return False

        # Modo hybrid: depende del intent y confianza
        if self.LLM_FIRST_MODE == "hybrid":
            # Si es intent elegible para FSM y confianza alta, usar FSM
            if intent in self.fsm_eligible_intents and confidence >= self.FSM_CONFIDENCE_THRESHOLD:
                return False
            # Caso contrario, usar LLM
            return True

        # Default: usar LLM
        return True


# Instancia global de configuración
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """
    Obtener configuración global (Singleton)
    """
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


# Para uso directo
settings = get_settings()
