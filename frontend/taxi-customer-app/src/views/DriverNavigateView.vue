<template>
  <div class="driver-nav">

    <!-- Header -->
    <div class="nav-header" :class="headerClass">
      <span class="nav-logo">{{ phaseIcon }}</span>
      <div class="nav-header-text">
        <p class="nav-title">{{ phaseLabel }}</p>
        <p class="nav-sub">{{ rideId }}</p>
      </div>
      <div v-if="eta" class="nav-eta">
        <span class="eta-time">{{ eta.duration }} min</span>
        <span class="eta-dist">{{ eta.distance }} km</span>
      </div>
    </div>

    <!-- Error -->
    <div v-if="error" class="nav-error">{{ error }}</div>

    <template v-else-if="ride">

      <!-- Mapa -->
      <div id="driver-map" class="nav-map"></div>

      <!-- Card info + acción -->
      <div class="info-card">

        <!-- Completado -->
        <div v-if="status === 'completed'" class="completed-block">
          <p class="completed-title">🎉 Viaje completado</p>
          <p class="completed-sub">{{ ride.destination?.address }}</p>
          <p class="fare-text">${{ fareFmt }} MXN</p>
        </div>

        <!-- Estados activos -->
        <template v-else>
          <div class="addr-row">
            <span class="addr-icon">{{ targetIcon }}</span>
            <div>
              <p class="addr-label">{{ targetLabel }}</p>
              <p class="addr-text">{{ targetAddress }}</p>
            </div>
          </div>

          <p v-if="!gpsGranted" class="gps-hint">
            ⚠️ Activa el GPS del navegador para ver tu ruta
          </p>

          <div class="action-row">
            <!-- Llamar cliente -->
            <a v-if="ride.customer_phone" :href="`tel:${ride.customer_phone}`" class="btn-call">
              📞 Cliente
            </a>

            <!-- Botón de acción principal -->
            <button
              class="btn-action"
              :class="actionClass"
              :disabled="actioning"
              @click="doAction"
            >
              {{ actioning ? 'Procesando…' : actionLabel }}
            </button>
          </div>
        </template>

      </div>
    </template>

    <!-- Loading -->
    <div v-else class="loading">
      <div class="spinner"></div>
      <p>Cargando viaje…</p>
    </div>

  </div>
</template>

<script setup>
import 'leaflet/dist/leaflet.css'
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute } from 'vue-router'

const route    = useRoute()
const rideId   = route.params.rideId
// driver phone pasa como ?p=<base64> — solo enviado al conductor por Telegram
const driverPhone = (() => {
  try {
    const p = new URLSearchParams(window.location.search).get('p')
    if (!p) return null
    const pad = p + '='.repeat((4 - p.length % 4) % 4)
    return atob(pad)
  } catch { return null }
})()

const ride      = ref(null)
const status    = ref(null)
const eta       = ref(null)
const error     = ref(null)
const gpsGranted = ref(false)
const actioning  = ref(false)

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api/v1'

let map          = null
let driverMarker = null
let originMarker = null
let destMarker   = null
let routeLayer   = null
let watchId      = null
let pollTimer    = null
let lastRouteLat = null
let lastRouteLng = null
let currentTarget = null  // 'origin' | 'destination' | null
let LLeaflet     = null

// ── Computed ──────────────────────────────────────────────────────────────────
const phaseIcon = computed(() => ({
  confirmed:      '🚕',
  driver_arrived: '⏳',
  in_progress:    '🚗',
  completed:      '✅',
}[status.value] ?? '🚕'))

const phaseLabel = computed(() => ({
  confirmed:      'En camino al origen',
  driver_arrived: 'Esperando al cliente',
  in_progress:    'Viaje en curso',
  completed:      'Viaje completado',
}[status.value] ?? 'Cargando…'))

const headerClass = computed(() => ({
  confirmed:      'hdr-yellow',
  driver_arrived: 'hdr-blue',
  in_progress:    'hdr-green',
  completed:      'hdr-done',
}[status.value] ?? ''))

const targetIcon    = computed(() => status.value === 'in_progress' ? '🏁' : '📍')
const targetLabel   = computed(() => status.value === 'in_progress' ? 'Destino' : 'Punto de recogida')
const targetAddress = computed(() =>
  status.value === 'in_progress'
    ? ride.value?.destination?.address
    : ride.value?.origin?.address
)

const actionLabel = computed(() => ({
  confirmed:      '🟢 Llegué al origen',
  driver_arrived: '🚗 Pasajero a bordo — Iniciar viaje',
  in_progress:    '✅ Completar viaje',
}[status.value] ?? ''))

const actionClass = computed(() => ({
  confirmed:      'btn-green',
  driver_arrived: 'btn-blue',
  in_progress:    'btn-purple',
}[status.value] ?? ''))

const fareFmt = computed(() => parseFloat(ride.value?.fare ?? 0).toFixed(0))

// ── Helpers ───────────────────────────────────────────────────────────────────
function haversineM(lat1, lng1, lat2, lng2) {
  const R = 6371000
  const dLat = (lat2 - lat1) * Math.PI / 180
  const dLng = (lng2 - lng1) * Math.PI / 180
  const a = Math.sin(dLat/2)**2 + Math.cos(lat1*Math.PI/180)*Math.cos(lat2*Math.PI/180)*Math.sin(dLng/2)**2
  return R * 2 * Math.asin(Math.sqrt(a))
}

function mkIcon(emoji, size = 32) {
  return LLeaflet.divIcon({
    html: `<span style="font-size:${size}px;line-height:1;filter:drop-shadow(0 1px 3px rgba(0,0,0,.5))">${emoji}</span>`,
    iconSize: [size, size], iconAnchor: [size/2, size/2], className: '',
  })
}

// ── Ruta OSRM ─────────────────────────────────────────────────────────────────
async function drawRoute(dLat, dLng, tLat, tLng, color = '#f59e0b') {
  if (!map || !LLeaflet) return
  if (routeLayer) { map.removeLayer(routeLayer); routeLayer = null }
  eta.value = null
  try {
    const url = `https://router.project-osrm.org/route/v1/driving/${dLng},${dLat};${tLng},${tLat}?overview=full&geometries=geojson`
    const r = await (await fetch(url)).json()
    if (r.routes?.[0]) {
      routeLayer = LLeaflet.geoJSON(r.routes[0].geometry, { style: { color, weight: 4, opacity: 0.9 } }).addTo(map)
      eta.value = { duration: Math.ceil(r.routes[0].duration / 60), distance: (r.routes[0].distance / 1000).toFixed(1) }
      lastRouteLat = dLat; lastRouteLng = dLng
      return
    }
  } catch (_) {}
  routeLayer = LLeaflet.polyline([[dLat, dLng], [tLat, tLng]], { color, weight: 3, opacity: 0.7, dashArray: '8,6' }).addTo(map)
  lastRouteLat = dLat; lastRouteLng = dLng
}

// ── Actualizar mapa según estado ──────────────────────────────────────────────
async function syncMap(data, driverPos) {
  if (!map || !LLeaflet) return
  const oLat = data.origin?.lat, oLng = data.origin?.lng
  const dLat = data.destination?.lat, dLng = data.destination?.lng

  // Marcadores fijos de origen y destino
  if (oLat != null && !originMarker) {
    originMarker = LLeaflet.marker([oLat, oLng], { icon: mkIcon('📍', 36) })
      .bindPopup(`<b>Origen</b><br>${data.origin.address}`).addTo(map)
  }
  if (dLat != null && !destMarker) {
    destMarker = LLeaflet.marker([dLat, dLng], { icon: mkIcon('🏁', 36) })
      .bindPopup(`<b>Destino</b><br>${data.destination.address}`).addTo(map)
  }

  const s = data.status

  if (s === 'confirmed' && oLat != null) {
    // Ruta conductor → origen (amarillo); usar GPS del nav o última pos del servidor
    const pos = driverPos ?? (data.driver?.lat != null ? [data.driver.lat, data.driver.lng] : null)
    if (pos) {
      const moved = lastRouteLat != null ? haversineM(lastRouteLat, lastRouteLng, pos[0], pos[1]) : Infinity
      if (moved > 40 || currentTarget !== 'origin') {
        currentTarget = 'origin'
        await drawRoute(pos[0], pos[1], oLat, oLng, '#f59e0b')
        map.fitBounds([pos, [oLat, oLng]], { padding: [50, 50] })
      }
    }
  } else if (s === 'driver_arrived' && oLat != null && dLat != null) {
    // Vista estática origen + destino
    if (currentTarget !== 'waiting') {
      currentTarget = 'waiting'
      if (routeLayer) { map.removeLayer(routeLayer); routeLayer = null }
      eta.value = null
      map.fitBounds([[oLat, oLng], [dLat, dLng]], { padding: [60, 60] })
    }
  } else if (s === 'in_progress' && dLat != null) {
    // Ruta conductor → destino (azul); usar GPS del nav o última pos del servidor
    const pos = driverPos ?? (data.driver?.lat != null ? [data.driver.lat, data.driver.lng] : null)
    if (pos) {
      const moved = lastRouteLat != null ? haversineM(lastRouteLat, lastRouteLng, pos[0], pos[1]) : Infinity
      if (moved > 40 || currentTarget !== 'destination') {
        currentTarget = 'destination'
        await drawRoute(pos[0], pos[1], dLat, dLng, '#3b82f6')
        map.fitBounds([pos, [dLat, dLng]], { padding: [50, 50] })
      }
    }
  } else if (s === 'completed' && oLat != null && dLat != null) {
    if (currentTarget !== 'done') {
      currentTarget = 'done'
      if (routeLayer) { map.removeLayer(routeLayer); routeLayer = null }
      eta.value = null
      await drawRoute(oLat, oLng, dLat, dLng, '#6b7280')
      map.fitBounds([[oLat, oLng], [dLat, dLng]], { padding: [60, 60] })
    }
  }
}

// ── Init mapa ─────────────────────────────────────────────────────────────────
async function initMap(centerLat, centerLng) {
  if (map) return
  const el = document.getElementById('driver-map')
  if (!el) return
  LLeaflet = (await import('leaflet')).default
  map = LLeaflet.map(el, { zoomControl: false }).setView([centerLat, centerLng], 14)
  LLeaflet.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19, attribution: '© OpenStreetMap'
  }).addTo(map)
  LLeaflet.control.zoom({ position: 'bottomright' }).addTo(map)
}

// ── GPS conductor ─────────────────────────────────────────────────────────────
let driverPos = null

async function startGPS() {
  if (!navigator.geolocation) return
  watchId = navigator.geolocation.watchPosition(
    async (pos) => {
      gpsGranted.value = true
      driverPos = [pos.coords.latitude, pos.coords.longitude]
      if (!LLeaflet || !map) return
      if (driverMarker) {
        driverMarker.setLatLng(driverPos)
      } else {
        driverMarker = LLeaflet.marker(driverPos, { icon: mkIcon('🚕', 36) })
          .bindPopup('<b>Tu posición</b>').addTo(map)
      }
      if (ride.value) await syncMap(ride.value, driverPos)
    },
    (e) => console.warn('[GPS]', e.message),
    { enableHighAccuracy: true, maximumAge: 5000, timeout: 15000 }
  )
}

// ── Poll estado ───────────────────────────────────────────────────────────────
async function fetchRide() {
  try {
    const resp = await fetch(`${API_BASE}/customer/rides/${rideId}/public-track`)
    if (!resp.ok) return
    const data = await resp.json()
    ride.value   = data
    status.value = data.status
    await syncMap(data, driverPos)
    if (data.status === 'completed') clearInterval(pollTimer)
  } catch (e) { console.error('[DriverNav] poll:', e) }
}

// ── Acción (arrived / start / complete) ──────────────────────────────────────
const ACTION_MAP = { confirmed: 'arrived', driver_arrived: 'start', in_progress: 'complete' }

async function doAction() {
  const action = ACTION_MAP[status.value]
  if (!action || !driverPhone) {
    alert('No se pudo identificar al conductor. Usa el bot de Telegram para continuar.')
    return
  }
  actioning.value = true
  try {
    const resp = await fetch(`${API_BASE}/driver/rides/${rideId}/driver-action`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action, driver_phone: driverPhone }),
    })
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}))
      alert(err.detail || 'Error al actualizar el estado')
      return
    }
    const data = await resp.json()
    status.value   = data.status
    currentTarget  = null   // forzar re-render de ruta
    lastRouteLat   = null
    await fetchRide()
  } catch (e) {
    alert('Error de conexión')
  } finally {
    actioning.value = false
  }
}

// ── Lifecycle ─────────────────────────────────────────────────────────────────
onMounted(async () => {
  try {
    const resp = await fetch(`${API_BASE}/customer/rides/${rideId}/public-track`)
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
    const data = await resp.json()
    ride.value   = data
    status.value = data.status
    await nextTick()  // esperar a que v-else-if="ride" renderice #driver-map

    const cLat = data.origin?.lat ?? 20.5236
    const cLng = data.origin?.lng ?? -100.8198
    await initMap(cLat, cLng)
    await syncMap(data, null)
    await startGPS()

    if (data.status !== 'completed') {
      pollTimer = setInterval(fetchRide, 5000)
    }
  } catch (e) {
    error.value = 'No se pudo cargar el viaje. Verifica el enlace.'
  }
})

onUnmounted(() => {
  clearInterval(pollTimer)
  if (watchId != null) navigator.geolocation.clearWatch(watchId)
  if (map) { map.remove(); map = null }
})
</script>

<style scoped>
* { box-sizing: border-box; margin: 0; padding: 0; }

.driver-nav {
  min-height: 100vh;
  background: #111827;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  color: #f9fafb;
  display: flex;
  flex-direction: column;
}

/* Header */
.nav-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  border-bottom: 1px solid #374151;
  transition: background .4s;
}
.hdr-yellow { background: #78350f; }
.hdr-blue   { background: #1e3a5f; }
.hdr-green  { background: #064e3b; }
.hdr-done   { background: #1f2937; }

.nav-logo { font-size: 28px; }
.nav-header-text { flex: 1; }
.nav-title { font-size: 16px; font-weight: 700; }
.nav-sub   { font-size: 12px; color: #9ca3af; margin-top: 1px; }
.nav-eta   { display: flex; flex-direction: column; align-items: flex-end; gap: 2px; }
.eta-time  { font-size: 20px; font-weight: 800; color: #fbbf24; }
.eta-dist  { font-size: 12px; color: #9ca3af; }

/* Mapa */
.nav-map {
  height: 52vh;
  min-height: 280px;
  width: 100%;
}

/* Card */
.info-card {
  background: #1f2937;
  margin: 12px;
  border-radius: 14px;
  padding: 16px;
  border: 1px solid #374151;
  flex: 1;
}

.addr-row { display: flex; gap: 12px; align-items: flex-start; }
.addr-icon { font-size: 24px; flex-shrink: 0; margin-top: 2px; }
.addr-label { font-size: 11px; color: #9ca3af; text-transform: uppercase; letter-spacing: .5px; margin-bottom: 4px; }
.addr-text  { font-size: 15px; color: #f9fafb; line-height: 1.4; }

.gps-hint {
  margin-top: 10px;
  font-size: 13px;
  color: #f59e0b;
  text-align: center;
}

.action-row {
  display: flex;
  gap: 10px;
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px solid #374151;
}

.btn-call {
  display: flex;
  align-items: center;
  justify-content: center;
  background: #065f46;
  color: #ecfdf5;
  font-weight: 700;
  font-size: 14px;
  padding: 12px 16px;
  border-radius: 10px;
  text-decoration: none;
  white-space: nowrap;
}

.btn-action {
  flex: 1;
  font-size: 15px;
  font-weight: 700;
  padding: 12px 10px;
  border-radius: 10px;
  border: none;
  cursor: pointer;
  color: #fff;
  transition: opacity .15s;
}
.btn-action:disabled { opacity: .6; cursor: not-allowed; }
.btn-green  { background: #16a34a; }
.btn-blue   { background: #2563eb; }
.btn-purple { background: #7c3aed; }

/* Completado */
.completed-block { text-align: center; padding: 12px 0; }
.completed-title { font-size: 22px; font-weight: 800; margin-bottom: 8px; }
.completed-sub   { font-size: 14px; color: #9ca3af; margin-bottom: 12px; }
.fare-text       { font-size: 28px; font-weight: 800; color: #fbbf24; }

/* Error / loading */
.nav-error {
  flex: 1; display: flex; align-items: center; justify-content: center;
  padding: 40px 24px; color: #fca5a5; font-size: 15px; text-align: center;
}
.loading {
  flex: 1; display: flex; flex-direction: column; align-items: center;
  justify-content: center; gap: 16px; color: #9ca3af;
}
.spinner {
  width: 36px; height: 36px;
  border: 3px solid #374151; border-top-color: #f59e0b;
  border-radius: 50%; animation: spin .8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
</style>
