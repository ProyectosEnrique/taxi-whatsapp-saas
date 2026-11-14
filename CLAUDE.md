# CLAUDE.md — Taxi WhatsApp SaaS
# taxi.nexoai.lat · Hetzner 5.78.200.46

## 1. Descripción del proyecto

Plataforma SaaS de taxi con atención por WhatsApp:
- Cliente escribe al número WhatsApp, el agente LLM solicita su ubicación y destino
- El sistema asigna conductor disponible y envía seguimiento en tiempo real
- Panel admin para operadores, app del conductor (GPS), y seguimiento público para el cliente
- WhatsApp Twilio: `+16204077336`
- Dominio: `taxi.nexoai.lat`
- Repo: `taxi-whatsapp-saas` (GitHub: ProyectosEnrique)

## 2. Contenedores Docker

| Contenedor | Puerto | Descripción |
|---|---|---|
| `taxi-nginx` | 80 → Traefik | Sirve frontends + reverse proxy |
| `taxi-whatsapp` | 8000 | Gateway WhatsApp (Twilio) |
| `taxi-agent` | 5000 | Sales agent FSM + LLM (Gunicorn) |
| `taxi-api` | 5011 | FastAPI — conductores, viajes, tarifas |

**Redis compartido:** `mandaya_redis` (red `mandaya_prod_mandaya_net`) en **DB 3**.
**PostgreSQL:** `mandaya_postgres` (red `mandaya_prod_mandaya_net`), base de datos `taxi_db`.
  - Creada manualmente: `docker exec mandaya_postgres psql -U mandaya -d postgres -c "CREATE DATABASE taxi_db;"`

## 3. Rutas nginx (`vps/nginx/nginx.conf`)

| URL pública | Destino | Quién la usa |
|---|---|---|
| `taxi.nexoai.lat/` | SPA cliente | Cliente final |
| `taxi.nexoai.lat/cliente` | SPA cliente | Cliente con seguimiento |
| `taxi.nexoai.lat/driver/` | App conductor | Conductor (GPS) |
| `taxi.nexoai.lat/admin/` | Panel admin | Operador |
| `taxi.nexoai.lat/api/v1/*` | taxi-api:5011 | API REST |
| `taxi.nexoai.lat/webhook/*` | taxi-whatsapp:8000 | WhatsApp Twilio |
| `taxi.nexoai.lat/agent/*` | taxi-agent:5000 | API agente |
| `taxi.nexoai.lat/u/*` | taxi-api:5011 | Seguimiento público `/u/{id}` |
| `taxi.nexoai.lat/t`, `/tc`, `/t/{taxi}` | taxi-api:5011 | QR de la calcomanía, de la tarjetita (igual para todos) y QR viejos con número (§29, §30) |

## 4. Agente LLM (`backend/sales-agent-base/`)

- **Servidor:** Gunicorn 21.2.0, 2 workers síncronos, puerto 5000
  - CMD: `gunicorn --bind 0.0.0.0:5000 --workers 2 --timeout 120 --preload src.api.app_v2:app`
  - Antes era Flask dev server (`python run_auto.py`) — cambiado para soportar ~50 taxis
- App entry point: `src/api/app_v2.py` — solo registra `sales_bp` (blueprint de `sales_routes.py`) + healthcheck
- **`src/taxi/` — módulos por responsabilidad** (antes un solo `agent.py` de 775 líneas):
  - `agent.py` — orquestador delgado: bucle de tool calling, manejo de GPS entrante, recovery de errores
  - `llm_cascade.py` — cascada de proveedores (Groq → Cerebras → Gemini → OpenRouter) + recuperación de tool calls XML malformados de Groq
  - `prompts.py` — `SYSTEM_PROMPT` (formato intención→acción)
  - `tools.py` — definiciones de function calling + dispatcher `run_tool()`
  - `taxi_client.py` — llamadas HTTP a taxi-api (geocoding, tarifas, viajes)
  - `session.py` — sesión de conversación en Redis (`MAX_HISTORY=30`, TTL 30min / 24h con viaje activo)
- **Config centralizada:** `src/config.py` (Pydantic Settings) — todas las variables de entorno del agente (LLM keys, `REDIS_URL`, `MENU_SERVICE_URL`, `WHATSAPP_SECRET`, `CUSTOMER_APP_URL`) se leen de `settings`, no de `os.getenv()` disperso
- **LLM fallback chain:** Groq → Cerebras → Gemini → OpenRouter
  - `parallel_tool_calls=False` (crítico para flujos secuenciales de tool calling)
  - Cerebras model: `gpt-oss-120b` — Cerebras retiró todos los modelos Llama (2026-06-28). Únicos disponibles: `gpt-oss-120b`, `zai-glm-4.7`
  - OpenRouter: `max_retries=0`, `timeout=20s` — evita esperar 60s cuando rate-limited y superar el timeout del gateway
  - `LLMCascade.has_primary_provider` (solo Groq+Cerebras) vs `has_any_provider` (los 4) — el guard de "servicio no disponible" en `agent.py` usa el primero a propósito, así se preservó el comportamiento original
- **Recovery:** patrón `_FAILED_GEN_RE` para tool calls XML fallidos de Groq; reset de historial cuando Groq retorna 400 ("tool call validation failed")

## 5. Variables de entorno críticas (`.env`)

| Variable | Servicio | Si falta |
|---|---|---|
| `POSTGRES_PASSWORD` | taxi-api | No conecta a mandaya_postgres |
| `GROQ_API_KEY` | taxi-agent, taxi-whatsapp | Agente sin LLM primario |
| `CEREBRAS_API_KEY` | taxi-agent | Sin fallback 1 |
| `GEMINI_API_KEY` | taxi-agent | Sin fallback 2 |
| `OPENROUTER_API_KEY` | taxi-agent | Sin fallback 3 |
| `TWILIO_ACCOUNT_SID` | taxi-whatsapp | No envía WhatsApp |
| `TWILIO_AUTH_TOKEN` | taxi-whatsapp | No envía WhatsApp |
| `TWILIO_WHATSAPP_NUMBER` | taxi-whatsapp | No envía WhatsApp |
| `TWILIO_WA_ACCOUNT_SID` / `TWILIO_WA_AUTH_TOKEN` | taxi-whatsapp | Subcuenta Twilio "TaxiCerca WhatsApp" (número +1 316 241 2111, portafolio Meta TaxiCerca). Vacías = usa `TWILIO_ACCOUNT_SID`/`TOKEN` como antes. Con ellas puestas, lo que llegue firmado por la cuenta principal (el 978) solo recibe el aviso de número nuevo, sin procesar viajes |
| `JWT_SECRET` | taxi-api | JWT inválidos |
| `GOOGLE_MAPS_API_KEY` | taxi-api | Geocoding usa solo Nominatim (OSM) como fallback — POIs pobres en ciudades pequeñas |
| `CITY_LAT` / `CITY_LNG` | taxi-api | Sin bias geográfico — geocoding puede retornar resultados de otras ciudades |

**Valores VPS actuales (Celaya, Gto.):**
- `CITY_LAT=20.5236` / `CITY_LNG=-100.8147` / `CITY_BBOX_DEG=0.3`
- `GOOGLE_MAPS_API_KEY` — activa en VPS, restringida a IP `5.78.200.46`

WhatsApp number: `whatsapp:+16204077336` (Twilio Sandbox)

## 6. Comandos útiles VPS

```bash
# Estado de todos los contenedores
ssh root@5.78.200.46 "docker compose -f /root/projects/taxi/docker-compose.vps.yml ps"

# Logs por servicio
ssh root@5.78.200.46 "docker logs taxi-agent --tail 50 -f"
ssh root@5.78.200.46 "docker logs taxi-api --tail 50 -f"
ssh root@5.78.200.46 "docker logs taxi-whatsapp --tail 50 -f"

# Rebuild completo
ssh root@5.78.200.46 "cd /root/projects/taxi && git pull && docker compose -f docker-compose.vps.yml --env-file .env up -d --build"

# Rebuild solo taxi-agent (cambios en agente)
ssh root@5.78.200.46 "cd /root/projects/taxi && docker compose -f docker-compose.vps.yml --env-file .env build --no-cache taxi-agent && docker compose -f docker-compose.vps.yml --env-file .env up -d --no-build --force-recreate taxi-agent"

# Verificar que Gunicorn está corriendo (no Flask dev server)
ssh root@5.78.200.46 "docker logs taxi-agent 2>&1 | grep -iE 'gunicorn|WARNING.*development'"

# Verificar DATABASE_URL en taxi-api
ssh root@5.78.200.46 "docker exec taxi-api sh -c 'echo \$DATABASE_URL'"

# Sesión Redis de un cliente (DB 3)
ssh root@5.78.200.46 "docker exec mandaya_redis redis-cli -n 3 KEYS '*'"

# Simular mensaje WhatsApp de prueba
ssh root@5.78.200.46 "docker exec taxi-whatsapp curl -s -X POST http://localhost:8000/webhook/twilio   -d 'From=whatsapp%3A%2B521234999999&Body=hola&ProfileName=Test&NumMedia=0'   -H 'Content-Type: application/x-www-form-urlencoded'"
```

## 7. Arquitectura de redes Docker

```
traefik-public ─── taxi-nginx ─── taxi_net ─┬─ taxi-whatsapp ─── mandaya_net ─── mandaya_redis (DB3)
                                              ├─ taxi-agent    ─── mandaya_net ─── mandaya_redis (DB3)
                                              └─ taxi-api      ─── mandaya_net ─── mandaya_postgres (taxi_db)
```

## 8. Checklist antes de modificar

- [ ] ¿Cambia agente LLM? → Rebuild `taxi-agent` con `--no-cache`
- [ ] ¿Cambia ruta nginx? → Actualizar `vps/nginx/nginx.conf` Y este archivo
- [ ] ¿Agrega columna al schema? → Crear migration SQL (taxi-api usa SQLAlchemy create_all)
- [ ] ¿Cambia variable de entorno? → Actualizar `.env` en VPS Y `docker-compose.vps.yml`
- [ ] ¿Cambia webhook URL WhatsApp? → Actualizar en Twilio Console

## 9. Notas importantes

- El HEALTHCHECK del taxi-agent tiene `start-period=20s` (Gunicorn tarda ~10s en cargar el modelo)
- `parallel_tool_calls=False` es obligatorio en `_llm_create()` — sin esto el agente hace tool calls en paralelo y rompe el flujo de conversación
- Si taxi-api no conecta a PostgreSQL: verificar que `mandaya_postgres` esté en red `mandaya_net` y que `taxi_db` exista
- Twilio display name "Taxi" — ticket #27706680 abierto con Twilio Support (número +16204077336 aún sin nombre asignado, esperando respuesta)

## 10. Geocoding — arquitectura

Módulo: `backend/api-service-base/src/routers/locations.py`

**Prioridad de búsqueda (`GET /api/v1/locations/search?q=...`):**
1. POIs locales (`local_pois` table en PostgreSQL) — sin latencia de red
2. Google Maps Geocoding API (`_google_search()`) — primario, entiende lenguaje natural en español
3. Nominatim/OSM (`_nom_search()`) — fallback gratuito

**Filtro de distancia (`_in_city()`):**
- Todas las respuestas pasan por `_in_city(lat, lng)` que rechaza resultados fuera del radio `CITY_BBOX_DEG * 111 * 1.5 km` (~50 km para Celaya)
- Sin este filtro, geocoding podía retornar la terminal de Querétaro (~55 km) cuando se pedía la "central de autobuses de Celaya"

**Dos funciones de normalización (en `routers/whatsapp.py`):**
- `_clean_query(q)`: solo limpa preposiciones iniciales — para Google Maps (que entiende "Central de Autobuses" nativamente)
- `_normalize_query(q)`: aplica además alias `_QUERY_SUBS` — solo para Nominatim (que necesita términos exactos de OSM)
- ⚠️ No usar `_QUERY_SUBS` con Google Maps — las sustituciones pueden empeorar los resultados

**POIs locales (`local_pois`):**
- Tabla gestionada por `LocalPOI` model en `models.py`
- Soft delete (`is_active = False`)
- API: `GET /pois?q=nombre`, `POST /pois`, `DELETE /pois/{id}`
- Útil para lugares que Google Maps no indexa bien (colonias locales, referencias informales, "El Arco", "La Feria")

**Google Maps API Key:**
- `GOOGLE_MAPS_API_KEY` en `.env` — restringida por IP `5.78.200.46` en GCP Console
- Sin esta key, el sistema cae directamente a Nominatim (cobertura más pobre en ciudades pequeñas)

**Bias geográfico con `bounds`:**
- Google Maps recibe `bounds="{lat-d},{lng-d}|{lat+d},{lng+d}"` donde `d = CITY_BBOX_DEG`
- Nominatim recibe `viewbox` + `bounded=1`

## 11. Mapas Leaflet — patrones y lecciones

**Mapa negro al cargar (`DriverNavigateView.vue`):**
- Causa: `initMap()` se llamaba antes de que Vue renderizara el `<div id="driver-map">` (que está dentro de `v-else-if="ride"`)
- Fix: `await nextTick()` después de asignar `ride.value = data` y antes de llamar `initMap()`
- Regla: cualquier `document.getElementById()` sobre elementos en `v-if/v-else-if` necesita `nextTick()`

**Ruta sin GPS disponible:**
- Problema: la ruta no se dibujaba si el GPS del navegador (`driverPos`) era null al cargar
- Fix: usar la posición del servidor como fallback:
  ```javascript
  const pos = driverPos ?? (data.driver?.lat != null ? [data.driver.lat, data.driver.lng] : null)
  ```

**Marcador del conductor con pan suave:**
```javascript
function _placeDriverMarker(pos) {
  if (driverMarker) {
    driverMarker.setLatLng(pos)
  } else {
    driverMarker = L.marker(pos, { icon: mkIcon('🚕', 36) }).addTo(map)
  }
  if (!map.getBounds().contains(pos)) {
    map.panTo(pos, { animate: true, duration: 0.6 })
  }
}
```
- No usar `fitBounds` en cada tick de GPS — solo en el primer render de cada fase → flag `firstRender`
- `fitBounds` en cada tick hace que el mapa salte constantemente; `panTo` es suave y no intrusivo

**Ruta dinámica por estado (`TrackPublicView.vue`):**
- `confirmed` → ruta amarilla conductor→origen (taxi en camino)
- `in_progress` → ruta azul conductor→destino
- Resto → trayecto completo origen→destino
- Solo se redibuja cuando `data.status` cambia (`lastRouteStatus` guard)

**URL del endpoint de acción del conductor:**
- Correcto: `POST /api/v1/driver/rides/{id}/driver-action`
- Error común: omitir el prefijo `/driver/` → 404

## 12. App conductor (`/driver/`)

- Ruta en frontend: `/conductor/viaje/{ride_id}?p=<phone_base64>` (Vue Router)
- `?p=` es el teléfono del conductor en Base64 — autenticación sin login completo
- Mapa: `<div id="driver-map">` dentro de `v-else-if="ride"` → necesita `nextTick()` antes de `initMap()`
- `watchPosition()` actualiza marcador 🚕 del conductor cada movimiento GPS real

## 13. Tests (`backend/api-service-base/tests/`)

- 19 tests con pytest contra SQLite en memoria (no toca Postgres real) — corren en segundos, sin Docker
- La app de test es un `FastAPI()` mínimo que solo monta los routers bajo prueba (`customer_rides`, `payments`) — evita el `lifespan` de `src.main` (engine real, tareas en background, webhook de Telegram)
- `conftest.py` (raíz de `api-service-base`) fija `DATABASE_URL` dummy antes de cualquier import — necesario porque `src/config.py` la exige
- Cobertura: `fare_service.calculate_fare` (base, mínimo, surge pico/madrugada/fin de semana con `datetime` congelado), registro/login, estimar tarifa, solicitar/cancelar viaje, webhook de MercadoPago (aprobado/rechazado/ignorado/idempotente) con `httpx.AsyncClient` mockeado
- Correr localmente: `cd backend/api-service-base && pytest tests/ -v`
- No hay CI configurado — correr manualmente antes de cambios grandes en `customer_rides.py`, `payments.py` o `fare_service.py`

## 14. Estructura del repo

Este repo nació de una plantilla SaaS multi-tenant genérica (restaurante/farmacia/vinatería) que se especializó a "solo taxi". En 2026-07 se limpiaron ~183 archivos de residuo (backends/frontends duplicados no usados por ningún Dockerfile, infra muerta de Railway/Render/Cloud Run/Firebase/Cloudflare, scripts multi-tenant, tests E2E de Cypress rotos, docs nunca actualizados desde el commit inicial). Lo que queda en la raíz y en `backend/`/`frontend/` es, con pocas excepciones, lo que realmente está en producción — no asumas que un archivo es residuo sin verificarlo contra `docker-compose.vps.yml` y `vps/nginx/Dockerfile` primero.

## 15. Ubicación de choferes por Telegram + despacho por cercanía (rama `ubicacion-telegram`, 2026-10-30)

- **Por qué:** la app del chofer es web — el navegador deja de mandar GPS al bloquear la pantalla, y los choferes que solo usan el bot de Telegram nunca la mandaban. La "ubicación en tiempo real" de Telegram sigue funcionando en segundo plano.
- **Chofer:** una vez por turno, en el chat del bot: 📎 → Ubicación → Compartir ubicación en tiempo real → 8 h. `/ubicacion` repite las instrucciones (también se mandan al `/vincular` y en `/disponible` si su ubicación no está fresca).
- **Webhook (`telegram_bot.py`):** `message.location` (primera vez, con `live_period`) responde confirmación; cada actualización llega como `edited_message.location` y se guarda en silencio (`drivers.current_lat/lng` + `drivers.location_updated_at`, columna nueva). `set_webhook` pide `allowed_updates` con `edited_message` explícito.
- **Despacho (`notify_drivers_new_ride`):** con ubicación fresca (≤ `LOCATION_FRESH_MIN`=5 min) avisa primero a los choferes a ≤ 2 km del origen, si nadie acepta en `DISPATCH_RING_WAIT_S`=60 s a ≤ 4 km, y luego a todos los online (`DISPATCH_RINGS_KM="2,4"`; vacío = todos de una vez, como antes). Sin nadie con ubicación fresca → todos de una vez. La ampliación corre en `asyncio.create_task(_expand_later)`; si el proceso se reinicia, `_ride_timeout_monitor` re-avisa a todos (`everyone=True`) a los 3 min. `ride_notifs.add` acumula avisos de todas las tandas para marcarlos "ya fue tomado".
- Estacionado (formado en la Central) Telegram casi no manda actualizaciones: con ubicación en vivo activa (`drivers.location_live_until`, se borra cuando llega la última edición sin `live_period`) la última posición vale hasta `LOCATION_LIVE_FRESH_MIN`=60 min.
- Distancia en línea recta (haversine). Pendiente: turno de fila para taxis dentro de la Central (todos están "igual de cerca").
- Tests: `tests/test_telegram_location.py` (14).

## 16. Menos cambios de app para el chofer (2026-11-07)

- Los mensajes de estado del bot (`_send_ride_action`) traen botones URL que abren **Google Maps ya navegando** (`maps/dir/?api=1&destination=…&dir_action=navigate`) (un solo botón 🚕 a lo ancho; Waze se quitó 2026-11-11): al aceptar → "🚕 Ruta completa" (pasajero como parada y luego destino); en curso → "🚕 Ir al destino". "🚕 Iniciar viaje" es el botón (callback) del mensaje "Llegaste". Se quitó el enlace a la app web `/conductor/viaje/…` (abría una tercera app).
- `_check_trip_proximity` corre con cada ubicación de Telegram: viaje `confirmed` a ≤ `AUTO_ARRIVE_RADIUS_M` (120 m) del origen → "Llegué" automático (`_mark_arrived`, mismo aviso WhatsApp al pasajero); viaje `driver_arrived` a > `AUTO_START_RADIUS_M` (200 m) del origen → "Iniciar viaje" automático (`_mark_started`, aviso "started" al pasajero); viaje `in_progress` a ≤ `NEAR_DEST_RADIUS_M` (200 m) del destino → mensaje con botón "Completar" (completar sigue manual: ahí cobra). Nada antes de `PROXIMITY_MIN_AGE_S` (60 s) desde el último cambio de estado. Una sola vez por viaje vía `ride_notifs.claim_once` (Redis SET NX). Radio 0 = desactivado.
- Tests: `tests/test_trip_proximity.py` (10).

## 17. Regalo de FarmaCerca en el primer viaje (2026-11-07)
- `services/farmacerca_gift.py`: `gift_for(trip, driver)` → `{"amount", "url"}` solo si es el **primer viaje completado**
  del pasajero (los cancelados no cuentan) y el chofer tiene `drivers.taxi_number` (número económico = código del taxi
  en FarmaCerca, aliado `TAXI`, `ally_units`). URL `FARMACERCA_GIFT_URL/{número}` (default `https://farmacia.nexoai.lat/r/taxi`);
  FarmaCerca abona $5 al pasajero y $3 al chofer. `FARMACERCA_GIFT_URL=""` = apagado.
- Se menciona una sola vez: línea extra en el aviso "Llegaste" (`telegram_bot._notify_customer_wa` y
  `driver_rides.complete_ride`) y banner `gift` en `/seguimiento` (`public_track` → `TrackPublicView.vue`).
- `taxi_number` se pone con `PUT /api/v1/admin/drivers/{phone}` (`{"taxi_number": "23"}`). Sin número no se promete nada.
- Reglas: lema "Tu farmacia por WhatsApp", vender el servicio (no medicinas), sin nombres de ciudades.

## 18. Botón de pánico SOS → encargado de la base (2026-11-08)
Lógica central en `services/sos.py` (`raise_sos`, `acknowledge`, `escalate_pending`). Entradas:
- **Chofer (Telegram):** botón "🚨 SOS" en cada mensaje del viaje (`sos_` → pide confirmar → `sosgo_`) o `/sos` (sin confirmar).
- **Pasajero (WhatsApp):** el gateway (`main_taxi._SOS_RE`, mensaje completo "sos/auxilio/socorro/emergencia/pánico/ayuda urgente")
  NO pasa por la IA ni por el rate limit → `POST /api/v1/sos/whatsapp` (clave `X-Taxi-Internal-Key` = `WHATSAPP_SECRET`,
  obligatoria) → respuesta en el TwiML. Env del gateway: `TAXI_API_URL` (default `http://taxi-api:5011`).
- **Pasajero (/seguimiento):** botón mantener presionado 2 s → `POST /api/v1/customer/rides/{id}/sos` (público; solo viaje
  activo o terminado hace ≤ 30 min). Manda GPS del celular si lo da en 4 s.
- **Apps con cuenta** (`routers/incidents.py`): mismo aviso + contacto de emergencia personal.

Destino: encargados `priority=1` de la **base del taxi involucrado** (`drivers.group_id` → tabla `base_managers`), sin importar
quién presionó + copia al operador (`TELEGRAM_ALERT_CHAT_ID`, avisa si la base no tiene encargado). Botón "✅ Ya lo atiendo"
(`sosack_`, solo encargados u operador; una vez) → avisa a los demás y a quien presionó. Sin atender en `SOS_ESCALATE_MIN`
(2) → encargados `priority=2` + operador ("SIN ATENDER"), loop `_dead_mans_switch` cada 30 s. Misma persona otra vez en
10 min = misma alerta. Sin GPS de quien avisó se usa la ubicación del taxi; la alerta trae el link de `/seguimiento`.
Alta de encargados: `POST /api/v1/admin/base-managers` `{name, phone, group_id, priority}` y la persona escribe al bot
`/encargado +52…`. Chofer a su base: `PUT /api/v1/admin/drivers/{phone}` `{"group_id": N}`. Todo mensaje recalca el 911.

## 19. Tarjeta de contacto "TaxiCerca" en el primer mensaje (2026-11-08)
Tras la primera respuesta del bot a cada cliente, el gateway (`_send_contact_card_once`) manda
`https://taxi.nexoai.lat/taxicerca.vcf` (archivo en `frontend/taxi-customer-app/public/`, nginx lo sirve como `text/vcard`)
como media de Twilio: WhatsApp la muestra como contacto y el cliente solo toca "Guardar". "Primera vez" lo decide
taxi-api: `POST /api/v1/contact-card/claim` (clave interna, `claim_once("vcard", phone)` en Redis, 1 año). Si cambia el
número de WhatsApp, actualizar el `.vcf`. `CONTACT_CARD_URL=""` en el gateway = apagado.

## 20. Búsqueda de lugares más precisa (2026-11-08)
`GET /api/v1/whatsapp/geocode` (`routers/whatsapp.py`): **Google Places Text Search (New)** primero (entiende nombres
de lugares: "Hospital General", "Soriana"; requiere habilitar "Places API (New)" en el proyecto de la clave — si
responde 403 se sigue solo con Geocoding) → Google Geocoding (calle y número) → Nominatim (`jsonv2`).
- Cada resultado trae `colonia`, `ciudad` y `aproximado`. Los de **nivel ciudad** (locality/municipio/estado; en
  Nominatim city/town/village…) se **descartan**: antes "Hospital X Celaya" sin coincidencia caía en el centro de
  Celaya y se aceptaba. Colonia sola o calle sin número = `aproximado` (el bot pregunta calle o referencia una vez).
  Exactos primero.
- **Cerca del pasajero:** `lat`/`lon` = sesgo de búsqueda (Places `locationBias` 20 km, Geocoding `bounds`) y el
  filtro de zona acepta ≤ ~50 km del centro de operación **o** del pasajero (`_within_radius`). El agente
  (`tools.run_tool`) manda la ubicación GPS del pasajero o, si no la hay, el último lugar encontrado en la
  conversación (`context.anchor`): origen y destino suelen estar en la misma ciudad.
- El prompt ya no agrega "Celaya" por su cuenta; resumen y `crear_viaje` llevan "nombre, colonia, ciudad".
- `reverse-geocode` también devuelve colonia y ciudad. Pruebas: `tests/test_geocode.py` (proveedores simulados).

## 21. Arranque solo con viajes al momento (2026-11-09)
Decisión del dueño para las primeras pruebas reales: **sin viajes programados**. `SCHEDULED_RIDES_ENABLED=False`
(config de taxi-api): `POST /api/v1/whatsapp/rides/create` con `scheduled_at` → **409** (NO se convierte en
inmediato: mandaría un taxi ya) y `POST /api/v1/customer/rides/schedule` → 409. El bot: `crear_viaje` ya no tiene
`scheduled_at` y el prompt responde "Por ahora solo atendemos viajes para este momento…". Pago: solo efectivo
(sin claves de Mercado Pago en el VPS). Para reactivar: `SCHEDULED_RIDES_ENABLED=true` en `.env` + compose,
devolver `scheduled_at` a la herramienta y la regla del prompt.

## 22. Alta de choferes con enlace de Telegram (2026-11-09)
Panel → Conductores → botón **📲** → `POST /api/v1/admin/drivers/{phone}/telegram-link` → `t.me/<TELEGRAM_BOT_USERNAME>?start=<código>`
(`services/telegram_link.py`: código secreto en Redis `taxi:tglink:*`, **un solo uso** (GETDEL), 7 días). El chofer toca el
enlace → "Iniciar" → el bot recibe `/start <código>` → `_link_driver` (misma bienvenida que `/vincular`; si ese Telegram
estaba ligado a otro chofer, se suelta). `/start` sin código responde con el ID de Telegram. La lista del panel marca
"✓ Telegram vinculado / ⚠ Sin Telegram" (`telegram_linked`). Bot de taxis = @TaxiNexoaiBot (solo TaxiCerca; Mandaya,
Ricomar y FarmaCerca tienen bots propios). `/vincular +52…` sigue funcionando.

## 23. Compartir ubicación = disponible (2026-11-09)
Para que el chofer no escriba /disponible ni /descanso cada día (`telegram_bot._handle_location`):
- Empieza a compartir **ubicación en tiempo real** (mensaje nuevo con `live_period`) → `is_online=True` y le avisa
  "🟢 Ya estás disponible".
- **Detiene** la ubicación (Telegram manda una última edición sin `live_period`) → `is_online=False` + aviso de descanso.
- **Vence** sola (las 8 h): Telegram no avisa → `_live_location_monitor` (main.py, cada 2 min) llama
  `expire_live_locations` → descanso + aviso. "Hasta que la desactive" se considera vigente mientras sigan llegando
  posiciones (`location_live_until` se extiende 2 h en cada actualización).
- Ubicación fija no cambia la disponibilidad. /disponible y /descanso siguen funcionando.

## 24. Tarifa por distancia de calle y "aproximada" (2026-11-09)
Mientras llega el tabulador de la base: `fare_service.route_km_min` da km y minutos **por calle** (OSRM, el mismo de
/seguimiento; si no responde, línea recta × 1.3) con caché de 30 min por coordenadas (estimación y creación del viaje
dan el mismo precio). Lo usan `whatsapp.estimate_fare/create`, y `customer_rides` estimate/request/schedule. El
pasajero ve "$X MXN aprox." y el chofer "Tarifa aprox. … (cobra según tu base)". Recargos (`_surge_multiplier`) con
hora de México (UTC-6); antes UTC: la "madrugada" empezaba a las 5 pm (surge sigue apagado). Tarifa redondeada al múltiplo de $5 más cercano (sin bajar de la mínima). Pruebas sin red:
`conftest._no_osrm`. Pendiente: tabulador por base (mínima de ciudad, precios fijos por colonia/comunidad, nocturno).

## 25. Solo WhatsApp: pedir desde la web apagado (2026-11-10)

Para el arranque los viajes se piden solo por WhatsApp (número real; la web dejaba registrarse con cualquier dato y no
tenía las mejoras de geocodificación/SOS). `settings.WEB_RIDES_ENABLED=False` → `customer_rides.web_rides_on` responde
403 en register/login/forgot/reset-password y rides estimate/request/schedule. En la app (`router/index.js`,
`WEB_RIDES_ENABLED=false`) las rutas de cuenta/pedido redirigen a `/` y la portada solo tiene "Pedir taxi por WhatsApp".
Siguen igual: `/seguimiento/{id}` (public-track, SOS), `/track`, `/pedir`, `/privacidad`, `/conductor`. Para
reabrir: poner ambos en true y redesplegar taxi-api y taxi-nginx.

## 26. Enlace corto de navegación sin "¿Abrir este enlace?" (2026-11-11)

Los botones URL de Telegram siempre piden confirmar. Los mensajes "Viaje aceptado" y "Viaje en curso" llevan además
el texto visible `👉 Abre directo en Maps: https://taxi.nexoai.lat/r/<código>` (`telegram_bot._short_link_line`),
que Telegram abre sin preguntar. `routers/nav_link.py` (`GET /r/{código}`, código = parte hex de `trip_id`; nginx
`location /r/` → taxi-api) redirige según el estado al tocarlo: aceptado → ruta completa (pasajero como parada);
llegó/en curso → destino; terminado/desconocido → 404. `nav_link.maps_url` arma también las URLs de los botones.
Pendiente: confirmar en el celular del chofer que de verdad abre sin preguntar; si no, quitar la línea.

## 27. Avisos al pasajero: solo los necesarios (2026-11-11)

Intervención mínima del chofer. El pasajero recibe: **"Conductor asignado"** (al aceptar) → **"Tu conductor está
llegando"** (una sola vez, `telegram_bot._notify_arriving`, `claim_once("arriving_msg")`: lo que pase primero entre
acercarse a `ARRIVING_NOTICE_RADIUS_M`=150 m con la ubicación en vivo, el "Llegué" automático a 120 m o el botón de
respaldo) → **"Llegaste a tu destino"** (al completar). Se quitaron "¡Tu taxi llegó!" y "¡Viaje en camino!" (al
iniciar no se avisa: ya va en el taxi). Mismo criterio en la acción web `driver_rides.driver_action_web`.
Requiere que el chofer comparta su ubicación en tiempo real; sin ella, solo el botón "Llegué" manda el aviso.

## 28. Chat del chofer limpio al terminar cada viaje (2026-11-11)

`services/trip_chat.py`: cada mensaje con botones del viaje (`telegram_bot._send_trip_msg`: aceptado, llegaste, en
curso, ya casi llegas; más el aviso de "viaje nuevo" del que lo tomó) se anota en Redis `taxi:tripmsgs:{trip_id}` (48 h).
Al **completar** (`trip_chat.finish`) se borran (`deleteMessage`; si Telegram no deja, `editMessageReplyMarkup` sin
botones) y queda un solo resumen sin botones (`completed_summary`: "✅ Viaje terminado · origen → destino · $X aprox.").
A los choferes que no alcanzaron el viaje, el "ya fue tomado" se borra a los `TAKEN_NOTICE_DELETE_S`=120 s
(`drop_taken_notices`, `asyncio.create_task`; si el proceso se reinicia antes, ya no tiene botones). Al **cancelar**
(`whatsapp.cancel_ride`, `customer_rides.cancel_ride` → `trip_chat.notify_cancelled`) se limpia igual, se borran los
avisos con "Aceptar" aún vivos y el chofer asignado recibe "❌ Viaje cancelado por el cliente". SOS nunca se borra.
Tests: `tests/test_trip_chat.py`.

## 29. Tarjetita QR dentro del taxi + calcomanía de afuera (2026-11-13)

Los pasajeros hoy paran el taxi en la calle: la tarjetita del respaldo les enseña a pedirlo por WhatsApp la próxima vez.
Decisión del dueño: calcomanía de afuera 100% TaxiCerca; adentro también TaxiCerca primero, FarmaCerca solo como regalo.
**Un solo QR** (dos QR = todos escanean el del dinero y nunca guardan TaxiCerca).
- `routers/taxi_qr.py`: `GET /t/{taxi}` → `wa.me/<TAXICERCA_WA_NUMBER>?text=Hola TaxiCerca 🚕 voy en el taxi 23`;
  `GET /t` (calcomanía de afuera) → "…quiero pedir un taxi" (lo atiende el bot normal). nginx `location ~ ^/t(/…)?$`.
  Los QR impresos apuntan al link corto, nunca directo al número: si cambia el número, no se reimprime.
- Gateway (`main_taxi._TAXI_SCAN_RE`, mensaje corto completo "voy en el taxi N"): NO pasa por la IA →
  `POST /api/v1/whatsapp/taxi-scan` (clave interna) → "📲 Guarda este chat…" + regalo de FarmaCerca
  (`FARMACERCA_GIFT_URL/{taxi}`) **solo si hay chofer activo con ese `taxi_number`**; luego la tarjeta de contacto (§19).
  No crea viaje ni avisa a choferes. Los límites del regalo los pone FarmaCerca (uno al día por pasajero, tope por taxi).
- Diseños: `Downloads\TaxiCerca - Tarjetita y calcomania\gen.py` (`python gen.py 23 8 …`).
- Tests: `tests/test_taxi_qr.py` (6).

## 30. Tarjetita igual para todos + regalo de alta a los choferes (2026-11-13)
Decisión del dueño: la tarjeta de contacto (§19) ya hace que el pasajero guarde TaxiCerca, así que el número de taxi en el
QR solo servía para pagarle $3 al chofer por escaneo. Se quita: un solo diseño para imprimir y un solo registro por chofer.
- **Tarjetita:** QR `taxi.nexoai.lat/tc` → "Hola TaxiCerca 🚕 voy en un taxi" → misma respuesta de §29 ("Guarda este chat"
  + regalo) sin número de taxi. `_TAXI_SCAN_RE` acepta "voy en un taxi" y "voy en el taxi 23" (QR viejos siguen sirviendo).
- **Pasajero:** el link del regalo es `FARMACERCA_GIFT_URL` sin número (`/r/taxi`) en el escaneo y en el primer viaje (§17);
  FarmaCerca da **$5 una sola vez por número** (un QR igual para todos se puede compartir en un grupo). Ya no depende de
  `drivers.taxi_number` ni de dar de alta cada taxi en FarmaCerca.
- **Chofer:** `services/farmacerca_driver_gift.py` → **$50 al ligar su Telegram** (`telegram_bot._link_driver`) y **$50 al
  terminar su primer viaje** (`is_first_trip`; botón Completar de Telegram, `driver_rides.complete_ride` y la acción web).
  `POST https://farmacia.nexoai.lat/api/v1/allies/partner-credit` con aliado `FARMACERCA_DRIVER_ALLY` (TAXICHOFER) y
  `X-Ally-Secret: FARMACERCA_DRIVER_SECRET` (solo en `.env`; vacío = apagado). Refs `AL{tel10}` / `V1{tel10}`: FarmaCerca no
  repite el abono, y el aviso por Telegram (monto, vigencia, link al WhatsApp de FarmaCerca) solo sale si sí se abonó.
  En FarmaCerca ese aliado tiene vigencia de 90 días y se usa completo (sin "hasta la mitad"), ver farmacia CLAUDE.md §37.
- Tests: `tests/test_taxi_qr.py` (7), `tests/test_farmacerca_driver_gift.py` (4), `tests/test_farmacerca_gift.py`.
