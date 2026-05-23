<template>
  <div class="drivers-management">
    <!-- Header -->
    <div class="page-header">
      <h1 class="text-3xl font-bold text-gray-900">Gestión de Conductores</h1>
      <button @click="showAddDriverModal = true" class="btn btn-primary">
        <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
        </svg>
        Agregar Conductor
      </button>
    </div>

    <!-- Stats Cards -->
    <div class="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
      <div class="stat-card">
        <div class="stat-icon bg-green-100">
          <svg class="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        <div>
          <p class="stat-label">Disponibles</p>
          <p class="stat-value text-green-600">{{ stats.available }}</p>
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-icon bg-yellow-100">
          <svg class="w-6 h-6 text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        <div>
          <p class="stat-label">Ocupados</p>
          <p class="stat-value text-yellow-600">{{ stats.busy }}</p>
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-icon bg-gray-100">
          <svg class="w-6 h-6 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" />
          </svg>
        </div>
        <div>
          <p class="stat-label">Offline</p>
          <p class="stat-value text-gray-600">{{ stats.offline }}</p>
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-icon bg-blue-100">
          <svg class="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
          </svg>
        </div>
        <div>
          <p class="stat-label">Total Conductores</p>
          <p class="stat-value text-blue-600">{{ stats.total }}</p>
        </div>
      </div>
    </div>

    <!-- Filters -->
    <div class="bg-white rounded-lg shadow p-6 mb-6">
      <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div>
          <input
            v-model="filters.search"
            type="text"
            placeholder="Buscar por nombre, teléfono..."
            class="input"
          />
        </div>

        <div>
          <select v-model="filters.status" class="input">
            <option value="">Todos los estados</option>
            <option value="available">Disponible</option>
            <option value="busy">Ocupado</option>
            <option value="offline">Offline</option>
            <option value="on_break">En descanso</option>
          </select>
        </div>

        <div>
          <select v-model="filters.vehicleType" class="input">
            <option value="">Todos los vehículos</option>
            <option value="sedan">Sedan</option>
            <option value="suv">SUV</option>
            <option value="van">Van</option>
            <option value="luxury">Lujo</option>
          </select>
        </div>

        <div>
          <select v-model="filters.rating" class="input">
            <option value="">Todas las calificaciones</option>
            <option value="5">5 estrellas</option>
            <option value="4">4+ estrellas</option>
            <option value="3">3+ estrellas</option>
          </select>
        </div>
      </div>
    </div>

    <!-- Drivers Table -->
    <div class="bg-white rounded-lg shadow overflow-hidden">
      <table class="min-w-full divide-y divide-gray-200">
        <thead class="bg-gray-50">
          <tr>
            <th class="table-header">Conductor</th>
            <th class="table-header">Vehículo</th>
            <th class="table-header">Estado</th>
            <th class="table-header">Rating</th>
            <th class="table-header">Viajes</th>
            <th class="table-header">Aceptación</th>
            <th class="table-header">Ubicación</th>
            <th class="table-header">Acciones</th>
          </tr>
        </thead>
        <tbody class="bg-white divide-y divide-gray-200">
          <tr v-for="driver in filteredDrivers" :key="driver.driver_id" class="hover:bg-gray-50">
            <!-- Conductor -->
            <td class="table-cell">
              <div class="flex items-center">
                <div class="flex-shrink-0 h-10 w-10">
                  <div class="h-10 w-10 rounded-full bg-gray-300 flex items-center justify-center">
                    <span class="text-gray-600 font-medium">{{ driver.name.charAt(0) }}</span>
                  </div>
                </div>
                <div class="ml-4">
                  <div class="text-sm font-medium text-gray-900">{{ driver.name }}</div>
                  <div class="text-sm text-gray-500">{{ driver.phone }}</div>
                </div>
              </div>
            </td>

            <!-- Vehículo -->
            <td class="table-cell">
              <div class="text-sm text-gray-900">{{ driver.vehicle.brand }} {{ driver.vehicle.model }}</div>
              <div class="text-sm text-gray-500">{{ driver.vehicle.plates }} • {{ driver.vehicle.color }}</div>
            </td>

            <!-- Estado -->
            <td class="table-cell">
              <span :class="getStatusClass(driver.status)" class="px-2 py-1 text-xs font-semibold rounded-full">
                {{ getStatusLabel(driver.status) }}
              </span>
            </td>

            <!-- Rating -->
            <td class="table-cell">
              <div class="flex items-center">
                <svg class="w-5 h-5 text-yellow-400 fill-current" viewBox="0 0 20 20">
                  <path d="M10 15l-5.878 3.09 1.123-6.545L.489 6.91l6.572-.955L10 0l2.939 5.955 6.572.955-4.756 4.635 1.123 6.545z"/>
                </svg>
                <span class="ml-1 text-sm font-medium text-gray-900">{{ driver.rating.toFixed(1) }}</span>
              </div>
            </td>

            <!-- Viajes -->
            <td class="table-cell">
              <div class="text-sm text-gray-900">{{ driver.total_rides }}</div>
            </td>

            <!-- Aceptación -->
            <td class="table-cell">
              <div class="text-sm text-gray-900">{{ (driver.acceptance_rate * 100).toFixed(0) }}%</div>
            </td>

            <!-- Ubicación -->
            <td class="table-cell">
              <button @click="showDriverOnMap(driver)" class="text-blue-600 hover:text-blue-800">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
              </button>
            </td>

            <!-- Acciones -->
            <td class="table-cell">
              <div class="flex items-center space-x-2">
                <button @click="viewDriver(driver)" class="btn-icon text-blue-600 hover:text-blue-800">
                  <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                  </svg>
                </button>

                <button @click="editDriver(driver)" class="btn-icon text-green-600 hover:text-green-800">
                  <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                  </svg>
                </button>

                <button @click="deleteDriver(driver)" class="btn-icon text-red-600 hover:text-red-800">
                  <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>

      <!-- Empty State -->
      <div v-if="filteredDrivers.length === 0" class="text-center py-12">
        <svg class="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
        </svg>
        <h3 class="mt-2 text-sm font-medium text-gray-900">No hay conductores</h3>
        <p class="mt-1 text-sm text-gray-500">Comienza agregando un nuevo conductor.</p>
      </div>
    </div>

    <!-- Add Driver Modal -->
    <!-- TODO: Implementar modal de agregar conductor -->
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'

// State
const drivers = ref([])
const stats = ref({
  available: 0,
  busy: 0,
  offline: 0,
  total: 0
})

const filters = ref({
  search: '',
  status: '',
  vehicleType: '',
  rating: ''
})

const showAddDriverModal = ref(false)

// Computed
const filteredDrivers = computed(() => {
  let filtered = drivers.value

  // Buscar por nombre o teléfono
  if (filters.value.search) {
    const search = filters.value.search.toLowerCase()
    filtered = filtered.filter(d =>
      d.name.toLowerCase().includes(search) ||
      d.phone.includes(search)
    )
  }

  // Filtrar por estado
  if (filters.value.status) {
    filtered = filtered.filter(d => d.status === filters.value.status)
  }

  // Filtrar por tipo de vehículo
  if (filters.value.vehicleType) {
    filtered = filtered.filter(d => d.vehicle.type === filters.value.vehicleType)
  }

  // Filtrar por rating
  if (filters.value.rating) {
    const minRating = parseInt(filters.value.rating)
    filtered = filtered.filter(d => d.rating >= minRating)
  }

  return filtered
})

// Methods
function getStatusClass(status) {
  const classes = {
    available: 'bg-green-100 text-green-800',
    busy: 'bg-yellow-100 text-yellow-800',
    offline: 'bg-gray-100 text-gray-800',
    on_break: 'bg-blue-100 text-blue-800'
  }
  return classes[status] || 'bg-gray-100 text-gray-800'
}

function getStatusLabel(status) {
  const labels = {
    available: 'Disponible',
    busy: 'Ocupado',
    offline: 'Offline',
    on_break: 'En descanso'
  }
  return labels[status] || status
}

function showDriverOnMap(driver) {
  // TODO: Abrir mapa centrado en conductor
  console.log('Show driver on map:', driver)
}

function viewDriver(driver) {
  // TODO: Abrir vista detallada del conductor
  console.log('View driver:', driver)
}

function editDriver(driver) {
  // TODO: Abrir modal de edición
  console.log('Edit driver:', driver)
}

function deleteDriver(driver) {
  if (confirm(`¿Estás seguro de eliminar a ${driver.name}?`)) {
    // TODO: Llamar API para eliminar
    console.log('Delete driver:', driver)
  }
}

async function loadDrivers() {
  // TODO: Llamar API real
  // Por ahora, datos de ejemplo
  drivers.value = [
    {
      driver_id: 'driver_001',
      name: 'Juan Pérez',
      phone: '+5215522222001',
      status: 'available',
      rating: 4.9,
      total_rides: 1523,
      acceptance_rate: 0.95,
      vehicle: {
        type: 'sedan',
        brand: 'Nissan',
        model: 'Versa',
        plates: 'ABC-1234',
        color: 'Blanco'
      }
    },
    {
      driver_id: 'driver_002',
      name: 'María González',
      phone: '+5215522222002',
      status: 'busy',
      rating: 4.8,
      total_rides: 892,
      acceptance_rate: 0.92,
      vehicle: {
        type: 'sedan',
        brand: 'Toyota',
        model: 'Corolla',
        plates: 'XYZ-5678',
        color: 'Gris'
      }
    },
    {
      driver_id: 'driver_003',
      name: 'Carlos Ramírez',
      phone: '+5215522222003',
      status: 'offline',
      rating: 4.7,
      total_rides: 654,
      acceptance_rate: 0.88,
      vehicle: {
        type: 'suv',
        brand: 'Mazda',
        model: 'CX-5',
        plates: 'DEF-9012',
        color: 'Negro'
      }
    }
  ]

  // Calcular estadísticas
  stats.value = {
    available: drivers.value.filter(d => d.status === 'available').length,
    busy: drivers.value.filter(d => d.status === 'busy').length,
    offline: drivers.value.filter(d => d.status === 'offline').length,
    total: drivers.value.length
  }
}

// Lifecycle
onMounted(() => {
  loadDrivers()
})
</script>

<style scoped>
.page-header {
  @apply flex justify-between items-center mb-8;
}

.stat-card {
  @apply bg-white rounded-lg shadow p-6 flex items-center space-x-4;
}

.stat-icon {
  @apply rounded-lg p-3;
}

.stat-label {
  @apply text-sm font-medium text-gray-500;
}

.stat-value {
  @apply text-2xl font-bold;
}

.input {
  @apply w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent;
}

.table-header {
  @apply px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider;
}

.table-cell {
  @apply px-6 py-4 whitespace-nowrap;
}

.btn {
  @apply px-4 py-2 rounded-lg font-medium transition-colors flex items-center;
}

.btn-primary {
  @apply bg-blue-600 text-white hover:bg-blue-700;
}

.btn-icon {
  @apply p-1 rounded hover:bg-gray-100 transition-colors;
}
</style>
