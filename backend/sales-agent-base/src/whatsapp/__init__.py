"""
================================================================================
WHATSAPP MODULE
================================================================================
Módulo para integración de WhatsApp con los agentes del sistema.

Componentes:
- broadcast_manager: Gestión de mensajes broadcast a clientes
- customer_segmentation: Segmentación de clientes para campañas
- message_personalizer: Personalización de mensajes
- analytics: Analytics de campañas de WhatsApp
================================================================================
"""

from .broadcast_manager import WhatsAppBroadcastManager, get_broadcast_manager
from .customer_segmentation import CustomerSegmenter, get_customer_segmenter
from .message_personalizer import MessagePersonalizer, get_message_personalizer

__all__ = [
    'WhatsAppBroadcastManager',
    'get_broadcast_manager',
    'CustomerSegmenter',
    'get_customer_segmenter',
    'MessagePersonalizer',
    'get_message_personalizer'
]
