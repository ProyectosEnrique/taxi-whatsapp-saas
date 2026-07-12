"""
Conftest raíz — se importa antes que nada, así que aquí fijamos las variables
de entorno que src/config.py necesita (DATABASE_URL es obligatoria y no debe
apuntar a nada real: los tests nunca usan el engine de producción, sólo
override get_db con SQLite en memoria) y agregamos este directorio a
sys.path para que `import src...` funcione igual que en el contenedor
(WORKDIR /app, `uvicorn src.main:app`).
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test_db")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("MERCADOPAGO_ACCESS_TOKEN", "test-mp-token")
os.environ.setdefault("MERCADOPAGO_CLIENT_ID", "test-mp-client-id")
os.environ.setdefault("MERCADOPAGO_CLIENT_SECRET", "test-mp-client-secret")
