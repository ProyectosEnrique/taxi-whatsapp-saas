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

    MERCADOPAGO_ACCESS_TOKEN: str = ""     # token de la plataforma (uso general, no por conductor)
    MERCADOPAGO_CLIENT_ID: str = ""        # credenciales de la aplicación MercadoPago (modo Marketplace)
    MERCADOPAGO_CLIENT_SECRET: str = ""    # una sola app para toda la plataforma, no por conductor
    PUBLIC_URL: str = "https://taxi.nexoai.lat"
    BUSINESS_NAME: str = "Taxi App"
    WHATSAPP_GATEWAY_URL: str = "http://taxi-whatsapp:8000"
    WHATSAPP_SECRET: str = ""           # clave compartida entre taxi-api y taxi-whatsapp
    WHATSAPP_NUMBER: str = ""           # número de flota, e.g. "+15551234567"
    EMERGENCY_PHONE: str = "911"        # número al que llama el botón de pánico

    # ==============================================================================
    # GEOCODING
    # ==============================================================================

    GOOGLE_MAPS_API_KEY: str = ""        # Google Maps Geocoding API key (primario)
    CITY_LAT: float = 0.0               # latitud del centro de la ciudad operativa
    CITY_LNG: float = 0.0               # longitud del centro
    CITY_BBOX_DEG: float = 0.3          # radio del bounding box en grados (~33 km, fallback Nominatim)

    # ==============================================================================
    # TWILIO SMS (recuperación de contraseña)
    # ==============================================================================

    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_SMS_FROM: str = ""           # número Twilio SMS-capable, e.g. "+16204077336"

    # ==============================================================================
    # TELEGRAM
    # ==============================================================================

    TELEGRAM_BOT_TOKEN: str = ""        # token del bot (@BotFather)
    TELEGRAM_ALERT_CHAT_ID: str = ""    # chat_id del grupo/canal del operador
    TELEGRAM_WEBHOOK_SECRET: str = ""   # secret para validar webhooks de Telegram
    TELEGRAM_BOT_USERNAME: str = "TaxiNexoaiBot"   # para los enlaces t.me/<bot>?start=… de los choferes

    # Despacho por cercanía (telegram_bot.notify_drivers_new_ride): el viaje se
    # avisa primero a los choferes dentro del 1er círculo; si nadie acepta en
    # DISPATCH_RING_WAIT_S segundos, al siguiente; al final, a todos los online.
    DISPATCH_RINGS_KM: str = "2,4"      # vacío = avisar a todos de una vez (como antes)
    DISPATCH_RING_WAIT_S: int = 60
    LOCATION_FRESH_MIN: int = 5         # ubicación más vieja que esto no cuenta como "cerca"...
    LOCATION_LIVE_FRESH_MIN: int = 60   # ...salvo con ubicación en vivo activa (estacionado casi no actualiza)
    # Avisos por cercanía durante el viaje (ubicación en vivo de Telegram):
    # "Llegué" se marca solo cerca del pasajero y, cerca del destino, se le
    # ofrece al chofer el botón de completar. 0 = desactivado.
    AUTO_ARRIVE_RADIUS_M: int = 120
    # Aviso "tu conductor está llegando" al pasajero, sin que el chofer toque nada. Un poco más
    # que los ~100 m pedidos: Telegram manda la ubicación cada tantos segundos. 0 = apagado.
    ARRIVING_NOTICE_RADIUS_M: int = 150
    NEAR_DEST_RADIUS_M: int = 200
    AUTO_START_RADIUS_M: int = 200      # ya llegó y se aleja esto del origen → viaje iniciado solo
    # Regalo de FarmaCerca en el primer viaje (ver services/farmacerca_gift.py). Vacío = apagado.
    FARMACERCA_GIFT_URL: str = "https://farmacia.nexoai.lat/r/taxi"
    FARMACERCA_GIFT_AMOUNT: int = 5
    # Número público de TaxiCerca para los QR de la tarjetita y la calcomanía (routers/taxi_qr.py)
    TAXICERCA_WA_NUMBER: str = "+13162412111"
    # Viajes programados apagados para el arranque (2026-11-09): solo viajes al momento.
    # La API rechaza scheduled_at (no lo convierte en inmediato: mandaría un taxi ya).
    SCHEDULED_RIDES_ENABLED: bool = False
    # Pedir desde la web (taxi.nexoai.lat/login → /home) apagado para el arranque (2026-11-10):
    # solo WhatsApp, donde el número es real. Seguimiento, SOS y /pedir siguen igual.
    WEB_RIDES_ENABLED: bool = False
    # SOS (ver services/sos.py): si nadie toca "Ya lo atiendo" en este tiempo, se avisa al respaldo
    SOS_ESCALATE_MIN: int = 2
    PROXIMITY_MIN_AGE_S: int = 60       # no antes de esto tras aceptar/iniciar (evita falsos al arrancar)

    # ==============================================================================
    # REDIS (ride_notifs.py — comparte estado entre workers si se escala > 1)
    # ==============================================================================

    REDIS_URL: str = ""

    # ==============================================================================
    # ADMIN
    # ==============================================================================
    ADMIN_PASSWORD: str = "admin1234"   # cambiar en .env del VPS

    # ==============================================================================
    # CONFIG FROM ENV FILE
    # ==============================================================================

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Crear instancia global de settings
settings = Settings()
