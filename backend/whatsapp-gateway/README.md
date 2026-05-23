# WhatsApp Gateway Service

Servicio que conecta WhatsApp Business con el Agente de Ventas IA.

## Arquitectura

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  CLIENTE                GATEWAY                 AGENTE              POS    │
│                                                                             │
│  ┌─────────┐         ┌───────────┐         ┌───────────┐      ┌─────────┐ │
│  │         │  MSG    │           │  MSG    │           │ ORDER│         │ │
│  │ WhatsApp│────────▶│  WhatsApp │────────▶│  Agente   │─────▶│ Middleware│ │
│  │  User   │         │  Gateway  │         │  Ventas   │      │   POS   │ │
│  │         │◀────────│           │◀────────│    IA     │◀─────│         │ │
│  └─────────┘  REPLY  └───────────┘  REPLY  └───────────┘ STATUS└─────────┘ │
│                           │                                                 │
│                           ▼                                                 │
│                    ┌───────────┐                                           │
│                    │  Sessions │                                           │
│                    │   Redis   │                                           │
│                    └───────────┘                                           │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Proveedores Soportados

| Proveedor | Estado | Notas |
|-----------|--------|-------|
| Twilio | ✅ Implementado | Más fácil para empezar |
| Meta Cloud API | ✅ Implementado | Oficial de WhatsApp |
| 360dialog | 🔜 Próximamente | Más económico |

## Configuración

```env
# Proveedor de WhatsApp
WHATSAPP_PROVIDER=twilio  # twilio | meta

# Twilio
TWILIO_ACCOUNT_SID=ACxxxxx
TWILIO_AUTH_TOKEN=xxxxx
TWILIO_WHATSAPP_NUMBER=+14155238886

# Meta Cloud API
META_PHONE_NUMBER_ID=xxxxx
META_ACCESS_TOKEN=xxxxx
META_VERIFY_TOKEN=mi_token_secreto

# Agente de Ventas
SALES_AGENT_URL=http://voice-assistant:8000

# Middleware POS
POS_MIDDLEWARE_URL=http://pos-middleware:8090

# Redis (sesiones)
REDIS_URL=redis://redis:6379/0
```

## Endpoints

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/webhook/twilio` | Recibe mensajes de Twilio |
| POST | `/webhook/meta` | Recibe mensajes de Meta |
| GET | `/webhook/meta` | Verificación de Meta |
| POST | `/api/send` | Enviar mensaje (interno) |
| GET | `/api/sessions/{phone}` | Ver sesión activa |

## Flujo de Mensajes

1. **Cliente envía mensaje** → WhatsApp → Twilio/Meta → Gateway
2. **Gateway procesa** → Extrae datos, busca/crea sesión
3. **Gateway llama al Agente** → Envía mensaje + contexto
4. **Agente responde** → Texto + botones opcionales
5. **Gateway envía respuesta** → Twilio/Meta → WhatsApp → Cliente
