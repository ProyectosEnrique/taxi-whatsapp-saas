"""
================================================================================
VOICE RESTAURANT ASSISTANT - STT HANDLER
================================================================================
Wrapper para Speech-to-Text (Deepgram)
Usa el SDK de Deepgram directamente
================================================================================
"""

import logging
from deepgram import DeepgramClient, PrerecordedOptions, FileSource

logger = logging.getLogger(__name__)


class STTHandler:
    """
    Handler para Speech-to-Text usando Deepgram SDK
    """

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = None

        if api_key:
            try:
                self.client = DeepgramClient(api_key)
                logger.info("STTHandler inicializado con Deepgram")
            except Exception as e:
                logger.error(f"Error inicializando Deepgram: {e}")
                self.client = None
        else:
            logger.warning("API key no proporcionada para Deepgram")

    async def transcribe_bytes(self, audio_bytes: bytes, convert_to_wav: bool = False) -> str:
        """
        Transcribir audio desde bytes

        Args:
            audio_bytes: Datos de audio
            convert_to_wav: Si convertir a WAV primero

        Returns:
            Transcripción del audio
        """
        if not self.client:
            logger.error("STT no inicializado")
            return ""

        try:
            # Log del tamaño del audio recibido
            logger.info(f"[STT] Procesando {len(audio_bytes)} bytes de audio...")

            # Preparar opciones de transcripción
            options = PrerecordedOptions(
                model="nova-2",
                language="es",
                smart_format=True
            )

            # Preparar fuente de audio
            payload: FileSource = {
                "buffer": audio_bytes,
            }

            # Transcribir (usando prerecorded para SDK v3.x)
            response = self.client.listen.prerecorded.v("1").transcribe_file(payload, options)

            # Extraer transcripción
            if response and response.results and response.results.channels:
                transcript = response.results.channels[0].alternatives[0].transcript
                logger.info(f"[STT] Transcripción: '{transcript}'")
                return transcript
            else:
                logger.warning("[STT] No se pudo obtener transcripción")
                return ""

        except Exception as e:
            logger.error(f"[STT] Error en transcripción: {e}")
            return ""


# Instancia global
_stt_handler = None


def get_stt_handler():
    """Obtener instancia global del STTHandler (Singleton)"""
    global _stt_handler
    if _stt_handler is None:
        from ..core.config import settings
        _stt_handler = STTHandler(api_key=settings.DEEPGRAM_API_KEY)
    return _stt_handler
