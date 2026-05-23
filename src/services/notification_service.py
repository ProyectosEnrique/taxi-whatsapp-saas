"""
Notification Service for Taxi Drivers

Servicio para enviar notificaciones a conductores:
- Push notifications (Firebase)
- SMS (Twilio)
- WhatsApp messages (Twilio)
- Email notifications (SendGrid)
"""

import os
import logging
from typing import Dict, List, Optional
from twilio.rest import Client
from datetime import datetime

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Servicio centralizado de notificaciones para conductores
    """

    def __init__(self):
        """
        Inicializa el servicio de notificaciones
        """
        # Twilio para SMS y WhatsApp
        self.twilio_sid = os.getenv('TWILIO_ACCOUNT_SID')
        self.twilio_token = os.getenv('TWILIO_AUTH_TOKEN')
        self.twilio_phone = os.getenv('TWILIO_SMS_NUMBER')
        self.twilio_whatsapp = os.getenv('TWILIO_WHATSAPP_NUMBER')

        if self.twilio_sid and self.twilio_token:
            self.twilio_client = Client(self.twilio_sid, self.twilio_token)
            logger.info("Twilio client initialized")
        else:
            self.twilio_client = None
            logger.warning("Twilio credentials not found")

        # TODO: Inicializar Firebase para push notifications
        # TODO: Inicializar SendGrid para emails

    async def notify_new_ride_request(
        self,
        driver: Dict,
        ride: Dict,
        notification_methods: List[str] = None
    ) -> Dict:
        """
        Notifica a un conductor sobre una nueva solicitud de viaje

        Args:
            driver: Información del conductor
            ride: Información del viaje
            notification_methods: ["push", "sms", "whatsapp"] (default: all)

        Returns:
            {
                "push": {"success": bool, "message_id": str},
                "sms": {"success": bool, "message_id": str},
                "whatsapp": {"success": bool, "message_id": str}
            }
        """
        if notification_methods is None:
            notification_methods = ["sms", "whatsapp"]  # Por defecto SMS y WhatsApp

        results = {}

        # Preparar mensaje
        message = self._format_new_ride_message(ride)

        # Enviar notificaciones
        if "push" in notification_methods:
            results["push"] = await self._send_push_notification(
                driver_id=driver['driver_id'],
                title="Nueva Solicitud de Viaje",
                body=message,
                data=ride
            )

        if "sms" in notification_methods:
            results["sms"] = await self._send_sms(
                to=driver['phone'],
                message=message
            )

        if "whatsapp" in notification_methods:
            results["whatsapp"] = await self._send_whatsapp(
                to=driver['phone'],
                message=message
            )

        logger.info(f"Ride request notification sent to driver {driver['driver_id']}: {results}")

        return results

    async def notify_ride_cancelled(
        self,
        driver: Dict,
        ride: Dict,
        reason: str = None
    ) -> Dict:
        """
        Notifica a conductor que el viaje fue cancelado
        """
        message = f"""🚫 Viaje Cancelado

ID: {ride['ride_id']}
Cliente: {ride['customer']['name']}
Origen: {ride['origin']['address'][:50]}

Motivo: {reason or 'Cliente canceló'}

El viaje ha sido cancelado."""

        return await self._send_notification_multi_channel(
            driver=driver,
            message=message,
            priority="normal"
        )

    async def notify_customer_waiting(
        self,
        driver: Dict,
        ride: Dict
    ) -> Dict:
        """
        Recuerda al conductor que el cliente está esperando
        """
        message = f"""⏰ Cliente Esperando

{ride['customer']['name']} está esperando en:
{ride['origin']['address']}

Por favor, confirma tu ETA."""

        return await self._send_notification_multi_channel(
            driver=driver,
            message=message,
            priority="high"
        )

    async def notify_shift_reminder(
        self,
        driver: Dict,
        message_type: str = "start"  # "start" o "end"
    ) -> Dict:
        """
        Recuerda al conductor sobre su turno
        """
        if message_type == "start":
            message = f"""🌅 Inicio de Turno

Hola {driver['name']},

¿Listo para comenzar tu turno?
Actívate en la app cuando estés disponible.

¡Que tengas un gran día! 🚕"""
        else:
            message = f"""🌙 Fin de Turno

Hola {driver['name']},

Tu turno está por terminar.
Recuerda desactivarte en la app.

¡Gracias por tu trabajo hoy! 🚕"""

        return await self._send_whatsapp(
            to=driver['phone'],
            message=message
        )

    async def notify_payment_received(
        self,
        driver: Dict,
        amount: float,
        ride_id: str
    ) -> Dict:
        """
        Notifica al conductor que recibió un pago
        """
        message = f"""💰 Pago Recibido

Viaje: {ride_id}
Monto: ${amount:.2f}

El pago ha sido procesado exitosamente."""

        return await self._send_notification_multi_channel(
            driver=driver,
            message=message,
            priority="normal"
        )

    async def notify_low_rating_alert(
        self,
        driver: Dict,
        current_rating: float,
        threshold: float = 4.0
    ) -> Dict:
        """
        Alerta al conductor sobre calificación baja
        """
        message = f"""⚠️ Alerta de Calificación

Hola {driver['name']},

Tu calificación actual es {current_rating:.1f} ⭐

Te recomendamos:
• Mantener el vehículo limpio
• Ser puntual
• Conducir con cuidado
• Trato amable con clientes

¡Sabemos que puedes mejorar! 💪"""

        return await self._send_whatsapp(
            to=driver['phone'],
            message=message
        )

    async def broadcast_message(
        self,
        drivers: List[Dict],
        message: str,
        filter_criteria: Dict = None
    ) -> Dict:
        """
        Envía mensaje a múltiples conductores

        Args:
            drivers: Lista de conductores
            message: Mensaje a enviar
            filter_criteria: Filtros opcionales {
                "status": "available",
                "min_rating": 4.5,
                "vehicle_type": "sedan"
            }

        Returns:
            {
                "total": 50,
                "sent": 45,
                "failed": 5,
                "details": [...]
            }
        """
        # Aplicar filtros si existen
        if filter_criteria:
            drivers = self._filter_drivers(drivers, filter_criteria)

        results = {
            "total": len(drivers),
            "sent": 0,
            "failed": 0,
            "details": []
        }

        for driver in drivers:
            try:
                result = await self._send_whatsapp(
                    to=driver['phone'],
                    message=message
                )

                if result.get('success'):
                    results['sent'] += 1
                else:
                    results['failed'] += 1

                results['details'].append({
                    "driver_id": driver['driver_id'],
                    "success": result.get('success'),
                    "message_id": result.get('message_id')
                })

            except Exception as e:
                logger.error(f"Failed to send broadcast to driver {driver['driver_id']}: {e}")
                results['failed'] += 1
                results['details'].append({
                    "driver_id": driver['driver_id'],
                    "success": False,
                    "error": str(e)
                })

        logger.info(f"Broadcast sent to {results['sent']}/{results['total']} drivers")

        return results

    # ============================================
    # MÉTODOS INTERNOS
    # ============================================

    async def _send_notification_multi_channel(
        self,
        driver: Dict,
        message: str,
        priority: str = "normal"
    ) -> Dict:
        """
        Envía notificación por múltiples canales según prioridad
        """
        results = {}

        if priority == "high":
            # Alta prioridad: Push + SMS + WhatsApp
            results["push"] = await self._send_push_notification(
                driver_id=driver['driver_id'],
                title="Alerta Importante",
                body=message
            )
            results["sms"] = await self._send_sms(
                to=driver['phone'],
                message=message
            )

        # Siempre enviar por WhatsApp
        results["whatsapp"] = await self._send_whatsapp(
            to=driver['phone'],
            message=message
        )

        return results

    async def _send_push_notification(
        self,
        driver_id: str,
        title: str,
        body: str,
        data: Dict = None
    ) -> Dict:
        """
        Envía push notification via Firebase
        """
        # TODO: Implementar con Firebase Cloud Messaging

        logger.info(f"Push notification sent to driver {driver_id}: {title}")

        return {
            "success": True,
            "message_id": f"push_{driver_id}_{datetime.now().timestamp()}",
            "method": "push"
        }

    async def _send_sms(
        self,
        to: str,
        message: str
    ) -> Dict:
        """
        Envía SMS via Twilio
        """
        if not self.twilio_client:
            logger.warning("Twilio not configured, SMS not sent")
            return {"success": False, "error": "Twilio not configured"}

        try:
            # Formatear número (debe incluir código de país)
            if not to.startswith('+'):
                to = f"+52{to}"  # Asumir México si no tiene código

            result = self.twilio_client.messages.create(
                body=message,
                from_=self.twilio_phone,
                to=to
            )

            logger.info(f"SMS sent to {to}: {result.sid}")

            return {
                "success": True,
                "message_id": result.sid,
                "method": "sms"
            }

        except Exception as e:
            logger.error(f"Failed to send SMS to {to}: {e}")
            return {
                "success": False,
                "error": str(e),
                "method": "sms"
            }

    async def _send_whatsapp(
        self,
        to: str,
        message: str
    ) -> Dict:
        """
        Envía mensaje de WhatsApp via Twilio
        """
        if not self.twilio_client:
            logger.warning("Twilio not configured, WhatsApp not sent")
            return {"success": False, "error": "Twilio not configured"}

        try:
            # Formatear número para WhatsApp
            if not to.startswith('whatsapp:'):
                if not to.startswith('+'):
                    to = f"+52{to}"
                to = f"whatsapp:{to}"

            from_number = f"whatsapp:{self.twilio_whatsapp}"

            result = self.twilio_client.messages.create(
                body=message,
                from_=from_number,
                to=to
            )

            logger.info(f"WhatsApp sent to {to}: {result.sid}")

            return {
                "success": True,
                "message_id": result.sid,
                "method": "whatsapp"
            }

        except Exception as e:
            logger.error(f"Failed to send WhatsApp to {to}: {e}")
            return {
                "success": False,
                "error": str(e),
                "method": "whatsapp"
            }

    def _format_new_ride_message(self, ride: Dict) -> str:
        """
        Formatea mensaje de nueva solicitud de viaje
        """
        message = f"""🚕 Nueva Solicitud de Viaje

📍 Origen: {ride['origin']['address'][:50]}
📍 Destino: {ride['destination']['address'][:50]}

🛣️ Distancia: {ride['distance_km']} km
⏱️ Tiempo: ~{ride['duration_minutes']} min
💰 Tarifa: ${ride['total_fare']}

Cliente: {ride['customer']['name']}

⏰ Expira en 30 segundos

Abre la app para aceptar."""

        return message

    def _filter_drivers(self, drivers: List[Dict], criteria: Dict) -> List[Dict]:
        """
        Filtra conductores según criterios
        """
        filtered = drivers

        if criteria.get('status'):
            filtered = [d for d in filtered if d.get('status') == criteria['status']]

        if criteria.get('min_rating'):
            filtered = [d for d in filtered if d.get('rating', 0) >= criteria['min_rating']]

        if criteria.get('vehicle_type'):
            filtered = [d for d in filtered if d.get('vehicle', {}).get('type') == criteria['vehicle_type']]

        return filtered


# Singleton instance
_notification_service = None


def get_notification_service() -> NotificationService:
    """
    Obtiene la instancia singleton del servicio de notificaciones
    """
    global _notification_service
    if _notification_service is None:
        _notification_service = NotificationService()
    return _notification_service
