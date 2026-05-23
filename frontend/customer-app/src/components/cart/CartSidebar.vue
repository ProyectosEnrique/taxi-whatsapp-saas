<template>
  <!-- Overlay -->
  <transition name="fade">
    <div
      v-if="cartStore.isOpen"
      @click="cartStore.closeCart()"
      class="fixed inset-0 bg-black bg-opacity-50 z-40"
    ></div>
  </transition>

  <!-- Sidebar -->
  <transition name="slide">
    <div
      v-if="cartStore.isOpen"
      class="fixed top-0 right-0 h-full w-full max-w-md bg-white shadow-2xl z-50 flex flex-col"
    >
      <!-- Header -->
      <div class="flex items-center justify-between p-4 border-b">
        <h2 class="text-xl font-bold">Mi Carrito</h2>
        <button
          @click="cartStore.closeCart()"
          class="p-2 hover:bg-gray-100 rounded-full transition"
        >
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <!-- Carrito Vacío -->
      <div v-if="cartStore.items.length === 0" class="flex-1 flex flex-col items-center justify-center p-8">
        <svg class="w-24 h-24 text-gray-300 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z" />
        </svg>
        <p class="text-gray-500 text-center mb-4">Tu carrito está vacío</p>
        <button
          @click="cartStore.closeCart()"
          class="btn-primary"
        >
          Ver Menú
        </button>
      </div>

      <!-- Items del Carrito -->
      <div v-else class="flex-1 overflow-y-auto p-4 space-y-4">
        <div
          v-for="(item, index) in cartStore.items"
          :key="index"
          class="card flex items-start space-x-4"
        >
          <!-- Imagen -->
          <div class="w-20 h-20 bg-gray-200 rounded-lg flex-shrink-0 overflow-hidden">
            <img
              v-if="item.image"
              :src="item.image"
              :alt="item.name"
              class="w-full h-full object-cover"
            />
            <div v-else class="w-full h-full flex items-center justify-center">
              <svg class="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
              </svg>
            </div>
          </div>

          <!-- Info -->
          <div class="flex-1 min-w-0">
            <h3 class="font-medium text-gray-900 truncate">{{ item.name }}</h3>
            <p class="text-sm text-gray-500">${{ item.price.toFixed(2) }}</p>

            <!-- Customizaciones -->
            <div v-if="Object.keys(item.customizations || {}).length > 0" class="mt-1">
              <p class="text-xs text-gray-400">
                {{ formatCustomizations(item.customizations) }}
              </p>
            </div>

            <!-- Cantidad -->
            <div class="flex items-center space-x-2 mt-2">
              <button
                @click="cartStore.updateQuantity(index, item.quantity - 1)"
                class="w-8 h-8 flex items-center justify-center bg-gray-100 hover:bg-gray-200 rounded"
              >
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 12H4" />
                </svg>
              </button>

              <span class="text-sm font-medium w-8 text-center">{{ item.quantity }}</span>

              <button
                @click="cartStore.updateQuantity(index, item.quantity + 1)"
                class="w-8 h-8 flex items-center justify-center bg-gray-100 hover:bg-gray-200 rounded"
              >
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                </svg>
              </button>
            </div>
          </div>

          <!-- Precio Total -->
          <div class="text-right">
            <p class="font-bold text-gray-900">${{ (item.price * item.quantity).toFixed(2) }}</p>
            <button
              @click="cartStore.removeItem(index)"
              class="text-red-500 hover:text-red-700 text-sm mt-2"
            >
              Eliminar
            </button>
          </div>
        </div>
      </div>

      <!-- Footer con Total y Checkout -->
      <div v-if="cartStore.items.length > 0" class="border-t p-4 space-y-4">
        <!-- Resumen -->
        <div class="space-y-2">
          <div class="flex justify-between text-sm">
            <span class="text-gray-600">Subtotal</span>
            <span class="font-medium">${{ cartStore.subtotal.toFixed(2) }}</span>
          </div>
          <div class="flex justify-between text-sm">
            <span class="text-gray-600">Envío</span>
            <span class="font-medium">${{ cartStore.deliveryFee.toFixed(2) }}</span>
          </div>
          <div class="flex justify-between text-lg font-bold border-t pt-2">
            <span>Total</span>
            <span>${{ cartStore.total.toFixed(2) }}</span>
          </div>
        </div>

        <!-- Alerta de mínimo -->
        <div v-if="!cartStore.meetsMinimum" class="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
          <p class="text-sm text-yellow-800">
            Pedido mínimo: ${{ cartStore.minOrderAmount.toFixed(2) }}
            <br>
            Faltan: ${{ (cartStore.minOrderAmount - cartStore.subtotal).toFixed(2) }}
          </p>
        </div>

        <!-- Botones -->
        <div class="space-y-2">
          <button
            @click="goToCheckout"
            :disabled="!cartStore.meetsMinimum"
            class="btn-primary w-full"
          >
            Proceder al Pago
          </button>
          <button
            @click="cartStore.closeCart()"
            class="btn-secondary w-full"
          >
            Seguir Comprando
          </button>
        </div>
      </div>
    </div>
  </transition>
</template>

<script setup>
import { useCartStore } from '@/stores/cart'
import { useRouter } from 'vue-router'

const cartStore = useCartStore()
const router = useRouter()

function formatCustomizations(customizations) {
  return Object.entries(customizations)
    .map(([key, value]) => `${key}: ${value}`)
    .join(', ')
}

function goToCheckout() {
  cartStore.closeCart()
  router.push('/checkout')
}
</script>

<style scoped>
.slide-enter-active,
.slide-leave-active {
  transition: transform 0.3s ease-out;
}

.slide-enter-from {
  transform: translateX(100%);
}

.slide-leave-to {
  transform: translateX(100%);
}
</style>
