"""
================================================================================
SEED DATA SCRIPT
================================================================================
Script para cargar datos de prueba con 3 tiendas diferentes
================================================================================

Uso:
    python seed_data.py

Este script crea:
- 3 Tenants (Taquería, Cafetería, Boutique)
- Categorías para cada tenant
- Productos para cada tenant
- Usuarios (admins y clientes)
- Roles
- Promociones
- Pedidos de ejemplo
- Reseñas

"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import random

from src.database import engine, SessionLocal
from src.models.database import Base
from src.models.user import User
from src.models.role import Role, RoleType
from src.models.tenant import Tenant
from src.models import Category, Product, Promotion
from src.models.address import Address
from src.models.order import Order, OrderItem, OrderStatus, PaymentMethod, DeliveryType
from src.models.review import Review
from src.models.loyalty import LoyaltyAccount, Reward, LoyaltyTransaction, LoyaltyLevel, TransactionType

# Importar función de hash de password
from src.routers.auth import hash_password


print("=" * 80)
print("INICIANDO CARGA DE DATOS DE PRUEBA")
print("=" * 80)


# ==============================================================================
# PASO 1: CREAR TABLAS
# ==============================================================================

print("\n1. Creando tablas...")
Base.metadata.create_all(bind=engine)
print("   ✓ Tablas creadas")


# ==============================================================================
# PASO 2: CREAR ROLES
# ==============================================================================

def create_roles(db: Session):
    """Crear roles del sistema"""
    print("\n2. Creando roles...")

    roles_data = [
        {"name": "Super Admin", "role_type": RoleType.SUPER_ADMIN.value, "description": "Administrador global del sistema"},
        {"name": "Admin", "role_type": RoleType.ADMIN.value, "description": "Administrador de tenant"},
        {"name": "Staff", "role_type": RoleType.STAFF.value, "description": "Personal del tenant"},
        {"name": "Customer", "role_type": RoleType.CUSTOMER.value, "description": "Cliente"},
    ]

    roles = {}
    for role_data in roles_data:
        existing = db.query(Role).filter(Role.name == role_data["name"]).first()
        if not existing:
            role = Role(**role_data)
            db.add(role)
            roles[role_data["role_type"]] = role
        else:
            roles[role_data["role_type"]] = existing

    db.commit()
    print("   ✓ Roles creados")
    return roles


# ==============================================================================
# PASO 3: CREAR TENANTS
# ==============================================================================

def create_tenants(db: Session):
    """Crear 3 tenants de prueba"""
    print("\n3. Creando tenants...")

    tenants_data = [
        {
            "tenant_id": "taqueria-loca",
            "name": "La Taquería Loca",
            "business_name": "Taquería Loca S.A. de C.V.",
            "description": "Los mejores tacos de la ciudad desde 2010",
            "slogan": "¡Tacos que vuelven loco!",
            "primary_color": "#DC2626",
            "secondary_color": "#059669",
            "phone": "5551234567",
            "email": "info@taquerialoca.com",
            "whatsapp_number": "5251234567",
            "settings": {
                "business_hours": {
                    "lunes": "10:00-22:00",
                    "martes": "10:00-22:00",
                    "miercoles": "10:00-22:00",
                    "jueves": "10:00-23:00",
                    "viernes": "10:00-23:00",
                    "sabado": "10:00-23:00",
                    "domingo": "10:00-21:00"
                },
                "delivery_fee": 30,
                "min_order_amount": 100,
                "accepts_cash": True,
                "accepts_card": True
            }
        },
        {
            "tenant_id": "cafe-aroma",
            "name": "Café Aroma",
            "business_name": "Aromas del Café S.A.",
            "description": "Café de especialidad y repostería artesanal",
            "slogan": "Donde cada taza cuenta una historia",
            "primary_color": "#92400E",
            "secondary_color": "#F59E0B",
            "phone": "5559876543",
            "email": "hola@cafearoma.com",
            "whatsapp_number": "5259876543",
            "settings": {
                "business_hours": {
                    "lunes": "07:00-20:00",
                    "martes": "07:00-20:00",
                    "miercoles": "07:00-20:00",
                    "jueves": "07:00-20:00",
                    "viernes": "07:00-21:00",
                    "sabado": "08:00-21:00",
                    "domingo": "08:00-19:00"
                },
                "delivery_fee": 25,
                "min_order_amount": 80,
                "accepts_cash": True,
                "accepts_card": True
            }
        },
        {
            "tenant_id": "boutique-fashion",
            "name": "Boutique Fashion",
            "business_name": "Fashion Boutique México S.A.",
            "description": "Moda contemporánea para toda la familia",
            "slogan": "Tu estilo, nuestra pasión",
            "primary_color": "#DB2777",
            "secondary_color": "#7C3AED",
            "phone": "5556789012",
            "email": "ventas@boutiquefashion.com",
            "whatsapp_number": "5256789012",
            "settings": {
                "business_hours": {
                    "lunes": "10:00-19:00",
                    "martes": "10:00-19:00",
                    "miercoles": "10:00-19:00",
                    "jueves": "10:00-19:00",
                    "viernes": "10:00-20:00",
                    "sabado": "10:00-20:00",
                    "domingo": "11:00-18:00"
                },
                "delivery_fee": 50,
                "min_order_amount": 200,
                "accepts_cash": True,
                "accepts_card": True,
                "free_shipping_from": 1000
            }
        }
    ]

    tenants = []
    for tenant_data in tenants_data:
        existing = db.query(Tenant).filter(Tenant.tenant_id == tenant_data["tenant_id"]).first()
        if not existing:
            tenant = Tenant(**tenant_data)
            db.add(tenant)
            tenants.append(tenant)
        else:
            tenants.append(existing)

    db.commit()
    print(f"   ✓ {len(tenants)} tenants creados")
    return tenants


# ==============================================================================
# PASO 4: CREAR USUARIOS
# ==============================================================================

def create_users(db: Session, roles: dict, tenants: list):
    """Crear usuarios de prueba"""
    print("\n4. Creando usuarios...")

    users_data = [
        # Super Admin
        {"email": "superadmin@system.com", "password": "Admin123!", "name": "Super Admin", "phone": "5550000000", "tenant_id": "system", "role_type": "super_admin"},

        # Admins por tenant
        {"email": "admin@taquerialoca.com", "password": "Admin123!", "name": "Juan Administrador", "phone": "5551111111", "tenant_id": "taqueria-loca", "role_type": "admin"},
        {"email": "admin@cafearoma.com", "password": "Admin123!", "name": "María Gerente", "phone": "5552222222", "tenant_id": "cafe-aroma", "role_type": "admin"},
        {"email": "admin@boutiquefashion.com", "password": "Admin123!", "name": "Carlos Manager", "phone": "5553333333", "tenant_id": "boutique-fashion", "role_type": "admin"},

        # Clientes
        {"email": "cliente1@gmail.com", "password": "Cliente123!", "name": "Pedro García", "phone": "5554444444", "tenant_id": "taqueria-loca", "role_type": "customer"},
        {"email": "cliente2@gmail.com", "password": "Cliente123!", "name": "Ana López", "phone": "5555555555", "tenant_id": "cafe-aroma", "role_type": "customer"},
        {"email": "cliente3@gmail.com", "password": "Cliente123!", "name": "Luis Martínez", "phone": "5556666666", "tenant_id": "boutique-fashion", "role_type": "customer"},
    ]

    users = {}
    for user_data in users_data:
        existing = db.query(User).filter(User.email == user_data["email"]).first()
        if not existing:
            role_type = user_data.pop("role_type")
            password = user_data.pop("password")

            user = User(
                **user_data,
                password_hash=hash_password(password),
                is_active=True,
                is_verified=True
            )

            # Asignar rol
            user.roles.append(roles[role_type])

            db.add(user)
            users[user_data["email"]] = user
        else:
            users[user_data["email"]] = existing

    db.commit()
    print(f"   ✓ {len(users)} usuarios creados")
    print("   Credenciales de prueba:")
    print("     Super Admin: superadmin@system.com / Admin123!")
    print("     Admin Taquería: admin@taquerialoca.com / Admin123!")
    print("     Admin Café: admin@cafearoma.com / Admin123!")
    print("     Admin Boutique: admin@boutiquefashion.com / Admin123!")
    return users


# ==============================================================================
# PASO 5: CREAR CATEGORÍAS Y PRODUCTOS
# ==============================================================================

def create_catalog(db: Session):
    """Crear categorías y productos para cada tenant"""
    print("\n5. Creando catálogos...")

    # TAQUERÍA
    print("   - Taquería Loca...")
    taqueria_categories = [
        {"name": "Tacos", "description": "Tacos tradicionales y especiales", "tenant_id": "taqueria-loca", "display_order": 1},
        {"name": "Quesadillas", "description": "Quesadillas al gusto", "tenant_id": "taqueria-loca", "display_order": 2},
        {"name": "Bebidas", "description": "Refrescos y aguas frescas", "tenant_id": "taqueria-loca", "display_order": 3, "is_beverage": True},
        {"name": "Postres", "description": "Dulces mexicanos", "tenant_id": "taqueria-loca", "display_order": 4},
    ]

    for cat_data in taqueria_categories:
        if not db.query(Category).filter(Category.name == cat_data["name"], Category.tenant_id == cat_data["tenant_id"]).first():
            db.add(Category(**cat_data))
    db.commit()

    tacos_cat = db.query(Category).filter(Category.name == "Tacos", Category.tenant_id == "taqueria-loca").first()
    bebidas_cat = db.query(Category).filter(Category.name == "Bebidas", Category.tenant_id == "taqueria-loca").first()

    taqueria_products = [
        {"name": "Taco de Suadero", "description": "Taco de suadero con cebolla y cilantro", "price": 25, "category_id": tacos_cat.id, "tenant_id": "taqueria-loca", "popularity": 5, "profitability": "alta"},
        {"name": "Taco de Pastor", "description": "Taco al pastor con piña", "price": 25, "category_id": tacos_cat.id, "tenant_id": "taqueria-loca", "popularity": 5, "profitability": "alta"},
        {"name": "Taco de Bistec", "description": "Taco de bistec jugoso", "price": 28, "category_id": tacos_cat.id, "tenant_id": "taqueria-loca", "popularity": 4, "profitability": "media"},
        {"name": "Coca Cola", "description": "Refresco 355ml", "price": 20, "category_id": bebidas_cat.id, "tenant_id": "taqueria-loca", "popularity": 5, "profitability": "alta"},
        {"name": "Agua de Horchata", "description": "Agua fresca de horchata", "price": 25, "category_id": bebidas_cat.id, "tenant_id": "taqueria-loca", "popularity": 4, "profitability": "alta"},
    ]

    for prod_data in taqueria_products:
        if not db.query(Product).filter(Product.name == prod_data["name"], Product.tenant_id == prod_data["tenant_id"]).first():
            db.add(Product(**prod_data))
    db.commit()

    # CAFETERÍA
    print("   - Café Aroma...")
    cafe_categories = [
        {"name": "Café Caliente", "description": "Cafés preparados calientes", "tenant_id": "cafe-aroma", "display_order": 1, "is_beverage": True},
        {"name": "Café Frío", "description": "Cafés fríos y frappes", "tenant_id": "cafe-aroma", "display_order": 2, "is_beverage": True},
        {"name": "Repostería", "description": "Pasteles y pays", "tenant_id": "cafe-aroma", "display_order": 3},
        {"name": "Desayunos", "description": "Desayunos completos", "tenant_id": "cafe-aroma", "display_order": 4},
    ]

    for cat_data in cafe_categories:
        if not db.query(Category).filter(Category.name == cat_data["name"], Category.tenant_id == cat_data["tenant_id"]).first():
            db.add(Category(**cat_data))
    db.commit()

    cafe_caliente_cat = db.query(Category).filter(Category.name == "Café Caliente", Category.tenant_id == "cafe-aroma").first()
    reposteria_cat = db.query(Category).filter(Category.name == "Repostería", Category.tenant_id == "cafe-aroma").first()

    cafe_products = [
        {"name": "Cappuccino", "description": "Cappuccino italiano", "price": 50, "category_id": cafe_caliente_cat.id, "tenant_id": "cafe-aroma", "popularity": 5, "profitability": "alta"},
        {"name": "Latte", "description": "Café latte con leche vaporizada", "price": 55, "category_id": cafe_caliente_cat.id, "tenant_id": "cafe-aroma", "popularity": 5, "profitability": "alta"},
        {"name": "Americano", "description": "Café americano doble shot", "price": 40, "category_id": cafe_caliente_cat.id, "tenant_id": "cafe-aroma", "popularity": 4, "profitability": "alta"},
        {"name": "Cheesecake", "description": "Rebanada de cheesecake de fresa", "price": 70, "category_id": reposteria_cat.id, "tenant_id": "cafe-aroma", "popularity": 4, "profitability": "media"},
        {"name": "Brownie", "description": "Brownie de chocolate con nuez", "price": 55, "category_id": reposteria_cat.id, "tenant_id": "cafe-aroma", "popularity": 5, "profitability": "alta"},
    ]

    for prod_data in cafe_products:
        if not db.query(Product).filter(Product.name == prod_data["name"], Product.tenant_id == prod_data["tenant_id"]).first():
            db.add(Product(**prod_data))
    db.commit()

    # BOUTIQUE
    print("   - Boutique Fashion...")
    boutique_categories = [
        {"name": "Mujer", "description": "Ropa para mujer", "tenant_id": "boutique-fashion", "display_order": 1},
        {"name": "Hombre", "description": "Ropa para hombre", "tenant_id": "boutique-fashion", "display_order": 2},
        {"name": "Accesorios", "description": "Bolsas, carteras y más", "tenant_id": "boutique-fashion", "display_order": 3},
    ]

    for cat_data in boutique_categories:
        if not db.query(Category).filter(Category.name == cat_data["name"], Category.tenant_id == cat_data["tenant_id"]).first():
            db.add(Category(**cat_data))
    db.commit()

    mujer_cat = db.query(Category).filter(Category.name == "Mujer", Category.tenant_id == "boutique-fashion").first()
    hombre_cat = db.query(Category).filter(Category.name == "Hombre", Category.tenant_id == "boutique-fashion").first()

    boutique_products = [
        {"name": "Blusa Casual", "description": "Blusa casual manga corta", "price": 350, "category_id": mujer_cat.id, "tenant_id": "boutique-fashion", "popularity": 4, "profitability": "alta"},
        {"name": "Pantalón Mezclilla Mujer", "description": "Pantalón de mezclilla corte skinny", "price": 550, "category_id": mujer_cat.id, "tenant_id": "boutique-fashion", "popularity": 5, "profitability": "media"},
        {"name": "Camisa Formal Hombre", "description": "Camisa formal manga larga", "price": 450, "category_id": hombre_cat.id, "tenant_id": "boutique-fashion", "popularity": 4, "profitability": "alta"},
        {"name": "Pantalón Mezclilla Hombre", "description": "Pantalón mezclilla corte recto", "price": 600, "category_id": hombre_cat.id, "tenant_id": "boutique-fashion", "popularity": 5, "profitability": "media"},
    ]

    for prod_data in boutique_products:
        if not db.query(Product).filter(Product.name == prod_data["name"], Product.tenant_id == prod_data["tenant_id"]).first():
            db.add(Product(**prod_data))
    db.commit()

    print("   ✓ Catálogos creados")


# ==============================================================================
# EJECUTAR
# ==============================================================================

if __name__ == "__main__":
    db = SessionLocal()

    try:
        roles = create_roles(db)
        tenants = create_tenants(db)
        users = create_users(db, roles, tenants)
        create_catalog(db)

        print("\n" + "=" * 80)
        print("✅ DATOS DE PRUEBA CARGADOS EXITOSAMENTE")
        print("=" * 80)
        print("\n🎉 Puedes probar el sistema con 3 tiendas diferentes:")
        print("   1. La Taquería Loca (taqueria-loca)")
        print("   2. Café Aroma (cafe-aroma)")
        print("   3. Boutique Fashion (boutique-fashion)")
        print("\n" + "=" * 80)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        db.rollback()
        raise
    finally:
        db.close()
