<template>
  <div id="app" class="min-h-screen flex flex-col">
    <!-- Header Global -->
    <AppHeader v-if="!hideHeader" />

    <!-- Main Content -->
    <main class="flex-1">
      <router-view v-slot="{ Component }">
        <transition name="fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>

    <!-- Footer Global -->
    <AppFooter v-if="!hideFooter" />

    <!-- Cart Sidebar (siempre disponible) -->
    <CartSidebar />

    <!-- Notifications Toast -->
    <NotificationsToast />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useTenantStore } from '@/stores/tenant'
import AppHeader from '@/components/layout/AppHeader.vue'
import AppFooter from '@/components/layout/AppFooter.vue'
import CartSidebar from '@/components/cart/CartSidebar.vue'
import NotificationsToast from '@/components/common/NotificationsToast.vue'

const route = useRoute()
const tenantStore = useTenantStore()

// Rutas donde ocultar header/footer
const hideHeader = computed(() => route.meta.hideHeader || false)
const hideFooter = computed(() => route.meta.hideFooter || false)

// Inicializar tenant al cargar la app
tenantStore.initializeTenant()
</script>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
