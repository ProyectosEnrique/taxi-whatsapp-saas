<template>
  <div class="card hover:shadow-lg transition-shadow cursor-pointer group">
    <!-- Imagen -->
    <div
      @click="goToProductDetail"
      class="relative h-48 bg-gray-200 rounded-lg overflow-hidden mb-4"
    >
      <img
        v-if="product.image"
        :src="product.image"
        :alt="product.name"
        class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
      />
      <div v-else class="w-full h-full flex items-center justify-center">
        <svg class="w-16 h-16 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
        </svg>
      </div>

      <!-- Badge de categoría -->
      <div class="absolute top-2 left-2">
        <span class="badge badge-success">
          {{ product.category }}
        </span>
      </div>

      <!-- Badge de stock bajo -->
      <div v-if="product.stock && product.stock < 5" class="absolute top-2 right-2">
        <span class="badge badge-warning">
          Últimas unidades
        </span>
      </div>
    </div>

    <!-- Info -->
    <div @click="goToProductDetail">
      <h3 class="font-bold text-lg text-gray-900 mb-2 line-clamp-2">
        {{ product.name }}
      </h3>

      <p v-if="product.description" class="text-sm text-gray-600 mb-3 line-clamp-2">
        {{ product.description }}
      </p>

      <!-- Precio -->
      <div class="flex items-center justify-between mb-4">
        <span class="text-2xl font-bold text-primary-600">
          ${{ product.price.toFixed(2) }}
        </span>

        <!-- Rating (si existe) -->
        <div v-if="product.rating" class="flex items-center space-x-1">
          <svg class="w-5 h-5 text-yellow-400 fill-current" viewBox="0 0 20 20">
            <path d="M10 15l-5.878 3.09 1.123-6.545L.489 6.91l6.572-.955L10 0l2.939 5.955 6.572.955-4.756 4.635 1.123 6.545z"/>
          </svg>
          <span class="text-sm text-gray-600">{{ product.rating }}</span>
        </div>
      </div>
    </div>

    <!-- Botón Agregar -->
    <button
      @click.stop="handleAddToCart"
      :disabled="!isAvailable"
      class="btn-primary w-full"
    >
      <span v-if="isAvailable" class="flex items-center justify-center">
        <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
        </svg>
        Agregar al Carrito
      </span>
      <span v-else>No Disponible</span>
    </button>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'

const props = defineProps({
  product: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['add-to-cart'])

const router = useRouter()

const isAvailable = computed(() => {
  if (!props.product.active) return false
  if (props.product.stock !== undefined && props.product.stock <= 0) return false
  return true
})

function handleAddToCart() {
  if (isAvailable.value) {
    emit('add-to-cart', props.product, 1)
  }
}

function goToProductDetail() {
  router.push({
    name: 'product-detail',
    params: { id: props.product.product_id }
  })
}
</script>

<style scoped>
.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
