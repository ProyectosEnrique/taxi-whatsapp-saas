"""
TaxiAgent — Agente LLM para reserva de taxis via WhatsApp.
Usa Groq (llama-3.3-70b) con function calling en lugar de FSM.

Orquestador delgado: la cascada de proveedores vive en llm_cascade.py,
las herramientas en tools.py, la sesión en session.py, las llamadas a
taxi-api en taxi_client.py y el prompt en prompts.py.
"""
import json
import logging
import re
from typing import Optional

from . import llm_cascade, prompts, session as sess, taxi_client, tools

logger = logging.getLogger(__name__)

_GPS_RE = re.compile(r'^\[GPS:([-\d.]+),([-\d.]+)(?::(.+))?\]$')


def _ride_confirmation_text(session: dict) -> str:
    """Mensaje a devolver cuando crear_viaje ya tuvo éxito en una ronda anterior
    pero una ronda posterior falla — el viaje es real e irreversible, así que el
    cliente debe recibir la confirmación real, nunca un error genérico que lo
    lleve a pensar que necesita solicitar el taxi de nuevo (doble viaje real)."""
    data       = session.get("_ride_data") or {}
    ride_id    = data.get("ride_id", "—")
    tracking   = data.get("tracking_url", "")
    tracking_line = f"\n\nSigue tu viaje aquí:\n{tracking}" if tracking else ""
    return f"¡Listo! Tu viaje *{ride_id}* ya está confirmado. 🚕{tracking_line}"


class AgentResult:
    def __init__(self, text: str):
        self.response_text = text
        self.intent = "llm"

    class _State:
        value = "llm"

    new_state = _State()


class TaxiAgent:
    def __init__(self):
        self._cascade = llm_cascade.LLMCascade()

    def process(self, phone: str, message: str) -> AgentResult:
        taxi_client.init_customer(phone)

        session = sess.load(phone)
        session.pop("_ride_sent", None)
        session.pop("_ride_data", None)
        history = session.get("history", [])
        ctx     = session.setdefault("context", {})

        # Convertir GPS a texto con dirección resuelta para el LLM
        # Hacemos reverse geocode aquí para que el LLM nunca vea coordenadas crudas
        # y no intente llamar buscar_lugar() con números de latitud/longitud.
        gps_match = _GPS_RE.match(message.strip())
        if gps_match:
            lat   = float(gps_match.group(1))
            lng   = float(gps_match.group(2))
            label = gps_match.group(3) or "Mi ubicación"
            rev = taxi_client.reverse_geocode(lat, lng)
            if rev and rev.get("name"):
                address_str = rev.get("short_address") or rev.get("name")
                if rev.get("ciudad") and rev["ciudad"] not in address_str:
                    address_str = f"{address_str}, {rev['ciudad']}"
                message = (
                    f"Mi ubicación actual es: {address_str} "
                    f"(coordenadas: {lat}, {lng})"
                )
                ctx["last_gps"] = {"lat": lat, "lng": lng, "address": address_str}
                logger.info(f"[TaxiAgent] GPS resuelto: {address_str} [{lat},{lng}]")
            else:
                message = f"Mi ubicación actual es: {label} (coordenadas: {lat}, {lng})"
                ctx["last_gps"] = {"lat": lat, "lng": lng, "address": label}

        history.append({"role": "user", "content": message})

        if not self._cascade.has_primary_provider:
            err = "Servicio temporalmente no disponible. Por favor intenta de nuevo."
            history.append({"role": "assistant", "content": err})
            session["history"] = history
            sess.save(phone, session)
            return AgentResult(err)

        messages = [{"role": "system", "content": prompts.SYSTEM_PROMPT}] + history

        # Bucle de tool calling (máximo 4 rondas)
        for round_num in range(4):
            try:
                resp, provider = self._cascade.create(
                    messages,
                    tools=tools.TOOLS,
                    max_tokens=600,
                    temperature=0.3,
                )
            except Exception as e:
                err_str = str(e)

                if session.get("_ride_sent"):
                    # crear_viaje ya se ejecutó con éxito en una ronda anterior — el viaje
                    # es real e irreversible. NUNCA responder con un error genérico aquí
                    # (llevaría al cliente a pensar que debe pedir el taxi de nuevo) ni
                    # reintentar/reset del historial (podría hacer que el LLM, sin memoria
                    # de que ya se creó el viaje, vuelva a llamar crear_viaje).
                    logger.warning(
                        f"[TaxiAgent] Proveedor falló tras crear_viaje (viaje ya confirmado) "
                        f"[{phone}]: {err_str[:120]}"
                    )
                    reply = _ride_confirmation_text(session)
                    history.append({"role": "assistant", "content": reply})
                    session["history"] = history
                    sess.save(phone, session)
                    return AgentResult(reply)

                # Groq occasionally generates malformed XML tool calls
                if "tool_use_failed" in err_str:
                    # Attempt to parse & execute the malformed tool call
                    recovered = llm_cascade.recover_tool_call(err_str, messages, phone, session)
                    if recovered:
                        messages = recovered
                        continue  # let the loop produce a final text response
                    # Can't recover — fall back to plain-text reply without tools
                    logger.warning(f"[TaxiAgent] tool_use_failed (no recovery), retrying text [{phone}]")
                    try:
                        resp, provider = self._cascade.create(messages, max_tokens=600, temperature=0.3)
                    except Exception as e2:
                        logger.error(f"[TaxiAgent] retry error [{phone}]: {e2}")
                        err = "Lo siento, hubo un error. Por favor intenta de nuevo."
                        history.append({"role": "assistant", "content": err})
                        session["history"] = history
                        sess.save(phone, session)
                        return AgentResult(err)
                elif "tool call validation failed" in err_str or "400" in err_str:
                    # Historial corrupto — limpiar y reintentar con solo el mensaje actual
                    logger.warning(f"[TaxiAgent] Historial corrupto, limpiando sesión [{phone}]")
                    history = []
                    messages = [{"role": "system", "content": prompts.SYSTEM_PROMPT}, {"role": "user", "content": message}]
                    session["history"] = []
                    sess.save(phone, session)
                    try:
                        resp, provider = self._cascade.create(messages, tools=tools.TOOLS, max_tokens=600, temperature=0.3)
                    except Exception as e2:
                        logger.error(f"[TaxiAgent] retry after reset error [{phone}]: {e2}")
                        return AgentResult("Lo siento, hubo un problema. Por favor escríbeme de nuevo.")
                else:
                    logger.error(f"[TaxiAgent] LLM error [{phone}]: {e}")
                    err = "Lo siento, hubo un error. Por favor intenta de nuevo."
                    history.append({"role": "assistant", "content": err})
                    session["history"] = history
                    sess.save(phone, session)
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
                    result_str = tools.run_tool(tc.function.name, args, phone, session)
                    tools.mark_ride_sent_if_success(session, tc.function.name, result_str)
                    logger.info(f"[TaxiAgent] {tc.function.name} → {result_str[:100]}")
                    messages.append({
                        "role":         "tool",
                        "tool_call_id": tc.id,
                        "name":         tc.function.name,
                        "content":      result_str,
                    })
                # Continuar bucle para respuesta final
            else:
                # Respuesta de texto final
                final_text = (msg.content or "").strip()

                # Detectar tool calls XML embebidas en el contenido (Groq quirk)
                xml_m = llm_cascade.CONTENT_FUNC_RE.search(final_text)
                if xml_m and round_num < 3:
                    func_name = xml_m.group(1)
                    try:
                        args = json.loads(xml_m.group(2))
                    except Exception:
                        args = {}
                    logger.warning(f"[TaxiAgent] XML tool en contenido: {func_name}({args})")
                    import uuid
                    tc_id      = f"call_{uuid.uuid4().hex[:8]}"
                    result_str = tools.run_tool(func_name, args, phone, session)
                    tools.mark_ride_sent_if_success(session, func_name, result_str)
                    messages.append({
                        "role": "assistant", "content": None,
                        "tool_calls": [{"id": tc_id, "type": "function",
                                        "function": {"name": func_name, "arguments": json.dumps(args)}}],
                    })
                    messages.append({"role": "tool", "tool_call_id": tc_id, "name": func_name, "content": result_str})
                    continue  # siguiente ronda para respuesta final limpia

                history.append({"role": "assistant", "content": final_text})
                session["history"] = history
                sess.save(phone, session)
                return AgentResult(final_text)

        # Fallback si se agotaron rondas
        if session.get("_ride_sent"):
            fallback = _ride_confirmation_text(session)
        else:
            fallback = "Perdón, no pude completar la solicitud. ¿Puedes repetirla?"
        history.append({"role": "assistant", "content": fallback})
        session["history"] = history
        sess.save(phone, session)
        return AgentResult(fallback)


# ── Singleton ──────────────────────────────────────────────────────────────────

_instance: Optional[TaxiAgent] = None


def get_taxi_agent() -> TaxiAgent:
    global _instance
    if _instance is None:
        _instance = TaxiAgent()
    return _instance
