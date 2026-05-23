<template>
  <div class="container mx-auto px-4 py-8 max-w-6xl">
    <!-- Loading State -->
    <div v-if="!product" class="text-center py-12">
      <div class="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mb-4"></div>
      <p class="text-gray-600">Cargando producto...</p>
    </div>

    <!-- Product Detail -->
    <div v-else>
      <!-- Breadcrumb -->
      <nav class="mb-6">
        <ol class="flex items-center space-x-2 text-sm">
          <li>
            <router-link to="/" class="text-gray-500 hover:text-gray-700">Menú</router-link>
          </li>
          <li class="text-gray-400">/</li>
          <li v-if="product.category">
            <span class="text-gray-500">{{ product.category }}</span>
          </li>
          <li class="text-gray-400">/</li>
          <li class="text-gray-900 font-medium">{{ product.name }}</li>
        </ol>
      </nav>

      <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <!-- Left: Image -->
        <div>
          <div class="bg-gray-200 rounded-lg overflow-hidden aspect-square mb-4">
            <img
              v-if="product.image"
              :src="product.image"
              :alt="product.name"
              class="w-full h-full object-cover"
            />
            <div v-else class="w-full h-full flex items-center justify-center">
              <svg class="w-32 h-32 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
              </svg>
            </div>
          </div>

          <!-- Gallery thumbnails (if multiple images) -->
          <!-- TODO: Implement multiple images -->
        </div>

        <!-- Right: Info -->
        <div>
          <div class="mb-6">
            <h1 class="text-3xl font-bold mb-2">{{ product.name }}</h1>

            <!-- Category Badge -->
            <span v-if="product.category" class="badge badge-success mb-4 inline-block">
              {{ product.category }}
            </span>

            <!-- Rating (if exists) -->
            <div v-if="product.rating" class="flex items-center space-x-2 mb-4">
              <div class="flex">
                <svg v-for="star in 5" :key="star" :class="[
                  'w-5 h-5',
                  star <= product.rating ? 'text-yellow-400 fill-current' : 'text-gray-300'
                ]" viewBox="0 0 20 20">
                  <path d="M10 15l-5.878 3.09 1.123-6.545L.489 6.91l6.572-.955L10 0l2.939 5.955 6.572.955-4.756 4.635 1.123 6.545z"/>
                </svg>
              </div>
              <span class="text-sm text-gray-600">({{ product.rating }})</span>
            </div>

            <!-- Price -->
            <p class="text-4xl font-bold text-primary-600 mb-6">
              ${{ product.price.toFixed(2) }}
            </p>

            <!-- Description -->
            <div v-if="product.description" class="mb-6">
              <h3 class="font-bold mb-2">Descripción</h3>
              <p class="text-gray-700">{{ product.description }}</p>
            </div>

            <!-- Additional Info -->
            <div class="space-y-3 mb-6">
              <div v-if="product.preparation_time" class="flex items-center space-x-3">
                <svg class="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span class="text-sm text-gray-600">Tiempo de preparación: {{ product.preparation_time }} min</span>
              </div>

              <div v-if="product.calories" class="flex items-center space-x-3">
                <svg class="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4M7.835 4.697a3.42 3.42 0 001.946-.806 3.42 3.42 0 014.438 0 3.42 3.42 0 001.946.806 3.42 3.42 0 013.138 3.138 3.42 3.42 0 00.806 1.946 3.42 3.42 0 010 4.438 3.42 3.42 0 00-.806 1.946 3.42 3.42 0 01-3.138 3.138 3.42 3.42 0 00-1.946.806 3.42 3.42 0 01-4.438 0 3.42 3.42 0 00-1.946-.806 3.42 3.42 0 01-3.138-3.138 3.42 3.42 0 00-.806-1.946 3.42 3.42 0 010-4.438 3.42 3.42 0 00.806-1.946 3.42 3.42 0 013.138-3.138z" />
                </svg>
                <span class="text-sm text-gray-600">{{ product.calories }} calorías</span>
              </div>

              <div v-if="product.dietary_options && product.dietary_options.length > 0" class="flex items-start space-x-3">
                <svg class="w-5 h-5 text-gray-400 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4M7.835 4.697a3.42 3.42 0 001.946-.806 3.42 3.42 0 014.438 0 3.42 3.42 0 001.946.806 3.42 3.42 0 013.138 3.138 3.42 3.42 0 00.806 1.946 3.42 3.42 0 010 4.438 3.42 3.42 0 00-.806 1.946 3.42 3.42 0 01-3.138 3.138 3.42 3.42 0 00-1.946.806 3.42 3.42 0 01-4.438 0 3.42 3.42 0 00-1.946-.806 3.42 3.42 0 01-3.138-3.138 3.42 3.42 0 00-.806-1.946 3.42 3.42 0 010-4.438 3.42 3.42 0 00.806-1.946 3.42 3.42 0 013.138-3.138z" />
                </svg>
                <div class="flex-1">
                  <p class="text-sm text-gray-600 mb-1">Opciones:</p>
                  <div class="flex flex-wrap gap-2">
                    <span v-for="option in product.dietary_options" :key="option" class="badge badge-success text-xs">
                      {{ option }}
                    </span>
                  </div>
                </div>
              </div>
            </div>

            <!-- Stock Warning -->
            <div v-if="product.stock && product.stock < 5" class="bg-yellow-50 border border-yellow-200 rounded-lg p-3 mb-6">
              <p class="text-sm text-yellow-800">
                ⚠️ ¡Últimas unidades! Solo quedan {{ product.stock }} disponibles
              </p>
            </div>

            <!-- Quantity Selector -->
            <div class="flex items-center space-x-4 mb-6">
              <p class="font-medium">Cantidad:</p>
              <div class="flex items-center space-x-2">
                <button
                  @click="quantity > 1 && quantity--"
                  class="w-10 h-10 flex items-center justify-center bg-gray-100 hover:bg-gray-200 rounded transition"
                >
                  <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 12H4" />
                  </svg>
                </button>
                <span class="text-xl font-bold w-12 text-center">{{ quantity }}</span>
                <button
                  @click="quantity++"
                  class="w-10 h-10 flex items-center justify-center bg-gray-100 hover:bg-gray-200 rounded transition"
                >
                  <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                  </svg>
                </button>
              </div>
            </div>

            <!-- Add to Cart Button -->
            <div class="flex space-x-4 mb-6">
              <button
                @click="handleAddToCart"
                :disabled="!product.active"
                class="btn-primary flex-1"
              >
                <svg class="w-5 h-5 mr-2 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z" />
                </svg>
                Agregar al Carrito
              </button>
            </div>

            <!-- Back to Menu -->
            <router-link to="/" class="text-primary-600 hover:text-primary-700 text-sm">
              ← Volver al menú
            </router-link>
          </div>
        </div>
      </div>

      <!-- Related Products (TODO) -->
      <!-- Reviews Section (TODO) -->
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useTenantStore } from '@/stores/tenant'
import { useCartStore } from '@/stores/cart'

const route = useRoute()
const router = useRouter()
const tenantStore = useTenantStore()
const cartStore = useCartStore()

const productId = ref(route.params.id)
const product = ref(null)
const quantity = ref(1)

function handleAddToCart() {
  if (!product.value) return

  cartStore.addItem(product.value, quantity.value)
  cartStore.openCart()
}

onMounted(() => {
  product.value = tenantStore.getProductById(productId.value)

  if (!product.value) {
    // Product not found, redirect to menu
    router.push('/')
  }
})
</script>
