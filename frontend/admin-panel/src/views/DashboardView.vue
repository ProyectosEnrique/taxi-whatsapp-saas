<template>
  <div class="dashboard">
    <!-- Header -->
    <div class="dashboard-header">
      <h1>📊 Dashboard Administrativo</h1>
      <p class="subtitle">Vista general del negocio en tiempo real</p>
      <button @click="refreshData" class="btn-refresh" :disabled="loading">
        {{ loading ? '🔄 Cargando...' : '🔄 Actualizar' }}
      </button>
    </div>

    <!-- Loading State -->
    <div v-if="loading && !analyticsStore.orders.length" class="loading-container">
      <div class="spinner"></div>
      <p>Cargando datos...</p>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="error-container">
      <p>❌ {{ error }}</p>
      <button @click="refreshData" class="btn-retry">Reintentar</button>
    </div>

    <!-- Main Content -->
    <div v-else class="dashboard-content">
      <!-- Metrics Cards - Fila Principal -->
      <div class="metrics-grid">
        <MetricsCard
          label="Ventas del Día"
          :value="analyticsStore.todaySales"
          icon="💰"
          variant="success"
          format="currency"
          :subtitle="salesComparisonText"
          :trend="analyticsStore.salesChange"
        />
        <MetricsCard
          label="Pedidos Hoy"
          :value="analyticsStore.todayOrdersCount"
          icon="📋"
          variant="warning"
          format="number"
          :subtitle="`Ayer: ${analyticsStore.yesterdayOrdersCount} pedidos`"
        />
        <MetricsCard
          label="Ocupación de Mesas"
          :value="analyticsStore.tableOccupancy"
          icon="🪑"
          variant="info"
          format="percent"
          subtitle="Mesas ocupadas"
        />
        <MetricsCard
          label="Ticket Promedio"
          :value="analyticsStore.averageTicket"
          icon="🧾"
          variant="default"
          format="currency"
          subtitle="Promedio por orden"
        />
      </div>

      <!-- Métricas Financieras - NUEVO -->
      <div class="metrics-grid financial-metrics">
        <MetricsCard
          label="Food Cost"
          :value="analyticsStore.todayFoodCost"
          icon="🍴"
          :variant="analyticsStore.todayFoodCost <= 35 ? 'success' : analyticsStore.todayFoodCost <= 40 ? 'warning' : 'danger'"
          format="percent"
          subtitle="Costo de alimentos hoy"
        />
        <MetricsCard
          label="Margen Bruto"
          :value="analyticsStore.todayGrossMargin"
          icon="💵"
          :variant="analyticsStore.todayGrossMargin >= 60 ? 'success' : analyticsStore.todayGrossMargin >= 50 ? 'warning' : 'danger'"
          format="percent"
          subtitle="Margen de ganancia"
        />
        <MetricsCard
          label="Rotación Productos"
          :value="analyticsStore.productRotationRate"
          icon="🔄"
          :variant="analyticsStore.productRotationRate >= 60 ? 'success' : analyticsStore.productRotationRate >= 40 ? 'warning' : 'info'"
          format="percent"
          :subtitle="`${analyticsStore.productsNotSoldToday.length} sin ventas hoy`"
        />
        <MetricsCard
          label="Ventas Semana"
          :value="analyticsStore.weeklySalesTotal"
          icon="📅"
          variant="info"
          format="currency"
          :subtitle="weeklyComparisonText"
          :trend="analyticsStore.weeklyChange"
        />
      </div>

      <!-- Gauge de Satisfacción + Tendencia Semanal -->
      <div class="sentiment-weekly-section">
        <SentimentGauge
          title="Satisfacción del Cliente"
          :value="analyticsStore.avgSentiment"
          description="Basado en análisis de conversaciones de voz"
        />

        <div class="weekly-trend-card">
          <h3>📈 Tendencia Semanal</h3>
          <div class="weekly-chart">
            <div
              v-for="day in analyticsStore.weeklyTrend"
              :key="day.date"
              class="week-day-bar"
            >
              <div
                class="bar-fill"
                :style="{ height: getBarHeight(day.sales) + '%' }"
                :class="{ 'best-day': isBestDay(day) }"
              ></div>
              <span class="day-label">{{ day.dayName }}</span>
              <span class="day-value">${{ formatNumber(day.sales) }}</span>
            </div>
          </div>
          <div v-if="analyticsStore.bestDayOfWeek" class="best-day-info">
            🏆 Mejor día: <strong>{{ analyticsStore.bestDayOfWeek.dayName }}</strong>
            (${{ formatNumber(analyticsStore.bestDayOfWeek.sales) }})
          </div>
        </div>
      </div>

      <!-- Alerta de productos agotados -->
      <div v-if="analyticsStore.soldOutProducts.length > 0" class="sold-out-alert">
        <div class="alert-header">
          <span class="alert-icon">⚠️</span>
          <span class="alert-title">Productos Agotados ({{ analyticsStore.soldOutProducts.length }})</span>
        </div>
        <div class="sold-out-list">
          <span v-for="product in analyticsStore.soldOutProducts" :key="product.id" class="sold-out-item">
            {{ product.name }}
          </span>
        </div>
      </div>

      <!-- Charts Section -->
      <div class="charts-section">
        <div class="chart-wrapper">
          <HourlyOrdersChart
            title="📈 Pedidos por Hora - Hoy"
            :data="hourlyChartData"
          />
        </div>
        <div class="chart-wrapper">
          <TopProductsList
            title="🏆 Top 10 Productos Más Vendidos"
            :products="analyticsStore.topProducts"
          />
        </div>
      </div>

      <!-- Voice Assistant Metrics Section -->
      <VoiceAssistantMetrics />

      <!-- Recent Orders -->
      <div class="recent-section">
        <RecentOrdersList
          title="🕐 Órdenes Recientes"
          :orders="analyticsStore.recentOrders"
        />
      </div>

      <!-- Quick Actions -->
      <div class="actions-section">
        <h3>⚡ Acciones Rápidas</h3>
        <div class="actions-grid">
          <button @click="viewReports" class="action-btn">
            📊 Ver Reportes
          </button>
          <button @click="manageMenu" class="action-btn">
            🍽️ Gestionar Menú
          </button>
          <button @click="manageTables" class="action-btn">
            🪑 Gestionar Mesas
          </button>
          <button @click="manageUsers" class="action-btn">
            👥 Gestionar Usuarios
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAnalyticsStore } from '../stores/analytics'
import MetricsCard from '../components/MetricsCard.vue'
import HourlyOrdersChart from '../components/HourlyOrdersChart.vue'
import TopProductsList from '../components/TopProductsList.vue'
import RecentOrdersList from '../components/RecentOrdersList.vue'
import VoiceAssistantMetrics from '../components/VoiceAssistantMetrics.vue'
import SentimentGauge from '../components/SentimentGauge.vue'

const router = useRouter()
const analyticsStore = useAnalyticsStore()

const loading = ref(false)
const error = ref(null)

const hourlyChartData = computed(() => {
  return analyticsStore.hourlyOrders.map(item => ({
    label: item.hour,
    value: item.orders
  }))
})

const salesComparisonText = computed(() => {
  const change = analyticsStore.salesChange
  const yesterday = analyticsStore.yesterdaySales
  if (change > 0) return `+${change}% vs ayer ($${yesterday.toFixed(0)})`
  if (change < 0) return `${change}% vs ayer ($${yesterday.toFixed(0)})`
  return `Sin cambio vs ayer ($${yesterday.toFixed(0)})`
})

const weeklyComparisonText = computed(() => {
  const change = analyticsStore.weeklyChange
  if (change > 0) return `+${change}% vs semana anterior`
  if (change < 0) return `${change}% vs semana anterior`
  return 'Sin cambio vs semana anterior'
})

function formatNumber(num) {
  if (num >= 1000) {
    return (num / 1000).toFixed(1) + 'k'
  }
  return Math.round(num).toString()
}

function getBarHeight(sales) {
  const maxSales = Math.max(...analyticsStore.weeklyTrend.map(d => d.sales))
  if (maxSales === 0) return 0
  return Math.round((sales / maxSales) * 100)
}

function isBestDay(day) {
  const best = analyticsStore.bestDayOfWeek
  return best && day.date === best.date
}

async function refreshData() {
  loading.value = true
  error.value = null

  try {
    // Cargar datos principales primero (más rápido)
    await analyticsStore.fetchAllData()

    // Cargar métricas de voz después (lazy loading)
    // No bloquea la renderización del dashboard principal
    analyticsStore.fetchVoiceMetrics(7).catch(err => {
      console.warn('Voice metrics failed to load:', err.message)
    })
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

function viewReports() {
  alert('Funcionalidad de reportes - En desarrollo')
}

function manageMenu() {
  router.push('/menu')
}

function manageTables() {
  router.push('/tables')
}

function manageUsers() {
  router.push('/users')
}

onMounted(() => {
  refreshData()

  // Auto-refresh every 60 seconds
  setInterval(() => {
    if (!loading.value) {
      refreshData()
    }
  }, 60000)
})
</script>

<style scoped>
.dashboard {
  min-height: 100vh;
}

/* Header */
.dashboard-header {
  background: linear-gradient(135deg, #34495e 0%, #2c3e50 100%);
  color: white;
  padding: 2rem;
  border-radius: 12px;
  margin-bottom: 2rem;
  position: relative;
}

.dashboard-header h1 {
  margin: 0 0 0.5rem 0;
  font-size: 2rem;
}

.subtitle {
  margin: 0;
  opacity: 0.9;
  font-size: 1rem;
}

.btn-refresh {
  position: absolute;
  top: 2rem;
  right: 2rem;
  padding: 0.75rem 1.5rem;
  background: rgba(255, 255, 255, 0.2);
  color: white;
  border: 2px solid white;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 600;
  transition: all 0.3s;
}

.btn-refresh:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.3);
  transform: translateY(-2px);
}

.btn-refresh:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* Loading */
.loading-container {
  text-align: center;
  padding: 4rem 2rem;
}

.spinner {
  width: 50px;
  height: 50px;
  margin: 0 auto 1rem;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #34495e;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

/* Error */
.error-container {
  text-align: center;
  padding: 2rem;
  background: #fadbd8;
  border-radius: 8px;
  color: #e74c3c;
}

.btn-retry {
  margin-top: 1rem;
  padding: 0.75rem 1.5rem;
  background: #e74c3c;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 600;
}

/* Metrics Grid */
.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1.5rem;
  margin-bottom: 2rem;
}

.financial-metrics {
  background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
  padding: 1.5rem;
  border-radius: 12px;
  margin-bottom: 2rem;
}

/* Sentiment + Weekly Section */
.sentiment-weekly-section {
  display: grid;
  grid-template-columns: 1fr 2fr;
  gap: 1.5rem;
  margin-bottom: 2rem;
}

.weekly-trend-card {
  background: white;
  padding: 1.5rem;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.weekly-trend-card h3 {
  margin: 0 0 1rem 0;
  color: #2c3e50;
}

.weekly-chart {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  height: 150px;
  padding: 0 0.5rem;
  gap: 0.5rem;
}

.week-day-bar {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  height: 100%;
}

.bar-fill {
  width: 100%;
  max-width: 40px;
  background: linear-gradient(180deg, #3498db 0%, #2980b9 100%);
  border-radius: 4px 4px 0 0;
  transition: height 0.3s ease;
  margin-top: auto;
}

.bar-fill.best-day {
  background: linear-gradient(180deg, #27ae60 0%, #1e8449 100%);
}

.day-label {
  font-size: 0.75rem;
  color: #7f8c8d;
  margin-top: 0.5rem;
}

.day-value {
  font-size: 0.7rem;
  color: #95a5a6;
}

.best-day-info {
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid #eee;
  font-size: 0.9rem;
  color: #7f8c8d;
  text-align: center;
}

.best-day-info strong {
  color: #27ae60;
}

/* Alerta de productos agotados */
.sold-out-alert {
  background: linear-gradient(135deg, #fff3cd 0%, #ffeeba 100%);
  border: 2px solid #f39c12;
  border-radius: 12px;
  padding: 1rem 1.5rem;
  margin-bottom: 2rem;
}

.alert-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
}

.alert-icon {
  font-size: 1.5rem;
}

.alert-title {
  font-weight: 700;
  color: #856404;
  font-size: 1.1rem;
}

.sold-out-list {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.sold-out-item {
  background: #e74c3c;
  color: white;
  padding: 0.3rem 0.75rem;
  border-radius: 15px;
  font-size: 0.9rem;
  font-weight: 600;
}

/* Charts Section */
.charts-section {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
  gap: 1.5rem;
  margin-bottom: 2rem;
}

.chart-wrapper {
  min-height: 300px;
}

/* Recent Section */
.recent-section {
  margin-bottom: 2rem;
}

/* Actions Section */
.actions-section {
  background: white;
  padding: 1.5rem;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.actions-section h3 {
  margin: 0 0 1rem 0;
  color: #2c3e50;
}

.actions-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
}

.action-btn {
  padding: 1rem;
  background: linear-gradient(135deg, #3498db 0%, #2980b9 100%);
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 600;
  font-size: 1rem;
  transition: all 0.3s;
}

.action-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(52, 152, 219, 0.3);
}

@media (max-width: 768px) {
  .dashboard-header h1 {
    font-size: 1.5rem;
  }

  .btn-refresh {
    position: static;
    margin-top: 1rem;
    width: 100%;
  }

  .metrics-grid {
    grid-template-columns: 1fr;
  }

  .sentiment-weekly-section {
    grid-template-columns: 1fr;
  }

  .charts-section {
    grid-template-columns: 1fr;
  }

  .financial-metrics {
    padding: 1rem;
  }
}
</style>
