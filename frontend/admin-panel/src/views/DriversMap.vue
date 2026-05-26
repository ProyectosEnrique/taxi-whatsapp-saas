<template>
  <div class="p-8">
    <div class="flex items-center justify-between mb-6">
      <div>
        <h1 class="text-3xl font-bold text-gray-900">Mapa de Flota</h1>
        <p class="text-gray-500 mt-1">Posición en tiempo real de todos los conductores</p>
      </div>
      <div class="flex items-center space-x-4">
        <div class="flex items-center space-x-2 text-sm text-gray-600">
          <span class="inline-block w-3 h-3 rounded-full bg-green-500"></span> Disponible
          <span class="inline-block w-3 h-3 rounded-full bg-yellow-400 ml-3"></span> En viaje
          <span class="inline-block w-3 h-3 rounded-full bg-gray-400 ml-3"></span> Desconectado
        </div>
        <span class="text-sm text-gray-400">Actualiza cada 10s</span>
      </div>
    </div>

    <!-- Stats bar -->
    <div class="grid grid-cols-3 gap-4 mb-6">
      <div class="bg-white rounded-lg shadow p-4 flex items-center space-x-3">
        <span class="inline-block w-4 h-4 rounded-full bg-green-500"></span>
        <div>
          <p class="text-xs text-gray-500">Disponibles</p>
          <p class="text-2xl font-bold text-green-600">{{ counts.available }}</p>
        </div>
      </div>
      <div class="bg-white rounded-lg shadow p-4 flex items-center space-x-3">
        <span class="inline-block w-4 h-4 rounded-full bg-yellow-400"></span>
        <div>
          <p class="text-xs text-gray-500">En viaje</p>
          <p class="text-2xl font-bold text-yellow-600">{{ counts.busy }}</p>
        </div>
      </div>
      <div class="bg-white rounded-lg shadow p-4 flex items-center space-x-3">
        <span class="inline-block w-4 h-4 rounded-full bg-gray-400"></span>
        <div>
          <p class="text-xs text-gray-500">Desconectados</p>
          <p class="text-2xl font-bold text-gray-500">{{ counts.offline }}</p>
        </div>
      </div>
    </div>

    <!-- Map container -->
    <div class="bg-white rounded-lg shadow overflow-hidden">
      <div ref="mapEl" style="height: 520px; width: 100%;"></div>
    </div>

    <!-- Driver list below map -->
    <div class="mt-6 bg-white rounded-lg shadow">
      <div class="p-4 border-b border-gray-200">
        <h2 class="text-lg font-semibold text-gray-900">Conductores en línea</h2>
      </div>
      <div class="divide-y divide-gray-100">
        <div v-for="d in onlineDrivers" :key="d.phone" class="p-4 flex items-center justify-between">
          <div class="flex items-center space-x-3">
            <span :class="d.status === 'available' ? 'bg-green-500' : 'bg-yellow-400'"
              class="inline-block w-3 h-3 rounded-full flex-shrink-0"></span>
            <div>
              <p class="font-medium text-gray-900">{{ d.name }}</p>
              <p class="text-xs text-gray-500">{{ d.vehicle?.plates || 'Sin placas' }} · {{ d.vehicle?.color || '' }} {{ d.vehicle?.brand || '' }} {{ d.vehicle?.model || '' }}</p>
            </div>
          </div>
          <div class="text-right text-sm text-gray-500">
            <p v-if="d.location?.lat && d.location?.lng">
              {{ d.location.lat.toFixed(4) }}, {{ d.location.lng.toFixed(4) }}
            </p>
            <p v-else class="text-gray-300">Sin señal GPS</p>
            <p class="text-xs">⭐ {{ d.rating?.toFixed(1) || '5.0' }} · {{ d.total_rides || 0 }} viajes</p>
          </div>
        </div>
        <div v-if="onlineDrivers.length === 0" class="p-10 text-center text-gray-400">
          <div class="text-4xl mb-2">📡</div>
          <p>Ningún conductor en línea ahora mismo</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'

const mapEl = ref(null)
const drivers = ref([])
let map = null
const markers = {}
let interval = null

const counts = computed(() => ({
  available: drivers.value.filter(d => d.status === 'available').length,
  busy:      drivers.value.filter(d => d.status === 'busy').length,
  offline:   drivers.value.filter(d => d.status === 'offline').length,
}))

const onlineDrivers = computed(() =>
  drivers.value.filter(d => d.status !== 'offline')
)

function markerColor(status) {
  if (status === 'available') return '#22c55e'
  if (status === 'busy')      return '#facc15'
  return '#9ca3af'
}

function makeIcon(status) {
  const L = window.L
  const color = markerColor(status)
  return L.divIcon({
    className: '',
    html: `<div style="
      width:20px;height:20px;border-radius:50%;
      background:${color};border:3px solid white;
      box-shadow:0 2px 6px rgba(0,0,0,.4);
    "></div>`,
    iconSize: [20, 20],
    iconAnchor: [10, 10],
  })
}

async function loadDrivers() {
  try {
    const res = await fetch('/api/v1/admin/drivers')
    if (!res.ok) return
    const data = await res.json()
    drivers.value = data.drivers || []
    updateMarkers()
  } catch (e) {
    console.error('DriversMap:', e)
  }
}

function updateMarkers() {
  const L = window.L
  if (!map) return

  const seen = new Set()
  for (const d of drivers.value) {
    const lat = d.location?.lat
    const lng = d.location?.lng
    if (!lat || !lng) continue

    seen.add(d.phone)
    const popup = `
      <b>${d.name}</b><br>
      ${d.vehicle?.brand || ''} ${d.vehicle?.model || ''} — ${d.vehicle?.plates || 'N/D'}<br>
      ⭐ ${(d.rating || 5).toFixed(1)} · ${d.total_rides || 0} viajes<br>
      📞 ${d.phone}
    `
    if (markers[d.phone]) {
      markers[d.phone].setLatLng([lat, lng])
      markers[d.phone].setIcon(makeIcon(d.status))
      markers[d.phone].setPopupContent(popup)
    } else {
      markers[d.phone] = L.marker([lat, lng], { icon: makeIcon(d.status) })
        .bindPopup(popup)
        .addTo(map)
    }
  }

  // Remove markers for drivers no longer in list
  for (const phone of Object.keys(markers)) {
    if (!seen.has(phone)) {
      markers[phone].remove()
      delete markers[phone]
    }
  }

  // Center map on first driver with GPS if map is still at default
  if (Object.keys(markers).length === 1) {
    const first = drivers.value.find(d => d.location?.lat && d.location?.lng)
    if (first) map.setView([first.location.lat, first.location.lng], 13)
  }
}

onMounted(() => {
  const L = window.L
  map = L.map(mapEl.value).setView([20.6597, -103.3496], 12) // Guadalajara default

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap contributors',
    maxZoom: 19,
  }).addTo(map)

  loadDrivers()
  interval = setInterval(loadDrivers, 10000)
})

onUnmounted(() => {
  clearInterval(interval)
  if (map) { map.remove(); map = null }
})
</script>
