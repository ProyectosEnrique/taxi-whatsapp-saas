# 🚀 Configuración de Demo Interactiva - Twilio + Cloudflare

## Índice
1. [Descripción General](#descripción-general)
2. [Configurar Twilio WhatsApp](#1-configurar-twilio-whatsapp)
3. [Configurar Cloudflare Tunnel](#2-configurar-cloudflare-tunnel)
4. [Iniciar el Sistema](#3-iniciar-el-sistema)
5. [Probar la Demo](#4-probar-la-demo)
6. [Promocionar la Demo](#5-promocionar-la-demo)
7. [Analytics y Seguimiento](#6-analytics-y-seguimiento)

---

## Descripción General

Este sistema te permite tener una demo **REAL** e **INTERACTIVA** donde prospectos pueden:

✅ Escanear un QR y abrir WhatsApp
✅ Explorar 6 tipos de negocios diferentes
✅ Navegar catálogos web reales
✅ Completar checkouts con sistema de puntos
✅ Recibir confirmaciones automáticas por WhatsApp

**Sin instalar nada, 100% funcional desde su teléfono.**

---

## 1. Configurar Twilio WhatsApp

### Paso 1: Crear Cuenta en Twilio

1. Ve a [https://www.twilio.com/try-twilio](https://www.twilio.com/try-twilio)
2. Regístrate con tu email
3. Verifica tu número de teléfono
4. Activa tu cuenta (Twilio te da $15 USD de crédito gratis)

### Paso 2: Comprar Número con WhatsApp

1. En el dashboard de Twilio, ve a **Phone Numbers** → **Buy a Number**
2. Selecciona:
   - **Country**: Mexico (+52)
   - **Capabilities**: ✅ WhatsApp
3. Busca un número disponible
4. Cómpralo (costo: ~$2 USD/mes)

![Twilio Buy Number](https://i.imgur.com/example.png)

### Paso 3: Habilitar WhatsApp en el Número

1. Ve a **Messaging** → **WhatsApp senders** (o Sandbox si es prueba)
2. Para **Producción**:
   - Solicitar aprobación de plantilla de mensaje
   - Configurar perfil de negocio
   - Esperar aprobación de Meta (~2-3 días)

3. Para **Sandbox (desarrollo)**:
   - Puedes usar inmediatamente
   - Solo tú y personas que se unan al sandbox pueden probarlo
   - Límite: ~50 mensajes/día

**Para esta demo, usa Sandbox inicialmente:**

1. Ve a **Messaging** → **Try it out** → **Send a WhatsApp message**
2. Escanea el QR con tu WhatsApp
3. Envía el código que te piden (ej: "join example-word")
4. ¡Listo! Tu WhatsApp está conectado

### Paso 4: Obtener Credenciales

1. Ve a **Account** → **API keys & tokens**
2. Copia:
   - **Account SID**: `ACxxxxxxxxxxxxxxxxxxxxxxxxxx`
   - **Auth Token**: `xxxxxxxxxxxxxxxxxxxxxx`
3. Anótalos, los necesitarás después

### Paso 5: Configurar Webhook

**IMPORTANTE**: Necesitas primero configurar Cloudflare Tunnel (siguiente sección) para tener una URL pública.

Una vez que tengas tu URL de Cloudflare (ej: `https://demo.tudominio.com`):

1. Ve a **Phone Numbers** → **Manage** → Tu número WhatsApp
2. En **Messaging Configuration**:
   - **A MESSAGE COMES IN**:
     - Webhook: `https://demo.tudominio.com/webhook/twilio`
     - Method: `HTTP POST`

3. Guarda cambios

---

## 2. Configurar Cloudflare Tunnel

Cloudflare Tunnel te permite exponer tu servidor local a internet con una URL fija y SSL automático.

### Ventajas vs ngrok:
- ✅ **URL permanente** (no cambia cada vez)
- ✅ **SSL automático** (HTTPS gratis)
- ✅ **Sin límite de tiempo**
- ✅ **Gratis para siempre**
- ✅ **Más rápido y estable**

### Paso 1: Instalar cloudflared

**Windows:**
```powershell
# Descargar desde GitHub
Invoke-WebRequest -Uri "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe" -OutFile "cloudflared.exe"

# Mover a una ubicación en PATH (opcional)
Move-Item cloudflared.exe C:\Windows\System32\cloudflared.exe
```

**Linux/Mac:**
```bash
# Linux
wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64
chmod +x cloudflared-linux-amd64
sudo mv cloudflared-linux-amd64 /usr/local/bin/cloudflared

# Mac
brew install cloudflared
```

### Paso 2: Autenticarse con Cloudflare

```bash
cloudflared tunnel login
```

Esto abrirá tu navegador. Selecciona el dominio donde quieres crear el tunnel.

### Paso 3: Crear el Tunnel

```bash
# Crear tunnel con nombre "demo-whatsapp"
cloudflared tunnel create demo-whatsapp
```

Esto generará un tunnel ID y un archivo de credenciales:
```
Tunnel credentials written to C:\Users\TuUsuario\.cloudflared\xxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx.json
```

Anota el **Tunnel ID** (las X's).

### Paso 4: Configurar DNS

```bash
# Asociar un subdominio a tu tunnel
cloudflared tunnel route dns demo-whatsapp demo.tudominio.com
```

Reemplaza `demo.tudominio.com` con tu dominio real.

### Paso 5: Crear Archivo de Configuración

Crea un archivo `config.yml` en `C:\Users\TuUsuario\.cloudflared\config.yml`:

```yaml
tunnel: TUNNEL_ID_AQUI
credentials-file: C:\Users\TuUsuario\.cloudflared\TUNNEL_ID_AQUI.json

ingress:
  - hostname: demo.tudominio.com
    service: http://localhost:8080
  - service: http_status:404
```

Reemplaza:
- `TUNNEL_ID_AQUI` con tu tunnel ID real
- `demo.tudominio.com` con tu dominio real

### Paso 6: Iniciar el Tunnel

```bash
cloudflared tunnel run demo-whatsapp
```

O para correr como servicio en background:

**Windows:**
```powershell
cloudflared service install
cloudflared service start
```

**Linux:**
```bash
sudo cloudflared service install
sudo systemctl start cloudflared
sudo systemctl enable cloudflared
```

### Verificar que funciona:

Abre `https://demo.tudominio.com/health` en tu navegador.

Deberías ver:
```json
{
  "status": "healthy",
  "service": "whatsapp-gateway",
  "provider": "twilio"
}
```

---

## 3. Iniciar el Sistema

### Configurar Variables de Entorno

Crea un archivo `.env` en `backend/whatsapp-gateway/`:

```env
# Twilio
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_WHATSAPP_NUMBER=whatsapp:+5255XXXXXXXX

# WhatsApp Provider
WHATSAPP_PROVIDER=twilio

# Cloudflare URL (para generar links)
BASE_URL=https://demo.tudominio.com

# Opcional: Pagos (dejar vacío para solo efectivo)
STRIPE_SECRET_KEY=
MERCADOPAGO_ACCESS_TOKEN=

# Opcional: STT para notas de voz
DEEPGRAM_API_KEY=
```

### Iniciar el Gateway

```bash
cd backend/whatsapp-gateway

# Instalar dependencias
pip install -r requirements.txt

# Iniciar con uvicorn
python -m uvicorn src.main:app --host 0.0.0.0 --port 8080 --reload
```

O usa el script helper:
```bash
python run_gateway.py
```

### Verificar que todo funciona:

1. **Gateway está corriendo**: http://localhost:8080/health
2. **Cloudflare expone el gateway**: https://demo.tudominio.com/health
3. **Twilio webhook está configurado**: Envía un mensaje de prueba a tu WhatsApp

---

## 4. Probar la Demo

### Flujo Completo de Prueba:

1. **Envía un mensaje** a tu número de Twilio WhatsApp
2. **Recibes bienvenida** con menú de industrias
3. **Selecciona "1"** (Restaurante)
4. **Recibes link** al catálogo web
5. **Abre el link**, agrega productos
6. **Completa checkout** (solo efectivo disponible)
7. **Recibes confirmación** automática con puntos

### Mensaje de Bienvenida Esperado:

```
👋 ¡Bienvenido a la DEMO INTERACTIVA!

Soy un asistente con IA. Aquí puedes PROBAR EN VIVO
cómo funciona nuestro sistema de ventas por WhatsApp.

✨ En esta demo:
✅ Exploras negocios reales (restaurante, tienda, etc)
✅ Navegas catálogos web completos
✅ Pruebas el checkout con puntos de fidelidad
✅ Recibes confirmaciones automáticas

🎁 Te daré 500 puntos de regalo para que
   pruebes cómo funciona el sistema de fidelidad.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎮 ¿Qué tipo de negocio quieres explorar?

1️⃣ 🍔 RESTAURANTE / TAQUERÍA
2️⃣ 🛍️ TIENDA / BOUTIQUE
3️⃣ 💊 FARMACIA / SALUD
4️⃣ 🛒 ABARROTES / SUPERMERCADO
5️⃣ 💇 SERVICIOS / SALÓN DE BELLEZA
6️⃣ 🐶 TIENDA DE MASCOTAS

Escribe el número de tu elección (ej: 1)
```

---

## 5. Promocionar la Demo

### Generar QR Code

**Opción 1: QR de WhatsApp Directo**

```
https://wa.me/5255XXXXXXXX
```

Genera el QR en: https://www.qr-code-generator.com/

**Opción 2: QR con Mensaje Pre-llenado**

```
https://wa.me/5255XXXXXXXX?text=Hola,%20quiero%20conocer%20el%20sistema
```

### Material de Marketing

**1. Volante/Flyer:**

```
┌─────────────────────────────────────┐
│  🚀 PRUEBA GRATIS NUESTRO SISTEMA  │
│     DE VENTAS POR WHATSAPP          │
│                                     │
│    ┌────────────┐                  │
│    │  QR CODE   │  ← Escanea       │
│    └────────────┘                  │
│                                     │
│  ✅ Sin instalar nada              │
│  ✅ Prueba 6 tipos de negocios     │
│  ✅ 100% funcional                 │
│                                     │
│  O escribe al: +52 55 XXXX XXXX    │
└─────────────────────────────────────┘
```

**2. Post para Redes Sociales:**

```
🚀 ¿Tienes un negocio local?

Prueba GRATIS cómo funciona nuestro sistema
de ventas por WhatsApp + Web.

✅ Sin apps para tus clientes
✅ Sin comisiones del 30% como Rappi
✅ Tu propia base de datos
✅ Sistema de puntos incluido

👉 Escanea el QR o escribe al +52 55 XXXX XXXX

#VentasPorWhatsApp #NegociosLocales #SinComisiones
```

**3. Email de Prospección:**

```
Asunto: ¿Cuánto pierdes pagando 30% de comisión a Rappi?

Hola [Nombre],

Si vendes $100,000 al mes, estás pagando $30,000 en comisiones.

Tengo una solución que cuesta solo $999/mes (sin comisiones):

🌮 Sistema completo de ventas por WhatsApp + Web
💰 Tus clientes pagan directamente a ti
📊 Base de datos 100% tuya
⭐ Sistema de puntos de fidelidad incluido

¿Quieres probarlo GRATIS?

Escanea este QR [ADJUNTAR QR] o escríbeme al +52 55 XXXX XXXX

En 5 minutos verás cómo funciona.

Saludos,
[Tu Nombre]
```

---

## 6. Analytics y Seguimiento

### Endpoint de Analytics

```bash
curl https://demo.tudominio.com/api/v1/demo/analytics
```

Response:
```json
{
  "total_prospects": 45,
  "completed_checkouts": 23,
  "requested_info": 18,
  "conversion_rate": 40.0,
  "checkout_rate": 51.11,
  "industry_popularity": {
    "demo_restaurant": 25,
    "demo_retail": 12,
    "demo_pharmacy": 8,
    "demo_grocery": 7,
    "demo_services": 5,
    "demo_pets": 3
  }
}
```

### Ver Prospectos

Los datos se guardan automáticamente en:
```
backend/whatsapp-gateway/data/demo/prospects.json
```

Puedes revisarlo para hacer follow-up:

```json
{
  "5215512345678": {
    "phone": "5215512345678",
    "industries_explored": ["demo_restaurant", "demo_retail"],
    "completed_checkout": true,
    "requested_info": true,
    "created_at": "2025-01-07T10:30:00",
    "last_interaction": "2025-01-07T10:45:00"
  }
}
```

### Follow-up Automático

Puedes crear un script para hacer follow-up:

```python
import json
from datetime import datetime, timedelta

# Leer prospectos
with open('data/demo/prospects.json') as f:
    prospects = json.load(f)

# Filtrar: completaron checkout pero no pidieron info
hot_leads = []
for phone, data in prospects.items():
    if data['completed_checkout'] and not data['requested_info']:
        hot_leads.append(phone)

print(f"Leads calientes: {len(hot_leads)}")

# Enviar mensaje de follow-up
for phone in hot_leads:
    # whatsapp_client.send_message(phone, "...")
    print(f"Follow-up a: {phone}")
```

---

## 7. Costos Estimados

### Twilio WhatsApp:
- **Número**: $2 USD/mes
- **Mensajes**: $0.005 USD por mensaje
- **100 prospectos/mes**: ~$3 USD total

### Cloudflare Tunnel:
- **Gratis para siempre** ✅

### Total:
- **~$5 USD/mes** para demo ilimitada

---

## 8. Troubleshooting

### Problema: "Webhook no responde"

```bash
# Verificar que el gateway está corriendo
curl http://localhost:8080/health

# Verificar que Cloudflare está activo
curl https://demo.tudominio.com/health

# Ver logs del tunnel
cloudflared tunnel info demo-whatsapp
```

### Problema: "No recibo mensajes"

1. Verificar webhook en Twilio dashboard
2. Ver logs del gateway:
   ```bash
   # El log debe mostrar:
   [Twilio] Mensaje de 5215512345678: Hola
   ```

3. Verificar que enviaste el "join" al sandbox

### Problema: "Link no abre catálogo"

1. Verificar BASE_URL en `.env`
2. Verificar que el frontend está desplegado
3. Ver logs del navegador (F12 → Console)

---

## 9. Próximos Pasos

Una vez que la demo funciona:

1. **Migrar de Sandbox a Producción**:
   - Solicitar aprobación de plantillas en Twilio
   - Configurar perfil de negocio
   - Esperar aprobación de Meta

2. **Agregar más industrias**:
   - Editar `src/demo_config.py`
   - Agregar catálogos personalizados

3. **Personalizar mensajes**:
   - Modificar textos en `demo_config.py`
   - Agregar tu branding

4. **Integrar CRM**:
   - Exportar prospectos automáticamente
   - Crear pipeline de ventas

---

¡Listo! Ahora tienes una demo **REAL** e **INTERACTIVA** funcionando 24/7.

Cualquier prospecto puede escanear el QR y probar el sistema completo desde su WhatsApp.

**¡A cerrar ventas! 🚀**
