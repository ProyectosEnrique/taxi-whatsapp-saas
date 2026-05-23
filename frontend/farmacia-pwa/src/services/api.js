/**
 * API Service - Cliente HTTP Multi-Tenant
 * Centraliza todas las llamadas al backend
 */
import axios from 'axios'

// Configuración desde variables de entorno
const API_URL = import.meta.env.VITE_API_URL || 'https://sales-agent-service-308574626875.us-central1.run.app'
const DEFAULT_TENANT_ID = import.meta.env.VITE_TENANT_ID || 'tenant_pharmacy_001'

// Cliente axios configurado
const apiClient = axios.create({
  baseURL: API_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Interceptor para agregar tenant_id automáticamente
apiClient.interceptors.request.use(config => {
  // Obtener tenant_id de la URL o usar el default
  const urlParams = new URLSearchParams(window.location.search)
  const tenantId = urlParams.get('tenant') || DEFAULT_TENANT_ID

  // Agregar tenant_id a los parámetros si no está
  if (!config.params) {
    config.params = {}
  }
  if (!config.params.tenant_id) {
    config.params.tenant_id = tenantId
  }

  return config
})

// Interceptor para manejo de errores
apiClient.interceptors.response.use(
  response => response,
  error => {
    console.error('[API] Error:', error.response?.data || error.message)
    return Promise.reject(error)
  }
)

// ============================================================
// TENANT ENDPOINTS
// ============================================================

/**
 * Obtiene información de un tenant
 */
export async function getTenant(tenantId) {
  const response = await apiClient.get(`/api/tenants/${tenantId}`)
  return response.data
}

/**
 * Obtiene settings de un tenant
 */
export async function getTenantSettings(tenantId) {
  const response = await apiClient.get(`/api/v1/tenant/${tenantId}/settings`)
  return response.data
}

// ============================================================
// CATEGORIES ENDPOINTS
// ============================================================

/**
 * Obtiene categorías de un tenant
 * @param {string} tenantId - ID del tenant
 * @param {string} parent - Nombre de categoría padre (opcional)
 */
export async function getCategories(tenantId, parent = null) {
  const params = { tenant_id: tenantId }
  if (parent) {
    params.parent = parent
  }
  const response = await apiClient.get('/api/v1/categories', { params })
  return response.data
}

// ============================================================
// PRODUCTS ENDPOINTS
// ============================================================

/**
 * Obtiene productos de un tenant con filtros
 * @param {string} tenantId - ID del tenant
 * @param {Object} filters - Filtros opcionales
 */
export async function getProducts(tenantId, filters = {}) {
  const params = {
    tenant_id: tenantId,
    ...filters
  }
  const response = await apiClient.get('/api/v1/products', { params })
  return response.data
}

/**
 * Obtiene productos por categoría
 */
export async function getProductsByCategory(tenantId, categoryId) {
  return getProducts(tenantId, { category_id: categoryId })
}

/**
 * Obtiene productos por subcategoría
 */
export async function getProductsBySubcategory(tenantId, subcategoryId) {
  return getProducts(tenantId, { subcategory_id: subcategoryId })
}

/**
 * Busca productos por término
 */
export async function searchProducts(tenantId, searchTerm, limit = 20) {
  return getProducts(tenantId, { search: searchTerm, limit })
}

// ============================================================
// SESSION ENDPOINTS (para Sofia)
// ============================================================

/**
 * Inicializa una sesión con el agente de ventas
 */
export async function initSession(tableId = 1) {
  const response = await apiClient.post('/api/session/init', { table_id: tableId })
  return response.data
}

/**
 * Procesa un mensaje de texto
 */
export async function processText(sessionId, text, tenantId) {
  const response = await apiClient.post('/api/text/process', {
    session_id: sessionId,
    text: text,
    tenant_id: tenantId
  })
  return response.data
}

// ============================================================
// CART/ORDER ENDPOINTS
// ============================================================

/**
 * Obtiene el carrito de una sesión
 */
export async function getCart(sessionId) {
  const response = await apiClient.get(`/api/order/cart/${sessionId}`)
  return response.data
}

/**
 * Envía el pedido a cocina/farmacia
 */
export async function submitOrder(sessionId, tableId = 1) {
  const response = await apiClient.post('/api/order/submit', {
    session_id: sessionId,
    table_id: tableId
  })
  return response.data
}

// ============================================================
// HELPERS
// ============================================================

/**
 * Obtiene el tenant_id actual desde URL o env
 */
export function getCurrentTenantId() {
  const urlParams = new URLSearchParams(window.location.search)
  return urlParams.get('tenant') || DEFAULT_TENANT_ID
}

export default apiClient
