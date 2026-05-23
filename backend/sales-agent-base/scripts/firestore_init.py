#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Firestore Initialization Script

Inicializa la estructura de Firestore para el sistema multi-tenant.
Crea las colecciones necesarias y configura índices.

Uso:
    python scripts/firestore_init.py
"""

import sys
from pathlib import Path

# Agregar directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from google.cloud import firestore
    from google.api_core import exceptions
except ImportError:
    print("❌ ERROR: google-cloud-firestore no está instalado")
    print("   Instalar con: pip install google-cloud-firestore")
    sys.exit(1)

def init_firestore():
    """Inicializa estructura de Firestore"""
    print("=" * 70)
    print("  FIRESTORE INITIALIZATION - Multi-Tenant System")
    print("=" * 70)
    print()

    # Conectar a Firestore
    try:
        db = firestore.Client()
        print("✅ Conectado a Firestore")
    except Exception as e:
        print(f"❌ Error conectando a Firestore: {e}")
        print()
        print("Verifica:")
        print("  1. Google Cloud SDK instalado: gcloud init")
        print("  2. Variable GOOGLE_APPLICATION_CREDENTIALS configurada")
        print("  3. Proyecto configurado: gcloud config set project PROJECT_ID")
        return False

    print()

    # Verificar/Crear colecciones
    collections = ['tenants', 'products', 'sessions', 'orders', 'customers']

    print("📁 Verificando colecciones...")
    print()

    for collection_name in collections:
        try:
            # Verificar si existe creando un documento temporal
            test_doc = db.collection(collection_name).document('__init__')

            # Verificar si ya existe
            if test_doc.get().exists:
                print(f"✅ Colección '{collection_name}' ya existe")
            else:
                # Crear documento de inicialización
                test_doc.set({
                    '_initialized': True,
                    '_created_at': firestore.SERVER_TIMESTAMP
                })
                print(f"✅ Colección '{collection_name}' creada")

        except Exception as e:
            print(f"❌ Error con colección '{collection_name}': {e}")

    print()

    # Crear índices compuestos (si es necesario)
    print("🔍 Configuración de índices...")
    print()
    print("ℹ️  Los índices compuestos se crean automáticamente al ejecutar queries")
    print("   Si necesitas índices específicos, créalos manualmente en Firebase Console")

    print()
    print("=" * 70)
    print("  ✅ FIRESTORE INICIALIZADO")
    print("=" * 70)
    print()
    print("Siguiente paso:")
    print("  python scripts/add_tenant.py --help")
    print()

    return True


if __name__ == '__main__':
    success = init_firestore()
    sys.exit(0 if success else 1)
