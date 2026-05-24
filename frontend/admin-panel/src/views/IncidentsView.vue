<template>
  <div class="p-8">
    <!-- Header -->
    <div class="flex items-center justify-between mb-8">
      <div>
        <h1 class="text-3xl font-bold text-gray-900">Incidentes</h1>
        <p class="text-gray-500 mt-1">Alertas de pánico de conductores y clientes</p>
      </div>
      <button @click="load" class="px-4 py-2 bg-white border border-gray-300 rounded-lg text-sm hover:bg-gray-50 transition">
        🔄 Actualizar
      </button>
    </div>

    <!-- Stats -->
    <div class="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
      <div class="bg-white rounded-lg shadow p-5 border-l-4 border-red-500">
        <p class="text-xs text-gray-500 uppercase font-medium">Activos</p>
        <p class="text-3xl font-bold text-red-600">{{ activeCount }}</p>
      </div>
      <div class="bg-white rounded-lg shadow p-5 border-l-4 border-green-500">
        <p class="text-xs text-gray-500 uppercase font-medium">Resueltos</p>
        <p class="text-3xl font-bold text-green-600">{{ resolvedCount }}</p>
      </div>
      <div class="bg-white rounded-lg shadow p-5 border-l-4 border-blue-500">
        <p class="text-xs text-gray-500 uppercase font-medium">Conductores</p>
        <p class="text-3xl font-bold text-blue-600">{{ incidents.filter(i => i.reporter_type === 'driver').length }}</p>
      </div>
      <div class="bg-white rounded-lg shadow p-5 border-l-4 border-purple-500">
        <p class="text-xs text-gray-500 uppercase font-medium">Clientes</p>
        <p class="text-3xl font-bold text-purple-600">{{ incidents.filter(i => i.reporter_type === 'customer').length }}</p>
      </div>
    </div>

    <!-- Filter -->
    <div class="bg-white rounded-lg shadow p-4 mb-6 flex items-center space-x-4">
      <select v-model="filterStatus" class="px-4 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
        <option value="">Todos los estados</option>
        <option value="active">Activos</option>
        <option value="resolved">Resueltos</option>
      </select>
      <select v-model="filterType" class="px-4 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
        <option value="">Todos los tipos</option>
        <option value="driver">Conductores</option>
        <option value="customer">Clientes</option>
      </select>
    </div>

    <!-- Incidents list -->
    <div class="space-y-4">
      <div
        v-for="inc in filtered"
        :key="inc.incident_id"
        class="bg-white rounded-lg shadow p-5"
        :class="inc.status === 'active' ? 'border-l-4 border-red-500' : 'border-l-4 border-green-500'"
      >
        <div class="flex items-start justify-between">
          <div class="flex items-start space-x-4">
            <span class="text-3xl mt-1">{{ inc.reporter_type === 'driver' ? '🚗' : '👤' }}</span>
            <div>
              <div class="flex items-center space-x-2 mb-1">
                <span class="font-semibold text-gray-900">{{ inc.reporter_name || inc.reporter_phone }}</span>
                <span
                  :class="inc.reporter_type === 'driver' ? 'bg-blue-100 text-blue-800' : 'bg-purple-100 text-purple-800'"
                  class="px-2 py-0.5 text-xs rounded-full font-medium"
                >
                  {{ inc.reporter_type === 'driver' ? 'Conductor' : 'Cliente' }}
                </span>
                <span
                  :class="inc.status === 'active' ? 'bg-red-100 text-red-800' : 'bg-green-100 text-green-800'"
                  class="px-2 py-0.5 text-xs rounded-full font-medium"
                >
                  {{ inc.status === 'active' ? '🚨 Activo' : '✅ Resuelto' }}
                </span>
              </div>

              <p class="text-sm text-gray-600 mb-1">
                <span class="font-medium">Tel:</span> {{ inc.reporter_phone }}
                <span v-if="inc.trip_id" class="ml-3"><span class="font-medium">Viaje:</span> {{ inc.trip_id }}</span>
              </p>

              <p v-if="inc.notes" class="text-sm text-gray-700 mb-2 italic">"{{ inc.notes }}"</p>

              <div class="flex items-center space-x-4 text-xs text-gray-500">
                <span>🕐 {{ formatDatetime(inc.created_at) }}</span>
                <span v-if="inc.lat">
                  📍
                  <a
                    :href="`https://maps.google.com/?q=${inc.lat},${inc.lng}`"
                    target="_blank"
                    class="text-blue-600 hover:underline"
                  >
                    Ver en mapa
                  </a>
                </span>
                <span class="font-mono text-gray-400">{{ inc.incident_id }}</span>
              </div>
            </div>
          </div>

          <div v-if="inc.status === 'active'">
            <button
              @click="resolve(inc)"
              class="px-3 py-1.5 bg-green-600 text-white text-xs font-medium rounded-lg hover:bg-green-700 transition"
            >
              Marcar resuelto
            </button>
          </div>
        </div>
      </div>

      <div v-if="filtered.length === 0" class="bg-white rounded-lg shadow p-12 text-center text-gray-400">
        <div class="text-5xl mb-3">✅</div>
        <p class="text-lg">Sin incidentes</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'

const incidents    = ref([])
const filterStatus = ref('')
const filterType   = ref('')
let interval       = null

const activeCount   = computed(() => incidents.value.filter(i => i.status === 'active').length)
const resolvedCount = computed(() => incidents.value.filter(i => i.status === 'resolved').length)

const filtered = computed(() => {
  return incidents.value.filter(i => {
    if (filterStatus.value && i.status !== filterStatus.value) return false
    if (filterType.value   && i.reporter_type !== filterType.value) return false
    return true
  })
})

function formatDatetime(ts) {
  if (!ts) return ''
  return new Date(ts).toLocaleString('es-MX', {
    day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit'
  })
}

async function resolve(inc) {
  if (!confirm(`¿Marcar ${inc.incident_id} como resuelto?`)) return
  try {
    const res = await fetch(`/api/v1/incidents/${inc.incident_id}/resolve`, {
      method: 'POST',
    })
    if (res.ok) {
      inc.status = 'resolved'
    }
  } catch {
    inc.status = 'resolved'
  }
}

async function load() {
  try {
    const res = await fetch('/api/v1/incidents')
    if (res.ok) {
      const data = await res.json()
      incidents.value = (data.incidents || []).sort((a, b) =>
        new Date(b.created_at) - new Date(a.created_at)
      )
    }
  } catch (e) {
    console.error('IncidentsView:', e)
  }
}

onMounted(() => {
  load()
  interval = setInterval(load, 10000)
})
onUnmounted(() => clearInterval(interval))
</script>
