<template>
  <div class="p-8">
    <!-- Header -->
    <div class="flex items-center justify-between mb-8">
      <div>
        <h1 class="text-3xl font-bold text-gray-900">Dashboard</h1>
        <p class="text-gray-500 mt-1">Resumen operativo en tiempo real</p>
      </div>
      <button @click="load" class="flex items-center space-x-2 px-4 py-2 bg-white border border-gray-300 rounded-lg text-sm hover:bg-gray-50 transition">
        <span :class="loading ? 'animate-spin' : ''">🔄</span>
        <span>Actualizar</span>
      </button>
    </div>

    <!-- KPI Cards -->
    <div class="grid grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
      <div class="bg-white rounded-xl shadow p-6 border-l-4 border-green-500">
        <p class="text-sm text-gray-500 mb-1">Conductores Online</p>
        <p class="text-4xl font-bold text-green-600">{{ stats.drivers.online }}</p>
        <p class="text-xs text-gray-400 mt-2">de {{ stats.drivers.total }} registrados</p>
      </div>

      <div class="bg-white rounded-xl shadow p-6 border-l-4 border-blue-500">
        <p class="text-sm text-gray-500 mb-1">Viajes Activos</p>
        <p class="text-4xl font-bold text-blue-600">{{ stats.trips.active }}</p>
        <p class="text-xs text-gray-400 mt-2">en este momento</p>
      </div>

      <div class="bg-white rounded-xl shadow p-6 border-l-4 border-yellow-500">
        <p class="text-sm text-gray-500 mb-1">Viajes Hoy</p>
        <p class="text-4xl font-bold text-yellow-600">{{ stats.trips.completed_today }}</p>
        <p class="text-xs text-gray-400 mt-2">completados</p>
      </div>

      <div class="bg-white rounded-xl shadow p-6 border-l-4 border-purple-500">
        <p class="text-sm text-gray-500 mb-1">Ganancias Hoy</p>
        <p class="text-4xl font-bold text-purple-600">${{ stats.earnings.today.toFixed(0) }}</p>
        <p class="text-xs text-gray-400 mt-2">MXN</p>
      </div>
    </div>

    <!-- Segunda fila -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
      <!-- Estado de flota -->
      <div class="bg-white rounded-xl shadow p-6">
        <h2 class="text-lg font-semibold text-gray-900 mb-4">Estado de Flota</h2>
        <div class="space-y-3">
          <div class="flex items-center justify-between">
            <div class="flex items-center space-x-2">
              <span class="h-3 w-3 rounded-full bg-green-500 inline-block"></span>
              <span class="text-sm text-gray-700">Disponibles</span>
            </div>
            <span class="font-semibold text-green-600">{{ stats.drivers.online - stats.drivers.busy }}</span>
          </div>
          <div class="flex items-center justify-between">
            <div class="flex items-center space-x-2">
              <span class="h-3 w-3 rounded-full bg-yellow-500 inline-block"></span>
              <span class="text-sm text-gray-700">En viaje</span>
            </div>
            <span class="font-semibold text-yellow-600">{{ stats.drivers.busy }}</span>
          </div>
          <div class="flex items-center justify-between">
            <div class="flex items-center space-x-2">
              <span class="h-3 w-3 rounded-full bg-gray-400 inline-block"></span>
              <span class="text-sm text-gray-700">Offline</span>
            </div>
            <span class="font-semibold text-gray-600">{{ stats.drivers.offline }}</span>
          </div>

          <!-- Bar visual -->
          <div class="mt-4 h-2 bg-gray-200 rounded-full overflow-hidden flex">
            <div
              class="h-full bg-green-500 transition-all"
              :style="{ width: fleetPct.available + '%' }"
            ></div>
            <div
              class="h-full bg-yellow-500 transition-all"
              :style="{ width: fleetPct.busy + '%' }"
            ></div>
          </div>
          <p class="text-xs text-gray-400">
            {{ stats.drivers.total > 0 ? Math.round(stats.drivers.online / stats.drivers.total * 100) : 0 }}% de la flota activa
          </p>
        </div>
      </div>

      <!-- Viajes por estado -->
      <div class="bg-white rounded-xl shadow p-6">
        <h2 class="text-lg font-semibold text-gray-900 mb-4">Viajes en Curso</h2>
        <div class="space-y-3">
          <div v-for="ride in activeRides.slice(0, 5)" :key="ride.ride_id" class="flex items-start justify-between text-sm">
            <div class="flex-1 min-w-0">
              <p class="font-medium text-gray-900 truncate">{{ ride.customer.name }}</p>
              <p class="text-xs text-gray-500 truncate">{{ ride.origin.address }}</p>
            </div>
            <span :class="statusClass(ride.status)" class="ml-2 flex-shrink-0 px-2 py-0.5 text-xs rounded-full">
              {{ statusLabel(ride.status) }}
            </span>
          </div>
          <div v-if="activeRides.length === 0" class="text-center py-4 text-gray-400 text-sm">
            Sin viajes activos
          </div>
          <router-link
            v-if="activeRides.length > 0"
            to="/rides"
            class="block text-center text-sm text-blue-600 hover:underline mt-2"
          >
            Ver todos ({{ activeRides.length }}) →
          </router-link>
        </div>
      </div>

      <!-- Incidentes / Alertas -->
      <div class="bg-white rounded-xl shadow p-6">
        <h2 class="text-lg font-semibold text-gray-900 mb-4">
          Incidentes Activos
          <span
            v-if="stats.incidents.active > 0"
            class="ml-2 bg-red-500 text-white text-xs font-bold px-2 py-0.5 rounded-full"
          >{{ stats.incidents.active }}</span>
        </h2>
        <div v-if="stats.incidents.active === 0" class="text-center py-6 text-gray-400">
          <div class="text-4xl mb-2">✅</div>
          <p class="text-sm">Sin incidentes activos</p>
        </div>
        <div v-else class="space-y-2">
          <div v-for="inc in incidents.slice(0, 4)" :key="inc.incident_id" class="flex items-start space-x-2 text-sm">
            <span class="text-red-500 flex-shrink-0">🚨</span>
            <div class="min-w-0">
              <p class="font-medium text-gray-900">{{ inc.reporter_name }}</p>
              <p class="text-xs text-gray-500">{{ inc.reporter_type === 'driver' ? 'Conductor' : 'Cliente' }} · {{ formatTime(inc.created_at) }}</p>
            </div>
          </div>
          <router-link to="/incidents" class="block text-center text-sm text-blue-600 hover:underline mt-2">
            Ver todos →
          </router-link>
        </div>
      </div>
    </div>

    <!-- Totales acumulados -->
    <div class="bg-white rounded-xl shadow p-6">
      <h2 class="text-lg font-semibold text-gray-900 mb-4">Acumulado Total</h2>
      <div class="grid grid-cols-2 lg:grid-cols-4 gap-6">
        <div>
          <p class="text-sm text-gray-500">Viajes Totales</p>
          <p class="text-2xl font-bold text-gray-900">{{ stats.trips.total }}</p>
        </div>
        <div>
          <p class="text-sm text-gray-500">Ganancias Totales</p>
          <p class="text-2xl font-bold text-green-600">${{ stats.earnings.total.toFixed(0) }}</p>
        </div>
        <div>
          <p class="text-sm text-gray-500">Conductores Registrados</p>
          <p class="text-2xl font-bold text-blue-600">{{ stats.drivers.total }}</p>
        </div>
        <div>
          <p class="text-sm text-gray-500">Incidentes Totales</p>
          <p class="text-2xl font-bold text-red-600">{{ incidentsTotal }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'

const API = '/api/v1/admin'

const loading = ref(false)
const stats = ref({
  drivers:   { total: 0, online: 0, busy: 0, offline: 0 },
  trips:     { active: 0, completed_today: 0, total: 0 },
  earnings:  { today: 0, total: 0 },
  incidents: { active: 0 },
})
const activeRides  = ref([])
const incidents    = ref([])
const incidentsTotal = ref(0)

let interval = null

const fleetPct = computed(() => {
  const t = stats.value.drivers.total || 1
  return {
    available: Math.round((stats.value.drivers.online - stats.value.drivers.busy) / t * 100),
    busy:      Math.round(stats.value.drivers.busy / t * 100),
  }
})

function statusLabel(s) {
  return { requested: 'Solicitado', confirmed: 'Asignado', in_progress: 'En viaje', scheduled: 'Programado' }[s] || s
}
function statusClass(s) {
  return {
    requested:   'bg-blue-100 text-blue-800',
    confirmed:   'bg-yellow-100 text-yellow-800',
    in_progress: 'bg-green-100 text-green-800',
  }[s] || 'bg-gray-100 text-gray-800'
}
function formatTime(ts) {
  if (!ts) return ''
  const diff = Date.now() - new Date(ts).getTime()
  if (diff < 60000) return 'Hace un momento'
  if (diff < 3600000) return `Hace ${Math.floor(diff / 60000)} min`
  return `Hace ${Math.floor(diff / 3600000)}h`
}

async function load() {
  loading.value = true
  try {
    const [sRes, rRes, iRes] = await Promise.all([
      fetch(`${API}/stats`),
      fetch(`${API}/rides`),
      fetch('/api/v1/incidents'),
    ])
    if (sRes.ok) stats.value = await sRes.json()
    if (rRes.ok) {
      const data = await rRes.json()
      activeRides.value = (data.rides || []).filter(r =>
        ['requested', 'confirmed', 'in_progress'].includes(r.status)
      )
    }
    if (iRes.ok) {
      const data = await iRes.json()
      incidentsTotal.value = (data.incidents || []).length
      incidents.value = (data.incidents || []).filter(i => i.status === 'active')
    }
  } catch (e) {
    console.error('Dashboard load error:', e)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  load()
  interval = setInterval(load, 15000)
})

onUnmounted(() => clearInterval(interval))
</script>
