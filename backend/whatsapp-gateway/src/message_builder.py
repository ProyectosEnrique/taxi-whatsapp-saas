"""
================================================================================
MESSAGE BUILDER - Templates Optimizados
================================================================================
Construye mensajes optimizados con botones interactivos para WhatsApp
================================================================================
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import logging

from .hybrid_session import DerivarReason

logger = logging.getLogger(__name__)


# ==============================================================================
# MESSAGE TEMPLATES
# ==============================================================================

@dataclass
class InteractiveButton:
    """Botón interactivo de WhatsApp"""
    id: str
    title: str  # Max 20 caracteres


@dataclass
class WhatsAppMessage:
    """Mensaje de WhatsApp con componentes opcionales"""
    text: str
    buttons: Optional[List[InteractiveButton]] = None
    url_button: Optional[Dict[str, str]] = None  # {"text": "Ver Menú", "url": "..."}


class MessageBuilder:
    """
    Constructor de mensajes optimizados para el flujo híbrido.

    Genera mensajes con:
    - Copy optimizado para conversión
    - Botones interactivos
    - URLs de redirección elegantes
    """

    def __init__(self):
        pass

    # ==========================================================================
    # MENSAJES DE BIENVENIDA
    # ==========================================================================

    def build_greeting_message(
        self,
        customer_name: str = "Cliente",
        is_returning: bool = False,
        promotions: List[Dict[str, Any]] = None
    ) -> WhatsAppMessage:
        """
        Mensaje de bienvenida inicial.
        """
        if is_returning:
            text = f"¡Hola de nuevo, {customer_name}! 👋\n\n"
        else:
            text = f"¡Hola {customer_name}! Bienvenido 👋\n\n"

        # Mostrar promociones si hay
        if promotions:
            text += "🔥 *Promociones de HOY:*\n"
            for promo in promotions[:2]:  # Max 2 promos
                text += f"• {promo['name']} - ${promo['price']}\n"
            text += "\n"

        text += "¿Qué te antoja hoy?\n"
        text += "Puedo ayudarte a hacer un pedido rápido o mostrarte el menú completo 📸"

        buttons = [
            InteractiveButton(id="quick_order", title="🍽️ Pedir Rápido"),
            InteractiveButton(id="see_menu", title="📋 Ver Menú"),
        ]

        if promotions:
            buttons.append(InteractiveButton(id="see_promos", title="🔥 Ver Promos"))

        return WhatsAppMessage(text=text, buttons=buttons[:3])  # Max 3 buttons

    def build_initial_message_with_recommendations(
        self,
        customer_name: str = "",
        is_returning: bool = False,
        promotions: List[Dict[str, Any]] = None,
        chef_recommendations: List[Dict[str, Any]] = None
    ) -> WhatsAppMessage:
        """
        Mensaje inicial MEJORADO con recomendaciones del Chef + promociones.

        Este es el mensaje que se envía automáticamente cuando el usuario
        dice "Hola" por primera vez.

        Args:
            customer_name: Nombre del cliente
            is_returning: Si es cliente que regresa
            promotions: Lista de promociones activas
            chef_recommendations: Recomendaciones del chef

        Returns:
            WhatsAppMessage con texto + botones
        """
        # Saludo
        if is_returning and customer_name:
            text = f"¡Hola de nuevo, {customer_name}! 👋\n"
        elif customer_name:
            text = f"¡Hola {customer_name}! 👋\n"
        else:
            text = "¡Hola! 👋 Soy tu mesero virtual.\n"

        text += "\n"

        # PROMOCIONES (si hay)
        if promotions and len(promotions) > 0:
            text += "🔥 *PROMOCIONES HOY:*\n"
            for promo in promotions[:2]:  # Max 2 promociones
                name = promo.get("name", "Producto")
                price = promo.get("price", 0)
                original_price = promo.get("original_price")

                text += f"• {name} - ${price:.2f}"
                if original_price:
                    discount = int(((original_price - price) / original_price) * 100)
                    text += f" (ahorra ${original_price - price:.2f})"
                text += "\n"
            text += "\n"

        # RECOMENDACIONES DEL CHEF (si hay)
        if chef_recommendations and len(chef_recommendations) > 0:
            text += "⭐ *RECOMENDACIÓN DEL CHEF:*\n"
            for rec in chef_recommendations[:1]:  # Solo 1 recomendación principal
                name = rec.get("name", "Platillo especial")
                price = rec.get("price")
                description = rec.get("description", "")

                text += f"• {name}"
                if price:
                    text += f" - ${price:.2f}"
                text += "\n"
                if description:
                    text += f"  _{description[:60]}..._\n"
            text += "\n"

        # Call to action
        text += "¿Qué te gustaría ordenar?"

        # Botones
        buttons = [
            InteractiveButton(id="ver_promos", title="🔥 Ver promociones"),
            InteractiveButton(id="hacer_pedido", title="💬 Hacer pedido"),
            InteractiveButton(id="ver_menu_web", title="📋 Ver menú completo")
        ]

        return WhatsAppMessage(text=text, buttons=buttons)

    # ==========================================================================
    # MENSAJES DE DERIVACIÓN A WEB
    # ==========================================================================

    def build_redirect_to_web_message(
        self,
        reason: DerivarReason,
        web_url: str,
        cart_size: int = 0
    ) -> WhatsAppMessage:
        """
        Mensaje para derivar a web de forma elegante.
        """
        messages_by_reason = {
            DerivarReason.BROWSING_DETECTED: {
                "text": (
                    "Perfecto! Para que veas *TODO el menú con fotos* 📸\n\n"
                    "Te abro nuestro menú interactivo donde puedes:\n"
                    "✅ Ver fotos de cada platillo\n"
                    "✅ Leer ingredientes y descripciones\n"
                    "✅ Filtrar por tipo de comida\n"
                    "✅ Armar tu pedido visualmente\n\n"
                    "Cuando termines, vuelves aquí para confirmar 👍"
                ),
                "button_text": "📸 Abrir Menú Visual"
            },

            DerivarReason.NEEDS_VISUAL: {
                "text": (
                    "¡Te entiendo! Es más fácil decidir viendo fotos 😊\n\n"
                    "Te muestro nuestro menú interactivo con:\n"
                    "📸 Fotos en alta calidad\n"
                    "⭐ Recomendaciones del chef\n"
                    "💡 Lo más popular\n\n"
                    "Explora tranquilo y cuando elijas, vuelves aquí para confirmar"
                ),
                "button_text": "🍽️ Ver con Fotos"
            },

            DerivarReason.COMPLEX_ORDER: {
                "text": (
                    f"Veo que vas armando un buen pedido! ({cart_size} items) 🛒\n\n"
                    "Para que lo personalices mejor, te abro la web donde puedes:\n"
                    "✅ Ver el carrito actualizado\n"
                    "✅ Editar cantidades fácilmente\n"
                    "✅ Agregar notas especiales\n"
                    "✅ Ver el total en tiempo real\n\n"
                    "Cuando estés listo, vuelves para confirmar"
                ),
                "button_text": "🛒 Ver Mi Carrito"
            },

            DerivarReason.CONVERSATION_TOO_LONG: {
                "text": (
                    "Mejor te muestro el menú completo con fotos! 😊\n\n"
                    "Será más fácil que elijas viendo las opciones:\n"
                    "📸 Fotos de todos los platillos\n"
                    "🏷️ Precios y descripciones\n"
                    "⭐ Reviews de otros clientes\n\n"
                    "Navega tranquilo, yo te espero aquí para confirmar"
                ),
                "button_text": "📱 Abrir Menú"
            },

            DerivarReason.CUSTOMIZATION_NEEDED: {
                "text": (
                    "Para personalizar mejor tu pedido, te abro la web 🎨\n\n"
                    "Ahí puedes:\n"
                    "✅ Elegir ingredientes\n"
                    "✅ Nivel de picante\n"
                    "✅ Agregar extras\n"
                    "✅ Notas especiales\n\n"
                    "Arma tu pedido perfecto y vuelves para confirmar 👌"
                ),
                "button_text": "✨ Personalizar"
            },

            DerivarReason.USER_REQUESTED: {
                "text": (
                    "¡Claro! Te abro el menú completo 📱\n\n"
                    "Explora todas las opciones con fotos y descripciones.\n"
                    "Cuando termines, vuelves aquí para confirmar tu pedido."
                ),
                "button_text": "🍽️ Ver Menú"
            }
        }

        template = messages_by_reason.get(reason, messages_by_reason[DerivarReason.BROWSING_DETECTED])

        return WhatsAppMessage(
            text=template["text"],
            url_button={"text": template["button_text"], "url": web_url}
        )

    # ==========================================================================
    # MENSAJES DE RETORNO DESDE WEB
    # ==========================================================================

    def build_welcome_back_message(
        self,
        cart: List[Dict[str, Any]],
        total: float,
        time_on_web_seconds: int
    ) -> WhatsAppMessage:
        """
        Mensaje cuando usuario regresa de web con carrito.
        """
        cart_summary = self._format_cart(cart)

        time_msg = ""
        if time_on_web_seconds < 60:
            time_msg = "¡Eso fue rápido!"
        elif time_on_web_seconds < 300:
            time_msg = "¡Perfecto!"
        else:
            time_msg = "¡Bienvenido de vuelta!"

        text = f"{time_msg} Vi que armaste tu pedido 🛒\n\n"
        text += cart_summary
        text += f"\n💰 *Total: ${total:.2f}*\n\n"
        text += "¿Confirmamos este pedido?"

        buttons = [
            InteractiveButton(id="confirm_order", title="✅ Confirmar"),
            InteractiveButton(id="edit_cart", title="✏️ Editar"),
        ]

        return WhatsAppMessage(text=text, buttons=buttons)

    # ==========================================================================
    # MENSAJES DE PROMOCIONES
    # ==========================================================================

    def build_promotions_message(
        self,
        promotions: List[Dict[str, Any]]
    ) -> WhatsAppMessage:
        """
        Mensaje de promociones del día.
        """
        text = "🔥 *PROMOCIONES DE HOY* 🔥\n\n"

        for promo in promotions[:5]:  # Max 5 promos
            name = promo.get("name", "Producto")
            price = promo.get("price", 0)
            original_price = promo.get("original_price")
            discount = promo.get("discount_percent")

            text += f"• *{name}*\n"
            text += f"  ${price:.2f}"

            if original_price:
                text += f" ~~${original_price:.2f}~~"
            if discount:
                text += f" ({discount}% OFF)"

            text += "\n\n"

        text += "_¿Te interesa alguna?_"

        buttons = [
            InteractiveButton(id="order_promo", title="🍽️ Pedir"),
            InteractiveButton(id="see_full_menu", title="📋 Ver Todo"),
        ]

        return WhatsAppMessage(text=text, buttons=buttons)

    # ==========================================================================
    # MENSAJES DE RECOMENDACIONES
    # ==========================================================================

    def build_recommendation_message(
        self,
        recommendations: List[Dict[str, Any]],
        reason: str = "popular"  # "popular", "chef", "similar", "personalized"
    ) -> WhatsAppMessage:
        """
        Mensaje con recomendaciones.
        """
        headers = {
            "popular": "⭐ *LO MÁS POPULAR* ⭐",
            "chef": "👨‍🍳 *RECOMENDACIÓN DEL CHEF* 👨‍🍳",
            "similar": "💡 *TE PUEDE INTERESAR* 💡",
            "personalized": "🎯 *ESPECIAL PARA TI* 🎯"
        }

        text = headers.get(reason, headers["popular"]) + "\n\n"

        for rec in recommendations[:3]:  # Max 3 recomendaciones
            name = rec.get("name", "Producto")
            price = rec.get("price", 0)
            rating = rec.get("rating", 0)
            description = rec.get("description", "")

            text += f"• *{name}* - ${price:.2f}\n"
            if rating:
                stars = "⭐" * int(rating)
                text += f"  {stars} ({rating}/5)\n"
            if description:
                text += f"  _{description[:50]}..._\n"
            text += "\n"

        text += "¿Qué te antoja?"

        buttons = [
            InteractiveButton(id="order_rec", title="🍽️ Pedir Esto"),
            InteractiveButton(id="see_more", title="📸 Ver Más"),
        ]

        return WhatsAppMessage(text=text, buttons=buttons)

    def build_what_do_you_recommend_response(
        self,
        promotions: List[Dict[str, Any]] = None,
        chef_recommendations: List[Dict[str, Any]] = None,
        popular_items: List[Dict[str, Any]] = None
    ) -> WhatsAppMessage:
        """
        Respuesta mejorada para "qué me recomiendas".

        IMPORTANTE: NO deriva a web automáticamente.
        Muestra recomendaciones + botones para que el USUARIO decida.

        Args:
            promotions: Promociones activas
            chef_recommendations: Recomendaciones del chef
            popular_items: Platillos más populares

        Returns:
            WhatsAppMessage con recomendaciones + botones de decisión
        """
        text = "¡Gran pregunta! 🤔\n\n"

        # Mostrar promociones primero (son la mejor oferta)
        if promotions and len(promotions) > 0:
            text += "🔥 *LO MÁS VENDIDO HOY:*\n"
            for promo in promotions[:2]:
                name = promo.get("name", "Producto")
                price = promo.get("price", 0)
                text += f"• {name} - ${price:.2f}\n"
            text += "\n"

        # Recomendación del chef
        if chef_recommendations and len(chef_recommendations) > 0:
            text += "⭐ *RECOMENDACIÓN DEL CHEF:*\n"
            rec = chef_recommendations[0]
            name = rec.get("name", "Platillo especial")
            price = rec.get("price", 0)
            text += f"• {name} - ${price:.2f}\n\n"

        # Si no hay nada, mostrar populares
        if not promotions and not chef_recommendations and popular_items:
            text += "⭐ *LO MÁS POPULAR:*\n"
            for item in popular_items[:2]:
                name = item.get("name", "Producto")
                price = item.get("price", 0)
                text += f"• {name} - ${price:.2f}\n"
            text += "\n"

        text += "¿Prefieres ver el menú completo con fotos o te ayudo a armar tu pedido?"

        # Botones: usuario DECIDE si quiere ir a web
        buttons = [
            InteractiveButton(id="ayuda_pedido", title="💬 Ayúdame a elegir"),
            InteractiveButton(id="ver_promos", title="🔥 Ver promociones"),
            InteractiveButton(id="ver_menu_fotos", title="📸 Menú con fotos")
        ]

        return WhatsAppMessage(text=text, buttons=buttons)

    # ==========================================================================
    # MENSAJES DE PEDIDO RÁPIDO
    # ==========================================================================

    def build_quick_order_confirmation(
        self,
        cart: List[Dict[str, Any]],
        total: float
    ) -> WhatsAppMessage:
        """
        Confirmación de pedido rápido.
        """
        cart_summary = self._format_cart(cart)

        text = "✅ *Pedido Agregado!*\n\n"
        text += cart_summary
        text += f"\n💰 *Total: ${total:.2f}*\n\n"
        text += "¿Deseas algo más o confirmamos?"

        buttons = [
            InteractiveButton(id="confirm", title="✅ Confirmar"),
            InteractiveButton(id="add_more", title="➕ Agregar Más"),
        ]

        return WhatsAppMessage(text=text, buttons=buttons)

    # ==========================================================================
    # HELPERS
    # ==========================================================================

    def _format_cart(self, cart: List[Dict[str, Any]]) -> str:
        """Formatear carrito para mostrar"""
        if not cart:
            return "_Carrito vacío_"

        text = "*Tu pedido:*\n"
        for item in cart:
            name = item.get("name", "Item")
            qty = item.get("quantity", 1)
            price = item.get("price", 0)
            subtotal = price * qty

            text += f"• {name} x{qty} - ${subtotal:.2f}\n"

            # Notas especiales
            notes = item.get("notes")
            if notes:
                text += f"  _({notes})_\n"

        return text


# ==============================================================================
# META WHATSAPP FORMATTER
# ==============================================================================

class MetaWhatsAppFormatter:
    """
    Formatea mensajes para Meta WhatsApp Business API.
    """

    @staticmethod
    def format_interactive_buttons(message: WhatsAppMessage) -> Dict[str, Any]:
        """
        Formatear mensaje con botones interactivos para Meta API.
        """
        if not message.buttons:
            return {
                "type": "text",
                "text": {"body": message.text}
            }

        # Formato de Meta para botones
        payload = {
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {"text": message.text},
                "action": {
                    "buttons": [
                        {
                            "type": "reply",
                            "reply": {
                                "id": btn.id,
                                "title": btn.title[:20]  # Max 20 chars
                            }
                        }
                        for btn in message.buttons[:3]  # Max 3 buttons
                    ]
                }
            }
        }

        return payload

    @staticmethod
    def format_url_button(message: WhatsAppMessage) -> Dict[str, Any]:
        """
        Formatear mensaje con botón de URL (para derivar a web).

        NOTA: Meta no soporta URL buttons directamente.
        Workaround: Enviar texto con link acortado (solo dominio).
        """
        text = message.text

        # Agregar solo dominio en vez de URL completa
        if message.url_button:
            button_text = message.url_button["text"]
            url = message.url_button["url"]

            # Extraer solo el dominio base
            from urllib.parse import urlparse
            parsed = urlparse(url)
            short_url = f"{parsed.scheme}://{parsed.netloc}"

            text += f"\n\n👉 {button_text}:\n{short_url}"

        return {
            "type": "text",
            "text": {"body": text}
        }


# ==============================================================================
# EXAMPLE USAGE
# ==============================================================================

if __name__ == "__main__":
    builder = MessageBuilder()

    # Test: Mensaje de derivación a web
    print("=" * 80)
    print("MENSAJE DE DERIVACIÓN A WEB")
    print("=" * 80)
    msg = builder.build_redirect_to_web_message(
        reason=DerivarReason.BROWSING_DETECTED,
        web_url="https://turestaurante.com/menu?st=abc123",
        cart_size=2
    )
    print(msg.text)
    print()

    # Test: Mensaje de retorno
    print("=" * 80)
    print("MENSAJE DE BIENVENIDA DE REGRESO")
    print("=" * 80)
    msg = builder.build_welcome_back_message(
        cart=[
            {"name": "Tacos al Pastor", "quantity": 3, "price": 110.0},
            {"name": "Refresco", "quantity": 2, "price": 25.0, "notes": "Sin hielo"}
        ],
        total=380.0,
        time_on_web_seconds=120
    )
    print(msg.text)
    print(f"Botones: {[b.title for b in msg.buttons]}")
    print()

    # Test: Formatear para Meta API
    print("=" * 80)
    print("FORMATO PARA META API")
    print("=" * 80)
    formatter = MetaWhatsAppFormatter()
    payload = formatter.format_interactive_buttons(msg)
    import json
    print(json.dumps(payload, indent=2, ensure_ascii=False))
