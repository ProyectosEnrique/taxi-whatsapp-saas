<template>
  <div class="rides-monitor">
    <!-- Header -->
    <div class="page-header">
      <div>
        <h1 class="text-3xl font-bold text-gray-900">Monitor de Viajes</h1>
        <p class="text-gray-600 mt-1">Seguimiento en tiempo real de todos los viajes</p>
      </div>

      <div class="flex items-center space-x-4">
        <div class="flex items-center space-x-2">
          <div class="h-3 w-3 rounded-full bg-green-500 animate-pulse"></div>
          <span class="text-sm text-gray-600">En vivo</span>
        </div>

        <button @click="refreshRides" class="btn btn-secondary">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
        </button>
      </div>
    </div>

    <!-- Stats Overview -->
    <div class="grid grid-cols-1 md:grid-cols-5 gap-4 mb-8">
      <div class="stat-card border-l-4 border-blue-500">
        <p class="stat-label">Solicitados</p>
        <p class="stat-value text-blue-600">{{ stats.requested }}</p>
      </div>

      <div class="stat-card border-l-4 border-yellow-500">
        <p class="stat-label">Asignados</p>
        <p class="stat-value text-yellow-600">{{ stats.assigned }}</p>
      </div>

      <div class="stat-card border-l-4 border-purple-500">
        <p class="stat-label">En Camino</p>
        <p class="stat-value text-purple-600">{{ stats.driver_arriving }}</p>
      </div>

      <div class="stat-card border-l-4 border-green-500">
        <p class="stat-label">En Progreso</p>
        <p class="stat-value text-green-600">{{ stats.in_progress }}</p>
      </div>

      <div class="stat-card border-l-4 border-gray-500">
        <p class="stat-label">Hoy</p>
        <p class="stat-value text-gray-900">{{ stats.completed_today }}</p>
      </div>
    </div>

    <!-- Filters -->
    <div class="bg-white rounded-lg shadow p-4 mb-6">
      <div class="flex items-center space-x-4">
        <div class="flex-1">
          <input
            v-model="filters.search"
            type="text"
            placeholder="Buscar por cliente, conductor, ID..."
            class="input"
          />
        </div>

        <select v-model="filters.status" class="input w-48">
          <option value="">Todos los estados</option>
          <option value="requested">Solicitado</option>
          <option value="assigned">Asignado</option>
          <option value="driver_arriving">Conductor en camino</option>
          <option value="started">Iniciado</option>
          <option value="in_progress">En progreso</option>
          <option value="completed">Completado</option>
          <option value="cancelled">Cancelado</option>
        </select>

        <select v-model="filters.timeRange" class="input w-48">
          <option value="today">Hoy</option>
          <option value="week">Esta semana</option>
          <option value="month">Este mes</option>
        </select>
      </div>
    </div>

    <!-- Rides Timeline -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <!-- Active Rides -->
      <div class="bg-white rounded-lg shadow">
        <div class="p-6 border-b border-gray-200">
          <h2 class="text-lg font-semibold text-gray-900">Viajes Activos</h2>
          <p class="text-sm text-gray-500">{{ activeRides.length }} viajes en curso</p>
        </div>

        <div class="divide-y divide-gray-200 max-h-[600px] overflow-y-auto">
          <div
            v-for="ride in activeRides"
            :key="ride.ride_id"
            class="p-4 hover:bg-gray-50 cursor-pointer"
            @click="viewRideDetails(ride)"
          >
            <!-- Status Badge -->
            <div class="flex items-center justify-between mb-3">
              <span :class="getStatusClass(ride.status)" class="px-3 py-1 text-xs font-semibold rounded-full">
                {{ getStatusLabel(ride.status) }}
              </span>
              <span class="text-xs text-gray-500">{{ formatTime(ride.requested_at) }}</span>
            </div>

            <!-- Driver & Customer -->
            <div class="grid grid-cols-2 gap-4 mb-3">
              <div>
                <p class="text-xs text-gray-500 mb-1">Conductor</p>
                <p class="text-sm font-medium text-gray-900">{{ ride.driver?.name || 'Asignando...' }}</p>
                <p class="text-xs text-gray-500">{{ ride.driver?.vehicle || '' }}</p>
              </div>

              <div>
                <p class="text-xs text-gray-500 mb-1">Cliente</p>
                <p class="text-sm font-medium text-gray-900">{{ ride.customer.name }}</p>
                <p class="text-xs text-gray-500">{{ ride.customer.phone }}</p>
              </div>
            </div>

            <!-- Route -->
            <div class="space-y-2">
              <div class="flex items-start">
                <div class="flex-shrink-0 mt-1">
                  <div class="h-3 w-3 rounded-full bg-green-500"></div>
                </div>
                <div class="ml-3 flex-1">
                  <p class="text-xs text-gray-500">Origen</p>
                  <p class="text-sm text-gray-900">{{ ride.origin.address }}</p>
                </div>
              </div>

              <div class="ml-1 border-l-2 border-gray-300 h-4"></div>

              <div class="flex items-start">
                <div class="flex-shrink-0 mt-1">
                  <div class="h-3 w-3 rounded-full bg-red-500"></div>
                </div>
                <div class="ml-3 flex-1">
                  <p class="text-xs text-gray-500">Destino</p>
                  <p class="text-sm text-gray-900">{{ ride.destination.address }}</p>
                </div>
              </div>
            </div>

            <!-- Details -->
            <div class="mt-3 pt-3 border-t border-gray-200 flex items-center justify-between">
              <div class="flex items-center space-x-4 text-xs text-gray-500">
                <span>🛣️ {{ ride.distance_km }} km</span>
                <span>⏱️ {{ ride.duration_minutes }} min</span>
                <span class="font-semibold text-gray-900">${{ ride.total_fare }}</span>
              </div>

              <button @click.stop="trackRide(ride)" class="text-blue-600 hover:text-blue-800">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
              </button>
            </div>
          </div>

          <!-- Empty State -->
          <div v-if="activeRides.length === 0" class="p-8 text-center">
            <svg class="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <h3 class="mt-2 text-sm font-medium text-gray-900">No hay viajes activos</h3>
            <p class="mt-1 text-sm text-gray-500">Los viajes aparecerán aquí cuando sean solicitados.</p>
          </div>
        </div>
      </div>

      <!-- Recent Completed Rides -->
      <div class="bg-white rounded-lg shadow">
        <div class="p-6 border-b border-gray-200">
          <h2 class="text-lg font-semibold text-gray-900">Viajes Completados Recientes</h2>
          <p class="text-sm text-gray-500">Últimos {{ completedRides.length }} viajes</p>
        </div>

        <div class="divide-y divide-gray-200 max-h-[600px] overflow-y-auto">
          <div
            v-for="ride in completedRides"
            :key="ride.ride_id"
            class="p-4 hover:bg-gray-50 cursor-pointer"
            @click="viewRideDetails(ride)"
          >
            <!-- Header -->
            <div class="flex items-center justify-between mb-2">
              <span class="text-xs text-gray-500">{{ formatTime(ride.completed_at) }}</span>
              <span class="text-sm font-semibold text-green-600">${{ ride.total_fare }}</span>
            </div>

            <!-- Info -->
            <div class="flex items-center justify-between text-sm">
              <div class="flex-1">
                <p class="text-gray-900 font-medium">{{ ride.driver.name }}</p>
                <p class="text-gray-500">→ {{ ride.customer.name }}</p>
              </div>

              <div class="text-right">
                <div class="flex items-center">
                  <svg class="w-4 h-4 text-yellow-400 fill-current" viewBox="0 0 20 20">
                    <path d="M10 15l-5.878 3.09 1.123-6.545L.489 6.91l6.572-.955L10 0l2.939 5.955 6.572.955-4.756 4.635 1.123 6.545z"/>
                  </svg>
                  <span class="ml-1 text-xs">{{ ride.customer_rating || '-' }}</span>
                </div>
                <p class="text-xs text-gray-500">{{ ride.distance_km }} km</p>
              </div>
            </div>
          </div>

          <!-- Empty State -->
          <div v-if="completedRides.length === 0" class="p-8 text-center">
            <svg class="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
            </svg>
            <h3 class="mt-2 text-sm font-medium text-gray-900">No hay viajes completados</h3>
            <p class="mt-1 text-sm text-gray-500">Los viajes completados aparecerán aquí.</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'

// State
const rides = ref([])
const stats = ref({
  requested: 0,
  assigned: 0,
  driver_arriving: 0,
  in_progress: 0,
  completed_today: 0
})

const filters = ref({
  search: '',
  status: '',
  timeRange: 'today'
})

let refreshInterval = null

// Computed
const activeRides = computed(() => {
  return rides.value.filter(ride =>
    ['requested', 'assigned', 'driver_arriving', 'started', 'in_progress'].includes(ride.status)
  )
})

const completedRides = computed(() => {
  return rides.value
    .filter(ride => ride.status === 'completed')
    .sort((a, b) => new Date(b.completed_at) - new Date(a.completed_at))
    .slice(0, 10)
})

// Methods
function getStatusClass(status) {
  const classes = {
    requested: 'bg-blue-100 text-blue-800',
    assigned: 'bg-yellow-100 text-yellow-800',
    driver_arriving: 'bg-purple-100 text-purple-800',
    started: 'bg-indigo-100 text-indigo-800',
    in_progress: 'bg-green-100 text-green-800',
    completed: 'bg-gray-100 text-gray-800',
    cancelled: 'bg-red-100 text-red-800'
  }
  return classes[status] || 'bg-gray-100 text-gray-800'
}

function getStatusLabel(status) {
  const labels = {
    requested: 'Solicitado',
    assigned: 'Asignado',
    driver_arriving: 'Conductor en camino',
    started: 'Iniciado',
    in_progress: 'En progreso',
    completed: 'Completado',
    cancelled: 'Cancelado'
  }
  return labels[status] || status
}

function formatTime(timestamp) {
  if (!timestamp) return '-'
  const date = new Date(timestamp)
  const now = new Date()
  const diff = now - date

  // Menos de 1 minuto
  if (diff < 60000) return 'Hace un momento'

  // Menos de 1 hora
  if (diff < 3600000) {
    const minutes = Math.floor(diff / 60000)
    return `Hace ${minutes} min`
  }

  // Menos de 24 horas
  if (diff < 86400000) {
    const hours = Math.floor(diff / 3600000)
    return `Hace ${hours}h`
  }

  // Formato de hora
  return date.toLocaleTimeString('es-MX', { hour: '2-digit', minute: '2-digit' })
}

function viewRideDetails(ride) {
  console.log('View ride:', ride)
  // TODO: Abrir modal con detalles completos
}

function trackRide(ride) {
  console.log('Track ride:', ride)
  // TODO: Abrir mapa con tracking en tiempo real
}

async function refreshRides() {
  // TODO: Llamar API real
  // Por ahora, datos de ejemplo
  rides.value = [
    {
      ride_id: 'ride_001',
      status: 'in_progress',
      requested_at: new Date(Date.now() - 600000).toISOString(),
      driver: {
        name: 'Juan Pérez',
        vehicle: 'Nissan Versa ABC-1234'
      },
      customer: {
        name: 'Laura Sánchez',
        phone: '+5215533333001'
      },
      origin: {
        address: 'Av. Insurgentes Sur 1234'
      },
      destination: {
        address: 'Av. Reforma 456'
      },
      distance_km: 8.5,
      duration_minutes: 22,
      total_fare: 165.00
    }
  ]

  // Actualizar estadísticas
  stats.value = {
    requested: rides.value.filter(r => r.status === 'requested').length,
    assigned: rides.value.filter(r => r.status === 'assigned').length,
    driver_arriving: rides.value.filter(r => r.status === 'driver_arriving').length,
    in_progress: rides.value.filter(r => r.status === 'in_progress').length,
    completed_today: 45 // TODO: Calcular real
  }
}

// Lifecycle
onMounted(() => {
  refreshRides()

  // Auto-refresh cada 5 segundos
  refreshInterval = setInterval(refreshRides, 5000)
})

onUnmounted(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
})
</script>

<style scoped>
.page-header {
  @apply flex justify-between items-start mb-8;
}

.stat-card {
  @apply bg-white rounded-lg shadow p-4;
}

.stat-label {
  @apply text-xs font-medium text-gray-500 uppercase tracking-wide;
}

.stat-value {
  @apply text-3xl font-bold mt-2;
}

.input {
  @apply px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent;
}

.btn {
  @apply px-4 py-2 rounded-lg font-medium transition-colors;
}

.btn-secondary {
  @apply bg-gray-100 text-gray-700 hover:bg-gray-200;
}
</style>
