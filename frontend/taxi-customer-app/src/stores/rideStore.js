import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { ridesApi } from '../services/api'

export const useRideStore = defineStore('ride', () => {
  const activeRide = ref(null)
  const rideHistory = ref([])
  const scheduledRides = ref([])
  const estimatedFare = ref(null)
  const loading = ref(false)
  const error = ref(null)
  const trackingInterval = ref(null)

  const hasActiveRide = computed(() => !!activeRide.value)
  const rideStatus = computed(() => activeRide.value?.status || null)

  const requestRide = async (rideData) => {
    loading.value = true
    error.value = null

    try {
      const response = await ridesApi.requestRide(rideData)
      activeRide.value = response.ride
      startTracking()
      return { success: true, ride: response.ride }
    } catch (err) {
      error.value = err.response?.data?.message || 'Error al solicitar viaje'
      return { success: false, error: error.value }
    } finally {
      loading.value = false
    }
  }

  const fetchActiveRide = async () => {
    try {
      const response = await ridesApi.getActiveRide()
      activeRide.value = response.ride || null
      if (activeRide.value && !trackingInterval.value) {
        startTracking()
      }
    } catch (err) {
      activeRide.value = null
    }
  }

  const fetchRideDetails = async (rideId) => {
    loading.value = true
    error.value = null

    try {
      const response = await ridesApi.getRideDetails(rideId)
      return { success: true, ride: response.ride }
    } catch (err) {
      error.value = err.response?.data?.message || 'Error al obtener detalles'
      return { success: false, error: error.value }
    } finally {
      loading.value = false
    }
  }

  const cancelRide = async (rideId, reason = 'Cliente canceló') => {
    loading.value = true
    error.value = null

    try {
      await ridesApi.cancelRide(rideId, reason)
      activeRide.value = null
      stopTracking()
      return { success: true }
    } catch (err) {
      error.value = err.response?.data?.message || 'Error al cancelar viaje'
      return { success: false, error: error.value }
    } finally {
      loading.value = false
    }
  }

  const rateRide = async (rideId, rating, comment = '') => {
    loading.value = true
    error.value = null

    try {
      await ridesApi.rateRide(rideId, rating, comment)
      return { success: true }
    } catch (err) {
      error.value = err.response?.data?.message || 'Error al calificar'
      return { success: false, error: error.value }
    } finally {
      loading.value = false
    }
  }

  const estimateFare = async (origin, destination) => {
    loading.value = true
    error.value = null

    try {
      const response = await ridesApi.estimateFare(origin, destination)
      estimatedFare.value = response.estimate
      return { success: true, estimate: response.estimate }
    } catch (err) {
      error.value = err.response?.data?.message || 'Error al estimar tarifa'
      return { success: false, error: error.value }
    } finally {
      loading.value = false
    }
  }

  const fetchHistory = async (filters = {}) => {
    loading.value = true
    error.value = null

    try {
      const response = await ridesApi.getHistory(filters)
      rideHistory.value = response.rides || []
      return { success: true }
    } catch (err) {
      error.value = err.response?.data?.message || 'Error al obtener historial'
      return { success: false, error: error.value }
    } finally {
      loading.value = false
    }
  }

  const startTracking = () => {
    if (trackingInterval.value) return

    trackingInterval.value = setInterval(async () => {
      if (activeRide.value) {
        const result = await fetchRideDetails(activeRide.value.ride_id)
        if (result.success) {
          activeRide.value = result.ride
          if (result.ride.status === 'completed' || result.ride.status === 'cancelled') {
            stopTracking()
          }
        }
      }
    }, 5000)
  }

  const stopTracking = () => {
    if (trackingInterval.value) {
      clearInterval(trackingInterval.value)
      trackingInterval.value = null
    }
  }

  const clearEstimate = () => {
    estimatedFare.value = null
  }

  const scheduleRide = async (rideData) => {
    loading.value = true
    error.value = null
    try {
      const response = await ridesApi.scheduleRide(rideData)
      scheduledRides.value.push(response.ride)
      scheduledRides.value.sort((a, b) => new Date(a.scheduled_at) - new Date(b.scheduled_at))
      return { success: true, ride: response.ride }
    } catch (err) {
      error.value = err.response?.data?.detail || 'Error al programar viaje'
      return { success: false, error: error.value }
    } finally {
      loading.value = false
    }
  }

  const fetchScheduledRides = async () => {
    try {
      const response = await ridesApi.getScheduledRides()
      scheduledRides.value = response.rides || []
    } catch (err) {
      scheduledRides.value = []
    }
  }

  const reassignRide = async (rideId) => {
    loading.value = true
    try {
      const response = await ridesApi.reassignRide(rideId)
      const idx = scheduledRides.value.findIndex(r => r.ride_id === rideId)
      if (idx !== -1) scheduledRides.value[idx] = response.ride
      return { success: true, ride: response.ride }
    } catch (err) {
      return { success: false, error: err.response?.data?.detail || 'Error al reasignar' }
    } finally {
      loading.value = false
    }
  }

  const cancelScheduledRide = async (rideId) => {
    loading.value = true
    try {
      await ridesApi.cancelScheduledRide(rideId)
      scheduledRides.value = scheduledRides.value.filter(r => r.ride_id !== rideId)
      return { success: true }
    } catch (err) {
      return { success: false, error: err.response?.data?.detail || 'Error al cancelar' }
    } finally {
      loading.value = false
    }
  }

  return {
    activeRide,
    rideHistory,
    scheduledRides,
    estimatedFare,
    loading,
    error,
    hasActiveRide,
    rideStatus,
    requestRide,
    fetchActiveRide,
    fetchRideDetails,
    cancelRide,
    rateRide,
    estimateFare,
    fetchHistory,
    startTracking,
    stopTracking,
    clearEstimate,
    scheduleRide,
    fetchScheduledRides,
    cancelScheduledRide,
    reassignRide
  }
})
