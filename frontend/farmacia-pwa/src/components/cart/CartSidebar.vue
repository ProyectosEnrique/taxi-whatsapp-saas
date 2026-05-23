<template>
  <Teleport to="body">
    <!-- Overlay -->
    <Transition name="fade">
      <div
        v-if="isOpen"
        class="fixed inset-0 bg-black/50 z-50"
        @click="closeCart"
      />
    </Transition>

    <!-- Sidebar -->
    <Transition name="slide">
      <div
        v-if="isOpen"
        class="fixed right-0 top-0 h-full w-full max-w-md bg-white shadow-xl z-50 flex flex-col"
      >
        <!-- Header -->
        <div class="flex items-center justify-between px-4 py-4 border-b">
          <h2 class="text-lg font-semibold text-gray-900">
            Mi carrito
            <span v-if="itemCount > 0" class="text-sm font-normal text-gray-500">
              ({{ itemCount }} {{ itemCount === 1 ? 'producto' : 'productos' }})
            </span>
          </h2>
          <button
            @click="closeCart"
            class="p-2 hover:bg-gray-100 rounded-full transition-colors"
          >
            <svg class="w-5 h-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <!-- Cart Items -->
        <div class="flex-1 overflow-y-auto p-4">
          <!-- Empty State -->
          <div v-if="isEmpty" class="flex flex-col items-center justify-center h-full text-center">
            <svg class="w-20 h-20 text-gray-200" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z" />
            </svg>
            <p class="mt-4 text-gray-500 font-medium">Tu carrito esta vacio</p>
            <p class="text-sm text-gray-400 mt-1">Agrega productos para continuar</p>
            <button
              @click="closeCart"
              class="mt-6 px-6 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 transition-colors"
            >
              Ver productos
            </button>
          </div>

          <!-- Items List -->
          <div v-else class="space-y-4">
            <div
              v-for="item in items"
              :key="item.id"
              class="flex gap-3 p-3 bg-gray-50 rounded-xl"
            >
              <!-- Info -->
              <div class="flex-1 min-w-0">
                <h3 class="font-medium text-gray-900 text-sm line-clamp-2">{{ item.name }}</h3>
                <p class="text-green-600 font-semibold mt-1">${{ item.price?.toFixed(2) }}</p>

                <!-- Quantity controls -->
                <div class="flex items-center gap-2 mt-2">
                  <button
                    @click="decrementItem(item.id)"
                    class="w-8 h-8 rounded-full bg-white border border-gray-200 flex items-center justify-center hover:bg-gray-100 transition-colors"
                  >
                    <svg class="w-4 h-4 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 12H4" />
                    </svg>
                  </button>
                  <span class="w-8 text-center font-medium">{{ item.quantity }}</span>
                  <button
                    @click="incrementItem(item.id)"
                    class="w-8 h-8 rounded-full bg-white border border-gray-200 flex items-center justify-center hover:bg-gray-100 transition-colors"
                  >
                    <svg class="w-4 h-4 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
                    </svg>
                  </button>
                </div>
              </div>

              <!-- Remove button -->
              <button
                @click="removeItem(item.id)"
                class="p-1 text-gray-400 hover:text-red-500 transition-colors self-start"
              >
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              </button>
            </div>
          </div>
        </div>

        <!-- Footer -->
        <div v-if="!isEmpty" class="border-t p-4 bg-gray-50">
          <!-- Summary -->
          <div class="space-y-2 mb-4">
            <div class="flex justify-between text-sm">
              <span class="text-gray-500">Subtotal</span>
              <span class="font-medium">${{ subtotal.toFixed(2) }}</span>
            </div>
            <div class="flex justify-between text-sm">
              <span class="text-gray-500">Envio</span>
              <span class="font-medium">${{ deliveryFee.toFixed(2) }}</span>
            </div>
            <div class="flex justify-between text-base pt-2 border-t">
              <span class="font-semibold">Total</span>
              <span class="font-bold text-green-600">${{ total.toFixed(2) }}</span>
            </div>
          </div>

          <!-- Minimum order warning -->
          <p v-if="!meetsMinimum" class="text-xs text-amber-600 mb-3 text-center">
            Pedido minimo: ${{ minOrderAmount.toFixed(2) }}
          </p>

          <!-- Checkout button -->
          <button
            @click="goToCheckout"
            :disabled="!meetsMinimum"
            class="w-full py-3 rounded-xl font-semibold text-white transition-colors disabled:bg-gray-300 disabled:cursor-not-allowed"
            :class="meetsMinimum ? 'bg-green-500 hover:bg-green-600' : ''"
          >
            Continuar al pago
          </button>

          <!-- Clear cart -->
          <button
            @click="confirmClear"
            class="w-full mt-2 py-2 text-sm text-gray-500 hover:text-red-500 transition-colors"
          >
            Vaciar carrito
          </button>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useCartStore } from '@/stores/cart'

const router = useRouter()
const cartStore = useCartStore()

// Computed
const isOpen = computed(() => cartStore.isOpen)
const items = computed(() => cartStore.items)
const itemCount = computed(() => cartStore.itemCount)
const isEmpty = computed(() => cartStore.isEmpty)
const subtotal = computed(() => cartStore.subtotal)
const total = computed(() => cartStore.total)
const deliveryFee = computed(() => cartStore.deliveryFee)
const minOrderAmount = computed(() => cartStore.minOrderAmount)
const meetsMinimum = computed(() => cartStore.meetsMinimum)

// Methods
function closeCart() {
  cartStore.closeCart()
}

function incrementItem(productId) {
  cartStore.incrementItem(productId)
}

function decrementItem(productId) {
  cartStore.decrementItem(productId)
}

function removeItem(productId) {
  cartStore.removeItem(productId)
}

function confirmClear() {
  if (confirm('¿Estas seguro de vaciar el carrito?')) {
    cartStore.clearCart()
  }
}

function goToCheckout() {
  closeCart()
  router.push('/checkout')
}
</script>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.slide-enter-active,
.slide-leave-active {
  transition: transform 0.3s ease;
}
.slide-enter-from,
.slide-leave-to {
  transform: translateX(100%);
}

.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
