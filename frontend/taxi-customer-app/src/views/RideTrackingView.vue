<template>
  <div class="h-screen flex flex-col bg-gray-50">
    <!-- Header -->
    <header class="bg-white shadow-sm z-20">
      <div class="max-w-7xl mx-auto px-4 py-3">
        <div class="flex items-center justify-between">
          <button @click="goBack" class="p-2 hover:bg-gray-100 rounded-lg">
            <span class="text-xl">←</span>
          </button>
          <div class="text-center">
            <h1 class="font-bold text-gray-900">{{ getStatusLabel(rideStatus) }}</h1>
            <p class="text-sm text-gray-500">ID: {{ rideId }}</p>
          </div>
          <div class="w-10"></div>
        </div>
      </div>
    </header>

    <!-- Loading -->
    <div v-if="loading" class="flex-1 flex items-center justify-center">
      <div class="text-center">
        <div class="text-6xl mb-4">⏳</div>
        <p class="text-gray-500">Cargando información del viaje...</p>
      </div>
    </div>

    <!-- Error -->
    <div v-else-if="error" class="flex-1 flex items-center justify-center">
      <div class="text-center">
        <div class="text-6xl mb-4">❌</div>
        <p class="text-red-600 mb-4">{{ error }}</p>
        <button @click="goBack" class="bg-gray-200 px-6 py-2 rounded-lg">
          Volver
        </button>
      </div>
    </div>

    <!-- Main Content -->
    <div v-else-if="ride" class="flex-1 flex flex-col">
      <!-- Map Area -->
      <div class="flex-1 relative bg-gray-200">
        <div class="absolute inset-0 flex items-center justify-center">
          <div class="text-center">
            <div class="text-6xl mb-4">🗺️</div>
            <p class="text-gray-600">Mapa con tracking en tiempo real</p>
            <p class="text-sm text-gray-500 mt-2">
              Conductor: {{ ride.driver?.current_lat?.toFixed(4) }}, {{ ride.driver?.current_lon?.toFixed(4) }}
            </p>
          </div>
        </div>

        <!-- Status Badge -->
        <div class="absolute top-4 left-4 right-4">
          <div :class="[
            'px-4 py-2 rounded-full text-white font-semibold text-center shadow-lg',
            getStatusColorClass(rideStatus)
          ]">
            {{ getStatusLabel(rideStatus) }}
          </div>
        </div>
      </div>

      <!-- Info Card -->
      <div class="bg-white rounded-t-3xl shadow-2xl p-6 max-h-[50vh] overflow-y-auto">
        <!-- Searching for Driver -->
        <div v-if="rideStatus === 'requested'" class="text-center py-8">
          <div class="text-6xl mb-4 animate-pulse">🔍</div>
          <h3 class="text-xl font-bold text-gray-900 mb-2">Buscando conductor...</h3>
          <p class="text-gray-600 mb-4">Esto puede tomar unos segundos</p>
          <div class="flex items-center justify-center space-x-2">
            <div class="w-2 h-2 bg-taxi-yellow rounded-full animate-bounce"></div>
            <div class="w-2 h-2 bg-taxi-yellow rounded-full animate-bounce" style="animation-delay: 0.1s"></div>
            <div class="w-2 h-2 bg-taxi-yellow rounded-full animate-bounce" style="animation-delay: 0.2s"></div>
          </div>
        </div>

        <!-- Driver Assigned -->
        <div v-else>
          <!-- Driver Info -->
          <div v-if="ride.driver" class="mb-6">
            <h3 class="text-lg font-semibold text-gray-900 mb-3">Tu Conductor</h3>
            <div class="flex items-center space-x-4 bg-gray-50 p-4 rounded-lg">
              <div class="w-16 h-16 bg-gray-300 rounded-full flex items-center justify-center text-3xl">
                👤
              </div>
              <div class="flex-1">
                <h4 class="text-lg font-semibold text-gray-900">{{ ride.driver.name }}</h4>
                <p class="text-sm text-gray-600">
                  {{ ride.driver.vehicle?.brand }} {{ ride.driver.vehicle?.model }}
                </p>
                <p class="text-sm text-gray-600">Placas: {{ ride.driver.vehicle?.plates }}</p>
                <div class="flex items-center mt-1">
                  <span class="text-yellow-500 mr-1">⭐</span>
                  <span class="text-sm font-medium">{{ ride.driver.rating?.toFixed(1) || '5.0' }}</span>
                </div>
              </div>
              <div class="flex flex-col space-y-2">
                <a
                  :href="`tel:${ride.driver.phone}`"
                  class="px-4 py-2 bg-green-500 text-white rounded-lg text-center hover:bg-green-600"
                >
                  📞
                </a>
                <a
                  :href="`sms:${ride.driver.phone}`"
                  class="px-4 py-2 bg-blue-500 text-white rounded-lg text-center hover:bg-blue-600"
                >
                  💬
                </a>
              </div>
            </div>
          </div>

          <!-- ETA -->
          <div v-if="rideStatus === 'assigned' || rideStatus === 'driver_arriving'" class="mb-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
            <div class="flex items-center justify-between">
              <div>
                <p class="text-sm text-gray-600">Tiempo estimado de llegada</p>
                <p class="text-3xl font-bold text-blue-600">{{ estimatedArrivalTime }} min</p>
              </div>
              <div class="text-4xl">🚗💨</div>
            </div>
          </div>

          <!-- Route Info -->
          <div class="mb-6">
            <h3 class="text-lg font-semibold text-gray-900 mb-3">Ruta del Viaje</h3>
            <div class="space-y-3">
              <div class="flex items-start">
                <span class="text-green-500 text-xl mr-3">📍</span>
                <div class="flex-1">
                  <p class="text-sm text-gray-500">Origen</p>
                  <p class="text-gray-900">{{ ride.origin.address }}</p>
                </div>
              </div>
              <div class="flex items-start">
                <span class="text-red-500 text-xl mr-3">📍</span>
                <div class="flex-1">
                  <p class="text-sm text-gray-500">Destino</p>
                  <p class="text-gray-900">{{ ride.destination.address }}</p>
                </div>
              </div>
            </div>
          </div>

          <!-- Fare Info -->
          <div class="mb-6 bg-green-50 border border-green-200 rounded-lg p-4">
            <div class="flex items-center justify-between">
              <div>
                <p class="text-sm text-gray-600">Tarifa Total</p>
                <p class="text-3xl font-bold text-green-600">${{ ride.total_fare }}</p>
              </div>
              <div class="text-right">
                <p class="text-sm text-gray-600">{{ ride.distance_km }} km</p>
                <p class="text-sm text-gray-600">~{{ ride.duration_minutes }} min</p>
              </div>
            </div>
            <p class="text-xs text-gray-500 mt-2">
              Método de pago: {{ ride.payment_method === 'cash' ? '💵 Efectivo' : '💳 Tarjeta' }}
            </p>
          </div>

          <!-- Actions -->
          <div class="space-y-3">
            <!-- Cancel Button (only if not started) -->
            <button
              v-if="rideStatus !== 'started' && rideStatus !== 'in_progress' && rideStatus !== 'completed'"
              @click="showCancelDialog = true"
              class="w-full py-3 border-2 border-red-500 text-red-500 font-semibold rounded-lg hover:bg-red-50"
            >
              Cancelar Viaje
            </button>

            <!-- Rate Ride (when completed) -->
            <div v-if="rideStatus === 'completed' && !rated" class="border-2 border-taxi-yellow rounded-lg p-4">
              <h3 class="text-lg font-semibold text-gray-900 mb-3">Califica tu viaje</h3>
              <div class="flex justify-center space-x-2 mb-3">
                <button
                  v-for="star in 5"
                  :key="star"
                  @click="rating = star"
                  class="text-3xl"
                >
                  {{ star <= rating ? '⭐' : '☆' }}
                </button>
              </div>
              <textarea
                v-model="ratingComment"
                placeholder="Comentario (opcional)"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg mb-3"
                rows="3"
              ></textarea>
              <button
                @click="submitRating"
                :disabled="rating === 0"
                class="w-full bg-taxi-yellow text-white py-3 rounded-lg font-semibold disabled:opacity-50"
              >
                Enviar Calificación
              </button>
            </div>

            <!-- Back to Home -->
            <button
              v-if="rideStatus === 'completed'"
              @click="goHome"
              class="w-full bg-taxi-green text-white py-3 rounded-lg font-semibold"
            >
              Solicitar Otro Viaje
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Cancel Dialog -->
    <div
      v-if="showCancelDialog"
      class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
      @click.self="showCancelDialog = false"
    >
      <div class="bg-white rounded-lg shadow-2xl max-w-md w-full p-6">
        <h3 class="text-xl font-bold text-gray-900 mb-4">¿Cancelar viaje?</h3>
        <p class="text-gray-600 mb-4">¿Estás seguro de que deseas cancelar este viaje?</p>

        <div class="mb-4">
          <label class="block text-sm font-medium text-gray-700 mb-2">Motivo (opcional)</label>
          <select
            v-model="cancelReason"
            class="w-full border border-gray-300 rounded-lg px-3 py-2"
          >
            <option value="">Selecciona un motivo...</option>
            <option value="changed_plans">Cambié de planes</option>
            <option value="too_long">Está tardando mucho</option>
            <option value="found_another">Encontré otro transporte</option>
            <option value="other">Otro motivo</option>
          </select>
        </div>

        <div class="flex space-x-3">
          <button
            @click="showCancelDialog = false"
            class="flex-1 bg-gray-200 hover:bg-gray-300 text-gray-700 font-semibold py-3 rounded-lg"
          >
            Volver
          </button>
          <button
            @click="cancelRide"
            :disabled="cancelling"
            class="flex-1 bg-red-500 hover:bg-red-600 text-white font-semibold py-3 rounded-lg disabled:opacity-50"
          >
            {{ cancelling ? 'Cancelando...' : 'Cancelar Viaje' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useRideStore } from '../stores/rideStore'

const router = useRouter()
const route = useRoute()
const rideStore = useRideStore()

const ride = ref(null)
const loading = ref(true)
const error = ref(null)
const showCancelDialog = ref(false)
const cancelReason = ref('')
const cancelling = ref(false)
const rating = ref(0)
const ratingComment = ref('')
const rated = ref(false)

const rideId = computed(() => route.params.rideId)
const rideStatus = computed(() => ride.value?.status || null)
const estimatedArrivalTime = computed(() => {
  // Simulación - en producción vendría del backend
  return Math.floor(Math.random() * 10) + 5
})

const getStatusLabel = (status) => {
  const labels = {
    requested: 'Buscando conductor...',
    assigned: 'Conductor asignado',
    driver_arriving: 'Conductor en camino',
    started: 'Viaje iniciado',
    in_progress: 'En camino al destino',
    completed: 'Viaje completado',
    cancelled: 'Viaje cancelado'
  }
  return labels[status] || 'Desconocido'
}

const getStatusColorClass = (status) => {
  const colors = {
    requested: 'bg-blue-500',
    assigned: 'bg-yellow-500',
    driver_arriving: 'bg-orange-500',
    started: 'bg-green-500',
    in_progress: 'bg-green-500',
    completed: 'bg-gray-500',
    cancelled: 'bg-red-500'
  }
  return colors[status] || 'bg-gray-500'
}

const loadRideDetails = async () => {
  loading.value = true
  error.value = null

  try {
    const result = await rideStore.fetchRideDetails(rideId.value)
    if (result.success) {
      ride.value = result.ride
    } else {
      error.value = result.error
    }
  } catch (err) {
    error.value = 'Error al cargar el viaje'
  } finally {
    loading.value = false
  }
}

const cancelRide = async () => {
  cancelling.value = true

  try {
    const result = await rideStore.cancelRide(rideId.value, cancelReason.value || 'Cliente canceló')

    if (result.success) {
      alert('Viaje cancelado exitosamente')
      router.push('/home')
    } else {
      alert(result.error || 'Error al cancelar')
    }
  } catch (err) {
    alert('Error de conexión')
  } finally {
    cancelling.value = false
    showCancelDialog.value = false
  }
}

const submitRating = async () => {
  if (rating.value === 0) return

  try {
    const result = await rideStore.rateRide(rideId.value, rating.value, ratingComment.value)

    if (result.success) {
      rated.value = true
      alert('¡Gracias por tu calificación!')
    } else {
      alert(result.error || 'Error al calificar')
    }
  } catch (err) {
    alert('Error de conexión')
  }
}

const goBack = () => {
  router.push('/home')
}

const goHome = () => {
  router.push('/home')
}

onMounted(() => {
  loadRideDetails()

  // Start tracking if ride is active
  if (rideStore.hasActiveRide) {
    rideStore.startTracking()
  }
})

onUnmounted(() => {
  // Clean up tracking when leaving
  if (rideStatus.value === 'completed' || rideStatus.value === 'cancelled') {
    rideStore.stopTracking()
  }
})
</script>
