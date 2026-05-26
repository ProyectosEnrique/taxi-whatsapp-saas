<template>
  <div class="min-h-screen bg-red-50 flex flex-col">
    <!-- Header -->
    <header class="bg-red-600 text-white px-4 py-4 shadow-lg">
      <div class="max-w-2xl mx-auto flex items-center space-x-3">
        <span class="text-3xl animate-pulse">🚨</span>
        <div>
          <h1 class="text-xl font-bold">ALERTA DE EMERGENCIA</h1>
          <p class="text-sm opacity-90">Rastreo en tiempo real</p>
        </div>
      </div>
    </header>

    <!-- Loading -->
    <div v-if="loading" class="flex-1 flex items-center justify-center">
      <div class="text-center">
        <div class="text-5xl mb-4 animate-spin">📡</div>
        <p class="text-gray-600">Cargando ubicación...</p>
      </div>
    </div>

    <!-- Error -->
    <div v-else-if="error" class="flex-1 flex items-center justify-center p-6">
      <div class="text-center bg-white rounded-xl shadow p-8 max-w-md w-full">
        <div class="text-5xl mb-4">❌</div>
        <p class="text-red-600 font-semibold">{{ error }}</p>
      </div>
    </div>

    <!-- Contenido -->
    <div v-else class="flex-1 flex flex-col max-w-2xl mx-auto w-full">

      <!-- Info de la persona -->
      <div class="bg-white mx-4 mt-4 rounded-xl shadow p-5 border-l-4 border-red-500">
        <div class="flex items-center space-x-4">
          <div class="w-14 h-14 bg-red-100 rounded-full flex items-center justify-center text-2xl">
            {{ incident.reporter_type === 'driver' ? '🚕' : '👤' }}
          </div>
          <div>
            <p class="text-xl font-bold text-gray-900">{{ incident.reporter_name }}</p>
            <p class="text-sm text-gray-500">
              {{ incident.reporter_type === 'driver' ? 'Conductor' : 'Pasajero' }}
              {{ incident.trip_id ? `· Viaje ${incident.trip_id}` : '' }}
            </p>
            <p class="text-xs text-gray-400 mt-1">Alerta activada: {{ formatTime(incident.created_at) }}</p>
          </div>
        </div>

        <div class="mt-4 flex items-center justify-between">
          <span :class="incident.status === 'active' ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'"
                class="px-3 py-1 rounded-full text-sm font-semibold">
            {{ incident.status === 'active' ? '🔴 ALERTA ACTIVA' : '✅ Resuelto' }}
          </span>
          <span class="text-xs text-gray-400">Actualizado: {{ formatTime(incident.updated_at) || 'Sin actualización' }}</span>
        </div>
      </div>

      <!-- Mapa -->
      <div class="mx-4 mt-4 rounded-xl overflow-hidden shadow" style="height: 320px;">
        <div ref="mapContainer" class="w-full h-full"></div>
      </div>

      <!-- Coordenadas + botones -->
      <div class="mx-4 mt-4 bg-white rounded-xl shadow p-4">
        <div v-if="incident.lat" class="mb-4">
          <p class="text-sm text-gray-500 mb-1">Última ubicación conocida</p>
          <p class="font-mono text-sm text-gray-700">{{ incident.lat?.toFixed(6) }}, {{ incident.lng?.toFixed(6) }}</p>
        </div>
        <div class="flex space-x-3">
          <a
            v-if="incident.lat"
            :href="`https://maps.google.com/?q=${incident.lat},${incident.lng}`"
            target="_blank"
            class="flex-1 bg-blue-600 text-white text-center py-3 rounded-lg font-semibold hover:bg-blue-700"
          >
            📍 Abrir en Maps
          </a>
          <a
            :href="`tel:${incident.emergency_phone || '911'}`"
            class="flex-1 bg-red-600 text-white text-center py-3 rounded-lg font-semibold hover:bg-red-700"
          >
            📞 Llamar al {{ incident.emergency_phone || '911' }}
          </a>
        </div>

        <!-- Audio si existe -->
        <div v-if="incident.audio_url" class="mt-4 p-3 bg-gray-50 rounded-lg">
          <p class="text-sm text-gray-600 mb-2 font-medium">🎙️ Audio grabado al activar SOS</p>
          <audio :src="incident.audio_url" controls class="w-full"></audio>
        </div>
      </div>

      <!-- Nota de actualización -->
      <p class="text-center text-xs text-gray-400 mt-4 mb-6">
        Esta página se actualiza automáticamente cada 15 segundos.
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const mapContainer = ref(null)
const loading = ref(true)
const error = ref(null)
const incident = ref(null)

let leafletMap = null
let marker = null
let originMarker = null
let pollInterval = null

const API_BASE = import.meta.env.VITE_API_URL || ''

const formatTime = (iso) => {
  if (!iso) return null
  return new Date(iso).toLocaleTimeString('es-MX', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

const initMap = async (data) => {
  if (!mapContainer.value) return
  if (typeof window.L === 'undefined') {
    // Cargar Leaflet dinámicamente
    await loadLeaflet()
  }
  const L = window.L
  const lat = data.lat || data.origin_lat || 20.5888
  const lng = data.lng || data.origin_lng || -100.3899

  if (!leafletMap) {
    leafletMap = L.map(mapContainer.value).setView([lat, lng], 15)
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '© OpenStreetMap'
    }).addTo(leafletMap)

    if (data.origin_lat && data.origin_lng) {
      originMarker = L.marker([data.origin_lat, data.origin_lng], {
        icon: L.divIcon({
          html: '<div style="background:#ef4444;color:white;width:34px;height:34px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:18px;border:3px solid white;box-shadow:0 2px 8px rgba(0,0,0,.4)">📍</div>',
          className: '', iconSize: [34, 34], iconAnchor: [17, 17]
        })
      }).addTo(leafletMap).bindPopup('<b>Ubicación al activar SOS</b>')
    }
  }

  if (data.lat && data.lng) {
    const pulseIcon = L.divIcon({
      html: '<div style="background:#dc2626;width:20px;height:20px;border-radius:50%;border:3px solid white;box-shadow:0 0 0 6px rgba(220,38,38,0.3);animation:pulse 1.5s infinite"></div>',
      className: '', iconSize: [20, 20], iconAnchor: [10, 10]
    })
    if (!marker) {
      marker = L.marker([data.lat, data.lng], { icon: pulseIcon })
        .addTo(leafletMap)
        .bindPopup(`<b>${data.reporter_name}</b><br>Última ubicación`)
    } else {
      marker.setLatLng([data.lat, data.lng])
    }
    leafletMap.setView([data.lat, data.lng], 15)
  }
}

const loadLeaflet = () => new Promise((resolve) => {
  if (window.L) { resolve(); return }
  const link = document.createElement('link')
  link.rel = 'stylesheet'
  link.href = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css'
  document.head.appendChild(link)
  const script = document.createElement('script')
  script.src = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js'
  script.onload = resolve
  document.head.appendChild(script)
})

const fetchIncident = async () => {
  const id = route.params.incidentId
  try {
    const resp = await fetch(`${API_BASE}/api/v1/incidents/${id}/track`)
    if (!resp.ok) throw new Error('No encontrado')
    const data = await resp.json()
    incident.value = data
    await initMap(data)
  } catch (e) {
    error.value = 'No se encontró la alerta o el link expiró.'
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  await fetchIncident()
  pollInterval = setInterval(fetchIncident, 15000)
})

onUnmounted(() => {
  if (pollInterval) clearInterval(pollInterval)
  if (leafletMap) { leafletMap.remove(); leafletMap = null }
})
</script>

<style scoped>
@keyframes pulse {
  0%, 100% { box-shadow: 0 0 0 6px rgba(220,38,38,0.3); }
  50%       { box-shadow: 0 0 0 12px rgba(220,38,38,0.1); }
}
</style>
