"""
================================================================================
URL GENERATOR CON TRACKING
================================================================================
Genera URLs para web con parámetros de tracking y contexto de sesión
================================================================================
"""

import os
import json
import base64
import hmac
import hashlib
from typing import Dict, Any, Optional, List
from urllib.parse import urlencode, quote
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class SecureURLGenerator:
    """
    Generador de URLs seguras con tracking para el flujo híbrido.

    Características:
    - Tokens firmados (HMAC) para prevenir manipulación
    - Context encoding para pasar estado a la web
    - UTM parameters para analytics
    - Carrito pre-cargado
    - Expiración de tokens
    """

    def __init__(self):
        self.base_url = os.getenv("CUSTOMER_APP_URL", "http://localhost:8080")
        self.secret_key = os.getenv("URL_SIGNING_SECRET", "change-me-in-production")
        self.token_ttl_minutes = 30

    def generate_web_url(
        self,
        session_id: str,
        phone: str,
        reason: str,
        cart: List[Dict[str, Any]] = None,
        table_id: Optional[int] = None,
        preferences: Dict[str, Any] = None
    ) -> str:
        """
        Generar URL segura para redirección a web.

        Args:
            session_id: ID de sesión de WhatsApp
            phone: Teléfono del cliente
            reason: Razón de la derivación (para analytics)
            cart: Carrito actual (si existe)
            table_id: Mesa (si aplica)
            preferences: Preferencias del cliente

        Returns:
            URL completa con tracking y contexto
        """
        # Crear session token seguro
        session_token = self._create_session_token(
            session_id=session_id,
            phone=phone
        )

        # Codificar contexto (carrito, preferencias, etc.)
        context = self._encode_context({
            "session_id": session_id,
            "phone_hash": self._hash_phone(phone),  # No exponer teléfono completo
            "cart": cart or [],
            "table_id": table_id,
            "preferences": preferences or {},
            "redirect_reason": reason,
            "timestamp": datetime.utcnow().isoformat()
        })

        # UTM parameters para analytics
        utm_params = {
            "utm_source": "whatsapp",
            "utm_medium": "chat",
            "utm_campaign": "hybrid_flow",
            "utm_content": reason
        }

        # Construir URL
        params = {
            "st": session_token,  # Session token
            "ctx": context,  # Context
            "from": "whatsapp",
            **utm_params
        }

        url = f"{self.base_url}/menu?{urlencode(params)}"

        logger.info(f"[URLGenerator] URL generada: ...{url[-50:]}")

        return url

    def generate_return_url(
        self,
        session_id: str,
        order_summary: Dict[str, Any]
    ) -> str:
        """
        Generar deep link de WhatsApp para retorno.

        Cuando el usuario termine en la web, puede hacer click
        para volver a WhatsApp con el pedido listo.

        Args:
            session_id: ID de sesión
            order_summary: Resumen del pedido desde web

        Returns:
            URL de WhatsApp con mensaje pre-escrito
        """
        whatsapp_number = os.getenv("TWILIO_WHATSAPP_NUMBER", "+14155238886")

        # Crear mensaje pre-escrito
        message_text = self._format_return_message(order_summary)

        # WhatsApp deep link
        wa_url = f"https://wa.me/{whatsapp_number.replace('+', '')}?text={quote(message_text)}"

        return wa_url

    def _create_session_token(
        self,
        session_id: str,
        phone: str
    ) -> str:
        """
        Crear token firmado de sesión.

        Format: base64(session_id|phone_hash|timestamp|signature)
        """
        timestamp = int(datetime.utcnow().timestamp())
        phone_hash = self._hash_phone(phone)

        # Datos a firmar
        data = f"{session_id}|{phone_hash}|{timestamp}"

        # Crear firma HMAC
        signature = hmac.new(
            self.secret_key.encode(),
            data.encode(),
            hashlib.sha256
        ).hexdigest()[:16]  # Primeros 16 chars

        # Token completo
        token = f"{data}|{signature}"

        # Encode a base64
        token_b64 = base64.urlsafe_b64encode(token.encode()).decode()

        return token_b64

    def verify_session_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Verificar y decodificar token de sesión.

        Returns:
            Dict con session_id, phone_hash, timestamp si es válido, None si no
        """
        try:
            # Decodificar base64
            token_decoded = base64.urlsafe_b64decode(token.encode()).decode()

            # Separar componentes
            parts = token_decoded.split("|")
            if len(parts) != 4:
                logger.warning("[URLGenerator] Token inválido: formato incorrecto")
                return None

            session_id, phone_hash, timestamp_str, signature = parts

            # Verificar firma
            data = f"{session_id}|{phone_hash}|{timestamp_str}"
            expected_signature = hmac.new(
                self.secret_key.encode(),
                data.encode(),
                hashlib.sha256
            ).hexdigest()[:16]

            if signature != expected_signature:
                logger.warning("[URLGenerator] Token inválido: firma incorrecta")
                return None

            # Verificar expiración
            timestamp = int(timestamp_str)
            now = int(datetime.utcnow().timestamp())
            age_minutes = (now - timestamp) / 60

            if age_minutes > self.token_ttl_minutes:
                logger.warning(f"[URLGenerator] Token expirado: {age_minutes:.1f} minutos")
                return None

            return {
                "session_id": session_id,
                "phone_hash": phone_hash,
                "timestamp": timestamp
            }

        except Exception as e:
            logger.error(f"[URLGenerator] Error verificando token: {e}")
            return None

    def _encode_context(self, context: Dict[str, Any]) -> str:
        """
        Codificar contexto como base64.

        El contexto se pasa a la web app para que tenga toda la info.
        """
        try:
            context_json = json.dumps(context, separators=(',', ':'))
            context_b64 = base64.urlsafe_b64encode(context_json.encode()).decode()
            return context_b64
        except Exception as e:
            logger.error(f"[URLGenerator] Error codificando contexto: {e}")
            return ""

    def decode_context(self, context_b64: str) -> Optional[Dict[str, Any]]:
        """
        Decodificar contexto desde base64.
        """
        try:
            context_json = base64.urlsafe_b64decode(context_b64.encode()).decode()
            context = json.loads(context_json)
            return context
        except Exception as e:
            logger.error(f"[URLGenerator] Error decodificando contexto: {e}")
            return None

    def _hash_phone(self, phone: str) -> str:
        """
        Hash del teléfono para privacidad.
        """
        return hashlib.sha256(phone.encode()).hexdigest()[:12]

    def _format_return_message(self, order_summary: Dict[str, Any]) -> str:
        """
        Formatear mensaje de retorno desde web.
        """
        cart = order_summary.get("cart", [])
        total = order_summary.get("total", 0)

        message = "✅ Listo! Armé mi pedido:\n\n"

        for item in cart:
            name = item.get("name", "Item")
            qty = item.get("quantity", 1)
            price = item.get("price", 0)
            message += f"• {name} x{qty} - ${price * qty:.2f}\n"

        message += f"\n💰 Total: ${total:.2f}\n\n"
        message += "¿Confirmo el pedido?"

        return message


# ==============================================================================
# ANALYTICS TRACKER
# ==============================================================================

class ConversionTracker:
    """
    Track de conversiones para medir efectividad del flujo híbrido.
    """

    def __init__(self):
        self.events = []

    def track_redirect_to_web(
        self,
        session_id: str,
        reason: str,
        cart_size: int
    ) -> None:
        """Track cuando usuario es redirigido a web"""
        event = {
            "event": "redirect_to_web",
            "session_id": session_id,
            "reason": reason,
            "cart_size": cart_size,
            "timestamp": datetime.utcnow().isoformat()
        }
        self.events.append(event)
        logger.info(f"[Analytics] {event}")

    def track_return_from_web(
        self,
        session_id: str,
        time_on_web_seconds: int,
        cart_updated: bool,
        cart_size_before: int,
        cart_size_after: int
    ) -> None:
        """Track cuando usuario regresa de web"""
        event = {
            "event": "return_from_web",
            "session_id": session_id,
            "time_on_web": time_on_web_seconds,
            "cart_updated": cart_updated,
            "cart_before": cart_size_before,
            "cart_after": cart_size_after,
            "timestamp": datetime.utcnow().isoformat()
        }
        self.events.append(event)
        logger.info(f"[Analytics] {event}")

    def track_order_completed(
        self,
        session_id: str,
        order_id: str,
        total: float,
        used_web: bool
    ) -> None:
        """Track pedido completado"""
        event = {
            "event": "order_completed",
            "session_id": session_id,
            "order_id": order_id,
            "total": total,
            "used_web": used_web,
            "timestamp": datetime.utcnow().isoformat()
        }
        self.events.append(event)
        logger.info(f"[Analytics] {event}")


# ==============================================================================
# EXAMPLE USAGE
# ==============================================================================

if __name__ == "__main__":
    generator = SecureURLGenerator()

    # Generar URL de redirección
    url = generator.generate_web_url(
        session_id="sess_abc123",
        phone="+5215551234567",
        reason="browsing_detected",
        cart=[
            {"product_id": 15, "name": "Tacos al Pastor", "quantity": 2, "price": 110.0}
        ],
        table_id=5
    )

    print("=" * 80)
    print("URL GENERADA:")
    print("=" * 80)
    print(url)
    print()

    # Extraer y verificar token
    import re
    match = re.search(r'st=([^&]+)', url)
    if match:
        token = match.group(1)
        print("\nVERIFICAR TOKEN:")
        print("=" * 80)
        result = generator.verify_session_token(token)
        print(f"Válido: {result is not None}")
        if result:
            print(f"Session ID: {result['session_id']}")
            print(f"Phone Hash: {result['phone_hash']}")

    # Generar URL de retorno
    print("\n\nURL DE RETORNO A WHATSAPP:")
    print("=" * 80)
    return_url = generator.generate_return_url(
        session_id="sess_abc123",
        order_summary={
            "cart": [
                {"name": "Tacos al Pastor", "quantity": 3, "price": 110.0},
                {"name": "Refresco", "quantity": 2, "price": 25.0}
            ],
            "total": 380.0
        }
    )
    print(return_url)
