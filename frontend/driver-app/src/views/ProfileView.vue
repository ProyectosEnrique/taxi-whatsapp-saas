<template>
  <div class="min-h-screen bg-gray-50">
    <!-- Header -->
    <header class="bg-white shadow-sm sticky top-0 z-10">
      <div class="max-w-7xl mx-auto px-4 py-4">
        <div class="flex items-center space-x-4">
          <button
            @click="goBack"
            class="p-2 hover:bg-gray-100 rounded-lg"
          >
            <span class="text-2xl">←</span>
          </button>
          <div class="flex-1">
            <h1 class="text-xl font-bold text-gray-900">Mi Perfil</h1>
            <p class="text-sm text-gray-500">Información personal y configuración</p>
          </div>
        </div>
      </div>
    </header>

    <!-- Contenido -->
    <main class="max-w-7xl mx-auto px-4 py-6">
      <!-- Información del conductor -->
      <div class="bg-white rounded-lg shadow mb-6 p-6">
        <div class="flex items-start space-x-6">
          <!-- Foto de perfil -->
          <div class="flex-shrink-0">
            <div class="w-24 h-24 bg-gray-200 rounded-full flex items-center justify-center text-5xl">
              👤
            </div>
            <button class="mt-2 text-sm text-blue-600 hover:underline">
              Cambiar foto
            </button>
          </div>

          <!-- Información básica -->
          <div class="flex-1">
            <h2 class="text-2xl font-bold text-gray-900 mb-2">{{ driver?.name || 'Conductor' }}</h2>
            <div class="space-y-1 text-gray-600">
              <p>📱 {{ driver?.phone || 'N/A' }}</p>
              <p>📧 {{ driver?.email || 'N/A' }}</p>
              <p>🆔 ID: {{ driver?.driver_id || 'N/A' }}</p>
            </div>

            <!-- Estadísticas -->
            <div class="mt-4 flex items-center space-x-6">
              <div>
                <p class="text-sm text-gray-500">Calificación</p>
                <p class="text-xl font-bold text-yellow-500">⭐ {{ driver?.rating?.toFixed(1) || '5.0' }}</p>
              </div>
              <div>
                <p class="text-sm text-gray-500">Viajes Totales</p>
                <p class="text-xl font-bold text-gray-900">{{ driver?.total_rides || 0 }}</p>
              </div>
              <div>
                <p class="text-sm text-gray-500">Aceptación</p>
                <p class="text-xl font-bold text-green-600">{{ ((driver?.acceptance_rate || 1) * 100).toFixed(0) }}%</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Información del vehículo -->
      <div class="bg-white rounded-lg shadow mb-6 p-6">
        <div class="flex items-center justify-between mb-4">
          <h3 class="text-lg font-semibold text-gray-900">🚗 Vehículo</h3>
          <button
            @click="editingVehicle = !editingVehicle"
            class="text-blue-600 hover:underline text-sm"
          >
            {{ editingVehicle ? 'Cancelar' : 'Editar' }}
          </button>
        </div>

        <div v-if="!editingVehicle" class="space-y-3">
          <div class="flex items-center justify-between">
            <span class="text-gray-600">Marca y Modelo</span>
            <span class="font-medium text-gray-900">{{ vehicle?.brand }} {{ vehicle?.model }}</span>
          </div>
          <div class="flex items-center justify-between">
            <span class="text-gray-600">Año</span>
            <span class="font-medium text-gray-900">{{ vehicle?.year }}</span>
          </div>
          <div class="flex items-center justify-between">
            <span class="text-gray-600">Placas</span>
            <span class="font-medium text-gray-900">{{ vehicle?.plates }}</span>
          </div>
          <div class="flex items-center justify-between">
            <span class="text-gray-600">Color</span>
            <span class="font-medium text-gray-900">{{ vehicle?.color }}</span>
          </div>
          <div class="flex items-center justify-between">
            <span class="text-gray-600">Tipo</span>
            <span class="font-medium text-gray-900 capitalize">{{ vehicle?.type }}</span>
          </div>
        </div>

        <form v-else @submit.prevent="saveVehicle" class="space-y-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Marca</label>
            <input
              v-model="vehicleForm.brand"
              type="text"
              required
              class="w-full border border-gray-300 rounded-lg px-3 py-2"
            />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Modelo</label>
            <input
              v-model="vehicleForm.model"
              type="text"
              required
              class="w-full border border-gray-300 rounded-lg px-3 py-2"
            />
          </div>
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Año</label>
              <input
                v-model.number="vehicleForm.year"
                type="number"
                required
                class="w-full border border-gray-300 rounded-lg px-3 py-2"
              />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Color</label>
              <input
                v-model="vehicleForm.color"
                type="text"
                required
                class="w-full border border-gray-300 rounded-lg px-3 py-2"
              />
            </div>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Placas</label>
            <input
              v-model="vehicleForm.plates"
              type="text"
              required
              class="w-full border border-gray-300 rounded-lg px-3 py-2"
            />
          </div>
          <button
            type="submit"
            :disabled="saving"
            class="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2 rounded-lg disabled:opacity-50"
          >
            {{ saving ? 'Guardando...' : 'Guardar Cambios' }}
          </button>
        </form>
      </div>

      <!-- Documentos -->
      <div class="bg-white rounded-lg shadow mb-6 p-6">
        <h3 class="text-lg font-semibold text-gray-900 mb-4">📄 Documentos</h3>
        <div class="space-y-3">
          <div class="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
            <div class="flex items-center space-x-3">
              <span class="text-2xl">🪪</span>
              <div>
                <p class="font-medium text-gray-900">Licencia de Conducir</p>
                <p class="text-sm text-green-600">✓ Verificada</p>
              </div>
            </div>
            <button class="text-blue-600 hover:underline text-sm">Ver</button>
          </div>

          <div class="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
            <div class="flex items-center space-x-3">
              <span class="text-2xl">📋</span>
              <div>
                <p class="font-medium text-gray-900">Seguro del Vehículo</p>
                <p class="text-sm text-green-600">✓ Verificado</p>
              </div>
            </div>
            <button class="text-blue-600 hover:underline text-sm">Ver</button>
          </div>

          <div class="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
            <div class="flex items-center space-x-3">
              <span class="text-2xl">🚗</span>
              <div>
                <p class="font-medium text-gray-900">Tarjeta de Circulación</p>
                <p class="text-sm text-green-600">✓ Verificada</p>
              </div>
            </div>
            <button class="text-blue-600 hover:underline text-sm">Ver</button>
          </div>
        </div>
      </div>

      <!-- Configuración -->
      <div class="bg-white rounded-lg shadow mb-6 p-6">
        <h3 class="text-lg font-semibold text-gray-900 mb-4">⚙️ Configuración</h3>
        <div class="space-y-4">
          <!-- Notificaciones -->
          <div class="flex items-center justify-between">
            <div>
              <p class="font-medium text-gray-900">Notificaciones Push</p>
              <p class="text-sm text-gray-500">Recibe alertas de nuevos viajes</p>
            </div>
            <label class="relative inline-flex items-center cursor-pointer">
              <input
                v-model="settings.pushNotifications"
                type="checkbox"
                class="sr-only peer"
                @change="saveSettings"
              />
              <div class="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
            </label>
          </div>

          <!-- Sonido -->
          <div class="flex items-center justify-between">
            <div>
              <p class="font-medium text-gray-900">Sonido de Notificaciones</p>
              <p class="text-sm text-gray-500">Reproducir sonido al recibir viajes</p>
            </div>
            <label class="relative inline-flex items-center cursor-pointer">
              <input
                v-model="settings.sound"
                type="checkbox"
                class="sr-only peer"
                @change="saveSettings"
              />
              <div class="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
            </label>
          </div>

          <!-- Navegación automática -->
          <div class="flex items-center justify-between">
            <div>
              <p class="font-medium text-gray-900">Navegación Automática</p>
              <p class="text-sm text-gray-500">Abrir Google Maps automáticamente</p>
            </div>
            <label class="relative inline-flex items-center cursor-pointer">
              <input
                v-model="settings.autoNavigation"
                type="checkbox"
                class="sr-only peer"
                @change="saveSettings"
              />
              <div class="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
            </label>
          </div>
        </div>
      </div>

      <!-- Soporte y ayuda -->
      <div class="bg-white rounded-lg shadow mb-6 p-6">
        <h3 class="text-lg font-semibold text-gray-900 mb-4">🆘 Soporte y Ayuda</h3>
        <div class="space-y-3">
          <a href="#" class="flex items-center justify-between p-3 hover:bg-gray-50 rounded-lg">
            <span class="text-gray-900">❓ Preguntas Frecuentes</span>
            <span class="text-gray-400">→</span>
          </a>
          <a href="#" class="flex items-center justify-between p-3 hover:bg-gray-50 rounded-lg">
            <span class="text-gray-900">📞 Contactar Soporte</span>
            <span class="text-gray-400">→</span>
          </a>
          <a href="#" class="flex items-center justify-between p-3 hover:bg-gray-50 rounded-lg">
            <span class="text-gray-900">📖 Guía del Conductor</span>
            <span class="text-gray-400">→</span>
          </a>
          <a href="#" class="flex items-center justify-between p-3 hover:bg-gray-50 rounded-lg">
            <span class="text-gray-900">📜 Términos y Condiciones</span>
            <span class="text-gray-400">→</span>
          </a>
          <a href="#" class="flex items-center justify-between p-3 hover:bg-gray-50 rounded-lg">
            <span class="text-gray-900">🔒 Política de Privacidad</span>
            <span class="text-gray-400">→</span>
          </a>
        </div>
      </div>

      <!-- Cerrar sesión -->
      <div class="bg-white rounded-lg shadow p-6">
        <button
          @click="handleLogout"
          class="w-full bg-red-500 hover:bg-red-600 text-white font-semibold py-3 rounded-lg transition"
        >
          🚪 Cerrar Sesión
        </button>
      </div>

      <!-- Versión -->
      <div class="mt-6 text-center text-sm text-gray-500">
        <p>Versión 1.0.0</p>
        <p class="mt-1">© 2024 Taxi App. Todos los derechos reservados.</p>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/authStore'
import { driverApi } from '../services/api'

const router = useRouter()
const authStore = useAuthStore()

const driver = computed(() => authStore.driver)
const vehicle = computed(() => driver.value?.vehicle || {})

const editingVehicle = ref(false)
const saving = ref(false)

const vehicleForm = reactive({
  brand: '',
  model: '',
  year: 2024,
  color: '',
  plates: '',
  type: 'sedan'
})

const settings = reactive({
  pushNotifications: true,
  sound: true,
  autoNavigation: false
})

const loadVehicleForm = () => {
  if (vehicle.value) {
    vehicleForm.brand = vehicle.value.brand || ''
    vehicleForm.model = vehicle.value.model || ''
    vehicleForm.year = vehicle.value.year || 2024
    vehicleForm.color = vehicle.value.color || ''
    vehicleForm.plates = vehicle.value.plates || ''
    vehicleForm.type = vehicle.value.type || 'sedan'
  }
}

const saveVehicle = async () => {
  saving.value = true

  try {
    await driverApi.updateProfile({
      vehicle: vehicleForm
    })

    // Actualizar en el store
    authStore.updateDriverData({
      vehicle: { ...vehicleForm }
    })

    alert('Vehículo actualizado exitosamente')
    editingVehicle.value = false
  } catch (err) {
    alert('Error al actualizar vehículo')
  } finally {
    saving.value = false
  }
}

const saveSettings = () => {
  // Guardar en localStorage
  localStorage.setItem('driver_settings', JSON.stringify(settings))
}

const loadSettings = () => {
  const saved = localStorage.getItem('driver_settings')
  if (saved) {
    Object.assign(settings, JSON.parse(saved))
  }
}

const handleLogout = async () => {
  if (confirm('¿Estás seguro de cerrar sesión?')) {
    await authStore.logout()
    router.push('/login')
  }
}

const goBack = () => {
  router.push('/dashboard')
}

onMounted(() => {
  loadVehicleForm()
  loadSettings()
})
</script>
