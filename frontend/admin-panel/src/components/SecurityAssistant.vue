<template>
  <div class="security-assistant" :class="{ expanded: isExpanded }">
    <!-- Proactive Notifications Badge -->
    <div v-if="!isExpanded && notifications.length > 0" class="notifications-badge" :class="{ critical: hasCriticalAlert }">
      {{ notifications.length }}
    </div>

    <!-- Toggle Button -->
    <button
      v-if="!isExpanded"
      class="assistant-toggle"
      @click="toggleAssistant"
      :class="{ 'has-alert': hasUnreadMessages || hasCriticalAlert }"
    >
      <span class="toggle-icon">🛡️</span>
      <span class="toggle-text">Seguridad</span>
    </button>

    <!-- Assistant Panel -->
    <div v-if="isExpanded" class="assistant-panel">
      <!-- Header -->
      <div class="panel-header" :class="overallStatus.toLowerCase()">
        <div class="header-info">
          <span class="assistant-icon">🛡️</span>
          <div class="header-text">
            <h3>Asistente de Seguridad IoT</h3>
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

      <!-- Critical Alerts Banner -->
      <div v-if="hasCriticalAlert" class="critical-banner">
        <span class="banner-icon">🚨</span>
        <span class="banner-text">{{ criticalAlertCount }} ALERTA(S) CRITICA(S) ACTIVA(S)</span>
        <button class="btn-ack" @click="acknowledgeCriticalAlerts">Reconocer</button>
      </div>

      <!-- Proactive Notifications Panel -->
      <div v-if="notifications.length > 0" class="notifications-panel">
        <div class="notifications-header">
          <span>⚡ Alertas de Sensores</span>
          <button class="btn-dismiss-all" @click="dismissAllNotifications">Descartar</button>
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
            <p v-if="notif.consequence" class="notif-consequence">{{ notif.consequence }}</p>
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
          <div class="welcome-icon">🛡️</div>
          <h4>Asistente de Seguridad IoT</h4>
          <p>Monitoreo en tiempo real de:</p>
          <ul>
            <li>🌡️ <strong>Temperatura</strong> - Refrigeradores, congeladores, cocina</li>
            <li>🔥 <strong>Humo/Fuego</strong> - Deteccion temprana de incendios</li>
            <li>⛽ <strong>Gas</strong> - Fugas y niveles peligrosos</li>
            <li>🌫️ <strong>CO2</strong> - Calidad del aire</li>
            <li>💧 <strong>Humedad</strong> - Control de moho</li>
            <li>👁️ <strong>Movimiento</strong> - Seguridad perimetral</li>
          </ul>
          <p class="hint">Preguntame sobre el estado de los sensores</p>
          <p class="hint-critical">🔔 Las alertas criticas se anuncian por voz automaticamente</p>
        </div>

        <!-- Messages -->
        <div
          v-for="(message, index) in messages"
          :key="index"
          class="message"
          :class="message.role"
        >
          <div class="message-avatar">
            {{ message.role === 'user' ? '👤' : '🛡️' }}
          </div>
          <div class="message-content">
            <div class="message-text" v-html="formatMessage(message.text)"></div>

            <!-- Sensor Data Visual -->
            <div v-if="message.sensorData" class="message-sensor-data">
              <div class="sensor-grid">
                <div
                  v-for="(sensor, i) in message.sensorData"
                  :key="i"
                  class="sensor-card"
                  :class="{ alert: sensor.alerta }"
                >
                  <span class="sensor-icon">{{ getSensorIcon(sensor.tipo) }}</span>
                  <div class="sensor-info">
                    <span class="sensor-type">{{ sensor.tipo }}</span>
                    <span class="sensor-value">{{ sensor.valor }}{{ sensor.unidad }}</span>
                  </div>
                  <span v-if="sensor.alerta" class="sensor-alert-badge">!</span>
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
          <div class="message-avatar">🛡️</div>
          <div class="message-content">
            <div class="typing-indicator">
              <span></span>
              <span></span>
              <span></span>
            </div>
          </div>
        </div>
      </div>

      <!-- Quick Actions - Security Categories -->
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
            :class="{ urgent: action.urgent }"
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
            placeholder="Pregunta sobre sensores..."
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
              {{ isRecording ? 'Toca para enviar' : isTranscribing ? 'Procesando...' : 'Hablar' }}
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

// Estado del panel
const isExpanded = ref(false)
const hasUnreadMessages = ref(false)
const overallStatus = ref('NORMAL')

// Mensajes
const messages = ref([])
const inputText = ref('')
const isProcessing = ref(false)

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

// Configuracion
const API_BASE_URL = import.meta.env.VITE_VOICE_ASSISTANT_URL || ''
const STORAGE_KEY = 'security_assistant_history'
const IOT_CHECK_INTERVAL = 30000 // 30 segundos

// Categorias de acciones de seguridad
const activeCategory = ref('general')

const actionCategories = [
  { id: 'general', icon: '📡', label: 'General' },
  { id: 'temperatura', icon: '🌡️', label: 'Temperatura' },
  { id: 'fuego', icon: '🔥', label: 'Fuego/Gas' },
  { id: 'ambiente', icon: '🌫️', label: 'Ambiente' },
  { id: 'seguridad', icon: '👁️', label: 'Seguridad' },
  { id: 'reportes', icon: '📊', label: 'Reportes' }
]

// Acciones rapidas de seguridad
const quickActions = ref([
  // General
  { id: 'status', icon: '📡', label: 'Estado general', text: 'Como estan todos los sensores del restaurante?', category: 'general' },
  { id: 'alerts', icon: '🚨', label: 'Alertas activas', text: 'Hay alertas de seguridad activas?', category: 'general', urgent: true },
  { id: 'devices', icon: '📶', label: 'Dispositivos', text: 'Cuantos dispositivos IoT estan conectados?', category: 'general' },
  { id: 'summary', icon: '📋', label: 'Resumen', text: 'Dame un resumen de seguridad del restaurante', category: 'general' },

  // Temperatura
  { id: 'temp_all', icon: '🌡️', label: 'Todas', text: 'Como esta la temperatura en todas las areas?', category: 'temperatura' },
  { id: 'temp_fridge', icon: '🧊', label: 'Refrigeradores', text: 'Como esta la temperatura de los refrigeradores?', category: 'temperatura' },
  { id: 'temp_freezer', icon: '❄️', label: 'Congeladores', text: 'Como estan los congeladores? Hay riesgo de descomposicion?', category: 'temperatura' },
  { id: 'temp_kitchen', icon: '👨‍🍳', label: 'Cocina', text: 'Cual es la temperatura en la cocina?', category: 'temperatura' },
  { id: 'temp_history', icon: '📈', label: 'Historial', text: 'Muestra el historial de temperatura de hoy', category: 'temperatura' },

  // Fuego/Gas
  { id: 'smoke', icon: '💨', label: 'Humo', text: 'Hay alertas de humo? Cual es el nivel actual?', category: 'fuego', urgent: true },
  { id: 'gas', icon: '⛽', label: 'Gas', text: 'Como estan los niveles de gas? Hay fugas detectadas?', category: 'fuego', urgent: true },
  { id: 'fire_risk', icon: '🔥', label: 'Riesgo incendio', text: 'Cual es el riesgo de incendio actual?', category: 'fuego', urgent: true },
  { id: 'fire_protocol', icon: '🧯', label: 'Protocolo', text: 'Cual es el protocolo en caso de incendio?', category: 'fuego' },

  // Ambiente
  { id: 'co2', icon: '🌫️', label: 'CO2', text: 'Como esta la calidad del aire y niveles de CO2?', category: 'ambiente' },
  { id: 'humidity', icon: '💧', label: 'Humedad', text: 'Como esta la humedad? Hay riesgo de moho?', category: 'ambiente' },
  { id: 'ventilation', icon: '🌬️', label: 'Ventilacion', text: 'La ventilacion es adecuada en todas las areas?', category: 'ambiente' },
  { id: 'comfort', icon: '😊', label: 'Confort', text: 'Las condiciones ambientales son confortables para clientes?', category: 'ambiente' },

  // Seguridad fisica
  { id: 'motion', icon: '👁️', label: 'Movimiento', text: 'Se ha detectado movimiento inusual?', category: 'seguridad' },
  { id: 'intrusion', icon: '🚨', label: 'Intrusion', text: 'Hay alertas de intrusion o acceso no autorizado?', category: 'seguridad', urgent: true },
  { id: 'doors', icon: '🚪', label: 'Accesos', text: 'Estado de los sensores en puertas y accesos', category: 'seguridad' },
  { id: 'after_hours', icon: '🌙', label: 'Fuera horario', text: 'Hubo actividad fuera del horario de operacion?', category: 'seguridad' },

  // Reportes
  { id: 'daily_report', icon: '📑', label: 'Reporte diario', text: 'Genera el reporte de seguridad del dia', category: 'reportes' },
  { id: 'alert_history', icon: '📜', label: 'Historial alertas', text: 'Muestra el historial de alertas de las ultimas 24 horas', category: 'reportes' },
  { id: 'sensor_health', icon: '💚', label: 'Salud sensores', text: 'Cual es el estado de salud de todos los sensores?', category: 'reportes' },
  { id: 'recommendations', icon: '💡', label: 'Recomendaciones', text: 'Que recomendaciones de seguridad tienes para hoy?', category: 'reportes' }
])

const filteredQuickActions = computed(() => {
  return quickActions.value.filter(a => a.category === activeCategory.value)
})

// Computed
const connectionStatusText = computed(() => {
  switch (connectionStatus.value) {
    case 'connected': return 'Conectado'
    case 'connecting': return 'Conectando...'
    case 'error': return 'Error'
    default: return 'Desconectado'
  }
})

const hasCriticalAlert = computed(() => {
  return notifications.value.some(n => n.type === 'critical' || n.type === 'emergency')
})

const criticalAlertCount = computed(() => {
  return notifications.value.filter(n => n.type === 'critical' || n.type === 'emergency').length
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
    console.error('Error saving security chat history:', error)
  }
}

function loadHistoryFromStorage() {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved) {
      const data = JSON.parse(saved)

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

        return true
      }
    }
  } catch (error) {
    console.error('Error loading security chat history:', error)
  }
  return false
}

watch(messages, () => {
  if (messages.value.length > 0) {
    saveHistoryToStorage()
  }
}, { deep: true })

// ============================================================
// IOT MONITORING
// ============================================================

let iotCheckInterval = null

async function checkIoTAlerts() {
  try {
    const response = await fetch(`${API_BASE_URL}/api/security/status`)

    if (response.ok) {
      const data = await response.json()

      if (data.success) {
        // Update overall status
        overallStatus.value = data.estado_general || 'NORMAL'

        // Process critical alerts
        if (data.alertas_criticas && data.alertas_criticas.length > 0) {
          for (const alerta of data.alertas_criticas) {
            const notifMessage = `🚨 ${alerta.tipo.toUpperCase()} en ${alerta.ubicacion}: ${alerta.mensaje}`

            addNotification({
              type: 'critical',
              message: notifMessage,
              action: `iot_critical_${alerta.tipo}`,
              actionLabel: 'Ver detalles',
              consequence: alerta.consecuencia,
              actionRequired: alerta.accion_requerida
            })

            // Auto voice alert for critical
            await speakCriticalAlert(alerta)
          }
        }

        // Process warning alerts
        if (data.alertas_advertencia && data.alertas_advertencia.length > 0) {
          for (const alerta of data.alertas_advertencia) {
            addNotification({
              type: 'warning',
              message: `⚠️ ${alerta.tipo}: ${alerta.mensaje}`,
              action: `iot_warning_${alerta.tipo}`,
              actionLabel: 'Revisar'
            })
          }
        }
      }
    }
  } catch (error) {
    console.error('[SecurityAssistant] Error verificando IoT:', error)
  }
}

async function speakCriticalAlert(alerta) {
  try {
    let voiceMessage = `ALERTA DE SEGURIDAD. ${alerta.tipo} en ${alerta.ubicacion}. `
    voiceMessage += alerta.mensaje + '. '

    if (alerta.consecuencia) {
      voiceMessage += `Riesgo: ${alerta.consecuencia}. `
    }

    if (alerta.accion_requerida) {
      voiceMessage += `Accion: ${alerta.accion_requerida}`
    }

    const response = await fetch(`${API_BASE_URL}/api/security/message`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId.value || 'security_alert',
        message: voiceMessage,
        voice_response: true
      })
    })

    if (response.ok) {
      const data = await response.json()
      if (data.audio_url) {
        lastAudioResponse.value = `${API_BASE_URL}${data.audio_url}`
        playResponse()
      }
    }
  } catch (error) {
    console.error('[SecurityAssistant] Error en alerta de voz:', error)
  }
}

function startIoTMonitoring() {
  checkIoTAlerts()
  iotCheckInterval = setInterval(checkIoTAlerts, IOT_CHECK_INTERVAL)
  console.log('[SecurityAssistant] Monitoreo IoT iniciado')
}

function addNotification(notif) {
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

function acknowledgeCriticalAlerts() {
  notifications.value = notifications.value.filter(n => n.type !== 'critical' && n.type !== 'emergency')
}

function handleNotificationAction(notif) {
  let question = ''

  if (notif.action.includes('temperature')) {
    question = 'Dame detalles sobre la alerta de temperatura. Que consecuencias tiene y que debo hacer?'
  } else if (notif.action.includes('smoke') || notif.action.includes('fire')) {
    question = 'URGENTE: Hay una alerta de humo. Que esta pasando y cual es el protocolo de emergencia?'
  } else if (notif.action.includes('gas')) {
    question = 'URGENTE: Hay una alerta de gas. Explicame la situacion y el protocolo de evacuacion'
  } else if (notif.action.includes('co2')) {
    question = 'Los niveles de CO2 son altos. Cuales son las consecuencias para la salud y que debo hacer?'
  } else if (notif.action.includes('humidity')) {
    question = 'La humedad esta fuera de rango. Cual es el riesgo de moho y que acciones tomar?'
  } else if (notif.action.includes('motion') || notif.action.includes('security')) {
    question = 'Se detecto movimiento. Es una posible intrusion? Que protocolo seguir?'
  } else {
    question = 'Dame detalles sobre esta alerta de seguridad y que acciones debo tomar'
  }

  if (notif.consequence) {
    question += ` Consecuencia reportada: ${notif.consequence}`
  }

  sendQuickAction(question)
  dismissNotification(notifications.value.indexOf(notif))
}

function getNotificationIcon(type) {
  switch (type) {
    case 'critical': return '🔴'
    case 'emergency': return '🆘'
    case 'warning': return '⚠️'
    case 'info': return 'ℹ️'
    default: return '📡'
  }
}

function getSensorIcon(tipo) {
  const icons = {
    temperature: '🌡️',
    smoke: '🔥',
    gas: '⛽',
    co2: '🌫️',
    humidity: '💧',
    motion: '👁️',
    light: '💡'
  }
  return icons[tipo] || '📡'
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
  const historyLoaded = loadHistoryFromStorage()

  if (sessionId.value && historyLoaded) {
    connectionStatus.value = 'connected'
    return
  }

  connectionStatus.value = 'connecting'
  try {
    const response = await fetch(`${API_BASE_URL}/api/security/session`, {
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
    sessionId.value = `security_${Date.now()}`
  }
}

async function sendMessage() {
  const text = inputText.value.trim()
  if (!text || isProcessing.value) return

  inputText.value = ''
  addMessage('user', text)
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
    // Inject IoT context
    const iotContext = await getIoTContext()

    const response = await fetch(`${API_BASE_URL}/api/security/message`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId.value,
        message: text,
        voice_response: true,
        iot_context: iotContext,
        assistant_type: 'security'
      })
    })

    if (response.ok) {
      const data = await response.json()

      // Extract sensor data if available
      let sensorData = null
      if (data.sensor_readings) {
        sensorData = data.sensor_readings
      }

      addMessage('assistant', data.text, data.intent, sensorData)

      // Auto-play voice response
      if (data.audio_url) {
        lastAudioResponse.value = `${API_BASE_URL}${data.audio_url}`
        playResponse()
      }
    } else {
      throw new Error('Failed to process message')
    }
  } catch (error) {
    console.error('Error processing message:', error)
    addMessage('assistant', 'Error procesando tu solicitud. Por favor intenta de nuevo.', 'error')
  } finally {
    isProcessing.value = false
  }
}

async function getIoTContext() {
  try {
    const response = await fetch(`${API_BASE_URL}/api/security/status`)
    if (response.ok) {
      const data = await response.json()
      return data
    }
  } catch (error) {
    console.error('Error getting IoT context:', error)
  }
  return null
}

function addMessage(role, text, intent = null, sensorData = null) {
  messages.value.push({
    role,
    text,
    intent,
    sensorData,
    timestamp: new Date()
  })

  scrollToBottom()

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

function clearChat() {
  messages.value = []
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
    addMessage('assistant', 'No pude acceder al microfono.', 'error')
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

    const response = await fetch(`${API_BASE_URL}/api/security/voice`, {
      method: 'POST',
      body: formData
    })

    if (response.ok) {
      const data = await response.json()

      if (data.transcription) {
        addMessage('user', data.transcription)
      }

      if (data.response) {
        addMessage('assistant', data.response, data.intent, data.sensor_readings)

        if (data.audio_url) {
          lastAudioResponse.value = `${API_BASE_URL}${data.audio_url}`
          playResponse()
        }
      }
    }
  } catch (error) {
    console.error('Error processing audio:', error)
    addMessage('assistant', 'Error procesando el audio.', 'error')
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

  let html = text
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\n/g, '<br>')

  // Highlight temperature values
  html = html.replace(/(\d+(?:\.\d+)?°C)/g, '<span class="temp-value">$1</span>')
  // Highlight ppm values
  html = html.replace(/(\d+(?:\.\d+)?\s*ppm)/gi, '<span class="ppm-value">$1</span>')
  // Highlight percentage values
  html = html.replace(/(\d+(?:\.\d+)?%)/g, '<span class="percent-value">$1</span>')

  return html
}

function formatTime(date) {
  if (!date) return ''
  return new Date(date).toLocaleTimeString('es-MX', {
    hour: '2-digit',
    minute: '2-digit'
  })
}

// ============================================================
// LIFECYCLE
// ============================================================

onMounted(() => {
  audioPlayer.value = new Audio()
  startIoTMonitoring()
})

onUnmounted(() => {
  if (audioPlayer.value) {
    audioPlayer.value.pause()
  }
  if (mediaRecorder.value && mediaRecorder.value.state !== 'inactive') {
    mediaRecorder.value.stop()
  }
  if (iotCheckInterval) {
    clearInterval(iotCheckInterval)
  }
})
</script>

<style scoped>
.security-assistant {
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
  background: #f39c12;
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.75rem;
  font-weight: bold;
  z-index: 1;
}

.notifications-badge.critical {
  background: #e74c3c;
  animation: pulse-critical-badge 0.5s infinite;
}

@keyframes pulse-critical-badge {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.2); }
}

/* Toggle Button */
.assistant-toggle {
  position: relative;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.25rem;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
  color: white;
  border: 2px solid #27ae60;
  border-radius: 50px;
  cursor: pointer;
  font-weight: 600;
  font-size: 1rem;
  box-shadow: 0 4px 15px rgba(39, 174, 96, 0.3);
  transition: all 0.3s ease;
}

.assistant-toggle:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(39, 174, 96, 0.4);
}

.assistant-toggle.has-alert {
  border-color: #e74c3c;
  animation: glow-alert 1s infinite;
}

@keyframes glow-alert {
  0%, 100% { box-shadow: 0 4px 15px rgba(231, 76, 60, 0.3); }
  50% { box-shadow: 0 4px 25px rgba(231, 76, 60, 0.6); }
}

.toggle-icon {
  font-size: 1.25rem;
}

/* Panel */
.assistant-panel {
  width: 420px;
  max-height: 650px;
  background: #1a1a2e;
  border-radius: 16px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.4);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border: 1px solid rgba(255,255,255,0.1);
}

/* Header */
.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
  color: white;
  border-bottom: 2px solid;
}

.panel-header.normal { border-bottom-color: #27ae60; }
.panel-header.atencion { border-bottom-color: #f1c40f; }
.panel-header.critico { border-bottom-color: #e74c3c; animation: pulse-header 1s infinite; }

@keyframes pulse-header {
  0%, 100% { background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); }
  50% { background: linear-gradient(135deg, #2c1810 0%, #3d1f1f 100%); }
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
  background: rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  cursor: pointer;
  font-size: 1rem;
  transition: background 0.2s;
}

.btn-icon:hover {
  background: rgba(255, 255, 255, 0.2);
}

/* Critical Banner */
.critical-banner {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 1rem;
  background: linear-gradient(90deg, #c0392b 0%, #e74c3c 100%);
  color: white;
  animation: pulse-banner 0.5s infinite;
}

@keyframes pulse-banner {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.8; }
}

.banner-icon {
  font-size: 1.5rem;
}

.banner-text {
  flex: 1;
  font-weight: 700;
  font-size: 0.85rem;
}

.btn-ack {
  padding: 0.4rem 0.8rem;
  background: rgba(255,255,255,0.2);
  border: 1px solid white;
  color: white;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.75rem;
  font-weight: 600;
}

.btn-ack:hover {
  background: rgba(255,255,255,0.3);
}

/* Notifications Panel */
.notifications-panel {
  background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%);
  padding: 0.75rem;
  max-height: 150px;
  overflow-y: auto;
}

.notifications-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
  font-weight: 600;
  color: #ecf0f1;
  font-size: 0.85rem;
}

.btn-dismiss-all {
  background: none;
  border: none;
  color: #bdc3c7;
  font-size: 0.75rem;
  cursor: pointer;
  text-decoration: underline;
}

.notification-item {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  padding: 0.5rem;
  background: rgba(0,0,0,0.3);
  border-radius: 8px;
  margin-bottom: 0.5rem;
  border-left: 3px solid;
}

.notification-item.warning { border-left-color: #f39c12; }
.notification-item.critical {
  border-left-color: #e74c3c;
  background: rgba(231, 76, 60, 0.2);
}
.notification-item.emergency {
  border-left-color: #c0392b;
  background: rgba(192, 57, 43, 0.3);
  animation: pulse-emergency 0.5s infinite;
}

@keyframes pulse-emergency {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
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
  color: #ecf0f1;
}

.notif-consequence {
  margin: 0.25rem 0 0;
  font-size: 0.75rem;
  color: #e74c3c;
  font-style: italic;
}

.notif-action-btn {
  margin-top: 0.25rem;
  padding: 0.2rem 0.5rem;
  background: #3498db;
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 0.75rem;
  cursor: pointer;
}

.btn-dismiss {
  background: none;
  border: none;
  color: #7f8c8d;
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
  background: #0d0d1a;
}

/* Welcome Message */
.welcome-message {
  text-align: center;
  padding: 1rem;
  color: #ecf0f1;
}

.welcome-icon {
  font-size: 3rem;
  margin-bottom: 0.5rem;
}

.welcome-message h4 {
  margin: 0 0 0.5rem 0;
  color: #fff;
}

.welcome-message ul {
  text-align: left;
  padding-left: 1.5rem;
  margin: 0.5rem 0;
}

.welcome-message li {
  margin: 0.25rem 0;
  color: #bdc3c7;
  font-size: 0.9rem;
}

.hint {
  font-size: 0.85rem;
  color: #7f8c8d;
  margin-top: 1rem;
}

.hint-critical {
  font-size: 0.8rem;
  color: #e74c3c;
  margin-top: 0.5rem;
  padding: 0.5rem;
  background: rgba(231, 76, 60, 0.1);
  border-radius: 6px;
  border-left: 3px solid #e74c3c;
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
  background: #2c3e50;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1rem;
  flex-shrink: 0;
}

.message.user .message-avatar {
  background: #3498db;
}

.message-content {
  max-width: 80%;
}

.message-text {
  padding: 0.75rem 1rem;
  border-radius: 12px;
  background: #2c3e50;
  color: #ecf0f1;
  font-size: 0.9rem;
  line-height: 1.4;
}

.message.user .message-text {
  background: linear-gradient(135deg, #3498db 0%, #2980b9 100%);
  color: white;
}

.message-text :deep(.temp-value) {
  font-weight: 700;
  color: #3498db;
}

.message-text :deep(.ppm-value) {
  font-weight: 700;
  color: #e74c3c;
}

.message-text :deep(.percent-value) {
  font-weight: 700;
  color: #27ae60;
}

/* Sensor Data Visual */
.message-sensor-data {
  margin-top: 0.5rem;
  padding: 0.75rem;
  background: rgba(0,0,0,0.3);
  border-radius: 8px;
}

.sensor-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 0.5rem;
}

.sensor-card {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem;
  background: rgba(255,255,255,0.05);
  border-radius: 6px;
  border: 1px solid rgba(255,255,255,0.1);
}

.sensor-card.alert {
  border-color: #e74c3c;
  background: rgba(231, 76, 60, 0.1);
}

.sensor-icon {
  font-size: 1.2rem;
}

.sensor-info {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.sensor-type {
  font-size: 0.7rem;
  color: #7f8c8d;
}

.sensor-value {
  font-weight: 700;
  font-size: 0.9rem;
  color: #ecf0f1;
}

.sensor-alert-badge {
  width: 18px;
  height: 18px;
  background: #e74c3c;
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.7rem;
  font-weight: 700;
}

.message-meta {
  display: flex;
  gap: 0.5rem;
  margin-top: 0.25rem;
  font-size: 0.7rem;
  color: #7f8c8d;
}

.message-intent {
  background: rgba(255,255,255,0.1);
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
  background: #7f8c8d;
  border-radius: 50%;
  animation: bounce 1.4s infinite ease-in-out both;
}

.typing-indicator span:nth-child(1) { animation-delay: -0.32s; }
.typing-indicator span:nth-child(2) { animation-delay: -0.16s; }

@keyframes bounce {
  0%, 80%, 100% { transform: scale(0); }
  40% { transform: scale(1); }
}

/* Quick Actions */
.quick-actions-container {
  border-top: 1px solid rgba(255,255,255,0.1);
  background: #16213e;
}

.quick-actions-tabs {
  display: flex;
  padding: 0.5rem 0.75rem 0;
  gap: 0.25rem;
  border-bottom: 1px solid rgba(255,255,255,0.1);
  overflow-x: auto;
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
  white-space: nowrap;
}

.tab-btn:hover {
  color: #3498db;
}

.tab-btn.active {
  color: #3498db;
  border-bottom-color: #3498db;
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
  background: rgba(255,255,255,0.05);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 16px;
  font-size: 0.75rem;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.2s;
  color: #bdc3c7;
}

.quick-action-btn:hover {
  background: #3498db;
  color: white;
  border-color: #3498db;
}

.quick-action-btn.urgent {
  border-color: #e74c3c;
  color: #e74c3c;
}

.quick-action-btn.urgent:hover {
  background: #e74c3c;
  color: white;
}

/* Input Area */
.input-area {
  padding: 0.75rem;
  background: #1a1a2e;
  border-top: 1px solid rgba(255,255,255,0.1);
}

.input-wrapper {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.input-wrapper input {
  flex: 1;
  padding: 0.6rem 0.8rem;
  border: 2px solid rgba(255,255,255,0.1);
  border-radius: 10px;
  font-size: 0.9rem;
  background: rgba(0,0,0,0.3);
  color: #ecf0f1;
  transition: border-color 0.2s;
}

.input-wrapper input::placeholder {
  color: #7f8c8d;
}

.input-wrapper input:focus {
  outline: none;
  border-color: #3498db;
}

.btn-send {
  width: 40px;
  height: 40px;
  border: none;
  background: linear-gradient(135deg, #27ae60 0%, #2ecc71 100%);
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
  background: rgba(0,0,0,0.3);
  border: 2px dashed rgba(255,255,255,0.2);
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s;
  position: relative;
  color: #bdc3c7;
}

.btn-voice:hover:not(:disabled) {
  border-color: #3498db;
  background: rgba(52, 152, 219, 0.1);
}

.btn-voice.recording {
  background: rgba(231, 76, 60, 0.2);
  border-color: #e74c3c;
  border-style: solid;
}

.btn-voice.processing {
  background: rgba(241, 196, 15, 0.2);
  border-color: #f1c40f;
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
  .security-assistant {
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
