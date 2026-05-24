import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { ridesApi } from '../services/api'

export const useRideStore = defineStore('ride', () => {
  // State
  const pendingRequests = ref([])
  const activeRide = ref(null)
  const rideHistory = ref([])
  const myScheduledRides = ref([])
  const poolScheduledRides = ref([])
  const loading = ref(false)
  const error = ref(null)
  const pollingInterval = ref(null)

  // Getters
  const hasPendingRequests = computed(() => pendingRequests.value.length > 0)
  const hasActiveRide = computed(() => !!activeRide.value)
  const activeRideStatus = computed(() => activeRide.value?.status || null)

  // Actions
  const fetchPendingRequests = async () => {
    try {
      const response = await ridesApi.getPendingRequests()
      pendingRequests.value = response.rides || []
    } catch (err) {
      console.error('Error al obtener solicitudes:', err)
    }
  }

  const fetchActiveRide = async () => {
    try {
      const response = await ridesApi.getActiveRide()
      activeRide.value = response.ride || null
    } catch (err) {
      // No hay viaje activo, no es un error
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
      error.value = err.response?.data?.message || 'Error al obtener detalles del viaje'
      return { success: false, error: error.value }
    } finally {
      loading.value = false
    }
  }

  const acceptRide = async (rideId) => {
    loading.value = true
    error.value = null

    try {
      const response = await ridesApi.acceptRide(rideId)

      // Actualizar viaje activo
      activeRide.value = response.ride

      // Remover de solicitudes pendientes
      pendingRequests.value = pendingRequests.value.filter(r => r.ride_id !== rideId)

      return { success: true, ride: response.ride }
    } catch (err) {
      error.value = err.response?.data?.message || 'Error al aceptar viaje'
      return { success: false, error: error.value }
    } finally {
      loading.value = false
    }
  }

  const rejectRide = async (rideId, reason = 'No disponible') => {
    loading.value = true
    error.value = null

    try {
      await ridesApi.rejectRide(rideId, reason)

      // Remover de solicitudes pendientes
      pendingRequests.value = pendingRequests.value.filter(r => r.ride_id !== rideId)

      return { success: true }
    } catch (err) {
      error.value = err.response?.data?.message || 'Error al rechazar viaje'
      return { success: false, error: error.value }
    } finally {
      loading.value = false
    }
  }

  const startRide = async (rideId) => {
    loading.value = true
    error.value = null

    try {
      const response = await ridesApi.startRide(rideId)
      activeRide.value = response.ride

      return { success: true, ride: response.ride }
    } catch (err) {
      error.value = err.response?.data?.message || 'Error al iniciar viaje'
      return { success: false, error: error.value }
    } finally {
      loading.value = false
    }
  }

  const completeRide = async (rideId, completionData) => {
    loading.value = true
    error.value = null

    try {
      const response = await ridesApi.completeRide(rideId, completionData)

      // Limpiar viaje activo
      activeRide.value = null

      // Agregar al historial
      rideHistory.value.unshift(response.ride)

      return { success: true, ride: response.ride }
    } catch (err) {
      error.value = err.response?.data?.message || 'Error al completar viaje'
      return { success: false, error: error.value }
    } finally {
      loading.value = false
    }
  }

  const cancelRide = async (rideId, reason) => {
    loading.value = true
    error.value = null

    try {
      await ridesApi.cancelRide(rideId, reason)

      // Limpiar viaje activo
      activeRide.value = null

      return { success: true }
    } catch (err) {
      error.value = err.response?.data?.message || 'Error al cancelar viaje'
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

  const startPolling = () => {
    if (pollingInterval.value) return

    // Actualizar solicitudes y viaje activo cada 5 segundos
    pollingInterval.value = setInterval(() => {
      fetchPendingRequests()
      fetchActiveRide()
    }, 5000)

    // Obtener inmediatamente
    fetchPendingRequests()
    fetchActiveRide()
  }

  const stopPolling = () => {
    if (pollingInterval.value) {
      clearInterval(pollingInterval.value)
      pollingInterval.value = null
    }
  }

  const fetchScheduledRides = async () => {
    try {
      const response = await ridesApi.getScheduledRides()
      myScheduledRides.value   = response.mine  || []
      poolScheduledRides.value = response.pool  || []
    } catch (err) {
      console.error('Error al obtener viajes programados:', err)
    }
  }

  const claimScheduledRide = async (rideId) => {
    loading.value = true
    try {
      await ridesApi.claimScheduledRide(rideId)
      await fetchScheduledRides()
      return { success: true }
    } catch (err) {
      return { success: false, error: err.response?.data?.detail || 'Error al reservar' }
    } finally {
      loading.value = false
    }
  }

  const releaseScheduledRide = async (rideId) => {
    loading.value = true
    try {
      await ridesApi.releaseScheduledRide(rideId)
      myScheduledRides.value = myScheduledRides.value.filter(r => r.ride_id !== rideId)
      return { success: true }
    } catch (err) {
      return { success: false, error: err.response?.data?.detail || 'Error al liberar' }
    } finally {
      loading.value = false
    }
  }

  return {
    // State
    pendingRequests,
    activeRide,
    rideHistory,
    myScheduledRides,
    poolScheduledRides,
    loading,
    error,
    // Getters
    hasPendingRequests,
    hasActiveRide,
    activeRideStatus,
    // Actions
    fetchPendingRequests,
    fetchActiveRide,
    fetchRideDetails,
    acceptRide,
    rejectRide,
    startRide,
    completeRide,
    cancelRide,
    fetchHistory,
    startPolling,
    stopPolling,
    fetchScheduledRides,
    claimScheduledRide,
    releaseScheduledRide
  }
})
