<template>
  <div class="min-h-screen flex items-center justify-center bg-gradient-to-br from-taxi-yellow to-yellow-600 px-4">
    <div class="max-w-md w-full">
      <div class="text-center mb-8">
        <div class="inline-flex items-center justify-center w-20 h-20 bg-white rounded-full shadow-lg mb-4">
          <span class="text-4xl">🔑</span>
        </div>
        <h1 class="text-3xl font-bold text-white mb-2">Recuperar contraseña</h1>
        <p class="text-yellow-100">
          {{ step === 1 ? 'Te enviaremos un código por WhatsApp' : 'Ingresa el código que recibiste' }}
        </p>
      </div>

      <div class="bg-white rounded-2xl shadow-2xl p-8">

        <!-- Paso 1: ingresar teléfono -->
        <form v-if="step === 1" @submit.prevent="handleRequestCode">
          <div class="mb-6">
            <label for="phone" class="block text-sm font-medium text-gray-700 mb-2">
              Número de teléfono registrado
            </label>
            <div class="relative">
              <span class="absolute inset-y-0 left-0 pl-3 flex items-center text-gray-500">📱</span>
              <input
                id="phone"
                v-model="phone"
                type="tel"
                required
                placeholder="+52 55 1234 5678"
                class="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-taxi-yellow focus:border-transparent"
                :disabled="loading"
              />
            </div>
          </div>

          <div v-if="error" class="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
            <p class="text-sm text-red-600 flex items-center">
              <span class="mr-2">⚠️</span>{{ error }}
            </p>
          </div>

          <button
            type="submit"
            :disabled="loading"
            class="w-full bg-taxi-yellow hover:bg-yellow-500 text-white font-semibold py-3 rounded-lg transition duration-200 disabled:opacity-50"
          >
            <span v-if="!loading">Enviar código por WhatsApp</span>
            <span v-else>Enviando...</span>
          </button>
        </form>

        <!-- Paso 2: ingresar código + nueva contraseña -->
        <form v-else @submit.prevent="handleResetPassword">
          <div class="mb-4 p-3 bg-green-50 border border-green-200 rounded-lg">
            <p class="text-sm text-green-700">
              Código enviado al número <strong>{{ phone }}</strong>. Revisa tu WhatsApp.
            </p>
          </div>

          <div class="mb-5">
            <label for="code" class="block text-sm font-medium text-gray-700 mb-2">
              Código de verificación (6 dígitos)
            </label>
            <input
              id="code"
              v-model="code"
              type="text"
              inputmode="numeric"
              maxlength="6"
              required
              placeholder="123456"
              class="w-full text-center text-2xl tracking-widest px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-taxi-yellow focus:border-transparent"
              :disabled="loading"
            />
          </div>

          <div class="mb-5">
            <label for="newPassword" class="block text-sm font-medium text-gray-700 mb-2">
              Nueva contraseña
            </label>
            <div class="relative">
              <span class="absolute inset-y-0 left-0 pl-3 flex items-center text-gray-500">🔒</span>
              <input
                id="newPassword"
                v-model="newPassword"
                :type="showPassword ? 'text' : 'password'"
                required
                minlength="6"
                placeholder="Mínimo 6 caracteres"
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

          <div class="mb-5">
            <label for="confirmPassword" class="block text-sm font-medium text-gray-700 mb-2">
              Confirmar nueva contraseña
            </label>
            <div class="relative">
              <span class="absolute inset-y-0 left-0 pl-3 flex items-center text-gray-500">🔒</span>
              <input
                id="confirmPassword"
                v-model="confirmPassword"
                :type="showPassword ? 'text' : 'password'"
                required
                placeholder="Repite la contraseña"
                class="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-taxi-yellow focus:border-transparent"
                :disabled="loading"
              />
            </div>
          </div>

          <div v-if="error" class="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
            <p class="text-sm text-red-600 flex items-center">
              <span class="mr-2">⚠️</span>{{ error }}
            </p>
          </div>

          <button
            type="submit"
            :disabled="loading"
            class="w-full bg-taxi-yellow hover:bg-yellow-500 text-white font-semibold py-3 rounded-lg transition duration-200 disabled:opacity-50"
          >
            <span v-if="!loading">Cambiar contraseña</span>
            <span v-else>Actualizando...</span>
          </button>

          <button
            type="button"
            @click="step = 1; error = null"
            class="w-full mt-3 text-sm text-gray-500 hover:text-gray-700 underline"
          >
            Usar otro número / reenviar código
          </button>
        </form>

        <div class="mt-6 text-center">
          <router-link to="/login" class="text-sm text-taxi-yellow hover:underline font-semibold">
            Volver al inicio de sesión
          </router-link>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { authApi } from '../services/api'

const router = useRouter()

const step = ref(1)
const phone = ref('')
const code = ref('')
const newPassword = ref('')
const confirmPassword = ref('')
const showPassword = ref(false)
const loading = ref(false)
const error = ref(null)

const handleRequestCode = async () => {
  loading.value = true
  error.value = null
  try {
    await authApi.forgotPassword(phone.value.trim())
    step.value = 2
  } catch (err) {
    error.value = err.response?.data?.detail || 'Error al enviar el código. Intenta de nuevo.'
  } finally {
    loading.value = false
  }
}

const handleResetPassword = async () => {
  error.value = null
  if (newPassword.value !== confirmPassword.value) {
    error.value = 'Las contraseñas no coinciden'
    return
  }
  if (newPassword.value.length < 6) {
    error.value = 'La contraseña debe tener al menos 6 caracteres'
    return
  }
  loading.value = true
  try {
    await authApi.resetPassword(phone.value.trim(), code.value.trim(), newPassword.value)
    router.push({ path: '/login', query: { reset: '1' } })
  } catch (err) {
    error.value = err.response?.data?.detail || 'Código incorrecto o expirado. Intenta de nuevo.'
  } finally {
    loading.value = false
  }
}
</script>
