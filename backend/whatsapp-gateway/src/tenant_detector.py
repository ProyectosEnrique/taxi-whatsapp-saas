"""
================================================================================
TENANT DETECTOR
================================================================================
Detecta el tenant (tienda) basado en:
1. Palabra clave en el mensaje (desarrollo/sandbox)
2. Número de WhatsApp receptor (producción)
3. Sesión existente
================================================================================
"""

import re
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class TenantDetector:
    """
    Detecta el tenant basado en el mensaje o número de WhatsApp.

    Para desarrollo (Twilio Sandbox):
    - Cliente: "restaurant-hola"  → tenant: "default" (restaurant)
    - Cliente: "farmacia-hola"    → tenant: "tenant_pharmacy_001"
    - Cliente: "carniceria-hola"  → tenant: "tenant_butchery_001"

    Para producción:
    - Cada tienda tiene su número de WhatsApp
    - Se detecta por el campo "To" del webhook
    """

    # Palabras clave por tenant (desarrollo/sandbox)
    TENANT_KEYWORDS = {
        "default": [
            "restaurant", "restaurante", "comida", "taqueria", "tacos"
        ],
        "tenant_pharmacy_001": [
            "farmacia", "pharmacy", "medicina", "medicamento", "medicamentos"
        ],
        "tenant_butchery_001": [
            "carniceria", "carnicería", "butchery", "carne", "carnes"
        ],
        "rico-mar-salvatierra": [
            "rico-mar", "ricomar", "mariscos", "salvatierra",
            "aguachiles", "ceviches", "camarones", "pescado", "sushi"
        ]
    }

    # Mapeo de números a tenants (producción)
    # +14155238886 = Sandbox de Twilio (usar keywords)
    # Los demás son números de producción
    PHONE_TO_TENANT = {
        "+14155238886": None,  # Sandbox - detectar por keyword
        # Ejemplo producción:
        # "+525512345678": "default",
        # "+525587654321": "tenant_pharmacy_001",
        # "+525599998888": "tenant_butchery_001",
    }

    @staticmethod
    def detect_from_message(message: str) -> Optional[str]:
        """
        Detectar tenant desde el mensaje usando palabras clave.

        Args:
            message: Mensaje del cliente

        Returns:
            tenant_id o None si no se detectó

        Ejemplos:
            "restaurant-hola" → "default"
            "farmacia-hola" → "tenant_pharmacy_001"
            "carniceria-hola" → "tenant_butchery_001"
            "hola" → None (no se puede detectar)
        """
        message_lower = message.lower().strip()

        # Buscar palabras clave en el mensaje
        for tenant_id, keywords in TenantDetector.TENANT_KEYWORDS.items():
            for keyword in keywords:
                if keyword in message_lower:
                    logger.info(f"[TenantDetector] Detectado '{tenant_id}' por keyword '{keyword}'")
                    return tenant_id

        logger.debug(f"[TenantDetector] No se detectó tenant en: '{message}'")
        return None

    @staticmethod
    def detect_from_phone(to_number: str) -> Optional[str]:
        """
        Detectar tenant desde el número de WhatsApp receptor.

        Args:
            to_number: Número de WhatsApp al que el cliente escribió
                       Formato: "whatsapp:+14155238886"

        Returns:
            tenant_id o None si es sandbox (usar keywords)
        """
        clean_number = to_number.replace("whatsapp:", "").strip()
        tenant_id = TenantDetector.PHONE_TO_TENANT.get(clean_number)

        if tenant_id:
            logger.info(f"[TenantDetector] Detectado '{tenant_id}' por número '{clean_number}'")
        else:
            logger.debug(f"[TenantDetector] Número '{clean_number}' es sandbox, usar keywords")

        return tenant_id

    @staticmethod
    def extract_clean_message(message: str, tenant_id: str) -> str:
        """
        Remover la palabra clave del mensaje para que el agente no la vea.

        Args:
            message: Mensaje original
            tenant_id: Tenant detectado

        Returns:
            Mensaje sin la palabra clave

        Ejemplos:
            ("restaurant-hola", "default") → "hola"
            ("farmacia quiero aspirinas", "tenant_pharmacy_001") → "quiero aspirinas"
        """
        message_lower = message.lower()
        keywords = TenantDetector.TENANT_KEYWORDS.get(tenant_id, [])

        for keyword in keywords:
            # Si la keyword está al inicio (con o sin guión)
            pattern = rf"^{keyword}[\s\-]*"
            if re.match(pattern, message_lower):
                # Remover keyword del mensaje original (mantener mayúsculas)
                clean_msg = re.sub(pattern, "", message, count=1, flags=re.IGNORECASE).strip()
                logger.debug(f"[TenantDetector] Mensaje limpio: '{message}' → '{clean_msg}'")
                return clean_msg

        # Si la keyword está en medio
        for keyword in keywords:
            if keyword in message_lower and len(keyword) > 5:  # Solo keywords largas
                parts = message_lower.split(keyword)
                if len(parts) == 2 and len(parts[0].strip()) < 3:  # Keyword casi al inicio
                    clean_msg = parts[1].strip()
                    logger.debug(f"[TenantDetector] Mensaje limpio (keyword en medio): '{message}' → '{clean_msg}'")
                    return clean_msg

        # No se encontró keyword para remover
        return message

    @staticmethod
    def get_tenant_info(tenant_id: str) -> dict:
        """
        Obtener información básica del tenant.

        Returns:
            Dict con nombre, tipo, etc.
        """
        tenant_info = {
            "default": {
                "name": "Demo Restaurant",
                "type": "restaurant",
                "emoji": "🍽️",
                "greeting": "¡Bienvenido a Demo Restaurant! 🍽️"
            },
            "tenant_pharmacy_001": {
                "name": "Farmacia Santa Fe",
                "type": "pharmacy",
                "emoji": "💊",
                "greeting": "¡Hola! Bienvenido a Farmacia Santa Fe 💊"
            },
            "tenant_butchery_001": {
                "name": "Carnicería El Buen Corte",
                "type": "butchery",
                "emoji": "🥩",
                "greeting": "¡Bienvenido a Carnicería El Buen Corte! 🥩"
            },
            "rico-mar-salvatierra": {
                "name": "Rico Mar Salvatierra",
                "type": "seafood_restaurant",
                "emoji": "🦐",
                "greeting": "¡Bienvenido a Rico Mar Salvatierra! 🦐🐟 Los mejores mariscos de la región"
            }
        }

        return tenant_info.get(tenant_id, tenant_info["rico-mar-salvatierra"])


# ==============================================================================
# EJEMPLO DE USO
# ==============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Test 1: Detectar por mensaje
    print("\n=== Test 1: Detección por mensaje ===")
    test_messages = [
        "restaurant-hola",
        "farmacia-hola",
        "carniceria-hola",
        "hola",
        "farmacia quiero aspirinas",
        "RESTAURANT necesito reservar",
    ]

    for msg in test_messages:
        tenant = TenantDetector.detect_from_message(msg)
        if tenant:
            clean = TenantDetector.extract_clean_message(msg, tenant)
            info = TenantDetector.get_tenant_info(tenant)
            print(f"✓ '{msg}' → Tenant: {tenant} ({info['name']})")
            print(f"  Mensaje limpio: '{clean}'")
        else:
            print(f"✗ '{msg}' → No detectado")

    # Test 2: Detectar por número
    print("\n=== Test 2: Detección por número ===")
    test_phones = [
        "whatsapp:+14155238886",  # Sandbox
        "whatsapp:+525512345678",  # Producción (no configurado aún)
    ]

    for phone in test_phones:
        tenant = TenantDetector.detect_from_phone(phone)
        if tenant:
            info = TenantDetector.get_tenant_info(tenant)
            print(f"✓ '{phone}' → {tenant} ({info['name']})")
        else:
            print(f"✗ '{phone}' → Sandbox (usar keywords)")
