#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Add Tenant Script

Agrega un nuevo tenant al sistema multi-tenant en Firestore.

Uso:
    python scripts/add_tenant.py --id tenant_001 --name "Mi Tienda" --type restaurant --phone "+5215512345678"
    python scripts/add_tenant.py --interactive
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime

# Agregar directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from google.cloud import firestore
except ImportError:
    print("❌ ERROR: google-cloud-firestore no está instalado")
    print("   Instalar con: pip install google-cloud-firestore")
    sys.exit(1)


def add_tenant(tenant_id, name, business_type, phone, **kwargs):
    """
    Agrega un tenant a Firestore

    Args:
        tenant_id: ID único del tenant
        name: Nombre del negocio
        business_type: Tipo de negocio (wine_store, pharmacy, restaurant, generic)
        phone: Número de teléfono de WhatsApp
        **kwargs: Configuración adicional
    """
    try:
        db = firestore.Client()
        print("✅ Conectado a Firestore")
    except Exception as e:
        print(f"❌ Error conectando a Firestore: {e}")
        return False

    print()
    print("=" * 70)
    print(f"  Agregando tenant: {tenant_id}")
    print("=" * 70)
    print()

    # Verificar si ya existe
    tenant_ref = db.collection('tenants').document(tenant_id)

    if tenant_ref.get().exists:
        print(f"⚠️  Tenant {tenant_id} ya existe")
        response = input("¿Sobrescribir? (s/N): ").strip().lower()

        if response != 's':
            print("❌ Operación cancelada")
            return False

    # Configuración por defecto según tipo de negocio
    default_configs = {
        'wine_store': {
            'fsm_config': {
                'decision_tree_version': 'wine_v1',
                'llm_fallback_enabled': True,
                'confidence_threshold': 0.8
            },
            'business_rules': {
                'min_order_amount': 200.0,
                'delivery_fee': 50.0,
                'age_verification_required': True
            },
            'branding': {
                'greeting_message': f'¡Bienvenido a {name}! ¿En qué puedo ayudarte?',
                'tone': 'formal',
                'language': 'es-MX'
            }
        },
        'pharmacy': {
            'fsm_config': {
                'decision_tree_version': 'pharmacy_v1',
                'llm_fallback_enabled': True,
                'confidence_threshold': 0.75,
                'prescription_required_check': True
            },
            'business_rules': {
                'min_order_amount': 50.0,
                'delivery_fee': 20.0,
                'prescription_verification': True
            },
            'branding': {
                'greeting_message': f'Hola, bienvenido a {name}. ¿En qué puedo ayudarte?',
                'tone': 'professional',
                'language': 'es-MX'
            }
        },
        'restaurant': {
            'fsm_config': {
                'decision_tree_version': 'restaurant_v1',
                'llm_fallback_enabled': True,
                'confidence_threshold': 0.7
            },
            'business_rules': {
                'min_order_amount': 100.0,
                'delivery_fee': 30.0
            },
            'branding': {
                'greeting_message': f'¡Hola! Bienvenido a {name}. ¿En qué puedo ayudarte?',
                'tone': 'friendly',
                'language': 'es-MX'
            }
        },
        'generic': {
            'fsm_config': {
                'decision_tree_version': 'generic_v1',
                'llm_fallback_enabled': True,
                'confidence_threshold': 0.7
            },
            'business_rules': {
                'min_order_amount': 100.0,
                'delivery_fee': 30.0
            },
            'branding': {
                'greeting_message': f'¡Hola! Bienvenido a {name}. ¿En qué puedo ayudarte?',
                'tone': 'neutral',
                'language': 'es-MX'
            }
        }
    }

    # Obtener configuración por defecto
    config = default_configs.get(business_type, default_configs['generic'])

    # Construir documento de tenant
    tenant_data = {
        'business_info': {
            'name': name,
            'type': business_type,
            'phone': phone,
            'address': kwargs.get('address', ''),
            'logo_url': kwargs.get('logo_url', ''),
            'active': kwargs.get('active', True)
        },
        'fsm_config': kwargs.get('fsm_config', config['fsm_config']),
        'business_rules': kwargs.get('business_rules', config['business_rules']),
        'branding': kwargs.get('branding', config['branding']),
        'created_at': firestore.SERVER_TIMESTAMP,
        'updated_at': firestore.SERVER_TIMESTAMP
    }

    # Guardar en Firestore
    try:
        tenant_ref.set(tenant_data)

        print("✅ Tenant creado exitosamente")
        print()
        print("Detalles:")
        print(f"  ID: {tenant_id}")
        print(f"  Nombre: {name}")
        print(f"  Tipo: {business_type}")
        print(f"  Teléfono: {phone}")
        print(f"  Activo: {tenant_data['business_info']['active']}")
        print()
        print("Siguiente paso:")
        print(f"  python scripts/add_products.py --tenant {tenant_id}")
        print()

        return True

    except Exception as e:
        print(f"❌ Error guardando tenant: {e}")
        return False


def interactive_mode():
    """Modo interactivo para agregar tenant"""
    print("=" * 70)
    print("  AGREGAR TENANT - Modo Interactivo")
    print("=" * 70)
    print()

    # Solicitar información
    tenant_id = input("ID del tenant (ej: tenant_001): ").strip()

    if not tenant_id:
        print("❌ ID requerido")
        return False

    name = input("Nombre del negocio: ").strip()

    if not name:
        print("❌ Nombre requerido")
        return False

    print()
    print("Tipos de negocio disponibles:")
    print("  1. wine_store   - Vinetería")
    print("  2. pharmacy     - Farmacia")
    print("  3. restaurant   - Restaurante")
    print("  4. generic      - Genérico")
    print()

    type_choice = input("Selecciona tipo (1-4): ").strip()

    type_map = {
        '1': 'wine_store',
        '2': 'pharmacy',
        '3': 'restaurant',
        '4': 'generic'
    }

    business_type = type_map.get(type_choice, 'generic')

    phone = input("Teléfono WhatsApp (ej: +5215512345678): ").strip()

    if not phone:
        print("❌ Teléfono requerido")
        return False

    address = input("Dirección (opcional): ").strip()

    print()
    print("Confirmación:")
    print(f"  ID: {tenant_id}")
    print(f"  Nombre: {name}")
    print(f"  Tipo: {business_type}")
    print(f"  Teléfono: {phone}")
    print(f"  Dirección: {address or 'N/A'}")
    print()

    confirm = input("¿Crear tenant? (S/n): ").strip().lower()

    if confirm and confirm != 's':
        print("❌ Operación cancelada")
        return False

    return add_tenant(
        tenant_id=tenant_id,
        name=name,
        business_type=business_type,
        phone=phone,
        address=address
    )


def main():
    parser = argparse.ArgumentParser(description='Agregar tenant al sistema multi-tenant')

    parser.add_argument('--id', help='ID del tenant')
    parser.add_argument('--name', help='Nombre del negocio')
    parser.add_argument('--type', choices=['wine_store', 'pharmacy', 'restaurant', 'generic'], help='Tipo de negocio')
    parser.add_argument('--phone', help='Teléfono WhatsApp')
    parser.add_argument('--address', help='Dirección (opcional)')
    parser.add_argument('--logo-url', help='URL del logo (opcional)')
    parser.add_argument('--active', type=bool, default=True, help='Tenant activo (default: True)')
    parser.add_argument('--interactive', '-i', action='store_true', help='Modo interactivo')

    args = parser.parse_args()

    # Modo interactivo
    if args.interactive:
        success = interactive_mode()
    # Modo con argumentos
    elif args.id and args.name and args.type and args.phone:
        success = add_tenant(
            tenant_id=args.id,
            name=args.name,
            business_type=args.type,
            phone=args.phone,
            address=args.address or '',
            logo_url=args.logo_url or '',
            active=args.active
        )
    else:
        parser.print_help()
        print()
        print("Ejemplos:")
        print("  python scripts/add_tenant.py --interactive")
        print("  python scripts/add_tenant.py --id tenant_001 --name \"Mi Vinetería\" --type wine_store --phone \"+5215512345678\"")
        success = False

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
