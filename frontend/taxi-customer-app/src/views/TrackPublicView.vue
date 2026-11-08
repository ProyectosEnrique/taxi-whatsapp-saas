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

      <!-- Tiempo y distancia -->
      <div v-if="etaText" class="eta-card">
        <span class="eta-main">{{ etaText.main }}</span>
        <span v-if="etaText.sub" class="eta-sub">{{ etaText.sub }}</span>
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

      <!-- SOS: mantener presionado 2 s (un toque por accidente no alerta a nadie) -->
      <div v-if="canSos" class="sos-box">
        <div v-if="sosSent" class="sos-sent">
          <p>🚨 <strong>Alerta enviada.</strong> El encargado de la base ya tiene tus datos y te va a contactar.</p>
          <a :href="`tel:${emergencyPhone}`" class="btn-911">📞 Llamar al {{ emergencyPhone }}</a>
        </div>
        <template v-else>
          <button
            class="btn-sos"
            :class="{ holding: sosHolding }"
            :disabled="sosSending"
            @pointerdown.prevent="startSosHold"
            @pointerup="cancelSosHold"
            @pointerleave="cancelSosHold"
            @pointercancel="cancelSosHold"
            @contextmenu.prevent
          >
            <span class="sos-fill" :style="{ width: sosProgress + '%' }"></span>
            <span class="sos-label">{{ sosSending ? 'Enviando alerta…' : '🚨 SOS — mantén presionado' }}</span>
          </button>
          <p v-if="sosError" class="sos-error">{{ sosError }}</p>
        </template>
      </div>

      <!-- Regalo FarmaCerca (primer viaje) -->
      <div v-if="ride.gift && ride.status !== 'cancelled'" class="info-card gift-card">
        <p v-if="!isCompleted">
          🎁 Al terminar tu viaje te regalamos <strong>${{ ride.gift.amount }}</strong> en tu
          Monedero FarmaCerca, <em>Tu farmacia por WhatsApp</em>.
        </p>
        <template v-else>
          <p>🎁 Por viajar con TaxiCerca tienes <strong>${{ ride.gift.amount }}</strong> en tu Monedero FarmaCerca.</p>
          <a :href="ride.gift.url" class="btn-gift" target="_blank" rel="noopener">Recoger mi regalo</a>
        </template>
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
let LLeafletRef = null
let driverMarker = null
let originMarker = null
let destMarker = null
let routeLayer = null
let pollTimer = null
let lastRouteStatus = null

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

// ── SOS ───────────────────────────────────────────────────────────────────────
const SOS_HOLD_MS = 2000
const canSos = computed(() => ['confirmed', 'driver_arrived', 'in_progress'].includes(ride.value?.status) || sosSent.value)
const sosHolding = ref(false)
const sosProgress = ref(0)
const sosSending = ref(false)
const sosSent = ref(false)
const sosError = ref('')
const emergencyPhone = ref('911')
let sosTimer = null
let sosStart = 0

function startSosHold() {
  if (sosSending.value) return
  sosError.value = ''
  sosHolding.value = true
  sosStart = Date.now()
  sosTimer = setInterval(() => {
    sosProgress.value = Math.min(100, (Date.now() - sosStart) / SOS_HOLD_MS * 100)
    if (sosProgress.value >= 100) {
      cancelSosHold()
      sendSos()
    }
  }, 50)
}

function cancelSosHold() {
  clearInterval(sosTimer)
  sosHolding.value = false
  if (!sosSending.value) sosProgress.value = 0
}

function _position() {
  // Ubicación del celular si la da en 4 s; si no, se usa la del taxi
  return new Promise(resolve => {
    if (!navigator.geolocation) return resolve({})
    navigator.geolocation.getCurrentPosition(
      p => resolve({ lat: p.coords.latitude, lng: p.coords.longitude }),
      () => resolve({}),
      { enableHighAccuracy: true, timeout: 4000, maximumAge: 30000 },
    )
  })
}

async function sendSos() {
  sosSending.value = true
  try {
    const where = await _position()
    const resp = await fetch(`${API_BASE}/customer/rides/${rideId}/sos`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(where),
    })
    const data = await resp.json().catch(() => ({}))
    if (!resp.ok) throw new Error(data.detail || `HTTP ${resp.status}`)
    emergencyPhone.value = data.emergency_phone || '911'
    sosSent.value = true
  } catch (e) {
    sosError.value = `No se pudo enviar la alerta. Si estás en peligro, llama al ${emergencyPhone.value}.`
  } finally {
    sosSending.value = false
    sosProgress.value = 0
  }
}

// ── Tiempo y distancia ─────────────────────────────────────────────────────────
// En camino: taxi → pasajero. En curso: taxi → destino. Antes de asignar: trayecto
// completo. Se recalcula cada 30 s (no en cada consulta de 5 s, para no saturar OSRM).
const eta = ref(null)            // { km, min, kind }
let lastEtaAt = 0
let lastEtaStatus = null
const ETA_EVERY_MS = 30000

function _haversineKm(a, b, c, d) {
  const R = 6371, toRad = x => x * Math.PI / 180
  const dLat = toRad(c - a), dLng = toRad(d - b)
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(toRad(a)) * Math.cos(toRad(c)) * Math.sin(dLng / 2) ** 2
  return 2 * R * Math.asin(Math.sqrt(h))
}

async function _routeKmMin(oLat, oLng, dLat, dLng) {
  try {
    const url = `https://router.project-osrm.org/route/v1/driving/${oLng},${oLat};${dLng},${dLat}?overview=false`
    const data = await (await fetch(url)).json()
    const r = data.routes?.[0]
    if (r) return { km: r.distance / 1000, min: r.duration / 60 }
  } catch (_) { /* aproximación abajo */ }
  // Línea recta × 1.3 por calles, ~25 km/h en ciudad
  const km = _haversineKm(oLat, oLng, dLat, dLng) * 1.3
  return { km, min: km / 25 * 60 }
}

async function updateEta(data) {
  const s = data.status
  const dr = data.driver, o = data.origin, d = data.destination
  let from = null, to = null, kind = null
  if (s === 'confirmed' && dr?.lat != null && o?.lat != null) {
    from = [dr.lat, dr.lng]; to = [o.lat, o.lng]; kind = 'pickup'
  } else if (s === 'in_progress' && dr?.lat != null && d?.lat != null) {
    from = [dr.lat, dr.lng]; to = [d.lat, d.lng]; kind = 'dest'
  } else if (['requested', 'scheduled'].includes(s) && o?.lat != null && d?.lat != null) {
    from = [o.lat, o.lng]; to = [d.lat, d.lng]; kind = 'trip'
  } else {
    eta.value = s === 'driver_arrived' ? { kind: 'arrived' } : null
    lastEtaStatus = s
    return
  }
  const now = Date.now()
  if (s === lastEtaStatus && now - lastEtaAt < ETA_EVERY_MS) return
  lastEtaStatus = s
  lastEtaAt = now
  const r = await _routeKmMin(...from, ...to)
  eta.value = { km: r.km, min: Math.max(1, Math.round(r.min)), kind }
}

const etaText = computed(() => {
  const e = eta.value
  if (!e) return null
  if (e.kind === 'arrived') return { main: '🚕 Tu taxi te está esperando' }
  const km = e.km < 1 ? `${Math.round(e.km * 1000)} m` : `${e.km.toFixed(1)} km`
  if (e.kind === 'pickup') return { main: `🚕 Tu taxi llega en ~${e.min} min`, sub: `a ${km} de ti` }
  if (e.kind === 'dest') return { main: `🏁 Llegas en ~${e.min} min`, sub: `faltan ${km} para tu destino` }
  return { main: `🛣️ Trayecto: ${km}`, sub: `~${e.min} min de viaje` }
})

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
    updateEta(data)
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

  import('leaflet').then(async L => {
    const Lm = L.default || L
    LLeafletRef = Lm

    const center = data.driver?.lat != null
      ? [data.driver.lat, data.driver.lng]
      : data.origin?.lat != null
      ? [data.origin.lat, data.origin.lng]
      : [20.5236, -100.8198]

    map = Lm.map(el, { zoomControl: true, attributionControl: false }).setView(center, 14)
    Lm.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19 }).addTo(map)

    const mkIcon = (emoji, size = 32) => Lm.divIcon({
      html: `<span style="font-size:${size}px;line-height:1">${emoji}</span>`,
      iconSize: [size, size], iconAnchor: [size / 2, size / 2], className: '',
    })

    const pts = []
    if (data.origin?.lat != null) {
      originMarker = Lm.marker([data.origin.lat, data.origin.lng], { icon: mkIcon('📍') })
        .bindPopup(`<b>Origen</b><br>${data.origin.address}`).addTo(map)
      pts.push([data.origin.lat, data.origin.lng])
    }
    if (data.destination?.lat != null) {
      destMarker = Lm.marker([data.destination.lat, data.destination.lng], { icon: mkIcon('🏁') })
        .bindPopup(`<b>Destino</b><br>${data.destination.address}`).addTo(map)
      pts.push([data.destination.lat, data.destination.lng])
    }
    if (data.driver?.lat != null) {
      driverMarker = Lm.marker([data.driver.lat, data.driver.lng], { icon: mkIcon('🚕', 36) })
        .bindPopup(`<b>${data.driver.name}</b><br>${data.driver.vehicle}`).addTo(map)
      pts.push([data.driver.lat, data.driver.lng])
    }

    if (pts.length > 1) map.fitBounds(pts, { padding: [40, 40] })
    await _updateRoute(data)
  })
}

async function _updateRoute(data) {
  if (!map || !LLeafletRef) return
  const Lm = LLeafletRef
  const s  = data.status
  const oLat = data.origin?.lat, oLng = data.origin?.lng
  const dLat = data.destination?.lat, dLng = data.destination?.lng
  const drLat = data.driver?.lat, drLng = data.driver?.lng

  // Solo redibujar cuando cambia el estado
  if (s === lastRouteStatus) return
  lastRouteStatus = s

  if (s === 'confirmed' && drLat != null && oLat != null) {
    // Taxi en camino al cliente — ruta amarilla conductor→origen
    await drawRoute(Lm, drLat, drLng, oLat, oLng)
    if (routeLayer) routeLayer.setStyle({ color: '#f59e0b', dashArray: '8,6' })
  } else if (s === 'in_progress' && drLat != null && dLat != null) {
    // Viaje en curso — ruta azul conductor→destino
    await drawRoute(Lm, drLat, drLng, dLat, dLng)
  } else if (oLat != null && dLat != null) {
    // Resto de estados — trayecto completo origen→destino
    await drawRoute(Lm, oLat, oLng, dLat, dLng)
  }
}

async function updateMarkers(data) {
  if (!map || !LLeafletRef) return
  const Lm = LLeafletRef

  if (data.driver?.lat != null) {
    const pos = [data.driver.lat, data.driver.lng]
    if (driverMarker) {
      driverMarker.setLatLng(pos)
      // Pan suave para mantener al conductor visible
      if (!map.getBounds().contains(pos)) {
        map.panTo(pos, { animate: true, duration: 0.6 })
      }
    }
  }

  await _updateRoute(data)
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

.btn-sos {
  position: relative;
  overflow: hidden;
  width: 100%;
  border: 0;
  border-radius: 12px;
  padding: 14px 16px;
  background: #b91c1c;
  color: #fff;
  font-size: 16px;
  font-weight: 700;
  user-select: none;
  -webkit-user-select: none;
  touch-action: none;
}
.btn-sos.holding { background: #7f1d1d; }
.sos-fill {
  position: absolute;
  inset: 0 auto 0 0;
  background: rgba(255,255,255,.25);
}
.sos-label { position: relative; }
.sos-error { margin: 8px 0 0; color: #b91c1c; font-size: 13px; text-align: center; }
.sos-sent {
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 12px;
  padding: 14px 16px;
  text-align: center;
  color: #7f1d1d;
}
.sos-sent p { margin: 0 0 12px; }
.btn-911 {
  display: inline-block;
  background: #b91c1c;
  color: #fff;
  font-weight: 700;
  padding: 10px 24px;
  border-radius: 50px;
  text-decoration: none;
}

.eta-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  background: #1a1a2e;
  color: #fff;
  border-radius: 12px;
  padding: 12px 16px;
}
.eta-main { font-size: 18px; font-weight: 700; }
.eta-sub { font-size: 13px; opacity: .8; }

.gift-card {
  background: #effaf3;
  border: 1px solid #b7e4c7;
  font-size: 14px;
  text-align: center;
}
.gift-card p { margin: 0; color: #1b4332; }
.btn-gift {
  display: inline-block;
  margin-top: 12px;
  background: #2d6a4f;
  color: #fff;
  font-weight: 700;
  padding: 10px 24px;
  border-radius: 50px;
  text-decoration: none;
}

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
