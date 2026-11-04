<template>
  <div class="min-h-screen flex items-center justify-center bg-gradient-to-br from-taxi-yellow to-yellow-600 px-4 py-8">
    <div class="max-w-md w-full">
      <div class="text-center mb-6">
        <div class="inline-flex items-center justify-center w-16 h-16 rounded-2xl shadow-lg mb-3 overflow-hidden">
          <img src="/favicon.svg" alt="TaxiCerca" class="w-16 h-16">
        </div>
        <h1 class="text-2xl font-bold text-white mb-1">Crear Cuenta</h1>
        <p class="text-yellow-100 text-sm">Únete y solicita tu primer viaje</p>
      </div>

      <div class="bg-white rounded-2xl shadow-2xl p-8">
        <form @submit.prevent="handleRegister">
          <div class="mb-4">
            <label class="block text-sm font-medium text-gray-700 mb-2">Nombre completo</label>
            <input
              v-model="form.name"
              type="text"
              required
              placeholder="Juan Pérez"
              class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-taxi-yellow focus:border-transparent"
              :disabled="loading"
            />
          </div>

          <div class="mb-4">
            <label class="block text-sm font-medium text-gray-700 mb-2">Teléfono</label>
            <input
              v-model="form.phone"
              type="tel"
              required
              placeholder="+52 55 1234 5678"
              class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-taxi-yellow focus:border-transparent"
              :disabled="loading"
            />
          </div>

          <div class="mb-4">
            <label class="block text-sm font-medium text-gray-700 mb-2">Email (opcional)</label>
            <input
              v-model="form.email"
              type="email"
              placeholder="correo@ejemplo.com"
              class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-taxi-yellow focus:border-transparent"
              :disabled="loading"
            />
          </div>

          <div class="mb-4">
            <label class="block text-sm font-medium text-gray-700 mb-2">Contraseña</label>
            <input
              v-model="form.password"
              :type="showPassword ? 'text' : 'password'"
              required
              placeholder="Mínimo 6 caracteres"
              class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-taxi-yellow focus:border-transparent"
              :disabled="loading"
            />
          </div>

          <div class="mb-6">
            <label class="block text-sm font-medium text-gray-700 mb-2">Confirmar contraseña</label>
            <input
              v-model="form.confirmPassword"
              :type="showPassword ? 'text' : 'password'"
              required
              placeholder="Repite tu contraseña"
              class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-taxi-yellow focus:border-transparent"
              :disabled="loading"
            />
          </div>

          <div v-if="error" class="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
            <p class="text-sm text-red-600">⚠️ {{ error }}</p>
          </div>

          <button
            type="submit"
            :disabled="loading"
            class="w-full bg-taxi-yellow hover:bg-yellow-500 text-white font-semibold py-3 rounded-lg transition duration-200 disabled:opacity-50"
          >
            <span v-if="!loading">Crear Cuenta</span>
            <span v-else>Creando cuenta...</span>
          </button>
        </form>

        <div class="mt-6 text-center">
          <p class="text-sm text-gray-600">
            ¿Ya tienes cuenta?
            <router-link to="/login" class="text-taxi-yellow hover:underline font-semibold">
              Inicia sesión
            </router-link>
          </p>
        </div>
      </div>

      <div class="mt-6 text-center">
        <p class="text-sm text-yellow-100">Al crear tu cuenta aceptas el <router-link to="/privacidad" class="underline">aviso de privacidad</router-link> · © 2026 TaxiCerca</p>
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
  name: '',
  phone: '',
  email: '',
  password: '',
  confirmPassword: ''
})

const showPassword = ref(false)
const loading = ref(false)
const error = ref(null)

const handleRegister = async () => {
  error.value = null

  if (form.password !== form.confirmPassword) {
    error.value = 'Las contraseñas no coinciden'
    return
  }

  if (form.password.length < 6) {
    error.value = 'La contraseña debe tener al menos 6 caracteres'
    return
  }

  loading.value = true

  try {
    const result = await authStore.register({
      name: form.name,
      phone: form.phone,
      email: form.email || null,
      password: form.password
    })

    if (result.success) {
      router.push('/home')
    } else {
      error.value = result.error || 'Error al crear cuenta'
    }
  } catch (err) {
    error.value = 'Error de conexión'
  } finally {
    loading.value = false
  }
}
</script>
