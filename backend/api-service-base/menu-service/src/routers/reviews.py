"""
================================================================================
REVIEWS ROUTER - Reseñas y Calificaciones
================================================================================
Endpoints para gestión de reseñas de pedidos
================================================================================
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import logging
import os
import uuid
from datetime import datetime

from ..database import get_db
from ..models.review import Review
from ..models.order import Order
from ..models.user import User
from ..schemas.review import (
    ReviewCreate,
    ReviewResponse,
    ReviewWithUser,
    UploadImageResponse
)
from ..routers.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()

# Directorio para guardar imágenes de reseñas
UPLOAD_DIR = "uploads/reviews"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ==============================================================================
# CREATE REVIEW
# ==============================================================================

@router.post(
    "",
    response_model=ReviewResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear reseña de pedido"
)
async def create_review(
    data: ReviewCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Crear una reseña para un pedido completado.

    Restricciones:
    - Solo el usuario que hizo el pedido puede dejarlo reseña
    - Solo se puede hacer una reseña por pedido
    - El pedido debe estar en estado 'delivered'
    """
    logger.info(f"Usuario {current_user.id} creando reseña para pedido {data.order_id}")

    # Verificar que el pedido existe
    order = db.query(Order).filter(Order.id == data.order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pedido no encontrado"
        )

    # Verificar que el pedido pertenece al usuario actual
    if order.customer_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para reseñar este pedido"
        )

    # Verificar que el pedido está entregado
    if order.status.value != "delivered":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo puedes reseñar pedidos entregados"
        )

    # Verificar que no existe ya una reseña para este pedido
    existing_review = db.query(Review).filter(Review.order_id == data.order_id).first()
    if existing_review:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe una reseña para este pedido"
        )

    # Calcular rating promedio
    rating = (data.food_quality + data.delivery_time + data.service) / 3.0

    # Crear reseña
    new_review = Review(
        order_id=data.order_id,
        user_id=current_user.id,
        food_quality=data.food_quality,
        delivery_time=data.delivery_time,
        service=data.service,
        rating=rating,
        comment=data.comment,
        image_url=data.image_url
    )

    db.add(new_review)
    db.commit()
    db.refresh(new_review)

    logger.info(f"Reseña creada exitosamente: ID {new_review.id}, Rating {rating}⭐")

    return new_review


# ==============================================================================
# GET REVIEW BY ORDER ID
# ==============================================================================

@router.get(
    "/order/{order_id}",
    response_model=ReviewResponse,
    summary="Obtener reseña de un pedido"
)
async def get_order_review(
    order_id: int,
    db: Session = Depends(get_db)
):
    """Obtener la reseña de un pedido específico"""
    logger.info(f"Consultando reseña del pedido {order_id}")

    review = db.query(Review).filter(Review.order_id == order_id).first()

    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontró reseña para este pedido"
        )

    return review


# ==============================================================================
# GET MY REVIEWS
# ==============================================================================

@router.get(
    "/my-reviews",
    response_model=List[ReviewResponse],
    summary="Obtener mis reseñas"
)
async def get_my_reviews(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100)
):
    """Obtener todas las reseñas del usuario actual"""
    logger.info(f"Obteniendo reseñas del usuario {current_user.id}")

    reviews = db.query(Review).filter(
        Review.user_id == current_user.id
    ).order_by(Review.created_at.desc()).offset(skip).limit(limit).all()

    return reviews


# ==============================================================================
# GET REVIEWS FOR PRODUCT
# ==============================================================================

@router.get(
    "/product/{product_id}",
    response_model=List[ReviewWithUser],
    summary="Obtener reseñas de un producto"
)
async def get_product_reviews(
    product_id: int,
    db: Session = Depends(get_db),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    min_rating: Optional[float] = Query(default=None, ge=1.0, le=5.0)
):
    """
    Obtener todas las reseñas de un producto específico.

    Busca en todos los pedidos que incluyen este producto y retorna sus reseñas.
    """
    logger.info(f"Obteniendo reseñas del producto {product_id}")

    # Importar aquí para evitar referencias circulares
    from ..models.order import OrderItem

    # Buscar todos los order_items que contienen este producto
    order_items = db.query(OrderItem).filter(
        OrderItem.product_id == product_id
    ).all()

    # Obtener los order_ids
    order_ids = [item.order_id for item in order_items]

    if not order_ids:
        return []

    # Buscar las reseñas de esos pedidos
    query = db.query(Review, User).join(User, Review.user_id == User.id).filter(
        Review.order_id.in_(order_ids)
    )

    if min_rating:
        query = query.filter(Review.rating >= min_rating)

    query = query.order_by(Review.created_at.desc())

    results = query.offset(skip).limit(limit).all()

    # Formatear respuesta
    reviews_with_user = []
    for review, user in results:
        reviews_with_user.append(ReviewWithUser(
            id=review.id,
            user_name=user.name,
            user_id=user.id,
            rating=review.rating,
            food_quality=review.food_quality,
            delivery_time=review.delivery_time,
            service=review.service,
            comment=review.comment,
            image_url=review.image_url,
            created_at=review.created_at
        ))

    logger.info(f"Encontradas {len(reviews_with_user)} reseñas para el producto {product_id}")

    return reviews_with_user


# ==============================================================================
# UPLOAD REVIEW IMAGE
# ==============================================================================

@router.post(
    "/upload-image",
    response_model=UploadImageResponse,
    summary="Subir imagen de reseña"
)
async def upload_review_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """
    Subir una imagen para adjuntar a una reseña.

    Formatos permitidos: JPG, JPEG, PNG
    Tamaño máximo: 5MB
    """
    logger.info(f"Usuario {current_user.id} subiendo imagen de reseña")

    # Validar tipo de archivo
    allowed_types = ["image/jpeg", "image/jpg", "image/png"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tipo de archivo no permitido. Use JPG o PNG"
        )

    # Validar tamaño (5MB)
    file.file.seek(0, 2)  # Ir al final del archivo
    file_size = file.file.tell()  # Obtener posición (tamaño)
    file.file.seek(0)  # Regresar al inicio

    if file_size > 5 * 1024 * 1024:  # 5MB
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo es demasiado grande. Máximo 5MB"
        )

    # Generar nombre único
    file_extension = file.filename.split(".")[-1]
    unique_filename = f"{uuid.uuid4()}.{file_extension}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)

    # Guardar archivo
    try:
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)

        logger.info(f"Imagen guardada: {file_path}")

        # Retornar URL (ajustar según configuración de servidor)
        image_url = f"/uploads/reviews/{unique_filename}"

        return UploadImageResponse(
            success=True,
            image_url=image_url,
            message="Imagen subida exitosamente"
        )

    except Exception as e:
        logger.error(f"Error al guardar imagen: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al guardar la imagen"
        )


# ==============================================================================
# DELETE REVIEW (OPTIONAL - ADMIN ONLY)
# ==============================================================================

@router.delete(
    "/{review_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar reseña (Admin)"
)
async def delete_review(
    review_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Eliminar una reseña (solo el autor o administrador).
    """
    logger.info(f"Eliminando reseña {review_id}")

    review = db.query(Review).filter(Review.id == review_id).first()

    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reseña no encontrada"
        )

    # Verificar permisos (solo el autor puede eliminar su reseña)
    if review.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para eliminar esta reseña"
        )

    db.delete(review)
    db.commit()

    logger.info(f"Reseña {review_id} eliminada exitosamente")

    return None


# ==============================================================================
# GET AVERAGE RATING FOR PRODUCT
# ==============================================================================

@router.get(
    "/product/{product_id}/average",
    summary="Obtener rating promedio de un producto"
)
async def get_product_average_rating(
    product_id: int,
    db: Session = Depends(get_db)
):
    """
    Calcular el rating promedio de un producto.

    Retorna:
    - average_rating: Promedio general
    - total_reviews: Cantidad de reseñas
    - rating_distribution: Distribución por estrellas
    """
    logger.info(f"Calculando rating promedio del producto {product_id}")

    from ..models.order import OrderItem
    from sqlalchemy import func

    # Buscar todos los order_items que contienen este producto
    order_items = db.query(OrderItem).filter(
        OrderItem.product_id == product_id
    ).all()

    order_ids = [item.order_id for item in order_items]

    if not order_ids:
        return {
            "product_id": product_id,
            "average_rating": 0.0,
            "total_reviews": 0,
            "rating_distribution": {
                "5": 0, "4": 0, "3": 0, "2": 0, "1": 0
            }
        }

    # Obtener todas las reseñas
    reviews = db.query(Review).filter(Review.order_id.in_(order_ids)).all()

    if not reviews:
        return {
            "product_id": product_id,
            "average_rating": 0.0,
            "total_reviews": 0,
            "rating_distribution": {
                "5": 0, "4": 0, "3": 0, "2": 0, "1": 0
            }
        }

    # Calcular promedio
    total_rating = sum(r.rating for r in reviews)
    average_rating = round(total_rating / len(reviews), 2)

    # Distribución de ratings
    distribution = {"5": 0, "4": 0, "3": 0, "2": 0, "1": 0}
    for review in reviews:
        rounded_rating = round(review.rating)
        distribution[str(rounded_rating)] += 1

    return {
        "product_id": product_id,
        "average_rating": average_rating,
        "total_reviews": len(reviews),
        "rating_distribution": distribution
    }
