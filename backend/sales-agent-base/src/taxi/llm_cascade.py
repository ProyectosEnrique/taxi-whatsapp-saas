"""
Cascada de proveedores LLM, mismo orden y modelos que FarmaCerca (2026-11-15):
Cerebras gpt-oss-120b → Groq gpt-oss-120b → Groq gpt-oss-20b → OpenRouter → Gemini 3.6 flash,
todos vía el SDK de OpenAI con base_url distinto. Antes: Groq llama-3.3-70b → Cerebras → Gemini 2.0 →
OpenRouter, pero llama-3.3-70b y gemini-2.0-flash ya no existen y gpt-oss-20b:free dejó de ser gratis
(solo Cerebras contestaba).

Gemini 3 exige de vuelta la "thought_signature" de cada tool call (extra_content.google); Cerebras rechaza
ese campo. _for_provider() lo quita para los demás y, para Gemini, pone la firma comodín de Google en los tool
calls que generó otro proveedor (o la recuperación de abajo).

También recupera tool calls malformados que a veces genera Groq (XML en vez de JSON).
"""
import copy
import json
import logging
import re
import uuid
from typing import Optional

from src.config import settings
from . import tools as _tools

logger = logging.getLogger(__name__)

GROQ_MODEL        = "openai/gpt-oss-120b"
GROQ_MODEL_FAST   = "openai/gpt-oss-20b"
GEMINI_MODEL      = "gemini-3.6-flash"
_GEMINI_SKIP_SIGNATURE = "skip_thought_signature_validator"   # firma comodín documentada por Google

GROQ_API_KEY      = settings.GROQ_API_KEY
CEREBRAS_API_KEY  = settings.CEREBRAS_API_KEY
GEMINI_API_KEY    = settings.GEMINI_API_KEY
OPENROUTER_API_KEY = settings.OPENROUTER_API_KEY

# Groq a veces genera el tool call como XML en vez de JSON:
# 'failed_generation': '<function=name{...}</function>'
_FAILED_GEN_RE = re.compile(
    r"'failed_generation':\s*'<function=(\w+)(\{.*?\})</function>'",
    re.DOTALL,
)
# Mismo patrón pero para cuando el LLM pone el XML en el contenido de texto (no en el error)
CONTENT_FUNC_RE = re.compile(
    r"<function=(\w+)[(\s]?(\{.*?\})\)?</function>",
    re.DOTALL,
)


def recover_tool_call(err_str: str, messages: list, phone: str, session: Optional[dict] = None) -> Optional[list]:
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
    tc_id      = f"call_{uuid.uuid4().hex[:8]}"
    result_str = _tools.run_tool(func_name, args, phone, session)
    if session is not None:
        _tools.mark_ride_sent_if_success(session, func_name, result_str)
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
            "name":         func_name,
            "content":      result_str,
        },
    ]


def _for_provider(messages: list, name: str) -> list:
    """Copia de los mensajes con extra_content solo donde el proveedor lo entiende (Gemini)."""
    if not any(m.get("tool_calls") for m in messages if isinstance(m, dict)):
        return messages
    out = copy.deepcopy(messages)
    for m in out:
        for tc in (m.get("tool_calls") or []) if isinstance(m, dict) else []:
            if name == "Gemini":
                tc.setdefault("extra_content", {"google": {"thought_signature": _GEMINI_SKIP_SIGNATURE}})
            else:
                tc.pop("extra_content", None)
    return out


class LLMCascade:
    """Inicializa los proveedores disponibles y llama al primero que responda."""

    def __init__(self):
        self._client   = None
        self._fallback = None
        self._gemini   = None
        self._openrouter = None
        try:
            from openai import OpenAI
            if GROQ_API_KEY:
                self._client = OpenAI(
                    api_key=GROQ_API_KEY,
                    base_url="https://api.groq.com/openai/v1",
                    timeout=30.0,
                    max_retries=0,
                )
                logger.info("[TaxiAgent] Groq inicializado")
            if CEREBRAS_API_KEY:
                self._fallback = OpenAI(
                    api_key=CEREBRAS_API_KEY,
                    base_url="https://api.cerebras.ai/v1",
                    timeout=30.0,
                    max_retries=0,
                )
                logger.info("[TaxiAgent] Cerebras fallback inicializado")
            if GEMINI_API_KEY:
                self._gemini = OpenAI(
                    api_key=GEMINI_API_KEY,
                    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
                    timeout=30.0,
                    max_retries=0,
                )
                logger.info("[TaxiAgent] Gemini fallback inicializado")
            if OPENROUTER_API_KEY:
                self._openrouter = OpenAI(
                    api_key=OPENROUTER_API_KEY,
                    base_url="https://openrouter.ai/api/v1",
                    timeout=20.0,
                    max_retries=0,
                    default_headers={"HTTP-Referer": "https://taxi.nexoai.lat", "X-Title": "TaxiNexoAI"},
                )
                logger.info("[TaxiAgent] OpenRouter fallback inicializado")
            if not self._client and not self._fallback and not self._gemini and not self._openrouter:
                logger.error("[TaxiAgent] Sin API keys configuradas")
        except Exception as e:
            logger.error(f"[TaxiAgent] init error: {e}")

    @property
    def has_any_provider(self) -> bool:
        return bool(self._client or self._fallback or self._gemini or self._openrouter)

    @property
    def has_primary_provider(self) -> bool:
        """Groq o Cerebras configurados (comportamiento original: process()
        solo consideraba estos dos para el guard de "servicio no disponible",
        aunque Gemini/OpenRouter sí participan en la cascada real)."""
        return bool(self._client or self._fallback)

    def create(self, messages: list, tools: list | None = None, **kwargs):
        """Intenta Cerebras primero; ante cualquier error cae al siguiente proveedor disponible."""
        providers = []
        if self._fallback:
            providers.append((self._fallback, "gpt-oss-120b",            "Cerebras"))
        if self._client:
            providers.append((self._client,   GROQ_MODEL,                "Groq"))
            providers.append((self._client,   GROQ_MODEL_FAST,           "Groq-fast"))
        if self._openrouter:
            providers.append((self._openrouter, "openai/gpt-oss-20b:free", "OpenRouter"))
        if self._gemini:
            providers.append((self._gemini,   GEMINI_MODEL,              "Gemini"))

        last_exc = RuntimeError("Sin proveedores LLM configurados")
        for i, (client, model, name) in enumerate(providers):
            try:
                kwargs_merged = {"model": model, "messages": _for_provider(messages, name), **kwargs}
                if tools:
                    kwargs_merged["tools"] = tools
                    kwargs_merged.setdefault("tool_choice", "auto")
                    kwargs_merged["parallel_tool_calls"] = False
                resp = client.chat.completions.create(**kwargs_merged)
                return resp, name
            except Exception as e:
                last_exc = e
                is_last = (i == len(providers) - 1)
                if not is_last:
                    next_name = providers[i + 1][2]
                    logger.warning(f"[TaxiAgent] {name} error ({type(e).__name__}: {str(e)[:80]}) — usando fallback {next_name}")
                    continue
                raise last_exc
        raise last_exc
