"""
Configuración centralizada del taxi-agent usando Pydantic Settings.
Lee de variables de entorno (ver docker-compose.vps.yml / .env del VPS).
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── Cascada LLM (Groq → Cerebras → Gemini → OpenRouter) ────────────────
    GROQ_API_KEY: str = ""
    CEREBRAS_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    OPENROUTER_API_KEY: str = ""

    # ── Redis (sesiones de conversación) ────────────────────────────────────
    REDIS_URL: str = ""

    # ── taxi-api ─────────────────────────────────────────────────────────
    MENU_SERVICE_URL: str = "http://taxi-api:5011"
    WHATSAPP_SECRET: str = ""
    CUSTOMER_APP_URL: str = "https://taxi.nexoai.lat/cliente"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


settings = Settings()
