/**
 * Tenant Store - Multi-Tenant State Management
 * Maneja la configuración del tenant, productos y categorías
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  getTenant,
  getTenantSettings,
  getCategories,
  getProducts,
  getCurrentTenantId
} from '@/services/api'

export const useTenantStore = defineStore('tenant', () => {
  // ============================================================
  // STATE
  // ============================================================

  const tenant = ref(null)
  const settings = ref(null)
  const categories = ref([])
  const subcategories = ref([])
  const products = ref([])
  const loading = ref(false)
  const error = ref(null)
  const initialized = ref(false)

  // Filtros activos
  const activeCategory = ref(null)
  const activeSubcategory = ref(null)
  const searchQuery = ref('')

  // ============================================================
  // GETTERS
  // ============================================================

  const tenantId = computed(() => tenant.value?.tenant?.tenant_id || getCurrentTenantId())
  const tenantName = computed(() => tenant.value?.tenant?.name || 'Farmacia')
  const tenantType = computed(() => tenant.value?.tenant?.type || 'pharmacy')

  const branding = computed(() => {
    const b = settings.value?.settings?.branding || tenant.value?.tenant?.branding || {}
    return {
      primaryColor: b.primary_color || '#10B981',
      secondaryColor: b.secondary_color || '#059669',
      greetingMessage: b.greeting_message || 'Bienvenido',
      tone: b.tone || 'professional'
    }
  })

  const businessRules = computed(() => {
    return settings.value?.settings?.business_rules || tenant.value?.tenant?.business_rules || {
      min_order_amount: 50,
      delivery_fee: 20
    }
  })

  // Categorías con conteo
  const categoriesWithCount = computed(() => {
    return categories.value.map(cat => ({
      ...cat,
      productCount: cat.product_count || 0
    }))
  })

  // Productos filtrados por categoría y búsqueda
  const filteredProducts = computed(() => {
    let result = products.value

    // Filtrar por categoría principal
    if (activeCategory.value) {
      result = result.filter(p => p.main_category_id === activeCategory.value)
    }

    // Filtrar por subcategoría
    if (activeSubcategory.value) {
      result = result.filter(p => p.subcategory_id === activeSubcategory.value)
    }

    // Filtrar por búsqueda
    if (searchQuery.value.trim()) {
      const query = searchQuery.value.toLowerCase()
      result = result.filter(p =>
        p.name?.toLowerCase().includes(query) ||
        p.description?.toLowerCase().includes(query) ||
        p.generic_name?.toLowerCase().includes(query) ||
        p.active_ingredient?.toLowerCase().includes(query)
      )
    }

    return result
  })

  // Subcategorías de la categoría activa
  const activeSubcategories = computed(() => {
    if (!activeCategory.value) return []
    return subcategories.value.filter(sub => sub.parent_id === activeCategory.value)
  })

  // Total de productos
  const totalProducts = computed(() => products.value.length)

  // ============================================================
  // ACTIONS
  // ============================================================

  /**
   * Inicializa el tenant - carga toda la configuración
   */
  async function initializeTenant() {
    if (initialized.value) return

    loading.value = true
    error.value = null

    try {
      const tenantIdValue = getCurrentTenantId()
      console.log('[TenantStore] Inicializando tenant:', tenantIdValue)

      // Cargar en paralelo para mayor velocidad
      const [tenantData, settingsData, categoriesData, productsData] = await Promise.all([
        getTenant(tenantIdValue).catch(() => null),
        getTenantSettings(tenantIdValue).catch(() => null),
        getCategories(tenantIdValue).catch(() => ({ main_categories: [], subcategories: [] })),
        getProducts(tenantIdValue, { limit: 2000 }).catch(() => ({ products: [] }))
      ])

      tenant.value = tenantData
      settings.value = settingsData
      categories.value = categoriesData.main_categories || []
      subcategories.value = categoriesData.subcategories || []
      products.value = productsData.products || []

      initialized.value = true

      console.log('[TenantStore] Tenant inicializado:', {
        name: tenantName.value,
        categories: categories.value.length,
        products: products.value.length
      })

    } catch (err) {
      console.error('[TenantStore] Error inicializando:', err)
      error.value = err.message || 'Error al cargar datos'
    } finally {
      loading.value = false
    }
  }

  /**
   * Selecciona una categoría
   */
  function selectCategory(categoryId) {
    activeCategory.value = categoryId
    activeSubcategory.value = null // Reset subcategoría
    searchQuery.value = '' // Reset búsqueda
  }

  /**
   * Selecciona una subcategoría
   */
  function selectSubcategory(subcategoryId) {
    activeSubcategory.value = subcategoryId
  }

  /**
   * Limpia todos los filtros
   */
  function clearFilters() {
    activeCategory.value = null
    activeSubcategory.value = null
    searchQuery.value = ''
  }

  /**
   * Busca productos
   */
  function setSearchQuery(query) {
    searchQuery.value = query
    // Si hay búsqueda, limpiar filtros de categoría
    if (query.trim()) {
      activeCategory.value = null
      activeSubcategory.value = null
    }
  }

  /**
   * Obtiene un producto por ID
   */
  function getProductById(productId) {
    return products.value.find(p => p.id === productId || p.id === String(productId))
  }

  /**
   * Recarga los productos (útil después de cambios)
   */
  async function reloadProducts() {
    try {
      const tenantIdValue = getCurrentTenantId()
      const productsData = await getProducts(tenantIdValue, { limit: 2000 })
      products.value = productsData.products || []
    } catch (err) {
      console.error('[TenantStore] Error recargando productos:', err)
    }
  }

  // ============================================================
  // RETURN
  // ============================================================

  return {
    // State
    tenant,
    settings,
    categories,
    subcategories,
    products,
    loading,
    error,
    initialized,
    activeCategory,
    activeSubcategory,
    searchQuery,

    // Getters
    tenantId,
    tenantName,
    tenantType,
    branding,
    businessRules,
    categoriesWithCount,
    filteredProducts,
    activeSubcategories,
    totalProducts,

    // Actions
    initializeTenant,
    selectCategory,
    selectSubcategory,
    clearFilters,
    setSearchQuery,
    getProductById,
    reloadProducts
  }
})
