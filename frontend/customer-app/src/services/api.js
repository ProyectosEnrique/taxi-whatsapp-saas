import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000'

// Crear instancia de axios
const apiClient = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Interceptor para agregar token de autenticación
apiClient.interceptors.request.use(config => {
  const token = localStorage.getItem('auth_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Interceptor para manejar errores
apiClient.interceptors.response.use(
  response => response.data,
  error => {
    const message = error.response?.data?.message || error.message || 'Error desconocido'
    console.error('API Error:', message)
    return Promise.reject(new Error(message))
  }
)

// ===== TENANT API =====
export async function getTenant(tenantId) {
  return await apiClient.get(`/api/tenants/${tenantId}`)
    .then(res => res.tenant)
}

export async function getTenantProducts(tenantId, category = null) {
  const params = category ? { category } : {}
  return await apiClient.get(`/api/tenants/${tenantId}/products`, { params })
    .then(res => res.products || [])
}

export async function getTenantByPhone(phone) {
  return await apiClient.get(`/api/tenants/by-phone/${phone}`)
    .then(res => res.tenant)
}

// ===== AUTH API =====
export async function login(credentials) {
  return await apiClient.post('/api/auth/login', credentials)
}

export async function register(userData) {
  return await apiClient.post('/api/auth/register', userData)
}

export async function getProfile() {
  return await apiClient.get('/api/auth/profile')
    .then(res => res.user)
}

export async function updateProfile(updates) {
  return await apiClient.put('/api/auth/profile', updates)
    .then(res => res.user)
}

// ===== ORDERS API =====
export async function createOrder(orderData) {
  return await apiClient.post('/api/orders', orderData)
    .then(res => res.order)
}

export async function getOrders() {
  return await apiClient.get('/api/orders')
    .then(res => res.orders || [])
}

export async function getOrder(orderId) {
  return await apiClient.get(`/api/orders/${orderId}`)
    .then(res => res.order)
}

export async function cancelOrder(orderId, reason) {
  return await apiClient.post(`/api/orders/${orderId}/cancel`, { reason })
}

export async function updateOrderStatus(orderId, status) {
  return await apiClient.put(`/api/orders/${orderId}/status`, { status })
}

// ===== ADDRESSES API =====
export async function getAddresses() {
  return await apiClient.get('/api/addresses')
    .then(res => res.addresses || [])
}

export async function createAddress(addressData) {
  return await apiClient.post('/api/addresses', addressData)
    .then(res => res.address)
}

export async function updateAddress(addressId, updates) {
  return await apiClient.put(`/api/addresses/${addressId}`, updates)
    .then(res => res.address)
}

export async function deleteAddress(addressId) {
  return await apiClient.delete(`/api/addresses/${addressId}`)
}

// ===== PROMOTIONS API =====
export async function getPromotions() {
  return await apiClient.get('/api/promotions')
    .then(res => res.promotions || [])
}

export async function validatePromoCode(code) {
  return await apiClient.post('/api/promotions/validate', { code })
    .then(res => res.promotion)
}

// ===== REVIEWS API =====
export async function getReviews(productId = null) {
  const params = productId ? { product_id: productId } : {}
  return await apiClient.get('/api/reviews', { params })
    .then(res => res.reviews || [])
}

export async function submitReview(reviewData) {
  return await apiClient.post('/api/reviews', reviewData)
    .then(res => res.review)
}

export async function uploadImage(file) {
  const formData = new FormData()
  formData.append('image', file)

  return await apiClient.post('/api/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }).then(res => res.url)
}

// ===== LOYALTY API =====
export async function getLoyaltyData() {
  return await apiClient.get('/api/loyalty')
    .then(res => res.data)
}

export async function getRewards() {
  return await apiClient.get('/api/loyalty/rewards')
    .then(res => res.rewards || [])
}

export async function redeemReward(rewardId) {
  return await apiClient.post(`/api/loyalty/redeem/${rewardId}`)
}

// Exportar API client y todas las funciones
export default {
  // Tenant
  getTenant,
  getTenantProducts,
  getTenantByPhone,

  // Auth
  login,
  register,
  getProfile,
  updateProfile,

  // Orders
  createOrder,
  getOrders,
  getOrder,
  cancelOrder,
  updateOrderStatus,

  // Addresses
  getAddresses,
  createAddress,
  updateAddress,
  deleteAddress,

  // Promotions
  getPromotions,
  validatePromoCode,

  // Reviews
  getReviews,
  submitReview,
  uploadImage,

  // Loyalty
  getLoyaltyData,
  getRewards,
  redeemReward
}
