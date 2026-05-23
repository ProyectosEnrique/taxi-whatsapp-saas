<template>
  <div class="container mx-auto px-4 py-8 max-w-4xl">
    <!-- Loading State -->
    <div v-if="ordersStore.loading" class="text-center py-12">
      <div class="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mb-4"></div>
      <p class="text-gray-600">Cargando información del pedido...</p>
    </div>

    <!-- Error State -->
    <div v-else-if="ordersStore.error" class="text-center py-12">
      <svg class="w-16 h-16 text-red-500 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      <p class="text-red-600 mb-4">{{ ordersStore.error }}</p>
      <router-link to="/" class="btn-primary">
        Volver al Menú
      </router-link>
    </div>

    <!-- Order Found -->
    <div v-else-if="order" class="space-y-6">
      <!-- Header -->
      <div class="text-center">
        <h1 class="text-3xl font-bold mb-2">Seguimiento de Pedido</h1>
        <p class="text-gray-600">Pedido #{{ order.order_id }}</p>
      </div>

      <!-- Timeline de Estado -->
      <div class="card">
        <h2 class="text-xl font-bold mb-6">Estado del Pedido</h2>

        <div class="space-y-4">
          <!-- Recibido -->
          <div class="flex items-start">
            <div class="flex-shrink-0">
              <div :class="[
                'w-10 h-10 rounded-full flex items-center justify-center',
                isStatusCompleted('pending') ? 'bg-green-500' : 'bg-gray-300'
              ]">
                <svg v-if="isStatusCompleted('pending')" class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                </svg>
                <span v-else class="text-white font-bold">1</span>
              </div>
            </div>
            <div class="ml-4 flex-1">
              <p class="font-medium">Pedido Recibido</p>
              <p class="text-sm text-gray-600">Hemos recibido tu pedido</p>
              <p v-if="order.created_at" class="text-xs text-gray-500 mt-1">
                {{ formatDate(order.created_at) }}
              </p>
            </div>
          </div>

          <!-- Preparando -->
          <div class="flex items-start">
            <div class="flex-shrink-0">
              <div :class="[
                'w-10 h-10 rounded-full flex items-center justify-center',
                isStatusCompleted('preparing') ? 'bg-green-500' : currentStatus === 'preparing' ? 'bg-yellow-500 animate-pulse' : 'bg-gray-300'
              ]">
                <svg v-if="isStatusCompleted('preparing')" class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                </svg>
                <span v-else class="text-white font-bold">2</span>
              </div>
            </div>
            <div class="ml-4 flex-1">
              <p class="font-medium">En Preparación</p>
              <p class="text-sm text-gray-600">Estamos preparando tu pedido</p>
              <p v-if="currentStatus === 'preparing'" class="text-xs text-yellow-600 mt-1">
                ⏱ Tiempo estimado: {{ order.estimated_time || '15-20' }} min
              </p>
            </div>
          </div>

          <!-- En Camino -->
          <div class="flex items-start">
            <div class="flex-shrink-0">
              <div :class="[
                'w-10 h-10 rounded-full flex items-center justify-center',
                isStatusCompleted('in_transit') ? 'bg-green-500' : currentStatus === 'in_transit' ? 'bg-blue-500 animate-pulse' : 'bg-gray-300'
              ]">
                <svg v-if="isStatusCompleted('in_transit')" class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                </svg>
                <span v-else class="text-white font-bold">3</span>
              </div>
            </div>
            <div class="ml-4 flex-1">
              <p class="font-medium">En Camino</p>
              <p class="text-sm text-gray-600">Tu pedido está en camino</p>
              <p v-if="order.driver && currentStatus === 'in_transit'" class="text-xs text-gray-600 mt-1">
                Repartidor: {{ order.driver.name }}
              </p>
            </div>
          </div>

          <!-- Entregado -->
          <div class="flex items-start">
            <div class="flex-shrink-0">
              <div :class="[
                'w-10 h-10 rounded-full flex items-center justify-center',
                currentStatus === 'delivered' ? 'bg-green-500' : 'bg-gray-300'
              ]">
                <svg v-if="currentStatus === 'delivered'" class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                </svg>
                <span v-else class="text-white font-bold">4</span>
              </div>
            </div>
            <div class="ml-4 flex-1">
              <p class="font-medium">Entregado</p>
              <p class="text-sm text-gray-600">¡Disfruta tu pedido!</p>
            </div>
          </div>
        </div>

        <!-- Cancelado -->
        <div v-if="currentStatus === 'cancelled'" class="mt-6 bg-red-50 border border-red-200 rounded-lg p-4">
          <p class="text-red-800 font-medium">Pedido Cancelado</p>
          <p v-if="order.cancel_reason" class="text-sm text-red-600 mt-1">
            Motivo: {{ order.cancel_reason }}
          </p>
        </div>
      </div>

      <!-- Detalles del Pedido -->
      <div class="card">
        <h2 class="text-xl font-bold mb-4">Detalles del Pedido</h2>

        <!-- Items -->
        <div class="space-y-3 mb-6">
          <div
            v-for="(item, index) in order.items"
            :key="index"
            class="flex items-start justify-between"
          >
            <div class="flex items-start space-x-3">
              <div class="w-16 h-16 bg-gray-200 rounded flex-shrink-0"></div>
              <div>
                <p class="font-medium">{{ item.name }}</p>
                <p class="text-sm text-gray-600">Cantidad: {{ item.quantity }}</p>
              </div>
            </div>
            <p class="font-medium">${{ (item.price * item.quantity).toFixed(2) }}</p>
          </div>
        </div>

        <!-- Totales -->
        <div class="border-t pt-4 space-y-2">
          <div class="flex justify-between text-sm">
            <span class="text-gray-600">Subtotal</span>
            <span>${{ order.subtotal?.toFixed(2) }}</span>
          </div>
          <div v-if="order.discount > 0" class="flex justify-between text-sm text-green-600">
            <span>Descuento</span>
            <span>-${{ order.discount?.toFixed(2) }}</span>
          </div>
          <div class="flex justify-between text-sm">
            <span class="text-gray-600">Envío</span>
            <span>${{ order.delivery_fee?.toFixed(2) }}</span>
          </div>
          <div class="flex justify-between text-lg font-bold border-t pt-2">
            <span>Total</span>
            <span class="text-primary-600">${{ order.total?.toFixed(2) }}</span>
          </div>
        </div>
      </div>

      <!-- Información de Entrega -->
      <div class="card">
        <h2 class="text-xl font-bold mb-4">Información de Entrega</h2>

        <div class="space-y-3">
          <div>
            <p class="text-sm text-gray-600">Nombre</p>
            <p class="font-medium">{{ order.customer?.name }}</p>
          </div>
          <div>
            <p class="text-sm text-gray-600">Teléfono</p>
            <p class="font-medium">{{ order.customer?.phone }}</p>
          </div>
          <div>
            <p class="text-sm text-gray-600">Dirección</p>
            <p class="font-medium">{{ formatAddress(order.delivery_address) }}</p>
          </div>
          <div v-if="order.notes">
            <p class="text-sm text-gray-600">Notas</p>
            <p class="font-medium">{{ order.notes }}</p>
          </div>
        </div>
      </div>

      <!-- Acciones -->
      <div class="flex space-x-4">
        <router-link to="/order-history" class="btn-secondary flex-1">
          Ver Mis Pedidos
        </router-link>
        <router-link to="/" class="btn-primary flex-1">
          Hacer Otro Pedido
        </router-link>
      </div>

      <!-- Botón Cancelar (solo si aplica) -->
      <div v-if="canCancel" class="text-center">
        <button
          @click="handleCancelOrder"
          class="text-red-600 hover:text-red-700 text-sm"
        >
          Cancelar Pedido
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { useOrdersStore } from '@/stores/orders'

const route = useRoute()
const ordersStore = useOrdersStore()

const orderId = ref(route.params.orderId)

const order = computed(() => ordersStore.currentOrder)
const currentStatus = computed(() => order.value?.status || 'pending')

const canCancel = computed(() => {
  return currentStatus.value === 'pending' || currentStatus.value === 'preparing'
})

function isStatusCompleted(status) {
  const statusOrder = ['pending', 'preparing', 'in_transit', 'delivered']
  const currentIndex = statusOrder.indexOf(currentStatus.value)
  const targetIndex = statusOrder.indexOf(status)
  return currentIndex > targetIndex
}

function formatDate(dateString) {
  const date = new Date(dateString)
  return date.toLocaleString('es-MX', {
    day: '2-digit',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit'
  })
}

function formatAddress(address) {
  if (!address) return ''
  return `${address.street}, ${address.neighborhood}, ${address.city}, ${address.state} ${address.zipCode}`
}

async function handleCancelOrder() {
  if (!confirm('¿Estás seguro de que deseas cancelar este pedido?')) return

  const reason = prompt('Motivo de cancelación (opcional):')
  const success = await ordersStore.cancelOrder(orderId.value, reason)

  if (success) {
    alert('Pedido cancelado exitosamente')
  }
}

onMounted(async () => {
  // Cargar orden
  await ordersStore.loadOrder(orderId.value)

  // Iniciar tracking en tiempo real
  ordersStore.startOrderTracking(orderId.value)
})

onUnmounted(() => {
  // Detener tracking al salir
  ordersStore.stopOrderTracking()
})
</script>
