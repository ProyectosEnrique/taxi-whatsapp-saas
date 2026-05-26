<template>
  <div class="min-h-screen flex items-center justify-center bg-gradient-to-br from-taxi-yellow to-yellow-600 px-4">
    <div class="max-w-md w-full">
      <div class="text-center mb-8">
        <div class="inline-flex items-center justify-center w-20 h-20 bg-white rounded-full shadow-lg mb-4">
          <span class="text-4xl">🚕</span>
        </div>
        <h1 class="text-3xl font-bold text-white mb-2">Taxi App</h1>
        <p class="text-yellow-100">Inicia sesión para solicitar tu viaje</p>
      </div>

      <div class="bg-white rounded-2xl shadow-2xl p-8">
        <form @submit.prevent="handleLogin">
          <div class="mb-6">
            <label for="phone" class="block text-sm font-medium text-gray-700 mb-2">
              Teléfono
            </label>
            <div class="relative">
              <span class="absolute inset-y-0 left-0 pl-3 flex items-center text-gray-500">📱</span>
              <input
                id="phone"
                v-model="form.phone"
                type="tel"
                required
                placeholder="+52 55 1234 5678"
                class="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-taxi-yellow focus:border-transparent"
                :disabled="loading"
              />
            </div>
          </div>

          <div class="mb-6">
            <label for="password" class="block text-sm font-medium text-gray-700 mb-2">
              Contraseña
            </label>
            <div class="relative">
              <span class="absolute inset-y-0 left-0 pl-3 flex items-center text-gray-500">🔒</span>
              <input
                id="password"
                v-model="form.password"
                :type="showPassword ? 'text' : 'password'"
                required
                placeholder="Ingresa tu contraseña"
                class="w-full pl-10 pr-12 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-taxi-yellow focus:border-transparent"
                :disabled="loading"
              />
              <button
                type="button"
                @click="showPassword = !showPassword"
                class="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-500"
              >
                {{ showPassword ? '👁️' : '👁️‍🗨️' }}
              </button>
            </div>
          </div>

          <div v-if="passwordResetSuccess" class="mb-4 p-3 bg-green-50 border border-green-200 rounded-lg">
            <p class="text-sm text-green-700 flex items-center">
              <span class="mr-2">✅</span>
              Contraseña actualizada. Ya puedes iniciar sesión.
            </p>
          </div>

          <div v-if="error" class="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
            <p class="text-sm text-red-600 flex items-center">
              <span class="mr-2">⚠️</span>
              {{ error }}
            </p>
          </div>

          <button
            type="submit"
            :disabled="loading"
            class="w-full bg-taxi-yellow hover:bg-yellow-500 text-white font-semibold py-3 rounded-lg transition duration-200 disabled:opacity-50"
          >
            <span v-if="!loading">Iniciar Sesión</span>
            <span v-else>Iniciando...</span>
          </button>
        </form>

        <div class="mt-4 text-center">
          <router-link
            to="/forgot-password"
            class="text-sm text-gray-500 hover:text-taxi-yellow hover:underline"
          >
            ¿Olvidaste tu contraseña?
          </router-link>
        </div>

        <div class="mt-4 text-center">
          <p class="text-sm text-gray-600">
            ¿No tienes cuenta?
            <router-link to="/register" class="text-taxi-yellow hover:underline font-semibold">
              Regístrate
            </router-link>
          </p>
        </div>
      </div>

      <div class="mt-6 text-center">
        <p class="text-sm text-yellow-100">© 2024 Taxi App. Todos los derechos reservados.</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '../stores/authStore'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const form = reactive({
  phone: '',
  password: ''
})

const showPassword = ref(false)
const loading = ref(false)
const error = ref(null)
const passwordResetSuccess = ref(route.query.reset === '1')

const handleLogin = async () => {
  loading.value = true
  error.value = null

  try {
    const result = await authStore.login(form.phone, form.password)

    if (result.success) {
      router.push('/home')
    } else {
      error.value = result.error || 'Error al iniciar sesión'
    }
  } catch (err) {
    error.value = 'Error de conexión. Por favor, intenta de nuevo.'
  } finally {
    loading.value = false
  }
}
</script>
