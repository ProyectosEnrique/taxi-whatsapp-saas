"""
================================================================================
UPLOAD ROUTER - Menu Service
================================================================================
Endpoint para subir imágenes de productos
Soporta local storage (desarrollo) y Cloud Storage (producción)
================================================================================
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, status
from fastapi.responses import JSONResponse
import os
import uuid
from pathlib import Path
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# ==============================================================================
# CONFIGURACIÓN
# ==============================================================================

# Directorio para guardar uploads (Docker)
UPLOAD_DIR = Path("/app/uploads/products")

# Tipos de archivo permitidos
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

# ==============================================================================
# UPLOAD IMAGE
# ==============================================================================

@router.post(
    "/image",
    summary="Subir imagen de producto",
    description="Sube una imagen y retorna la URL pública",
    responses={
        200: {
            "description": "Imagen subida exitosamente",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "url": "/uploads/products/abc123.jpg",
                        "filename": "abc123.jpg"
                    }
                }
            }
        },
        400: {"description": "Archivo inválido o muy grande"}
    }
)
async def upload_image(file: UploadFile = File(...)):
    """
    Sube una imagen de producto.

    - **file**: Archivo de imagen (JPG, PNG, GIF, WEBP)
    - **max size**: 5MB

    Retorna URL pública de la imagen.
    """

    logger.info(f"[Upload] Recibiendo archivo: {file.filename}")

    # Validar que sea un archivo
    if not file:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se proporcionó ningún archivo"
        )

    # Validar tipo de archivo por extensión
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Extensión no permitida. Use: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    # Validar content type
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se permiten imágenes"
        )

    # Leer contenido
    try:
        content = await file.read()
    except Exception as e:
        logger.error(f"[Upload] Error leyendo archivo: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al leer el archivo"
        )

    # Validar tamaño
    if len(content) > MAX_FILE_SIZE:
        size_mb = len(content) / (1024 * 1024)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Imagen muy grande ({size_mb:.2f}MB). Máximo 5MB"
        )

    # Generar nombre único
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = str(uuid.uuid4())[:8]
    filename = f"{timestamp}_{unique_id}{file_ext}"

    # Asegurar que el directorio existe
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    # Guardar archivo localmente
    file_path = UPLOAD_DIR / filename

    try:
        with open(file_path, "wb") as f:
            f.write(content)

        logger.info(f"[Upload] Imagen guardada: {filename} ({len(content)} bytes)")

    except Exception as e:
        logger.error(f"[Upload] Error guardando archivo: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al guardar el archivo"
        )

    # URL pública (servida por el mismo servicio)
    image_url = f"/uploads/products/{filename}"

    return JSONResponse({
        "success": True,
        "url": image_url,
        "filename": filename,
        "size": len(content)
    })


# ==============================================================================
# DELETE IMAGE (opcional)
# ==============================================================================

@router.delete(
    "/image/{filename}",
    summary="Eliminar imagen",
    description="Elimina una imagen previamente subida"
)
async def delete_image(filename: str):
    """Elimina una imagen del servidor"""

    file_path = UPLOAD_DIR / filename

    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Imagen no encontrada"
        )

    try:
        file_path.unlink()
        logger.info(f"[Upload] Imagen eliminada: {filename}")

        return JSONResponse({
            "success": True,
            "message": "Imagen eliminada correctamente"
        })

    except Exception as e:
        logger.error(f"[Upload] Error eliminando imagen: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al eliminar la imagen"
        )
