import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import axios from 'axios'

// URL del voice-assistant service
const VOICE_ASSISTANT_URL = import.meta.env.VITE_VOICE_ASSISTANT_URL || 'http://localhost:5000'

export const useAnalyticsStore = defineStore('analytics', () => {
  const orders = ref([])
  const tables = ref([])
  const products = ref([])
  const loading = ref(false)
  const error = ref(null)

  // ============================================================
  // MÉTRICAS DEL ASISTENTE DE VOZ
  // ============================================================
  const voiceMetrics = ref({
    total_conversations: 0,
    total_revenue: 0,
    total_items_sold: 0,
    avg_order_value: 0,
    avg_conversation_duration: 0,
    avg_sentiment: 0.5,
    upsell_success_rate: 0,
    crosssell_success_rate: 0,
    daily_revenue: {},
    hourly_distribution: {},
    top_products: {},
    intents_summary: {},
    daily_summaries: []
  })

  const voiceMetricsLoading = ref(false)
  const voiceMetricsError = ref(null)

  // Computed metrics
  const todaySales = computed(() => {
    const today = new Date().toISOString().split('T')[0]
    return orders.value
      .filter(o => o.created_at?.startsWith(today) && o.status !== 'cancelled')
      .reduce((sum, o) => sum + parseFloat(o.total_amount || 0), 0)
  })

  const activeOrders = computed(() => {
    return orders.value.filter(o =>
      !['delivered', 'cancelled', 'paid'].includes(o.status?.toLowerCase())
    ).length
  })

  const tableOccupancy = computed(() => {
    if (tables.value.length === 0) return 0
    const occupied = tables.value.filter(t => t.status === 'occupied').length
    return Math.round((occupied / tables.value.length) * 100)
  })

  const averageTicket = computed(() => {
    const today = new Date().toISOString().split('T')[0]
    const todayOrders = orders.value.filter(o =>
      o.created_at?.startsWith(today) && o.status !== 'cancelled'
    )
    if (todayOrders.length === 0) return 0
    return todaySales.value / todayOrders.length
  })

  const topProducts = computed(() => {
    const productCounts = {}
    orders.value.forEach(order => {
      if (order.items && Array.isArray(order.items)) {
        order.items.forEach(item => {
          const name = item.product_name || item.name
          if (!productCounts[name]) {
            productCounts[name] = { name, quantity: 0, revenue: 0 }
          }
          productCounts[name].quantity += item.quantity || 0
          productCounts[name].revenue += parseFloat(item.price || 0) * (item.quantity || 0)
        })
      }
    })
    return Object.values(productCounts)
      .sort((a, b) => b.quantity - a.quantity)
      .slice(0, 10)
  })

  const hourlyOrders = computed(() => {
    const today = new Date().toISOString().split('T')[0]
    const hourCounts = Array(24).fill(0)

    orders.value
      .filter(o => o.created_at?.startsWith(today))
      .forEach(order => {
        const hour = new Date(order.created_at).getHours()
        hourCounts[hour]++
      })

    return hourCounts.map((count, hour) => ({
      hour: `${hour.toString().padStart(2, '0')}:00`,
      orders: count
    }))
  })

  const recentOrders = computed(() => {
    return orders.value
      .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
      .slice(0, 10)
  })


  // Ventas de ayer
  const yesterdaySales = computed(() => {
    const yesterday = new Date()
    yesterday.setDate(yesterday.getDate() - 1)
    const yesterdayStr = yesterday.toISOString().split('T')[0]
    return orders.value
      .filter(o => o.created_at?.startsWith(yesterdayStr) && o.status !== 'cancelled')
      .reduce((sum, o) => sum + parseFloat(o.total_amount || 0), 0)
  })

  // Comparativa de ventas (porcentaje de cambio)
  const salesChange = computed(() => {
    if (yesterdaySales.value === 0) return todaySales.value > 0 ? 100 : 0
    return Math.round(((todaySales.value - yesterdaySales.value) / yesterdaySales.value) * 100)
  })

  // Productos agotados (no disponibles)
  const soldOutProducts = computed(() => {
    return products.value.filter(p => !p.is_available)
  })

  // Total de pedidos hoy
  const todayOrdersCount = computed(() => {
    const today = new Date().toISOString().split('T')[0]
    return orders.value.filter(o => o.created_at?.startsWith(today) && o.status !== 'cancelled').length
  })

  // Pedidos de ayer
  const yesterdayOrdersCount = computed(() => {
    const yesterday = new Date()
    yesterday.setDate(yesterday.getDate() - 1)
    const yesterdayStr = yesterday.toISOString().split('T')[0]
    return orders.value.filter(o => o.created_at?.startsWith(yesterdayStr) && o.status !== 'cancelled').length
  })

  // ============================================================
  // MÉTRICAS FINANCIERAS AVANZADAS
  // ============================================================

  // Calcular costo y margen por producto (usa cost_price si está disponible)
  const productProfitability = computed(() => {
    const profitData = {}
    orders.value.forEach(order => {
      if (order.items && Array.isArray(order.items) && order.status !== 'cancelled') {
        order.items.forEach(item => {
          const name = item.product_name || item.name
          const price = parseFloat(item.price || 0)
          const cost = parseFloat(item.cost_price || item.cost || price * 0.35) // Default 35% food cost
          const qty = item.quantity || 1

          if (!profitData[name]) {
            profitData[name] = {
              name,
              revenue: 0,
              cost: 0,
              quantity: 0,
              unitPrice: price,
              unitCost: cost
            }
          }
          profitData[name].revenue += price * qty
          profitData[name].cost += cost * qty
          profitData[name].quantity += qty
        })
      }
    })

    return Object.values(profitData).map(p => ({
      ...p,
      margin: p.revenue - p.cost,
      marginPercent: p.revenue > 0 ? Math.round(((p.revenue - p.cost) / p.revenue) * 100) : 0,
      foodCostPercent: p.revenue > 0 ? Math.round((p.cost / p.revenue) * 100) : 0
    })).sort((a, b) => b.margin - a.margin)
  })

  // Food cost promedio del día
  const todayFoodCost = computed(() => {
    const today = new Date().toISOString().split('T')[0]
    let totalRevenue = 0
    let totalCost = 0

    orders.value
      .filter(o => o.created_at?.startsWith(today) && o.status !== 'cancelled')
      .forEach(order => {
        if (order.items && Array.isArray(order.items)) {
          order.items.forEach(item => {
            const price = parseFloat(item.price || 0) * (item.quantity || 1)
            const cost = parseFloat(item.cost_price || item.cost || price * 0.35) * (item.quantity || 1)
            totalRevenue += price
            totalCost += cost
          })
        }
      })

    return totalRevenue > 0 ? Math.round((totalCost / totalRevenue) * 100) : 0
  })

  // Margen bruto del día
  const todayGrossMargin = computed(() => {
    return 100 - todayFoodCost.value
  })

  // Productos con mejor margen (Top 5)
  const topMarginProducts = computed(() => {
    return productProfitability.value
      .filter(p => p.quantity >= 3) // Mínimo 3 vendidos
      .sort((a, b) => b.marginPercent - a.marginPercent)
      .slice(0, 5)
  })

  // Productos con peor margen (oportunidad de mejora)
  const lowMarginProducts = computed(() => {
    return productProfitability.value
      .filter(p => p.quantity >= 3 && p.marginPercent < 50)
      .sort((a, b) => a.marginPercent - b.marginPercent)
      .slice(0, 5)
  })

  // ============================================================
  // TENDENCIAS SEMANALES Y MENSUALES
  // ============================================================

  // Ventas de los últimos 7 días
  const weeklyTrend = computed(() => {
    const trend = []
    for (let i = 6; i >= 0; i--) {
      const date = new Date()
      date.setDate(date.getDate() - i)
      const dateStr = date.toISOString().split('T')[0]
      const dayName = date.toLocaleDateString('es', { weekday: 'short' })

      const daySales = orders.value
        .filter(o => o.created_at?.startsWith(dateStr) && o.status !== 'cancelled')
        .reduce((sum, o) => sum + parseFloat(o.total_amount || 0), 0)

      const dayOrders = orders.value
        .filter(o => o.created_at?.startsWith(dateStr) && o.status !== 'cancelled')
        .length

      trend.push({
        date: dateStr,
        dayName: dayName.charAt(0).toUpperCase() + dayName.slice(1),
        sales: daySales,
        orders: dayOrders,
        avgTicket: dayOrders > 0 ? daySales / dayOrders : 0
      })
    }
    return trend
  })

  // Totales de la semana
  const weeklySalesTotal = computed(() => {
    return weeklyTrend.value.reduce((sum, d) => sum + d.sales, 0)
  })

  const weeklyOrdersTotal = computed(() => {
    return weeklyTrend.value.reduce((sum, d) => sum + d.orders, 0)
  })

  // Semana anterior para comparación
  const previousWeekSales = computed(() => {
    let total = 0
    for (let i = 13; i >= 7; i--) {
      const date = new Date()
      date.setDate(date.getDate() - i)
      const dateStr = date.toISOString().split('T')[0]

      total += orders.value
        .filter(o => o.created_at?.startsWith(dateStr) && o.status !== 'cancelled')
        .reduce((sum, o) => sum + parseFloat(o.total_amount || 0), 0)
    }
    return total
  })

  // Cambio semanal en porcentaje
  const weeklyChange = computed(() => {
    if (previousWeekSales.value === 0) return weeklySalesTotal.value > 0 ? 100 : 0
    return Math.round(((weeklySalesTotal.value - previousWeekSales.value) / previousWeekSales.value) * 100)
  })

  // Mejor día de la semana
  const bestDayOfWeek = computed(() => {
    if (weeklyTrend.value.length === 0) return null
    return weeklyTrend.value.reduce((best, day) =>
      day.sales > best.sales ? day : best
    , weeklyTrend.value[0])
  })

  // ============================================================
  // ROTACIÓN DE PRODUCTOS
  // ============================================================

  // Tasa de rotación (productos vendidos / total productos)
  const productRotationRate = computed(() => {
    if (products.value.length === 0) return 0
    const productsSold = new Set()
    const today = new Date().toISOString().split('T')[0]

    orders.value
      .filter(o => o.created_at?.startsWith(today) && o.status !== 'cancelled')
      .forEach(order => {
        if (order.items && Array.isArray(order.items)) {
          order.items.forEach(item => {
            productsSold.add(item.product_id || item.product_name || item.name)
          })
        }
      })

    return Math.round((productsSold.size / products.value.length) * 100)
  })

  // Productos sin ventas hoy
  const productsNotSoldToday = computed(() => {
    const today = new Date().toISOString().split('T')[0]
    const soldProductIds = new Set()

    orders.value
      .filter(o => o.created_at?.startsWith(today) && o.status !== 'cancelled')
      .forEach(order => {
        if (order.items && Array.isArray(order.items)) {
          order.items.forEach(item => {
            soldProductIds.add(item.product_id || item.product_name || item.name)
          })
        }
      })

    return products.value.filter(p =>
      p.is_available && !soldProductIds.has(p.id) && !soldProductIds.has(p.name)
    )
  })

  async function fetchAllData() {
    loading.value = true
    error.value = null

    try {
      // Reducido de 200 a 100 órdenes para mejorar tiempo de carga
      // 100 órdenes son suficientes para métricas diarias/semanales
      const [ordersRes, tablesRes, productsRes] = await Promise.all([
        axios.get('/api/v1/orders', { params: { limit: 100 } }),
        axios.get('/api/v1/tables'),
        axios.get('/api/v1/products')
      ])

      orders.value = ordersRes.data
      tables.value = tablesRes.data
      products.value = productsRes.data

      console.log('✅ Analytics data loaded:', {
        orders: orders.value.length,
        tables: tables.value.length,
        products: products.value.length
      })
    } catch (err) {
      console.error('❌ Error loading analytics:', err)
      error.value = err.message
    } finally {
      loading.value = false
    }
  }

  async function fetchReports() {
    try {
      const response = await axios.get('http://localhost:5015/api/v1/reports/sales')
      return response.data
    } catch (err) {
      console.error('Error fetching reports:', err)
      throw err
    }
  }

  // ============================================================
  // FUNCIONES PARA MÉTRICAS DEL ASISTENTE DE VOZ
  // ============================================================

  async function fetchVoiceMetrics(days = 7) {
    voiceMetricsLoading.value = true
    voiceMetricsError.value = null

    try {
      const response = await axios.get(`${VOICE_ASSISTANT_URL}/api/session/metrics`, {
        params: { days }
      })

      if (response.data.success) {
        voiceMetrics.value = response.data.metrics
        console.log('✅ Voice metrics loaded:', voiceMetrics.value)
      }
    } catch (err) {
      console.error('❌ Error loading voice metrics:', err)
      voiceMetricsError.value = err.message
    } finally {
      voiceMetricsLoading.value = false
    }
  }

  async function fetchDailySummary(date = null) {
    try {
      const params = date ? { date } : {}
      const response = await axios.get(`${VOICE_ASSISTANT_URL}/api/session/daily-summary`, { params })

      if (response.data.success) {
        return response.data.summary
      }
      return null
    } catch (err) {
      console.error('Error fetching daily summary:', err)
      return null
    }
  }

  // Computed para métricas de voz
  const voiceConversationsToday = computed(() => {
    const today = new Date().toISOString().split('T')[0]
    const todaySummary = voiceMetrics.value.daily_summaries?.find(s => s.date === today)
    return todaySummary?.conversations || 0
  })

  const voiceRevenueToday = computed(() => {
    const today = new Date().toISOString().split('T')[0]
    return voiceMetrics.value.daily_revenue?.[today] || 0
  })

  const upsellSuccessRate = computed(() => {
    return Math.round((voiceMetrics.value.upsell_success_rate || 0) * 100)
  })

  const crosssellSuccessRate = computed(() => {
    return Math.round((voiceMetrics.value.crosssell_success_rate || 0) * 100)
  })

  const avgSentiment = computed(() => {
    return Math.round((voiceMetrics.value.avg_sentiment || 0.5) * 100)
  })

  const avgConversationDuration = computed(() => {
    return (voiceMetrics.value.avg_conversation_duration || 0).toFixed(1)
  })

  const voiceHourlyDistribution = computed(() => {
    const dist = voiceMetrics.value.hourly_distribution || {}
    return Object.entries(dist)
      .map(([hour, count]) => ({
        hour: `${hour.padStart(2, '0')}:00`,
        conversations: count
      }))
      .sort((a, b) => a.hour.localeCompare(b.hour))
  })

  const voiceTopIntents = computed(() => {
    const intents = voiceMetrics.value.intents_summary || {}
    return Object.entries(intents)
      .map(([intent, count]) => ({ intent, count }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 8)
  })

  const voiceTopProducts = computed(() => {
    const products = voiceMetrics.value.top_products || {}
    return Object.entries(products)
      .map(([name, count]) => ({ name, count }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 5)
  })

  const dailyTrend = computed(() => {
    return (voiceMetrics.value.daily_summaries || [])
      .map(s => ({
        date: s.date,
        conversations: s.conversations,
        revenue: s.revenue,
        sentiment: Math.round((s.avg_sentiment || 0.5) * 100)
      }))
      .sort((a, b) => a.date.localeCompare(b.date))
  })

  return {
    // Datos de pedidos (existente)
    orders,
    tables,
    products,
    loading,
    error,
    todaySales,
    activeOrders,
    tableOccupancy,
    averageTicket,
    topProducts,
    hourlyOrders,
    recentOrders,
    yesterdaySales,
    salesChange,
    soldOutProducts,
    todayOrdersCount,
    yesterdayOrdersCount,
    fetchAllData,
    fetchReports,

    // Métricas financieras (NUEVO)
    productProfitability,
    todayFoodCost,
    todayGrossMargin,
    topMarginProducts,
    lowMarginProducts,

    // Tendencias semanales (NUEVO)
    weeklyTrend,
    weeklySalesTotal,
    weeklyOrdersTotal,
    previousWeekSales,
    weeklyChange,
    bestDayOfWeek,

    // Rotación de productos (NUEVO)
    productRotationRate,
    productsNotSoldToday,

    // Métricas del asistente de voz (nuevo)
    voiceMetrics,
    voiceMetricsLoading,
    voiceMetricsError,
    voiceConversationsToday,
    voiceRevenueToday,
    upsellSuccessRate,
    crosssellSuccessRate,
    avgSentiment,
    avgConversationDuration,
    voiceHourlyDistribution,
    voiceTopIntents,
    voiceTopProducts,
    dailyTrend,
    fetchVoiceMetrics,
    fetchDailySummary
  }
})
