"""
TaxiFSM — máquina de estados para el agente de taxis por WhatsApp.
Cada sesión se identifica por el número de teléfono del cliente.
"""
import json
import logging
import os
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from typing import Optional

_GPS_RE = re.compile(r'^\[GPS:([-\d.]+),([-\d.]+)(?::(.+))?\]$')
_SESSION_TTL = 86400  # 24 horas

# ── Intent / language helpers ─────────────────────────────────────────────────

# Pure greeting with nothing else: "hola", "buenas", "buenos días", etc.
_GREETING_RE = re.compile(
    r'^\s*(?:hola+|hey|hi|buenas?|buenos?\s+(?:d[ií]as?|tardes?|noches?)'
    r'|buen\s+d[ií]a|saludos?)\s*[!.¡]*\s*$',
    re.IGNORECASE,
)

# Phrases that mean "start over" anywhere in the message
_RESET_RE = re.compile(
    r'\b(nuevo\s+viaje|otro\s+viaje|de\s+nuevo|empezar?\s+de\s+nuevo|'
    r'volver\s+a\s+empezar|otra\s+vez|reiniciar)\b',
    re.IGNORECASE,
)

# Conversational / meta phrases — not address text
_CONVERSATIONAL_RE = re.compile(
    r'(\?|¿|\b(?:ayudas?|ayudar|puedes?|podr[ií]as?|quiero|quisiera|'
    r'necesito|agendar|agenda|programar?|solicitar|pedir|'
    r'me\s+llevas?|me\s+puedes?|me\s+ayudas?|por\s+favor|gracias)\b)',
    re.IGNORECASE,
)

# Extract destination from intent phrase: "quiero ir al X", "llévame a X", etc.
_DEST_INTENT_RE = re.compile(
    r'\b(?:ir\s+al?|llevar(?:me)?\s+al?|quiero\s+(?:ir\s+)?al?|'
    r'voy\s+(?:para\s+)?al?|lleva(?:me)?\s+al?)\s+(.+)',
    re.IGNORECASE,
)

import httpx

try:
    import redis as _redis_lib
    _redis_client = _redis_lib.from_url(os.getenv("REDIS_URL", ""), decode_responses=True) if os.getenv("REDIS_URL") else None
except Exception:
    _redis_client = None

logger = logging.getLogger(__name__)

_DIAS_ES = {
    "lunes": 0, "martes": 1, "miércoles": 2, "miercoles": 2,
    "jueves": 3, "viernes": 4, "sábado": 5, "sabado": 5, "domingo": 6,
}


def _parse_scheduled_at(text: str, now: Optional[datetime] = None) -> Optional[str]:
    """
    Interpreta texto en español y devuelve un ISO 8601 datetime string,
    o 'NOW' si el usuario quiere viaje inmediato, o None si no se pudo parsear.
    """
    if now is None:
        now = datetime.now()

    lower = text.lower().strip()

    # Palabras que significan "inmediato"
    if re.search(r'\b(ahora|ya|inmediato|inmediatamente|de una vez|ahorita|ya mismo)\b', lower):
        return "NOW"

    # "en N horas"
    m = re.search(r'\ben\s+(\d+)\s+(hora|horas)\b', lower)
    if m:
        dt = now + timedelta(hours=int(m.group(1)))
        return dt.strftime("%Y-%m-%dT%H:%M:00")

    # "en N minutos"
    m = re.search(r'\ben\s+(\d+)\s+(minuto|minutos|min)\b', lower)
    if m:
        dt = now + timedelta(minutes=int(m.group(1)))
        return dt.strftime("%Y-%m-%dT%H:%M:00")

    # ── Parsear hora ──────────────────────────────────────────────────────────
    hour: Optional[int] = None
    minute = 0

    # "X de la mañana/tarde/noche"
    m = re.search(r'(\d{1,2})(?::(\d{2}))?\s*de\s+la\s+(mañana|manana|tarde|noche)', lower)
    if m:
        hour = int(m.group(1))
        minute = int(m.group(2) or 0)
        period = m.group(3)
        if period in ("tarde", "noche") and hour < 12:
            hour += 12
        elif period in ("mañana", "manana") and hour == 12:
            hour = 0

    if hour is None:
        # "3pm" / "3am" / "3:30pm"
        m = re.search(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b', lower)
        if m:
            hour = int(m.group(1))
            minute = int(m.group(2) or 0)
            if m.group(3) == "pm" and hour < 12:
                hour += 12
            elif m.group(3) == "am" and hour == 12:
                hour = 0

    if hour is None:
        # "a las X" / "a la 1"
        m = re.search(r'a\s+la[s]?\s+(\d{1,2})(?::(\d{2}))?', lower)
        if m:
            hour = int(m.group(1))
            minute = int(m.group(2) or 0)
            if hour < 6:
                hour += 12  # heurística: si <6 sin am/pm → tarde

    if hour is None:
        # "15:30" o "9:00"
        m = re.search(r'\b(\d{1,2}):(\d{2})\b', lower)
        if m:
            hour = int(m.group(1))
            minute = int(m.group(2))

    if hour is None or not (0 <= hour <= 23 and 0 <= minute <= 59):
        return None

    # ── Parsear fecha ─────────────────────────────────────────────────────────
    base_date = None

    if re.search(r'\bpasado\s+ma[ñn]ana\b', lower):
        base_date = (now + timedelta(days=2)).date()
    elif re.search(r'\bma[ñn]ana\b', lower):
        base_date = (now + timedelta(days=1)).date()
    elif re.search(r'\bhoy\b', lower):
        base_date = now.date()
    else:
        for dia, weekday in _DIAS_ES.items():
            if re.search(rf'\b{dia}\b', lower):
                days_ahead = (weekday - now.weekday()) % 7
                if days_ahead == 0:
                    days_ahead = 7  # próximo de ese día
                base_date = (now + timedelta(days=days_ahead)).date()
                break

    if base_date is None:
        # Sin fecha explícita: usar hoy si la hora es futura (>15 min), si no mañana
        candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if candidate <= now + timedelta(minutes=15):
            candidate += timedelta(days=1)
        return candidate.strftime("%Y-%m-%dT%H:%M:00")

    scheduled = datetime.combine(base_date, datetime.min.time().replace(hour=hour, minute=minute))
    return scheduled.strftime("%Y-%m-%dT%H:%M:00")


def _format_scheduled_at(iso: str) -> str:
    """Formatea '2026-06-11T15:30:00' → 'jueves 11 jun a las 3:30 pm'."""
    try:
        dt = datetime.fromisoformat(iso)
        dias = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
        meses = ["", "ene", "feb", "mar", "abr", "may", "jun",
                 "jul", "ago", "sep", "oct", "nov", "dic"]
        dia_sem = dias[dt.weekday()]
        hora12 = dt.hour % 12 or 12
        ampm = "pm" if dt.hour >= 12 else "am"
        minutos = f":{dt.minute:02d}" if dt.minute else ""
        return f"{dia_sem} {dt.day} {meses[dt.month]} a las {hora12}{minutos} {ampm}"
    except Exception:
        return iso


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
    scheduled_at: Optional[str] = None       # ISO 8601, None = viaje inmediato
    awaiting_continuation: bool = False      # True mientras esperamos "continuar"/"nuevo"


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

    # ── Session persistence (Redis → in-memory fallback) ──────────────────────

    def _load_session(self, phone: str) -> TaxiSession:
        if _redis_client:
            try:
                raw = _redis_client.get(f"taxi:session:{phone}")
                if raw:
                    data = json.loads(raw)
                    data.setdefault("awaiting_continuation", False)
                    return TaxiSession(**data)
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
        lower = msg.lower().strip()

        # ── 1. Responder elección de continuación ─────────────────────────────
        if s.awaiting_continuation:
            s.awaiting_continuation = False
            if any(w in lower for w in ("continuar", "seguir", "sí", "si", "yes", "ok", "dale", "claro")):
                return self._resume_session(s)
            else:
                phone = s.phone
                s.__init__(phone=phone)
                return self._idle(s, msg)

        # ── 2. Reset global (palabra clave exacta) ────────────────────────────
        if lower in ("cancelar", "cancel", "salir", "restart", "reiniciar") and s.state != "IDLE":
            if s.ride_id and s.state == "RIDE_ACTIVE":
                self._cancel_ride(s.ride_id)
            phone = s.phone
            s.__init__(phone=phone)
            return "Entendido, reiniciamos. ¿A dónde te llevamos? 🚕"

        # ── 3. Soft reset ("nuevo viaje", "de nuevo", etc.) ───────────────────
        if s.state not in ("IDLE", "RIDE_ACTIVE") and _RESET_RE.search(lower):
            phone = s.phone
            s.__init__(phone=phone)
            return (
                "¡Empezamos de nuevo! 😊\n\n"
                "¿A dónde te llevamos?\n"
                "_Escribe el nombre o dirección de tu destino._"
            )

        # ── 4. Saludo en sesión activa → ofrecer continuación o reinicio ──────
        if s.state not in ("IDLE", "RIDE_ACTIVE") and _GREETING_RE.match(msg.strip()):
            if s.destination:
                dest_name = s.destination.get("name", "tu destino anterior")
                s.awaiting_continuation = True
                return (
                    f"¡Hola de nuevo! 👋\n\n"
                    f"Tienes un viaje pendiente a *{dest_name}*.\n\n"
                    f"¿Continuamos con ese viaje o prefieres empezar de nuevo?\n"
                    f"Responde *continuar* o *nuevo viaje*."
                )
            else:
                phone = s.phone
                s.__init__(phone=phone)
                return self._idle(s, msg)

        # ── 5. Ruteo normal por estado ────────────────────────────────────────
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
        if s.state == "ASKING_WHEN":
            return self._asking_when(s, msg)
        if s.state == "CONFIRMING":
            return self._confirming(s, msg)
        if s.state == "RIDE_ACTIVE":
            return self._ride_active(s, msg)
        # Fallback
        s.state = "IDLE"
        return self._idle(s, msg)

    # ── States ────────────────────────────────────────────────────────────────

    def _resume_session(self, s: TaxiSession) -> str:
        """Retoma la sesión desde donde se dejó después del prompt de continuación."""
        if s.state == "ASKING_DESTINATION":
            return (
                "Perfecto 😊\n\n"
                "¿A dónde te llevamos?\n"
                "_Escribe el nombre o dirección de tu destino._"
            )
        if s.state in ("ASKING_ORIGIN", "CHOOSING_ORIGIN"):
            dest_name = s.destination.get("name", "tu destino") if s.destination else "tu destino"
            return (
                f"Perfecto, continuamos 😊\n\n"
                f"📍 Destino: *{dest_name}*\n\n"
                f"¿Dónde te recogemos?\n"
                f"_Escribe tu calle, colonia o 📎 comparte tu ubicación._"
            )
        if s.state in ("ASKING_WHEN", "CONFIRMING"):
            return self._show_confirmation(s)
        # Estado inesperado — reiniciar
        phone = s.phone
        s.__init__(phone=phone)
        return self._idle(s, "hola")

    def _idle(self, s: TaxiSession, msg: str) -> str:
        # Detectar código de conductor QR "[ABC123]"
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

        # Si el mensaje contiene más que un saludo, intentar extraer destino directamente
        stripped = msg.strip()
        if not _GREETING_RE.match(stripped) and len(stripped) > 3:
            # Intentar extraer destino de frases de intención: "quiero ir al X" → "X"
            m = _DEST_INTENT_RE.search(msg)
            dest_text = m.group(1).strip() if m else None

            # Si no hay patrón de intención pero tampoco es conversacional → tratar como dirección
            if not dest_text and not _CONVERSATIONAL_RE.search(msg) and len(stripped) < 60:
                dest_text = stripped

            if dest_text:
                return self._ask_dest(s, dest_text)

        app_url = os.getenv("CUSTOMER_APP_URL", "")
        url_line = f"📱 También puedes agendar en: {app_url}\n\n" if app_url else ""
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
            return self._ask_when(s)

    def _ask_dest(self, s: TaxiSession, msg: str) -> str:
        gps_reply = self._try_gps(s, msg, set_destination=True)
        if gps_reply:
            return gps_reply
        if len(msg) < 4:
            return "Escribe el nombre de tu destino (ej: *Aeropuerto*, *Plaza Galerías*, *Hospital General*)."

        # Detectar frases conversacionales — no geocodificar
        if _CONVERSATIONAL_RE.search(msg) and len(msg) > 15:
            return (
                "¿A dónde te llevamos? 😊\n\n"
                "Escribe el *nombre o dirección* de tu destino, por ejemplo:\n"
                "• *Aeropuerto*\n• *Hospital IMSS*\n• *Plaza Las Américas*\n\n"
                "_O 📎 comparte tu ubicación desde WhatsApp._"
            )

        results = self._geocode(msg)
        if not results:
            return (
                "No encontré ese lugar. 🤔\n\n"
                "Intenta agregar el municipio o colonia:\n"
                "• ✏️ *Hospital General, Irapuato*\n"
                "• ✏️ *Plaza Mayor, Salamanca*\n"
                "• ✏️ *Aeropuerto del Bajío, Silao*\n\n"
                "O 📎 *comparte tu ubicación* desde WhatsApp."
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
        # Tratar como nueva búsqueda de destino
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
                "No encontré ese punto. 🤔\n\n"
                "Intenta ser más específico:\n"
                "• ✏️ *Calle Juárez 45, Centro*\n"
                "• ✏️ *Colonia Las Flores, Irapuato*\n\n"
                "O 📎 *comparte tu ubicación* desde WhatsApp — es lo más preciso."
            )
        s.origin_results = results[:3]
        if len(results) == 1:
            s.origin = results[0]
            return self._ask_when(s)
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
                return self._ask_when(s)
        s.state = "ASKING_ORIGIN"
        return self._ask_origin(s, msg)

    def _ask_when(self, s: TaxiSession) -> str:
        s.state = "ASKING_WHEN"
        return (
            "🕐 *¿Para cuándo necesitas el taxi?*\n\n"
            "• *ahora* — lo pedimos de inmediato\n"
            "• *mañana a las 10am* — programar para más tarde\n"
            "• *el viernes a las 3pm*\n"
            "• *en 2 horas*\n\n"
            "_Escribe cuándo lo necesitas._"
        )

    def _asking_when(self, s: TaxiSession, msg: str) -> str:
        result = _parse_scheduled_at(msg)
        if result is None:
            return (
                "No entendí la fecha u hora. 🤔\n\n"
                "Intenta así:\n"
                "• *ahora* — viaje inmediato\n"
                "• *mañana a las 9am*\n"
                "• *el lunes a las 2pm*\n"
                "• *hoy a las 6 de la tarde*\n"
                "• *en 3 horas*"
            )
        if result == "NOW":
            s.scheduled_at = None
        else:
            s.scheduled_at = result
        return self._show_confirmation(s)

    def _show_confirmation(self, s: TaxiSession) -> str:
        fare_info = self._estimate(s.origin, s.destination)
        s.last_fare = fare_info.get("fare", 0)
        s.state = "CONFIRMING"
        orig_name = s.origin["name"] if s.origin else "Tu ubicación"
        dest_name = s.destination["name"] if s.destination else "Destino"
        driver_line = f"🚕 Conductor: *{s.preferred_driver_name}*\n" if s.preferred_driver_name else ""
        when_line = (
            f"🗓 Programado: *{_format_scheduled_at(s.scheduled_at)}*\n"
            if s.scheduled_at else "🕐 Viaje: *inmediato*\n"
        )
        # Links de verificación en Maps para que el cliente confirme las coordenadas
        dest_lat = s.destination.get("lat") if s.destination else None
        dest_lng = s.destination.get("lng") if s.destination else None
        orig_lat = s.origin.get("lat") if s.origin else None
        orig_lng = s.origin.get("lng") if s.origin else None
        maps_dest = (
            f"🗺 Verifica el destino: https://maps.google.com/?q={dest_lat},{dest_lng}\n"
            if dest_lat and dest_lng else ""
        )
        maps_orig = (
            f"🗺 Verifica el origen: https://maps.google.com/?q={orig_lat},{orig_lng}\n"
            if orig_lat and orig_lng else ""
        )
        return (
            f"📋 *Resumen del viaje*\n\n"
            f"🟢 Salida: *{orig_name}*\n"
            f"{maps_orig}"
            f"🔴 Destino: *{dest_name}*\n"
            f"{maps_dest}"
            f"{driver_line}"
            f"{when_line}"
            f"\n💰 Tarifa estimada: *${fare_info.get('fare', 0):.0f} MXN*\n"
            f"📏 Distancia: ~{fare_info.get('distance_km', 0):.1f} km\n"
            f"⏱ Tiempo: ~{fare_info.get('duration_minutes', 0)} min\n\n"
            "¿Confirmamos?\n"
            "Responde *sí* para confirmar o *no* para cambiar el destino."
        )

    def _confirming(self, s: TaxiSession, msg: str) -> str:
        lower = msg.lower()
        if any(w in lower for w in ("sí", "si", "yes", "confirmar", "confirma", "ok", "dale", "va")):
            result = self._create_ride(s)
            if result:
                s.ride_id = result["ride_id"]
                s.state = "RIDE_ACTIVE"
                if s.scheduled_at:
                    when_txt = _format_scheduled_at(s.scheduled_at)
                    return (
                        f"✅ *¡Viaje programado!*\n\n"
                        f"🗓 Fecha: *{when_txt}*\n"
                        f"🔴 Destino: *{s.destination['name']}*\n"
                        f"💰 Tarifa estimada: *${result['fare']:.0f} MXN*\n\n"
                        f"Te avisaremos cuando un conductor confirme tu viaje.\n\n"
                        f"_Escribe *cancelar* si cambias de opinión._"
                    )
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
            s.scheduled_at = None
            return "Entendido. ¿A dónde te llevamos? 🚕"
        return (
            "Por favor responde:\n"
            "• *sí* — confirmar el viaje\n"
            "• *no* — cambiar origen o destino"
        )

    def _ride_active(self, s: TaxiSession, msg: str) -> str:
        # Auto-reset si el viaje ya terminó
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
                        "scheduled":      f"🗓 Viaje programado para *{_format_scheduled_at(s.scheduled_at)}*" if s.scheduled_at else "🗓 Viaje programado",
                        "requested":      "🔍 Buscando conductor...",
                        "confirmed":      f"✅ Conductor asignado: *{ride.get('driver_name') or 'en camino'}*",
                        "driver_arrived": "🚕 ¡Tu conductor llegó al punto de recogida!",
                        "in_progress":    "🚗 Viaje en curso, ¡disfruta el trayecto!",
                        "completed":      "✅ Viaje completado",
                        "cancelled":      "❌ Viaje cancelado",
                    }
                    return status_map.get(ride.get("status", "requested"), f"Estado: {ride.get('status')}")
        if s.scheduled_at:
            return (
                f"Tu viaje está programado 🗓\n\n"
                f"📅 Fecha: *{_format_scheduled_at(s.scheduled_at)}*\n"
                f"🔴 Destino: *{s.destination['name'] if s.destination else 'N/A'}*\n\n"
                "• Escribe *estado* para ver el progreso\n"
                "• Escribe *cancelar* si ya no lo necesitas"
            )
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
            if s.scheduled_at:
                payload["scheduled_at"] = s.scheduled_at
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
