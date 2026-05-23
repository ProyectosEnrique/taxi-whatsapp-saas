"""
================================================================================
DEMO MIGRATION SCRIPT
================================================================================
Migra el sistema demo existente (demo_config.py) a PostgreSQL como tienda
especial con is_demo=TRUE.

Esto permite que el demo use el mismo sistema multi-tenant que las tiendas reales.
================================================================================
"""

import sys
import os
from pathlib import Path

# Add backend directory to Python path
backend_path = Path(__file__).parent.parent / "backend" / "whatsapp-gateway"
sys.path.insert(0, str(backend_path / "src"))

from sqlalchemy.orm import Session
from database import SessionLocal, init_db
from orm_models import (
    RestaurantORM,
    CategoryORM,
    ProductORM,
    LoyaltyConfigORM
)
from demo_config import DEMO_CATALOGS, DemoIndustry, DEMO_INITIAL_POINTS
import uuid


def generate_category_id() -> str:
    """Generar ID único para categoría"""
    return f"cat_{uuid.uuid4().hex[:12]}"


def generate_product_id() -> str:
    """Generar ID único para producto"""
    return f"prod_{uuid.uuid4().hex[:12]}"


def migrate_demo_restaurant(db: Session):
    """
    Migrar demo de RESTAURANTE a PostgreSQL.
    Crea la tienda demo con todos sus productos y configuración.
    """

    print("\n" + "="*80)
    print("MIGRANDO DEMO RESTAURANT A POSTGRESQL")
    print("="*80 + "\n")

    # 1. Verificar si ya existe
    existing = db.query(RestaurantORM).filter(
        RestaurantORM.restaurant_id == "demo_restaurant"
    ).first()

    if existing:
        print("⚠️  La tienda demo ya existe. Eliminando para recrear...")
        db.delete(existing)
        db.commit()

    # 2. Obtener datos del demo
    demo_data = DEMO_CATALOGS[DemoIndustry.RESTAURANT]

    print(f"📝 Datos del demo:")
    print(f"   Nombre: {demo_data['name']}")
    print(f"   Categorías: {len(demo_data['categories'])}")
    print(f"   Productos: {len(demo_data['products'])}")
    print()

    # 3. Crear tienda demo
    print("🏪 Creando tienda demo...")
    restaurant = RestaurantORM(
        restaurant_id="demo_restaurant",
        name=demo_data["name"],
        slug="demo-taqueria",
        owner_name="Demo Admin",
        owner_email="demo@tuplatforma.com",
        owner_phone="+14155238886",
        business_type="restaurant",
        plan="demo",
        twilio_number="+14155238886",
        webhook_url="https://tu-dominio.com/webhook/whatsapp/demo_restaurant",
        status="active",
        is_demo=True,
        settings={
            "welcome_message": demo_data["welcome_message"],
            "icon": demo_data["icon"],
            "description": demo_data["description"]
        }
    )
    db.add(restaurant)
    db.flush()  # Para obtener el ID
    print(f"   ✅ Tienda creada: {restaurant.restaurant_id}")

    # 4. Crear categorías
    print(f"\n📂 Creando {len(demo_data['categories'])} categorías...")
    category_map = {}  # Mapeo de slug a category_id para productos

    for idx, cat_data in enumerate(demo_data["categories"]):
        category = CategoryORM(
            category_id=generate_category_id(),
            restaurant_id="demo_restaurant",
            name=cat_data["name"],
            slug=cat_data["id"],
            icon=cat_data["icon"],
            display_order=idx,
            is_active=True
        )
        db.add(category)
        category_map[cat_data["id"]] = category.category_id
        print(f"   ✅ {cat_data['icon']} {cat_data['name']}")

    db.flush()

    # 5. Crear productos
    print(f"\n🍽️  Creando {len(demo_data['products'])} productos...")

    for prod_data in demo_data["products"]:
        # Mapear category slug a category_id
        category_slug = prod_data["category"]
        category_id = category_map.get(category_slug)

        if not category_id:
            print(f"   ⚠️  Categoría '{category_slug}' no encontrada para producto '{prod_data['name']}'")
            continue

        product = ProductORM(
            product_id=prod_data["id"],  # Usar el ID del demo
            restaurant_id="demo_restaurant",
            category_id=category_id,
            name=prod_data["name"],
            slug=prod_data["id"],
            description=prod_data["description"],
            price=prod_data["price"],
            image_url=prod_data.get("image"),
            available=prod_data["available"],
            stock_quantity=999  # Stock ilimitado para demo
        )
        db.add(product)
        print(f"   ✅ {prod_data['name']} - ${prod_data['price']:.2f}")

    db.flush()

    # 6. Crear configuración de puntos de fidelidad
    print(f"\n🎁 Creando configuración de loyalty...")
    loyalty_config = LoyaltyConfigORM(
        restaurant_id="demo_restaurant",
        enabled=True,
        points_per_currency=0.1,  # 10 puntos por cada $100
        currency_per_point=0.5,   # $0.50 por cada punto
        min_points_to_redeem=100,
        tier_thresholds={
            "bronce": 0,
            "plata": 1000,
            "oro": 2500
        },
        tier_multipliers={
            "bronce": 1.0,
            "plata": 1.5,
            "oro": 2.0
        },
        tier_names={
            "bronce": "🥉 Cliente Bronce",
            "plata": "🥈 Cliente Plata",
            "oro": "🥇 Cliente Oro"
        }
    )
    db.add(loyalty_config)
    print(f"   ✅ Sistema de puntos configurado")
    print(f"   - Puntos por compra: {loyalty_config.points_per_currency * 100} pts/$100")
    print(f"   - Valor por punto: ${loyalty_config.currency_per_point}")
    print(f"   - Mínimo para canjear: {loyalty_config.min_points_to_redeem} pts")

    # 7. Commit final
    db.commit()

    print("\n" + "="*80)
    print("✅ MIGRACIÓN COMPLETADA EXITOSAMENTE")
    print("="*80)
    print(f"\n📊 Resumen:")
    print(f"   • Tienda: demo_restaurant")
    print(f"   • Categorías: {len(demo_data['categories'])}")
    print(f"   • Productos: {len(demo_data['products'])}")
    print(f"   • Loyalty: Configurado")
    print(f"   • Twilio Number: +1 415 523 8886")
    print(f"   • Webhook URL: /webhook/whatsapp/demo_restaurant")
    print()


def main():
    """Función principal"""
    try:
        print("\n🔧 Inicializando base de datos...")
        init_db()

        print("✅ Base de datos inicializada")

        # Crear sesión
        db = SessionLocal()

        try:
            # Migrar demo
            migrate_demo_restaurant(db)

            print("✅ Proceso completado")
            print("\n📝 Próximos pasos:")
            print("   1. Actualizar main_multitenant.py con lógica de demo")
            print("   2. Configurar webhook de Twilio: /webhook/whatsapp/demo_restaurant")
            print("   3. Probar flujo completo desde WhatsApp")
            print()

        except Exception as e:
            print(f"\n❌ Error durante la migración: {e}")
            db.rollback()
            raise
        finally:
            db.close()

    except Exception as e:
        print(f"\n❌ Error fatal: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
