import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '../services/api'

export const useAuthStore = defineStore('auth', () => {
  // State
  const token = ref(localStorage.getItem('driver_token') || null)
  const driver = ref(JSON.parse(localStorage.getItem('driver_data') || 'null'))
  const loading = ref(false)
  const error = ref(null)

  // Getters
  const isAuthenticated = computed(() => !!token.value)
  const driverInfo = computed(() => driver.value)

  // Actions
  const login = async (phone, password) => {
    loading.value = true
    error.value = null

    try {
      const response = await authApi.login(phone, password)

      token.value = response.token
      driver.value = response.driver

      // Guardar en localStorage
      localStorage.setItem('driver_token', response.token)
      localStorage.setItem('driver_data', JSON.stringify(response.driver))

      return { success: true }
    } catch (err) {
      error.value = err.response?.data?.message || 'Error al iniciar sesión'
      return { success: false, error: error.value }
    } finally {
      loading.value = false
    }
  }

  const logout = async () => {
    try {
      await authApi.logout()
    } catch (err) {
      console.error('Error al cerrar sesión:', err)
    } finally {
      // Limpiar estado local
      token.value = null
      driver.value = null
      localStorage.removeItem('driver_token')
      localStorage.removeItem('driver_data')
    }
  }

  const checkAuth = async () => {
    if (!token.value) return false

    try {
      const response = await authApi.verifyToken()
      driver.value = response.driver
      localStorage.setItem('driver_data', JSON.stringify(response.driver))
      return true
    } catch (err) {
      // Token inválido, limpiar
      await logout()
      return false
    }
  }

  const updateDriverData = (newData) => {
    driver.value = { ...driver.value, ...newData }
    localStorage.setItem('driver_data', JSON.stringify(driver.value))
  }

  return {
    // State
    token,
    driver,
    loading,
    error,
    // Getters
    isAuthenticated,
    driverInfo,
    // Actions
    login,
    logout,
    checkAuth,
    updateDriverData
  }
})
