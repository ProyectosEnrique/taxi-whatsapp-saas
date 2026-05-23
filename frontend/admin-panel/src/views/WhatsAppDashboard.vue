<template>
  <div class="whatsapp-dashboard">
    <!-- Header -->
    <div class="page-header">
      <div>
        <h1>📱 Dashboard WhatsApp</h1>
        <p class="subtitle">Métricas y gestión del canal de WhatsApp</p>
      </div>
      <button @click="refreshData" class="btn-refresh" :disabled="loading">
        {{ loading ? '🔄 Cargando...' : '🔄 Actualizar' }}
      </button>
    </div>

    <!-- Loading State -->
    <div v-if="loading && !metrics" class="loading-container">
      <div class="spinner"></div>
      <p>Cargando datos de WhatsApp...</p>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="error-container">
      <p>❌ {{ error }}</p>
      <button @click="refreshData" class="btn-retry">Reintentar</button>
    </div>

    <!-- Main Content -->
    <div v-else class="dashboard-content">
      <!-- Métricas Principales -->
      <div class="metrics-grid">
        <div class="metric-card success">
          <div class="metric-icon">💬</div>
          <div class="metric-content">
            <div class="metric-value">{{ metrics?.total_conversations || 0 }}</div>
            <div class="metric-label">Conversaciones Totales</div>
            <div class="metric-detail">{{ metrics?.active_conversations || 0 }} activas ahora</div>
          </div>
        </div>

        <div class="metric-card warning">
          <div class="metric-icon">📋</div>
          <div class="metric-content">
            <div class="metric-value">{{ metrics?.total_orders || 0 }}</div>
            <div class="metric-label">Pedidos por WhatsApp</div>
            <div class="metric-detail">{{ formatCurrency(metrics?.total_revenue || 0) }} en ventas</div>
          </div>
        </div>

        <div class="metric-card info">
          <div class="metric-icon">📈</div>
          <div class="metric-content">
            <div class="metric-value">{{ metrics?.conversion_rate?.toFixed(1) || 0 }}%</div>
            <div class="metric-label">Tasa de Conversión</div>
            <div class="metric-detail">Mensajes → Pedidos</div>
          </div>
        </div>

        <div class="metric-card default">
          <div class="metric-icon">💰</div>
          <div class="metric-content">
            <div class="metric-value">{{ formatCurrency(metrics?.avg_order_value || 0) }}</div>
            <div class="metric-label">Ticket Promedio</div>
            <div class="metric-detail">Por pedido de WhatsApp</div>
          </div>
        </div>
      </div>

      <!-- Conversaciones Activas -->
      <div class="section-card">
        <div class="section-header">
          <h2>💬 Conversaciones Activas</h2>
          <span class="badge">{{ activeConversations.length }} activas</span>
        </div>

        <div v-if="activeConversations.length === 0" class="empty-state">
          <p>No hay conversaciones activas en este momento</p>
        </div>

        <div v-else class="conversations-list">
          <div
            v-for="conv in activeConversations"
            :key="conv.phone"
            class="conversation-item"
          >
            <div class="conv-avatar">👤</div>
            <div class="conv-info">
              <div class="conv-name">{{ conv.customer_name }}</div>
              <div class="conv-phone">{{ conv.phone }}</div>
              <div class="conv-message">{{ conv.last_message }}</div>
            </div>
            <div class="conv-meta">
              <span class="conv-state" :class="conv.state">{{ getStateLabel(conv.state) }}</span>
              <span class="conv-time">{{ formatTime(conv.last_activity) }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Campañas de Broadcast -->
      <div class="section-card">
        <div class="section-header">
          <h2>📢 Campañas de Broadcast</h2>
          <button @click="showNewCampaignModal = true" class="btn-primary">
            + Nueva Campaña
          </button>
        </div>

        <div v-if="campaigns.length === 0" class="empty-state">
          <p>No hay campañas de broadcast aún</p>
          <button @click="showNewCampaignModal = true" class="btn-secondary">
            Crear Primera Campaña
          </button>
        </div>

        <div v-else class="campaigns-list">
          <div
            v-for="campaign in campaigns"
            :key="campaign.campaign_id"
            class="campaign-item"
          >
            <div class="campaign-header">
              <div class="campaign-title">
                <span class="campaign-icon">🔥</span>
                <span>{{ campaign.promotion_name || 'Campaña Custom' }}</span>
              </div>
              <span class="campaign-time">{{ formatDate(campaign.created_at) }}</span>
            </div>

            <div class="campaign-stats">
              <div class="stat-item">
                <span class="stat-label">Enviados</span>
                <span class="stat-value">{{ campaign.total_sent }}</span>
              </div>
              <div class="stat-item">
                <span class="stat-label">Exitosos</span>
                <span class="stat-value success">{{ campaign.successful }}</span>
              </div>
              <div class="stat-item">
                <span class="stat-label">Fallidos</span>
                <span class="stat-value error">{{ campaign.failed }}</span>
              </div>
              <div class="stat-item">
                <span class="stat-label">Tasa Éxito</span>
                <span class="stat-value">{{ ((campaign.successful / campaign.total_sent) * 100).toFixed(1) }}%</span>
              </div>
            </div>

            <div class="campaign-segment">
              <span class="segment-badge">{{ getSegmentLabel(campaign.customer_segment) }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Top Productos por WhatsApp -->
      <div class="section-card">
        <div class="section-header">
          <h2>🏆 Top Productos por WhatsApp</h2>
        </div>

        <div v-if="!metrics?.top_products || metrics.top_products.length === 0" class="empty-state">
          <p>No hay datos de productos aún</p>
        </div>

        <div v-else class="top-products-chart">
          <div
            v-for="(product, index) in metrics.top_products"
            :key="index"
            class="product-bar-item"
          >
            <div class="product-rank">{{ index + 1 }}</div>
            <div class="product-info">
              <div class="product-name">{{ product.name }}</div>
              <div class="product-stats">
                {{ product.orders }} pedidos • {{ formatCurrency(product.revenue) }}
              </div>
            </div>
            <div class="product-bar-container">
              <div
                class="product-bar"
                :style="{ width: getBarWidth(product, metrics.top_products) + '%' }"
              ></div>
            </div>
          </div>
        </div>
      </div>

      <!-- Horas Pico -->
      <div class="section-card">
        <div class="section-header">
          <h2>⏰ Horarios Pico</h2>
        </div>

        <div v-if="!metrics?.peak_hours || metrics.peak_hours.length === 0" class="empty-state">
          <p>No hay datos de horarios aún</p>
        </div>

        <div v-else class="peak-hours">
          <div
            v-for="hour in metrics.peak_hours"
            :key="hour"
            class="hour-badge"
          >
            {{ hour }}:00
          </div>
          <p class="peak-hint">Mejores horarios para enviar broadcasts</p>
        </div>
      </div>
    </div>

    <!-- Modal Nueva Campaña -->
    <Transition name="modal">
      <div v-if="showNewCampaignModal" class="modal-overlay" @click="closeNewCampaignModal">
        <div class="modal-content" @click.stop>
          <div class="modal-header">
            <h2>📢 Nueva Campaña de Broadcast</h2>
            <button @click="closeNewCampaignModal" class="btn-close">✕</button>
          </div>

          <div class="modal-body">
            <div class="form-group">
              <label>Mensaje *</label>
              <textarea
                v-model="newCampaign.message"
                rows="4"
                placeholder="Escribe el mensaje que se enviará a los clientes..."
                required
              ></textarea>
              <span class="char-count">{{ newCampaign.message.length }} caracteres</span>
            </div>

            <div class="form-group">
              <label>Segmento de Clientes *</label>
              <select v-model="newCampaign.segment" @change="updateAudiencePreview">
                <option value="all">Todos los clientes</option>
                <option value="frequent">Clientes frecuentes (3+ órdenes)</option>
                <option value="inactive">Clientes inactivos (30+ días)</option>
                <option value="new">Clientes nuevos (1-2 órdenes)</option>
                <option value="vip">Clientes VIP (alto valor)</option>
              </select>
              <span class="audience-preview" v-if="audienceCount !== null">
                📊 Se enviará a aproximadamente {{ audienceCount }} clientes
              </span>
            </div>

            <div class="form-group">
              <label>
                <input type="checkbox" v-model="newCampaign.personalize" />
                Personalizar mensajes para cada cliente
              </label>
              <span class="hint">Incluye nombre y menciona productos favoritos</span>
            </div>
          </div>

          <div class="modal-footer">
            <button @click="closeNewCampaignModal" class="btn-secondary">Cancelar</button>
            <button
              @click="sendCampaign"
              class="btn-primary"
              :disabled="!newCampaign.message || sendingCampaign"
            >
              {{ sendingCampaign ? 'Enviando...' : '📤 Enviar Campaña' }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import axios from 'axios'

// State
const loading = ref(false)
const error = ref(null)
const metrics = ref(null)
const activeConversations = ref([])
const campaigns = ref([])
const showNewCampaignModal = ref(false)
const sendingCampaign = ref(false)
const audienceCount = ref(null)

const newCampaign = ref({
  message: '',
  segment: 'all',
  personalize: true
})

// API Base URL
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// Methods
const refreshData = async () => {
  loading.value = true
  error.value = null

  try {
    // Fetch WhatsApp metrics
    const [metricsRes, campaignsRes] = await Promise.all([
      axios.get(`${API_URL}/api/analytics/whatsapp/metrics`),
      axios.get(`${API_URL}/api/analytics/whatsapp/campaigns`)
    ])

    metrics.value = metricsRes.data
    campaigns.value = campaignsRes.data.campaigns || []

    // Mock active conversations (TODO: implementar endpoint real)
    activeConversations.value = [
      {
        phone: '+525551234567',
        customer_name: 'María García',
        last_message: 'Quiero 2 hamburguesas BBQ',
        state: 'confirming',
        last_activity: new Date()
      },
      {
        phone: '+525559876543',
        customer_name: 'Juan Pérez',
        last_message: '¿Tienen tacos al pastor?',
        state: 'browsing',
        last_activity: new Date(Date.now() - 5 * 60 * 1000)
      }
    ]
  } catch (err) {
    console.error('Error fetching WhatsApp data:', err)
    error.value = 'Error cargando datos de WhatsApp'

    // Usar datos mock en caso de error
    metrics.value = {
      total_conversations: 156,
      active_conversations: 18,
      total_orders: 25,
      total_revenue: 3250.0,
      avg_order_value: 130.0,
      conversion_rate: 16.0,
      top_products: [
        { name: 'Hamburguesa BBQ', orders: 15, revenue: 1125.0 },
        { name: 'Tacos al Pastor', orders: 12, revenue: 720.0 },
        { name: 'Cerveza', orders: 10, revenue: 300.0 }
      ],
      peak_hours: [13, 14, 19, 20, 21]
    }
  } finally {
    loading.value = false
  }
}

const updateAudiencePreview = async () => {
  try {
    const res = await axios.post(`${API_URL}/api/admin/whatsapp/preview-audience`, {
      segment: newCampaign.value.segment
    })
    audienceCount.value = res.data.count
  } catch (err) {
    console.error('Error getting audience preview:', err)
    // Mock count
    const mockCounts = {
      all: 156,
      frequent: 45,
      inactive: 28,
      new: 15,
      vip: 12
    }
    audienceCount.value = mockCounts[newCampaign.value.segment] || 0
  }
}

const sendCampaign = async () => {
  if (!newCampaign.value.message) {
    alert('Por favor escribe un mensaje')
    return
  }

  sendingCampaign.value = true

  try {
    const res = await axios.post(`${API_URL}/api/admin/whatsapp/broadcast`, {
      message: newCampaign.value.message,
      audience_filter: {
        segment: newCampaign.value.segment
      },
      personalize: newCampaign.value.personalize
    })

    alert(`✅ Campaña enviada exitosamente!\n\nEnviados: ${res.data.total_sent}\nExitosos: ${res.data.successful}`)

    // Refresh data
    await refreshData()

    // Close modal
    closeNewCampaignModal()
  } catch (err) {
    console.error('Error sending campaign:', err)
    alert('❌ Error enviando campaña. Intenta de nuevo.')
  } finally {
    sendingCampaign.value = false
  }
}

const closeNewCampaignModal = () => {
  showNewCampaignModal.value = false
  newCampaign.value = {
    message: '',
    segment: 'all',
    personalize: true
  }
  audienceCount.value = null
}

// Formatters
const formatCurrency = (value) => {
  return new Intl.NumberFormat('es-MX', {
    style: 'currency',
    currency: 'MXN'
  }).format(value)
}

const formatDate = (date) => {
  if (!date) return ''
  return new Date(date).toLocaleString('es-MX', {
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const formatTime = (date) => {
  if (!date) return ''
  const now = new Date()
  const diff = now - new Date(date)
  const minutes = Math.floor(diff / 60000)

  if (minutes < 1) return 'Justo ahora'
  if (minutes < 60) return `Hace ${minutes} min`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `Hace ${hours}h`
  return `Hace ${Math.floor(hours / 24)}d`
}

const getStateLabel = (state) => {
  const labels = {
    browsing: 'Navegando',
    confirming: 'Confirmando',
    ordering: 'Ordenando',
    completed: 'Completado'
  }
  return labels[state] || state
}

const getSegmentLabel = (segment) => {
  const labels = {
    all: 'Todos los clientes',
    frequent: 'Clientes frecuentes',
    inactive: 'Clientes inactivos',
    new: 'Clientes nuevos',
    vip: 'Clientes VIP'
  }
  return labels[segment] || segment
}

const getBarWidth = (product, allProducts) => {
  const maxOrders = Math.max(...allProducts.map(p => p.orders))
  return (product.orders / maxOrders) * 100
}

// Lifecycle
onMounted(() => {
  refreshData()
})
</script>

<style scoped>
.whatsapp-dashboard {
  padding: 2rem;
  background: #f5f5f5;
  min-height: 100vh;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 2rem;
}

.page-header h1 {
  font-size: 2rem;
  margin: 0;
  color: #25d366; /* WhatsApp green */
}

.subtitle {
  color: #666;
  margin-top: 0.5rem;
}

.btn-refresh {
  padding: 0.75rem 1.5rem;
  background: #25d366;
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 500;
}

.btn-refresh:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.loading-container, .error-container {
  text-align: center;
  padding: 3rem;
}

.spinner {
  border: 4px solid #f3f3f3;
  border-top: 4px solid #25d366;
  border-radius: 50%;
  width: 40px;
  height: 40px;
  animation: spin 1s linear infinite;
  margin: 0 auto 1rem;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

/* Metrics Grid */
.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1.5rem;
  margin-bottom: 2rem;
}

.metric-card {
  background: white;
  padding: 1.5rem;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  display: flex;
  align-items: center;
  gap: 1rem;
}

.metric-icon {
  font-size: 2.5rem;
}

.metric-content {
  flex: 1;
}

.metric-value {
  font-size: 2rem;
  font-weight: bold;
  margin-bottom: 0.25rem;
}

.metric-label {
  color: #666;
  font-size: 0.9rem;
  margin-bottom: 0.25rem;
}

.metric-detail {
  color: #999;
  font-size: 0.85rem;
}

.metric-card.success .metric-value { color: #27ae60; }
.metric-card.warning .metric-value { color: #f39c12; }
.metric-card.info .metric-value { color: #3498db; }

/* Section Card */
.section-card {
  background: white;
  padding: 1.5rem;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  margin-bottom: 1.5rem;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
  padding-bottom: 1rem;
  border-bottom: 2px solid #f0f0f0;
}

.section-header h2 {
  margin: 0;
  font-size: 1.3rem;
}

.badge {
  background: #25d366;
  color: white;
  padding: 0.25rem 0.75rem;
  border-radius: 12px;
  font-size: 0.85rem;
}

.empty-state {
  text-align: center;
  padding: 2rem;
  color: #999;
}

/* Conversations */
.conversations-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.conversation-item {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  transition: all 0.2s;
}

.conversation-item:hover {
  background: #f9f9f9;
  border-color: #25d366;
}

.conv-avatar {
  font-size: 2rem;
  width: 50px;
  height: 50px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #e8f5e9;
  border-radius: 50%;
}

.conv-info {
  flex: 1;
}

.conv-name {
  font-weight: bold;
  margin-bottom: 0.25rem;
}

.conv-phone {
  color: #666;
  font-size: 0.85rem;
  margin-bottom: 0.25rem;
}

.conv-message {
  color: #999;
  font-size: 0.9rem;
  font-style: italic;
}

.conv-meta {
  text-align: right;
}

.conv-state {
  display: inline-block;
  padding: 0.25rem 0.75rem;
  border-radius: 12px;
  font-size: 0.8rem;
  margin-bottom: 0.5rem;
}

.conv-state.browsing { background: #e3f2fd; color: #1976d2; }
.conv-state.confirming { background: #fff3e0; color: #f57c00; }
.conv-state.ordering { background: #e8f5e9; color: #388e3c; }

.conv-time {
  color: #999;
  font-size: 0.8rem;
}

/* Campaigns */
.campaigns-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.campaign-item {
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 1rem;
}

.campaign-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.campaign-title {
  font-weight: bold;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.campaign-stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1rem;
  margin-bottom: 1rem;
}

.stat-item {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.stat-label {
  font-size: 0.8rem;
  color: #666;
}

.stat-value {
  font-size: 1.2rem;
  font-weight: bold;
}

.stat-value.success { color: #27ae60; }
.stat-value.error { color: #e74c3c; }

.segment-badge {
  display: inline-block;
  padding: 0.25rem 0.75rem;
  background: #e8f5e9;
  color: #2e7d32;
  border-radius: 12px;
  font-size: 0.85rem;
}

/* Top Products */
.top-products-chart {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.product-bar-item {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.product-rank {
  font-size: 1.5rem;
  font-weight: bold;
  color: #25d366;
  width: 40px;
  text-align: center;
}

.product-info {
  flex: 0 0 200px;
}

.product-name {
  font-weight: 500;
  margin-bottom: 0.25rem;
}

.product-stats {
  font-size: 0.85rem;
  color: #666;
}

.product-bar-container {
  flex: 1;
  height: 30px;
  background: #f0f0f0;
  border-radius: 4px;
  position: relative;
}

.product-bar {
  height: 100%;
  background: linear-gradient(90deg, #25d366, #128c7e);
  border-radius: 4px;
  transition: width 0.3s ease;
}

/* Peak Hours */
.peak-hours {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  align-items: center;
}

.hour-badge {
  padding: 0.5rem 1rem;
  background: #e8f5e9;
  color: #2e7d32;
  border-radius: 8px;
  font-weight: 500;
}

.peak-hint {
  width: 100%;
  color: #666;
  font-size: 0.9rem;
  margin-top: 0.5rem;
  font-style: italic;
}

/* Buttons */
.btn-primary {
  padding: 0.75rem 1.5rem;
  background: #25d366;
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 500;
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-secondary {
  padding: 0.75rem 1.5rem;
  background: #f0f0f0;
  color: #333;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 500;
}

.btn-retry {
  padding: 0.75rem 1.5rem;
  background: #3498db;
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
}

/* Modal */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0,0,0,0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  border-radius: 12px;
  max-width: 600px;
  width: 90%;
  max-height: 90vh;
  overflow-y: auto;
}

.modal-header {
  padding: 1.5rem;
  border-bottom: 1px solid #e0e0e0;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.modal-header h2 {
  margin: 0;
}

.btn-close {
  background: none;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  color: #999;
}

.modal-body {
  padding: 1.5rem;
}

.form-group {
  margin-bottom: 1.5rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 500;
}

.form-group textarea,
.form-group select {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  font-family: inherit;
}

.char-count,
.audience-preview,
.hint {
  display: block;
  margin-top: 0.5rem;
  font-size: 0.85rem;
  color: #666;
}

.audience-preview {
  color: #25d366;
  font-weight: 500;
}

.modal-footer {
  padding: 1.5rem;
  border-top: 1px solid #e0e0e0;
  display: flex;
  justify-content: flex-end;
  gap: 1rem;
}

/* Modal Transitions */
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.3s;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}
</style>
