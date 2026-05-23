import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { driverApi } from '../services/api'
import { useAuthStore } from './authStore'

export const useDriverStore = defineStore('driver', () => {
  // State
  const status = ref('offline') // 'available', 'busy', 'offline'
  const location = ref({ lat: null, lon: null })
  const stats = ref({
    total_rides: 0,
    completed_today: 0,
    rating: 5.0,
    acceptance_rate: 1.0,
    earnings_today: 0,
    earnings_week: 0
  })
  const loading = ref(false)
  const error = ref(null)
  const pollingInterval = ref(null)

  // Getters
  const isAvailable = computed(() => status.value === 'available')
  const isBusy = computed(() => status.value === 'busy')
  const isOffline = computed(() => status.value === 'offline')
  const statusLabel = computed(() => {
    const labels = {
      available: 'Disponible',
      busy: 'Ocupado',
      offline: 'Desconectado'
    }
    return labels[status.value] || 'Desconocido'
  })
  const statusColor = computed(() => {
    const colors = {
      available: 'bg-green-500',
      busy: 'bg-yellow-500',
      offline: 'bg-gray-500'
    }
    return colors[status.value] || 'bg-gray-500'
  })

  // Actions
  const updateStatus = async (newStatus) => {
    loading.value = true
    error.value = null

    try {
      const response = await driverApi.updateStatus(newStatus)
      status.value = response.status

      // Actualizar en authStore también
      const authStore = useAuthStore()
      authStore.updateDriverData({ status: response.status })

      return { success: true }
    } catch (err) {
      error.value = err.response?.data?.message || 'Error al actualizar estado'
      return { success: false, error: error.value }
    } finally {
      loading.value = false
    }
  }

  const updateLocation = async (lat, lon) => {
    try {
      await driverApi.updateLocation(lat, lon)
      location.value = { lat, lon }
    } catch (err) {
      console.error('Error al actualizar ubicación:', err)
    }
  }

  const fetchStats = async () => {
    try {
      const response = await driverApi.getStats()
      stats.value = response.stats
    } catch (err) {
      console.error('Error al obtener estadísticas:', err)
    }
  }

  const startPolling = () => {
    if (pollingInterval.value) return

    // Actualizar estadísticas cada 30 segundos
    pollingInterval.value = setInterval(() => {
      fetchStats()
    }, 30000)

    // Obtener inmediatamente
    fetchStats()
  }

  const stopPolling = () => {
    if (pollingInterval.value) {
      clearInterval(pollingInterval.value)
      pollingInterval.value = null
    }
  }

  const startLocationTracking = () => {
    if (!navigator.geolocation) {
      console.error('Geolocalización no soportada')
      return
    }

    // Actualizar ubicación cada 10 segundos
    const watchId = navigator.geolocation.watchPosition(
      (position) => {
        const { latitude, longitude } = position.coords
        updateLocation(latitude, longitude)
      },
      (error) => {
        console.error('Error de geolocalización:', error)
      },
      {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 0
      }
    )

    return watchId
  }

  const toggleStatus = async () => {
    const newStatus = isAvailable.value ? 'offline' : 'available'
    return await updateStatus(newStatus)
  }

  return {
    // State
    status,
    location,
    stats,
    loading,
    error,
    // Getters
    isAvailable,
    isBusy,
    isOffline,
    statusLabel,
    statusColor,
    // Actions
    updateStatus,
    updateLocation,
    fetchStats,
    startPolling,
    stopPolling,
    startLocationTracking,
    toggleStatus
  }
})
