"""
================================================================================
AGENT ROUTER - Menu Service (PUBLIC)
================================================================================
Endpoints optimizados para el agente de ventas por voz.
Proporciona datos de ingeniería del menú para recomendaciones inteligentes.
NOTA: Todos los endpoints requieren tenant_id para aislamiento de datos.
================================================================================
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional, List
import logging

from ..database import get_db
from ..models import Product, Category

logger = logging.getLogger(__name__)

router = APIRouter()


# ==============================================================================
# OBTENER MENU COMPLETO PARA EL AGENTE
# ==============================================================================

@router.get(
    "/menu",
    summary="Obtener menú completo para el agente de ventas",
    description="Retorna el menú estructurado con datos de ingeniería para el agente de voz"
)
async def get_menu_for_agent(
    tenant_id: str = Query(..., description="ID del tenant"),
    available_only: bool = Query(default=True, description="Solo productos disponibles"),
    db: Session = Depends(get_db)
):
    """
    Obtener menú completo estructurado por categorías.
    Incluye campos de ingeniería del menú para recomendaciones inteligentes.

    IMPORTANTE: Filtra datos por tenant_id para aislamiento.
    """
    logger.info(f"Fetching menu for voice agent, tenant: {tenant_id}")

    # Obtener categorías activas con sus productos - FILTRADO POR TENANT
    categories = db.query(Category).filter(
        Category.tenant_id == tenant_id,
        Category.is_active == True
    ).order_by(Category.display_order).all()

    menu_data = {
        "categories": [],
        "recommendations": {
            "estrellas": [],      # Alta popularidad + alta rentabilidad
            "caballos": [],       # Alta popularidad + baja rentabilidad
            "rompecabezas": [],   # Baja popularidad + alta rentabilidad (para sugerir)
            "para_vender": []     # Top items que el agente debe promover
        },
        "unavailable": []
    }

    # Productos para recomendaciones
    all_products = []

    for category in categories:
        products_query = db.query(Product).filter(
            Product.category_id == category.id,
            Product.tenant_id == tenant_id  # SECURITY: Filtrar por tenant
        )

        if available_only:
            products_query = products_query.filter(Product.is_available == True)

        products = products_query.order_by(Product.name).all()

        category_data = {
            "id": category.id,
            "name": category.name,
            "description": category.description,
            "products": []
        }

        for product in products:
            product_data = {
                "id": product.id,
                "name": product.name,
                "price": float(product.price) if product.price else 0,
                "description": product.description,
                "ingredients": product.ingredients,
                "spice_level": product.spice_level or 0,
                "spice_label": _get_spice_label(product.spice_level or 0),
                "preparation_time": product.preparation_time_minutes or 15,
                "is_available": product.is_available,
                "popularity": product.popularity or 3,
                "profitability": product.profitability or "media",
                "menu_classification": product.menu_classification,
                "cost": float(product.cost) if product.cost else None,
                "margin": _calculate_margin(product.price, product.cost),
                "video_url": product.video_url
            }

            category_data["products"].append(product_data)
            all_products.append(product_data)

        menu_data["categories"].append(category_data)

    # Obtener productos no disponibles - FILTRADO POR TENANT
    unavailable = db.query(Product).filter(
        Product.tenant_id == tenant_id,
        Product.is_available == False
    ).all()
    menu_data["unavailable"] = [{"id": p.id, "name": p.name} for p in unavailable]

    # Clasificar productos para recomendaciones
    for product in all_products:
        classification = product.get("menu_classification")
        if classification == "estrella":
            menu_data["recommendations"]["estrellas"].append({
                "id": product["id"],
                "name": product["name"],
                "price": product["price"],
                "description": product["description"]
            })
        elif classification == "caballo":
            menu_data["recommendations"]["caballos"].append({
                "id": product["id"],
                "name": product["name"],
                "price": product["price"]
            })
        elif classification == "rompecabezas":
            menu_data["recommendations"]["rompecabezas"].append({
                "id": product["id"],
                "name": product["name"],
                "price": product["price"],
                "description": product["description"]
            })

    # Top productos para vender (estrellas + rompecabezas con alta rentabilidad)
    menu_data["recommendations"]["para_vender"] = (
        menu_data["recommendations"]["estrellas"][:5] +
        [p for p in all_products if p.get("profitability") == "alta" and p.get("menu_classification") != "estrella"][:3]
    )

    logger.info(f"Menu loaded for tenant {tenant_id}: {len(all_products)} products, {len(menu_data['unavailable'])} unavailable")

    return menu_data


# ==============================================================================
# OBTENER PRODUCTOS RECOMENDADOS
# ==============================================================================

@router.get(
    "/recommendations",
    summary="Obtener recomendaciones inteligentes",
    description="Retorna productos recomendados basados en ingeniería del menú"
)
async def get_recommendations(
    tenant_id: str = Query(..., description="ID del tenant"),
    classification: Optional[str] = Query(
        default=None,
        description="Filtrar por clasificación: estrella, caballo, perro, rompecabezas"
    ),
    max_spice: Optional[int] = Query(
        default=None, ge=0, le=3,
        description="Nivel máximo de picante: 0=nada, 1=bajo, 2=medio, 3=alto"
    ),
    max_price: Optional[float] = Query(
        default=None,
        description="Precio máximo"
    ),
    category_id: Optional[int] = Query(
        default=None,
        description="Filtrar por categoría"
    ),
    limit: int = Query(default=5, ge=1, le=20, description="Cantidad de recomendaciones"),
    db: Session = Depends(get_db)
):
    """
    Obtener productos recomendados con filtros inteligentes.
    Prioriza productos estrella y de alta rentabilidad.

    IMPORTANTE: Filtrado por tenant_id.
    """
    logger.info(f"Getting recommendations for tenant {tenant_id}: classification={classification}, max_spice={max_spice}")

    # SECURITY: SIEMPRE filtrar por tenant
    query = db.query(Product).filter(
        Product.tenant_id == tenant_id,
        Product.is_available == True
    )

    # Aplicar filtros
    if classification:
        query = query.filter(Product.menu_classification == classification)

    if max_spice is not None:
        query = query.filter(Product.spice_level <= max_spice)

    if max_price:
        query = query.filter(Product.price <= max_price)

    if category_id:
        query = query.filter(Product.category_id == category_id)

    # Ordenar por popularidad y rentabilidad
    products = query.order_by(
        Product.popularity.desc(),
        Product.profitability.desc()
    ).limit(limit).all()

    recommendations = []
    for product in products:
        recommendations.append({
            "id": product.id,
            "name": product.name,
            "price": float(product.price) if product.price else 0,
            "description": product.description,
            "ingredients": product.ingredients,
            "spice_level": product.spice_level or 0,
            "spice_label": _get_spice_label(product.spice_level or 0),
            "popularity": product.popularity or 3,
            "profitability": product.profitability or "media",
            "menu_classification": product.menu_classification,
            "reason": _get_recommendation_reason(product)
        })

    return {
        "count": len(recommendations),
        "recommendations": recommendations
    }


# ==============================================================================
# BUSCAR PRODUCTOS POR PREFERENCIAS
# ==============================================================================

@router.get(
    "/search",
    summary="Buscar productos por preferencias",
    description="Busca productos según preferencias del cliente para el agente"
)
async def search_by_preferences(
    tenant_id: str = Query(..., description="ID del tenant"),
    query: Optional[str] = Query(default=None, description="Búsqueda por nombre/descripción"),
    sin_picante: bool = Query(default=False, description="Solo productos sin picante"),
    vegetariano: bool = Query(default=False, description="Solo productos vegetarianos"),
    rapido: bool = Query(default=False, description="Tiempo de preparación <= 10 min"),
    economico: bool = Query(default=False, description="Productos económicos (< $50)"),
    premium: bool = Query(default=False, description="Productos premium/estrella"),
    db: Session = Depends(get_db)
):
    """
    Buscar productos según las preferencias expresadas por el cliente.
    Útil para el agente cuando el cliente menciona restricciones.

    IMPORTANTE: Filtrado por tenant_id.
    """
    logger.info(f"Search by preferences for tenant {tenant_id}: query={query}, sin_picante={sin_picante}")

    # SECURITY: SIEMPRE filtrar por tenant
    products_query = db.query(Product).filter(
        Product.tenant_id == tenant_id,
        Product.is_available == True
    )

    # Filtrar por búsqueda de texto
    if query:
        search_term = f"%{query}%"
        products_query = products_query.filter(
            (Product.name.ilike(search_term)) |
            (Product.description.ilike(search_term)) |
            (Product.ingredients.ilike(search_term))
        )

    # Sin picante
    if sin_picante:
        products_query = products_query.filter(Product.spice_level == 0)

    # Vegetariano (buscar en ingredientes)
    if vegetariano:
        # Excluir productos con carne
        meat_terms = ['carne', 'pollo', 'res', 'cerdo', 'pastor', 'chorizo', 'tocino', 'suadero', 'bistec']
        for term in meat_terms:
            products_query = products_query.filter(~Product.ingredients.ilike(f"%{term}%"))

    # Rápido
    if rapido:
        products_query = products_query.filter(Product.preparation_time_minutes <= 10)

    # Económico
    if economico:
        products_query = products_query.filter(Product.price < 50)

    # Premium/Estrella
    if premium:
        products_query = products_query.filter(Product.menu_classification == 'estrella')

    products = products_query.order_by(Product.popularity.desc()).limit(10).all()

    results = []
    for product in products:
        results.append({
            "id": product.id,
            "name": product.name,
            "price": float(product.price) if product.price else 0,
            "description": product.description,
            "ingredients": product.ingredients,
            "spice_level": product.spice_level or 0,
            "spice_label": _get_spice_label(product.spice_level or 0),
            "preparation_time": product.preparation_time_minutes or 15,
            "category_id": product.category_id
        })

    return {
        "count": len(results),
        "products": results,
        "filters_applied": {
            "query": query,
            "sin_picante": sin_picante,
            "vegetariano": vegetariano,
            "rapido": rapido,
            "economico": economico,
            "premium": premium
        }
    }


# ==============================================================================
# OBTENER SUGERENCIA DE UPSELL
# ==============================================================================

@router.get(
    "/upsell/{product_id}",
    summary="Obtener sugerencia de upsell para un producto",
    description="Sugiere productos complementarios o mejoras"
)
async def get_upsell_suggestion(
    product_id: int,
    tenant_id: str = Query(..., description="ID del tenant"),
    db: Session = Depends(get_db)
):
    """
    Obtener sugerencias de venta cruzada/upsell basadas en el producto.

    IMPORTANTE: Filtrado por tenant_id.
    """
    logger.info(f"Getting upsell suggestions for product {product_id}, tenant {tenant_id}")

    # SECURITY: Verificar que el producto pertenece al tenant
    product = db.query(Product).filter(
        Product.id == product_id,
        Product.tenant_id == tenant_id
    ).first()

    if not product:
        return {"error": "Product not found", "suggestions": []}

    suggestions = []

    # Buscar bebidas si el producto es comida - FILTRADO POR TENANT
    if product.category_id and product.category_id in [1, 2, 3, 4, 5, 6, 7]:  # Categorías de comida
        bebidas = db.query(Product).filter(
            Product.tenant_id == tenant_id,  # SECURITY: Filtrar por tenant
            Product.is_available == True,
            Product.category_id == 8  # Bebidas
        ).order_by(Product.popularity.desc()).limit(2).all()

        for b in bebidas:
            suggestions.append({
                "type": "complemento",
                "product": {
                    "id": b.id,
                    "name": b.name,
                    "price": float(b.price) if b.price else 0
                },
                "script": f"¿Le gustaría agregar {b.name} por solo ${b.price:.0f}?"
            })

    # Buscar postres - FILTRADO POR TENANT
    postres = db.query(Product).filter(
        Product.tenant_id == tenant_id,  # SECURITY: Filtrar por tenant
        Product.is_available == True,
        Product.category_id == 7  # Postres
    ).order_by(Product.popularity.desc()).limit(1).all()

    for p in postres:
        suggestions.append({
            "type": "postre",
            "product": {
                "id": p.id,
                "name": p.name,
                "price": float(p.price) if p.price else 0
            },
            "script": f"Para finalizar, ¿le gustaría probar nuestro {p.name}?"
        })

    # Buscar producto estrella de la misma categoría - FILTRADO POR TENANT
    estrella = db.query(Product).filter(
        Product.tenant_id == tenant_id,  # SECURITY: Filtrar por tenant
        Product.is_available == True,
        Product.category_id == product.category_id,
        Product.menu_classification == 'estrella',
        Product.id != product_id
    ).order_by(Product.popularity.desc()).first()

    if estrella:
        price_diff = float(estrella.price - product.price) if estrella.price and product.price else 0
        if price_diff > 0:
            suggestions.append({
                "type": "upgrade",
                "product": {
                    "id": estrella.id,
                    "name": estrella.name,
                    "price": float(estrella.price) if estrella.price else 0
                },
                "script": f"Por solo ${price_diff:.0f} más puede llevar {estrella.name}, es uno de nuestros platillos estrella."
            })

    return {
        "original_product": {
            "id": product.id,
            "name": product.name,
            "price": float(product.price) if product.price else 0
        },
        "suggestions": suggestions
    }


# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

def _get_spice_label(level: int) -> str:
    """Convertir nivel numérico de picante a etiqueta"""
    labels = {
        0: "sin picante",
        1: "poco picante",
        2: "picante medio",
        3: "muy picante"
    }
    return labels.get(level, "sin picante")


def _calculate_margin(price, cost) -> Optional[float]:
    """Calcular margen de ganancia"""
    if price and cost and float(cost) > 0:
        return round((float(price) - float(cost)) / float(price) * 100, 1)
    return None


def _get_recommendation_reason(product) -> str:
    """Generar razón de recomendación para el agente"""
    reasons = []

    classification = product.menu_classification
    if classification == "estrella":
        reasons.append("platillo estrella muy popular")
    elif classification == "rompecabezas":
        reasons.append("excelente opción con alta rentabilidad")

    if product.popularity and product.popularity >= 4:
        reasons.append("favorito de nuestros clientes")

    if product.profitability == "alta":
        reasons.append("gran relación calidad-precio")

    return " - ".join(reasons) if reasons else "buena opción"


# ==============================================================================
# NOTAS IMPORTANTES
# ==============================================================================

"""
⚠️ SEGURIDAD:

1. Este router es SOLO para lectura (GET)
2. Todos los endpoints REQUIEREN tenant_id
3. Todos los queries filtran por tenant_id
4. Diseñado para el agente de voz con datos de ingeniería del menú

CRÍTICO: El agente de voz DEBE pasar el tenant_id correcto en cada request
para evitar mostrar productos de otros restaurantes.

"""
