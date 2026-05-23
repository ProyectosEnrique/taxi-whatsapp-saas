import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { useCartStore } from './cart'

export const useChatStore = defineStore('chat', () => {
  // State
  const isOpen = ref(false)
  const messages = ref([])
  const sessionId = ref(null)
  const tableNumber = ref(null)
  const isProcessing = ref(false)
  const isRecording = ref(false)
  const isPlaying = ref(false)
  const visualData = ref(null)
  const lastCartAction = ref(null)
  const lastCategory = ref(null)  // Track current category/topic
  const isOnline = ref(navigator.onLine)  // Estado de conexión

  // Computed
  const hasMessages = computed(() => messages.value.length > 0)
  const isVoiceEnabled = computed(() => isOnline.value)  // Voz solo cuando hay conexión

  // Actions
  function openChat() {
    console.log('[ChatStore] Opening chat')
    isOpen.value = true
  }

  function closeChat() {
    console.log('[ChatStore] Closing chat')
    isOpen.value = false
  }

  function toggleChat() {
    console.log('[ChatStore] Toggling chat, current:', isOpen.value)
    isOpen.value = !isOpen.value
  }

  function setSession(id, table) {
    sessionId.value = id
    tableNumber.value = table
    console.log('[ChatStore] Session set:', id, 'table:', table)
  }

  // Máximo de mensajes a mantener (3 intercambios = 6 mensajes)
  const MAX_MESSAGES = 6

  function addMessage(sender, text, type) {
    messages.value.push({ sender, text, type })
    // Limpiar mensajes antiguos para evitar saturar el modal
    if (messages.value.length > MAX_MESSAGES) {
      messages.value = messages.value.slice(-MAX_MESSAGES)
    }
  }

  function setVisualData(data) {
    // Detectar cambio de categoría/tópico y limpiar historial
    if (data && data.category) {
      const newCategory = data.category
      if (lastCategory.value && lastCategory.value !== newCategory) {
        // El usuario cambió de tópico - limpiar historial para contexto fresco
        console.log('[ChatStore] Topic changed from', lastCategory.value, 'to', newCategory, '- clearing old messages')
        // Mantener solo el último mensaje del usuario y la respuesta actual
        if (messages.value.length > 2) {
          messages.value = messages.value.slice(-2)
        }
      }
      lastCategory.value = newCategory
    }
    visualData.value = data
  }

  function clearVisualData() {
    visualData.value = null
  }

  function setProcessing(value) {
    isProcessing.value = value
  }

  function setRecording(value) {
    isRecording.value = value
  }

  function setPlaying(value) {
    isPlaying.value = value
  }

  function clearChat() {
    messages.value = []
    visualData.value = null
    lastCategory.value = null
  }

  // Funciones para manejar estado de conexión
  function setOnline(value) {
    const wasOffline = !isOnline.value
    isOnline.value = value
    console.log('[ChatStore] Connection status:', value ? 'ONLINE' : 'OFFLINE')

    // Si volvemos online después de estar offline, notificar al usuario
    if (value && wasOffline && isOpen.value) {
      addMessage('Sofia', '¡Conexión restaurada! Ya puedes usar la voz nuevamente.', 'assistant')
    }
  }

  function initConnectionListeners() {
    window.addEventListener('online', () => setOnline(true))
    window.addEventListener('offline', () => setOnline(false))
    // Verificar estado inicial
    setOnline(navigator.onLine)
  }

  function removeConnectionListeners() {
    window.removeEventListener('online', () => setOnline(true))
    window.removeEventListener('offline', () => setOnline(false))
  }

  /**
   * Procesa una cart_action del backend para sincronizar el carrito del frontend
   * @param {Object} cartAction - Objeto con action, items y total
   */
  function processCartAction(cartAction) {
    if (!cartAction || !cartAction.action) {
      console.log('[ChatStore] No cart action to process')
      return
    }

    const cartStore = useCartStore()
    lastCartAction.value = cartAction

    console.log('[ChatStore] Processing cart action:', cartAction.action, 'items:', cartAction.items?.length)

    if (cartAction.action === 'sync') {
      // Sincronizar todo el carrito
      // Primero limpiar el carrito actual
      cartStore.clear()

      // Agregar cada item del backend
      if (cartAction.items && Array.isArray(cartAction.items)) {
        cartAction.items.forEach(item => {
          const product = {
            id: item.product_id || item.id,
            name: item.name,
            price: item.price,
            image_url: item.image_url || null,
            description: item.description || '',
            category: item.category || ''
          }

          const options = {
            quantity: item.quantity || 1,
            modifiers: item.modifiers || [],
            specialNotes: item.specialNotes || item.notes || ''
          }

          cartStore.addItem(product, options)
          console.log('[ChatStore] Added to cart:', product.name, 'qty:', options.quantity)
        })
      }

      console.log('[ChatStore] Cart synced. Total items:', cartStore.itemCount, 'Total:', cartStore.total)
    } else if (cartAction.action === 'add') {
      // Agregar un solo item
      const item = cartAction.item
      if (item) {
        const product = {
          id: item.product_id || item.id,
          name: item.name,
          price: item.price
        }
        cartStore.addItem(product, {
          quantity: item.quantity || 1,
          modifiers: item.modifiers || [],
          specialNotes: item.specialNotes || ''
        })
      }
    } else if (cartAction.action === 'clear') {
      cartStore.clear()
    }
  }

  return {
    // State
    isOpen,
    messages,
    sessionId,
    tableNumber,
    isProcessing,
    isRecording,
    isPlaying,
    visualData,
    lastCartAction,
    lastCategory,
    isOnline,
    // Computed
    hasMessages,
    isVoiceEnabled,
    // Actions
    openChat,
    closeChat,
    toggleChat,
    setSession,
    addMessage,
    setVisualData,
    clearVisualData,
    setProcessing,
    setRecording,
    setPlaying,
    clearChat,
    processCartAction,
    setOnline,
    initConnectionListeners,
    removeConnectionListeners
  }
})
