<template>
  <div class="container mx-auto px-4 py-8 max-w-6xl">
    <h1 class="text-3xl font-bold mb-8">Finalizar Pedido</h1>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
      <!-- Left Column: Formulario -->
      <div class="lg:col-span-2 space-y-6">
        <!-- Paso 1: Información de Contacto -->
        <div class="card">
          <div class="flex items-center mb-4">
            <div class="w-8 h-8 bg-primary-600 text-white rounded-full flex items-center justify-center font-bold mr-3">
              1
            </div>
            <h2 class="text-xl font-bold">Información de Contacto</h2>
          </div>

          <div v-if="!authStore.isAuthenticated" class="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
            <p class="text-sm text-blue-800">
              ¿Ya tienes cuenta?
              <router-link to="/login" class="font-medium underline">Inicia sesión</router-link>
              para una experiencia más rápida
            </p>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium mb-1">Nombre</label>
              <input
                v-model="checkoutData.name"
                type="text"
                required
                class="input"
                :placeholder="authStore.isAuthenticated ? authStore.userName : 'Tu nombre'"
              />
            </div>
            <div>
              <label class="block text-sm font-medium mb-1">Teléfono</label>
              <input
                v-model="checkoutData.phone"
                type="tel"
                required
                class="input"
                placeholder="+52 55 1234 5678"
              />
            </div>
            <div class="md:col-span-2">
              <label class="block text-sm font-medium mb-1">Email</label>
              <input
                v-model="checkoutData.email"
                type="email"
                required
                class="input"
                :placeholder="authStore.isAuthenticated ? authStore.userEmail : 'tu@email.com'"
              />
            </div>
          </div>
        </div>

        <!-- Paso 2: Dirección de Entrega -->
        <div class="card">
          <div class="flex items-center mb-4">
            <div class="w-8 h-8 bg-primary-600 text-white rounded-full flex items-center justify-center font-bold mr-3">
              2
            </div>
            <h2 class="text-xl font-bold">Dirección de Entrega</h2>
          </div>

          <div class="space-y-4">
            <div>
              <label class="block text-sm font-medium mb-1">Calle y Número</label>
              <input
                v-model="checkoutData.address.street"
                type="text"
                required
                class="input"
                placeholder="Av. Principal 123"
              />
            </div>

            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-sm font-medium mb-1">Colonia</label>
                <input
                  v-model="checkoutData.address.neighborhood"
                  type="text"
                  required
                  class="input"
                  placeholder="Centro"
                />
              </div>
              <div>
                <label class="block text-sm font-medium mb-1">Código Postal</label>
                <input
                  v-model="checkoutData.address.zipCode"
                  type="text"
                  required
                  class="input"
                  placeholder="06000"
                />
              </div>
            </div>

            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-sm font-medium mb-1">Ciudad</label>
                <input
                  v-model="checkoutData.address.city"
                  type="text"
                  required
                  class="input"
                  placeholder="Ciudad de México"
                />
              </div>
              <div>
                <label class="block text-sm font-medium mb-1">Estado</label>
                <input
                  v-model="checkoutData.address.state"
                  type="text"
                  required
                  class="input"
                  placeholder="CDMX"
                />
              </div>
            </div>

            <div>
              <label class="block text-sm font-medium mb-1">Referencia (opcional)</label>
              <textarea
                v-model="checkoutData.address.reference"
                class="input"
                rows="2"
                placeholder="Casa blanca, portón negro..."
              ></textarea>
            </div>
          </div>
        </div>

        <!-- Paso 3: Método de Pago -->
        <div class="card">
          <div class="flex items-center mb-4">
            <div class="w-8 h-8 bg-primary-600 text-white rounded-full flex items-center justify-center font-bold mr-3">
              3
            </div>
            <h2 class="text-xl font-bold">Método de Pago</h2>
          </div>

          <div class="space-y-3">
            <label class="flex items-center p-4 border-2 rounded-lg cursor-pointer hover:bg-gray-50 transition"
                   :class="checkoutData.paymentMethod === 'cash' ? 'border-primary-600 bg-primary-50' : 'border-gray-200'">
              <input
                v-model="checkoutData.paymentMethod"
                type="radio"
                value="cash"
                class="h-4 w-4 text-primary-600"
              />
              <div class="ml-3">
                <p class="font-medium">Efectivo</p>
                <p class="text-sm text-gray-600">Paga al recibir tu pedido</p>
              </div>
            </label>

            <label class="flex items-center p-4 border-2 rounded-lg cursor-pointer hover:bg-gray-50 transition"
                   :class="checkoutData.paymentMethod === 'card' ? 'border-primary-600 bg-primary-50' : 'border-gray-200'">
              <input
                v-model="checkoutData.paymentMethod"
                type="radio"
                value="card"
                class="h-4 w-4 text-primary-600"
              />
              <div class="ml-3">
                <p class="font-medium">Tarjeta de Crédito/Débito</p>
                <p class="text-sm text-gray-600">Pago seguro en línea</p>
              </div>
            </label>

            <label class="flex items-center p-4 border-2 rounded-lg cursor-pointer hover:bg-gray-50 transition"
                   :class="checkoutData.paymentMethod === 'transfer' ? 'border-primary-600 bg-primary-50' : 'border-gray-200'">
              <input
                v-model="checkoutData.paymentMethod"
                type="radio"
                value="transfer"
                class="h-4 w-4 text-primary-600"
              />
              <div class="ml-3">
                <p class="font-medium">Transferencia</p>
                <p class="text-sm text-gray-600">Envía comprobante después</p>
              </div>
            </label>
          </div>
        </div>

        <!-- Paso 4: Notas Adicionales -->
        <div class="card">
          <div class="flex items-center mb-4">
            <div class="w-8 h-8 bg-gray-300 text-white rounded-full flex items-center justify-center font-bold mr-3">
              4
            </div>
            <h2 class="text-xl font-bold">Notas Adicionales</h2>
          </div>

          <textarea
            v-model="checkoutData.notes"
            class="input"
            rows="3"
            placeholder="Instrucciones especiales para tu pedido..."
          ></textarea>
        </div>
      </div>

      <!-- Right Column: Resumen del Pedido -->
      <div class="lg:col-span-1">
        <div class="card sticky top-4">
          <h2 class="text-xl font-bold mb-4">Resumen del Pedido</h2>

          <!-- Items -->
          <div class="space-y-3 mb-4 max-h-64 overflow-y-auto">
            <div
              v-for="(item, index) in cartStore.items"
              :key="index"
              class="flex items-start space-x-3"
            >
              <div class="w-16 h-16 bg-gray-200 rounded flex-shrink-0"></div>
              <div class="flex-1 min-w-0">
                <p class="font-medium text-sm truncate">{{ item.name }}</p>
                <p class="text-xs text-gray-600">Cantidad: {{ item.quantity }}</p>
                <p class="text-sm font-bold text-primary-600">
                  ${{ (item.price * item.quantity).toFixed(2) }}
                </p>
              </div>
            </div>
          </div>

          <!-- Código Promocional -->
          <div class="border-t pt-4 mb-4">
            <div class="flex space-x-2">
              <input
                v-model="promoCode"
                type="text"
                class="input flex-1"
                placeholder="Código promocional"
              />
              <button
                @click="applyPromoCode"
                :disabled="promotionsStore.loading"
                class="btn-secondary whitespace-nowrap"
              >
                Aplicar
              </button>
            </div>
            <p v-if="promotionsStore.appliedPromoCode" class="text-xs text-green-600 mt-1">
              ✓ Código aplicado: {{ promotionsStore.appliedPromoCode.code }}
            </p>
          </div>

          <!-- Totales -->
          <div class="border-t pt-4 space-y-2">
            <div class="flex justify-between text-sm">
              <span class="text-gray-600">Subtotal</span>
              <span class="font-medium">${{ cartStore.subtotal.toFixed(2) }}</span>
            </div>

            <div v-if="discount > 0" class="flex justify-between text-sm text-green-600">
              <span>Descuento</span>
              <span>-${{ discount.toFixed(2) }}</span>
            </div>

            <div class="flex justify-between text-sm">
              <span class="text-gray-600">Envío</span>
              <span class="font-medium">${{ cartStore.deliveryFee.toFixed(2) }}</span>
            </div>

            <div class="flex justify-between text-lg font-bold border-t pt-2">
              <span>Total</span>
              <span class="text-primary-600">${{ finalTotal.toFixed(2) }}</span>
            </div>
          </div>

          <!-- Botón Confirmar -->
          <button
            @click="handleCheckout"
            :disabled="!canCheckout || ordersStore.loading"
            class="btn-primary w-full mt-4"
          >
            <span v-if="!ordersStore.loading">Confirmar Pedido</span>
            <span v-else class="flex items-center justify-center">
              <svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              Procesando...
            </span>
          </button>

          <p v-if="!cartStore.meetsMinimum" class="text-xs text-red-600 mt-2">
            Pedido mínimo: ${{ cartStore.minOrderAmount.toFixed(2) }}
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useCartStore } from '@/stores/cart'
import { useAuthStore } from '@/stores/auth'
import { useOrdersStore } from '@/stores/orders'
import { usePromotionsStore } from '@/stores/promotions'
import { useTenantStore } from '@/stores/tenant'

const router = useRouter()
const cartStore = useCartStore()
const authStore = useAuthStore()
const ordersStore = useOrdersStore()
const promotionsStore = usePromotionsStore()
const tenantStore = useTenantStore()

const checkoutData = ref({
  name: '',
  phone: '',
  email: '',
  address: {
    street: '',
    neighborhood: '',
    zipCode: '',
    city: '',
    state: '',
    reference: ''
  },
  paymentMethod: 'cash',
  notes: ''
})

const promoCode = ref('')

const discount = computed(() => {
  if (!promotionsStore.appliedPromoCode) return 0
  return promotionsStore.calculateDiscount(cartStore.subtotal)
})

const finalTotal = computed(() => {
  return cartStore.subtotal - discount.value + cartStore.deliveryFee
})

const canCheckout = computed(() => {
  return cartStore.meetsMinimum &&
         cartStore.items.length > 0 &&
         checkoutData.value.name &&
         checkoutData.value.phone &&
         checkoutData.value.email &&
         checkoutData.value.address.street &&
         checkoutData.value.paymentMethod
})

async function applyPromoCode() {
  if (!promoCode.value) return

  const result = await promotionsStore.applyPromoCode(promoCode.value)
  if (!result.success) {
    alert(result.error)
  }
}

async function handleCheckout() {
  if (!canCheckout.value) return

  try {
    const orderData = {
      tenant_id: tenantStore.tenantId,
      customer: {
        name: checkoutData.value.name,
        phone: checkoutData.value.phone,
        email: checkoutData.value.email
      },
      items: cartStore.items,
      delivery_address: checkoutData.value.address,
      payment_method: checkoutData.value.paymentMethod,
      promo_code: promotionsStore.appliedPromoCode?.code || null,
      notes: checkoutData.value.notes,
      subtotal: cartStore.subtotal,
      discount: discount.value,
      delivery_fee: cartStore.deliveryFee,
      total: finalTotal.value
    }

    const order = await ordersStore.createOrder(orderData)

    // Limpiar carrito
    cartStore.clearCart()

    // Redirigir a tracking
    router.push({
      name: 'order-tracking',
      params: { orderId: order.order_id }
    })
  } catch (error) {
    console.error('Error al crear pedido:', error)
    alert('Hubo un error al procesar tu pedido. Inténtalo de nuevo.')
  }
}

onMounted(() => {
  // Verificar que el carrito no esté vacío
  if (cartStore.items.length === 0) {
    router.push('/')
    return
  }

  // Pre-llenar datos si está autenticado
  if (authStore.isAuthenticated) {
    checkoutData.value.name = authStore.userName
    checkoutData.value.email = authStore.userEmail
  }
})
</script>
