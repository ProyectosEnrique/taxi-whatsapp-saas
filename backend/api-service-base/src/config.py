"""
================================================================================
CONFIGURATION - Menu Service
================================================================================
Configuración centralizada usando Pydantic Settings
================================================================================
"""

from typing import List
from pydantic_settings import BaseSettings
from pydantic import field_validator


class Settings(BaseSettings):
    """Configuración de la aplicación"""

    # ==============================================================================
    # SERVICE INFO
    # ==============================================================================

    SERVICE_NAME: str = "menu_service"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"

    # ==============================================================================
    # DATABASE
    # ==============================================================================

    DATABASE_URL: str
    POSTGRES_POOL_SIZE: int = 20
    POSTGRES_MAX_OVERFLOW: int = 10

    # ==============================================================================
    # LOGGING
    # ==============================================================================

    LOG_LEVEL: str = "INFO"

    # ==============================================================================
    # CORS
    # ==============================================================================

    CORS_ORIGINS: List[str] = [
        "http://localhost:8080",
        "http://localhost:8081",
        "http://localhost:8082",
        "http://localhost:8083",
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    # ==============================================================================
    # API SETTINGS
    # ==============================================================================

    API_V1_PREFIX: str = "/api/v1"

    # ==============================================================================
    # MERCADOPAGO
    # ==============================================================================

    MERCADOPAGO_ACCESS_TOKEN: str = ""
    PUBLIC_URL: str = "https://taxi.nexoai.lat"
    BUSINESS_NAME: str = "Taxi App"
    WHATSAPP_GATEWAY_URL: str = "http://taxi-whatsapp:8000"
    WHATSAPP_SECRET: str = ""           # clave compartida entre taxi-api y taxi-whatsapp
    WHATSAPP_NUMBER: str = ""           # número de flota, e.g. "+15551234567"
    EMERGENCY_PHONE: str = "911"        # número al que llama el botón de pánico

    # ==============================================================================
    # TELEGRAM
    # ==============================================================================

    TELEGRAM_BOT_TOKEN: str = ""        # token del bot (@BotFather)
    TELEGRAM_ALERT_CHAT_ID: str = ""    # chat_id del grupo/canal del operador

    # ==============================================================================
    # CONFIG FROM ENV FILE
    # ==============================================================================

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Crear instancia global de settings
settings = Settings()
