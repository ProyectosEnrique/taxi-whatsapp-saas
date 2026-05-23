<template>
  <div class="container mx-auto px-4 py-8 max-w-6xl">
    <h1 class="text-3xl font-bold mb-8">Mis Pedidos</h1>

    <!-- Tabs de Filtros -->
    <div class="mb-6">
      <div class="flex space-x-2 border-b">
        <button
          v-for="tab in tabs"
          :key="tab.key"
          @click="activeTab = tab.key"
          :class="[
            'px-4 py-2 font-medium transition border-b-2',
            activeTab === tab.key
              ? 'border-primary-600 text-primary-600'
              : 'border-transparent text-gray-600 hover:text-gray-900'
          ]"
        >
          {{ tab.label }}
          <span v-if="tab.count" class="ml-2 px-2 py-0.5 bg-gray-200 rounded-full text-xs">
            {{ tab.count }}
          </span>
        </button>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="ordersStore.loading" class="text-center py-12">
      <div class="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mb-4"></div>
      <p class="text-gray-600">Cargando pedidos...</p>
    </div>

    <!-- Empty State -->
    <div v-else-if="displayedOrders.length === 0" class="text-center py-12">
      <svg class="w-16 h-16 text-gray-300 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
      </svg>
      <p class="text-gray-500 mb-4">No tienes pedidos {{ activeTab === 'all' ? '' : activeTab === 'active' ? 'activos' : activeTab === 'completed' ? 'completados' : 'cancelados' }}</p>
      <router-link to="/" class="btn-primary">
        Hacer un Pedido
      </router-link>
    </div>

    <!-- Orders List -->
    <div v-else class="space-y-4">
      <div
        v-for="order in displayedOrders"
        :key="order.order_id"
        class="card hover:shadow-lg transition-shadow cursor-pointer"
        @click="goToTracking(order.order_id)"
      >
        <div class="flex items-start justify-between mb-4">
          <div>
            <h3 class="font-bold text-lg">Pedido #{{ order.order_id }}</h3>
            <p class="text-sm text-gray-600">{{ formatDate(order.created_at) }}</p>
          </div>
          <span :class="[
            'badge',
            order.status === 'delivered' ? 'badge-success' : '',
            order.status === 'cancelled' ? 'badge-error' : '',
            order.status === 'pending' || order.status === 'preparing' || order.status === 'in_transit' ? 'badge-warning' : ''
          ]">
            {{ getStatusLabel(order.status) }}
          </span>
        </div>

        <!-- Items Preview -->
        <div class="mb-4">
          <p class="text-sm text-gray-600 mb-2">
            {{ order.items.length }} producto{{ order.items.length > 1 ? 's' : '' }}
          </p>
          <div class="flex flex-wrap gap-2">
            <span
              v-for="(item, index) in order.items.slice(0, 3)"
              :key="index"
              class="text-xs bg-gray-100 px-2 py-1 rounded"
            >
              {{ item.quantity }}x {{ item.name }}
            </span>
            <span v-if="order.items.length > 3" class="text-xs text-gray-500 px-2 py-1">
              +{{ order.items.length - 3 }} más
            </span>
          </div>
        </div>

        <!-- Total y Acciones -->
        <div class="flex items-center justify-between border-t pt-4">
          <div>
            <p class="text-2xl font-bold text-primary-600">
              ${{ order.total?.toFixed(2) }}
            </p>
          </div>
          <div class="flex space-x-2">
            <button
              @click.stop="goToTracking(order.order_id)"
              class="btn-secondary text-sm"
            >
              Ver Detalles
            </button>
            <button
              v-if="order.status === 'delivered' && !order.reviewed"
              @click.stop="goToReview(order.order_id)"
              class="btn-primary text-sm"
            >
              Calificar
            </button>
            <button
              v-if="order.status === 'delivered'"
              @click.stop="handleReorder(order)"
              class="btn-primary text-sm"
            >
              Volver a Pedir
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useOrdersStore } from '@/stores/orders'
import { useCartStore } from '@/stores/cart'

const router = useRouter()
const ordersStore = useOrdersStore()
const cartStore = useCartStore()

const activeTab = ref('all')

const tabs = computed(() => [
  { key: 'all', label: 'Todos', count: ordersStore.orders.length },
  { key: 'active', label: 'Activos', count: ordersStore.activeOrders.length },
  { key: 'completed', label: 'Completados', count: ordersStore.completedOrders.length },
  { key: 'cancelled', label: 'Cancelados', count: ordersStore.cancelledOrders.length }
])

const displayedOrders = computed(() => {
  switch (activeTab.value) {
    case 'active':
      return ordersStore.activeOrders
    case 'completed':
      return ordersStore.completedOrders
    case 'cancelled':
      return ordersStore.cancelledOrders
    default:
      return ordersStore.orders
  }
})

function getStatusLabel(status) {
  const labels = {
    pending: 'Pendiente',
    preparing: 'Preparando',
    in_transit: 'En Camino',
    delivered: 'Entregado',
    cancelled: 'Cancelado'
  }
  return labels[status] || status
}

function formatDate(dateString) {
  const date = new Date(dateString)
  return date.toLocaleString('es-MX', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

function goToTracking(orderId) {
  router.push({
    name: 'order-tracking',
    params: { orderId }
  })
}

function goToReview(orderId) {
  router.push({
    name: 'review-order',
    params: { orderId }
  })
}

function handleReorder(order) {
  // Limpiar carrito actual
  cartStore.clearCart()

  // Agregar todos los items del pedido anterior
  order.items.forEach(item => {
    cartStore.addItem(item, item.quantity)
  })

  // Abrir carrito y redirigir
  cartStore.openCart()
  router.push('/')
}

onMounted(() => {
  ordersStore.loadOrders()
})
</script>
