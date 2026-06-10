<template>
  <div class="min-h-screen bg-gray-50">
    <!-- Header -->
    <header class="bg-white shadow-sm sticky top-0 z-10">
      <div class="max-w-7xl mx-auto px-4 py-4">
        <div class="flex items-center justify-between">
          <!-- Logo y saludo -->
          <div class="flex items-center space-x-3">
            <span class="text-3xl">🚕</span>
            <div>
              <h1 class="text-xl font-bold text-gray-900">Hola, {{ driverName }}</h1>
              <p class="text-sm text-gray-500">{{ currentDate }}</p>
            </div>
          </div>

          <!-- Status toggle y menú -->
          <div class="flex items-center space-x-4">
            <!-- Toggle de disponibilidad -->
            <div class="flex items-center space-x-2 bg-gray-100 rounded-full p-1">
              <button
                @click="setStatus('available')"
                :class="[
                  'px-4 py-2 rounded-full text-sm font-medium transition-all',
                  driverStore.isAvailable
                    ? 'bg-green-500 text-white shadow-md'
                    : 'text-gray-600 hover:text-gray-900'
                ]"
              >
                ✓ Disponible
              </button>
              <button
                @click="setStatus('offline')"
                :class="[
                  'px-4 py-2 rounded-full text-sm font-medium transition-all',
                  driverStore.isOffline
                    ? 'bg-gray-500 text-white shadow-md'
                    : 'text-gray-600 hover:text-gray-900'
                ]"
              >
                ○ Desconectado
              </button>
            </div>

            <!-- Menú hamburguesa -->
            <button
              @click="showMenu = !showMenu"
              class="p-2 hover:bg-gray-100 rounded-lg"
            >
              <span class="text-2xl">☰</span>
            </button>
          </div>
        </div>
      </div>

      <!-- Menú desplegable -->
      <div
        v-if="showMenu"
        class="absolute right-4 top-20 bg-white shadow-lg rounded-lg py-2 w-48 z-20"
      >
        <router-link
          to="/profile"
          class="block px-4 py-2 hover:bg-gray-100 text-gray-700"
          @click="showMenu = false"
        >
          👤 Mi Perfil
        </router-link>
        <router-link
          to="/agenda"
          class="flex items-center justify-between px-4 py-2 hover:bg-gray-100 text-gray-700"
          @click="showMenu = false"
        >
          <span>📅 Agenda</span>
          <span
            v-if="rideStore.myScheduledRides.length"
            class="bg-yellow-400 text-white text-xs font-bold px-2 py-0.5 rounded-full"
          >
            {{ rideStore.myScheduledRides.length }}
          </span>
        </router-link>
        <router-link
          to="/history"
          class="block px-4 py-2 hover:bg-gray-100 text-gray-700"
          @click="showMenu = false"
        >
          📜 Historial
        </router-link>
        <router-link
          to="/earnings"
          class="block px-4 py-2 hover:bg-gray-100 text-gray-700"
          @click="showMenu = false"
        >
          💰 Ganancias
        </router-link>
        <hr class="my-2" />
        <button
          @click="handleLogout"
          class="w-full text-left px-4 py-2 hover:bg-gray-100 text-red-600"
        >
          🚪 Cerrar Sesión
        </button>
      </div>
    </header>

    <!-- Contenido principal -->
    <main class="max-w-7xl mx-auto px-4 py-6">
      <!-- Estado de disponibilidad banner -->
      <div
        v-if="driverStore.isAvailable"
        class="mb-6 bg-gradient-to-r from-green-500 to-green-600 text-white rounded-lg p-6 shadow-lg"
      >
        <div class="flex items-center justify-between">
          <div>
            <h2 class="text-2xl font-bold mb-1">Estás Disponible</h2>
            <p class="text-green-100">Esperando solicitudes de viaje...</p>
          </div>
          <div class="text-5xl animate-pulse">📡</div>
        </div>
      </div>

      <div
        v-else-if="driverStore.isOffline"
        class="mb-6 bg-gradient-to-r from-gray-500 to-gray-600 text-white rounded-lg p-6 shadow-lg"
      >
        <div class="flex items-center justify-between">
          <div>
            <h2 class="text-2xl font-bold mb-1">Estás Desconectado</h2>
            <p class="text-gray-100">Actívate para recibir viajes</p>
          </div>
          <div class="text-5xl">😴</div>
        </div>
      </div>

      <!-- Estadísticas del día -->
      <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <!-- Viajes completados hoy -->
        <div class="bg-white rounded-lg p-6 shadow">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm text-gray-500 mb-1">Viajes Hoy</p>
              <p class="text-3xl font-bold text-gray-900">{{ driverStore.stats.completed_today }}</p>
            </div>
            <div class="text-4xl">🚗</div>
          </div>
        </div>

        <!-- Ganancias del día -->
        <div class="bg-white rounded-lg p-6 shadow">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm text-gray-500 mb-1">Ganancias Hoy</p>
              <p class="text-3xl font-bold text-green-600">${{ driverStore.stats.earnings_today.toFixed(2) }}</p>
            </div>
            <div class="text-4xl">💰</div>
          </div>
        </div>

        <!-- Rating -->
        <div class="bg-white rounded-lg p-6 shadow">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm text-gray-500 mb-1">Calificación</p>
              <p class="text-3xl font-bold text-yellow-500">{{ driverStore.stats.rating.toFixed(1) }} ⭐</p>
            </div>
            <div class="text-4xl">🌟</div>
          </div>
        </div>

        <!-- Tasa de aceptación -->
        <div class="bg-white rounded-lg p-6 shadow">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm text-gray-500 mb-1">Aceptación</p>
              <p class="text-3xl font-bold text-blue-600">{{ (driverStore.stats.acceptance_rate * 100).toFixed(0) }}%</p>
            </div>
            <div class="text-4xl">✓</div>
          </div>
        </div>
      </div>

      <!-- Banner GPS -->
      <div v-if="driverStore.isAvailable && driverStore.gpsStatus === 'denied'" class="mb-6 p-4 bg-red-50 border border-red-300 rounded-lg">
        <p class="font-semibold text-red-700 mb-2">&#128205; GPS bloqueado en Chrome</p>
        <p class="text-sm text-red-600 mb-2">En la barra de Chrome escribe esta direccion y presiona Enter:</p>
        <div class="bg-white border border-red-200 rounded p-2 mb-3 font-mono text-xs text-red-800 break-all select-all">chrome://settings/content/siteDetails?site=https://taxi.nexoai.lat</div>
        <p class="text-sm text-red-600 mb-3">Cambia <strong>Ubicacion</strong> a <strong>Permitir</strong>, luego vuelve aqui y recarga.</p>
        <button @click="reloadPage()" class="px-4 py-2 bg-red-600 text-white text-sm font-semibold rounded-lg">Recargar pagina</button>
      </div>
      <div v-else-if="driverStore.isAvailable && driverStore.gpsStatus !== 'granted'" class="mb-4 p-3 bg-yellow-50 border border-yellow-300 rounded-lg flex items-center justify-between">
        <p class="text-sm text-yellow-800">&#128205; Activa tu ubicacion para recibir viajes.</p>
        <button @click="driverStore.requestGPSPermission()" class="ml-3 px-3 py-1 bg-yellow-500 text-white text-sm font-semibold rounded-lg whitespace-nowrap">Permitir GPS</button>
      </div>

      <!-- Solicitudes de viaje pendientes -->
      <div v-if="rideStore.hasPendingRequests" class="mb-6">
        <h3 class="text-lg font-semibold text-gray-900 mb-4">Solicitudes de Viaje</h3>
        <div class="space-y-4">
          <div
            v-for="ride in rideStore.pendingRequests"
            :key="ride.ride_id"
            class="bg-white rounded-lg shadow-lg border-2 border-taxi-yellow p-6 animate-pulse-slow"
          >
            <div class="flex items-start justify-between mb-4">
              <div class="flex-1">
                <div class="flex items-center space-x-2 mb-2">
                  <span class="px-3 py-1 bg-yellow-100 text-yellow-800 rounded-full text-sm font-medium">
                    Nueva Solicitud
                  </span>
                  <span class="text-sm text-gray-500">Expira en {{ ride.expires_in }}s</span>
                </div>

                <h4 class="text-lg font-semibold text-gray-900 mb-3">{{ ride.customer.name }}</h4>

                <!-- Ruta -->
                <div class="space-y-2 mb-4">
                  <div class="flex items-start">
                    <span class="text-green-500 mr-2">📍</span>
                    <div class="flex-1">
                      <p class="text-sm text-gray-500">Origen</p>
                      <p class="text-gray-900">{{ ride.origin.address }}</p>
                    </div>
                  </div>
                  <div class="flex items-start">
                    <span class="text-red-500 mr-2">📍</span>
                    <div class="flex-1">
                      <p class="text-sm text-gray-500">Destino</p>
                      <p class="text-gray-900">{{ ride.destination.address }}</p>
                    </div>
                  </div>
                </div>

                <!-- Detalles del viaje -->
                <div class="flex items-center space-x-4 text-sm text-gray-600">
                  <span>🛣️ {{ ride.distance_km }} km</span>
                  <span>⏱️ ~{{ ride.duration_minutes }} min</span>
                  <span class="text-green-600 font-semibold">💰 ${{ ride.total_fare }}</span>
                </div>
              </div>
            </div>

            <!-- Botones de acción -->
            <div class="flex space-x-3">
              <button
                @click="acceptRide(ride.ride_id)"
                class="flex-1 bg-taxi-green hover:bg-green-600 text-white font-semibold py-3 rounded-lg transition duration-200"
              >
                ✓ Aceptar Viaje
              </button>
              <button
                @click="rejectRide(ride.ride_id)"
                class="flex-1 bg-gray-200 hover:bg-gray-300 text-gray-700 font-semibold py-3 rounded-lg transition duration-200"
              >
                ✕ Rechazar
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Viaje activo -->
      <div v-if="rideStore.hasActiveRide" class="mb-6">
        <div class="bg-gradient-to-r from-blue-500 to-blue-600 text-white rounded-lg p-6 shadow-lg">
          <h3 class="text-xl font-bold mb-4">Viaje en Curso</h3>
          <div class="flex items-center justify-between">
            <div>
              <p class="mb-2">{{ rideStore.activeRide.customer.name }}</p>
              <p class="text-sm text-blue-100">{{ rideStore.activeRide.destination.address }}</p>
            </div>
            <router-link
              :to="`/active-ride/${rideStore.activeRide.ride_id}`"
              class="bg-white text-blue-600 px-6 py-2 rounded-lg font-semibold hover:bg-blue-50 transition"
            >
              Ver Detalles →
            </router-link>
          </div>
        </div>
      </div>

      <!-- Sin actividad -->
      <div
        v-if="!rideStore.hasPendingRequests && !rideStore.hasActiveRide && driverStore.isAvailable"
        class="bg-white rounded-lg p-12 text-center shadow"
      >
        <div class="text-6xl mb-4">🔍</div>
        <h3 class="text-xl font-semibold text-gray-900 mb-2">Sin solicitudes por el momento</h3>
        <p class="text-gray-500">Te notificaremos cuando haya un nuevo viaje cerca de ti</p>
      </div>

      <!-- ── Viajes Programados ──────────────────────────────────────────────── -->
      <div v-if="rideStore.myScheduledRides.length || rideStore.poolScheduledRides.length" class="mt-6">
        <div class="flex items-center justify-between mb-3">
          <h3 class="text-lg font-semibold text-gray-900">
            📅 Viajes Programados
            <span
              v-if="rideStore.myScheduledRides.length"
              class="ml-2 bg-yellow-400 text-white text-xs font-bold px-2 py-0.5 rounded-full"
            >{{ rideStore.myScheduledRides.length }}</span>
          </h3>
          <router-link to="/agenda" class="text-sm font-semibold text-yellow-600 hover:underline">
            Ver agenda →
          </router-link>
        </div>

        <!-- Mis reservas (máx 2) -->
        <div v-if="rideStore.myScheduledRides.length" class="space-y-3 mb-3">
          <div
            v-for="ride in rideStore.myScheduledRides.slice(0, 2)"
            :key="ride.ride_id"
            class="bg-white rounded-lg shadow p-4 border-l-4 border-yellow-400"
          >
            <div class="flex items-center justify-between mb-2">
              <span class="text-xs font-bold text-yellow-700 bg-yellow-50 px-2 py-0.5 rounded-full">📌 Mi reserva</span>
              <span class="font-bold text-green-600">${{ ride.total_fare }}</span>
            </div>
            <p class="text-sm font-bold text-gray-800 mb-1">{{ formatScheduledDate(ride.scheduled_at) }}</p>
            <p class="text-xs text-gray-500 truncate">📍 {{ ride.origin?.address }}</p>
            <p class="text-xs text-gray-500 truncate">🏁 {{ ride.destination?.address }}</p>
          </div>
          <p v-if="rideStore.myScheduledRides.length > 2" class="text-xs text-center text-gray-400">
            +{{ rideStore.myScheduledRides.length - 2 }} más en la agenda
          </p>
        </div>

        <!-- Pool disponible (máx 2, solo si no tengo reservas propias para no saturar) -->
        <div v-if="!rideStore.myScheduledRides.length && rideStore.poolScheduledRides.length" class="space-y-3">
          <div
            v-for="ride in rideStore.poolScheduledRides.slice(0, 2)"
            :key="ride.ride_id"
            class="bg-white rounded-lg shadow p-4 border-l-4 border-blue-300"
          >
            <div class="flex items-center justify-between mb-2">
              <span class="text-xs font-bold text-blue-600 bg-blue-50 px-2 py-0.5 rounded-full">🔍 Disponible</span>
              <span class="font-bold text-green-600">${{ ride.total_fare }}</span>
            </div>
            <p class="text-sm font-bold text-gray-800 mb-1">{{ formatScheduledDate(ride.scheduled_at) }}</p>
            <p class="text-xs text-gray-500 truncate">📍 {{ ride.origin?.address }}</p>
            <p class="text-xs text-gray-500 truncate">🏁 {{ ride.destination?.address }}</p>
          </div>
          <p v-if="rideStore.poolScheduledRides.length > 2" class="text-xs text-center text-gray-400">
            +{{ rideStore.poolScheduledRides.length - 2 }} más disponibles
          </p>
        </div>

        <!-- Si tengo reservas Y hay pool: mostrar contador del pool -->
        <div v-if="rideStore.myScheduledRides.length && rideStore.poolScheduledRides.length" class="mt-1">
          <router-link to="/agenda" class="block text-center text-xs text-blue-600 hover:underline">
            {{ rideStore.poolScheduledRides.length }} viaje{{ rideStore.poolScheduledRides.length > 1 ? 's' : '' }} disponibles para reservar →
          </router-link>
        </div>
      </div>

      <!-- Resumen semanal -->
      <div class="mt-6 bg-white rounded-lg p-6 shadow">
        <h3 class="text-lg font-semibold text-gray-900 mb-4">Resumen de la Semana</h3>
        <div class="grid grid-cols-2 gap-4">
          <div>
            <p class="text-sm text-gray-500">Total de Viajes</p>
            <p class="text-2xl font-bold text-gray-900">{{ driverStore.stats.total_rides }}</p>
          </div>
          <div>
            <p class="text-sm text-gray-500">Ganancias</p>
            <p class="text-2xl font-bold text-green-600">${{ driverStore.stats.earnings_week.toFixed(2) }}</p>
          </div>
        </div>
        <router-link
          to="/earnings"
          class="mt-4 block text-center text-taxi-yellow hover:underline"
        >
          Ver detalles completos →
        </router-link>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/authStore'
import { useDriverStore } from '../stores/driverStore'
import { useRideStore } from '../stores/rideStore'

const router = useRouter()
const authStore = useAuthStore()
const driverStore = useDriverStore()
const rideStore = useRideStore()

const showMenu = ref(false)

const driverName = computed(() => authStore.driver?.name || 'Conductor')
const currentDate = computed(() => {
  const options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' }
  return new Date().toLocaleDateString('es-ES', options)
})

const formatScheduledDate = (iso) => {
  if (!iso) return ''
  return new Date(iso).toLocaleString('es-MX', { dateStyle: 'medium', timeStyle: 'short' })
}

const setStatus = async (status) => {
  const result = await driverStore.updateStatus(status)
  if (result.success && status === 'available') {
    if ('Notification' in window && Notification.permission === 'default') {
      Notification.requestPermission()
    }
    rideStore.startPolling()
    driverStore.startLocationTracking()
    // Forzar dialogo de permiso GPS inmediatamente
    driverStore.requestGPSPermission()
  } else if (result.success && status === 'offline') {
    rideStore.stopPolling()
    driverStore.stopLocationTracking()
  }
}

const acceptRide = async (rideId) => {
  const result = await rideStore.acceptRide(rideId)
  if (result.success) {
    router.push(`/active-ride/${rideId}`)
  }
}

const rejectRide = async (rideId) => {
  if (confirm('¿Estás seguro de rechazar este viaje?')) {
    await rideStore.rejectRide(rideId, 'No disponible')
  }
}

const handleLogout = async () => {
  if (confirm('¿Estás seguro de cerrar sesión?')) {
    rideStore.stopPolling()
    driverStore.stopPolling()
    driverStore.stopLocationTracking()
    await authStore.logout()
    router.push('/login')
  }
}

onMounted(() => {
  if (authStore.driver?.is_online && !driverStore.isAvailable) {
    driverStore.status = 'available'
  }
  if (driverStore.isAvailable) {
    rideStore.startPolling()
    driverStore.startPolling()
    driverStore.startLocationTracking()
    // Solicitar permiso GPS al arrancar
    driverStore.requestGPSPermission()
  }
  rideStore.fetchScheduledRides()
})

const reloadPage = () => { window.location.reload() }

onUnmounted(() => {
  rideStore.stopPolling()
  driverStore.stopLocationTracking()
})
</script>

<style scoped>
@keyframes pulse-slow {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.95;
  }
}

.animate-pulse-slow {
  animation: pulse-slow 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}
</style>
