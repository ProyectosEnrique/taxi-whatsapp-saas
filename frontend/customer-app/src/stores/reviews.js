import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/services/api'

export const useReviewsStore = defineStore('reviews', () => {
  // State
  const reviews = ref([])
  const loading = ref(false)
  const error = ref(null)

  // Actions
  async function loadReviews(productId = null) {
    try {
      loading.value = true
      error.value = null

      const reviewsData = await api.getReviews(productId)
      reviews.value = reviewsData
    } catch (err) {
      error.value = err.message
    } finally {
      loading.value = false
    }
  }

  async function submitReview(reviewData) {
    try {
      loading.value = true
      error.value = null

      const newReview = await api.submitReview(reviewData)
      reviews.value.unshift(newReview)

      return { success: true, review: newReview }
    } catch (err) {
      error.value = err.message
      return { success: false, error: err.message }
    } finally {
      loading.value = false
    }
  }

  async function uploadReviewImage(file) {
    try {
      const imageUrl = await api.uploadImage(file)
      return imageUrl
    } catch (err) {
      console.error('Error subiendo imagen:', err)
      throw err
    }
  }

  function getReviewStats(productId = null) {
    const relevantReviews = productId
      ? reviews.value.filter(r => r.product_id === productId)
      : reviews.value

    if (relevantReviews.length === 0) {
      return {
        averageRating: 0,
        totalReviews: 0,
        distribution: { 5: 0, 4: 0, 3: 0, 2: 0, 1: 0 }
      }
    }

    const totalRating = relevantReviews.reduce((sum, r) => sum + r.rating, 0)
    const averageRating = totalRating / relevantReviews.length

    const distribution = { 5: 0, 4: 0, 3: 0, 2: 0, 1: 0 }
    relevantReviews.forEach(r => {
      distribution[r.rating] = (distribution[r.rating] || 0) + 1
    })

    return {
      averageRating: averageRating.toFixed(1),
      totalReviews: relevantReviews.length,
      distribution
    }
  }

  return {
    // State
    reviews,
    loading,
    error,

    // Actions
    loadReviews,
    submitReview,
    uploadReviewImage,
    getReviewStats
  }
})
