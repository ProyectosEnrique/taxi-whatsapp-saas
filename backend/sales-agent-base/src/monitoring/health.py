# ============================================================
# HEALTH CHECKER - Verificación de Salud del Sistema
# ============================================================
# Verifica estado de todos los componentes
# Expone endpoint /health con detalles
# ============================================================

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
import httpx

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Estados de salud posibles"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class ComponentHealth:
    """Estado de salud de un componente"""
    name: str
    status: HealthStatus
    latency_ms: float = 0.0
    message: str = ""
    last_check: datetime = field(default_factory=datetime.utcnow)
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SystemHealth:
    """Estado de salud del sistema completo"""
    status: HealthStatus
    components: List[ComponentHealth]
    uptime_seconds: float
    version: str = "2.0.0"
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict:
        """Convierte a diccionario para JSON"""
        return {
            "status": self.status.value,
            "version": self.version,
            "uptime_seconds": self.uptime_seconds,
            "timestamp": self.timestamp.isoformat(),
            "components": {
                c.name: {
                    "status": c.status.value,
                    "latency_ms": c.latency_ms,
                    "message": c.message,
                    "details": c.details
                }
                for c in self.components
            }
        }


class HealthChecker:
    """
    Verificador de salud del sistema.

    Verifica:
    - Servicios internos (Menu, Orders, etc.)
    - APIs externas (LLM providers, TTS, STT)
    - Bases de datos
    - Event Bus
    """

    def __init__(self):
        self._start_time = time.time()
        self._last_check: Optional[SystemHealth] = None
        self._check_interval = 30  # segundos
        self._service_urls = {
            "menu-service": "http://menu-service:5011/health",
            "orders-service": "http://orders-service:5012/health",
            "tables-service": "http://tables-service:5013/health",
            "auth-service": "http://auth-service:5014/health",
        }

    async def check_component(self, name: str, url: str, timeout: float = 5.0) -> ComponentHealth:
        """Verifica salud de un componente HTTP"""
        start = time.time()
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(url)
                latency = (time.time() - start) * 1000

                if response.status_code == 200:
                    return ComponentHealth(
                        name=name,
                        status=HealthStatus.HEALTHY,
                        latency_ms=latency,
                        message="OK"
                    )
                else:
                    return ComponentHealth(
                        name=name,
                        status=HealthStatus.DEGRADED,
                        latency_ms=latency,
                        message=f"HTTP {response.status_code}"
                    )

        except httpx.TimeoutException:
            return ComponentHealth(
                name=name,
                status=HealthStatus.UNHEALTHY,
                latency_ms=(time.time() - start) * 1000,
                message="Timeout"
            )
        except Exception as e:
            return ComponentHealth(
                name=name,
                status=HealthStatus.UNHEALTHY,
                latency_ms=(time.time() - start) * 1000,
                message=str(e)
            )

    async def check_redis(self) -> ComponentHealth:
        """Verifica conexión a Redis"""
        try:
            import redis.asyncio as aioredis
            import os

            url = os.environ.get("REDIS_URL", "redis://redis:6379")
            start = time.time()

            client = await aioredis.from_url(url, encoding="utf-8")
            await client.ping()
            await client.close()

            return ComponentHealth(
                name="redis",
                status=HealthStatus.HEALTHY,
                latency_ms=(time.time() - start) * 1000,
                message="Connected"
            )
        except ImportError:
            return ComponentHealth(
                name="redis",
                status=HealthStatus.UNKNOWN,
                message="Redis client not installed"
            )
        except Exception as e:
            return ComponentHealth(
                name="redis",
                status=HealthStatus.UNHEALTHY,
                message=str(e)
            )

    async def check_nlu(self) -> ComponentHealth:
        """Verifica disponibilidad de NLU"""
        try:
            from ..nlp.intent_classifier import get_intent_classifier

            start = time.time()
            classifier = get_intent_classifier()

            if classifier.is_ready:
                # Hacer una predicción de prueba
                result = classifier.predict("hola")
                latency = (time.time() - start) * 1000

                return ComponentHealth(
                    name="nlu",
                    status=HealthStatus.HEALTHY,
                    latency_ms=latency,
                    message="Model loaded",
                    details={"model": "all-MiniLM-L6-v2"}
                )
            else:
                return ComponentHealth(
                    name="nlu",
                    status=HealthStatus.DEGRADED,
                    message="Model not ready"
                )

        except ImportError:
            return ComponentHealth(
                name="nlu",
                status=HealthStatus.UNKNOWN,
                message="NLU module not available"
            )
        except Exception as e:
            return ComponentHealth(
                name="nlu",
                status=HealthStatus.UNHEALTHY,
                message=str(e)
            )

    async def check_llm_providers(self) -> ComponentHealth:
        """Verifica disponibilidad de LLM providers"""
        import os

        providers_available = []
        providers_missing = []

        # Verificar API keys
        if os.environ.get("GROQ_API_KEY"):
            providers_available.append("groq")
        else:
            providers_missing.append("groq")

        if os.environ.get("OPENAI_API_KEY"):
            providers_available.append("openai")
        else:
            providers_missing.append("openai")

        if len(providers_available) >= 2:
            status = HealthStatus.HEALTHY
            message = f"Providers: {', '.join(providers_available)}"
        elif len(providers_available) == 1:
            status = HealthStatus.DEGRADED
            message = f"Only {providers_available[0]} available"
        else:
            status = HealthStatus.UNHEALTHY
            message = "No LLM providers configured"

        return ComponentHealth(
            name="llm-providers",
            status=status,
            message=message,
            details={
                "available": providers_available,
                "missing": providers_missing
            }
        )

    async def check_tts(self) -> ComponentHealth:
        """Verifica disponibilidad de TTS"""
        import os

        if os.environ.get("ELEVENLABS_API_KEY"):
            return ComponentHealth(
                name="tts",
                status=HealthStatus.HEALTHY,
                message="ElevenLabs configured"
            )
        else:
            return ComponentHealth(
                name="tts",
                status=HealthStatus.DEGRADED,
                message="Using fallback gTTS"
            )

    async def check_stt(self) -> ComponentHealth:
        """Verifica disponibilidad de STT"""
        import os

        if os.environ.get("DEEPGRAM_API_KEY"):
            return ComponentHealth(
                name="stt",
                status=HealthStatus.HEALTHY,
                message="Deepgram configured"
            )
        else:
            return ComponentHealth(
                name="stt",
                status=HealthStatus.UNHEALTHY,
                message="No STT provider configured"
            )

    async def check_all(self) -> SystemHealth:
        """Verifica todos los componentes"""
        components: List[ComponentHealth] = []

        # Verificar servicios internos
        service_checks = [
            self.check_component(name, url)
            for name, url in self._service_urls.items()
        ]

        # Verificar otros componentes
        other_checks = [
            self.check_redis(),
            self.check_nlu(),
            self.check_llm_providers(),
            self.check_tts(),
            self.check_stt(),
        ]

        # Ejecutar todos en paralelo
        all_results = await asyncio.gather(*service_checks, *other_checks, return_exceptions=True)

        for result in all_results:
            if isinstance(result, ComponentHealth):
                components.append(result)
            elif isinstance(result, Exception):
                components.append(ComponentHealth(
                    name="unknown",
                    status=HealthStatus.UNHEALTHY,
                    message=str(result)
                ))

        # Determinar estado general
        unhealthy_count = sum(1 for c in components if c.status == HealthStatus.UNHEALTHY)
        degraded_count = sum(1 for c in components if c.status == HealthStatus.DEGRADED)

        if unhealthy_count > 2:
            overall_status = HealthStatus.UNHEALTHY
        elif unhealthy_count > 0 or degraded_count > 2:
            overall_status = HealthStatus.DEGRADED
        else:
            overall_status = HealthStatus.HEALTHY

        uptime = time.time() - self._start_time

        self._last_check = SystemHealth(
            status=overall_status,
            components=components,
            uptime_seconds=uptime
        )

        return self._last_check

    async def get_quick_health(self) -> Dict:
        """Retorna estado rápido sin verificar todos los componentes"""
        uptime = time.time() - self._start_time
        return {
            "status": "healthy",
            "uptime_seconds": uptime,
            "version": "2.0.0"
        }

    def get_last_check(self) -> Optional[SystemHealth]:
        """Retorna último resultado de verificación"""
        return self._last_check


# Singleton
_health_checker: Optional[HealthChecker] = None


def get_health_checker() -> HealthChecker:
    """Obtiene instancia singleton del health checker"""
    global _health_checker
    if _health_checker is None:
        _health_checker = HealthChecker()
    return _health_checker
