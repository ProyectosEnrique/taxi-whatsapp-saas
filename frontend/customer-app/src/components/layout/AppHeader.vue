<template>
  <header class="bg-white shadow-sm sticky top-0 z-50">
    <div class="container mx-auto px-4">
      <div class="flex items-center justify-between h-16">
        <!-- Logo y Nombre -->
        <router-link to="/" class="flex items-center space-x-2">
          <div class="w-10 h-10 bg-primary-600 rounded-full flex items-center justify-center">
            <span class="text-white font-bold text-xl">{{ tenantInitial }}</span>
          </div>
          <span class="font-bold text-xl text-gray-800">{{ tenantName }}</span>
        </router-link>

        <!-- Navegación Desktop -->
        <nav class="hidden md:flex items-center space-x-6">
          <router-link to="/menu" class="text-gray-600 hover:text-primary-600 transition">
            Menú
          </router-link>
          <router-link to="/promotions" class="text-gray-600 hover:text-primary-600 transition">
            Promociones
          </router-link>
          <router-link to="/help" class="text-gray-600 hover:text-primary-600 transition">
            Ayuda
          </router-link>
        </nav>

        <!-- Acciones -->
        <div class="flex items-center space-x-4">
          <!-- Carrito -->
          <button
            @click="cartStore.toggleCart()"
            class="relative p-2 text-gray-600 hover:text-primary-600 transition"
          >
            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z" />
            </svg>
            <span
              v-if="cartStore.itemCount > 0"
              class="absolute -top-1 -right-1 bg-red-500 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center"
            >
              {{ cartStore.itemCount }}
            </span>
          </button>

          <!-- Usuario -->
          <div v-if="authStore.isAuthenticated" class="relative">
            <button
              @click="showUserMenu = !showUserMenu"
              class="flex items-center space-x-2 text-gray-600 hover:text-primary-600"
            >
              <div class="w-8 h-8 bg-primary-100 rounded-full flex items-center justify-center">
                <span class="text-primary-600 font-medium">{{ userInitial }}</span>
              </div>
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
              </svg>
            </button>

            <!-- Dropdown Menu -->
            <div
              v-if="showUserMenu"
              v-click-outside="() => showUserMenu = false"
              class="absolute right-0 mt-2 w-48 bg-white rounded-lg shadow-lg border border-gray-200 py-2"
            >
              <router-link to="/profile" class="block px-4 py-2 text-gray-700 hover:bg-gray-50">
                Mi Perfil
              </router-link>
              <router-link to="/order-history" class="block px-4 py-2 text-gray-700 hover:bg-gray-50">
                Mis Pedidos
              </router-link>
              <router-link to="/loyalty" class="block px-4 py-2 text-gray-700 hover:bg-gray-50">
                Mis Puntos
              </router-link>
              <hr class="my-2">
              <button
                @click="handleLogout"
                class="block w-full text-left px-4 py-2 text-red-600 hover:bg-gray-50"
              >
                Cerrar Sesión
              </button>
            </div>
          </div>

          <router-link
            v-else
            to="/login"
            class="btn-primary text-sm"
          >
            Iniciar Sesión
          </router-link>
        </div>
      </div>
    </div>
  </header>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useTenantStore } from '@/stores/tenant'
import { useCartStore } from '@/stores/cart'
import { useAuthStore } from '@/stores/auth'
import { useRouter } from 'vue-router'

const tenantStore = useTenantStore()
const cartStore = useCartStore()
const authStore = useAuthStore()
const router = useRouter()

const showUserMenu = ref(false)

const tenantName = computed(() => tenantStore.tenantName || 'Pedidos en Línea')
const tenantInitial = computed(() => tenantName.value.charAt(0).toUpperCase())
const userInitial = computed(() => authStore.userName.charAt(0).toUpperCase())

function handleLogout() {
  authStore.logout()
  router.push('/')
  showUserMenu.value = false
}

// Directiva para cerrar el dropdown al hacer click fuera
const vClickOutside = {
  mounted(el, binding) {
    el.clickOutsideEvent = (event) => {
      if (!(el === event.target || el.contains(event.target))) {
        binding.value()
      }
    }
    document.addEventListener('click', el.clickOutsideEvent)
  },
  unmounted(el) {
    document.removeEventListener('click', el.clickOutsideEvent)
  }
}
</script>
