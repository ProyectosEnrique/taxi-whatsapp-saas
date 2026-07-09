"""
Cascada de proveedores LLM (Groq → Cerebras → Gemini → OpenRouter, todos
vía el SDK de OpenAI con base_url distinto) + recuperación de tool calls
malformados que a veces genera Groq llama-3.3.
"""
import json
import logging
import os
import re
import uuid
from typing import Optional

from . import tools as _tools

logger = logging.getLogger(__name__)

GROQ_API_KEY      = os.getenv("GROQ_API_KEY", "")
CEREBRAS_API_KEY  = os.getenv("CEREBRAS_API_KEY", "")
GEMINI_API_KEY    = os.getenv("GEMINI_API_KEY", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")

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


def recover_tool_call(err_str: str, messages: list, phone: str) -> Optional[list]:
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
    result_str = _tools.run_tool(func_name, args, phone)
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
                )
                logger.info("[TaxiAgent] Groq inicializado")
            if CEREBRAS_API_KEY:
                self._fallback = OpenAI(
                    api_key=CEREBRAS_API_KEY,
                    base_url="https://api.cerebras.ai/v1",
                    timeout=30.0,
                )
                logger.info("[TaxiAgent] Cerebras fallback inicializado")
            if GEMINI_API_KEY:
                self._gemini = OpenAI(
                    api_key=GEMINI_API_KEY,
                    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
                    timeout=30.0,
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
        """Intenta Groq primero; ante cualquier error cae al siguiente proveedor disponible."""
        providers = []
        if self._client:
            providers.append((self._client,   "llama-3.3-70b-versatile", "Groq"))
        if self._fallback:
            providers.append((self._fallback, "gpt-oss-120b",           "Cerebras"))
        if self._gemini:
            providers.append((self._gemini,   "gemini-2.0-flash",        "Gemini"))
        if self._openrouter:
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
