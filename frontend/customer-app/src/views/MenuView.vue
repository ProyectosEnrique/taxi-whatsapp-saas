<template>
  <div class="flex h-screen bg-gray-50">
    <!-- Sidebar de Categorías (Izquierda) -->
    <aside class="w-64 bg-white shadow-lg overflow-y-auto">
      <div class="sticky top-0 bg-white z-10 p-4 border-b">
        <h2 class="text-xl font-bold text-gray-900">Categorías</h2>
      </div>

      <nav class="p-2">
        <button
          v-for="category in categories"
          :key="category"
          @click="selectedCategory = category"
          :class="[
            'w-full text-left px-4 py-3 rounded-lg mb-1 transition',
            selectedCategory === category
              ? 'bg-primary-600 text-white font-semibold'
              : 'text-gray-700 hover:bg-gray-100'
          ]"
        >
          {{ category }}
        </button>
      </nav>
    </aside>

    <!-- Contenido Principal (Derecha) -->
    <main class="flex-1 overflow-y-auto">
      <div class="max-w-5xl mx-auto p-8">
        <!-- Header -->
        <div class="mb-8">
          <h1 class="text-4xl font-bold text-gray-900 mb-2">{{ tenantName }}</h1>
          <p class="text-gray-600">{{ greetingMessage }}</p>
        </div>

        <!-- Barra de Búsqueda -->
        <div class="mb-8">
          <div class="relative">
            <input
              v-model="searchQuery"
              type="text"
              placeholder="Buscar productos..."
              class="input pl-12 w-full"
            />
            <svg
              class="absolute left-4 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </div>
        </div>

        <!-- Loading State -->
        <div v-if="tenantStore.loading" class="text-center py-12">
          <div class="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
          <p class="mt-4 text-gray-600">Cargando menú...</p>
        </div>

        <!-- Error State -->
        <div v-else-if="tenantStore.error" class="text-center py-12">
          <svg class="w-16 h-16 text-red-500 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <p class="text-red-600">{{ tenantStore.error }}</p>
        </div>

        <!-- Lista Continua de Productos (estilo menú físico) -->
        <div v-else class="bg-white rounded-lg shadow">
          <!-- Header de la categoría actual -->
          <div class="sticky top-0 bg-primary-50 px-6 py-3 border-b">
            <h2 class="text-2xl font-bold text-primary-900">
              {{ selectedCategory }}
            </h2>
          </div>

          <!-- Lista de productos -->
          <div class="divide-y">
            <ProductListItem
              v-for="product in displayedProducts"
              :key="product.product_id"
              :product="product"
              @click="openProductModal(product)"
            />
          </div>

          <!-- Empty State -->
          <div v-if="displayedProducts.length === 0" class="text-center py-12">
            <svg class="w-16 h-16 text-gray-300 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
            </svg>
            <p class="text-gray-500">No se encontraron productos</p>
          </div>
        </div>
      </div>
    </main>

    <!-- Modal de Detalle de Producto -->
    <ProductDetailModal
      v-if="selectedProduct"
      :product="selectedProduct"
      @close="closeProductModal"
      @add-to-cart="handleAddToCart"
    />
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useTenantStore } from '@/stores/tenant'
import { useCartStore } from '@/stores/cart'
import ProductListItem from '@/components/products/ProductListItem.vue'
import ProductDetailModal from '@/components/products/ProductDetailModal.vue'

const tenantStore = useTenantStore()
const cartStore = useCartStore()

const searchQuery = ref('')
const selectedCategory = ref(null)
const selectedProduct = ref(null)

// Computed
const tenantName = computed(() => tenantStore.tenantName)
const greetingMessage = computed(() =>
  tenantStore.branding?.greeting_message || '¡Bienvenido! Descubre nuestros productos'
)

const categories = computed(() => {
  const cats = ['Todos', ...tenantStore.categories]
  return cats
})

const displayedProducts = computed(() => {
  let products = tenantStore.products

  // Filtrar por búsqueda
  if (searchQuery.value) {
    products = tenantStore.searchProducts(searchQuery.value)
  }
  // Filtrar por categoría
  else if (selectedCategory.value && selectedCategory.value !== 'Todos') {
    products = products.filter(p => p.category === selectedCategory.value)
  }

  // Solo productos activos
  return products.filter(p => p.active)
})

// Watch: Reset category when searching
watch(searchQuery, (newValue) => {
  if (newValue) {
    selectedCategory.value = 'Todos'
  }
})

// Methods
function openProductModal(product) {
  selectedProduct.value = product
}

function closeProductModal() {
  selectedProduct.value = null
}

function handleAddToCart(product, quantity = 1) {
  cartStore.addItem(product, quantity)
  cartStore.openCart()
  closeProductModal()
}

// Initialize
if (!selectedCategory.value && categories.value.length > 0) {
  selectedCategory.value = categories.value[0]
}
</script>

<style scoped>
/* Asegurar que el sidebar sea sticky en móvil */
@media (max-width: 768px) {
  aside {
    position: fixed;
    left: -100%;
    transition: left 0.3s;
    z-index: 50;
  }

  aside.open {
    left: 0;
  }
}
</style>
