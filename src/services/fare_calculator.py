"""
Fare Calculator Service

Calcula tarifas dinámicas para viajes de taxi basado en:
- Distancia recorrida
- Tiempo de viaje
- Hora del día (hora pico)
- Día de la semana
- Condiciones especiales (aeropuerto, peajes, etc.)
- Promociones y descuentos
"""

from datetime import datetime, time
from typing import Dict, Optional, List
import logging

logger = logging.getLogger(__name__)


class FareCalculator:
    """
    Calculadora de tarifas para servicio de taxi
    """

    def __init__(self, tenant_id: str, config: Dict = None):
        """
        Inicializa la calculadora con configuración del tenant

        Args:
            tenant_id: ID del tenant (sitio de taxis)
            config: Configuración personalizada de tarifas
        """
        self.tenant_id = tenant_id

        # Configuración por defecto
        self.config = {
            "base_fare": 50.0,  # Banderazo
            "per_km_rate": 8.0,  # Por kilómetro
            "per_minute_rate": 2.0,  # Por minuto (tráfico)
            "minimum_fare": 70.0,  # Tarifa mínima
            "currency": "MXN",
            "currency_symbol": "$",

            # Recargos
            "surge_pricing": {
                "enabled": True,
                "peak_hours_multiplier": 1.3,  # 30% más en hora pico
                "late_night_multiplier": 1.5,  # 50% más en madrugada
                "weekend_multiplier": 1.2,  # 20% más en fin de semana
            },

            # Horarios de hora pico
            "peak_hours": [
                {"start": "07:00", "end": "09:30"},  # Mañana
                {"start": "18:00", "end": "21:00"},  # Tarde
            ],

            # Horarios de madrugada
            "late_night_hours": {
                "start": "23:00",
                "end": "05:00"
            },

            # Recargos especiales
            "special_charges": {
                "airport_pickup": 30.0,
                "airport_dropoff": 30.0,
                "toll_roads": 0.0,  # Se agrega el costo real
                "extra_passenger": 10.0,  # Por pasajero adicional (más de 2)
                "luggage": 5.0,  # Por maleta grande
            },

            # Descuentos
            "discounts": {
                "frequent_rider": 0.10,  # 10% para clientes frecuentes
                "corporate": 0.15,  # 15% para corporativos
                "promo_code": 0.20,  # 20% con código promocional
            }
        }

        # Sobrescribir con configuración personalizada
        if config:
            self.config.update(config)

        logger.info(f"FareCalculator initialized for tenant: {tenant_id}")

    def calculate(
        self,
        distance_km: float,
        duration_minutes: float,
        pickup_time: datetime = None,
        special_conditions: Dict = None
    ) -> Dict:
        """
        Calcula la tarifa total del viaje

        Args:
            distance_km: Distancia en kilómetros
            duration_minutes: Duración en minutos
            pickup_time: Hora de inicio del viaje (default: now)
            special_conditions: Condiciones especiales {
                "airport_pickup": bool,
                "airport_dropoff": bool,
                "extra_passengers": int,
                "luggage_count": int,
                "promo_code": str,
                "customer_type": str  # "frequent", "corporate", "new"
            }

        Returns:
            {
                "base_fare": 50.0,
                "distance_charge": 100.0,
                "time_charge": 50.0,
                "surge_charge": 60.0,
                "special_charges": 30.0,
                "subtotal": 290.0,
                "discount": 29.0,
                "total": 261.0,
                "currency": "MXN",
                "breakdown": [...]  # Desglose detallado
            }
        """
        if pickup_time is None:
            pickup_time = datetime.now()

        special_conditions = special_conditions or {}

        # 1. Tarifa base (banderazo)
        base_fare = self.config["base_fare"]

        # 2. Cargo por distancia
        distance_charge = distance_km * self.config["per_km_rate"]

        # 3. Cargo por tiempo (tráfico)
        time_charge = duration_minutes * self.config["per_minute_rate"]

        # 4. Subtotal antes de recargos
        subtotal = base_fare + distance_charge + time_charge

        # 5. Recargos dinámicos (surge pricing)
        surge_multiplier = self._get_surge_multiplier(pickup_time)
        surge_charge = 0.0

        if surge_multiplier > 1.0:
            surge_charge = subtotal * (surge_multiplier - 1.0)
            subtotal += surge_charge

        # 6. Recargos especiales
        special_charges_total = 0.0
        special_charges_breakdown = []

        if special_conditions.get("airport_pickup"):
            charge = self.config["special_charges"]["airport_pickup"]
            special_charges_total += charge
            special_charges_breakdown.append({"type": "Recogida en aeropuerto", "amount": charge})

        if special_conditions.get("airport_dropoff"):
            charge = self.config["special_charges"]["airport_dropoff"]
            special_charges_total += charge
            special_charges_breakdown.append({"type": "Destino aeropuerto", "amount": charge})

        extra_passengers = special_conditions.get("extra_passengers", 0)
        if extra_passengers > 2:
            charge = (extra_passengers - 2) * self.config["special_charges"]["extra_passenger"]
            special_charges_total += charge
            special_charges_breakdown.append({"type": f"Pasajeros extra ({extra_passengers-2})", "amount": charge})

        luggage_count = special_conditions.get("luggage_count", 0)
        if luggage_count > 0:
            charge = luggage_count * self.config["special_charges"]["luggage"]
            special_charges_total += charge
            special_charges_breakdown.append({"type": f"Equipaje ({luggage_count})", "amount": charge})

        toll_cost = special_conditions.get("toll_roads", 0.0)
        if toll_cost > 0:
            special_charges_total += toll_cost
            special_charges_breakdown.append({"type": "Peajes", "amount": toll_cost})

        subtotal += special_charges_total

        # 7. Descuentos
        discount_amount = 0.0
        discount_type = None

        promo_code = special_conditions.get("promo_code")
        customer_type = special_conditions.get("customer_type", "new")

        if promo_code:
            # TODO: Validar código promocional en BD
            discount_rate = self.config["discounts"].get("promo_code", 0)
            discount_amount = subtotal * discount_rate
            discount_type = f"Código promocional: {promo_code}"

        elif customer_type == "frequent":
            discount_rate = self.config["discounts"]["frequent_rider"]
            discount_amount = subtotal * discount_rate
            discount_type = "Cliente frecuente"

        elif customer_type == "corporate":
            discount_rate = self.config["discounts"]["corporate"]
            discount_amount = subtotal * discount_rate
            discount_type = "Cuenta corporativa"

        # 8. Total final
        total = subtotal - discount_amount

        # 9. Aplicar tarifa mínima
        if total < self.config["minimum_fare"]:
            total = self.config["minimum_fare"]

        # 10. Redondear
        total = round(total, 2)

        # Construir respuesta
        result = {
            "base_fare": round(base_fare, 2),
            "distance_charge": round(distance_charge, 2),
            "time_charge": round(time_charge, 2),
            "surge_multiplier": surge_multiplier,
            "surge_charge": round(surge_charge, 2),
            "special_charges": round(special_charges_total, 2),
            "special_charges_breakdown": special_charges_breakdown,
            "subtotal": round(subtotal, 2),
            "discount": round(discount_amount, 2),
            "discount_type": discount_type,
            "total": total,
            "minimum_fare_applied": total == self.config["minimum_fare"],
            "currency": self.config["currency"],
            "currency_symbol": self.config["currency_symbol"],
            "breakdown": self._generate_breakdown(
                base_fare, distance_charge, time_charge, surge_charge,
                special_charges_breakdown, discount_amount, discount_type
            )
        }

        logger.info(f"Fare calculated: {distance_km}km, {duration_minutes}min = {total} {self.config['currency']}")

        return result

    def _get_surge_multiplier(self, pickup_time: datetime) -> float:
        """
        Calcula el multiplicador de surge pricing según la hora

        Returns:
            1.0 = sin recargo, >1.0 = con recargo
        """
        if not self.config["surge_pricing"]["enabled"]:
            return 1.0

        time_of_day = pickup_time.time()
        day_of_week = pickup_time.weekday()  # 0=Monday, 6=Sunday

        # Madrugada (11pm - 5am)
        if self._is_late_night(time_of_day):
            return self.config["surge_pricing"]["late_night_multiplier"]

        # Hora pico (7-9:30am, 6-9pm)
        if self._is_peak_hour(time_of_day):
            multiplier = self.config["surge_pricing"]["peak_hours_multiplier"]

            # Extra en fin de semana
            if day_of_week >= 5:  # Sábado o Domingo
                multiplier *= self.config["surge_pricing"]["weekend_multiplier"]

            return multiplier

        # Fin de semana normal
        if day_of_week >= 5:
            return self.config["surge_pricing"]["weekend_multiplier"]

        # Sin recargo
        return 1.0

    def _is_peak_hour(self, time_of_day: time) -> bool:
        """
        Verifica si está en hora pico
        """
        for peak in self.config["peak_hours"]:
            start = datetime.strptime(peak["start"], "%H:%M").time()
            end = datetime.strptime(peak["end"], "%H:%M").time()

            if start <= time_of_day <= end:
                return True

        return False

    def _is_late_night(self, time_of_day: time) -> bool:
        """
        Verifica si está en horario de madrugada
        """
        late_night = self.config["late_night_hours"]
        start = datetime.strptime(late_night["start"], "%H:%M").time()
        end = datetime.strptime(late_night["end"], "%H:%M").time()

        # Manejar caso donde el rango cruza medianoche
        if start > end:
            return time_of_day >= start or time_of_day <= end
        else:
            return start <= time_of_day <= end

    def _generate_breakdown(
        self,
        base_fare: float,
        distance_charge: float,
        time_charge: float,
        surge_charge: float,
        special_charges: List[Dict],
        discount: float,
        discount_type: str
    ) -> List[str]:
        """
        Genera desglose legible de la tarifa
        """
        breakdown = []

        breakdown.append(f"Banderazo: ${base_fare:.2f}")
        breakdown.append(f"Por distancia: ${distance_charge:.2f}")
        breakdown.append(f"Por tiempo: ${time_charge:.2f}")

        if surge_charge > 0:
            breakdown.append(f"Recargo de hora: ${surge_charge:.2f}")

        for charge in special_charges:
            breakdown.append(f"{charge['type']}: ${charge['amount']:.2f}")

        if discount > 0 and discount_type:
            breakdown.append(f"Descuento ({discount_type}): -${discount:.2f}")

        return breakdown

    def estimate_fare_range(
        self,
        distance_km: float,
        duration_minutes: float
    ) -> Dict:
        """
        Estima un rango de tarifa (mínimo y máximo)

        Útil para mostrar al usuario antes de confirmar

        Returns:
            {
                "min": 180.0,
                "max": 280.0,
                "typical": 220.0
            }
        """
        # Tarifa normal (sin recargos)
        normal_fare = self.calculate(distance_km, duration_minutes)["total"]

        # Tarifa en hora pico
        peak_time = datetime.now().replace(hour=8, minute=0)  # 8am
        peak_fare = self.calculate(distance_km, duration_minutes, peak_time)["total"]

        # Tarifa en madrugada
        late_night_time = datetime.now().replace(hour=2, minute=0)  # 2am
        late_night_fare = self.calculate(distance_km, duration_minutes, late_night_time)["total"]

        return {
            "min": round(normal_fare, 2),
            "max": round(max(peak_fare, late_night_fare), 2),
            "typical": round(normal_fare, 2),
            "currency": self.config["currency"]
        }

    def get_config(self) -> Dict:
        """
        Retorna la configuración actual de tarifas
        """
        return self.config.copy()

    def update_config(self, new_config: Dict):
        """
        Actualiza la configuración de tarifas
        """
        self.config.update(new_config)
        logger.info(f"Fare configuration updated for tenant: {self.tenant_id}")


# Utilidades para promociones y descuentos
class PromoCodeValidator:
    """
    Validador de códigos promocionales
    """

    def __init__(self, db_connection=None):
        self.db = db_connection

    async def validate_promo_code(self, code: str, customer_phone: str, tenant_id: str) -> Dict:
        """
        Valida un código promocional

        Returns:
            {
                "valid": True,
                "discount_rate": 0.20,
                "discount_type": "percentage",  # "percentage" o "fixed_amount"
                "discount_value": 20.0,
                "max_discount": 100.0,
                "expires_at": "2026-02-01",
                "usage_limit": 1,
                "times_used": 0
            }
        """
        # TODO: Consultar base de datos
        # Por ahora, códigos de ejemplo

        promo_codes = {
            "BIENVENIDO": {
                "valid": True,
                "discount_rate": 0.20,
                "discount_type": "percentage",
                "discount_value": 20.0,
                "max_discount": 100.0,
                "description": "20% de descuento en tu primer viaje"
            },
            "AIRPORT50": {
                "valid": True,
                "discount_rate": 0.0,
                "discount_type": "fixed_amount",
                "discount_value": 50.0,
                "description": "$50 de descuento en viajes al aeropuerto"
            }
        }

        code_upper = code.upper()

        if code_upper in promo_codes:
            return promo_codes[code_upper]
        else:
            return {"valid": False, "error": "Código no válido"}
