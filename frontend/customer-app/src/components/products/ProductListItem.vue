<template>
  <div
    class="px-6 py-4 hover:bg-gray-50 cursor-pointer transition-colors group"
    :class="{ 'opacity-50': !isAvailable }"
  >
    <div class="flex items-center justify-between">
      <!-- Información del producto (izquierda) -->
      <div class="flex-1 pr-4">
        <div class="flex items-center space-x-3">
          <!-- Badge de categoría -->
          <span class="badge badge-success text-xs">
            {{ product.category }}
          </span>

          <!-- Nombre del producto -->
          <h3 class="text-lg font-medium text-gray-900 group-hover:text-primary-600 transition-colors">
            {{ product.name }}
          </h3>

          <!-- Indicadores de stock o especiales -->
          <div class="flex items-center space-x-2">
            <span
              v-if="product.stock && product.stock < 5"
              class="badge badge-warning text-xs"
            >
              Últimas unidades
            </span>

            <span
              v-if="product.prescription_required"
              class="badge badge-info text-xs"
            >
              Receta
            </span>

            <span
              v-if="!isAvailable"
              class="badge badge-error text-xs"
            >
              No disponible
            </span>
          </div>
        </div>

        <!-- Descripción breve (opcional, solo en modo expandido) -->
        <p
          v-if="showDescription && product.description"
          class="mt-1 text-sm text-gray-600 line-clamp-1"
        >
          {{ product.description }}
        </p>
      </div>

      <!-- Precio y puntos de relleno (derecha) -->
      <div class="flex items-center space-x-4">
        <!-- Línea punteada de separación (estilo menú físico) -->
        <div class="hidden md:block flex-1 border-b border-dotted border-gray-300 mx-4"></div>

        <!-- Precio -->
        <div class="text-right">
          <span class="text-2xl font-bold text-primary-600">
            ${{ product.price.toFixed(2) }}
          </span>

          <!-- Rating (si existe) -->
          <div v-if="product.rating" class="flex items-center justify-end space-x-1 mt-1">
            <svg class="w-4 h-4 text-yellow-400 fill-current" viewBox="0 0 20 20">
              <path d="M10 15l-5.878 3.09 1.123-6.545L.489 6.91l6.572-.955L10 0l2.939 5.955 6.572.955-4.756 4.635 1.123 6.545z"/>
            </svg>
            <span class="text-xs text-gray-600">{{ product.rating }}</span>
          </div>
        </div>

        <!-- Ícono de ver más -->
        <div class="ml-4">
          <svg
            class="w-6 h-6 text-gray-400 group-hover:text-primary-600 transition-colors"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
          </svg>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  product: {
    type: Object,
    required: true
  },
  showDescription: {
    type: Boolean,
    default: false
  }
})

const isAvailable = computed(() => {
  if (!props.product.active) return false
  if (props.product.stock !== undefined && props.product.stock <= 0) return false
  return true
})
</script>

<style scoped>
.line-clamp-1 {
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.badge {
  @apply px-2 py-1 rounded-full text-xs font-medium;
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
