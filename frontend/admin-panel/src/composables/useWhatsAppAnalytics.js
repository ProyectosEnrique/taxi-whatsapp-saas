import { ref, computed } from 'vue'

/**
 * Composable para manejar analytics de WhatsApp
 * Proporciona funciones para obtener métricas, campañas y conversaciones
 */
export function useWhatsAppAnalytics() {
  const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001'

  // State
  const metrics = ref(null)
  const campaigns = ref([])
  const conversations = ref([])
  const topProducts = ref([])
  const peakHours = ref([])
  const loading = ref(false)
  const error = ref(null)

  /**
   * Obtener métricas generales del canal WhatsApp
   */
  const fetchMetrics = async () => {
    try {
      loading.value = true
      error.value = null

      const response = await fetch(`${API_URL}/api/analytics/whatsapp/metrics`)

      if (!response.ok) {
        throw new Error('Error al cargar métricas')
      }

      const data = await response.json()
      metrics.value = data

      return data
    } catch (err) {
      console.error('Error fetching WhatsApp metrics:', err)
      error.value = err.message

      // Fallback a datos de desarrollo
      metrics.value = {
        total_conversations: 245,
        total_orders: 87,
        conversion_rate: 35.5,
        avg_ticket: 185.50,
        active_conversations: 12,
        pending_responses: 3
      }

      return metrics.value
    } finally {
      loading.value = false
    }
  }

  /**
   * Obtener historial de campañas broadcast
   */
  const fetchCampaigns = async () => {
    try {
      loading.value = true
      error.value = null

      const response = await fetch(`${API_URL}/api/analytics/whatsapp/campaigns`)

      if (!response.ok) {
        throw new Error('Error al cargar campañas')
      }

      const data = await response.json()
      campaigns.value = data

      return data
    } catch (err) {
      console.error('Error fetching WhatsApp campaigns:', err)
      error.value = err.message

      // Fallback a datos de desarrollo
      campaigns.value = [
        {
          id: 1,
          name: '2x1 Hamburguesas',
          date: new Date().toISOString(),
          segment: 'frequent',
          total_sent: 45,
          successful: 43,
          failed: 2,
          read_count: 38,
          orders_generated: 12,
          revenue: 1250.00
        },
        {
          id: 2,
          name: '20% Descuento Bebidas',
          date: new Date(Date.now() - 86400000).toISOString(),
          segment: 'all',
          total_sent: 150,
          successful: 145,
          failed: 5,
          read_count: 120,
          orders_generated: 28,
          revenue: 890.00
        },
        {
          id: 3,
          name: 'Reactivación Clientes',
          date: new Date(Date.now() - 172800000).toISOString(),
          segment: 'inactive',
          total_sent: 32,
          successful: 30,
          failed: 2,
          read_count: 25,
          orders_generated: 8,
          revenue: 650.00
        }
      ]

      return campaigns.value
    } finally {
      loading.value = false
    }
  }

  /**
   * Obtener conversaciones activas
   */
  const fetchConversations = async () => {
    try {
      loading.value = true
      error.value = null

      const response = await fetch(`${API_URL}/api/whatsapp/conversations/active`)

      if (!response.ok) {
        throw new Error('Error al cargar conversaciones')
      }

      const data = await response.json()
      conversations.value = data

      return data
    } catch (err) {
      console.error('Error fetching WhatsApp conversations:', err)
      error.value = err.message

      // Fallback a datos de desarrollo
      conversations.value = [
        {
          id: 1,
          customer_name: 'María García',
          phone: '+5215551234567',
          state: 'taking_order',
          last_message: 'Quiero una hamburguesa BBQ',
          last_message_time: new Date(Date.now() - 300000).toISOString(),
          order_total: 125.00
        },
        {
          id: 2,
          customer_name: 'Juan Pérez',
          phone: '+5215559876543',
          state: 'greeting',
          last_message: 'Hola',
          last_message_time: new Date(Date.now() - 600000).toISOString(),
          order_total: 0
        },
        {
          id: 3,
          customer_name: 'Ana Martínez',
          phone: '+5215551122334',
          state: 'confirming',
          last_message: 'Sí, confirmo mi pedido',
          last_message_time: new Date(Date.now() - 900000).toISOString(),
          order_total: 235.50
        }
      ]

      return conversations.value
    } finally {
      loading.value = false
    }
  }

  /**
   * Obtener productos más vendidos por WhatsApp
   */
  const fetchTopProducts = async () => {
    try {
      loading.value = true
      error.value = null

      const response = await fetch(`${API_URL}/api/analytics/whatsapp/top-products`)

      if (!response.ok) {
        throw new Error('Error al cargar productos top')
      }

      const data = await response.json()
      topProducts.value = data

      return data
    } catch (err) {
      console.error('Error fetching top products:', err)
      error.value = err.message

      // Fallback a datos de desarrollo
      topProducts.value = [
        { name: 'Hamburguesa BBQ', orders: 45, revenue: 1350.00 },
        { name: 'Tacos al Pastor', orders: 38, revenue: 950.00 },
        { name: 'Pizza Margarita', orders: 32, revenue: 1280.00 },
        { name: 'Ensalada César', orders: 28, revenue: 560.00 },
        { name: 'Cerveza Corona', orders: 65, revenue: 975.00 }
      ]

      return topProducts.value
    } finally {
      loading.value = false
    }
  }

  /**
   * Obtener horarios pico de pedidos por WhatsApp
   */
  const fetchPeakHours = async () => {
    try {
      loading.value = true
      error.value = null

      const response = await fetch(`${API_URL}/api/analytics/whatsapp/peak-hours`)

      if (!response.ok) {
        throw new Error('Error al cargar horarios pico')
      }

      const data = await response.json()
      peakHours.value = data

      return data
    } catch (err) {
      console.error('Error fetching peak hours:', err)
      error.value = err.message

      // Fallback a datos de desarrollo
      peakHours.value = [
        { hour: '13:00', orders: 25, percentage: 85 },
        { hour: '14:00', orders: 30, percentage: 100 },
        { hour: '15:00', orders: 22, percentage: 73 },
        { hour: '20:00', orders: 28, percentage: 93 },
        { hour: '21:00', orders: 26, percentage: 87 }
      ]

      return peakHours.value
    } finally {
      loading.value = false
    }
  }

  /**
   * Previsualizar audiencia para un segmento
   */
  const previewAudience = async (segment) => {
    try {
      const response = await fetch(`${API_URL}/api/admin/whatsapp/preview-audience`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ segment })
      })

      if (!response.ok) {
        throw new Error('Error al obtener preview')
      }

      const data = await response.json()
      return data.count || 0
    } catch (err) {
      console.error('Error previewing audience:', err)

      // Fallback a datos mockeados
      const mockCounts = {
        all: 150,
        frequent: 45,
        inactive: 32,
        new: 28,
        vip: 15
      }

      return mockCounts[segment] || 0
    }
  }

  /**
   * Enviar broadcast a segmento de clientes
   */
  const sendBroadcast = async (payload) => {
    try {
      const response = await fetch(`${API_URL}/api/admin/whatsapp/broadcast`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })

      if (!response.ok) {
        throw new Error('Error al enviar broadcast')
      }

      const result = await response.json()

      // Refrescar campañas después de enviar
      await fetchCampaigns()

      return result
    } catch (err) {
      console.error('Error sending broadcast:', err)
      throw err
    }
  }

  /**
   * Formatear fecha relativa (hace X tiempo)
   */
  const formatRelativeTime = (dateString) => {
    const date = new Date(dateString)
    const now = new Date()
    const diffMs = now - date
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMs / 3600000)
    const diffDays = Math.floor(diffMs / 86400000)

    if (diffMins < 1) return 'Ahora'
    if (diffMins < 60) return `Hace ${diffMins} min`
    if (diffHours < 24) return `Hace ${diffHours}h`
    return `Hace ${diffDays}d`
  }

  /**
   * Formatear número de teléfono
   */
  const formatPhone = (phone) => {
    // Formato: +52 55 1234 5678
    if (!phone) return ''
    const cleaned = phone.replace(/\D/g, '')
    if (cleaned.length === 12) {
      return `+${cleaned.slice(0, 2)} ${cleaned.slice(2, 4)} ${cleaned.slice(4, 8)} ${cleaned.slice(8)}`
    }
    return phone
  }

  /**
   * Calcular métricas computadas
   */
  const totalRevenue = computed(() => {
    return campaigns.value.reduce((sum, c) => sum + (c.revenue || 0), 0)
  })

  const avgConversionRate = computed(() => {
    if (campaigns.value.length === 0) return 0
    const totalSent = campaigns.value.reduce((sum, c) => sum + c.total_sent, 0)
    const totalOrders = campaigns.value.reduce((sum, c) => sum + (c.orders_generated || 0), 0)
    return totalSent > 0 ? ((totalOrders / totalSent) * 100).toFixed(1) : 0
  })

  const avgSuccessRate = computed(() => {
    if (campaigns.value.length === 0) return 0
    const totalSent = campaigns.value.reduce((sum, c) => sum + c.total_sent, 0)
    const totalSuccess = campaigns.value.reduce((sum, c) => sum + c.successful, 0)
    return totalSent > 0 ? ((totalSuccess / totalSent) * 100).toFixed(1) : 0
  })

  return {
    // State
    metrics,
    campaigns,
    conversations,
    topProducts,
    peakHours,
    loading,
    error,

    // Computed
    totalRevenue,
    avgConversionRate,
    avgSuccessRate,

    // Methods
    fetchMetrics,
    fetchCampaigns,
    fetchConversations,
    fetchTopProducts,
    fetchPeakHours,
    previewAudience,
    sendBroadcast,

    // Utils
    formatRelativeTime,
    formatPhone
  }
}
