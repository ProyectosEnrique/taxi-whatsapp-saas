import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/services/api'
import { io } from 'socket.io-client'

export const useOrdersStore = defineStore('orders', () => {
  // State
  const orders = ref([])
  const currentOrder = ref(null)
  const loading = ref(false)
  const error = ref(null)
  const socket = ref(null)

  // Getters
  const activeOrders = computed(() => {
    return orders.value.filter(order => {
      return ['pending', 'preparing', 'in_transit'].includes(order.status)
    })
  })

  const completedOrders = computed(() => {
    return orders.value.filter(order => order.status === 'delivered')
  })

  const cancelledOrders = computed(() => {
    return orders.value.filter(order => order.status === 'cancelled')
  })

  // Actions
  async function createOrder(orderData) {
    try {
      loading.value = true
      error.value = null

      const newOrder = await api.createOrder(orderData)
      orders.value.unshift(newOrder)
      currentOrder.value = newOrder

      // Iniciar tracking en tiempo real
      startOrderTracking(newOrder.order_id)

      return newOrder
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function loadOrders() {
    try {
      loading.value = true
      error.value = null

      const ordersData = await api.getOrders()
      orders.value = ordersData
    } catch (err) {
      error.value = err.message
    } finally {
      loading.value = false
    }
  }

  async function loadOrder(orderId) {
    try {
      loading.value = true
      error.value = null

      const orderData = await api.getOrder(orderId)
      currentOrder.value = orderData

      // Actualizar en la lista si existe
      const index = orders.value.findIndex(o => o.order_id === orderId)
      if (index !== -1) {
        orders.value[index] = orderData
      }

      return orderData
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function cancelOrder(orderId, reason) {
    try {
      loading.value = true
      error.value = null

      await api.cancelOrder(orderId, reason)

      // Actualizar estado local
      const order = orders.value.find(o => o.order_id === orderId)
      if (order) {
        order.status = 'cancelled'
      }

      if (currentOrder.value?.order_id === orderId) {
        currentOrder.value.status = 'cancelled'
      }

      return true
    } catch (err) {
      error.value = err.message
      return false
    } finally {
      loading.value = false
    }
  }

  function startOrderTracking(orderId) {
    // Conectar a Socket.IO para tracking en tiempo real
    const socketUrl = import.meta.env.VITE_SOCKET_URL || 'http://localhost:5000'

    socket.value = io(socketUrl, {
      query: { order_id: orderId }
    })

    socket.value.on('order_update', (data) => {
      console.log('Order update received:', data)

      // Actualizar orden actual
      if (currentOrder.value?.order_id === data.order_id) {
        currentOrder.value = { ...currentOrder.value, ...data }
      }

      // Actualizar en la lista
      const index = orders.value.findIndex(o => o.order_id === data.order_id)
      if (index !== -1) {
        orders.value[index] = { ...orders.value[index], ...data }
      }
    })

    socket.value.on('connect_error', (err) => {
      console.error('Socket connection error:', err)
    })
  }

  function stopOrderTracking() {
    if (socket.value) {
      socket.value.disconnect()
      socket.value = null
    }
  }

  return {
    // State
    orders,
    currentOrder,
    loading,
    error,

    // Getters
    activeOrders,
    completedOrders,
    cancelledOrders,

    // Actions
    createOrder,
    loadOrders,
    loadOrder,
    cancelOrder,
    startOrderTracking,
    stopOrderTracking
  }
})
