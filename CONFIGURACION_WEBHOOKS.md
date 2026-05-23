# 🔗 CONFIGURACIÓN DE WEBHOOKS - WHATSAPP SAAS

**Fecha:** 2026-01-27
**Estado:** 📝 Guía paso a paso

---

## 🎯 URLs DE WEBHOOKS DESPLEGADOS

```
Twilio:  https://whatsapp-gateway-308574626875.us-central1.run.app/webhook/whatsapp
Meta:    https://whatsapp-gateway-308574626875.us-central1.run.app/webhook/meta
```

---

## 📱 OPCIÓN 1: TWILIO WHATSAPP (Rápido para Testing)

### ✅ Ventajas de Twilio
- Setup en 5 minutos
- Ideal para pruebas y desarrollo
- No requiere número de WhatsApp Business propio

### ⚠️ Limitaciones
- El número `+14155238886` es un **sandbox**
- Cada usuario debe enviar un código de activación antes de chatear
- Código típico: `join [palabra-clave]` (ej: `join restaurant-bot`)

---

### 📋 PASO A PASO - TWILIO

#### 1. Acceder a Twilio Console

Abre tu navegador y ve a:
```
https://console.twilio.com/
```

**Credenciales para login:**
- Account SID: `ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`
- Auth Token: `xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

#### 2. Navegar a WhatsApp Sandbox

1. En el menú lateral, ve a: **Messaging**
2. Luego: **Try it out**
3. Selecciona: **Send a WhatsApp message**

O usa este link directo:
```
https://console.twilio.com/us1/develop/sms/try-it-out/whatsapp-learn
```

#### 3. Configurar Webhook

En la sección **Sandbox Configuration:**

1. Busca el campo: **When a message comes in**
2. Pega esta URL:
   ```
   https://whatsapp-gateway-308574626875.us-central1.run.app/webhook/whatsapp
   ```
3. Selecciona método: **HTTP POST**
4. Haz clic en **Save**

#### 4. Activar el Sandbox en tu WhatsApp

1. Abre WhatsApp en tu teléfono
2. Agrega el número: **+1 415 523 8886**
3. Envía el mensaje que te indica Twilio (algo como):
   ```
   join [palabra-clave]
   ```
   La palabra clave aparece en la consola de Twilio.

#### 5. Probar el Bot

Después de activar el sandbox, envía:
```
Hola
```

Deberías recibir una respuesta del bot de ventas.

---

## 🏢 OPCIÓN 2: META WHATSAPP BUSINESS API (Producción)

### ✅ Ventajas de Meta
- API oficial de WhatsApp
- Tu propio número de WhatsApp Business
- Sin limitaciones de sandbox
- Mejor para producción

### ⚠️ Requisitos
- Cuenta de Meta for Developers
- WhatsApp Business App verificada
- Número de teléfono verificado

---

### 📋 PASO A PASO - META

#### 1. Acceder a Meta for Developers

Abre tu navegador y ve a:
```
https://developers.facebook.com/
```

Inicia sesión con tu cuenta de Facebook/Meta.

#### 2. Seleccionar tu App

1. En el dashboard, busca tu **WhatsApp Business App**
2. Si no tienes una, créala:
   - Clic en **Create App**
   - Selecciona **Business**
   - Agrega **WhatsApp** como producto

#### 3. Navegar a Configuración de WhatsApp

1. En el menú lateral, ve a: **WhatsApp**
2. Luego: **Configuration**

O usa el menú: **WhatsApp → Getting Started**

#### 4. Configurar Webhook

En la sección **Webhook:**

1. Haz clic en **Configure Webhook** o **Edit**

2. Llena los campos:

   **Callback URL:**
   ```
   https://whatsapp-gateway-308574626875.us-central1.run.app/webhook/meta
   ```

   **Verify Token:**
   ```
   mi_token_secreto_restaurant_2025
   ```

3. Haz clic en **Verify and Save**

Meta enviará una petición de verificación a tu webhook. Si todo está bien, aparecerá un ✅.

#### 5. Suscribirse a Eventos

En la misma página de **Configuration**, busca **Webhook fields**:

1. Activa estas suscripciones:
   - ✅ **messages** (mensajes entrantes)
   - ✅ **messaging_postbacks** (respuestas de botones)
   - ✅ **message_status** (estados de mensajes - opcional)

2. Guarda los cambios

#### 6. Verificar Phone Number ID

En la sección **API Setup** verifica que tienes:
```
Phone Number ID: 923707364155428
```

Este ID ya está configurado en tu `env-vars-whatsapp-gateway.yaml`.

#### 7. Obtener Access Token

Tu Access Token actual es:
```
EAAbVn3hOsa8BQRKGfsm1sTSghUZBZC3MKu7ZCzE8g2D5k5Kxe9oZB86PtZBoOuQ6rLSYvz5lDjdDKNOMBdZCwZB7Auel45Qa0pEkIitF5PEk4RNG32V6r2g0HLBHtDVvuYb1qK8GB0sasMqTbZAYViNojN1s0YgzTly4G5gPTH7yI79ZAiuPSVhNENZA82JrfiKZBCSIFsziq6oNPKJ9CzPfTfRVDOMHh9ZByhlBfCwH708bgB9WorqiZAwhB0NYbjDBBUAVs1xroS971BFgWwAPot7kS
```

**⚠️ IMPORTANTE:** Este token puede expirar. Si ves errores de autenticación:

1. Ve a: **WhatsApp → API Setup**
2. Genera un nuevo **Temporary Access Token** o configura un **Permanent Access Token**
3. Actualiza el token en `env-vars-whatsapp-gateway.yaml`
4. Redesplega el servicio

#### 8. Agregar Número de Prueba

Para testing, Meta te permite agregar números de prueba:

1. Ve a: **WhatsApp → API Setup**
2. Busca **To** (destinatarios)
3. Haz clic en **Add phone number**
4. Ingresa tu número de WhatsApp con código de país
5. Verifica el código que te llegará por WhatsApp

#### 9. Probar el Bot

Desde el número verificado, envía un WhatsApp al número de tu negocio:
```
Hola
```

Deberías recibir respuesta del bot.

---

## 🧪 TESTING Y VERIFICACIÓN

### Test 1: Health Check

Verifica que los servicios estén activos:

```powershell
# Test whatsapp-gateway
curl https://whatsapp-gateway-308574626875.us-central1.run.app/health

# Debería retornar: {"status": "healthy"}
```

### Test 2: Webhook Verification

Para Meta, el webhook debe responder correctamente a la verificación:

```powershell
# Simular verificación de Meta
curl "https://whatsapp-gateway-308574626875.us-central1.run.app/webhook/meta?hub.mode=subscribe&hub.verify_token=mi_token_secreto_restaurant_2025&hub.challenge=CHALLENGE_TEST"

# Debería retornar: CHALLENGE_TEST
```

### Test 3: Enviar Mensaje de Prueba

**Desde Twilio:**
- Activa sandbox: envía `join [palabra-clave]` a +1 415 523 8886
- Prueba: envía `Hola`

**Desde Meta:**
- Asegúrate de que tu número esté verificado en Meta
- Envía `Hola` al número de tu negocio

### Test 4: Revisar Logs

Monitorea los logs en tiempo real:

```powershell
# Ver logs del gateway
& "C:\Program Files (x86)\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd" run logs tail whatsapp-gateway --region=us-central1

# Ver logs del agente
& "C:\Program Files (x86)\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd" run logs tail sales-agent-service --region=us-central1
```

Deberías ver:
```
✅ Webhook recibido
✅ Mensaje procesado
✅ Respuesta enviada
```

---

## 🔍 VERIFICACIÓN DE CONFIGURACIÓN

### Checklist - Twilio ✅

- [ ] Webhook URL configurada en Twilio Console
- [ ] Método POST seleccionado
- [ ] Sandbox activado en WhatsApp personal
- [ ] Mensaje de prueba enviado
- [ ] Respuesta del bot recibida

### Checklist - Meta ✅

- [ ] Webhook URL configurada en Meta Developers
- [ ] Verify Token correcto
- [ ] Webhook verificado por Meta (✅ verde)
- [ ] Eventos suscritos: messages, messaging_postbacks
- [ ] Phone Number ID correcto
- [ ] Access Token válido
- [ ] Número de prueba agregado y verificado
- [ ] Mensaje de prueba enviado
- [ ] Respuesta del bot recibida

---

## 🎯 CONFIGURACIÓN MULTI-TENANT

Para usar el mismo sistema con múltiples negocios (Restaurant, Farmacia, Taxis):

### Opción A: Diferentes números de WhatsApp

1. Configura un número de WhatsApp por negocio
2. Cada webhook incluye el parámetro `tenant`:

```
Restaurant: https://whatsapp-gateway-308574626875.us-central1.run.app/webhook/whatsapp?tenant=restaurant
Farmacia:   https://whatsapp-gateway-308574626875.us-central1.run.app/webhook/whatsapp?tenant=farmacia
Taxis:      https://whatsapp-gateway-308574626875.us-central1.run.app/webhook/whatsapp?tenant=taxis
```

### Opción B: Un solo número (Meta solamente)

Con Meta WhatsApp Business Platform, puedes usar Business Solution Providers para manejar múltiples clientes desde una sola integración.

---

## 🆘 TROUBLESHOOTING

### Problema: Webhook no recibe mensajes

**Diagnóstico:**
```powershell
# Ver logs
& "C:\Program Files (x86)\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd" run logs read whatsapp-gateway --region=us-central1 --limit=20
```

**Soluciones:**
1. Verifica que la URL del webhook esté correcta (sin espacios extra)
2. Verifica que el servicio esté `--allow-unauthenticated`
3. Verifica que el método sea POST
4. Para Meta: verifica que el verify token sea exacto

### Problema: Bot no responde

**Diagnóstico:**
```powershell
# Ver logs del agente
& "C:\Program Files (x86)\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd" run logs read sales-agent-service --region=us-central1 --limit=20
```

**Soluciones:**
1. Verifica que las API keys de IA estén activas (Cerebras, Groq, etc.)
2. Verifica conexión a Redis
3. Revisa los logs para ver errores específicos

### Problema: Error 401 Unauthorized (Meta)

**Causa:** Access Token expirado o inválido

**Solución:**
1. Genera nuevo Access Token en Meta Developers
2. Actualiza `env-vars-whatsapp-gateway.yaml`:
   ```yaml
   META_ACCESS_TOKEN: "NUEVO_TOKEN_AQUI"
   ```
3. Redesplegar:
   ```powershell
   & "C:\Program Files (x86)\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd" run deploy whatsapp-gateway --image=us-central1-docker.pkg.dev/restaurant-voice-system/restaurant-services/whatsapp-gateway:latest --env-vars-file=env-vars-whatsapp-gateway.yaml --region=us-central1 --quiet
   ```

### Problema: Webhook verification failed (Meta)

**Causa:** Verify Token incorrecto

**Solución:**
1. Verifica que el token en Meta sea exactamente:
   ```
   mi_token_secreto_restaurant_2025
   ```
2. Verifica que coincida con `env-vars-whatsapp-gateway.yaml`
3. El verify token es case-sensitive

### Problema: Message delivery failed

**Diagnóstico:**
Ver logs y buscar error específico.

**Soluciones comunes:**
1. **Twilio:** Verifica que el destinatario haya activado el sandbox
2. **Meta:** Verifica que el número destinatario esté agregado como número de prueba
3. Verifica que tengas crédito/saldo en Twilio o Meta

---

## 📊 MONITOREO POST-CONFIGURACIÓN

### Dashboard de Twilio

```
https://console.twilio.com/us1/monitor/logs/sms
```

Aquí puedes ver:
- Mensajes enviados/recibidos
- Errores de entrega
- Webhooks llamados

### Dashboard de Meta

```
https://business.facebook.com/wa/manage/home/
```

Aquí puedes ver:
- Mensajes enviados/recibidos
- Analytics
- Calidad del número

### Cloud Run Metrics

```powershell
# Ver métricas del servicio
& "C:\Program Files (x86)\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd" run services describe whatsapp-gateway --region=us-central1
```

---

## ✅ CONFIGURACIÓN COMPLETADA

Una vez que ambos webhooks estén configurados y funcionando:

### Testing Final

1. **Twilio Test:**
   - Envía: `Hola` desde tu WhatsApp activado
   - Espera respuesta del bot
   - Envía: `¿Cuál es el menú?`
   - Verifica interacción completa

2. **Meta Test:**
   - Envía: `Hola` desde número verificado
   - Espera respuesta del bot
   - Prueba diferentes mensajes
   - Verifica que los mensajes se guarden en la base de datos

3. **Multi-Tenant Test (si aplica):**
   - Envía mensajes a diferentes tenants
   - Verifica que cada uno tenga datos separados

### Próximos Pasos

Una vez funcionando:
1. ✅ Monitorear logs durante las primeras 24h
2. ✅ Ajustar mensajes del bot según necesidad
3. ✅ Configurar alertas en Cloud Monitoring
4. ✅ Opcional: Configurar dominios custom
5. ✅ Opcional: Implementar rate limiting

---

## 📞 INFORMACIÓN DE CONTACTO

**Números de WhatsApp configurados:**
- Twilio Sandbox: `+1 415 523 8886`
- Meta Business: (Tu número de WhatsApp Business)

**Webhooks activos:**
- Twilio: https://whatsapp-gateway-308574626875.us-central1.run.app/webhook/whatsapp
- Meta: https://whatsapp-gateway-308574626875.us-central1.run.app/webhook/meta

---

**🎉 ¡WEBHOOKS LISTOS PARA CONFIGURAR!**

Sigue los pasos de este documento para configurar Twilio y Meta. Comienza con Twilio para testing rápido, luego configura Meta para producción.

**Tiempo estimado:** 10-15 minutos total
**Dificultad:** Baja
**Resultado:** Bot de WhatsApp completamente funcional

---

**Última actualización:** 2026-01-27
**Preparado por:** Claude Code (Anthropic)
