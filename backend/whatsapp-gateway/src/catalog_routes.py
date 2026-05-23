"""
================================================================================
CATALOG ROUTES - WhatsApp Gateway
================================================================================
Endpoints de administracion para el catalogo de Meta Commerce.

Permite:
- Sincronizar productos con el catalogo de Meta
- Ver estado de sincronizacion
- Subir imagenes de productos
- Validar configuracion

Uso:
    POST /api/catalog/sync - Sincronizar todos los productos
    GET /api/catalog/status - Ver estado de sincronizacion
    POST /api/catalog/sync/{product_id} - Sincronizar producto especifico
    POST /api/catalog/upload-image/{product_id} - Subir imagen
    GET /api/catalog/config - Validar configuracion
    DELETE /api/catalog/{retailer_id} - Eliminar producto del catalogo
================================================================================
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import logging
import os

from .catalog import get_catalog_service, MetaCatalogClient, MetaImageUploader

logger = logging.getLogger(__name__)

# Router
router = APIRouter(prefix="/api/catalog", tags=["catalog"])


# ==============================================================================
# MODELS
# ==============================================================================

class SyncRequest(BaseModel):
    """Request para sincronizacion"""
    status_filter: Optional[str] = "pending"
    limit: Optional[int] = 100


class SyncResponse(BaseModel):
    """Response de sincronizacion"""
    success: bool
    synced: int = 0
    errors: int = 0
    message: Optional[str] = None
    details: Optional[List[Dict[str, Any]]] = None


class ConfigStatus(BaseModel):
    """Estado de configuracion"""
    configured: bool
    catalog_id: Optional[str] = None
    phone_number_id: Optional[str] = None
    has_access_token: bool = False
    warnings: List[str] = []


# ==============================================================================
# ENDPOINTS
# ==============================================================================

@router.get("/config", response_model=ConfigStatus)
async def get_config_status():
    """
    Obtener estado de configuracion del catalogo.

    Verifica que todas las variables de entorno esten configuradas
    y que la conexion con Meta sea posible.
    """
    catalog_id = os.getenv("META_CATALOG_ID", "")
    phone_number_id = os.getenv("META_PHONE_NUMBER_ID", "")
    access_token = os.getenv("META_ACCESS_TOKEN", "")

    warnings = []

    if not catalog_id:
        warnings.append("META_CATALOG_ID no configurado")
    if not phone_number_id:
        warnings.append("META_PHONE_NUMBER_ID no configurado")
    if not access_token:
        warnings.append("META_ACCESS_TOKEN no configurado")

    configured = bool(catalog_id and phone_number_id and access_token)

    return ConfigStatus(
        configured=configured,
        catalog_id=catalog_id[:10] + "..." if catalog_id else None,
        phone_number_id=phone_number_id[:10] + "..." if phone_number_id else None,
        has_access_token=bool(access_token),
        warnings=warnings
    )


@router.post("/sync", response_model=SyncResponse)
async def sync_all_products(
    request: SyncRequest,
    background_tasks: BackgroundTasks
):
    """
    Sincronizar todos los productos pendientes con Meta.

    Parametros:
        - status_filter: Filtrar por estado (pending, error, all)
        - limit: Numero maximo de productos a sincronizar

    Este endpoint inicia la sincronizacion en background y retorna inmediatamente.
    """
    service = get_catalog_service()

    if not service.is_configured:
        raise HTTPException(
            status_code=503,
            detail="Catalog service not configured. Check META_CATALOG_ID and META_ACCESS_TOKEN."
        )

    logger.info(f"[CatalogRoutes] Starting sync: filter={request.status_filter}, limit={request.limit}")

    # Ejecutar sync
    result = await service.sync_all_products(
        status_filter=request.status_filter,
        limit=request.limit
    )

    return SyncResponse(
        success=result.get("success", False),
        synced=result.get("synced", 0),
        errors=result.get("errors", 0),
        message=result.get("message"),
        details=result.get("details")
    )


@router.post("/sync/{product_id}")
async def sync_single_product(product_id: int):
    """
    Sincronizar un producto especifico con Meta.

    Util para re-sincronizar un producto despues de actualizarlo.
    """
    import aiohttp

    service = get_catalog_service()

    if not service.is_configured:
        raise HTTPException(
            status_code=503,
            detail="Catalog service not configured"
        )

    # Obtener producto del menu-service
    menu_service_url = os.getenv("MENU_SERVICE_URL", "http://menu-service:8001")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{menu_service_url}/api/v1/products/{product_id}") as response:
                if response.status == 404:
                    raise HTTPException(status_code=404, detail="Product not found")
                if response.status != 200:
                    raise HTTPException(status_code=502, detail="Menu service error")

                product = await response.json()

    except aiohttp.ClientError as e:
        logger.error(f"[CatalogRoutes] Error fetching product: {e}")
        raise HTTPException(status_code=502, detail="Could not connect to menu service")

    # Sincronizar producto
    result = await service.sync_product(product)

    return {
        "success": result.success,
        "product_id": result.product_id,
        "retailer_id": result.retailer_id,
        "image_uploaded": result.image_uploaded,
        "error": result.error
    }


@router.get("/status")
async def get_sync_status():
    """
    Obtener estado de sincronizacion del catalogo.

    Retorna estadisticas de productos sincronizados, pendientes y con error.
    """
    service = get_catalog_service()

    if not service.is_configured:
        return {
            "configured": False,
            "message": "Catalog service not configured",
            "stats": {}
        }

    status = await service.get_sync_status()

    return {
        "configured": True,
        **status
    }


@router.post("/upload-image/{product_id}")
async def upload_product_image(
    product_id: int,
    file: UploadFile = File(...)
):
    """
    Subir imagen de producto a Meta Media API.

    La imagen subida se puede usar en el catalogo de Meta Commerce.

    Formatos soportados: JPEG, PNG, WebP
    Tamano maximo: 5MB
    """
    uploader = MetaImageUploader()

    if not uploader.is_configured:
        raise HTTPException(
            status_code=503,
            detail="Image uploader not configured. Check META_ACCESS_TOKEN and META_PHONE_NUMBER_ID."
        )

    # Validar tipo de archivo
    content_type = file.content_type or "image/jpeg"
    if content_type not in uploader.SUPPORTED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {content_type}. Use JPEG, PNG or WebP."
        )

    # Leer archivo
    try:
        image_data = await file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading file: {e}")

    # Validar tamano
    if len(image_data) > uploader.MAX_SIZE_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: {uploader.MAX_SIZE_BYTES // (1024*1024)}MB"
        )

    # Subir a Meta
    media_id = await uploader.upload_bytes(
        image_data,
        content_type,
        file.filename
    )

    if not media_id:
        raise HTTPException(status_code=502, detail="Failed to upload image to Meta")

    # Actualizar producto en menu-service
    import aiohttp
    menu_service_url = os.getenv("MENU_SERVICE_URL", "http://menu-service:8001")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.patch(
                f"{menu_service_url}/api/v1/products/{product_id}/meta",
                json={"meta_image_id": media_id}
            ) as response:
                if response.status >= 400:
                    logger.warning(f"[CatalogRoutes] Failed to update product image: {response.status}")

    except Exception as e:
        logger.warning(f"[CatalogRoutes] Could not update product: {e}")

    return {
        "success": True,
        "media_id": media_id,
        "product_id": product_id
    }


@router.delete("/{retailer_id}")
async def delete_from_catalog(retailer_id: str):
    """
    Eliminar un producto del catalogo de Meta.

    Esto no elimina el producto del menu-service, solo del catalogo de WhatsApp.
    """
    service = get_catalog_service()

    if not service.is_configured:
        raise HTTPException(
            status_code=503,
            detail="Catalog service not configured"
        )

    result = await service.delete_product(retailer_id)

    if not result.get("success"):
        raise HTTPException(
            status_code=502,
            detail=result.get("error", "Failed to delete from catalog")
        )

    return {
        "success": True,
        "retailer_id": retailer_id,
        "message": "Product removed from catalog"
    }


@router.get("/products")
async def list_catalog_products(limit: int = 50):
    """
    Listar productos en el catalogo de Meta.

    Obtiene los productos directamente del catalogo de Meta Commerce.
    """
    catalog_client = MetaCatalogClient()

    if not catalog_client.is_configured:
        raise HTTPException(
            status_code=503,
            detail="Catalog client not configured"
        )

    result = await catalog_client.get_products(limit=limit)

    return {
        "success": result.get("success", False),
        "products": result.get("products", []),
        "total": len(result.get("products", [])),
        "error": result.get("error")
    }


@router.get("/info")
async def get_catalog_info():
    """
    Obtener informacion del catalogo de Meta.

    Retorna detalles del catalogo configurado.
    """
    catalog_client = MetaCatalogClient()

    if not catalog_client.is_configured:
        return {
            "configured": False,
            "message": "Catalog client not configured"
        }

    info = await catalog_client.get_catalog_info()

    return {
        "configured": True,
        **info
    }
