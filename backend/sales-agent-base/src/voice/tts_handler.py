"""
================================================================================
VOICE RESTAURANT ASSISTANT - TTS HANDLER v5.0 with Cartesia Sonic
================================================================================
Text-to-Speech ultra-rapido con multiples proveedores:

Proveedores (en orden de prioridad):
1. Cartesia Sonic 3 (~90ms) - RECOMENDADO, ultra-rapido
2. Piper TTS (~200-500ms) - Fallback local gratuito
3. gTTS (~500-2000ms) - Fallback de emergencia

Caracteristicas:
- Prosodia natural con pausas y enfasis
- Normalizacion de precios a texto hablado
- Cascade automatico entre proveedores
- Metricas de latencia por proveedor
================================================================================
"""

from pathlib import Path
import logging
import wave
import io
import re
import time
import httpx
from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ProsodyMode(Enum):
    """Modos de prosodia para el TTS"""
    NORMAL = "normal"           # Sin modificaciones
    FRIENDLY = "friendly"       # Más pausas, tono amigable
    EXCITED = "excited"         # Para ofertas y recomendaciones
    EMPATHETIC = "empathetic"   # Para quejas o problemas


@dataclass
class ProsodyConfig:
    """Configuración de prosodia para respuestas"""
    pause_after_greeting: str = "300ms"      # Pausa después de saludo
    pause_after_product: str = "200ms"       # Pausa después de nombre de producto
    pause_before_price: str = "150ms"        # Pausa antes de precio
    pause_after_sentence: str = "400ms"      # Pausa después de oración
    emphasis_products: bool = True           # Enfatizar nombres de productos
    emphasis_prices: bool = True             # Enfatizar precios


def add_prosody_markers(text: str, mode: ProsodyMode = ProsodyMode.FRIENDLY) -> str:
    """
    Agrega marcadores de prosodia al texto para que suene más natural.

    Los marcadores son procesados por el TTS para:
    - Agregar pausas naturales
    - Enfatizar palabras clave
    - Hacer el habla más expresiva

    Args:
        text: Texto original
        mode: Modo de prosodia

    Returns:
        Texto con marcadores de prosodia
    """
    if mode == ProsodyMode.NORMAL:
        return text

    # Copiar texto para modificar
    result = text

    # Pausas después de puntuación (usando ... como marcador universal)
    # Esto funciona con Piper y la mayoría de TTS

    # Pausa larga después de punto (fin de oración)
    result = re.sub(r'\.(\s+|$)', '... ', result)

    # Pausa media después de coma
    result = re.sub(r',(\s+)', ', ', result)  # Ya tiene pausa natural

    # Pausa después de signos de interrogación/exclamación
    result = re.sub(r'([!?])(\s+|$)', r'\1.. ', result)

    # Pausa después de dos puntos (antes de lista)
    result = re.sub(r':(\s+)', ':.. ', result)

    # En modo empático, agregar pausas más largas
    if mode == ProsodyMode.EMPATHETIC:
        result = result.replace('...', '.... ')

    # En modo excited, menos pausas
    elif mode == ProsodyMode.EXCITED:
        result = result.replace('...', '.. ')

    # Limpiar espacios múltiples
    result = re.sub(r'\s+', ' ', result).strip()

    return result


def normalize_price_for_speech(text: str) -> str:
    """
    Convierte precios con formato "$XXX.XX" a texto legible para TTS.
    
    Ejemplos:
        "$195.00" -> "ciento noventa y cinco pesos"
        "$45.50" -> "cuarenta y cinco pesos con cincuenta centavos"
    """

    def number_to_words(n: int) -> str:
        """Convierte numero entero a palabras en espanol"""
        if n == 0:
            return "cero"

        units = ["", "uno", "dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho", "nueve"]
        teens = ["diez", "once", "doce", "trece", "catorce", "quince", "dieciseis", "diecisiete", "dieciocho", "diecinueve"]
        tens = ["", "", "veinte", "treinta", "cuarenta", "cincuenta", "sesenta", "setenta", "ochenta", "noventa"]
        hundreds = ["", "ciento", "doscientos", "trescientos", "cuatrocientos", "quinientos", "seiscientos", "setecientos", "ochocientos", "novecientos"]

        if n < 10:
            return units[n]
        elif n < 20:
            return teens[n - 10]
        elif n < 100:
            if n % 10 == 0:
                return tens[n // 10]
            elif n < 30:
                return f"veinti{units[n % 10]}"
            else:
                return f"{tens[n // 10]} y {units[n % 10]}"
        elif n == 100:
            return "cien"
        elif n < 1000:
            remainder = n % 100
            if remainder == 0:
                return hundreds[n // 100]
            else:
                return f"{hundreds[n // 100]} {number_to_words(remainder)}"
        elif n < 2000:
            remainder = n % 1000
            if remainder == 0:
                return "mil"
            else:
                return f"mil {number_to_words(remainder)}"
        elif n < 1000000:
            thousands = n // 1000
            remainder = n % 1000
            if remainder == 0:
                return f"{number_to_words(thousands)} mil"
            else:
                return f"{number_to_words(thousands)} mil {number_to_words(remainder)}"
        else:
            return str(n)

    def replace_price(match) -> str:
        """Reemplaza un precio con su version en palabras"""
        price_str = match.group(0)
        clean = price_str.replace("$", "").replace(",", "")

        try:
            price = float(clean)
            pesos = int(price)
            centavos = int(round((price - pesos) * 100))

            result = number_to_words(pesos) + " pesos"

            if centavos > 0:
                result += f" con {number_to_words(centavos)} centavos"

            return result
        except ValueError:
            return price_str

    # Patron para precios: $XXX.XX o $X,XXX.XX
    price_pattern = r'\$[\d,]+\.?\d*'

    return re.sub(price_pattern, replace_price, text)


class TTSProvider(Enum):
    """Proveedores de TTS disponibles"""
    CARTESIA = "cartesia"    # Ultra-rapido (~90ms)
    PIPER = "piper"          # Local gratuito (~200-500ms)
    GTTS = "gtts"            # Fallback de emergencia
    ELEVENLABS = "elevenlabs"  # Premium (opcional)


class TTSHandler:
    """
    Handler para Text-to-Speech con multiples proveedores y prosodia avanzada.

    Features v5.0:
    - Cartesia Sonic 3 como proveedor principal (~90ms)
    - Cascade automatico: Cartesia -> Piper -> gTTS
    - Prosodia natural con pausas y enfasis
    - Normalizacion de precios a texto hablado
    - Metricas de latencia por proveedor
    - Modos: FRIENDLY, EXCITED, EMPATHETIC
    """

    def __init__(
        self,
        piper_url: str = "http://piper-api:5555",
        lang: str = "es",
        default_prosody: ProsodyMode = ProsodyMode.FRIENDLY,
        preferred_provider: str = "cartesia"
    ):
        self.piper_url = piper_url
        self.lang = lang
        self.default_prosody = default_prosody
        self.prosody_config = ProsodyConfig()
        self.preferred_provider = preferred_provider

        # Metricas de latencia
        self._latency_stats = {
            "cartesia": {"count": 0, "total_ms": 0, "avg_ms": 0},
            "piper": {"count": 0, "total_ms": 0, "avg_ms": 0},
            "gtts": {"count": 0, "total_ms": 0, "avg_ms": 0},
        }

        # Inicializar Cartesia si esta disponible
        self._cartesia_handler = None
        self._init_cartesia()

        provider_info = "Cartesia" if self._cartesia_handler else "Piper (fallback)"
        logger.info(f"[TTS] v5.0 inicializado - Provider: {provider_info}, Prosody: {default_prosody.value}")

    def _init_cartesia(self):
        """Inicializa el handler de Cartesia si esta configurado"""
        try:
            from .cartesia_tts import get_cartesia_handler
            handler = get_cartesia_handler()
            if handler.is_available:
                self._cartesia_handler = handler
                logger.info("[TTS] Cartesia Sonic disponible como proveedor principal")
            else:
                logger.warning("[TTS] Cartesia no disponible, usando Piper como fallback")
        except ImportError as e:
            logger.warning(f"[TTS] Cartesia no importable: {e}")
        except Exception as e:
            logger.warning(f"[TTS] Error inicializando Cartesia: {e}")

    def _record_latency(self, provider: str, latency_ms: float):
        """Registra la latencia de un proveedor"""
        stats = self._latency_stats.get(provider)
        if stats:
            stats["count"] += 1
            stats["total_ms"] += latency_ms
            stats["avg_ms"] = stats["total_ms"] / stats["count"]

    def get_latency_stats(self) -> dict:
        """Retorna estadisticas de latencia por proveedor"""
        return self._latency_stats.copy()

    async def synthesize_to_file(
        self,
        text: str,
        output_path: Path,
        prosody_mode: ProsodyMode = None
    ) -> bool:
        """
        Sintetizar texto a archivo de audio con prosodia natural.

        Flujo de proveedores (cascade):
        1. Cartesia Sonic (~90ms) - Si esta disponible
        2. Piper TTS (~200-500ms) - Fallback local
        3. gTTS (~500-2000ms) - Fallback de emergencia

        Args:
            text: Texto a sintetizar
            output_path: Ruta del archivo de salida
            prosody_mode: Modo de prosodia (usa default si None)

        Returns:
            True si la sintesis fue exitosa
        """
        mode = prosody_mode or self.default_prosody

        # 1. Normalizar precios
        processed_text = normalize_price_for_speech(text)

        # 2. Agregar prosodia (pausas naturales)
        processed_text = add_prosody_markers(processed_text, mode)

        if processed_text != text:
            logger.debug(f"[TTS] Texto procesado: '{processed_text[:100]}...'")

        # 3. Intentar con Cartesia (ultra-rapido)
        if self._cartesia_handler and self.preferred_provider == "cartesia":
            start_time = time.time()
            cartesia_success = await self._synthesize_cartesia(processed_text, output_path)
            latency_ms = (time.time() - start_time) * 1000

            if cartesia_success:
                self._record_latency("cartesia", latency_ms)
                logger.info(f"[TTS] Audio generado con Cartesia ({latency_ms:.0f}ms, mode={mode.value})")
                return True
            else:
                logger.warning("[TTS] Cartesia fallo, intentando Piper...")

        # 4. Fallback a Piper TTS
        start_time = time.time()
        piper_success = await self._synthesize_piper(processed_text, output_path)
        latency_ms = (time.time() - start_time) * 1000

        if piper_success:
            self._record_latency("piper", latency_ms)
            logger.info(f"[TTS] Audio generado con Piper ({latency_ms:.0f}ms, mode={mode.value})")
            return True

        # 5. Fallback de emergencia a gTTS
        logger.warning("[TTS] Piper no disponible, usando gTTS fallback")
        start_time = time.time()
        gtts_success = self._synthesize_gtts(processed_text, output_path)
        latency_ms = (time.time() - start_time) * 1000

        if gtts_success:
            self._record_latency("gtts", latency_ms)
            logger.info(f"[TTS] Audio generado con gTTS ({latency_ms:.0f}ms)")

        return gtts_success

    async def _synthesize_cartesia(self, text: str, output_path: Path) -> bool:
        """Sintetizar usando Cartesia Sonic (ultra-rapido)"""
        if not self._cartesia_handler:
            return False

        try:
            return await self._cartesia_handler.synthesize_to_file(text, output_path)
        except Exception as e:
            logger.error(f"[TTS] Error en Cartesia: {e}")
            return False

    def set_prosody_mode(self, mode: ProsodyMode):
        """Cambia el modo de prosodia predeterminado"""
        self.default_prosody = mode
        logger.info(f"[TTS] Prosody mode cambiado a: {mode.value}")

    async def _synthesize_piper(self, text: str, output_path: Path) -> bool:
        """Sintetizar usando Piper TTS via API REST"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.piper_url}/api/tts",
                    json={"text": text}
                )

                if response.status_code == 200:
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(output_path, 'wb') as f:
                        f.write(response.content)
                    logger.info(f"Audio Piper generado: {output_path} ({len(response.content)} bytes)")
                    return True
                else:
                    logger.error(f"Piper API error: {response.status_code} - {response.text}")
                    return False

        except httpx.ConnectError as e:
            logger.error(f"No se pudo conectar a Piper API en {self.piper_url}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error inesperado en Piper API: {e}", exc_info=True)
            return False

    def _synthesize_gtts(self, text: str, output_path: Path) -> bool:
        """Sintetizar usando gTTS (fallback de emergencia)"""
        try:
            from gtts import gTTS
            tts = gTTS(text=text, lang=self.lang, tld="es")
            tts.save(str(output_path))
            logger.info(f"Audio gTTS generado (fallback): {output_path}")
            return True
        except Exception as e:
            logger.error(f"Error en gTTS fallback: {e}")
            return False

    def synthesize_to_file_sync(self, text: str, output_path: Path) -> bool:
        """Version sincrona para compatibilidad"""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(self.synthesize_to_file(text, output_path))


# Instancia global
_tts_handler = None


def get_tts_handler():
    """Obtener instancia global del TTSHandler (Singleton)"""
    global _tts_handler
    if _tts_handler is None:
        from ..core.config import settings

        piper_url = getattr(settings, 'PIPER_TTS_URL', "http://piper-api:5555")
        lang = getattr(settings, 'ASSISTANT_VOICE_LANG', 'es')
        preferred_provider = getattr(settings, 'TTS_PROVIDER', 'cartesia')

        _tts_handler = TTSHandler(
            piper_url=piper_url,
            lang=lang,
            preferred_provider=preferred_provider
        )
    return _tts_handler


def get_tts_status() -> dict:
    """Obtiene el estado del sistema TTS"""
    handler = get_tts_handler()
    return {
        "preferred_provider": handler.preferred_provider,
        "cartesia_available": handler._cartesia_handler is not None,
        "latency_stats": handler.get_latency_stats(),
        "prosody_mode": handler.default_prosody.value,
    }
