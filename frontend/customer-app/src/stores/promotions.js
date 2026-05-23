import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/services/api'

export const usePromotionsStore = defineStore('promotions', () => {
  // State
  const promotions = ref([])
  const appliedPromoCode = ref(null)
  const loading = ref(false)
  const error = ref(null)

  // Getters
  const activePromotions = computed(() => {
    const now = new Date()
    return promotions.value.filter(promo => {
      const validFrom = new Date(promo.valid_from)
      const validUntil = new Date(promo.valid_until)
      return promo.active && now >= validFrom && now <= validUntil
    })
  })

  const discount = computed(() => {
    if (!appliedPromoCode.value) return 0

    const promo = appliedPromoCode.value
    if (promo.discount_type === 'percentage') {
      return promo.discount_value // Porcentaje
    } else if (promo.discount_type === 'fixed') {
      return promo.discount_value // Monto fijo
    }
    return 0
  })

  // Actions
  async function loadPromotions() {
    try {
      loading.value = true
      error.value = null

      const promoData = await api.getPromotions()
      promotions.value = promoData
    } catch (err) {
      error.value = err.message
    } finally {
      loading.value = false
    }
  }

  async function applyPromoCode(code) {
    try {
      loading.value = true
      error.value = null

      const promo = await api.validatePromoCode(code)

      if (promo.valid) {
        appliedPromoCode.value = promo
        return { success: true, promo }
      } else {
        error.value = 'Código promocional inválido o expirado'
        return { success: false, error: error.value }
      }
    } catch (err) {
      error.value = err.message
      return { success: false, error: err.message }
    } finally {
      loading.value = false
    }
  }

  function removePromoCode() {
    appliedPromoCode.value = null
  }

  function calculateDiscount(subtotal) {
    if (!appliedPromoCode.value) return 0

    const promo = appliedPromoCode.value

    if (promo.discount_type === 'percentage') {
      return (subtotal * promo.discount_value) / 100
    } else if (promo.discount_type === 'fixed') {
      return Math.min(promo.discount_value, subtotal)
    }

    return 0
  }

  return {
    // State
    promotions,
    appliedPromoCode,
    loading,
    error,

    // Getters
    activePromotions,
    discount,

    // Actions
    loadPromotions,
    applyPromoCode,
    removePromoCode,
    calculateDiscount
  }
})
