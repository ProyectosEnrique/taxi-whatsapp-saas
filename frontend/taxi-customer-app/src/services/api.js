import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json'
  }
})

api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('customer_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('customer_token')
      localStorage.removeItem('customer_data')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export const authApi = {
  login: async (phone, password) => {
    const response = await api.post('/customer/login', { phone, password })
    return response.data
  },

  register: async (userData) => {
    const response = await api.post('/customer/register', userData)
    return response.data
  },

  logout: async () => {
    const response = await api.post('/customer/logout')
    return response.data
  },

  verifyToken: async () => {
    const response = await api.get('/customer/verify')
    return response.data
  }
}

export const customerApi = {
  getProfile: async () => {
    const response = await api.get('/customer/profile')
    return response.data
  },

  updateProfile: async (profileData) => {
    const response = await api.put('/customer/profile', profileData)
    return response.data
  },

  updateLocation: async (lat, lon) => {
    const response = await api.put('/customer/location', { lat, lon })
    return response.data
  }
}

export const ridesApi = {
  requestRide: async (rideData) => {
    const response = await api.post('/customer/rides/request', rideData)
    return response.data
  },

  getRideDetails: async (rideId) => {
    const response = await api.get(`/customer/rides/${rideId}`)
    return response.data
  },

  cancelRide: async (rideId, reason) => {
    const response = await api.post(`/customer/rides/${rideId}/cancel`, { reason })
    return response.data
  },

  rateRide: async (rideId, rating, comment) => {
    const response = await api.post(`/customer/rides/${rideId}/rate`, { rating, comment })
    return response.data
  },

  getHistory: async (filters = {}) => {
    const response = await api.get('/customer/rides/history', { params: filters })
    return response.data
  },

  getActiveRide: async () => {
    const response = await api.get('/customer/rides/active')
    return response.data
  },

  estimateFare: async (origin, destination) => {
    const response = await api.post('/customer/rides/estimate', { origin, destination })
    return response.data
  }
}

export const locationsApi = {
  searchAddress: async (query) => {
    const response = await api.get('/locations/search', { params: { q: query } })
    return response.data
  },

  geocode: async (address) => {
    const response = await api.post('/locations/geocode', { address })
    return response.data
  },

  reverseGeocode: async (lat, lon) => {
    const response = await api.post('/locations/reverse-geocode', { lat, lon })
    return response.data
  },

  getPopularDestinations: async () => {
    const response = await api.get('/locations/popular')
    return response.data
  }
}

export const paymentApi = {
  getPaymentMethods: async () => {
    const response = await api.get('/customer/payment-methods')
    return response.data
  },

  addPaymentMethod: async (paymentData) => {
    const response = await api.post('/customer/payment-methods', paymentData)
    return response.data
  },

  deletePaymentMethod: async (methodId) => {
    const response = await api.delete(`/customer/payment-methods/${methodId}`)
    return response.data
  },

  setDefaultPaymentMethod: async (methodId) => {
    const response = await api.put(`/customer/payment-methods/${methodId}/default`)
    return response.data
  }
}

export const promoApi = {
  validatePromo: async (code) => {
    const response = await api.post('/customer/promo/validate', { code })
    return response.data
  },

  getAvailablePromos: async () => {
    const response = await api.get('/customer/promo/available')
    return response.data
  }
}

export default api
