import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/services/api'

export const useLoyaltyStore = defineStore('loyalty', () => {
  // State
  const points = ref(0)
  const level = ref('Bronze')
  const history = ref([])
  const rewards = ref([])
  const loading = ref(false)
  const error = ref(null)

  // Getters
  const availableRewards = computed(() => {
    return rewards.value.filter(reward => {
      return reward.points_required <= points.value && reward.active
    })
  })

  const nextLevelPoints = computed(() => {
    const levels = {
      'Bronze': 0,
      'Silver': 500,
      'Gold': 1500,
      'Platinum': 3000
    }

    const currentLevelPoints = levels[level.value] || 0
    const nextLevel = Object.keys(levels).find(l => levels[l] > currentLevelPoints)

    return nextLevel ? levels[nextLevel] : null
  })

  const progressToNextLevel = computed(() => {
    if (!nextLevelPoints.value) return 100 // Ya está en el nivel máximo

    const levels = {
      'Bronze': 0,
      'Silver': 500,
      'Gold': 1500,
      'Platinum': 3000
    }

    const currentLevelPoints = levels[level.value] || 0
    const pointsNeeded = nextLevelPoints.value - currentLevelPoints
    const currentProgress = points.value - currentLevelPoints

    return Math.min((currentProgress / pointsNeeded) * 100, 100)
  })

  // Actions
  async function loadLoyaltyData() {
    try {
      loading.value = true
      error.value = null

      const data = await api.getLoyaltyData()

      points.value = data.points || 0
      level.value = data.level || 'Bronze'
      history.value = data.history || []
    } catch (err) {
      error.value = err.message
    } finally {
      loading.value = false
    }
  }

  async function loadRewards() {
    try {
      const rewardsData = await api.getRewards()
      rewards.value = rewardsData
    } catch (err) {
      console.error('Error cargando recompensas:', err)
    }
  }

  async function redeemReward(rewardId) {
    try {
      loading.value = true
      error.value = null

      const result = await api.redeemReward(rewardId)

      if (result.success) {
        // Actualizar puntos localmente
        const reward = rewards.value.find(r => r.id === rewardId)
        if (reward) {
          points.value -= reward.points_required

          // Agregar al historial
          history.value.unshift({
            type: 'redemption',
            points: -reward.points_required,
            description: `Canjeado: ${reward.name}`,
            date: new Date().toISOString()
          })
        }

        return { success: true }
      }

      return { success: false, error: result.error }
    } catch (err) {
      error.value = err.message
      return { success: false, error: err.message }
    } finally {
      loading.value = false
    }
  }

  function calculatePointsFromOrder(orderTotal) {
    // 1 punto por cada $10 gastados
    return Math.floor(orderTotal / 10)
  }

  return {
    // State
    points,
    level,
    history,
    rewards,
    loading,
    error,

    // Getters
    availableRewards,
    nextLevelPoints,
    progressToNextLevel,

    // Actions
    loadLoyaltyData,
    loadRewards,
    redeemReward,
    calculatePointsFromOrder
  }
})
