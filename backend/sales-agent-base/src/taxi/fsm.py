"""
TaxiFSM — máquina de estados para el agente de taxis por WhatsApp.
Cada sesión se identifica por el número de teléfono del cliente.
"""
import json
import logging
import os
import re
from dataclasses import dataclass, field, asdict
from typing import Optional

_GPS_RE = re.compile(r'^\[GPS:([-\d.]+),([-\d.]+)(?::(.+))?\]$')
_SESSION_TTL = 86400  # 24 horas

import httpx

try:
    import redis as _redis_lib
    _redis_client = _redis_lib.from_url(os.getenv("REDIS_URL", ""), decode_responses=True) if os.getenv("REDIS_URL") else None
except Exception:
    _redis_client = None

logger = logging.getLogger(__name__)


@dataclass
class TaxiSession:
    phone: str
    state: str = "IDLE"
    destination: Optional[dict] = None   # {name, address, lat, lng}
    origin: Optional[dict] = None        # {name, address, lat, lng}
    geocode_results: list = field(default_factory=list)
    origin_results: list = field(default_factory=list)
    ride_id: Optional[str] = None
    last_fare: Optional[float] = None
    driver_code: Optional[str] = None
    preferred_driver_phone: Optional[str] = None
    preferred_driver_name: Optional[str] = None


# ── Respuesta compatible con sales_routes.py ──────────────────────────────────

class _FsmResult:
    def __init__(self, text: str, state: str):
        self.response_text = text
        self.intent = "taxi"
        self.visual_data = None
        self.cart_action = None

        class _State:
            def __init__(self, v):
                self.value = v
        self.new_state = _State(state)


class TaxiFSM:
    def __init__(self, api_base_url: str, internal_key: str):
        self.api_base = api_base_url.rstrip("/")
        self.key = internal_key
        self.sessions: dict[str, TaxiSession] = {}

    # ── Public interface (matches restaurant FSM) ──────────────────────────────

    # ── Session persistence (Redis → in-memory fallback) ──────────────────────

    def _load_session(self, phone: str) -> TaxiSession:
        if _redis_client:
            try:
                raw = _redis_client.get(f"taxi:session:{phone}")
                if raw:
                    return TaxiSession(**json.loads(raw))
            except Exception as e:
                logger.warning(f"[TaxiFSM] Redis read error: {e}")
        return self.sessions.get(phone, TaxiSession(phone=phone))

    def _save_session(self, s: TaxiSession) -> None:
        if _redis_client:
            try:
                _redis_client.setex(f"taxi:session:{s.phone}", _SESSION_TTL, json.dumps(asdict(s)))
                return
            except Exception as e:
                logger.warning(f"[TaxiFSM] Redis write error: {e}")
        self.sessions[s.phone] = s

    def _delete_session(self, phone: str) -> None:
        if _redis_client:
            try:
                _redis_client.delete(f"taxi:session:{phone}")
            except Exception:
                pass
        self.sessions.pop(phone, None)

    def process(self, session_id: str, message: str) -> _FsmResult:
        """session_id == customer phone for WhatsApp taxi sessions."""
        session = self._load_session(session_id)
        text = self._dispatch(session, message.strip())
        self._save_session(session)
        return _FsmResult(text, session.state)

    # ── Dispatcher ────────────────────────────────────────────────────────────

    def _dispatch(self, s: TaxiSession, msg: str) -> str:
        lower = msg.lower()

        # Global cancel / restart
        if lower in ("cancelar", "cancel", "salir", "restart", "reiniciar") and s.state != "IDLE":
            if s.ride_id and s.state == "RIDE_ACTIVE":
                self._cancel_ride(s.ride_id)
            phone = s.phone
            s.__init__(phone=phone)
            return "Entendido, reiniciamos. ¿A dónde te llevamos? 🚕"

        if s.state == "IDLE":
            return self._idle(s, msg)
        if s.state == "ASKING_DESTINATION":
            return self._ask_dest(s, msg)
        if s.state == "CHOOSING_DEST":
            return self._choose_dest(s, msg)
        if s.state == "ASKING_ORIGIN":
            return self._ask_origin(s, msg)
        if s.state == "CHOOSING_ORIGIN":
            return self._choose_origin(s, msg)
        if s.state == "CONFIRMING":
            return self._confirming(s, msg)
        if s.state == "RIDE_ACTIVE":
            return self._ride_active(s, msg)
        # Fallback
        s.state = "IDLE"
        return self._idle(s, msg)

    # ── States ────────────────────────────────────────────────────────────────

    def _idle(self, s: TaxiSession, msg: str) -> str:
        # Extract driver_code from QR-generated messages like "[ABC123]"
        match = re.search(r'\[([A-Za-z0-9_-]+)\]', msg)
        if match:
            code = match.group(1)
            driver = self._lookup_driver(code)
            if driver:
                s.driver_code = code
                s.preferred_driver_phone = driver.get("phone")
                s.preferred_driver_name = driver.get("name")
                self._init_customer(s.phone, driver_code=code)
                s.state = "ASKING_DESTINATION"
                return (
                    f"¡Hola! 👋 Te conectaste con el taxi de *{driver['name']}*.\n\n"
                    "¿A dónde te llevamos hoy?\n"
                    "_Escribe el nombre o dirección de tu destino._"
                )
        self._init_customer(s.phone)
        s.state = "ASKING_DESTINATION"
        app_url = os.getenv("CUSTOMER_APP_URL", "")
        url_line = f"📱 También puedes agendar viajes en: {app_url}\n\n" if app_url else ""
        return (
            f"¡Hola! 👋 Soy tu asistente de taxi.\n\n"
            f"{url_line}"
            "¿A dónde te llevamos hoy?\n"
            "_Escribe el nombre o dirección de tu destino._"
        )

    def _try_gps(self, s: TaxiSession, msg: str, set_destination: bool) -> Optional[str]:
        m = _GPS_RE.match(msg.strip())
        if not m:
            return None
        lat, lon = float(m.group(1)), float(m.group(2))
        label = (m.group(3) or "").strip() or "Ubicación compartida"
        location = {"name": label, "short_address": "", "address": label, "lat": lat, "lng": lon}
        if set_destination:
            s.destination = location
            s.state = "ASKING_ORIGIN"
            return (
                f"📍 Destino: *{label}*\n\n"
                "¿Dónde te recogemos?\n"
                "_Escribe tu calle, colonia o 📎 comparte tu ubicación._"
            )
        else:
            s.origin = location
            return self._show_confirmation(s)

    def _ask_dest(self, s: TaxiSession, msg: str) -> str:
        gps_reply = self._try_gps(s, msg, set_destination=True)
        if gps_reply:
            return gps_reply
        if len(msg) < 4:
            return "Escribe el nombre de tu destino (ej: *Aeropuerto*, *Plaza Galerías*, *Hospital General*)."
        results = self._geocode(msg)
        if not results:
            return (
                "No encontré ese destino. 🤔\n"
                "Intenta con más detalle, por ejemplo:\n"
                "• *Aeropuerto del Bajío*\n• *Hospital IMSS Irapuato*\n• *Centro de Salamanca*"
            )
        s.geocode_results = results[:3]
        if len(results) == 1:
            s.destination = results[0]
            s.state = "ASKING_ORIGIN"
            addr = results[0].get("short_address") or results[0]["address"][:80]
            return (
                f"📍 Destino: *{results[0]['name']}*\n"
                f"_{addr}_\n\n"
                "¿Dónde te recogemos?\n"
                "_Escribe tu calle, colonia o 📎 comparte tu ubicación._"
            )
        _nums = ["1️⃣", "2️⃣", "3️⃣"]
        lines = ["Encontré varios lugares con ese nombre:\n"]
        for i, r in enumerate(results[:3], 1):
            addr = r.get("short_address") or r["address"][:55]
            lines.append(f"{_nums[i-1]} *{r['name']}*\n   _{addr}_\n")
        lines.append("¿Cuál es? Responde *1*, *2* o *3*.")
        s.state = "CHOOSING_DEST"
        return "\n".join(lines)

    def _choose_dest(self, s: TaxiSession, msg: str) -> str:
        if msg in ("1", "2", "3"):
            idx = int(msg) - 1
            if idx < len(s.geocode_results):
                s.destination = s.geocode_results[idx]
                s.state = "ASKING_ORIGIN"
                return (
                    f"✅ Destino: *{s.destination['name']}*\n\n"
                    "¿Dónde te recogemos?\n"
                    "_Escribe tu calle, colonia o lugar de recogida._"
                )
        # Treat as a new destination search
        s.state = "ASKING_DESTINATION"
        return self._ask_dest(s, msg)

    def _ask_origin(self, s: TaxiSession, msg: str) -> str:
        gps_reply = self._try_gps(s, msg, set_destination=False)
        if gps_reply:
            return gps_reply
        if len(msg) < 4:
            return "Escribe tu punto de recogida (calle, colonia o lugar conocido)."
        results = self._geocode(msg)
        if not results:
            return (
                "No encontré ese punto. 🤔\n"
                "Intenta con más detalle, por ejemplo:\n"
                "• *Calle Independencia 25, Centro*\n• *Colonia Las Flores*"
            )
        s.origin_results = results[:3]
        if len(results) == 1:
            s.origin = results[0]
            return self._show_confirmation(s)
        _nums = ["1️⃣", "2️⃣", "3️⃣"]
        lines = ["¿Dónde exactamente te recogemos?\n"]
        for i, r in enumerate(results[:3], 1):
            addr = r.get("short_address") or r["address"][:55]
            lines.append(f"{_nums[i-1]} *{r['name']}*\n   _{addr}_\n")
        lines.append("¿Cuál? Responde *1*, *2* o *3*.")
        s.state = "CHOOSING_ORIGIN"
        return "\n".join(lines)

    def _choose_origin(self, s: TaxiSession, msg: str) -> str:
        if msg in ("1", "2", "3"):
            idx = int(msg) - 1
            if idx < len(s.origin_results):
                s.origin = s.origin_results[idx]
                return self._show_confirmation(s)
        s.state = "ASKING_ORIGIN"
        return self._ask_origin(s, msg)

    def _show_confirmation(self, s: TaxiSession) -> str:
        fare_info = self._estimate(s.origin, s.destination)
        s.last_fare = fare_info.get("fare", 0)
        s.state = "CONFIRMING"
        orig_name = s.origin["name"] if s.origin else "Tu ubicación"
        dest_name = s.destination["name"] if s.destination else "Destino"
        driver_line = f"🚕 Conductor: *{s.preferred_driver_name}*\n" if s.preferred_driver_name else ""
        return (
            f"📋 *Resumen del viaje*\n\n"
            f"🟢 Salida: *{orig_name}*\n"
            f"🔴 Destino: *{dest_name}*\n"
            f"{driver_line}"
            f"\n💰 Tarifa estimada: *${fare_info.get('fare', 0):.0f} MXN*\n"
            f"📏 Distancia: ~{fare_info.get('distance_km', 0):.1f} km\n"
            f"⏱ Tiempo: ~{fare_info.get('duration_minutes', 0)} min\n\n"
            "¿Confirmamos el viaje?\n"
            "Responde *sí* para pedir tu taxi o *no* para cambiar los datos."
        )

    def _confirming(self, s: TaxiSession, msg: str) -> str:
        lower = msg.lower()
        if any(w in lower for w in ("sí", "si", "yes", "confirmar", "confirma", "ok", "dale", "va")):
            result = self._create_ride(s)
            if result:
                s.ride_id = result["ride_id"]
                s.state = "RIDE_ACTIVE"
                return (
                    f"✅ *¡Viaje solicitado!*\n\n"
                    f"🔴 Destino: *{s.destination['name']}*\n"
                    f"💰 Tarifa: *${result['fare']:.0f} MXN*\n\n"
                    f"🔍 Buscando conductor disponible...\n"
                    f"Te avisaremos cuando un conductor acepte tu viaje.\n\n"
                    f"_Escribe *cancelar* si cambias de opinión._"
                )
            return "Hubo un error al crear el viaje. Por favor intenta de nuevo en unos momentos."
        if any(w in lower for w in ("no", "cambiar", "otro", "corregir")):
            s.state = "ASKING_DESTINATION"
            s.destination = None
            s.origin = None
            return "Entendido. ¿A dónde te llevamos? 🚕"
        return (
            "Por favor responde:\n"
            "• *sí* — confirmar el viaje\n"
            "• *no* — cambiar origen o destino"
        )

    def _ride_active(self, s: TaxiSession, msg: str) -> str:
        # Auto-reset si el viaje ya terminó (ej. conductor marcó completado/cancelado)
        if s.ride_id:
            ride = self._get_ride(s.ride_id)
            if ride and ride.get("status") in ("completed", "cancelled"):
                phone = s.phone
                s.__init__(phone=phone)
                return self._idle(s, msg)

        lower = msg.lower()
        if any(w in lower for w in ("cancelar", "cancel", "cancela")):
            if s.ride_id:
                self._cancel_ride(s.ride_id)
            phone = s.phone
            s.__init__(phone=phone)
            return "Tu viaje fue cancelado. ¿Deseas pedir otro taxi? 🚕"
        if any(w in lower for w in ("estado", "status", "donde", "dónde", "cuánto", "cuanto", "info")):
            if s.ride_id:
                ride = self._get_ride(s.ride_id)
                if ride:
                    status_map = {
                        "requested":      "🔍 Buscando conductor...",
                        "confirmed":      f"✅ Conductor asignado: *{ride.get('driver_name') or 'en camino'}*",
                        "driver_arrived": "🚕 ¡Tu conductor llegó al punto de recogida!",
                        "in_progress":    "🚗 Viaje en curso, ¡disfruta el trayecto!",
                        "completed":      "✅ Viaje completado",
                        "cancelled":      "❌ Viaje cancelado",
                    }
                    return status_map.get(ride.get("status", "requested"), f"Estado: {ride.get('status')}")
        return (
            "Tienes un viaje activo 🚗\n\n"
            "• Escribe *estado* para ver el progreso del viaje\n"
            "• Escribe *cancelar* si ya no lo necesitas"
        )

    # ── API helpers ───────────────────────────────────────────────────────────

    def _headers(self) -> dict:
        return {"X-Taxi-Internal-Key": self.key, "Content-Type": "application/json"}

    def _init_customer(self, phone: str, driver_code: Optional[str] = None):
        try:
            payload: dict = {"phone": phone}
            if driver_code:
                payload["driver_code"] = driver_code
            with httpx.Client(timeout=4.0) as c:
                c.post(
                    f"{self.api_base}/api/v1/whatsapp/customer/init",
                    json=payload,
                    headers=self._headers(),
                )
        except Exception as e:
            logger.debug(f"[TaxiFSM] customer/init: {e}")

    def _lookup_driver(self, driver_code: str) -> Optional[dict]:
        try:
            with httpx.Client(timeout=4.0) as c:
                resp = c.get(
                    f"{self.api_base}/api/v1/whatsapp/driver/{driver_code}",
                    headers=self._headers(),
                )
                if resp.status_code == 200:
                    return resp.json()
        except Exception as e:
            logger.debug(f"[TaxiFSM] lookup_driver: {e}")
        return None

    def _geocode(self, query: str) -> list:
        try:
            with httpx.Client(timeout=8.0) as c:
                resp = c.get(
                    f"{self.api_base}/api/v1/whatsapp/geocode",
                    params={"q": query},
                    headers=self._headers(),
                )
                return resp.json().get("results", [])
        except Exception as e:
            logger.warning(f"[TaxiFSM] geocode error: {e}")
            return []

    def _estimate(self, origin: Optional[dict], destination: Optional[dict]) -> dict:
        try:
            with httpx.Client(timeout=5.0) as c:
                resp = c.post(
                    f"{self.api_base}/api/v1/whatsapp/rides/estimate",
                    json={
                        "origin": {"lat": origin["lat"], "lng": origin["lng"]} if origin else {},
                        "destination": {"lat": destination["lat"], "lng": destination["lng"]} if destination else {},
                    },
                    headers=self._headers(),
                )
                return resp.json()
        except Exception as e:
            logger.warning(f"[TaxiFSM] estimate error: {e}")
            return {"fare": 80.0, "distance_km": 5.0, "duration_minutes": 15}

    def _create_ride(self, s: TaxiSession) -> Optional[dict]:
        try:
            payload: dict = {
                "customer_phone": s.phone,
                "origin": {
                    "address": s.origin["address"] if s.origin else "",
                    "lat": s.origin["lat"] if s.origin else 0,
                    "lng": s.origin["lng"] if s.origin else 0,
                },
                "destination": {
                    "address": s.destination["address"] if s.destination else "",
                    "lat": s.destination["lat"] if s.destination else 0,
                    "lng": s.destination["lng"] if s.destination else 0,
                },
                "payment_method": "cash",
            }
            if s.preferred_driver_phone:
                payload["preferred_driver_phone"] = s.preferred_driver_phone
            if s.preferred_driver_name:
                payload["preferred_driver_name"] = s.preferred_driver_name
            with httpx.Client(timeout=8.0) as c:
                resp = c.post(
                    f"{self.api_base}/api/v1/whatsapp/rides/create",
                    json=payload,
                    headers=self._headers(),
                )
                if resp.status_code == 200:
                    return resp.json()
                logger.error(f"[TaxiFSM] create_ride {resp.status_code}: {resp.text}")
        except Exception as e:
            logger.error(f"[TaxiFSM] create_ride error: {e}")
        return None

    def _cancel_ride(self, ride_id: str):
        try:
            with httpx.Client(timeout=4.0) as c:
                c.post(
                    f"{self.api_base}/api/v1/whatsapp/rides/{ride_id}/cancel",
                    headers=self._headers(),
                )
        except Exception as e:
            logger.debug(f"[TaxiFSM] cancel_ride: {e}")

    def _get_ride(self, ride_id: str) -> Optional[dict]:
        try:
            with httpx.Client(timeout=4.0) as c:
                resp = c.get(
                    f"{self.api_base}/api/v1/whatsapp/rides/{ride_id}",
                    headers=self._headers(),
                )
                return resp.json()
        except Exception as e:
            logger.debug(f"[TaxiFSM] get_ride: {e}")
        return None


# ── Singleton ─────────────────────────────────────────────────────────────────

_instance: Optional[TaxiFSM] = None


def get_taxi_fsm() -> TaxiFSM:
    global _instance
    if _instance is None:
        api_url = os.getenv("MENU_SERVICE_URL", "http://taxi-api:5011")
        secret = os.getenv("WHATSAPP_SECRET", "")
        _instance = TaxiFSM(api_base_url=api_url, internal_key=secret)
        logger.info(f"[TaxiFSM] Inicializado → {api_url}")
    return _instance
