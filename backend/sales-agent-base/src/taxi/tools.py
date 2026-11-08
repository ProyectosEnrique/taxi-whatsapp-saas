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


def mark_ride_sent_if_success(session: dict, name: str, result_str: str) -> None:
    """Si `crear_viaje` tuvo éxito, guarda el resultado en la sesión para que el
    llamador pueda devolver la confirmación real en vez de un error genérico
    si el proveedor LLM falla en una ronda posterior (el viaje ya es real e
    irreversible — no debe reintentarse ni perderse de la respuesta al cliente)."""
    if name != "crear_viaje":
        return
    try:
        data = json.loads(result_str)
    except Exception:
        return
    if data.get("success"):
        session["_ride_sent"] = True
        session["_ride_data"] = data


def run_tool(name: str, args: dict, phone: str, session: dict | None = None) -> str:
    if name == "buscar_lugar":
        # Buscar cerca del pasajero: su ubicación (GPS) o, si no la mandó, el último
        # lugar ya encontrado en esta conversación (origen y destino suelen estar en
        # la misma ciudad). Así "Hidalgo 45" sale en Salvatierra si está en Salvatierra.
        ctx = session.setdefault("context", {}) if session is not None else {}
        near = ctx.get("last_gps") or ctx.get("anchor")
        results = client.geocode(args.get("query", ""), near=near)
        if not results:
            return json.dumps({"error": "No encontré ese lugar con precisión. Pide una calle con número, "
                                        "un lugar de referencia cercano o que comparta su ubicación."})
        ctx["anchor"] = {"lat": results[0]["lat"], "lng": results[0]["lng"]}
        return json.dumps({"results": [
            {k: r.get(k) for k in ("name", "colonia", "ciudad", "aproximado", "lat", "lng", "short_address")}
            for r in results[:3]
        ]})

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
