# 📱 Taxi Customer App - Estructura Completa

## ✅ Estado: Estructura Base Completada

### Archivos de Configuración Creados
- ✅ package.json - Dependencias Vue 3, Vite, Pinia, Axios
- ✅ vite.config.js - Puerto 3004
- ✅ tailwind.config.js - Colores personalizados taxi
- ✅ postcss.config.js
- ✅ index.html
- ✅ .env.example
- ✅ README.md

### Estructura de Directorios
```
taxi-customer-app/
├── src/
│   ├── App.vue                 ✅ Componente raíz
│   ├── main.js                 ✅ Entry point
│   ├── style.css               ✅ Estilos globales
│   ├── router/
│   │   └── index.js            ✅ 7 rutas configuradas
│   ├── stores/                 📝 A implementar:
│   │   ├── authStore.js        - Autenticación cliente
│   │   ├── rideStore.js        - Gestión de viajes
│   │   └── locationStore.js    - Ubicaciones y mapas
│   ├── services/               📝 A implementar:
│   │   └── api.js              - Cliente HTTP con endpoints
│   ├── views/                  📝 A implementar (7 vistas):
│   │   ├── LoginView.vue
│   │   ├── RegisterView.vue
│   │   ├── HomeView.vue        - Mapa + solicitud
│   │   ├── RideTrackingView.vue
│   │   ├── HistoryView.vue
│   │   ├── PaymentView.vue
│   │   └── ProfileView.vue
│   └── components/             📝 A implementar:
│       ├── MapComponent.vue
│       ├── LocationPicker.vue
│       └── RideCard.vue
```

## 🎯 Funcionalidades Principales a Implementar

### 1. Autenticación (LoginView, RegisterView)
- Login con teléfono/email y contraseña
- Registro de nuevos usuarios
- Sesión persistente
- Recovery de contraseña

### 2. Home con Mapa (HomeView)
- Mapa interactivo con Google Maps
- Ubicación actual del usuario
- Búsqueda de direcciones
- Selección de origen y destino con pins
- Estimación de tarifa en tiempo real
- Botón "Solicitar Taxi"
- Destinos favoritos (Casa, Trabajo)
- Promociones disponibles

### 3. Tracking en Tiempo Real (RideTrackingView)
- Mapa con ubicación del conductor en vivo
- Información del conductor:
  - Nombre y foto
  - Vehículo (marca, modelo, placas, color)
  - Rating
- ETA (tiempo estimado de llegada)
- Botones de contacto (llamar, SMS)
- Estados del viaje:
  - Buscando conductor
  - Conductor asignado
  - Conductor en camino
  - Conductor llegando
  - Viaje en progreso
  - Viaje completado
- Botón cancelar viaje

### 4. Historial (HistoryView)
- Lista de viajes completados
- Filtros por fecha
- Búsqueda
- Detalles de cada viaje:
  - Ruta
  - Conductor
  - Tarifa pagada
  - Método de pago
  - Fecha y hora
- Calificaciones otorgadas
- Opción de volver a solicitar el mismo viaje

### 5. Métodos de Pago (PaymentView)
- Lista de tarjetas guardadas
- Agregar nueva tarjeta
- Eliminar tarjeta
- Establecer método predeterminado
- Opción de efectivo
- Historial de transacciones

### 6. Perfil (ProfileView)
- Información personal
- Foto de perfil
- Teléfono y email
- Lugares favoritos:
  - Casa (guardar dirección)
  - Trabajo (guardar dirección)
  - Otros favoritos
- Preferencias:
  - Notificaciones
  - Idioma
  - Tema
- Códigos promocionales aplicados
- Soporte y ayuda
- Cerrar sesión

## 🔄 Stores Pinia

### authStore.js
```javascript
- State: token, customer, loading, error
- Actions:
  - login()
  - register()
  - logout()
  - checkAuth()
  - updateProfile()
```

### rideStore.js
```javascript
- State: activeRide, rideHistory, estimatedFare
- Actions:
  - requestRide()
  - cancelRide()
  - rateRide()
  - fetchActiveRide()
  - fetchHistory()
  - estimateFare()
  - trackRide() // polling cada 5s
```

### locationStore.js
```javascript
- State: currentLocation, origin, destination, favoriteLocations
- Actions:
  - getCurrentLocation()
  - searchAddress()
  - selectOrigin()
  - selectDestination()
  - saveFavoriteLocation()
  - deleteFavoriteLocation()
```

## 🌐 API Endpoints (services/api.js)

### Autenticación
- POST /customer/login
- POST /customer/register
- POST /customer/logout
- GET /customer/verify

### Cliente
- GET /customer/profile
- PUT /customer/profile
- PUT /customer/location

### Viajes
- POST /customer/rides/request
- GET /customer/rides/:id
- POST /customer/rides/:id/cancel
- POST /customer/rides/:id/rate
- GET /customer/rides/active
- GET /customer/rides/history
- POST /customer/rides/estimate

### Ubicaciones
- GET /locations/search?q=query
- POST /locations/geocode
- POST /locations/reverse-geocode
- GET /locations/popular

### Pagos
- GET /customer/payment-methods
- POST /customer/payment-methods
- DELETE /customer/payment-methods/:id
- PUT /customer/payment-methods/:id/default

### Promociones
- POST /customer/promo/validate
- GET /customer/promo/available

## 📊 Flujo de Usuario

1. **Primera vez**:
   - Usuario abre la app
   - Ve pantalla de login
   - Crea cuenta (RegisterView)
   - Otorga permisos de ubicación
   - Configura método de pago
   - Ve el mapa (HomeView)

2. **Solicitar viaje**:
   - Usuario ve el mapa con su ubicación
   - Selecciona destino (buscador o mapa)
   - Ve estimación de tarifa
   - Confirma solicitud
   - Sistema busca conductor
   - Conductor asignado
   - Usuario ve RideTrackingView

3. **Durante el viaje**:
   - Ve ubicación del conductor en tiempo real
   - Ve ETA
   - Puede contactar al conductor
   - Ve estado actualizado

4. **Fin del viaje**:
   - Conductor completa el viaje
   - Usuario califica al conductor
   - Ve recibo
   - Cargo automático o pago en efectivo
   - Regresa a HomeView

## 🔧 Componentes Reutilizables

- **MapComponent.vue**: Mapa de Google Maps con markers
- **LocationPicker.vue**: Buscador de direcciones con autocompletado
- **RideCard.vue**: Tarjeta de viaje para historial
- **DriverInfo.vue**: Info del conductor durante el viaje
- **FareEstimate.vue**: Tarjeta de estimación de tarifa
- **PaymentMethodCard.vue**: Tarjeta de método de pago

## 🎨 Diseño y UX

- **Colores**:
  - Primary: taxi-yellow (#FFC107)
  - Success: taxi-green (#4CAF50)
  - Info: taxi-blue (#2196F3)
  - Danger: taxi-red (#F44336)

- **Características**:
  - Diseño limpio y minimalista
  - Mapa ocupa pantalla completa
  - Cards flotantes sobre el mapa
  - Animaciones suaves
  - Responsive (móvil first)
  - Loading states claros
  - Feedback visual inmediato

## 🚀 Próximos Pasos de Implementación

1. **Fase 1 - Autenticación** (2-3 horas):
   - Implementar LoginView y RegisterView
   - Crear authStore completo
   - Integrar con backend

2. **Fase 2 - Mapa y Solicitud** (4-5 horas):
   - Integrar Google Maps en HomeView
   - Implementar LocationPicker
   - Crear estimación de tarifa
   - Botón de solicitud de viaje

3. **Fase 3 - Tracking** (3-4 horas):
   - RideTrackingView con mapa en vivo
   - Polling del estado del viaje
   - Información del conductor
   - Botones de contacto

4. **Fase 4 - Secundarias** (2-3 horas):
   - HistoryView
   - PaymentView
   - ProfileView

## 📝 Notas Importantes

- Requiere Google Maps API Key válida
- Debe configurarse VITE_GOOGLE_MAPS_API_KEY en .env
- La app depende de que el backend esté corriendo
- Geolocalización requiere HTTPS en producción
- Push notifications requieren service worker

## 🔗 Integración con Otros Componentes

- **Backend**: API REST en http://localhost:8000
- **Driver App**: Puerto 3002
- **Admin Panel**: Puerto 3001
- **Customer App**: Puerto 3004

---

**Estado**: Estructura base lista para implementación
**Siguiente paso**: Implementar stores y servicios API
