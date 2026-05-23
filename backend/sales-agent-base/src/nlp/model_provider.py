"""
================================================================================
MODEL PROVIDER - PATRÓN STRATEGY PARA LLM
================================================================================
Permite cambiar entre diferentes proveedores de LLM:
- Cerebras (nube) - Llama 3.3 70B (gratis, ultra-rápido) ⭐ PRINCIPAL
- Gemini (nube) - Gemini 1.5 Pro (premium, para casos complejos)
- Groq (nube) - Llama 3.1 8B (gratis, rápido) - Fallback
- OpenAI (nube) - GPT-4o (premium) - Legacy
- LoRA Local - Mistral 7B fine-tuned (SOLO fallback offline)

Cascade (modo recomendado): Cerebras → Gemini → LoRA
- Cerebras maneja 99% de consultas (gratis, rápido)
- Gemini para objeciones/quejas (más inteligente)
- LoRA solo cuando NO hay internet (offline mode)

Configuración via .env:
- LLM_PROVIDER=cascade (recomendado)
- CEREBRAS_API_KEY=csk-xxx
- GOOGLE_API_KEY=xxx (para Gemini)
- LORA_MODEL_PATH=ruta/al/modelo (para fallback offline)
================================================================================
"""

import logging
import time
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


class LLMProviderType(Enum):
    """Tipos de proveedores LLM disponibles"""
    CEREBRAS = "cerebras"   # Cerebras Cloud (Llama 3.3 70B) - Gratis, Ultra-rápido ⭐
    GROQ = "groq"           # Groq Cloud (Llama 3.1 8B) - Gratis
    GEMINI = "gemini"       # Google Gemini 1.5 Pro - Premium (reemplaza GPT-4o) ⭐
    OPENAI = "openai"       # OpenAI (GPT-4o) - Premium (legacy)
    LORA = "lora"           # Modelo LoRA local (TinyLlama/Mistral fine-tuned)
    OLLAMA = "ollama"       # Ollama Server (Mistral 7B local) - Modo Offline ⭐
    CASCADE = "cascade"     # Cadena: Cerebras → Gemini → Ollama → LoRA


@dataclass
class ProviderMetrics:
    """Métricas de uso de un provider"""
    provider_name: str
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    total_tokens: int = 0
    total_latency_ms: float = 0.0
    estimated_cost_usd: float = 0.0

    def record_call(self, success: bool, tokens: int, latency_ms: float, cost: float = 0.0):
        """Registra una llamada al provider"""
        self.total_calls += 1
        if success:
            self.successful_calls += 1
        else:
            self.failed_calls += 1
        self.total_tokens += tokens
        self.total_latency_ms += latency_ms
        self.estimated_cost_usd += cost

    @property
    def avg_latency_ms(self) -> float:
        return self.total_latency_ms / self.total_calls if self.total_calls > 0 else 0

    @property
    def success_rate(self) -> float:
        return self.successful_calls / self.total_calls if self.total_calls > 0 else 0

    def to_dict(self) -> Dict:
        return {
            "provider": self.provider_name,
            "total_calls": self.total_calls,
            "successful_calls": self.successful_calls,
            "failed_calls": self.failed_calls,
            "success_rate": f"{self.success_rate:.1%}",
            "total_tokens": self.total_tokens,
            "avg_latency_ms": f"{self.avg_latency_ms:.0f}",
            "estimated_cost_usd": f"${self.estimated_cost_usd:.4f}"
        }


class BaseLLMProvider(ABC):
    """
    Clase base abstracta para proveedores de LLM.
    Implementa el patrón Strategy.
    """

    @abstractmethod
    def generate(
        self,
        prompt: str,
        messages: List[Dict] = None,
        temperature: float = 0.7,
        max_tokens: int = 300
    ) -> Dict[str, Any]:
        """
        Genera una respuesta del LLM.

        Args:
            prompt: Prompt del sistema
            messages: Lista de mensajes de conversación
            temperature: Creatividad (0.0-1.0)
            max_tokens: Máximo de tokens en respuesta

        Returns:
            Dict con response_text, tokens_used, provider
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Verifica si el proveedor está disponible"""
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Nombre del proveedor"""
        pass


class GroqProvider(BaseLLMProvider):
    """
    Proveedor que usa Groq Cloud API.
    Modelo: Llama 3.1 8B Instant
    """

    def __init__(self, api_key: str, model: str = "llama-3.1-8b-instant"):
        self.api_key = api_key
        self.model = model
        self._client = None
        self._available = None

    @property
    def client(self):
        """Lazy loading del cliente Groq"""
        if self._client is None:
            try:
                from groq import Groq
                self._client = Groq(api_key=self.api_key)
                logger.info(f"[GROQ] Cliente inicializado (model: {self.model})")
            except Exception as e:
                logger.error(f"[GROQ] Error inicializando cliente: {e}")
                self._client = False
        return self._client if self._client else None

    def is_available(self) -> bool:
        if self._available is None:
            self._available = self.client is not None
        return self._available

    @property
    def provider_name(self) -> str:
        return "groq"

    def generate(
        self,
        prompt: str,
        messages: List[Dict] = None,
        temperature: float = 0.7,
        max_tokens: int = 300
    ) -> Dict[str, Any]:

        if not self.is_available():
            return {
                "response_text": "",
                "error": "Groq no disponible",
                "provider": self.provider_name
            }

        try:
            # Preparar mensajes
            api_messages = [{"role": "system", "content": prompt}]

            if messages:
                for msg in messages:
                    role = "user" if msg.get('role') == 'user' else "assistant"
                    api_messages.append({
                        "role": role,
                        "content": msg.get('content', '')
                    })

            # Llamar a Groq
            response = self.client.chat.completions.create(
                model=self.model,
                messages=api_messages,
                temperature=temperature,
                max_tokens=max_tokens
            )

            response_text = response.choices[0].message.content.strip()
            tokens_used = response.usage.total_tokens if hasattr(response, 'usage') else 0

            logger.debug(f"[GROQ] Respuesta generada: {len(response_text)} chars")

            return {
                "response_text": response_text,
                "tokens_used": tokens_used,
                "provider": self.provider_name,
                "model": self.model
            }

        except Exception as e:
            logger.error(f"[GROQ] Error generando respuesta: {e}")
            return {
                "response_text": "",
                "error": str(e),
                "provider": self.provider_name
            }


class CerebrasProvider(BaseLLMProvider):
    """
    Proveedor que usa Cerebras Cloud API.
    Modelo: Llama 3.3 70B (gratis, 6x más rápido que Groq)

    Límites gratuitos:
    - 30 requests/minuto
    - 1 millón tokens/día
    - ~1000 tokens/segundo (ultra-rápido)

    Obtener API key: https://cloud.cerebras.ai/
    """

    def __init__(self, api_key: str, model: str = "llama-3.3-70b"):
        self.api_key = api_key
        self.model = model
        self._client = None
        self._available = None
        self.metrics = ProviderMetrics(provider_name="cerebras")

    @property
    def client(self):
        """Lazy loading del cliente Cerebras (compatible con OpenAI SDK)"""
        if self._client is None:
            try:
                from openai import OpenAI
                self._client = OpenAI(
                    api_key=self.api_key,
                    base_url="https://api.cerebras.ai/v1"
                )
                logger.info(f"[CEREBRAS] Cliente inicializado (model: {self.model})")
            except Exception as e:
                logger.error(f"[CEREBRAS] Error inicializando cliente: {e}")
                self._client = False
        return self._client if self._client else None

    def is_available(self) -> bool:
        if self._available is None:
            self._available = self.client is not None and bool(self.api_key)
        return self._available

    @property
    def provider_name(self) -> str:
        return "cerebras"

    def generate(
        self,
        prompt: str,
        messages: List[Dict] = None,
        temperature: float = 0.7,
        max_tokens: int = 300
    ) -> Dict[str, Any]:

        if not self.is_available():
            return {
                "response_text": "",
                "error": "Cerebras no disponible",
                "provider": self.provider_name
            }

        start_time = time.time()

        try:
            # Preparar mensajes
            api_messages = [{"role": "system", "content": prompt}]

            if messages:
                for msg in messages:
                    role = "user" if msg.get('role') == 'user' else "assistant"
                    api_messages.append({
                        "role": role,
                        "content": msg.get('content', '')
                    })

            # Llamar a Cerebras (API compatible con OpenAI)
            response = self.client.chat.completions.create(
                model=self.model,
                messages=api_messages,
                temperature=temperature,
                max_tokens=max_tokens
            )

            response_text = response.choices[0].message.content.strip()
            tokens_used = response.usage.total_tokens if hasattr(response, 'usage') else 0

            latency_ms = (time.time() - start_time) * 1000
            self.metrics.record_call(True, tokens_used, latency_ms, 0)  # Gratis

            logger.debug(f"[CEREBRAS] Respuesta generada: {len(response_text)} chars, {latency_ms:.0f}ms")

            return {
                "response_text": response_text,
                "tokens_used": tokens_used,
                "latency_ms": latency_ms,
                "provider": self.provider_name,
                "model": self.model,
                "cost_usd": 0  # Cerebras es gratis
            }

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            self.metrics.record_call(False, 0, latency_ms, 0)
            logger.error(f"[CEREBRAS] Error generando respuesta: {e}")
            return {
                "response_text": "",
                "error": str(e),
                "provider": self.provider_name
            }


class GeminiProvider(BaseLLMProvider):
    """
    Proveedor que usa Google Gemini API.
    Modelo: Gemini 1.5 Pro (premium, reemplaza GPT-4o)

    Ventajas sobre GPT-4o:
    - 50% más barato ($1.25/1M input vs $2.50)
    - 1M tokens de contexto (vs 128K)
    - Free tier generoso (1,500 req/día gratis)

    Costos (Dic 2024):
    - Gemini 1.5 Pro: $1.25/1M input, $5/1M output
    - Gemini 1.5 Flash: $0.075/1M input, $0.30/1M output

    Obtener API key: https://aistudio.google.com/app/apikey
    """

    COST_PER_1K_INPUT = {
        "gemini-1.5-pro": 0.00125,
        "gemini-1.5-flash": 0.000075,
        "gemini-1.5-flash-8b": 0.0000375,
        "gemini-2.0-flash-exp": 0.0  # Experimental, gratis por ahora
    }
    COST_PER_1K_OUTPUT = {
        "gemini-1.5-pro": 0.005,
        "gemini-1.5-flash": 0.0003,
        "gemini-1.5-flash-8b": 0.00015,
        "gemini-2.0-flash-exp": 0.0
    }

    def __init__(self, api_key: str, model: str = "gemini-2.0-flash-exp"):
        self.api_key = api_key
        self.model = model
        self._client = None
        self._available = None
        self.metrics = ProviderMetrics(provider_name="gemini")

    @property
    def client(self):
        """Lazy loading del cliente Gemini"""
        if self._client is None:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                self._client = genai.GenerativeModel(self.model)
                logger.info(f"[GEMINI] Cliente inicializado (model: {self.model})")
            except ImportError:
                logger.error("[GEMINI] Librería google-generativeai no instalada. Ejecuta: pip install google-generativeai")
                self._client = False
            except Exception as e:
                logger.error(f"[GEMINI] Error inicializando cliente: {e}")
                self._client = False
        return self._client if self._client else None

    def is_available(self) -> bool:
        if self._available is None:
            self._available = self.client is not None and bool(self.api_key)
        return self._available

    @property
    def provider_name(self) -> str:
        return "gemini"

    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calcula el costo estimado de la llamada"""
        input_cost = (input_tokens / 1000) * self.COST_PER_1K_INPUT.get(self.model, 0.00125)
        output_cost = (output_tokens / 1000) * self.COST_PER_1K_OUTPUT.get(self.model, 0.005)
        return input_cost + output_cost

    def generate(
        self,
        prompt: str,
        messages: List[Dict] = None,
        temperature: float = 0.7,
        max_tokens: int = 300
    ) -> Dict[str, Any]:

        if not self.is_available():
            return {
                "response_text": "",
                "error": "Gemini no disponible",
                "provider": self.provider_name
            }

        start_time = time.time()

        try:
            import google.generativeai as genai

            # Construir el contenido de la conversación
            # Gemini usa un formato diferente para el historial
            chat_history = []

            # Agregar mensajes previos al historial
            if messages:
                for msg in messages[:-1]:  # Todos excepto el último
                    role = "user" if msg.get('role') == 'user' else "model"
                    chat_history.append({
                        "role": role,
                        "parts": [msg.get('content', '')]
                    })

            # Configurar generación
            generation_config = genai.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
            )

            # Crear chat con historial y system instruction
            chat = self._client.start_chat(history=chat_history)

            # Obtener el último mensaje del usuario
            last_user_message = ""
            if messages:
                for msg in reversed(messages):
                    if msg.get('role') == 'user':
                        last_user_message = msg.get('content', '')
                        break

            # Si no hay mensaje, usar prompt como contexto
            if not last_user_message:
                last_user_message = "Hola"

            # Enviar mensaje con contexto del sistema
            full_prompt = f"{prompt}\n\nUsuario: {last_user_message}"
            response = chat.send_message(full_prompt, generation_config=generation_config)

            response_text = response.text.strip()

            # Estimar tokens (Gemini no siempre retorna usage)
            input_tokens = len(full_prompt.split()) * 1.3  # Aproximación
            output_tokens = len(response_text.split()) * 1.3
            total_tokens = int(input_tokens + output_tokens)

            # Calcular costo
            cost = self._calculate_cost(int(input_tokens), int(output_tokens))

            latency_ms = (time.time() - start_time) * 1000
            self.metrics.record_call(True, total_tokens, latency_ms, cost)

            logger.debug(f"[GEMINI] Respuesta generada: {len(response_text)} chars, ${cost:.4f}")

            return {
                "response_text": response_text,
                "tokens_used": total_tokens,
                "input_tokens": int(input_tokens),
                "output_tokens": int(output_tokens),
                "cost_usd": cost,
                "latency_ms": latency_ms,
                "provider": self.provider_name,
                "model": self.model
            }

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            self.metrics.record_call(False, 0, latency_ms, 0)
            logger.error(f"[GEMINI] Error generando respuesta: {e}")
            return {
                "response_text": "",
                "error": str(e),
                "provider": self.provider_name
            }


class OpenAIProvider(BaseLLMProvider):
    """
    Proveedor que usa OpenAI API.
    Modelo: GPT-4o (premium, más inteligente)

    Costos aproximados (Dic 2024):
    - GPT-4o: $2.50/1M input tokens, $10/1M output tokens
    - GPT-4o-mini: $0.15/1M input, $0.60/1M output
    """

    # Costos por 1000 tokens (para métricas)
    COST_PER_1K_INPUT = {
        "gpt-4o": 0.0025,
        "gpt-4o-mini": 0.00015,
        "gpt-4-turbo": 0.01,
        "gpt-3.5-turbo": 0.0005
    }
    COST_PER_1K_OUTPUT = {
        "gpt-4o": 0.01,
        "gpt-4o-mini": 0.0006,
        "gpt-4-turbo": 0.03,
        "gpt-3.5-turbo": 0.0015
    }

    def __init__(self, api_key: str, model: str = "gpt-4o"):
        self.api_key = api_key
        self.model = model
        self._client = None
        self._available = None
        self.metrics = ProviderMetrics(provider_name="openai")

    @property
    def client(self):
        """Lazy loading del cliente OpenAI"""
        if self._client is None:
            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=self.api_key)
                logger.info(f"[OPENAI] Cliente inicializado (model: {self.model})")
            except ImportError:
                logger.error("[OPENAI] Librería openai no instalada. Ejecuta: pip install openai")
                self._client = False
            except Exception as e:
                logger.error(f"[OPENAI] Error inicializando cliente: {e}")
                self._client = False
        return self._client if self._client else None

    def is_available(self) -> bool:
        if self._available is None:
            self._available = self.client is not None and bool(self.api_key)
        return self._available

    @property
    def provider_name(self) -> str:
        return "openai"

    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calcula el costo estimado de la llamada"""
        input_cost = (input_tokens / 1000) * self.COST_PER_1K_INPUT.get(self.model, 0.0025)
        output_cost = (output_tokens / 1000) * self.COST_PER_1K_OUTPUT.get(self.model, 0.01)
        return input_cost + output_cost

    def generate(
        self,
        prompt: str,
        messages: List[Dict] = None,
        temperature: float = 0.7,
        max_tokens: int = 300
    ) -> Dict[str, Any]:

        if not self.is_available():
            return {
                "response_text": "",
                "error": "OpenAI no disponible",
                "provider": self.provider_name
            }

        start_time = time.time()

        try:
            # Preparar mensajes
            api_messages = [{"role": "system", "content": prompt}]

            if messages:
                for msg in messages:
                    role = "user" if msg.get('role') == 'user' else "assistant"
                    api_messages.append({
                        "role": role,
                        "content": msg.get('content', '')
                    })

            # Llamar a OpenAI
            response = self.client.chat.completions.create(
                model=self.model,
                messages=api_messages,
                temperature=temperature,
                max_tokens=max_tokens
            )

            response_text = response.choices[0].message.content.strip()

            # Extraer uso de tokens
            input_tokens = response.usage.prompt_tokens if response.usage else 0
            output_tokens = response.usage.completion_tokens if response.usage else 0
            total_tokens = input_tokens + output_tokens

            # Calcular costo
            cost = self._calculate_cost(input_tokens, output_tokens)

            # Registrar métricas
            latency_ms = (time.time() - start_time) * 1000
            self.metrics.record_call(True, total_tokens, latency_ms, cost)

            logger.debug(f"[OPENAI] Respuesta generada: {len(response_text)} chars, ${cost:.4f}")

            return {
                "response_text": response_text,
                "tokens_used": total_tokens,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cost_usd": cost,
                "latency_ms": latency_ms,
                "provider": self.provider_name,
                "model": self.model
            }

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            self.metrics.record_call(False, 0, latency_ms, 0)
            logger.error(f"[OPENAI] Error generando respuesta: {e}")
            return {
                "response_text": "",
                "error": str(e),
                "provider": self.provider_name
            }


class LoRAProvider(BaseLLMProvider):
    """
    Proveedor que usa modelo LoRA local.

    Modelos soportados:
    - TinyLlama 1.1B + LoRA (legacy, bajo rendimiento)
    - Mistral 7B + LoRA (RECOMENDADO, mejor calidad)

    El modelo base se detecta automáticamente según el adaptador LoRA.
    """

    # Mapeo de modelos base soportados
    SUPPORTED_BASE_MODELS = {
        "tinyllama": "TinyLlama/TinyLlama-1.1B-Chat-v1.0",
        "mistral": "mistralai/Mistral-7B-Instruct-v0.3",
        "mistral-v0.2": "mistralai/Mistral-7B-Instruct-v0.2",
        "llama2-7b": "meta-llama/Llama-2-7b-chat-hf",
    }

    def __init__(self, model_path: str, device: str = "auto", base_model: str = None):
        """
        Args:
            model_path: Ruta al adaptador LoRA
            device: Dispositivo (auto, cuda, cpu)
            base_model: Modelo base (auto-detecta si es None)
        """
        self.model_path = model_path
        self.device = device
        self.base_model_override = base_model
        self._model = None
        self._tokenizer = None
        self._available = None
        self._loaded = False
        self._detected_base_model = None
        self._is_mistral = False

    def _detect_base_model(self) -> str:
        """Detecta el modelo base del adaptador LoRA"""
        import os
        import json

        adapter_config_path = os.path.join(self.model_path, "adapter_config.json")

        if os.path.exists(adapter_config_path):
            try:
                with open(adapter_config_path, 'r') as f:
                    config = json.load(f)
                    base_model = config.get("base_model_name_or_path", "")

                    # Detectar tipo de modelo
                    if "mistral" in base_model.lower():
                        self._is_mistral = True
                        return base_model
                    elif "tinyllama" in base_model.lower():
                        return base_model
                    elif "llama" in base_model.lower():
                        return base_model

            except Exception as e:
                logger.warning(f"[LORA] No se pudo leer adapter_config.json: {e}")

        # Fallback a TinyLlama (legacy)
        return self.SUPPORTED_BASE_MODELS["tinyllama"]

    def _load_model(self):
        """Carga el modelo LoRA (lazy loading)"""
        if self._loaded:
            return

        try:
            import torch
            from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
            from peft import PeftModel

            logger.info(f"[LORA] Cargando modelo desde: {self.model_path}")

            # Detectar modelo base
            if self.base_model_override:
                base_model = self.base_model_override
                self._is_mistral = "mistral" in base_model.lower()
            else:
                base_model = self._detect_base_model()

            self._detected_base_model = base_model
            logger.info(f"[LORA] Modelo base detectado: {base_model}")
            logger.info(f"[LORA] Es Mistral: {self._is_mistral}")

            # Cargar tokenizer
            self._tokenizer = AutoTokenizer.from_pretrained(base_model, trust_remote_code=True)
            self._tokenizer.pad_token = self._tokenizer.eos_token

            # Detectar dispositivo
            if self.device == "auto":
                device_map = "cuda" if torch.cuda.is_available() else "cpu"
            else:
                device_map = self.device

            # Configuración según modelo
            if self._is_mistral and device_map == "cuda":
                # Mistral 7B requiere cuantización 4-bit en GPUs con menos de 16GB VRAM
                logger.info("[LORA] Usando cuantización 4-bit para Mistral 7B")
                bnb_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype=torch.bfloat16,
                    bnb_4bit_quant_type="nf4",
                    bnb_4bit_use_double_quant=True,
                )
                base = AutoModelForCausalLM.from_pretrained(
                    base_model,
                    quantization_config=bnb_config,
                    device_map=device_map,
                    trust_remote_code=True,
                )
            else:
                # TinyLlama o CPU: sin cuantización
                base = AutoModelForCausalLM.from_pretrained(
                    base_model,
                    torch_dtype=torch.float16 if device_map == "cuda" else torch.float32,
                    device_map=device_map,
                    trust_remote_code=True,
                )

            # Cargar adaptador LoRA
            self._model = PeftModel.from_pretrained(base, self.model_path)
            self._model.eval()

            self._loaded = True
            self._available = True
            model_type = "Mistral 7B" if self._is_mistral else "TinyLlama 1.1B"
            logger.info(f"[LORA] Modelo {model_type} cargado exitosamente en {device_map}")

        except Exception as e:
            logger.error(f"[LORA] Error cargando modelo: {e}")
            self._available = False
            self._loaded = True

    def is_available(self) -> bool:
        if self._available is None:
            self._load_model()
        return self._available

    @property
    def provider_name(self) -> str:
        return "lora"

    def generate(
        self,
        prompt: str,
        messages: List[Dict] = None,
        temperature: float = 0.7,
        max_tokens: int = 300
    ) -> Dict[str, Any]:

        if not self.is_available():
            return {
                "response_text": "",
                "error": "Modelo LoRA no disponible",
                "provider": self.provider_name
            }

        try:
            import torch

            # Construir prompt en formato de conversación
            conversation = self._build_conversation_prompt(prompt, messages)

            # Tokenizar
            inputs = self._tokenizer(
                conversation,
                return_tensors="pt",
                truncation=True,
                max_length=512
            ).to(self._model.device)

            # Generar
            with torch.no_grad():
                outputs = self._model.generate(
                    **inputs,
                    max_new_tokens=max_tokens,
                    temperature=temperature,
                    do_sample=temperature > 0,
                    pad_token_id=self._tokenizer.eos_token_id,
                    eos_token_id=self._tokenizer.eos_token_id
                )

            # Decodificar solo los tokens nuevos
            response_text = self._tokenizer.decode(
                outputs[0][inputs['input_ids'].shape[1]:],
                skip_special_tokens=True
            ).strip()

            # Limpiar respuesta (quitar prefijos comunes)
            response_text = self._clean_response(response_text)

            logger.debug(f"[LORA] Respuesta generada: {len(response_text)} chars")

            model_name = "Mistral-7B-LoRA-Restaurant" if self._is_mistral else "TinyLlama-LoRA-Restaurant"
            return {
                "response_text": response_text,
                "tokens_used": len(outputs[0]),
                "provider": self.provider_name,
                "model": model_name
            }

        except Exception as e:
            logger.error(f"[LORA] Error generando respuesta: {e}")
            return {
                "response_text": "",
                "error": str(e),
                "provider": self.provider_name
            }

    def _build_conversation_prompt(self, system_prompt: str, messages: List[Dict] = None) -> str:
        """Construye el prompt en formato de conversación según el modelo"""

        if self._is_mistral:
            return self._build_mistral_prompt(system_prompt, messages)
        else:
            return self._build_tinyllama_prompt(system_prompt, messages)

    def _build_mistral_prompt(self, system_prompt: str, messages: List[Dict] = None) -> str:
        """Construye prompt en formato Mistral Instruct"""
        # Formato: [INST] system + user [/INST] assistant

        # Obtener último mensaje del usuario
        last_user_msg = ""
        if messages:
            for msg in reversed(messages):
                if msg.get('role') == 'user':
                    last_user_msg = msg.get('content', '')
                    break

        if not last_user_msg:
            last_user_msg = "Hola"

        # Formato Mistral con system prompt incluido
        prompt = f"[INST] {system_prompt}\n\nCliente: {last_user_msg} [/INST]"
        return prompt

    def _build_tinyllama_prompt(self, system_prompt: str, messages: List[Dict] = None) -> str:
        """Construye prompt en formato simple para TinyLlama"""
        parts = []

        # Agregar contexto del sistema (resumido)
        if system_prompt:
            short_prompt = system_prompt[:500] if len(system_prompt) > 500 else system_prompt
            parts.append(f"Sistema: {short_prompt}\n")

        # Agregar mensajes de conversación
        if messages:
            for msg in messages[-3:]:  # Solo últimos 3 mensajes
                role = "Cliente" if msg.get('role') == 'user' else "Agente"
                content = msg.get('content', '')
                parts.append(f"{role}: {content}")

        parts.append("Agente:")

        return "\n".join(parts)

    def _clean_response(self, text: str) -> str:
        """Limpia la respuesta del modelo"""
        text = text.strip()

        # Limpiar formato Mistral
        if "[/INST]" in text:
            text = text.split("[/INST]")[-1].strip()

        # Si hay "Cliente:" en la respuesta, cortar ahí
        if "Cliente:" in text:
            text = text.split("Cliente:")[0].strip()

        # Quitar prefijos comunes
        prefixes_to_remove = ["Agente:", "Asistente:", "Bot:", "[INST]"]
        for prefix in prefixes_to_remove:
            if text.startswith(prefix):
                text = text[len(prefix):].strip()

        return text


class OllamaProvider(BaseLLMProvider):
    """
    Proveedor que usa Ollama como servidor LLM local.
    Ideal para modo offline cuando no hay conexión a internet.

    Características:
    - Ejecuta modelos localmente via Ollama
    - Soporta Mistral 7B (compatible con pesos LoRA)
    - Sin límites de rate ni costos
    - Requiere ~8GB RAM para Mistral 7B

    Configuración:
    - OLLAMA_URL: http://ollama:11434 (en Docker)
    - OLLAMA_MODEL: mistral:7b-instruct (por defecto)
    """

    def __init__(self, base_url: str = "http://ollama:11434", model: str = "mistral:7b-instruct"):
        self.base_url = base_url.rstrip('/')
        self.model = model
        self._available = None
        self.metrics = ProviderMetrics(provider_name="ollama")

    def is_available(self) -> bool:
        """Verifica si Ollama está disponible haciendo ping al servidor"""
        if self._available is not None:
            return self._available

        try:
            import requests
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            self._available = response.status_code == 200
            if self._available:
                logger.info(f"[OLLAMA] Servidor disponible en {self.base_url}")
            return self._available
        except Exception as e:
            logger.warning(f"[OLLAMA] Servidor no disponible: {e}")
            self._available = False
            return False

    @property
    def provider_name(self) -> str:
        return "ollama"

    def generate(
        self,
        prompt: str,
        messages: List[Dict] = None,
        temperature: float = 0.7,
        max_tokens: int = 300
    ) -> Dict[str, Any]:

        if not self.is_available():
            return {
                "response_text": "",
                "error": "Ollama no disponible",
                "provider": self.provider_name
            }

        start_time = time.time()

        try:
            import requests

            # Construir el prompt completo
            full_prompt = self._build_prompt(prompt, messages)

            # Llamar a Ollama API
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": full_prompt,
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                        "num_predict": max_tokens,
                    }
                },
                timeout=60
            )

            if response.status_code != 200:
                raise Exception(f"HTTP {response.status_code}: {response.text}")

            result = response.json()
            response_text = result.get('response', '').strip()

            # Calcular métricas
            latency_ms = (time.time() - start_time) * 1000
            tokens_used = result.get('eval_count', len(response_text.split()))

            self.metrics.record_call(True, tokens_used, latency_ms, 0)  # Sin costo

            logger.debug(f"[OLLAMA] Respuesta generada: {len(response_text)} chars, {latency_ms:.0f}ms")

            return {
                "response_text": response_text,
                "tokens_used": tokens_used,
                "latency_ms": latency_ms,
                "provider": self.provider_name,
                "model": self.model,
                "cost_usd": 0  # Local = gratis
            }

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            self.metrics.record_call(False, 0, latency_ms, 0)
            logger.error(f"[OLLAMA] Error generando respuesta: {e}")
            return {
                "response_text": "",
                "error": str(e),
                "provider": self.provider_name
            }

    def _build_prompt(self, system_prompt: str, messages: List[Dict] = None) -> str:
        """Construye el prompt en formato Mistral Instruct"""
        # Obtener último mensaje del usuario
        last_user_msg = ""
        if messages:
            for msg in reversed(messages):
                if msg.get('role') == 'user':
                    last_user_msg = msg.get('content', '')
                    break

        if not last_user_msg:
            last_user_msg = "Hola"

        # Formato Mistral Instruct
        return f"[INST] {system_prompt}\n\nCliente: {last_user_msg} [/INST]"

    def ensure_model_available(self) -> bool:
        """Verifica que el modelo esté descargado, si no lo descarga"""
        try:
            import requests

            # Verificar si el modelo existe
            response = requests.get(f"{self.base_url}/api/tags", timeout=10)
            if response.status_code == 200:
                models = response.json().get('models', [])
                model_names = [m.get('name', '') for m in models]

                if self.model in model_names or any(self.model in name for name in model_names):
                    logger.info(f"[OLLAMA] Modelo {self.model} disponible")
                    return True

            # Modelo no existe, intentar descargarlo
            logger.info(f"[OLLAMA] Descargando modelo {self.model}...")
            pull_response = requests.post(
                f"{self.base_url}/api/pull",
                json={"name": self.model},
                timeout=600  # 10 minutos para descarga
            )
            return pull_response.status_code == 200

        except Exception as e:
            logger.error(f"[OLLAMA] Error verificando modelo: {e}")
            return False


class HybridProvider(BaseLLMProvider):
    """
    Proveedor híbrido simple que usa LoRA para respuestas rápidas
    y Groq como fallback para casos complejos.

    NOTA: Usar CascadeProvider para funcionalidad más avanzada.
    """

    def __init__(self, lora_provider: LoRAProvider, groq_provider: GroqProvider):
        self.lora = lora_provider
        self.groq = groq_provider
        self.lora_max_input_length = 100

    def is_available(self) -> bool:
        return self.lora.is_available() or self.groq.is_available()

    @property
    def provider_name(self) -> str:
        return "hybrid"

    def generate(
        self,
        prompt: str,
        messages: List[Dict] = None,
        temperature: float = 0.7,
        max_tokens: int = 300
    ) -> Dict[str, Any]:

        use_lora = self._should_use_lora(prompt, messages)

        if use_lora and self.lora.is_available():
            result = self.lora.generate(prompt, messages, temperature, max_tokens)

            if result.get('error') or len(result.get('response_text', '')) < 10:
                logger.info("[HYBRID] LoRA falló, usando Groq como fallback")
                result = self.groq.generate(prompt, messages, temperature, max_tokens)
                result['fallback_used'] = True

            return result

        return self.groq.generate(prompt, messages, temperature, max_tokens)

    def _should_use_lora(self, prompt: str, messages: List[Dict] = None) -> bool:
        if not self.lora.is_available():
            return False
        if len(prompt) > 1000:
            return False
        if messages and len(messages) > 5:
            return False

        last_user_msg = ""
        if messages:
            for msg in reversed(messages):
                if msg.get('role') == 'user':
                    last_user_msg = msg.get('content', '')
                    break

        if len(last_user_msg) > self.lora_max_input_length:
            return False

        return True


class CascadeProvider(BaseLLMProvider):
    """
    Proveedor en cascada inteligente.

    Flujo: Cerebras → Gemini → LoRA
    (LoRA solo como último recurso cuando no hay internet)

    Características:
    - Prioriza Cerebras (gratis, rápido, 70B) para uso normal
    - Escala a Gemini para intents complejos (objeciones, quejas)
    - LoRA como fallback offline (cuando no hay internet)
    - Registra métricas de cada provider
    - Soporta modo "force_premium" para casos especiales

    Proveedores en orden:
    1. Cerebras (Llama 3.3 70B, gratis, ultra-rápido) - Mayoría de casos
    2. Gemini (1.5 Pro, premium) - Objeciones, quejas, casos complejos
    3. LoRA (local, offline) - Fallback sin internet
    """

    # Intenciones que siempre usan Gemini (requieren más inteligencia)
    PREMIUM_INTENTS = {
        'handle_objection',      # "Es muy caro" → necesita persuasión
        'complex_recommendation', # Recomendaciones con restricciones múltiples
        'negotiate',             # Descuentos, regateo
        'complaint',             # Manejo de quejas
        'special_request'        # Pedidos especiales complejos
    }

    def __init__(
        self,
        providers: List[BaseLLMProvider],
        min_response_length: int = 10,
        premium_intents: set = None
    ):
        """
        Args:
            providers: Lista de providers en orden de prioridad (menor a mayor costo)
            min_response_length: Longitud mínima para considerar respuesta válida
            premium_intents: Intenciones que siempre usan el provider premium
        """
        self.providers = providers
        self.min_response_length = min_response_length
        self.premium_intents = premium_intents or self.PREMIUM_INTENTS
        self.metrics = ProviderMetrics(provider_name="cascade")

        # Log providers disponibles
        available = [p.provider_name for p in providers if p.is_available()]
        logger.info(f"[CASCADE] Providers disponibles: {available}")

    def is_available(self) -> bool:
        return any(p.is_available() for p in self.providers)

    @property
    def provider_name(self) -> str:
        return "cascade"

    def generate(
        self,
        prompt: str,
        messages: List[Dict] = None,
        temperature: float = 0.7,
        max_tokens: int = 300,
        intent: str = None,
        force_premium: bool = False
    ) -> Dict[str, Any]:
        """
        Genera respuesta usando cascada de providers.

        Args:
            prompt: Prompt del sistema
            messages: Mensajes de conversación
            temperature: Creatividad
            max_tokens: Máximo tokens
            intent: Intención detectada (para decidir si usar premium)
            force_premium: Forzar uso de OpenAI
        """
        start_time = time.time()
        fallback_chain = []
        last_error = None

        # Determinar si usar directamente el provider premium
        use_premium_first = force_premium or (intent in self.premium_intents)

        if use_premium_first:
            # Buscar provider premium (Gemini o OpenAI) y usarlo primero
            for provider in reversed(self.providers):
                if provider.provider_name in ("gemini", "openai") and provider.is_available():
                    logger.info(f"[CASCADE] Usando {provider.provider_name} directamente (intent: {intent})")
                    result = provider.generate(prompt, messages, temperature, max_tokens)
                    result['cascade_reason'] = f"premium_intent:{intent}" if intent else "force_premium"
                    result['fallback_chain'] = [provider.provider_name]
                    return result

        # Intentar providers en orden
        for provider in self.providers:
            if not provider.is_available():
                continue

            provider_name = provider.provider_name
            fallback_chain.append(provider_name)

            logger.debug(f"[CASCADE] Intentando con: {provider_name}")

            result = provider.generate(prompt, messages, temperature, max_tokens)
            response_text = result.get('response_text', '')

            # Verificar si la respuesta es válida
            if not result.get('error') and len(response_text) >= self.min_response_length:
                # Respuesta válida
                total_latency = (time.time() - start_time) * 1000

                result['fallback_chain'] = fallback_chain
                result['cascade_latency_ms'] = total_latency
                result['providers_tried'] = len(fallback_chain)

                # Si hubo fallback, registrarlo
                if len(fallback_chain) > 1:
                    result['fallback_used'] = True
                    logger.info(f"[CASCADE] Éxito con {provider_name} después de {len(fallback_chain)-1} fallback(s)")

                self.metrics.record_call(
                    success=True,
                    tokens=result.get('tokens_used', 0),
                    latency_ms=total_latency,
                    cost=result.get('cost_usd', 0)
                )

                return result

            # Registrar error para siguiente intento
            last_error = result.get('error', 'Respuesta muy corta')
            logger.warning(f"[CASCADE] {provider_name} falló: {last_error}")

        # Todos fallaron
        total_latency = (time.time() - start_time) * 1000
        self.metrics.record_call(False, 0, total_latency, 0)

        return {
            "response_text": "",
            "error": f"Todos los providers fallaron. Último error: {last_error}",
            "provider": self.provider_name,
            "fallback_chain": fallback_chain,
            "cascade_latency_ms": total_latency
        }

    def get_metrics_summary(self) -> Dict:
        """Retorna resumen de métricas de todos los providers"""
        summary = {
            "cascade": self.metrics.to_dict(),
            "providers": {}
        }

        for provider in self.providers:
            if hasattr(provider, 'metrics'):
                summary["providers"][provider.provider_name] = provider.metrics.to_dict()

        return summary


# ============================================================
# FACTORY Y SINGLETON
# ============================================================

_provider_instance: Optional[BaseLLMProvider] = None
_all_providers: Dict[str, BaseLLMProvider] = {}


def get_model_provider(
    provider_type: str = None,
    # Cerebras (NUEVO - reemplaza Groq como principal gratis)
    cerebras_api_key: str = None,
    cerebras_model: str = None,
    # Groq (legacy, aún soportado)
    groq_api_key: str = None,
    groq_model: str = None,
    # Gemini (NUEVO - reemplaza OpenAI como premium)
    google_api_key: str = None,
    gemini_model: str = None,
    # OpenAI (legacy, aún soportado)
    openai_api_key: str = None,
    openai_model: str = None,
    # LoRA local
    lora_model_path: str = None,
    lora_device: str = None,
    # Ollama (NUEVO - para modo offline)
    ollama_url: str = None,
    ollama_model: str = None
) -> BaseLLMProvider:
    """
    Obtiene el proveedor de modelo configurado (Singleton).

    Args:
        provider_type: "cerebras", "groq", "gemini", "openai", "lora", "hybrid", o "cascade"
        cerebras_api_key: API key de Cerebras (NUEVO)
        cerebras_model: Modelo de Cerebras (llama-3.3-70b por defecto)
        groq_api_key: API key de Groq
        groq_model: Modelo de Groq a usar
        google_api_key: API key de Google para Gemini (NUEVO)
        gemini_model: Modelo de Gemini (gemini-1.5-pro por defecto)
        openai_api_key: API key de OpenAI (legacy)
        openai_model: Modelo de OpenAI a usar
        lora_model_path: Ruta al modelo LoRA
        lora_device: Dispositivo para LoRA (auto, cuda, cpu)

    Returns:
        Instancia del proveedor configurado
    """
    global _provider_instance, _all_providers

    if _provider_instance is not None:
        return _provider_instance

    # Cargar configuración desde settings si no se proporcionan
    from ..core.config import settings

    provider_type = provider_type or getattr(settings, 'LLM_PROVIDER', 'cascade')

    # Cerebras (NUEVO - preferido sobre Groq)
    cerebras_api_key = cerebras_api_key or getattr(settings, 'CEREBRAS_API_KEY', None)
    cerebras_model = cerebras_model or getattr(settings, 'CEREBRAS_MODEL', 'llama-3.3-70b')

    # Groq (legacy fallback)
    groq_api_key = groq_api_key or getattr(settings, 'GROQ_API_KEY', None)
    groq_model = groq_model or getattr(settings, 'GROQ_MODEL', 'llama-3.1-8b-instant')

    # Gemini (NUEVO - preferido sobre OpenAI)
    google_api_key = google_api_key or getattr(settings, 'GOOGLE_API_KEY', None)
    gemini_model = gemini_model or getattr(settings, 'GEMINI_MODEL', 'gemini-1.5-pro')

    # OpenAI (legacy fallback)
    openai_api_key = openai_api_key or getattr(settings, 'OPENAI_API_KEY', None)
    openai_model = openai_model or getattr(settings, 'OPENAI_MODEL', 'gpt-4o')

    # LoRA local
    lora_model_path = lora_model_path or getattr(settings, 'LORA_MODEL_PATH', None)
    lora_device = lora_device or getattr(settings, 'LORA_DEVICE', 'auto')

    # Ollama (NUEVO - para modo offline)
    ollama_url = ollama_url or getattr(settings, 'OLLAMA_URL', 'http://ollama:11434')
    ollama_model = ollama_model or getattr(settings, 'OLLAMA_MODEL', 'mistral:7b-instruct')

    logger.info(f"[PROVIDER] Inicializando proveedor: {provider_type}")

    # Crear instancias de providers individuales
    cerebras_provider = CerebrasProvider(cerebras_api_key, cerebras_model) if cerebras_api_key else None
    groq_provider = GroqProvider(groq_api_key, groq_model) if groq_api_key else None
    gemini_provider = GeminiProvider(google_api_key, gemini_model) if google_api_key else None
    openai_provider = OpenAIProvider(openai_api_key, openai_model) if openai_api_key else None
    lora_provider = LoRAProvider(lora_model_path, lora_device) if lora_model_path else None
    ollama_provider = OllamaProvider(ollama_url, ollama_model)  # Siempre crear, verificar disponibilidad lazy

    # Guardar referencia a todos los providers
    if cerebras_provider:
        _all_providers['cerebras'] = cerebras_provider
    if groq_provider:
        _all_providers['groq'] = groq_provider
    if gemini_provider:
        _all_providers['gemini'] = gemini_provider
    if openai_provider:
        _all_providers['openai'] = openai_provider
    if lora_provider:
        _all_providers['lora'] = lora_provider
    _all_providers['ollama'] = ollama_provider  # Siempre disponible como fallback offline

    # Seleccionar provider según tipo
    if provider_type == "cerebras":
        if cerebras_provider and cerebras_provider.is_available():
            _provider_instance = cerebras_provider
        else:
            logger.warning("[PROVIDER] Cerebras no disponible, usando Groq")
            _provider_instance = groq_provider or GroqProvider(groq_api_key, groq_model)

    elif provider_type == "gemini":
        if gemini_provider and gemini_provider.is_available():
            _provider_instance = gemini_provider
        else:
            logger.warning("[PROVIDER] Gemini no disponible, usando OpenAI")
            _provider_instance = openai_provider or OpenAIProvider(openai_api_key, openai_model)

    elif provider_type == "openai":
        if openai_provider and openai_provider.is_available():
            _provider_instance = openai_provider
        else:
            logger.warning("[PROVIDER] OpenAI no disponible, usando Gemini")
            _provider_instance = gemini_provider or cerebras_provider or groq_provider

    elif provider_type == "groq":
        if groq_provider and groq_provider.is_available():
            _provider_instance = groq_provider
        else:
            logger.warning("[PROVIDER] Groq no disponible, usando Cerebras")
            _provider_instance = cerebras_provider or CerebrasProvider(cerebras_api_key, cerebras_model)

    elif provider_type == "lora":
        if lora_provider:
            _provider_instance = lora_provider
        else:
            logger.warning("[PROVIDER] LORA_MODEL_PATH no configurado, usando Cerebras")
            _provider_instance = cerebras_provider or groq_provider

    elif provider_type == "hybrid":
        # Híbrido: LoRA + Cerebras (antes era LoRA + Groq)
        fast_provider = cerebras_provider or groq_provider
        if lora_provider and fast_provider:
            _provider_instance = HybridProvider(lora_provider, fast_provider)
        elif fast_provider:
            logger.warning("[PROVIDER] LoRA no disponible para híbrido, usando Cerebras/Groq")
            _provider_instance = fast_provider
        else:
            _provider_instance = GroqProvider(groq_api_key, groq_model)

    elif provider_type == "cascade":
        # Construir cadena de providers en orden de prioridad
        # Cerebras → Gemini → LoRA (LoRA solo como fallback offline)
        cascade_providers = []

        # 1. Cerebras (gratis, Llama 3.3 70B, ultra-rápido) - Principal
        if cerebras_provider:
            cascade_providers.append(cerebras_provider)
        elif groq_provider:
            # Fallback a Groq si no hay Cerebras
            cascade_providers.append(groq_provider)

        # 2. Gemini (premium) - Para intents complejos y fallback de Cerebras
        if gemini_provider:
            cascade_providers.append(gemini_provider)
        elif openai_provider:
            # Fallback a OpenAI si no hay Gemini
            cascade_providers.append(openai_provider)

        # 3. Ollama (NUEVO - LLM local via servidor) - Fallback offline preferido
        if ollama_provider:
            cascade_providers.append(ollama_provider)

        # 4. LoRA (carga directa del modelo) - Último recurso si Ollama no está
        if lora_provider:
            cascade_providers.append(lora_provider)

        if cascade_providers:
            _provider_instance = CascadeProvider(cascade_providers)
            logger.info(f"[CASCADE] Orden: {[p.provider_name for p in cascade_providers]}")
        else:
            logger.error("[PROVIDER] No hay providers disponibles para cascade")
            _provider_instance = GroqProvider(groq_api_key, groq_model)

    else:  # Default: cerebras (antes era groq)
        _provider_instance = cerebras_provider or groq_provider or GroqProvider(groq_api_key, groq_model)

    return _provider_instance


def get_all_providers() -> Dict[str, BaseLLMProvider]:
    """Retorna todos los providers inicializados"""
    global _all_providers
    return _all_providers


def get_provider_metrics() -> Dict:
    """Retorna métricas de todos los providers"""
    global _provider_instance, _all_providers

    metrics = {}

    # Métricas del provider principal
    if _provider_instance:
        if hasattr(_provider_instance, 'get_metrics_summary'):
            metrics = _provider_instance.get_metrics_summary()
        elif hasattr(_provider_instance, 'metrics'):
            metrics[_provider_instance.provider_name] = _provider_instance.metrics.to_dict()

    # Métricas de providers individuales
    for name, provider in _all_providers.items():
        if hasattr(provider, 'metrics') and name not in metrics:
            metrics[name] = provider.metrics.to_dict()

    return metrics


def reset_provider():
    """Resetea el proveedor (útil para testing)"""
    global _provider_instance, _all_providers
    _provider_instance = None
    _all_providers = {}
