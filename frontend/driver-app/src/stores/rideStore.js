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
  const scheduledPollingInterval = ref(null)

  // SSE — módulo-level (no reactivo, no necesita ser ref)
  let _sseSource = null
  let _sseReconnectTimer = null
  let _sseConnected = false

  // Getters
  const hasPendingRequests = computed(() => pendingRequests.value.length > 0)
  const hasActiveRide = computed(() => !!activeRide.value)
  const activeRideStatus = computed(() => activeRide.value?.status || null)

  // Notification helpers
  let _knownRideIds = new Set()

  function _requestNotificationPermission() {
    if ('Notification' in window && Notification.permission === 'default') {
      Notification.requestPermission()
    }
  }

  function _playAlert() {
    try {
      const ctx = new (window.AudioContext || window.webkitAudioContext)()
      const osc = ctx.createOscillator()
      const gain = ctx.createGain()
      osc.connect(gain)
      gain.connect(ctx.destination)
      osc.type = 'sine'
      osc.frequency.setValueAtTime(880, ctx.currentTime)
      gain.gain.setValueAtTime(0.4, ctx.currentTime)
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.6)
      osc.start(ctx.currentTime)
      osc.stop(ctx.currentTime + 0.6)
    } catch (_) {}
  }

  function _notifyNewRide(ride) {
    _playAlert()
    if ('vibrate' in navigator) navigator.vibrate([200, 100, 200])
    if ('Notification' in window && Notification.permission === 'granted') {
      new Notification('🚕 Nueva solicitud de viaje', {
        body: `${ride.customer?.name || 'Pasajero'} → ${ride.destination?.address || 'Destino'}  $${ride.total_fare}`,
        icon: '/icons/icon-192x192.png',
        tag: ride.ride_id,
      })
    }
  }

  // Actions
  const fetchPendingRequests = async () => {
    try {
      const response = await ridesApi.getPendingRequests()
      const rides = response.rides || []
      const newRides = rides.filter(r => !_knownRideIds.has(r.ride_id))
      newRides.forEach(r => {
        _knownRideIds.add(r.ride_id)
        _notifyNewRide(r)
      })
      // Clean up ids that are no longer pending
      const currentIds = new Set(rides.map(r => r.ride_id))
      _knownRideIds = new Set([...currentIds].filter(id => currentIds.has(id)))
      pendingRequests.value = rides
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

  // Fetch inmediato al volver al frente (mobile background → foreground)
  const _onVisibilityChange = () => {
    if (!document.hidden) {
      fetchPendingRequests()
      fetchActiveRide()
      // Si SSE se cortó mientras estaba en background, reconectar
      if (!_sseSource && pollingInterval.value) startSSE()
    }
  }

  // ── SSE ──────────────────────────────────────────────────────────────────

  const _setPollingInterval = (ms) => {
    if (!pollingInterval.value) return
    clearInterval(pollingInterval.value)
    pollingInterval.value = setInterval(() => {
      fetchPendingRequests()
      fetchActiveRide()
    }, ms)
  }

  const _handleSSEEvent = (type, data) => {
    if (type === 'new_ride') {
      // Fetch completo para obtener el formato exacto que espera el frontend
      fetchPendingRequests()
    } else if (type === 'ride_taken') {
      pendingRequests.value = pendingRequests.value.filter(r => r.ride_id !== data.ride_id)
      _knownRideIds.delete(data.ride_id)
    } else if (type === 'assigned') {
      fetchActiveRide()
      fetchPendingRequests()
    }
  }

  const startSSE = () => {
    if (_sseSource) return
    const token = localStorage.getItem('driver_token')
    if (!token) return

    const url = `/api/v1/driver/stream?token=${encodeURIComponent(token)}`
    _sseSource = new EventSource(url)

    _sseSource.onopen = () => {
      _sseConnected = true
      // Con SSE activo el polling es solo fallback de sincronía
      _setPollingInterval(20000)
    }

    _sseSource.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data)
        _handleSSEEvent(msg.type, msg.data || {})
      } catch (_) {}
    }

    _sseSource.onerror = () => {
      _sseConnected = false
      _sseSource?.close()
      _sseSource = null
      // Sin SSE: polling rápido como fallback
      _setPollingInterval(3000)
      // Reintentar SSE en 5 segundos
      _sseReconnectTimer = setTimeout(() => {
        if (pollingInterval.value) startSSE()
      }, 5000)
    }
  }

  const stopSSE = () => {
    if (_sseReconnectTimer) { clearTimeout(_sseReconnectTimer); _sseReconnectTimer = null }
    if (_sseSource) { _sseSource.close(); _sseSource = null }
    _sseConnected = false
  }

  // ── Polling ──────────────────────────────────────────────────────────────

  const startPolling = () => {
    if (pollingInterval.value) return

    // Inicia con 3s; se reduce a 20s cuando SSE conecta
    pollingInterval.value = setInterval(() => {
      fetchPendingRequests()
      fetchActiveRide()
    }, 3000)

    // Viajes programados cada 30 segundos
    if (!scheduledPollingInterval.value) {
      scheduledPollingInterval.value = setInterval(() => {
        fetchScheduledRides()
      }, 30000)
    }

    document.addEventListener('visibilitychange', _onVisibilityChange)

    // Fetch inmediato + abrir SSE
    fetchPendingRequests()
    fetchActiveRide()
    fetchScheduledRides()
    startSSE()
  }

  const stopPolling = () => {
    stopSSE()
    if (pollingInterval.value) {
      clearInterval(pollingInterval.value)
      pollingInterval.value = null
    }
    if (scheduledPollingInterval.value) {
      clearInterval(scheduledPollingInterval.value)
      scheduledPollingInterval.value = null
    }
    document.removeEventListener('visibilitychange', _onVisibilityChange)
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
