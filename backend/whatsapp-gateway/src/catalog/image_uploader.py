"""
================================================================================
META IMAGE UPLOADER - WhatsApp Gateway
================================================================================
Subida de imagenes a Meta Media API para usar en el catalogo de WhatsApp.

Las imagenes subidas pueden usarse en:
- Catalogo de productos (Meta Commerce)
- Mensajes multimedia de WhatsApp

Documentacion:
https://developers.facebook.com/docs/whatsapp/cloud-api/reference/media
================================================================================
"""

import os
import logging
import mimetypes
from typing import Optional, Dict, Any
from io import BytesIO

import aiohttp

logger = logging.getLogger(__name__)


class MetaImageUploader:
    """
    Subida de imagenes a Meta Media API.

    Permite subir imagenes desde:
    - URLs externas (descarga y sube)
    - Bytes en memoria
    - Archivos locales
    """

    BASE_URL = "https://graph.facebook.com/v18.0"

    # Tipos MIME soportados por WhatsApp
    SUPPORTED_TYPES = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp"
    }

    # Tamano maximo: 5MB
    MAX_SIZE_BYTES = 5 * 1024 * 1024

    def __init__(
        self,
        access_token: str = None,
        phone_number_id: str = None,
        timeout: int = 60
    ):
        """
        Inicializar uploader de imagenes.

        Args:
            access_token: Token de acceso de Meta
            phone_number_id: ID del numero de telefono de WhatsApp Business
            timeout: Timeout para requests (subida puede ser lenta)
        """
        self.access_token = access_token or os.getenv("META_ACCESS_TOKEN", "")
        self.phone_number_id = phone_number_id or os.getenv("META_PHONE_NUMBER_ID", "")
        self.timeout = aiohttp.ClientTimeout(total=timeout)

        if not self.phone_number_id:
            logger.warning("[ImageUploader] No phone_number_id configured")

    @property
    def is_configured(self) -> bool:
        """Verificar si el uploader esta configurado"""
        return bool(self.access_token and self.phone_number_id)

    async def upload_from_url(self, image_url: str) -> Optional[str]:
        """
        Descargar imagen desde URL y subir a Meta.

        Args:
            image_url: URL de la imagen a subir

        Returns:
            ID de la imagen en Meta (media_id) o None si falla
        """
        if not self.is_configured:
            logger.warning("[ImageUploader] Not configured, skipping upload")
            return None

        if not image_url:
            return None

        logger.info(f"[ImageUploader] Downloading image from: {image_url[:50]}...")

        try:
            # Descargar imagen
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(image_url) as response:
                    if response.status != 200:
                        logger.warning(f"[ImageUploader] Failed to download: {response.status}")
                        return None

                    # Verificar tipo de contenido
                    content_type = response.headers.get("Content-Type", "").split(";")[0]
                    if content_type not in self.SUPPORTED_TYPES:
                        logger.warning(f"[ImageUploader] Unsupported type: {content_type}")
                        # Intentar con jpeg por defecto
                        content_type = "image/jpeg"

                    # Leer imagen
                    image_data = await response.read()

                    # Verificar tamano
                    if len(image_data) > self.MAX_SIZE_BYTES:
                        logger.warning(f"[ImageUploader] Image too large: {len(image_data)} bytes")
                        # Podriamos redimensionar aqui, pero por ahora solo advertimos
                        return None

            # Subir a Meta
            return await self.upload_bytes(image_data, content_type)

        except aiohttp.ClientError as e:
            logger.error(f"[ImageUploader] Network error downloading: {e}")
            return None
        except Exception as e:
            logger.error(f"[ImageUploader] Error downloading image: {e}")
            return None

    async def upload_bytes(
        self,
        image_data: bytes,
        content_type: str = "image/jpeg",
        filename: str = None
    ) -> Optional[str]:
        """
        Subir bytes de imagen a Meta Media API.

        Args:
            image_data: Bytes de la imagen
            content_type: Tipo MIME de la imagen
            filename: Nombre del archivo (opcional)

        Returns:
            ID de la imagen en Meta (media_id) o None si falla
        """
        if not self.is_configured:
            logger.warning("[ImageUploader] Not configured, skipping upload")
            return None

        if not image_data:
            return None

        # Generar nombre de archivo si no se proporciona
        if not filename:
            ext = self.SUPPORTED_TYPES.get(content_type, ".jpg")
            filename = f"product{ext}"

        url = f"{self.BASE_URL}/{self.phone_number_id}/media"

        # Preparar form data
        form = aiohttp.FormData()
        form.add_field(
            "file",
            image_data,
            filename=filename,
            content_type=content_type
        )
        form.add_field("messaging_product", "whatsapp")
        form.add_field("type", "image")

        headers = {"Authorization": f"Bearer {self.access_token}"}

        logger.info(f"[ImageUploader] Uploading {len(image_data)} bytes ({content_type})")

        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.post(url, data=form, headers=headers) as response:
                    result = await response.json()

                    if response.status >= 400:
                        logger.error(f"[ImageUploader] Upload failed: {result}")
                        return None

                    media_id = result.get("id")
                    logger.info(f"[ImageUploader] Upload successful: {media_id}")
                    return media_id

        except aiohttp.ClientError as e:
            logger.error(f"[ImageUploader] Network error uploading: {e}")
            return None
        except Exception as e:
            logger.error(f"[ImageUploader] Error uploading: {e}")
            return None

    async def upload_from_path(self, file_path: str) -> Optional[str]:
        """
        Subir imagen desde archivo local.

        Args:
            file_path: Ruta al archivo de imagen

        Returns:
            ID de la imagen en Meta o None si falla
        """
        if not os.path.exists(file_path):
            logger.error(f"[ImageUploader] File not found: {file_path}")
            return None

        # Detectar tipo MIME
        content_type = mimetypes.guess_type(file_path)[0] or "image/jpeg"

        if content_type not in self.SUPPORTED_TYPES:
            logger.warning(f"[ImageUploader] Unsupported file type: {content_type}")
            content_type = "image/jpeg"

        # Leer archivo
        try:
            with open(file_path, "rb") as f:
                image_data = f.read()
        except IOError as e:
            logger.error(f"[ImageUploader] Error reading file: {e}")
            return None

        filename = os.path.basename(file_path)
        return await self.upload_bytes(image_data, content_type, filename)

    async def get_media_url(self, media_id: str) -> Optional[str]:
        """
        Obtener URL temporal de un media subido.

        Args:
            media_id: ID del media en Meta

        Returns:
            URL temporal del media o None
        """
        if not self.is_configured or not media_id:
            return None

        url = f"{self.BASE_URL}/{media_id}"

        headers = {"Authorization": f"Bearer {self.access_token}"}

        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(url, headers=headers) as response:
                    result = await response.json()

                    if response.status >= 400:
                        logger.error(f"[ImageUploader] Get URL failed: {result}")
                        return None

                    return result.get("url")

        except Exception as e:
            logger.error(f"[ImageUploader] Error getting URL: {e}")
            return None

    async def delete_media(self, media_id: str) -> bool:
        """
        Eliminar un media subido.

        Args:
            media_id: ID del media en Meta

        Returns:
            True si se elimino correctamente
        """
        if not self.is_configured or not media_id:
            return False

        url = f"{self.BASE_URL}/{media_id}"

        headers = {"Authorization": f"Bearer {self.access_token}"}

        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.delete(url, headers=headers) as response:
                    result = await response.json()

                    if response.status >= 400:
                        logger.error(f"[ImageUploader] Delete failed: {result}")
                        return False

                    success = result.get("success", False)
                    if success:
                        logger.info(f"[ImageUploader] Media deleted: {media_id}")
                    return success

        except Exception as e:
            logger.error(f"[ImageUploader] Error deleting: {e}")
            return False
