import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { locationsApi } from '../services/api'

export const useLocationStore = defineStore('location', () => {
  const currentLocation = ref(null)
  const origin = ref(null)
  const destination = ref(null)
  const favoriteLocations = ref([])
  const searchResults = ref([])
  const loading = ref(false)
  const error = ref(null)

  const hasOrigin = computed(() => !!origin.value)
  const hasDestination = computed(() => !!destination.value)
  const canRequestRide = computed(() => hasOrigin.value && hasDestination.value)
  const homeLocation = computed(() =>
    favoriteLocations.value.find(loc => loc.type === 'home')
  )
  const workLocation = computed(() =>
    favoriteLocations.value.find(loc => loc.type === 'work')
  )

  const getCurrentLocation = () => {
    return new Promise((resolve, reject) => {
      if (!navigator.geolocation) {
        error.value = 'Geolocalización no soportada'
        reject(new Error('Geolocalización no soportada'))
        return
      }

      navigator.geolocation.getCurrentPosition(
        async (position) => {
          const { latitude, longitude } = position.coords
          currentLocation.value = { lat: latitude, lon: longitude }

          try {
            const response = await locationsApi.reverseGeocode(latitude, longitude)
            currentLocation.value.address = response.address
          } catch (err) {
            console.error('Error al obtener dirección:', err)
          }

          resolve(currentLocation.value)
        },
        (err) => {
          error.value = 'Error al obtener ubicación'
          reject(err)
        },
        {
          enableHighAccuracy: true,
          timeout: 10000,
          maximumAge: 0
        }
      )
    })
  }

  const searchAddress = async (query) => {
    if (!query || query.length < 3) {
      searchResults.value = []
      return { success: true, results: [] }
    }

    loading.value = true
    error.value = null

    try {
      // Pasa coordenadas actuales para sesgar los resultados al área del usuario
      const coords = currentLocation.value
        ? { lat: currentLocation.value.lat, lon: currentLocation.value.lon }
        : null
      const response = await locationsApi.searchAddress(query, coords)
      searchResults.value = response.results || []
      return { success: true, results: response.results }
    } catch (err) {
      error.value = err.response?.data?.message || 'Error al buscar dirección'
      return { success: false, error: error.value }
    } finally {
      loading.value = false
    }
  }

  const geocodeAddress = async (address) => {
    loading.value = true
    error.value = null

    try {
      const response = await locationsApi.geocode(address)
      return { success: true, location: response.location }
    } catch (err) {
      error.value = err.response?.data?.message || 'Error al geocodificar'
      return { success: false, error: error.value }
    } finally {
      loading.value = false
    }
  }

  const selectOrigin = (location) => {
    origin.value = location
  }

  const selectDestination = (location) => {
    destination.value = location
  }

  const setOriginToCurrent = async () => {
    try {
      const location = await getCurrentLocation()
      origin.value = location
    } catch (err) {
      error.value = 'No se pudo obtener ubicación actual'
    }
  }

  const swapOriginDestination = () => {
    const temp = origin.value
    origin.value = destination.value
    destination.value = temp
  }

  const clearOrigin = () => {
    origin.value = null
  }

  const clearDestination = () => {
    destination.value = null
  }

  const clearBoth = () => {
    origin.value = null
    destination.value = null
  }

  const saveFavoriteLocation = async (location, type = 'other', name = '') => {
    try {
      const favorite = {
        ...location,
        type,
        name,
        id: Date.now().toString()
      }

      favoriteLocations.value.push(favorite)
      localStorage.setItem('favorite_locations', JSON.stringify(favoriteLocations.value))

      return { success: true }
    } catch (err) {
      error.value = 'Error al guardar ubicación favorita'
      return { success: false, error: error.value }
    }
  }

  const deleteFavoriteLocation = (locationId) => {
    favoriteLocations.value = favoriteLocations.value.filter(
      loc => loc.id !== locationId
    )
    localStorage.setItem('favorite_locations', JSON.stringify(favoriteLocations.value))
  }

  const loadFavoriteLocations = () => {
    const saved = localStorage.getItem('favorite_locations')
    if (saved) {
      favoriteLocations.value = JSON.parse(saved)
    }
  }

  const getPopularDestinations = async () => {
    try {
      const response = await locationsApi.getPopularDestinations()
      return { success: true, destinations: response.destinations }
    } catch (err) {
      return { success: false, error: 'Error al obtener destinos populares' }
    }
  }

  return {
    currentLocation,
    origin,
    destination,
    favoriteLocations,
    searchResults,
    loading,
    error,
    hasOrigin,
    hasDestination,
    canRequestRide,
    homeLocation,
    workLocation,
    getCurrentLocation,
    searchAddress,
    geocodeAddress,
    selectOrigin,
    selectDestination,
    setOriginToCurrent,
    swapOriginDestination,
    clearOrigin,
    clearDestination,
    clearBoth,
    saveFavoriteLocation,
    deleteFavoriteLocation,
    loadFavoriteLocations,
    getPopularDestinations
  }
})
