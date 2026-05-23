<template>
  <div class="admin-assistant" :class="{ expanded: isExpanded }">
    <!-- Proactive Notifications Badge -->
    <div v-if="!isExpanded && notifications.length > 0" class="notifications-badge">
      {{ notifications.length }}
    </div>

    <!-- Toggle Button -->
    <button
      v-if="!isExpanded"
      class="assistant-toggle"
      @click="toggleAssistant"
      :class="{ 'has-notification': hasUnreadMessages || notifications.length > 0 }"
    >
      <span class="toggle-icon">🎙️</span>
      <span class="toggle-text">Asistente</span>
    </button>

    <!-- Assistant Panel -->
    <div v-if="isExpanded" class="assistant-panel">
      <!-- Header -->
      <div class="panel-header">
        <div class="header-info">
          <span class="assistant-icon">🤖</span>
          <div class="header-text">
            <h3>Asistente Administrativo</h3>
            <span class="status" :class="connectionStatus">
              {{ connectionStatusText }}
            </span>
          </div>
        </div>
        <div class="header-actions">
          <button class="btn-icon" @click="clearChat" title="Limpiar chat">
            🗑️
          </button>
          <button class="btn-icon" @click="toggleAssistant" title="Minimizar">
            ➖
          </button>
        </div>
      </div>

      <!-- Proactive Notifications Panel -->
      <div v-if="notifications.length > 0" class="notifications-panel">
        <div class="notifications-header">
          <span>⚡ Alertas Importantes</span>
          <button class="btn-dismiss-all" @click="dismissAllNotifications">Descartar todas</button>
        </div>
        <div
          v-for="(notif, index) in notifications"
          :key="index"
          class="notification-item"
          :class="notif.type"
        >
          <span class="notif-icon">{{ getNotificationIcon(notif.type) }}</span>
          <div class="notif-content">
            <p class="notif-message">{{ notif.message }}</p>
            <button
              v-if="notif.action"
              class="notif-action-btn"
              @click="handleNotificationAction(notif)"
            >
              {{ notif.actionLabel }}
            </button>
          </div>
          <button class="btn-dismiss" @click="dismissNotification(index)">✕</button>
        </div>
      </div>

      <!-- Messages Container -->
      <div class="messages-container" ref="messagesContainer">
        <!-- Welcome Message -->
        <div v-if="messages.length === 0" class="welcome-message">
          <div class="welcome-icon">👋</div>
          <h4>Hola! Soy tu asistente</h4>
          <p>Puedo ayudarte con:</p>
          <ul>
            <li>📊 Consultar ventas y metricas</li>
            <li>🎉 Crear promociones</li>
            <li>🍽️ Gestionar disponibilidad y menu</li>
            <li>➕ Crear productos y categorias</li>
            <li>💰 Actualizar precios</li>
            <li>⚙️ Metricas de operaciones (food cost, margen)</li>
            <li>🎙️ Metricas del asistente de voz</li>
          </ul>
          <p class="hint">Escribe o usa el microfono para hablar</p>
        </div>

        <!-- Messages -->
        <div
          v-for="(message, index) in messages"
          :key="index"
          class="message"
          :class="message.role"
        >
          <div class="message-avatar">
            {{ message.role === 'user' ? '👤' : '🤖' }}
          </div>
          <div class="message-content">
            <div class="message-text" v-html="formatMessage(message.text)"></div>

            <!-- Visual Data Components -->
            <div v-if="message.visualData" class="message-visual">
              <!-- Sales Summary Card -->
              <div v-if="message.visualData.type === 'sales_summary'" class="visual-sales-summary">
                <div class="summary-grid">
                  <div class="summary-item">
                    <span class="summary-value">${{ formatNumber(message.visualData.data.total_sales) }}</span>
                    <span class="summary-label">Ventas</span>
                  </div>
                  <div class="summary-item">
                    <span class="summary-value">{{ message.visualData.data.order_count }}</span>
                    <span class="summary-label">Ordenes</span>
                  </div>
                  <div class="summary-item">
                    <span class="summary-value">${{ formatNumber(message.visualData.data.avg_ticket) }}</span>
                    <span class="summary-label">Ticket Prom.</span>
                  </div>
                </div>
              </div>

              <!-- Top Products Chart -->
              <div v-if="message.visualData.type === 'top_products_chart'" class="visual-top-products">
                <div
                  v-for="(product, i) in message.visualData.data.slice(0, 5)"
                  :key="i"
                  class="product-bar-item"
                >
                  <div class="product-info">
                    <span class="product-rank">{{ i + 1 }}</span>
                    <span class="product-name">{{ product.name }}</span>
                  </div>
                  <div class="product-bar-container">
                    <div
                      class="product-bar"
                      :style="{ width: `${getBarWidth(product.quantity, message.visualData.data)}%` }"
                    ></div>
                    <span class="product-qty">{{ product.quantity }}</span>
                  </div>
                </div>
              </div>

              <!-- Hourly Chart -->
              <div v-if="message.visualData.type === 'hourly_chart'" class="visual-hourly-chart">
                <div class="hourly-bars">
                  <div
                    v-for="(value, hour) in message.visualData.data"
                    :key="hour"
                    class="hourly-bar-wrapper"
                    :title="`${hour}: $${formatNumber(value)}`"
                  >
                    <div
                      class="hourly-bar"
                      :style="{ height: `${getHourlyBarHeight(value, message.visualData.data)}%` }"
                    ></div>
                    <span class="hourly-label">{{ hour.split(':')[0] }}</span>
                  </div>
                </div>
              </div>

              <!-- Daily Report -->
              <div v-if="message.visualData.type === 'daily_report'" class="visual-daily-report">
                <div class="report-header">Reporte del {{ message.visualData.data.date }}</div>
                <div class="report-grid">
                  <div class="report-item">
                    <span class="report-icon">💰</span>
                    <span class="report-value">${{ formatNumber(message.visualData.data.summary?.total_sales || 0) }}</span>
                    <span class="report-label">Ventas</span>
                  </div>
                  <div class="report-item">
                    <span class="report-icon">📋</span>
                    <span class="report-value">{{ message.visualData.data.summary?.order_count || 0 }}</span>
                    <span class="report-label">Ordenes</span>
                  </div>
                  <div class="report-item">
                    <span class="report-icon">🕐</span>
                    <span class="report-value">{{ message.visualData.data.peak_hour || '--' }}</span>
                    <span class="report-label">Hora Pico</span>
                  </div>
                </div>
              </div>

              <!-- Voice Metrics -->
              <div v-if="message.visualData.type === 'voice_metrics'" class="visual-voice-metrics">
                <div class="voice-metrics-grid">
                  <div class="vm-item">
                    <span class="vm-icon">💬</span>
                    <span class="vm-value">{{ message.visualData.data.total_conversations }}</span>
                    <span class="vm-label">Conversaciones</span>
                  </div>
                  <div class="vm-item">
                    <span class="vm-icon">📈</span>
                    <span class="vm-value">{{ Math.round((message.visualData.data.upsell_success_rate || 0) * 100) }}%</span>
                    <span class="vm-label">Upsell</span>
                  </div>
                  <div class="vm-item">
                    <span class="vm-icon">😊</span>
                    <span class="vm-value">{{ Math.round((message.visualData.data.avg_sentiment || 0.5) * 100) }}%</span>
                    <span class="vm-label">Satisfaccion</span>
                  </div>
                  <div class="vm-item">
                    <span class="vm-icon">💵</span>
                    <span class="vm-value">${{ formatNumber(message.visualData.data.total_revenue || 0) }}</span>
                    <span class="vm-label">Ingresos</span>
                  </div>
                </div>
              </div>
            </div>

            <div class="message-meta">
              <span class="message-time">{{ formatTime(message.timestamp) }}</span>
              <span v-if="message.intent" class="message-intent">{{ message.intent }}</span>
            </div>
          </div>
        </div>

        <!-- Typing Indicator -->
        <div v-if="isProcessing" class="message assistant typing">
          <div class="message-avatar">🤖</div>
          <div class="message-content">
            <div class="typing-indicator">
              <span></span>
              <span></span>
              <span></span>
            </div>
          </div>
        </div>

        <!-- Confirmation Dialog -->
        <div v-if="pendingConfirmation" class="confirmation-dialog">
          <p>{{ pendingConfirmation.message }}</p>
          <div class="confirmation-actions">
            <button class="btn-confirm" @click="confirmAction">
              ✓ Si, confirmar
            </button>
            <button class="btn-cancel" @click="cancelAction">
              ✗ No, cancelar
            </button>
          </div>
        </div>
      </div>

      <!-- Quick Actions - Now with categories -->
      <div class="quick-actions-container">
        <div class="quick-actions-tabs">
          <button
            v-for="category in actionCategories"
            :key="category.id"
            class="tab-btn"
            :class="{ active: activeCategory === category.id }"
            @click="activeCategory = category.id"
          >
            {{ category.icon }} {{ category.label }}
          </button>
        </div>
        <div class="quick-actions">
          <button
            v-for="action in filteredQuickActions"
            :key="action.id"
            class="quick-action-btn"
            @click="sendQuickAction(action.text)"
          >
            {{ action.icon }} {{ action.label }}
          </button>
        </div>
      </div>

      <!-- Input Area -->
      <div class="input-area">
        <div class="input-wrapper">
          <input
            ref="textInput"
            v-model="inputText"
            type="text"
            placeholder="Escribe tu mensaje..."
            @keyup.enter="sendMessage"
            :disabled="isProcessing || isRecording"
          />
          <button
            class="btn-send"
            @click="sendMessage"
            :disabled="!inputText.trim() || isProcessing"
          >
            ➤
          </button>
        </div>

        <!-- Voice Controls -->
        <div class="voice-controls">
          <button
            class="btn-voice"
            :class="{ recording: isRecording, processing: isTranscribing }"
            @click="toggleRecording"
            :disabled="isProcessing"
          >
            <span v-if="isRecording" class="pulse"></span>
            <span class="voice-icon">
              {{ isRecording ? '🔴' : isTranscribing ? '⏳' : '🎤' }}
            </span>
            <span class="voice-text">
              {{ isRecording ? 'Toca para enviar' : isTranscribing ? 'Procesando...' : 'Toca para hablar' }}
            </span>
          </button>

          <!-- Audio Feedback -->
          <div v-if="lastAudioResponse" class="audio-playback">
            <button class="btn-play" @click="playResponse">
              {{ isPlayingAudio ? '⏸️' : '🔊' }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { useAnalyticsStore } from '../stores/analytics'

const analyticsStore = useAnalyticsStore()

// Estado del panel
const isExpanded = ref(false)
const hasUnreadMessages = ref(false)

// Mensajes
const messages = ref([])
const inputText = ref('')
const isProcessing = ref(false)

// Confirmacion
const pendingConfirmation = ref(null)

// Grabacion de voz
const isRecording = ref(false)
const isTranscribing = ref(false)
const mediaRecorder = ref(null)
const audioChunks = ref([])

// Reproduccion de audio
const lastAudioResponse = ref(null)
const isPlayingAudio = ref(false)
const audioPlayer = ref(null)

// Conexion
const sessionId = ref(null)
const connectionStatus = ref('disconnected')

// Refs DOM
const messagesContainer = ref(null)
const textInput = ref(null)

// Notificaciones proactivas
const notifications = ref([])
const lastNotificationCheck = ref(null)

// Configuracion
const API_BASE_URL = import.meta.env.VITE_VOICE_ASSISTANT_URL || ''
const STORAGE_KEY = 'admin_assistant_history'
const NOTIFICATION_CHECK_INTERVAL = 60000 // 1 minuto

// Categorias de acciones
const activeCategory = ref('ventas')

const actionCategories = [
  { id: 'ventas', icon: '💰', label: 'Ventas' },
  { id: 'menu', icon: '🍽️', label: 'Menu' },
  { id: 'promos', icon: '🎉', label: 'Promos' },
  { id: 'operaciones', icon: '⚙️', label: 'Operaciones' },
  { id: 'voz', icon: '🎙️', label: 'Voz' }
]

// Acciones rapidas expandidas
const quickActions = ref([
  // Ventas
  { id: 'sales_today', icon: '💰', label: 'Ventas hoy', text: 'Cuanto vendimos hoy?', category: 'ventas' },
  { id: 'sales_yesterday', icon: '📅', label: 'Ventas ayer', text: 'Cuanto vendimos ayer?', category: 'ventas' },
  { id: 'sales_week', icon: '📊', label: 'Semana', text: 'Resumen de ventas de la semana', category: 'ventas' },
  { id: 'top_products', icon: '🏆', label: 'Top productos', text: 'Cuales son los productos mas vendidos?', category: 'ventas' },
  { id: 'orders_count', icon: '📋', label: 'Ordenes', text: 'Cuantas ordenes tenemos hoy?', category: 'ventas' },
  { id: 'hourly', icon: '🕐', label: 'Por hora', text: 'Ventas por hora de hoy', category: 'ventas' },
  { id: 'avg_ticket', icon: '🧾', label: 'Ticket prom.', text: 'Cual es el ticket promedio?', category: 'ventas' },
  { id: 'daily_report', icon: '📑', label: 'Reporte', text: 'Dame el reporte completo del dia', category: 'ventas' },

  // Menu
  { id: 'unavailable', icon: '❌', label: 'Agotados', text: 'Que productos estan agotados?', category: 'menu' },
  { id: 'toggle_available', icon: '✅', label: 'Disponible', text: 'Marcar producto como disponible', category: 'menu' },
  { id: 'toggle_unavailable', icon: '🚫', label: 'Agotar', text: 'Marcar producto como agotado', category: 'menu' },
  { id: 'update_price', icon: '💵', label: 'Cambiar precio', text: 'Actualizar precio de un producto', category: 'menu' },
  { id: 'create_product', icon: '➕', label: 'Crear producto', text: 'Quiero crear un nuevo producto', category: 'menu' },
  { id: 'create_category', icon: '📁', label: 'Crear categoria', text: 'Quiero crear una nueva categoria', category: 'menu' },
  { id: 'list_categories', icon: '📋', label: 'Categorias', text: 'Cuales son las categorias del menu?', category: 'menu' },

  // Promociones
  { id: 'list_promos', icon: '📋', label: 'Ver promos', text: 'Que promociones tenemos activas?', category: 'promos' },
  { id: 'create_2x1', icon: '🎁', label: 'Crear 2x1', text: 'Crear promocion 2x1', category: 'promos' },
  { id: 'create_discount', icon: '🏷️', label: 'Descuento %', text: 'Crear promocion con descuento porcentual', category: 'promos' },
  { id: 'toggle_promo', icon: '🔄', label: 'Activar/Desactivar', text: 'Activar o desactivar una promocion', category: 'promos' },

  // Operaciones (NUEVO)
  { id: 'food_cost', icon: '🍴', label: 'Food Cost', text: 'Cual es el food cost de hoy?', category: 'operaciones' },
  { id: 'margin', icon: '💵', label: 'Margen', text: 'Cual es el margen bruto?', category: 'operaciones' },
  { id: 'rotation', icon: '🔄', label: 'Rotacion', text: 'Como esta la rotacion de productos?', category: 'operaciones' },
  { id: 'weekly_trend', icon: '📈', label: 'Tendencia', text: 'Cual es la tendencia de ventas semanal?', category: 'operaciones' },
  { id: 'low_margin', icon: '⚠️', label: 'Bajo margen', text: 'Que productos tienen bajo margen?', category: 'operaciones' },
  { id: 'best_margin', icon: '🏆', label: 'Mejor margen', text: 'Que productos tienen mejor margen?', category: 'operaciones' },
  { id: 'products_not_sold', icon: '📭', label: 'Sin ventas', text: 'Que productos no se han vendido hoy?', category: 'operaciones' },
  { id: 'best_day', icon: '🗓️', label: 'Mejor dia', text: 'Cual fue el mejor dia de la semana?', category: 'operaciones' },

  // Voz
  { id: 'voice_metrics', icon: '📊', label: 'Metricas voz', text: 'Metricas del asistente de voz', category: 'voz' },
  { id: 'voice_today', icon: '💬', label: 'Hoy', text: 'Conversaciones de voz de hoy', category: 'voz' },
  { id: 'upsell_rate', icon: '📈', label: 'Upsell', text: 'Cual es la tasa de upsell?', category: 'voz' },
  { id: 'sentiment', icon: '😊', label: 'Satisfaccion', text: 'Como esta la satisfaccion del cliente?', category: 'voz' }
])

const filteredQuickActions = computed(() => {
  return quickActions.value.filter(a => a.category === activeCategory.value)
})

// Computed
const connectionStatusText = computed(() => {
  switch (connectionStatus.value) {
    case 'connected': return 'Conectado'
    case 'connecting': return 'Conectando...'
    case 'error': return 'Error de conexion'
    default: return 'Desconectado'
  }
})

// ============================================================
// PERSISTENCIA DEL HISTORIAL
// ============================================================

function saveHistoryToStorage() {
  try {
    const historyData = {
      messages: messages.value.map(m => ({
        ...m,
        timestamp: m.timestamp.toISOString()
      })),
      sessionId: sessionId.value,
      savedAt: new Date().toISOString()
    }
    localStorage.setItem(STORAGE_KEY, JSON.stringify(historyData))
  } catch (error) {
    console.error('Error saving chat history:', error)
  }
}

function loadHistoryFromStorage() {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved) {
      const data = JSON.parse(saved)

      // Solo cargar si fue guardado en las ultimas 24 horas
      const savedAt = new Date(data.savedAt)
      const now = new Date()
      const hoursSinceSave = (now - savedAt) / (1000 * 60 * 60)

      if (hoursSinceSave < 24 && data.messages?.length > 0) {
        messages.value = data.messages.map(m => ({
          ...m,
          timestamp: new Date(m.timestamp)
        }))

        if (data.sessionId) {
          sessionId.value = data.sessionId
        }

        console.log(`[AdminAssistant] Loaded ${messages.value.length} messages from storage`)
        return true
      }
    }
  } catch (error) {
    console.error('Error loading chat history:', error)
  }
  return false
}

// Watch para guardar cambios
watch(messages, () => {
  if (messages.value.length > 0) {
    saveHistoryToStorage()
  }
}, { deep: true })

// ============================================================
// NOTIFICACIONES PROACTIVAS
// ============================================================

async function checkProactiveNotifications() {
  try {
    // 1. Verificar productos agotados
    const unavailableProducts = analyticsStore.soldOutProducts
    if (unavailableProducts.length > 3) {
      addNotification({
        type: 'warning',
        message: `Hay ${unavailableProducts.length} productos agotados`,
        action: 'show_unavailable',
        actionLabel: 'Ver lista'
      })
    }

    // 2. Verificar ventas bajas (comparar con ayer)
    const salesChange = analyticsStore.salesChange
    if (salesChange < -20) {
      addNotification({
        type: 'alert',
        message: `Ventas ${Math.abs(salesChange)}% abajo vs ayer`,
        action: 'suggest_promo',
        actionLabel: 'Sugerir promo'
      })
    }

    // 3. Verificar metricas de voz
    await analyticsStore.fetchVoiceMetrics(1) // Solo hoy
    const sentiment = analyticsStore.avgSentiment
    if (sentiment < 50) {
      addNotification({
        type: 'alert',
        message: `Satisfaccion del cliente baja (${sentiment}%)`,
        action: 'show_sentiment',
        actionLabel: 'Ver detalles'
      })
    }

    // 4. Verificar hora pico cercana
    const currentHour = new Date().getHours()
    if ([12, 13, 19, 20].includes(currentHour)) {
      const pendingOrders = analyticsStore.activeOrders
      if (pendingOrders > 5) {
        addNotification({
          type: 'info',
          message: `Hora pico: ${pendingOrders} ordenes pendientes`,
          action: 'show_orders',
          actionLabel: 'Ver ordenes'
        })
      }
    }

    // NUEVO: 5. Verificar food cost alto
    const foodCost = analyticsStore.todayFoodCost
    if (foodCost > 40) {
      addNotification({
        type: 'alert',
        message: `Food cost alto (${foodCost}%) - Revisar costos`,
        action: 'show_food_cost',
        actionLabel: 'Ver detalles'
      })
    }

    // NUEVO: 6. Verificar productos con bajo margen vendidos hoy
    const lowMargin = analyticsStore.lowMarginProducts
    if (lowMargin.length > 2) {
      addNotification({
        type: 'warning',
        message: `${lowMargin.length} productos con margen bajo estan vendiendose`,
        action: 'show_low_margin',
        actionLabel: 'Ver productos'
      })
    }

    // NUEVO: 7. Prediccion: Si es dia de la semana tipicamente bueno
    const today = new Date()
    const dayOfWeek = today.getDay() // 0=Dom, 5=Vie, 6=Sab
    if ([5, 6].includes(dayOfWeek)) {
      const currentSales = analyticsStore.todaySales
      const bestDay = analyticsStore.bestDayOfWeek
      if (bestDay && currentSales < bestDay.sales * 0.5 && currentHour >= 14) {
        addNotification({
          type: 'info',
          message: `Fin de semana: Ventas por debajo del potencial`,
          action: 'suggest_weekend_promo',
          actionLabel: 'Sugerir promo'
        })
      }
    }

    // NUEVO: 8. Productos sin ventas (oportunidad)
    const notSold = analyticsStore.productsNotSoldToday
    if (notSold.length > 10 && currentHour >= 12) {
      addNotification({
        type: 'info',
        message: `${notSold.length} productos sin ventas hoy`,
        action: 'show_not_sold',
        actionLabel: 'Ver lista'
      })
    }

    // NUEVO: 9. Tendencia semanal negativa
    const weeklyChange = analyticsStore.weeklyChange
    if (weeklyChange < -15) {
      addNotification({
        type: 'alert',
        message: `Tendencia semanal negativa (${weeklyChange}%)`,
        action: 'show_weekly_trend',
        actionLabel: 'Ver tendencia'
      })
    }

    lastNotificationCheck.value = new Date()

  } catch (error) {
    console.error('Error checking proactive notifications:', error)
  }
}

function addNotification(notif) {
  // No duplicar notificaciones similares
  const exists = notifications.value.some(n =>
    n.message === notif.message || n.action === notif.action
  )

  if (!exists) {
    notifications.value.push({
      ...notif,
      id: Date.now(),
      timestamp: new Date()
    })
  }
}

function dismissNotification(index) {
  notifications.value.splice(index, 1)
}

function dismissAllNotifications() {
  notifications.value = []
}

function handleNotificationAction(notif) {
  switch (notif.action) {
    case 'show_unavailable':
      sendQuickAction('Que productos estan agotados?')
      break
    case 'suggest_promo':
      sendQuickAction('Sugiere una promocion para mejorar las ventas')
      break
    case 'show_sentiment':
      sendQuickAction('Dame detalles de la satisfaccion del cliente')
      break
    case 'show_orders':
      sendQuickAction('Cuantas ordenes pendientes hay?')
      break
    // NUEVOS handlers para alertas consolidadas
    case 'show_food_cost':
      sendQuickAction('Cual es el food cost de hoy?')
      break
    case 'show_low_margin':
      sendQuickAction('Que productos tienen bajo margen?')
      break
    case 'suggest_weekend_promo':
      sendQuickAction('Sugiere una promocion especial de fin de semana')
      break
    case 'show_not_sold':
      sendQuickAction('Que productos no se han vendido hoy?')
      break
    case 'show_weekly_trend':
      sendQuickAction('Cual es la tendencia de ventas semanal?')
      break

    default:
      break
  }
  dismissNotification(notifications.value.indexOf(notif))
}

function getNotificationIcon(type) {
  switch (type) {
    case 'warning': return '⚠️'
    case 'alert': return '🚨'
    case 'info': return 'ℹ️'
    case 'success': return '✅'
    default: return '📢'
  }
}

// ============================================================
// METODOS PRINCIPALES
// ============================================================

function toggleAssistant() {
  isExpanded.value = !isExpanded.value
  if (isExpanded.value) {
    hasUnreadMessages.value = false
    initSession()
    nextTick(() => {
      textInput.value?.focus()
      scrollToBottom()
    })
  }
}

async function initSession() {
  // Primero intentar cargar historial guardado
  const historyLoaded = loadHistoryFromStorage()

  if (sessionId.value && historyLoaded) {
    connectionStatus.value = 'connected'
    return
  }

  connectionStatus.value = 'connecting'
  try {
    const response = await fetch(`${API_BASE_URL}/api/admin/session`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    })

    if (response.ok) {
      const data = await response.json()
      sessionId.value = data.session_id
      connectionStatus.value = 'connected'
    } else {
      throw new Error('Failed to create session')
    }
  } catch (error) {
    console.error('Error creating session:', error)
    connectionStatus.value = 'error'
    // Usar session ID local como fallback
    sessionId.value = `local_${Date.now()}`
  }
}

async function sendMessage() {
  const text = inputText.value.trim()
  if (!text || isProcessing.value) return

  inputText.value = ''

  // Agregar mensaje del usuario
  addMessage('user', text)

  // Procesar mensaje
  await processMessage(text)
}

async function sendQuickAction(text) {
  if (isProcessing.value) return
  addMessage('user', text)
  await processMessage(text)
}

async function processMessage(text) {
  isProcessing.value = true

  try {
    const q = text.toLowerCase()

    // Detectar si es consulta de metricas de voz
    const isVoiceQuery = q.includes('voz') ||
                         q.includes('conversacion') ||
                         q.includes('upsell') ||
                         q.includes('satisfaccion') ||
                         q.includes('sentiment')

    if (isVoiceQuery) {
      // Obtener metricas de voz directamente
      await analyticsStore.fetchVoiceMetrics(7)

      const metrics = analyticsStore.voiceMetrics
      const responseText = formatVoiceMetricsResponse(metrics, text)

      addMessage('assistant', responseText, 'voice_metrics', {
        type: 'voice_metrics',
        data: metrics
      })

      isProcessing.value = false
      return
    }

    // Detectar consultas de operaciones/financieras (NUEVO)
    const isOperationsQuery = q.includes('food cost') ||
                              q.includes('margen') ||
                              q.includes('rotacion') ||
                              q.includes('tendencia') ||
                              q.includes('bajo margen') ||
                              q.includes('mejor margen') ||
                              q.includes('sin ventas') ||
                              q.includes('no se han vendido') ||
                              q.includes('mejor dia')

    if (isOperationsQuery) {
      const responseText = formatOperationsResponse(text)
      addMessage('assistant', responseText, 'operations_metrics', {
        type: 'operations_metrics',
        data: {
          foodCost: analyticsStore.todayFoodCost,
          margin: analyticsStore.todayGrossMargin,
          rotation: analyticsStore.productRotationRate,
          weeklyTrend: analyticsStore.weeklyTrend,
          bestDay: analyticsStore.bestDayOfWeek
        }
      })
      isProcessing.value = false
      return
    }

    // ================================================================
    // ESTRATEGIA 2: CONTEXT INJECTION - Recolectar contexto del dashboard
    // ================================================================
    const dashboardContext = collectDashboardContext()

    // Procesar con backend (enviando contexto del dashboard)
    const response = await fetch(`${API_BASE_URL}/api/admin/message`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId.value,
        message: text,
        voice_response: true,  // Habilitar respuesta de voz automática
        dashboard_context: dashboardContext  // NUEVO: Contexto inyectado
      })
    })

    if (response.ok) {
      const data = await response.json()

      // Verificar si requiere confirmacion
      if (data.requires_confirmation) {
        pendingConfirmation.value = {
          message: data.confirmation_message || data.text,
          action: data.pending_action
        }
        addMessage('assistant', data.text, data.intent)
      } else {
        addMessage('assistant', data.text, data.intent, data.visual_data)

        // NUEVO: Sincronizar dashboard cuando se detectan acciones de modificacion
        const modifyingIntents = [
          'toggle_availability', 'update_price', 'create_product',
          'create_category', 'create_promotion', 'toggle_promotion',
          'mark_unavailable', 'mark_available', 'update_menu'
        ]

        if (data.intent && modifyingIntents.includes(data.intent)) {
          console.log('[AdminAssistant] Accion de modificacion detectada, sincronizando dashboard...')
          setTimeout(() => {
            analyticsStore.fetchAllData()
          }, 500)
        }
      }

      // Guardar y reproducir audio automáticamente si existe
      if (data.audio_url) {
        lastAudioResponse.value = `${API_BASE_URL}${data.audio_url}`
        // Auto-play: Reproducir respuesta de voz automáticamente
        playResponse()
      }
    } else {
      throw new Error('Failed to process message')
    }
  } catch (error) {
    console.error('Error processing message:', error)
    addMessage('assistant', 'Disculpa, tuve un problema procesando tu solicitud. Por favor intenta de nuevo.', 'error')
  } finally {
    isProcessing.value = false
  }
}

function formatVoiceMetricsResponse(metrics, query) {
  const q = query.toLowerCase()

  if (q.includes('upsell')) {
    const rate = Math.round((metrics.upsell_success_rate || 0) * 100)
    return `La tasa de upsell es del ${rate}%. Esto significa que ${rate} de cada 100 clientes aceptaron productos adicionales sugeridos por el asistente de voz.`
  }

  if (q.includes('satisfaccion') || q.includes('sentiment')) {
    const sentiment = Math.round((metrics.avg_sentiment || 0.5) * 100)
    let evaluation = sentiment >= 70 ? 'excelente' : sentiment >= 50 ? 'buena' : 'necesita atencion'
    return `La satisfaccion del cliente es del ${sentiment}% (${evaluation}). Este indicador se calcula analizando el sentimiento de las conversaciones con el asistente de voz.`
  }

  if (q.includes('conversacion') || q.includes('hoy')) {
    const today = analyticsStore.voiceConversationsToday
    return `Hoy hemos tenido ${today} conversaciones con el asistente de voz. En total del periodo: ${metrics.total_conversations} conversaciones.`
  }

  // Respuesta general
  const total = metrics.total_conversations || 0
  const revenue = metrics.total_revenue || 0
  const upsell = Math.round((metrics.upsell_success_rate || 0) * 100)
  const sentiment = Math.round((metrics.avg_sentiment || 0.5) * 100)

  return `**Metricas del Asistente de Voz:**\n` +
         `- Total conversaciones: ${total}\n` +
         `- Ingresos generados: $${formatNumber(revenue)}\n` +
         `- Tasa de upsell: ${upsell}%\n` +
         `- Satisfaccion: ${sentiment}%`
}

// ================================================================
// ESTRATEGIA 2: CONTEXT INJECTION - Recolector de contexto del dashboard
// ================================================================
function collectDashboardContext() {
  /**
   * Recolecta el estado actual del dashboard para inyectarlo al LLM.
   * Esto permite que el asistente tenga conocimiento en tiempo real
   * de las metricas y pueda dar respuestas mas contextualizadas.
   */
  const now = new Date()
  const currentHour = now.getHours()
  const dayOfWeek = now.getDay() // 0=Dom, 6=Sab
  const isWeekend = [0, 6].includes(dayOfWeek)
  const isPeakHour = [12, 13, 14, 19, 20, 21].includes(currentHour)

  // Determinar momento del dia
  let dayPeriod = 'madrugada'
  if (currentHour >= 6 && currentHour < 12) dayPeriod = 'mañana'
  else if (currentHour >= 12 && currentHour < 15) dayPeriod = 'mediodia'
  else if (currentHour >= 15 && currentHour < 19) dayPeriod = 'tarde'
  else if (currentHour >= 19 && currentHour < 23) dayPeriod = 'noche'

  // Clasificar el estado de las metricas
  const foodCost = analyticsStore.todayFoodCost || 0
  const grossMargin = analyticsStore.todayGrossMargin || 0
  const weeklyChange = analyticsStore.weeklyChange || 0
  const salesChange = analyticsStore.salesChange || 0

  // Determinar alertas activas
  const activeAlerts = []

  if (foodCost > 40) {
    activeAlerts.push({
      type: 'critico',
      metric: 'food_cost',
      message: `Food cost critico: ${foodCost}% (deberia ser <35%)`
    })
  } else if (foodCost > 35) {
    activeAlerts.push({
      type: 'advertencia',
      metric: 'food_cost',
      message: `Food cost elevado: ${foodCost}%`
    })
  }

  if (grossMargin < 45) {
    activeAlerts.push({
      type: 'critico',
      metric: 'margen',
      message: `Margen bruto bajo: ${grossMargin}%`
    })
  }

  if (weeklyChange < -15) {
    activeAlerts.push({
      type: 'advertencia',
      metric: 'tendencia',
      message: `Tendencia semanal negativa: ${weeklyChange}%`
    })
  }

  if (salesChange < -20) {
    activeAlerts.push({
      type: 'advertencia',
      metric: 'ventas',
      message: `Ventas ${Math.abs(salesChange)}% abajo vs ayer`
    })
  }

  const soldOutCount = analyticsStore.soldOutProducts?.length || 0
  if (soldOutCount > 5) {
    activeAlerts.push({
      type: 'info',
      metric: 'inventario',
      message: `${soldOutCount} productos agotados`
    })
  }

  // Construir contexto completo
  return {
    // Temporal
    temporal: {
      fecha: now.toISOString().split('T')[0],
      hora: `${currentHour}:${String(now.getMinutes()).padStart(2, '0')}`,
      periodo_dia: dayPeriod,
      es_fin_de_semana: isWeekend,
      es_hora_pico: isPeakHour,
      dia_semana: ['Domingo', 'Lunes', 'Martes', 'Miercoles', 'Jueves', 'Viernes', 'Sabado'][dayOfWeek]
    },

    // Ventas actuales
    ventas: {
      hoy: analyticsStore.todaySales || 0,
      ayer: analyticsStore.yesterdaySales || 0,
      cambio_vs_ayer: salesChange,
      semana: analyticsStore.weeklySalesTotal || 0,
      cambio_semanal: weeklyChange,
      ordenes_hoy: analyticsStore.ordersToday || 0,
      ticket_promedio: analyticsStore.avgTicket || 0,
      ordenes_pendientes: analyticsStore.activeOrders || 0
    },

    // Metricas financieras
    financiero: {
      food_cost: foodCost,
      margen_bruto: grossMargin,
      clasificacion_food_cost: foodCost <= 30 ? 'excelente' : foodCost <= 35 ? 'bueno' : foodCost <= 40 ? 'aceptable' : 'critico',
      clasificacion_margen: grossMargin >= 65 ? 'excelente' : grossMargin >= 55 ? 'bueno' : grossMargin >= 45 ? 'aceptable' : 'bajo'
    },

    // Productos
    productos: {
      top_5: (analyticsStore.topProducts || []).slice(0, 5).map(p => ({
        nombre: p.name,
        cantidad: p.quantity,
        ingresos: p.revenue
      })),
      agotados: soldOutCount,
      bajo_margen: (analyticsStore.lowMarginProducts || []).length,
      sin_ventas_hoy: (analyticsStore.productsNotSoldToday || []).length,
      rotacion: analyticsStore.productRotationRate || 0
    },

    // Tendencias
    tendencias: {
      mejor_dia_semana: analyticsStore.bestDayOfWeek ? {
        dia: analyticsStore.bestDayOfWeek.dayName,
        ventas: analyticsStore.bestDayOfWeek.sales
      } : null,
      hora_pico: analyticsStore.peakHour || null,
      tendencia_semanal: (analyticsStore.weeklyTrend || []).map(d => ({
        dia: d.dayName,
        ventas: d.sales,
        ordenes: d.orders
      }))
    },

    // Voz
    voz: {
      conversaciones_hoy: analyticsStore.voiceConversationsToday || 0,
      tasa_upsell: Math.round((analyticsStore.voiceMetrics?.upsell_success_rate || 0) * 100),
      satisfaccion: Math.round((analyticsStore.voiceMetrics?.avg_sentiment || 0.5) * 100)
    },

    // Alertas activas
    alertas: activeAlerts,

    // Resumen ejecutivo para el LLM
    resumen_ejecutivo: buildExecutiveSummary(
      analyticsStore.todaySales || 0,
      salesChange,
      foodCost,
      grossMargin,
      activeAlerts,
      isPeakHour,
      dayPeriod
    )
  }
}

function buildExecutiveSummary(sales, salesChange, foodCost, margin, alerts, isPeakHour, dayPeriod) {
  /**
   * Genera un resumen ejecutivo en texto para que el LLM tenga
   * contexto rapido de la situacion actual del restaurante.
   */
  const lines = []

  // Estado general de ventas
  if (salesChange > 10) {
    lines.push(`Ventas excelentes hoy (+${salesChange}% vs ayer)`)
  } else if (salesChange > 0) {
    lines.push(`Ventas positivas (+${salesChange}% vs ayer)`)
  } else if (salesChange > -10) {
    lines.push(`Ventas estables (${salesChange}% vs ayer)`)
  } else {
    lines.push(`Ventas por debajo de lo esperado (${salesChange}% vs ayer)`)
  }

  // Estado de rentabilidad
  if (foodCost > 40) {
    lines.push(`ALERTA: Food cost critico (${foodCost}%)`)
  } else if (margin < 50) {
    lines.push(`Margen ajustado (${margin}%)`)
  } else if (margin > 65) {
    lines.push(`Excelente rentabilidad (margen ${margin}%)`)
  }

  // Contexto temporal
  if (isPeakHour) {
    lines.push(`Actualmente en hora pico`)
  } else if (dayPeriod === 'madrugada' || dayPeriod === 'mañana') {
    lines.push(`Inicio del dia - proyecciones preliminares`)
  }

  // Alertas importantes
  const criticalAlerts = alerts.filter(a => a.type === 'critico')
  if (criticalAlerts.length > 0) {
    lines.push(`${criticalAlerts.length} alerta(s) critica(s) activa(s)`)
  }

  return lines.join('. ') + '.'
}

// NUEVO: Formatear respuestas de operaciones/financieras
function formatOperationsResponse(query) {
  const q = query.toLowerCase()

  if (q.includes('food cost')) {
    const fc = analyticsStore.todayFoodCost
    const evaluation = fc <= 30 ? 'excelente' : fc <= 35 ? 'bueno' : fc <= 40 ? 'aceptable' : 'alto'
    return `El **Food Cost** de hoy es del **${fc}%** (${evaluation}).\n\n` +
           `El food cost ideal para un restaurante deberia estar entre 28-35%. ` +
           `Un food cost del ${fc}% significa que de cada $100 en ventas, $${fc} son costos de ingredientes.`
  }

  if (q.includes('margen bruto') || (q.includes('margen') && !q.includes('bajo') && !q.includes('mejor'))) {
    const margin = analyticsStore.todayGrossMargin
    const evaluation = margin >= 65 ? 'excelente' : margin >= 55 ? 'bueno' : margin >= 45 ? 'aceptable' : 'bajo'
    return `El **Margen Bruto** de hoy es del **${margin}%** (${evaluation}).\n\n` +
           `Esto significa que por cada $100 en ventas, te quedan $${margin} despues de los costos de productos.`
  }

  if (q.includes('rotacion')) {
    const rotation = analyticsStore.productRotationRate
    const notSold = analyticsStore.productsNotSoldToday
    return `La **Rotacion de Productos** hoy es del **${rotation}%**.\n\n` +
           `${rotation}% del menu se ha vendido hoy. ` +
           `Hay **${notSold.length} productos** sin ventas:\n` +
           notSold.slice(0, 5).map(p => `- ${p.name}`).join('\n') +
           (notSold.length > 5 ? `\n... y ${notSold.length - 5} mas` : '')
  }

  if (q.includes('tendencia') || q.includes('semanal')) {
    const trend = analyticsStore.weeklyTrend
    const total = analyticsStore.weeklySalesTotal
    const change = analyticsStore.weeklyChange
    const changeText = change >= 0 ? `+${change}%` : `${change}%`

    let trendText = `**Tendencia Semanal de Ventas:**\n\n`
    trend.forEach(d => {
      trendText += `- ${d.dayName}: $${formatNumber(d.sales)} (${d.orders} ordenes)\n`
    })
    trendText += `\n**Total semana:** $${formatNumber(total)} (${changeText} vs semana anterior)`
    return trendText
  }

  if (q.includes('bajo margen')) {
    const lowMargin = analyticsStore.lowMarginProducts
    if (lowMargin.length === 0) {
      return `No hay productos con margen bajo (menor a 50%). Todos los productos vendidos tienen buenos margenes.`
    }
    let text = `**Productos con Bajo Margen** (menos del 50%):\n\n`
    lowMargin.forEach((p, i) => {
      text += `${i + 1}. **${p.name}**: ${p.marginPercent}% margen (vendidos: ${p.quantity})\n`
    })
    text += `\nConsidera ajustar precios o negociar con proveedores para estos productos.`
    return text
  }

  if (q.includes('mejor margen')) {
    const topMargin = analyticsStore.topMarginProducts
    if (topMargin.length === 0) {
      return `Aun no hay suficientes datos de ventas para determinar productos con mejor margen.`
    }
    let text = `**Productos con Mejor Margen:**\n\n`
    topMargin.forEach((p, i) => {
      text += `${i + 1}. **${p.name}**: ${p.marginPercent}% margen ($${formatNumber(p.margin)} ganancia)\n`
    })
    text += `\nEstos productos son los mas rentables. Considera promocionarlos mas.`
    return text
  }

  if (q.includes('sin ventas') || q.includes('no se han vendido')) {
    const notSold = analyticsStore.productsNotSoldToday
    if (notSold.length === 0) {
      return `Excelente! Todos los productos disponibles se han vendido al menos una vez hoy.`
    }
    let text = `**Productos sin Ventas Hoy** (${notSold.length} productos):\n\n`
    notSold.slice(0, 10).forEach((p, i) => {
      text += `${i + 1}. ${p.name}\n`
    })
    if (notSold.length > 10) {
      text += `\n... y ${notSold.length - 10} productos mas sin ventas.`
    }
    text += `\n\nConsidera hacer promociones o revisar si deben estar en el menu.`
    return text
  }

  if (q.includes('mejor dia')) {
    const bestDay = analyticsStore.bestDayOfWeek
    if (!bestDay) {
      return `Aun no hay suficientes datos para determinar el mejor dia de la semana.`
    }
    return `El **mejor dia** de esta semana fue **${bestDay.dayName}** con:\n\n` +
           `- Ventas: $${formatNumber(bestDay.sales)}\n` +
           `- Ordenes: ${bestDay.orders}\n` +
           `- Ticket promedio: $${formatNumber(bestDay.avgTicket)}`
  }

  // Respuesta general de operaciones
  return `**Resumen de Operaciones:**\n\n` +
         `- Food Cost: ${analyticsStore.todayFoodCost}%\n` +
         `- Margen Bruto: ${analyticsStore.todayGrossMargin}%\n` +
         `- Rotacion: ${analyticsStore.productRotationRate}%\n` +
         `- Ventas semana: $${formatNumber(analyticsStore.weeklySalesTotal)}\n` +
         `- Cambio semanal: ${analyticsStore.weeklyChange >= 0 ? '+' : ''}${analyticsStore.weeklyChange}%`
}

function addMessage(role, text, intent = null, visualData = null) {
  messages.value.push({
    role,
    text,
    intent,
    visualData,
    timestamp: new Date()
  })

  scrollToBottom()

  // Notificacion si el panel esta cerrado
  if (!isExpanded.value && role === 'assistant') {
    hasUnreadMessages.value = true
  }
}

function scrollToBottom() {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

async function confirmAction() {
  if (!pendingConfirmation.value) return

  pendingConfirmation.value = null
  addMessage('user', 'Si, confirmar')
  await processMessage('si')
}

async function cancelAction() {
  if (!pendingConfirmation.value) return

  pendingConfirmation.value = null
  addMessage('user', 'No, cancelar')
  await processMessage('no')
}

function clearChat() {
  messages.value = []
  pendingConfirmation.value = null
  localStorage.removeItem(STORAGE_KEY)
}

// ============================================================
// GRABACION DE VOZ
// ============================================================

async function startRecording() {
  if (isRecording.value || isProcessing.value) return

  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    mediaRecorder.value = new MediaRecorder(stream)
    audioChunks.value = []

    mediaRecorder.value.ondataavailable = (event) => {
      if (event.data.size > 0) {
        audioChunks.value.push(event.data)
      }
    }

    mediaRecorder.value.onstop = async () => {
      stream.getTracks().forEach(track => track.stop())
      await processAudio()
    }

    mediaRecorder.value.start()
    isRecording.value = true
  } catch (error) {
    console.error('Error accessing microphone:', error)
    addMessage('assistant', 'No pude acceder al microfono. Verifica los permisos.', 'error')
  }
}

function stopRecording() {
  if (!isRecording.value || !mediaRecorder.value) return

  mediaRecorder.value.stop()
  isRecording.value = false
}

function toggleRecording() {
  if (isRecording.value) {
    stopRecording()
  } else {
    startRecording()
  }
}

async function processAudio() {
  if (audioChunks.value.length === 0) return

  isTranscribing.value = true

  try {
    const audioBlob = new Blob(audioChunks.value, { type: 'audio/webm' })
    const formData = new FormData()
    formData.append('audio', audioBlob, 'recording.webm')
    formData.append('session_id', sessionId.value)

    const response = await fetch(`${API_BASE_URL}/api/admin/voice`, {
      method: 'POST',
      body: formData
    })

    if (response.ok) {
      const data = await response.json()

      // Mostrar transcripcion
      if (data.transcription) {
        addMessage('user', data.transcription)
      }

      // Procesar respuesta
      if (data.response) {
        // Verificar si requiere confirmacion
        if (data.requires_confirmation) {
          pendingConfirmation.value = {
            message: data.confirmation_message || data.response,
            action: data.pending_action
          }
        }

        addMessage('assistant', data.response, data.intent, data.visual_data)

        // Audio de respuesta
        if (data.audio_url) {
          lastAudioResponse.value = `${API_BASE_URL}${data.audio_url}`
          playResponse()
        }
      }
    } else {
      throw new Error('Failed to process audio')
    }
  } catch (error) {
    console.error('Error processing audio:', error)
    addMessage('assistant', 'No pude procesar el audio. Intenta de nuevo.', 'error')
  } finally {
    isTranscribing.value = false
    audioChunks.value = []
  }
}

// ============================================================
// REPRODUCCION DE AUDIO
// ============================================================

function playResponse() {
  if (!lastAudioResponse.value) return

  if (audioPlayer.value) {
    audioPlayer.value.pause()
  }

  audioPlayer.value = new Audio(lastAudioResponse.value)
  audioPlayer.value.onplay = () => { isPlayingAudio.value = true }
  audioPlayer.value.onended = () => { isPlayingAudio.value = false }
  audioPlayer.value.onpause = () => { isPlayingAudio.value = false }
  audioPlayer.value.play()
}

// ============================================================
// FORMATEO Y UTILIDADES
// ============================================================

function formatMessage(text) {
  if (!text) return ''

  // Convertir markdown basico a HTML
  let html = text
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\n/g, '<br>')

  // Formatear montos
  html = html.replace(/\$(\d+(?:,\d{3})*(?:\.\d{2})?)/g, '<span class="amount">$$$1</span>')

  return html
}

function formatTime(date) {
  if (!date) return ''
  return new Date(date).toLocaleTimeString('es-MX', {
    hour: '2-digit',
    minute: '2-digit'
  })
}

function formatNumber(num) {
  if (num === null || num === undefined) return '0'
  return Number(num).toLocaleString('es-MX', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2
  })
}

function getBarWidth(value, data) {
  const max = Math.max(...data.map(d => d.quantity || 0))
  return max > 0 ? (value / max) * 100 : 0
}

function getHourlyBarHeight(value, data) {
  const values = Object.values(data)
  const max = Math.max(...values)
  return max > 0 ? (value / max) * 100 : 0
}

// ============================================================
// LIFECYCLE
// ============================================================

let notificationInterval = null

onMounted(() => {
  audioPlayer.value = new Audio()

  // Cargar datos iniciales para notificaciones
  analyticsStore.fetchAllData()

  // Verificar notificaciones cada minuto
  checkProactiveNotifications()
  notificationInterval = setInterval(checkProactiveNotifications, NOTIFICATION_CHECK_INTERVAL)
})

onUnmounted(() => {
  if (audioPlayer.value) {
    audioPlayer.value.pause()
  }
  if (mediaRecorder.value && mediaRecorder.value.state !== 'inactive') {
    mediaRecorder.value.stop()
  }
  if (notificationInterval) {
    clearInterval(notificationInterval)
  }
})
</script>

<style scoped>
.admin-assistant {
  position: fixed;
  bottom: 20px;
  right: 20px;
  z-index: 1000;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

/* Notifications Badge */
.notifications-badge {
  position: absolute;
  top: -8px;
  right: -8px;
  width: 24px;
  height: 24px;
  background: #e74c3c;
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.75rem;
  font-weight: bold;
  animation: pulse-badge 2s infinite;
  z-index: 1;
}

@keyframes pulse-badge {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.1); }
}

/* Toggle Button */
.assistant-toggle {
  position: relative;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.25rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 50px;
  cursor: pointer;
  font-weight: 600;
  font-size: 1rem;
  box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
  transition: all 0.3s ease;
}

.assistant-toggle:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(102, 126, 234, 0.5);
}

.assistant-toggle.has-notification {
  animation: glow 2s infinite;
}

@keyframes glow {
  0%, 100% { box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4); }
  50% { box-shadow: 0 4px 25px rgba(231, 76, 60, 0.6); }
}

.toggle-icon {
  font-size: 1.25rem;
}

/* Panel */
.assistant-panel {
  width: 420px;
  max-height: 650px;
  background: white;
  border-radius: 16px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.15);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* Header */
.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.header-info {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.assistant-icon {
  font-size: 2rem;
}

.header-text h3 {
  margin: 0;
  font-size: 1rem;
}

.status {
  font-size: 0.75rem;
  opacity: 0.9;
}

.status.connected { color: #2ecc71; }
.status.connecting { color: #f1c40f; }
.status.error { color: #e74c3c; }

.header-actions {
  display: flex;
  gap: 0.5rem;
}

.btn-icon {
  width: 32px;
  height: 32px;
  border: none;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 8px;
  cursor: pointer;
  font-size: 1rem;
  transition: background 0.2s;
}

.btn-icon:hover {
  background: rgba(255, 255, 255, 0.3);
}

/* Notifications Panel */
.notifications-panel {
  background: linear-gradient(135deg, #fff3cd 0%, #ffeeba 100%);
  padding: 0.75rem;
  border-bottom: 2px solid #f39c12;
  max-height: 150px;
  overflow-y: auto;
}

.notifications-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
  font-weight: 600;
  color: #856404;
  font-size: 0.85rem;
}

.btn-dismiss-all {
  background: none;
  border: none;
  color: #856404;
  font-size: 0.75rem;
  cursor: pointer;
  text-decoration: underline;
}

.notification-item {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  padding: 0.5rem;
  background: white;
  border-radius: 8px;
  margin-bottom: 0.5rem;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

.notification-item.warning { border-left: 3px solid #f39c12; }
.notification-item.alert { border-left: 3px solid #e74c3c; }
.notification-item.info { border-left: 3px solid #3498db; }
.notification-item.critical {
  border-left: 4px solid #c0392b;
  background: linear-gradient(90deg, #fee2e2 0%, white 100%);
  animation: pulse-critical 1s ease-in-out infinite;
}
.notification-item.emergency {
  border-left: 4px solid #7c0a02;
  background: linear-gradient(90deg, #fecaca 0%, white 100%);
  animation: pulse-critical 0.5s ease-in-out infinite;
}

@keyframes pulse-critical {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.85; }
}

.notif-icon {
  font-size: 1.2rem;
  flex-shrink: 0;
}

.notif-content {
  flex: 1;
}

.notif-message {
  margin: 0;
  font-size: 0.85rem;
  color: #2c3e50;
}

.notif-action-btn {
  margin-top: 0.25rem;
  padding: 0.2rem 0.5rem;
  background: #667eea;
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 0.75rem;
  cursor: pointer;
}

.btn-dismiss {
  background: none;
  border: none;
  color: #95a5a6;
  cursor: pointer;
  font-size: 0.9rem;
  padding: 0;
}

/* Messages Container */
.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: 1rem;
  min-height: 180px;
  max-height: 280px;
  background: #f8f9fa;
}

/* Welcome Message */
.welcome-message {
  text-align: center;
  padding: 1rem;
}

.welcome-icon {
  font-size: 3rem;
  margin-bottom: 0.5rem;
}

.welcome-message h4 {
  margin: 0 0 0.5rem 0;
  color: #2c3e50;
}

.welcome-message ul {
  text-align: left;
  padding-left: 1.5rem;
  margin: 0.5rem 0;
}

.welcome-message li {
  margin: 0.25rem 0;
  color: #7f8c8d;
  font-size: 0.9rem;
}

.hint {
  font-size: 0.85rem;
  color: #95a5a6;
  margin-top: 1rem;
}

.hint-iot {
  font-size: 0.8rem;
  color: #2980b9;
  margin-top: 0.5rem;
  padding: 0.5rem;
  background: #ebf5fb;
  border-radius: 6px;
  border-left: 3px solid #3498db;
}

/* Messages */
.message {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.message.user {
  flex-direction: row-reverse;
}

.message-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: #ecf0f1;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1rem;
  flex-shrink: 0;
}

.message.user .message-avatar {
  background: #667eea;
}

.message-content {
  max-width: 80%;
}

.message-text {
  padding: 0.75rem 1rem;
  border-radius: 12px;
  background: white;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  font-size: 0.9rem;
  line-height: 1.4;
}

.message.user .message-text {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.message-text :deep(.amount) {
  font-weight: 700;
  color: #27ae60;
}

.message.user .message-text :deep(.amount) {
  color: #2ecc71;
}

/* Visual Data Components */
.message-visual {
  margin-top: 0.5rem;
  padding: 0.75rem;
  background: #f8f9fa;
  border-radius: 8px;
  border: 1px solid #e9ecef;
}

/* Sales Summary */
.visual-sales-summary .summary-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.5rem;
}

.summary-item {
  text-align: center;
  padding: 0.5rem;
  background: white;
  border-radius: 6px;
}

.summary-value {
  display: block;
  font-size: 1.1rem;
  font-weight: bold;
  color: #27ae60;
}

.summary-label {
  font-size: 0.7rem;
  color: #7f8c8d;
}

/* Top Products */
.visual-top-products {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.product-bar-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.product-info {
  display: flex;
  align-items: center;
  gap: 0.3rem;
  min-width: 100px;
}

.product-rank {
  width: 18px;
  height: 18px;
  background: #667eea;
  color: white;
  border-radius: 50%;
  font-size: 0.65rem;
  display: flex;
  align-items: center;
  justify-content: center;
}

.product-name {
  font-size: 0.75rem;
  color: #2c3e50;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.product-bar-container {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 0.3rem;
}

.product-bar {
  height: 16px;
  background: linear-gradient(90deg, #27ae60, #2ecc71);
  border-radius: 4px;
  min-width: 5px;
}

.product-qty {
  font-size: 0.7rem;
  font-weight: bold;
  color: #2c3e50;
}

/* Hourly Chart */
.visual-hourly-chart .hourly-bars {
  display: flex;
  align-items: flex-end;
  gap: 2px;
  height: 60px;
}

.hourly-bar-wrapper {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  height: 100%;
}

.hourly-bar {
  width: 100%;
  max-width: 15px;
  background: linear-gradient(180deg, #3498db, #2980b9);
  border-radius: 2px 2px 0 0;
  min-height: 2px;
}

.hourly-label {
  font-size: 0.55rem;
  color: #95a5a6;
  margin-top: 2px;
}

/* Daily Report */
.visual-daily-report .report-header {
  font-weight: 600;
  color: #2c3e50;
  margin-bottom: 0.5rem;
  font-size: 0.85rem;
}

.report-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.5rem;
}

.report-item {
  text-align: center;
  padding: 0.5rem;
  background: white;
  border-radius: 6px;
}

.report-icon {
  font-size: 1.2rem;
  display: block;
}

.report-value {
  display: block;
  font-weight: bold;
  font-size: 0.9rem;
  color: #2c3e50;
}

.report-label {
  font-size: 0.65rem;
  color: #7f8c8d;
}

/* Voice Metrics */
.visual-voice-metrics .voice-metrics-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 0.5rem;
}

.vm-item {
  text-align: center;
  padding: 0.5rem;
  background: linear-gradient(135deg, #9b59b6 0%, #8e44ad 100%);
  border-radius: 6px;
  color: white;
}

.vm-icon {
  font-size: 1rem;
  display: block;
}

.vm-value {
  display: block;
  font-weight: bold;
  font-size: 1rem;
}

.vm-label {
  font-size: 0.65rem;
  opacity: 0.9;
}

.message-meta {
  display: flex;
  gap: 0.5rem;
  margin-top: 0.25rem;
  font-size: 0.7rem;
  color: #95a5a6;
}

.message-intent {
  background: #ecf0f1;
  padding: 0.1rem 0.4rem;
  border-radius: 4px;
}

/* Typing Indicator */
.typing-indicator {
  display: flex;
  gap: 4px;
  padding: 0.75rem 1rem;
}

.typing-indicator span {
  width: 8px;
  height: 8px;
  background: #95a5a6;
  border-radius: 50%;
  animation: bounce 1.4s infinite ease-in-out both;
}

.typing-indicator span:nth-child(1) { animation-delay: -0.32s; }
.typing-indicator span:nth-child(2) { animation-delay: -0.16s; }

@keyframes bounce {
  0%, 80%, 100% { transform: scale(0); }
  40% { transform: scale(1); }
}

/* Confirmation Dialog */
.confirmation-dialog {
  background: linear-gradient(135deg, #fff3cd 0%, #ffeeba 100%);
  border: 2px solid #f39c12;
  border-radius: 12px;
  padding: 1rem;
  margin-top: 1rem;
}

.confirmation-dialog p {
  margin: 0 0 1rem 0;
  font-weight: 500;
  color: #856404;
}

.confirmation-actions {
  display: flex;
  gap: 0.5rem;
}

.btn-confirm, .btn-cancel {
  flex: 1;
  padding: 0.5rem;
  border: none;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-confirm {
  background: #27ae60;
  color: white;
}

.btn-confirm:hover {
  background: #219a52;
}

.btn-cancel {
  background: #e74c3c;
  color: white;
}

.btn-cancel:hover {
  background: #c0392b;
}

/* Quick Actions */
.quick-actions-container {
  border-top: 1px solid #ecf0f1;
  background: #f8f9fa;
}

.quick-actions-tabs {
  display: flex;
  padding: 0.5rem 0.75rem 0;
  gap: 0.25rem;
  border-bottom: 1px solid #e9ecef;
}

.tab-btn {
  padding: 0.4rem 0.6rem;
  background: transparent;
  border: none;
  border-bottom: 2px solid transparent;
  font-size: 0.75rem;
  cursor: pointer;
  color: #7f8c8d;
  transition: all 0.2s;
}

.tab-btn:hover {
  color: #667eea;
}

.tab-btn.active {
  color: #667eea;
  border-bottom-color: #667eea;
  font-weight: 600;
}

.quick-actions {
  display: flex;
  gap: 0.4rem;
  padding: 0.5rem 0.75rem;
  overflow-x: auto;
  flex-wrap: wrap;
}

.quick-action-btn {
  padding: 0.35rem 0.6rem;
  background: white;
  border: 1px solid #ddd;
  border-radius: 16px;
  font-size: 0.75rem;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.2s;
}

.quick-action-btn:hover {
  background: #667eea;
  color: white;
  border-color: #667eea;
}

/* Input Area */
.input-area {
  padding: 0.75rem;
  background: white;
  border-top: 1px solid #ecf0f1;
}

.input-wrapper {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.input-wrapper input {
  flex: 1;
  padding: 0.6rem 0.8rem;
  border: 2px solid #ecf0f1;
  border-radius: 10px;
  font-size: 0.9rem;
  transition: border-color 0.2s;
}

.input-wrapper input:focus {
  outline: none;
  border-color: #667eea;
}

.btn-send {
  width: 40px;
  height: 40px;
  border: none;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-radius: 10px;
  cursor: pointer;
  font-size: 1.1rem;
  transition: all 0.2s;
}

.btn-send:hover:not(:disabled) {
  transform: scale(1.05);
}

.btn-send:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Voice Controls */
.voice-controls {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

.btn-voice {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 0.6rem;
  background: #f8f9fa;
  border: 2px dashed #ddd;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s;
  position: relative;
}

.btn-voice:hover:not(:disabled) {
  border-color: #667eea;
  background: #f0f4ff;
}

.btn-voice.recording {
  background: #fee2e2;
  border-color: #e74c3c;
  border-style: solid;
}

.btn-voice.processing {
  background: #fef3c7;
  border-color: #f39c12;
  border-style: solid;
}

.btn-voice:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.pulse {
  position: absolute;
  width: 100%;
  height: 100%;
  border-radius: 10px;
  background: #e74c3c;
  opacity: 0.3;
  animation: pulse 1s infinite;
}

@keyframes pulse {
  0% { transform: scale(1); opacity: 0.3; }
  50% { transform: scale(1.05); opacity: 0.1; }
  100% { transform: scale(1); opacity: 0.3; }
}

.voice-icon {
  font-size: 1.1rem;
}

.voice-text {
  font-size: 0.8rem;
  color: #7f8c8d;
}

.btn-voice.recording .voice-text,
.btn-voice.processing .voice-text {
  color: #2c3e50;
  font-weight: 500;
}

/* Audio Playback */
.audio-playback {
  margin-left: auto;
}

.btn-play {
  width: 36px;
  height: 36px;
  border: none;
  background: #27ae60;
  color: white;
  border-radius: 50%;
  cursor: pointer;
  font-size: 1.1rem;
  transition: all 0.2s;
}

.btn-play:hover {
  transform: scale(1.1);
}

/* Responsive */
@media (max-width: 480px) {
  .admin-assistant {
    bottom: 10px;
    right: 10px;
    left: 10px;
  }

  .assistant-panel {
    width: 100%;
    max-height: 85vh;
  }

  .quick-actions-tabs {
    overflow-x: auto;
  }
}
</style>
