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
    # SECURITY
    # ==============================================================================

    SECRET_KEY: str = "your-secret-key-here-change-in-production-use-env-var"
    # En producción, usar: openssl rand -hex 32

    # ==============================================================================
    # CONFIG FROM ENV FILE
    # ==============================================================================

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Crear instancia global de settings
settings = Settings()
