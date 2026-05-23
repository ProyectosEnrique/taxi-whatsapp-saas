"""
================================================================================
SEED RICO MAR - Migración del Menú Completo
================================================================================
Script para migrar el menú de Rico Mar Salvatierra (2,291 líneas)
desde RESTAURANT_VOICE_SYSTEM_2.0_COPIA al PROYECTO_B_WHATSAPP_SAAS

Autor: Claude Code
Fecha: 2026-01-20
================================================================================
"""

import sys
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from sqlalchemy.orm import Session
from datetime import datetime
from typing import Dict, List, Any

from src.database import engine, SessionLocal, Base
from src.menu_models import Category, Product
from src.models import Tenant, Role, RoleType, User

# Hash password
from passlib.context import CryptContext
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)


# ==============================================================================
# CONFIGURACIÓN
# ==============================================================================

MENU_JSON_PATH = Path(__file__).parent.parent.parent.parent.parent / "RESTAURANT_VOICE_SYSTEM_2.0_COPIA" / "menu" / "rico_mar_menu_completo.json"

TENANT_DATA = {
    "tenant_id": "rico-mar-salvatierra",
    "name": "Rico Mar Salvatierra",
    "business_name": "Rico Mar Salvatierra S.A. de C.V.",
    "description": "Restaurante especializado en mariscos y comida gourmet con más de 15 años de experiencia",
    "slogan": "Los mejores mariscos de la región",
    "primary_color": "#0284C7",  # Azul océano
    "secondary_color": "#DC2626",  # Rojo coral
    "phone": "4611234567",
    "email": "contacto@ricomarsalvatierra.com",
    "whatsapp_number": "524611234567",
    "settings": {
        "business_hours": {
            "lunes": "07:00-22:00",
            "martes": "07:00-22:00",
            "miercoles": "07:00-22:00",
            "jueves": "07:00-22:00",
            "viernes": "07:00-23:00",
            "sabado": "08:00-23:00",
            "domingo": "08:00-21:00"
        },
        "delivery_fee": 50,
        "min_order_amount": 150,
        "payment_methods": ["cash", "card", "transfer"],
        "currency": "MXN",
        "restaurant_type": "mariscos_gourmet",
        "stations": []  # Se llenará desde el JSON
    }
}

print("=" * 80)
print("MIGRACION MENU RICO MAR SALVATIERRA")
print("=" * 80)
print(f"\nOrigen: {MENU_JSON_PATH}")
print(f"Destino: Base de datos PROYECTO_B\n")


# ==============================================================================
# VERIFICAR ARCHIVO JSON
# ==============================================================================

print("[1/6] Verificando archivo de menú...")
if not MENU_JSON_PATH.exists():
    print(f"   [ERROR] ERROR: No se encontró el archivo {MENU_JSON_PATH}")
    print(f"   Verifica que el proyecto RESTAURANT_VOICE_SYSTEM_2.0_COPIA esté en la ruta correcta")
    sys.exit(1)

print(f"   [OK] Archivo encontrado: {MENU_JSON_PATH.name}")


# ==============================================================================
# LEER MENÚ JSON
# ==============================================================================

print("\n[2/6] Leyendo menú JSON...")
try:
    with open(MENU_JSON_PATH, 'r', encoding='utf-8') as f:
        menu_data = json.load(f)

    total_categories = len(menu_data.get('categorias', []))
    total_products = sum(len(cat.get('productos', [])) for cat in menu_data.get('categorias', []))

    print(f"   [OK] Menú cargado correctamente")
    print(f"   Categorias: {total_categories}")
    print(f"   Productos: {total_products}")
    print(f"   Restaurante: {menu_data.get('restaurant_name')}")
    print(f"   Tipo: {menu_data.get('restaurant_type')}")

    # Actualizar settings con stations del JSON
    TENANT_DATA['settings']['stations'] = menu_data.get('stations', [])

except Exception as e:
    print(f"   [ERROR] ERROR leyendo JSON: {e}")
    sys.exit(1)


# ==============================================================================
# CREAR TABLAS
# ==============================================================================

print("\n[3/6] Creando tablas en base de datos...")
try:
    Base.metadata.drop_all(bind=engine)  # Limpiar BD
    Base.metadata.create_all(bind=engine)
    print("   [OK] Tablas creadas")
except Exception as e:
    print(f"   [ERROR] ERROR creando tablas: {e}")
    sys.exit(1)


# ==============================================================================
# CREAR ROLES
# ==============================================================================

def create_roles(db: Session) -> Dict[str, Role]:
    """Crear roles del sistema"""
    print("\n[4/6] Creando roles...")

    roles_data = [
        {"name": "Super Admin", "role_type": RoleType.SUPER_ADMIN.value, "description": "Administrador global"},
        {"name": "Admin", "role_type": RoleType.ADMIN.value, "description": "Administrador de tenant"},
        {"name": "Staff", "role_type": RoleType.STAFF.value, "description": "Personal del tenant"},
        {"name": "Customer", "role_type": RoleType.CUSTOMER.value, "description": "Cliente"},
    ]

    roles = {}
    for role_data in roles_data:
        role = Role(**role_data)
        db.add(role)
        roles[role_data["role_type"]] = role

    db.commit()
    print(f"   [OK] {len(roles_data)} roles creados")
    return roles


# ==============================================================================
# CREAR TENANT
# ==============================================================================

def create_tenant(db: Session) -> Tenant:
    """Crear tenant Rico Mar"""
    print("\n[5/6] Creando tenant Rico Mar Salvatierra...")

    tenant = Tenant(**TENANT_DATA)
    db.add(tenant)
    db.commit()

    print(f"   [OK] Tenant creado: {tenant.tenant_id}")
    print(f"   Nombre: {tenant.name}")
    print(f"   WhatsApp: {tenant.whatsapp_number}")

    return tenant


# ==============================================================================
# MIGRAR CATEGORÍAS Y PRODUCTOS
# ==============================================================================

def migrate_menu(db: Session, menu_json: Dict[str, Any], tenant_id: str):
    """Migrar categorías y productos desde el JSON"""
    print("\n[6/6] Migrando categorías y productos...")

    categorias_json = menu_json.get('categorias', [])

    total_products = 0
    total_categories = 0

    for cat_data in categorias_json:
        # Crear categoría
        category = Category(
            tenant_id=tenant_id,
            name=cat_data.get('name'),
            description=cat_data.get('description'),
            display_order=cat_data.get('orden', 0),
            is_active=True,
            is_beverage=(cat_data.get('id') == 'bebidas')
        )
        db.add(category)
        db.flush()  # Para obtener el ID

        total_categories += 1

        # Migrar productos de esta categoría
        productos_json = cat_data.get('productos', [])
        products_count = 0

        for prod_data in productos_json:
            # Saltar productos sin precio
            if not prod_data.get('price') or prod_data.get('price') == 0:
                print(f"   [SKIP] {prod_data.get('name')} - Sin precio")
                continue

            # Mapear spicy_level de texto a número
            spicy_map = {
                'ninguno': 0,
                'bajo': 1,
                'medio': 2,
                'alto': 3,
                'muy alto': 4
            }
            spicy_text = prod_data.get('spicy_level', 'ninguno')
            spicy_num = spicy_map.get(spicy_text.lower() if spicy_text else 'ninguno', 0)

            # Extraer tiempo de preparación (convertir "10-15 min" a número)
            prep_time_str = prod_data.get('preparation_time', '15 min')
            prep_time = 15  # Default
            try:
                # Extraer primer número de "10-15 min"
                prep_time = int(prep_time_str.split('-')[0].strip().replace('min', '').strip())
            except:
                prep_time = 15

            # Calcular popularidad basado en tags
            tags = prod_data.get('tags', [])
            popularity = 3  # Default
            if 'popular' in tags:
                popularity = 5
            elif 'premium' in tags:
                popularity = 4

            # Crear producto
            product = Product(
                tenant_id=tenant_id,
                category_id=category.id,
                name=prod_data.get('name'),
                description=prod_data.get('description', ''),
                price=prod_data.get('price', 0),
                is_available=prod_data.get('available', True),

                # Información extra
                ingredients=', '.join(prod_data.get('includes', [])) if prod_data.get('includes') else None,
                spice_level=spicy_num,
                preparation_time_minutes=prep_time,

                # Ingeniería del menú
                popularity=popularity,
                profitability='media',  # Default

                # Meta Commerce
                product_retailer_id=prod_data.get('id'),  # Usar el ID del JSON
                meta_sync_status='pending'
            )
            db.add(product)
            products_count += 1
            total_products += 1

        db.commit()
        print(f"   [OK] {category.name}: {products_count} productos")

    print(f"\n   MIGRACION COMPLETADA:")
    print(f"   {total_categories} categorias creadas")
    print(f"   {total_products} productos migrados")

    return total_categories, total_products


# ==============================================================================
# CREAR USUARIO ADMIN
# ==============================================================================

def create_admin_user(db: Session, tenant_id: str, roles: Dict[str, Role]):
    """Crear usuario administrador para el tenant"""
    print("\n[+] Creando usuario administrador...")

    admin_user = User(
        tenant_id=tenant_id,
        email="admin@ricomarsalvatierra.com",
        name="Administrador Rico Mar",
        password_hash=hash_password("ricomar2026"),  # Cambiar en producción
        phone=TENANT_DATA['phone'],
        is_active=True,
        is_verified=True
    )

    # Asignar rol de admin
    admin_user.roles.append(roles[RoleType.ADMIN.value])

    db.add(admin_user)
    db.commit()

    print(f"   [OK] Usuario admin creado")
    print(f"   Email: admin@ricomarsalvatierra.com")
    print(f"   Password: ricomar2026")
    print(f"   [!] CAMBIAR PASSWORD EN PRODUCCION")


# ==============================================================================
# MAIN
# ==============================================================================

def main():
    """Ejecutar migración completa"""
    db = SessionLocal()

    try:
        # 1. Crear roles
        roles = create_roles(db)

        # 2. Crear tenant
        tenant = create_tenant(db)

        # 3. Migrar menú
        migrate_menu(db, menu_data, tenant.tenant_id)

        # 4. Crear admin
        create_admin_user(db, tenant.tenant_id, roles)

        print("\n" + "=" * 80)
        print("[OK] MIGRACION EXITOSA - RICO MAR SALVATIERRA")
        print("=" * 80)
        print("\nRESUMEN:")
        print(f"   * Tenant ID: {tenant.tenant_id}")
        print(f"   * WhatsApp: {tenant.whatsapp_number}")
        print(f"   * Email: {tenant.email}")
        print(f"   * Estaciones: {len(TENANT_DATA['settings']['stations'])}")
        print("\nSIGUIENTE PASO:")
        print("   1. Configurar keyword en whatsapp-gateway:")
        print(f"      'rico-mar-hola' -> tenant_id='{tenant.tenant_id}'")
        print("   2. Actualizar config/tenants.json en sales-agent-base")
        print("   3. Reiniciar servicios: docker-compose restart")
        print("\nPROBAR:")
        print("   Enviar por WhatsApp: 'rico-mar-hola'")
        print("   Deberias recibir: 'Bienvenido a Rico Mar Salvatierra!'")
        print()

    except Exception as e:
        print(f"\n[ERROR] ERROR en migración: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
