<template>
  <div class="min-h-screen bg-gray-50">
    <!-- Header -->
    <header class="sticky top-0 z-40 bg-white shadow-sm">
      <div class="max-w-2xl mx-auto px-4 py-4 flex items-center gap-4">
        <button
          @click="goBack"
          class="p-2 hover:bg-gray-100 rounded-full transition-colors"
        >
          <svg class="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
          </svg>
        </button>
        <h1 class="text-lg font-semibold text-gray-900">Finalizar pedido</h1>
      </div>
    </header>

    <main class="max-w-2xl mx-auto px-4 py-6">
      <!-- Empty cart -->
      <div v-if="isEmpty" class="text-center py-12">
        <svg class="w-20 h-20 text-gray-200 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z" />
        </svg>
        <p class="mt-4 text-gray-500">Tu carrito esta vacio</p>
        <button
          @click="goBack"
          class="mt-4 px-6 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 transition-colors"
        >
          Ver productos
        </button>
      </div>

      <div v-else>
        <!-- Order Summary -->
        <div class="bg-white rounded-xl p-4 shadow-sm mb-4">
          <h2 class="font-semibold text-gray-900 mb-4">Resumen del pedido</h2>

          <div class="space-y-3">
            <div
              v-for="item in items"
              :key="item.id"
              class="flex justify-between items-center py-2 border-b border-gray-100 last:border-0"
            >
              <div class="flex-1">
                <p class="text-sm font-medium text-gray-900">{{ item.name }}</p>
                <p class="text-xs text-gray-500">Cantidad: {{ item.quantity }}</p>
              </div>
              <p class="font-medium text-gray-900">
                ${{ (item.price * item.quantity).toFixed(2) }}
              </p>
            </div>
          </div>

          <div class="mt-4 pt-4 border-t space-y-2">
            <div class="flex justify-between text-sm">
              <span class="text-gray-500">Subtotal</span>
              <span>${{ subtotal.toFixed(2) }}</span>
            </div>
            <div class="flex justify-between text-sm">
              <span class="text-gray-500">Envio</span>
              <span>${{ deliveryFee.toFixed(2) }}</span>
            </div>
            <div class="flex justify-between text-lg font-bold pt-2 border-t">
              <span>Total</span>
              <span class="text-green-600">${{ total.toFixed(2) }}</span>
            </div>
          </div>
        </div>

        <!-- Contact Info -->
        <div class="bg-white rounded-xl p-4 shadow-sm mb-4">
          <h2 class="font-semibold text-gray-900 mb-4">Informacion de contacto</h2>

          <div class="space-y-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Nombre completo</label>
              <input
                v-model="form.name"
                type="text"
                class="w-full px-4 py-2.5 rounded-lg border border-gray-200 focus:border-green-500 focus:ring-2 focus:ring-green-500/20 outline-none transition-all"
                placeholder="Tu nombre"
              />
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Telefono</label>
              <input
                v-model="form.phone"
                type="tel"
                class="w-full px-4 py-2.5 rounded-lg border border-gray-200 focus:border-green-500 focus:ring-2 focus:ring-green-500/20 outline-none transition-all"
                placeholder="Tu telefono"
              />
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Direccion de entrega</label>
              <textarea
                v-model="form.address"
                rows="2"
                class="w-full px-4 py-2.5 rounded-lg border border-gray-200 focus:border-green-500 focus:ring-2 focus:ring-green-500/20 outline-none transition-all resize-none"
                placeholder="Calle, numero, colonia..."
              />
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Notas adicionales (opcional)</label>
              <textarea
                v-model="form.notes"
                rows="2"
                class="w-full px-4 py-2.5 rounded-lg border border-gray-200 focus:border-green-500 focus:ring-2 focus:ring-green-500/20 outline-none transition-all resize-none"
                placeholder="Instrucciones especiales..."
              />
            </div>
          </div>
        </div>

        <!-- Payment Method -->
        <div class="bg-white rounded-xl p-4 shadow-sm mb-6">
          <h2 class="font-semibold text-gray-900 mb-4">Metodo de pago</h2>

          <div class="space-y-3">
            <label
              v-for="method in paymentMethods"
              :key="method.id"
              class="flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-colors"
              :class="form.paymentMethod === method.id ? 'border-green-500 bg-green-50' : 'border-gray-200 hover:border-gray-300'"
            >
              <input
                v-model="form.paymentMethod"
                type="radio"
                :value="method.id"
                class="w-4 h-4 text-green-500 focus:ring-green-500"
              />
              <span class="text-2xl">{{ method.icon }}</span>
              <span class="font-medium text-gray-900">{{ method.name }}</span>
            </label>
          </div>
        </div>

        <!-- Submit Button -->
        <button
          @click="submitOrder"
          :disabled="!isFormValid || isSubmitting"
          class="w-full py-4 rounded-xl font-semibold text-white transition-colors disabled:bg-gray-300 disabled:cursor-not-allowed"
          :class="isFormValid && !isSubmitting ? 'bg-green-500 hover:bg-green-600' : ''"
        >
          <span v-if="isSubmitting" class="flex items-center justify-center gap-2">
            <svg class="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            Procesando...
          </span>
          <span v-else>Confirmar pedido - ${{ total.toFixed(2) }}</span>
        </button>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useCartStore } from '@/stores/cart'

const router = useRouter()
const cartStore = useCartStore()

// Form data
const form = ref({
  name: '',
  phone: '',
  address: '',
  notes: '',
  paymentMethod: 'cash'
})

const isSubmitting = ref(false)

// Payment methods
const paymentMethods = [
  { id: 'cash', name: 'Efectivo', icon: '💵' },
  { id: 'card', name: 'Tarjeta', icon: '💳' },
  { id: 'transfer', name: 'Transferencia', icon: '🏦' }
]

// Computed from cart
const items = computed(() => cartStore.items)
const isEmpty = computed(() => cartStore.isEmpty)
const subtotal = computed(() => cartStore.subtotal)
const total = computed(() => cartStore.total)
const deliveryFee = computed(() => cartStore.deliveryFee)

// Form validation
const isFormValid = computed(() => {
  return form.value.name.trim() &&
         form.value.phone.trim() &&
         form.value.address.trim() &&
         form.value.paymentMethod
})

// Methods
function goBack() {
  router.push('/')
}

async function submitOrder() {
  if (!isFormValid.value || isSubmitting.value) return

  isSubmitting.value = true

  try {
    // Simular envio (aqui iria la llamada real al API)
    await new Promise(resolve => setTimeout(resolve, 2000))

    // Limpiar carrito
    cartStore.clearCart()

    // Mostrar confirmacion
    alert('Pedido confirmado! Te contactaremos pronto.')

    // Regresar al menu
    router.push('/')
  } catch (error) {
    console.error('Error al enviar pedido:', error)
    alert('Error al procesar el pedido. Intenta de nuevo.')
  } finally {
    isSubmitting.value = false
  }
}
</script>
