<template>
  <div class="agriculture-assistant">
    <!-- Header -->
    <div class="page-header">
      <div class="header-content">
        <h1>📝 Notas y Recordatorios</h1>
        <p class="subtitle">Organiza tus tareas y notas del restaurante</p>
      </div>
      <div class="header-status">
        <span class="status-indicator" :class="{ online: isConnected }">
          {{ isConnected ? 'Conectado' : 'Desconectado' }}
        </span>
        <span class="last-update">Actualizado: {{ formatTime(lastUpdate) }}</span>
      </div>
    </div>

    <div class="main-layout">
      <!-- Panel Izquierdo: Chat y Notas -->
      <div class="left-panel">
        <!-- Chat Section -->
        <div class="chat-section">
          <div class="section-header">
            <h3>Chat con el Asistente</h3>
            <button @click="clearChat" class="btn-icon" title="Limpiar chat">
              <span>🗑️</span>
            </button>
          </div>

          <div class="chat-messages" ref="chatContainer">
            <!-- Welcome Message -->
            <div v-if="messages.length === 0" class="welcome-message">
              <div class="welcome-icon">📝</div>
              <h4>Hola! Soy tu asistente de notas</h4>
              <p>Puedo ayudarte con:</p>
              <ul>
                <li>📋 Crear y organizar notas</li>
                <li>⏰ Configurar recordatorios</li>
                <li>✅ Gestionar tareas pendientes</li>
                <li>📊 Revisar historial de actividades</li>
                <li>🔔 Alertas importantes</li>
              </ul>
            </div>

            <!-- Messages -->
            <div
              v-for="(msg, index) in messages"
              :key="index"
              class="chat-message"
              :class="msg.role"
            >
              <div class="message-avatar">
                {{ msg.role === 'user' ? '👤' : '📝' }}
              </div>
              <div class="message-content">
                <div class="message-text" v-html="formatMessage(msg.text)"></div>
                <span class="message-time">{{ formatTime(msg.timestamp) }}</span>
              </div>
            </div>

            <!-- Typing Indicator -->
            <div v-if="isProcessing" class="chat-message assistant typing">
              <div class="message-avatar">📝</div>
              <div class="message-content">
                <div class="typing-dots">
                  <span></span><span></span><span></span>
                </div>
              </div>
            </div>
          </div>

          <!-- Quick Actions -->
          <div class="quick-actions">
            <button
              v-for="action in quickActions"
              :key="action.id"
              @click="sendQuickAction(action.text)"
              class="quick-action-btn"
            >
              {{ action.icon }} {{ action.label }}
            </button>
          </div>

          <!-- Chat Input -->
          <div class="chat-input-area">
            <input
              v-model="inputText"
              type="text"
              placeholder="Escribe tu consulta..."
              @keyup.enter="sendMessage"
              :disabled="isProcessing"
              ref="chatInput"
            />
            <button
              @click="toggleVoice"
              class="btn-voice"
              :class="{ recording: isRecording }"
              :disabled="isProcessing"
            >
              {{ isRecording ? '🔴' : '🎤' }}
            </button>
            <button
              @click="sendMessage"
              class="btn-send"
              :disabled="!inputText.trim() || isProcessing"
            >
              ➤
            </button>
          </div>
        </div>

        <!-- Notes Section -->
        <div class="notes-section">
          <div class="section-header">
            <h3>Notas</h3>
            <button @click="showNoteModal = true" class="btn-add">
              + Nueva
            </button>
          </div>

          <div class="notes-list">
            <div
              v-for="note in notes"
              :key="note.id"
              class="note-card"
              :class="note.category"
            >
              <div class="note-header">
                <span class="note-category-icon">{{ getCategoryIcon(note.category) }}</span>
                <span class="note-date">{{ formatDate(note.created_at) }}</span>
                <div class="note-actions">
                  <button @click="editNote(note)" class="btn-icon-small">✏️</button>
                  <button @click="deleteNote(note.id)" class="btn-icon-small">🗑️</button>
                </div>
              </div>
              <div class="note-content">{{ note.content }}</div>
              <div v-if="note.tags?.length" class="note-tags">
                <span v-for="tag in note.tags" :key="tag" class="tag">{{ tag }}</span>
              </div>
            </div>

            <div v-if="notes.length === 0" class="empty-state">
              <span>📝</span>
              <p>No hay notas aun</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Panel Derecho: Contexto y Recordatorios -->
      <div class="right-panel">
        <!-- Environment Status -->
        <div class="environment-section">
          <div class="section-header">
            <h3>Estado del Ambiente</h3>
            <button @click="refreshSensors" class="btn-icon" :disabled="loadingSensors">
              {{ loadingSensors ? '⏳' : '🔄' }}
            </button>
          </div>

          <div class="sensors-summary">
            <div class="sensor-item" :class="{ alert: sensorAlerts.temperature }">
              <span class="sensor-icon">🌡️</span>
              <div class="sensor-info">
                <span class="sensor-value">{{ sensors.temperature?.toFixed(1) ?? '--' }}°C</span>
                <span class="sensor-label">Temperatura</span>
              </div>
              <span v-if="sensorAlerts.temperature" class="alert-badge">!</span>
            </div>

            <div class="sensor-item" :class="{ alert: sensorAlerts.humidity }">
              <span class="sensor-icon">💧</span>
              <div class="sensor-info">
                <span class="sensor-value">{{ sensors.humidity?.toFixed(1) ?? '--' }}%</span>
                <span class="sensor-label">Humedad</span>
              </div>
              <span v-if="sensorAlerts.humidity" class="alert-badge">!</span>
            </div>

            <div class="sensor-item" :class="{ alert: sensorAlerts.co2 }">
              <span class="sensor-icon">🌫️</span>
              <div class="sensor-info">
                <span class="sensor-value">{{ sensors.co2?.toFixed(0) ?? '--' }} ppm</span>
                <span class="sensor-label">CO2</span>
              </div>
              <span v-if="sensorAlerts.co2" class="alert-badge">!</span>
            </div>

            <div class="sensor-item">
              <span class="sensor-icon">💡</span>
              <div class="sensor-info">
                <span class="sensor-value">{{ sensors.light?.toFixed(0) ?? '--' }} lux</span>
                <span class="sensor-label">Luz</span>
              </div>
            </div>
          </div>

          <!-- Environment Evaluation -->
          <div class="environment-evaluation" :class="environmentStatus">
            <span class="eval-icon">{{ getEnvironmentIcon() }}</span>
            <span class="eval-text">{{ getEnvironmentText() }}</span>
          </div>
        </div>

        <!-- Active Alerts -->
        <div v-if="activeAlerts.length > 0" class="alerts-section">
          <div class="section-header">
            <h3>Alertas Activas</h3>
            <span class="alert-count">{{ activeAlerts.length }}</span>
          </div>

          <div class="alerts-list">
            <div
              v-for="alert in activeAlerts"
              :key="alert.id"
              class="alert-item"
              :class="alert.severity"
            >
              <span class="alert-icon">{{ getAlertIcon(alert.severity) }}</span>
              <div class="alert-content">
                <span class="alert-message">{{ alert.message }}</span>
                <span class="alert-time">{{ formatTime(alert.timestamp) }}</span>
              </div>
              <button @click="dismissAlert(alert.id)" class="btn-dismiss">✕</button>
            </div>
          </div>
        </div>

        <!-- Reminders Section -->
        <div class="reminders-section">
          <div class="section-header">
            <h3>Recordatorios</h3>
            <button @click="showReminderModal = true" class="btn-add">
              + Nuevo
            </button>
          </div>

          <div class="reminders-list">
            <div
              v-for="reminder in sortedReminders"
              :key="reminder.id"
              class="reminder-card"
              :class="{ overdue: isOverdue(reminder), soon: isSoon(reminder) }"
            >
              <div class="reminder-check">
                <input
                  type="checkbox"
                  :checked="reminder.completed"
                  @change="toggleReminder(reminder)"
                />
              </div>
              <div class="reminder-content">
                <span class="reminder-title" :class="{ completed: reminder.completed }">
                  {{ reminder.title }}
                </span>
                <span class="reminder-due">
                  {{ formatReminderTime(reminder.due_date) }}
                </span>
              </div>
              <div class="reminder-actions">
                <button @click="editReminder(reminder)" class="btn-icon-small">✏️</button>
                <button @click="deleteReminder(reminder.id)" class="btn-icon-small">🗑️</button>
              </div>
            </div>

            <div v-if="reminders.length === 0" class="empty-state">
              <span>⏰</span>
              <p>No hay recordatorios</p>
            </div>
          </div>
        </div>

        <!-- Quick Control Actions -->
        <div class="controls-section">
          <div class="section-header">
            <h3>Acciones Rapidas</h3>
          </div>

          <div class="control-buttons">
            <button @click="executeAction('inventario')" class="control-btn">
              <span class="control-icon">📦</span>
              <span class="control-label">Revisar Inventario</span>
            </button>
            <button @click="executeAction('personal')" class="control-btn">
              <span class="control-icon">👥</span>
              <span class="control-label">Gestionar Personal</span>
            </button>
            <button @click="executeAction('mantenimiento')" class="control-btn">
              <span class="control-icon">🔧</span>
              <span class="control-label">Mantenimiento</span>
            </button>
            <button @click="generateReport" class="control-btn">
              <span class="control-icon">📊</span>
              <span class="control-label">Generar Reporte</span>
            </button>
          </div>
        </div>

        <!-- Action History -->
        <div class="history-section">
          <div class="section-header">
            <h3>Historial de Acciones</h3>
          </div>

          <div class="history-list">
            <div
              v-for="(action, index) in actionHistory.slice(0, 5)"
              :key="index"
              class="history-item"
            >
              <span class="history-icon">{{ action.icon }}</span>
              <span class="history-text">{{ action.description }}</span>
              <span class="history-time">{{ formatTime(action.timestamp) }}</span>
            </div>

            <div v-if="actionHistory.length === 0" class="empty-state small">
              <p>Sin acciones recientes</p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Note Modal -->
    <div v-if="showNoteModal" class="modal-overlay" @click.self="showNoteModal = false">
      <div class="modal-content">
        <div class="modal-header">
          <h3>{{ editingNote ? 'Editar Nota' : 'Nueva Nota' }}</h3>
          <button @click="showNoteModal = false" class="btn-close">✕</button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label>Categoria</label>
            <select v-model="noteForm.category">
              <option value="general">General</option>
              <option value="inventario">Inventario</option>
              <option value="personal">Personal</option>
              <option value="mantenimiento">Mantenimiento</option>
              <option value="pedidos">Pedidos</option>
              <option value="finanzas">Finanzas</option>
            </select>
          </div>
          <div class="form-group">
            <label>Contenido</label>
            <textarea
              v-model="noteForm.content"
              rows="4"
              placeholder="Escribe tu nota..."
            ></textarea>
          </div>
          <div class="form-group">
            <label>Tags (separados por coma)</label>
            <input
              v-model="noteForm.tagsInput"
              type="text"
              placeholder="ej: urgente, cocina, proveedor"
            />
          </div>
        </div>
        <div class="modal-footer">
          <button @click="showNoteModal = false" class="btn-cancel">Cancelar</button>
          <button @click="saveNote" class="btn-save">Guardar</button>
        </div>
      </div>
    </div>

    <!-- Reminder Modal -->
    <div v-if="showReminderModal" class="modal-overlay" @click.self="showReminderModal = false">
      <div class="modal-content">
        <div class="modal-header">
          <h3>{{ editingReminder ? 'Editar Recordatorio' : 'Nuevo Recordatorio' }}</h3>
          <button @click="showReminderModal = false" class="btn-close">✕</button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label>Titulo</label>
            <input
              v-model="reminderForm.title"
              type="text"
              placeholder="ej: Llamar al proveedor"
            />
          </div>
          <div class="form-group">
            <label>Fecha y Hora</label>
            <input
              v-model="reminderForm.due_date"
              type="datetime-local"
            />
          </div>
          <div class="form-group">
            <label>Repetir</label>
            <select v-model="reminderForm.repeat">
              <option value="none">No repetir</option>
              <option value="daily">Diariamente</option>
              <option value="weekly">Semanalmente</option>
              <option value="monthly">Mensualmente</option>
            </select>
          </div>
          <div class="form-group">
            <label>Prioridad</label>
            <select v-model="reminderForm.priority">
              <option value="low">Baja</option>
              <option value="medium">Media</option>
              <option value="high">Alta</option>
            </select>
          </div>
        </div>
        <div class="modal-footer">
          <button @click="showReminderModal = false" class="btn-cancel">Cancelar</button>
          <button @click="saveReminder" class="btn-save">Guardar</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, nextTick } from 'vue'

// ============================================================
// STATE
// ============================================================

// Connection
const isConnected = ref(false)
const lastUpdate = ref(new Date())

// Chat
const messages = ref([])
const inputText = ref('')
const isProcessing = ref(false)
const isRecording = ref(false)
const chatContainer = ref(null)
const chatInput = ref(null)

// Sensors
const sensors = reactive({
  temperature: null,
  humidity: null,
  co2: null,
  light: null,
  soil_moisture: null
})
const loadingSensors = ref(false)
const sensorAlerts = reactive({
  temperature: false,
  humidity: false,
  co2: false
})

// Notes
const notes = ref([])
const showNoteModal = ref(false)
const editingNote = ref(null)
const noteForm = reactive({
  category: 'general',
  content: '',
  tagsInput: ''
})

// Reminders
const reminders = ref([])
const showReminderModal = ref(false)
const editingReminder = ref(null)
const reminderForm = reactive({
  title: '',
  due_date: '',
  repeat: 'none',
  priority: 'medium'
})

// Alerts
const activeAlerts = ref([])

// Action History
const actionHistory = ref([])

// Config
const API_BASE = ''  // Relative URLs through nginx
const STORAGE_PREFIX = 'agriculture_assistant_'

// ============================================================
// QUICK ACTIONS
// ============================================================

const quickActions = [
  { id: 'status', icon: '📊', label: 'Ver resumen', text: 'Dame un resumen de las tareas pendientes' },
  { id: 'recommendations', icon: '💡', label: 'Sugerencias', text: 'Que deberia hacer hoy?' },
  { id: 'inventory', icon: '📦', label: 'Inventario', text: 'Que necesito revisar del inventario?' },
  { id: 'alerts', icon: '⚠️', label: 'Alertas', text: 'Hay alguna alerta o problema?' }
]

// ============================================================
// COMPUTED
// ============================================================

const environmentStatus = computed(() => {
  const temp = sensors.temperature
  const hum = sensors.humidity
  const co2 = sensors.co2

  if (!temp && !hum) return 'unknown'

  let score = 0
  if (temp >= 18 && temp <= 28) score++
  if (hum >= 40 && hum <= 70) score++
  if (!co2 || co2 < 1000) score++

  if (score >= 3) return 'optimal'
  if (score >= 2) return 'good'
  if (score >= 1) return 'warning'
  return 'critical'
})

const sortedReminders = computed(() => {
  return [...reminders.value]
    .filter(r => !r.completed)
    .sort((a, b) => new Date(a.due_date) - new Date(b.due_date))
    .concat(reminders.value.filter(r => r.completed))
})

// ============================================================
// CHAT FUNCTIONS
// ============================================================

async function sendMessage() {
  const text = inputText.value.trim()
  if (!text || isProcessing.value) return

  inputText.value = ''
  addMessage('user', text)

  isProcessing.value = true

  try {
    // Include sensor context in the message
    const context = {
      sensors: { ...sensors },
      alerts: activeAlerts.value.length,
      reminders_pending: reminders.value.filter(r => !r.completed).length
    }

    const response = await fetch(`${API_BASE}/api/admin/message`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: getSessionId(),
        message: text,
        voice_response: false,
        context_type: 'notes',
        dashboard_context: context
      })
    })

    if (response.ok) {
      const data = await response.json()
      addMessage('assistant', data.text)

      // Check if response contains actionable items
      if (data.suggested_action) {
        handleSuggestedAction(data.suggested_action)
      }
    } else {
      throw new Error('API Error')
    }
  } catch (error) {
    console.error('Error sending message:', error)
    addMessage('assistant', 'Disculpa, hubo un problema procesando tu mensaje. Intenta de nuevo.')
  } finally {
    isProcessing.value = false
  }
}

function sendQuickAction(text) {
  inputText.value = text
  sendMessage()
}

function addMessage(role, text) {
  messages.value.push({
    role,
    text,
    timestamp: new Date()
  })
  saveToStorage('messages', messages.value.slice(-50))
  scrollToBottom()
}

function clearChat() {
  messages.value = []
  localStorage.removeItem(STORAGE_PREFIX + 'messages')
}

function scrollToBottom() {
  nextTick(() => {
    if (chatContainer.value) {
      chatContainer.value.scrollTop = chatContainer.value.scrollHeight
    }
  })
}

// ============================================================
// VOICE FUNCTIONS
// ============================================================

let mediaRecorder = null
let audioChunks = []

async function toggleVoice() {
  if (isRecording.value) {
    stopRecording()
  } else {
    await startRecording()
  }
}

async function startRecording() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    mediaRecorder = new MediaRecorder(stream)
    audioChunks = []

    mediaRecorder.ondataavailable = (e) => {
      if (e.data.size > 0) audioChunks.push(e.data)
    }

    mediaRecorder.onstop = async () => {
      stream.getTracks().forEach(t => t.stop())
      await processVoice()
    }

    mediaRecorder.start()
    isRecording.value = true
  } catch (error) {
    console.error('Error accessing microphone:', error)
  }
}

function stopRecording() {
  if (mediaRecorder && mediaRecorder.state !== 'inactive') {
    mediaRecorder.stop()
  }
  isRecording.value = false
}

async function processVoice() {
  if (audioChunks.length === 0) return

  isProcessing.value = true

  try {
    const blob = new Blob(audioChunks, { type: 'audio/webm' })
    const formData = new FormData()
    formData.append('audio', blob, 'recording.webm')
    formData.append('session_id', getSessionId())

    const response = await fetch(`${API_BASE}/api/admin/voice`, {
      method: 'POST',
      body: formData
    })

    if (response.ok) {
      const data = await response.json()
      if (data.transcription) {
        addMessage('user', data.transcription)
      }
      if (data.response) {
        addMessage('assistant', data.response)
      }
    }
  } catch (error) {
    console.error('Error processing voice:', error)
  } finally {
    isProcessing.value = false
    audioChunks = []
  }
}

// ============================================================
// SENSORS FUNCTIONS
// ============================================================

async function refreshSensors() {
  loadingSensors.value = true

  try {
    const response = await fetch(`${API_BASE}/api/iot/sensors/latest`)
    if (response.ok) {
      const data = await response.json()

      for (const reading of (data.readings || [])) {
        if (sensors.hasOwnProperty(reading.sensor_type)) {
          sensors[reading.sensor_type] = reading.value
        }
      }

      // Check alerts
      sensorAlerts.temperature = sensors.temperature > 35 || sensors.temperature < 10
      sensorAlerts.humidity = sensors.humidity < 30 || sensors.humidity > 80
      sensorAlerts.co2 = sensors.co2 > 1000

      lastUpdate.value = new Date()
      isConnected.value = true
    }
  } catch (error) {
    console.error('Error loading sensors:', error)
    isConnected.value = false
  } finally {
    loadingSensors.value = false
  }
}

// ============================================================
// NOTES FUNCTIONS
// ============================================================

function saveNote() {
  const note = {
    id: editingNote.value?.id || Date.now(),
    category: noteForm.category,
    content: noteForm.content,
    tags: noteForm.tagsInput.split(',').map(t => t.trim()).filter(t => t),
    created_at: editingNote.value?.created_at || new Date().toISOString(),
    updated_at: new Date().toISOString()
  }

  if (editingNote.value) {
    const index = notes.value.findIndex(n => n.id === note.id)
    if (index >= 0) notes.value[index] = note
  } else {
    notes.value.unshift(note)
  }

  saveToStorage('notes', notes.value)
  resetNoteForm()
  showNoteModal.value = false
}

function editNote(note) {
  editingNote.value = note
  noteForm.category = note.category
  noteForm.content = note.content
  noteForm.tagsInput = note.tags?.join(', ') || ''
  showNoteModal.value = true
}

function deleteNote(id) {
  if (confirm('Eliminar esta nota?')) {
    notes.value = notes.value.filter(n => n.id !== id)
    saveToStorage('notes', notes.value)
  }
}

function resetNoteForm() {
  editingNote.value = null
  noteForm.category = 'general'
  noteForm.content = ''
  noteForm.tagsInput = ''
}

function getCategoryIcon(category) {
  const icons = {
    general: '📝',
    inventario: '📦',
    personal: '👥',
    mantenimiento: '🔧',
    pedidos: '🛒',
    finanzas: '💰'
  }
  return icons[category] || '📝'
}

// ============================================================
// REMINDERS FUNCTIONS
// ============================================================

function saveReminder() {
  const reminder = {
    id: editingReminder.value?.id || Date.now(),
    title: reminderForm.title,
    due_date: reminderForm.due_date,
    repeat: reminderForm.repeat,
    priority: reminderForm.priority,
    completed: editingReminder.value?.completed || false,
    created_at: editingReminder.value?.created_at || new Date().toISOString()
  }

  if (editingReminder.value) {
    const index = reminders.value.findIndex(r => r.id === reminder.id)
    if (index >= 0) reminders.value[index] = reminder
  } else {
    reminders.value.push(reminder)
  }

  saveToStorage('reminders', reminders.value)
  resetReminderForm()
  showReminderModal.value = false
}

function editReminder(reminder) {
  editingReminder.value = reminder
  reminderForm.title = reminder.title
  reminderForm.due_date = reminder.due_date
  reminderForm.repeat = reminder.repeat
  reminderForm.priority = reminder.priority
  showReminderModal.value = true
}

function deleteReminder(id) {
  if (confirm('Eliminar este recordatorio?')) {
    reminders.value = reminders.value.filter(r => r.id !== id)
    saveToStorage('reminders', reminders.value)
  }
}

function toggleReminder(reminder) {
  reminder.completed = !reminder.completed
  saveToStorage('reminders', reminders.value)

  if (reminder.completed) {
    addToHistory('✅', `Completado: ${reminder.title}`)
  }
}

function resetReminderForm() {
  editingReminder.value = null
  reminderForm.title = ''
  reminderForm.due_date = ''
  reminderForm.repeat = 'none'
  reminderForm.priority = 'medium'
}

function isOverdue(reminder) {
  return !reminder.completed && new Date(reminder.due_date) < new Date()
}

function isSoon(reminder) {
  if (reminder.completed) return false
  const due = new Date(reminder.due_date)
  const now = new Date()
  const diff = due - now
  return diff > 0 && diff < 3600000 // Less than 1 hour
}

// ============================================================
// ALERTS FUNCTIONS
// ============================================================

function dismissAlert(id) {
  activeAlerts.value = activeAlerts.value.filter(a => a.id !== id)
}

function getAlertIcon(severity) {
  const icons = { info: 'ℹ️', warning: '⚠️', critical: '🔴', emergency: '🚨' }
  return icons[severity] || '⚠️'
}

// ============================================================
// CONTROL ACTIONS
// ============================================================

function executeAction(actionType) {
  const actions = {
    inventario: { icon: '📦', description: 'Revision de inventario iniciada' },
    personal: { icon: '👥', description: 'Gestion de personal abierta' },
    mantenimiento: { icon: '🔧', description: 'Tarea de mantenimiento registrada' }
  }

  const action = actions[actionType]
  if (action) {
    addToHistory(action.icon, action.description)
    console.log(`Executing action: ${actionType}`)
  }
}

function generateReport() {
  addToHistory('📊', 'Reporte generado')
  sendQuickAction('Genera un reporte completo del estado actual')
}

function addToHistory(icon, description) {
  actionHistory.value.unshift({
    icon,
    description,
    timestamp: new Date()
  })
  actionHistory.value = actionHistory.value.slice(0, 20)
  saveToStorage('history', actionHistory.value)
}

function handleSuggestedAction(action) {
  // Handle suggested actions from assistant
  console.log('Suggested action:', action)
}

// ============================================================
// ENVIRONMENT EVALUATION
// ============================================================

function getEnvironmentIcon() {
  const icons = {
    optimal: '✅',
    good: '👍',
    warning: '⚠️',
    critical: '🔴',
    unknown: '❓'
  }
  return icons[environmentStatus.value]
}

function getEnvironmentText() {
  const texts = {
    optimal: 'Condiciones optimas',
    good: 'Condiciones buenas',
    warning: 'Requiere atencion',
    critical: 'Condiciones criticas',
    unknown: 'Sin datos'
  }
  return texts[environmentStatus.value]
}

// ============================================================
// UTILITIES
// ============================================================

function getSessionId() {
  let sessionId = localStorage.getItem(STORAGE_PREFIX + 'session_id')
  if (!sessionId) {
    sessionId = `agri_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
    localStorage.setItem(STORAGE_PREFIX + 'session_id', sessionId)
  }
  return sessionId
}

function formatTime(date) {
  if (!date) return '--'
  return new Date(date).toLocaleTimeString('es-MX', {
    hour: '2-digit',
    minute: '2-digit'
  })
}

function formatDate(date) {
  if (!date) return '--'
  return new Date(date).toLocaleDateString('es-MX', {
    day: 'numeric',
    month: 'short'
  })
}

function formatReminderTime(date) {
  if (!date) return '--'
  const d = new Date(date)
  const now = new Date()
  const diff = d - now

  if (diff < 0) return 'Vencido'
  if (diff < 3600000) return `En ${Math.round(diff / 60000)} min`
  if (diff < 86400000) return `Hoy ${formatTime(d)}`

  return d.toLocaleDateString('es-MX', {
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit'
  })
}

function formatMessage(text) {
  if (!text) return ''
  return text
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\n/g, '<br>')
}

function saveToStorage(key, data) {
  try {
    localStorage.setItem(STORAGE_PREFIX + key, JSON.stringify(data))
  } catch (e) {
    console.error('Error saving to storage:', e)
  }
}

function loadFromStorage(key) {
  try {
    const data = localStorage.getItem(STORAGE_PREFIX + key)
    return data ? JSON.parse(data) : null
  } catch (e) {
    console.error('Error loading from storage:', e)
    return null
  }
}

// ============================================================
// LIFECYCLE
// ============================================================

let refreshInterval = null

onMounted(() => {
  // Load saved data
  messages.value = loadFromStorage('messages') || []
  notes.value = loadFromStorage('notes') || []
  reminders.value = loadFromStorage('reminders') || []
  actionHistory.value = loadFromStorage('history') || []

  // Load sensors
  refreshSensors()

  // Auto-refresh every 30 seconds
  refreshInterval = setInterval(refreshSensors, 30000)

  // Focus chat input
  nextTick(() => chatInput.value?.focus())
})

onUnmounted(() => {
  if (refreshInterval) clearInterval(refreshInterval)
  if (mediaRecorder && mediaRecorder.state !== 'inactive') {
    mediaRecorder.stop()
  }
})
</script>

<style scoped>
.agriculture-assistant {
  min-height: 100%;
}

/* Header */
.page-header {
  background: linear-gradient(135deg, #2d5a27 0%, #4a7c45 100%);
  color: white;
  padding: 1.5rem 2rem;
  border-radius: 12px;
  margin-bottom: 1.5rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.page-header h1 {
  margin: 0;
  font-size: 1.75rem;
}

.subtitle {
  margin: 0.25rem 0 0 0;
  opacity: 0.9;
}

.header-status {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 0.25rem;
}

.status-indicator {
  padding: 0.4rem 0.8rem;
  border-radius: 15px;
  font-size: 0.8rem;
  font-weight: 600;
  background: rgba(231, 76, 60, 0.3);
}

.status-indicator.online {
  background: rgba(39, 174, 96, 0.3);
}

.last-update {
  font-size: 0.75rem;
  opacity: 0.8;
}

/* Main Layout */
.main-layout {
  display: grid;
  grid-template-columns: 1fr 380px;
  gap: 1.5rem;
}

/* Panels */
.left-panel,
.right-panel {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

/* Sections */
.chat-section,
.notes-section,
.environment-section,
.alerts-section,
.reminders-section,
.controls-section,
.history-section {
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  overflow: hidden;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.25rem;
  border-bottom: 1px solid #eee;
}

.section-header h3 {
  margin: 0;
  font-size: 1rem;
  color: #2c3e50;
}

/* Chat Section */
.chat-section {
  display: flex;
  flex-direction: column;
  min-height: 450px;
}

.chat-messages {
  flex: 1;
  padding: 1rem;
  overflow-y: auto;
  max-height: 300px;
  background: #f8f9fa;
}

.welcome-message {
  text-align: center;
  padding: 2rem 1rem;
}

.welcome-icon {
  font-size: 3rem;
  margin-bottom: 0.5rem;
}

.welcome-message h4 {
  margin: 0 0 0.5rem 0;
  color: #2d5a27;
}

.welcome-message ul {
  text-align: left;
  max-width: 280px;
  margin: 1rem auto;
  padding-left: 1.5rem;
}

.welcome-message li {
  margin: 0.4rem 0;
  color: #666;
}

.chat-message {
  display: flex;
  gap: 0.75rem;
  margin-bottom: 1rem;
}

.chat-message.user {
  flex-direction: row-reverse;
}

.message-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: #e9ecef;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.1rem;
  flex-shrink: 0;
}

.chat-message.user .message-avatar {
  background: #2d5a27;
}

.message-content {
  max-width: 75%;
}

.message-text {
  padding: 0.75rem 1rem;
  border-radius: 12px;
  background: white;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
  line-height: 1.4;
}

.chat-message.user .message-text {
  background: linear-gradient(135deg, #2d5a27 0%, #4a7c45 100%);
  color: white;
}

.message-time {
  font-size: 0.7rem;
  color: #999;
  margin-top: 0.25rem;
  display: block;
}

.typing-dots {
  display: flex;
  gap: 4px;
  padding: 0.75rem 1rem;
}

.typing-dots span {
  width: 8px;
  height: 8px;
  background: #999;
  border-radius: 50%;
  animation: bounce 1.4s infinite ease-in-out;
}

.typing-dots span:nth-child(1) { animation-delay: -0.32s; }
.typing-dots span:nth-child(2) { animation-delay: -0.16s; }

@keyframes bounce {
  0%, 80%, 100% { transform: scale(0); }
  40% { transform: scale(1); }
}

/* Quick Actions */
.quick-actions {
  display: flex;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  border-top: 1px solid #eee;
  overflow-x: auto;
}

.quick-action-btn {
  padding: 0.4rem 0.75rem;
  background: #f0f7ee;
  border: 1px solid #c8e6c9;
  border-radius: 15px;
  font-size: 0.8rem;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.2s;
}

.quick-action-btn:hover {
  background: #2d5a27;
  color: white;
  border-color: #2d5a27;
}

/* Chat Input */
.chat-input-area {
  display: flex;
  gap: 0.5rem;
  padding: 1rem;
  border-top: 1px solid #eee;
}

.chat-input-area input {
  flex: 1;
  padding: 0.75rem 1rem;
  border: 2px solid #e0e0e0;
  border-radius: 10px;
  font-size: 0.95rem;
  transition: border-color 0.2s;
}

.chat-input-area input:focus {
  outline: none;
  border-color: #2d5a27;
}

.btn-voice,
.btn-send {
  width: 42px;
  height: 42px;
  border: none;
  border-radius: 10px;
  cursor: pointer;
  font-size: 1.1rem;
  transition: all 0.2s;
}

.btn-voice {
  background: #f0f0f0;
}

.btn-voice:hover {
  background: #e0e0e0;
}

.btn-voice.recording {
  background: #fee2e2;
  animation: pulse 1s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.6; }
}

.btn-send {
  background: linear-gradient(135deg, #2d5a27 0%, #4a7c45 100%);
  color: white;
}

.btn-send:hover:not(:disabled) {
  transform: scale(1.05);
}

.btn-send:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Notes Section */
.notes-section {
  max-height: 350px;
  display: flex;
  flex-direction: column;
}

.notes-list {
  flex: 1;
  overflow-y: auto;
  padding: 1rem;
}

.note-card {
  background: #f8f9fa;
  border-radius: 8px;
  padding: 0.75rem;
  margin-bottom: 0.75rem;
  border-left: 4px solid #95a5a6;
}

.note-card.inventario { border-left-color: #3498db; }
.note-card.personal { border-left-color: #9b59b6; }
.note-card.mantenimiento { border-left-color: #e74c3c; }
.note-card.pedidos { border-left-color: #f39c12; }
.note-card.finanzas { border-left-color: #1abc9c; }

.note-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.note-category-icon {
  font-size: 1rem;
}

.note-date {
  flex: 1;
  font-size: 0.75rem;
  color: #999;
}

.note-actions {
  display: flex;
  gap: 0.25rem;
  opacity: 0;
  transition: opacity 0.2s;
}

.note-card:hover .note-actions {
  opacity: 1;
}

.note-content {
  font-size: 0.9rem;
  color: #333;
  line-height: 1.4;
}

.note-tags {
  display: flex;
  gap: 0.25rem;
  margin-top: 0.5rem;
  flex-wrap: wrap;
}

.tag {
  padding: 0.15rem 0.5rem;
  background: #e0e0e0;
  border-radius: 10px;
  font-size: 0.7rem;
  color: #666;
}

/* Environment Section */
.sensors-summary {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 0.75rem;
  padding: 1rem;
}

.sensor-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem;
  background: #f8f9fa;
  border-radius: 8px;
  position: relative;
}

.sensor-item.alert {
  background: #fee2e2;
}

.sensor-icon {
  font-size: 1.5rem;
}

.sensor-info {
  display: flex;
  flex-direction: column;
}

.sensor-value {
  font-weight: 700;
  font-size: 1.1rem;
  color: #2c3e50;
}

.sensor-label {
  font-size: 0.75rem;
  color: #999;
}

.alert-badge {
  position: absolute;
  top: 0.25rem;
  right: 0.25rem;
  width: 18px;
  height: 18px;
  background: #e74c3c;
  color: white;
  border-radius: 50%;
  font-size: 0.7rem;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
}

.environment-evaluation {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 0.75rem;
  margin: 0 1rem 1rem 1rem;
  border-radius: 8px;
  font-weight: 600;
}

.environment-evaluation.optimal {
  background: #d4edda;
  color: #155724;
}

.environment-evaluation.good {
  background: #d1ecf1;
  color: #0c5460;
}

.environment-evaluation.warning {
  background: #fff3cd;
  color: #856404;
}

.environment-evaluation.critical {
  background: #f8d7da;
  color: #721c24;
}

.environment-evaluation.unknown {
  background: #e9ecef;
  color: #6c757d;
}

/* Alerts Section */
.alerts-section .section-header {
  background: #fff3cd;
}

.alert-count {
  background: #e74c3c;
  color: white;
  padding: 0.2rem 0.6rem;
  border-radius: 10px;
  font-size: 0.8rem;
  font-weight: bold;
}

.alerts-list {
  padding: 0.75rem;
}

.alert-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.6rem;
  background: #f8f9fa;
  border-radius: 6px;
  margin-bottom: 0.5rem;
  border-left: 3px solid #f39c12;
}

.alert-item.critical {
  border-left-color: #e74c3c;
  background: #fee2e2;
}

.alert-icon {
  font-size: 1.1rem;
}

.alert-content {
  flex: 1;
}

.alert-message {
  display: block;
  font-size: 0.85rem;
}

.alert-time {
  font-size: 0.7rem;
  color: #999;
}

.btn-dismiss {
  background: none;
  border: none;
  color: #999;
  cursor: pointer;
  font-size: 0.9rem;
}

/* Reminders Section */
.reminders-list {
  padding: 0.75rem;
  max-height: 250px;
  overflow-y: auto;
}

.reminder-card {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.6rem;
  background: #f8f9fa;
  border-radius: 6px;
  margin-bottom: 0.5rem;
}

.reminder-card.overdue {
  background: #fee2e2;
  border-left: 3px solid #e74c3c;
}

.reminder-card.soon {
  background: #fff3cd;
  border-left: 3px solid #f39c12;
}

.reminder-check input {
  width: 18px;
  height: 18px;
  cursor: pointer;
}

.reminder-content {
  flex: 1;
}

.reminder-title {
  display: block;
  font-size: 0.9rem;
}

.reminder-title.completed {
  text-decoration: line-through;
  color: #999;
}

.reminder-due {
  font-size: 0.75rem;
  color: #666;
}

.reminder-actions {
  display: flex;
  gap: 0.25rem;
  opacity: 0;
  transition: opacity 0.2s;
}

.reminder-card:hover .reminder-actions {
  opacity: 1;
}

/* Controls Section */
.control-buttons {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 0.75rem;
  padding: 1rem;
}

.control-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  padding: 1rem;
  background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
  border: 2px solid #dee2e6;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s;
}

.control-btn:hover {
  border-color: #2d5a27;
  background: linear-gradient(135deg, #f0f7ee 0%, #e8f5e9 100%);
}

.control-icon {
  font-size: 1.5rem;
}

.control-label {
  font-size: 0.8rem;
  font-weight: 600;
  color: #2c3e50;
}

/* History Section */
.history-list {
  padding: 0.75rem;
  max-height: 180px;
  overflow-y: auto;
}

.history-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem;
  border-bottom: 1px solid #eee;
}

.history-icon {
  font-size: 1rem;
}

.history-text {
  flex: 1;
  font-size: 0.85rem;
  color: #666;
}

.history-time {
  font-size: 0.7rem;
  color: #999;
}

/* Empty States */
.empty-state {
  text-align: center;
  padding: 2rem 1rem;
  color: #999;
}

.empty-state span {
  font-size: 2rem;
  display: block;
  margin-bottom: 0.5rem;
}

.empty-state.small {
  padding: 1rem;
}

.empty-state.small span {
  font-size: 1.5rem;
}

/* Buttons */
.btn-icon {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 1rem;
  opacity: 0.7;
  transition: opacity 0.2s;
}

.btn-icon:hover {
  opacity: 1;
}

.btn-icon-small {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 0.85rem;
  padding: 0.2rem;
  opacity: 0.6;
}

.btn-icon-small:hover {
  opacity: 1;
}

.btn-add {
  padding: 0.4rem 0.8rem;
  background: #2d5a27;
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 0.8rem;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-add:hover {
  background: #1e3d1a;
}

/* Modal */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  border-radius: 12px;
  width: 90%;
  max-width: 450px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.25rem;
  border-bottom: 1px solid #eee;
}

.modal-header h3 {
  margin: 0;
}

.btn-close {
  background: none;
  border: none;
  font-size: 1.25rem;
  cursor: pointer;
  color: #999;
}

.modal-body {
  padding: 1.25rem;
}

.form-group {
  margin-bottom: 1rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.4rem;
  font-weight: 600;
  font-size: 0.9rem;
  color: #333;
}

.form-group input,
.form-group select,
.form-group textarea {
  width: 100%;
  padding: 0.6rem 0.8rem;
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  font-size: 0.95rem;
  transition: border-color 0.2s;
}

.form-group input:focus,
.form-group select:focus,
.form-group textarea:focus {
  outline: none;
  border-color: #2d5a27;
}

.form-group textarea {
  resize: vertical;
  min-height: 80px;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  padding: 1rem 1.25rem;
  border-top: 1px solid #eee;
}

.btn-cancel {
  padding: 0.6rem 1.25rem;
  background: #e0e0e0;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 600;
}

.btn-save {
  padding: 0.6rem 1.25rem;
  background: #2d5a27;
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 600;
}

.btn-save:hover {
  background: #1e3d1a;
}

/* Responsive */
@media (max-width: 1024px) {
  .main-layout {
    grid-template-columns: 1fr;
  }

  .right-panel {
    order: -1;
  }
}

@media (max-width: 600px) {
  .page-header {
    flex-direction: column;
    text-align: center;
    gap: 1rem;
  }

  .sensors-summary {
    grid-template-columns: 1fr;
  }

  .control-buttons {
    grid-template-columns: 1fr;
  }
}
</style>
