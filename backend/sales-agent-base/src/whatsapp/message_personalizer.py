"""
================================================================================
MESSAGE PERSONALIZER
================================================================================
Personaliza mensajes de WhatsApp según el historial y preferencias del cliente.

Personalización incluye:
- Usar el nombre del cliente
- Mencionar productos favoritos
- Adaptar tono según frecuencia de visitas
- Incluir recomendaciones personalizadas
================================================================================
"""

import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class MessagePersonalizer:
    """
    Personaliza mensajes para cada cliente según su historial.

    Transforma mensajes genéricos en mensajes personalizados que
    aumentan la tasa de conversión.
    """

    def personalize(
        self,
        message_template: str,
        customer: Dict,
        promotion: Optional[Dict] = None
    ) -> str:
        """
        Personaliza un mensaje para un cliente específico.

        Args:
            message_template: Template del mensaje
            customer: Datos del cliente
            promotion: Datos de la promoción (opcional)

        Returns:
            Mensaje personalizado
        """
        customer_name = customer.get('name', 'Cliente')
        order_count = customer.get('order_count', 0)
        favorite_products = customer.get('preferences', {}).get('favorite_products', [])

        # Construir saludo personalizado
        greeting = self._get_personalized_greeting(customer_name, order_count)

        # Construir mensaje
        personalized = f"{greeting}\n\n{message_template}"

        # Si hay promoción y el cliente tiene productos favoritos relevantes
        if promotion and favorite_products:
            relevant_products = self._check_promotion_relevance(promotion, favorite_products)
            if relevant_products:
                personalized += f"\n\n💡 Tip: Esta promo aplica a tu favorito: {relevant_products[0]}"

        # Agregar CTA personalizado
        cta = self._get_personalized_cta(order_count)
        personalized += f"\n\n{cta}"

        return personalized

    def _get_personalized_greeting(self, name: str, order_count: int) -> str:
        """Genera saludo personalizado según historial"""
        if order_count == 0:
            return f"¡Hola {name}! 👋"
        elif order_count == 1:
            return f"¡Hola de nuevo {name}! 👋"
        elif order_count < 5:
            return f"¡Hola {name}! 🌮"
        elif order_count < 10:
            return f"¡Hola {name}! Es un gusto verte de nuevo 😊"
        else:
            return f"¡Hola {name}! ⭐ Nuestro cliente especial está de vuelta"

    def _get_personalized_cta(self, order_count: int) -> str:
        """Genera call-to-action personalizado"""
        if order_count == 0:
            return "¿Te animas a probar nuestra comida?"
        elif order_count < 3:
            return "¿Quieres ordenar de nuevo?"
        elif order_count < 10:
            return "¿Quieres tu platillo favorito?"
        else:
            return "¿Lo de siempre? 😊"

    def _check_promotion_relevance(
        self,
        promotion: Dict,
        favorite_products: list
    ) -> list:
        """
        Verifica si la promoción es relevante para los productos favoritos.

        Returns:
            Lista de productos favoritos incluidos en la promoción
        """
        # TODO: Implementar lógica real según estructura de promociones
        # Por ahora retornamos el primer favorito si hay promoción
        if promotion and favorite_products:
            return [favorite_products[0]]
        return []

    def personalize_order_confirmation(
        self,
        customer: Dict,
        order_items: list,
        total: float
    ) -> str:
        """Personaliza mensaje de confirmación de pedido"""
        name = customer.get('name', 'Cliente')
        order_count = customer.get('order_count', 0)

        message = f"¡Gracias {name}! 🙌\n\n"
        message += "Tu pedido está confirmado:\n\n"

        # Listar items
        for item in order_items:
            qty = item.get('quantity', 1)
            product_name = item.get('name', 'Producto')
            message += f"• {qty}x {product_name}\n"

        message += f"\n*Total: ${total:.2f}*\n\n"

        # Mensaje según historial
        if order_count >= 5:
            message += "Como siempre, preparado con el mejor cuidado para ti ❤️"
        elif order_count >= 3:
            message += "¡Ya casi eres parte de la familia! 🌮"
        else:
            message += "Preparándolo con mucho cariño 😊"

        message += "\n\nTe avisaremos cuando esté listo."

        return message

    def personalize_upsell_suggestion(
        self,
        customer: Dict,
        current_cart: list,
        suggested_product: Dict
    ) -> str:
        """Personaliza sugerencia de upsell"""
        name = customer.get('name', 'Cliente')
        product_name = suggested_product.get('name', 'este producto')
        price = suggested_product.get('price', 0)

        # Verificar si es favorito
        favorite_products = customer.get('preferences', {}).get('favorite_products', [])
        product_id = suggested_product.get('id', '')

        if product_id in favorite_products:
            message = f"{name}, ¿quieres agregar tu favorito {product_name}? (${price})"
        else:
            message = f"¿Te gustaría agregar {product_name} por solo ${price}?"

        return message


# Singleton
_message_personalizer = None


def get_message_personalizer() -> MessagePersonalizer:
    """Obtiene instancia singleton del MessagePersonalizer"""
    global _message_personalizer
    if _message_personalizer is None:
        _message_personalizer = MessagePersonalizer()
    return _message_personalizer
