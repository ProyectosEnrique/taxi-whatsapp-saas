#!/usr/bin/env python3
"""
Script para agregar category_id a los productos de farmacia
basado en el mapeo de categorías del inventario.
"""
import json
from pathlib import Path

# Mapeo de categorías del inventario a category_id
# Basado en categories.json
CATEGORY_MAPPING = {
    # Medicamentos (main_category_id: 1)
    "ANTIBIOTICOS": {"main_category_id": 1, "subcategory_id": 102, "subcategory_name": "Antibióticos"},
    "ANTIGRIPALES": {"main_category_id": 1, "subcategory_id": 103, "subcategory_name": "Antigripales"},
    "ANTIGRIPAL SIN AZÚCAR": {"main_category_id": 1, "subcategory_id": 103, "subcategory_name": "Antigripales"},
    "MEDICINA GENERAL": {"main_category_id": 1, "subcategory_id": 101, "subcategory_name": "Analgésicos"},
    "PATENTE": {"main_category_id": 1, "subcategory_id": 101, "subcategory_name": "Analgésicos"},
    "GOTAS": {"main_category_id": 1, "subcategory_id": 101, "subcategory_name": "Analgésicos"},
    "ANTIDIARRÉICOS": {"main_category_id": 1, "subcategory_id": 105, "subcategory_name": "Digestivos"},

    # Vitaminas y Suplementos (main_category_id: 4)
    "VITAMINAS": {"main_category_id": 4, "subcategory_id": 401, "subcategory_name": "Multivitamínicos"},

    # Cuidado Personal (main_category_id: 2)
    "DESOD. EGO BARRA HOMBRE": {"main_category_id": 2, "subcategory_id": 204, "subcategory_name": "Desodorantes"},
    "DESOD. SPEED STICK ROLL-ON MEN 50GR": {"main_category_id": 2, "subcategory_id": 204, "subcategory_name": "Desodorantes"},
    "DESOD. SPEED TICK BARRA 50 GR": {"main_category_id": 2, "subcategory_id": 204, "subcategory_name": "Desodorantes"},
    "AGUA": {"main_category_id": 2, "subcategory_id": 203, "subcategory_name": "Cuidado de la Piel"},
    "ALCOHOL Y AGUA OXIGENADA": {"main_category_id": 7, "subcategory_id": 704, "subcategory_name": "Primeros Auxilios"},

    # Hidratación / Electrolitos (lo ponemos en Vitaminas/Suplementos)
    "ELECTROLIT": {"main_category_id": 4, "subcategory_id": 406, "subcategory_name": "Probióticos"},
    "ELECTROLITOS EN POLVO": {"main_category_id": 4, "subcategory_id": 406, "subcategory_name": "Probióticos"},
    "SOLURAL": {"main_category_id": 4, "subcategory_id": 406, "subcategory_name": "Probióticos"},
    "SUEROX ALOE VERA-LYCHE": {"main_category_id": 4, "subcategory_id": 406, "subcategory_name": "Probióticos"},

    # Equipo Médico (main_category_id: 7)
    "JERINGAS": {"main_category_id": 7, "subcategory_id": 704, "subcategory_name": "Primeros Auxilios"},

    # Vitrina / Varios (los ponemos en una categoría general)
    "VITRINA": {"main_category_id": 2, "subcategory_id": 203, "subcategory_name": "Cuidado de la Piel"},
    "CAJITA DE VITRINA": {"main_category_id": 2, "subcategory_id": 203, "subcategory_name": "Cuidado de la Piel"},

    # Ofertas (categoría especial)
    "OFERTAS": {"main_category_id": 1, "subcategory_id": 101, "subcategory_name": "Analgésicos", "is_offer": True},
}

# Mapeo de nombres de categoría principal
MAIN_CATEGORY_NAMES = {
    1: "Medicamentos",
    2: "Cuidado Personal",
    3: "Bebés y Niños",
    4: "Vitaminas y Suplementos",
    5: "Dermocosméticos",
    6: "Salud Sexual",
    7: "Equipo Médico",
    8: "Naturistas",
}


def normalize_category(category: str) -> str:
    """Normaliza el nombre de categoría para el mapeo"""
    if not category:
        return "MEDICINA GENERAL"

    # Normalizar caracteres especiales
    normalized = category.upper().strip()
    normalized = normalized.replace("Á", "A").replace("É", "E").replace("Í", "I").replace("Ó", "O").replace("Ú", "U")

    # Buscar coincidencia exacta primero
    for key in CATEGORY_MAPPING.keys():
        key_normalized = key.upper().replace("Á", "A").replace("É", "E").replace("Í", "I").replace("Ó", "O").replace("Ú", "U")
        if normalized == key_normalized:
            return key

    # Buscar coincidencia parcial
    for key in CATEGORY_MAPPING.keys():
        key_normalized = key.upper().replace("Á", "A").replace("É", "E").replace("Í", "I").replace("Ó", "O").replace("Ú", "U")
        if key_normalized in normalized or normalized in key_normalized:
            return key

    # Si empieza con "DESOD"
    if normalized.startswith("DESOD"):
        return "DESOD. EGO BARRA HOMBRE"

    # Default
    return "MEDICINA GENERAL"


def process_products():
    """Procesa productos y agrega category_id"""

    # Rutas
    config_path = Path(__file__).parent.parent / 'config' / 'pharmacy' / 'tenant_pharmacy_001'
    products_path = config_path / 'products.json'

    print(f"[INFO] Leyendo: {products_path}")

    with open(products_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    products = data.get('products', [])
    print(f"[INFO] Total productos: {len(products)}")

    # Contadores
    stats = {
        "updated": 0,
        "by_main_category": {},
        "by_subcategory": {},
        "unmapped": []
    }

    # Procesar cada producto
    for product in products:
        original_category = product.get('category', '')
        mapped_key = normalize_category(original_category)

        if mapped_key in CATEGORY_MAPPING:
            mapping = CATEGORY_MAPPING[mapped_key]

            # Agregar IDs de categoría
            product['main_category_id'] = mapping['main_category_id']
            product['subcategory_id'] = mapping['subcategory_id']
            product['main_category_name'] = MAIN_CATEGORY_NAMES.get(mapping['main_category_id'], 'Otros')
            product['subcategory_name'] = mapping['subcategory_name']

            if mapping.get('is_offer'):
                product['is_offer'] = True

            stats['updated'] += 1

            # Estadísticas
            main_cat = product['main_category_name']
            stats['by_main_category'][main_cat] = stats['by_main_category'].get(main_cat, 0) + 1

            sub_cat = product['subcategory_name']
            stats['by_subcategory'][sub_cat] = stats['by_subcategory'].get(sub_cat, 0) + 1
        else:
            stats['unmapped'].append(original_category)

    # Guardar
    output_path = products_path
    print(f"[INFO] Guardando: {output_path}")

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # Mostrar estadísticas
    print("\n" + "="*50)
    print("ESTADISTICAS")
    print("="*50)
    print(f"[OK] Productos actualizados: {stats['updated']}")

    print("\nPor categoria principal:")
    for cat, count in sorted(stats['by_main_category'].items(), key=lambda x: -x[1]):
        print(f"   {cat}: {count}")

    print("\nPor subcategoria:")
    for cat, count in sorted(stats['by_subcategory'].items(), key=lambda x: -x[1]):
        print(f"   {cat}: {count}")

    if stats['unmapped']:
        print(f"\n[WARN] Categorias sin mapear: {set(stats['unmapped'])}")

    print("\n[OK] Proceso completado!")


if __name__ == '__main__':
    process_products()
