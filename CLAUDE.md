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

## 4. Agente LLM (`backend/sales-agent-base/`)

- **Servidor:** Gunicorn 21.2.0, 2 workers síncronos, puerto 5000
  - CMD: `gunicorn --bind 0.0.0.0:5000 --workers 2 --timeout 120 --preload src.api.app_v2:app`
  - Antes era Flask dev server (`python run_auto.py`) — cambiado para soportar ~50 taxis
- **LLM fallback chain:** Groq → Cerebras → Gemini → OpenRouter
  - `parallel_tool_calls=False` (crítico para flujos secuenciales de tool calling)
  - Cerebras model: `gpt-oss-120b` — Cerebras retiró todos los modelos Llama (2026-06-28). Únicos disponibles: `gpt-oss-120b`, `zai-glm-4.7`
  - OpenRouter: `max_retries=0`, `timeout=20s` — evita esperar 60s cuando rate-limited y superar el timeout del gateway
- **Recovery:** patrón `_FAILED_GEN_RE` para tool calls XML fallidos de Groq; reset de historial cuando Groq retorna 400 ("tool call validation failed")
- App entry point: `src/api/app_v2.py`
- Setup inicial: `src/setup_auto.py` (`setup_proyecto()`) — corre una vez al arrancar

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
| `JWT_SECRET` | taxi-api | JWT inválidos |

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
- Twilio display name "Taxi" — ticket pendiente con Twilio Support (número +16204077336 aún sin nombre asignado)
