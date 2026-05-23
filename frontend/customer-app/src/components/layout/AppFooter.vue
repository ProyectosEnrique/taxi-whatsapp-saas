<template>
  <footer class="bg-gray-800 text-white mt-auto">
    <div class="container mx-auto px-4 py-8">
      <div class="grid grid-cols-1 md:grid-cols-3 gap-8">
        <!-- Columna 1: Info -->
        <div>
          <h3 class="font-bold text-lg mb-4">{{ tenantName }}</h3>
          <p class="text-gray-400 text-sm">
            {{ tenantDescription }}
          </p>
        </div>

        <!-- Columna 2: Links -->
        <div>
          <h3 class="font-bold text-lg mb-4">Enlaces Rápidos</h3>
          <ul class="space-y-2 text-sm">
            <li>
              <router-link to="/menu" class="text-gray-400 hover:text-white transition">
                Menú
              </router-link>
            </li>
            <li>
              <router-link to="/promotions" class="text-gray-400 hover:text-white transition">
                Promociones
              </router-link>
            </li>
            <li>
              <router-link to="/help" class="text-gray-400 hover:text-white transition">
                Centro de Ayuda
              </router-link>
            </li>
            <li v-if="authStore.isAuthenticated">
              <router-link to="/order-history" class="text-gray-400 hover:text-white transition">
                Mis Pedidos
              </router-link>
            </li>
          </ul>
        </div>

        <!-- Columna 3: Contacto -->
        <div>
          <h3 class="font-bold text-lg mb-4">Contacto</h3>
          <ul class="space-y-2 text-sm text-gray-400">
            <li v-if="tenantPhone" class="flex items-center space-x-2">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
              </svg>
              <span>{{ tenantPhone }}</span>
            </li>
            <li v-if="tenantEmail" class="flex items-center space-x-2">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
              </svg>
              <span>{{ tenantEmail }}</span>
            </li>
          </ul>
        </div>
      </div>

      <!-- Copyright -->
      <div class="border-t border-gray-700 mt-8 pt-6 text-center text-sm text-gray-400">
        <p>&copy; {{ currentYear }} {{ tenantName }}. Todos los derechos reservados.</p>
      </div>
    </div>
  </footer>
</template>

<script setup>
import { computed } from 'vue'
import { useTenantStore } from '@/stores/tenant'
import { useAuthStore } from '@/stores/auth'

const tenantStore = useTenantStore()
const authStore = useAuthStore()

const tenantName = computed(() => tenantStore.tenantName || 'Pedidos en Línea')
const tenantDescription = computed(() =>
  tenantStore.branding?.description || 'Haz tu pedido en línea de forma rápida y sencilla'
)
const tenantPhone = computed(() => tenantStore.tenant?.phone)
const tenantEmail = computed(() => tenantStore.tenant?.email)
const currentYear = computed(() => new Date().getFullYear())
</script>
