<template>
  <div class="min-h-screen bg-gray-50">
    <header class="bg-white shadow-sm sticky top-0 z-10">
      <div class="max-w-7xl mx-auto px-4 py-4">
        <div class="flex items-center space-x-4">
          <button @click="goBack" class="p-2 hover:bg-gray-100 rounded-lg">
            <span class="text-2xl">←</span>
          </button>
          <div class="flex-1">
            <h1 class="text-xl font-bold text-gray-900">Mi Perfil</h1>
            <p class="text-sm text-gray-500">Información personal y configuración</p>
          </div>
        </div>
      </div>
    </header>

    <main class="max-w-7xl mx-auto px-4 py-6">
      <div class="bg-white rounded-lg shadow mb-6 p-6">
        <div class="flex items-start space-x-6">
          <div class="flex-shrink-0">
            <div class="w-24 h-24 bg-gray-200 rounded-full flex items-center justify-center text-5xl">
              👤
            </div>
            <button class="mt-2 text-sm text-blue-600 hover:underline">Cambiar foto</button>
          </div>

          <div class="flex-1">
            <h2 class="text-2xl font-bold text-gray-900 mb-2">{{ customer?.name || 'Usuario' }}</h2>
            <div class="space-y-1 text-gray-600">
              <p>📱 {{ customer?.phone || 'N/A' }}</p>
              <p v-if="customer?.email">📧 {{ customer.email }}</p>
            </div>

            <div class="mt-4 flex items-center space-x-6">
              <div>
                <p class="text-sm text-gray-500">Viajes realizados</p>
                <p class="text-xl font-bold text-gray-900">{{ customer?.total_rides || 0 }}</p>
              </div>
              <div>
                <p class="text-sm text-gray-500">Calificación</p>
                <p class="text-xl font-bold text-yellow-500">⭐ {{ customer?.rating?.toFixed(1) || '5.0' }}</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="bg-white rounded-lg shadow mb-6 p-6">
        <h3 class="text-lg font-semibold text-gray-900 mb-4">🏠 Lugares Favoritos</h3>

        <div v-if="favoriteLocations.length === 0" class="text-center py-8 text-gray-500">
          <p class="mb-3">No tienes lugares favoritos guardados</p>
          <button @click="addFavorite('home')" class="text-blue-600 hover:underline font-medium">
            + Agregar Casa
          </button>
        </div>

        <div v-else class="space-y-3">
          <div
            v-for="favorite in favoriteLocations"
            :key="favorite.id"
            class="flex items-center justify-between p-4 border border-gray-200 rounded-lg"
          >
            <div class="flex items-center space-x-3">
              <span class="text-3xl">{{ favorite.type === 'home' ? '🏠' : favorite.type === 'work' ? '💼' : '⭐' }}</span>
              <div>
                <p class="font-semibold text-gray-900">
                  {{ favorite.type === 'home' ? 'Casa' : favorite.type === 'work' ? 'Trabajo' : favorite.name }}
                </p>
                <p class="text-sm text-gray-600">{{ favorite.address }}</p>
              </div>
            </div>
            <button @click="deleteFavorite(favorite.id)" class="text-red-600 hover:text-red-700 p-2">
              🗑️
            </button>
          </div>
        </div>

        <button
          v-if="favoriteLocations.length < 5"
          @click="showAddFavorite = true"
          class="mt-4 w-full py-3 border-2 border-dashed border-gray-300 rounded-lg text-gray-600 hover:border-taxi-yellow hover:text-taxi-yellow"
        >
          + Agregar Lugar Favorito
        </button>
      </div>

      <div class="bg-white rounded-lg shadow mb-6 p-6">
        <h3 class="text-lg font-semibold text-gray-900 mb-4">⚙️ Configuración</h3>
        <div class="space-y-4">
          <div class="flex items-center justify-between">
            <div>
              <p class="font-medium text-gray-900">Notificaciones</p>
              <p class="text-sm text-gray-500">Recibe alertas de tus viajes</p>
            </div>
            <label class="relative inline-flex items-center cursor-pointer">
              <input v-model="settings.notifications" type="checkbox" class="sr-only peer" />
              <div class="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
            </label>
          </div>

          <div class="flex items-center justify-between">
            <div>
              <p class="font-medium text-gray-900">Guardar ubicaciones</p>
              <p class="text-sm text-gray-500">Guarda tus búsquedas recientes</p>
            </div>
            <label class="relative inline-flex items-center cursor-pointer">
              <input v-model="settings.saveLocations" type="checkbox" class="sr-only peer" />
              <div class="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
            </label>
          </div>
        </div>
      </div>

      <div class="bg-white rounded-lg shadow mb-6 p-6">
        <h3 class="text-lg font-semibold text-gray-900 mb-4">💳 Pagos</h3>
        <router-link to="/payment" class="flex items-center justify-between p-3 hover:bg-gray-50 rounded-lg">
          <span class="text-gray-900">Métodos de pago</span>
          <span class="text-gray-400">→</span>
        </router-link>
      </div>

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
            <span class="text-gray-900">📜 Términos y Condiciones</span>
            <span class="text-gray-400">→</span>
          </a>
          <a href="#" class="flex items-center justify-between p-3 hover:bg-gray-50 rounded-lg">
            <span class="text-gray-900">🔒 Política de Privacidad</span>
            <span class="text-gray-400">→</span>
          </a>
        </div>
      </div>

      <div class="bg-white rounded-lg shadow p-6">
        <button
          @click="handleLogout"
          class="w-full bg-red-500 hover:bg-red-600 text-white font-semibold py-3 rounded-lg transition"
        >
          🚪 Cerrar Sesión
        </button>
      </div>

      <div class="mt-6 text-center text-sm text-gray-500">
        <p>Versión 1.0.0</p>
        <p class="mt-1">© 2024 Taxi App. Todos los derechos reservados.</p>
      </div>
    </main>

    <div v-if="showAddFavorite" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4" @click.self="showAddFavorite = false">
      <div class="bg-white rounded-lg shadow-2xl max-w-md w-full p-6">
        <h3 class="text-xl font-bold text-gray-900 mb-4">Agregar Lugar Favorito</h3>

        <form @submit.prevent="saveFavorite">
          <div class="mb-4">
            <label class="block text-sm font-medium text-gray-700 mb-2">Tipo</label>
            <select
              v-model="newFavorite.type"
              class="w-full px-4 py-3 border border-gray-300 rounded-lg"
              required
            >
              <option value="home">🏠 Casa</option>
              <option value="work">💼 Trabajo</option>
              <option value="other">⭐ Otro</option>
            </select>
          </div>

          <div v-if="newFavorite.type === 'other'" class="mb-4">
            <label class="block text-sm font-medium text-gray-700 mb-2">Nombre</label>
            <input
              v-model="newFavorite.name"
              type="text"
              placeholder="Ej: Gimnasio, Casa de mamá"
              class="w-full px-4 py-3 border border-gray-300 rounded-lg"
              required
            />
          </div>

          <div class="mb-4">
            <label class="block text-sm font-medium text-gray-700 mb-2">Dirección</label>
            <input
              v-model="newFavorite.address"
              type="text"
              placeholder="Ingresa la dirección completa"
              class="w-full px-4 py-3 border border-gray-300 rounded-lg"
              required
            />
          </div>

          <div class="flex space-x-3">
            <button
              type="button"
              @click="showAddFavorite = false"
              class="flex-1 bg-gray-200 hover:bg-gray-300 text-gray-700 font-semibold py-3 rounded-lg"
            >
              Cancelar
            </button>
            <button
              type="submit"
              class="flex-1 bg-taxi-blue text-white font-semibold py-3 rounded-lg hover:bg-blue-600"
            >
              Guardar
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/authStore'
import { useLocationStore } from '../stores/locationStore'

const router = useRouter()
const authStore = useAuthStore()
const locationStore = useLocationStore()

const customer = computed(() => authStore.customer)
const favoriteLocations = computed(() => locationStore.favoriteLocations)

const showAddFavorite = ref(false)
const settings = reactive({
  notifications: true,
  saveLocations: true
})

const newFavorite = reactive({
  type: 'home',
  name: '',
  address: ''
})

const saveFavorite = async () => {
  const location = {
    lat: 0,
    lon: 0,
    address: newFavorite.address
  }

  await locationStore.saveFavoriteLocation(
    location,
    newFavorite.type,
    newFavorite.name
  )

  showAddFavorite.value = false
  newFavorite.type = 'home'
  newFavorite.name = ''
  newFavorite.address = ''
}

const deleteFavorite = (id) => {
  if (confirm('¿Eliminar este lugar favorito?')) {
    locationStore.deleteFavoriteLocation(id)
  }
}

const handleLogout = async () => {
  if (confirm('¿Estás seguro de cerrar sesión?')) {
    await authStore.logout()
    router.push('/login')
  }
}

const goBack = () => {
  router.push('/home')
}

onMounted(() => {
  locationStore.loadFavoriteLocations()

  const savedSettings = localStorage.getItem('customer_settings')
  if (savedSettings) {
    Object.assign(settings, JSON.parse(savedSettings))
  }
})
</script>
