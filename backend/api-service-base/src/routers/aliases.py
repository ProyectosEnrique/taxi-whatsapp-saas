"""
================================================================================
ALIASES ROUTER - Gestión de aliases de productos para voz
================================================================================
Endpoints para:
- Obtener todos los aliases activos
- Regenerar aliases automáticamente
- CRUD de aliases manuales
================================================================================
"""

import re
import unicodedata
from typing import List, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import delete
from pydantic import BaseModel

from ..database import get_db
from ..models import Product, ProductAlias, Category

router = APIRouter(prefix="/aliases", tags=["aliases"])


# ==============================================================================
# SCHEMAS
# ==============================================================================

class AliasResponse(BaseModel):
    """Respuesta de alias individual"""
    alias: str
    product_id: int
    product_name: str
    alias_type: str
    priority: int

    class Config:
        from_attributes = True


class AliasMapResponse(BaseModel):
    """Mapa de aliases para el voice assistant"""
    aliases: Dict[str, str]  # alias -> product_name
    product_lookup: Dict[str, int]  # product_name -> product_id
    total_aliases: int
    total_products: int


class GenerateAliasesResponse(BaseModel):
    """Respuesta de generación de aliases"""
    generated: int
    products_processed: int
    message: str


# ==============================================================================
# UTILIDADES DE NORMALIZACIÓN
# ==============================================================================

def normalize_text(text: str) -> str:
    """
    Normaliza texto removiendo acentos y convirtiendo a minúsculas.
    """
    # Normalizar unicode y remover acentos
    normalized = unicodedata.normalize('NFD', text)
    without_accents = ''.join(
        char for char in normalized
        if unicodedata.category(char) != 'Mn'
    )
    return without_accents.lower().strip()


def generate_aliases_for_product(product: Product) -> List[Dict]:
    """
    Genera aliases automáticos para un producto.

    Estrategias:
    1. Nombre completo normalizado
    2. Palabras individuales significativas
    3. Combinaciones de palabras
    4. Versiones sin artículos (de, la, el, con)
    """
    aliases = []
    name = product.name
    name_normalized = normalize_text(name)

    # Palabras a ignorar
    stop_words = {'de', 'la', 'el', 'los', 'las', 'con', 'sin', 'y', 'a', 'en', 'al'}

    # 1. Nombre completo normalizado (prioridad alta)
    aliases.append({
        'alias': name_normalized,
        'alias_original': name,
        'alias_type': 'exact',
        'priority': 10
    })

    # 2. Extraer palabras significativas
    words = re.findall(r'\b\w+\b', name_normalized)
    significant_words = [w for w in words if w not in stop_words and len(w) > 2]

    # Cada palabra significativa es un alias
    for word in significant_words:
        if word != name_normalized:  # Evitar duplicados
            aliases.append({
                'alias': word,
                'alias_original': word.capitalize(),
                'alias_type': 'partial',
                'priority': 5
            })

    # 3. Nombre sin artículos (ej: "Taco de Suadero" -> "taco suadero")
    without_articles = ' '.join(significant_words)
    if without_articles != name_normalized and len(without_articles) > 3:
        aliases.append({
            'alias': without_articles,
            'alias_original': without_articles.title(),
            'alias_type': 'colloquial',
            'priority': 7
        })

    # 4. Plurales/Singulares comunes para español
    for word in significant_words:
        # Si termina en 'o', agregar versión con 's' (taco -> tacos)
        if word.endswith('o') and not word.endswith('os'):
            plural = word + 's'
            aliases.append({
                'alias': plural,
                'alias_original': plural.capitalize(),
                'alias_type': 'colloquial',
                'priority': 4
            })
        # Si termina en 'os', agregar versión singular (tacos -> taco)
        elif word.endswith('os'):
            singular = word[:-1]
            if singular not in stop_words and len(singular) > 2:
                aliases.append({
                    'alias': singular,
                    'alias_original': singular.capitalize(),
                    'alias_type': 'colloquial',
                    'priority': 4
                })
        # Si termina en 'a', agregar versión con 's' (hamburguesa -> hamburguesas)
        elif word.endswith('a') and not word.endswith('as'):
            plural = word + 's'
            aliases.append({
                'alias': plural,
                'alias_original': plural.capitalize(),
                'alias_type': 'colloquial',
                'priority': 4
            })
        # Si termina en 'as', agregar versión singular
        elif word.endswith('as'):
            singular = word[:-1]
            if singular not in stop_words and len(singular) > 2:
                aliases.append({
                    'alias': singular,
                    'alias_original': singular.capitalize(),
                    'alias_type': 'colloquial',
                    'priority': 4
                })

    # 5. Combinaciones especiales por categoría
    category_name = product.category.name.lower() if product.category else ''

    if 'taco' in category_name or 'taco' in name_normalized:
        # Agregar variantes de tacos
        for word in significant_words:
            if word not in ['taco', 'tacos']:
                # "tacos de X" y "taco de X"
                aliases.append({
                    'alias': f'tacos de {word}',
                    'alias_original': f'Tacos de {word.capitalize()}',
                    'alias_type': 'colloquial',
                    'priority': 6
                })

    if 'hamburguesa' in category_name or 'hamburguesa' in name_normalized:
        # Variantes de hamburguesas
        for word in significant_words:
            if word not in ['hamburguesa', 'hamburguesas']:
                aliases.append({
                    'alias': f'hamburguesa {word}',
                    'alias_original': f'Hamburguesa {word.capitalize()}',
                    'alias_type': 'colloquial',
                    'priority': 6
                })

    if 'bebida' in category_name or 'agua' in name_normalized:
        # Variantes de bebidas
        for word in significant_words:
            if word not in ['agua', 'aguas', 'bebida', 'bebidas']:
                aliases.append({
                    'alias': f'agua de {word}',
                    'alias_original': f'Agua de {word.capitalize()}',
                    'alias_type': 'colloquial',
                    'priority': 6
                })

    # Eliminar duplicados manteniendo mayor prioridad
    seen = {}
    unique_aliases = []
    for alias in aliases:
        key = alias['alias']
        if key not in seen or seen[key]['priority'] < alias['priority']:
            seen[key] = alias

    return list(seen.values())


# ==============================================================================
# ENDPOINTS
# ==============================================================================

@router.get("/", response_model=List[AliasResponse])
def get_all_aliases(
    active_only: bool = True,
    db: Session = Depends(get_db)
):
    """
    Obtiene todos los aliases.
    """
    query = db.query(ProductAlias).join(Product)

    if active_only:
        query = query.filter(ProductAlias.is_active == True)

    aliases = query.order_by(ProductAlias.priority.desc()).all()

    return [
        AliasResponse(
            alias=a.alias,
            product_id=a.product_id,
            product_name=a.product.name,
            alias_type=a.alias_type,
            priority=a.priority
        )
        for a in aliases
    ]


@router.get("/map", response_model=AliasMapResponse)
def get_alias_map(db: Session = Depends(get_db)):
    """
    Obtiene un mapa de aliases optimizado para el voice assistant.

    Retorna:
    - aliases: Dict[alias -> product_name]
    - product_lookup: Dict[product_name -> product_id]
    """
    # Obtener aliases activos ordenados por prioridad
    aliases = db.query(ProductAlias).join(Product).filter(
        ProductAlias.is_active == True,
        Product.is_available == True
    ).order_by(ProductAlias.priority.desc()).all()

    # Construir mapa (el primero con mayor prioridad gana)
    alias_map = {}
    product_lookup = {}
    products_seen = set()

    for a in aliases:
        # Solo agregar si el alias no existe (mayor prioridad primero)
        if a.alias not in alias_map:
            alias_map[a.alias] = a.product.name
            product_lookup[a.product.name] = a.product_id
            products_seen.add(a.product_id)

    return AliasMapResponse(
        aliases=alias_map,
        product_lookup=product_lookup,
        total_aliases=len(alias_map),
        total_products=len(products_seen)
    )


@router.post("/generate", response_model=GenerateAliasesResponse)
def generate_aliases(
    replace_existing: bool = False,
    db: Session = Depends(get_db)
):
    """
    Genera aliases automáticamente para todos los productos.

    Args:
        replace_existing: Si True, elimina aliases auto-generados existentes
    """
    # Obtener productos con categoría
    products = db.query(Product).join(Category).filter(
        Product.is_available == True
    ).all()

    if not products:
        raise HTTPException(status_code=404, detail="No hay productos disponibles")

    # Si reemplazar, eliminar aliases auto-generados
    if replace_existing:
        db.execute(
            delete(ProductAlias).where(ProductAlias.is_auto_generated == True)
        )
        db.commit()

    generated_count = 0

    for product in products:
        aliases_data = generate_aliases_for_product(product)

        for alias_data in aliases_data:
            # Verificar si ya existe
            existing = db.query(ProductAlias).filter(
                ProductAlias.alias == alias_data['alias'],
                ProductAlias.product_id == product.id
            ).first()

            if not existing:
                alias = ProductAlias(
                    product_id=product.id,
                    alias=alias_data['alias'],
                    alias_original=alias_data['alias_original'],
                    alias_type=alias_data['alias_type'],
                    priority=alias_data['priority'],
                    is_auto_generated=True,
                    is_active=True
                )
                db.add(alias)
                generated_count += 1

    db.commit()

    return GenerateAliasesResponse(
        generated=generated_count,
        products_processed=len(products),
        message=f"Se generaron {generated_count} aliases para {len(products)} productos"
    )


@router.delete("/auto-generated")
def delete_auto_generated_aliases(db: Session = Depends(get_db)):
    """
    Elimina todos los aliases auto-generados.
    """
    result = db.execute(
        delete(ProductAlias).where(ProductAlias.is_auto_generated == True)
    )
    db.commit()

    return {
        "deleted": result.rowcount,
        "message": f"Se eliminaron {result.rowcount} aliases auto-generados"
    }


@router.post("/custom")
def add_custom_alias(
    product_id: int,
    alias: str,
    alias_type: str = "colloquial",
    priority: int = 8,
    db: Session = Depends(get_db)
):
    """
    Agrega un alias personalizado (manual).
    """
    # Verificar producto existe
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    # Normalizar alias
    alias_normalized = normalize_text(alias)

    # Verificar si ya existe
    existing = db.query(ProductAlias).filter(
        ProductAlias.alias == alias_normalized
    ).first()

    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"El alias '{alias}' ya existe para el producto '{existing.product.name}'"
        )

    new_alias = ProductAlias(
        product_id=product_id,
        alias=alias_normalized,
        alias_original=alias,
        alias_type=alias_type,
        priority=priority,
        is_auto_generated=False,
        is_active=True
    )

    db.add(new_alias)
    db.commit()
    db.refresh(new_alias)

    return {
        "id": new_alias.id,
        "alias": new_alias.alias,
        "product_name": product.name,
        "message": f"Alias '{alias}' agregado para '{product.name}'"
    }
