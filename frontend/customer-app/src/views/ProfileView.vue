<template>
  <div class="container mx-auto px-4 py-8 max-w-4xl">
    <h1 class="text-3xl font-bold mb-8">Mi Perfil</h1>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <!-- Sidebar -->
      <div class="lg:col-span-1">
        <div class="card">
          <!-- Avatar -->
          <div class="text-center mb-4">
            <div class="w-24 h-24 bg-primary-600 rounded-full mx-auto flex items-center justify-center mb-3">
              <span class="text-white text-4xl font-bold">
                {{ userInitial }}
              </span>
            </div>
            <h2 class="font-bold text-xl">{{ authStore.userName }}</h2>
            <p class="text-sm text-gray-600">{{ authStore.userEmail }}</p>
          </div>

          <!-- Stats (con Loyalty) -->
          <div class="border-t pt-4 space-y-3">
            <div class="flex items-center justify-between">
              <span class="text-sm text-gray-600">Puntos</span>
              <span class="font-bold text-primary-600">{{ loyaltyStore.points }}</span>
            </div>
            <div class="flex items-center justify-between">
              <span class="text-sm text-gray-600">Nivel</span>
              <span class="font-medium">{{ loyaltyStore.level }}</span>
            </div>
            <router-link to="/loyalty" class="btn-primary w-full text-sm">
              Ver Mi Programa de Lealtad
            </router-link>
          </div>
        </div>

        <!-- Menu -->
        <div class="card mt-4">
          <nav class="space-y-1">
            <button
              @click="activeSection = 'info'"
              :class="[
                'w-full text-left px-4 py-2 rounded transition',
                activeSection === 'info' ? 'bg-primary-600 text-white' : 'hover:bg-gray-100'
              ]"
            >
              Información Personal
            </button>
            <button
              @click="activeSection = 'password'"
              :class="[
                'w-full text-left px-4 py-2 rounded transition',
                activeSection === 'password' ? 'bg-primary-600 text-white' : 'hover:bg-gray-100'
              ]"
            >
              Cambiar Contraseña
            </button>
            <router-link
              to="/addresses"
              class="block px-4 py-2 rounded hover:bg-gray-100"
            >
              Mis Direcciones
            </router-link>
            <router-link
              to="/order-history"
              class="block px-4 py-2 rounded hover:bg-gray-100"
            >
              Mis Pedidos
            </router-link>
            <button
              @click="handleLogout"
              class="w-full text-left px-4 py-2 rounded hover:bg-red-50 text-red-600"
            >
              Cerrar Sesión
            </button>
          </nav>
        </div>
      </div>

      <!-- Main Content -->
      <div class="lg:col-span-2">
        <!-- Información Personal -->
        <div v-if="activeSection === 'info'" class="card">
          <h2 class="text-xl font-bold mb-6">Información Personal</h2>

          <!-- Success Message -->
          <div v-if="successMessage" class="bg-green-50 border border-green-200 rounded-lg p-4 mb-4">
            <p class="text-green-800">{{ successMessage }}</p>
          </div>

          <!-- Error Message -->
          <div v-if="authStore.error" class="bg-red-50 border border-red-200 rounded-lg p-4 mb-4">
            <p class="text-red-600">{{ authStore.error }}</p>
          </div>

          <form @submit.prevent="handleUpdateProfile" class="space-y-4">
            <div>
              <label class="block text-sm font-medium mb-1">Nombre Completo</label>
              <input
                v-model="profileForm.name"
                type="text"
                required
                class="input"
              />
            </div>

            <div>
              <label class="block text-sm font-medium mb-1">Correo Electrónico</label>
              <input
                v-model="profileForm.email"
                type="email"
                required
                class="input"
              />
            </div>

            <div>
              <label class="block text-sm font-medium mb-1">Teléfono</label>
              <input
                v-model="profileForm.phone"
                type="tel"
                class="input"
              />
            </div>

            <button
              type="submit"
              :disabled="authStore.loading"
              class="btn-primary"
            >
              <span v-if="!authStore.loading">Guardar Cambios</span>
              <span v-else>Guardando...</span>
            </button>
          </form>
        </div>

        <!-- Cambiar Contraseña -->
        <div v-if="activeSection === 'password'" class="card">
          <h2 class="text-xl font-bold mb-6">Cambiar Contraseña</h2>

          <!-- Success Message -->
          <div v-if="passwordSuccess" class="bg-green-50 border border-green-200 rounded-lg p-4 mb-4">
            <p class="text-green-800">Contraseña actualizada exitosamente</p>
          </div>

          <!-- Error Message -->
          <div v-if="passwordError" class="bg-red-50 border border-red-200 rounded-lg p-4 mb-4">
            <p class="text-red-600">{{ passwordError }}</p>
          </div>

          <form @submit.prevent="handleChangePassword" class="space-y-4">
            <div>
              <label class="block text-sm font-medium mb-1">Contraseña Actual</label>
              <input
                v-model="passwordForm.current"
                type="password"
                required
                class="input"
              />
            </div>

            <div>
              <label class="block text-sm font-medium mb-1">Nueva Contraseña</label>
              <input
                v-model="passwordForm.new"
                type="password"
                required
                minlength="8"
                class="input"
              />
              <p class="text-xs text-gray-500 mt-1">Mínimo 8 caracteres</p>
            </div>

            <div>
              <label class="block text-sm font-medium mb-1">Confirmar Nueva Contraseña</label>
              <input
                v-model="passwordForm.confirm"
                type="password"
                required
                class="input"
              />
              <p v-if="passwordMismatch" class="text-xs text-red-600 mt-1">
                Las contraseñas no coinciden
              </p>
            </div>

            <button
              type="submit"
              :disabled="passwordMismatch || authStore.loading"
              class="btn-primary"
            >
              <span v-if="!authStore.loading">Cambiar Contraseña</span>
              <span v-else>Actualizando...</span>
            </button>
          </form>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useLoyaltyStore } from '@/stores/loyalty'

const router = useRouter()
const authStore = useAuthStore()
const loyaltyStore = useLoyaltyStore()

const activeSection = ref('info')
const successMessage = ref('')
const passwordSuccess = ref(false)
const passwordError = ref('')

const profileForm = ref({
  name: '',
  email: '',
  phone: ''
})

const passwordForm = ref({
  current: '',
  new: '',
  confirm: ''
})

const userInitial = computed(() => {
  return authStore.userName.charAt(0).toUpperCase()
})

const passwordMismatch = computed(() => {
  return passwordForm.value.new && passwordForm.value.confirm &&
         passwordForm.value.new !== passwordForm.value.confirm
})

async function handleUpdateProfile() {
  successMessage.value = ''

  const success = await authStore.updateProfile({
    name: profileForm.value.name,
    email: profileForm.value.email,
    phone: profileForm.value.phone
  })

  if (success) {
    successMessage.value = 'Perfil actualizado exitosamente'
    setTimeout(() => {
      successMessage.value = ''
    }, 3000)
  }
}

async function handleChangePassword() {
  passwordSuccess.value = false
  passwordError.value = ''

  if (passwordMismatch.value) {
    passwordError.value = 'Las contraseñas no coinciden'
    return
  }

  // TODO: Implementar cambio de contraseña en el backend
  // Por ahora, simular éxito
  passwordSuccess.value = true
  passwordForm.value = {
    current: '',
    new: '',
    confirm: ''
  }

  setTimeout(() => {
    passwordSuccess.value = false
  }, 3000)
}

function handleLogout() {
  if (confirm('¿Estás seguro de que deseas cerrar sesión?')) {
    authStore.logout()
    router.push('/')
  }
}

onMounted(() => {
  // Pre-llenar formulario con datos actuales
  profileForm.value = {
    name: authStore.userName,
    email: authStore.userEmail,
    phone: authStore.user?.phone || ''
  }

  // Cargar datos de lealtad
  loyaltyStore.loadLoyaltyData()
})
</script>
