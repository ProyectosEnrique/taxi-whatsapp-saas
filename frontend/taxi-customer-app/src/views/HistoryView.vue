<template>
  <div class="min-h-screen bg-gray-50">
    <header class="bg-white shadow-sm sticky top-0 z-10">
      <div class="max-w-7xl mx-auto px-4 py-4">
        <div class="flex items-center space-x-4">
          <button @click="goBack" class="p-2 hover:bg-gray-100 rounded-lg">
            <span class="text-2xl">←</span>
          </button>
          <div class="flex-1">
            <h1 class="text-xl font-bold text-gray-900">Historial de Viajes</h1>
            <p class="text-sm text-gray-500">Todos tus viajes realizados</p>
          </div>
        </div>
      </div>
    </header>

    <main class="max-w-7xl mx-auto px-4 py-6">
      <div v-if="loading" class="flex items-center justify-center h-64">
        <div class="text-center">
          <div class="text-6xl mb-4">⏳</div>
          <p class="text-gray-500">Cargando historial...</p>
        </div>
      </div>

      <div v-else-if="error" class="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
        <div class="text-6xl mb-4">❌</div>
        <p class="text-red-600">{{ error }}</p>
      </div>

      <div v-else-if="rides.length === 0" class="bg-white rounded-lg p-12 text-center shadow">
        <div class="text-6xl mb-4">📭</div>
        <h3 class="text-xl font-semibold text-gray-900 mb-2">No hay viajes</h3>
        <p class="text-gray-500 mb-6">Aún no has realizado ningún viaje</p>
        <button @click="goHome" class="bg-taxi-yellow text-white px-6 py-3 rounded-lg font-semibold">
          Solicitar mi primer viaje
        </button>
      </div>

      <div v-else class="space-y-4">
        <div
          v-for="ride in rides"
          :key="ride.ride_id"
          class="bg-white rounded-lg shadow hover:shadow-md transition-shadow p-6"
        >
          <div class="flex items-start justify-between mb-4">
            <div class="flex-1">
              <div class="flex items-center space-x-2 mb-2">
                <span :class="[
                  'px-3 py-1 rounded-full text-sm font-medium',
                  ride.status === 'completed' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                ]">
                  {{ ride.status === 'completed' ? '✓ Completado' : '✕ Cancelado' }}
                </span>
                <span class="text-sm text-gray-500">{{ formatDate(ride.created_at) }}</span>
              </div>

              <h4 class="text-lg font-semibold text-gray-900 mb-1">{{ ride.driver?.name || 'Conductor' }}</h4>
              <p class="text-sm text-gray-500">ID: {{ ride.ride_id }}</p>
            </div>

            <div class="text-right">
              <p class="text-2xl font-bold text-green-600">${{ ride.total_fare }}</p>
              <p class="text-sm text-gray-500">{{ ride.payment_method === 'cash' ? '💵' : '💳' }}</p>
            </div>
          </div>

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

          <div class="flex items-center justify-between text-sm">
            <div class="flex items-center space-x-4 text-gray-600">
              <span>🛣️ {{ ride.distance_km }} km</span>
              <span>⏱️ {{ ride.duration_minutes }} min</span>
              <span v-if="ride.rating" class="text-yellow-500">⭐ {{ ride.rating }}</span>
            </div>

            <button @click="viewDetails(ride)" class="text-blue-600 hover:underline">
              Ver detalles →
            </button>
          </div>
        </div>
      </div>
    </main>

    <div v-if="selectedRide" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4" @click.self="selectedRide = null">
      <div class="bg-white rounded-lg shadow-2xl max-w-2xl w-full p-6 max-h-screen overflow-y-auto">
        <div class="flex items-center justify-between mb-6">
          <h3 class="text-2xl font-bold text-gray-900">Detalles del Viaje</h3>
          <button @click="selectedRide = null" class="text-gray-500 hover:text-gray-700 text-2xl">✕</button>
        </div>

        <div class="space-y-4">
          <div class="border-b pb-4">
            <p class="text-sm text-gray-500">ID del Viaje</p>
            <p class="text-lg font-mono">{{ selectedRide.ride_id }}</p>
          </div>

          <div class="border-b pb-4">
            <p class="text-sm text-gray-500">Conductor</p>
            <p class="text-lg font-semibold">{{ selectedRide.driver?.name }}</p>
            <p class="text-sm text-gray-600">{{ selectedRide.driver?.phone }}</p>
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
              <p class="text-lg">{{ selectedRide.payment_method === 'cash' ? '💵 Efectivo' : '💳 Tarjeta' }}</p>
              <p class="text-3xl font-bold text-green-600">${{ selectedRide.total_fare }}</p>
            </div>
          </div>

          <div v-if="selectedRide.rating">
            <p class="text-sm text-gray-500">Tu calificación</p>
            <p class="text-2xl">{{ '⭐'.repeat(selectedRide.rating) }}</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useRideStore } from '../stores/rideStore'

const router = useRouter()
const rideStore = useRideStore()

const loading = ref(true)
const error = ref(null)
const selectedRide = ref(null)

const rides = ref([])

const loadHistory = async () => {
  loading.value = true
  error.value = null

  try {
    const result = await rideStore.fetchHistory()
    if (result.success) {
      rides.value = rideStore.rideHistory
    } else {
      error.value = result.error
    }
  } catch (err) {
    error.value = 'Error al cargar historial'
  } finally {
    loading.value = false
  }
}

const formatDate = (dateString) => {
  const date = new Date(dateString)
  const options = { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }
  return date.toLocaleDateString('es-ES', options)
}

const viewDetails = (ride) => {
  selectedRide.value = ride
}

const goBack = () => {
  router.push('/home')
}

const goHome = () => {
  router.push('/home')
}

onMounted(() => {
  loadHistory()
})
</script>
