"""
================================================================================
VOICE RESTAURANT ASSISTANT - CARTESIA SONIC TTS HANDLER
================================================================================
Text-to-Speech ultra-rapido usando Cartesia Sonic 3

Caracteristicas:
- Latencia ~90ms (vs 200-1000ms de Piper)
- Calidad de voz natural comparable a ElevenLabs
- Soporte para espanol con multiples voces
- Cliente asincrono para mejor rendimiento
- Streaming opcional para latencia aun menor

Documentacion: https://docs.cartesia.ai/
================================================================================
"""

import os
import logging
import asyncio
import struct
from pathlib import Path
from typing import Optional, AsyncIterator
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class CartesiaVoice(Enum):
    """Voces en espanol disponibles en Cartesia"""
    # Voces masculinas
    NARRATOR_MAN = "a67e0421-22e0-4d5b-b586-bd4a64aee41d"        # Narrador profesional
    STORYTELLER_MAN = "846fa30b-6e1a-49b9-b7df-6be47092a09a"     # Cuenta cuentos
    SPEAKING_MAN = "34dbb662-8e98-413c-a1ef-1a3407675fe7"        # Conversacional
    REPORTER_MAN = "2695b6b5-5543-4be1-96d9-3967fb5e7fec"        # Estilo reportero

    # Voces femeninas
    NARRATOR_LADY = "2deb3edf-b9d8-4d06-8db9-5742fb8a3cb2"       # Narradora profesional
    SPEAKING_LADY = "846d6cb0-2301-48b6-9683-48f5618ea2f6"       # Conversacional
    YOUNG_WOMAN = "db832ebd-3cb6-42e7-9d47-912b425adbaa"         # Joven, fresca


@dataclass
class CartesiaConfig:
    """Configuracion para Cartesia TTS"""
    api_key: str
    voice_id: str = CartesiaVoice.SPEAKING_LADY.value  # Voz femenina conversacional por defecto
    model_id: str = "sonic-3"                           # Modelo mas reciente
    language: str = "es"                                # Espanol
    sample_rate: int = 22050                            # Balance calidad/tamano
    output_format: str = "wav"                          # Formato de salida


class CartesiaTTSHandler:
    """
    Handler para Text-to-Speech usando Cartesia Sonic 3.

    Ventajas sobre Piper:
    - 5-10x mas rapido (~90ms vs 200-1000ms)
    - Mejor calidad de voz
    - Voces nativas en espanol
    - Soporte para streaming

    Uso:
        handler = CartesiaTTSHandler(api_key="...")
        await handler.synthesize_to_file("Hola mundo", Path("output.wav"))
    """

    def __init__(self, config: Optional[CartesiaConfig] = None):
        """
        Inicializa el handler de Cartesia TTS.

        Args:
            config: Configuracion de Cartesia. Si no se proporciona,
                   se crea una usando variables de entorno.
        """
        self._client = None
        self._async_client = None

        if config:
            self.config = config
        else:
            api_key = os.getenv("CARTESIA_API_KEY", "")
            voice_id = os.getenv("CARTESIA_VOICE_ID", CartesiaVoice.SPEAKING_LADY.value)
            self.config = CartesiaConfig(api_key=api_key, voice_id=voice_id)

        self._initialized = False
        self._init_error = None

        if self.config.api_key:
            self._initialize_client()
        else:
            logger.warning("[Cartesia] API key no proporcionada - TTS no disponible")

    def _initialize_client(self):
        """Inicializa el cliente de Cartesia"""
        try:
            from cartesia import Cartesia, AsyncCartesia

            self._client = Cartesia(api_key=self.config.api_key)
            self._async_client = AsyncCartesia(api_key=self.config.api_key)
            self._initialized = True

            logger.info(f"[Cartesia] TTS inicializado - Modelo: {self.config.model_id}, Voz: {self.config.voice_id[:8]}...")

        except ImportError:
            self._init_error = "Cartesia SDK no instalado. Ejecuta: pip install cartesia"
            logger.error(f"[Cartesia] {self._init_error}")
        except Exception as e:
            self._init_error = str(e)
            logger.error(f"[Cartesia] Error inicializando: {e}")

    @property
    def is_available(self) -> bool:
        """Verifica si Cartesia esta disponible y configurado"""
        return self._initialized and self._async_client is not None

    def set_voice(self, voice: CartesiaVoice):
        """
        Cambia la voz activa.

        Args:
            voice: Voz de CartesiaVoice enum
        """
        self.config.voice_id = voice.value
        logger.info(f"[Cartesia] Voz cambiada a: {voice.name}")

    def set_voice_by_id(self, voice_id: str):
        """
        Cambia la voz usando un ID personalizado.

        Args:
            voice_id: UUID de la voz en Cartesia
        """
        self.config.voice_id = voice_id
        logger.info(f"[Cartesia] Voz cambiada a ID: {voice_id[:8]}...")

    def _pcm_to_wav(self, pcm_data: bytes, sample_rate: int = 22050) -> bytes:
        """Convierte datos PCM raw a formato WAV con header correcto"""
        num_channels = 1
        bits_per_sample = 16
        byte_rate = sample_rate * num_channels * bits_per_sample // 8
        block_align = num_channels * bits_per_sample // 8
        data_size = len(pcm_data)

        wav_header = b'RIFF'
        wav_header += struct.pack('<I', 36 + data_size)
        wav_header += b'WAVE'
        wav_header += b'fmt '
        wav_header += struct.pack('<I', 16)
        wav_header += struct.pack('<H', 1)
        wav_header += struct.pack('<H', num_channels)
        wav_header += struct.pack('<I', sample_rate)
        wav_header += struct.pack('<I', byte_rate)
        wav_header += struct.pack('<H', block_align)
        wav_header += struct.pack('<H', bits_per_sample)
        wav_header += b'data'
        wav_header += struct.pack('<I', data_size)

        return wav_header + pcm_data

    async def synthesize_to_file(
        self,
        text: str,
        output_path: Path,
        voice_id: Optional[str] = None
    ) -> bool:
        """
        Sintetiza texto a un archivo de audio.

        Args:
            text: Texto a sintetizar
            output_path: Ruta del archivo de salida
            voice_id: ID de voz opcional (usa default si no se especifica)

        Returns:
            True si la sintesis fue exitosa, False en caso contrario
        """
        if not self.is_available:
            logger.error(f"[Cartesia] No disponible: {self._init_error}")
            return False

        if not text or not text.strip():
            logger.warning("[Cartesia] Texto vacio, saltando sintesis")
            return False

        try:
            # Usar voz especificada o la configurada
            voice = voice_id or self.config.voice_id

            logger.debug(f"[Cartesia] Sintetizando {len(text)} caracteres...")

            # SDK v1.x: get_output_format toma un nombre de formato como string
            # Formatos disponibles: pcm_16000, pcm_22050, pcm_44100
            output_format = self._async_client.tts.get_output_format("pcm_22050")

            # Generar audio usando SSE (Server-Sent Events)
            # SDK v1.x: sse() con stream=False puede retornar bytes, dict, o generator
            result = await self._async_client.tts.sse(
                model_id=self.config.model_id,
                transcript=text,
                voice_id=voice,
                output_format=output_format,
                stream=False,
            )

            # Extraer audio del resultado
            audio_data = None
            if isinstance(result, bytes):
                audio_data = result
            elif hasattr(result, 'audio'):
                audio_data = result.audio
            elif isinstance(result, dict) and 'audio' in result:
                audio_data = result['audio']
            else:
                # Si es un async generator, iterar
                audio_chunks = []
                async for event in result:
                    if isinstance(event, bytes):
                        audio_chunks.append(event)
                    elif hasattr(event, 'audio') and event.audio:
                        audio_chunks.append(event.audio)
                    elif isinstance(event, dict) and 'audio' in event:
                        audio_chunks.append(event['audio'])
                if audio_chunks:
                    audio_data = b''.join(audio_chunks)

            if not audio_data:
                logger.error("[Cartesia] No se recibio audio del servidor")
                return False

            # Convertir PCM raw a WAV y escribir archivo
            output_path.parent.mkdir(parents=True, exist_ok=True)
            wav_data = self._pcm_to_wav(audio_data, 22050)

            with open(output_path, 'wb') as f:
                f.write(wav_data)

            file_size = output_path.stat().st_size
            logger.info(f"[Cartesia] Audio generado: {output_path.name} ({file_size} bytes)")

            return True

        except Exception as e:
            logger.error(f"[Cartesia] Error en sintesis: {e}", exc_info=True)
            return False

    async def synthesize_to_bytes(
        self,
        text: str,
        voice_id: Optional[str] = None
    ) -> Optional[bytes]:
        """
        Sintetiza texto y retorna los bytes de audio directamente.

        Args:
            text: Texto a sintetizar
            voice_id: ID de voz opcional

        Returns:
            Bytes del audio WAV o None si falla
        """
        if not self.is_available:
            logger.error(f"[Cartesia] No disponible: {self._init_error}")
            return None

        if not text or not text.strip():
            return None

        try:
            voice = voice_id or self.config.voice_id

            # SDK v1.x: usar nombre de formato como string
            output_format = self._async_client.tts.get_output_format("pcm_22050")

            result = await self._async_client.tts.sse(
                model_id=self.config.model_id,
                transcript=text,
                voice_id=voice,
                output_format=output_format,
                stream=False,
            )

            # Extraer audio
            audio_data = None
            if isinstance(result, bytes):
                audio_data = result
            elif hasattr(result, 'audio'):
                audio_data = result.audio
            elif isinstance(result, dict) and 'audio' in result:
                audio_data = result['audio']
            else:
                audio_chunks = []
                async for event in result:
                    if isinstance(event, bytes):
                        audio_chunks.append(event)
                    elif hasattr(event, 'audio') and event.audio:
                        audio_chunks.append(event.audio)
                    elif isinstance(event, dict) and 'audio' in event:
                        audio_chunks.append(event['audio'])
                if audio_chunks:
                    audio_data = b''.join(audio_chunks)

            if audio_data:
                return self._pcm_to_wav(audio_data, 22050)
            return None

        except Exception as e:
            logger.error(f"[Cartesia] Error en sintesis a bytes: {e}")
            return None

    async def synthesize_streaming(
        self,
        text: str,
        voice_id: Optional[str] = None
    ) -> AsyncIterator[bytes]:
        """
        Sintetiza texto con streaming para latencia ultra-baja.

        El audio se genera y retorna en chunks mientras se procesa,
        permitiendo comenzar la reproduccion antes de terminar la sintesis.

        Args:
            text: Texto a sintetizar
            voice_id: ID de voz opcional

        Yields:
            Chunks de audio en formato raw PCM
        """
        if not self.is_available:
            logger.error(f"[Cartesia] No disponible para streaming")
            return

        if not text or not text.strip():
            return

        try:
            voice = voice_id or self.config.voice_id

            # SDK v1.x: usar nombre de formato
            output_format = self._async_client.tts.get_output_format("pcm_22050")

            result = await self._async_client.tts.sse(
                model_id=self.config.model_id,
                transcript=text,
                voice_id=voice,
                output_format=output_format,
                stream=True,
            )

            async for event in result:
                if isinstance(event, bytes):
                    yield event
                elif hasattr(event, 'audio') and event.audio:
                    yield event.audio
                elif isinstance(event, dict) and 'audio' in event:
                    yield event['audio']

        except Exception as e:
            logger.error(f"[Cartesia] Error en streaming: {e}")

    def synthesize_to_file_sync(
        self,
        text: str,
        output_path: Path,
        voice_id: Optional[str] = None
    ) -> bool:
        """
        Version sincrona de synthesize_to_file para compatibilidad.

        Args:
            text: Texto a sintetizar
            output_path: Ruta del archivo de salida
            voice_id: ID de voz opcional

        Returns:
            True si la sintesis fue exitosa
        """
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(
            self.synthesize_to_file(text, output_path, voice_id)
        )

    async def list_voices(self) -> list:
        """
        Lista todas las voces disponibles en Cartesia.

        Returns:
            Lista de voces con sus IDs y metadatos
        """
        if not self.is_available:
            return []

        try:
            voices = []
            for voice in self._client.voices.list():
                voices.append({
                    "id": voice.id,
                    "name": voice.name,
                    "description": getattr(voice, 'description', ''),
                    "language": getattr(voice, 'language', 'unknown'),
                })
            return voices
        except Exception as e:
            logger.error(f"[Cartesia] Error listando voces: {e}")
            return []

    def get_status(self) -> dict:
        """Retorna el estado del handler"""
        return {
            "available": self.is_available,
            "model": self.config.model_id,
            "voice_id": self.config.voice_id[:8] + "..." if self.config.voice_id else None,
            "language": self.config.language,
            "sample_rate": self.config.sample_rate,
            "error": self._init_error,
        }


# ============================================================
# SINGLETON Y FACTORY
# ============================================================

_cartesia_handler: Optional[CartesiaTTSHandler] = None


def get_cartesia_handler() -> CartesiaTTSHandler:
    """
    Obtiene la instancia global del handler de Cartesia (Singleton).

    Returns:
        Instancia de CartesiaTTSHandler
    """
    global _cartesia_handler

    if _cartesia_handler is None:
        _cartesia_handler = CartesiaTTSHandler()

    return _cartesia_handler


def create_cartesia_handler(
    api_key: str,
    voice: CartesiaVoice = CartesiaVoice.SPEAKING_LADY
) -> CartesiaTTSHandler:
    """
    Crea una nueva instancia del handler con configuracion personalizada.

    Args:
        api_key: API key de Cartesia
        voice: Voz a usar (default: SPEAKING_LADY)

    Returns:
        Nueva instancia de CartesiaTTSHandler
    """
    config = CartesiaConfig(
        api_key=api_key,
        voice_id=voice.value
    )
    return CartesiaTTSHandler(config)
