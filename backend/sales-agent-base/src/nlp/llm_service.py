"""
================================================================================
VOICE RESTAURANT ASSISTANT - LLM SERVICE
================================================================================
Servicio de LLM integrado con configuraciones de prompts y reglas de venta.

Soporta múltiples proveedores via model_provider:
- Cerebras (nube) - Llama 3.3 70B (gratis, ultra-rápido)
- Gemini (nube) - Gemini 1.5 Pro (premium)
- Groq (nube) - Llama 3.1 8B (gratis)
- OpenAI (nube) - GPT-4o (premium)
- LoRA (local) - Mistral 7B fine-tuned
- Cascade - LoRA → Cerebras → Gemini (inteligente)

NUEVO: Integra Knowledge Distillation para entrenar LoRA automáticamente
con las respuestas de Cerebras/Gemini, permitiendo operación offline.

Configuración via .env:
- LLM_PROVIDER=cerebras|gemini|groq|openai|lora|hybrid|cascade
- ENABLE_DISTILLATION=true (para capturar datos de entrenamiento)
================================================================================
"""

import json
import logging
import os
from typing import Dict, List, Optional, Any

from ..core.config import settings
from ..core.config_loader import get_config_loader
from .model_provider import get_model_provider, get_provider_metrics, BaseLLMProvider, CascadeProvider

logger = logging.getLogger(__name__)

# Importar DistillationCollector (lazy para evitar dependencias circulares)
_distillation_collector = None

def _get_distillation_collector():
    """Obtiene el collector de destilación (lazy loading)"""
    global _distillation_collector
    if _distillation_collector is None:
        try:
            from ..training.distillation_collector import get_distillation_collector
            _distillation_collector = get_distillation_collector()
            logger.info("[LLM_SERVICE] DistillationCollector inicializado")
        except ImportError as e:
            logger.warning(f"[LLM_SERVICE] DistillationCollector no disponible: {e}")
            _distillation_collector = False  # Marcar como no disponible
    return _distillation_collector if _distillation_collector else None


class LLMService:
    """
    Servicio de LLM que utiliza configuraciones cargadas dinámicamente.

    Integra:
    - Prompts maestros del asistente
    - Reglas de venta por categoría
    - Conocimiento del menú
    - Templates de respuesta

    Usa model_provider para abstraer el backend (Groq/LoRA/Híbrido)
    """

    # Providers que se consideran "teachers" para destilación
    TEACHER_PROVIDERS = {"cerebras", "gemini", "openai", "groq"}

    def __init__(self, provider: BaseLLMProvider = None, enable_distillation: bool = None):
        """
        Inicializar servicio LLM.

        Args:
            provider: Proveedor de modelo opcional. Si no se proporciona,
                     se usa el configurado en settings.
            enable_distillation: Habilitar captura de datos para entrenar LoRA.
                                Si es None, se lee de ENABLE_DISTILLATION env var.
        """
        self.provider = provider or get_model_provider()
        self.config_loader = get_config_loader()

        # Configuración de destilación
        if enable_distillation is None:
            enable_distillation = os.environ.get('ENABLE_DISTILLATION', 'true').lower() == 'true'
        self.enable_distillation = enable_distillation

        # Contexto actual (se actualiza externamente por el FSM)
        self._current_session_id: str = ""
        self._current_fsm_state: str = ""
        self._current_active_category: Optional[str] = None
        self._current_order_items: List[str] = []

        logger.info(f"LLMService inicializado (provider: {self.provider.provider_name}, distillation: {self.enable_distillation})")

    def get_contextual_prompt(self,
                              intent: str = None,
                              user_message: str = None,
                              conversation_history: List[Dict] = None,
                              custom_context: Dict = None) -> str:
        """
        Construir prompt contextual basado en la intención y contexto

        Args:
            intent: Intención detectada (create_order, view_menu, etc.)
            user_message: Mensaje actual del usuario
            conversation_history: Historial de la conversación
            custom_context: Contexto adicional personalizado

        Returns:
            Prompt completo con contexto
        """
        # Obtener prompt maestro
        master_prompt = self.config_loader.get_master_prompt(
            restaurant_name=self.config_loader.get_restaurant_name()
        )

        # Construir contexto adicional
        context_parts = [master_prompt]

        # Agregar información del menú actual
        menu_info = self._build_menu_context()
        if menu_info:
            context_parts.append(f"\n# MENÚ ACTUAL\n{menu_info}")

        # Agregar promociones activas
        promotions = self.config_loader.get_active_promotions()
        if promotions:
            promo_text = "\n".join([f"- {p['name']}: {p['description']}" for p in promotions])
            context_parts.append(f"\n# PROMOCIONES ACTIVAS\n{promo_text}")

        # Agregar reglas específicas según intención
        if intent:
            sales_rule = self._get_sales_rule_for_intent(intent)
            if sales_rule:
                context_parts.append(f"\n# REGLAS PARA {intent.upper()}\n{sales_rule}")

        # Agregar historial de conversación
        if conversation_history:
            history_text = self._format_conversation_history(conversation_history)
            context_parts.append(f"\n# HISTORIAL DE CONVERSACIÓN\n{history_text}")

        # Agregar contexto personalizado
        if custom_context:
            context_parts.append(f"\n# CONTEXTO ADICIONAL\n{json.dumps(custom_context, indent=2)}")

        return "\n".join(context_parts)

    def generate_response(self,
                          user_message: str,
                          intent: str = None,
                          conversation_history: List[Dict] = None,
                          context: Dict = None,
                          temperature: float = 0.7,
                          max_tokens: int = 300,
                          force_premium: bool = False) -> Dict[str, Any]:
        """
        Generar respuesta del asistente usando el provider configurado.

        Args:
            user_message: Mensaje del usuario
            intent: Intención detectada (usado por CascadeProvider para decidir provider)
            conversation_history: Historial de conversación
            context: Contexto adicional
            temperature: Creatividad del modelo (0.0-1.0)
            max_tokens: Máximo de tokens en la respuesta
            force_premium: Forzar uso de OpenAI (para casos especiales)

        Returns:
            Dict con response_text y metadata
        """
        try:
            # Construir prompt contextual
            system_prompt = self.get_contextual_prompt(
                intent=intent,
                user_message=user_message,
                conversation_history=conversation_history,
                custom_context=context
            )

            # Preparar mensajes para el provider
            messages = []

            # Agregar historial reciente (últimas 5 interacciones)
            if conversation_history:
                for msg in conversation_history[-5:]:
                    role = "user" if msg.get('role') == 'user' else "assistant"
                    messages.append({
                        "role": role,
                        "content": msg.get('content', '')
                    })

            # Agregar mensaje actual
            messages.append({
                "role": "user",
                "content": user_message
            })

            logger.debug(f"Generating response for intent: {intent} via {self.provider.provider_name}")

            # Llamar al provider con intent (CascadeProvider lo usa para decidir)
            if isinstance(self.provider, CascadeProvider):
                result = self.provider.generate(
                    prompt=system_prompt,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    intent=intent,
                    force_premium=force_premium
                )
            else:
                result = self.provider.generate(
                    prompt=system_prompt,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens
                )

            response_text = result.get('response_text', '')
            provider_used = result.get('provider', 'unknown')
            model_used = result.get('model', 'unknown')

            if result.get('error'):
                logger.warning(f"Provider error: {result.get('error')}")

            # Log detallado para cascade
            if result.get('fallback_chain'):
                logger.info(f"Response via cascade: {result.get('fallback_chain')} | intent: {intent}")
            else:
                logger.info(f"Response generated via {provider_used}: {len(response_text)} chars")

            # ============================================================
            # KNOWLEDGE DISTILLATION: Capturar respuestas de teachers
            # ============================================================
            if (self.enable_distillation and
                response_text and
                not result.get('error') and
                provider_used.lower() in self.TEACHER_PROVIDERS):

                self._capture_for_distillation(
                    user_message=user_message,
                    intent=intent,
                    intent_confidence=context.get('intent_confidence', 0.8) if context else 0.8,
                    response_text=response_text,
                    provider=provider_used,
                    model=model_used,
                    conversation_history=conversation_history,
                    tokens_used=result.get('tokens_used', 0),
                    latency_ms=result.get('latency_ms', 0)
                )

            return {
                "response_text": response_text,
                "model": model_used,
                "provider": provider_used,
                "tokens_used": result.get('tokens_used', 0),
                "fallback_used": result.get('fallback_used', False),
                "fallback_chain": result.get('fallback_chain'),
                "cost_usd": result.get('cost_usd', 0),
                "cascade_reason": result.get('cascade_reason')
            }

        except Exception as e:
            logger.error(f"Error generating LLM response: {e}")
            return {
                "response_text": "Disculpa, tuve un problema al procesar tu solicitud. ¿Podrías intentar de nuevo?",
                "error": str(e)
            }

    def get_metrics(self) -> Dict:
        """Obtener métricas de uso de providers"""
        return get_provider_metrics()

    def generate_recommendation(self,
                                user_preferences: Dict = None,
                                conversation_context: List[Dict] = None) -> Dict[str, Any]:
        """
        Generar recomendación personalizada basada en preferencias

        Args:
            user_preferences: Preferencias del usuario (dietarias, presupuesto, etc.)
            conversation_context: Contexto de la conversación

        Returns:
            Dict con recomendación y productos sugeridos
        """
        try:
            # Obtener productos disponibles
            all_products = self.config_loader.get_all_products()

            # Filtrar productos según preferencias
            filtered_products = self._filter_products_by_preferences(
                all_products,
                user_preferences or {}
            )

            # Si no hay productos filtrados, usar populares
            if not filtered_products:
                filtered_products = self.config_loader.get_popular_products()[:3]

            # Construir prompt de recomendación
            recommendation_prompt = self.config_loader.get_prompt_template('recommendation_prompt')

            products_context = {
                "available_products": [
                    {
                        "name": p['name'],
                        "description": p.get('description', ''),
                        "price": p.get('price'),
                        "category": p.get('category_name')
                    }
                    for p in filtered_products[:3]
                ],
                "user_preferences": user_preferences or {}
            }

            # Generar recomendación usando LLM
            result = self.generate_response(
                user_message=f"Recomiéndame algo según estas preferencias: {json.dumps(user_preferences)}",
                intent="get_recommendation",
                context=products_context,
                conversation_history=conversation_context
            )

            return {
                **result,
                "recommended_products": filtered_products[:3],
                "total_available": len(filtered_products)
            }

        except Exception as e:
            logger.error(f"Error generating recommendation: {e}")
            return {
                "response_text": "Déjame mostrarte nuestras opciones más populares.",
                "recommended_products": self.config_loader.get_popular_products()[:3],
                "error": str(e)
            }

    def generate_upsell_suggestion(self,
                                   current_order: List[Dict],
                                   conversation_context: List[Dict] = None) -> Dict[str, Any]:
        """
        Generar sugerencia de upselling basada en orden actual

        Args:
            current_order: Items de la orden actual
            conversation_context: Contexto de la conversación

        Returns:
            Dict con sugerencia de upselling
        """
        try:
            # Obtener reglas de upselling
            sales_rules = self.config_loader.load_sales_rules()
            upselling_prompt = self.config_loader.get_prompt_template('upselling_prompt')

            # Analizar orden actual para determinar estrategia
            order_context = {
                "current_items": current_order,
                "has_drink": any('bebida' in item.get('category_name', '').lower() for item in current_order),
                "has_side": any('complemento' in item.get('category_name', '').lower() for item in current_order),
                "total_items": len(current_order)
            }

            # Generar sugerencia usando LLM
            result = self.generate_response(
                user_message="Genera una sugerencia de upselling para esta orden",
                intent="upselling",
                context=order_context,
                conversation_history=conversation_context,
                temperature=0.6,
                max_tokens=150
            )

            return result

        except Exception as e:
            logger.error(f"Error generating upsell: {e}")
            return {
                "response_text": "¿Te gustaría agregar algo más a tu pedido?",
                "error": str(e)
            }

    # ========================================
    # MÉTODOS DE CONTEXTO Y DESTILACIÓN
    # ========================================

    def set_context(self,
                    session_id: str = None,
                    fsm_state: str = None,
                    active_category: str = None,
                    order_items: List[str] = None):
        """
        Actualiza el contexto actual para la destilación.

        Debe llamarse desde el FSM antes de generar respuestas.

        Args:
            session_id: ID de la sesión actual
            fsm_state: Estado actual del FSM (exploracion, upsell, etc.)
            active_category: Categoría activa del menú
            order_items: Lista de items en el pedido actual
        """
        if session_id is not None:
            self._current_session_id = session_id
        if fsm_state is not None:
            self._current_fsm_state = fsm_state
        if active_category is not None:
            self._current_active_category = active_category
        if order_items is not None:
            self._current_order_items = order_items

    def _capture_for_distillation(self,
                                   user_message: str,
                                   intent: str,
                                   intent_confidence: float,
                                   response_text: str,
                                   provider: str,
                                   model: str,
                                   conversation_history: List[Dict] = None,
                                   tokens_used: int = 0,
                                   latency_ms: float = 0):
        """
        Captura una respuesta del teacher para entrenar LoRA.

        Se ejecuta automáticamente cuando:
        - La destilación está habilitada
        - El provider es un teacher (Cerebras/Gemini/OpenAI/Groq)
        - La respuesta es válida (sin error)
        """
        collector = _get_distillation_collector()
        if not collector:
            return

        try:
            collector.capture(
                session_id=self._current_session_id or "unknown",
                user_input=user_message,
                detected_intent=intent or "unknown",
                intent_confidence=intent_confidence,
                teacher_response=response_text,
                teacher_provider=provider,
                teacher_model=model,
                conversation_history=conversation_history or [],
                fsm_state=self._current_fsm_state,
                active_category=self._current_active_category,
                order_items=self._current_order_items,
                response_tokens=tokens_used,
                latency_ms=latency_ms
            )
        except Exception as e:
            # No fallar si la captura falla - es secundario
            logger.warning(f"[DISTILLATION] Error capturando: {e}")

    def record_user_feedback(self, accepted: bool, led_to_sale: bool = None):
        """
        Registra feedback del usuario sobre la última respuesta.

        Útil para mejorar la calidad de los datos de entrenamiento.

        Args:
            accepted: Si el usuario aceptó la sugerencia
            led_to_sale: Si la interacción resultó en venta
        """
        collector = _get_distillation_collector()
        if not collector:
            return

        # El collector mantiene internamente el último entry_id
        # por session, se puede mejorar esto en el futuro
        logger.debug(f"[DISTILLATION] Feedback: accepted={accepted}, sale={led_to_sale}")

    def get_distillation_stats(self) -> Dict:
        """Obtiene estadísticas de datos capturados para destilación"""
        collector = _get_distillation_collector()
        if not collector:
            return {"error": "Distillation not available"}

        return collector.get_stats()

    # ========================================
    # MÉTODOS AUXILIARES
    # ========================================

    def _build_menu_context(self) -> str:
        """Construir contexto del menu con ingenieria del menu"""
        categories = self.config_loader.get_menu_categories()
        recommendations = self.config_loader.get_recommendations()
        context_lines = []
        estrellas = recommendations.get('estrellas', [])
        if estrellas:
            nombres = [p['name'] for p in estrellas[:5]]
            context_lines.append(f"**PLATILLOS ESTRELLA**: {', '.join(nombres)}")
        unavailable = self.config_loader.get_unavailable_products()
        if unavailable:
            context_lines.append(f"**NO DISPONIBLES**: {', '.join([p['name'] for p in unavailable])}")
        context_lines.append("**MENU:**")
        for category in categories[:3]:
            cat_name = category.get('name')
            products = category.get('products', [])
            info = [f"{p['name']} ${p.get('price', 0)}" for p in products[:3]]
            context_lines.append(f"  {cat_name}: {', '.join(info)}")
        return "\n".join(context_lines)

    def _get_sales_rule_for_intent(self, intent: str) -> Optional[str]:
        """Obtener reglas de venta específicas para una intención"""
        # Mapear intenciones a categorías de reglas
        intent_to_category = {
            "create_order": "general",
            "view_menu": "general",
            "view_category": "general",
            "get_recommendation": "recommendation"
        }

        category = intent_to_category.get(intent)
        if not category:
            return None

        sales_rules = self.config_loader.load_sales_rules()
        rules_by_category = sales_rules.get('sales_rules_by_category', {})

        # Obtener regla específica
        rule = rules_by_category.get(category, {})
        return json.dumps(rule, indent=2) if rule else None

    def _format_conversation_history(self, history: List[Dict]) -> str:
        """Formatear historial de conversación para el prompt"""
        formatted = []
        for msg in history[-5:]:  # Últimas 5 interacciones
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')
            formatted.append(f"[{role.upper()}]: {content}")

        return "\n".join(formatted)

    def _filter_products_by_preferences(self,
                                       products: List[Dict],
                                       preferences: Dict) -> List[Dict]:
        """
        Filtrar productos según preferencias del usuario

        Args:
            products: Lista de productos
            preferences: Preferencias (dietary_preference, budget, meal_type)

        Returns:
            Lista filtrada de productos
        """
        filtered = products.copy()

        # Filtro dietario
        dietary_pref = preferences.get('dietary_preference', '').lower()
        if dietary_pref:
            if 'sin picante' in dietary_pref or 'no picante' in dietary_pref:
                filtered = [p for p in filtered if p.get('spice_level_num', 0) == 0]
            elif 'vegetariano' in dietary_pref:
                filtered = [p for p in filtered if 'vegetariano' in p.get('tags', [])]
            elif 'saludable' in dietary_pref:
                filtered = [p for p in filtered if 'saludable' in p.get('tags', [])]

        # Filtro de presupuesto
        budget = preferences.get('budget', '').lower()
        if budget:
            if 'económico' in budget or 'barato' in budget:
                filtered = [p for p in filtered if float(p.get('price', 999)) <= 100]
            elif 'premium' in budget or 'caro' in budget:
                filtered = [p for p in filtered if float(p.get('price', 0)) >= 100]

        # Filtro de tipo de comida
        meal_type = preferences.get('meal_type', '').lower()
        if meal_type:
            if 'entrada' in meal_type:
                filtered = [p for p in filtered if 'entrada' in p.get('tags', [])]
            elif 'postre' in meal_type:
                filtered = [p for p in filtered if 'postre' in p.get('tags', [])]
            elif 'bebida' in meal_type:
                filtered = [p for p in filtered if 'bebida' in p.get('tags', [])]

        return filtered


# Instancia global
_llm_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    """Obtener instancia global del LLMService (Singleton)"""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service
