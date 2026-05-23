<template>
  <Teleport to="body">
    <!-- Overlay -->
    <div
      class="fixed inset-0 bg-black/50 z-50 flex items-end sm:items-center justify-center"
      @click.self="$emit('close')"
    >
      <!-- Modal -->
      <div class="bg-white w-full sm:max-w-lg sm:rounded-2xl rounded-t-2xl max-h-[90vh] overflow-y-auto">
        <!-- Header -->
        <div class="sticky top-0 bg-white px-4 py-3 border-b flex items-center justify-between z-10">
          <h2 class="text-lg font-semibold text-gray-900">Detalle del producto</h2>
          <button
            @click="$emit('close')"
            class="p-2 hover:bg-gray-100 rounded-full transition-colors"
          >
            <svg class="w-5 h-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <!-- Content -->
        <div class="p-4">
          <!-- Badge de receta -->
          <div v-if="product.requires_prescription" class="mb-3">
            <span class="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-red-100 text-red-700">
              <svg class="w-4 h-4 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
              Requiere receta medica
            </span>
          </div>

          <!-- Nombre -->
          <h3 class="text-xl font-bold text-gray-900 mb-2">
            {{ product.name }}
          </h3>

          <!-- Info basica -->
          <div class="space-y-2 mb-4">
            <p v-if="product.generic_name" class="text-sm text-gray-600">
              <span class="font-medium">Generico:</span> {{ product.generic_name }}
            </p>
            <p v-if="product.active_ingredient" class="text-sm text-gray-600">
              <span class="font-medium">Principio activo:</span> {{ product.active_ingredient }}
            </p>
            <p v-if="product.presentation" class="text-sm text-gray-600">
              <span class="font-medium">Presentacion:</span> {{ product.presentation }}
              <span v-if="product.dosage">- {{ product.dosage }}</span>
            </p>
          </div>

          <!-- Descripcion -->
          <p v-if="product.description" class="text-sm text-gray-500 mb-4">
            {{ product.description }}
          </p>

          <!-- Categoria -->
          <div v-if="product.main_category_name" class="mb-4">
            <span class="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-green-100 text-green-700">
              {{ product.main_category_name }}
              <span v-if="product.subcategory_name" class="ml-1 text-green-600">
                / {{ product.subcategory_name }}
              </span>
            </span>
          </div>

          <!-- Sintomas (si hay) -->
          <div v-if="product.symptoms && product.symptoms.length > 0" class="mb-4">
            <p class="text-sm font-medium text-gray-700 mb-2">Indicado para:</p>
            <div class="flex flex-wrap gap-2">
              <span
                v-for="symptom in product.symptoms"
                :key="symptom"
                class="px-2 py-1 bg-gray-100 rounded-full text-xs text-gray-600"
              >
                {{ symptom }}
              </span>
            </div>
          </div>

          <!-- Precio y Stock -->
          <div class="flex items-center justify-between py-4 border-t border-b mb-4">
            <div>
              <p class="text-3xl font-bold text-green-600">
                ${{ product.price?.toFixed(2) }}
              </p>
              <p v-if="product.stock > 0" class="text-sm text-green-600 mt-1">
                {{ product.stock }} unidades disponibles
              </p>
              <p v-else class="text-sm text-red-500 mt-1">
                Producto agotado
              </p>
            </div>

            <!-- Quantity selector -->
            <div v-if="product.stock > 0" class="flex items-center gap-3">
              <button
                @click="quantity > 1 && quantity--"
                :disabled="quantity <= 1"
                class="w-10 h-10 rounded-full border border-gray-300 flex items-center justify-center hover:bg-gray-100 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <svg class="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 12H4" />
                </svg>
              </button>
              <span class="w-8 text-center text-xl font-semibold">{{ quantity }}</span>
              <button
                @click="quantity < product.stock && quantity++"
                :disabled="quantity >= product.stock"
                class="w-10 h-10 rounded-full border border-gray-300 flex items-center justify-center hover:bg-gray-100 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <svg class="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
                </svg>
              </button>
            </div>
          </div>

          <!-- Advertencias -->
          <div v-if="product.min_age && product.min_age > 0" class="mb-4 p-3 bg-amber-50 rounded-lg">
            <p class="text-sm text-amber-700">
              <svg class="w-4 h-4 inline mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
              Edad minima recomendada: {{ product.min_age }} años
            </p>
          </div>

          <!-- Add to cart button -->
          <button
            @click="addToCart"
            :disabled="product.stock <= 0"
            class="w-full py-4 rounded-xl font-semibold text-white transition-colors disabled:bg-gray-300 disabled:cursor-not-allowed"
            :class="product.stock > 0 ? 'bg-green-500 hover:bg-green-600' : ''"
          >
            <span v-if="product.stock > 0">
              Agregar {{ quantity }} al carrito - ${{ (product.price * quantity).toFixed(2) }}
            </span>
            <span v-else>Producto no disponible</span>
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref } from 'vue'

const props = defineProps({
  product: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['close', 'add-to-cart'])

const quantity = ref(1)

function addToCart() {
  emit('add-to-cart', props.product, quantity.value)
}
</script>
