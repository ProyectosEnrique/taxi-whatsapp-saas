<template>
  <div class="min-h-screen bg-gray-50">
    <header class="bg-white shadow-sm sticky top-0 z-10">
      <div class="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
        <div class="flex items-center space-x-3">
          <button @click="router.push('/home')" class="p-2 hover:bg-gray-100 rounded-lg">
            ← Inicio
          </button>
          <div>
            <h1 class="text-xl font-bold text-gray-900">Viajes Programados</h1>
            <p class="text-sm text-gray-500">{{ rides.length }} reserva{{ rides.length !== 1 ? 's' : '' }} pendiente{{ rides.length !== 1 ? 's' : '' }}</p>
          </div>
        </div>
        <button
          @click="router.push('/schedule')"
          class="bg-yellow-400 hover:bg-yellow-500 text-white px-4 py-2 rounded-lg font-medium text-sm"
        >
          + Nueva
        </button>
      </div>
    </header>

    <main class="max-w-7xl mx-auto px-4 py-6">

      <div v-if="loading" class="flex items-center justify-center h-48">
        <p class="text-gray-500">Cargando...</p>
      </div>

      <div v-else-if="rides.length === 0" class="text-center py-16">
        <div class="text-6xl mb-4">📅</div>
        <h3 class="text-xl font-semibold text-gray-700 mb-2">Sin viajes programados</h3>
        <p class="text-gray-500 mb-6">Reserva con anticipación y evita esperas</p>
        <button
          @click="router.push('/schedule')"
          class="bg-yellow-400 hover:bg-yellow-500 text-white px-6 py-3 rounded-lg font-semibold"
        >
          📅 Programar Viaje
        </button>
      </div>

      <div v-else class="space-y-4">
        <!-- Modal: conductor liberó el viaje -->
      <div
        v-if="releasedRide"
        class="fixed inset-0 bg-black bg-opacity-60 flex items-center justify-center z-50 p-4"
      >
        <div class="bg-white rounded-2xl shadow-2xl max-w-sm w-full p-6">
          <div class="text-center mb-4">
            <div class="text-5xl mb-3">😔</div>
            <h3 class="text-xl font-bold text-gray-900">Tu conductor no puede llevarte</h3>
            <p class="text-gray-600 mt-2 text-sm">
              <span class="font-semibold">{{ releasedRide.preferred_driver_name }}</span>
              tuvo un imprevisto y liberó tu viaje del
              {{ formatDate(releasedRide.scheduled_at) }}.
            </p>
          </div>
          <p class="text-sm text-gray-500 text-center mb-6">¿Qué quieres hacer?</p>
          <div class="space-y-3">
            <button
              @click="handleReassign"
              :disabled="actionLoading"
              class="w-full bg-yellow-400 hover:bg-yellow-500 text-white font-bold py-3 rounded-lg disabled:opacity-50"
            >
              🔍 Buscar otro conductor
            </button>
            <button
              @click="handleCancelReleased"
              :disabled="actionLoading"
              class="w-full bg-gray-100 hover:bg-gray-200 text-gray-700 font-semibold py-3 rounded-lg disabled:opacity-50"
            >
              ✕ Cancelar mi viaje
            </button>
          </div>
        </div>
      </div>

      <div
          v-for="ride in rides"
          :key="ride.ride_id"
          class="bg-white rounded-lg shadow p-5"
        >
          <!-- Fecha y hora -->
          <div class="flex items-center justify-between mb-3">
            <div class="flex items-center space-x-2">
              <span class="text-2xl">🗓️</span>
              <div>
                <p class="font-bold text-gray-900">{{ formatDate(ride.scheduled_at) }}</p>
                <p class="text-sm text-gray-500">{{ timeUntil(ride.scheduled_at) }}</p>
              </div>
            </div>
            <span
              v-if="ride.status === 'driver_released'"
              class="bg-red-100 text-red-700 text-xs font-semibold px-3 py-1 rounded-full animate-pulse"
            >
              ⚠️ Sin conductor
            </span>
            <span v-else class="bg-blue-100 text-blue-700 text-xs font-semibold px-3 py-1 rounded-full">
              {{ ride.driver_name ? '✓ ' + ride.driver_name : 'Sin asignar' }}
            </span>
          </div>

          <!-- Ruta -->
          <div class="space-y-2 mb-4">
            <div class="flex items-start space-x-3">
              <div class="w-6 h-6 bg-green-100 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
                <span class="text-green-600 font-bold text-xs">A</span>
              </div>
              <p class="text-sm text-gray-700 leading-tight">{{ ride.origin.address }}</p>
            </div>
            <div class="ml-3 border-l-2 border-dashed border-gray-200 h-3"></div>
            <div class="flex items-start space-x-3">
              <div class="w-6 h-6 bg-red-100 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
                <span class="text-red-600 font-bold text-xs">B</span>
              </div>
              <p class="text-sm text-gray-700 leading-tight">{{ ride.destination.address }}</p>
            </div>
          </div>

          <!-- Detalles y acciones -->
          <div class="flex items-center justify-between">
            <div class="flex items-center space-x-4 text-sm text-gray-600">
              <span>📏 {{ ride.distance_km }} km</span>
              <span>💵 ${{ ride.total_fare }}</span>
              <span>{{ ride.payment_method === 'cash' ? '💵 Efectivo' : '💳 Tarjeta' }}</span>
            </div>
            <button
              @click="confirmCancel(ride)"
              class="text-red-500 hover:text-red-700 text-sm font-medium"
            >
              Cancelar
            </button>
          </div>
        </div>
      </div>
    </main>

    <!-- Modal de confirmación de cancelación -->
    <div
      v-if="rideToCancel"
      class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
      @click.self="rideToCancel = null"
    >
      <div class="bg-white rounded-lg shadow-2xl max-w-sm w-full p-6">
        <h3 class="text-lg font-bold text-gray-900 mb-2">¿Cancelar reserva?</h3>
        <p class="text-gray-600 text-sm mb-4">
          Viaje del {{ formatDate(rideToCancel.scheduled_at) }} —
          {{ rideToCancel.origin.address }} → {{ rideToCancel.destination.address }}
        </p>
        <div class="flex space-x-3">
          <button
            @click="rideToCancel = null"
            class="flex-1 bg-gray-100 hover:bg-gray-200 text-gray-700 font-semibold py-3 rounded-lg"
          >
            Conservar
          </button>
          <button
            @click="handleCancel"
            :disabled="cancelling"
            class="flex-1 bg-red-500 hover:bg-red-600 text-white font-semibold py-3 rounded-lg disabled:opacity-50"
          >
            {{ cancelling ? 'Cancelando...' : 'Sí, cancelar' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useRideStore } from '../stores/rideStore'
import { useToast } from '../composables/useToast'

const { error: toastError } = useToast()

const router = useRouter()
const rideStore = useRideStore()

const loading = ref(false)
const actionLoading = ref(false)
const rideToCancel = ref(null)
const cancelling = ref(false)
let pollInterval = null

const rides = computed(() => rideStore.scheduledRides)

// Viaje que el conductor liberó — dispara el modal automáticamente
const releasedRide = computed(() =>
  rides.value.find(r => r.status === 'driver_released') || null
)

const formatDate = (iso) => {
  if (!iso) return ''
  return new Date(iso).toLocaleString('es-MX', { dateStyle: 'medium', timeStyle: 'short' })
}

const timeUntil = (iso) => {
  if (!iso) return ''
  const diff = new Date(iso) - Date.now()
  if (diff <= 0) return 'Próximamente'
  const hours = Math.floor(diff / 3600000)
  const days = Math.floor(hours / 24)
  if (days > 0) return `En ${days} día${days > 1 ? 's' : ''}`
  if (hours > 0) return `En ${hours} hora${hours > 1 ? 's' : ''}`
  const mins = Math.floor(diff / 60000)
  return `En ${mins} minuto${mins > 1 ? 's' : ''}`
}

const confirmCancel = (ride) => {
  rideToCancel.value = ride
}

const handleCancel = async () => {
  if (!rideToCancel.value) return
  cancelling.value = true
  const result = await rideStore.cancelScheduledRide(rideToCancel.value.ride_id)
  cancelling.value = false
  rideToCancel.value = null
  if (!result.success) toastError(result.error || 'No se pudo cancelar')
}

const handleReassign = async () => {
  if (!releasedRide.value) return
  actionLoading.value = true
  const result = await rideStore.reassignRide(releasedRide.value.ride_id)
  actionLoading.value = false
  if (!result.success) toastError(result.error || 'Error al reasignar')
}

const handleCancelReleased = async () => {
  if (!releasedRide.value) return
  actionLoading.value = true
  const result = await rideStore.cancelScheduledRide(releasedRide.value.ride_id)
  actionLoading.value = false
  if (!result.success) toastError(result.error || 'No se pudo cancelar')
}

onMounted(async () => {
  loading.value = true
  await rideStore.fetchScheduledRides()
  loading.value = false
  // Polling para detectar liberación del conductor en tiempo casi real
  pollInterval = setInterval(() => rideStore.fetchScheduledRides(), 10000)
})

onUnmounted(() => {
  if (pollInterval) clearInterval(pollInterval)
})
</script>
