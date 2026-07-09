"""
Herramientas (function calling) que el LLM puede invocar: definiciones
en formato OpenAI tools + el dispatcher que las ejecuta de verdad.
"""
import json
import logging

from . import session as sess
from . import taxi_client as client

logger = logging.getLogger(__name__)

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "buscar_lugar",
            "description": (
                "Busca un lugar o dirección por nombre o texto y devuelve resultados con coordenadas. "
                "Funciona para lugares locales, nombres de sitios conocidos (terminales, hospitales, plazas), "
                "y direcciones en otras ciudades de México. "
                "Úsalo siempre que necesites geocodificar el origen o destino del viaje."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "Nombre del lugar o dirección completa. "
                            "Ejemplos: 'Central de Autobuses de Morelia', 'Hospital General', "
                            "'Plaza de la Paz Guanajuato', 'Calle Hidalgo 45 Moroleón'."
                        ),
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "estimar_tarifa",
            "description": "Estima costo y tiempo de viaje dadas las coordenadas de origen y destino.",
            "parameters": {
                "type": "object",
                "properties": {
                    "origin_lat": {"type": "number"},
                    "origin_lng": {"type": "number"},
                    "dest_lat":   {"type": "number"},
                    "dest_lng":   {"type": "number"},
                },
                "required": ["origin_lat", "origin_lng", "dest_lat", "dest_lng"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "crear_viaje",
            "description": (
                "Crea y registra el viaje en el sistema. "
                "Llama esta función SOLO después de que el cliente confirmó la tarifa."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "origin_address": {"type": "string", "description": "Dirección de origen en texto"},
                    "origin_lat":     {"type": "number"},
                    "origin_lng":     {"type": "number"},
                    "dest_address":   {"type": "string", "description": "Dirección de destino en texto"},
                    "dest_lat":       {"type": "number"},
                    "dest_lng":       {"type": "number"},
                    "scheduled_at": {
                        "type": "string",
                        "description": (
                            "Fecha y hora ISO 8601 para viaje programado, "
                            "e.g. '2026-06-11T15:30:00'. Omitir para viaje inmediato."
                        ),
                    },
                },
                "required": [
                    "origin_address", "origin_lat", "origin_lng",
                    "dest_address", "dest_lat", "dest_lng",
                ],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ver_estado_viaje",
            "description": "Consulta el estado actual de un viaje por su ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ride_id": {
                        "type": "string",
                        "description": "ID del viaje, e.g. 'TRIP-ABC12345'",
                    }
                },
                "required": ["ride_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "cancelar_viaje",
            "description": "Cancela un viaje activo.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ride_id": {
                        "type": "string",
                        "description": "ID del viaje a cancelar",
                    }
                },
                "required": ["ride_id"],
            },
        },
    },
]


def run_tool(name: str, args: dict, phone: str) -> str:
    if name == "buscar_lugar":
        results = client.geocode(args.get("query", ""))
        if not results:
            return json.dumps({"error": "No encontré ese lugar. Pide al cliente que sea más específico o comparta su ubicación GPS."})
        return json.dumps({"results": results[:3]})

    if name == "estimar_tarifa":
        est = client.estimate(
            float(args.get("origin_lat", 0)),
            float(args.get("origin_lng", 0)),
            float(args.get("dest_lat", 0)),
            float(args.get("dest_lng", 0)),
        )
        return json.dumps(est)

    if name == "crear_viaje":
        origin = {
            "address": args.get("origin_address", ""),
            "lat":     float(args.get("origin_lat", 0)),
            "lng":     float(args.get("origin_lng", 0)),
        }
        dest = {
            "address": args.get("dest_address", ""),
            "lat":     float(args.get("dest_lat", 0)),
            "lng":     float(args.get("dest_lng", 0)),
        }
        data = client.create_ride(phone, origin, dest, args.get("scheduled_at"))
        if data:
            ride    = data.get("ride", data)
            ride_id = ride.get("ride_id") or ride.get("id") or "desconocido"
            sess.extend_ttl_for_ride(phone)
            return json.dumps({
                "success":      True,
                "ride_id":      ride_id,
                "status":       ride.get("status", "requested"),
                "fare":         ride.get("total_fare"),
                "tracking_url": f"{client.TRACKING_BASE}/seguimiento/{ride_id}",
            })
        return json.dumps({"error": "No se pudo crear el viaje. Intenta de nuevo."})

    if name == "ver_estado_viaje":
        data = client.get_ride(args.get("ride_id", ""))
        if data:
            ride = data.get("ride", data)
            return json.dumps({
                "ride_id": ride.get("ride_id"),
                "status":  ride.get("status"),
                "driver":  ride.get("driver"),
                "fare":    ride.get("total_fare"),
            })
        return json.dumps({"error": "No encontré ese viaje."})

    if name == "cancelar_viaje":
        client.cancel_ride(args.get("ride_id", ""))
        return json.dumps({"success": True, "message": "Viaje cancelado."})

    return json.dumps({"error": f"Herramienta desconocida: {name}"})
