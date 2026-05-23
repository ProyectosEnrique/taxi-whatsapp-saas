# ============================================================================
# PRODUCTS ROUTER - CRUD Endpoints para Productos
# ============================================================================

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid
from slugify import slugify

from src.database import get_db
from src.orm_models import ProductORM, RestaurantORM, CategoryORM
from src.models_multitenant import (
    Product, ProductCreate, ProductUpdate,
    SuccessResponse, PaginatedResponse
)
from src.auth import check_restaurant_access, allow_manager

router = APIRouter(prefix="/api/v1/restaurants/{restaurant_id}/products", tags=["Products"])


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def create_product_slug(name: str, restaurant_id: str, db: Session) -> str:
    """Crear slug único para el producto"""
    base_slug = slugify(name)
    slug = base_slug
    counter = 1

    while db.query(ProductORM).filter(
        ProductORM.restaurant_id == restaurant_id,
        ProductORM.slug == slug
    ).first():
        slug = f"{base_slug}-{counter}"
        counter += 1

    return slug


# ============================================================================
# CREATE PRODUCT
# ============================================================================

@router.post("", response_model=Product, status_code=status.HTTP_201_CREATED)
async def create_product(
    restaurant_id: str,
    product_data: ProductCreate,
    restaurant: RestaurantORM = Depends(check_restaurant_access),
    current_user = Depends(allow_manager),
    db: Session = Depends(get_db)
):
    """
    Crear nuevo producto.

    Permisos: owner, manager, super_admin
    """
    # Verificar que la categoría existe (si se proporciona)
    if product_data.category_id:
        category = db.query(CategoryORM).filter(
            CategoryORM.category_id == product_data.category_id,
            CategoryORM.restaurant_id == restaurant_id
        ).first()

        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found"
            )

    # Generar IDs
    product_id = f"prod_{uuid.uuid4().hex[:12]}"
    slug = create_product_slug(product_data.name, restaurant_id, db)

    # Crear producto
    product = ProductORM(
        product_id=product_id,
        restaurant_id=restaurant_id,
        slug=slug,
        **product_data.dict()
    )

    db.add(product)
    db.commit()
    db.refresh(product)

    return Product.from_orm(product)


# ============================================================================
# GET ALL PRODUCTS
# ============================================================================

@router.get("", response_model=List[Product])
async def get_products(
    restaurant_id: str,
    category_id: Optional[str] = None,
    available: Optional[bool] = None,
    is_featured: Optional[bool] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    restaurant: RestaurantORM = Depends(check_restaurant_access),
    db: Session = Depends(get_db)
):
    """
    Listar todos los productos del restaurante.

    Filtros opcionales:
    - category_id: Filtrar por categoría
    - available: Solo productos disponibles
    - is_featured: Solo productos destacados
    - search: Buscar por nombre
    """
    query = db.query(ProductORM).filter(
        ProductORM.restaurant_id == restaurant_id,
        ProductORM.deleted_at == None
    )

    if category_id:
        query = query.filter(ProductORM.category_id == category_id)

    if available is not None:
        query = query.filter(ProductORM.available == available)

    if is_featured is not None:
        query = query.filter(ProductORM.is_featured == is_featured)

    if search:
        query = query.filter(ProductORM.name.ilike(f"%{search}%"))

    products = query.order_by(
        ProductORM.display_order,
        ProductORM.created_at.desc()
    ).offset(skip).limit(limit).all()

    return [Product.from_orm(p) for p in products]


# ============================================================================
# GET PRODUCT BY ID
# ============================================================================

@router.get("/{product_id}", response_model=Product)
async def get_product(
    restaurant_id: str,
    product_id: str,
    restaurant: RestaurantORM = Depends(check_restaurant_access),
    db: Session = Depends(get_db)
):
    """
    Obtener detalles de un producto específico.
    """
    product = db.query(ProductORM).filter(
        ProductORM.restaurant_id == restaurant_id,
        ProductORM.product_id == product_id,
        ProductORM.deleted_at == None
    ).first()

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )

    return Product.from_orm(product)


# ============================================================================
# UPDATE PRODUCT
# ============================================================================

@router.patch("/{product_id}", response_model=Product)
async def update_product(
    restaurant_id: str,
    product_id: str,
    product_update: ProductUpdate,
    restaurant: RestaurantORM = Depends(check_restaurant_access),
    current_user = Depends(allow_manager),
    db: Session = Depends(get_db)
):
    """
    Actualizar producto.

    Permisos: owner, manager, super_admin
    """
    product = db.query(ProductORM).filter(
        ProductORM.restaurant_id == restaurant_id,
        ProductORM.product_id == product_id,
        ProductORM.deleted_at == None
    ).first()

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )

    # Actualizar campos
    update_data = product_update.dict(exclude_unset=True)

    # Si cambia el nombre, actualizar slug
    if "name" in update_data and update_data["name"] != product.name:
        update_data["slug"] = create_product_slug(
            update_data["name"], restaurant_id, db
        )

    for field, value in update_data.items():
        if hasattr(product, field):
            setattr(product, field, value)

    db.commit()
    db.refresh(product)

    return Product.from_orm(product)


# ============================================================================
# DELETE PRODUCT (Soft Delete)
# ============================================================================

@router.delete("/{product_id}", response_model=SuccessResponse)
async def delete_product(
    restaurant_id: str,
    product_id: str,
    restaurant: RestaurantORM = Depends(check_restaurant_access),
    current_user = Depends(allow_manager),
    db: Session = Depends(get_db)
):
    """
    Eliminar producto (soft delete).

    Permisos: owner, manager, super_admin
    """
    product = db.query(ProductORM).filter(
        ProductORM.restaurant_id == restaurant_id,
        ProductORM.product_id == product_id,
        ProductORM.deleted_at == None
    ).first()

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )

    # Soft delete
    from datetime import datetime
    product.deleted_at = datetime.utcnow()
    product.available = False

    db.commit()

    return SuccessResponse(
        success=True,
        message="Product deleted successfully",
        data={"product_id": product_id}
    )


# ============================================================================
# BULK IMPORT PRODUCTS
# ============================================================================

@router.post("/bulk", response_model=SuccessResponse)
async def bulk_import_products(
    restaurant_id: str,
    products_data: List[ProductCreate],
    restaurant: RestaurantORM = Depends(check_restaurant_access),
    current_user = Depends(allow_manager),
    db: Session = Depends(get_db)
):
    """
    Importación masiva de productos.

    Útil para cargar catálogo inicial.
    """
    created_products = []

    for product_data in products_data:
        # Generar IDs
        product_id = f"prod_{uuid.uuid4().hex[:12]}"
        slug = create_product_slug(product_data.name, restaurant_id, db)

        # Crear producto
        product = ProductORM(
            product_id=product_id,
            restaurant_id=restaurant_id,
            slug=slug,
            **product_data.dict()
        )

        db.add(product)
        created_products.append(product_id)

    db.commit()

    return SuccessResponse(
        success=True,
        message=f"{len(created_products)} products imported successfully",
        data={
            "count": len(created_products),
            "product_ids": created_products
        }
    )


# ============================================================================
# UPDATE STOCK
# ============================================================================

@router.patch("/{product_id}/stock", response_model=Product)
async def update_stock(
    restaurant_id: str,
    product_id: str,
    quantity: int,
    operation: str = Query(..., regex="^(set|add|subtract)$"),
    restaurant: RestaurantORM = Depends(check_restaurant_access),
    current_user = Depends(allow_manager),
    db: Session = Depends(get_db)
):
    """
    Actualizar inventario del producto.

    Operaciones:
    - set: Establecer cantidad exacta
    - add: Agregar cantidad
    - subtract: Restar cantidad
    """
    product = db.query(ProductORM).filter(
        ProductORM.restaurant_id == restaurant_id,
        ProductORM.product_id == product_id,
        ProductORM.deleted_at == None
    ).first()

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )

    if not product.track_inventory:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Product does not track inventory"
        )

    # Actualizar stock
    if operation == "set":
        product.stock_quantity = quantity
    elif operation == "add":
        product.stock_quantity += quantity
    elif operation == "subtract":
        product.stock_quantity -= quantity
        if product.stock_quantity < 0:
            product.stock_quantity = 0

    # Auto-desactivar si stock bajo
    if product.stock_quantity == 0:
        product.available = False

    db.commit()
    db.refresh(product)

    return Product.from_orm(product)
