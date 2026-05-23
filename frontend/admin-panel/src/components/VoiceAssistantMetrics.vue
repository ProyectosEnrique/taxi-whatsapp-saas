<template>
  <div class="voice-metrics-section">
    <div class="section-header">
      <h2>🎙️ Métricas del Asistente de Voz</h2>
      <div class="header-actions">
        <select v-model="selectedDays" @change="loadMetrics" class="days-selector">
          <option :value="1">Hoy</option>
          <option :value="7">Últimos 7 días</option>
          <option :value="14">Últimos 14 días</option>
          <option :value="30">Últimos 30 días</option>
        </select>
        <button @click="loadMetrics" class="btn-refresh" :disabled="loading">
          {{ loading ? '⏳' : '🔄' }}
        </button>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading && !hasData" class="loading-state">
      <div class="spinner-small"></div>
      <span>Cargando métricas...</span>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="error-state">
      <span>⚠️ {{ error }}</span>
      <button @click="loadMetrics" class="btn-retry-small">Reintentar</button>
    </div>

    <!-- Metrics Content -->
    <div v-else class="metrics-content">
      <!-- KPI Cards -->
      <div class="voice-metrics-grid">
        <MetricsCard
          label="Conversaciones (Hoy)"
          :value="analyticsStore.voiceConversationsToday"
          icon="💬"
          variant="info"
          format="number"
          :subtitle="`Total período: ${analyticsStore.voiceMetrics.total_conversations}`"
        />
        <MetricsCard
          label="Ingresos por Voz (Hoy)"
          :value="analyticsStore.voiceRevenueToday"
          icon="💵"
          variant="success"
          format="currency"
          :subtitle="`Total período: $${totalRevenue}`"
        />
        <MetricsCard
          label="Tasa de Upsell"
          :value="analyticsStore.upsellSuccessRate"
          icon="📈"
          :variant="upsellVariant"
          format="percent"
          subtitle="Ventas adicionales aceptadas"
        />
        <MetricsCard
          label="Tasa de Cross-sell"
          :value="analyticsStore.crosssellSuccessRate"
          icon="🔗"
          :variant="crosssellVariant"
          format="percent"
          subtitle="Ventas cruzadas aceptadas"
        />
        <MetricsCard
          label="Satisfacción del Cliente"
          :value="analyticsStore.avgSentiment"
          icon="😊"
          :variant="sentimentVariant"
          format="percent"
          subtitle="Análisis de sentimiento"
        />
        <MetricsCard
          label="Duración Promedio"
          :value="avgDurationFormatted"
          icon="⏱️"
          variant="default"
          format="number"
          subtitle="minutos por conversación"
        />
      </div>

      <!-- Charts Row -->
      <div class="voice-charts-grid">
        <!-- Hourly Distribution -->
        <div class="chart-card">
          <h3>📊 Distribución por Hora</h3>
          <div class="simple-chart">
            <div
              v-for="(item, index) in hourlyDistribution"
              :key="index"
              class="chart-bar-wrapper"
              :title="`${item.hour}: ${item.conversations} conversaciones`"
            >
              <div
                class="chart-bar"
                :style="{ height: `${getBarHeight(item.conversations, maxHourly)}%` }"
              >
                <span v-if="item.conversations > 0" class="bar-value">{{ item.conversations }}</span>
              </div>
              <span class="bar-label">{{ item.hour.split(':')[0] }}</span>
            </div>
          </div>
        </div>

        <!-- Top Intents -->
        <div class="chart-card">
          <h3>🎯 Intenciones Más Frecuentes</h3>
          <div class="intents-list">
            <div
              v-for="(intent, index) in analyticsStore.voiceTopIntents"
              :key="index"
              class="intent-item"
            >
              <div class="intent-info">
                <span class="intent-rank">{{ index + 1 }}</span>
                <span class="intent-name">{{ formatIntentName(intent.intent) }}</span>
              </div>
              <div class="intent-bar-container">
                <div
                  class="intent-bar"
                  :style="{ width: `${getBarWidth(intent.count, maxIntentCount)}%` }"
                ></div>
                <span class="intent-count">{{ intent.count }}</span>
              </div>
            </div>
            <div v-if="analyticsStore.voiceTopIntents.length === 0" class="no-data">
              Sin datos de intenciones
            </div>
          </div>
        </div>
      </div>

      <!-- Top Products from Voice -->
      <div class="chart-card full-width">
        <h3>🏆 Productos Más Pedidos por Voz</h3>
        <div class="products-grid">
          <div
            v-for="(product, index) in analyticsStore.voiceTopProducts"
            :key="index"
            class="product-badge"
          >
            <span class="product-rank">{{ index + 1 }}</span>
            <span class="product-name">{{ product.name }}</span>
            <span class="product-count">{{ product.count }} pedidos</span>
          </div>
          <div v-if="analyticsStore.voiceTopProducts.length === 0" class="no-data">
            Sin datos de productos
          </div>
        </div>
      </div>

      <!-- Daily Trend -->
      <div class="chart-card full-width">
        <h3>📅 Tendencia Diaria</h3>
        <div class="trend-chart">
          <div
            v-for="(day, index) in analyticsStore.dailyTrend"
            :key="index"
            class="trend-day"
          >
            <div class="trend-bars">
              <div
                class="trend-bar conversations"
                :style="{ height: `${getBarHeight(day.conversations, maxTrendConversations)}%` }"
                :title="`${day.conversations} conversaciones`"
              ></div>
            </div>
            <div class="trend-info">
              <span class="trend-date">{{ formatDate(day.date) }}</span>
              <span class="trend-revenue">${{ day.revenue?.toFixed(0) || 0 }}</span>
            </div>
          </div>
          <div v-if="analyticsStore.dailyTrend.length === 0" class="no-data">
            Sin datos de tendencia
          </div>
        </div>
        <div class="trend-legend">
          <span class="legend-item"><span class="legend-color conversations"></span> Conversaciones</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useAnalyticsStore } from '../stores/analytics'
import MetricsCard from './MetricsCard.vue'

const analyticsStore = useAnalyticsStore()

const selectedDays = ref(7)
const loading = ref(false)
const error = ref(null)

const hasData = computed(() => {
  return analyticsStore.voiceMetrics.total_conversations > 0
})

const totalRevenue = computed(() => {
  return (analyticsStore.voiceMetrics.total_revenue || 0).toFixed(2)
})

const avgDurationFormatted = computed(() => {
  return analyticsStore.avgConversationDuration
})

// Variants based on performance
const upsellVariant = computed(() => {
  const rate = analyticsStore.upsellSuccessRate
  if (rate >= 30) return 'success'
  if (rate >= 15) return 'warning'
  return 'default'
})

const crosssellVariant = computed(() => {
  const rate = analyticsStore.crosssellSuccessRate
  if (rate >= 25) return 'success'
  if (rate >= 10) return 'warning'
  return 'default'
})

const sentimentVariant = computed(() => {
  const sentiment = analyticsStore.avgSentiment
  if (sentiment >= 70) return 'success'
  if (sentiment >= 50) return 'warning'
  return 'danger'
})

// Chart data helpers
const hourlyDistribution = computed(() => {
  return analyticsStore.voiceHourlyDistribution
})

const maxHourly = computed(() => {
  const values = hourlyDistribution.value.map(h => h.conversations)
  return Math.max(...values, 1)
})

const maxIntentCount = computed(() => {
  const values = analyticsStore.voiceTopIntents.map(i => i.count)
  return Math.max(...values, 1)
})

const maxTrendConversations = computed(() => {
  const values = analyticsStore.dailyTrend.map(d => d.conversations)
  return Math.max(...values, 1)
})

function getBarHeight(value, max) {
  if (max === 0) return 0
  return Math.max((value / max) * 100, value > 0 ? 5 : 0)
}

function getBarWidth(value, max) {
  if (max === 0) return 0
  return Math.max((value / max) * 100, value > 0 ? 5 : 0)
}

function formatIntentName(intent) {
  // Convertir snake_case a Title Case
  return intent
    .replace(/_/g, ' ')
    .replace(/\b\w/g, l => l.toUpperCase())
}

function formatDate(dateStr) {
  const date = new Date(dateStr)
  return date.toLocaleDateString('es-MX', { weekday: 'short', day: 'numeric' })
}

async function loadMetrics() {
  loading.value = true
  error.value = null

  try {
    await analyticsStore.fetchVoiceMetrics(selectedDays.value)
  } catch (err) {
    error.value = err.message || 'Error al cargar métricas'
  } finally {
    loading.value = false
  }
}

// No llamar loadMetrics en onMounted - DashboardView ya lo hace
// Solo se recarga cuando el usuario cambia el selector de días
</script>

<style scoped>
.voice-metrics-section {
  margin: 2rem 0;
  padding: 1.5rem;
  background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
  border-radius: 16px;
  border: 2px solid #dee2e6;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
  flex-wrap: wrap;
  gap: 1rem;
}

.section-header h2 {
  margin: 0;
  color: #2c3e50;
  font-size: 1.5rem;
}

.header-actions {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

.days-selector {
  padding: 0.5rem 1rem;
  border: 2px solid #3498db;
  border-radius: 8px;
  background: white;
  color: #2c3e50;
  font-weight: 500;
  cursor: pointer;
}

.btn-refresh {
  padding: 0.5rem 0.75rem;
  background: #3498db;
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 1.1rem;
  transition: all 0.3s;
}

.btn-refresh:hover:not(:disabled) {
  background: #2980b9;
  transform: scale(1.05);
}

.btn-refresh:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* Loading & Error States */
.loading-state,
.error-state {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  padding: 2rem;
  background: white;
  border-radius: 12px;
}

.spinner-small {
  width: 24px;
  height: 24px;
  border: 3px solid #f3f3f3;
  border-top: 3px solid #3498db;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.error-state {
  background: #fadbd8;
  color: #e74c3c;
}

.btn-retry-small {
  padding: 0.4rem 0.8rem;
  background: #e74c3c;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.85rem;
}

/* Metrics Grid */
.voice-metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 1rem;
  margin-bottom: 1.5rem;
}

/* Charts Grid */
.voice-charts-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
  gap: 1.5rem;
  margin-bottom: 1.5rem;
}

.chart-card {
  background: white;
  padding: 1.5rem;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.chart-card.full-width {
  grid-column: 1 / -1;
}

.chart-card h3 {
  margin: 0 0 1rem 0;
  color: #2c3e50;
  font-size: 1.1rem;
}

/* Simple Bar Chart */
.simple-chart {
  display: flex;
  align-items: flex-end;
  gap: 4px;
  height: 150px;
  padding-top: 20px;
}

.chart-bar-wrapper {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  height: 100%;
}

.chart-bar {
  width: 100%;
  max-width: 30px;
  background: linear-gradient(180deg, #3498db 0%, #2980b9 100%);
  border-radius: 4px 4px 0 0;
  position: relative;
  transition: all 0.3s;
  min-height: 2px;
}

.chart-bar:hover {
  opacity: 0.8;
}

.bar-value {
  position: absolute;
  top: -20px;
  left: 50%;
  transform: translateX(-50%);
  font-size: 0.7rem;
  font-weight: 600;
  color: #2c3e50;
}

.bar-label {
  font-size: 0.65rem;
  color: #7f8c8d;
  margin-top: 4px;
}

/* Intents List */
.intents-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.intent-item {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.intent-info {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  min-width: 140px;
}

.intent-rank {
  width: 24px;
  height: 24px;
  background: #3498db;
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.75rem;
  font-weight: bold;
}

.intent-name {
  font-size: 0.85rem;
  color: #2c3e50;
  font-weight: 500;
}

.intent-bar-container {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.intent-bar {
  height: 20px;
  background: linear-gradient(90deg, #27ae60 0%, #2ecc71 100%);
  border-radius: 4px;
  transition: width 0.3s;
}

.intent-count {
  font-size: 0.85rem;
  font-weight: 600;
  color: #2c3e50;
  min-width: 40px;
}

/* Products Grid */
.products-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
}

.product-badge {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  background: linear-gradient(135deg, #f39c12 0%, #e67e22 100%);
  color: white;
  border-radius: 20px;
  font-size: 0.9rem;
}

.product-rank {
  width: 22px;
  height: 22px;
  background: rgba(255, 255, 255, 0.3);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  font-size: 0.8rem;
}

.product-name {
  font-weight: 600;
}

.product-count {
  opacity: 0.9;
  font-size: 0.8rem;
}

/* Trend Chart */
.trend-chart {
  display: flex;
  gap: 8px;
  min-height: 180px;
  align-items: flex-end;
  overflow-x: auto;
  padding: 20px 0 0 0;
}

.trend-day {
  flex: 1;
  min-width: 60px;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.trend-bars {
  height: 120px;
  width: 100%;
  display: flex;
  justify-content: center;
  align-items: flex-end;
  gap: 2px;
}

.trend-bar {
  width: 20px;
  border-radius: 4px 4px 0 0;
  transition: height 0.3s;
  min-height: 2px;
}

.trend-bar.conversations {
  background: linear-gradient(180deg, #9b59b6 0%, #8e44ad 100%);
}

.trend-info {
  text-align: center;
  margin-top: 8px;
}

.trend-date {
  display: block;
  font-size: 0.75rem;
  color: #7f8c8d;
}

.trend-revenue {
  display: block;
  font-size: 0.8rem;
  font-weight: 600;
  color: #27ae60;
}

.trend-legend {
  display: flex;
  justify-content: center;
  gap: 1.5rem;
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid #eee;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.85rem;
  color: #7f8c8d;
}

.legend-color {
  width: 12px;
  height: 12px;
  border-radius: 2px;
}

.legend-color.conversations {
  background: #9b59b6;
}

/* No Data */
.no-data {
  text-align: center;
  padding: 2rem;
  color: #95a5a6;
  font-style: italic;
}

@media (max-width: 768px) {
  .section-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .voice-metrics-grid {
    grid-template-columns: 1fr;
  }

  .voice-charts-grid {
    grid-template-columns: 1fr;
  }

  .intent-info {
    min-width: 100px;
  }

  .intent-name {
    font-size: 0.75rem;
  }
}
</style>
