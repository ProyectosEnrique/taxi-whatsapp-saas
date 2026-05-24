import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

// Crear instancia de axios
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Interceptor para agregar token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('driver_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Interceptor para manejar errores
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('driver_token')
      localStorage.removeItem('driver_data')
      window.location.href = import.meta.env.BASE_URL + 'login'
    }
    return Promise.reject(error)
  }
)

// ============================================
// AUTH API
// ============================================

export const authApi = {
  login: async (phone, password) => {
    const response = await api.post('/driver/login', { phone, password })
    return response.data
  },

  logout: async () => {
    const response = await api.post('/driver/logout')
    return response.data
  },

  verifyToken: async () => {
    const response = await api.get('/driver/verify')
    return response.data
  }
}

// ============================================
// DRIVER API
// ============================================

export const driverApi = {
  getProfile: async () => {
    const response = await api.get('/driver/profile')
    return response.data
  },

  updateStatus: async (status) => {
    const response = await api.put('/driver/status', { status })
    return response.data
  },

  updateLocation: async (lat, lon) => {
    const response = await api.put('/driver/location', { lat, lon })
    return response.data
  },

  getStats: async () => {
    const response = await api.get('/driver/stats')
    return response.data
  },

  updateProfile: async (profileData) => {
    const response = await api.put('/driver/profile', profileData)
    return response.data
  }
}

// ============================================
// RIDES API
// ============================================

export const ridesApi = {
  getPendingRequests: async () => {
    const response = await api.get('/driver/rides/pending')
    return response.data
  },

  getRideDetails: async (rideId) => {
    const response = await api.get(`/driver/rides/${rideId}`)
    return response.data
  },

  acceptRide: async (rideId) => {
    const response = await api.post(`/driver/rides/${rideId}/accept`)
    return response.data
  },

  rejectRide: async (rideId, reason) => {
    const response = await api.post(`/driver/rides/${rideId}/reject`, { reason })
    return response.data
  },

  startRide: async (rideId) => {
    const response = await api.post(`/driver/rides/${rideId}/start`)
    return response.data
  },

  completeRide: async (rideId, completionData) => {
    const response = await api.post(`/driver/rides/${rideId}/complete`, completionData)
    return response.data
  },

  cancelRide: async (rideId, reason) => {
    const response = await api.post(`/driver/rides/${rideId}/cancel`, { reason })
    return response.data
  },

  getHistory: async (filters = {}) => {
    const response = await api.get('/driver/rides/history', { params: filters })
    return response.data
  },

  getActiveRide: async () => {
    const response = await api.get('/driver/rides/active')
    return response.data
  },

  getScheduledRides: async () => {
    const response = await api.get('/driver/rides/scheduled')
    return response.data
  },

  claimScheduledRide: async (rideId) => {
    const response = await api.post(`/driver/rides/${rideId}/claim`)
    return response.data
  },

  releaseScheduledRide: async (rideId) => {
    const response = await api.post(`/driver/rides/${rideId}/release`)
    return response.data
  },

  reportIncident: async (incidentData) => {
    const response = await api.post('/driver/incidents', incidentData)
    return response.data
  }
}

// ============================================
// EARNINGS API
// ============================================

export const earningsApi = {
  getEarnings: async (period = 'week') => {
    const response = await api.get('/driver/earnings', { params: { period } })
    return response.data
  },

  getEarningsBreakdown: async (startDate, endDate) => {
    const response = await api.get('/driver/earnings/breakdown', {
      params: { start_date: startDate, end_date: endDate }
    })
    return response.data
  }
}

// ============================================
// NOTIFICATIONS API
// ============================================

export const notificationsApi = {
  getNotifications: async () => {
    const response = await api.get('/driver/notifications')
    return response.data
  },

  markAsRead: async (notificationId) => {
    const response = await api.put(`/driver/notifications/${notificationId}/read`)
    return response.data
  }
}

// ============================================
// SCHEDULES API
// ============================================

export const schedulesApi = {
  getAll: async (driverId, tenantId) => {
    const response = await api.get('/driver/schedule', {
      params: { driver_id: driverId, tenant_id: tenantId }
    })
    return response.data
  },

  create: async (data) => {
    const response = await api.post('/driver/schedule', data)
    return response.data
  },

  createBulk: async (data) => {
    const response = await api.post('/driver/schedule/bulk', data)
    return response.data
  },

  update: async (scheduleId, data) => {
    const response = await api.put(`/driver/schedule/${scheduleId}`, data)
    return response.data
  },

  delete: async (scheduleId, tenantId) => {
    const response = await api.delete(`/driver/schedule/${scheduleId}`, {
      params: { tenant_id: tenantId }
    })
    return response.data
  },

  getTemplates: async () => {
    const response = await api.get('/driver/schedule/templates')
    return response.data
  }
}

export default api
