<template>
  <div class="min-h-screen bg-gray-50">
    <!-- Header -->
    <header class="sticky top-0 z-40 bg-white shadow-sm">
      <div class="max-w-7xl mx-auto px-4 py-3">
        <!-- Logo y nombre -->
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-3">
            <div
              class="w-10 h-10 rounded-full flex items-center justify-center text-white font-bold text-lg"
              :style="{ backgroundColor: branding.primaryColor }"
            >
              {{ tenantName.charAt(0) }}
            </div>
            <div>
              <h1 class="font-semibold text-gray-900">{{ tenantName }}</h1>
              <p class="text-xs text-gray-500">{{ totalProducts }} productos</p>
            </div>
          </div>

          <!-- Carrito -->
          <button
            @click="cartStore.toggleCart()"
            class="relative p-2 rounded-full hover:bg-gray-100 transition-colors"
          >
            <svg class="w-6 h-6 text-gray-700" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z" />
            </svg>
            <span
              v-if="cartStore.itemCount > 0"
              class="absolute -top-1 -right-1 w-5 h-5 rounded-full text-white text-xs flex items-center justify-center"
              :style="{ backgroundColor: branding.primaryColor }"
            >
              {{ cartStore.itemCount }}
            </span>
          </button>
        </div>

        <!-- Barra de busqueda -->
        <div class="mt-3">
          <div class="relative">
            <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <input
              v-model="searchInput"
              @input="debouncedSearch"
              type="text"
              placeholder="Buscar medicamentos, vitaminas..."
              class="w-full pl-10 pr-4 py-2.5 rounded-xl border border-gray-200 focus:border-green-500 focus:ring-2 focus:ring-green-500/20 outline-none transition-all text-sm"
            />
            <button
              v-if="searchInput"
              @click="clearSearch"
              class="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
            >
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>
      </div>
    </header>

    <!-- Loading State -->
    <div v-if="loading" class="flex items-center justify-center py-20">
      <div class="text-center">
        <div
          class="w-12 h-12 border-4 border-t-transparent rounded-full animate-spin mx-auto"
          :style="{ borderColor: branding.primaryColor, borderTopColor: 'transparent' }"
        ></div>
        <p class="mt-4 text-gray-500">Cargando productos...</p>
      </div>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="flex items-center justify-center py-20">
      <div class="text-center">
        <svg class="w-16 h-16 text-red-400 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
        <p class="mt-4 text-gray-600">{{ error }}</p>
        <button
          @click="retryLoad"
          class="mt-4 px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 transition-colors"
        >
          Reintentar
        </button>
      </div>
    </div>

    <!-- Main Content -->
    <main v-else class="max-w-7xl mx-auto px-4 py-4">
      <!-- Categorias horizontales -->
      <div class="mb-4 -mx-4 px-4 overflow-x-auto scrollbar-hide">
        <div class="flex gap-2 pb-2">
          <!-- Boton "Todos" -->
          <button
            @click="selectCategory(null)"
            :class="[
              'px-4 py-2 rounded-full text-sm font-medium whitespace-nowrap transition-all',
              !activeCategory
                ? 'text-white shadow-md'
                : 'bg-white text-gray-700 border border-gray-200 hover:border-gray-300'
            ]"
            :style="!activeCategory ? { backgroundColor: branding.primaryColor } : {}"
          >
            Todos
          </button>

          <!-- Categorias -->
          <button
            v-for="cat in categories"
            :key="cat.id"
            @click="selectCategory(cat.id)"
            :class="[
              'px-4 py-2 rounded-full text-sm font-medium whitespace-nowrap transition-all flex items-center gap-1.5',
              activeCategory === cat.id
                ? 'text-white shadow-md'
                : 'bg-white text-gray-700 border border-gray-200 hover:border-gray-300'
            ]"
            :style="activeCategory === cat.id ? { backgroundColor: branding.primaryColor } : {}"
          >
            <span>{{ cat.icon }}</span>
            <span>{{ cat.name }}</span>
            <span class="text-xs opacity-75">({{ cat.product_count }})</span>
          </button>
        </div>
      </div>

      <!-- Subcategorias (si hay categoria activa) -->
      <div v-if="activeSubcategories.length > 0" class="mb-4 -mx-4 px-4 overflow-x-auto scrollbar-hide">
        <div class="flex gap-2 pb-2">
          <button
            v-for="sub in activeSubcategories"
            :key="sub.id"
            @click="selectSubcategory(sub.id)"
            :class="[
              'px-3 py-1.5 rounded-full text-xs font-medium whitespace-nowrap transition-all',
              activeSubcategory === sub.id
                ? 'bg-gray-800 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            ]"
          >
            {{ sub.icon }} {{ sub.name }}
          </button>
        </div>
      </div>

      <!-- Titulo de seccion -->
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-lg font-semibold text-gray-900">
          {{ sectionTitle }}
        </h2>
        <span class="text-sm text-gray-500">
          {{ filteredProducts.length }} productos
        </span>
      </div>

      <!-- Grid de productos -->
      <div v-if="filteredProducts.length > 0" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <div
          v-for="product in filteredProducts"
          :key="product.id"
          @click="openProductModal(product)"
          class="bg-white rounded-xl p-4 shadow-sm hover:shadow-md transition-shadow cursor-pointer border border-gray-100"
        >
          <!-- Badge de receta si aplica -->
          <div v-if="product.requires_prescription" class="mb-2">
            <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-red-100 text-red-700">
              Requiere receta
            </span>
          </div>

          <!-- Info del producto -->
          <div class="flex justify-between items-start gap-3">
            <div class="flex-1 min-w-0">
              <h3 class="font-medium text-gray-900 text-sm leading-tight line-clamp-2">
                {{ product.name }}
              </h3>
              <p v-if="product.generic_name" class="text-xs text-gray-500 mt-1">
                {{ product.generic_name }}
              </p>
              <p v-if="product.presentation" class="text-xs text-gray-400 mt-0.5">
                {{ product.presentation }} {{ product.dosage ? `- ${product.dosage}` : '' }}
              </p>
            </div>

            <div class="text-right flex-shrink-0">
              <p class="font-bold text-lg" :style="{ color: branding.primaryColor }">
                ${{ product.price?.toFixed(2) }}
              </p>
              <p v-if="product.stock > 0" class="text-xs text-green-600">
                En stock
              </p>
              <p v-else class="text-xs text-red-500">
                Agotado
              </p>
            </div>
          </div>

          <!-- Boton agregar -->
          <button
            @click.stop="addToCart(product)"
            :disabled="product.stock <= 0"
            class="mt-3 w-full py-2 rounded-lg text-sm font-medium transition-colors disabled:bg-gray-100 disabled:text-gray-400"
            :class="product.stock > 0 ? 'bg-green-50 text-green-700 hover:bg-green-100' : ''"
          >
            {{ product.stock > 0 ? 'Agregar al carrito' : 'No disponible' }}
          </button>
        </div>
      </div>

      <!-- Empty State -->
      <div v-else class="text-center py-12">
        <svg class="w-16 h-16 text-gray-300 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <p class="mt-4 text-gray-500">No se encontraron productos</p>
        <button
          @click="clearFilters"
          class="mt-2 text-green-600 hover:text-green-700 text-sm font-medium"
        >
          Ver todos los productos
        </button>
      </div>
    </main>

    <!-- Cart Sidebar -->
    <CartSidebar />

    <!-- Product Modal -->
    <ProductModal
      v-if="selectedProduct"
      :product="selectedProduct"
      @close="selectedProduct = null"
      @add-to-cart="addToCartFromModal"
    />

    <!-- Sofia Floating Button -->
    <button
      @click="openSofia"
      class="fixed bottom-6 right-6 w-14 h-14 rounded-full shadow-lg flex items-center justify-center text-white z-50 hover:scale-105 transition-transform"
      :style="{ backgroundColor: branding.primaryColor }"
    >
      <svg class="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
      </svg>
    </button>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useTenantStore } from '@/stores/tenant'
import { useCartStore } from '@/stores/cart'
import { useChatStore } from '@/stores/chat'
import CartSidebar from '@/components/cart/CartSidebar.vue'
import ProductModal from '@/components/products/ProductModal.vue'

// Stores
const tenantStore = useTenantStore()
const cartStore = useCartStore()
const chatStore = useChatStore()
const route = useRoute()

// State local
const searchInput = ref('')
const selectedProduct = ref(null)
let searchTimeout = null

// Computed desde tenant store
const loading = computed(() => tenantStore.loading)
const error = computed(() => tenantStore.error)
const tenantName = computed(() => tenantStore.tenantName)
const branding = computed(() => tenantStore.branding)
const categories = computed(() => tenantStore.categoriesWithCount)
const filteredProducts = computed(() => tenantStore.filteredProducts)
const totalProducts = computed(() => tenantStore.totalProducts)
const activeCategory = computed(() => tenantStore.activeCategory)
const activeSubcategory = computed(() => tenantStore.activeSubcategory)
const activeSubcategories = computed(() => tenantStore.activeSubcategories)

// Titulo de seccion dinamico
const sectionTitle = computed(() => {
  if (tenantStore.searchQuery) {
    return `Resultados para "${tenantStore.searchQuery}"`
  }
  if (activeSubcategory.value) {
    const sub = tenantStore.subcategories.find(s => s.id === activeSubcategory.value)
    return sub?.name || 'Productos'
  }
  if (activeCategory.value) {
    const cat = categories.value.find(c => c.id === activeCategory.value)
    return cat?.name || 'Productos'
  }
  return 'Todos los productos'
})

// Metodos
function selectCategory(categoryId) {
  tenantStore.selectCategory(categoryId)
  searchInput.value = ''
}

function selectSubcategory(subcategoryId) {
  tenantStore.selectSubcategory(subcategoryId)
}

function clearFilters() {
  tenantStore.clearFilters()
  searchInput.value = ''
}

function debouncedSearch() {
  clearTimeout(searchTimeout)
  searchTimeout = setTimeout(() => {
    tenantStore.setSearchQuery(searchInput.value)
  }, 300)
}

function clearSearch() {
  searchInput.value = ''
  tenantStore.setSearchQuery('')
}

function addToCart(product) {
  cartStore.addItem(product)
}

function openProductModal(product) {
  selectedProduct.value = product
}

function addToCartFromModal(product, quantity) {
  cartStore.addItem(product, quantity)
  selectedProduct.value = null
}

function openSofia() {
  chatStore.isOpen = true
}

async function retryLoad() {
  await tenantStore.initializeTenant()
}

// Inicializar al montar
onMounted(async () => {
  await tenantStore.initializeTenant()

  // Actualizar reglas de negocio en cart
  cartStore.updateBusinessRules(tenantStore.businessRules)

  // Si viene con categoria en la URL
  if (route.params.categoryId) {
    selectCategory(parseInt(route.params.categoryId))
  }
})

// Watch para sincronizar con ruta
watch(() => route.params.categoryId, (newCategoryId) => {
  if (newCategoryId) {
    selectCategory(parseInt(newCategoryId))
  }
})
</script>

<style scoped>
.scrollbar-hide::-webkit-scrollbar {
  display: none;
}
.scrollbar-hide {
  -ms-overflow-style: none;
  scrollbar-width: none;
}
.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
