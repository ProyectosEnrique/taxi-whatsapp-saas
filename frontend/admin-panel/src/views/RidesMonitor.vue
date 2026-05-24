<template>
  <div class="p-8">
    <!-- Header -->
    <div class="flex items-center justify-between mb-8">
      <div>
        <h1 class="text-3xl font-bold text-gray-900">Monitor de Viajes</h1>
        <p class="text-gray-500 mt-1">Seguimiento en tiempo real de todos los viajes</p>
      </div>
      <div class="flex items-center space-x-3">
        <div class="flex items-center space-x-2">
          <span class="h-2.5 w-2.5 rounded-full bg-green-500 animate-pulse inline-block"></span>
          <span class="text-sm text-gray-600">En vivo</span>
        </div>
        <button @click="load" class="px-3 py-2 bg-white border border-gray-300 rounded-lg text-sm hover:bg-gray-50 transition">
          🔄
        </button>
      </div>
    </div>

    <!-- Stats -->
    <div class="grid grid-cols-2 lg:grid-cols-5 gap-4 mb-8">
      <div v-for="s in statusStats" :key="s.key" class="bg-white rounded-lg shadow p-4 border-l-4" :class="s.border">
        <p class="text-xs font-medium text-gray-500 uppercase">{{ s.label }}</p>
        <p class="text-3xl font-bold mt-1" :class="s.color">{{ s.count }}</p>
      </div>
    </div>

    <!-- Filters -->
    <div class="bg-white rounded-lg shadow p-4 mb-6 flex items-center space-x-4">
      <input
        v-model="search"
        type="text"
        placeholder="Buscar por cliente, conductor o ID..."
        class="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
      />
      <select v-model="filterStatus" class="px-4 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
        <option value="">Todos</option>
        <option value="requested">Solicitado</option>
        <option value="confirmed">Asignado</option>
        <option value="in_progress">En progreso</option>
        <option value="completed">Completado</option>
        <option value="cancelled">Cancelado</option>
      </select>
    </div>

    <!-- Two-column layout: active | recent completed -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <!-- Active Rides -->
      <div class="bg-white rounded-lg shadow">
        <div class="p-5 border-b border-gray-200">
          <h2 class="text-lg font-semibold text-gray-900">Viajes Activos</h2>
          <p class="text-sm text-gray-500">{{ activeRides.length }} en curso</p>
        </div>
        <div class="divide-y divide-gray-100 max-h-[600px] overflow-y-auto">
          <div v-for="ride in activeRides" :key="ride.ride_id" class="p-4">
            <div class="flex items-center justify-between mb-2">
              <span :class="badgeClass(ride.status)" class="px-2 py-0.5 text-xs font-semibold rounded-full">
                {{ statusLabel(ride.status) }}
              </span>
              <span class="text-xs text-gray-400">{{ formatTime(ride.requested_at) }}</span>
            </div>
            <div class="grid grid-cols-2 gap-3 mb-2 text-sm">
              <div>
                <p class="text-xs text-gray-400">Cliente</p>
                <p class="font-medium text-gray-900">{{ ride.customer.name }}</p>
                <p class="text-xs text-gray-500">{{ ride.customer.phone }}</p>
              </div>
              <div>
                <p class="text-xs text-gray-400">Conductor</p>
                <p class="font-medium text-gray-900">{{ ride.driver?.name || '—' }}</p>
              </div>
            </div>
            <div class="space-y-1 text-sm">
              <div class="flex items-center space-x-2">
                <span class="h-2 w-2 rounded-full bg-green-500 flex-shrink-0"></span>
                <span class="text-gray-600 truncate">{{ ride.origin.address }}</span>
              </div>
              <div class="flex items-center space-x-2">
                <span class="h-2 w-2 rounded-full bg-red-500 flex-shrink-0"></span>
                <span class="text-gray-600 truncate">{{ ride.destination.address }}</span>
              </div>
            </div>
            <div class="mt-2 pt-2 border-t border-gray-100 flex items-center justify-between text-xs text-gray-500">
              <span>🛣️ {{ ride.distance_km }} km · ⏱️ {{ ride.duration_minutes }} min</span>
              <span class="font-semibold text-gray-900">${{ ride.total_fare }}</span>
            </div>
          </div>
          <div v-if="activeRides.length === 0" class="p-10 text-center text-gray-400">
            <div class="text-4xl mb-2">✅</div>
            <p>Sin viajes activos</p>
          </div>
        </div>
      </div>

      <!-- Recent Completed -->
      <div class="bg-white rounded-lg shadow">
        <div class="p-5 border-b border-gray-200">
          <h2 class="text-lg font-semibold text-gray-900">Viajes Recientes</h2>
          <p class="text-sm text-gray-500">Últimos completados / cancelados</p>
        </div>
        <div class="divide-y divide-gray-100 max-h-[600px] overflow-y-auto">
          <div v-for="ride in recentRides" :key="ride.ride_id" class="p-4">
            <div class="flex items-center justify-between mb-1">
              <span :class="badgeClass(ride.status)" class="px-2 py-0.5 text-xs font-semibold rounded-full">
                {{ statusLabel(ride.status) }}
              </span>
              <span class="text-sm font-semibold" :class="ride.status === 'completed' ? 'text-green-600' : 'text-gray-400'">
                ${{ ride.total_fare }}
              </span>
            </div>
            <div class="flex items-center justify-between text-sm">
              <div class="min-w-0 flex-1">
                <p class="font-medium text-gray-900 truncate">{{ ride.customer.name }}</p>
                <p class="text-xs text-gray-500 truncate">→ {{ ride.destination.address }}</p>
              </div>
              <div class="text-right ml-4">
                <p class="text-xs text-gray-500">{{ ride.distance_km }} km</p>
                <p class="text-xs text-gray-400">{{ formatTime(ride.requested_at) }}</p>
              </div>
            </div>
          </div>
          <div v-if="recentRides.length === 0" class="p-10 text-center text-gray-400">
            Sin viajes recientes
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'

const API = '/api/v1/admin'
const rides        = ref([])
const search       = ref('')
const filterStatus = ref('')
let interval       = null

const ACTIVE_STATUSES   = ['requested', 'confirmed', 'in_progress', 'scheduled']
const INACTIVE_STATUSES = ['completed', 'cancelled']

const activeRides = computed(() => {
  return rides.value
    .filter(r => ACTIVE_STATUSES.includes(r.status))
    .filter(matchesSearch)
})

const recentRides = computed(() => {
  return rides.value
    .filter(r => INACTIVE_STATUSES.includes(r.status))
    .filter(matchesSearch)
    .slice(0, 20)
})

function matchesSearch(r) {
  if (filterStatus.value && r.status !== filterStatus.value) return false
  const q = search.value.toLowerCase()
  if (!q) return true
  return (
    r.customer.name.toLowerCase().includes(q) ||
    (r.driver?.name || '').toLowerCase().includes(q) ||
    r.ride_id.toLowerCase().includes(q)
  )
}

const statusStats = computed(() => [
  { key: 'requested',   label: 'Solicitados',  count: rides.value.filter(r => r.status === 'requested').length,   border: 'border-blue-500',   color: 'text-blue-600' },
  { key: 'confirmed',   label: 'Asignados',    count: rides.value.filter(r => r.status === 'confirmed').length,   border: 'border-yellow-500', color: 'text-yellow-600' },
  { key: 'in_progress', label: 'En Progreso',  count: rides.value.filter(r => r.status === 'in_progress').length, border: 'border-green-500',  color: 'text-green-600' },
  { key: 'completed',   label: 'Completados',  count: rides.value.filter(r => r.status === 'completed').length,   border: 'border-gray-400',   color: 'text-gray-700' },
  { key: 'cancelled',   label: 'Cancelados',   count: rides.value.filter(r => r.status === 'cancelled').length,   border: 'border-red-400',    color: 'text-red-600' },
])

function statusLabel(s) {
  return {
    requested:   'Solicitado',
    confirmed:   'Asignado',
    in_progress: 'En progreso',
    completed:   'Completado',
    cancelled:   'Cancelado',
    scheduled:   'Programado',
  }[s] || s
}

function badgeClass(s) {
  return {
    requested:   'bg-blue-100 text-blue-800',
    confirmed:   'bg-yellow-100 text-yellow-800',
    in_progress: 'bg-green-100 text-green-800',
    completed:   'bg-gray-100 text-gray-700',
    cancelled:   'bg-red-100 text-red-800',
    scheduled:   'bg-purple-100 text-purple-800',
  }[s] || 'bg-gray-100 text-gray-700'
}

function formatTime(ts) {
  if (!ts) return ''
  const diff = Date.now() - new Date(ts).getTime()
  if (diff < 60000) return 'Ahora'
  if (diff < 3600000) return `Hace ${Math.floor(diff / 60000)} min`
  if (diff < 86400000) return `Hace ${Math.floor(diff / 3600000)}h`
  return new Date(ts).toLocaleTimeString('es-MX', { hour: '2-digit', minute: '2-digit' })
}

async function load() {
  try {
    const res = await fetch(`${API}/rides?limit=200`)
    if (res.ok) {
      const data = await res.json()
      rides.value = data.rides || []
    }
  } catch (e) {
    console.error('RidesMonitor:', e)
  }
}

onMounted(() => {
  load()
  interval = setInterval(load, 5000)
})
onUnmounted(() => clearInterval(interval))
</script>
