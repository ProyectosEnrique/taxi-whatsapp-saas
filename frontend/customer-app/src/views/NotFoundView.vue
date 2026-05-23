<template>
  <div class="min-h-screen flex items-center justify-center bg-gray-50">
    <div class="text-center px-4">
      <!-- 404 Illustration -->
      <div class="mb-8">
        <svg class="w-64 h-64 mx-auto text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      </div>

      <!-- 404 Text -->
      <h1 class="text-6xl font-bold text-gray-900 mb-4">404</h1>
      <h2 class="text-2xl font-bold text-gray-700 mb-2">Página No Encontrada</h2>
      <p class="text-gray-600 mb-8 max-w-md mx-auto">
        Lo sentimos, la página que estás buscando no existe o ha sido movida.
      </p>

      <!-- Actions -->
      <div class="flex flex-col sm:flex-row items-center justify-center space-y-4 sm:space-y-0 sm:space-x-4">
        <router-link to="/" class="btn-primary">
          <svg class="w-5 h-5 mr-2 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
          </svg>
          Ir al Inicio
        </router-link>

        <button @click="$router.go(-1)" class="btn-secondary">
          <svg class="w-5 h-5 mr-2 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
          </svg>
          Volver Atrás
        </button>
      </div>

      <!-- Popular Links -->
      <div class="mt-12">
        <p class="text-sm text-gray-500 mb-4">Tal vez estabas buscando:</p>
        <div class="flex flex-wrap justify-center gap-3">
          <router-link to="/" class="text-sm text-primary-600 hover:text-primary-700">
            Menú
          </router-link>
          <span class="text-gray-300">•</span>
          <router-link to="/promotions" class="text-sm text-primary-600 hover:text-primary-700">
            Promociones
          </router-link>
          <span class="text-gray-300">•</span>
          <router-link to="/order-history" class="text-sm text-primary-600 hover:text-primary-700">
            Mis Pedidos
          </router-link>
          <span class="text-gray-300">•</span>
          <router-link to="/help" class="text-sm text-primary-600 hover:text-primary-700">
            Ayuda
          </router-link>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
// No logic needed for 404 page
</script>
