# ⚡ CONFIGURACIÓN RÁPIDA DE WEBHOOKS

**Servicio verificado:** ✅ whatsapp-gateway está activo y saludable

---

## 🔵 TWILIO WHATSAPP (5 minutos)

### 1. Ir a Twilio Console
```
https://console.twilio.com/us1/develop/sms/try-it-out/whatsapp-learn
```

**Credenciales:**
- Account SID: `ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`
- Auth Token: `xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

### 2. Configurar Webhook

En **"When a message comes in"**, pega:
```
https://whatsapp-gateway-308574626875.us-central1.run.app/webhook/whatsapp
```

Método: **HTTP POST**

### 3. Activar Sandbox

Desde tu WhatsApp:
1. Agrega: **+1 415 523 8886**
2. Envía el mensaje que aparece en la consola (ej: `join restaurant-bot`)

### 4. Probar

Envía: `Hola`

---

## 🟢 META WHATSAPP BUSINESS (10 minutos)

### 1. Ir a Meta Developers
```
https://developers.facebook.com/apps
```

### 2. Configurar Webhook

1. Selecciona tu App de WhatsApp
2. Ve a: **WhatsApp → Configuration**
3. Haz clic en **Configure Webhook**

**Callback URL:**
```
https://whatsapp-gateway-308574626875.us-central1.run.app/webhook/meta
```

**Verify Token:**
```
mi_token_secreto_restaurant_2025
```

4. Haz clic en **Verify and Save**

### 3. Suscribir Eventos

Activa:
- ✅ messages
- ✅ messaging_postbacks

### 4. Agregar Número de Prueba

1. Ve a: **WhatsApp → API Setup**
2. En **"To"**, haz clic en **Add phone number**
3. Agrega tu número con código de país (ej: +52 para México)
4. Verifica el código que llegue a WhatsApp

### 5. Probar

Desde tu número verificado, envía WhatsApp al número de tu negocio:
```
Hola
```

---

## ✅ VERIFICACIÓN

### Test del Webhook

```bash
# Debería retornar: {"status":"healthy","service":"whatsapp-gateway","provider":"meta"}
curl https://whatsapp-gateway-308574626875.us-central1.run.app/health
```

### Ver Logs en Tiempo Real

```powershell
& "C:\Program Files (x86)\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd" run logs tail whatsapp-gateway --region=us-central1
```

---

## 🎯 MULTI-TENANT (Opcional)

Para diferentes negocios, agrega `?tenant=nombre` al webhook:

```
Restaurant: .../webhook/whatsapp?tenant=restaurant
Farmacia:   .../webhook/whatsapp?tenant=farmacia
Taxis:      .../webhook/whatsapp?tenant=taxis
```

---

## 🆘 Si algo falla

1. Ver logs: `gcloud run logs read whatsapp-gateway --region=us-central1 --limit=20`
2. Ver guía completa: `CONFIGURACION_WEBHOOKS.md`
3. Verificar que el servicio esté activo: `curl [url]/health`

---

**URLs Importantes:**

- Twilio Console: https://console.twilio.com/
- Meta Developers: https://developers.facebook.com/
- Webhook Gateway: https://whatsapp-gateway-308574626875.us-central1.run.app
- Guía Completa: CONFIGURACION_WEBHOOKS.md

---

**✅ Status:** Servicios activos, listos para recibir webhooks
