# 🚀 PASOS COMPLETOS PARA INICIAR EL PROYECTO

## ✅ YA COMPLETADO

- ✓ Docker limpiado (~20 GB liberados)
- ✓ Archivo `.env` creado con credenciales
- ✓ Base de datos con 3 tiendas (199 productos)
- ✓ Scripts de inicio creados

---

## 📋 PASO A PASO

### **PASO 1: Optimizar Docker Desktop** (2 minutos) ⭐

**Opción A - Automático:**
```
Doble click en:
C:\Users\ASUS\Desktop\PROYECTOS_AGENTE_VENTAS\ABRIR_DOCKER_SETTINGS.bat
```

**Opción B - Manual:**

1. Abrir **Docker Desktop**
2. Click en ⚙️ **Settings** (arriba derecha)
3. **Resources → Advanced**
4. Configurar:
   ```
   CPUs:   2
   Memory: 2 GB
   Swap:   1 GB
   Disk:   20 GB
   ```
5. Click **Apply & Restart**
6. Esperar 30 segundos

✅ **Beneficio:** Libera 2-6 GB de RAM

---

### **PASO 2: Iniciar el Proyecto** (5-15 minutos primera vez)

```
Doble click en:
C:\Users\ASUS\Desktop\PROYECTOS_AGENTE_VENTAS\PROYECTO_B_WHATSAPP_SAAS\INICIAR_PROYECTO.bat
```

**Te preguntará:**
```
1. LIGERO   - Solo WhatsApp (3 servicios, ~1 GB RAM) ⭐ RECOMENDADO
2. COMPLETO - Todos los servicios (5 servicios, ~2 GB RAM)
```

**Elige opción 1** para empezar.

**Primera vez tomará 10-15 minutos** (descarga imágenes Docker)
**Siguientes veces: 30 segundos**

---

### **PASO 3: Exponer con ngrok** (1 minuto)

**Abrir NUEVA ventana de comandos** y ejecutar:

```
Doble click en:
C:\Users\ASUS\Desktop\PROYECTOS_AGENTE_VENTAS\PROYECTO_B_WHATSAPP_SAAS\INICIAR_NGROK.bat
```

**Verás algo como:**
```
Session Status    online
Forwarding        https://abc123.ngrok.io -> http://localhost:8095
                  ^^^^^^^^^^^^^^^^^^^^^^^^
                  COPIA ESTA URL
```

⚠️ **IMPORTANTE:** Deja esta ventana ABIERTA

---

### **PASO 4: Configurar Webhook en Twilio** (2 minutos)

1. Ve a: https://console.twilio.com/us1/develop/sms/settings/whatsapp-sandbox

2. En **"When a message comes in":**
   ```
   URL: https://abc123.ngrok.io/webhook/whatsapp
        ^^^^^^^^^^^^^^^^^^^^^^
        (pega tu URL de ngrok + /webhook/whatsapp)

   Method: POST
   ```

3. Click **SAVE**

---

### **PASO 5: Activar WhatsApp Sandbox** (1 minuto)

Si no lo has hecho antes:

1. En la misma página de Twilio verás:
   ```
   join stomach-mountain
   ^^^^^^^^^^^^^^^^^^^^^^
   (tu código único)
   ```

2. Desde tu WhatsApp:
   - Buscar: **+1 415 523 8886**
   - Enviar: `join stomach-mountain` (tu código)
   - Recibirás: "✅ You are all set!"

---

### **PASO 6: PROBAR LAS 3 TIENDAS** 🎉

Desde tu WhatsApp al número **+1 415 523 8886**:

#### **🍽️ Restaurante "El Sabor del Sur"**
```
Hola, quiero tacos
```

#### **🍷 Vinetería "Vinos y Licores Premium"**
```
Hola, tienen vino tinto?
```

#### **💊 Farmacia "FarmaSalud 24/7"**
```
Hola, necesito paracetamol
```

**El sistema detecta automáticamente la tienda** según las keywords.

---

## 🔍 VERIFICAR QUE TODO FUNCIONA

### Ver logs en tiempo real:

```bash
cd C:\Users\ASUS\Desktop\PROYECTOS_AGENTE_VENTAS\PROYECTO_B_WHATSAPP_SAAS
docker-compose logs -f whatsapp-gateway
```

Deberías ver:
```
[INFO] Mensaje recibido de: +52XXXXXXXXXX
[INFO] Mensaje: "Hola, quiero tacos"
[INFO] Tenant detectado: restaurante-sabor-sur
[INFO] Respuesta enviada
```

### Ver estado de servicios:

```bash
docker-compose ps
```

Deberías ver:
```
NAME                STATE    PORTS
whatsapp-gateway    Up       8095:8000
sales-agent         Up       5000:5000
api-service         Up       5011:5011
```

---

## 🛑 DETENER EL PROYECTO

Cuando termines de probar:

```bash
cd C:\Users\ASUS\Desktop\PROYECTOS_AGENTE_VENTAS\PROYECTO_B_WHATSAPP_SAAS
docker-compose down
```

Esto libera la RAM pero **NO elimina** las imágenes (inicio rápido la próxima vez).

---

## 🐛 TROUBLESHOOTING

### Error: "Cannot connect to Docker daemon"
- ✅ Abre Docker Desktop
- ✅ Espera a que diga "Docker Desktop is running"
- ✅ Ejecuta `INICIAR_PROYECTO.bat` de nuevo

### Error: "Port 8095 already in use"
```bash
# Ver qué usa el puerto
netstat -ano | findstr :8095

# Matar el proceso
taskkill /PID [numero] /F
```

### Webhook no recibe mensajes
1. ✅ Verifica que ngrok esté corriendo
2. ✅ Copia la URL COMPLETA de ngrok
3. ✅ Configura en Twilio con `/webhook/whatsapp` al final
4. ✅ Método debe ser **POST**

### Bot no responde
```bash
# Ver logs del sales-agent
docker-compose logs sales-agent

# Revisar si hay errores de API keys
```

---

## 📊 RESUMEN DE RECURSOS

```
Modo LIGERO (Recomendado):
├─ Servicios: 3
├─ RAM usada: ~1 GB
├─ Tiempo inicio: 30 segundos
└─ Funcionalidad: WhatsApp completo ✓

Modo COMPLETO:
├─ Servicios: 5
├─ RAM usada: ~2 GB
├─ Tiempo inicio: 45 segundos
└─ Funcionalidad: WhatsApp + Admin Panel + Customer App
```

---

## ✅ CHECKLIST FINAL

```bash
[ ] Docker Desktop optimizado (2 GB RAM, 20 GB Disk)
[ ] INICIAR_PROYECTO.bat ejecutado sin errores
[ ] docker-compose ps muestra servicios "Up"
[ ] INICIAR_NGROK.bat corriendo en otra ventana
[ ] URL de ngrok copiada
[ ] Webhook configurado en Twilio
[ ] Join code enviado al sandbox de Twilio
[ ] Mensaje de prueba enviado a +14155238886
[ ] Bot respondió correctamente
```

---

## 🎯 SIGUIENTE PASO

Una vez que todo funcione:

1. **Probar las 3 tiendas** (restaurante, vinetería, farmacia)
2. **Ver logs** para entender el flujo
3. **Experimentar** con diferentes productos
4. **Personalizar prompts** (opcional - avanzado)

---

**Estado actual:** ✅ TODO LISTO PARA INICIAR

**Tiempo total:** 10-20 minutos (primera vez)

**Siguiente comando:** Ejecutar `INICIAR_PROYECTO.bat`
