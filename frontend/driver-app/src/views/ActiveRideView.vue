<template>
  <div class="min-h-screen bg-gray-50">
    <!-- Header con estado del viaje -->
    <header class="bg-white shadow-sm sticky top-0 z-10">
      <div class="max-w-7xl mx-auto px-4 py-4">
        <div class="flex items-center justify-between">
          <div class="flex items-center space-x-3">
            <span class="text-3xl">🚗</span>
            <div>
              <h1 class="text-xl font-bold text-gray-900">Viaje en Curso</h1>
              <p :class="[
                'text-sm font-medium',
                getStatusColor(rideStatus)
              ]">
                {{ getStatusLabel(rideStatus) }}
              </p>
            </div>
          </div>
          <div class="text-2xl font-bold text-green-600">
            ${{ ride?.total_fare || '0.00' }}
          </div>
        </div>
      </div>
    </header>

    <!-- Contenido principal -->
    <main class="max-w-7xl mx-auto px-4 py-6">
      <div v-if="loading" class="flex items-center justify-center h-64">
        <div class="text-center">
          <div class="text-6xl mb-4">⏳</div>
          <p class="text-gray-500">Cargando información del viaje...</p>
        </div>
      </div>

      <div v-else-if="error" class="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
        <div class="text-6xl mb-4">❌</div>
        <h3 class="text-xl font-semibold text-red-600 mb-2">Error</h3>
        <p class="text-red-500">{{ error }}</p>
      </div>

      <div v-else-if="ride" class="space-y-6">
        <!-- Información del cliente -->
        <div class="bg-white rounded-lg shadow-lg p-6">
          <div class="flex items-center justify-between">
            <div class="flex items-center space-x-4">
              <div class="w-16 h-16 bg-gray-200 rounded-full flex items-center justify-center text-3xl">
                👤
              </div>
              <div>
                <h3 class="text-xl font-semibold text-gray-900">{{ ride.customer.name }}</h3>
                <div class="flex items-center space-x-3 mt-1">
                  <span class="text-sm text-gray-500">📱 {{ ride.customer.phone }}</span>
                  <span class="text-sm text-yellow-500">⭐ {{ ride.customer.rating || 'N/A' }}</span>
                </div>
              </div>
            </div>
            <div class="flex flex-col space-y-2">
              <a
                :href="`tel:${ride.customer.phone}`"
                class="bg-green-500 hover:bg-green-600 text-white px-4 py-2 rounded-lg text-center"
              >
                📞 Llamar
              </a>
              <a
                :href="`sms:${ride.customer.phone}`"
                class="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded-lg text-center"
              >
                💬 SMS
              </a>
            </div>
          </div>
        </div>

        <!-- Ruta y navegación -->
        <div class="bg-white rounded-lg shadow-lg p-6">
          <h3 class="text-lg font-semibold text-gray-900 mb-4">Ruta de Navegación</h3>

          <!-- Origen -->
          <div class="flex items-start space-x-3 mb-4 pb-4 border-b">
            <div class="flex-shrink-0 w-10 h-10 bg-green-100 rounded-full flex items-center justify-center">
              <span class="text-green-600 font-bold text-lg">A</span>
            </div>
            <div class="flex-1">
              <p class="text-sm text-gray-500 mb-1">Punto de Recogida</p>
              <p class="text-gray-900 font-medium">{{ ride.origin.address }}</p>
              <button
                v-if="rideStatus === 'assigned'"
                @click="navigateToOrigin"
                class="mt-2 text-sm text-blue-600 hover:underline flex items-center"
              >
                🧭 Navegar al origen
              </button>
            </div>
          </div>

          <!-- Destino -->
          <div class="flex items-start space-x-3">
            <div class="flex-shrink-0 w-10 h-10 bg-red-100 rounded-full flex items-center justify-center">
              <span class="text-red-600 font-bold text-lg">B</span>
            </div>
            <div class="flex-1">
              <p class="text-sm text-gray-500 mb-1">Destino Final</p>
              <p class="text-gray-900 font-medium">{{ ride.destination.address }}</p>
              <button
                v-if="rideStatus === 'started' || rideStatus === 'in_progress'"
                @click="navigateToDestination"
                class="mt-2 text-sm text-blue-600 hover:underline flex items-center"
              >
                🧭 Navegar al destino
              </button>
            </div>
          </div>

          <!-- Mapa placeholder -->
          <div class="mt-6 bg-gray-200 rounded-lg h-64 flex flex-col items-center justify-center">
            <div class="text-6xl mb-2">🗺️</div>
            <p class="text-gray-600 mb-4">Vista de mapa en vivo</p>
            <div class="flex space-x-2">
              <button
                @click="openGoogleMaps"
                class="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm"
              >
                Abrir Google Maps
              </button>
              <button
                @click="openWaze"
                class="bg-cyan-600 hover:bg-cyan-700 text-white px-4 py-2 rounded-lg text-sm"
              >
                Abrir Waze
              </button>
            </div>
          </div>
        </div>

        <!-- Detalles del viaje -->
        <div class="bg-white rounded-lg shadow-lg p-6">
          <h3 class="text-lg font-semibold text-gray-900 mb-4">Detalles del Viaje</h3>
          <div class="grid grid-cols-2 gap-4">
            <div class="bg-gray-50 rounded-lg p-4">
              <p class="text-sm text-gray-500 mb-1">Distancia</p>
              <p class="text-2xl font-bold text-gray-900">{{ ride.distance_km }} km</p>
            </div>
            <div class="bg-gray-50 rounded-lg p-4">
              <p class="text-sm text-gray-500 mb-1">Tiempo Estimado</p>
              <p class="text-2xl font-bold text-gray-900">{{ ride.duration_minutes }} min</p>
            </div>
            <div class="bg-gray-50 rounded-lg p-4">
              <p class="text-sm text-gray-500 mb-1">Tarifa</p>
              <p class="text-2xl font-bold text-green-600">${{ ride.total_fare }}</p>
            </div>
            <div class="bg-gray-50 rounded-lg p-4">
              <p class="text-sm text-gray-500 mb-1">Método de Pago</p>
              <p class="text-lg font-semibold text-gray-900">
                {{ ride.payment_method === 'cash' ? '💵 Efectivo' : '💳 Tarjeta' }}
              </p>
            </div>
          </div>
        </div>

        <!-- Cronómetro del viaje -->
        <div v-if="rideStatus === 'started' || rideStatus === 'in_progress'" class="bg-gradient-to-r from-blue-500 to-blue-600 text-white rounded-lg shadow-lg p-6 text-center">
          <p class="text-sm mb-2">Tiempo de viaje</p>
          <p class="text-5xl font-bold">{{ elapsedTime }}</p>
        </div>

        <!-- Botones de acción según estado -->
        <div class="sticky bottom-0 bg-white border-t shadow-lg p-4">
          <div class="max-w-7xl mx-auto space-y-3">
            <!-- Estado: Asignado (esperando llegar al origen) -->
            <div v-if="rideStatus === 'assigned'">
              <button
                @click="handleStartRide"
                :disabled="submitting"
                class="w-full bg-taxi-green hover:bg-green-600 text-white font-semibold py-4 rounded-lg transition duration-200 disabled:opacity-50 shadow-lg"
              >
                <span v-if="!submitting">▶️ Iniciar Viaje (He recogido al cliente)</span>
                <span v-else>Iniciando...</span>
              </button>
              <button
                @click="showCancelDialog = true"
                class="w-full mt-2 bg-gray-200 hover:bg-gray-300 text-gray-700 font-semibold py-3 rounded-lg"
              >
                ✕ Cancelar Viaje
              </button>
            </div>

            <!-- Estado: Iniciado (viaje en progreso) -->
            <div v-else-if="rideStatus === 'started' || rideStatus === 'in_progress'">
              <button
                @click="handleCompleteRide"
                :disabled="submitting"
                class="w-full bg-taxi-green hover:bg-green-600 text-white font-semibold py-4 rounded-lg transition duration-200 disabled:opacity-50 shadow-lg"
              >
                <span v-if="!submitting">✓ Completar Viaje (He llegado al destino)</span>
                <span v-else>Completando...</span>
              </button>
              <button
                @click="showCancelDialog = true"
                class="w-full mt-2 bg-gray-200 hover:bg-gray-300 text-gray-700 font-semibold py-3 rounded-lg"
              >
                ✕ Cancelar Viaje
              </button>
            </div>
          </div>
        </div>
      </div>
    </main>

    <!-- Modal de cancelación -->
    <div
      v-if="showCancelDialog"
      class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
      @click.self="showCancelDialog = false"
    >
      <div class="bg-white rounded-lg shadow-2xl max-w-md w-full p-6">
        <h3 class="text-xl font-bold text-gray-900 mb-4">Cancelar Viaje</h3>
        <p class="text-gray-600 mb-4">¿Estás seguro de que deseas cancelar este viaje?</p>

        <div class="mb-4">
          <label class="block text-sm font-medium text-gray-700 mb-2">Motivo de cancelación</label>
          <select
            v-model="cancelReason"
            class="w-full border border-gray-300 rounded-lg px-3 py-2"
          >
            <option value="">Selecciona un motivo...</option>
            <option value="customer_no_show">Cliente no se presentó</option>
            <option value="customer_requested">Cliente solicitó cancelación</option>
            <option value="vehicle_issue">Problema con el vehículo</option>
            <option value="emergency">Emergencia personal</option>
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
            @click="handleCancelRide"
            :disabled="!cancelReason || submitting"
            class="flex-1 bg-red-500 hover:bg-red-600 text-white font-semibold py-3 rounded-lg disabled:opacity-50"
          >
            <span v-if="!submitting">Confirmar Cancelación</span>
            <span v-else>Cancelando...</span>
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
const submitting = ref(false)
const showCancelDialog = ref(false)
const cancelReason = ref('')
const elapsedTime = ref('00:00:00')
const timerInterval = ref(null)
const startTime = ref(null)

const rideId = computed(() => route.params.rideId)
// backend usa 'confirmed' para viaje aceptado, el template espera 'assigned'
const rideStatus = computed(() => {
  const s = ride.value?.status || null
  if (s === 'confirmed') return 'assigned'
  return s
})

const getStatusLabel = (status) => {
  const labels = {
    assigned: 'Asignado - Dirígete al origen',
    driver_arriving: 'Llegando al origen',
    started: 'Viaje iniciado',
    in_progress: 'En progreso',
    completed: 'Completado'
  }
  return labels[status] || 'Desconocido'
}

const getStatusColor = (status) => {
  const colors = {
    assigned: 'text-yellow-600',
    driver_arriving: 'text-orange-600',
    started: 'text-blue-600',
    in_progress: 'text-blue-600',
    completed: 'text-green-600'
  }
  return colors[status] || 'text-gray-600'
}

const loadRideDetails = async () => {
  loading.value = true
  error.value = null

  try {
    const result = await rideStore.fetchRideDetails(rideId.value)
    if (result.success) {
      ride.value = result.ride

      // Iniciar cronómetro si el viaje ya empezó
      if (ride.value.status === 'started' || ride.value.status === 'in_progress') {
        startTimer()
      }
    } else {
      error.value = result.error
    }
  } catch (err) {
    error.value = 'Error al cargar detalles del viaje'
  } finally {
    loading.value = false
  }
}

const startTimer = () => {
  startTime.value = Date.now()
  timerInterval.value = setInterval(() => {
    const elapsed = Math.floor((Date.now() - startTime.value) / 1000)
    const hours = Math.floor(elapsed / 3600)
    const minutes = Math.floor((elapsed % 3600) / 60)
    const seconds = elapsed % 60
    elapsedTime.value = `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`
  }, 1000)
}

const handleStartRide = async () => {
  submitting.value = true
  const result = await rideStore.startRide(rideId.value)

  if (result.success) {
    ride.value = result.ride
    startTimer()
  } else {
    alert(result.error || 'Error al iniciar el viaje')
  }
  submitting.value = false
}

const handleCompleteRide = async () => {
  if (!confirm('¿Has llegado al destino y el cliente ha bajado?')) {
    return
  }

  submitting.value = true
  const result = await rideStore.completeRide(rideId.value, {
    actual_distance_km: ride.value.distance_km,
    actual_duration_minutes: ride.value.duration_minutes
  })

  if (result.success) {
    alert('¡Viaje completado exitosamente!')
    router.push('/dashboard')
  } else {
    alert(result.error || 'Error al completar el viaje')
    submitting.value = false
  }
}

const handleCancelRide = async () => {
  submitting.value = true
  const result = await rideStore.cancelRide(rideId.value, cancelReason.value)

  if (result.success) {
    alert('Viaje cancelado')
    router.push('/dashboard')
  } else {
    alert(result.error || 'Error al cancelar el viaje')
    submitting.value = false
  }
}

const navigateToOrigin = () => {
  openGoogleMapsNavigation(ride.value.origin.lat, ride.value.origin.lon)
}

const navigateToDestination = () => {
  openGoogleMapsNavigation(ride.value.destination.lat, ride.value.destination.lon)
}

const openGoogleMapsNavigation = (lat, lon) => {
  window.open(`https://www.google.com/maps/dir/?api=1&destination=${lat},${lon}&travelmode=driving`, '_blank')
}

const openGoogleMaps = () => {
  const origin = `${ride.value.origin.lat},${ride.value.origin.lon}`
  const destination = `${ride.value.destination.lat},${ride.value.destination.lon}`
  window.open(`https://www.google.com/maps/dir/${origin}/${destination}`, '_blank')
}

const openWaze = () => {
  window.open(`https://waze.com/ul?ll=${ride.value.destination.lat},${ride.value.destination.lon}&navigate=yes`, '_blank')
}

onMounted(() => {
  loadRideDetails()
})

onUnmounted(() => {
  if (timerInterval.value) {
    clearInterval(timerInterval.value)
  }
})
</script>
