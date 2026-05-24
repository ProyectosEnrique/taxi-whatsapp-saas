<template>
  <div class="min-h-screen bg-gray-50">
    <header class="bg-white shadow-sm sticky top-0 z-10">
      <div class="max-w-7xl mx-auto px-4 py-4 flex items-center space-x-3">
        <button @click="router.back()" class="p-2 hover:bg-gray-100 rounded-lg">
          ← Volver
        </button>
        <div>
          <h1 class="text-xl font-bold text-gray-900">Programar Viaje</h1>
          <p class="text-sm text-gray-500">Reserva con anticipación</p>
        </div>
      </div>
    </header>

    <main class="max-w-7xl mx-auto px-4 py-6 space-y-6">

      <!-- Fecha y hora -->
      <div class="bg-white rounded-lg shadow p-6">
        <h2 class="text-lg font-semibold text-gray-900 mb-4">🗓️ Fecha y Hora</h2>

        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Fecha</label>
            <input
              v-model="selectedDate"
              type="date"
              :min="minDate"
              class="w-full border border-gray-300 rounded-lg px-3 py-2 focus:border-yellow-400 focus:outline-none"
            />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Hora</label>
            <input
              v-model="selectedTime"
              type="time"
              class="w-full border border-gray-300 rounded-lg px-3 py-2 focus:border-yellow-400 focus:outline-none"
            />
          </div>
        </div>

        <p v-if="scheduledDateError" class="mt-2 text-sm text-red-600">{{ scheduledDateError }}</p>
        <p v-else-if="selectedDate && selectedTime" class="mt-2 text-sm text-green-600 font-medium">
          ✓ Viaje el {{ formatScheduledDate() }}
        </p>
      </div>

      <!-- Origen -->
      <div class="bg-white rounded-lg shadow p-6">
        <h2 class="text-lg font-semibold text-gray-900 mb-4">📍 Origen</h2>
        <div class="relative">
          <input
            v-model="originSearch"
            @input="searchOrigin"
            @focus="showOriginResults = true"
            type="text"
            placeholder="¿Dónde te recogemos?"
            class="w-full pl-4 pr-10 py-3 border-2 border-gray-300 rounded-lg focus:border-yellow-400 focus:outline-none"
          />
          <button v-if="origin" @click="clearOrigin" class="absolute inset-y-0 right-3 flex items-center text-gray-400">✕</button>
        </div>

        <div v-if="showOriginResults && originResults.length > 0" class="mt-2 border rounded-lg shadow-lg max-h-48 overflow-y-auto">
          <div
            v-for="r in originResults" :key="r.id"
            @click="selectOrigin(r)"
            class="p-3 hover:bg-gray-50 cursor-pointer border-b last:border-b-0"
          >
            <p class="font-medium text-gray-900">{{ r.name }}</p>
            <p class="text-sm text-gray-500 truncate">{{ r.address }}</p>
          </div>
        </div>

        <button @click="setCurrentAsOrigin" class="mt-2 text-sm text-blue-600 hover:underline">
          📍 Usar mi ubicación actual
        </button>
      </div>

      <!-- Destino -->
      <div class="bg-white rounded-lg shadow p-6">
        <h2 class="text-lg font-semibold text-gray-900 mb-4">🏁 Destino</h2>
        <div class="relative">
          <input
            v-model="destinationSearch"
            @input="searchDestination"
            @focus="showDestinationResults = true"
            type="text"
            placeholder="¿A dónde vas?"
            class="w-full pl-4 pr-10 py-3 border-2 border-gray-300 rounded-lg focus:border-yellow-400 focus:outline-none"
          />
          <button v-if="destination" @click="clearDestination" class="absolute inset-y-0 right-3 flex items-center text-gray-400">✕</button>
        </div>

        <div v-if="showDestinationResults && destinationResults.length > 0" class="mt-2 border rounded-lg shadow-lg max-h-48 overflow-y-auto">
          <div
            v-for="r in destinationResults" :key="r.id"
            @click="selectDestination(r)"
            class="p-3 hover:bg-gray-50 cursor-pointer border-b last:border-b-0"
          >
            <p class="font-medium text-gray-900">{{ r.name }}</p>
            <p class="text-sm text-gray-500 truncate">{{ r.address }}</p>
          </div>
        </div>
      </div>

      <!-- Estimación de tarifa -->
      <div v-if="estimate" class="bg-green-50 border border-green-200 rounded-lg p-4">
        <div class="flex items-center justify-between">
          <span class="text-sm font-medium text-gray-700">Tarifa estimada</span>
          <span class="text-2xl font-bold text-green-600">${{ estimate.fare }}</span>
        </div>
        <div class="mt-1 text-xs text-gray-500 flex justify-between">
          <span>{{ estimate.distance_km }} km</span>
          <span>~{{ estimate.duration_minutes }} min</span>
        </div>
      </div>

      <!-- Método de pago -->
      <div class="bg-white rounded-lg shadow p-6">
        <h2 class="text-lg font-semibold text-gray-900 mb-4">💳 Método de Pago</h2>
        <div class="grid grid-cols-2 gap-3">
          <button
            @click="paymentMethod = 'cash'"
            :class="['border-2 rounded-lg p-4 text-center transition', paymentMethod === 'cash' ? 'border-yellow-400 bg-yellow-50' : 'border-gray-200 hover:border-gray-300']"
          >
            <div class="text-2xl mb-1">💵</div>
            <p class="font-medium text-gray-900">Efectivo</p>
          </button>
          <button
            @click="paymentMethod = 'card'"
            :class="['border-2 rounded-lg p-4 text-center transition', paymentMethod === 'card' ? 'border-yellow-400 bg-yellow-50' : 'border-gray-200 hover:border-gray-300']"
          >
            <div class="text-2xl mb-1">💳</div>
            <p class="font-medium text-gray-900">Tarjeta</p>
          </button>
        </div>
      </div>

      <!-- Botón programar -->
      <div class="pb-6">
        <button
          @click="handleSchedule"
          :disabled="!canSchedule || submitting"
          class="w-full bg-yellow-400 hover:bg-yellow-500 text-white font-bold py-4 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed shadow-lg text-lg"
        >
          <span v-if="!submitting">📅 Confirmar Reserva</span>
          <span v-else>Programando...</span>
        </button>
        <p v-if="!canSchedule && !submitting" class="mt-2 text-xs text-center text-gray-500">
          Completa fecha, hora, origen y destino
        </p>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useRideStore } from '../stores/rideStore'
import { useLocationStore } from '../stores/locationStore'
import { useToast } from '../composables/useToast'

const { success: toastSuccess, error: toastError } = useToast()

const router = useRouter()
const rideStore = useRideStore()
const locationStore = useLocationStore()

const selectedDate = ref('')
const selectedTime = ref('')
const paymentMethod = ref('cash')
const submitting = ref(false)

const origin = ref(null)
const destination = ref(null)
const originSearch = ref('')
const destinationSearch = ref('')
const originResults = ref([])
const destinationResults = ref([])
const showOriginResults = ref(false)
const showDestinationResults = ref(false)
const estimate = ref(null)

let searchTimeout = null

const minDate = computed(() => {
  const d = new Date()
  return d.toISOString().split('T')[0]
})

const scheduledDateError = computed(() => {
  if (!selectedDate.value || !selectedTime.value) return null
  const chosen = new Date(`${selectedDate.value}T${selectedTime.value}`)
  const minTime = new Date(Date.now() + 30 * 60 * 1000)
  if (chosen < minTime) return 'Mínimo 30 minutos de anticipación'
  return null
})

const canSchedule = computed(() =>
  selectedDate.value &&
  selectedTime.value &&
  !scheduledDateError.value &&
  origin.value &&
  destination.value
)

const formatScheduledDate = () => {
  const d = new Date(`${selectedDate.value}T${selectedTime.value}`)
  return d.toLocaleString('es-MX', { dateStyle: 'full', timeStyle: 'short' })
}

const searchOrigin = () => {
  clearTimeout(searchTimeout)
  searchTimeout = setTimeout(async () => {
    if (originSearch.value.length >= 3) {
      const result = await locationStore.searchAddress(originSearch.value)
      if (result.success) originResults.value = result.results
    } else {
      originResults.value = []
    }
  }, 300)
}

const searchDestination = () => {
  clearTimeout(searchTimeout)
  searchTimeout = setTimeout(async () => {
    if (destinationSearch.value.length >= 3) {
      const result = await locationStore.searchAddress(destinationSearch.value)
      if (result.success) destinationResults.value = result.results
    } else {
      destinationResults.value = []
    }
  }, 300)
}

const selectOrigin = async (r) => {
  origin.value = r
  originSearch.value = r.address
  showOriginResults.value = false
  originResults.value = []
  if (destination.value) await getEstimate()
}

const selectDestination = async (r) => {
  destination.value = r
  destinationSearch.value = r.address
  showDestinationResults.value = false
  destinationResults.value = []
  if (origin.value) await getEstimate()
}

const clearOrigin = () => { origin.value = null; originSearch.value = ''; estimate.value = null }
const clearDestination = () => { destination.value = null; destinationSearch.value = ''; estimate.value = null }

const setCurrentAsOrigin = async () => {
  await locationStore.getCurrentLocation()
  if (locationStore.currentLocation) {
    origin.value = {
      address: locationStore.currentLocation.address || 'Mi ubicación',
      lat: locationStore.currentLocation.lat,
      lng: locationStore.currentLocation.lng,
    }
    originSearch.value = origin.value.address
    if (destination.value) await getEstimate()
  }
}

const getEstimate = async () => {
  if (!origin.value || !destination.value) return
  const result = await rideStore.estimateFare(origin.value, destination.value)
  if (result.success) estimate.value = result.estimate
}

const handleSchedule = async () => {
  if (!canSchedule.value) return
  submitting.value = true

  const scheduledAt = new Date(`${selectedDate.value}T${selectedTime.value}`).toISOString()

  const result = await rideStore.scheduleRide({
    origin: origin.value,
    destination: destination.value,
    scheduled_at: scheduledAt,
    payment_method: paymentMethod.value,
  })

  if (result.success) {
    toastSuccess(`Viaje programado para ${formatScheduledDate()}`)
    router.push('/scheduled')
  } else {
    toastError(result.error || 'Error al programar el viaje')
    submitting.value = false
  }
}
</script>
