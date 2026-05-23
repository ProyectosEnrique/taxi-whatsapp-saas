# 🍽️ MENU SERVICE (CAPA 11)

Servicio de gestión de menú y productos para el sistema de restaurante.

---

## 📋 DESCRIPCIÓN

El **Menu Service** es responsable de:
- Gestión de categorías de productos
- CRUD completo de productos del menú
- Filtrado y búsqueda de productos
- Control de disponibilidad de productos
- Asociación de productos con categorías

---

## 🏗️ ARQUITECTURA

```
11_menu_service/
├── src/
│   ├── main.py              # Aplicación FastAPI principal
│   ├── config.py            # Configuración con Pydantic Settings
│   ├── database.py          # Conexión SQLAlchemy
│   ├── models.py            # Modelos SQLAlchemy (Category, Product)
│   ├── schemas.py           # Schemas Pydantic para validación
│   └── routers/
│       ├── products.py      # Endpoints de productos
│       └── categories.py    # Endpoints de categorías
├── tests/
│   ├── unit/                # Tests unitarios
│   └── integration/         # Tests de integración
├── config/
│   └── database.yaml        # Configuración de base de datos
├── Dockerfile               # Imagen Docker
├── requirements.txt         # Dependencias Python
└── README.md                # Este archivo
```

---

## 🔗 ENDPOINTS

### Productos

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/api/v1/products` | Listar productos (con filtros) |
| `GET` | `/api/v1/products/{id}` | Obtener producto por ID |
| `POST` | `/api/v1/products` | Crear nuevo producto |
| `PUT` | `/api/v1/products/{id}` | Actualizar producto |
| `DELETE` | `/api/v1/products/{id}` | Eliminar producto |
| `PATCH` | `/api/v1/products/{id}/availability` | Cambiar disponibilidad |

### Categorías

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/api/v1/categories` | Listar categorías |
| `GET` | `/api/v1/categories/{id}` | Obtener categoría por ID |
| `GET` | `/api/v1/categories/{id}/products` | Obtener categoría con productos |
| `POST` | `/api/v1/categories` | Crear nueva categoría |
| `PUT` | `/api/v1/categories/{id}` | Actualizar categoría |
| `DELETE` | `/api/v1/categories/{id}` | Eliminar categoría |

### Utilidad

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `GET` | `/ready` | Readiness check |
| `GET` | `/metrics` | Métricas Prometheus |
| `GET` | `/docs` | Documentación Swagger |

---

## 🚀 QUICK START

### Desarrollo Local (sin Docker)

```bash
# Ir al directorio del servicio
cd BACKEND/services/11_menu_service

# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
export DATABASE_URL="postgresql://restaurante:password@localhost:5432/restaurante_db"
export LOG_LEVEL="DEBUG"

# Ejecutar servicio
uvicorn src.main:app --reload --host 0.0.0.0 --port 5011
```

### Con Docker Compose

```bash
# Desde la carpeta INFRASTRUCTURE
cd ../../INFRASTRUCTURE

# Iniciar solo este servicio
docker-compose up -d postgres menu_service

# Ver logs
docker-compose logs -f menu_service
```

---

## 📊 MODELOS DE DATOS

### Category

```python
{
    "id": 1,
    "name": "Platos Fuertes",
    "description": "Platillos principales",
    "display_order": 1,
    "is_active": true,
    "created_at": "2025-11-10T10:00:00Z",
    "updated_at": "2025-11-10T10:00:00Z"
}
```

### Product

```python
{
    "id": 1,
    "uuid": "550e8400-e29b-41d4-a716-446655440000",
    "category_id": 1,
    "name": "Tacos de Carne Asada",
    "description": "Orden de 4 tacos con tortilla de maíz",
    "price": 150.00,
    "image_url": "https://example.com/tacos.jpg",
    "is_available": true,
    "preparation_time_minutes": 20,
    "created_at": "2025-11-10T10:00:00Z",
    "updated_at": "2025-11-10T10:00:00Z"
}
```

---

## 🧪 TESTING

### Ejecutar Tests

```bash
# Tests unitarios
pytest tests/unit/

# Tests de integración
pytest tests/integration/

# Coverage
pytest --cov=src --cov-report=html
```

### Ejemplos de Tests

```python
# tests/unit/test_products.py
def test_create_product():
    """Test de creación de producto"""
    response = client.post("/api/v1/products", json={
        "name": "Test Product",
        "price": 100.00,
        "category_id": 1
    })
    assert response.status_code == 201
    assert response.json()["name"] == "Test Product"
```

---

## 📡 EJEMPLOS DE USO

### Crear Categoría

```bash
curl -X POST http://localhost:5011/api/v1/categories \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Bebidas",
    "description": "Bebidas frías y calientes",
    "display_order": 3
  }'
```

### Listar Productos

```bash
# Todos los productos
curl http://localhost:5011/api/v1/products

# Solo disponibles de categoría 1
curl "http://localhost:5011/api/v1/products?category_id=1&available_only=true"

# Buscar por nombre
curl "http://localhost:5011/api/v1/products?search=taco"
```

### Crear Producto

```bash
curl -X POST http://localhost:5011/api/v1/products \
  -H "Content-Type: application/json" \
  -d '{
    "category_id": 1,
    "name": "Enchiladas Verdes",
    "description": "Enchiladas con salsa verde y queso",
    "price": 135.00,
    "is_available": true,
    "preparation_time_minutes": 25
  }'
```

### Actualizar Disponibilidad

```bash
curl -X PATCH "http://localhost:5011/api/v1/products/1/availability?is_available=false"
```

---

## ⚙️ CONFIGURACIÓN

### Variables de Entorno

```bash
# Base de datos
DATABASE_URL=postgresql://user:password@host:port/database

# Logging
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL

# CORS
CORS_ORIGINS=http://localhost:8080,http://localhost:8081

# Servicio
SERVICE_NAME=menu_service
ENVIRONMENT=development  # development, staging, production
```

---

## 🔍 MONITOREO

### Logs Estructurados (JSON)

```json
{
  "timestamp": "2025-11-10T10:30:00Z",
  "level": "INFO",
  "service": "menu_service",
  "message": "Request completed",
  "correlation_id": "req-abc-123",
  "method": "GET",
  "path": "/api/v1/products",
  "status_code": 200,
  "duration_seconds": 0.045
}
```

### Métricas Prometheus

```bash
# Acceder a métricas
curl http://localhost:5011/metrics

# Métricas disponibles:
# - http_requests_total (contador)
# - http_request_duration_seconds (histograma)
```

---

## 🐛 TROUBLESHOOTING

### Error: Cannot connect to database

```bash
# Verificar que PostgreSQL está corriendo
docker ps | grep postgres

# Verificar string de conexión
echo $DATABASE_URL

# Test de conexión manual
psql $DATABASE_URL
```

### Error: Import errors

```bash
# Reinstalar dependencias
pip install --no-cache-dir -r requirements.txt

# Verificar estructura de carpetas
ls -la src/
```

---

## 📚 DOCUMENTACIÓN ADICIONAL

- **API Docs (Swagger):** http://localhost:5011/docs
- **ReDoc:** http://localhost:5011/redoc
- **OpenAPI JSON:** http://localhost:5011/openapi.json

---

## 🔄 MIGRACIÓN DE BASE DE DATOS (Alembic)

```bash
# Inicializar Alembic (primera vez)
alembic init alembic

# Crear migración
alembic revision --autogenerate -m "Add products table"

# Aplicar migraciones
alembic upgrade head

# Rollback
alembic downgrade -1
```

---

## 🤝 CONTRIBUCIÓN

Para agregar nuevos endpoints:

1. Agregar schema en `schemas.py`
2. Crear router en `routers/`
3. Incluir router en `main.py`
4. Agregar tests en `tests/`
5. Documentar en este README

---

**Versión:** 1.0.0
**Puerto:** 5011
**Base de Datos:** PostgreSQL
**Framework:** FastAPI
