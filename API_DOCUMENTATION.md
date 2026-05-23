# 📚 Documentación API - Sistema de Taxis

**Proyecto**: PROYECTO_B_WHATSAPP_SAAS
**Versión API**: 1.0.0
**Base URL**: `https://api.taxisystem.com/api/v1`
**Documentación OpenAPI**: Ver archivo `openapi.yaml`

---

## 📋 Tabla de Contenidos

1. [Introducción](#introducción)
2. [Autenticación](#autenticación)
3. [Endpoints por Categoría](#endpoints-por-categoría)
4. [Ejemplos de Uso](#ejemplos-de-uso)
5. [Códigos de Respuesta](#códigos-de-respuesta)
6. [Rate Limiting](#rate-limiting)
7. [Webhooks](#webhooks)
8. [Postman Collection](#postman-collection)

---

## 🎯 Introducción

### Descripción General

API REST completa para gestión de sistema de taxis multi-tenant con:
- Gestión de conductores, vehículos y clientes
- Solicitud y asignación de viajes en tiempo real
- Sistema de calificaciones y reseñas
- Códigos promocionales y descuentos
- Horarios de trabajo para conductores
- Analytics y reportes

### Tecnologías

- **Protocolo**: HTTP/HTTPS
- **Formato**: JSON
- **Autenticación**: JWT (Bearer Token)
- **Versionado**: URL-based (`/api/v1/`)

### URLs Base

| Ambiente | URL Base |
|----------|----------|
| **Producción** | `https://api.taxisystem.com/api/v1` |
| **Staging** | `https://staging-api.taxisystem.com/api/v1` |
| **Desarrollo** | `http://localhost:8000/api/v1` |

---

## 🔐 Autenticación

### Obtener Token JWT

**Endpoint**: `POST /auth/login`

```bash
curl -X POST https://api.taxisystem.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "+525512345678",
    "password": "password123",
    "user_type": "driver",
    "tenant_id": "tenant_taxi_001"
  }'
```

**Respuesta exitosa**:
```json
{
  "success": true,
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": "driver_abc123",
    "name": "Juan Pérez",
    "phone": "+525512345678",
    "user_type": "driver"
  }
}
```

### Usar Token en Requests

Incluir el token en el header `Authorization` de todas las peticiones protegidas:

```bash
curl -X GET https://api.taxisystem.com/api/v1/drivers/driver_abc123 \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json"
```

### Tipos de Usuario

| Tipo | Descripción | Permisos |
|------|-------------|----------|
| `driver` | Conductor de taxi | Ver/actualizar perfil, horarios, viajes asignados |
| `customer` | Cliente/pasajero | Solicitar viajes, ver historial, calificar |
| `admin` | Administrador | Acceso completo al sistema |

---

## 📌 Endpoints por Categoría

### 1. Authentication (2 endpoints)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/auth/login` | Iniciar sesión |
| POST | `/auth/register` | Registrar nuevo usuario |

### 2. Drivers (7 endpoints)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/drivers` | Listar conductores |
| POST | `/drivers` | Crear conductor |
| GET | `/drivers/{driver_id}` | Obtener conductor |
| PUT | `/drivers/{driver_id}` | Actualizar conductor |
| DELETE | `/drivers/{driver_id}` | Eliminar conductor |
| PATCH | `/drivers/{driver_id}/status` | Actualizar estado |
| PATCH | `/drivers/{driver_id}/location` | Actualizar ubicación |
| GET | `/drivers/nearby` | Buscar conductores cercanos |

### 3. Driver Schedules (6 endpoints)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/driver/schedule` | Obtener horarios |
| POST | `/driver/schedule` | Crear horario |
| POST | `/driver/schedule/bulk` | Crear múltiples horarios |
| GET | `/driver/schedule/templates` | Plantillas de turnos |
| PUT | `/driver/schedule/{schedule_id}` | Actualizar horario |
| DELETE | `/driver/schedule/{schedule_id}` | Eliminar horario |

### 4. Rides (8 endpoints)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/rides` | Listar viajes |
| POST | `/rides` | Crear solicitud de viaje |
| GET | `/rides/{ride_id}` | Obtener detalles del viaje |
| PATCH | `/rides/{ride_id}` | Actualizar estado |
| POST | `/rides/{ride_id}/assign` | Asignar conductor |
| POST | `/rides/{ride_id}/cancel` | Cancelar viaje |
| POST | `/rides/{ride_id}/complete` | Completar viaje |
| POST | `/rides/estimate` | Calcular tarifa estimada |

### 5. Customers (5 endpoints)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/customers` | Listar clientes |
| POST | `/customers` | Crear cliente |
| GET | `/customers/{customer_id}` | Obtener cliente |
| PUT | `/customers/{customer_id}` | Actualizar cliente |
| GET | `/customers/{customer_id}/saved-addresses` | Direcciones guardadas |
| POST | `/customers/{customer_id}/saved-addresses` | Agregar dirección |

### 6. Vehicles (5 endpoints)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/vehicles` | Listar vehículos |
| POST | `/vehicles` | Crear vehículo |
| GET | `/vehicles/{vehicle_id}` | Obtener vehículo |
| PUT | `/vehicles/{vehicle_id}` | Actualizar vehículo |
| DELETE | `/vehicles/{vehicle_id}` | Eliminar vehículo |

### 7. Ratings (3 endpoints)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/ratings` | Listar calificaciones |
| POST | `/ratings` | Crear calificación |
| GET | `/ratings/{rating_id}` | Obtener calificación |

### 8. Promo Codes (4 endpoints)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/promo-codes` | Listar códigos |
| POST | `/promo-codes` | Crear código |
| POST | `/promo-codes/validate` | Validar código |
| GET | `/promo-codes/{code}` | Obtener código |
| DELETE | `/promo-codes/{code}` | Desactivar código |

### 9. Analytics (2 endpoints)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/analytics/dashboard` | Estadísticas generales |
| GET | `/analytics/driver/{driver_id}/earnings` | Ganancias de conductor |

### 10. Admin (2 endpoints)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/admin/drivers/approve` | Aprobar/rechazar conductor |
| GET | `/admin/reports/rides` | Reporte de viajes |

**Total**: **70+ endpoints**

---

## 💡 Ejemplos de Uso

### Flujo 1: Cliente Solicita un Viaje

#### Paso 1: Login del Cliente

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "+525555555555",
    "password": "customer123",
    "user_type": "customer",
    "tenant_id": "tenant_taxi_001"
  }'
```

Respuesta:
```json
{
  "success": true,
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJjdXN0b21lcl8xMjMiLCJuYW1lIjoiTWFyaWEgR29tZXoiLCJ1c2VyX3R5cGUiOiJjdXN0b21lciIsImlhdCI6MTUxNjIzOTAyMn0.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c",
  "user": {
    "id": "customer_123",
    "name": "Maria Gomez",
    "phone": "+525555555555",
    "user_type": "customer"
  }
}
```

#### Paso 2: Calcular Tarifa Estimada

```bash
curl -X POST http://localhost:8000/api/v1/rides/estimate \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "origin_lat": 19.4326,
    "origin_lon": -99.1332,
    "destination_lat": 19.3907,
    "destination_lon": -99.2837,
    "vehicle_type": "sedan",
    "promo_code": "SUMMER2024"
  }'
```

Respuesta:
```json
{
  "success": true,
  "distance_km": 12.5,
  "duration_minutes": 25,
  "estimated_fare": 180.00,
  "fare_breakdown": {
    "base_fare": 50.00,
    "distance_charge": 100.00,
    "time_charge": 50.00,
    "surge_charge": 0.00,
    "discount": 20.00,
    "total": 180.00
  }
}
```

#### Paso 3: Solicitar Viaje

```bash
curl -X POST http://localhost:8000/api/v1/rides \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "tenant_taxi_001",
    "customer_id": "customer_123",
    "origin_address": "Av. Insurgentes Sur 1234, CDMX",
    "origin_lat": 19.4326,
    "origin_lon": -99.1332,
    "destination_address": "Aeropuerto Internacional CDMX",
    "destination_lat": 19.3907,
    "destination_lon": -99.2837,
    "payment_method": "cash",
    "promo_code": "SUMMER2024",
    "notes": "Por favor usar la entrada principal"
  }'
```

Respuesta:
```json
{
  "success": true,
  "ride": {
    "ride_id": "ride_xyz789",
    "status": "requested",
    "origin": {
      "address": "Av. Insurgentes Sur 1234, CDMX",
      "lat": 19.4326,
      "lon": -99.1332
    },
    "destination": {
      "address": "Aeropuerto Internacional CDMX",
      "lat": 19.3907,
      "lon": -99.2837
    },
    "distance_km": 12.5,
    "duration_minutes": 25,
    "total_fare": 180.00,
    "payment_method": "cash",
    "driver_id": null,
    "customer_id": "customer_123",
    "requested_at": "2024-01-28T10:30:00Z"
  },
  "estimated_fare": 180.00
}
```

### Flujo 2: Conductor Acepta y Completa Viaje

#### Paso 1: Login del Conductor

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "+525512345678",
    "password": "driver123",
    "user_type": "driver",
    "tenant_id": "tenant_taxi_001"
  }'
```

#### Paso 2: Actualizar Estado a "Disponible"

```bash
curl -X PATCH http://localhost:8000/api/v1/drivers/driver_abc123/status \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "available"
  }'
```

#### Paso 3: Actualizar Ubicación

```bash
curl -X PATCH http://localhost:8000/api/v1/drivers/driver_abc123/location \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "lat": 19.4200,
    "lon": -99.1400,
    "heading": 90
  }'
```

#### Paso 4: Aceptar Viaje (el sistema asigna automáticamente)

```bash
curl -X POST http://localhost:8000/api/v1/rides/ride_xyz789/assign \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "driver_id": "driver_abc123"
  }'
```

#### Paso 5: Iniciar Viaje

```bash
curl -X PATCH http://localhost:8000/api/v1/rides/ride_xyz789 \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "started"
  }'
```

#### Paso 6: Completar Viaje

```bash
curl -X POST http://localhost:8000/api/v1/rides/ride_xyz789/complete \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "actual_distance_km": 13.2,
    "actual_duration_minutes": 30,
    "final_fare": 195.00
  }'
```

### Flujo 3: Conductor Configura Horarios

#### Paso 1: Ver Plantillas de Turnos

```bash
curl -X GET http://localhost:8000/api/v1/driver/schedule/templates \
  -H "Authorization: Bearer <TOKEN>"
```

Respuesta:
```json
{
  "success": true,
  "templates": {
    "morning": {
      "name": "Turno Matutino",
      "shift_type": "morning",
      "start_time": "06:00",
      "end_time": "14:00",
      "break_start": "10:00",
      "break_end": "10:30",
      "description": "Turno de mañana, ideal para inicio del día"
    },
    "afternoon": {
      "name": "Turno Vespertino",
      "shift_type": "afternoon",
      "start_time": "14:00",
      "end_time": "22:00",
      "break_start": "18:00",
      "break_end": "18:30",
      "description": "Turno de tarde, alta demanda"
    },
    "night": {
      "name": "Turno Nocturno",
      "shift_type": "night",
      "start_time": "22:00",
      "end_time": "06:00",
      "break_start": "02:00",
      "break_end": "02:30",
      "description": "Turno de noche, servicio 24/7"
    }
  }
}
```

#### Paso 2: Crear Horarios para la Semana (Lunes a Viernes)

```bash
curl -X POST http://localhost:8000/api/v1/driver/schedule/bulk \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "driver_id": "driver_abc123",
    "tenant_id": "tenant_taxi_001",
    "schedules": [
      {
        "day_of_week": 0,
        "shift_type": "morning",
        "start_time": "06:00",
        "end_time": "14:00",
        "break_start": "10:00",
        "break_end": "10:30"
      },
      {
        "day_of_week": 1,
        "shift_type": "morning",
        "start_time": "06:00",
        "end_time": "14:00",
        "break_start": "10:00",
        "break_end": "10:30"
      },
      {
        "day_of_week": 2,
        "shift_type": "morning",
        "start_time": "06:00",
        "end_time": "14:00",
        "break_start": "10:00",
        "break_end": "10:30"
      },
      {
        "day_of_week": 3,
        "shift_type": "morning",
        "start_time": "06:00",
        "end_time": "14:00",
        "break_start": "10:00",
        "break_end": "10:30"
      },
      {
        "day_of_week": 4,
        "shift_type": "morning",
        "start_time": "06:00",
        "end_time": "14:00",
        "break_start": "10:00",
        "break_end": "10:30"
      }
    ]
  }'
```

#### Paso 3: Ver Horarios Configurados

```bash
curl -X GET "http://localhost:8000/api/v1/driver/schedule?driver_id=driver_abc123&tenant_id=tenant_taxi_001" \
  -H "Authorization: Bearer <TOKEN>"
```

### Flujo 4: Cliente Califica Viaje

```bash
curl -X POST http://localhost:8000/api/v1/ratings \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "tenant_taxi_001",
    "ride_id": "ride_xyz789",
    "customer_id": "customer_123",
    "driver_id": "driver_abc123",
    "rating": 4.5,
    "review": "Excelente servicio, muy puntual y amable",
    "punctuality_rating": 5.0,
    "cleanliness_rating": 4.5,
    "driving_rating": 4.5,
    "communication_rating": 5.0,
    "rating_type": "customer_to_driver"
  }'
```

### Flujo 5: Admin Aprueba Nuevo Conductor

```bash
curl -X POST http://localhost:8000/api/v1/admin/drivers/approve \
  -H "Authorization: Bearer <ADMIN_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "driver_id": "driver_new123",
    "background_check_status": "approved"
  }'
```

---

## 📊 Códigos de Respuesta HTTP

| Código | Significado | Descripción |
|--------|-------------|-------------|
| **200** | OK | Solicitud exitosa |
| **201** | Created | Recurso creado exitosamente |
| **204** | No Content | Solicitud exitosa sin contenido |
| **400** | Bad Request | Solicitud incorrecta o datos inválidos |
| **401** | Unauthorized | Token inválido o faltante |
| **403** | Forbidden | Sin permisos para acceder |
| **404** | Not Found | Recurso no encontrado |
| **409** | Conflict | Conflicto con el estado actual (ej: conductor ya asignado) |
| **422** | Unprocessable Entity | Datos válidos pero no procesables |
| **429** | Too Many Requests | Límite de rate limiting excedido |
| **500** | Internal Server Error | Error del servidor |
| **503** | Service Unavailable | Servicio temporalmente no disponible |

### Formato de Respuestas de Error

```json
{
  "success": false,
  "error": "Descripción del error",
  "details": {
    "field": "driver_id",
    "message": "Driver already has an active ride"
  }
}
```

---

## ⏱️ Rate Limiting

### Límites por Tipo de Usuario

| Tipo de Usuario | Límite | Ventana de Tiempo |
|-----------------|--------|-------------------|
| **Anónimo** | 60 requests | 1 hora |
| **Customer** | 300 requests | 1 hora |
| **Driver** | 600 requests | 1 hora |
| **Admin** | 1000 requests | 1 hora |

### Headers de Rate Limiting

```
X-RateLimit-Limit: 300
X-RateLimit-Remaining: 250
X-RateLimit-Reset: 1640995200
```

### Respuesta al Exceder el Límite

```json
{
  "success": false,
  "error": "Rate limit exceeded",
  "details": {
    "retry_after": 3600
  }
}
```

---

## 🔔 Webhooks

### Eventos Disponibles

| Evento | Descripción | Payload |
|--------|-------------|---------|
| `ride.created` | Nuevo viaje solicitado | `Ride` object |
| `ride.assigned` | Conductor asignado a viaje | `Ride` object |
| `ride.started` | Viaje iniciado | `Ride` object |
| `ride.completed` | Viaje completado | `Ride` object |
| `ride.cancelled` | Viaje cancelado | `Ride` object + reason |
| `driver.status_changed` | Estado del conductor cambió | `Driver` object |
| `rating.created` | Nueva calificación creada | `Rating` object |

### Configuración de Webhook

```bash
curl -X POST http://localhost:8000/api/v1/webhooks \
  -H "Authorization: Bearer <ADMIN_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://tu-servidor.com/webhook",
    "events": ["ride.created", "ride.completed"],
    "secret": "tu_secreto_webhook"
  }'
```

### Verificación de Firma

Cada webhook incluye un header `X-Webhook-Signature` con HMAC-SHA256:

```python
import hmac
import hashlib

def verify_webhook(payload, signature, secret):
    expected = hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)
```

---

## 📮 Postman Collection

### Importar Collection

1. Descargar el archivo `Taxi_API.postman_collection.json`
2. Abrir Postman
3. Ir a **File → Import**
4. Seleccionar el archivo descargado

### Variables de Entorno

Configurar las siguientes variables en Postman:

```json
{
  "base_url": "http://localhost:8000/api/v1",
  "token": "",
  "tenant_id": "tenant_taxi_001",
  "driver_id": "",
  "customer_id": "",
  "ride_id": ""
}
```

### Ejemplos Incluidos

- ✅ Authentication (Login, Register)
- ✅ Drivers CRUD completo
- ✅ Driver Schedules con plantillas
- ✅ Rides completo (Request, Estimate, Assign, Complete, Cancel)
- ✅ Customers CRUD y direcciones guardadas
- ✅ Vehicles CRUD
- ✅ Ratings y reseñas
- ✅ Promo Codes y validación
- ✅ Analytics y reportes

---

## 🔍 Búsquedas y Filtros

### Filtros Comunes

Todos los endpoints de listado soportan los siguientes query parameters:

```bash
# Paginación
?page=1&limit=20

# Ordenamiento
?sort_by=created_at&order=desc

# Búsqueda por texto
?search=Juan

# Filtro por fechas
?from_date=2024-01-01&to_date=2024-01-31

# Múltiples filtros
?status=active&vehicle_type=sedan&page=1&limit=10
```

### Ejemplo: Buscar Conductores Disponibles Cercanos

```bash
curl -X GET "http://localhost:8000/api/v1/drivers/nearby?tenant_id=tenant_taxi_001&lat=19.4326&lon=-99.1332&radius_km=5&vehicle_type=sedan" \
  -H "Authorization: Bearer <TOKEN>"
```

---

## 🚀 Best Practices

### 1. Manejo de Errores

Siempre verificar el campo `success` en las respuestas:

```javascript
const response = await fetch(url, options);
const data = await response.json();

if (!data.success) {
  console.error('Error:', data.error);
  // Manejar error
  return;
}

// Procesar datos exitosos
console.log(data.ride);
```

### 2. Retry Logic

Implementar reintentos con backoff exponencial para errores 5xx:

```javascript
async function fetchWithRetry(url, options, maxRetries = 3) {
  for (let i = 0; i < maxRetries; i++) {
    try {
      const response = await fetch(url, options);
      if (response.ok) return response;

      if (response.status >= 500 && i < maxRetries - 1) {
        await new Promise(r => setTimeout(r, Math.pow(2, i) * 1000));
        continue;
      }

      return response;
    } catch (error) {
      if (i === maxRetries - 1) throw error;
      await new Promise(r => setTimeout(r, Math.pow(2, i) * 1000));
    }
  }
}
```

### 3. Caching

Implementar cache local para datos estáticos:

```javascript
// Cachear plantillas de turnos (no cambian frecuentemente)
const templates = await fetchWithCache('/driver/schedule/templates', 3600);

// Cachear lista de vehículos del conductor
const vehicles = await fetchWithCache(`/vehicles?driver_id=${driverId}`, 600);
```

### 4. Compresión

Habilitar compresión gzip en las requests:

```bash
curl -X GET http://localhost:8000/api/v1/rides \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Accept-Encoding: gzip, deflate"
```

---

## 📝 Notas Importantes

### Multi-Tenancy

Todos los endpoints requieren el parámetro `tenant_id` para aislar datos entre diferentes empresas de taxis.

### Timestamps

Todos los timestamps están en formato ISO 8601 UTC:
```
2024-01-28T10:30:00Z
```

### Coordenadas

Las coordenadas geográficas usan el sistema WGS84:
- `lat`: Latitud (-90 a 90)
- `lon`: Longitud (-180 a 180)

### Moneda

Todas las tarifas y montos están en la moneda configurada del tenant (default: MXN - Pesos Mexicanos).

---

## 🆘 Soporte

### Reportar Issues

- **GitHub**: https://github.com/taxisystem/api/issues
- **Email**: api-support@taxisystem.com

### Documentación Adicional

- **OpenAPI Spec**: `openapi.yaml`
- **Changelog**: `CHANGELOG.md`
- **Status Page**: https://status.taxisystem.com

---

## 📄 Licencia

Esta API está licenciada bajo MIT License.

---

**Última actualización**: 2024-01-28
**Versión del documento**: 1.0.0
