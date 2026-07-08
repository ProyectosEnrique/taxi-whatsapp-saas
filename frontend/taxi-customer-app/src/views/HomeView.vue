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
          <div class="flex items-center space-x-2">
            <router-link to="/scheduled" class="p-2 hover:bg-gray-100 rounded-lg" title="Viajes programados">
              <span class="text-xl">📅</span>
            </router-link>
            <router-link to="/history" class="p-2 hover:bg-gray-100 rounded-lg" title="Historial">
              <span class="text-xl">📜</span>
            </router-link>
            <router-link to="/profile" class="p-2 hover:bg-gray-100 rounded-lg" title="Perfil">
              <span class="text-xl">👤</span>
            </router-link>
          </div>
        </div>
      </div>
    </header>

    <!-- Main Content -->
    <div class="flex-1 relative overflow-hidden">
      <!-- Leaflet Map -->
      <div ref="mapContainer" class="absolute inset-0" style="z-index:0"></div>

      <!-- Current Location Button -->
      <button
        @click="getCurrentLocation"
        class="absolute top-4 right-4 bg-white p-3 rounded-full shadow-lg hover:bg-gray-50"
        style="z-index:800"
      >
        <span class="text-2xl">📍</span>
      </button>

      <!-- Location Selection Card -->
      <div class="absolute bottom-0 left-0 right-0 bg-white rounded-t-3xl shadow-2xl p-6 max-h-[70vh] overflow-y-auto" style="z-index:10">
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
            <span class="text-2xl font-bold text-green-600">${{ estimatedFare.fare }}</span>
          </div>
          <div class="text-xs text-gray-600 space-y-1">
            <div class="flex justify-between">
              <span>Distancia: {{ estimatedFare.distance_km }} km</span>
              <span>Tiempo: ~{{ estimatedFare.duration_minutes }} min</span>
            </div>
          </div>
        </div>

        <!-- Método de pago -->
        <div class="mb-4">
          <p class="text-xs font-medium text-gray-500 mb-2">Método de pago</p>
          <div class="grid grid-cols-2 gap-2">
            <button
              @click="paymentMethod = 'cash'"
              :class="[
                'flex items-center justify-center gap-2 py-3 rounded-lg border-2 font-semibold text-sm transition',
                paymentMethod === 'cash'
                  ? 'border-taxi-yellow bg-yellow-50 text-gray-900'
                  : 'border-gray-200 bg-white text-gray-500 hover:border-gray-300'
              ]"
            >
              💵 Efectivo
            </button>
            <button
              @click="paymentMethod = 'card'"
              :class="[
                'flex items-center justify-center gap-2 py-3 rounded-lg border-2 font-semibold text-sm transition',
                paymentMethod === 'card'
                  ? 'border-blue-500 bg-blue-50 text-blue-700'
                  : 'border-gray-200 bg-white text-gray-500 hover:border-gray-300'
              ]"
            >
              💳 Tarjeta
            </button>
          </div>
          <p v-if="paymentMethod === 'card'" class="text-xs text-blue-600 mt-1.5 text-center">
            Serás redirigido al checkout de MercadoPago
          </p>
        </div>

        <!-- Request Ride Button -->
        <button
          @click="requestRide"
          :disabled="!locationStore.canRequestRide || requesting"
          class="w-full bg-taxi-yellow hover:bg-yellow-500 text-white font-bold py-4 rounded-lg transition duration-200 disabled:opacity-50 disabled:cursor-not-allowed shadow-lg"
        >
          <span v-if="requesting">
            <span v-if="creatingPayment">Generando link de pago...</span>
            <span v-else>Solicitando...</span>
          </span>
          <span v-else>{{ locationStore.canRequestRide ? '🚕 Solicitar Taxi' : 'Ingresa origen y destino' }}</span>
        </button>

        <!-- Programar viaje -->
        <button
          @click="router.push('/schedule')"
          class="w-full mt-3 bg-white border-2 border-gray-200 hover:border-yellow-400 text-gray-700 font-semibold py-3 rounded-lg transition flex items-center justify-center space-x-2"
        >
          <span>📅</span><span>Programar para después</span>
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
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useLocationStore } from '../stores/locationStore'
import { useRideStore } from '../stores/rideStore'
import { useToast } from '../composables/useToast'
import { ridesApi, promoApi, paymentApi } from '../services/api'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

const { success: toastSuccess, error: toastError, info: toastInfo } = useToast()

const router = useRouter()
const locationStore = useLocationStore()
const rideStore = useRideStore()

// ── Mapa ─────────────────────────────────────────────────────────────────────
const mapContainer = ref(null)
let leafletMap = null
let originMarker = null
let destMarker   = null
let userMarker   = null
let routeLayer   = null

const DEFAULT_CENTER = [20.5888, -100.3899] // Querétaro
const DEFAULT_ZOOM   = 13

const makeMarkerIcon = (label, bg) => L.divIcon({
  html: `<div style="background:${bg};color:#fff;width:28px;height:28px;border-radius:50% 50% 50% 0;transform:rotate(-45deg);display:flex;align-items:center;justify-content:center;font-weight:700;font-size:13px;border:2px solid #fff;box-shadow:0 2px 6px rgba(0,0,0,.3)"><span style="transform:rotate(45deg)">${label}</span></div>`,
  className: '', iconSize: [28, 28], iconAnchor: [14, 28]
})

const userIcon = L.divIcon({
  html: '<div style="width:16px;height:16px;border-radius:50%;background:#3b82f6;border:3px solid #fff;box-shadow:0 0 0 3px rgba(59,130,246,.35)"></div>',
  className: '', iconSize: [16, 16], iconAnchor: [8, 8]
})

const initMap = async () => {
  await nextTick()
  if (!mapContainer.value || leafletMap) return

  leafletMap = L.map(mapContainer.value, { zoomControl: false })
    .setView(DEFAULT_CENTER, DEFAULT_ZOOM)

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap'
  }).addTo(leafletMap)

  L.control.zoom({ position: 'bottomright' }).addTo(leafletMap)

  // Si ya hay ubicación actual, centrar en ella
  if (locationStore.currentLocation) {
    const { lat, lng } = locationStore.currentLocation
    placeUserMarker(lat, lng)
    leafletMap.setView([lat, lng], 15)
  }
  // Si hay origen/destino pre-cargados, pintarlos
  if (locationStore.origin) placeOriginMarker(locationStore.origin.lat, locationStore.origin.lng)
  if (locationStore.destination) placeDestMarker(locationStore.destination.lat, locationStore.destination.lng)
  if (locationStore.origin && locationStore.destination) {
    await drawRoute(locationStore.origin.lat, locationStore.origin.lng,
                    locationStore.destination.lat, locationStore.destination.lng)
  }
}

const placeUserMarker = (lat, lng) => {
  if (!leafletMap) return
  if (userMarker) userMarker.setLatLng([lat, lng])
  else userMarker = L.marker([lat, lng], { icon: userIcon, zIndexOffset: 100 }).addTo(leafletMap)
}

const placeOriginMarker = (lat, lng) => {
  if (!leafletMap) return
  if (originMarker) originMarker.setLatLng([lat, lng])
  else originMarker = L.marker([lat, lng], { icon: makeMarkerIcon('A', '#22c55e') }).addTo(leafletMap)
}

const placeDestMarker = (lat, lng) => {
  if (!leafletMap) return
  if (destMarker) destMarker.setLatLng([lat, lng])
  else destMarker = L.marker([lat, lng], { icon: makeMarkerIcon('B', '#ef4444') }).addTo(leafletMap)
}

const clearMarker = (markerRef) => {
  if (markerRef && leafletMap) leafletMap.removeLayer(markerRef)
  return null
}

const clearRoute = () => {
  if (routeLayer && leafletMap) {
    leafletMap.removeLayer(routeLayer)
    routeLayer = null
  }
}

const drawRoute = async (oLat, oLng, dLat, dLng) => {
  clearRoute()
  try {
    const resp = await fetch(
      `https://router.project-osrm.org/route/v1/driving/${oLng},${oLat};${dLng},${dLat}?overview=full&geometries=geojson`
    )
    const data = await resp.json()
    if (data.routes?.[0]) {
      routeLayer = L.geoJSON(data.routes[0].geometry, {
        style: { color: '#3b82f6', weight: 4, opacity: 0.85 }
      }).addTo(leafletMap)
    }
  } catch {
    routeLayer = L.polyline([[oLat, oLng], [dLat, dLng]], {
      color: '#3b82f6', weight: 3, dashArray: '8,8', opacity: 0.7
    }).addTo(leafletMap)
  }
  // Ajustar vista para ver toda la ruta
  const bounds = [[oLat, oLng], [dLat, dLng]]
  leafletMap.fitBounds(bounds, { padding: [60, 60], maxZoom: 16 })
}

// Watchers reactivos: origen y destino
watch(() => locationStore.origin, async (loc) => {
  if (!leafletMap) return
  if (loc?.lat && loc?.lng) {
    placeOriginMarker(loc.lat, loc.lng)
    if (locationStore.destination) {
      await drawRoute(loc.lat, loc.lng, locationStore.destination.lat, locationStore.destination.lng)
    } else {
      leafletMap.flyTo([loc.lat, loc.lng], 15, { duration: 1 })
    }
  } else {
    originMarker = clearMarker(originMarker)
    clearRoute()
  }
})

watch(() => locationStore.destination, async (loc) => {
  // Sync the text input (handles pre-fill from Sofia or other external sources)
  if (loc?.address) destinationSearch.value = loc.address
  else if (!loc) destinationSearch.value = ''

  if (!leafletMap) return
  if (loc?.lat && loc?.lng) {
    placeDestMarker(loc.lat, loc.lng)
    if (locationStore.origin) {
      await drawRoute(locationStore.origin.lat, locationStore.origin.lng, loc.lat, loc.lng)
      estimateFare()
    } else {
      leafletMap.flyTo([loc.lat, loc.lng], 15, { duration: 1 })
    }
  } else {
    destMarker = clearMarker(destMarker)
    clearRoute()
  }
})

watch(() => locationStore.currentLocation, (loc) => {
  if (!leafletMap || !loc) return
  placeUserMarker(loc.lat, loc.lng)
  if (!locationStore.origin && !locationStore.destination) {
    leafletMap.flyTo([loc.lat, loc.lng], 15, { duration: 1.2 })
  }
})
// ─────────────────────────────────────────────────────────────────────────────

const originSearch = ref('')
const destinationSearch = ref('')
const originResults = ref([])
const destinationResults = ref([])
const showOriginResults = ref(false)
const showDestinationResults = ref(false)
const requesting = ref(false)
const creatingPayment = ref(false)
const paymentMethod = ref('cash')
const showPromoCode = ref(false)
const promoCode = ref('')
const promoDiscount = ref(0)
const promoValidating = ref(false)

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
  } catch (err) {
    toastError('No se pudo obtener la ubicación')
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
  const code = promoCode.value.trim()
  if (!code) return
  promoValidating.value = true
  promoDiscount.value = 0
  try {
    const res = await promoApi.validatePromo(code)
    if (res.valid) {
      promoDiscount.value = res.discount_pct
      toastSuccess(res.message)
    } else {
      toastError(res.message || 'Código no válido')
      promoCode.value = ''
    }
  } catch {
    toastError('Error al validar el código')
  } finally {
    promoValidating.value = false
  }
}

const requestRide = async () => {
  if (!locationStore.canRequestRide) return

  requesting.value = true
  creatingPayment.value = false

  try {
    const rideData = {
      origin:         locationStore.origin,
      destination:    locationStore.destination,
      payment_method: paymentMethod.value,
      promo_code:     promoCode.value || null,
    }

    const result = await rideStore.requestRide(rideData)

    if (!result.success) {
      toastError(result.error || 'Error al solicitar viaje')
      return
    }

    const tripId = result.ride.ride_id

    // Pago con tarjeta: crear preferencia MP y redirigir al checkout
    if (paymentMethod.value === 'card') {
      creatingPayment.value = true
      try {
        const pref = await paymentApi.createMPPreference(tripId)
        // Guardar trip_id en sessionStorage para recuperar al volver de MP
        sessionStorage.setItem('pending_mp_trip', tripId)
        // Redirigir al checkout de MercadoPago (misma ventana)
        window.location.href = pref.init_point
      } catch {
        toastError('No se pudo generar el link de pago. Intenta con efectivo.')
        // El viaje ya fue creado — ir al tracking de todas formas
        router.push(`/ride/${tripId}`)
      }
      return
    }

    router.push(`/ride/${tripId}`)
  } catch (err) {
    toastError('Error de conexión')
  } finally {
    requesting.value = false
    creatingPayment.value = false
  }
}

onMounted(async () => {
  locationStore.loadFavoriteLocations()

  // Redirigir si hay viaje activo
  rideStore.fetchActiveRide().then(() => {
    if (rideStore.hasActiveRide) {
      router.push(`/ride/${rideStore.activeRide.ride_id}`)
    }
  })

  await initMap()

  // Sync inputs if pre-filled externally (e.g. por Sofia antes de navegar aquí)
  if (locationStore.destination?.address) {
    destinationSearch.value = locationStore.destination.address
    if (locationStore.canRequestRide) estimateFare()
  }
  if (locationStore.origin?.address) {
    originSearch.value = locationStore.origin.address
  }
})

onUnmounted(() => {
  if (leafletMap) {
    leafletMap.remove()
    leafletMap = null
  }
})
</script>
