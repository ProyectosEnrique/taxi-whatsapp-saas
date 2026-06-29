<template>
  <div class="track-public">
    <!-- Header -->
    <div class="track-header">
      <span class="track-logo">🚕</span>
      <span class="track-title">Seguimiento de Viaje</span>
    </div>

    <!-- Error -->
    <div v-if="error" class="track-error">
      <p>{{ error }}</p>
      <a href="/" class="btn-link">Ir al inicio</a>
    </div>

    <!-- Loading -->
    <div v-else-if="!ride" class="track-loading">
      <div class="spinner"></div>
      <p>Cargando información del viaje...</p>
    </div>

    <!-- Content -->
    <div v-else class="track-content">
      <!-- Status badge -->
      <div class="status-badge" :class="statusClass">
        <span>{{ statusIcon }} {{ statusLabel }}</span>
      </div>

      <!-- Map -->
      <div id="public-map" class="track-map"></div>

      <!-- Driver card -->
      <div v-if="ride.driver" class="info-card driver-card">
        <div class="card-icon">👤</div>
        <div class="card-body">
          <p class="card-name">{{ ride.driver.name }}</p>
          <p class="card-sub">{{ ride.driver.vehicle }}</p>
          <p class="card-plates">Placas: <strong>{{ ride.driver.plates }}</strong></p>
        </div>
      </div>
      <div v-else-if="!isFinished" class="info-card">
        <div class="card-body">
          <p class="card-sub">Buscando conductor disponible...</p>
        </div>
      </div>

      <!-- Route card -->
      <div class="info-card route-card">
        <div class="route-row">
          <span class="route-dot origin-dot"></span>
          <div class="route-text">
            <p class="route-label">Origen</p>
            <p>{{ ride.origin.address || 'Punto de recogida' }}</p>
          </div>
        </div>
        <div class="route-line"></div>
        <div class="route-row">
          <span class="route-dot dest-dot"></span>
          <div class="route-text">
            <p class="route-label">Destino</p>
            <p>{{ ride.destination.address }}</p>
          </div>
        </div>
        <div class="fare-row">
          <span>Tarifa estimada</span>
          <strong>${{ ride.fare.toFixed(0) }} MXN</strong>
        </div>
      </div>

      <!-- Finished -->
      <div v-if="isFinished" class="info-card finished-card">
        <p>{{ isCompleted ? '¡Llegaste a tu destino! 🎉' : 'Viaje cancelado.' }}</p>
        <a href="/" class="btn-primary">Solicitar otro viaje</a>
      </div>
    </div>
  </div>
</template>

<script setup>
import 'leaflet/dist/leaflet.css'
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const rideId = route.params.rideId

const ride = ref(null)
const error = ref(null)
let map = null
let driverMarker = null
let originMarker = null
let destMarker = null
let routeLayer = null
let pollTimer = null

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api/v1'

const STATUS_MAP = {
  requested:      { label: 'Buscando conductor', icon: '🔍', cls: 'status-searching' },
  confirmed:      { label: 'Conductor en camino', icon: '🚗', cls: 'status-coming' },
  driver_arrived: { label: 'Conductor llegó', icon: '🚕', cls: 'status-arrived' },
  in_progress:    { label: 'Viaje en curso', icon: '🛣️', cls: 'status-progress' },
  completed:      { label: 'Viaje completado', icon: '✅', cls: 'status-done' },
  cancelled:      { label: 'Viaje cancelado', icon: '❌', cls: 'status-cancelled' },
  scheduled:      { label: 'Viaje programado', icon: '📅', cls: 'status-searching' },
}

const statusLabel = computed(() => STATUS_MAP[ride.value?.status]?.label ?? ride.value?.status ?? '')
const statusIcon  = computed(() => STATUS_MAP[ride.value?.status]?.icon ?? '')
const statusClass = computed(() => STATUS_MAP[ride.value?.status]?.cls ?? '')
const isFinished  = computed(() => ['completed', 'cancelled'].includes(ride.value?.status))
const isCompleted = computed(() => ride.value?.status === 'completed')

async function fetchRide() {
  try {
    const resp = await fetch(`${API_BASE}/customer/rides/${rideId}/public-track`)
    if (resp.status === 404) {
      error.value = 'Viaje no encontrado. Verifica el enlace.'
      clearInterval(pollTimer)
      return
    }
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
    const data = await resp.json()
    ride.value = data
    await nextTick()
    initMap(data)
    updateMarkers(data)
    if (isFinished.value) clearInterval(pollTimer)
  } catch (e) {
    console.error('[TrackPublic] fetch error:', e)
  }
}

async function drawRoute(Lm, oLat, oLng, dLat, dLng) {
  if (routeLayer) { map.removeLayer(routeLayer); routeLayer = null }
  try {
    const url = `https://router.project-osrm.org/route/v1/driving/${oLng},${oLat};${dLng},${dLat}?overview=full&geometries=geojson`
    const resp = await fetch(url)
    const data = await resp.json()
    if (data.routes?.[0]) {
      routeLayer = Lm.geoJSON(data.routes[0].geometry, {
        style: { color: '#3b82f6', weight: 4, opacity: 0.8 },
      }).addTo(map)
      return
    }
  } catch (_) { /* fallback */ }
  routeLayer = Lm.polyline([[oLat, oLng], [dLat, dLng]], {
    color: '#3b82f6', weight: 3, opacity: 0.7, dashArray: '8,6',
  }).addTo(map)
}

function initMap(data) {
  if (map) return
  const el = document.getElementById('public-map')
  if (!el) return

  import('leaflet').then(L => {
    const Lm = L.default || L

    // Center on driver position, then origin, then city fallback
    const center = data.driver?.lat != null
      ? [data.driver.lat, data.driver.lng]
      : data.origin?.lat != null
      ? [data.origin.lat, data.origin.lng]
      : [20.5236, -100.8198]

    map = Lm.map(el, { zoomControl: true, attributionControl: false }).setView(center, 14)
    Lm.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
    }).addTo(map)

    const mkIcon = (emoji, size = 32) => Lm.divIcon({
      html: `<span style="font-size:${size}px;line-height:1">${emoji}</span>`,
      iconSize: [size, size],
      iconAnchor: [size / 2, size / 2],
      className: '',
    })

    const pts = []
    if (data.origin?.lat != null) {
      originMarker = Lm.marker([data.origin.lat, data.origin.lng], { icon: mkIcon('📍') })
        .bindPopup(`<b>Origen</b><br>${data.origin.address}`)
        .addTo(map)
      pts.push([data.origin.lat, data.origin.lng])
    }
    if (data.destination?.lat != null) {
      destMarker = Lm.marker([data.destination.lat, data.destination.lng], { icon: mkIcon('🏁') })
        .bindPopup(`<b>Destino</b><br>${data.destination.address}`)
        .addTo(map)
      pts.push([data.destination.lat, data.destination.lng])
    }
    if (data.driver?.lat != null) {
      driverMarker = Lm.marker([data.driver.lat, data.driver.lng], { icon: mkIcon('🚕', 36) })
        .bindPopup(`<b>${data.driver.name}</b><br>${data.driver.vehicle}`)
        .addTo(map)
      pts.push([data.driver.lat, data.driver.lng])
    }

    if (pts.length > 1) map.fitBounds(pts, { padding: [40, 40] })

    // Dibujar trayecto entre origen y destino
    if (data.origin?.lat != null && data.destination?.lat != null) {
      drawRoute(Lm, data.origin.lat, data.origin.lng, data.destination.lat, data.destination.lng)
    }
  })
}

function updateMarkers(data) {
  if (!map || data.driver?.lat == null) return
  import('leaflet').then(L => {
    const Lm = L.default || L
    const pos = [data.driver.lat, data.driver.lng]
    if (driverMarker) {
      driverMarker.setLatLng(pos)
    } else {
      const mkIcon = (emoji, size = 36) => Lm.divIcon({
        html: `<span style="font-size:${size}px;line-height:1">${emoji}</span>`,
        iconSize: [size, size],
        iconAnchor: [size / 2, size / 2],
        className: '',
      })
      driverMarker = Lm.marker(pos, { icon: mkIcon('🚕', 36) })
        .bindPopup(`<b>${data.driver.name}</b><br>${data.driver.vehicle}`)
        .addTo(map)
      // Refit bounds to include new driver position
      const pts = [pos]
      if (data.origin?.lat != null) pts.push([data.origin.lat, data.origin.lng])
      if (data.destination?.lat != null) pts.push([data.destination.lat, data.destination.lng])
      if (pts.length > 1) map.fitBounds(pts, { padding: [40, 40] })
    }
  })
}

onMounted(() => {
  fetchRide()
  pollTimer = setInterval(fetchRide, 5000)
})

onUnmounted(() => {
  clearInterval(pollTimer)
  if (map) { map.remove(); map = null }
})
</script>

<style scoped>
.track-public {
  min-height: 100vh;
  background: #f5f5f5;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}

.track-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 16px 20px;
  background: #1a1a2e;
  color: #fff;
}
.track-logo { font-size: 28px; }
.track-title { font-size: 18px; font-weight: 600; }

.track-loading, .track-error {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  gap: 16px;
  color: #555;
}

.spinner {
  width: 40px; height: 40px;
  border: 4px solid #ddd;
  border-top-color: #f7c948;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.track-content {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-width: 600px;
  margin: 0 auto;
}

.status-badge {
  padding: 12px 16px;
  border-radius: 12px;
  font-weight: 600;
  font-size: 15px;
  text-align: center;
}
.status-searching { background: #fff3cd; color: #856404; }
.status-coming    { background: #d1ecf1; color: #0c5460; }
.status-arrived   { background: #cce5ff; color: #004085; }
.status-progress  { background: #d4edda; color: #155724; }
.status-done      { background: #d4edda; color: #155724; }
.status-cancelled { background: #f8d7da; color: #721c24; }

.track-map {
  height: 260px;
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid #ddd;
}

.info-card {
  background: #fff;
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 1px 4px rgba(0,0,0,.08);
}

.driver-card {
  display: flex;
  align-items: center;
  gap: 14px;
}
.card-icon { font-size: 36px; }
.card-name { font-weight: 700; font-size: 16px; margin: 0 0 4px; }
.card-sub  { color: #555; font-size: 14px; margin: 0 0 2px; }
.card-plates { font-size: 13px; color: #888; margin: 0; }

.route-row {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 4px 0;
}
.route-dot {
  width: 12px; height: 12px;
  border-radius: 50%;
  margin-top: 4px;
  flex-shrink: 0;
}
.origin-dot { background: #28a745; }
.dest-dot   { background: #dc3545; }
.route-line {
  width: 2px; height: 20px;
  background: #ddd;
  margin: 0 5px 4px 5px;
}
.route-label { font-size: 12px; color: #888; margin: 0 0 2px; }
.route-text p { margin: 0; font-size: 14px; }

.fare-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #f0f0f0;
  font-size: 14px;
  color: #555;
}
.fare-row strong { font-size: 18px; color: #1a1a2e; }

.finished-card {
  text-align: center;
  font-size: 15px;
}
.finished-card p { margin: 0 0 16px; }

.btn-primary {
  display: inline-block;
  background: #f7c948;
  color: #1a1a2e;
  font-weight: 700;
  padding: 12px 28px;
  border-radius: 50px;
  text-decoration: none;
  font-size: 15px;
}

.btn-link {
  color: #007bff;
  text-decoration: none;
}
</style>
