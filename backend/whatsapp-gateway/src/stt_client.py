"""
================================================================================
STT CLIENT - Speech-to-Text para WhatsApp Gateway
================================================================================
Cliente para transcribir notas de voz de WhatsApp usando Deepgram
================================================================================
"""

import logging
import os
import aiohttp
from typing import Optional

logger = logging.getLogger(__name__)


class STTClient:
    """
    Cliente para Speech-to-Text usando Deepgram.

    Transcribe notas de voz de WhatsApp a texto.
    """

    def __init__(self):
        self.api_key = os.getenv("DEEPGRAM_API_KEY", "")
        self.api_url = "https://api.deepgram.com/v1/listen"
        self.is_available = bool(self.api_key)

        if self.is_available:
            logger.info("[STT] Deepgram inicializado correctamente")
        else:
            logger.warning("[STT] Deepgram API key no configurada - Notas de voz no funcionarán")

    async def transcribe_audio_url(self, audio_url: str, auth: tuple = None) -> Optional[str]:
        """
        Transcribir audio desde una URL (usado para notas de voz de Twilio).

        Args:
            audio_url: URL del audio (ej: URL de Twilio MediaUrl)
            auth: Tupla (username, password) para autenticación básica (para Twilio)

        Returns:
            Texto transcrito o None si falla
        """
        if not self.is_available:
            logger.error("[STT] Deepgram no está configurado")
            return None

        try:
            # Descargar audio primero
            audio_bytes = await self._download_audio(audio_url, auth)
            if not audio_bytes:
                logger.error(f"[STT] No se pudo descargar audio de {audio_url}")
                return None

            # Transcribir
            return await self.transcribe_bytes(audio_bytes)

        except Exception as e:
            logger.error(f"[STT] Error transcribiendo URL: {e}")
            return None

    async def transcribe_bytes(self, audio_bytes: bytes) -> Optional[str]:
        """
        Transcribir audio desde bytes.

        Args:
            audio_bytes: Bytes del audio

        Returns:
            Texto transcrito o None si falla
        """
        if not self.is_available:
            logger.error("[STT] Deepgram no está configurado")
            return None

        try:
            logger.info(f"[STT] Transcribiendo {len(audio_bytes)} bytes de audio...")

            headers = {
                "Authorization": f"Token {self.api_key}",
                "Content-Type": "audio/ogg"  # Twilio envía en OGG/Opus generalmente
            }

            params = {
                "model": "nova-2",
                "language": "es",
                "smart_format": "true",
                "punctuate": "true"
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.api_url,
                    headers=headers,
                    params=params,
                    data=audio_bytes,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:

                    if response.status == 200:
                        result = await response.json()

                        # Extraer transcripción
                        try:
                            transcript = result["results"]["channels"][0]["alternatives"][0]["transcript"]

                            if transcript:
                                logger.info(f"[STT] Transcripción exitosa: '{transcript}'")
                                return transcript
                            else:
                                logger.warning("[STT] Transcripción vacía")
                                return None

                        except (KeyError, IndexError) as e:
                            logger.error(f"[STT] Error extrayendo transcripción: {e}")
                            return None

                    else:
                        error_text = await response.text()
                        logger.error(f"[STT] Error de Deepgram ({response.status}): {error_text}")
                        return None

        except Exception as e:
            logger.error(f"[STT] Error en transcripción: {e}")
            return None

    async def _download_audio(self, url: str, auth: tuple = None) -> Optional[bytes]:
        """
        Descargar audio desde URL.

        Args:
            url: URL del audio
            auth: Tupla (username, password) para auth básica

        Returns:
            Bytes del audio o None si falla
        """
        try:
            logger.info(f"[STT] Descargando audio de {url[:50]}...")

            async with aiohttp.ClientSession() as session:
                kwargs = {"timeout": aiohttp.ClientTimeout(total=30)}

                # Agregar autenticación si se proporciona (para Twilio)
                if auth:
                    kwargs["auth"] = aiohttp.BasicAuth(auth[0], auth[1])

                async with session.get(url, **kwargs) as response:
                    if response.status == 200:
                        audio_bytes = await response.read()
                        logger.info(f"[STT] Audio descargado: {len(audio_bytes)} bytes")
                        return audio_bytes
                    else:
                        logger.error(f"[STT] Error descargando audio ({response.status})")
                        return None

        except Exception as e:
            logger.error(f"[STT] Error descargando audio: {e}")
            return None


# Instancia global
_stt_client = None


def get_stt_client() -> STTClient:
    """Obtener instancia global del STTClient (Singleton)"""
    global _stt_client
    if _stt_client is None:
        _stt_client = STTClient()
    return _stt_client
