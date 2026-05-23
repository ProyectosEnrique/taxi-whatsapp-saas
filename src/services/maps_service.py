"""
Google Maps API Service

Servicios de integración con Google Maps API:
- Cálculo de rutas y distancias
- Geocoding (dirección → coordenadas)
- Reverse Geocoding (coordenadas → dirección)
- Autocompletado de direcciones
- Matriz de distancias para múltiples puntos
"""

import googlemaps
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class MapsService:
    """
    Servicio para interactuar con Google Maps API
    """

    def __init__(self, api_key: str):
        """
        Inicializa el servicio de Google Maps

        Args:
            api_key: API key de Google Maps
        """
        if not api_key:
            raise ValueError("Google Maps API key is required")

        self.gmaps = googlemaps.Client(key=api_key)
        logger.info("MapsService initialized successfully")

    def calculate_route(
        self,
        origin: Dict[str, float],
        destination: Dict[str, float],
        mode: str = "driving"
    ) -> Optional[Dict]:
        """
        Calcula la ruta entre dos puntos

        Args:
            origin: {"lat": 19.432, "lon": -99.133} o dirección string
            destination: {"lat": 19.334, "lon": -99.192} o dirección string
            mode: "driving", "walking", "bicycling", "transit"

        Returns:
            {
                "distance_km": 12.5,
                "duration_minutes": 25,
                "duration_in_traffic_minutes": 32,
                "route_polyline": "encoded_polyline_string",
                "origin_address": "Av. Juárez #123, Centro",
                "destination_address": "Ciudad Universitaria, UNAM",
                "bounds": {"northeast": {...}, "southwest": {...}},
                "steps": [...]  # Instrucciones paso a paso
            }
        """
        try:
            # Convertir coordenadas a tupla si es necesario
            if isinstance(origin, dict) and "lat" in origin:
                origin_point = (origin["lat"], origin["lon"])
            else:
                origin_point = origin

            if isinstance(destination, dict) and "lat" in destination:
                destination_point = (destination["lat"], destination["lon"])
            else:
                destination_point = destination

            # Solicitar dirección con tráfico en tiempo real
            result = self.gmaps.directions(
                origin=origin_point,
                destination=destination_point,
                mode=mode,
                departure_time=datetime.now(),  # Para tráfico en tiempo real
                traffic_model="best_guess"
            )

            if not result or len(result) == 0:
                logger.warning(f"No route found from {origin} to {destination}")
                return None

            # Extraer información de la primera ruta
            route = result[0]
            leg = route['legs'][0]

            # Duración con tráfico
            duration_in_traffic = leg.get('duration_in_traffic', leg['duration'])

            return {
                "distance_km": round(leg['distance']['value'] / 1000, 2),
                "distance_meters": leg['distance']['value'],
                "duration_minutes": round(leg['duration']['value'] / 60, 1),
                "duration_in_traffic_minutes": round(duration_in_traffic['value'] / 60, 1),
                "route_polyline": route['overview_polyline']['points'],
                "origin_address": leg['start_address'],
                "destination_address": leg['end_address'],
                "bounds": route['bounds'],
                "steps": self._extract_steps(leg['steps'])
            }

        except Exception as e:
            logger.error(f"Error calculating route: {e}")
            return None

    def geocode_address(self, address: str) -> Optional[Dict]:
        """
        Convierte una dirección en coordenadas

        Args:
            address: "Av. Juárez #123, Centro, CDMX"

        Returns:
            {
                "lat": 19.432608,
                "lon": -99.133209,
                "formatted_address": "Av. Pres. Juárez 123, Centro...",
                "place_id": "ChIJ...",
                "address_components": [...]
            }
        """
        try:
            result = self.gmaps.geocode(address)

            if not result:
                logger.warning(f"No geocoding results for: {address}")
                return None

            location = result[0]['geometry']['location']

            return {
                "lat": location['lat'],
                "lon": location['lng'],
                "formatted_address": result[0]['formatted_address'],
                "place_id": result[0]['place_id'],
                "address_components": result[0]['address_components'],
                "location_type": result[0]['geometry']['location_type']
            }

        except Exception as e:
            logger.error(f"Error geocoding address '{address}': {e}")
            return None

    def reverse_geocode(self, lat: float, lon: float) -> Optional[str]:
        """
        Convierte coordenadas en dirección legible

        Args:
            lat: Latitud
            lon: Longitud

        Returns:
            "Av. Insurgentes Sur 3000, Coyoacán, 04510 CDMX"
        """
        try:
            result = self.gmaps.reverse_geocode((lat, lon))

            if not result:
                logger.warning(f"No reverse geocoding results for: {lat}, {lon}")
                return None

            # Retornar la dirección más específica
            return result[0]['formatted_address']

        except Exception as e:
            logger.error(f"Error reverse geocoding ({lat}, {lon}): {e}")
            return None

    def reverse_geocode_detailed(self, lat: float, lon: float) -> Optional[Dict]:
        """
        Convierte coordenadas en información detallada de dirección

        Returns:
            {
                "formatted_address": "...",
                "street": "Av. Insurgentes Sur",
                "street_number": "3000",
                "neighborhood": "Coyoacán",
                "city": "Ciudad de México",
                "state": "CDMX",
                "postal_code": "04510",
                "country": "México"
            }
        """
        try:
            result = self.gmaps.reverse_geocode((lat, lon))

            if not result:
                return None

            address_components = result[0]['address_components']

            # Extraer componentes
            components = {}
            for component in address_components:
                types = component['types']

                if 'street_number' in types:
                    components['street_number'] = component['long_name']
                elif 'route' in types:
                    components['street'] = component['long_name']
                elif 'neighborhood' in types or 'sublocality' in types:
                    components['neighborhood'] = component['long_name']
                elif 'locality' in types:
                    components['city'] = component['long_name']
                elif 'administrative_area_level_1' in types:
                    components['state'] = component['short_name']
                elif 'postal_code' in types:
                    components['postal_code'] = component['long_name']
                elif 'country' in types:
                    components['country'] = component['long_name']

            components['formatted_address'] = result[0]['formatted_address']

            return components

        except Exception as e:
            logger.error(f"Error detailed reverse geocoding: {e}")
            return None

    def autocomplete(self, input_text: str, location: Dict = None, radius: int = 50000) -> List[Dict]:
        """
        Autocompletado de direcciones

        Args:
            input_text: "Av. Insurgentes"
            location: {"lat": 19.432, "lon": -99.133} (opcional, para bias geográfico)
            radius: Radio en metros para búsqueda (default 50km)

        Returns:
            [
                {
                    "description": "Av. Insurgentes Sur, CDMX",
                    "place_id": "ChIJ...",
                    "types": ["route", "geocode"]
                },
                ...
            ]
        """
        try:
            location_point = None
            if location:
                location_point = (location["lat"], location["lon"])

            result = self.gmaps.places_autocomplete(
                input_text=input_text,
                location=location_point,
                radius=radius
            )

            return [
                {
                    "description": place['description'],
                    "place_id": place['place_id'],
                    "types": place['types']
                }
                for place in result
            ]

        except Exception as e:
            logger.error(f"Error in autocomplete: {e}")
            return []

    def distance_matrix(
        self,
        origins: List[Dict],
        destinations: List[Dict],
        mode: str = "driving"
    ) -> Optional[Dict]:
        """
        Calcula distancias y tiempos entre múltiples orígenes y destinos

        Útil para encontrar conductor más cercano

        Args:
            origins: [{"lat": 19.4, "lon": -99.1}, ...]
            destinations: [{"lat": 19.3, "lon": -99.2}, ...]

        Returns:
            {
                "rows": [
                    {
                        "elements": [
                            {
                                "distance_km": 10.5,
                                "duration_minutes": 20
                            },
                            ...
                        ]
                    },
                    ...
                ]
            }
        """
        try:
            # Convertir coordenadas a tuplas
            origin_points = [(o["lat"], o["lon"]) for o in origins]
            destination_points = [(d["lat"], d["lon"]) for d in destinations]

            result = self.gmaps.distance_matrix(
                origins=origin_points,
                destinations=destination_points,
                mode=mode,
                departure_time=datetime.now()
            )

            # Procesar resultado
            rows = []
            for row in result['rows']:
                elements = []
                for element in row['elements']:
                    if element['status'] == 'OK':
                        elements.append({
                            "distance_km": round(element['distance']['value'] / 1000, 2),
                            "duration_minutes": round(element['duration']['value'] / 60, 1),
                            "status": "OK"
                        })
                    else:
                        elements.append({
                            "status": element['status']
                        })
                rows.append({"elements": elements})

            return {"rows": rows}

        except Exception as e:
            logger.error(f"Error in distance matrix: {e}")
            return None

    def find_place(self, query: str, location: Dict = None) -> Optional[Dict]:
        """
        Busca un lugar por nombre (restaurante, aeropuerto, etc.)

        Args:
            query: "Aeropuerto Internacional de la Ciudad de México"
            location: {"lat": 19.432, "lon": -99.133} (opcional)

        Returns:
            {
                "name": "Aeropuerto Internacional...",
                "lat": 19.4363,
                "lon": -99.0721,
                "formatted_address": "...",
                "place_id": "..."
            }
        """
        try:
            location_point = None
            if location:
                location_point = (location["lat"], location["lon"])

            result = self.gmaps.find_place(
                input=query,
                input_type="textquery",
                location_bias=f"circle:50000@{location_point[0]},{location_point[1]}" if location_point else None,
                fields=["name", "geometry", "formatted_address", "place_id"]
            )

            if not result or not result.get('candidates'):
                return None

            place = result['candidates'][0]
            location = place['geometry']['location']

            return {
                "name": place.get('name'),
                "lat": location['lat'],
                "lon": location['lng'],
                "formatted_address": place.get('formatted_address'),
                "place_id": place['place_id']
            }

        except Exception as e:
            logger.error(f"Error finding place '{query}': {e}")
            return None

    def _extract_steps(self, steps: List[Dict]) -> List[Dict]:
        """
        Extrae instrucciones simplificadas de navegación
        """
        simplified_steps = []

        for step in steps:
            simplified_steps.append({
                "instruction": step['html_instructions'],
                "distance_km": round(step['distance']['value'] / 1000, 2),
                "duration_minutes": round(step['duration']['value'] / 60, 1)
            })

        return simplified_steps

    def get_place_details(self, place_id: str) -> Optional[Dict]:
        """
        Obtiene detalles completos de un lugar por su place_id

        Args:
            place_id: ID del lugar de Google

        Returns:
            Información detallada del lugar
        """
        try:
            result = self.gmaps.place(place_id=place_id)

            if result['status'] != 'OK':
                return None

            place = result['result']
            location = place['geometry']['location']

            return {
                "name": place.get('name'),
                "lat": location['lat'],
                "lon": location['lng'],
                "formatted_address": place.get('formatted_address'),
                "phone": place.get('formatted_phone_number'),
                "rating": place.get('rating'),
                "types": place.get('types'),
                "website": place.get('website')
            }

        except Exception as e:
            logger.error(f"Error getting place details: {e}")
            return None


# Clase de utilidades para cálculos geográficos sin API
import math

class GeoUtils:
    """
    Utilidades para cálculos geográficos sin necesidad de API
    """

    @staticmethod
    def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
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

    @staticmethod
    def is_within_radius(
        center_lat: float,
        center_lon: float,
        point_lat: float,
        point_lon: float,
        radius_km: float
    ) -> bool:
        """
        Verifica si un punto está dentro de un radio

        Args:
            center_lat, center_lon: Centro del círculo
            point_lat, point_lon: Punto a verificar
            radius_km: Radio en kilómetros

        Returns:
            True si el punto está dentro del radio
        """
        distance = GeoUtils.haversine_distance(
            center_lat, center_lon,
            point_lat, point_lon
        )

        return distance <= radius_km

    @staticmethod
    def bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calcula el rumbo (bearing) entre dos puntos en grados

        Returns:
            Ángulo en grados (0-360) donde 0=Norte, 90=Este, etc.
        """
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        dlon = math.radians(lon2 - lon1)

        y = math.sin(dlon) * math.cos(lat2_rad)
        x = (math.cos(lat1_rad) * math.sin(lat2_rad) -
             math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(dlon))

        bearing = math.atan2(y, x)
        bearing = math.degrees(bearing)
        bearing = (bearing + 360) % 360

        return bearing
