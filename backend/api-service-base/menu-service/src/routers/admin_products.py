"""
================================================================================
ADMIN PRODUCTS ROUTER - Gestión de Productos
================================================================================
Endpoints de administración para crear y gestionar productos
================================================================================
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import logging

from ..database import get_db
from ..models import Product, Category
from ..models.user import User
from ..schemas import ProductCreate, ProductUpdate, ProductResponse
from ..auth.permissions import require_admin, verify_tenant_admin

logger = logging.getLogger(__name__)

router = APIRouter()


# ==============================================================================
# CREATE PRODUCT
# ==============================================================================

@router.post(
    "",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear nuevo producto"
)
async def create_product(
    data: ProductCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Crear un nuevo producto en el catálogo del tenant.

    Solo administradores pueden crear productos para su tenant.
    """
    logger.info(f"Admin {current_user.id} creando producto: {data.name}")

    # El producto se crea para el tenant del usuario actual
    # (a menos que sea super admin y especifique otro)
    tenant_id = current_user.tenant_id

    # Verificar que la categoría pertenece al tenant (si se especifica)
    if data.category_id:
        category = db.query(Category).filter(Category.id == data.category_id).first()
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Categoría no encontrada"
            )
        if category.tenant_id != tenant_id and not current_user.is_super_admin():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="La categoría no pertenece a tu tenant"
            )

    # Crear producto
    new_product = Product(
        tenant_id=tenant_id,
        name=data.name,
        description=data.description,
        price=data.price,
        category_id=data.category_id,
        image_url=data.image_url,
        video_url=data.video_url,
        is_available=data.is_available if data.is_available is not None else True,
        ingredients=data.ingredients,
        spice_level=data.spice_level,
        preparation_time_minutes=data.preparation_time_minutes,
        popularity=data.popularity,
        profitability=data.profitability,
        cost=data.cost,
        menu_classification=data.menu_classification
    )

    db.add(new_product)
    db.commit()
    db.refresh(new_product)

    logger.info(f"Producto creado: {new_product.id} - {new_product.name}")

    return new_product


# ==============================================================================
# UPDATE PRODUCT
# ==============================================================================

@router.put(
    "/{product_id}",
    response_model=ProductResponse,
    summary="Actualizar producto"
)
async def update_product(
    product_id: int,
    data: ProductUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Actualizar un producto existente.

    Solo administradores pueden actualizar productos de su tenant.
    """
    logger.info(f"Actualizando producto: {product_id}")

    # Buscar producto
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado"
        )

    # Verificar que el admin pertenece al tenant del producto
    if product.tenant_id != current_user.tenant_id and not current_user.is_super_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para modificar este producto"
        )

    # Actualizar campos
    update_data = data.dict(exclude_unset=True)

    # Si se actualiza la categoría, verificar que pertenezca al tenant
    if 'category_id' in update_data and update_data['category_id']:
        category = db.query(Category).filter(Category.id == update_data['category_id']).first()
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Categoría no encontrada"
            )
        if category.tenant_id != product.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La categoría debe pertenecer al mismo tenant"
            )

    for field, value in update_data.items():
        setattr(product, field, value)

    db.commit()
    db.refresh(product)

    logger.info(f"Producto {product_id} actualizado exitosamente")

    return product


# ==============================================================================
# DELETE PRODUCT
# ==============================================================================

@router.delete(
    "/{product_id}",
    summary="Eliminar producto"
)
async def delete_product(
    product_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Eliminar un producto del catálogo.

    Solo administradores pueden eliminar productos de su tenant.
    """
    logger.info(f"Eliminando producto: {product_id}")

    # Buscar producto
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado"
        )

    # Verificar permisos
    if product.tenant_id != current_user.tenant_id and not current_user.is_super_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para eliminar este producto"
        )

    db.delete(product)
    db.commit()

    logger.info(f"Producto {product_id} eliminado")

    return {
        "success": True,
        "message": "Producto eliminado exitosamente"
    }


# ==============================================================================
# LIST PRODUCTS (ADMIN VIEW WITH TENANT FILTER)
# ==============================================================================

@router.get(
    "",
    response_model=List[ProductResponse],
    summary="Listar productos (Vista Admin)"
)
async def list_products_admin(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    category_id: Optional[int] = Query(default=None),
    is_available: Optional[bool] = Query(default=None),
    search: Optional[str] = Query(default=None, description="Buscar por nombre"),
    tenant_id: Optional[str] = Query(default=None, description="Filtrar por tenant (solo super admin)")
):
    """
    Listar productos con filtros (vista de administración).

    - Admin normal ve solo productos de su tenant
    - Super admin puede ver productos de cualquier tenant
    """
    logger.info(f"Admin {current_user.id} listando productos")

    query = db.query(Product)

    # Filtrar por tenant
    if tenant_id:
        # Solo super admin puede filtrar por otros tenants
        if not current_user.is_super_admin():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo super admin puede filtrar por otros tenants"
            )
        query = query.filter(Product.tenant_id == tenant_id)
    else:
        # Admin normal solo ve su tenant
        if not current_user.is_super_admin():
            query = query.filter(Product.tenant_id == current_user.tenant_id)

    # Otros filtros
    if category_id:
        query = query.filter(Product.category_id == category_id)

    if is_available is not None:
        query = query.filter(Product.is_available == is_available)

    if search:
        query = query.filter(Product.name.ilike(f"%{search}%"))

    products = query.order_by(Product.created_at.desc()).offset(skip).limit(limit).all()

    logger.info(f"Encontrados {len(products)} productos")

    return products


# ==============================================================================
# TOGGLE PRODUCT AVAILABILITY
# ==============================================================================

@router.patch(
    "/{product_id}/availability",
    response_model=ProductResponse,
    summary="Cambiar disponibilidad del producto"
)
async def toggle_product_availability(
    product_id: int,
    is_available: bool,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Activar o desactivar la disponibilidad de un producto.

    Útil para productos temporalmente agotados.
    """
    logger.info(f"Cambiando disponibilidad del producto {product_id} a {is_available}")

    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado"
        )

    # Verificar permisos
    if product.tenant_id != current_user.tenant_id and not current_user.is_super_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para modificar este producto"
        )

    product.is_available = is_available
    db.commit()
    db.refresh(product)

    logger.info(f"Disponibilidad actualizada para producto {product_id}")

    return product


# ==============================================================================
# BULK CREATE PRODUCTS
# ==============================================================================

@router.post(
    "/bulk",
    summary="Crear múltiples productos"
)
async def bulk_create_products(
    products: List[ProductCreate],
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Crear múltiples productos de una vez.

    Útil para carga inicial de catálogo.
    """
    logger.info(f"Creando {len(products)} productos en bulk")

    tenant_id = current_user.tenant_id
    created_products = []
    errors = []

    for idx, product_data in enumerate(products):
        try:
            # Verificar categoría si existe
            if product_data.category_id:
                category = db.query(Category).filter(Category.id == product_data.category_id).first()
                if not category or (category.tenant_id != tenant_id and not current_user.is_super_admin()):
                    errors.append({
                        "index": idx,
                        "name": product_data.name,
                        "error": "Categoría inválida"
                    })
                    continue

            new_product = Product(
                tenant_id=tenant_id,
                name=product_data.name,
                description=product_data.description,
                price=product_data.price,
                category_id=product_data.category_id,
                image_url=product_data.image_url,
                is_available=product_data.is_available if product_data.is_available is not None else True,
                ingredients=product_data.ingredients,
                spice_level=product_data.spice_level,
                preparation_time_minutes=product_data.preparation_time_minutes,
                popularity=product_data.popularity,
                profitability=product_data.profitability,
                cost=product_data.cost
            )

            db.add(new_product)
            created_products.append(new_product)

        except Exception as e:
            errors.append({
                "index": idx,
                "name": product_data.name,
                "error": str(e)
            })

    db.commit()

    logger.info(f"Creados {len(created_products)} productos. Errores: {len(errors)}")

    return {
        "success": True,
        "created": len(created_products),
        "errors": errors
    }
