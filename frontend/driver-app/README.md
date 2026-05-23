# Conductor App - Aplicación para Conductores de Taxi

Aplicación web/móvil para conductores de taxi que permite gestionar viajes en tiempo real, ver ganancias, y administrar su perfil.

## Características

### 🔐 Autenticación
- Login seguro con teléfono y contraseña
- Sesión persistente
- Verificación de token

### 📊 Dashboard Principal
- Toggle de disponibilidad (Disponible/Desconectado)
- Estadísticas en tiempo real:
  - Viajes completados hoy
  - Ganancias del día
  - Calificación promedio
  - Tasa de aceptación
- Notificaciones de nuevos viajes
- Vista de viaje activo

### 🚗 Gestión de Viajes
- Recepción de solicitudes de viaje en tiempo real
- Detalles completos del viaje:
  - Información del cliente
  - Ruta (origen y destino)
  - Distancia y tiempo estimado
  - Tarifa y método de pago
- Aceptar o rechazar viajes
- Navegación integrada con Google Maps y Waze
- Control del estado del viaje:
  - Iniciar viaje (al recoger al cliente)
  - Completar viaje (al llegar al destino)
  - Cancelar viaje (con motivo)

### 📜 Historial
- Listado completo de viajes realizados
- Filtros por:
  - Periodo (hoy, semana, mes, todo)
  - Estado (completados, cancelados)
  - Búsqueda por cliente o dirección
- Resumen de estadísticas
- Detalles de cada viaje

### 💰 Ganancias
- Vista de ganancias por periodo:
  - Hoy
  - Esta semana
  - Este mes
  - Este año
- Desglose por método de pago (efectivo vs tarjeta)
- Desglose diario
- Mejor día de ganancias
- Objetivos de ganancias con progreso visual
- Tips para aumentar ingresos

### 👤 Perfil
- Información personal del conductor
- Estadísticas generales (rating, viajes, aceptación)
- Gestión de vehículo:
  - Marca, modelo, año
  - Placas y color
  - Tipo de vehículo
- Documentos verificados:
  - Licencia de conducir
  - Seguro del vehículo
  - Tarjeta de circulación
- Configuración:
  - Notificaciones push
  - Sonido de alertas
  - Navegación automática
- Enlaces de soporte y ayuda

## Stack Tecnológico

- **Vue.js 3** - Framework JavaScript
- **Vite** - Build tool
- **Pinia** - State management
- **Vue Router 4** - Routing
- **Axios** - HTTP client
- **Tailwind CSS** - Estilos
- **Geolocation API** - Rastreo de ubicación

## Estructura del Proyecto

```
driver-app/
├── src/
│   ├── views/              # Vistas principales
│   │   ├── LoginView.vue
│   │   ├── DashboardView.vue
│   │   ├── RideRequestView.vue
│   │   ├── ActiveRideView.vue
│   │   ├── HistoryView.vue
│   │   ├── EarningsView.vue
│   │   └── ProfileView.vue
│   ├── stores/             # Pinia stores
│   │   ├── authStore.js
│   │   ├── driverStore.js
│   │   └── rideStore.js
│   ├── services/           # API services
│   │   └── api.js
│   ├── router/             # Vue Router
│   │   └── index.js
│   ├── App.vue             # Root component
│   ├── main.js             # App entry point
│   └── style.css           # Global styles
├── index.html
├── vite.config.js
├── tailwind.config.js
├── postcss.config.js
├── package.json
└── README.md
```

## Instalación

1. Instalar dependencias:
```bash
npm install
```

2. Configurar variables de entorno:
```bash
cp .env.example .env
```

Editar `.env` con la URL de tu backend:
```
VITE_API_BASE_URL=http://localhost:8000
```

3. Iniciar servidor de desarrollo:
```bash
npm run dev
```

La aplicación estará disponible en `http://localhost:3002`

## Scripts Disponibles

- `npm run dev` - Inicia servidor de desarrollo
- `npm run build` - Construye para producción
- `npm run preview` - Preview del build de producción
- `npm run lint` - Ejecuta linter

## Flujo de Trabajo del Conductor

1. **Login**
   - El conductor inicia sesión con su teléfono y contraseña

2. **Activación**
   - Cambia su estado a "Disponible" en el dashboard
   - La app comienza a rastrear su ubicación
   - Inicia polling de solicitudes de viaje cada 5 segundos

3. **Recepción de Viajes**
   - Aparece una notificación con detalles del viaje
   - Tiene 30 segundos para aceptar o rechazar
   - Al aceptar, el viaje se asigna y pasa a "Viaje Activo"

4. **Viaje Activo**
   - Ve detalles completos del cliente y ruta
   - Puede llamar o enviar SMS al cliente
   - Navega al origen usando Google Maps/Waze
   - Inicia el viaje al recoger al cliente
   - Navega al destino
   - Completa el viaje al llegar

5. **Post-Viaje**
   - El viaje se agrega al historial
   - Las ganancias se actualizan
   - Regresa al estado disponible
   - Espera el siguiente viaje

6. **Desconexión**
   - Cambia su estado a "Desconectado"
   - Detiene polling y rastreo de ubicación
   - Puede ver historial y ganancias

## Integración con Backend

La aplicación se comunica con el backend a través de la API REST:

### Endpoints Utilizados

**Autenticación:**
- `POST /driver/login` - Login del conductor
- `POST /driver/logout` - Logout
- `GET /driver/verify` - Verificar token

**Conductor:**
- `GET /driver/profile` - Obtener perfil
- `PUT /driver/status` - Actualizar estado (available/offline)
- `PUT /driver/location` - Actualizar ubicación
- `GET /driver/stats` - Obtener estadísticas
- `PUT /driver/profile` - Actualizar perfil

**Viajes:**
- `GET /driver/rides/pending` - Solicitudes pendientes
- `GET /driver/rides/:id` - Detalles de viaje
- `GET /driver/rides/active` - Viaje activo actual
- `POST /driver/rides/:id/accept` - Aceptar viaje
- `POST /driver/rides/:id/reject` - Rechazar viaje
- `POST /driver/rides/:id/start` - Iniciar viaje
- `POST /driver/rides/:id/complete` - Completar viaje
- `POST /driver/rides/:id/cancel` - Cancelar viaje
- `GET /driver/rides/history` - Historial de viajes

**Ganancias:**
- `GET /driver/earnings` - Obtener ganancias por periodo
- `GET /driver/earnings/breakdown` - Desglose detallado

## Características Adicionales

### Polling en Tiempo Real
- Auto-refresh de solicitudes de viaje cada 5 segundos
- Auto-refresh de estadísticas cada 30 segundos
- Actualización automática de estado del viaje activo

### Geolocalización
- Rastreo continuo de ubicación cuando está disponible
- Envío de ubicación al backend cada 10 segundos
- Alta precisión (enableHighAccuracy: true)

### Persistencia
- Token y datos del conductor en localStorage
- Configuraciones guardadas localmente
- Sesión persistente entre recargas

### UX/UI
- Diseño responsivo (móvil y desktop)
- Animaciones suaves
- Indicadores visuales de estado
- Colores distintivos (verde=disponible, amarillo=ocupado, gris=offline)
- Notificaciones visuales

## Seguridad

- Token JWT en headers de autenticación
- Auto-logout en caso de token inválido (401)
- Validación de sesión al iniciar
- Timeout de 10 segundos en requests

## Próximas Mejoras

- Push notifications nativas
- Mapa en vivo con seguimiento en tiempo real
- Chat integrado con clientes
- Modo offline con sincronización
- Reporte de problemas/incidencias
- Sistema de propinas
- Múltiples idiomas
- Tema oscuro
- PWA con instalación offline

## Soporte

Para soporte técnico o reportar problemas, contactar a:
- Email: soporte@taxiapp.com
- Teléfono: +52 55 1234 5678

## Licencia

© 2024 Taxi App. Todos los derechos reservados.
