<template>
  <div class="p-8">
    <!-- Header -->
    <div class="flex items-center justify-between mb-8">
      <div>
        <h1 class="text-3xl font-bold text-gray-900">Conductores</h1>
        <p class="text-gray-500 mt-1">Gestión de la flota de conductores</p>
      </div>
      <button @click="openAdd" class="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition text-sm font-medium">
        <span>+</span>
        <span>Agregar Conductor</span>
      </button>
    </div>

    <!-- Stats Cards -->
    <div class="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
      <div class="bg-white rounded-lg shadow p-5 flex items-center space-x-4">
        <div class="p-3 bg-green-100 rounded-lg">
          <span class="text-2xl">✅</span>
        </div>
        <div>
          <p class="text-xs text-gray-500 uppercase font-medium">Disponibles</p>
          <p class="text-2xl font-bold text-green-600">{{ countByStatus('available') }}</p>
        </div>
      </div>
      <div class="bg-white rounded-lg shadow p-5 flex items-center space-x-4">
        <div class="p-3 bg-yellow-100 rounded-lg">
          <span class="text-2xl">🚗</span>
        </div>
        <div>
          <p class="text-xs text-gray-500 uppercase font-medium">En Viaje</p>
          <p class="text-2xl font-bold text-yellow-600">{{ countByStatus('busy') }}</p>
        </div>
      </div>
      <div class="bg-white rounded-lg shadow p-5 flex items-center space-x-4">
        <div class="p-3 bg-gray-100 rounded-lg">
          <span class="text-2xl">💤</span>
        </div>
        <div>
          <p class="text-xs text-gray-500 uppercase font-medium">Offline</p>
          <p class="text-2xl font-bold text-gray-600">{{ countByStatus('offline') }}</p>
        </div>
      </div>
      <div class="bg-white rounded-lg shadow p-5 flex items-center space-x-4">
        <div class="p-3 bg-blue-100 rounded-lg">
          <span class="text-2xl">👥</span>
        </div>
        <div>
          <p class="text-xs text-gray-500 uppercase font-medium">Total</p>
          <p class="text-2xl font-bold text-blue-600">{{ drivers.length }}</p>
        </div>
      </div>
    </div>

    <!-- Search -->
    <div class="bg-white rounded-lg shadow p-4 mb-6">
      <input
        v-model="search"
        type="text"
        placeholder="Buscar por nombre, teléfono o placas..."
        class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
      />
    </div>

    <!-- Table -->
    <div class="bg-white rounded-lg shadow overflow-hidden">
      <table class="min-w-full divide-y divide-gray-200">
        <thead class="bg-gray-50">
          <tr>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Conductor</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Vehículo</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Estado</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Rating</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Viajes</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Acciones</th>
          </tr>
        </thead>
        <tbody class="bg-white divide-y divide-gray-200">
          <tr v-for="d in filtered" :key="d.driver_id" class="hover:bg-gray-50" :class="!d.is_active ? 'opacity-50' : ''">
            <td class="px-6 py-4">
              <div class="flex items-center space-x-3">
                <div class="h-9 w-9 rounded-full bg-blue-100 flex items-center justify-center text-blue-700 font-bold">
                  {{ d.name.charAt(0).toUpperCase() }}
                </div>
                <div>
                  <p class="text-sm font-medium text-gray-900">{{ d.name }}</p>
                  <p class="text-xs text-gray-500">{{ d.phone }}</p>
                </div>
              </div>
            </td>
            <td class="px-6 py-4 text-sm text-gray-700">
              <p>{{ d.vehicle.brand }} {{ d.vehicle.model }}</p>
              <p class="text-xs text-gray-500">{{ d.vehicle.plates }} · {{ d.vehicle.color }}</p>
            </td>
            <td class="px-6 py-4">
              <span :class="statusClass(d.status)" class="px-2 py-1 text-xs font-semibold rounded-full">
                {{ statusLabel(d.status) }}
              </span>
            </td>
            <td class="px-6 py-4 text-sm">
              <span class="text-yellow-500">★</span>
              <span class="font-medium">{{ d.rating.toFixed(1) }}</span>
            </td>
            <td class="px-6 py-4 text-sm text-gray-700">{{ d.total_rides }}</td>
            <td class="px-6 py-4">
              <div class="flex items-center space-x-2">
                <button @click="openEdit(d)" class="p-1.5 text-blue-600 hover:bg-blue-50 rounded transition" title="Editar">✏️</button>
                <button @click="toggleActive(d)" class="p-1.5 rounded transition"
                  :class="d.is_active ? 'text-red-600 hover:bg-red-50' : 'text-green-600 hover:bg-green-50'"
                  :title="d.is_active ? 'Desactivar' : 'Activar'">
                  {{ d.is_active ? '🚫' : '✅' }}
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-if="filtered.length === 0" class="text-center py-12 text-gray-400">
        <div class="text-5xl mb-3">🔍</div>
        <p>No hay conductores que coincidan</p>
      </div>
    </div>

    <!-- Modal Agregar / Editar -->
    <div v-if="showModal" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div class="bg-white rounded-xl shadow-2xl w-full max-w-md">
        <div class="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
          <h2 class="text-lg font-semibold text-gray-900">{{ editingDriver ? 'Editar Conductor' : 'Nuevo Conductor' }}</h2>
          <button @click="showModal = false" class="text-gray-400 hover:text-gray-600 text-2xl leading-none">&times;</button>
        </div>

        <form @submit.prevent="saveDriver" class="p-6 space-y-4">
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Nombre *</label>
              <input v-model="form.name" required class="input" placeholder="Carlos García" />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Teléfono *</label>
              <input v-model="form.phone" required :disabled="!!editingDriver" class="input disabled:bg-gray-100" placeholder="+5215511111111" />
            </div>
          </div>

          <div v-if="!editingDriver">
            <label class="block text-sm font-medium text-gray-700 mb-1">Contraseña</label>
            <input v-model="form.password" type="password" class="input" placeholder="1234" />
          </div>
          <div v-else>
            <label class="block text-sm font-medium text-gray-700 mb-1">Nueva contraseña (vacío = sin cambio)</label>
            <input v-model="form.password" type="password" class="input" placeholder="Dejar vacío para no cambiar" />
          </div>

          <div class="border-t pt-4">
            <p class="text-sm font-medium text-gray-700 mb-3">Vehículo</p>
            <div class="grid grid-cols-2 gap-3">
              <input v-model="form.vehicle_brand" class="input" placeholder="Marca (Nissan)" />
              <input v-model="form.vehicle_model" class="input" placeholder="Modelo (Versa)" />
              <input v-model="form.vehicle_plates" class="input" placeholder="Placas (ABC-123)" />
              <input v-model="form.vehicle_color" class="input" placeholder="Color" />
              <input v-model.number="form.vehicle_year" type="number" class="input" placeholder="Año (2020)" />
            </div>
          </div>

          <p v-if="formError" class="text-sm text-red-600">{{ formError }}</p>

          <div class="flex space-x-3 pt-2">
            <button type="button" @click="showModal = false" class="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-sm hover:bg-gray-50 transition">
              Cancelar
            </button>
            <button type="submit" :disabled="saving" class="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 transition disabled:opacity-50">
              {{ saving ? 'Guardando...' : (editingDriver ? 'Guardar Cambios' : 'Crear Conductor') }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'

const API = '/api/v1/admin'
const drivers = ref([])
const search  = ref('')
const showModal      = ref(false)
const editingDriver  = ref(null)
const saving         = ref(false)
const formError      = ref('')

const form = ref({
  name: '', phone: '', password: '',
  vehicle_brand: '', vehicle_model: '', vehicle_plates: '', vehicle_color: '', vehicle_year: null,
})

const filtered = computed(() => {
  const q = search.value.toLowerCase()
  return drivers.value.filter(d =>
    !q ||
    d.name.toLowerCase().includes(q) ||
    d.phone.includes(q) ||
    (d.vehicle.plates || '').toLowerCase().includes(q)
  )
})

function countByStatus(s) {
  if (s === 'available') return drivers.value.filter(d => d.status === 'available' && d.is_active).length
  if (s === 'busy')      return drivers.value.filter(d => d.status === 'busy').length
  return drivers.value.filter(d => !d.is_online && d.is_active).length
}

function statusLabel(s) {
  return { available: 'Disponible', busy: 'En viaje', offline: 'Offline' }[s] || s
}
function statusClass(s) {
  return {
    available: 'bg-green-100 text-green-800',
    busy:      'bg-yellow-100 text-yellow-800',
    offline:   'bg-gray-100 text-gray-800',
  }[s] || 'bg-gray-100 text-gray-800'
}

function openAdd() {
  editingDriver.value = null
  formError.value = ''
  form.value = { name: '', phone: '', password: '1234', vehicle_brand: '', vehicle_model: '', vehicle_plates: '', vehicle_color: '', vehicle_year: null }
  showModal.value = true
}

function openEdit(driver) {
  editingDriver.value = driver
  formError.value = ''
  form.value = {
    name: driver.name,
    phone: driver.phone,
    password: '',
    vehicle_brand:  driver.vehicle.brand,
    vehicle_model:  driver.vehicle.model,
    vehicle_plates: driver.vehicle.plates,
    vehicle_color:  driver.vehicle.color,
    vehicle_year:   driver.vehicle.year,
  }
  showModal.value = true
}

async function saveDriver() {
  saving.value = true
  formError.value = ''
  try {
    let res
    if (editingDriver.value) {
      res = await fetch(`${API}/drivers/${editingDriver.value.phone}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form.value),
      })
    } else {
      res = await fetch(`${API}/drivers`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form.value),
      })
    }
    const data = await res.json()
    if (!res.ok) throw new Error(data.detail || 'Error al guardar')
    showModal.value = false
    await loadDrivers()
  } catch (e) {
    formError.value = e.message
  } finally {
    saving.value = false
  }
}

async function toggleActive(driver) {
  const action = driver.is_active ? 'desactivar' : 'activar'
  if (!confirm(`¿${action} a ${driver.name}?`)) return
  try {
    const res = await fetch(`${API}/drivers/${driver.phone}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ is_active: !driver.is_active }),
    })
    if (res.ok) await loadDrivers()
  } catch (e) {
    console.error(e)
  }
}

async function loadDrivers() {
  try {
    const res = await fetch(`${API}/drivers`)
    if (res.ok) {
      const data = await res.json()
      drivers.value = data.drivers || []
    }
  } catch (e) {
    console.error('loadDrivers:', e)
  }
}

onMounted(loadDrivers)
</script>

<style scoped>
.input {
  @apply w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm;
}
</style>
