import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/services/api'

export const useAuthStore = defineStore('auth', () => {
  // State
  const user = ref(null)
  const token = ref(localStorage.getItem('auth_token') || null)
  const loading = ref(false)
  const error = ref(null)

  // Getters
  const isAuthenticated = computed(() => !!token.value && !!user.value)
  const userName = computed(() => user.value?.name || '')
  const userEmail = computed(() => user.value?.email || '')

  // Actions
  async function login(credentials) {
    try {
      loading.value = true
      error.value = null

      const response = await api.login(credentials)

      token.value = response.token
      user.value = response.user

      // Guardar token en localStorage
      localStorage.setItem('auth_token', token.value)

      return true
    } catch (err) {
      error.value = err.message
      return false
    } finally {
      loading.value = false
    }
  }

  async function register(userData) {
    try {
      loading.value = true
      error.value = null

      const response = await api.register(userData)

      token.value = response.token
      user.value = response.user

      // Guardar token en localStorage
      localStorage.setItem('auth_token', token.value)

      return true
    } catch (err) {
      error.value = err.message
      return false
    } finally {
      loading.value = false
    }
  }

  function logout() {
    user.value = null
    token.value = null
    localStorage.removeItem('auth_token')
  }

  async function loadUser() {
    if (!token.value) return

    try {
      loading.value = true
      const userData = await api.getProfile()
      user.value = userData
    } catch (err) {
      console.error('Error cargando usuario:', err)
      // Si el token es inválido, hacer logout
      logout()
    } finally {
      loading.value = false
    }
  }

  async function updateProfile(updates) {
    try {
      loading.value = true
      error.value = null

      const updatedUser = await api.updateProfile(updates)
      user.value = updatedUser

      return true
    } catch (err) {
      error.value = err.message
      return false
    } finally {
      loading.value = false
    }
  }

  // Cargar usuario si hay token al inicializar
  if (token.value) {
    loadUser()
  }

  return {
    // State
    user,
    token,
    loading,
    error,

    // Getters
    isAuthenticated,
    userName,
    userEmail,

    // Actions
    login,
    register,
    logout,
    loadUser,
    updateProfile
  }
})
