"""
================================================================================
REVIEW MODEL
================================================================================
Modelo para reseñas y calificaciones de pedidos
================================================================================
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..database import Base


class Review(Base):
    """Reseña de un pedido"""

    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, unique=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Calificaciones individuales (1-5)
    food_quality = Column(Integer, nullable=False)      # Calidad de la comida
    delivery_time = Column(Integer, nullable=False)     # Tiempo de entrega
    service = Column(Integer, nullable=False)           # Servicio general

    # Rating promedio calculado
    rating = Column(Float, nullable=False)  # Promedio de los 3 anteriores

    # Comentarios
    comment = Column(Text, nullable=True)

    # Imagen opcional
    image_url = Column(String(500), nullable=True)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relaciones
    order = relationship("Order", back_populates="review")
    user = relationship("User", back_populates="reviews")

    def __repr__(self):
        return f"<Review Order#{self.order_id} - {self.rating}⭐>"

    def to_dict(self):
        """Convertir a diccionario"""
        return {
            "id": self.id,
            "order_id": self.order_id,
            "user_id": self.user_id,
            "food_quality": self.food_quality,
            "delivery_time": self.delivery_time,
            "service": self.service,
            "rating": self.rating,
            "comment": self.comment,
            "image_url": self.image_url,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
