# Configurar Deepgram para Notas de Voz

## ✅ Funcionalidad Implementada

Ahora el WhatsApp Gateway puede **transcribir notas de voz** automáticamente usando Deepgram STT (Speech-to-Text).

**Cómo funciona:**
1. Usuario envía nota de voz por WhatsApp 🎤
2. Sistema descarga el audio de Twilio
3. Deepgram transcribe a texto en ~1-2 segundos
4. Mesero virtual procesa el texto
5. Responde con texto como siempre ✅

---

## 🔧 Configuración Necesaria

### **Paso 1: Crear cuenta en Deepgram**

1. Ve a https://deepgram.com
2. Click en "Start Free" o "Sign Up"
3. Crea una cuenta (puedes usar Google/GitHub)
4. **Obtienes $200 USD de crédito gratis** al registrarte

### **Paso 2: Obtener API Key**

1. Una vez logueado, ve al Dashboard
2. En el menú lateral, click en **"API Keys"**
3. Click en **"Create a New API Key"**
4. Dale un nombre (ej: "WhatsApp Gateway")
5. **Copia la API Key** (la verás solo una vez)

La API Key se ve así:
```
f7a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6
```

### **Paso 3: Agregar al archivo .env**

1. Abre el archivo `.env` en la raíz del proyecto
2. Agrega esta línea:

```bash
# Deepgram API Key para Speech-to-Text (notas de voz)
DEEPGRAM_API_KEY=TU_API_KEY_AQUI
```

3. Reemplaza `TU_API_KEY_AQUI` con tu API key real
4. Guarda el archivo

### **Paso 4: Restart del servicio**

```bash
docker-compose restart whatsapp-gateway
```

---

## ✅ Verificar que Funciona

### **Opción 1: Revisar logs al iniciar**

```bash
docker logs restaurant_whatsapp_gateway --tail 20
```

Deberías ver:
```
INFO:src.stt_client:[STT] Deepgram inicializado correctamente
```

Si ves esto, significa que NO está configurado:
```
WARNING:src.stt_client:[STT] Deepgram API key no configurada
```

### **Opción 2: Enviar nota de voz de prueba**

1. Abre WhatsApp
2. Envía una nota de voz al bot diciendo:
   🎤 "Quiero una hamburguesa deluxe con papas"

3. Revisa los logs:
```bash
docker logs restaurant_whatsapp_gateway -f
```

Deberías ver:
```
INFO:src.main:[Twilio] Nota de voz recibida de +52XXXXXXXXXX
INFO:src.stt_client:[STT] Transcribiendo 12543 bytes de audio...
INFO:src.stt_client:[STT] Transcripción exitosa: 'quiero una hamburguesa deluxe con papas'
INFO:src.hybrid_flow_handler:[HybridFlow] Mensaje procesado...
```

4. El bot te responderá con texto normalmente

---

## 💰 Costos de Deepgram

| Plan | Precio | Incluye |
|------|--------|----------|
| **Free Tier** | $0 | $200 USD de crédito inicial |
| **Pay as you go** | $0.0043/min | Solo pagas lo que usas |

**Ejemplos de costo:**
- Nota de voz de 30 segundos: **$0.002 USD** (~4 centavos MXN)
- 1,000 notas de voz de 30 seg: **$2 USD** (~$40 MXN)
- Con $200 USD gratis: **~100,000 notas de voz** 🚀

**Muy económico** ✅

---

## 🔍 Troubleshooting

### **Problema: Bot no transcribe notas de voz**

**Solución 1:** Verifica que DEEPGRAM_API_KEY esté en el .env
```bash
cat .env | grep DEEPGRAM
```

**Solución 2:** Revisa los logs para ver el error
```bash
docker logs restaurant_whatsapp_gateway --tail 50 | grep STT
```

**Solución 3:** Verifica que la API key sea válida
- Ve a https://console.deepgram.com/
- Revisa que la API key esté activa
- Crea una nueva si es necesario

### **Problema: Error "Invalid API key"**

- Revisa que copiaste la API key completa
- Asegúrate de no tener espacios antes/después
- Verifica que no esté entre comillas en el .env

### **Problema: Transcripción vacía o incorrecta**

- Deepgram funciona mejor con audio claro
- Pide al usuario que hable más despacio
- Revisa que el audio no esté muy distorsionado

---

## 📊 Monitoreo

Para ver estadísticas de uso de Deepgram:
1. Ve a https://console.deepgram.com/
2. Click en **"Usage"**
3. Verás gráficas de:
   - Minutos transcribidos
   - Crédito restante
   - Requests por día

---

## 🎯 Resumen

| Configuración | Estado |
|---------------|--------|
| ✅ Código implementado | Listo |
| ⏳ Deepgram API Key | Necesitas configurar |
| ✅ Dependencias instaladas | Listo |

**Siguiente paso:** Agregar `DEEPGRAM_API_KEY` al archivo `.env` 🚀
