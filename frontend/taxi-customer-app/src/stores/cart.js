import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

// Stub store — taxi app has no cart; kept for chat.js compatibility
export const useCartStore = defineStore('cart', () => {
  const items = ref([])
  const itemCount = computed(() => items.value.length)
  const total = computed(() => 0)
  function addItem() {}
  function clear() { items.value = [] }
  return { items, itemCount, total, addItem, clear }
})
