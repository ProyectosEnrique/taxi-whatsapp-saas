<template>
  <!-- Gate de autenticación -->
  <div v-if="!authenticated" class="min-h-screen bg-gray-900 flex items-center justify-center p-4">
    <div class="bg-white rounded-2xl shadow-2xl w-full max-w-sm p-8">
      <div class="text-center mb-8">
        <span class="text-5xl">🚕</span>
        <h1 class="text-2xl font-bold text-gray-900 mt-3">TaxiAdmin</h1>
        <p class="text-gray-500 text-sm mt-1">Panel de Control</p>
      </div>
      <form @submit.prevent="tryLogin">
        <label class="block text-sm font-medium text-gray-700 mb-1">Contraseña</label>
        <input
          v-model="password"
          type="password"
          placeholder="••••••••"
          autofocus
          class="w-full px-4 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-yellow-400 mb-3"
        />
        <p v-if="loginError" class="text-red-600 text-sm mb-3">{{ loginError }}</p>
        <button
          type="submit"
          :disabled="checking"
          class="w-full py-2.5 bg-yellow-500 hover:bg-yellow-600 text-gray-900 font-semibold rounded-lg transition disabled:opacity-50"
        >
          {{ checking ? 'Verificando...' : 'Entrar' }}
        </button>
      </form>
    </div>
  </div>

  <!-- Panel completo -->
  <div v-else id="app" class="flex min-h-screen bg-gray-100">
    <!-- Sidebar -->
    <aside class="w-64 bg-gray-900 text-white flex flex-col flex-shrink-0">
      <div class="px-6 py-5 border-b border-gray-700">
        <div class="flex items-center space-x-3">
          <span class="text-3xl">🚕</span>
          <div>
            <h1 class="text-lg font-bold leading-tight">TaxiAdmin</h1>
            <p class="text-xs text-gray-400">Panel de Control</p>
          </div>
        </div>
      </div>

      <nav class="flex-1 px-3 py-4 space-y-1">
        <router-link
          v-for="item in navItems"
          :key="item.to"
          :to="item.to"
          class="flex items-center space-x-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors"
          :class="$route.path === item.to
            ? 'bg-yellow-500 text-gray-900'
            : 'text-gray-300 hover:bg-gray-800 hover:text-white'"
        >
          <span class="text-lg">{{ item.icon }}</span>
          <span>{{ item.label }}</span>
          <span
            v-if="item.badge"
            class="ml-auto bg-red-500 text-white text-xs font-bold px-1.5 py-0.5 rounded-full"
          >{{ item.badge }}</span>
        </router-link>
      </nav>

      <div class="px-4 py-4 border-t border-gray-700 text-xs text-gray-500 flex items-center justify-between">
        <span>v1.0 · {{ today }}</span>
        <button @click="logout" class="text-gray-400 hover:text-white transition text-xs">Salir</button>
      </div>
    </aside>

    <main class="flex-1 overflow-auto">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const authenticated = ref(false)
const password = ref('')
const loginError = ref('')
const checking = ref(false)

const today = computed(() =>
  new Date().toLocaleDateString('es-MX', { day: 'numeric', month: 'short' })
)

const navItems = [
  { to: '/',          icon: '📊', label: 'Dashboard' },
  { to: '/drivers',    icon: '🚗', label: 'Conductores' },
  { to: '/drivers-qr', icon: '📲', label: 'QR Taxis' },
  { to: '/map',       icon: '🗺️', label: 'Mapa de Flota' },
  { to: '/reports',   icon: '📈', label: 'Reportes' },
  { to: '/rides',     icon: '🛣️', label: 'Monitor de Viajes' },
  { to: '/incidents', icon: '🚨', label: 'Incidentes' },
  { to: '/fares',     icon: '💰', label: 'Tarifas' },
  { to: '/promos',    icon: '🏷️', label: 'Promociones' },
]

// Parchea window.fetch globalmente para inyectar x-admin-key en
// todas las llamadas a /api/v1/admin sin tocar cada componente.
function patchFetch(key) {
  const _orig = window._origFetch || window.fetch
  window._origFetch = _orig
  window.fetch = (input, init = {}) => {
    const url = typeof input === 'string' ? input : input?.url || ''
    if (url.includes('/api/v1/admin')) {
      init.headers = { ...(init.headers || {}), 'x-admin-key': key }
    }
    return _orig(input, init)
  }
}

async function tryLogin() {
  if (!password.value) return
  checking.value = true
  loginError.value = ''
  try {
    const res = await fetch('/api/v1/admin/stats', {
      headers: { 'x-admin-key': password.value },
    })
    if (res.ok) {
      localStorage.setItem('admin_key', password.value)
      patchFetch(password.value)
      authenticated.value = true
    } else {
      loginError.value = 'Contraseña incorrecta'
    }
  } catch {
    loginError.value = 'Error de conexión'
  } finally {
    checking.value = false
  }
}

function logout() {
  localStorage.removeItem('admin_key')
  authenticated.value = false
  password.value = ''
}

onMounted(() => {
  const saved = localStorage.getItem('admin_key')
  if (saved) {
    patchFetch(saved)
    authenticated.value = true
  }
})
</script>
