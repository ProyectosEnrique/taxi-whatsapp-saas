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

      <!-- Foto del vehículo -->
      <div class="bg-white rounded-lg shadow mb-6 p-6">
        <h3 class="text-lg font-semibold text-gray-900 mb-4">📷 Foto del Vehículo</h3>
        <div class="flex flex-col items-center space-y-3">
          <div class="w-full max-w-xs h-44 bg-gray-100 rounded-xl overflow-hidden flex items-center justify-center border-2 border-dashed border-gray-300">
            <img v-if="photoPreview || vehicle?.photo_url"
              :src="photoPreview || vehicle?.photo_url"
              alt="Foto del vehículo"
              class="w-full h-full object-cover"
            />
            <span v-else class="text-5xl">🚗</span>
          </div>
          <label class="cursor-pointer px-5 py-2 bg-blue-600 text-white text-sm font-semibold rounded-lg hover:bg-blue-700 transition">
            {{ uploadingPhoto ? 'Subiendo...' : 'Seleccionar foto' }}
            <input
              type="file"
              accept="image/jpeg,image/png,image/webp"
              class="hidden"
              :disabled="uploadingPhoto"
              @change="handlePhotoChange"
            />
          </label>
          <p v-if="photoError" class="text-sm text-red-600">{{ photoError }}</p>
          <p class="text-xs text-gray-400">JPG, PNG o WebP · Máx. 5 MB</p>
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

      <!-- Cambiar contraseña -->
      <div class="bg-white rounded-lg shadow mb-6 p-6">
        <h3 class="text-lg font-semibold text-gray-900 mb-4">🔑 Cambiar Contraseña</h3>
        <div class="space-y-3">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Contraseña actual</label>
            <input
              v-model="passwordForm.current"
              type="password"
              placeholder="••••••••"
              class="w-full px-4 py-2.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-400 focus:border-transparent"
            />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Nueva contraseña</label>
            <input
              v-model="passwordForm.newPass"
              type="password"
              placeholder="Mínimo 6 caracteres"
              class="w-full px-4 py-2.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-400 focus:border-transparent"
            />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Confirmar nueva contraseña</label>
            <input
              v-model="passwordForm.confirm"
              type="password"
              placeholder="Repite la nueva contraseña"
              class="w-full px-4 py-2.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-400 focus:border-transparent"
            />
          </div>
          <p v-if="passwordError" class="text-red-600 text-sm">{{ passwordError }}</p>
          <p v-if="passwordSaved" class="text-green-600 text-sm">✓ Contraseña actualizada correctamente</p>
          <button
            @click="changePassword"
            :disabled="changingPassword"
            class="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-semibold py-3 rounded-lg transition"
          >
            {{ changingPassword ? 'Guardando...' : 'Actualizar Contraseña' }}
          </button>
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
import { useToast } from '../composables/useToast'

const { success: toastSuccess, error: toastError } = useToast()

const router = useRouter()
const authStore = useAuthStore()

const driver = computed(() => authStore.driver)
const vehicle = computed(() => driver.value?.vehicle || {})

const editingVehicle = ref(false)
const saving = ref(false)
const uploadingPhoto = ref(false)
const photoPreview = ref(null)
const photoError = ref('')

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

const passwordForm = reactive({ current: '', newPass: '', confirm: '' })
const changingPassword = ref(false)
const passwordSaved = ref(false)
const passwordError = ref('')

const changePassword = async () => {
  passwordError.value = ''
  passwordSaved.value = false
  if (!passwordForm.current || !passwordForm.newPass || !passwordForm.confirm) {
    passwordError.value = 'Completa todos los campos.'
    return
  }
  if (passwordForm.newPass.length < 6) {
    passwordError.value = 'La nueva contraseña debe tener al menos 6 caracteres.'
    return
  }
  if (passwordForm.newPass !== passwordForm.confirm) {
    passwordError.value = 'Las contraseñas no coinciden.'
    return
  }
  changingPassword.value = true
  try {
    await driverApi.changePassword(passwordForm.current, passwordForm.newPass)
    passwordSaved.value = true
    passwordForm.current = ''
    passwordForm.newPass = ''
    passwordForm.confirm = ''
    setTimeout(() => { passwordSaved.value = false }, 4000)
  } catch (e) {
    passwordError.value = e?.response?.data?.detail || 'Error al cambiar contraseña. Verifica la contraseña actual.'
  } finally {
    changingPassword.value = false
  }
}

const handlePhotoChange = async (e) => {
  const file = e.target.files?.[0]
  if (!file) return
  photoError.value = ''
  photoPreview.value = URL.createObjectURL(file)
  uploadingPhoto.value = true
  try {
    const res = await driverApi.uploadVehiclePhoto(file)
    authStore.updateDriverData({ vehicle: { ...vehicle.value, photo_url: res.photo_url } })
    toastSuccess('Foto actualizada')
  } catch (err) {
    photoError.value = err?.response?.data?.detail || 'Error al subir la foto'
    photoPreview.value = null
  } finally {
    uploadingPhoto.value = false
    e.target.value = ''
  }
}

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

    toastSuccess('Vehículo actualizado')
    editingVehicle.value = false
  } catch (err) {
    toastError('Error al actualizar vehículo')
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
