# TaxiSaaS — Claude Code Context

## Proyecto
Sistema de transporte con WhatsApp bot + apps web (conductor, cliente, admin).

**VPS:** `ssh root@5.78.200.46` — `/root/projects/taxi`
**Dominio:** `https://taxi.nexoai.lat`
**Deploy:** `cd /root/projects/taxi && git pull && docker compose -f docker-compose.vps.yml --env-file .env up -d --build`

## Estructura de directorios
```
backend/
  api-service-base/src/
    routers/         # customer_rides.py, driver.py, admin.py, auth.py
    services/        # telegram.py, etc.
    models.py
    database.py
frontend/
  taxi-customer-app/   # Vue 3 + Vite — app cliente (scope /)
  driver-app/          # Vue 3 + Vite — app conductor (scope /driver/)
  admin-panel/         # Vue 3 + Vite — panel admin (scope /admin/)
vps/
  nginx.conf           # Traefik + routing
docker-compose.vps.yml
```

## Contenedores Docker (VPS)
| Contenedor | Puerto | Descripción |
|-----------|--------|-------------|
| `taxi-api` | 5011 | FastAPI + SQLite |
| `taxi-nginx` | 80 → Traefik | Frontends + reverse proxy |
| `taxi-agent` | 5000 | TaxiFSM + Redis sessions |
| `taxi-whatsapp` | 8000 | Gateway WhatsApp (Twilio + Meta) |

## Arquitectura GPS tracking
Solo el conductor necesita GPS. No es peer-to-peer:

```
Conductor (driver-app) → PUT /api/v1/driver/location (cada 5s)
  → DB: driver.current_lat / current_lng
    → Cliente polling GET /api/v1/customer/rides/active (cada 5s)
      → Leaflet: driverMarker.setLatLng([lat, lng])
```

El `driverStore.js` usa `navigator.geolocation.watchPosition()` para tracking continuo.

## Notificaciones Telegram
`services/telegram.py` → `send_to_operator()` — envía mensaje HTML al `TELEGRAM_ALERT_CHAT_ID`.

Implementado en `routers/customer_rides.py` → `async def request_ride()`: cuando el cliente solicita un viaje, el operador recibe Telegram con ID, cliente, origen, destino y tarifa.

## Cuentas / Credenciales
**Admin:** `taxi.nexoai.lat/admin/`
**Conductores demo:**
- `+521234567001` / `demo1234` — Carlos Méndez
- `+521234567002` / `demo1234` — María González
- `+521234567003` / `demo1234` — Roberto Sánchez

**Conductores reales:**
- `+524611130530` / `Yadira2026!` — Yadira Hernández | VW Vento 2018 Blanco ABC-123 | driver_id=5 | iPhone Safari

Nuevos conductores: registrar en `/admin/` → Conductores → Nuevo.

## Lecciones aprendidas

### PWA Service Worker scope
El customer app tiene SW en scope `/` que intercepta TODAS las rutas, incluyendo `/driver/` y `/admin/`. Sin el fix, iOS Safari en `/driver/` recibía HTML del cliente → Vue Router sin ruta → pantalla en blanco.

**Fix en `frontend/taxi-customer-app/vite.config.js`:**
```javascript
workbox: {
  navigateFallbackDenylist: [/^\/driver/, /^\/admin/],
  // ...
}
```
Después del fix, los usuarios iOS deben limpiar caché (Ajustes → Safari → Borrar historial y datos de sitios web).

### GPS en Chrome Android — dos capas de permisos
1. OS Android → Chrome app tiene permiso de ubicación
2. Chrome site settings → el sitio tiene permiso

Si capa 2 fue denegada antes, `getCurrentPosition()` falla con código 1 sin mostrar popup. El usuario debe ir manualmente a:
`chrome://settings/content/siteDetails?site=https://taxi.nexoai.lat`

La UI del conductor (`DashboardView.vue`) muestra:
- Banner **rojo** si GPS bloqueado (`gpsStatus === 'denied'`): instrucciones para ir a Chrome settings
- Banner **amarillo** si GPS no concedido aún (`gpsStatus !== 'granted'`): botón "Permitir GPS"

### iOS Safari GPS
En iPhone sin historial previo de denegación, Safari pide permiso automáticamente. Recomendado para conductores nuevos.

### `chr(10)` para parchear Python vía SSH heredoc
Al editar código Python remotamente con `cat <<EOF`, los `\n` se convierten en newlines reales → `SyntaxError`. Usar `nl = chr(10)` y `nl.join(lista)` en lugar de `"\n".join(lista)`.

## Comandos útiles
```bash
# Logs en tiempo real del API
docker logs taxi-api --tail 50 -f

# Rebuild solo el API sin afectar otros
docker compose -f docker-compose.vps.yml --env-file .env up -d --build --no-deps taxi-api

# Conectar a SQLite de la API
docker exec -it taxi-api python -c "from src.database import SessionLocal; ..."

# Ver viajes activos
docker exec taxi-api python -c "
from src.database import SessionLocal
from src.models import Ride
db = SessionLocal()
rides = db.query(Ride).filter(Ride.status.notin_(['CANCELLED','COMPLETED'])).all()
for r in rides: print(r.trip_id, r.status)
"

# Cancelar un viaje atascado
docker exec taxi-api python -c "
from src.database import SessionLocal
from src.models import Ride
db = SessionLocal()
r = db.query(Ride).filter(Ride.trip_id=='TRIP-XXXXXXXX').first()
r.status = 'CANCELLED'
db.commit()
"
```
