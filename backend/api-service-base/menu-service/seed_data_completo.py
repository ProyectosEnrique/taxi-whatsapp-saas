"""
================================================================================
SEED DATA COMPLETO - 3 Tiendas Multi-Tenant
================================================================================
Script para cargar datos de prueba con:
- 🍽️  RESTAURANTE "El Sabor del Sur" (~70 productos)
- 🍷 VINETERÍA "Vinos y Licores Premium" (~70 productos)
- 💊 FARMACIA "FarmaSalud 24/7" (~70 productos)
================================================================================
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import random
import importlib.util

from src.database import engine, SessionLocal, Base

# Importar Category, Product, Promotion desde src/menu_models.py
from src.menu_models import Category, Product, Promotion

# Importar desde src/models/ (paquete/directorio)
from src.models import User, Role, RoleType, Tenant

# Hash password usando passlib directamente
from passlib.context import CryptContext
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

print("=" * 80)
print("[*] INICIANDO CARGA DE DATOS - 3 TIENDAS COMPLETAS")
print("=" * 80)

# ==============================================================================
# CREAR TABLAS
# ==============================================================================

print("\n[i] 1. Creando tablas...")
Base.metadata.drop_all(bind=engine)  # Limpiar BD
Base.metadata.create_all(bind=engine)
print("   [v] Tablas creadas")


# ==============================================================================
# CREAR ROLES
# ==============================================================================

def create_roles(db: Session):
    print("\n[U] 2. Creando roles...")
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
    print("   [v] 4 roles creados")
    return roles


# ==============================================================================
# CREAR TENANTS
# ==============================================================================

def create_tenants(db: Session):
    print("\n[S] 3. Creando tenants...")

    tenants_data = [
        # 🍽️ RESTAURANTE
        {
            "tenant_id": "restaurante-sabor-sur",
            "name": "El Sabor del Sur",
            "business_name": "Restaurante El Sabor del Sur S.A.",
            "description": "Comida casera y tradicional mexicana con más de 20 años de experiencia",
            "slogan": "El verdadero sabor de México en cada platillo",
            "primary_color": "#DC2626",
            "secondary_color": "#059669",
            "phone": "5551234567",
            "email": "contacto@sabordelsur.com",
            "whatsapp_number": "5251234567",
            "settings": {
                "business_hours": {
                    "lunes": "09:00-22:00",
                    "martes": "09:00-22:00",
                    "miercoles": "09:00-22:00",
                    "jueves": "09:00-23:00",
                    "viernes": "09:00-23:00",
                    "sabado": "09:00-23:00",
                    "domingo": "09:00-21:00"
                },
                "delivery_fee": 35,
                "min_order_amount": 100,
                "accepts_cash": True,
                "accepts_card": True
            }
        },
        # 🍷 VINETERÍA
        {
            "tenant_id": "vineteria-premium",
            "name": "Vinos y Licores Premium",
            "business_name": "Vinetería Premium México S.A.",
            "description": "La mejor selección de vinos, licores y destilados importados y nacionales",
            "slogan": "El placer de un buen vino",
            "primary_color": "#7C2D12",
            "secondary_color": "#DC2626",
            "phone": "5559876543",
            "email": "ventas@vineteriapremium.com",
            "whatsapp_number": "5259876543",
            "settings": {
                "business_hours": {
                    "lunes": "10:00-21:00",
                    "martes": "10:00-21:00",
                    "miercoles": "10:00-21:00",
                    "jueves": "10:00-21:00",
                    "viernes": "10:00-22:00",
                    "sabado": "10:00-22:00",
                    "domingo": "12:00-20:00"
                },
                "delivery_fee": 50,
                "min_order_amount": 200,
                "accepts_cash": True,
                "accepts_card": True,
                "age_restricted": True
            }
        },
        # 💊 FARMACIA
        {
            "tenant_id": "farmasalud-24",
            "name": "FarmaSalud 24/7",
            "business_name": "Farmacias de México S.A. de C.V.",
            "description": "Tu farmacia de confianza, abierta las 24 horas. Medicamentos, salud y belleza",
            "slogan": "Cuidando tu salud día y noche",
            "primary_color": "#0891B2",
            "secondary_color": "#06B6D4",
            "phone": "5555551234",
            "email": "contacto@farmasalud24.com",
            "whatsapp_number": "5255551234",
            "settings": {
                "business_hours": {
                    "lunes": "00:00-23:59",
                    "martes": "00:00-23:59",
                    "miercoles": "00:00-23:59",
                    "jueves": "00:00-23:59",
                    "viernes": "00:00-23:59",
                    "sabado": "00:00-23:59",
                    "domingo": "00:00-23:59"
                },
                "delivery_fee": 25,
                "min_order_amount": 50,
                "accepts_cash": True,
                "accepts_card": True,
                "prescription_required": True
            }
        }
    ]

    tenants = []
    for tenant_data in tenants_data:
        tenant = Tenant(**tenant_data)
        db.add(tenant)
        tenants.append(tenant)

    db.commit()
    print(f"   [v] {len(tenants)} tenants creados")
    return tenants


# ==============================================================================
# PRODUCTOS - RESTAURANTE (67 productos)
# ==============================================================================

RESTAURANTE_MENU = {
    "Entradas y Botanas": [
        {"name": "Guacamole con Totopos", "price": 85, "desc": "Guacamole fresco preparado al momento con aguacate Hass, cebolla, cilantro, chile serrano y limón. Servido con totopos calientes.", "img": "https://images.unsplash.com/photo-1626610403558-f0f4597a1bda", "time": 8, "pop": 5, "profit": "alta"},
        {"name": "Nachos Supremos", "price": 125, "desc": "Totopos gratinados con queso cheddar, frijoles refritos, jalapeños, crema, guacamole y pico de gallo.", "img": "https://images.unsplash.com/photo-1513456852971-30c0b8199d4d", "time": 12, "pop": 5, "profit": "alta"},
        {"name": "Alitas Buffalo", "price": 135, "desc": "10 alitas de pollo fritas bañadas en salsa buffalo picante. Servidas con aderezo ranch y apio.", "img": "https://images.unsplash.com/photo-1608039755401-742074f0548d", "time": 15, "pop": 4, "profit": "media"},
        {"name": "Dedos de Queso", "price": 95, "desc": "6 dedos de queso mozzarella empanizados y fritos. Servidos con salsa marinara.", "img": "https://images.unsplash.com/photo-1531749668029-2db88e4276c7", "time": 10, "pop": 4, "profit": "alta"},
        {"name": "Camarones al Coco", "price": 165, "desc": "Camarones empanizados en coco, fritos dorados. Servidos con salsa agridulce.", "img": "https://images.unsplash.com/photo-1565680018434-b513d5e5fd47", "time": 12, "pop": 3, "profit": "media"},
        {"name": "Aros de Cebolla", "price": 75, "desc": "Aros de cebolla empanizados y fritos hasta quedar crujientes.", "img": "https://images.unsplash.com/photo-1639024471283-03518883512d", "time": 8, "pop": 3, "profit": "alta"},
        {"name": "Champiñones Rellenos", "price": 115, "desc": "Champiñones portobello rellenos de queso crema, ajo y hierbas, horneados.", "img": "https://images.unsplash.com/photo-1599599810769-bcde5a160d32", "time": 15, "pop": 3, "profit": "media"},
    ],

    "Sopas y Cremas": [
        {"name": "Sopa de Tortilla", "price": 75, "desc": "Caldo de tomate con tiras de tortilla frita, aguacate, queso fresco, crema y chile pasilla.", "img": "https://images.unsplash.com/photo-1547592166-23ac45744acd", "time": 10, "pop": 5, "profit": "alta"},
        {"name": "Crema de Champiñones", "price": 85, "desc": "Crema suave de champiñones frescos con un toque de vino blanco y crutones.", "img": "https://images.unsplash.com/photo-1547592166-23ac45744acd", "time": 12, "pop": 4, "profit": "alta"},
        {"name": "Caldo Tlalpeño", "price": 95, "desc": "Caldo de pollo con garbanzos, zanahoria, chipotle, aguacate y queso.", "img": "https://images.unsplash.com/photo-1547592166-23ac45744acd", "time": 15, "pop": 4, "profit": "media"},
        {"name": "Crema de Brócoli", "price": 80, "desc": "Crema de brócoli fresco con queso parmesano y crutones de ajo.", "img": "https://images.unsplash.com/photo-1547592166-23ac45744acd", "time": 10, "pop": 3, "profit": "alta"},
        {"name": "Consomé de Pollo", "price": 65, "desc": "Caldo de pollo casero con verduras, arroz y pollo desmenuzado.", "img": "https://images.unsplash.com/photo-1547592166-23ac45744acd", "time": 8, "pop": 4, "profit": "alta"},
    ],

    "Ensaladas": [
        {"name": "Ensalada César", "price": 95, "desc": "Lechuga romana, crutones, queso parmesano y aderezo césar. Opción de agregar pollo (+$40).", "img": "https://images.unsplash.com/photo-1546793665-c74683f339c1", "time": 8, "pop": 5, "profit": "alta"},
        {"name": "Ensalada Griega", "price": 105, "desc": "Lechuga, tomate, pepino, cebolla morada, aceitunas, queso feta y vinagreta.", "img": "https://images.unsplash.com/photo-1540189549336-e6e99c3679fe", "time": 8, "pop": 4, "profit": "alta"},
        {"name": "Ensalada de Atún", "price": 125, "desc": "Atún fresco sobre cama de lechugas mixtas con aguacate, tomate y vinagreta.", "img": "https://images.unsplash.com/photo-1546069901-ba9599a7e63c", "time": 10, "pop": 4, "profit": "media"},
        {"name": "Ensalada Caprese", "price": 115, "desc": "Tomate, mozzarella fresca, albahaca, aceite de oliva y reducción balsámica.", "img": "https://images.unsplash.com/photo-1592417817098-8fd3d9eb14a5", "time": 8, "pop": 3, "profit": "media"},
        {"name": "Ensalada Tropical", "price": 110, "desc": "Mix de lechugas, piña, mango, nuez caramelizada, queso de cabra y vinagreta de miel.", "img": "https://images.unsplash.com/photo-1512621776951-a57141f2eefd", "time": 10, "pop": 3, "profit": "alta"},
    ],

    "Tacos": [
        {"name": "Tacos al Pastor", "price": 145, "desc": "4 tacos de carne al pastor con piña, cebolla y cilantro en tortilla de maíz.", "img": "https://images.unsplash.com/photo-1565299585323-38d6b0865b47", "time": 12, "pop": 5, "profit": "alta"},
        {"name": "Tacos de Arrachera", "price": 165, "desc": "4 tacos de arrachera asada con guacamole, cebolla asada y salsa.", "img": "https://images.unsplash.com/photo-1599974579688-8dbdd52446db", "time": 15, "pop": 5, "profit": "media"},
        {"name": "Tacos de Pescado", "price": 155, "desc": "4 tacos de pescado empanizado con col morada, pico de gallo y salsa chipotle.", "img": "https://images.unsplash.com/photo-1551504734-5ee1c4a1479b", "time": 12, "pop": 4, "profit": "media"},
        {"name": "Tacos de Carnitas", "price": 140, "desc": "4 tacos de carnitas de cerdo con cebolla, cilantro y limón.", "img": "https://images.unsplash.com/photo-1613514785940-daed07799d9b", "time": 10, "pop": 4, "profit": "alta"},
        {"name": "Tacos Dorados", "price": 125, "desc": "5 tacos dorados de pollo o papa con lechuga, crema, queso y salsa roja.", "img": "https://images.unsplash.com/photo-1599974579688-8dbdd52446db", "time": 12, "pop": 4, "profit": "alta"},
        {"name": "Tacos de Cochinita Pibil", "price": 155, "desc": "4 tacos de cochinita pibil yucateca con cebolla morada encurtida.", "img": "https://images.unsplash.com/photo-1565299585323-38d6b0865b47", "time": 12, "pop": 3, "profit": "media"},
    ],

    "Quesadillas y Sincronizadas": [
        {"name": "Quesadilla de Queso", "price": 85, "desc": "Tortilla de harina con queso gratinado. Servida con guacamole.", "img": "https://images.unsplash.com/photo-1618040996337-56904b7850b9", "time": 8, "pop": 5, "profit": "alta"},
        {"name": "Quesadilla de Champiñones", "price": 105, "desc": "Quesadilla con champiñones salteados, queso y epazote.", "img": "https://images.unsplash.com/photo-1618040996337-56904b7850b9", "time": 10, "pop": 4, "profit": "alta"},
        {"name": "Quesadilla de Arrachera", "price": 145, "desc": "Quesadilla con arrachera asada, queso, cebolla y pimientos.", "img": "https://images.unsplash.com/photo-1618040996337-56904b7850b9", "time": 12, "pop": 4, "profit": "media"},
        {"name": "Sincronizada Hawaiana", "price": 115, "desc": "Tortilla de harina con jamón, queso y piña. Servida dorada y crujiente.", "img": "https://images.unsplash.com/photo-1618040996337-56904b7850b9", "time": 10, "pop": 4, "profit": "alta"},
        {"name": "Quesadilla de Tinga", "price": 125, "desc": "Quesadilla con tinga de pollo, queso y aguacate.", "img": "https://images.unsplash.com/photo-1618040996337-56904b7850b9", "time": 12, "pop": 4, "profit": "alta"},
    ],

    "Platos Fuertes": [
        {"name": "Enchiladas Verdes", "price": 145, "desc": "3 enchiladas de pollo bañadas en salsa verde con crema, queso y cebolla. Incluye arroz y frijoles.", "img": "https://images.unsplash.com/photo-1599918359193-492941e6ad09", "time": 18, "pop": 5, "profit": "alta"},
        {"name": "Mole Poblano", "price": 165, "desc": "Pechuga de pollo bañada en mole poblano tradicional. Incluye arroz y tortillas.", "img": "https://images.unsplash.com/photo-1626200419199-391ae4be7a41", "time": 20, "pop": 4, "profit": "media"},
        {"name": "Chile Relleno", "price": 135, "desc": "Chile poblano relleno de queso o picadillo, capeado y bañado en salsa de tomate.", "img": "https://images.unsplash.com/photo-1626200419199-391ae4be7a41", "time": 20, "pop": 4, "profit": "alta"},
        {"name": "Arrachera a la Parrilla", "price": 245, "desc": "300g de arrachera asada con cebollitas, nopales, frijoles charros y guacamole.", "img": "https://images.unsplash.com/photo-1529692236671-f1f6cf9683ba", "time": 25, "pop": 5, "profit": "media"},
        {"name": "Pechuga Rellena", "price": 185, "desc": "Pechuga de pollo rellena de queso y espinacas, bañada en salsa de champiñones.", "img": "https://images.unsplash.com/photo-1598103442097-8b74394b95c6", "time": 25, "pop": 4, "profit": "alta"},
        {"name": "Filete de Pescado", "price": 195, "desc": "Filete de pescado al mojo de ajo o a la veracruzana. Incluye arroz y verduras.", "img": "https://images.unsplash.com/photo-1534766438357-2b3a1923d249", "time": 20, "pop": 4, "profit": "media"},
        {"name": "Camarones a la Diabla", "price": 215, "desc": "Camarones en salsa de chile seco muy picante. Incluye arroz y ensalada.", "img": "https://images.unsplash.com/photo-1565680018434-b513d5e5fd47", "time": 18, "pop": 3, "profit": "media"},
        {"name": "Milanesa de Res", "price": 155, "desc": "Milanesa de res empanizada y frita. Incluye papas, ensalada y frijoles.", "img": "https://images.unsplash.com/photo-1529692236671-f1f6cf9683ba", "time": 20, "pop": 4, "profit": "alta"},
        {"name": "Chiles en Nogada", "price": 185, "desc": "Chile poblano relleno de picadillo, bañado en salsa de nuez y granada (temporada).", "img": "https://images.unsplash.com/photo-1626200419199-391ae4be7a41", "time": 25, "pop": 3, "profit": "media"},
        {"name": "Pozole Rojo", "price": 125, "desc": "Pozole rojo tradicional con cerdo, maíz cacahuazintle, lechuga, rábano y tostadas.", "img": "https://images.unsplash.com/photo-1626200419199-391ae4be7a41", "time": 15, "pop": 4, "profit": "alta"},
    ],

    "Hamburguesas": [
        {"name": "Hamburguesa Clásica", "price": 125, "desc": "Carne de res 180g, queso americano, lechuga, tomate, cebolla y papas.", "img": "https://images.unsplash.com/photo-1568901346375-23c9450c58cd", "time": 15, "pop": 5, "profit": "alta"},
        {"name": "Hamburguesa BBQ Bacon", "price": 155, "desc": "Carne, tocino, queso cheddar, aros de cebolla, salsa BBQ y papas.", "img": "https://images.unsplash.com/photo-1586190848861-99aa4a171e90", "time": 18, "pop": 5, "profit": "media"},
        {"name": "Hamburguesa Mexicana", "price": 145, "desc": "Carne, queso manchego, jalapeños, guacamole, pico de gallo y papas.", "img": "https://images.unsplash.com/photo-1550547660-d9450f859349", "time": 15, "pop": 4, "profit": "alta"},
        {"name": "Hamburguesa Doble", "price": 175, "desc": "Doble carne 180g c/u, doble queso, lechuga, tomate y papas.", "img": "https://images.unsplash.com/photo-1572802419224-296b0aeee0d9", "time": 18, "pop": 4, "profit": "media"},
    ],

    "Bebidas Frías": [
        {"name": "Agua de Jamaica", "price": 35, "desc": "Agua fresca de flor de jamaica natural.", "img": "https://images.unsplash.com/photo-1556679343-c7306c1976bc", "time": 2, "pop": 5, "profit": "alta"},
        {"name": "Agua de Horchata", "price": 35, "desc": "Agua fresca de horchata de arroz con canela.", "img": "https://images.unsplash.com/photo-1556679343-c7306c1976bc", "time": 2, "pop": 5, "profit": "alta"},
        {"name": "Agua de Limón", "price": 35, "desc": "Agua fresca de limón natural con hierbabuena.", "img": "https://images.unsplash.com/photo-1556679343-c7306c1976bc", "time": 2, "pop": 4, "profit": "alta"},
        {"name": "Limonada Mineral", "price": 45, "desc": "Limonada preparada con agua mineral y hielo.", "img": "https://images.unsplash.com/photo-1523677011781-c91d1bbe2f6c", "time": 3, "pop": 4, "profit": "alta"},
        {"name": "Naranjada", "price": 55, "desc": "Jugo de naranja natural recién exprimido.", "img": "https://images.unsplash.com/photo-1600271886742-f049cd451bba", "time": 3, "pop": 4, "profit": "media"},
        {"name": "Coca-Cola", "price": 30, "desc": "Refresco Coca-Cola 600ml.", "img": "https://images.unsplash.com/photo-1554866585-cd94860890b7", "time": 1, "pop": 5, "profit": "baja"},
        {"name": "Sprite", "price": 30, "desc": "Refresco Sprite 600ml.", "img": "https://images.unsplash.com/photo-1625772299848-391b6a87d7b3", "time": 1, "pop": 4, "profit": "baja"},
        {"name": "Fanta", "price": 30, "desc": "Refresco Fanta 600ml.", "img": "https://images.unsplash.com/photo-1624517452488-04869289c4ca", "time": 1, "pop": 3, "profit": "baja"},
        {"name": "Agua Mineral", "price": 25, "desc": "Agua mineral 600ml.", "img": "https://images.unsplash.com/photo-1559827260-dc66d52bef19", "time": 1, "pop": 4, "profit": "alta"},
        {"name": "Té Helado", "price": 40, "desc": "Té negro helado con limón.", "img": "https://images.unsplash.com/photo-1556679343-c7306c1976bc", "time": 2, "pop": 3, "profit": "alta"},
    ],

    "Bebidas Calientes": [
        {"name": "Café Americano", "price": 35, "desc": "Café americano recién preparado.", "img": "https://images.unsplash.com/photo-1509042239860-f550ce710b93", "time": 3, "pop": 5, "profit": "alta"},
        {"name": "Café con Leche", "price": 45, "desc": "Café con leche caliente espumada.", "img": "https://images.unsplash.com/photo-1461023058943-07fcbe16d735", "time": 4, "pop": 5, "profit": "alta"},
        {"name": "Cappuccino", "price": 50, "desc": "Espresso con leche espumada y canela.", "img": "https://images.unsplash.com/photo-1572442388796-11668a67e53d", "time": 4, "pop": 4, "profit": "alta"},
        {"name": "Chocolate Caliente", "price": 50, "desc": "Chocolate abuelita con leche caliente.", "img": "https://images.unsplash.com/photo-1542990253-0d0f5be5f0ed", "time": 5, "pop": 4, "profit": "alta"},
        {"name": "Té de Manzanilla", "price": 30, "desc": "Té de manzanilla natural.", "img": "https://images.unsplash.com/photo-1597318185940-69e1c8034b49", "time": 3, "pop": 3, "profit": "alta"},
    ],

    "Postres": [
        {"name": "Pastel de Chocolate", "price": 75, "desc": "Rebanada de pastel de chocolate húmedo con betún.", "img": "https://images.unsplash.com/photo-1578985545062-69928b1d9587", "time": 5, "pop": 5, "profit": "alta"},
        {"name": "Flan Napolitano", "price": 65, "desc": "Flan de huevo con caramelo.", "img": "https://images.unsplash.com/photo-1587048124340-9fa21f2389af", "time": 5, "pop": 5, "profit": "alta"},
        {"name": "Churros con Chocolate", "price": 85, "desc": "6 churros recién hechos con chocolate caliente para remojar.", "img": "https://images.unsplash.com/photo-1568471173238-64687c45e0d4", "time": 8, "pop": 4, "profit": "alta"},
        {"name": "Pay de Limón", "price": 70, "desc": "Pay de limón con merengue italiano.", "img": "https://images.unsplash.com/photo-1565958011703-44f9829ba187", "time": 5, "pop": 4, "profit": "alta"},
        {"name": "Helado (2 bolas)", "price": 60, "desc": "2 bolas de helado a elegir: vainilla, chocolate o fresa.", "img": "https://images.unsplash.com/photo-1563805042-7684c019e1cb", "time": 3, "pop": 4, "profit": "media"},
        {"name": "Arroz con Leche", "price": 55, "desc": "Arroz con leche casero con canela y pasas.", "img": "https://images.unsplash.com/photo-1587048124340-9fa21f2389af", "time": 5, "pop": 3, "profit": "alta"},
        {"name": "Gelatina", "price": 45, "desc": "Gelatina de leche o agua de sabor.", "img": "https://images.unsplash.com/photo-1587048124340-9fa21f2389af", "time": 2, "pop": 3, "profit": "alta"},
    ],
}


# ==============================================================================
# PRODUCTOS - VINETERÍA (70 productos)
# ==============================================================================

VINETERIA_MENU = {
    "Vinos Tintos Mexicanos": [
        {"name": "L.A. Cetto Cabernet Sauvignon", "price": 285, "desc": "Vino tinto seco del Valle de Guadalupe. Notas a frutas rojas y roble. 750ml.", "img": "https://images.unsplash.com/photo-1510812431401-41d2bd2722f3", "time": 1, "pop": 5, "profit": "media"},
        {"name": "Casa Madero Merlot", "price": 320, "desc": "Vino tinto elegante con cuerpo medio. Notas a ciruela y chocolate. 750ml.", "img": "https://images.unsplash.com/photo-1510812431401-41d2bd2722f3", "time": 1, "pop": 4, "profit": "media"},
        {"name": "Santo Tomás Cabernet", "price": 295, "desc": "Vino tinto robusto con taninos suaves y final prolongado. 750ml.", "img": "https://images.unsplash.com/photo-1510812431401-41d2bd2722f3", "time": 1, "pop": 4, "profit": "media"},
        {"name": "Monte Xanic Calixa", "price": 450, "desc": "Blend premium de tintos mexicanos. Crianza en barrica. 750ml.", "img": "https://images.unsplash.com/photo-1510812431401-41d2bd2722f3", "time": 1, "pop": 3, "profit": "alta"},
        {"name": "Adobe Guadalupe Arcángel", "price": 850, "desc": "Vino de autor del Valle de Guadalupe. Edición limitada. 750ml.", "img": "https://images.unsplash.com/photo-1510812431401-41d2bd2722f3", "time": 1, "pop": 2, "profit": "alta"},
    ],

    "Vinos Tintos Importados": [
        {"name": "Casillero del Diablo Cabernet", "price": 320, "desc": "Vino chileno con notas a frutas negras y especias. 750ml.", "img": "https://images.unsplash.com/photo-1474722883778-792e7990302f", "time": 1, "pop": 5, "profit": "media"},
        {"name": "Trivento Malbec Reserve", "price": 385, "desc": "Malbec argentino intenso con taninos suaves. 750ml.", "img": "https://images.unsplash.com/photo-1474722883778-792e7990302f", "time": 1, "pop": 5, "profit": "media"},
        {"name": "Marqués de Riscal Reserva", "price": 520, "desc": "Rioja español de crianza tradicional. Elegante y complejo. 750ml.", "img": "https://images.unsplash.com/photo-1474722883778-792e7990302f", "time": 1, "pop": 4, "profit": "alta"},
        {"name": "Robert Mondavi Cabernet", "price": 680, "desc": "Vino californiano premium con estructura compleja. 750ml.", "img": "https://images.unsplash.com/photo-1474722883778-792e7990302f", "time": 1, "pop": 3, "profit": "alta"},
        {"name": "Château Margaux", "price": 3500, "desc": "Gran vino francés de Bordeaux. Cosecha premium. 750ml.", "img": "https://images.unsplash.com/photo-1474722883778-792e7990302f", "time": 1, "pop": 1, "profit": "alta"},
    ],

    "Vinos Blancos": [
        {"name": "L.A. Cetto Chardonnay", "price": 265, "desc": "Blanco mexicano fresco con notas cítricas y tropicales. 750ml.", "img": "https://images.unsplash.com/photo-1547595628-c61a29f496f0", "time": 1, "pop": 4, "profit": "media"},
        {"name": "Casa Madero Chenin Blanc", "price": 285, "desc": "Blanco aromático con buena acidez. Perfecto para mariscos. 750ml.", "img": "https://images.unsplash.com/photo-1547595628-c61a29f496f0", "time": 1, "pop": 4, "profit": "media"},
        {"name": "Casillero del Diablo Sauvignon", "price": 295, "desc": "Sauvignon Blanc chileno refrescante. Notas herbales. 750ml.", "img": "https://images.unsplash.com/photo-1547595628-c61a29f496f0", "time": 1, "pop": 5, "profit": "media"},
        {"name": "Chablis Premier Cru", "price": 850, "desc": "Vino blanco francés mineral y elegante. 750ml.", "img": "https://images.unsplash.com/photo-1547595628-c61a29f496f0", "time": 1, "pop": 2, "profit": "alta"},
        {"name": "Cloudy Bay Sauvignon Blanc", "price": 720, "desc": "Icónico blanco neozelandés. Fresco y aromático. 750ml.", "img": "https://images.unsplash.com/photo-1547595628-c61a29f496f0", "time": 1, "pop": 2, "profit": "alta"},
    ],

    "Vinos Rosados y Espumosos": [
        {"name": "L.A. Cetto Rosado", "price": 245, "desc": "Vino rosado mexicano ligero y afrutado. 750ml.", "img": "https://images.unsplash.com/photo-1584916201218-f4242ceb4809", "time": 1, "pop": 4, "profit": "media"},
        {"name": "Freixenet Rosé", "price": 285, "desc": "Espumoso rosado español tipo cava. 750ml.", "img": "https://images.unsplash.com/photo-1584916201218-f4242ceb4809", "time": 1, "pop": 5, "profit": "media"},
        {"name": "Moët & Chandon Rosé", "price": 1450, "desc": "Champagne rosé francés. Elegancia y finura. 750ml.", "img": "https://images.unsplash.com/photo-1584916201218-f4242ceb4809", "time": 1, "pop": 3, "profit": "alta"},
        {"name": "Prosecco Zonin", "price": 320, "desc": "Espumoso italiano ligero y afrutado. 750ml.", "img": "https://images.unsplash.com/photo-1584916201218-f4242ceb4809", "time": 1, "pop": 5, "profit": "media"},
        {"name": "Veuve Clicquot Brut", "price": 1650, "desc": "Champagne francés icónico. Etiqueta amarilla. 750ml.", "img": "https://images.unsplash.com/photo-1584916201218-f4242ceb4809", "time": 1, "pop": 3, "profit": "alta"},
    ],

    "Tequilas Blancos": [
        {"name": "Don Julio Blanco", "price": 850, "desc": "Tequila 100% agave. Suave y cristalino. 750ml.", "img": "https://images.unsplash.com/photo-1601924638867-e1da1c421e8d", "time": 1, "pop": 5, "profit": "media"},
        {"name": "Patrón Silver", "price": 1050, "desc": "Tequila ultra premium. Notas a agave fresco. 750ml.", "img": "https://images.unsplash.com/photo-1601924638867-e1da1c421e8d", "time": 1, "pop": 5, "profit": "alta"},
        {"name": "Clase Azul Plata", "price": 2850, "desc": "Tequila artesanal en botella pintada a mano. 750ml.", "img": "https://images.unsplash.com/photo-1601924638867-e1da1c421e8d", "time": 1, "pop": 3, "profit": "alta"},
        {"name": "Herradura Plata", "price": 680, "desc": "Tequila tradicional reposado 45 días. 750ml.", "img": "https://images.unsplash.com/photo-1601924638867-e1da1c421e8d", "time": 1, "pop": 4, "profit": "media"},
        {"name": "Espolón Blanco", "price": 420, "desc": "Tequila joven con carácter. Excelente calidad-precio. 750ml.", "img": "https://images.unsplash.com/photo-1601924638867-e1da1c421e8d", "time": 1, "pop": 4, "profit": "media"},
    ],

    "Tequilas Reposados y Añejos": [
        {"name": "Don Julio Reposado", "price": 950, "desc": "Reposado 8 meses en barrica. Suave y complejo. 750ml.", "img": "https://images.unsplash.com/photo-1582994990170-7e4b2d754b03", "time": 1, "pop": 5, "profit": "media"},
        {"name": "Don Julio Añejo", "price": 1250, "desc": "Añejo 18 meses. Notas a caramelo y vainilla. 750ml.", "img": "https://images.unsplash.com/photo-1582994990170-7e4b2d754b03", "time": 1, "pop": 4, "profit": "alta"},
        {"name": "Patrón Añejo", "price": 1450, "desc": "Añejo en barricas de roble. Sabor robusto. 750ml.", "img": "https://images.unsplash.com/photo-1582994990170-7e4b2d754b03", "time": 1, "pop": 4, "profit": "alta"},
        {"name": "Clase Azul Reposado", "price": 3500, "desc": "Tequila artesanal reposado. Botella icónica. 750ml.", "img": "https://images.unsplash.com/photo-1582994990170-7e4b2d754b03", "time": 1, "pop": 3, "profit": "alta"},
        {"name": "Herradura Añejo", "price": 980, "desc": "Añejo 25 meses. Sabor intenso a roble. 750ml.", "img": "https://images.unsplash.com/photo-1582994990170-7e4b2d754b03", "time": 1, "pop": 4, "profit": "media"},
    ],

    "Mezcales": [
        {"name": "Mezcal Unión Uno", "price": 650, "desc": "Mezcal joven de Oaxaca. Ahumado suave. 750ml.", "img": "https://images.unsplash.com/photo-1596040326284-d7b4ef378be9", "time": 1, "pop": 4, "profit": "media"},
        {"name": "Mezcal 400 Conejos", "price": 480, "desc": "Mezcal artesanal oaxaqueño. Sabor tradicional. 750ml.", "img": "https://images.unsplash.com/photo-1596040326284-d7b4ef378be9", "time": 1, "pop": 4, "profit": "media"},
        {"name": "Del Maguey Vida", "price": 850, "desc": "Mezcal orgánico de agave espadín. 750ml.", "img": "https://images.unsplash.com/photo-1596040326284-d7b4ef378be9", "time": 1, "pop": 3, "profit": "alta"},
        {"name": "Montelobos Joven", "price": 720, "desc": "Mezcal equilibrado con notas cítricas. 750ml.", "img": "https://images.unsplash.com/photo-1596040326284-d7b4ef378be9", "time": 1, "pop": 3, "profit": "media"},
        {"name": "Mezcal Koch Espadín", "price": 1450, "desc": "Mezcal premium de lote limitado. 750ml.", "img": "https://images.unsplash.com/photo-1596040326284-d7b4ef378be9", "time": 1, "pop": 2, "profit": "alta"},
    ],

    "Whisky": [
        {"name": "Johnnie Walker Red Label", "price": 450, "desc": "Whisky escocés blended. Sabor intenso. 750ml.", "img": "https://images.unsplash.com/photo-1527281400-e8eff224f0c4", "time": 1, "pop": 5, "profit": "media"},
        {"name": "Johnnie Walker Black Label", "price": 750, "desc": "Whisky escocés 12 años. Suave y ahumado. 750ml.", "img": "https://images.unsplash.com/photo-1527281400-e8eff224f0c4", "time": 1, "pop": 5, "profit": "media"},
        {"name": "Jack Daniel's", "price": 680, "desc": "Whiskey Tennessee. Filtrado con carbón de maple. 750ml.", "img": "https://images.unsplash.com/photo-1527281400-e8eff224f0c4", "time": 1, "pop": 5, "profit": "media"},
        {"name": "Glenfiddich 12 años", "price": 980, "desc": "Single malt escocés. Notas a pera y roble. 750ml.", "img": "https://images.unsplash.com/photo-1527281400-e8eff224f0c4", "time": 1, "pop": 4, "profit": "alta"},
        {"name": "Macallan 12 años", "price": 1850, "desc": "Single malt premium. Madurado en jerez. 750ml.", "img": "https://images.unsplash.com/photo-1527281400-e8eff224f0c4", "time": 1, "pop": 3, "profit": "alta"},
        {"name": "Chivas Regal 12 años", "price": 850, "desc": "Whisky escocés suave y refinado. 750ml.", "img": "https://images.unsplash.com/photo-1527281400-e8eff224f0c4", "time": 1, "pop": 4, "profit": "media"},
    ],

    "Ron": [
        {"name": "Bacardí Blanco", "price": 285, "desc": "Ron blanco ligero. Ideal para cocteles. 750ml.", "img": "https://images.unsplash.com/photo-1514362545857-3bc16c4c7d1b", "time": 1, "pop": 5, "profit": "media"},
        {"name": "Bacardí Añejo", "price": 380, "desc": "Ron dorado suave con toques de vainilla. 750ml.", "img": "https://images.unsplash.com/photo-1514362545857-3bc16c4c7d1b", "time": 1, "pop": 4, "profit": "media"},
        {"name": "Havana Club 7 años", "price": 520, "desc": "Ron cubano añejado. Sabor complejo. 750ml.", "img": "https://images.unsplash.com/photo-1514362545857-3bc16c4c7d1b", "time": 1, "pop": 4, "profit": "media"},
        {"name": "Zacapa 23", "price": 1250, "desc": "Ron guatemalteco premium. Sistema solera. 750ml.", "img": "https://images.unsplash.com/photo-1514362545857-3bc16c4c7d1b", "time": 1, "pop": 3, "profit": "alta"},
        {"name": "Captain Morgan Spiced", "price": 350, "desc": "Ron especiado con vainilla y especias. 750ml.", "img": "https://images.unsplash.com/photo-1514362545857-3bc16c4c7d1b", "time": 1, "pop": 4, "profit": "media"},
    ],

    "Vodka y Gin": [
        {"name": "Smirnoff Vodka", "price": 320, "desc": "Vodka triple destilado. Suave y limpio. 750ml.", "img": "https://images.unsplash.com/photo-1528823872057-9c018a7a7553", "time": 1, "pop": 5, "profit": "media"},
        {"name": "Absolut Vodka", "price": 480, "desc": "Vodka sueco premium. Cristalino. 750ml.", "img": "https://images.unsplash.com/photo-1528823872057-9c018a7a7553", "time": 1, "pop": 5, "profit": "media"},
        {"name": "Grey Goose", "price": 980, "desc": "Vodka francés ultra premium. 750ml.", "img": "https://images.unsplash.com/photo-1528823872057-9c018a7a7553", "time": 1, "pop": 3, "profit": "alta"},
        {"name": "Tanqueray Gin", "price": 550, "desc": "Gin londinense seco. Notas a enebro. 750ml.", "img": "https://images.unsplash.com/photo-1528823872057-9c018a7a7553", "time": 1, "pop": 4, "profit": "media"},
        {"name": "Bombay Sapphire", "price": 620, "desc": "Gin premium con 10 botánicos. 750ml.", "img": "https://images.unsplash.com/photo-1528823872057-9c018a7a7553", "time": 1, "pop": 4, "profit": "media"},
        {"name": "Hendrick's Gin", "price": 850, "desc": "Gin escocés con pepino y rosa. Único. 750ml.", "img": "https://images.unsplash.com/photo-1528823872057-9c018a7a7553", "time": 1, "pop": 3, "profit": "alta"},
    ],

    "Licores y Cremas": [
        {"name": "Baileys Irish Cream", "price": 480, "desc": "Crema irlandesa de whiskey. 750ml.", "img": "https://images.unsplash.com/photo-1569529465841-dfecdab7503b", "time": 1, "pop": 5, "profit": "media"},
        {"name": "Kahlúa", "price": 380, "desc": "Licor de café mexicano. 750ml.", "img": "https://images.unsplash.com/photo-1569529465841-dfecdab7503b", "time": 1, "pop": 5, "profit": "media"},
        {"name": "Jägermeister", "price": 520, "desc": "Licor alemán de hierbas. 56 botánicos. 750ml.", "img": "https://images.unsplash.com/photo-1569529465841-dfecdab7503b", "time": 1, "pop": 4, "profit": "media"},
        {"name": "Amaretto Disaronno", "price": 580, "desc": "Licor italiano de almendra. 750ml.", "img": "https://images.unsplash.com/photo-1569529465841-dfecdab7503b", "time": 1, "pop": 3, "profit": "media"},
        {"name": "Cointreau", "price": 680, "desc": "Licor francés de naranja triple sec. 750ml.", "img": "https://images.unsplash.com/photo-1569529465841-dfecdab7503b", "time": 1, "pop": 3, "profit": "alta"},
        {"name": "Grand Marnier", "price": 850, "desc": "Licor de naranja con cognac. 750ml.", "img": "https://images.unsplash.com/photo-1569529465841-dfecdab7503b", "time": 1, "pop": 2, "profit": "alta"},
    ],

    "Cervezas Artesanales": [
        {"name": "Minerva IPA", "price": 55, "desc": "Cerveza artesanal mexicana India Pale Ale. 355ml.", "img": "https://images.unsplash.com/photo-1535958636474-b021ee887b13", "time": 1, "pop": 5, "profit": "media"},
        {"name": "Cucapá Clásica", "price": 50, "desc": "Cerveza artesanal mexicana estilo amber. 355ml.", "img": "https://images.unsplash.com/photo-1535958636474-b021ee887b13", "time": 1, "pop": 4, "profit": "media"},
        {"name": "Primus Lager", "price": 50, "desc": "Cerveza artesanal clara mexicana. 355ml.", "img": "https://images.unsplash.com/photo-1535958636474-b021ee887b13", "time": 1, "pop": 4, "profit": "media"},
        {"name": "Wendlandt Pale Ale", "price": 60, "desc": "Cerveza artesanal de Ensenada. 355ml.", "img": "https://images.unsplash.com/photo-1535958636474-b021ee887b13", "time": 1, "pop": 3, "profit": "media"},
        {"name": "Colima Cayaco", "price": 55, "desc": "Cerveza artesanal estilo kolsch. 355ml.", "img": "https://images.unsplash.com/photo-1535958636474-b021ee887b13", "time": 1, "pop": 3, "profit": "media"},
    ],

    "Cervezas Importadas": [
        {"name": "Corona Extra", "price": 35, "desc": "Cerveza clara mexicana. 355ml.", "img": "https://images.unsplash.com/photo-1608270586620-248524c67de9", "time": 1, "pop": 5, "profit": "baja"},
        {"name": "Modelo Especial", "price": 35, "desc": "Cerveza clara pilsner mexicana. 355ml.", "img": "https://images.unsplash.com/photo-1608270586620-248524c67de9", "time": 1, "pop": 5, "profit": "baja"},
        {"name": "Heineken", "price": 40, "desc": "Cerveza holandesa lager. 355ml.", "img": "https://images.unsplash.com/photo-1608270586620-248524c67de9", "time": 1, "pop": 5, "profit": "baja"},
        {"name": "Stella Artois", "price": 45, "desc": "Cerveza belga premium. 330ml.", "img": "https://images.unsplash.com/photo-1608270586620-248524c67de9", "time": 1, "pop": 4, "profit": "media"},
        {"name": "Guinness Stout", "price": 65, "desc": "Cerveza irlandesa oscura cremosa. 330ml.", "img": "https://images.unsplash.com/photo-1608270586620-248524c67de9", "time": 1, "pop": 3, "profit": "media"},
    ],
}


# ==============================================================================
# PRODUCTOS - FARMACIA (70 productos)
# ==============================================================================

FARMACIA_MENU = {
    "Analgésicos y Antiinflamatorios": [
        {"name": "Paracetamol 500mg", "price": 45, "desc": "Caja con 20 tabletas. Analgésico y antipirético.", "img": "https://images.unsplash.com/photo-1584308666744-24d5c474f2ae", "time": 1, "pop": 5, "profit": "alta"},
        {"name": "Ibuprofeno 400mg", "price": 65, "desc": "Caja con 20 cápsulas. Antiinflamatorio no esteroideo.", "img": "https://images.unsplash.com/photo-1584308666744-24d5c474f2ae", "time": 1, "pop": 5, "profit": "alta"},
        {"name": "Aspirina 500mg", "price": 55, "desc": "Caja con 20 tabletas. Analgésico y antiagregante plaquetario.", "img": "https://images.unsplash.com/photo-1584308666744-24d5c474f2ae", "time": 1, "pop": 4, "profit": "alta"},
        {"name": "Naproxeno Sódico 220mg", "price": 85, "desc": "Caja con 20 tabletas. Antiinflamatorio de acción prolongada.", "img": "https://images.unsplash.com/photo-1584308666744-24d5c474f2ae", "time": 1, "pop": 4, "profit": "alta"},
        {"name": "Diclofenaco Gel", "price": 120, "desc": "Tubo 60g. Gel antiinflamatorio tópico para dolores musculares.", "img": "https://images.unsplash.com/photo-1584308666744-24d5c474f2ae", "time": 1, "pop": 4, "profit": "media"},
        {"name": "Ketorolaco 10mg", "price": 95, "desc": "Caja con 10 tabletas. Analgésico potente de corta duración.", "img": "https://images.unsplash.com/photo-1584308666744-24d5c474f2ae", "time": 1, "pop": 3, "profit": "alta"},
    ],

    "Antigripales y Antihistamínicos": [
        {"name": "Tabcin", "price": 85, "desc": "Caja con 12 tabletas. Alivio de síntomas de gripe y resfriado.", "img": "https://images.unsplash.com/photo-1587854692152-cbe660dbde88", "time": 1, "pop": 5, "profit": "alta"},
        {"name": "Desenfriol-D", "price": 95, "desc": "Caja con 12 cápsulas. Descongestivo nasal y antigripal.", "img": "https://images.unsplash.com/photo-1587854692152-cbe660dbde88", "time": 1, "pop": 5, "profit": "alta"},
        {"name": "Loratadina 10mg", "price": 65, "desc": "Caja con 10 tabletas. Antihistamínico para alergias.", "img": "https://images.unsplash.com/photo-1587854692152-cbe660dbde88", "time": 1, "pop": 5, "profit": "alta"},
        {"name": "Cetirizina 10mg", "price": 75, "desc": "Caja con 10 tabletas. Antihistamínico no sedante.", "img": "https://images.unsplash.com/photo-1587854692152-cbe660dbde88", "time": 1, "pop": 4, "profit": "alta"},
        {"name": "Clorfenamina 4mg", "price": 45, "desc": "Caja con 20 tabletas. Antihistamínico clásico.", "img": "https://images.unsplash.com/photo-1587854692152-cbe660dbde88", "time": 1, "pop": 4, "profit": "alta"},
        {"name": "Vitamina C 1000mg", "price": 125, "desc": "Frasco con 30 tabletas efervescentes. Refuerza defensas.", "img": "https://images.unsplash.com/photo-1587854692152-cbe660dbde88", "time": 1, "pop": 4, "profit": "media"},
    ],

    "Digestivos y Gastroenterología": [
        {"name": "Omeprazol 20mg", "price": 85, "desc": "Caja con 14 cápsulas. Inhibidor de bomba de protones.", "img": "https://images.unsplash.com/photo-1587854692152-cbe660dbde88", "time": 1, "pop": 5, "profit": "alta"},
        {"name": "Ranitidina 150mg", "price": 75, "desc": "Caja con 20 tabletas. Antiácido para gastritis y reflujo.", "img": "https://images.unsplash.com/photo-1587854692152-cbe660dbde88", "time": 1, "pop": 4, "profit": "alta"},
        {"name": "Sal de Uvas Picot", "price": 35, "desc": "Sobre individual. Antiácido efervescente.", "img": "https://images.unsplash.com/photo-1587854692152-cbe660dbde88", "time": 1, "pop": 5, "profit": "alta"},
        {"name": "Pepto-Bismol", "price": 145, "desc": "Frasco 240ml. Para diarrea, náuseas y malestar estomacal.", "img": "https://images.unsplash.com/photo-1587854692152-cbe660dbde88", "time": 1, "pop": 4, "profit": "media"},
        {"name": "Loperamida 2mg", "price": 55, "desc": "Caja con 6 cápsulas. Antidiarreico de acción rápida.", "img": "https://images.unsplash.com/photo-1587854692152-cbe660dbde88", "time": 1, "pop": 4, "profit": "alta"},
        {"name": "Probióticos Enterogermina", "price": 185, "desc": "Caja con 10 frascos. Reestablece flora intestinal.", "img": "https://images.unsplash.com/photo-1587854692152-cbe660dbde88", "time": 1, "pop": 3, "profit": "media"},
        {"name": "Melox Plus", "price": 95, "desc": "Frasco 360ml. Antiácido en suspensión con simeticona.", "img": "https://images.unsplash.com/photo-1587854692152-cbe660dbde88", "time": 1, "pop": 4, "profit": "media"},
    ],

    "Antibióticos y Antimicrobianos": [
        {"name": "Amoxicilina 500mg", "price": 145, "desc": "Caja con 12 cápsulas. Antibiótico de amplio espectro. REQUIERE RECETA.", "img": "https://images.unsplash.com/photo-1471864190281-a93a3070b6de", "time": 1, "pop": 5, "profit": "media"},
        {"name": "Azitromicina 500mg", "price": 185, "desc": "Caja con 3 tabletas. Antibiótico macrólido. REQUIERE RECETA.", "img": "https://images.unsplash.com/photo-1471864190281-a93a3070b6de", "time": 1, "pop": 4, "profit": "media"},
        {"name": "Ciprofloxacino 500mg", "price": 165, "desc": "Caja con 6 tabletas. Antibiótico quinolona. REQUIERE RECETA.", "img": "https://images.unsplash.com/photo-1471864190281-a93a3070b6de", "time": 1, "pop": 3, "profit": "media"},
        {"name": "Trimetoprim con Sulfa", "price": 125, "desc": "Caja con 14 tabletas. Para infecciones urinarias. REQUIERE RECETA.", "img": "https://images.unsplash.com/photo-1471864190281-a93a3070b6de", "time": 1, "pop": 4, "profit": "alta"},
    ],

    "Vitaminas y Suplementos": [
        {"name": "Centrum Adultos", "price": 285, "desc": "Frasco con 30 tabletas. Multivitamínico completo diario.", "img": "https://images.unsplash.com/photo-1607619056574-7b8d3ee536b2", "time": 1, "pop": 5, "profit": "media"},
        {"name": "Vitamina D3 2000 UI", "price": 195, "desc": "Frasco con 30 cápsulas. Esencial para huesos y sistema inmune.", "img": "https://images.unsplash.com/photo-1607619056574-7b8d3ee536b2", "time": 1, "pop": 4, "profit": "media"},
        {"name": "Omega 3", "price": 245, "desc": "Frasco con 60 cápsulas. Aceite de pescado para salud cardiovascular.", "img": "https://images.unsplash.com/photo-1607619056574-7b8d3ee536b2", "time": 1, "pop": 4, "profit": "media"},
        {"name": "Calcio + Vitamina D", "price": 215, "desc": "Frasco con 60 tabletas. Para salud ósea.", "img": "https://images.unsplash.com/photo-1607619056574-7b8d3ee536b2", "time": 1, "pop": 4, "profit": "media"},
        {"name": "Complejo B", "price": 145, "desc": "Frasco con 30 tabletas. Para energía y sistema nervioso.", "img": "https://images.unsplash.com/photo-1607619056574-7b8d3ee536b2", "time": 1, "pop": 4, "profit": "alta"},
        {"name": "Colágeno Hidrolizado", "price": 385, "desc": "Bote 300g. Para piel, cabello, uñas y articulaciones.", "img": "https://images.unsplash.com/photo-1607619056574-7b8d3ee536b2", "time": 1, "pop": 3, "profit": "media"},
        {"name": "Hierro 65mg", "price": 165, "desc": "Frasco con 30 tabletas. Para anemia y deficiencia de hierro.", "img": "https://images.unsplash.com/photo-1607619056574-7b8d3ee536b2", "time": 1, "pop": 3, "profit": "alta"},
    ],

    "Cuidado de la Piel": [
        {"name": "Crema Nivea Lata Azul", "price": 85, "desc": "Lata 200ml. Crema humectante clásica para todo el cuerpo.", "img": "https://images.unsplash.com/photo-1556228578-8c89e6adf883", "time": 1, "pop": 5, "profit": "media"},
        {"name": "Bloqueador Solar FPS 50", "price": 245, "desc": "Frasco 120ml. Protección UVA/UVB. Resistente al agua.", "img": "https://images.unsplash.com/photo-1556228578-8c89e6adf883", "time": 1, "pop": 5, "profit": "media"},
        {"name": "Crema Facial Antiarrugas", "price": 385, "desc": "Crema 50ml con retinol y vitamina E. Uso nocturno.", "img": "https://images.unsplash.com/photo-1556228578-8c89e6adf883", "time": 1, "pop": 4, "profit": "alta"},
        {"name": "Crema para Manos", "price": 65, "desc": "Tubo 75ml. Hidratación intensiva.", "img": "https://images.unsplash.com/photo-1556228578-8c89e6adf883", "time": 1, "pop": 4, "profit": "alta"},
        {"name": "Gel Limpiador Facial", "price": 145, "desc": "Frasco 200ml. Para rostro con pH balanceado.", "img": "https://images.unsplash.com/photo-1556228578-8c89e6adf883", "time": 1, "pop": 4, "profit": "media"},
        {"name": "Gel de Sábila Pura", "price": 95, "desc": "Frasco 250ml. Hidratante natural para piel y cabello.", "img": "https://images.unsplash.com/photo-1556228578-8c89e6adf883", "time": 1, "pop": 4, "profit": "alta"},
        {"name": "Bálsamo Labial", "price": 45, "desc": "Tubo 4.5g. Hidratación y protección para labios.", "img": "https://images.unsplash.com/photo-1556228578-8c89e6adf883", "time": 1, "pop": 3, "profit": "alta"},
    ],

    "Higiene Personal": [
        {"name": "Jabón Líquido Antibacterial", "price": 65, "desc": "Frasco 500ml con dosificador. Elimina 99.9% bacterias.", "img": "https://images.unsplash.com/photo-1610806021308-8667c754cb0f", "time": 1, "pop": 5, "profit": "media"},
        {"name": "Shampoo Anticaspa", "price": 125, "desc": "Frasco 400ml. Controla caspa y picazón.", "img": "https://images.unsplash.com/photo-1610806021308-8667c754cb0f", "time": 1, "pop": 4, "profit": "media"},
        {"name": "Desodorante Roll-on", "price": 55, "desc": "Roll-on 50ml. Protección 48 horas.", "img": "https://images.unsplash.com/photo-1610806021308-8667c754cb0f", "time": 1, "pop": 5, "profit": "media"},
        {"name": "Pasta Dental con Flúor", "price": 45, "desc": "Tubo 150ml. Protección contra caries.", "img": "https://images.unsplash.com/photo-1610806021308-8667c754cb0f", "time": 1, "pop": 5, "profit": "media"},
        {"name": "Enjuague Bucal", "price": 85, "desc": "Frasco 500ml. Protección total 12 horas.", "img": "https://images.unsplash.com/photo-1610806021308-8667c754cb0f", "time": 1, "pop": 4, "profit": "media"},
        {"name": "Gel Antibacterial", "price": 55, "desc": "Frasco 250ml. Elimina 99.9% virus y bacterias.", "img": "https://images.unsplash.com/photo-1610806021308-8667c754cb0f", "time": 1, "pop": 5, "profit": "alta"},
        {"name": "Toallas Húmedas Antibacteriales", "price": 35, "desc": "Paquete 10 piezas. Para manos y superficies.", "img": "https://images.unsplash.com/photo-1610806021308-8667c754cb0f", "time": 1, "pop": 4, "profit": "alta"},
        {"name": "Hilo Dental", "price": 35, "desc": "Rollo 50m. Limpieza interdental.", "img": "https://images.unsplash.com/photo-1610806021308-8667c754cb0f", "time": 1, "pop": 3, "profit": "alta"},
    ],

    "Primeros Auxilios": [
        {"name": "Curitas Banda Aid", "price": 45, "desc": "Caja con 20 piezas surtidas. Adhesivas flexibles.", "img": "https://images.unsplash.com/photo-1603398938378-e54eab446dde", "time": 1, "pop": 5, "profit": "alta"},
        {"name": "Gasas Estériles", "price": 35, "desc": "Paquete con 10 gasas 10x10cm. Estériles.", "img": "https://images.unsplash.com/photo-1603398938378-e54eab446dde", "time": 1, "pop": 4, "profit": "alta"},
        {"name": "Alcohol 96°", "price": 45, "desc": "Frasco 250ml. Para desinfección de heridas.", "img": "https://images.unsplash.com/photo-1603398938378-e54eab446dde", "time": 1, "pop": 5, "profit": "alta"},
        {"name": "Agua Oxigenada", "price": 35, "desc": "Frasco 250ml. Antiséptico para heridas.", "img": "https://images.unsplash.com/photo-1603398938378-e54eab446dde", "time": 1, "pop": 4, "profit": "alta"},
        {"name": "Vendas Elásticas", "price": 55, "desc": "Venda 10cm x 5m. Para contenciones y esguinces.", "img": "https://images.unsplash.com/photo-1603398938378-e54eab446dde", "time": 1, "pop": 4, "profit": "media"},
        {"name": "Micropore", "price": 45, "desc": "Rollo 2.5cm x 5m. Cinta adhesiva para vendajes.", "img": "https://images.unsplash.com/photo-1603398938378-e54eab446dde", "time": 1, "pop": 4, "profit": "alta"},
        {"name": "Termómetro Digital", "price": 145, "desc": "Termómetro digital preciso. Resultado en 60 segundos.", "img": "https://images.unsplash.com/photo-1603398938378-e54eab446dde", "time": 1, "pop": 3, "profit": "media"},
        {"name": "Guantes Látex", "price": 65, "desc": "Caja con 100 guantes desechables talla M.", "img": "https://images.unsplash.com/photo-1603398938378-e54eab446dde", "time": 1, "pop": 4, "profit": "media"},
    ],

    "Salud Sexual": [
        {"name": "Preservativos Surtidos", "price": 95, "desc": "Caja con 12 condones. Varios tamaños y texturas.", "img": "https://images.unsplash.com/photo-1517976487492-5750f3195933", "time": 1, "pop": 5, "profit": "alta"},
        {"name": "Lubricante Íntimo", "price": 145, "desc": "Frasco 50ml. Base agua. Compatible con condones.", "img": "https://images.unsplash.com/photo-1517976487492-5750f3195933", "time": 1, "pop": 4, "profit": "media"},
        {"name": "Prueba de Embarazo", "price": 85, "desc": "Test de embarazo en orina. Resultado en 5 minutos.", "img": "https://images.unsplash.com/photo-1517976487492-5750f3195933", "time": 1, "pop": 4, "profit": "alta"},
        {"name": "Toallas Femeninas Nocturnas", "price": 65, "desc": "Paquete 10 piezas. Máxima protección nocturna.", "img": "https://images.unsplash.com/photo-1517976487492-5750f3195933", "time": 1, "pop": 5, "profit": "media"},
        {"name": "Tampones", "price": 75, "desc": "Caja 18 piezas. Absorción regular.", "img": "https://images.unsplash.com/photo-1517976487492-5750f3195933", "time": 1, "pop": 4, "profit": "media"},
    ],

    "Medicamentos Pediátricos": [
        {"name": "Tempra Jarabe Infantil", "price": 95, "desc": "Frasco 120ml. Paracetamol para niños. Sabor cereza.", "img": "https://images.unsplash.com/photo-1587854692152-cbe660dbde88", "time": 1, "pop": 5, "profit": "media"},
        {"name": "Motrin Pediátrico", "price": 115, "desc": "Frasco 120ml. Ibuprofeno suspensión para niños.", "img": "https://images.unsplash.com/photo-1587854692152-cbe660dbde88", "time": 1, "pop": 5, "profit": "media"},
        {"name": "Suero Oral Sabores", "price": 45, "desc": "Sobre individual. Rehidratación oral para niños.", "img": "https://images.unsplash.com/photo-1587854692152-cbe660dbde88", "time": 1, "pop": 5, "profit": "alta"},
        {"name": "Vitaminas Gomitas Niños", "price": 185, "desc": "Frasco 60 gomitas. Multivitamínico infantil sabor frutas.", "img": "https://images.unsplash.com/photo-1587854692152-cbe660dbde88", "time": 1, "pop": 4, "profit": "media"},
        {"name": "Jarabe para la Tos Infantil", "price": 125, "desc": "Frasco 120ml. Alivia tos seca y con flemas en niños.", "img": "https://images.unsplash.com/photo-1587854692152-cbe660dbde88", "time": 1, "pop": 4, "profit": "media"},
    ],

    "Cuidado Bucal": [
        {"name": "Cepillo Dental Suave", "price": 45, "desc": "Cepillo con cerdas suaves. Cabeza mediana.", "img": "https://images.unsplash.com/photo-1607613009820-a29f7bb81c04", "time": 1, "pop": 5, "profit": "media"},
        {"name": "Cepillo Eléctrico", "price": 485, "desc": "Cepillo eléctrico recargable con 3 cabezales.", "img": "https://images.unsplash.com/photo-1607613009820-a29f7bb81c04", "time": 1, "pop": 3, "profit": "media"},
        {"name": "Blanqueador Dental", "price": 285, "desc": "Kit blanqueamiento 7 días. Resultados visibles.", "img": "https://images.unsplash.com/photo-1607613009820-a29f7bb81c04", "time": 1, "pop": 3, "profit": "alta"},
        {"name": "Limpiador Lenguas", "price": 35, "desc": "Raspador de lengua. Mejora higiene bucal.", "img": "https://images.unsplash.com/photo-1607613009820-a29f7bb81c04", "time": 1, "pop": 2, "profit": "alta"},
    ],
}


# ==============================================================================
# CREAR CATEGORÍAS Y PRODUCTOS
# ==============================================================================

def create_categories_and_products(db: Session, tenant: Tenant, menu_dict: dict):
    """Crear categorías y productos desde el diccionario de menú"""
    print(f"\n[P] Creando menú para {tenant.name}...")

    total_categories = len(menu_dict)
    total_products = sum(len(products) for products in menu_dict.values())

    print(f"   [F] Categorías: {total_categories}")
    print(f"   [#]  Productos: {total_products}")

    display_order = 1
    product_count = 0

    for category_name, products_list in menu_dict.items():
        # Crear categoría
        category = Category(
            tenant_id=tenant.tenant_id,
            name=category_name,
            description=f"Productos de {category_name.lower()}",
            display_order=display_order,
            is_active=True
        )
        db.add(category)
        db.flush()  # Para obtener el ID

        # Crear productos de esta categoría
        for product_data in products_list:
            product = Product(
                tenant_id=tenant.tenant_id,
                category_id=category.id,
                name=product_data["name"],
                description=product_data["desc"],
                price=float(product_data["price"]),
                cost=float(product_data["price"]) * 0.5,  # 50% de costo aproximado
                image_url=product_data["img"],
                is_available=True,
                preparation_time_minutes=product_data["time"],
                popularity=product_data["pop"],
                profitability=product_data["profit"],
                menu_classification="estrella" if product_data["profit"] == "alta" and product_data["pop"] >= 4 else "caballo"
            )
            db.add(product)
            product_count += 1

        display_order += 1

    db.commit()
    print(f"   [v] {total_categories} categorías creadas")
    print(f"   [v] {product_count} productos creados")


# ==============================================================================
# CREAR USUARIOS
# ==============================================================================

def create_users(db: Session, roles: dict, tenants: list):
    """Crear usuarios para cada tenant"""
    print("\n[UU] 4. Creando usuarios...")

    users_created = 0

    for tenant in tenants:
        # Admin del tenant
        admin = User(
            tenant_id=tenant.tenant_id,
            name=f"Admin {tenant.name}",
            email=f"admin@{tenant.tenant_id}.com",
            password_hash=hash_password("Admin123!"),
            phone=f"555{random.randint(1000000, 9999999)}",
            is_active=True,
            email_verified=True
        )
        admin.roles.append(roles[RoleType.ADMIN.value])
        db.add(admin)
        users_created += 1

        # Staff del tenant
        staff = User(
            tenant_id=tenant.tenant_id,
            name=f"Staff {tenant.name}",
            email=f"staff@{tenant.tenant_id}.com",
            password_hash=hash_password("Staff123!"),
            phone=f"555{random.randint(1000000, 9999999)}",
            is_active=True,
            email_verified=True
        )
        staff.roles.append(roles[RoleType.STAFF.value])
        db.add(staff)
        users_created += 1

        # 3 Clientes de prueba
        for i in range(1, 4):
            customer = User(
                tenant_id=tenant.tenant_id,
                name=f"Cliente {i}",
                email=f"cliente{i}@{tenant.tenant_id}.com",
                password_hash=hash_password("Cliente123!"),
                phone=f"521{random.randint(1000000000, 9999999999)}",
                is_active=True,
                email_verified=True
            )
            customer.roles.append(roles[RoleType.CUSTOMER.value])
            db.add(customer)
            users_created += 1

    db.commit()
    print(f"   [v] {users_created} usuarios creados")
    print(f"      - Admins: {len(tenants)}")
    print(f"      - Staff: {len(tenants)}")
    print(f"      - Clientes: {len(tenants) * 3}")


# ==============================================================================
# CREAR PROMOCIONES
# ==============================================================================

def create_promotions(db: Session, tenants: list):
    """Crear promociones de ejemplo para cada tenant"""
    print("\n[G] 5. Creando promociones...")

    promotions_created = 0

    for tenant in tenants:
        # Obtener productos del tenant
        products = db.query(Product).filter(
            Product.tenant_id == tenant.tenant_id,
            Product.popularity >= 4
        ).limit(5).all()

        if len(products) < 2:
            continue

        # Promoción 1: Descuento porcentual
        promo1 = Promotion(
            tenant_id=tenant.tenant_id,
            name=f"Descuento 20% - {tenant.name}",
            description="Descuento del 20% en productos seleccionados",
            promotion_type="discount",
            discount_type="percentage",
            discount_value=20,
            start_date=datetime.now(),
            end_date=datetime.now() + timedelta(days=30),
            is_active=True,
            priority=1
        )
        promo1.products = products[:2]
        db.add(promo1)
        promotions_created += 1

        # Promoción 2: 2x1
        if len(products) >= 3:
            promo2 = Promotion(
                tenant_id=tenant.tenant_id,
                name=f"2x1 - {tenant.name}",
                description="Compra 2 y paga 1 en productos seleccionados",
                promotion_type="discount",
                discount_type="percentage",
                discount_value=50,
                start_date=datetime.now(),
                end_date=datetime.now() + timedelta(days=15),
                is_active=True,
                priority=2,
                min_quantity=2
            )
            promo2.products = products[2:4]
            db.add(promo2)
            promotions_created += 1

    db.commit()
    print(f"   [v] {promotions_created} promociones creadas")


# ==============================================================================
# EJECUCIÓN PRINCIPAL
# ==============================================================================

if __name__ == "__main__":
    db = SessionLocal()

    try:
        # 1. Crear roles
        roles = create_roles(db)

        # 2. Crear tenants
        tenants = create_tenants(db)

        # 3. Crear categorías y productos para cada tenant
        for tenant in tenants:
            if tenant.tenant_id == "restaurante-sabor-sur":
                create_categories_and_products(db, tenant, RESTAURANTE_MENU)
            elif tenant.tenant_id == "vineteria-premium":
                create_categories_and_products(db, tenant, VINETERIA_MENU)
            elif tenant.tenant_id == "farmasalud-24":
                create_categories_and_products(db, tenant, FARMACIA_MENU)

        # 4. Crear usuarios
        create_users(db, roles, tenants)

        # 5. Crear promociones
        create_promotions(db, tenants)

        print("\n" + "=" * 80)
        print("[OK] DATOS CARGADOS EXITOSAMENTE")
        print("=" * 80)
        print("\n[i] RESUMEN:")
        print(f"   [S] Tenants: {len(tenants)}")
        print(f"   [U] Roles: {len(roles)}")

        # Contar productos
        total_products = db.query(Product).count()
        total_categories = db.query(Category).count()
        total_users = db.query(User).count()
        total_promotions = db.query(Promotion).count()

        print(f"   [P] Categorías totales: {total_categories}")
        print(f"   [#]  Productos totales: {total_products}")
        print(f"   [UU] Usuarios totales: {total_users}")
        print(f"   [G] Promociones: {total_promotions}")

        print("\n[KEY] CREDENCIALES DE ACCESO:")
        print("=" * 80)

        for tenant in tenants:
            print(f"\n{tenant.name} ({tenant.tenant_id}):")
            print(f"   Admin:  admin@{tenant.tenant_id}.com / Admin123!")
            print(f"   Staff:  staff@{tenant.tenant_id}.com / Staff123!")
            print(f"   Cliente: cliente1@{tenant.tenant_id}.com / Cliente123!")

        print("\n" + "=" * 80)
        print("[*] SIGUIENTE PASO:")
        print("   Iniciar el servidor: uvicorn src.main:app --reload --port 8000")
        print("   Documentación API: http://localhost:8000/docs")
        print("=" * 80)

    except Exception as e:
        print(f"\n[X] ERROR: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


# ============================================================================== (Continúa en siguiente mensaje...)
