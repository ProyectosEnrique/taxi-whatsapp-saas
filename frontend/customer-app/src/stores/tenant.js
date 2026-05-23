import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/services/api'

export const useTenantStore = defineStore('tenant', () => {
  // State
  const tenant = ref(null)
  const products = ref([])
  const categories = ref([])
  const loading = ref(false)
  const error = ref(null)

  // Getters
  const tenantId = computed(() => tenant.value?.tenant_id || 'default')
  const tenantName = computed(() => tenant.value?.name || '')
  const tenantType = computed(() => tenant.value?.type || 'restaurant')
  const branding = computed(() => tenant.value?.branding || {})
  const businessRules = computed(() => tenant.value?.business_rules || {})

  // Computed - Productos por categoría
  const productsByCategory = computed(() => {
    const grouped = {}
    products.value.forEach(product => {
      const category = product.category || 'Otros'
      if (!grouped[category]) {
        grouped[category] = []
      }
      if (product.active) {
        grouped[category].push(product)
      }
    })
    return grouped
  })

  // Actions
  async function initializeTenant() {
    // Obtener tenant_id de .env o URL
    const envTenantId = import.meta.env.VITE_TENANT_ID
    const urlParams = new URLSearchParams(window.location.search)
    const urlTenantId = urlParams.get('tenant')

    const targetTenantId = urlTenantId || envTenantId || 'default'

    try {
      loading.value = true
      error.value = null

      // Cargar configuración del tenant
      const tenantData = await api.getTenant(targetTenantId)
      tenant.value = tenantData

      // Cargar productos del tenant
      await loadProducts()

      // Aplicar branding dinámico
      applyBranding()

    } catch (err) {
      console.error('Error inicializando tenant:', err)
      error.value = err.message

      // Fallback a tenant por defecto
      if (targetTenantId !== 'default') {
        console.log('Intentando cargar tenant por defecto...')
        const defaultTenant = await api.getTenant('default')
        tenant.value = defaultTenant
        await loadProducts()
      }
    } finally {
      loading.value = false
    }
  }

  async function loadProducts() {
    try {
      const productsData = await api.getTenantProducts(tenantId.value)
      products.value = productsData

      // Extraer categorías únicas
      const uniqueCategories = [...new Set(productsData.map(p => p.category))]
      categories.value = uniqueCategories.sort()

    } catch (err) {
      console.error('Error cargando productos:', err)
      error.value = err.message
    }
  }

  function applyBranding() {
    if (!branding.value) return

    // Aplicar colores personalizados
    if (branding.value.primary_color) {
      document.documentElement.style.setProperty('--color-primary', branding.value.primary_color)
    }

    // Aplicar logo/favicon
    if (branding.value.logo_url) {
      const favicon = document.querySelector('link[rel="icon"]')
      if (favicon) {
        favicon.href = branding.value.logo_url
      }
    }

    // Aplicar título
    if (branding.value.brand_name) {
      document.title = branding.value.brand_name
    }
  }

  function getProductById(productId) {
    return products.value.find(p => p.product_id === productId)
  }

  function searchProducts(query) {
    const lowerQuery = query.toLowerCase()
    return products.value.filter(product => {
      return (
        product.name.toLowerCase().includes(lowerQuery) ||
        product.description?.toLowerCase().includes(lowerQuery) ||
        product.aliases?.some(alias => alias.toLowerCase().includes(lowerQuery))
      )
    })
  }

  return {
    // State
    tenant,
    products,
    categories,
    loading,
    error,

    // Getters
    tenantId,
    tenantName,
    tenantType,
    branding,
    businessRules,
    productsByCategory,

    // Actions
    initializeTenant,
    loadProducts,
    applyBranding,
    getProductById,
    searchProducts
  }
})
