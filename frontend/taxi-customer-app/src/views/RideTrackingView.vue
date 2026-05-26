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
          <!-- Botón SOS -->
          <button
            v-if="rideStatus && rideStatus !== 'completed' && rideStatus !== 'cancelled'"
            @click="showPanicModal = true"
            :class="[
              'px-3 py-1.5 rounded-lg font-bold text-sm transition',
              panicSent
                ? 'bg-red-600 text-white animate-pulse'
                : 'bg-red-500 hover:bg-red-600 text-white'
            ]"
          >
            🚨 SOS
          </button>
          <div v-else class="w-10"></div>
        </div>
      </div>
    </header>

    <!-- Banner alerta activa -->
    <div v-if="panicSent" class="bg-red-600 text-white px-4 py-3 text-center">
      <p class="font-bold text-sm">🚨 ALERTA ENVIADA — Ayuda en camino — {{ panicTime }}</p>
      <p v-if="panicTrackingUrl" class="text-xs mt-1 opacity-90">
        Comparte tu rastreo:
        <button @click="copyTracking" class="underline font-semibold">Copiar link</button>
      </p>
    </div>

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

    <!-- Pantalla de espera de pago con MercadoPago -->
    <div v-else-if="ride && ride.payment_method === 'card' && paymentPending" class="flex-1 flex flex-col items-center justify-center p-8 text-center">
      <div class="text-7xl mb-5 animate-pulse">💳</div>
      <h2 class="text-2xl font-bold text-gray-900 mb-2">Esperando confirmación de pago</h2>
      <p class="text-gray-500 mb-6">Verifica tu pago en MercadoPago.<br>Esta pantalla se actualizará automáticamente.</p>
      <div class="flex justify-center space-x-1 mb-8">
        <div class="w-2.5 h-2.5 bg-blue-500 rounded-full animate-bounce"></div>
        <div class="w-2.5 h-2.5 bg-blue-500 rounded-full animate-bounce" style="animation-delay:0.15s"></div>
        <div class="w-2.5 h-2.5 bg-blue-500 rounded-full animate-bounce" style="animation-delay:0.3s"></div>
      </div>
      <div class="bg-blue-50 border border-blue-200 rounded-xl p-4 w-full max-w-sm mb-6">
        <p class="text-sm text-gray-600 mb-1">Viaje <span class="font-mono font-bold">{{ ride.ride_id }}</span></p>
        <p class="text-2xl font-bold text-blue-600">${{ ride.total_fare }} MXN</p>
        <p class="text-xs text-gray-500 mt-1">{{ ride.destination?.address }}</p>
      </div>
      <button
        @click="retryPayment"
        :disabled="retryingPayment"
        class="w-full max-w-sm py-3 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-semibold rounded-xl mb-3 transition"
      >
        {{ retryingPayment ? 'Generando link...' : '🔗 Volver a MercadoPago' }}
      </button>
      <button @click="goBack" class="text-sm text-gray-400 hover:text-gray-600">
        Cancelar viaje
      </button>
    </div>

    <!-- Pago fallido -->
    <div v-else-if="ride && ride.payment_status === 'failed'" class="flex-1 flex flex-col items-center justify-center p-8 text-center">
      <div class="text-7xl mb-5">❌</div>
      <h2 class="text-2xl font-bold text-gray-900 mb-2">Pago no procesado</h2>
      <p class="text-gray-500 mb-6">El pago fue rechazado o cancelado.</p>
      <button @click="goBack" class="w-full max-w-sm py-3 bg-taxi-yellow text-white font-semibold rounded-xl">
        Solicitar nuevo viaje
      </button>
    </div>

    <!-- Main Content -->
    <div v-else-if="ride" class="flex-1 flex flex-col min-h-0">
      <!-- Map Area -->
      <div class="flex-1 relative min-h-0">
        <div ref="mapContainer" class="absolute inset-0" style="z-index:0"></div>

        <!-- Status Badge overlay -->
        <div class="absolute top-4 left-4 right-4" style="z-index:800">
          <div :class="[
            'px-4 py-2 rounded-full text-white font-semibold text-center shadow-lg',
            getStatusColorClass(rideStatus)
          ]">
            {{ getStatusLabel(rideStatus) }}
          </div>
        </div>

        <!-- Searching spinner overlay -->
        <div v-if="rideStatus === 'requested'" class="absolute inset-0 flex items-center justify-center" style="z-index:800">
          <div class="bg-white bg-opacity-90 rounded-2xl p-6 text-center shadow-xl">
            <div class="text-5xl mb-3 animate-pulse">🔍</div>
            <p class="font-bold text-gray-900">Buscando conductor...</p>
            <div class="flex justify-center space-x-1 mt-2">
              <div class="w-2 h-2 bg-taxi-yellow rounded-full animate-bounce"></div>
              <div class="w-2 h-2 bg-taxi-yellow rounded-full animate-bounce" style="animation-delay:0.1s"></div>
              <div class="w-2 h-2 bg-taxi-yellow rounded-full animate-bounce" style="animation-delay:0.2s"></div>
            </div>
          </div>
        </div>
      </div>

      <!-- Info Card -->
      <div class="bg-white rounded-t-3xl shadow-2xl p-6 max-h-[50vh] overflow-y-auto" style="z-index:10">
        <!-- Driver Assigned -->
        <div v-if="ride.driver">
          <!-- Driver Info -->
          <div class="mb-4">
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
          <div v-if="rideStatus === 'assigned' || rideStatus === 'driver_arriving'" class="mb-4 bg-blue-50 border border-blue-200 rounded-lg p-4">
            <div class="flex items-center justify-between">
              <div>
                <p class="text-sm text-gray-600">Tiempo estimado de llegada</p>
                <p class="text-3xl font-bold text-blue-600">{{ estimatedArrivalTime }} min</p>
              </div>
              <div class="text-4xl">🚗💨</div>
            </div>
          </div>
        </div>

        <!-- Route Info -->
        <div class="mb-4">
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
        <div class="mb-4 bg-green-50 border border-green-200 rounded-lg p-4">
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

    <!-- Modal Pánico -->
    <div
      v-if="showPanicModal"
      class="fixed inset-0 bg-black bg-opacity-70 flex items-center justify-center z-50 p-4"
    >
      <div class="bg-white rounded-2xl shadow-2xl max-w-sm w-full overflow-hidden">
        <div class="bg-red-600 p-6 text-white text-center">
          <div class="text-6xl mb-2">🚨</div>
          <h2 class="text-2xl font-black">EMERGENCIA</h2>
          <p class="text-red-100 text-sm mt-1">¿Confirmas que necesitas ayuda ahora?</p>
        </div>
        <div class="p-5 space-y-3">
          <button
            @click="triggerPanic"
            :disabled="sendingPanic"
            class="w-full bg-red-600 hover:bg-red-700 text-white font-black py-4 rounded-xl text-lg disabled:opacity-50 shadow-lg"
          >
            {{ sendingPanic ? 'Enviando alerta...' : '📞 SÍ, LLAMAR AHORA' }}
          </button>
          <button
            @click="showPanicModal = false"
            class="w-full bg-gray-100 hover:bg-gray-200 text-gray-700 font-semibold py-3 rounded-xl"
          >
            Cancelar — Estoy bien
          </button>
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
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useRideStore } from '../stores/rideStore'
import { ridesApi, paymentApi } from '../services/api'
import { useToast } from '../composables/useToast'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

const { success: toastSuccess, error: toastError } = useToast()

const router = useRouter()
const route = useRoute()
const rideStore = useRideStore()

const ride = ref(null)
const loading = ref(true)
const error = ref(null)
const showCancelDialog = ref(false)
const showPanicModal = ref(false)
const sendingPanic = ref(false)
const panicSent = ref(false)
const panicTime = ref('')
const panicIncidentId = ref(null)
const panicTrackingUrl = ref(null)
const cancelReason = ref('')

let gpsWatchId = null
let mediaRecorder = null
let audioChunks = []
const cancelling = ref(false)
const rating = ref(0)
const ratingComment = ref('')
const rated = ref(false)
const mapContainer = ref(null)
const retryingPayment = ref(false)

const paymentPending = computed(() => ride.value?.payment_status === 'pending_payment')

let leafletMap = null
let driverMarker = null
let routeLayer = null
let paymentPollInterval = null

const rideId = computed(() => route.params.rideId)
const rideStatus = computed(() => ride.value?.status || null)
const estimatedArrivalTime = ref(Math.floor(Math.random() * 10) + 5)

const getStatusLabel = (status) => {
  const labels = {
    requested: 'Buscando conductor...',
    assigned: 'Conductor asignado',
    confirmed: 'Conductor confirmado',
    driver_arriving: 'Conductor en camino',
    driver_arrived: '¡Tu conductor llegó!',
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
    confirmed: 'bg-yellow-500',
    driver_arriving: 'bg-orange-500',
    driver_arrived: 'bg-green-600',
    started: 'bg-green-500',
    in_progress: 'bg-green-500',
    completed: 'bg-gray-500',
    cancelled: 'bg-red-500'
  }
  return colors[status] || 'bg-gray-500'
}

const makeMarkerIcon = (label, color) => L.divIcon({
  html: `<div style="background:${color};color:white;width:30px;height:30px;border-radius:50% 50% 50% 0;transform:rotate(-45deg);display:flex;align-items:center;justify-content:center;font-weight:bold;font-size:14px;border:2px solid white;box-shadow:0 2px 6px rgba(0,0,0,.35)"><span style="transform:rotate(45deg)">${label}</span></div>`,
  className: '',
  iconSize: [30, 30],
  iconAnchor: [15, 30]
})

const makeTaxiIcon = () => L.divIcon({
  html: '<div style="font-size:30px;filter:drop-shadow(0 2px 4px rgba(0,0,0,.5));line-height:1">🚕</div>',
  className: '',
  iconSize: [34, 34],
  iconAnchor: [17, 17]
})

const initMap = async (rideData) => {
  await nextTick()
  if (!mapContainer.value) return

  if (leafletMap) {
    leafletMap.remove()
    leafletMap = null
    driverMarker = null
    routeLayer = null
  }

  const oLat = rideData.origin?.lat
  const oLng = rideData.origin?.lng
  const dLat = rideData.destination?.lat
  const dLng = rideData.destination?.lng

  const centerLat = oLat || 20.5888
  const centerLng = oLng || -100.3899

  leafletMap = L.map(mapContainer.value, { zoomControl: false }).setView([centerLat, centerLng], 14)

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
      const osrmUrl = `https://router.project-osrm.org/route/v1/driving/${oLng},${oLat};${dLng},${dLat}?overview=full&geometries=geojson`
      const resp = await fetch(osrmUrl)
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
  }

  const driverLat = rideData.driver?.current_lat
  const driverLon = rideData.driver?.current_lon
  if (driverLat && driverLon) {
    driverMarker = L.marker([driverLat, driverLon], { icon: makeTaxiIcon() })
      .addTo(leafletMap)
      .bindPopup(`<b>${rideData.driver.name}</b>`)
    bounds.push([driverLat, driverLon])
  }

  if (bounds.length >= 2) {
    leafletMap.fitBounds(bounds, { padding: [50, 50] })
  } else if (bounds.length === 1) {
    leafletMap.setView(bounds[0], 15)
  }
}

const updateDriverMarker = (lat, lon) => {
  if (!leafletMap || !lat || !lon) return
  if (driverMarker) {
    driverMarker.setLatLng([lat, lon])
  } else {
    driverMarker = L.marker([lat, lon], { icon: makeTaxiIcon() })
      .addTo(leafletMap)
      .bindPopup(ride.value?.driver?.name || 'Conductor')
  }
}

watch(() => rideStore.activeRide, (newRide) => {
  if (!newRide) return
  ride.value = newRide
  const lat = newRide.driver?.current_lat
  const lon = newRide.driver?.current_lon
  if (lat && lon) updateDriverMarker(lat, lon)
}, { deep: true })

const loadRideDetails = async () => {
  loading.value = true
  error.value = null

  try {
    const result = await rideStore.fetchRideDetails(rideId.value)
    if (result.success) {
      ride.value = result.ride
      rideStore.activeRide = result.ride
    } else {
      error.value = result.error
    }
  } catch (err) {
    error.value = 'Error al cargar el viaje'
  } finally {
    loading.value = false
  }

  if (ride.value) {
    await initMap(ride.value)
    const trackable = ['requested', 'assigned', 'confirmed', 'driver_arriving', 'driver_arrived', 'started', 'in_progress']
    if (trackable.includes(ride.value.status)) {
      rideStore.startTracking()
    }
  }
}

const cancelRide = async () => {
  cancelling.value = true
  try {
    const result = await rideStore.cancelRide(rideId.value, cancelReason.value || 'Cliente canceló')
    if (result.success) {
      toastSuccess('Viaje cancelado exitosamente')
      router.push('/home')
    } else {
      toastError(result.error || 'Error al cancelar')
    }
  } catch (err) {
    toastError('Error de conexión')
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
      toastSuccess('¡Gracias por tu calificación!')
    } else {
      toastError(result.error || 'Error al calificar')
    }
  } catch (err) {
    toastError('Error de conexión')
  }
}

const triggerPanic = async () => {
  sendingPanic.value = true
  try {
    let lat = null, lng = null
    try {
      const pos = await new Promise((resolve, reject) =>
        navigator.geolocation.getCurrentPosition(resolve, reject, { timeout: 3000 })
      )
      lat = pos.coords.latitude
      lng = pos.coords.longitude
    } catch (_) { /* GPS no disponible */ }

    const result = await ridesApi.reportIncident({
      trip_id: ride.value?.ride_id || null,
      lat, lng,
      notes: 'Pánico activado desde app del cliente',
    })

    panicSent.value = true
    panicTime.value = new Date().toLocaleTimeString('es-MX')
    panicIncidentId.value = result.incident_id || null
    panicTrackingUrl.value = result.tracking_url || null
    showPanicModal.value = false

    // Iniciar GPS en vivo cada 15s
    _startGpsTracking(result.incident_id)

    // Grabar audio 30s y subir
    _startAudioRecording(result.incident_id)

    window.open(`tel:${result.emergency_phone || '911'}`)
  } catch (err) {
    window.open('tel:911')
    panicSent.value = true
    panicTime.value = new Date().toLocaleTimeString('es-MX')
    showPanicModal.value = false
  } finally {
    sendingPanic.value = false
  }
}

const _startGpsTracking = (incidentId) => {
  if (!incidentId || !navigator.geolocation) return
  gpsWatchId = navigator.geolocation.watchPosition(
    async (pos) => {
      try {
        await ridesApi.updateIncidentLocation(incidentId, {
          lat: pos.coords.latitude,
          lng: pos.coords.longitude,
        })
      } catch (_) { /* best-effort */ }
    },
    () => {},
    { enableHighAccuracy: true, maximumAge: 10000, timeout: 8000 }
  )
}

const _startAudioRecording = async (incidentId) => {
  if (!incidentId || !navigator.mediaDevices?.getUserMedia) return
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    audioChunks = []
    mediaRecorder = new MediaRecorder(stream)
    mediaRecorder.ondataavailable = (e) => { if (e.data.size > 0) audioChunks.push(e.data) }
    mediaRecorder.onstop = async () => {
      stream.getTracks().forEach(t => t.stop())
      const blob = new Blob(audioChunks, { type: 'audio/webm' })
      const formData = new FormData()
      formData.append('file', blob, `${incidentId}.webm`)
      try {
        await ridesApi.uploadIncidentAudio(incidentId, formData)
      } catch (_) { /* best-effort */ }
    }
    mediaRecorder.start()
    setTimeout(() => { if (mediaRecorder?.state === 'recording') mediaRecorder.stop() }, 30000)
  } catch (_) { /* sin micrófono o permiso denegado */ }
}

const retryPayment = async () => {
  retryingPayment.value = true
  try {
    const pref = await paymentApi.createMPPreference(rideId.value)
    sessionStorage.setItem('pending_mp_trip', rideId.value)
    window.location.href = pref.init_point
  } catch {
    toastError('No se pudo generar el link de pago. Intenta de nuevo.')
  } finally {
    retryingPayment.value = false
  }
}

const startPaymentPolling = () => {
  if (paymentPollInterval) return
  paymentPollInterval = setInterval(async () => {
    try {
      const data = await paymentApi.getPaymentStatus(rideId.value)
      if (data.payment_status && data.payment_status !== 'pending_payment') {
        ride.value = { ...ride.value, payment_status: data.payment_status }
        clearInterval(paymentPollInterval)
        paymentPollInterval = null
        if (data.payment_status === 'approved') {
          toastSuccess('¡Pago confirmado!')
        }
      }
    } catch { /* ignorar errores de red en polling */ }
  }, 3000)
}

const copyTracking = async () => {
  if (!panicTrackingUrl.value) return
  try {
    await navigator.clipboard.writeText(panicTrackingUrl.value)
    toastSuccess('Link copiado — compártelo con alguien de confianza')
  } catch (_) {
    toastError('No se pudo copiar')
  }
}

const goBack = () => router.push('/home')
const goHome = () => router.push('/home')

onMounted(async () => {
  await loadRideDetails()
  if (ride.value?.payment_method === 'card' && ride.value?.payment_status === 'pending_payment') {
    startPaymentPolling()
  }
})

onUnmounted(() => {
  rideStore.stopTracking()
  if (paymentPollInterval) {
    clearInterval(paymentPollInterval)
    paymentPollInterval = null
  }
  if (leafletMap) {
    leafletMap.remove()
    leafletMap = null
  }
  if (gpsWatchId !== null) {
    navigator.geolocation.clearWatch(gpsWatchId)
    gpsWatchId = null
  }
  if (mediaRecorder?.state === 'recording') {
    mediaRecorder.stop()
  }
})
</script>
