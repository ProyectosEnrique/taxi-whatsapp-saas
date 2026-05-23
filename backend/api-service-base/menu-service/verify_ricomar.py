"""Verificar datos de Rico Mar en la base de datos"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.database import SessionLocal
from src.models import Tenant, Product, Category

db = SessionLocal()

try:
    # Verificar tenant
    tenant = db.query(Tenant).filter(Tenant.tenant_id == 'rico-mar-salvatierra').first()
    if tenant:
        print(f'[OK] Tenant: {tenant.name}')
        print(f'[OK] WhatsApp: {tenant.whatsapp_number}')
        print(f'[OK] Email: {tenant.email}')
    else:
        print('[ERROR] Tenant no encontrado')
        sys.exit(1)

    # Contar categorías
    categories = db.query(Category).filter(Category.tenant_id == 'rico-mar-salvatierra').count()
    print(f'[OK] Categorias: {categories}')

    # Contar productos
    products = db.query(Product).filter(Product.tenant_id == 'rico-mar-salvatierra').count()
    print(f'[OK] Productos: {products}')

    # Mostrar 5 productos de ejemplo
    print('\n[EJEMPLO] Primeros 5 productos:')
    sample_products = db.query(Product).filter(Product.tenant_id == 'rico-mar-salvatierra').limit(5).all()
    for p in sample_products:
        cat = db.query(Category).filter(Category.id == p.category_id).first()
        cat_name = cat.name if cat else "Sin categoria"
        print(f'  - [{cat_name}] {p.name}: ${p.price}')

    print('\n[OK] Base de datos verificada correctamente!')

except Exception as e:
    print(f'[ERROR] {e}')
    import traceback
    traceback.print_exc()
finally:
    db.close()
