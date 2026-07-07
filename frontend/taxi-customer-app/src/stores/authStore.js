import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '../services/api'

function readStoredCustomer() {
  const raw = localStorage.getItem('customer_data')
  if (!raw) return null
  try {
    return JSON.parse(raw)
  } catch (err) {
    // customer_data corrupto (ej. se guardó el string "undefined") — limpiar
    // y arrancar sin sesión en vez de tumbar el arranque de toda la app.
    localStorage.removeItem('customer_data')
    localStorage.removeItem('customer_token')
    return null
  }
}

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('customer_token') || null)
  const customer = ref(readStoredCustomer())
  const loading = ref(false)
  const error = ref(null)

  const isAuthenticated = computed(() => !!token.value)
  const customerInfo = computed(() => customer.value)

  const login = async (phone, password) => {
    loading.value = true
    error.value = null

    try {
      const response = await authApi.login(phone, password)
      token.value = response.token
      customer.value = response.customer
      localStorage.setItem('customer_token', response.token)
      localStorage.setItem('customer_data', JSON.stringify(response.customer))
      return { success: true }
    } catch (err) {
      error.value = err.response?.data?.message || 'Error al iniciar sesión'
      return { success: false, error: error.value }
    } finally {
      loading.value = false
    }
  }

  const register = async (userData) => {
    loading.value = true
    error.value = null

    try {
      const response = await authApi.register(userData)
      token.value = response.token
      customer.value = response.customer
      localStorage.setItem('customer_token', response.token)
      localStorage.setItem('customer_data', JSON.stringify(response.customer))
      return { success: true }
    } catch (err) {
      error.value = err.response?.data?.message || 'Error al registrarse'
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
      token.value = null
      customer.value = null
      localStorage.removeItem('customer_token')
      localStorage.removeItem('customer_data')
    }
  }

  const checkAuth = async () => {
    if (!token.value) return false
    try {
      const response = await authApi.verifyToken()
      customer.value = response.customer
      localStorage.setItem('customer_data', JSON.stringify(response.customer))
      return true
    } catch (err) {
      await logout()
      return false
    }
  }

  const updateCustomerData = (newData) => {
    customer.value = { ...customer.value, ...newData }
    localStorage.setItem('customer_data', JSON.stringify(customer.value))
  }

  return {
    token,
    customer,
    loading,
    error,
    isAuthenticated,
    customerInfo,
    login,
    register,
    logout,
    checkAuth,
    updateCustomerData
  }
})
