"""
Driver Assignment Engine

Motor para asignar conductores a viajes:
- Encuentra conductor más cercano disponible
- Considera rating, tipo de vehículo, preferencias
- Algoritmo de asignación eficiente
- Manejo de rechazos y reasignación
"""

import math
from typing import List, Optional, Dict, Tuple
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class DriverAssignmentEngine:
    """
    Motor de asignación de conductores a viajes
    """

    def __init__(self, db_connection=None, maps_service=None):
        """
        Inicializa el motor de asignación

        Args:
            db_connection: Conexión a base de datos
            maps_service: Servicio de Google Maps para calcular ETAs
        """
        self.db = db_connection
        self.maps = maps_service

    async def find_best_driver(
        self,
        pickup_location: Dict[str, float],
        tenant_id: str,
        ride_requirements: Dict = None
    ) -> Optional[Dict]:
        """
        Encuentra el mejor conductor para un viaje

        Args:
            pickup_location: {"lat": 19.432, "lon": -99.133}
            tenant_id: ID del tenant (sitio de taxis)
            ride_requirements: {
                "vehicle_type": "sedan",  # sedan, suv, van
                "min_rating": 4.0,
                "max_distance_km": 10.0,  # Máxima distancia del conductor
                "luggage_space": False,
                "wheelchair_accessible": False
            }

        Returns:
            {
                "driver_id": "driver_001",
                "name": "Juan Pérez",
                "phone": "+52-555-1234",
                "vehicle_info": {...},
                "current_location": {"lat": ..., "lon": ...},
                "distance_km": 2.5,
                "eta_minutes": 8,
                "rating": 4.9,
                "total_rides": 1523
            }
        """
        ride_requirements = ride_requirements or {}

        # 1. Obtener conductores disponibles
        available_drivers = await self._get_available_drivers(tenant_id, ride_requirements)

        if not available_drivers:
            logger.warning(f"No available drivers found for tenant: {tenant_id}")
            return None

        # 2. Calcular distancia a cada conductor
        drivers_with_distance = []

        for driver in available_drivers:
            # Calcular distancia en línea recta (Haversine)
            distance_km = self._haversine_distance(
                pickup_location["lat"],
                pickup_location["lon"],
                driver["current_lat"],
                driver["current_lon"]
            )

            # Filtrar por distancia máxima
            max_distance = ride_requirements.get("max_distance_km", 15.0)
            if distance_km > max_distance:
                continue

            # Estimar ETA (aproximado: distancia / velocidad promedio en ciudad ~30km/h)
            eta_minutes = (distance_km / 30.0) * 60

            drivers_with_distance.append({
                **driver,
                "distance_km": round(distance_km, 2),
                "eta_minutes": round(eta_minutes)
            })

        if not drivers_with_distance:
            logger.warning("No drivers within acceptable distance")
            return None

        # 3. Ordenar por algoritmo de scoring
        scored_drivers = self._score_drivers(drivers_with_distance, pickup_location)

        # 4. Retornar el mejor conductor
        best_driver = scored_drivers[0]

        logger.info(f"Best driver assigned: {best_driver['driver_id']} ({best_driver['name']})")

        return best_driver

    async def find_multiple_drivers(
        self,
        pickup_location: Dict[str, float],
        tenant_id: str,
        count: int = 3,
        ride_requirements: Dict = None
    ) -> List[Dict]:
        """
        Encuentra los N mejores conductores disponibles

        Útil para mostrar opciones al cliente o tener backups

        Returns:
            Lista de conductores ordenados por score
        """
        ride_requirements = ride_requirements or {}

        available_drivers = await self._get_available_drivers(tenant_id, ride_requirements)

        if not available_drivers:
            return []

        # Calcular distancias
        drivers_with_distance = []

        for driver in available_drivers:
            distance_km = self._haversine_distance(
                pickup_location["lat"],
                pickup_location["lon"],
                driver["current_lat"],
                driver["current_lon"]
            )

            max_distance = ride_requirements.get("max_distance_km", 15.0)
            if distance_km > max_distance:
                continue

            eta_minutes = (distance_km / 30.0) * 60

            drivers_with_distance.append({
                **driver,
                "distance_km": round(distance_km, 2),
                "eta_minutes": round(eta_minutes)
            })

        # Ordenar por score
        scored_drivers = self._score_drivers(drivers_with_distance, pickup_location)

        # Retornar top N
        return scored_drivers[:count]

    def _score_drivers(self, drivers: List[Dict], pickup_location: Dict) -> List[Dict]:
        """
        Asigna un score a cada conductor y los ordena

        Criterios de scoring:
        - Distancia (60% del score) - Más cercano es mejor
        - Rating (30% del score) - Mayor rating es mejor
        - Tiempo de respuesta histórico (10% del score)

        Returns:
            Lista ordenada por score (mayor a menor)
        """
        scored_drivers = []

        for driver in drivers:
            # 1. Score de distancia (inverso: menos distancia = mayor score)
            # Normalizar: 0km = 100 pts, 10km = 0 pts
            distance_score = max(0, 100 - (driver["distance_km"] * 10))

            # 2. Score de rating (0-5 estrellas → 0-100 pts)
            rating_score = (driver.get("rating", 4.0) / 5.0) * 100

            # 3. Score de aceptación (tasa de aceptación de viajes)
            acceptance_rate = driver.get("acceptance_rate", 0.9)
            acceptance_score = acceptance_rate * 100

            # Calcular score total ponderado
            total_score = (
                distance_score * 0.60 +      # 60% distancia
                rating_score * 0.30 +        # 30% rating
                acceptance_score * 0.10      # 10% aceptación
            )

            scored_drivers.append({
                **driver,
                "score": round(total_score, 2),
                "score_breakdown": {
                    "distance_score": round(distance_score, 2),
                    "rating_score": round(rating_score, 2),
                    "acceptance_score": round(acceptance_score, 2)
                }
            })

        # Ordenar por score descendente
        scored_drivers.sort(key=lambda x: x["score"], reverse=True)

        return scored_drivers

    async def _get_available_drivers(
        self,
        tenant_id: str,
        requirements: Dict
    ) -> List[Dict]:
        """
        Obtiene conductores disponibles de la base de datos

        Returns:
            Lista de conductores con ubicación y metadata
        """
        # TODO: Consultar PostgreSQL
        # Por ahora, conductores de ejemplo

        mock_drivers = [
            {
                "driver_id": "driver_001",
                "name": "Juan Pérez",
                "phone": "+52-555-1234-5678",
                "vehicle_info": {
                    "type": "sedan",
                    "brand": "Nissan",
                    "model": "Versa",
                    "year": 2022,
                    "color": "Blanco",
                    "plates": "ABC-1234"
                },
                "current_lat": 19.428,
                "current_lon": -99.138,
                "rating": 4.9,
                "total_rides": 1523,
                "acceptance_rate": 0.95,
                "status": "available",
                "last_updated": datetime.now().isoformat()
            },
            {
                "driver_id": "driver_002",
                "name": "María González",
                "phone": "+52-555-8765-4321",
                "vehicle_info": {
                    "type": "sedan",
                    "brand": "Toyota",
                    "model": "Corolla",
                    "year": 2023,
                    "color": "Gris",
                    "plates": "XYZ-5678"
                },
                "current_lat": 19.435,
                "current_lon": -99.130,
                "rating": 4.8,
                "total_rides": 892,
                "acceptance_rate": 0.92,
                "status": "available",
                "last_updated": datetime.now().isoformat()
            },
            {
                "driver_id": "driver_003",
                "name": "Carlos Ramírez",
                "phone": "+52-555-9999-8888",
                "vehicle_info": {
                    "type": "suv",
                    "brand": "Mazda",
                    "model": "CX-5",
                    "year": 2021,
                    "color": "Negro",
                    "plates": "DEF-9012"
                },
                "current_lat": 19.440,
                "current_lon": -99.125,
                "rating": 4.7,
                "total_rides": 654,
                "acceptance_rate": 0.88,
                "status": "available",
                "last_updated": datetime.now().isoformat()
            }
        ]

        # Filtrar por tipo de vehículo si se especifica
        vehicle_type = requirements.get("vehicle_type")
        if vehicle_type:
            mock_drivers = [
                d for d in mock_drivers
                if d["vehicle_info"]["type"] == vehicle_type
            ]

        # Filtrar por rating mínimo
        min_rating = requirements.get("min_rating", 0.0)
        mock_drivers = [
            d for d in mock_drivers
            if d["rating"] >= min_rating
        ]

        return mock_drivers

    async def assign_ride_to_driver(
        self,
        ride_id: str,
        driver_id: str,
        tenant_id: str
    ) -> bool:
        """
        Asigna un viaje a un conductor en la BD

        Returns:
            True si la asignación fue exitosa
        """
        # TODO: Actualizar en PostgreSQL
        # - Cambiar status del conductor a "busy"
        # - Asociar ride_id con driver_id
        # - Enviar notificación al conductor

        logger.info(f"Ride {ride_id} assigned to driver {driver_id}")
        return True

    async def handle_driver_rejection(
        self,
        ride_id: str,
        driver_id: str,
        pickup_location: Dict[str, float],
        tenant_id: str
    ) -> Optional[Dict]:
        """
        Maneja el rechazo de un viaje por parte del conductor

        Busca otro conductor disponible automáticamente

        Returns:
            Nuevo conductor asignado o None
        """
        logger.warning(f"Driver {driver_id} rejected ride {ride_id}")

        # Registrar rechazo en BD
        # TODO: Actualizar acceptance_rate del conductor

        # Buscar siguiente mejor conductor
        # Excluir al conductor que rechazó
        next_driver = await self.find_best_driver(
            pickup_location=pickup_location,
            tenant_id=tenant_id,
            ride_requirements={"excluded_drivers": [driver_id]}
        )

        return next_driver

    async def update_driver_location(
        self,
        driver_id: str,
        lat: float,
        lon: float,
        tenant_id: str
    ):
        """
        Actualiza la ubicación del conductor

        Se llama periódicamente desde la app del conductor
        """
        # TODO: Actualizar en PostgreSQL
        logger.debug(f"Updated location for driver {driver_id}: {lat}, {lon}")

    async def get_driver_status(self, driver_id: str) -> Dict:
        """
        Obtiene el estado actual de un conductor
        """
        # TODO: Consultar BD
        return {
            "driver_id": driver_id,
            "status": "available",  # available, busy, offline
            "current_ride_id": None,
            "current_location": {"lat": 19.432, "lon": -99.133}
        }

    def _haversine_distance(
        self,
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float
    ) -> float:
        """
        Calcula distancia en línea recta entre dos puntos (km)
        usando la fórmula de Haversine

        Args:
            lat1, lon1: Coordenadas del punto 1
            lat2, lon2: Coordenadas del punto 2

        Returns:
            Distancia en kilómetros
        """
        R = 6371  # Radio de la Tierra en km

        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)

        a = (math.sin(dlat/2) * math.sin(dlat/2) +
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
             math.sin(dlon/2) * math.sin(dlon/2))

        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

        return R * c


class RideQueue:
    """
    Cola de viajes pendientes de asignación

    Útil para períodos de alta demanda cuando no hay conductores disponibles
    """

    def __init__(self):
        self.queue: List[Dict] = []

    def add_ride(self, ride_info: Dict):
        """
        Agrega un viaje a la cola
        """
        ride_info["queued_at"] = datetime.now()
        self.queue.append(ride_info)
        logger.info(f"Ride {ride_info['ride_id']} added to queue")

    def get_next_ride(self) -> Optional[Dict]:
        """
        Obtiene el siguiente viaje de la cola (FIFO)
        """
        if not self.queue:
            return None

        ride = self.queue.pop(0)
        logger.info(f"Ride {ride['ride_id']} retrieved from queue")
        return ride

    def get_queue_length(self) -> int:
        """
        Retorna cantidad de viajes en espera
        """
        return len(self.queue)

    def remove_ride(self, ride_id: str) -> bool:
        """
        Remueve un viaje de la cola (cancelación)
        """
        original_length = len(self.queue)
        self.queue = [r for r in self.queue if r["ride_id"] != ride_id]

        removed = original_length > len(self.queue)
        if removed:
            logger.info(f"Ride {ride_id} removed from queue")

        return removed

    def get_estimated_wait_time(self) -> int:
        """
        Estima tiempo de espera en minutos basado en la cola
        """
        # Aproximación: 5 minutos por viaje en la cola
        return len(self.queue) * 5
