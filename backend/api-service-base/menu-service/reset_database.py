"""
================================================================================
RESET DATABASE SCRIPT
================================================================================
Script para limpiar completamente la base de datos y empezar de nuevo
================================================================================

⚠️ ADVERTENCIA: Este script ELIMINARÁ TODOS LOS DATOS

Uso:
    python reset_database.py

"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.database import engine
from src.models.database import Base

print("=" * 80)
print("⚠️  ADVERTENCIA: RESET DE BASE DE DATOS")
print("=" * 80)
print("\nEste script eliminará TODAS las tablas y datos.")
print("No se puede deshacer esta operación.")

response = input("\n¿Estás seguro? Escribe 'SI' para continuar: ")

if response != "SI":
    print("\n❌ Operación cancelada")
    sys.exit(0)

print("\n🗑️  Eliminando todas las tablas...")
Base.metadata.drop_all(bind=engine)
print("   ✓ Tablas eliminadas")

print("\n📦 Creando tablas limpias...")
Base.metadata.create_all(bind=engine)
print("   ✓ Tablas creadas")

print("\n" + "=" * 80)
print("✅ BASE DE DATOS RESETEADA")
print("=" * 80)
print("\n💡 Ahora puedes ejecutar:")
print("   python seed_data.py")
print("\n" + "=" * 80)
