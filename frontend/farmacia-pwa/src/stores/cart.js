/**
 * Cart Store - Gestión del Carrito de Compras
 * Sincronizado con Sofia y persistido en sessionStorage
 */
import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'

const CART_STORAGE_KEY = 'farmacia_cart'

export const useCartStore = defineStore('cart', () => {
  // ============================================================
  // STATE
  // ============================================================

  const items = ref([])
  const isOpen = ref(false)
  const deliveryFee = ref(20) // Default, se actualiza desde tenant
  const minOrderAmount = ref(50) // Default, se actualiza desde tenant

  // ============================================================
  // GETTERS
  // ============================================================

  // Cantidad total de items
  const itemCount = computed(() => {
    return items.value.reduce((total, item) => total + item.quantity, 0)
  })

  // Subtotal (sin envío)
  const subtotal = computed(() => {
    return items.value.reduce((total, item) => total + (item.price * item.quantity), 0)
  })

  // Total con envío
  const total = computed(() => {
    return subtotal.value + (subtotal.value >= minOrderAmount.value ? deliveryFee.value : 0)
  })

  // Si el carrito está vacío
  const isEmpty = computed(() => items.value.length === 0)

  // Si cumple el mínimo de pedido
  const meetsMinimum = computed(() => subtotal.value >= minOrderAmount.value)

  // Resumen formateado
  const summary = computed(() => {
    if (isEmpty.value) return 'Carrito vacío'
    return `${itemCount.value} producto${itemCount.value > 1 ? 's' : ''} - $${subtotal.value.toFixed(2)}`
  })

  // ============================================================
  // ACTIONS
  // ============================================================

  /**
   * Agrega un producto al carrito
   */
  function addItem(product, quantity = 1) {
    const existingIndex = items.value.findIndex(item => item.id === product.id)

    if (existingIndex > -1) {
      // Incrementar cantidad si ya existe
      items.value[existingIndex].quantity += quantity
    } else {
      // Agregar nuevo item
      items.value.push({
        id: product.id,
        name: product.name,
        price: product.price,
        quantity: quantity,
        image: product.image || null,
        requiresPrescription: product.requires_prescription || false
      })
    }

    saveToStorage()
    console.log('[CartStore] Item agregado:', product.name, 'x', quantity)
  }

  /**
   * Remueve un producto del carrito
   */
  function removeItem(productId) {
    const index = items.value.findIndex(item => item.id === productId)
    if (index > -1) {
      items.value.splice(index, 1)
      saveToStorage()
    }
  }

  /**
   * Actualiza la cantidad de un producto
   */
  function updateQuantity(productId, quantity) {
    const item = items.value.find(item => item.id === productId)
    if (item) {
      if (quantity <= 0) {
        removeItem(productId)
      } else {
        item.quantity = quantity
        saveToStorage()
      }
    }
  }

  /**
   * Incrementa la cantidad de un producto
   */
  function incrementItem(productId) {
    const item = items.value.find(item => item.id === productId)
    if (item) {
      item.quantity += 1
      saveToStorage()
    }
  }

  /**
   * Decrementa la cantidad de un producto
   */
  function decrementItem(productId) {
    const item = items.value.find(item => item.id === productId)
    if (item) {
      if (item.quantity <= 1) {
        removeItem(productId)
      } else {
        item.quantity -= 1
        saveToStorage()
      }
    }
  }

  /**
   * Limpia todo el carrito
   */
  function clearCart() {
    items.value = []
    saveToStorage()
  }

  /**
   * Abre/cierra el sidebar del carrito
   */
  function toggleCart() {
    isOpen.value = !isOpen.value
  }

  function openCart() {
    isOpen.value = true
  }

  function closeCart() {
    isOpen.value = false
  }

  /**
   * Actualiza las reglas de negocio desde el tenant
   */
  function updateBusinessRules(rules) {
    if (rules.delivery_fee !== undefined) {
      deliveryFee.value = rules.delivery_fee
    }
    if (rules.min_order_amount !== undefined) {
      minOrderAmount.value = rules.min_order_amount
    }
  }

  /**
   * Procesa una acción de carrito desde Sofia
   * (Sincronización bidireccional)
   */
  function processCartAction(action) {
    if (!action) return

    console.log('[CartStore] Procesando cart_action:', action)

    if (action.action === 'add' && action.items) {
      // Agregar items desde Sofia
      action.items.forEach(item => {
        addItem({
          id: item.product_id || item.id,
          name: item.name,
          price: item.price
        }, item.quantity || 1)
      })
    } else if (action.action === 'clear') {
      clearCart()
    } else if (action.action === 'remove' && action.product_id) {
      removeItem(action.product_id)
    }
  }

  // ============================================================
  // PERSISTENCE
  // ============================================================

  /**
   * Guarda el carrito en sessionStorage
   */
  function saveToStorage() {
    try {
      sessionStorage.setItem(CART_STORAGE_KEY, JSON.stringify(items.value))
    } catch (e) {
      console.warn('[CartStore] Error guardando en storage:', e)
    }
  }

  /**
   * Carga el carrito desde sessionStorage
   */
  function loadFromStorage() {
    try {
      const saved = sessionStorage.getItem(CART_STORAGE_KEY)
      if (saved) {
        items.value = JSON.parse(saved)
      }
    } catch (e) {
      console.warn('[CartStore] Error cargando desde storage:', e)
    }
  }

  // Cargar al iniciar
  loadFromStorage()

  // ============================================================
  // RETURN
  // ============================================================

  return {
    // State
    items,
    isOpen,
    deliveryFee,
    minOrderAmount,

    // Getters
    itemCount,
    subtotal,
    total,
    isEmpty,
    meetsMinimum,
    summary,

    // Actions
    addItem,
    removeItem,
    updateQuantity,
    incrementItem,
    decrementItem,
    clearCart,
    toggleCart,
    openCart,
    closeCart,
    updateBusinessRules,
    processCartAction,
    loadFromStorage
  }
})
