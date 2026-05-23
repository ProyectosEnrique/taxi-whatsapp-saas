"""
================================================================================
WHATSAPP CLIENT
================================================================================
Cliente para enviar mensajes de WhatsApp via Twilio o Meta Cloud API.
================================================================================
"""

from typing import Optional, List, Dict, Any
import aiohttp
import logging
import os

logger = logging.getLogger(__name__)


class WhatsAppClient:
    """
    Cliente para enviar mensajes de WhatsApp.

    Soporta:
    - Twilio WhatsApp API
    - Meta Cloud API (WhatsApp Business)

    Características:
    - Mensajes de texto
    - Mensajes con botones
    - Listas interactivas
    - Imágenes
    - Multi-Product Messages (catálogo)
    - Single Product Messages (catálogo)
    """

    def __init__(self):
        self.provider = os.getenv("WHATSAPP_PROVIDER", "twilio")

        # Twilio config
        self.twilio_sid = os.getenv("TWILIO_ACCOUNT_SID", "")
        self.twilio_token = os.getenv("TWILIO_AUTH_TOKEN", "")
        self.twilio_number = os.getenv("TWILIO_WHATSAPP_NUMBER", "")

        # Meta config
        self.meta_phone_id = os.getenv("META_PHONE_NUMBER_ID", "")
        self.meta_token = os.getenv("META_ACCESS_TOKEN", "")
        self.meta_catalog_id = os.getenv("META_CATALOG_ID", "")

        self.timeout = aiohttp.ClientTimeout(total=30)

    @property
    def has_catalog(self) -> bool:
        """Verificar si el catálogo está configurado"""
        return bool(self.meta_catalog_id and self.provider == "meta")

    async def send_message(
        self,
        to: str,
        message: str,
        buttons: Optional[List[Dict[str, str]]] = None,
        list_items: Optional[List[Dict[str, Any]]] = None,
        image_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Enviar mensaje de WhatsApp.

        Args:
            to: Número de teléfono destino
            message: Texto del mensaje
            buttons: Lista de botones [{"id": "1", "title": "Opción 1"}, ...]
            list_items: Lista interactiva
            image_url: URL de imagen a enviar

        Returns:
            Dict con resultado del envío
        """
        if self.provider == "twilio":
            return await self._send_twilio(to, message, buttons, image_url)
        elif self.provider == "meta":
            return await self._send_meta(to, message, buttons, list_items, image_url)
        else:
            raise ValueError(f"Proveedor no soportado: {self.provider}")

    async def _send_twilio(
        self,
        to: str,
        message: str,
        buttons: Optional[List[Dict[str, str]]] = None,
        image_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Enviar mensaje via Twilio"""
        url = f"https://api.twilio.com/2010-04-01/Accounts/{self.twilio_sid}/Messages.json"

        # Formatear mensaje con botones (Twilio no soporta botones nativos)
        formatted_message = message
        if buttons:
            formatted_message += "\n\n"
            for i, btn in enumerate(buttons, 1):
                formatted_message += f"{i}️⃣ {btn.get('title', btn.get('id', ''))}\n"
            formatted_message += "\n_Responde con el número de tu opción_"

        # Formatear número
        to_formatted = to if to.startswith("+") else f"+{to}"

        data = {
            "From": f"whatsapp:{self.twilio_number}",
            "To": f"whatsapp:{to_formatted}",
            "Body": formatted_message
        }

        if image_url:
            data["MediaUrl"] = image_url

        auth = aiohttp.BasicAuth(self.twilio_sid, self.twilio_token)

        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.post(url, data=data, auth=auth) as response:
                result = await response.json()

                if response.status >= 400:
                    logger.error(f"[Twilio] Error: {result}")
                    return {"success": False, "error": result}

                logger.info(f"[Twilio] Mensaje enviado: {result.get('sid')}")
                return {
                    "success": True,
                    "message_id": result.get("sid"),
                    "status": result.get("status")
                }

    async def _send_meta(
        self,
        to: str,
        message: str,
        buttons: Optional[List[Dict[str, str]]] = None,
        list_items: Optional[List[Dict[str, Any]]] = None,
        image_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Enviar mensaje via Meta Cloud API"""
        url = f"https://graph.facebook.com/v18.0/{self.meta_phone_id}/messages"

        headers = {
            "Authorization": f"Bearer {self.meta_token}",
            "Content-Type": "application/json"
        }

        # Construir payload según tipo de mensaje
        if buttons and len(buttons) <= 3:
            # Mensaje con botones (máximo 3)
            payload = self._build_button_message(to, message, buttons)
        elif list_items:
            # Lista interactiva
            payload = self._build_list_message(to, message, list_items)
        elif image_url:
            # Mensaje con imagen
            payload = self._build_image_message(to, message, image_url)
        else:
            # Mensaje de texto simple
            payload = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": to,
                "type": "text",
                "text": {"body": message}
            }

        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.post(url, json=payload, headers=headers) as response:
                result = await response.json()

                if response.status >= 400:
                    logger.error(f"[Meta] Error: {result}")
                    return {"success": False, "error": result}

                message_id = result.get("messages", [{}])[0].get("id")
                logger.info(f"[Meta] Mensaje enviado: {message_id}")

                return {
                    "success": True,
                    "message_id": message_id
                }

    def _build_button_message(
        self,
        to: str,
        message: str,
        buttons: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """Construir mensaje con botones para Meta"""
        return {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {"text": message},
                "action": {
                    "buttons": [
                        {
                            "type": "reply",
                            "reply": {
                                "id": btn.get("id", str(i)),
                                "title": btn.get("title", "")[:20]  # Max 20 chars
                            }
                        }
                        for i, btn in enumerate(buttons[:3])  # Max 3 buttons
                    ]
                }
            }
        }

    def _build_list_message(
        self,
        to: str,
        message: str,
        list_items: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Construir lista interactiva para Meta"""
        sections = []

        for section in list_items:
            rows = [
                {
                    "id": item.get("id", str(i)),
                    "title": item.get("title", "")[:24],  # Max 24 chars
                    "description": item.get("description", "")[:72]  # Max 72 chars
                }
                for i, item in enumerate(section.get("items", []))
            ]
            sections.append({
                "title": section.get("title", "Opciones")[:24],
                "rows": rows[:10]  # Max 10 items per section
            })

        return {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "interactive",
            "interactive": {
                "type": "list",
                "body": {"text": message},
                "action": {
                    "button": "Ver opciones",
                    "sections": sections[:10]  # Max 10 sections
                }
            }
        }

    def _build_image_message(
        self,
        to: str,
        caption: str,
        image_url: str
    ) -> Dict[str, Any]:
        """Construir mensaje con imagen para Meta"""
        return {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "image",
            "image": {
                "link": image_url,
                "caption": caption
            }
        }

    async def send_template(
        self,
        to: str,
        template_name: str,
        language: str = "es",
        components: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Enviar mensaje de plantilla (solo Meta).
        Útil para mensajes fuera de la ventana de 24h.
        """
        if self.provider != "meta":
            logger.warning("Templates solo soportados en Meta")
            return {"success": False, "error": "Templates only supported on Meta"}

        url = f"https://graph.facebook.com/v18.0/{self.meta_phone_id}/messages"

        headers = {
            "Authorization": f"Bearer {self.meta_token}",
            "Content-Type": "application/json"
        }

        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language},
                "components": components or []
            }
        }

        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.post(url, json=payload, headers=headers) as response:
                result = await response.json()

                if response.status >= 400:
                    return {"success": False, "error": result}

                return {
                    "success": True,
                    "message_id": result.get("messages", [{}])[0].get("id")
                }

    # ==========================================================================
    # PRODUCT CATALOG MESSAGES (Meta Cloud API)
    # ==========================================================================

    async def send_multi_product_message(
        self,
        to: str,
        header_text: str,
        body_text: str,
        sections: List[Dict[str, Any]],
        footer_text: str = "",
        catalog_id: str = None
    ) -> Dict[str, Any]:
        """
        Enviar Multi-Product Message (hasta 30 productos con imágenes).

        Requiere catálogo configurado en Meta Commerce Manager.

        Args:
            to: Número de teléfono destino
            header_text: Título del mensaje (máx 60 chars)
            body_text: Descripción del mensaje (máx 1024 chars)
            sections: Lista de secciones con productos:
                [
                    {
                        "title": "Categoría",
                        "product_items": [
                            {"product_retailer_id": "prod_1"},
                            {"product_retailer_id": "prod_2"}
                        ]
                    }
                ]
            footer_text: Pie de mensaje (máx 60 chars)
            catalog_id: ID del catálogo (usa default si no se especifica)

        Returns:
            Dict con resultado del envío
        """
        catalog = catalog_id or self.meta_catalog_id

        # Fallback si no hay catálogo configurado
        if not catalog or self.provider != "meta":
            logger.warning("[WhatsApp] No catalog configured, falling back to list")
            return await self._fallback_mpm_to_list(to, header_text, body_text, sections)

        url = f"https://graph.facebook.com/v18.0/{self.meta_phone_id}/messages"

        headers = {
            "Authorization": f"Bearer {self.meta_token}",
            "Content-Type": "application/json"
        }

        # Construir payload de Multi-Product Message
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "interactive",
            "interactive": {
                "type": "product_list",
                "header": {
                    "type": "text",
                    "text": header_text[:60]
                },
                "body": {
                    "text": body_text[:1024]
                },
                "action": {
                    "catalog_id": catalog,
                    "sections": self._prepare_product_sections(sections)
                }
            }
        }

        if footer_text:
            payload["interactive"]["footer"] = {"text": footer_text[:60]}

        logger.info(f"[WhatsApp] Sending Multi-Product Message to {to}")

        return await self._send_meta_request(url, payload, headers)

    async def send_single_product_message(
        self,
        to: str,
        body_text: str,
        product_retailer_id: str,
        footer_text: str = "",
        catalog_id: str = None
    ) -> Dict[str, Any]:
        """
        Enviar Single Product Message (vista detallada de un producto).

        Muestra el producto con imagen, descripción, precio y opción de agregar al carrito.

        Args:
            to: Número de teléfono destino
            body_text: Descripción del mensaje (máx 1024 chars)
            product_retailer_id: ID del producto en el catálogo
            footer_text: Pie de mensaje (máx 60 chars)
            catalog_id: ID del catálogo

        Returns:
            Dict con resultado del envío
        """
        catalog = catalog_id or self.meta_catalog_id

        # Fallback si no hay catálogo
        if not catalog or self.provider != "meta":
            logger.warning("[WhatsApp] No catalog configured, falling back to text")
            return await self.send_message(
                to=to,
                message=f"{body_text}\n\n_Producto: {product_retailer_id}_"
            )

        url = f"https://graph.facebook.com/v18.0/{self.meta_phone_id}/messages"

        headers = {
            "Authorization": f"Bearer {self.meta_token}",
            "Content-Type": "application/json"
        }

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "interactive",
            "interactive": {
                "type": "product",
                "body": {
                    "text": body_text[:1024]
                },
                "action": {
                    "catalog_id": catalog,
                    "product_retailer_id": product_retailer_id
                }
            }
        }

        if footer_text:
            payload["interactive"]["footer"] = {"text": footer_text[:60]}

        logger.info(f"[WhatsApp] Sending Single Product Message to {to}: {product_retailer_id}")

        return await self._send_meta_request(url, payload, headers)

    async def send_catalog_message(
        self,
        to: str,
        body_text: str,
        thumbnail_product_retailer_id: str = None,
        catalog_id: str = None
    ) -> Dict[str, Any]:
        """
        Enviar mensaje de catálogo completo.

        Muestra un botón que abre el catálogo completo del negocio.

        Args:
            to: Número de teléfono destino
            body_text: Descripción (máx 1024 chars)
            thumbnail_product_retailer_id: Producto para usar como miniatura
            catalog_id: ID del catálogo

        Returns:
            Dict con resultado del envío
        """
        catalog = catalog_id or self.meta_catalog_id

        if not catalog or self.provider != "meta":
            logger.warning("[WhatsApp] No catalog configured")
            return await self.send_message(to=to, message=body_text)

        url = f"https://graph.facebook.com/v18.0/{self.meta_phone_id}/messages"

        headers = {
            "Authorization": f"Bearer {self.meta_token}",
            "Content-Type": "application/json"
        }

        action = {"name": "catalog_message"}
        if thumbnail_product_retailer_id:
            action["parameters"] = {
                "thumbnail_product_retailer_id": thumbnail_product_retailer_id
            }

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "interactive",
            "interactive": {
                "type": "catalog_message",
                "body": {"text": body_text[:1024]},
                "action": action
            }
        }

        logger.info(f"[WhatsApp] Sending Catalog Message to {to}")

        return await self._send_meta_request(url, payload, headers)

    # ==========================================================================
    # HELPER METHODS
    # ==========================================================================

    async def _send_meta_request(
        self,
        url: str,
        payload: Dict[str, Any],
        headers: Dict[str, str]
    ) -> Dict[str, Any]:
        """Helper para enviar requests a Meta API"""
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.post(url, json=payload, headers=headers) as response:
                    result = await response.json()

                    if response.status >= 400:
                        logger.error(f"[Meta] Error: {result}")
                        return {"success": False, "error": result, "status_code": response.status}

                    message_id = result.get("messages", [{}])[0].get("id")
                    logger.info(f"[Meta] Message sent: {message_id}")

                    return {"success": True, "message_id": message_id}

        except aiohttp.ClientError as e:
            logger.error(f"[Meta] Network error: {e}")
            return {"success": False, "error": str(e)}
        except Exception as e:
            logger.error(f"[Meta] Unexpected error: {e}")
            return {"success": False, "error": str(e)}

    def _prepare_product_sections(
        self,
        sections: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Preparar secciones de productos para el payload"""
        prepared = []

        for section in sections[:10]:  # Máximo 10 secciones
            product_items = section.get("product_items", [])[:30]  # Máximo 30 productos total

            if product_items:
                prepared.append({
                    "title": section.get("title", "Productos")[:24],
                    "product_items": [
                        {"product_retailer_id": item.get("product_retailer_id", "")}
                        for item in product_items
                        if item.get("product_retailer_id")
                    ]
                })

        return prepared

    async def _fallback_mpm_to_list(
        self,
        to: str,
        header: str,
        body: str,
        sections: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Fallback de Multi-Product Message a lista interactiva.

        Usado cuando el catálogo no está configurado.
        """
        # Convertir secciones de productos a lista interactiva
        list_sections = []

        for section in sections:
            items = []
            for product in section.get("product_items", []):
                retailer_id = product.get("product_retailer_id", "")
                # Extraer nombre legible del retailer_id
                display_name = retailer_id.replace("product_", "").replace("_", " ").title()
                items.append({
                    "id": retailer_id,
                    "title": display_name[:24],
                    "description": "Toca para seleccionar"[:72]
                })

            if items:
                list_sections.append({
                    "title": section.get("title", "Productos")[:24],
                    "items": items[:10]
                })

        if list_sections:
            return await self.send_message(
                to=to,
                message=f"*{header}*\n\n{body}",
                list_items=list_sections
            )
        else:
            return await self.send_message(to=to, message=f"*{header}*\n\n{body}")
