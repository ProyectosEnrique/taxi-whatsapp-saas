<template>
  <div class="container mx-auto px-4 py-8 max-w-6xl">
    <div class="text-center mb-8">
      <h1 class="text-4xl font-bold mb-2">Promociones y Ofertas</h1>
      <p class="text-gray-600">Aprovecha nuestras mejores ofertas</p>
    </div>

    <!-- Loading State -->
    <div v-if="promotionsStore.loading" class="text-center py-12">
      <div class="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mb-4"></div>
      <p class="text-gray-600">Cargando promociones...</p>
    </div>

    <!-- Empty State -->
    <div v-else-if="promotionsStore.activePromotions.length === 0" class="text-center py-12">
      <svg class="w-16 h-16 text-gray-300 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v13m0-13V6a2 2 0 112 2h-2zm0 0V5.5A2.5 2.5 0 109.5 8H12zm-7 4h14M5 12a2 2 0 110-4h14a2 2 0 110 4M5 12v7a2 2 0 002 2h10a2 2 0 002-2v-7" />
      </svg>
      <p class="text-gray-500 mb-4">No hay promociones activas en este momento</p>
      <router-link to="/" class="btn-primary">
        Ver Menú
      </router-link>
    </div>

    <!-- Promotions Grid -->
    <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      <div
        v-for="promo in promotionsStore.activePromotions"
        :key="promo.id"
        class="card hover:shadow-xl transition-shadow relative overflow-hidden"
      >
        <!-- Badge de Descuento -->
        <div class="absolute top-4 right-4 z-10">
          <div class="bg-red-500 text-white px-3 py-1 rounded-full font-bold text-sm">
            <span v-if="promo.discount_type === 'percentage'">
              -{{ promo.discount_value }}%
            </span>
            <span v-else>
              ${{ promo.discount_value }} OFF
            </span>
          </div>
        </div>

        <!-- Image -->
        <div class="h-48 bg-gradient-to-br from-primary-400 to-primary-600 rounded-lg mb-4 flex items-center justify-center overflow-hidden">
          <img
            v-if="promo.image"
            :src="promo.image"
            :alt="promo.title"
            class="w-full h-full object-cover"
          />
          <svg v-else class="w-24 h-24 text-white opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v13m0-13V6a2 2 0 112 2h-2zm0 0V5.5A2.5 2.5 0 109.5 8H12zm-7 4h14M5 12a2 2 0 110-4h14a2 2 0 110 4M5 12v7a2 2 0 002 2h10a2 2 0 002-2v-7" />
          </svg>
        </div>

        <!-- Content -->
        <div class="mb-4">
          <h3 class="font-bold text-xl mb-2">{{ promo.title }}</h3>
          <p class="text-gray-600 text-sm mb-3">{{ promo.description }}</p>

          <!-- Promo Code -->
          <div class="bg-gray-100 border-2 border-dashed border-gray-300 rounded-lg p-3 mb-3">
            <div class="flex items-center justify-between">
              <div>
                <p class="text-xs text-gray-600 mb-1">Código promocional:</p>
                <p class="font-mono font-bold text-lg">{{ promo.code }}</p>
              </div>
              <button
                @click="copyCode(promo.code)"
                class="p-2 hover:bg-gray-200 rounded transition"
                title="Copiar código"
              >
                <svg class="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
              </button>
            </div>
          </div>

          <!-- Validity -->
          <div class="flex items-center text-sm text-gray-600 mb-3">
            <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span>Válido hasta: {{ formatDate(promo.valid_until) }}</span>
          </div>

          <!-- Conditions -->
          <div v-if="promo.min_purchase" class="text-xs text-gray-500">
            * Compra mínima: ${{ promo.min_purchase.toFixed(2) }}
          </div>
        </div>

        <!-- Button -->
        <button
          @click="usePromotion(promo)"
          class="btn-primary w-full"
        >
          Usar Ahora
        </button>
      </div>
    </div>

    <!-- Copied Notification -->
    <div
      v-if="showCopiedNotification"
      class="fixed bottom-4 right-4 bg-green-500 text-white px-6 py-3 rounded-lg shadow-lg animate-slide-in"
    >
      ✓ Código copiado al portapapeles
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { usePromotionsStore } from '@/stores/promotions'
import { useCartStore } from '@/stores/cart'

const router = useRouter()
const promotionsStore = usePromotionsStore()
const cartStore = useCartStore()

const showCopiedNotification = ref(false)

function formatDate(dateString) {
  const date = new Date(dateString)
  return date.toLocaleDateString('es-MX', {
    day: '2-digit',
    month: 'long',
    year: 'numeric'
  })
}

function copyCode(code) {
  navigator.clipboard.writeText(code)

  showCopiedNotification.value = true
  setTimeout(() => {
    showCopiedNotification.value = false
  }, 3000)
}

function usePromotion(promo) {
  // Aplicar promoción al carrito
  promotionsStore.applyPromoCode(promo.code)

  // Abrir carrito y redirigir a checkout si hay items
  if (cartStore.items.length > 0) {
    router.push('/checkout')
  } else {
    // Si no hay items, ir al menú
    router.push('/')
  }
}

onMounted(() => {
  promotionsStore.loadPromotions()
})
</script>
