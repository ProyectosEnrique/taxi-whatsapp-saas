# Taxi Customer App - Aplicación para Clientes

Aplicación web/móvil para clientes que permite solicitar viajes de taxi, seguimiento en tiempo real, historial y gestión de pagos.

## Características

### 🏠 Página Principal
- Mapa interactivo con ubicación actual
- Selección de origen y destino
- Estimación de tarifa en tiempo real
- Solicitud de viaje con un click

### 🚗 Seguimiento de Viaje
- Tracking en tiempo real del conductor
- Información del conductor (nombre, foto, vehículo)
- Tiempo estimado de llegada (ETA)
- Contacto directo con el conductor
- Estado del viaje en vivo

### 📜 Historial
- Lista completa de viajes realizados
- Detalles de cada viaje
- Recibos y facturas
- Calificaciones otorgadas

### 💳 Métodos de Pago
- Tarjetas de crédito/débito
- Efectivo
- Gestión de métodos de pago
- Historial de transacciones

### 👤 Perfil
- Información personal
- Lugares favoritos (casa, trabajo)
- Configuración de preferencias
- Soporte y ayuda

## Instalación

```bash
cd frontend/taxi-customer-app
npm install
cp .env.example .env
# Editar .env con tus configuraciones
npm run dev
```

La aplicación estará disponible en `http://localhost:3004`

## Stack Tecnológico

- Vue.js 3
- Vite
- Pinia
- Vue Router 4
- Axios
- Tailwind CSS
- Google Maps API

## Puerto

- Desarrollo: 3004
- Producción: Configurar según deployment
