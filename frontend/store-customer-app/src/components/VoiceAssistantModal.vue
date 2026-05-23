<template>
  <Transition
    enter-active-class="transition duration-300 ease-out"
    enter-from-class="opacity-0 translate-y-4 scale-95"
    enter-to-class="opacity-100 translate-y-0 scale-100"
    leave-active-class="transition duration-200 ease-in"
    leave-from-class="opacity-100 translate-y-0 scale-100"
    leave-to-class="opacity-0 translate-y-4 scale-95"
  >
    <div v-if="chatStore.isOpen" class="modal-fixed-container">
      <div class="modal-container">
        <!-- Header -->
        <div class="modal-header">
          <div class="header-info">
            <h2>Sofia - {{ storeName }}</h2>
            <span v-if="!chatStore.isOnline" class="offline-badge">
              Sin conexión - Solo texto
            </span>
          </div>
          <button class="close-button" @click="chatStore.closeChat">
            <svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
              <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
            </svg>
          </button>
        </div>

        <!-- Conversation Area -->
        <div class="conversation-area" ref="conversationRef">
          <!-- Welcome Message -->
          <div v-if="chatStore.messages.length === 0" class="welcome-message">
            <div class="welcome-icon">
              <span class="icon-emoji">{{ storeIcon }}</span>
            </div>
            <h3>¡Hola! Soy Sofia {{ storeIcon }}</h3>
            <p>{{ storeWelcome }}</p>
            <p class="text-sm text-gray-600 mt-2">Puedes escribir o usar tu voz para hacer tu pedido</p>

            <!-- Quick Actions -->
            <div class="quick-actions">
              <button
                v-for="action in quickActions"
                :key="action.message"
                class="quick-action-btn"
                @click="handleQuickMessage(action.message)"
              >
                <span class="action-icon">{{ action.icon }}</span>
                <span class="action-label">{{ action.label }}</span>
              </button>
            </div>
          </div>

          <!-- Messages -->
          <div v-for="(msg, index) in chatStore.messages" :key="index" class="message" :class="msg.type">
            <div class="message-avatar">
              <svg v-if="msg.type === 'user'" viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
                <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/>
              </svg>
              <svg v-else viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
                <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2z"/>
              </svg>
            </div>
            <div class="message-content">
              <span class="message-sender">{{ msg.sender }}</span>
              <p class="message-text">{{ msg.text }}</p>
            </div>
          </div>

          <!-- Processing Indicator -->
          <div v-if="chatStore.isProcessing" class="message assistant">
            <div class="message-avatar">
              <svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
                <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2z"/>
              </svg>
            </div>
            <div class="message-content">
              <span class="message-sender">Sofia</span>
              <div class="typing-indicator">
                <span></span><span></span><span></span>
              </div>
            </div>
          </div>
        </div>

        <!-- Input Area -->
        <div class="input-area">
          <ChatInput
            v-model="textInput"
            :disabled="chatStore.isProcessing || chatStore.isRecording"
            @submit="sendTextMessage(textInput)"
            placeholder="Escribe tu mensaje..."
          />

          <!-- Voice Button -->
          <VoiceButton
            v-if="chatStore.isVoiceEnabled"
            :isRecording="chatStore.isRecording"
            :isPlaying="chatStore.isPlaying"
            :disabled="chatStore.isProcessing"
            size="medium"
            @start="startRecording"
            @stop="stopRecording"
          />
        </div>
      </div>
    </div>
  </Transition>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useChatStore } from '../stores/chat'
import ChatInput from './ChatInput.vue'
import VoiceButton from './VoiceButton.vue'

const chatStore = useChatStore()
const conversationRef = ref(null)
const textInput = ref('')

// MediaRecorder for audio
let mediaRecorder = null
let audioChunks = []

// Sales agent service URL
const SALES_AGENT_URL = 'https://sales-agent-service-308574626875.us-central1.run.app'

// Detect tenant from environment or URL
const tenantId = ref(import.meta.env.VITE_TENANT_ID || 'tenant_pharmacy_001')

// Store configurations
const storeConfigs = {
  tenant_pharmacy_001: {
    name: 'Farmacia Santa Fe',
    icon: '💊',
    welcome: 'Tu farmacia de confianza',
    quickActions: [
      { icon: '💊', label: 'Ver medicamentos', message: 'Muéstrame medicamentos disponibles' },
      { icon: '🔍', label: 'Buscar producto', message: 'Necesito buscar un medicamento' },
      { icon: '❓', label: 'Ayuda', message: 'Ayuda' }
    ]
  },
  tenant_wine_001: {
    name: 'Vinetería Don Juan',
    icon: '🍷',
    welcome: 'La mejor selección de vinos',
    quickActions: [
      { icon: '🍷', label: 'Ver vinos', message: 'Muéstrame los vinos disponibles' },
      { icon: '🥃', label: 'Ver licores', message: 'Quiero ver licores' },
      { icon: '❓', label: 'Ayuda', message: 'Ayuda' }
    ]
  }
}

const currentConfig = computed(() => storeConfigs[tenantId.value] || storeConfigs.tenant_pharmacy_001)
const storeName = computed(() => currentConfig.value.name)
const storeIcon = computed(() => currentConfig.value.icon)
const storeWelcome = computed(() => currentConfig.value.welcome)
const quickActions = computed(() => currentConfig.value.quickActions)

onMounted(async () => {
  console.log('[StoreVoiceAssistant] Mounted, tenant:', tenantId.value)
  chatStore.initConnectionListeners()
  await initSession()
})

onUnmounted(() => {
  chatStore.removeConnectionListeners()
  if (mediaRecorder && mediaRecorder.state === 'recording') {
    stopRecording()
  }
})

const scrollToBottom = async () => {
  await nextTick()
  if (conversationRef.value) {
    conversationRef.value.scrollTop = conversationRef.value.scrollHeight
  }
}

const initSession = async () => {
  try {
    const response = await fetch(`${SALES_AGENT_URL}/api/session/init`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tenant_id: tenantId.value })
    })

    if (response.ok) {
      const data = await response.json()
      chatStore.setSession(data.session_id, null)
      console.log('[StoreVoiceAssistant] Session initialized:', data.session_id)
    } else {
      console.error('[StoreVoiceAssistant] Failed to initialize session:', response.status)
    }
  } catch (error) {
    console.error('[StoreVoiceAssistant] Session init error:', error)
    chatStore.addMessage('Sistema', 'Error al conectar. Por favor recarga la página.', 'assistant')
  }
}

const handleQuickMessage = (message) => {
  sendTextMessage(message)
}

const sendTextMessage = async (text) => {
  if (!text || !text.trim() || !chatStore.sessionId) {
    return
  }

  textInput.value = ''
  chatStore.addMessage('Tú', text, 'user')
  chatStore.setProcessing(true)
  scrollToBottom()

  try {
    const response = await fetch(`${SALES_AGENT_URL}/api/text/process`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: chatStore.sessionId,
        text: text,
        tenant_id: tenantId.value
      })
    })

    if (response.ok) {
      const data = await response.json()
      const responseText = data.response || data.response_text || 'Sin respuesta'
      chatStore.addMessage('Sofia', responseText, 'assistant')

      if (data.visual_data) {
        chatStore.setVisualData(data.visual_data)
      }
    } else {
      chatStore.addMessage('Sofia', 'Lo siento, hubo un error.', 'assistant')
    }
  } catch (error) {
    chatStore.addMessage('Sofia', 'No pude conectar con el servicio.', 'assistant')
  } finally {
    chatStore.setProcessing(false)
    scrollToBottom()
  }
}

const startRecording = async () => {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    mediaRecorder = new MediaRecorder(stream)
    audioChunks = []

    mediaRecorder.ondataavailable = (event) => {
      audioChunks.push(event.data)
    }

    mediaRecorder.onstop = async () => {
      const audioBlob = new Blob(audioChunks, { type: 'audio/webm' })
      await sendVoiceMessage(audioBlob)
      stream.getTracks().forEach(track => track.stop())
    }

    mediaRecorder.start()
    chatStore.setRecording(true)
  } catch (error) {
    console.error('[StoreVoiceAssistant] Recording error:', error)
  }
}

const stopRecording = () => {
  if (mediaRecorder && mediaRecorder.state === 'recording') {
    mediaRecorder.stop()
    chatStore.setRecording(false)
  }
}

const sendVoiceMessage = async (audioBlob) => {
  if (!chatStore.sessionId) return

  chatStore.setProcessing(true)

  try {
    const formData = new FormData()
    formData.append('audio', audioBlob, 'recording.webm')
    formData.append('session_id', chatStore.sessionId)
    formData.append('tenant_id', tenantId.value)

    const response = await fetch(`${SALES_AGENT_URL}/api/voice/process`, {
      method: 'POST',
      body: formData
    })

    if (response.ok) {
      const data = await response.json()

      if (data.transcription) {
        chatStore.addMessage('Tú', data.transcription, 'user')
      }

      const responseText = data.response || data.response_text || 'Sin respuesta'
      chatStore.addMessage('Sofia', responseText, 'assistant')

      if (data.visual_data) {
        chatStore.setVisualData(data.visual_data)
      }

      if (data.audio_url) {
        await playAudio(data.audio_url)
      }
    } else {
      chatStore.addMessage('Sofia', 'No pude procesar el audio.', 'assistant')
    }
  } catch (error) {
    chatStore.addMessage('Sofia', 'Error al procesar la voz.', 'assistant')
  } finally {
    chatStore.setProcessing(false)
    scrollToBottom()
  }
}

const playAudio = async (audioUrl) => {
  try {
    chatStore.setPlaying(true)
    const audio = new Audio(audioUrl)

    audio.onended = () => {
      chatStore.setPlaying(false)
    }

    audio.onerror = () => {
      chatStore.setPlaying(false)
    }

    await audio.play()
  } catch (error) {
    chatStore.setPlaying(false)
  }
}
</script>

<style scoped>
/* Same styles as taxi version */
.modal-fixed-container {
  position: fixed;
  top: 0;
  right: 0;
  bottom: 0;
  width: 100%;
  max-width: 450px;
  background: white;
  box-shadow: -4px 0 15px rgba(0, 0, 0, 0.1);
  z-index: 1000;
  display: flex;
  flex-direction: column;
}

.modal-container {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.5rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.header-info h2 {
  margin: 0;
  font-size: 1.25rem;
  font-weight: 600;
}

.offline-badge {
  display: inline-block;
  font-size: 0.75rem;
  background: rgba(255, 255, 255, 0.2);
  padding: 0.25rem 0.5rem;
  border-radius: 12px;
  margin-top: 0.25rem;
}

.close-button {
  background: rgba(255, 255, 255, 0.2);
  border: none;
  border-radius: 50%;
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: background 0.2s;
}

.close-button:hover {
  background: rgba(255, 255, 255, 0.3);
}

.conversation-area {
  flex: 1;
  overflow-y: auto;
  padding: 1.5rem;
  background: #f9fafb;
}

.welcome-message {
  text-align: center;
  padding: 2rem 1rem;
}

.welcome-icon {
  display: flex;
  justify-content: center;
  margin-bottom: 1rem;
}

.icon-emoji {
  font-size: 3rem;
}

.welcome-message h3 {
  font-size: 1.5rem;
  font-weight: 600;
  margin: 0 0 0.5rem 0;
  color: #1f2937;
}

.welcome-message p {
  color: #6b7280;
  margin: 0.5rem 0;
}

.quick-actions {
  display: grid;
  grid-template-columns: 1fr;
  gap: 0.75rem;
  margin-top: 1.5rem;
}

.quick-action-btn {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 1rem;
  background: white;
  border: 2px solid #e5e7eb;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s;
  text-align: left;
}

.quick-action-btn:hover {
  border-color: #667eea;
  background: #f3f4f6;
  transform: translateY(-2px);
}

.action-icon {
  font-size: 1.5rem;
}

.action-label {
  font-weight: 500;
  color: #374151;
}

.message {
  display: flex;
  gap: 0.75rem;
  margin-bottom: 1rem;
}

.message.user {
  flex-direction: row-reverse;
}

.message-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.message.user .message-avatar {
  background: #667eea;
  color: white;
}

.message.assistant .message-avatar {
  background: #e5e7eb;
  color: #6b7280;
}

.message-content {
  max-width: 75%;
}

.message.user .message-content {
  text-align: right;
}

.message-sender {
  font-size: 0.75rem;
  font-weight: 600;
  color: #6b7280;
  display: block;
  margin-bottom: 0.25rem;
}

.message-text {
  background: white;
  padding: 0.75rem 1rem;
  border-radius: 12px;
  margin: 0;
  color: #1f2937;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}

.message.user .message-text {
  background: #667eea;
  color: white;
}

.typing-indicator {
  display: flex;
  gap: 0.25rem;
  padding: 0.75rem 1rem;
  background: white;
  border-radius: 12px;
}

.typing-indicator span {
  width: 8px;
  height: 8px;
  background: #9ca3af;
  border-radius: 50%;
  animation: typing 1.4s infinite;
}

.typing-indicator span:nth-child(2) {
  animation-delay: 0.2s;
}

.typing-indicator span:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes typing {
  0%, 60%, 100% {
    transform: translateY(0);
    opacity: 0.7;
  }
  30% {
    transform: translateY(-10px);
    opacity: 1;
  }
}

.input-area {
  padding: 1rem 1.5rem;
  background: white;
  border-top: 1px solid #e5e7eb;
  display: flex;
  gap: 0.75rem;
  align-items: center;
}

@media (max-width: 640px) {
  .modal-fixed-container {
    max-width: 100%;
  }
}
</style>
