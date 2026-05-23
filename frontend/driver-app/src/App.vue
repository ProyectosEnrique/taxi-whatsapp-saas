<template>
  <div id="app" class="min-h-screen bg-gray-50">
    <router-view />
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useAuthStore } from './stores/authStore'
import { useDriverStore } from './stores/driverStore'

const authStore = useAuthStore()
const driverStore = useDriverStore()

onMounted(() => {
  // Verificar si hay sesión activa
  authStore.checkAuth()

  // Si está autenticado, iniciar polling de datos
  if (authStore.isAuthenticated) {
    driverStore.startPolling()
  }
})
</script>

<style>
/* Estilos globales adicionales si se necesitan */
</style>
