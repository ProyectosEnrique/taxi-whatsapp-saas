#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tenant Manager - Gestión de Multi-Tenancy

Gestiona la configuración y datos de múltiples tenants (tiendas).
Cada tenant tiene:
- Configuración de negocio
- FSM personalizado
- Catálogo de productos propio
- Reglas de negocio específicas
"""

import logging
from typing import Optional, Dict, List, Any
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class TenantConfig:
    """Configuración de un tenant"""
    tenant_id: str
    name: str
    type: str  # wine_store, pharmacy, restaurant, generic
    phone: str
    active: bool = True

    # Configuración FSM
    fsm_config: Dict[str, Any] = None

    # Reglas de negocio
    business_rules: Dict[str, Any] = None

    # Branding y mensajes
    branding: Dict[str, Any] = None

    # Metadata
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __post_init__(self):
        """Inicializar valores por defecto"""
        if self.fsm_config is None:
            self.fsm_config = {}
        if self.business_rules is None:
            self.business_rules = {}
        if self.branding is None:
            self.branding = {}


class TenantManager:
    """
    Gestiona la configuración y datos de múltiples tenants

    Responsabilidades:
    1. Cargar configuración de tenants
    2. Obtener productos por tenant
    3. Identificar tenant desde número de teléfono
    4. Cache de configuraciones
    """

    def __init__(self, use_firestore: bool = True):
        """
        Inicializa el TenantManager

        Args:
            use_firestore: Si True, usa Firestore. Si False, usa JSON local.
        """
        self.use_firestore = use_firestore
        self._tenant_cache: Dict[str, TenantConfig] = {}
        self._phone_to_tenant: Dict[str, str] = {}

        # Inicializar Firestore si está habilitado
        if self.use_firestore:
            try:
                from google.cloud import firestore
                self.db = firestore.Client()
                logger.info("✅ Firestore conectado")
            except Exception as e:
                logger.warning(f"⚠️ Firestore no disponible: {e}")
                logger.info("📁 Usando almacenamiento local (JSON)")
                self.use_firestore = False
                self.db = None
        else:
            self.db = None
            logger.info("📁 Usando almacenamiento local (JSON)")

        # Cargar tenants iniciales
        self._load_initial_tenants()

    def _load_initial_tenants(self):
        """Carga configuración inicial de tenants"""
        if self.use_firestore:
            self._load_from_firestore()
        else:
            self._load_from_json()

    def _load_from_firestore(self):
        """Carga tenants desde Firestore"""
        try:
            tenants_ref = self.db.collection('tenants')
            docs = tenants_ref.stream()

            count = 0
            for doc in docs:
                data = doc.to_dict()
                tenant_id = doc.id

                config = self._parse_tenant_data(tenant_id, data)
                self._tenant_cache[tenant_id] = config

                # Mapear teléfono a tenant
                if config.phone:
                    self._phone_to_tenant[config.phone] = tenant_id

                count += 1

            logger.info(f"✅ Cargados {count} tenants desde Firestore")

        except Exception as e:
            logger.error(f"❌ Error cargando tenants desde Firestore: {e}")

    def _load_from_json(self):
        """Carga tenants desde archivos JSON locales"""
        import json
        from pathlib import Path

        # Buscar archivo de configuración de tenants
        config_path = Path(__file__).parent.parent.parent / 'config' / 'tenants.json'

        if not config_path.exists():
            logger.warning(f"⚠️ No existe {config_path}, creando tenant por defecto")
            self._create_default_tenant()
            return

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                tenants_data = json.load(f)

            for tenant_id, data in tenants_data.get('tenants', {}).items():
                config = self._parse_tenant_data(tenant_id, data)
                self._tenant_cache[tenant_id] = config

                # Mapear teléfono a tenant
                if config.phone:
                    self._phone_to_tenant[config.phone] = tenant_id

            logger.info(f"✅ Cargados {len(self._tenant_cache)} tenants desde JSON")

        except Exception as e:
            logger.error(f"❌ Error cargando tenants desde JSON: {e}")
            self._create_default_tenant()

    def _parse_tenant_data(self, tenant_id: str, data: Dict[str, Any]) -> TenantConfig:
        """Parsea datos de tenant a TenantConfig"""
        business_info = data.get('business_info', {})

        return TenantConfig(
            tenant_id=tenant_id,
            name=business_info.get('name', f'Tenant {tenant_id}'),
            type=business_info.get('type', 'generic'),
            phone=business_info.get('phone', ''),
            active=business_info.get('active', True),
            fsm_config=data.get('fsm_config', {}),
            business_rules=data.get('business_rules', {}),
            branding=data.get('branding', {}),
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at')
        )

    def _create_default_tenant(self):
        """Crea un tenant por defecto para desarrollo"""
        default_tenant = TenantConfig(
            tenant_id='default',
            name='Demo Restaurant',
            type='restaurant',
            phone='+5215500000000',
            active=True,
            fsm_config={
                'decision_tree_version': 'restaurant_v1',
                'llm_fallback_enabled': True,
                'confidence_threshold': 0.7
            },
            business_rules={
                'min_order_amount': 100.0,
                'delivery_fee': 30.0,
                'operating_hours': {
                    'monday': '09:00-22:00',
                    'tuesday': '09:00-22:00',
                    'wednesday': '09:00-22:00',
                    'thursday': '09:00-22:00',
                    'friday': '09:00-23:00',
                    'saturday': '10:00-23:00',
                    'sunday': '10:00-21:00'
                }
            },
            branding={
                'greeting_message': '¡Hola! Bienvenido a Demo Restaurant. ¿En qué puedo ayudarte?',
                'tone': 'friendly',
                'language': 'es-MX'
            }
        )

        self._tenant_cache['default'] = default_tenant
        self._phone_to_tenant[default_tenant.phone] = 'default'

        logger.info("✅ Tenant por defecto creado: 'default'")

    def get_tenant(self, tenant_id: str) -> Optional[TenantConfig]:
        """
        Obtiene configuración de un tenant

        Args:
            tenant_id: ID del tenant

        Returns:
            TenantConfig o None si no existe
        """
        # Revisar cache primero
        if tenant_id in self._tenant_cache:
            return self._tenant_cache[tenant_id]

        # Si usa Firestore, intentar cargar
        if self.use_firestore and self.db:
            try:
                doc_ref = self.db.collection('tenants').document(tenant_id)
                doc = doc_ref.get()

                if doc.exists:
                    data = doc.to_dict()
                    config = self._parse_tenant_data(tenant_id, data)

                    # Guardar en cache
                    self._tenant_cache[tenant_id] = config
                    if config.phone:
                        self._phone_to_tenant[config.phone] = tenant_id

                    return config
            except Exception as e:
                logger.error(f"❌ Error cargando tenant {tenant_id}: {e}")

        return None

    def get_tenant_by_phone(self, phone: str) -> Optional[TenantConfig]:
        """
        Identifica tenant por número de teléfono

        Args:
            phone: Número de WhatsApp del negocio

        Returns:
            TenantConfig o None
        """
        # Buscar en mapeo de cache
        tenant_id = self._phone_to_tenant.get(phone)

        if tenant_id:
            return self.get_tenant(tenant_id)

        # Si usa Firestore, buscar en BD
        if self.use_firestore and self.db:
            try:
                query = self.db.collection('tenants').where(
                    'business_info.phone', '==', phone
                ).limit(1)

                docs = list(query.stream())

                if docs:
                    doc = docs[0]
                    data = doc.to_dict()
                    config = self._parse_tenant_data(doc.id, data)

                    # Guardar en cache
                    self._tenant_cache[doc.id] = config
                    self._phone_to_tenant[phone] = doc.id

                    return config
            except Exception as e:
                logger.error(f"❌ Error buscando tenant por teléfono {phone}: {e}")

        return None

    def get_products(self, tenant_id: str, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Obtiene productos de un tenant

        Args:
            tenant_id: ID del tenant
            category: Categoría opcional para filtrar

        Returns:
            Lista de productos
        """
        products = []

        if self.use_firestore and self.db:
            try:
                # Query a Firestore
                query = self.db.collection('products').where('tenant_id', '==', tenant_id)

                if category:
                    query = query.where('category', '==', category)

                # Solo productos activos
                query = query.where('active', '==', True)

                docs = query.stream()
                products = [doc.to_dict() for doc in docs]

                logger.info(f"✅ Cargados {len(products)} productos para {tenant_id}")

            except Exception as e:
                logger.error(f"❌ Error cargando productos: {e}")
        else:
            # Cargar desde JSON local
            products = self._load_products_from_json(tenant_id, category)

        return products

    def _load_products_from_json(self, tenant_id: str, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Carga productos desde JSON local (nueva estructura multi-tenant)"""
        import json
        from pathlib import Path

        config_base = Path(__file__).parent.parent.parent / 'config'

        # NUEVA ESTRUCTURA: config/{business_type}/{tenant_id}/products.json
        # Primero obtener el tipo de negocio del tenant
        tenant_config = self.get_tenant(tenant_id)
        business_type = tenant_config.type if tenant_config else None

        products_path = None

        # Intentar nueva estructura primero
        if business_type:
            new_path = config_base / business_type / tenant_id / 'products.json'
            if new_path.exists():
                products_path = new_path
                logger.debug(f"📂 Usando nueva estructura: {new_path}")

        # Fallback: buscar en todas las carpetas de tipo de negocio
        if not products_path:
            for business_dir in config_base.iterdir():
                if business_dir.is_dir() and not business_dir.name.startswith('.'):
                    tenant_dir = business_dir / tenant_id
                    if tenant_dir.exists():
                        potential_path = tenant_dir / 'products.json'
                        if potential_path.exists():
                            products_path = potential_path
                            logger.debug(f"📂 Encontrado en: {potential_path}")
                            break

        # Fallback: estructura antigua (products_{tenant_id}.json)
        if not products_path:
            legacy_path = config_base / f'products_{tenant_id}.json'
            if legacy_path.exists():
                products_path = legacy_path
                logger.debug(f"📂 Usando estructura legacy: {legacy_path}")

        # Último fallback: archivo genérico
        if not products_path:
            generic_path = config_base / 'products.json'
            if generic_path.exists():
                products_path = generic_path

        if not products_path or not products_path.exists():
            logger.warning(f"⚠️ No existe archivo de productos para {tenant_id}")
            return []

        try:
            with open(products_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            all_products = data.get('products', [])

            # Filtrar por tenant_id y categoría
            products = []
            for product in all_products:
                # Si el producto no tiene tenant_id, asumir que es del tenant actual
                product_tenant = product.get('tenant_id', tenant_id)

                if product_tenant != tenant_id:
                    continue

                if not product.get('active', True):
                    continue

                if category and product.get('category') != category:
                    continue

                products.append(product)

            logger.info(f"✅ Cargados {len(products)} productos desde {products_path.name}")
            return products

        except Exception as e:
            logger.error(f"❌ Error cargando productos desde JSON: {e}")
            return []

    def get_categories(self, tenant_id: str) -> Dict[str, Any]:
        """
        Obtiene categorías de un tenant

        Args:
            tenant_id: ID del tenant

        Returns:
            Diccionario con main_categories y subcategories
        """
        import json
        from pathlib import Path

        config_base = Path(__file__).parent.parent.parent / 'config'

        # Obtener tipo de negocio del tenant
        tenant_config = self.get_tenant(tenant_id)
        business_type = tenant_config.type if tenant_config else None

        categories_path = None

        # Buscar en nueva estructura
        if business_type:
            new_path = config_base / business_type / tenant_id / 'categories.json'
            if new_path.exists():
                categories_path = new_path

        # Fallback: buscar en todas las carpetas
        if not categories_path:
            for business_dir in config_base.iterdir():
                if business_dir.is_dir() and not business_dir.name.startswith('.'):
                    tenant_dir = business_dir / tenant_id
                    if tenant_dir.exists():
                        potential_path = tenant_dir / 'categories.json'
                        if potential_path.exists():
                            categories_path = potential_path
                            break

        # Fallback: estructura antigua
        if not categories_path:
            legacy_path = config_base / f'categories_{tenant_id}.json'
            if legacy_path.exists():
                categories_path = legacy_path

        if not categories_path or not categories_path.exists():
            logger.warning(f"⚠️ No existe archivo de categorías para {tenant_id}")
            return {"main_categories": [], "subcategories": []}

        try:
            with open(categories_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            logger.info(f"✅ Cargadas categorías para {tenant_id}")
            return {
                "main_categories": data.get("main_categories", []),
                "subcategories": data.get("subcategories", [])
            }

        except Exception as e:
            logger.error(f"❌ Error cargando categorías: {e}")
            return {"main_categories": [], "subcategories": []}

    def get_tenant_settings(self, tenant_id: str) -> Dict[str, Any]:
        """
        Obtiene settings específicos de un tenant desde la nueva estructura

        Args:
            tenant_id: ID del tenant

        Returns:
            Diccionario con configuración del tenant
        """
        import json
        from pathlib import Path

        config_base = Path(__file__).parent.parent.parent / 'config'

        # Obtener tipo de negocio
        tenant_config = self.get_tenant(tenant_id)
        business_type = tenant_config.type if tenant_config else None

        settings_path = None

        # Buscar en nueva estructura
        if business_type:
            new_path = config_base / business_type / tenant_id / 'settings.json'
            if new_path.exists():
                settings_path = new_path

        # Fallback: buscar en todas las carpetas
        if not settings_path:
            for business_dir in config_base.iterdir():
                if business_dir.is_dir() and not business_dir.name.startswith('.'):
                    tenant_dir = business_dir / tenant_id
                    if tenant_dir.exists():
                        potential_path = tenant_dir / 'settings.json'
                        if potential_path.exists():
                            settings_path = potential_path
                            break

        if not settings_path or not settings_path.exists():
            # Retornar configuración del tenant_cache como fallback
            if tenant_config:
                return {
                    "tenant_id": tenant_id,
                    "business_info": {
                        "name": tenant_config.name,
                        "type": tenant_config.type,
                        "phone": tenant_config.phone,
                        "active": tenant_config.active
                    },
                    "branding": tenant_config.branding,
                    "business_rules": tenant_config.business_rules
                }
            return {}

        try:
            with open(settings_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            logger.info(f"✅ Cargados settings para {tenant_id}")
            return data

        except Exception as e:
            logger.error(f"❌ Error cargando settings: {e}")
            return {}

    def list_tenants(self) -> List[TenantConfig]:
        """
        Lista todos los tenants activos

        Returns:
            Lista de TenantConfig
        """
        return [t for t in self._tenant_cache.values() if t.active]

    def reload_tenant(self, tenant_id: str) -> bool:
        """
        Recarga configuración de un tenant desde la BD

        Args:
            tenant_id: ID del tenant

        Returns:
            True si se recargó exitosamente
        """
        # Limpiar cache
        if tenant_id in self._tenant_cache:
            old_config = self._tenant_cache[tenant_id]
            if old_config.phone in self._phone_to_tenant:
                del self._phone_to_tenant[old_config.phone]
            del self._tenant_cache[tenant_id]

        # Recargar
        config = self.get_tenant(tenant_id)

        return config is not None

    def get_greeting_message(self, tenant_id: str) -> str:
        """
        Obtiene mensaje de saludo personalizado del tenant

        Args:
            tenant_id: ID del tenant

        Returns:
            Mensaje de saludo
        """
        config = self.get_tenant(tenant_id)

        if config and config.branding:
            return config.branding.get(
                'greeting_message',
                '¡Hola! ¿En qué puedo ayudarte?'
            )

        return '¡Hola! ¿En qué puedo ayudarte?'


# ============================================================
# SINGLETON GLOBAL
# ============================================================

_tenant_manager: Optional[TenantManager] = None


def get_tenant_manager() -> TenantManager:
    """
    Obtiene instancia global del TenantManager (Singleton)

    Returns:
        TenantManager
    """
    global _tenant_manager

    if _tenant_manager is None:
        # Intentar usar Firestore por defecto
        _tenant_manager = TenantManager(use_firestore=True)

    return _tenant_manager


def init_tenant_manager(use_firestore: bool = True) -> TenantManager:
    """
    Inicializa el TenantManager con configuración específica

    Args:
        use_firestore: Si True, usa Firestore. Si False, JSON local.

    Returns:
        TenantManager
    """
    global _tenant_manager
    _tenant_manager = TenantManager(use_firestore=use_firestore)
    return _tenant_manager
