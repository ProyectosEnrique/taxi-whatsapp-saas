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
          <div class="flex items-center space-x-3">
            <div class="text-2xl font-bold text-green-600">
              ${{ ride?.total_fare || '0.00' }}
            </div>
            <button
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
          </div>
        </div>
      </div>
    </header>

    <!-- Banner alerta activa -->
    <div v-if="panicSent" class="bg-red-600 text-white px-4 py-2 text-center text-sm font-semibold">
      🚨 ALERTA ENVIADA — {{ panicTime }} — Ayuda en camino
    </div>

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

          <!-- Mapa Leaflet (OpenStreetMap) -->
          <div ref="mapContainer" class="mt-6 rounded-lg overflow-hidden" style="height:280px;z-index:0"></div>
          <div class="mt-3 flex space-x-2">
            <button
              @click="openGoogleMaps"
              class="flex-1 bg-blue-600 hover:bg-blue-700 text-white px-3 py-2 rounded-lg text-sm font-medium"
            >
              🗺️ Google Maps
            </button>
            <button
              @click="openWaze"
              class="flex-1 bg-cyan-600 hover:bg-cyan-700 text-white px-3 py-2 rounded-lg text-sm font-medium"
            >
              🔵 Waze
            </button>
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
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useRideStore } from '../stores/rideStore'
import { useDriverStore } from '../stores/driverStore'
import { ridesApi } from '../services/api'
import { useToast } from '../composables/useToast'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

const { success: toastSuccess, error: toastError } = useToast()

const router = useRouter()
const route = useRoute()
const rideStore = useRideStore()
const driverStore = useDriverStore()

const ride = ref(null)
const loading = ref(true)
const error = ref(null)
const submitting = ref(false)
const showCancelDialog = ref(false)
const cancelReason = ref('')
const elapsedTime = ref('00:00:00')
const timerInterval = ref(null)
const startTime = ref(null)
const mapContainer = ref(null)
let leafletMap = null
let driverMarker = null
const showPanicModal = ref(false)
const sendingPanic = ref(false)
const panicSent = ref(false)
const panicTime = ref('')
const panicTrackingUrl = ref(null)

let gpsWatchId = null
let mediaRecorder = null
let audioChunks = []

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

const initMap = async (rideData) => {
  await nextTick()
  if (!mapContainer.value || !rideData) return

  if (leafletMap) {
    leafletMap.remove()
    leafletMap = null
    driverMarker = null
  }

  // Convert 0/null to null so falsy checks below work correctly
  const oLat = rideData.origin?.lat || null
  const oLng = rideData.origin?.lng || null
  const dLat = rideData.destination?.lat || null
  const dLng = rideData.destination?.lng || null

  // Always create the map — use available coords or city fallback as center
  const centerLat = oLat ?? dLat ?? 20.5236
  const centerLng = oLng ?? dLng ?? -100.8198

  leafletMap = L.map(mapContainer.value).setView([centerLat, centerLng], 13)

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap contributors',
    maxZoom: 19,
  }).addTo(leafletMap)

  const iconA = L.divIcon({
    html: '<div style="background:#22c55e;color:#fff;width:28px;height:28px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:bold;font-size:14px;border:2px solid #fff;box-shadow:0 2px 4px rgba(0,0,0,.4)">A</div>',
    className: '',
    iconSize: [28, 28],
    iconAnchor: [14, 14],
  })
  const iconB = L.divIcon({
    html: '<div style="background:#ef4444;color:#fff;width:28px;height:28px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:bold;font-size:14px;border:2px solid #fff;box-shadow:0 2px 4px rgba(0,0,0,.4)">B</div>',
    className: '',
    iconSize: [28, 28],
    iconAnchor: [14, 14],
  })

  const bounds = []
  if (oLat && oLng) {
    L.marker([oLat, oLng], { icon: iconA }).addTo(leafletMap)
      .bindPopup(`<b>Origen</b><br>${rideData.origin.address}`)
    bounds.push([oLat, oLng])
  }
  if (dLat && dLng) {
    L.marker([dLat, dLng], { icon: iconB }).addTo(leafletMap)
      .bindPopup(`<b>Destino</b><br>${rideData.destination.address}`)
    bounds.push([dLat, dLng])
  }

  if (bounds.length >= 2) {
    leafletMap.fitBounds(bounds, { padding: [40, 40] })
  } else if (bounds.length === 1) {
    leafletMap.setView(bounds[0], 15)
  }

  if (oLat && oLng && dLat && dLng) {
    // Intentar ruta real con OSRM, fallback a línea recta
    try {
      const res = await fetch(
        `https://router.project-osrm.org/route/v1/driving/${oLng},${oLat};${dLng},${dLat}?overview=full&geometries=geojson`
      )
      if (res.ok) {
        const data = await res.json()
        const coords = data.routes[0].geometry.coordinates.map(([lng, lat]) => [lat, lng])
        L.polyline(coords, { color: '#3b82f6', weight: 4, opacity: 0.8 }).addTo(leafletMap)
        return
      }
    } catch (_) { /* OSRM no disponible, usar línea recta */ }

    L.polyline([[oLat, oLng], [dLat, dLng]], {
      color: '#3b82f6', weight: 3, opacity: 0.6, dashArray: '8,6'
    }).addTo(leafletMap)
  }
}

const updateDriverMarker = (lat, lon) => {
  if (!leafletMap || lat == null || lon == null) return
  const pos = [lat, lon]
  if (driverMarker) {
    driverMarker.setLatLng(pos)
  } else {
    const icon = L.divIcon({
      html: '<span style="font-size:32px;line-height:1">🚕</span>',
      iconSize: [32, 32],
      iconAnchor: [16, 16],
      className: '',
    })
    driverMarker = L.marker(pos, { icon })
      .bindPopup('<b>Tu posición actual</b>')
      .addTo(leafletMap)
  }
}

watch(() => driverStore.location, (loc) => {
  if (loc?.lat != null && loc?.lon != null) updateDriverMarker(loc.lat, loc.lon)
}, { deep: true })

const loadRideDetails = async () => {
  loading.value = true
  error.value = null

  try {
    const result = await rideStore.fetchRideDetails(rideId.value)
    if (result.success) {
      ride.value = result.ride

      if (ride.value.status === 'started' || ride.value.status === 'in_progress') {
        startTimer()
      }

      initMap(ride.value)
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
    toastError(result.error || 'Error al iniciar el viaje')
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
    toastSuccess('¡Viaje completado exitosamente!')
    router.push('/dashboard')
  } else {
    toastError(result.error || 'Error al completar el viaje')
    submitting.value = false
  }
}

const handleCancelRide = async () => {
  submitting.value = true
  const result = await rideStore.cancelRide(rideId.value, cancelReason.value)

  if (result.success) {
    toastSuccess('Viaje cancelado')
    router.push('/dashboard')
  } else {
    toastError(result.error || 'Error al cancelar el viaje')
    submitting.value = false
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
      notes: 'Pánico activado desde app del conductor',
    }, 'driver')

    panicSent.value = true
    panicTime.value = new Date().toLocaleTimeString('es-MX')
    panicTrackingUrl.value = result.tracking_url || null
    showPanicModal.value = false

    _startGpsTracking(result.incident_id)
    _startAudioRecording(result.incident_id)

    window.open(`tel:${result.emergency_phone || '911'}`)
  } catch (_) {
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
        }, 'driver')
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
        await ridesApi.uploadIncidentAudio(incidentId, formData, 'driver')
      } catch (_) { /* best-effort */ }
    }
    mediaRecorder.start()
    setTimeout(() => { if (mediaRecorder?.state === 'recording') mediaRecorder.stop() }, 30000)
  } catch (_) { /* sin micrófono */ }
}

const navigateToOrigin = () => {
  const { lat, lng, address } = ride.value.origin
  const dest = (lat && lng) ? `${lat},${lng}` : encodeURIComponent(address)
  window.open(`https://www.google.com/maps/dir/?api=1&destination=${dest}&travelmode=driving`, '_blank')
}

const navigateToDestination = () => {
  const { lat, lng, address } = ride.value.destination
  const dest = (lat && lng) ? `${lat},${lng}` : encodeURIComponent(address)
  window.open(`https://www.google.com/maps/dir/?api=1&destination=${dest}&travelmode=driving`, '_blank')
}

const openGoogleMaps = () => {
  const o = ride.value.origin, d = ride.value.destination
  const origin = (o.lat && o.lng) ? `${o.lat},${o.lng}` : encodeURIComponent(o.address)
  const destination = (d.lat && d.lng) ? `${d.lat},${d.lng}` : encodeURIComponent(d.address)
  window.open(`https://www.google.com/maps/dir/?api=1&origin=${origin}&destination=${destination}&travelmode=driving`, '_blank')
}

const openWaze = () => {
  const { lat, lng, address } = ride.value.destination
  const wazeUrl = (lat && lng)
    ? `https://waze.com/ul?ll=${lat},${lng}&navigate=yes`
    : `https://waze.com/ul?q=${encodeURIComponent(address)}&navigate=yes`
  window.open(wazeUrl, '_blank')
}

onMounted(() => {
  loadRideDetails()
  // Asegurar GPS activo durante el viaje aunque el conductor venga de otra ruta
  driverStore.startLocationTracking()
})

onUnmounted(() => {
  if (timerInterval.value) {
    clearInterval(timerInterval.value)
  }
  if (leafletMap) {
    leafletMap.remove()
    leafletMap = null
    driverMarker = null
  }
})
</script>
