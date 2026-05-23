"""
================================================================================
DEMO CONFIG - Configuración de Tiendas Demo Interactivas
================================================================================
Define catálogos, productos y configuraciones para cada industria demo
================================================================================
"""

from typing import Dict, List, Any
from enum import Enum


class DemoIndustry(str, Enum):
    """Industrias disponibles en la demo"""
    RESTAURANT = "demo_restaurant"
    RETAIL = "demo_retail"
    PHARMACY = "demo_pharmacy"
    GROCERY = "demo_grocery"
    SERVICES = "demo_services"
    PETS = "demo_pets"


# ==============================================================================
# CATÁLOGOS DEMO POR INDUSTRIA
# ==============================================================================

DEMO_CATALOGS = {
    # -------------------------------------------------------------------------
    # 1. RICO MAR SALVATIERRA - MARISCOS GOURMET
    # -------------------------------------------------------------------------
    DemoIndustry.RESTAURANT: {
        "name": "Rico Mar Salvatierra",
        "description": "Mariscos Gourmet de la Región",
        "icon": "🦐",
        "welcome_message": """👋 ¡Bienvenido a Rico Mar Salvatierra! 🦐🐟

Los mejores mariscos gourmet de la región. Soy tu mesero virtual con IA.

Puedo ayudarte a:
• Ver el menú completo de mariscos
• Hacer pedidos por voz o texto
• Gestionar tus puntos de fidelidad
• Consultar promociones especiales

¿Qué te gustaría hacer?

1️⃣ Ver menú completo en web
2️⃣ Hacer un pedido
3️⃣ Ver mis puntos de fidelidad
4️⃣ Promociones del día
5️⃣ Hablar con mesero virtual

Responde con el número o dime qué se te antoja 😊""",

        "categories": [
            {"id": "tostadas", "name": "Tostadas", "icon": "🦐"},
            {"id": "aguachiles", "name": "Aguachiles", "icon": "🌶️"},
            {"id": "sushi", "name": "Sushi Rolls", "icon": "🍣"},
            {"id": "caldos", "name": "Caldos", "icon": "🥣"},
            {"id": "bebidas", "name": "Bebidas", "icon": "🥤"}
        ],

        "products": [
            {
                "id": "tostada_ceviche",
                "name": "Tostada de Ceviche de Camarón",
                "description": "Camarón curtido al limón con aguacate",
                "price": 95.00,
                "category": "tostadas",
                "image": "https://images.unsplash.com/photo-1626200419199-391ae4be7a41?w=400",
                "available": True
            },
            {
                "id": "tostada_mazatleca",
                "name": "Tostada Mazatleca",
                "description": "Camarón, pulpo, jaiba y callo de almeja",
                "price": 120.00,
                "category": "tostadas",
                "image": "https://images.unsplash.com/photo-1559181567-c3190ca9959b?w=400",
                "available": True
            },
            {
                "id": "aguachile_verde",
                "name": "Aguachile Verde",
                "description": "Camarones frescos en salsa verde picante",
                "price": 230.00,
                "category": "aguachiles",
                "image": "https://images.unsplash.com/photo-1565958011703-44f9829ba187?w=400",
                "available": True
            },
            {
                "id": "aguachile_mango",
                "name": "Aguachile Mango Habanero",
                "description": "Camarones en salsa de mango con habanero",
                "price": 250.00,
                "category": "aguachiles",
                "image": "https://images.unsplash.com/photo-1609501676725-7186f017a4b7?w=400",
                "available": True
            },
            {
                "id": "california_roll",
                "name": "California Roll",
                "description": "Rollo con camarón, aguacate y queso crema",
                "price": 120.00,
                "category": "sushi",
                "image": "https://images.unsplash.com/photo-1579584425555-c3ce17fd4351?w=400",
                "available": True
            },
            {
                "id": "rico_mar_roll",
                "name": "Rico Mar Roll",
                "description": "Rollo empanizado especial de la casa",
                "price": 140.00,
                "category": "sushi",
                "image": "https://images.unsplash.com/photo-1617196034796-73dfa7b1fd56?w=400",
                "available": True
            },
            {
                "id": "caldo_camaron",
                "name": "Caldo de Camarón",
                "description": "Caldo caliente con camarones grandes",
                "price": 200.00,
                "category": "caldos",
                "image": "https://images.unsplash.com/photo-1547592166-23ac45744acd?w=400",
                "available": True
            },
            {
                "id": "refresco",
                "name": "Refresco",
                "description": "Coca-Cola, Sprite o Fanta 600ml",
                "price": 30.00,
                "category": "bebidas",
                "image": "https://images.unsplash.com/photo-1554866585-cd94860890b7?w=400",
                "available": True
            },
            {
                "id": "cerveza",
                "name": "Cerveza Nacional",
                "description": "Corona, Victoria, Modelo o Pacifico",
                "price": 40.00,
                "category": "bebidas",
                "image": "https://images.unsplash.com/photo-1608270586620-248524c67de9?w=400",
                "available": True
            },
            {
                "id": "jugo_natural",
                "name": "Jugo Natural",
                "description": "Naranja, toronja o zanahoria",
                "price": 40.00,
                "category": "bebidas",
                "image": "https://images.unsplash.com/photo-1600271886742-f049cd451bba?w=400",
                "available": True
            }
        ]
    },

    # -------------------------------------------------------------------------
    # 2. TIENDA / BOUTIQUE
    # -------------------------------------------------------------------------
    DemoIndustry.RETAIL: {
        "name": "Boutique Fashion Point",
        "description": "Moda y estilo para todos",
        "icon": "🛍️",
        "welcome_message": """👋 ¡Hola! Bienvenido a Fashion Point

Soy tu asistente de compras con IA. Puedo ayudarte a:
• Explorar nuestro catálogo
• Buscar productos específicos
• Recomendarte outfits
• Gestionar tus puntos de fidelidad

¿Qué te gustaría hacer?

1️⃣ Ver catálogo completo
2️⃣ Buscar algo específico
3️⃣ Ver mis puntos
4️⃣ Ofertas de temporada

Responde con el número o dime qué buscas 😊""",

        "categories": [
            {"id": "ropa_mujer", "name": "Ropa Mujer", "icon": "👗"},
            {"id": "ropa_hombre", "name": "Ropa Hombre", "icon": "👔"},
            {"id": "accesorios", "name": "Accesorios", "icon": "👜"},
            {"id": "calzado", "name": "Calzado", "icon": "👠"}
        ],

        "products": [
            {
                "id": "vestido_rojo",
                "name": "Vestido Rojo Elegante",
                "description": "Vestido largo, ideal para eventos",
                "price": 899.00,
                "category": "ropa_mujer",
                "image": "https://images.unsplash.com/photo-1566174053879-31528523f8ae?w=400",
                "available": True
            },
            {
                "id": "blusa_blanca",
                "name": "Blusa Blanca Formal",
                "description": "Blusa de seda, talla S-M-L",
                "price": 450.00,
                "category": "ropa_mujer",
                "image": "https://images.unsplash.com/photo-1564584217132-2271feaeb3c5?w=400",
                "available": True
            },
            {
                "id": "camisa_hombre",
                "name": "Camisa Casual Hombre",
                "description": "Camisa de algodón, varios colores",
                "price": 550.00,
                "category": "ropa_hombre",
                "image": "https://images.unsplash.com/photo-1602810318383-e386cc2a3ccf?w=400",
                "available": True
            },
            {
                "id": "pantalon_mezclilla",
                "name": "Pantalón de Mezclilla",
                "description": "Jeans corte recto, azul",
                "price": 680.00,
                "category": "ropa_hombre",
                "image": "https://images.unsplash.com/photo-1542272604-787c3835535d?w=400",
                "available": True
            },
            {
                "id": "bolsa_negra",
                "name": "Bolsa Negra Elegante",
                "description": "Bolsa de piel sintética",
                "price": 750.00,
                "category": "accesorios",
                "image": "https://images.unsplash.com/photo-1590874103328-eac38a683ce7?w=400",
                "available": True
            },
            {
                "id": "zapatos_mujer",
                "name": "Zapatos de Tacón",
                "description": "Tacón medio, color negro",
                "price": 850.00,
                "category": "calzado",
                "image": "https://images.unsplash.com/photo-1543163521-1bf539c55dd2?w=400",
                "available": True
            }
        ]
    },

    # -------------------------------------------------------------------------
    # 3. FARMACIA / SALUD
    # -------------------------------------------------------------------------
    DemoIndustry.PHARMACY: {
        "name": "Farmacia Salud Plus",
        "description": "Tu salud, nuestra prioridad",
        "icon": "💊",
        "welcome_message": """👋 ¡Hola! Bienvenido a Farmacia Salud Plus

Soy tu asistente farmacéutico virtual. Puedo ayudarte a:
• Buscar medicamentos
• Subir recetas médicas
• Programar entregas urgentes
• Gestionar tus puntos

¿Qué necesitas?

1️⃣ Ver catálogo de productos
2️⃣ Subir receta médica
3️⃣ Delivery urgente
4️⃣ Ver mis puntos

Responde con el número o dime qué necesitas 😊""",

        "categories": [
            {"id": "medicamentos", "name": "Medicamentos", "icon": "💊"},
            {"id": "vitaminas", "name": "Vitaminas", "icon": "🌿"},
            {"id": "higiene", "name": "Higiene", "icon": "🧴"},
            {"id": "primeros_auxilios", "name": "Primeros Auxilios", "icon": "🩹"}
        ],

        "products": [
            {
                "id": "paracetamol",
                "name": "Paracetamol 500mg",
                "description": "Caja con 20 tabletas",
                "price": 45.00,
                "category": "medicamentos",
                "image": "https://images.unsplash.com/photo-1584308666744-24d5c474f2ae?w=400",
                "available": True
            },
            {
                "id": "ibuprofeno",
                "name": "Ibuprofeno 400mg",
                "description": "Antiinflamatorio, caja 10 tabs",
                "price": 65.00,
                "category": "medicamentos",
                "image": "https://images.unsplash.com/photo-1471864190281-a93a3070b6de?w=400",
                "available": True
            },
            {
                "id": "vitamina_c",
                "name": "Vitamina C 1000mg",
                "description": "Frasco con 60 tabletas",
                "price": 180.00,
                "category": "vitaminas",
                "image": "https://images.unsplash.com/photo-1607619056574-7b8d3ee536b2?w=400",
                "available": True
            },
            {
                "id": "multivitaminico",
                "name": "Multivitamínico",
                "description": "Vitaminas A-Z, 30 cápsulas",
                "price": 250.00,
                "category": "vitaminas",
                "image": "https://images.unsplash.com/photo-1550572017-4104796e48e9?w=400",
                "available": True
            },
            {
                "id": "gel_antibacterial",
                "name": "Gel Antibacterial 500ml",
                "description": "70% alcohol",
                "price": 85.00,
                "category": "higiene",
                "image": "https://images.unsplash.com/photo-1584744982491-665216d95f8b?w=400",
                "available": True
            }
        ]
    },

    # -------------------------------------------------------------------------
    # 4. ABARROTES / SUPERMERCADO
    # -------------------------------------------------------------------------
    DemoIndustry.GROCERY: {
        "name": "Super Abarrotes La Esquina",
        "description": "Tu despensa completa",
        "icon": "🛒",
        "welcome_message": """👋 ¡Hola! Bienvenido a Super La Esquina

Soy tu asistente de compras. Puedo ayudarte a:
• Hacer tu despensa semanal
• Repetir tu última compra
• Buscar productos específicos
• Gestionar tus puntos

¿Qué necesitas hoy?

1️⃣ Ver productos disponibles
2️⃣ Repetir mi despensa habitual
3️⃣ Buscar algo específico
4️⃣ Ver mis puntos

Responde con el número o dime qué necesitas 😊""",

        "categories": [
            {"id": "despensa", "name": "Despensa", "icon": "🥫"},
            {"id": "lacteos", "name": "Lácteos", "icon": "🥛"},
            {"id": "frutas", "name": "Frutas y Verduras", "icon": "🍎"},
            {"id": "limpieza", "name": "Limpieza", "icon": "🧹"}
        ],

        "products": [
            {
                "id": "arroz",
                "name": "Arroz 1kg",
                "description": "Arroz blanco grano largo",
                "price": 25.00,
                "category": "despensa",
                "image": "https://images.unsplash.com/photo-1586201375761-83865001e31c?w=400",
                "available": True
            },
            {
                "id": "frijol",
                "name": "Frijol Negro 1kg",
                "description": "Frijol negro entero",
                "price": 30.00,
                "category": "despensa",
                "image": "https://images.unsplash.com/photo-1589362193579-d663ee1a0e89?w=400",
                "available": True
            },
            {
                "id": "leche",
                "name": "Leche Entera 1L",
                "description": "Leche pasteurizada",
                "price": 22.00,
                "category": "lacteos",
                "image": "https://images.unsplash.com/photo-1563636619-e9143da7973b?w=400",
                "available": True
            },
            {
                "id": "huevos",
                "name": "Huevos 12 piezas",
                "description": "Huevos blancos",
                "price": 45.00,
                "category": "lacteos",
                "image": "https://images.unsplash.com/photo-1582722872445-44dc5f7e3c8f?w=400",
                "available": True
            },
            {
                "id": "manzanas",
                "name": "Manzanas Rojas 1kg",
                "description": "Manzanas frescas",
                "price": 40.00,
                "category": "frutas",
                "image": "https://images.unsplash.com/photo-1560806887-1e4cd0b6cbd6?w=400",
                "available": True
            }
        ]
    },

    # -------------------------------------------------------------------------
    # 5. SERVICIOS / SALÓN DE BELLEZA
    # -------------------------------------------------------------------------
    DemoIndustry.SERVICES: {
        "name": "Salón Bella Imagen",
        "description": "Belleza y estilo profesional",
        "icon": "💇",
        "welcome_message": """👋 ¡Hola! Bienvenido a Salón Bella Imagen

Soy tu asistente virtual. Puedo ayudarte a:
• Agendar citas
• Ver servicios disponibles
• Consultar promociones
• Gestionar tus puntos

¿Qué te gustaría hacer?

1️⃣ Ver servicios y precios
2️⃣ Agendar una cita
3️⃣ Promociones del mes
4️⃣ Ver mis puntos

Responde con el número o dime qué necesitas 😊""",

        "categories": [
            {"id": "cabello", "name": "Cabello", "icon": "💇"},
            {"id": "unas", "name": "Uñas", "icon": "💅"},
            {"id": "facial", "name": "Facial", "icon": "✨"},
            {"id": "paquetes", "name": "Paquetes", "icon": "🎁"}
        ],

        "products": [
            {
                "id": "corte_dama",
                "name": "Corte de Cabello Dama",
                "description": "Lavado + Corte + Secado",
                "price": 200.00,
                "category": "cabello",
                "image": "https://images.unsplash.com/photo-1562322140-8baeececf3df?w=400",
                "available": True
            },
            {
                "id": "corte_caballero",
                "name": "Corte Caballero",
                "description": "Corte + Perfilado",
                "price": 120.00,
                "category": "cabello",
                "image": "https://images.unsplash.com/photo-1599351431202-1e0f0137899a?w=400",
                "available": True
            },
            {
                "id": "tinte",
                "name": "Tinte Completo",
                "description": "Incluye baño de color",
                "price": 500.00,
                "category": "cabello",
                "image": "https://images.unsplash.com/photo-1487412947147-5cebf100ffc2?w=400",
                "available": True
            },
            {
                "id": "manicure",
                "name": "Manicure",
                "description": "Limado + Esmaltado",
                "price": 150.00,
                "category": "unas",
                "image": "https://images.unsplash.com/photo-1604654894610-df63bc536371?w=400",
                "available": True
            },
            {
                "id": "pedicure",
                "name": "Pedicure",
                "description": "Completo con masaje",
                "price": 180.00,
                "category": "unas",
                "image": "https://images.unsplash.com/photo-1607779097040-26e80aa78e66?w=400",
                "available": True
            },
            {
                "id": "facial",
                "name": "Limpieza Facial",
                "description": "Facial profunda + Mascarilla",
                "price": 350.00,
                "category": "facial",
                "image": "https://images.unsplash.com/photo-1570172619644-dfd03ed5d881?w=400",
                "available": True
            }
        ]
    },

    # -------------------------------------------------------------------------
    # 6. TIENDA DE MASCOTAS
    # -------------------------------------------------------------------------
    DemoIndustry.PETS: {
        "name": "PetShop Huellitas Felices",
        "description": "Todo para tu mascota",
        "icon": "🐶",
        "welcome_message": """👋 ¡Hola! Bienvenido a Huellitas Felices

Soy tu asistente pet-friendly. Puedo ayudarte a:
• Buscar alimento y accesorios
• Programar entregas recurrentes
• Recordar vacunas
• Gestionar tus puntos

¿Qué necesitas para tu peludo?

1️⃣ Ver productos
2️⃣ Alimento para mi mascota
3️⃣ Agendar consulta veterinaria
4️⃣ Ver mis puntos

Responde con el número o dime qué necesitas 😊""",

        "categories": [
            {"id": "alimento_perro", "name": "Alimento Perro", "icon": "🐕"},
            {"id": "alimento_gato", "name": "Alimento Gato", "icon": "🐈"},
            {"id": "accesorios", "name": "Accesorios", "icon": "🦴"},
            {"id": "higiene", "name": "Higiene", "icon": "🛁"}
        ],

        "products": [
            {
                "id": "croquetas_perro",
                "name": "Croquetas para Perro 10kg",
                "description": "Alimento premium adulto",
                "price": 650.00,
                "category": "alimento_perro",
                "image": "https://images.unsplash.com/photo-1589924691995-400dc9ecc119?w=400",
                "available": True
            },
            {
                "id": "croquetas_gato",
                "name": "Croquetas para Gato 5kg",
                "description": "Alimento premium adulto",
                "price": 450.00,
                "category": "alimento_gato",
                "image": "https://images.unsplash.com/photo-1548681528-6a5c45b66b42?w=400",
                "available": True
            },
            {
                "id": "collar",
                "name": "Collar Ajustable",
                "description": "Collar para perro mediano",
                "price": 120.00,
                "category": "accesorios",
                "image": "https://images.unsplash.com/photo-1601758228041-f3b2795255f1?w=400",
                "available": True
            },
            {
                "id": "juguete",
                "name": "Juguete Interactivo",
                "description": "Pelota resistente",
                "price": 85.00,
                "category": "accesorios",
                "image": "https://images.unsplash.com/photo-1591845132927-88cd8bcfaa1c?w=400",
                "available": True
            },
            {
                "id": "shampoo",
                "name": "Shampoo para Mascotas",
                "description": "500ml, hipoalergénico",
                "price": 150.00,
                "category": "higiene",
                "image": "https://images.unsplash.com/photo-1629198735700-614f162f3d62?w=400",
                "available": True
            }
        ]
    }
}


# ==============================================================================
# CONFIGURACIÓN INICIAL DE PUNTOS DEMO
# ==============================================================================

DEMO_INITIAL_POINTS = 500  # Puntos que recibe cada nuevo prospecto
DEMO_MODE_IDENTIFIER = "🎯 MODO DEMO"  # Identificador en mensajes


def get_demo_catalog(industry: DemoIndustry) -> Dict[str, Any]:
    """Obtener catálogo completo de una industria demo"""
    return DEMO_CATALOGS.get(industry, DEMO_CATALOGS[DemoIndustry.RESTAURANT])


def get_industry_menu() -> str:
    """Obtener menú de selección de industrias"""
    return """🎮 ¿Qué tipo de negocio quieres explorar?

1️⃣ 🍔 RESTAURANTE / TAQUERÍA
   Pedidos por voz, menú digital, delivery

2️⃣ 🛍️ TIENDA / BOUTIQUE
   Catálogo web, inventario, checkout

3️⃣ 💊 FARMACIA / SALUD
   Recetas, delivery urgente, medicamentos

4️⃣ 🛒 ABARROTES / SUPERMERCADO
   Despensa, suscripciones, ofertas

5️⃣ 💇 SERVICIOS / SALÓN DE BELLEZA
   Agendamiento, citas, recordatorios

6️⃣ 🐶 TIENDA DE MASCOTAS
   Alimento, accesorios, veterinaria

━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Escribe el número de tu elección (ej: 1)

💡 Puedes probar varios. Solo escribe "cambiar"
   para explorar otro tipo de negocio."""


def get_demo_info_message() -> str:
    """Mensaje de información sobre planes y precios"""
    return """📊 PLANES Y PRECIOS

━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💼 PLAN GROWTH (Recomendado)
$999/mes - Sin comisiones por venta

✅ Todo lo que acabas de probar:
   • WhatsApp Bot con IA
   • Catálogo web responsive
   • Sistema de puntos completo
   • Checkout integrado
   • Pagos online (Stripe/MercadoPago)
   • Hasta 3 sucursales
   • Analytics y reportes
   • Soporte por chat

💰 AHORRAS vs Apps de Delivery:
   Rappi/Uber cobran 30% por venta
   = $30,000 en comisiones si vendes $100K/mes

   Con nosotros: $999/mes fijo
   ✅ AHORRAS: $29,000/mes

━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎁 OFERTA ESPECIAL:
✓ 14 días GRATIS (sin tarjeta)
✓ Setup incluido (te ayudamos)
✓ 1 mes gratis si contratas anual

━━━━━━━━━━━━━━━━━━━━━━━━━━━━

¿Te interesa?

1️⃣ Empezar prueba gratis (14 días)
2️⃣ Agendar demo personalizada 1-on-1
3️⃣ Hablar con un asesor
4️⃣ Ver otros planes

Escribe el número de tu opción."""
