<template>
  <!-- Backdrop -->
  <div
    class="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4"
    @click.self="handleClose"
  >
    <!-- Modal -->
    <div
      class="bg-white rounded-2xl shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden"
      @click.stop
    >
      <!-- Header con botón de cerrar -->
      <div class="sticky top-0 bg-white z-10 px-6 py-4 border-b flex items-center justify-between">
        <h2 class="text-2xl font-bold text-gray-900">Detalle del Producto</h2>
        <button
          @click="handleClose"
          class="text-gray-400 hover:text-gray-600 transition-colors"
        >
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <!-- Contenido del modal (scrollable) -->
      <div class="overflow-y-auto max-h-[calc(90vh-200px)]">
        <div class="p-6">
          <div class="grid md:grid-cols-2 gap-8">
            <!-- Columna Izquierda: Imagen -->
            <div>
              <div class="relative bg-gray-200 rounded-lg overflow-hidden aspect-square">
                <img
                  v-if="product.image"
                  :src="product.image"
                  :alt="product.name"
                  class="w-full h-full object-cover"
                />
                <div v-else class="w-full h-full flex items-center justify-center">
                  <svg class="w-24 h-24 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                  </svg>
                </div>

                <!-- Badges sobre la imagen -->
                <div class="absolute top-4 left-4 flex flex-col space-y-2">
                  <span class="badge badge-success">
                    {{ product.category }}
                  </span>

                  <span
                    v-if="product.stock && product.stock < 5"
                    class="badge badge-warning"
                  >
                    Últimas unidades
                  </span>

                  <span
                    v-if="product.prescription_required"
                    class="badge badge-info"
                  >
                    Requiere Receta
                  </span>
                </div>
              </div>

              <!-- Galería de imágenes adicionales (si existen) -->
              <div v-if="product.images && product.images.length > 1" class="mt-4 grid grid-cols-4 gap-2">
                <div
                  v-for="(img, idx) in product.images"
                  :key="idx"
                  class="aspect-square bg-gray-200 rounded-lg overflow-hidden cursor-pointer hover:opacity-75 transition"
                >
                  <img :src="img" :alt="`${product.name} ${idx + 1}`" class="w-full h-full object-cover" />
                </div>
              </div>
            </div>

            <!-- Columna Derecha: Información -->
            <div>
              <!-- Nombre y Precio -->
              <h1 class="text-3xl font-bold text-gray-900 mb-2">
                {{ product.name }}
              </h1>

              <!-- Rating -->
              <div v-if="product.rating" class="flex items-center space-x-2 mb-4">
                <div class="flex items-center">
                  <svg
                    v-for="star in 5"
                    :key="star"
                    class="w-5 h-5"
                    :class="star <= Math.floor(product.rating) ? 'text-yellow-400 fill-current' : 'text-gray-300'"
                    viewBox="0 0 20 20"
                  >
                    <path d="M10 15l-5.878 3.09 1.123-6.545L.489 6.91l6.572-.955L10 0l2.939 5.955 6.572.955-4.756 4.635 1.123 6.545z"/>
                  </svg>
                </div>
                <span class="text-sm text-gray-600">({{ product.rating }})</span>
              </div>

              <!-- Precio -->
              <div class="mb-6">
                <span class="text-4xl font-bold text-primary-600">
                  ${{ product.price.toFixed(2) }}
                </span>
              </div>

              <!-- Descripción -->
              <div v-if="product.description" class="mb-6">
                <h3 class="text-lg font-semibold text-gray-900 mb-2">Descripción</h3>
                <p class="text-gray-700 leading-relaxed">
                  {{ product.description }}
                </p>
              </div>

              <!-- Información adicional -->
              <div class="space-y-4 mb-6">
                <!-- Dosificación (para farmacia) -->
                <div v-if="product.dosage" class="flex items-start">
                  <svg class="w-5 h-5 text-gray-500 mr-3 mt-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  <div>
                    <p class="font-medium text-gray-900">Dosificación</p>
                    <p class="text-gray-600 text-sm">{{ product.dosage }}</p>
                  </div>
                </div>

                <!-- Presentación -->
                <div v-if="product.presentation" class="flex items-start">
                  <svg class="w-5 h-5 text-gray-500 mr-3 mt-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
                  </svg>
                  <div>
                    <p class="font-medium text-gray-900">Presentación</p>
                    <p class="text-gray-600 text-sm">{{ product.presentation }}</p>
                  </div>
                </div>

                <!-- Síntomas -->
                <div v-if="product.symptoms && product.symptoms.length > 0" class="flex items-start">
                  <svg class="w-5 h-5 text-gray-500 mr-3 mt-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                  </svg>
                  <div>
                    <p class="font-medium text-gray-900">Indicado para</p>
                    <div class="flex flex-wrap gap-2 mt-1">
                      <span
                        v-for="symptom in product.symptoms"
                        :key="symptom"
                        class="badge badge-info"
                      >
                        {{ symptom }}
                      </span>
                    </div>
                  </div>
                </div>

                <!-- Alergenos (para restaurante) -->
                <div v-if="product.allergens && product.allergens.length > 0" class="flex items-start">
                  <svg class="w-5 h-5 text-red-500 mr-3 mt-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                  </svg>
                  <div>
                    <p class="font-medium text-gray-900">Alergenos</p>
                    <div class="flex flex-wrap gap-2 mt-1">
                      <span
                        v-for="allergen in product.allergens"
                        :key="allergen"
                        class="badge badge-error"
                      >
                        {{ allergen }}
                      </span>
                    </div>
                  </div>
                </div>

                <!-- Stock -->
                <div v-if="product.stock !== undefined" class="flex items-start">
                  <svg class="w-5 h-5 text-gray-500 mr-3 mt-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4" />
                  </svg>
                  <div>
                    <p class="font-medium text-gray-900">Disponibilidad</p>
                    <p
                      class="text-sm"
                      :class="product.stock > 5 ? 'text-green-600' : 'text-yellow-600'"
                    >
                      {{ product.stock > 0 ? `${product.stock} unidades disponibles` : 'Sin stock' }}
                    </p>
                  </div>
                </div>
              </div>

              <!-- Selector de cantidad -->
              <div v-if="isAvailable" class="mb-6">
                <label class="block text-sm font-medium text-gray-700 mb-2">Cantidad</label>
                <div class="flex items-center space-x-4">
                  <button
                    @click="decreaseQuantity"
                    :disabled="quantity <= 1"
                    class="w-10 h-10 rounded-full bg-gray-200 hover:bg-gray-300 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center transition"
                  >
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 12H4" />
                    </svg>
                  </button>

                  <span class="text-2xl font-bold text-gray-900 w-12 text-center">
                    {{ quantity }}
                  </span>

                  <button
                    @click="increaseQuantity"
                    :disabled="product.stock && quantity >= product.stock"
                    class="w-10 h-10 rounded-full bg-gray-200 hover:bg-gray-300 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center transition"
                  >
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
                    </svg>
                  </button>
                </div>
              </div>

              <!-- Botón de agregar al carrito -->
              <button
                v-if="isAvailable"
                @click="handleAddToCart"
                class="btn-primary w-full py-4 text-lg"
              >
                <span class="flex items-center justify-center">
                  <svg class="w-6 h-6 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z" />
                  </svg>
                  Agregar al Carrito - ${{ (product.price * quantity).toFixed(2) }}
                </span>
              </button>

              <div v-else class="bg-red-50 border border-red-200 rounded-lg p-4">
                <p class="text-red-800 font-medium text-center">
                  Producto no disponible
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  product: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['close', 'add-to-cart'])

const quantity = ref(1)

const isAvailable = computed(() => {
  if (!props.product.active) return false
  if (props.product.stock !== undefined && props.product.stock <= 0) return false
  return true
})

function handleClose() {
  emit('close')
}

function decreaseQuantity() {
  if (quantity.value > 1) {
    quantity.value--
  }
}

function increaseQuantity() {
  if (!props.product.stock || quantity.value < props.product.stock) {
    quantity.value++
  }
}

function handleAddToCart() {
  if (isAvailable.value) {
    emit('add-to-cart', props.product, quantity.value)
  }
}
</script>

<style scoped>
.badge {
  @apply px-3 py-1 rounded-full text-xs font-medium;
}

.badge-success {
  @apply bg-green-100 text-green-800;
}

.badge-warning {
  @apply bg-yellow-100 text-yellow-800;
}

.badge-info {
  @apply bg-blue-100 text-blue-800;
}

.badge-error {
  @apply bg-red-100 text-red-800;
}
</style>
