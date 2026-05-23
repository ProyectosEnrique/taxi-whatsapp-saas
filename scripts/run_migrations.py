#!/usr/bin/env python3
"""
Script para ejecutar migraciones de base de datos
Crea todas las tablas necesarias incluyendo driver_schedules
"""

import sys
import os

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend', 'sales-agent-base'))

try:
    from src.models.taxi_models import create_tables, Base
    from src.database.connection import get_engine

    print("=" * 60)
    print("EJECUTANDO MIGRACIONES DE BASE DE DATOS")
    print("=" * 60)
    print()

    # Obtener engine
    engine = get_engine()

    print("✓ Conexión a base de datos establecida")
    print(f"  Engine: {engine}")
    print()

    # Listar tablas que se crearán
    print("Tablas a crear:")
    for table in Base.metadata.sorted_tables:
        print(f"  - {table.name}")
    print()

    # Crear tablas
    print("Creando tablas...")
    create_tables(engine)

    print()
    print("=" * 60)
    print("✅ MIGRACIONES COMPLETADAS EXITOSAMENTE")
    print("=" * 60)
    print()
    print("Tablas creadas:")
    print("  - drivers")
    print("  - vehicles")
    print("  - customers")
    print("  - rides")
    print("  - ratings")
    print("  - promo_codes")
    print("  - driver_schedules (NUEVA)")
    print()

except ImportError as e:
    print()
    print("❌ ERROR: No se pudieron importar los modelos")
    print(f"  {e}")
    print()
    print("Asegúrate de estar en el directorio correcto:")
    print("  cd C:\\Users\\ASUS\\Desktop\\PROYECTOS_AGENTE_VENTAS\\PROYECTO_B_WHATSAPP_SAAS")
    print()
    sys.exit(1)

except Exception as e:
    print()
    print("❌ ERROR durante las migraciones:")
    print(f"  {e}")
    print()
    sys.exit(1)
