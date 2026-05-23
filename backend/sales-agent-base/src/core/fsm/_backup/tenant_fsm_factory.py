#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tenant FSM Factory - Crea FSM personalizado por tipo de negocio

Factory que genera instancias de SalesAgentFSM personalizadas según:
- Tipo de negocio (wine_store, pharmacy, restaurant, etc.)
- Configuración del tenant
- Decision tree especializado
"""

import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
import json

from .state_machine import SalesAgentFSM
from .decision_tree import IntentDecisionTree, Intent
from ..tenant_manager import TenantConfig

logger = logging.getLogger(__name__)


class TenantFSMFactory:
    """
    Factory para crear FSM personalizado por tenant

    Responsabilidades:
    1. Cargar decision trees especializados por tipo de negocio
    2. Configurar FSM con parámetros del tenant
    3. Aplicar branding y personalización
    """

    # Cache de decision trees por tipo
    _decision_tree_cache: Dict[str, IntentDecisionTree] = {}

    @classmethod
    def create_fsm(cls, tenant_config: TenantConfig) -> SalesAgentFSM:
        """
        Crea FSM personalizado para el tenant

        Args:
            tenant_config: Configuración del tenant

        Returns:
            SalesAgentFSM configurado
        """
        business_type = tenant_config.type

        logger.info(f"🏭 Creando FSM para tenant {tenant_config.tenant_id} (tipo: {business_type})")

        # 1. Cargar decision tree según tipo de negocio
        decision_tree = cls._get_decision_tree(business_type, tenant_config.tenant_id)

        # 2. Extraer configuración FSM
        fsm_config = tenant_config.fsm_config or {}

        # 3. Crear instancia de FSM
        fsm = SalesAgentFSM(
            decision_tree=decision_tree,
            tenant_id=tenant_config.tenant_id,
            config=fsm_config
        )

        # 4. Configurar branding (mensaje de saludo, etc.)
        if tenant_config.branding:
            cls._apply_branding(fsm, tenant_config.branding)

        logger.info(f"✅ FSM creado para {tenant_config.name}")

        return fsm

    @classmethod
    def _get_decision_tree(cls, business_type: str, tenant_id: str) -> IntentDecisionTree:
        """
        Obtiene o crea decision tree para tipo de negocio

        Args:
            business_type: Tipo de negocio
            tenant_id: ID del tenant (para logging)

        Returns:
            IntentDecisionTree
        """
        # Revisar cache
        cache_key = business_type
        if cache_key in cls._decision_tree_cache:
            logger.debug(f"📦 Decision tree de {business_type} desde cache")
            return cls._decision_tree_cache[cache_key]

        # Cargar según tipo
        if business_type == 'wine_store':
            tree = cls._create_wine_decision_tree()
        elif business_type == 'pharmacy':
            tree = cls._create_pharmacy_decision_tree()
        elif business_type == 'restaurant':
            tree = cls._create_restaurant_decision_tree()
        elif business_type == 'generic':
            tree = cls._create_generic_decision_tree()
        else:
            logger.warning(f"⚠️ Tipo de negocio '{business_type}' desconocido, usando genérico")
            tree = cls._create_generic_decision_tree()

        # Guardar en cache
        cls._decision_tree_cache[cache_key] = tree

        logger.info(f"✅ Decision tree de {business_type} cargado")

        return tree

    @staticmethod
    def _apply_branding(fsm: SalesAgentFSM, branding: Dict[str, Any]):
        """
        Aplica branding personalizado al FSM

        Args:
            fsm: Instancia del FSM
            branding: Configuración de branding
        """
        # Mensaje de saludo personalizado
        if 'greeting_message' in branding:
            fsm.greeting_message = branding['greeting_message']

        # Tono de conversación
        if 'tone' in branding:
            fsm.tone = branding['tone']

        # Idioma
        if 'language' in branding:
            fsm.language = branding['language']

    # ========================================================================
    # DECISION TREES POR TIPO DE NEGOCIO
    # ========================================================================

    @staticmethod
    def _create_wine_decision_tree() -> IntentDecisionTree:
        """
        Decision tree para vinetería

        Intenciones especializadas:
        - Pedir vino por tipo (tinto, blanco, rosado)
        - Recomendar vino (para carne, pescado, etc.)
        - Preguntar por origen (francés, italiano, español)
        - Verificación de edad (mayor de 18)
        """
        patterns = {
            # Saludos
            Intent.GREETING: [
                r"^hola\b",
                r"^buenos días\b",
                r"^buenas tardes\b",
                r"^buenas noches\b",
                r"^hey\b",
                r"^qué tal\b"
            ],

            # Agregar al pedido - Especializado para vinos
            Intent.ADD_TO_ORDER: [
                r"quiero\s+(?:(\d+)\s+)?(?:botella(?:s)?|vino(?:s)?)\s+(?:de\s+)?(\w+)",
                r"me das\s+(?:(\d+)\s+)?(?:botella(?:s)?|vino(?:s)?)\s+(?:de\s+)?(\w+)",
                r"ponme\s+(?:(\d+)\s+)?(?:botella(?:s)?|vino(?:s)?)\s+(?:de\s+)?(\w+)",
                r"dame\s+(?:(\d+)\s+)?(?:botella(?:s)?|vino(?:s)?)\s+(?:de\s+)?(\w+)",
                r"quiero\s+(?:un\s+)?(?:tinto|blanco|rosado|espumoso)",
                r"me\s+(?:das|traes|vendes)\s+(?:un\s+)?(\w+)"
            ],

            # Recomendación - Especializado para vinos
            Intent.GET_RECOMMENDATION: [
                r"(?:qué|que)\s+vino\s+(?:me\s+)?recomiendas?",
                r"recomiéndame\s+(?:un\s+)?vino",
                r"(?:qué|que)\s+(?:vino\s+)?va\s+(?:bien\s+)?(?:con\s+)?(\w+)",
                r"para\s+(?:carne|pescado|pollo|queso)",
                r"(?:qué|que)\s+(?:tinto|blanco|rosado)\s+(?:me\s+)?recomiendas?"
            ],

            # Ver menú
            Intent.VIEW_MENU: [
                r"(?:qué|que)\s+vinos?\s+(?:tienen|tienes|hay)",
                r"muestra(?:me)?\s+(?:el\s+)?(?:menú|carta|vinos?|catálogo)",
                r"(?:qué|que)\s+(?:tienen|tienes|hay)\s+(?:de\s+)?vinos?",
                r"opciones\s+de\s+vinos?",
                r"ver\s+(?:la\s+)?carta"
            ],

            # Preguntar precio
            Intent.ASK_PRICE: [
                r"(?:cuánto|cuanto)\s+(?:cuesta|vale|sale|es)\s+(?:el\s+|la\s+)?(\w+)",
                r"precio\s+(?:del?\s+)?(\w+)",
                r"(\w+)\s+(?:cuánto|cuanto)\s+(?:cuesta|vale)"
            ],

            # Confirmar pedido
            Intent.CONFIRM_ORDER: [
                r"(?:sí|si)\s*,?\s*(?:está|esta)\s+(?:bien|ok|correcto)",
                r"confirma(?:r)?",
                r"(?:así|asi)\s+(?:está|esta)\s+bien",
                r"ok\s*,?\s*(?:confirmo)?",
                r"perfecto",
                r"procede(?:r)?",
                r"adelante"
            ],

            # Modificar pedido
            Intent.MODIFY_ORDER: [
                r"cambiar?\s+(?:el\s+)?pedido",
                r"modificar?\s+(?:el\s+)?pedido",
                r"quita(?:r)?\s+(?:el\s+)?(\w+)",
                r"elimina(?:r)?\s+(?:el\s+)?(\w+)",
                r"mejor\s+(?:dame|quiero)\s+(\w+)",
                r"no\s*,?\s*(?:mejor|dame)\s+(\w+)"
            ],

            # Cancelar
            Intent.GOODBYE: [
                r"cancela(?:r)?\s+(?:el\s+)?pedido",
                r"no\s+(?:quiero|necesito)\s+nada",
                r"mejor\s+(?:no|nada)",
                r"dejalo",
                r"olvídalo"
            ],

            # Ayuda
            Intent.HELP: [
                r"ayuda",
                r"(?:qué|que)\s+(?:puedo|puedes)\s+(?:hacer|pedir)",
                r"(?:cómo|como)\s+(?:funciona|hago)",
                r"no\s+(?:entiendo|sé|se)"
            ],

            # Despedida
            Intent.GOODBYE: [
                r"(?:adiós|adios|chao|bye|hasta luego|nos vemos)",
                r"gracias?\s*,?\s*(?:adiós|adios|chao|bye)?",
                r"eso\s+es\s+todo"
            ]
        }

        return IntentDecisionTree(patterns)

    @staticmethod
    def _create_pharmacy_decision_tree() -> IntentDecisionTree:
        """
        Decision tree para farmacia

        Intenciones especializadas:
        - Buscar medicamento
        - Preguntar si requiere receta
        - Consultar síntomas
        - Verificar stock
        """
        patterns = {
            # Saludos
            Intent.GREETING: [
                r"^hola\b",
                r"^buenos días\b",
                r"^buenas tardes\b",
                r"^buenas noches\b"
            ],

            # Buscar producto/medicamento
            Intent.ADD_TO_ORDER: [
                r"(?:necesito|quiero|busco)\s+(\w+)",
                r"(?:tienen|tienes|hay)\s+(\w+)",
                r"me\s+(?:das|vendes|traes)\s+(\w+)",
                r"(?:cuánto|cuanto)\s+(?:cuesta|vale)\s+(?:el\s+)?(\w+)"
            ],

            # Recomendación por síntoma
            Intent.GET_RECOMMENDATION: [
                r"(?:qué|que)\s+(?:me\s+)?(?:puedo\s+)?tomar\s+para\s+(?:el\s+|la\s+)?(\w+)",
                r"(?:tengo|me duele|siento)\s+(\w+)",
                r"recomiéndame\s+(?:algo\s+)?para\s+(?:el\s+|la\s+)?(\w+)",
                r"(?:qué|que)\s+(?:es\s+)?(?:bueno|sirve)\s+para\s+(\w+)"
            ],

            # Ver catálogo
            Intent.VIEW_MENU: [
                r"(?:qué|que)\s+(?:medicamentos?|productos?)\s+(?:tienen|hay)",
                r"muestra(?:me)?\s+(?:el\s+)?(?:catálogo|inventario)",
                r"(?:qué|que)\s+(?:tienen|hay)"
            ],

            # Preguntar precio
            Intent.ASK_PRICE: [
                r"(?:cuánto|cuanto)\s+(?:cuesta|vale|sale)\s+(?:el\s+)?(\w+)",
                r"precio\s+(?:del?\s+)?(\w+)"
            ],

            # Confirmar
            Intent.CONFIRM_ORDER: [
                r"(?:sí|si)",
                r"confirma(?:r)?",
                r"ok",
                r"perfecto",
                r"adelante"
            ],

            # Modificar
            Intent.MODIFY_ORDER: [
                r"cambiar?",
                r"modificar?",
                r"quita(?:r)?\s+(\w+)",
                r"mejor\s+(\w+)"
            ],

            # Cancelar
            Intent.GOODBYE: [
                r"cancela(?:r)?",
                r"no\s+(?:quiero|necesito)",
                r"dejalo"
            ],

            # Ayuda
            Intent.HELP: [
                r"ayuda",
                r"(?:qué|que)\s+puedo\s+(?:hacer|pedir)",
                r"(?:cómo|como)\s+funciona"
            ],

            # Despedida
            Intent.GOODBYE: [
                r"(?:adiós|adios|chao|bye|gracias)"
            ]
        }

        return IntentDecisionTree(patterns)

    @staticmethod
    def _create_restaurant_decision_tree() -> IntentDecisionTree:
        """
        Decision tree para restaurante

        Intenciones especializadas:
        - Pedir comida
        - Preguntar ingredientes
        - Modificar platillo (sin cebolla, etc.)
        - Preguntar tiempo de entrega
        """
        patterns = {
            # Saludos
            Intent.GREETING: [
                r"^hola\b",
                r"^buenos días\b",
                r"^buenas tardes\b",
                r"^buenas noches\b",
                r"^hey\b"
            ],

            # Agregar al pedido - Especializado para comida
            Intent.ADD_TO_ORDER: [
                r"quiero\s+(?:(\d+)\s+)?(\w+)",
                r"me das\s+(?:(\d+)\s+)?(\w+)",
                r"ponme\s+(?:(\d+)\s+)?(\w+)",
                r"dame\s+(?:(\d+)\s+)?(\w+)",
                r"pido\s+(?:(\d+)\s+)?(\w+)",
                r"(?:una|un)\s+(\w+)",
                r"(\d+)\s+(?:de\s+)?(\w+)"
            ],

            # Recomendación
            Intent.GET_RECOMMENDATION: [
                r"(?:qué|que)\s+(?:me\s+)?recomiendas?",
                r"recomiéndame\s+algo",
                r"(?:qué|que)\s+(?:tienen|hay)\s+(?:de\s+)?(?:especial|bueno)",
                r"(?:qué|que)\s+(?:está|esta)\s+(?:bueno|rico)"
            ],

            # Ver menú
            Intent.VIEW_MENU: [
                r"(?:qué|que)\s+(?:tienen|tienes|hay)",
                r"muestra(?:me)?\s+(?:el\s+)?menú",
                r"opciones",
                r"ver\s+(?:el\s+)?menú"
            ],

            # Preguntar precio
            Intent.ASK_PRICE: [
                r"(?:cuánto|cuanto)\s+(?:cuesta|vale|sale)\s+(?:el\s+|la\s+)?(\w+)",
                r"precio\s+(?:del?\s+|de\s+la\s+)?(\w+)"
            ],

            # Confirmar pedido
            Intent.CONFIRM_ORDER: [
                r"(?:sí|si)",
                r"confirma(?:r)?",
                r"(?:está|esta)\s+bien",
                r"ok",
                r"perfecto",
                r"adelante"
            ],

            # Modificar pedido
            Intent.MODIFY_ORDER: [
                r"cambiar?",
                r"modificar?",
                r"quita(?:r)?\s+(\w+)",
                r"sin\s+(\w+)",
                r"agrega(?:r)?\s+(\w+)",
                r"con\s+(\w+)",
                r"mejor\s+(\w+)"
            ],

            # Cancelar
            Intent.GOODBYE: [
                r"cancela(?:r)?",
                r"no\s+(?:quiero|necesito)",
                r"dejalo"
            ],

            # Ayuda
            Intent.HELP: [
                r"ayuda",
                r"(?:qué|que)\s+puedo\s+(?:hacer|pedir)",
                r"(?:cómo|como)\s+funciona"
            ],

            # Despedida
            Intent.GOODBYE: [
                r"(?:adiós|adios|chao|bye|gracias)"
            ]
        }

        return IntentDecisionTree(patterns)

    @staticmethod
    def _create_generic_decision_tree() -> IntentDecisionTree:
        """
        Decision tree genérico

        Para negocios que no tienen especialización
        """
        patterns = {
            # Saludos
            Intent.GREETING: [
                r"^hola\b",
                r"^buenos días\b",
                r"^buenas tardes\b",
                r"^buenas noches\b",
                r"^hey\b",
                r"^qué tal\b"
            ],

            # Agregar al pedido
            Intent.ADD_TO_ORDER: [
                r"quiero\s+(\w+)",
                r"me das\s+(\w+)",
                r"ponme\s+(\w+)",
                r"dame\s+(\w+)",
                r"pido\s+(\w+)"
            ],

            # Recomendación
            Intent.GET_RECOMMENDATION: [
                r"(?:qué|que)\s+(?:me\s+)?recomiendas?",
                r"recomiéndame",
                r"(?:qué|que)\s+(?:tienen|hay)\s+(?:de\s+)?(?:especial|bueno)"
            ],

            # Ver menú
            Intent.VIEW_MENU: [
                r"(?:qué|que)\s+(?:tienen|tienes|hay)",
                r"muestra(?:me)?\s+(?:el\s+)?(?:menú|catálogo)",
                r"opciones"
            ],

            # Preguntar precio
            Intent.ASK_PRICE: [
                r"(?:cuánto|cuanto)\s+(?:cuesta|vale|sale)\s+(\w+)",
                r"precio\s+(?:del?\s+)?(\w+)"
            ],

            # Confirmar pedido
            Intent.CONFIRM_ORDER: [
                r"(?:sí|si)",
                r"confirma(?:r)?",
                r"ok",
                r"perfecto"
            ],

            # Modificar pedido
            Intent.MODIFY_ORDER: [
                r"cambiar?",
                r"modificar?",
                r"quita(?:r)?\s+(\w+)"
            ],

            # Cancelar
            Intent.GOODBYE: [
                r"cancela(?:r)?",
                r"no\s+(?:quiero|necesito)"
            ],

            # Ayuda
            Intent.HELP: [
                r"ayuda",
                r"(?:qué|que)\s+puedo",
                r"(?:cómo|como)\s+funciona"
            ],

            # Despedida
            Intent.GOODBYE: [
                r"(?:adiós|adios|chao|bye|gracias)"
            ]
        }

        return IntentDecisionTree(patterns)

    @classmethod
    def clear_cache(cls):
        """Limpia el cache de decision trees"""
        cls._decision_tree_cache.clear()
        logger.info("🗑️ Cache de decision trees limpiado")
