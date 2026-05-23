import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { useTenantStore } from './tenant'

export const useCartStore = defineStore('cart', () => {
  // State
  const items = ref([])
  const isOpen = ref(false)

  // Getters
  const itemCount = computed(() => {
    return items.value.reduce((total, item) => total + item.quantity, 0)
  })

  const subtotal = computed(() => {
    return items.value.reduce((total, item) => {
      return total + (item.price * item.quantity)
    }, 0)
  })

  const deliveryFee = computed(() => {
    const tenantStore = useTenantStore()
    return tenantStore.businessRules?.delivery_fee || 0
  })

  const minOrderAmount = computed(() => {
    const tenantStore = useTenantStore()
    return tenantStore.businessRules?.min_order_amount || 0
  })

  const total = computed(() => {
    return subtotal.value + deliveryFee.value
  })

  const meetsMinimum = computed(() => {
    return subtotal.value >= minOrderAmount.value
  })

  // Actions
  function addItem(product, quantity = 1, customizations = {}) {
    const existingItemIndex = items.value.findIndex(item => {
      return item.product_id === product.product_id &&
             JSON.stringify(item.customizations) === JSON.stringify(customizations)
    })

    if (existingItemIndex !== -1) {
      items.value[existingItemIndex].quantity += quantity
    } else {
      items.value.push({
        product_id: product.product_id,
        name: product.name,
        price: product.price,
        quantity,
        customizations,
        image: product.image || null
      })
    }

    // Guardar en localStorage
    saveCart()
  }

  function removeItem(index) {
    items.value.splice(index, 1)
    saveCart()
  }

  function updateQuantity(index, quantity) {
    if (quantity <= 0) {
      removeItem(index)
    } else {
      items.value[index].quantity = quantity
      saveCart()
    }
  }

  function clearCart() {
    items.value = []
    saveCart()
  }

  function toggleCart() {
    isOpen.value = !isOpen.value
  }

  function openCart() {
    isOpen.value = true
  }

  function closeCart() {
    isOpen.value = false
  }

  function saveCart() {
    localStorage.setItem('cart', JSON.stringify(items.value))
  }

  function loadCart() {
    const savedCart = localStorage.getItem('cart')
    if (savedCart) {
      try {
        items.value = JSON.parse(savedCart)
      } catch (err) {
        console.error('Error cargando carrito:', err)
        items.value = []
      }
    }
  }

  // Cargar carrito al inicializar
  loadCart()

  return {
    // State
    items,
    isOpen,

    // Getters
    itemCount,
    subtotal,
    deliveryFee,
    minOrderAmount,
    total,
    meetsMinimum,

    // Actions
    addItem,
    removeItem,
    updateQuantity,
    clearCart,
    toggleCart,
    openCart,
    closeCart,
    saveCart,
    loadCart
  }
})
