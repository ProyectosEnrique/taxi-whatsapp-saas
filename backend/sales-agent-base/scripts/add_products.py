#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Add Products Script

Agrega productos a un tenant en Firestore.
Puede cargar desde archivo JSON o agregar interactivamente.

Uso:
    python scripts/add_products.py --tenant tenant_001 --file products.json
    python scripts/add_products.py --tenant tenant_001 --interactive
"""

import sys
import json
import argparse
from pathlib import Path

# Agregar directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from google.cloud import firestore
except ImportError:
    print("❌ ERROR: google-cloud-firestore no está instalado")
    print("   Instalar con: pip install google-cloud-firestore")
    sys.exit(1)


def add_products_from_json(tenant_id, json_file):
    """
    Agrega productos desde un archivo JSON

    Args:
        tenant_id: ID del tenant
        json_file: Ruta al archivo JSON con productos
    """
    try:
        db = firestore.Client()
        print("✅ Conectado a Firestore")
    except Exception as e:
        print(f"❌ Error conectando a Firestore: {e}")
        return False

    # Leer archivo JSON
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        products = data.get('products', [])

        if not products:
            print(f"⚠️  No se encontraron productos en {json_file}")
            return False

        print(f"📦 Cargando {len(products)} productos para tenant {tenant_id}...")
        print()

    except FileNotFoundError:
        print(f"❌ Archivo no encontrado: {json_file}")
        return False
    except json.JSONDecodeError as e:
        print(f"❌ Error parseando JSON: {e}")
        return False

    # Agregar productos
    added = 0
    errors = 0

    for product in products:
        try:
            # Generar ID del documento
            product_id = product.get('product_id', f"product_{added+1:03d}")
            doc_id = f"{tenant_id}_{product_id}"

            # Agregar tenant_id al producto
            product['tenant_id'] = tenant_id

            # Guardar en Firestore
            db.collection('products').document(doc_id).set(product)

            print(f"✅ {product.get('name', 'Sin nombre')} ({doc_id})")
            added += 1

        except Exception as e:
            print(f"❌ Error agregando producto: {e}")
            errors += 1

    print()
    print("=" * 70)
    print(f"  ✅ PRODUCTOS AGREGADOS: {added}")
    if errors > 0:
        print(f"  ❌ ERRORES: {errors}")
    print("=" * 70)
    print()

    return errors == 0


def add_product_interactive(tenant_id):
    """
    Agrega un producto interactivamente

    Args:
        tenant_id: ID del tenant
    """
    try:
        db = firestore.Client()
    except Exception as e:
        print(f"❌ Error conectando a Firestore: {e}")
        return False

    print("=" * 70)
    print(f"  AGREGAR PRODUCTO - Tenant: {tenant_id}")
    print("=" * 70)
    print()

    # Solicitar información del producto
    product_id = input("ID del producto (ej: product_001): ").strip()

    if not product_id:
        print("❌ ID requerido")
        return False

    name = input("Nombre del producto: ").strip()

    if not name:
        print("❌ Nombre requerido")
        return False

    category = input("Categoría (ej: bebidas, comida, medicinas): ").strip()
    price = input("Precio: ").strip()

    try:
        price = float(price)
    except ValueError:
        print("❌ Precio inválido")
        return False

    description = input("Descripción (opcional): ").strip()
    aliases_input = input("Aliases separados por coma (opcional): ").strip()
    aliases = [a.strip() for a in aliases_input.split(',')] if aliases_input else []

    stock_input = input("Stock disponible (opcional): ").strip()
    stock = int(stock_input) if stock_input else None

    # Construir documento de producto
    product_data = {
        'tenant_id': tenant_id,
        'product_id': product_id,
        'name': name,
        'category': category,
        'price': price,
        'description': description,
        'aliases': aliases,
        'active': True,
        'created_at': firestore.SERVER_TIMESTAMP
    }

    if stock is not None:
        product_data['stock'] = stock

    # Confirmar
    print()
    print("Confirmación:")
    print(f"  ID: {product_id}")
    print(f"  Nombre: {name}")
    print(f"  Categoría: {category}")
    print(f"  Precio: ${price:.2f}")
    if aliases:
        print(f"  Aliases: {', '.join(aliases)}")
    if stock is not None:
        print(f"  Stock: {stock}")
    print()

    confirm = input("¿Agregar producto? (S/n): ").strip().lower()

    if confirm and confirm != 's':
        print("❌ Operación cancelada")
        return False

    # Guardar en Firestore
    try:
        doc_id = f"{tenant_id}_{product_id}"
        db.collection('products').document(doc_id).set(product_data)

        print()
        print(f"✅ Producto agregado: {name} ({doc_id})")
        print()

        # Preguntar si desea agregar otro
        another = input("¿Agregar otro producto? (s/N): ").strip().lower()

        if another == 's':
            return add_product_interactive(tenant_id)

        return True

    except Exception as e:
        print(f"❌ Error guardando producto: {e}")
        return False


def create_sample_json(output_file):
    """Crea un archivo JSON de ejemplo"""
    sample_data = {
        "products": [
            {
                "product_id": "product_001",
                "name": "Producto Ejemplo 1",
                "category": "categoria1",
                "price": 100.0,
                "description": "Descripción del producto",
                "aliases": ["alias1", "alias2"],
                "stock": 50,
                "active": True
            },
            {
                "product_id": "product_002",
                "name": "Producto Ejemplo 2",
                "category": "categoria2",
                "price": 150.0,
                "description": "Otro producto",
                "aliases": ["alias3"],
                "stock": 30,
                "active": True
            }
        ]
    }

    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(sample_data, f, indent=2, ensure_ascii=False)

        print(f"✅ Archivo de ejemplo creado: {output_file}")
        print()
        print(f"Edita {output_file} y luego ejecuta:")
        print(f"  python scripts/add_products.py --tenant TENANT_ID --file {output_file}")
        print()

        return True

    except Exception as e:
        print(f"❌ Error creando archivo: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description='Agregar productos a un tenant')

    parser.add_argument('--tenant', required=False, help='ID del tenant')
    parser.add_argument('--file', help='Archivo JSON con productos')
    parser.add_argument('--interactive', '-i', action='store_true', help='Modo interactivo')
    parser.add_argument('--sample', help='Crear archivo JSON de ejemplo')

    args = parser.parse_args()

    # Crear archivo de ejemplo
    if args.sample:
        success = create_sample_json(args.sample)
        sys.exit(0 if success else 1)

    # Validar tenant_id
    if not args.tenant:
        parser.print_help()
        print()
        print("Ejemplos:")
        print("  python scripts/add_products.py --sample products_ejemplo.json")
        print("  python scripts/add_products.py --tenant tenant_001 --file products.json")
        print("  python scripts/add_products.py --tenant tenant_001 --interactive")
        sys.exit(1)

    # Modo con archivo JSON
    if args.file:
        success = add_products_from_json(args.tenant, args.file)
    # Modo interactivo
    elif args.interactive:
        success = add_product_interactive(args.tenant)
    else:
        parser.print_help()
        success = False

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
