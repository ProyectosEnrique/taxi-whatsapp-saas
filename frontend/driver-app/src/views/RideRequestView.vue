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
          <div>
            <h1 class="text-xl font-bold text-gray-900">Solicitud de Viaje</h1>
            <p class="text-sm text-red-500">Expira en {{ timeRemaining }}s</p>
          </div>
        </div>
      </div>
    </header>

    <!-- Contenido -->
    <main class="max-w-7xl mx-auto px-4 py-6">
      <div v-if="loading" class="flex items-center justify-center h-64">
        <div class="text-center">
          <div class="text-6xl mb-4">⏳</div>
          <p class="text-gray-500">Cargando detalles del viaje...</p>
        </div>
      </div>

      <div v-else-if="error" class="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
        <div class="text-6xl mb-4">❌</div>
        <h3 class="text-xl font-semibold text-red-600 mb-2">Error</h3>
        <p class="text-red-500 mb-4">{{ error }}</p>
        <button
          @click="goBack"
          class="bg-gray-200 hover:bg-gray-300 text-gray-700 px-6 py-2 rounded-lg"
        >
          Volver al Dashboard
        </button>
      </div>

      <div v-else-if="ride" class="space-y-6">
        <!-- Información del cliente -->
        <div class="bg-white rounded-lg shadow-lg p-6">
          <h3 class="text-lg font-semibold text-gray-900 mb-4">Información del Cliente</h3>
          <div class="flex items-center space-x-4">
            <div class="w-16 h-16 bg-gray-200 rounded-full flex items-center justify-center text-3xl">
              👤
            </div>
            <div class="flex-1">
              <h4 class="text-xl font-semibold text-gray-900">{{ ride.customer.name }}</h4>
              <div class="flex items-center space-x-4 mt-1">
                <span class="text-sm text-gray-500">📱 {{ ride.customer.phone }}</span>
                <span class="text-sm text-yellow-500">⭐ {{ ride.customer.rating || 'N/A' }}</span>
              </div>
            </div>
            <a
              :href="`tel:${ride.customer.phone}`"
              class="bg-green-500 hover:bg-green-600 text-white px-4 py-2 rounded-lg"
            >
              📞 Llamar
            </a>
          </div>
        </div>

        <!-- Ruta del viaje -->
        <div class="bg-white rounded-lg shadow-lg p-6">
          <h3 class="text-lg font-semibold text-gray-900 mb-4">Ruta del Viaje</h3>

          <!-- Origen -->
          <div class="flex items-start space-x-3 mb-4 pb-4 border-b">
            <div class="flex-shrink-0 w-8 h-8 bg-green-100 rounded-full flex items-center justify-center">
              <span class="text-green-600 font-bold">A</span>
            </div>
            <div class="flex-1">
              <p class="text-sm text-gray-500 mb-1">Origen (Punto de Recogida)</p>
              <p class="text-gray-900 font-medium">{{ ride.origin.address }}</p>
              <div class="mt-2 flex items-center space-x-2">
                <a
                  :href="getGoogleMapsUrl(ride.origin.lat, ride.origin.lon)"
                  target="_blank"
                  class="text-sm text-blue-600 hover:underline"
                >
                  🗺️ Abrir en Google Maps
                </a>
              </div>
            </div>
          </div>

          <!-- Destino -->
          <div class="flex items-start space-x-3">
            <div class="flex-shrink-0 w-8 h-8 bg-red-100 rounded-full flex items-center justify-center">
              <span class="text-red-600 font-bold">B</span>
            </div>
            <div class="flex-1">
              <p class="text-sm text-gray-500 mb-1">Destino</p>
              <p class="text-gray-900 font-medium">{{ ride.destination.address }}</p>
              <div class="mt-2 flex items-center space-x-2">
                <a
                  :href="getGoogleMapsUrl(ride.destination.lat, ride.destination.lon)"
                  target="_blank"
                  class="text-sm text-blue-600 hover:underline"
                >
                  🗺️ Abrir en Google Maps
                </a>
              </div>
            </div>
          </div>

          <!-- Mapa Leaflet -->
          <div ref="mapContainer" class="mt-6 rounded-lg overflow-hidden" style="height:200px;z-index:0"></div>
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
              <p class="text-xl font-semibold text-gray-900">
                {{ ride.payment_method === 'cash' ? '💵 Efectivo' : '💳 Tarjeta' }}
              </p>
            </div>
          </div>

          <!-- Notas adicionales -->
          <div v-if="ride.notes" class="mt-4 bg-yellow-50 border border-yellow-200 rounded-lg p-4">
            <p class="text-sm text-gray-700">
              <strong>Notas del cliente:</strong> {{ ride.notes }}
            </p>
          </div>
        </div>

        <!-- Botones de acción -->
        <div class="sticky bottom-0 bg-white border-t shadow-lg p-4">
          <div class="max-w-7xl mx-auto flex space-x-4">
            <button
              @click="handleReject"
              :disabled="submitting"
              class="flex-1 bg-gray-200 hover:bg-gray-300 text-gray-700 font-semibold py-4 rounded-lg transition duration-200 disabled:opacity-50"
            >
              ✕ Rechazar
            </button>
            <button
              @click="handleAccept"
              :disabled="submitting"
              class="flex-1 bg-taxi-green hover:bg-green-600 text-white font-semibold py-4 rounded-lg transition duration-200 disabled:opacity-50 shadow-lg"
            >
              <span v-if="!submitting">✓ Aceptar Viaje</span>
              <span v-else>Aceptando...</span>
            </button>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useRideStore } from '../stores/rideStore'
import { useToast } from '../composables/useToast'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

const { error: toastError } = useToast()

const router = useRouter()
const route = useRoute()
const rideStore = useRideStore()

const ride = ref(null)
const loading = ref(true)
const error = ref(null)
const submitting = ref(false)
const timeRemaining = ref(30)
const countdownInterval = ref(null)
const mapContainer = ref(null)
let leafletMap = null

const rideId = computed(() => route.params.rideId)

const getGoogleMapsUrl = (lat, lon) => {
  return `https://www.google.com/maps/search/?api=1&query=${lat},${lon}`
}

const makeMarkerIcon = (label, color) => L.divIcon({
  html: `<div style="background:${color};color:white;width:28px;height:28px;border-radius:50% 50% 50% 0;transform:rotate(-45deg);display:flex;align-items:center;justify-content:center;font-weight:bold;font-size:13px;border:2px solid white;box-shadow:0 2px 6px rgba(0,0,0,.3)"><span style="transform:rotate(45deg)">${label}</span></div>`,
  className: '',
  iconSize: [28, 28],
  iconAnchor: [14, 28]
})

const initMap = async (rideData) => {
  await nextTick()
  if (!mapContainer.value) return

  const oLat = rideData.origin?.lat
  const oLng = rideData.origin?.lng ?? rideData.origin?.lon
  const dLat = rideData.destination?.lat
  const dLng = rideData.destination?.lng ?? rideData.destination?.lon

  const centerLat = oLat || 20.5888
  const centerLng = oLng || -100.3899

  leafletMap = L.map(mapContainer.value, { zoomControl: false })
    .setView([centerLat, centerLng], 14)

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap'
  }).addTo(leafletMap)

  L.control.zoom({ position: 'bottomright' }).addTo(leafletMap)

  const bounds = []

  if (oLat && oLng) {
    L.marker([oLat, oLng], { icon: makeMarkerIcon('A', '#22c55e') })
      .addTo(leafletMap)
      .bindPopup(`<b>Origen</b><br>${rideData.origin.address || ''}`)
    bounds.push([oLat, oLng])
  }

  if (dLat && dLng) {
    L.marker([dLat, dLng], { icon: makeMarkerIcon('B', '#ef4444') })
      .addTo(leafletMap)
      .bindPopup(`<b>Destino</b><br>${rideData.destination.address || ''}`)
    bounds.push([dLat, dLng])
  }

  if (oLat && oLng && dLat && dLng) {
    try {
      const resp = await fetch(
        `https://router.project-osrm.org/route/v1/driving/${oLng},${oLat};${dLng},${dLat}?overview=full&geometries=geojson`
      )
      const data = await resp.json()
      if (data.routes?.[0]) {
        L.geoJSON(data.routes[0].geometry, {
          style: { color: '#3b82f6', weight: 4, opacity: 0.85 }
        }).addTo(leafletMap)
      }
    } catch {
      L.polyline([[oLat, oLng], [dLat, dLng]], {
        color: '#3b82f6', weight: 3, dashArray: '8,8', opacity: 0.7
      }).addTo(leafletMap)
    }
  }

  if (bounds.length >= 2) {
    leafletMap.fitBounds(bounds, { padding: [30, 30] })
  } else if (bounds.length === 1) {
    leafletMap.setView(bounds[0], 15)
  }
}

const loadRideDetails = async () => {
  loading.value = true
  error.value = null

  try {
    const result = await rideStore.fetchRideDetails(rideId.value)
    if (result.success) {
      ride.value = result.ride
      startCountdown()
    } else {
      error.value = result.error
    }
  } catch (err) {
    error.value = 'Error al cargar detalles del viaje'
  } finally {
    loading.value = false
  }

  if (ride.value) {
    await initMap(ride.value)
  }
}

const startCountdown = () => {
  countdownInterval.value = setInterval(() => {
    timeRemaining.value--
    if (timeRemaining.value <= 0) {
      clearInterval(countdownInterval.value)
      error.value = 'La solicitud ha expirado'
      setTimeout(() => {
        goBack()
      }, 2000)
    }
  }, 1000)
}

const handleAccept = async () => {
  submitting.value = true
  const result = await rideStore.acceptRide(rideId.value)

  if (result.success) {
    router.push(`/active-ride/${rideId.value}`)
  } else {
    toastError(result.error || 'Error al aceptar el viaje')
    submitting.value = false
  }
}

const handleReject = async () => {
  if (confirm('¿Estás seguro de rechazar este viaje?')) {
    submitting.value = true
    const result = await rideStore.rejectRide(rideId.value, 'No disponible')

    if (result.success) {
      router.push('/dashboard')
    } else {
      toastError(result.error || 'Error al rechazar el viaje')
      submitting.value = false
    }
  }
}

const goBack = () => {
  router.push('/dashboard')
}

onMounted(() => {
  loadRideDetails()
})

onUnmounted(() => {
  if (countdownInterval.value) {
    clearInterval(countdownInterval.value)
  }
  if (leafletMap) {
    leafletMap.remove()
    leafletMap = null
  }
})
</script>
