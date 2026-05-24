<template>
  <Transition
    enter-active-class="transition duration-300 ease-out"
    enter-from-class="opacity-0 translate-y-4 scale-95"
    enter-to-class="opacity-100 translate-y-0 scale-100"
    leave-active-class="transition duration-200 ease-in"
    leave-from-class="opacity-100 translate-y-0 scale-100"
    leave-to-class="opacity-0 translate-y-4 scale-95"
  >
    <div v-if="chatStore.isOpen" class="sofia-container">
      <div class="sofia-modal">

        <!-- Header -->
        <div class="sofia-header">
          <div class="header-left">
            <span class="sofia-avatar">🚕</span>
            <div>
              <h2 class="sofia-title">Sofia</h2>
              <span class="sofia-sub">Asistente de viajes</span>
            </div>
          </div>
          <button class="sofia-close" @click="chatStore.closeChat">
            <svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
              <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
            </svg>
          </button>
        </div>

        <!-- Conversation -->
        <div class="sofia-conversation" ref="conversationRef">

          <!-- Welcome -->
          <div v-if="chatStore.messages.length === 0 && !pendingLocation && searchResults.length === 0" class="sofia-welcome">
            <div class="welcome-taxi">🚕</div>
            <h3>¡Hola! Soy Sofia</h3>
            <p>Dime a dónde quieres ir y pre-lleno el destino por ti.</p>
            <p class="welcome-hint">Puedes escribir o usar tu voz 🎤</p>
            <div class="sofia-quickactions">
              <button class="qa-btn" @click="processMessage('Llévame al aeropuerto')">✈️ Aeropuerto</button>
              <button class="qa-btn" @click="processMessage('Al centro histórico')">🏛️ Centro</button>
              <button class="qa-btn" @click="processMessage('Al hospital general')">🏥 Hospital</button>
              <button class="qa-btn" @click="processMessage('A la central de autobuses')">🚌 Central</button>
            </div>
          </div>

          <!-- Messages -->
          <div
            v-for="(msg, i) in chatStore.messages"
            :key="i"
            class="sofia-message"
            :class="msg.type === 'user' ? 'msg-user' : 'msg-sofia'"
          >
            <p class="msg-text">{{ msg.text }}</p>
          </div>

          <!-- Typing indicator -->
          <div v-if="chatStore.isProcessing" class="sofia-message msg-sofia">
            <div class="typing-dots">
              <span></span><span></span><span></span>
            </div>
          </div>

          <!-- Confirmation card -->
          <div v-if="pendingLocation" class="confirm-card">
            <p class="confirm-label">¿Es este tu destino?</p>
            <div class="confirm-place">
              <span class="place-pin">📍</span>
              <div class="place-info">
                <p class="place-name">{{ pendingLocation.name }}</p>
                <p class="place-address">{{ pendingLocation.address }}</p>
              </div>
            </div>
            <div class="confirm-btns">
              <button class="btn-yes" @click="confirmDestination">✓ Sí, ir aquí</button>
              <button class="btn-no" @click="rejectDestination">Buscar otro</button>
            </div>
          </div>

          <!-- Multiple results list -->
          <div v-if="searchResults.length > 0 && !pendingLocation" class="results-list">
            <p class="results-label">Selecciona el lugar:</p>
            <button
              v-for="(r, i) in searchResults"
              :key="i"
              class="result-item"
              @click="selectResult(r)"
            >
              <span class="result-pin">📍</span>
              <div>
                <p class="result-name">{{ r.name }}</p>
                <p class="result-addr">{{ r.address }}</p>
              </div>
            </button>
          </div>

        </div>

        <!-- Input Area -->
        <div class="sofia-input-area">
          <input
            v-model="textInput"
            @keyup.enter="submitText"
            :disabled="chatStore.isProcessing || listening"
            type="text"
            placeholder="Escribe tu destino..."
            class="sofia-input"
            ref="inputRef"
          />
          <button
            @click="toggleVoice"
            :class="['sofia-voice-btn', { 'voice-active': listening }]"
            :disabled="chatStore.isProcessing || !voiceAvailable"
            :title="voiceAvailable ? (listening ? 'Detener' : 'Usar voz') : 'Voz no disponible en este navegador'"
          >
            <span v-if="listening" class="voice-stop">⏹</span>
            <svg v-else viewBox="0 0 24 24" fill="currentColor" width="22" height="22">
              <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3zm-1-9c0-.55.45-1 1-1s1 .45 1 1v6c0 .55-.45 1-1 1s-1-.45-1-1V5zm6 6c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z"/>
            </svg>
          </button>
        </div>
        <p v-if="listening" class="listening-hint">🎤 Escuchando... habla ahora</p>

      </div>
    </div>
  </Transition>
</template>

<script setup>
import { ref, nextTick, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useChatStore } from '../stores/chat'
import { useLocationStore } from '../stores/locationStore'

const chatStore = useChatStore()
const locationStore = useLocationStore()
const router = useRouter()

const conversationRef = ref(null)
const inputRef = ref(null)
const textInput = ref('')
const pendingLocation = ref(null)
const searchResults = ref([])
const listening = ref(false)

const voiceAvailable = typeof window !== 'undefined' &&
  !!(window.SpeechRecognition || window.webkitSpeechRecognition)

let recognition = null

// ── Intent extraction ─────────────────────────────────────────────────────────
const DEST_PATTERNS = [
  /(?:llévame|llevame|lleva(?:me)?)\s+(?:al?|a\s+la|a\s+los|a\s+las)\s+(.+)/i,
  /(?:quiero\s+ir|necesito\s+ir|me\s+llevas?|puedes?\s+llevarme)\s+(?:al?|a\s+la|hacia)\s+(.+)/i,
  /(?:taxi|viaje|uber)\s+(?:al?|a\s+la|hacia)\s+(.+)/i,
  /(?:voy|ando)\s+(?:al?|para)\s+(.+)/i,
  /^(?:al?|a\s+la|a\s+los|a\s+las|para)\s+(.+)/i,
]

const FILLER_RE = /^(hola|ok|bien|sí|si|no|ayuda|help|gracias|¿|qué|como|cómo|cuánto|cuanto)\b/i

function extractDestination(text) {
  const t = text.trim()
  for (const p of DEST_PATTERNS) {
    const m = t.match(p)
    if (m?.[1]?.length > 2) {
      return m[1].replace(/\s*por\s+favor\s*$/i, '').trim()
    }
  }
  // Short text without question marks or filler words → treat as raw destination query
  if (t.length < 70 && !t.includes('?') && !FILLER_RE.test(t)) return t
  return null
}

// ── Helpers ───────────────────────────────────────────────────────────────────
const scrollToBottom = async () => {
  await nextTick()
  if (conversationRef.value) {
    conversationRef.value.scrollTop = conversationRef.value.scrollHeight
  }
}

const addMessage = (sender, text, type) => {
  chatStore.addMessage(sender, text, type)
  scrollToBottom()
}

// ── Core flow ─────────────────────────────────────────────────────────────────
const processMessage = async (text) => {
  if (!text?.trim() || chatStore.isProcessing) return

  const query = text.trim()
  textInput.value = ''
  pendingLocation.value = null
  searchResults.value = []

  addMessage('Tú', query, 'user')

  const dest = extractDestination(query)
  if (!dest) {
    addMessage('Sofia', 'Dime a dónde quieres ir. Por ejemplo: "llévame al aeropuerto" o escribe directamente el nombre del lugar.', 'assistant')
    return
  }

  chatStore.setProcessing(true)
  scrollToBottom()

  try {
    const result = await locationStore.searchAddress(dest)

    if (!result.success || !result.results?.length) {
      addMessage('Sofia', `No encontré "${dest}". Intenta con un nombre más específico o una dirección.`, 'assistant')
      return
    }

    if (result.results.length === 1) {
      pendingLocation.value = result.results[0]
      addMessage('Sofia', '¿Es este el lugar correcto?', 'assistant')
    } else {
      searchResults.value = result.results.slice(0, 4)
      addMessage('Sofia', `Encontré ${result.results.length} lugares. ¿Cuál es el tuyo?`, 'assistant')
    }
  } catch {
    addMessage('Sofia', 'Hubo un error al buscar la dirección. Intenta de nuevo.', 'assistant')
  } finally {
    chatStore.setProcessing(false)
    scrollToBottom()
  }
}

const selectResult = (result) => {
  searchResults.value = []
  pendingLocation.value = result
  scrollToBottom()
}

const confirmDestination = () => {
  if (!pendingLocation.value) return
  const loc = pendingLocation.value
  locationStore.selectDestination(loc)
  pendingLocation.value = null
  searchResults.value = []
  chatStore.clearChat()
  chatStore.closeChat()
  router.push('/home')
}

const rejectDestination = () => {
  pendingLocation.value = null
  addMessage('Sofia', '¿Cuál es el destino correcto? Escríbelo o dilo por voz.', 'assistant')
}

const submitText = () => {
  processMessage(textInput.value)
}

// ── Voice (Web Speech API) ────────────────────────────────────────────────────
const startListening = () => {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition
  if (!SR) return

  recognition = new SR()
  recognition.lang = 'es-MX'
  recognition.interimResults = false
  recognition.maxAlternatives = 1

  recognition.onresult = (event) => {
    const transcript = event.results[0][0].transcript
    listening.value = false
    processMessage(transcript)
  }

  recognition.onerror = (event) => {
    listening.value = false
    if (event.error !== 'no-speech' && event.error !== 'aborted') {
      addMessage('Sofia', 'No pude escucharte bien. Intenta de nuevo o escribe tu destino.', 'assistant')
    }
  }

  recognition.onend = () => {
    listening.value = false
  }

  recognition.start()
  listening.value = true
}

const toggleVoice = () => {
  if (!voiceAvailable) return
  if (listening.value) {
    recognition?.stop()
  } else {
    startListening()
  }
}

onUnmounted(() => {
  recognition?.stop()
})
</script>

<style scoped>
.sofia-container {
  position: fixed;
  inset: 0;
  display: flex;
  align-items: flex-end;
  justify-content: flex-end;
  z-index: 1000;
  pointer-events: none;
}

.sofia-modal {
  pointer-events: all;
  width: 100%;
  max-width: 420px;
  height: 100%;
  max-height: 100%;
  background: white;
  display: flex;
  flex-direction: column;
  box-shadow: -4px 0 24px rgba(0,0,0,.15);
}

@media (min-width: 640px) {
  .sofia-modal {
    max-height: 620px;
    border-radius: 20px 0 0 20px;
    align-self: flex-end;
  }
}

/* Header */
.sofia-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  background: linear-gradient(135deg, #1e3a5f 0%, #2563eb 100%);
  color: white;
  flex-shrink: 0;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.sofia-avatar {
  font-size: 28px;
  line-height: 1;
}

.sofia-title {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
}

.sofia-sub {
  font-size: 12px;
  opacity: 0.8;
}

.sofia-close {
  background: rgba(255,255,255,.15);
  border: none;
  border-radius: 50%;
  width: 34px;
  height: 34px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: white;
  transition: background .2s;
}

.sofia-close:hover { background: rgba(255,255,255,.25); }

/* Conversation */
.sofia-conversation {
  flex: 1;
  overflow-y: auto;
  padding: 20px 16px;
  background: #f8fafc;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

/* Welcome */
.sofia-welcome {
  text-align: center;
  padding: 16px 8px;
}

.welcome-taxi {
  font-size: 52px;
  margin-bottom: 12px;
}

.sofia-welcome h3 {
  font-size: 20px;
  font-weight: 700;
  color: #1e293b;
  margin: 0 0 6px;
}

.sofia-welcome p {
  color: #64748b;
  margin: 0 0 4px;
  font-size: 14px;
}

.welcome-hint {
  font-size: 13px !important;
  color: #94a3b8 !important;
  margin-bottom: 16px !important;
}

.sofia-quickactions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  margin-top: 12px;
}

.qa-btn {
  background: white;
  border: 2px solid #e2e8f0;
  border-radius: 12px;
  padding: 10px 8px;
  font-size: 13px;
  font-weight: 600;
  color: #374151;
  cursor: pointer;
  transition: all .2s;
  text-align: center;
}

.qa-btn:hover {
  border-color: #2563eb;
  background: #eff6ff;
  transform: translateY(-1px);
}

/* Messages */
.sofia-message {
  max-width: 82%;
  word-break: break-word;
}

.msg-user {
  align-self: flex-end;
}

.msg-sofia {
  align-self: flex-start;
}

.msg-text {
  margin: 0;
  padding: 10px 14px;
  border-radius: 16px;
  font-size: 14px;
  line-height: 1.45;
}

.msg-user .msg-text {
  background: #2563eb;
  color: white;
  border-bottom-right-radius: 4px;
}

.msg-sofia .msg-text {
  background: white;
  color: #1e293b;
  border-bottom-left-radius: 4px;
  box-shadow: 0 1px 3px rgba(0,0,0,.08);
}

/* Typing dots */
.typing-dots {
  display: flex;
  gap: 5px;
  padding: 12px 16px;
  background: white;
  border-radius: 16px;
  border-bottom-left-radius: 4px;
  box-shadow: 0 1px 3px rgba(0,0,0,.08);
  width: fit-content;
}

.typing-dots span {
  width: 8px;
  height: 8px;
  background: #94a3b8;
  border-radius: 50%;
  animation: bounce-dot 1.2s ease-in-out infinite;
}

.typing-dots span:nth-child(2) { animation-delay: .2s; }
.typing-dots span:nth-child(3) { animation-delay: .4s; }

@keyframes bounce-dot {
  0%, 60%, 100% { transform: translateY(0); opacity: .6; }
  30%            { transform: translateY(-8px); opacity: 1; }
}

/* Confirmation card */
.confirm-card {
  background: white;
  border: 2px solid #2563eb;
  border-radius: 16px;
  padding: 16px;
  align-self: stretch;
  box-shadow: 0 4px 12px rgba(37,99,235,.12);
}

.confirm-label {
  font-size: 13px;
  font-weight: 600;
  color: #2563eb;
  margin: 0 0 12px;
  text-transform: uppercase;
  letter-spacing: .5px;
}

.confirm-place {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  margin-bottom: 14px;
  background: #f8fafc;
  border-radius: 10px;
  padding: 12px;
}

.place-pin { font-size: 22px; flex-shrink: 0; }

.place-name {
  font-weight: 700;
  color: #1e293b;
  font-size: 15px;
  margin: 0 0 3px;
}

.place-address {
  font-size: 12px;
  color: #64748b;
  margin: 0;
  line-height: 1.4;
}

.confirm-btns {
  display: flex;
  gap: 8px;
}

.btn-yes {
  flex: 1;
  background: #2563eb;
  color: white;
  border: none;
  border-radius: 10px;
  padding: 12px;
  font-weight: 700;
  font-size: 14px;
  cursor: pointer;
  transition: background .2s;
}

.btn-yes:hover { background: #1d4ed8; }

.btn-no {
  flex: 1;
  background: #f1f5f9;
  color: #475569;
  border: none;
  border-radius: 10px;
  padding: 12px;
  font-weight: 600;
  font-size: 14px;
  cursor: pointer;
  transition: background .2s;
}

.btn-no:hover { background: #e2e8f0; }

/* Results list */
.results-list {
  background: white;
  border-radius: 16px;
  padding: 14px;
  align-self: stretch;
  box-shadow: 0 2px 8px rgba(0,0,0,.08);
}

.results-label {
  font-size: 13px;
  font-weight: 600;
  color: #64748b;
  margin: 0 0 10px;
}

.result-item {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  width: 100%;
  background: none;
  border: none;
  padding: 10px;
  border-radius: 10px;
  cursor: pointer;
  text-align: left;
  transition: background .15s;
}

.result-item:hover { background: #f0f9ff; }
.result-item + .result-item { border-top: 1px solid #f1f5f9; }

.result-pin { font-size: 18px; flex-shrink: 0; margin-top: 1px; }

.result-name {
  font-weight: 600;
  color: #1e293b;
  font-size: 14px;
  margin: 0 0 2px;
}

.result-addr {
  font-size: 12px;
  color: #64748b;
  margin: 0;
  line-height: 1.35;
}

/* Input area */
.sofia-input-area {
  display: flex;
  gap: 8px;
  padding: 12px 16px;
  background: white;
  border-top: 1px solid #e2e8f0;
  flex-shrink: 0;
}

.sofia-input {
  flex: 1;
  border: 2px solid #e2e8f0;
  border-radius: 12px;
  padding: 11px 14px;
  font-size: 14px;
  color: #1e293b;
  outline: none;
  transition: border-color .2s;
}

.sofia-input:focus { border-color: #2563eb; }
.sofia-input:disabled { background: #f8fafc; }

.sofia-voice-btn {
  width: 46px;
  height: 46px;
  border-radius: 12px;
  border: 2px solid #e2e8f0;
  background: white;
  color: #475569;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all .2s;
  flex-shrink: 0;
}

.sofia-voice-btn:hover:not(:disabled) {
  border-color: #2563eb;
  color: #2563eb;
  background: #eff6ff;
}

.sofia-voice-btn.voice-active {
  background: #ef4444;
  border-color: #ef4444;
  color: white;
  animation: pulse-red 1.2s ease-in-out infinite;
}

.sofia-voice-btn:disabled {
  opacity: .4;
  cursor: not-allowed;
}

.voice-stop { font-size: 18px; }

@keyframes pulse-red {
  0%, 100% { box-shadow: 0 0 0 0 rgba(239,68,68,.5); }
  50%       { box-shadow: 0 0 0 8px rgba(239,68,68,0); }
}

.listening-hint {
  text-align: center;
  font-size: 12px;
  color: #ef4444;
  font-weight: 600;
  padding: 0 16px 10px;
  background: white;
  margin: 0;
}
</style>
