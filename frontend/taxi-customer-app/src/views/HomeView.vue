<template>
  <div class="h-screen flex flex-col bg-gray-50">
    <!-- Header -->
    <header class="bg-white shadow-sm z-20">
      <div class="max-w-7xl mx-auto px-4 py-3">
        <div class="flex items-center justify-between">
          <div class="flex items-center space-x-2">
            <span class="text-2xl">🚕</span>
            <h1 class="text-lg font-bold text-gray-900">Taxi App</h1>
          </div>
          <div class="flex items-center space-x-3">
            <router-link to="/history" class="p-2 hover:bg-gray-100 rounded-lg">
              <span class="text-xl">📜</span>
            </router-link>
            <router-link to="/profile" class="p-2 hover:bg-gray-100 rounded-lg">
              <span class="text-xl">👤</span>
            </router-link>
          </div>
        </div>
      </div>
    </header>

    <!-- Main Content -->
    <div class="flex-1 relative overflow-hidden">
      <!-- Map Placeholder -->
      <div class="absolute inset-0 bg-gray-200 flex items-center justify-center">
        <div class="text-center">
          <div class="text-6xl mb-4">🗺️</div>
          <p class="text-gray-600 mb-2">Mapa Interactivo</p>
          <p class="text-sm text-gray-500">Integración con Google Maps aquí</p>
        </div>
      </div>

      <!-- Current Location Button -->
      <button
        @click="getCurrentLocation"
        class="absolute top-4 right-4 bg-white p-3 rounded-full shadow-lg hover:bg-gray-50"
      >
        <span class="text-2xl">📍</span>
      </button>

      <!-- Location Selection Card -->
      <div class="absolute bottom-0 left-0 right-0 bg-white rounded-t-3xl shadow-2xl p-6 max-h-[70vh] overflow-y-auto">
        <!-- Origin Selection -->
        <div class="mb-4">
          <label class="block text-sm font-medium text-gray-700 mb-2">¿Dónde estás?</label>
          <div class="relative">
            <span class="absolute inset-y-0 left-0 pl-3 flex items-center text-green-500">📍</span>
            <input
              v-model="originSearch"
              @input="searchOrigin"
              @focus="showOriginResults = true"
              type="text"
              placeholder="Ingresa tu ubicación actual"
              class="w-full pl-10 pr-10 py-3 border-2 border-gray-300 rounded-lg focus:border-taxi-yellow"
            />
            <button
              v-if="locationStore.hasOrigin"
              @click="clearOrigin"
              class="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 hover:text-gray-600"
            >
              ✕
            </button>
          </div>

          <!-- Origin Search Results -->
          <div v-if="showOriginResults && originResults.length > 0" class="mt-2 bg-white border rounded-lg shadow-lg max-h-48 overflow-y-auto">
            <div
              v-for="result in originResults"
              :key="result.id"
              @click="selectOrigin(result)"
              class="p-3 hover:bg-gray-50 cursor-pointer border-b last:border-b-0"
            >
              <p class="font-medium text-gray-900">{{ result.name }}</p>
              <p class="text-sm text-gray-500">{{ result.address }}</p>
            </div>
          </div>

          <!-- Current Location Button -->
          <button
            @click="setOriginToCurrent"
            class="mt-2 text-sm text-taxi-blue hover:underline flex items-center"
          >
            <span class="mr-1">📍</span>
            Usar mi ubicación actual
          </button>
        </div>

        <!-- Destination Selection -->
        <div class="mb-4">
          <label class="block text-sm font-medium text-gray-700 mb-2">¿A dónde vas?</label>
          <div class="relative">
            <span class="absolute inset-y-0 left-0 pl-3 flex items-center text-red-500">📍</span>
            <input
              v-model="destinationSearch"
              @input="searchDestination"
              @focus="showDestinationResults = true"
              type="text"
              placeholder="Ingresa tu destino"
              class="w-full pl-10 pr-10 py-3 border-2 border-gray-300 rounded-lg focus:border-taxi-yellow"
            />
            <button
              v-if="locationStore.hasDestination"
              @click="clearDestination"
              class="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 hover:text-gray-600"
            >
              ✕
            </button>
          </div>

          <!-- Destination Search Results -->
          <div v-if="showDestinationResults && destinationResults.length > 0" class="mt-2 bg-white border rounded-lg shadow-lg max-h-48 overflow-y-auto">
            <div
              v-for="result in destinationResults"
              :key="result.id"
              @click="selectDestination(result)"
              class="p-3 hover:bg-gray-50 cursor-pointer border-b last:border-b-0"
            >
              <p class="font-medium text-gray-900">{{ result.name }}</p>
              <p class="text-sm text-gray-500">{{ result.address }}</p>
            </div>
          </div>
        </div>

        <!-- Favorite Locations -->
        <div v-if="favoriteLocations.length > 0" class="mb-4">
          <p class="text-sm font-medium text-gray-700 mb-2">Lugares favoritos</p>
          <div class="grid grid-cols-2 gap-2">
            <button
              v-for="favorite in favoriteLocations"
              :key="favorite.id"
              @click="selectDestination(favorite)"
              class="p-3 border-2 border-gray-200 rounded-lg hover:border-taxi-yellow text-left"
            >
              <p class="font-medium text-gray-900">{{ favorite.type === 'home' ? '🏠 Casa' : favorite.type === 'work' ? '💼 Trabajo' : '⭐ ' + favorite.name }}</p>
              <p class="text-xs text-gray-500 truncate">{{ favorite.address }}</p>
            </button>
          </div>
        </div>

        <!-- Fare Estimate -->
        <div v-if="estimatedFare" class="mb-4 bg-green-50 border border-green-200 rounded-lg p-4">
          <div class="flex items-center justify-between mb-2">
            <span class="text-sm font-medium text-gray-700">Tarifa estimada</span>
            <span class="text-2xl font-bold text-green-600">${{ estimatedFare.total }}</span>
          </div>
          <div class="text-xs text-gray-600 space-y-1">
            <div class="flex justify-between">
              <span>Distancia: {{ estimatedFare.distance_km }} km</span>
              <span>Tiempo: ~{{ estimatedFare.duration_minutes }} min</span>
            </div>
          </div>
        </div>

        <!-- Request Ride Button -->
        <button
          @click="requestRide"
          :disabled="!locationStore.canRequestRide || requesting"
          class="w-full bg-taxi-yellow hover:bg-yellow-500 text-white font-bold py-4 rounded-lg transition duration-200 disabled:opacity-50 disabled:cursor-not-allowed shadow-lg"
        >
          <span v-if="!requesting">{{ locationStore.canRequestRide ? '🚕 Solicitar Taxi' : 'Ingresa origen y destino' }}</span>
          <span v-else>Solicitando...</span>
        </button>

        <!-- Promo Code -->
        <button
          @click="showPromoCode = !showPromoCode"
          class="w-full mt-3 text-sm text-taxi-blue hover:underline"
        >
          {{ showPromoCode ? '✕ Ocultar código promocional' : '🎁 ¿Tienes un código promocional?' }}
        </button>

        <div v-if="showPromoCode" class="mt-3 flex gap-2">
          <input
            v-model="promoCode"
            type="text"
            placeholder="Ingresa código"
            class="flex-1 px-3 py-2 border border-gray-300 rounded-lg"
          />
          <button
            @click="validatePromo"
            class="px-4 py-2 bg-taxi-green text-white rounded-lg hover:bg-green-600"
          >
            Aplicar
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useLocationStore } from '../stores/locationStore'
import { useRideStore } from '../stores/rideStore'

const router = useRouter()
const locationStore = useLocationStore()
const rideStore = useRideStore()

const originSearch = ref('')
const destinationSearch = ref('')
const originResults = ref([])
const destinationResults = ref([])
const showOriginResults = ref(false)
const showDestinationResults = ref(false)
const requesting = ref(false)
const showPromoCode = ref(false)
const promoCode = ref('')

const estimatedFare = computed(() => rideStore.estimatedFare)
const favoriteLocations = computed(() => locationStore.favoriteLocations)

let searchTimeout = null

const searchOrigin = async () => {
  clearTimeout(searchTimeout)
  searchTimeout = setTimeout(async () => {
    if (originSearch.value.length >= 3) {
      const result = await locationStore.searchAddress(originSearch.value)
      if (result.success) {
        originResults.value = result.results
      }
    } else {
      originResults.value = []
    }
  }, 300)
}

const searchDestination = async () => {
  clearTimeout(searchTimeout)
  searchTimeout = setTimeout(async () => {
    if (destinationSearch.value.length >= 3) {
      const result = await locationStore.searchAddress(destinationSearch.value)
      if (result.success) {
        destinationResults.value = result.results
      }
    } else {
      destinationResults.value = []
    }
  }, 300)
}

const selectOrigin = (location) => {
  locationStore.selectOrigin(location)
  originSearch.value = location.address
  showOriginResults.value = false
  originResults.value = []

  if (locationStore.hasDestination) {
    estimateFare()
  }
}

const selectDestination = (location) => {
  locationStore.selectDestination(location)
  destinationSearch.value = location.address
  showDestinationResults.value = false
  destinationResults.value = []

  if (locationStore.hasOrigin) {
    estimateFare()
  }
}

const clearOrigin = () => {
  locationStore.clearOrigin()
  originSearch.value = ''
  rideStore.clearEstimate()
}

const clearDestination = () => {
  locationStore.clearDestination()
  destinationSearch.value = ''
  rideStore.clearEstimate()
}

const getCurrentLocation = async () => {
  try {
    await locationStore.getCurrentLocation()
    alert('Ubicación obtenida')
  } catch (err) {
    alert('No se pudo obtener la ubicación')
  }
}

const setOriginToCurrent = async () => {
  await locationStore.setOriginToCurrent()
  if (locationStore.origin) {
    originSearch.value = locationStore.origin.address || 'Mi ubicación'
    if (locationStore.hasDestination) {
      estimateFare()
    }
  }
}

const estimateFare = async () => {
  if (locationStore.canRequestRide) {
    await rideStore.estimateFare(locationStore.origin, locationStore.destination)
  }
}

const validatePromo = async () => {
  if (promoCode.value) {
    alert(`Código ${promoCode.value} aplicado`)
  }
}

const requestRide = async () => {
  if (!locationStore.canRequestRide) return

  requesting.value = true

  try {
    const rideData = {
      origin: locationStore.origin,
      destination: locationStore.destination,
      payment_method: 'cash',
      promo_code: promoCode.value || null
    }

    const result = await rideStore.requestRide(rideData)

    if (result.success) {
      router.push(`/ride/${result.ride.ride_id}`)
    } else {
      alert(result.error || 'Error al solicitar viaje')
    }
  } catch (err) {
    alert('Error de conexión')
  } finally {
    requesting.value = false
  }
}

onMounted(() => {
  locationStore.loadFavoriteLocations()

  // Check if there's an active ride
  rideStore.fetchActiveRide().then(() => {
    if (rideStore.hasActiveRide) {
      router.push(`/ride/${rideStore.activeRide.ride_id}`)
    }
  })
})
</script>
