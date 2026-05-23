"""
FSM (Finite State Machine) para Servicio de Taxi por WhatsApp

Este módulo maneja el flujo de conversación para solicitar taxis:
- Cliente solicita taxi
- Bot pregunta destino y origen
- Calcula tarifa y asigna conductor
- Tracking en tiempo real
- Completar viaje y calificación
"""

from enum import Enum
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import re
import logging

logger = logging.getLogger(__name__)


class TaxiState(Enum):
    """Estados del flujo de conversación para servicio de taxi"""
    GREETING = "greeting"
    ASKING_DESTINATION = "asking_destination"
    ASKING_ORIGIN = "asking_origin"
    ASKING_WHEN = "asking_when"
    CALCULATING_FARE = "calculating_fare"
    CONFIRMING_RIDE = "confirming_ride"
    ASSIGNING_DRIVER = "assigning_driver"
    DRIVER_ASSIGNED = "driver_assigned"
    WAITING_FOR_DRIVER = "waiting_for_driver"
    DRIVER_ARRIVING = "driver_arriving"
    RIDE_STARTED = "ride_started"
    RIDE_IN_PROGRESS = "ride_in_progress"
    RIDE_COMPLETED = "ride_completed"
    RATING = "rating"
    PAYMENT = "payment"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TaxiFSM:
    """
    Máquina de estados para manejar solicitudes de taxi por WhatsApp
    """

    def __init__(self, tenant_id: str, session_id: str, config: Dict = None):
        self.tenant_id = tenant_id
        self.session_id = session_id
        self.config = config or {}

        # Estado actual
        self.state = TaxiState.GREETING

        # Contexto de la conversación
        self.context = {
            "customer_phone": None,
            "customer_name": None,
            "destination": None,
            "destination_coords": None,
            "origin": None,
            "origin_coords": None,
            "when": "now",  # "now" o timestamp para programado
            "ride_id": None,
            "driver_id": None,
            "driver_info": None,
            "fare": None,
            "distance_km": None,
            "duration_minutes": None,
            "eta_minutes": None,
            "rating": None,
            "payment_method": "cash",
            "special_requests": [],
            "created_at": datetime.now(),
        }

    async def process_message(self, message: str, customer_phone: str, media_data: Dict = None) -> Dict:
        """
        Procesa un mensaje del cliente según el estado actual

        Args:
            message: Texto del mensaje
            customer_phone: Teléfono del cliente
            media_data: Datos de ubicación u otros medios

        Returns:
            Dict con respuesta y nuevo estado
        """
        self.context["customer_phone"] = customer_phone

        logger.info(f"Processing message in state {self.state.value}: {message[:50]}")

        # Comandos especiales que funcionan en cualquier estado
        if message.lower() in ["cancelar", "cancel", "no", "ya no"]:
            return await self.handle_cancel()

        if message.lower() in ["ayuda", "help", "?"]:
            return await self.handle_help()

        # Procesar según el estado actual
        if self.state == TaxiState.GREETING:
            return await self.handle_greeting(message)

        elif self.state == TaxiState.ASKING_DESTINATION:
            return await self.handle_destination(message, media_data)

        elif self.state == TaxiState.ASKING_ORIGIN:
            return await self.handle_origin(message, media_data)

        elif self.state == TaxiState.ASKING_WHEN:
            return await self.handle_when(message)

        elif self.state == TaxiState.CONFIRMING_RIDE:
            return await self.handle_confirmation(message)

        elif self.state == TaxiState.RATING:
            return await self.handle_rating(message)

        elif self.state == TaxiState.PAYMENT:
            return await self.handle_payment(message)

        else:
            return {
                "response": "Un momento por favor...",
                "state": self.state.value
            }

    async def handle_greeting(self, message: str) -> Dict:
        """
        Maneja el saludo inicial y detecta intención de solicitar taxi
        """
        message_lower = message.lower()

        # Detectar intención de solicitar taxi
        taxi_keywords = ["taxi", "viaje", "llevar", "transporte", "ir a", "necesito"]

        if any(keyword in message_lower for keyword in taxi_keywords):
            # Ya expresó que necesita taxi
            self.state = TaxiState.ASKING_DESTINATION

            # Intentar extraer destino del mensaje inicial
            destination = self._extract_destination_from_message(message)

            if destination:
                self.context["destination"] = destination
                self.state = TaxiState.ASKING_ORIGIN
                return {
                    "response": f"Perfecto! Te llevaremos a *{destination}* 🚕\n\n¿Desde dónde te recogemos?\n\nPuedes escribir la dirección o enviar tu ubicación 📍",
                    "state": self.state.value
                }
            else:
                return {
                    "response": "¡Hola! 👋 Con gusto te ayudo a solicitar un taxi.\n\n¿A dónde te diriges? 🗺️\n\nEscribe la dirección o el nombre del lugar.",
                    "state": self.state.value
                }
        else:
            # Saludo genérico
            return {
                "response": "¡Hola! 👋 Bienvenido a nuestro servicio de taxi.\n\n¿Necesitas un taxi? Dime *necesito taxi* para comenzar 🚕",
                "state": self.state.value
            }

    async def handle_destination(self, message: str, media_data: Dict = None) -> Dict:
        """
        Maneja la captura del destino
        """
        # Si envió ubicación GPS
        if media_data and media_data.get("type") == "location":
            lat = media_data.get("latitude")
            lon = media_data.get("longitude")

            self.context["destination_coords"] = {"lat": lat, "lon": lon}

            # Intentar obtener dirección con geocoding reverso
            # TODO: Integrar con Google Maps API
            address = f"Lat: {lat}, Lon: {lon}"  # Placeholder
            self.context["destination"] = address

            self.state = TaxiState.ASKING_ORIGIN
            return {
                "response": f"Perfecto! Te llevaremos a *{address}* 📍\n\n¿Desde dónde te recogemos?\n\nPuedes escribir la dirección o enviar tu ubicación.",
                "state": self.state.value
            }

        # Si escribió dirección
        else:
            destination = message.strip()

            # Validar que no esté vacío
            if len(destination) < 3:
                return {
                    "response": "Por favor escribe una dirección válida o envía tu ubicación 📍",
                    "state": self.state.value
                }

            self.context["destination"] = destination
            self.state = TaxiState.ASKING_ORIGIN

            return {
                "response": f"Perfecto! Te llevaremos a *{destination}* 🚕\n\n¿Desde dónde te recogemos?\n\nPuedes escribir la dirección o enviar tu ubicación 📍",
                "state": self.state.value
            }

    async def handle_origin(self, message: str, media_data: Dict = None) -> Dict:
        """
        Maneja la captura del origen
        """
        # Si envió ubicación GPS
        if media_data and media_data.get("type") == "location":
            lat = media_data.get("latitude")
            lon = media_data.get("longitude")

            self.context["origin_coords"] = {"lat": lat, "lon": lon}

            # Intentar obtener dirección con geocoding reverso
            address = f"Lat: {lat}, Lon: {lon}"  # Placeholder
            self.context["origin"] = address

            # Proceder a calcular ruta y tarifa
            return await self.calculate_and_confirm_fare()

        # Si escribió dirección
        else:
            origin = message.strip()

            # Validar que no esté vacío
            if len(origin) < 3:
                return {
                    "response": "Por favor escribe una dirección válida o envía tu ubicación 📍",
                    "state": self.state.value
                }

            self.context["origin"] = origin

            # Proceder a calcular ruta y tarifa
            return await self.calculate_and_confirm_fare()

    async def calculate_and_confirm_fare(self) -> Dict:
        """
        Calcula la tarifa y solicita confirmación
        """
        self.state = TaxiState.CALCULATING_FARE

        # TODO: Integrar con Google Maps API para calcular ruta real
        # Por ahora, valores de ejemplo
        self.context["distance_km"] = 12.5
        self.context["duration_minutes"] = 25

        # TODO: Calcular tarifa real con FareCalculator
        base_fare = 50
        per_km = 8.0
        total_fare = base_fare + (self.context["distance_km"] * per_km)
        self.context["fare"] = round(total_fare, 2)

        self.state = TaxiState.CONFIRMING_RIDE

        response = f"""¡Listo! 🚕 Aquí está la información de tu viaje:

📍 *Origen:* {self.context['origin']}
📍 *Destino:* {self.context['destination']}

🛣️ *Distancia:* {self.context['distance_km']} km
⏱️ *Tiempo estimado:* {self.context['duration_minutes']} minutos

💰 *Tarifa:* ${self.context['fare']}

¿Confirmas el viaje?

Responde:
✅ *Sí* - Solicitar taxi
❌ *No* - Cancelar"""

        return {
            "response": response,
            "state": self.state.value
        }

    async def handle_confirmation(self, message: str) -> Dict:
        """
        Maneja la confirmación del viaje
        """
        message_lower = message.lower()

        # Respuestas afirmativas
        if any(word in message_lower for word in ["si", "sí", "yes", "ok", "confirmar", "dale"]):
            # Proceder a asignar conductor
            return await self.assign_driver()

        # Respuestas negativas
        elif any(word in message_lower for word in ["no", "cancelar", "cancel"]):
            return await self.handle_cancel()

        else:
            return {
                "response": "Por favor responde *Sí* para confirmar o *No* para cancelar.",
                "state": self.state.value
            }

    async def assign_driver(self) -> Dict:
        """
        Asigna un conductor disponible
        """
        self.state = TaxiState.ASSIGNING_DRIVER

        # TODO: Integrar con DriverAssignmentEngine para encontrar conductor real
        # Por ahora, conductor de ejemplo

        # Simular que encontramos conductor
        self.context["driver_id"] = "driver_001"
        self.context["driver_info"] = {
            "name": "Juan Pérez",
            "phone": "+52-555-1234-5678",
            "vehicle": "Nissan Versa Blanco",
            "plates": "ABC-1234",
            "rating": 4.9
        }
        self.context["eta_minutes"] = 8

        # Crear registro de viaje en BD
        # TODO: Guardar en PostgreSQL
        self.context["ride_id"] = f"ride_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        self.state = TaxiState.DRIVER_ASSIGNED

        driver = self.context["driver_info"]
        rating_stars = "⭐" * int(driver["rating"])

        response = f"""¡Taxi asignado! 🚕✅

👤 *Conductor:* {driver['name']} {rating_stars}
🚗 *Vehículo:* {driver['vehicle']}
🔢 *Placas:* {driver['plates']}

⏱️ *Llega en:* {self.context['eta_minutes']} minutos

📱 *Teléfono:* {driver['phone']}

Te avisaremos cuando el conductor esté cerca."""

        # TODO: Enviar notificación al conductor

        return {
            "response": response,
            "state": self.state.value,
            "ride_id": self.context["ride_id"]
        }

    async def handle_rating(self, message: str) -> Dict:
        """
        Maneja la calificación del viaje
        """
        # Detectar estrellas o número
        stars_count = message.count("⭐")

        if stars_count >= 1 and stars_count <= 5:
            rating = stars_count
        else:
            # Intentar extraer número
            numbers = re.findall(r'\d+', message)
            if numbers:
                rating = int(numbers[0])
                if rating < 1 or rating > 5:
                    rating = 5
            else:
                rating = 5

        self.context["rating"] = rating
        self.state = TaxiState.COMPLETED

        response = f"""¡Gracias por tu calificación! {('⭐' * rating)} 😊

Tu opinión nos ayuda a mejorar.

*¿Necesitas otro taxi?*
Envía un mensaje cuando quieras."""

        # TODO: Guardar rating en BD

        return {
            "response": response,
            "state": self.state.value
        }

    async def handle_payment(self, message: str) -> Dict:
        """
        Maneja el pago (efectivo, tarjeta, etc.)
        """
        # TODO: Integrar con Stripe u otro procesador
        self.state = TaxiState.COMPLETED

        return {
            "response": "Pago procesado correctamente. ¡Gracias! 😊",
            "state": self.state.value
        }

    async def handle_cancel(self) -> Dict:
        """
        Maneja la cancelación del viaje
        """
        self.state = TaxiState.CANCELLED

        response = "Viaje cancelado. 😔\n\nCuando necesites un taxi, envíanos un mensaje."

        # TODO: Notificar al conductor si ya estaba asignado

        return {
            "response": response,
            "state": self.state.value
        }

    async def handle_help(self) -> Dict:
        """
        Proporciona ayuda sobre el servicio
        """
        help_text = """🚕 *AYUDA - Servicio de Taxi*

*Para solicitar un taxi:*
1️⃣ Dime tu destino
2️⃣ Dime tu ubicación de origen
3️⃣ Confirma el viaje
4️⃣ ¡Listo! Te asignamos conductor

*Comandos:*
• *cancelar* - Cancelar viaje
• *ayuda* - Ver esta ayuda

*Tarifas:*
• Banderazo: $50
• Por kilómetro: $8
• Por minuto: $2

¿En qué te puedo ayudar?"""

        return {
            "response": help_text,
            "state": self.state.value
        }

    def _extract_destination_from_message(self, message: str) -> Optional[str]:
        """
        Intenta extraer el destino de un mensaje como "necesito taxi al aeropuerto"
        """
        message_lower = message.lower()

        # Patrones comunes
        patterns = [
            r'(?:al?|a la|hacia|para|rumbo a?)\s+(.+)',
            r'(?:ir a?|llevar a?|voy a?)\s+(.+)',
            r'(?:necesito taxi)\s+(?:al?|a la|para)\s+(.+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, message_lower)
            if match:
                destination = match.group(1).strip()
                # Limpiar palabras de relleno
                destination = re.sub(r'\s+(por favor|porfavor|gracias).*$', '', destination)
                return destination

        return None

    def get_state(self) -> str:
        """Retorna el estado actual"""
        return self.state.value

    def get_context(self) -> Dict:
        """Retorna el contexto completo"""
        return self.context

    def to_dict(self) -> Dict:
        """Serializa el FSM a diccionario para guardar en sesión"""
        return {
            "tenant_id": self.tenant_id,
            "session_id": self.session_id,
            "state": self.state.value,
            "context": self.context,
            "config": self.config
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "TaxiFSM":
        """Reconstruye el FSM desde un diccionario"""
        fsm = cls(
            tenant_id=data["tenant_id"],
            session_id=data["session_id"],
            config=data.get("config", {})
        )
        fsm.state = TaxiState(data["state"])
        fsm.context = data["context"]
        return fsm
