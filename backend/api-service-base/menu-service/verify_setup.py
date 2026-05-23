"""
================================================================================
VERIFICATION SCRIPT
================================================================================
Verifica que todos los módulos estén correctamente importados
================================================================================
"""

import sys
from pathlib import Path

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent / "src"))

print("=" * 80)
print("VERIFICANDO SETUP DEL SISTEMA")
print("=" * 80)

# Test 1: Verificar imports de modelos
print("\n1. Verificando modelos...")
try:
    from src.models.user import User
    from src.models.order import Order, OrderItem, OrderStatus, PaymentMethod, DeliveryType
    from src.models.tenant import Tenant
    from src.models.address import Address
    from src.models.review import Review
    from src.models.loyalty import LoyaltyAccount, Reward, LoyaltyTransaction, LoyaltyLevel
    print("   ✓ Todos los modelos importados correctamente")
except Exception as e:
    print(f"   ✗ Error importando modelos: {e}")
    sys.exit(1)

# Test 2: Verificar imports de schemas
print("\n2. Verificando schemas...")
try:
    from src.schemas.auth import RegisterRequest, LoginRequest, UserResponse
    from src.schemas.order import CreateOrderRequest, OrderResponse
    from src.schemas.tenant import TenantResponse
    from src.schemas.address import AddressCreate, AddressResponse
    from src.schemas.review import ReviewCreate, ReviewResponse
    from src.schemas.loyalty import LoyaltyAccountResponse, RewardResponse
    print("   ✓ Todos los schemas importados correctamente")
except Exception as e:
    print(f"   ✗ Error importando schemas: {e}")
    sys.exit(1)

# Test 3: Verificar imports de routers
print("\n3. Verificando routers...")
try:
    from src.routers import auth, orders, tenants, addresses, reviews, loyalty
    print("   ✓ Todos los routers importados correctamente")
except Exception as e:
    print(f"   ✗ Error importando routers: {e}")
    sys.exit(1)

# Test 4: Verificar Socket.IO
print("\n4. Verificando Socket.IO...")
try:
    from src.socketio_server import sio, socket_app
    print("   ✓ Socket.IO importado correctamente")
except Exception as e:
    print(f"   ✗ Error importando Socket.IO: {e}")
    sys.exit(1)

# Test 5: Verificar main app
print("\n5. Verificando aplicación principal...")
try:
    from src.main import app
    print("   ✓ Aplicación principal importada correctamente")
except Exception as e:
    print(f"   ✗ Error importando aplicación: {e}")
    sys.exit(1)

# Test 6: Verificar routers registrados
print("\n6. Verificando routers registrados...")
try:
    routes = [route.path for route in app.routes]

    required_prefixes = [
        "/api/v1/auth",
        "/api/v1/orders",
        "/api/v1/tenants",
        "/api/v1/addresses",
        "/api/v1/reviews",
        "/api/v1/loyalty",
        "/socket.io"
    ]

    missing = []
    for prefix in required_prefixes:
        found = any(prefix in route for route in routes)
        if found:
            print(f"   ✓ {prefix}")
        else:
            print(f"   ✗ {prefix} NO ENCONTRADO")
            missing.append(prefix)

    if missing:
        print(f"\n   ⚠️  Advertencia: Algunos prefijos no encontrados: {missing}")
    else:
        print("\n   ✓ Todos los routers registrados correctamente")

except Exception as e:
    print(f"   ✗ Error verificando routers: {e}")
    sys.exit(1)

# Test 7: Verificar endpoints count
print("\n7. Contando endpoints...")
try:
    api_routes = [r for r in app.routes if hasattr(r, 'methods') and r.path.startswith('/api/v1')]
    print(f"   ✓ Total de endpoints API: {len(api_routes)}")

    # Contar por módulo
    modules = {
        'auth': 0,
        'orders': 0,
        'tenants': 0,
        'addresses': 0,
        'reviews': 0,
        'loyalty': 0
    }

    for route in api_routes:
        for module in modules.keys():
            if f'/{module}' in route.path:
                modules[module] += 1

    print("\n   Endpoints por módulo:")
    for module, count in modules.items():
        print(f"     - {module.capitalize()}: {count}")

except Exception as e:
    print(f"   ✗ Error contando endpoints: {e}")

# Test 8: Verificar dependencias críticas
print("\n8. Verificando dependencias críticas...")
try:
    import fastapi
    import sqlalchemy
    import pydantic
    import socketio
    import bcrypt
    import jwt
    print("   ✓ Todas las dependencias críticas instaladas")
except ImportError as e:
    print(f"   ✗ Falta instalar dependencia: {e}")
    print("   → Ejecutar: pip install -r requirements.txt")
    sys.exit(1)

# Resumen final
print("\n" + "=" * 80)
print("VERIFICACIÓN COMPLETADA")
print("=" * 80)
print("\n✅ Sistema listo para ejecutar")
print("\nPara iniciar el servidor:")
print("  uvicorn src.main:app --reload --host 0.0.0.0 --port 8000")
print("\nDocumentación interactiva:")
print("  http://localhost:8000/docs")
print("\nSocket.IO:")
print("  ws://localhost:8000/socket.io")
print("\n" + "=" * 80)
