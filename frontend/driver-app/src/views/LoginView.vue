<template>
  <div class="min-h-screen flex items-center justify-center bg-gradient-to-br from-taxi-yellow to-yellow-600 px-4">
    <div class="max-w-md w-full">
      <!-- Logo y título -->
      <div class="text-center mb-8">
        <div class="inline-flex items-center justify-center w-20 h-20 bg-white rounded-full shadow-lg mb-4">
          <span class="text-4xl">🚕</span>
        </div>
        <h1 class="text-3xl font-bold text-white mb-2">Conductor App</h1>
        <p class="text-yellow-100">Inicia sesión para comenzar tu turno</p>
      </div>

      <!-- Formulario de login -->
      <div class="bg-white rounded-2xl shadow-2xl p-8">
        <form @submit.prevent="handleLogin">
          <!-- Campo de teléfono -->
          <div class="mb-6">
            <label for="phone" class="block text-sm font-medium text-gray-700 mb-2">
              Número de teléfono
            </label>
            <div class="relative">
              <span class="absolute inset-y-0 left-0 pl-3 flex items-center text-gray-500">
                📱
              </span>
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

          <!-- Campo de contraseña -->
          <div class="mb-6">
            <label for="password" class="block text-sm font-medium text-gray-700 mb-2">
              Contraseña
            </label>
            <div class="relative">
              <span class="absolute inset-y-0 left-0 pl-3 flex items-center text-gray-500">
                🔒
              </span>
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
                class="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-500 hover:text-gray-700"
              >
                {{ showPassword ? '👁️' : '👁️‍🗨️' }}
              </button>
            </div>
          </div>

          <!-- Error message -->
          <div v-if="error" class="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
            <p class="text-sm text-red-600 flex items-center">
              <span class="mr-2">⚠️</span>
              {{ error }}
            </p>
          </div>

          <!-- Recordar sesión -->
          <div class="flex items-center mb-6">
            <input
              id="remember"
              v-model="form.remember"
              type="checkbox"
              class="w-4 h-4 text-taxi-yellow border-gray-300 rounded focus:ring-taxi-yellow"
            />
            <label for="remember" class="ml-2 block text-sm text-gray-700">
              Mantener sesión iniciada
            </label>
          </div>

          <!-- Botón de login -->
          <button
            type="submit"
            :disabled="loading"
            class="w-full bg-taxi-yellow hover:bg-yellow-500 text-white font-semibold py-3 rounded-lg transition duration-200 flex items-center justify-center disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <span v-if="!loading">Iniciar Sesión</span>
            <span v-else class="flex items-center">
              <svg class="animate-spin h-5 w-5 mr-2" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              Iniciando...
            </span>
          </button>
        </form>

        <!-- Enlaces adicionales -->
        <div class="mt-6 text-center">
          <a href="#" class="text-sm text-gray-600 hover:text-taxi-yellow">
            ¿Olvidaste tu contraseña?
          </a>
        </div>

        <!-- Información de contacto -->
        <div class="mt-8 pt-6 border-t border-gray-200 text-center">
          <p class="text-xs text-gray-500 mb-2">¿Problemas para iniciar sesión?</p>
          <a href="#" class="text-sm text-taxi-yellow hover:underline">
            Contacta a soporte
          </a>
        </div>
      </div>

      <!-- Footer -->
      <div class="mt-6 text-center">
        <p class="text-sm text-yellow-100">
          © 2024 Taxi App. Todos los derechos reservados.
        </p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/authStore'

const router = useRouter()
const authStore = useAuthStore()

const form = reactive({
  phone: '',
  password: '',
  remember: false
})

const showPassword = ref(false)
const loading = ref(false)
const error = ref(null)

const handleLogin = async () => {
  loading.value = true
  error.value = null

  try {
    const result = await authStore.login(form.phone, form.password)

    if (result.success) {
      // Login exitoso, redirigir al dashboard
      router.push('/dashboard')
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

<style scoped>
/* Animación personalizada */
@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.bg-white {
  animation: fadeIn 0.5s ease-out;
}
</style>
