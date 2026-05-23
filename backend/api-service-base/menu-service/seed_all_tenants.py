"""
================================================================================
SEED ALL TENANTS - Professional Multi-Tenant Database Seeding
================================================================================
Script unificado para cargar TODOS los tenants en un solo proceso:
- 🦐 Rico Mar Salvatierra (173 productos - mariscos)
- 🚕 Taxi Rápido (datos de servicio de taxi)
- 🍷 Vinetería Don Juan (~70 productos - vinos y licores)
- 💊 Farmacia Santa Fe (~800+ productos - medicamentos)

Autor: Claude Code
Fecha: 2026-02-01
================================================================================
"""

import sys
import json
from pathlib import Path
from typing import Dict, List, Any
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from sqlalchemy.orm import Session
from datetime import datetime

from src.database import engine, SessionLocal, Base
from src.menu_models import Category, Product
from src.models import Tenant, Role, RoleType, User

# Password hashing
from passlib.context import CryptContext
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)


# ==============================================================================
# CONFIGURACIÓN DE TENANTS
# ==============================================================================

TENANTS_DATA = {
    "rico-mar-salvatierra": {
        "json_file": "data/rico_mar_menu.json",
        "type": "restaurant",
        "name": "Rico Mar Salvatierra",
        "business_name": "Rico Mar Salvatierra S.A. de C.V.",
        "description": "Restaurante especializado en mariscos y comida gourmet",
        "slogan": "Los mejores mariscos de la región",
        "primary_color": "#0284C7",
        "secondary_color": "#DC2626",
        "phone": "4611234567",
        "email": "contacto@ricomarsalvatierra.com",
        "whatsapp_number": "524611234567",
    },
    "tenant_wine_001": {
        "json_file": "data/wine_products.json",
        "type": "wine_store",
        "name": "Vinetería Don Juan",
        "business_name": "Vinetería Don Juan S.A. de C.V.",
        "description": "Vinos premium y licores de importación",
        "slogan": "La mejor selección de vinos",
        "primary_color": "#7C3AED",
        "secondary_color": "#DC2626",
        "phone": "5512345678",
        "email": "contacto@vineteriajuan.com",
        "whatsapp_number": "525512345678",
    },
    "tenant_pharmacy_001": {
        "json_file": "data/pharmacy_products.json",
        "type": "pharmacy",
        "name": "Farmacia Santa Fe",
        "business_name": "Farmacia Santa Fe S.A. de C.V.",
        "description": "Farmacia de confianza con medicamentos de calidad",
        "slogan": "Tu salud es lo primero",
        "primary_color": "#10B981",
        "secondary_color": "#059669",
        "phone": "5587654321",
        "email": "contacto@farmaciasantafe.com",
        "whatsapp_number": "525587654321",
    },
    "tenant_taxi_001": {
        "json_file": "data/taxi_service.json",
        "type": "taxi",
        "name": "Taxi Rápido",
        "business_name": "Servicios de Taxi Rápido S.A. de C.V.",
        "description": "Servicio de taxi rápido y confiable",
        "slogan": "Llegamos donde nos necesites",
        "primary_color": "#F59E0B",
        "secondary_color": "#D97706",
        "phone": "5500001111",
        "email": "contacto@taxirapido.com",
        "whatsapp_number": "525500001111",
    }
}


# ==============================================================================
# FUNCIONES DE SEED
# ==============================================================================

def create_tables(db: Session):
    """Crear todas las tablas en la base de datos"""
    logger.info("📦 Creando tablas en la base de datos...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    logger.info("✅ Tablas creadas exitosamente")


def create_roles(db: Session) -> Dict:
    """Crear roles del sistema"""
    logger.info("👥 Creando roles del sistema...")

    roles_data = [
        {"name": "Super Admin", "role_type": RoleType.SUPER_ADMIN.value,
         "description": "Administrador global del sistema"},
        {"name": "Admin", "role_type": RoleType.ADMIN.value,
         "description": "Administrador de tenant"},
        {"name": "Staff", "role_type": RoleType.STAFF.value,
         "description": "Personal del tenant"},
        {"name": "Customer", "role_type": RoleType.CUSTOMER.value,
         "description": "Cliente"},
    ]

    roles = {}
    for role_data in roles_data:
        role = Role(**role_data)
        db.add(role)
        roles[role_data["role_type"]] = role

    db.commit()
    logger.info(f"✅ {len(roles)} roles creados")
    return roles


def seed_tenant_rico_mar(db: Session, tenant_id: str, config: Dict) -> int:
    """Seed de Rico Mar desde JSON"""
    logger.info(f"🦐 Cargando {config['name']}...")

    json_path = Path(__file__).parent / config["json_file"]
    if not json_path.exists():
        logger.warning(f"⚠️  Archivo no encontrado: {json_path}")
        return 0

    with open(json_path, 'r', encoding='utf-8') as f:
        menu_data = json.load(f)

    # Crear categorías
    category_map = {}
    for idx, cat_data in enumerate(menu_data.get('categorias', []), start=1):
        category = Category(
            tenant_id=tenant_id,
            name=cat_data['name'],
            description=cat_data.get('description', ''),
            display_order=cat_data.get('orden', idx),
            is_active=True,
            is_beverage=('bebida' in cat_data['name'].lower())
        )
        db.add(category)
        db.flush()
        category_map[cat_data['id']] = category.id

    # Crear productos
    product_count = 0
    for cat_data in menu_data.get('categorias', []):
        cat_id = category_map[cat_data['id']]

        for prod in cat_data.get('productos', []):
            product = Product(
                tenant_id=tenant_id,
                category_id=cat_id,
                name=prod['name'],
                description=prod.get('description', ''),
                price=str(prod['price']),
                is_available=prod.get('available', True),
                spice_level=prod.get('spicy_level', 0) if isinstance(prod.get('spicy_level'), int) else 0,
                preparation_time_minutes=int(prod.get('preparation_time', '10').split('-')[0]) if isinstance(prod.get('preparation_time'), str) else 10,
                popularity=3,
                menu_classification='regular'
            )
            db.add(product)
            product_count += 1

    db.commit()
    logger.info(f"✅ {config['name']}: {len(category_map)} categorías, {product_count} productos")
    return product_count


def seed_tenant_generic(db: Session, tenant_id: str, config: Dict) -> int:
    """Seed genérico para otros tenants (Wine, Pharmacy, Taxi)"""
    logger.info(f"📦 Cargando {config['name']}...")

    json_path = Path(__file__).parent / config["json_file"]
    if not json_path.exists():
        logger.warning(f"⚠️  Archivo no encontrado: {json_path}")
        logger.info(f"   Creando categorías y productos de ejemplo...")

        # Crear categoría de ejemplo
        category = Category(
            tenant_id=tenant_id,
            name="General",
            description=f"Productos de {config['name']}",
            display_order=1,
            is_active=True,
            is_beverage=False
        )
        db.add(category)
        db.flush()

        # Crear producto de ejemplo
        product = Product(
            tenant_id=tenant_id,
            category_id=category.id,
            name=f"Producto de {config['name']}",
            description="Producto de ejemplo",
            price="100.00",
            is_available=True,
            popularity=3,
            menu_classification='regular'
        )
        db.add(product)
        db.commit()

        logger.info(f"✅ {config['name']}: 1 categoría, 1 producto (ejemplo)")
        return 1

    # Si existe el archivo JSON, cargarlo
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    product_count = 0

    # Detectar estructura del JSON y procesar
    if 'categories' in data:
        # Estructura con categorías
        for cat_data in data['categories']:
            category = Category(
                tenant_id=tenant_id,
                name=cat_data['name'],
                description=cat_data.get('description', ''),
                display_order=cat_data.get('order', 1),
                is_active=True,
                is_beverage=False
            )
            db.add(category)
            db.flush()

            for prod in cat_data.get('products', []):
                product = Product(
                    tenant_id=tenant_id,
                    category_id=category.id,
                    name=prod['name'],
                    description=prod.get('description', ''),
                    price=str(prod.get('price', '0')),
                    is_available=prod.get('available', True),
                    popularity=3,
                    menu_classification='regular'
                )
                db.add(product)
                product_count += 1

    db.commit()
    logger.info(f"✅ {config['name']}: {product_count} productos cargados")
    return product_count


def create_tenant(db: Session, tenant_id: str, config: Dict) -> Tenant:
    """Crear tenant en la base de datos"""

    tenant = Tenant(
        tenant_id=tenant_id,
        name=config['name'],
        business_name=config['business_name'],
        description=config['description'],
        slogan=config['slogan'],
        primary_color=config['primary_color'],
        secondary_color=config['secondary_color'],
        phone=config['phone'],
        email=config['email'],
        whatsapp_number=config['whatsapp_number'],
        settings={
            "business_hours": {
                "monday": "09:00-22:00",
                "tuesday": "09:00-22:00",
                "wednesday": "09:00-22:00",
                "thursday": "09:00-22:00",
                "friday": "09:00-23:00",
                "saturday": "10:00-23:00",
                "sunday": "10:00-21:00"
            },
            "delivery_fee": 50,
            "min_order_amount": 150,
            "payment_methods": ["cash", "card", "transfer"],
            "currency": "MXN",
            "type": config['type']
        }
    )

    db.add(tenant)
    db.commit()
    db.refresh(tenant)

    return tenant


# ==============================================================================
# MAIN
# ==============================================================================

def main():
    """Ejecutar seed de todos los tenants"""

    logger.info("=" * 80)
    logger.info("SEED ALL TENANTS - Multi-Tenant Database Initialization")
    logger.info("=" * 80)

    db = SessionLocal()

    try:
        # 1. Crear tablas
        create_tables(db)

        # 2. Crear roles
        roles = create_roles(db)

        # 3. Seed cada tenant
        total_products = 0

        for tenant_id, config in TENANTS_DATA.items():
            logger.info(f"\n{'='*80}")
            logger.info(f"TENANT: {tenant_id}")
            logger.info(f"{'='*80}")

            # Crear tenant
            tenant = create_tenant(db, tenant_id, config)
            logger.info(f"✅ Tenant creado: {tenant.name}")

            # Seed productos según tipo
            if tenant_id == "rico-mar-salvatierra":
                count = seed_tenant_rico_mar(db, tenant_id, config)
            else:
                count = seed_tenant_generic(db, tenant_id, config)

            total_products += count

        # 4. Resumen final
        logger.info("\n" + "=" * 80)
        logger.info("RESUMEN FINAL")
        logger.info("=" * 80)
        logger.info(f"✅ Tenants creados: {len(TENANTS_DATA)}")
        logger.info(f"✅ Productos totales: {total_products}")
        logger.info(f"✅ Roles creados: {len(roles)}")
        logger.info("=" * 80)
        logger.info("🎉 SEED COMPLETADO EXITOSAMENTE")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"❌ Error durante el seed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
