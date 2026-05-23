<template>
  <div class="min-h-screen bg-gray-50">
    <!-- Header -->
    <header class="bg-white shadow-sm sticky top-0 z-10">
      <div class="max-w-7xl mx-auto px-4 py-4">
        <div class="flex items-center space-x-4">
          <button
            @click="goBack"
            class="p-2 hover:bg-gray-100 rounded-lg"
          >
            <span class="text-2xl">←</span>
          </button>
          <div class="flex-1">
            <h1 class="text-xl font-bold text-gray-900">Historial de Viajes</h1>
            <p class="text-sm text-gray-500">Todos tus viajes completados</p>
          </div>
        </div>
      </div>
    </header>

    <!-- Contenido -->
    <main class="max-w-7xl mx-auto px-4 py-6">
      <!-- Filtros -->
      <div class="bg-white rounded-lg shadow mb-6 p-4">
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Periodo</label>
            <select
              v-model="filters.period"
              @change="loadHistory"
              class="w-full border border-gray-300 rounded-lg px-3 py-2"
            >
              <option value="today">Hoy</option>
              <option value="week">Esta semana</option>
              <option value="month">Este mes</option>
              <option value="all">Todo</option>
            </select>
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Estado</label>
            <select
              v-model="filters.status"
              @change="applyFilters"
              class="w-full border border-gray-300 rounded-lg px-3 py-2"
            >
              <option value="all">Todos</option>
              <option value="completed">Completados</option>
              <option value="cancelled">Cancelados</option>
            </select>
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Buscar</label>
            <input
              v-model="filters.search"
              type="text"
              placeholder="Cliente, origen, destino..."
              @input="applyFilters"
              class="w-full border border-gray-300 rounded-lg px-3 py-2"
            />
          </div>
        </div>
      </div>

      <!-- Resumen -->
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div class="bg-white rounded-lg p-6 shadow">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm text-gray-500 mb-1">Total Viajes</p>
              <p class="text-3xl font-bold text-gray-900">{{ summary.total_rides }}</p>
            </div>
            <div class="text-4xl">🚗</div>
          </div>
        </div>

        <div class="bg-white rounded-lg p-6 shadow">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm text-gray-500 mb-1">Total Ganado</p>
              <p class="text-3xl font-bold text-green-600">${{ summary.total_earnings.toFixed(2) }}</p>
            </div>
            <div class="text-4xl">💰</div>
          </div>
        </div>

        <div class="bg-white rounded-lg p-6 shadow">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm text-gray-500 mb-1">Promedio por Viaje</p>
              <p class="text-3xl font-bold text-blue-600">${{ summary.average_fare.toFixed(2) }}</p>
            </div>
            <div class="text-4xl">📊</div>
          </div>
        </div>
      </div>

      <!-- Loading -->
      <div v-if="loading" class="flex items-center justify-center h-64">
        <div class="text-center">
          <div class="text-6xl mb-4">⏳</div>
          <p class="text-gray-500">Cargando historial...</p>
        </div>
      </div>

      <!-- Error -->
      <div v-else-if="error" class="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
        <div class="text-6xl mb-4">❌</div>
        <p class="text-red-600">{{ error }}</p>
      </div>

      <!-- Lista de viajes -->
      <div v-else-if="filteredRides.length > 0" class="space-y-4">
        <div
          v-for="ride in filteredRides"
          :key="ride.ride_id"
          class="bg-white rounded-lg shadow hover:shadow-md transition-shadow p-6"
        >
          <!-- Header del viaje -->
          <div class="flex items-start justify-between mb-4">
            <div class="flex-1">
              <div class="flex items-center space-x-2 mb-2">
                <span
                  :class="[
                    'px-3 py-1 rounded-full text-sm font-medium',
                    ride.status === 'completed'
                      ? 'bg-green-100 text-green-800'
                      : 'bg-red-100 text-red-800'
                  ]"
                >
                  {{ ride.status === 'completed' ? '✓ Completado' : '✕ Cancelado' }}
                </span>
                <span class="text-sm text-gray-500">
                  {{ formatDate(ride.created_at) }}
                </span>
              </div>

              <h4 class="text-lg font-semibold text-gray-900 mb-1">{{ ride.customer.name }}</h4>
              <p class="text-sm text-gray-500">ID: {{ ride.ride_id }}</p>
            </div>

            <div class="text-right">
              <p class="text-2xl font-bold text-green-600">${{ ride.total_fare }}</p>
              <p class="text-sm text-gray-500">{{ ride.payment_method === 'cash' ? '💵 Efectivo' : '💳 Tarjeta' }}</p>
            </div>
          </div>

          <!-- Ruta -->
          <div class="space-y-2 mb-4 pb-4 border-b">
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

          <!-- Detalles -->
          <div class="flex items-center justify-between text-sm">
            <div class="flex items-center space-x-4 text-gray-600">
              <span>🛣️ {{ ride.distance_km }} km</span>
              <span>⏱️ {{ ride.duration_minutes }} min</span>
              <span v-if="ride.rating" class="text-yellow-500">⭐ {{ ride.rating }}</span>
            </div>

            <button
              @click="viewRideDetails(ride)"
              class="text-blue-600 hover:underline"
            >
              Ver detalles →
            </button>
          </div>
        </div>
      </div>

      <!-- Sin resultados -->
      <div v-else class="bg-white rounded-lg p-12 text-center shadow">
        <div class="text-6xl mb-4">📭</div>
        <h3 class="text-xl font-semibold text-gray-900 mb-2">No hay viajes</h3>
        <p class="text-gray-500">No se encontraron viajes con los filtros seleccionados</p>
      </div>
    </main>

    <!-- Modal de detalles -->
    <div
      v-if="selectedRide"
      class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
      @click.self="selectedRide = null"
    >
      <div class="bg-white rounded-lg shadow-2xl max-w-2xl w-full p-6 max-h-screen overflow-y-auto">
        <div class="flex items-center justify-between mb-6">
          <h3 class="text-2xl font-bold text-gray-900">Detalles del Viaje</h3>
          <button
            @click="selectedRide = null"
            class="text-gray-500 hover:text-gray-700 text-2xl"
          >
            ✕
          </button>
        </div>

        <!-- Detalles completos -->
        <div class="space-y-4">
          <div class="border-b pb-4">
            <p class="text-sm text-gray-500">ID del Viaje</p>
            <p class="text-lg font-mono">{{ selectedRide.ride_id }}</p>
          </div>

          <div class="border-b pb-4">
            <p class="text-sm text-gray-500">Cliente</p>
            <p class="text-lg font-semibold">{{ selectedRide.customer.name }}</p>
            <p class="text-sm text-gray-600">{{ selectedRide.customer.phone }}</p>
          </div>

          <div class="border-b pb-4">
            <p class="text-sm text-gray-500 mb-2">Ruta</p>
            <div class="space-y-2">
              <div class="flex items-start">
                <span class="text-green-500 mr-2">📍</span>
                <div>
                  <p class="text-sm text-gray-500">Origen</p>
                  <p class="text-gray-900">{{ selectedRide.origin.address }}</p>
                </div>
              </div>
              <div class="flex items-start">
                <span class="text-red-500 mr-2">📍</span>
                <div>
                  <p class="text-sm text-gray-500">Destino</p>
                  <p class="text-gray-900">{{ selectedRide.destination.address }}</p>
                </div>
              </div>
            </div>
          </div>

          <div class="grid grid-cols-2 gap-4 border-b pb-4">
            <div>
              <p class="text-sm text-gray-500">Distancia</p>
              <p class="text-xl font-semibold">{{ selectedRide.distance_km }} km</p>
            </div>
            <div>
              <p class="text-sm text-gray-500">Duración</p>
              <p class="text-xl font-semibold">{{ selectedRide.duration_minutes }} min</p>
            </div>
          </div>

          <div class="border-b pb-4">
            <p class="text-sm text-gray-500 mb-2">Pago</p>
            <div class="flex items-center justify-between">
              <p class="text-lg">
                {{ selectedRide.payment_method === 'cash' ? '💵 Efectivo' : '💳 Tarjeta' }}
              </p>
              <p class="text-3xl font-bold text-green-600">${{ selectedRide.total_fare }}</p>
            </div>
          </div>

          <div v-if="selectedRide.rating">
            <p class="text-sm text-gray-500">Calificación del cliente</p>
            <p class="text-2xl">⭐ {{ selectedRide.rating }} / 5</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useRideStore } from '../stores/rideStore'

const router = useRouter()
const rideStore = useRideStore()

const loading = ref(true)
const error = ref(null)
const selectedRide = ref(null)

const filters = ref({
  period: 'week',
  status: 'all',
  search: ''
})

const rides = computed(() => rideStore.rideHistory || [])

const filteredRides = computed(() => {
  let result = rides.value

  // Filtrar por estado
  if (filters.value.status !== 'all') {
    result = result.filter(r => r.status === filters.value.status)
  }

  // Filtrar por búsqueda
  if (filters.value.search) {
    const search = filters.value.search.toLowerCase()
    result = result.filter(r =>
      r.customer.name.toLowerCase().includes(search) ||
      r.origin.address.toLowerCase().includes(search) ||
      r.destination.address.toLowerCase().includes(search)
    )
  }

  return result
})

const summary = computed(() => {
  const total = filteredRides.value.length
  const earnings = filteredRides.value.reduce((sum, r) => sum + (r.total_fare || 0), 0)

  return {
    total_rides: total,
    total_earnings: earnings,
    average_fare: total > 0 ? earnings / total : 0
  }
})

const loadHistory = async () => {
  loading.value = true
  error.value = null

  try {
    const result = await rideStore.fetchHistory({ period: filters.value.period })
    if (!result.success) {
      error.value = result.error
    }
  } catch (err) {
    error.value = 'Error al cargar historial'
  } finally {
    loading.value = false
  }
}

const applyFilters = () => {
  // Los filtros se aplican automáticamente via computed
}

const viewRideDetails = (ride) => {
  selectedRide.value = ride
}

const formatDate = (dateString) => {
  const date = new Date(dateString)
  const options = {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  }
  return date.toLocaleDateString('es-ES', options)
}

const goBack = () => {
  router.push('/dashboard')
}

onMounted(() => {
  loadHistory()
})
</script>
