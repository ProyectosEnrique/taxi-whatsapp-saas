"""
TaxiAgent — Agente LLM para reserva de taxis via WhatsApp.
Usa Groq (llama-3.3-70b) con function calling en lugar de FSM.
"""
import json
import logging
import os
import re
from typing import Optional

import httpx

try:
    import redis as _redis_lib
    _redis_client = _redis_lib.from_url(
        os.getenv("REDIS_URL", ""), decode_responses=True
    ) if os.getenv("REDIS_URL") else None
except Exception:
    _redis_client = None

logger = logging.getLogger(__name__)

_SESSION_TTL           = 1800   # 30 min sin actividad → conversación vence
_SESSION_TTL_WITH_RIDE = 86400  # 24 h una vez que hay viaje confirmado
_MAX_HISTORY           = 20     # mensajes a retener por sesión
_GPS_RE       = re.compile(r'^\[GPS:([-\d.]+),([-\d.]+)(?::(.+))?\]$')

GROQ_API_KEY      = os.getenv("GROQ_API_KEY", "")
CEREBRAS_API_KEY  = os.getenv("CEREBRAS_API_KEY", "")
API_BASE          = os.getenv("MENU_SERVICE_URL", "http://taxi-api:5011")
WHATSAPP_SECRET   = os.getenv("WHATSAPP_SECRET", "")
CUSTOMER_APP_URL  = os.getenv("CUSTOMER_APP_URL", "https://taxi.nexoai.lat/cliente")
# Derive base domain for tracking URLs (strip /cliente suffix if present)
_TRACKING_BASE    = CUSTOMER_APP_URL.replace('/cliente', '').rstrip('/')

_HEADERS = {"X-Taxi-Internal-Key": WHATSAPP_SECRET} if WHATSAPP_SECRET else {}


# ── Llamadas HTTP a taxi-api ───────────────────────────────────────────────────

def _geocode(query: str) -> list:
    try:
        with httpx.Client(timeout=8.0) as c:
            resp = c.get(
                f"{API_BASE}/api/v1/whatsapp/geocode",
                params={"q": query},
                headers=_HEADERS,
            )
            return resp.json().get("results", [])
    except Exception as e:
        logger.warning(f"[TaxiAgent] geocode error: {e}")
        return []


def _estimate(origin_lat: float, origin_lng: float, dest_lat: float, dest_lng: float) -> dict:
    try:
        with httpx.Client(timeout=5.0) as c:
            resp = c.post(
                f"{API_BASE}/api/v1/whatsapp/rides/estimate",
                json={
                    "origin":      {"lat": origin_lat, "lng": origin_lng},
                    "destination": {"lat": dest_lat,   "lng": dest_lng},
                },
                headers=_HEADERS,
            )
            return resp.json()
    except Exception as e:
        logger.warning(f"[TaxiAgent] estimate error: {e}")
        return {"fare": 80.0, "distance_km": 5.0, "duration_minutes": 15}


def _create_ride(
    phone: str,
    origin: dict,
    destination: dict,
    scheduled_at: Optional[str] = None,
) -> Optional[dict]:
    payload: dict = {
        "customer_phone": phone,
        "origin":         origin,
        "destination":    destination,
        "payment_method": "cash",
    }
    if scheduled_at:
        payload["scheduled_at"] = scheduled_at
    try:
        with httpx.Client(timeout=8.0) as c:
            resp = c.post(
                f"{API_BASE}/api/v1/whatsapp/rides/create",
                json=payload,
                headers=_HEADERS,
            )
            if resp.status_code == 200:
                return resp.json()
            logger.error(f"[TaxiAgent] create_ride {resp.status_code}: {resp.text}")
    except Exception as e:
        logger.error(f"[TaxiAgent] create_ride error: {e}")
    return None


def _cancel_ride(ride_id: str):
    try:
        with httpx.Client(timeout=4.0) as c:
            c.post(
                f"{API_BASE}/api/v1/whatsapp/rides/{ride_id}/cancel",
                headers=_HEADERS,
            )
    except Exception as e:
        logger.debug(f"[TaxiAgent] cancel_ride: {e}")


def _get_ride(ride_id: str) -> Optional[dict]:
    try:
        with httpx.Client(timeout=4.0) as c:
            resp = c.get(
                f"{API_BASE}/api/v1/whatsapp/rides/{ride_id}",
                headers=_HEADERS,
            )
            return resp.json()
    except Exception as e:
        logger.debug(f"[TaxiAgent] get_ride: {e}")
    return None


def _init_customer(phone: str):
    try:
        with httpx.Client(timeout=3.0) as c:
            c.post(
                f"{API_BASE}/api/v1/whatsapp/customer/init",
                json={"phone": phone},
                headers=_HEADERS,
            )
    except Exception:
        pass


# ── Sesión Redis ───────────────────────────────────────────────────────────────

def _session_key(phone: str) -> str:
    return f"taxi:agent:{phone}"


def _load_session(phone: str) -> dict:
    if not _redis_client:
        return {"history": [], "context": {}}
    try:
        raw = _redis_client.get(_session_key(phone))
        if raw:
            return json.loads(raw)
    except Exception as e:
        logger.warning(f"[TaxiAgent] session load: {e}")
    return {"history": [], "context": {}}


def _save_session(phone: str, session: dict):
    if not _redis_client:
        return
    try:
        if len(session.get("history", [])) > _MAX_HISTORY:
            session["history"] = session["history"][-_MAX_HISTORY:]
        _redis_client.setex(_session_key(phone), _SESSION_TTL, json.dumps(session))
    except Exception as e:
        logger.warning(f"[TaxiAgent] session save: {e}")


# ── Definiciones de herramientas ───────────────────────────────────────────────

_TOOLS = [
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


# ── System prompt ──────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """
Eres TaxiBot, asistente de WhatsApp para reservar taxis en Celaya, Gto. y municipios cercanos
(Cortazar, Villagrán, Apaseo el Grande, Salvatierra). Hablas español mexicano, eres amigable
y conciso — como un despachador real, no un robot.
Pago: únicamente en efectivo al terminar el viaje.

═══════════════════════════════════════
SALUDO INICIAL
═══════════════════════════════════════

Si el cliente saluda o escribe su primer mensaje, responde con calidez y pregunta de inmediato
a dónde lo llevamos. Ejemplo de tono (no copies literal):
"¡Hola! 👋 ¿A dónde te llevamos hoy?"

═══════════════════════════════════════
FLUJO OBLIGATORIO (sigue este orden SIEMPRE)
═══════════════════════════════════════

1. Consigue el DESTINO primero. Si no lo tienes, pregunta: "¿A dónde te llevamos?"
2. Consigue el ORIGEN. Si no lo tienes, pregunta: "¿Dónde te recogemos?"
3. Con AMBOS puntos listos, llama estimar_tarifa() con las coordenadas.
4. Muestra el resumen con links de Maps para que el cliente verifique cada punto:
   🗺 Verifica origen: https://maps.google.com/?q=<origin_lat>,<origin_lng>
   🗺 Verifica destino: https://maps.google.com/?q=<dest_lat>,<dest_lng>
   💰 Tarifa: $X MXN | Y km | ~Z min
   Pregunta: ¿el viaje es para ahora o lo agendamos para después?
5. Solo cuando el cliente confirme tarifa Y horario → llama crear_viaje().
6. Si crear_viaje falla o no hay conductores, responde:
   "En este momento no hay conductores disponibles. Te avisaremos en cuanto uno acepte. 🙏"

CONFIRMACIÓN DE UBICACIÓN:
Cuando buscar_lugar() devuelva resultados, confirma brevemente antes de continuar al
siguiente paso. Ejemplo: "¡Listo! Te recojo en [nombre del lugar] 📍 ¿Y a dónde vas?"

═══════════════════════════════════════
TRAS CREAR EL VIAJE
═══════════════════════════════════════

Responde EXACTAMENTE con este formato (usa el campo tracking_url del resultado de crear_viaje):
✅ *¡Viaje solicitado!*

🔴 Destino: *<nombre del destino>*
💰 Tarifa: *$<tarifa> MXN*

🔍 Buscando conductor disponible...
Te avisaremos cuando un conductor acepte tu viaje.

📍 Sigue tu viaje: <tracking_url>

_Escribe *cancelar* si cambias de opinión._

═══════════════════════════════════════
CONSULTAR / CANCELAR VIAJE
═══════════════════════════════════════

Si el cliente pregunta por el estado de su viaje o quiere cancelarlo, usa ver_estado_viaje
o cancelar_viaje con el ride_id del historial (o pídelo si no lo tienes).

═══════════════════════════════════════
REGLAS ESTRICTAS — NUNCA las violes
═══════════════════════════════════════

• NUNCA preguntes origen antes de tener destino.
• NUNCA inventes ni estimes tarifas. La tarifa SOLO viene de llamar estimar_tarifa().
• NUNCA llames crear_viaje() sin haber mostrado antes la tarifa al cliente.
• Si el cliente da ORIGEN y DESTINO en un solo mensaje ("voy de X a Y"), llama
  buscar_lugar() para AMBOS puntos antes de hacer cualquier pregunta.
• Si el primer mensaje es GPS (coordenadas), úsalo como ORIGEN y pregunta el destino.
• Si el cliente comparte GPS sin haber dado destino, guárdalo como origen y SIGUE preguntando destino.
• Si buscar_lugar() devuelve vacío, simplifica la búsqueda (quita número, agrega ciudad).
  Solo si falla dos veces seguidas, pide al cliente que comparta su ubicación GPS.
• Al llamar buscar_lugar(), usa la dirección TAL COMO la escribió el cliente — NO corrijas
  ortografía, NO parafrasees. Si el cliente escribe "Rayando el sol 22", pasa exactamente "Rayando el sol 22 Ciudad".
• Al mostrar origen/destino al cliente, usa el campo `name` o `address` que devolvió buscar_lugar().
  NUNCA re-escribas la dirección de memoria — copia el valor exacto del resultado de la herramienta.
• Confirmar = sí / ok / dale / listo / confirmo / claro / de acuerdo / va / sip / ándale / perfecto / sale / eso → crea el viaje.
• Cancelar = no / cancelar / espera / mejor no / otro → vuelve a preguntar sin crear.
• *Negritas* para destino, tarifa e ID de viaje.

═══════════════════════════════════════
ESTILO DE RESPUESTA
═══════════════════════════════════════
• Máximo 3-4 líneas por mensaje.
• Una sola pregunta por mensaje.
• Usa emojis con moderación — amigable y directo, no como un bot publicitario.
• Responde SOLO con texto plano y emojis. Nunca uses bloques de código (```), JSON ni XML.
"""



# ── Ejecución de herramientas ──────────────────────────────────────────────────

def _run_tool(name: str, args: dict, phone: str) -> str:
    if name == "buscar_lugar":
        results = _geocode(args.get("query", ""))
        if not results:
            return json.dumps({"error": "No encontré ese lugar. Pide al cliente que sea más específico o comparta su ubicación GPS."})
        return json.dumps({"results": results[:3]})

    if name == "estimar_tarifa":
        est = _estimate(
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
        data = _create_ride(phone, origin, dest, args.get("scheduled_at"))
        if data:
            ride    = data.get("ride", data)
            ride_id = ride.get("ride_id") or ride.get("id") or "desconocido"
            # Extend session TTL to 24 h now that a ride exists
            if _redis_client:
                try:
                    _redis_client.expire(_session_key(phone), _SESSION_TTL_WITH_RIDE)
                except Exception:
                    pass
            return json.dumps({
                "success":      True,
                "ride_id":      ride_id,
                "status":       ride.get("status", "requested"),
                "fare":         ride.get("total_fare"),
                "tracking_url": f"{_TRACKING_BASE}/seguimiento/{ride_id}",
            })
        return json.dumps({"error": "No se pudo crear el viaje. Intenta de nuevo."})

    if name == "ver_estado_viaje":
        data = _get_ride(args.get("ride_id", ""))
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
        _cancel_ride(args.get("ride_id", ""))
        return json.dumps({"success": True, "message": "Viaje cancelado."})

    return json.dumps({"error": f"Herramienta desconocida: {name}"})


# ── Recuperación de tool calls malformados (Groq quirk) ──────────────────────

_FAILED_GEN_RE = re.compile(
    r"'failed_generation':\s*'<function=(\w+)(\{.*?\})</function>'",
    re.DOTALL,
)


def _recover_tool_call(err_str: str, messages: list, phone: str) -> Optional[list]:
    """
    Groq llama-3.3 sometimes generates tool calls as XML instead of JSON.
    Error contains 'failed_generation': '<function=name{...}</function>'
    We parse it, execute the tool, and inject both call + result into messages.
    """
    m = _FAILED_GEN_RE.search(err_str)
    if not m:
        return None
    func_name = m.group(1)
    try:
        args = json.loads(m.group(2))
    except Exception:
        return None
    import uuid
    tc_id      = f"call_{uuid.uuid4().hex[:8]}"
    result_str = _run_tool(func_name, args, phone)
    logger.info(f"[TaxiAgent] Recovered {func_name}({args}) → {result_str[:80]}")
    return messages + [
        {
            "role":       "assistant",
            "content":    None,
            "tool_calls": [{
                "id":   tc_id,
                "type": "function",
                "function": {"name": func_name, "arguments": json.dumps(args)},
            }],
        },
        {
            "role":         "tool",
            "tool_call_id": tc_id,
            "content":      result_str,
        },
    ]


# ── Resultado compatible con sales_routes.py ──────────────────────────────────

class AgentResult:
    def __init__(self, text: str):
        self.response_text = text
        self.intent = "llm"

    class _State:
        value = "llm"

    new_state = _State()


# ── Clase principal ────────────────────────────────────────────────────────────

class TaxiAgent:
    def __init__(self):
        self._client   = None
        self._fallback = None
        try:
            from openai import OpenAI
            if GROQ_API_KEY:
                self._client = OpenAI(
                    api_key=GROQ_API_KEY,
                    base_url="https://api.groq.com/openai/v1",
                    timeout=30.0,
                )
                logger.info("[TaxiAgent] Groq inicializado")
            if CEREBRAS_API_KEY:
                self._fallback = OpenAI(
                    api_key=CEREBRAS_API_KEY,
                    base_url="https://api.cerebras.ai/v1",
                    timeout=30.0,
                )
                logger.info("[TaxiAgent] Cerebras fallback inicializado")
            _gemini_key = os.getenv("GEMINI_API_KEY", "")
            if _gemini_key:
                self._gemini = OpenAI(
                    api_key=_gemini_key,
                    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
                    timeout=30.0,
                )
                logger.info("[TaxiAgent] Gemini fallback inicializado")
            else:
                self._gemini = None
            _openrouter_key = os.getenv("OPENROUTER_API_KEY", "")
            if _openrouter_key:
                self._openrouter = OpenAI(
                    api_key=_openrouter_key,
                    base_url="https://openrouter.ai/api/v1",
                    timeout=40.0,
                    default_headers={"HTTP-Referer": "https://taxi.nexoai.lat", "X-Title": "TaxiNexoAI"},
                )
                logger.info("[TaxiAgent] OpenRouter fallback inicializado")
            else:
                self._openrouter = None
            if not self._client and not self._fallback and not self._gemini and not self._openrouter:
                logger.error("[TaxiAgent] Sin API keys configuradas")
        except Exception as e:
            logger.error(f"[TaxiAgent] init error: {e}")

    def _llm_create(self, messages: list, tools: list | None = None, **kwargs):
        """Intenta Groq primero; ante cualquier error cae a Cerebras automáticamente."""
        providers = []
        if self._client:
            providers.append((self._client,   "llama-3.3-70b-versatile", "Groq"))
        if self._fallback:
            providers.append((self._fallback, "llama-3.3-70b",           "Cerebras"))
        if getattr(self, "_gemini", None):
            providers.append((self._gemini,   "gemini-2.0-flash",        "Gemini"))
        if getattr(self, "_openrouter", None):
            providers.append((self._openrouter, "meta-llama/llama-3.3-70b-instruct:free", "OpenRouter"))

        last_exc = RuntimeError("Sin proveedores LLM configurados")
        for client, model, name in providers:
            try:
                kwargs_merged = {"model": model, "messages": messages, **kwargs}
                if tools:
                    kwargs_merged["tools"] = tools
                    kwargs_merged.setdefault("tool_choice", "auto")
                    kwargs_merged["parallel_tool_calls"] = False
                resp = client.chat.completions.create(**kwargs_merged)
                return resp, name
            except Exception as e:
                last_exc = e
                is_last = (name == providers[-1][2])
                if not is_last:
                    logger.warning(f"[TaxiAgent] {name} error ({type(e).__name__}: {str(e)[:80]}) — usando fallback Cerebras")
                    continue
                raise last_exc
        raise last_exc

    def process(self, phone: str, message: str) -> AgentResult:
        _init_customer(phone)

        session = _load_session(phone)
        history = session.get("history", [])
        ctx     = session.setdefault("context", {})

        # Convertir GPS a texto con coords explícitas para el LLM
        gps_match = _GPS_RE.match(message.strip())
        if gps_match:
            lat   = float(gps_match.group(1))
            lng   = float(gps_match.group(2))
            label = gps_match.group(3) or "Mi ubicación"
            message = f"Mi ubicación actual es: {label} (coordenadas: {lat}, {lng})"
            ctx["last_gps"] = {"lat": lat, "lng": lng, "label": label}

        history.append({"role": "user", "content": message})

        if not self._client and not self._fallback:
            err = "Servicio temporalmente no disponible. Por favor intenta de nuevo."
            history.append({"role": "assistant", "content": err})
            session["history"] = history
            _save_session(phone, session)
            return AgentResult(err)

        messages = [{"role": "system", "content": _SYSTEM_PROMPT}] + history

        # Bucle de tool calling (máximo 4 rondas)
        for round_num in range(4):
            try:
                resp, provider = self._llm_create(
                    messages,
                    tools=_TOOLS,
                    max_tokens=600,
                    temperature=0.3,
                )
            except Exception as e:
                err_str = str(e)
                # Groq occasionally generates malformed XML tool calls
                if "tool_use_failed" in err_str:
                    # Attempt to parse & execute the malformed tool call
                    recovered = _recover_tool_call(err_str, messages, phone)
                    if recovered:
                        messages = recovered
                        continue  # let the loop produce a final text response
                    # Can't recover — fall back to plain-text reply without tools
                    logger.warning(f"[TaxiAgent] tool_use_failed (no recovery), retrying text [{phone}]")
                    try:
                        resp, provider = self._llm_create(messages, max_tokens=600, temperature=0.3)
                    except Exception as e2:
                        logger.error(f"[TaxiAgent] retry error [{phone}]: {e2}")
                        err = "Lo siento, hubo un error. Por favor intenta de nuevo."
                        history.append({"role": "assistant", "content": err})
                        session["history"] = history
                        _save_session(phone, session)
                        return AgentResult(err)
                else:
                    logger.error(f"[TaxiAgent] LLM error [{phone}]: {e}")
                    err = "Lo siento, hubo un error. Por favor intenta de nuevo."
                    history.append({"role": "assistant", "content": err})
                    session["history"] = history
                    _save_session(phone, session)
                    return AgentResult(err)

            choice = resp.choices[0]
            msg    = choice.message

            if msg.tool_calls:
                # Agregar respuesta del asistente con tool calls al hilo
                messages.append({
                    "role":       "assistant",
                    "content":    None,
                    "tool_calls": [
                        {
                            "id":       tc.id,
                            "type":     "function",
                            "function": {
                                "name":      tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in msg.tool_calls
                    ],
                })

                for tc in msg.tool_calls:
                    try:
                        args = json.loads(tc.function.arguments)
                    except Exception:
                        args = {}
                    result_str = _run_tool(tc.function.name, args, phone)
                    logger.info(f"[TaxiAgent] {tc.function.name} → {result_str[:100]}")
                    messages.append({
                        "role":         "tool",
                        "tool_call_id": tc.id,
                        "content":      result_str,
                    })
                # Continuar bucle para respuesta final
            else:
                # Respuesta de texto final
                final_text = (msg.content or "").strip()
                history.append({"role": "assistant", "content": final_text})
                session["history"] = history
                _save_session(phone, session)
                return AgentResult(final_text)

        # Fallback si se agotaron rondas
        fallback = "Perdón, no pude completar la solicitud. ¿Puedes repetirla?"
        history.append({"role": "assistant", "content": fallback})
        session["history"] = history
        _save_session(phone, session)
        return AgentResult(fallback)


# ── Singleton ──────────────────────────────────────────────────────────────────

_instance: Optional[TaxiAgent] = None


def get_taxi_agent() -> TaxiAgent:
    global _instance
    if _instance is None:
        _instance = TaxiAgent()
    return _instance
