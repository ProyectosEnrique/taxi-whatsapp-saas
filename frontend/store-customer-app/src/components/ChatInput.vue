<template>
  <div class="chat-input-container">
    <!-- Input Mode Toggle -->
    <div class="mode-toggle">
      <button
        class="toggle-btn"
        :class="{ active: inputMode === 'text' }"
        @click="inputMode = 'text'"
        title="Escribir mensaje"
      >
        <svg viewBox="0 0 24 24" fill="currentColor" width="18" height="18">
          <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
        </svg>
        <span>Texto</span>
      </button>
      <button
        class="toggle-btn"
        :class="{ active: inputMode === 'voice', disabled: !chatStore.isVoiceEnabled }"
        @click="chatStore.isVoiceEnabled && (inputMode = 'voice')"
        :title="chatStore.isVoiceEnabled ? 'Hablar' : 'Voz no disponible sin conexión'"
        :disabled="!chatStore.isVoiceEnabled"
      >
        <svg viewBox="0 0 24 24" fill="currentColor" width="18" height="18">
          <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z"/>
          <path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z"/>
        </svg>
        <span>{{ chatStore.isVoiceEnabled ? 'Voz' : 'Sin conexión' }}</span>
      </button>
    </div>

    <!-- Input Area -->
    <div class="input-area" :class="{ 'voice-mode': inputMode === 'voice' }">
      <!-- Text Input -->
      <template v-if="inputMode === 'text'">
        <div class="text-input-wrapper">
          <textarea
            ref="textInput"
            v-model="textMessage"
            class="text-input"
            :placeholder="placeholder"
            :disabled="disabled"
            @keydown.enter.exact.prevent="sendTextMessage"
            @input="autoResize"
            rows="1"
          ></textarea>
          <button
            class="send-btn"
            :disabled="!textMessage.trim() || disabled"
            @click="sendTextMessage"
            title="Enviar mensaje"
          >
            <svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
              <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
            </svg>
          </button>
        </div>
      </template>

      <!-- Voice Input -->
      <template v-else>
        <div class="voice-input-wrapper">
          <div class="voice-status">
            <template v-if="isRecording">
              <div class="recording-indicator">
                <span class="dot"></span>
                Grabando... Toca para enviar
              </div>
            </template>
            <template v-else-if="isPlaying">
              <div class="playing-indicator">
                <span class="wave">
                  <span></span><span></span><span></span><span></span>
                </span>
                Reproduciendo respuesta...
              </div>
            </template>
            <template v-else>
              <span class="hint">Toca para hablar</span>
            </template>
          </div>

          <VoiceButton
            :is-recording="isRecording"
            :is-playing="isPlaying"
            :disabled="disabled"
            size="large"
            @start="$emit('voice-start')"
            @stop="$emit('voice-stop')"
          />
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick, watch } from 'vue'
import { useChatStore } from '../stores/chat'
import VoiceButton from './VoiceButton.vue'

const chatStore = useChatStore()

const props = defineProps({
  placeholder: {
    type: String,
    default: 'Escribe tu mensaje...'
  },
  disabled: {
    type: Boolean,
    default: false
  },
  isRecording: {
    type: Boolean,
    default: false
  },
  isPlaying: {
    type: Boolean,
    default: false
  },
  defaultMode: {
    type: String,
    default: 'voice',
    validator: (val) => ['text', 'voice'].includes(val)
  }
})

const emit = defineEmits(['send-text', 'voice-start', 'voice-stop'])

// Si está offline, forzar modo texto
const initialMode = chatStore.isVoiceEnabled ? props.defaultMode : 'text'
const inputMode = ref(initialMode)
const textMessage = ref('')
const textInput = ref(null)

// Watch: Si perdemos conexión y estamos en modo voz, cambiar a texto
watch(() => chatStore.isOnline, (online) => {
  if (!online && inputMode.value === 'voice') {
    inputMode.value = 'text'
  }
})

function sendTextMessage() {
  const message = textMessage.value.trim()
  if (message && !props.disabled) {
    emit('send-text', message)
    textMessage.value = ''
    nextTick(() => {
      if (textInput.value) {
        textInput.value.style.height = 'auto'
      }
    })
  }
}

function autoResize() {
  if (textInput.value) {
    textInput.value.style.height = 'auto'
    const newHeight = Math.min(textInput.value.scrollHeight, 120)
    textInput.value.style.height = newHeight + 'px'
  }
}

// Expose for parent component
defineExpose({
  focusInput: () => {
    if (textInput.value) {
      textInput.value.focus()
    }
  },
  setMode: (mode) => {
    inputMode.value = mode
  }
})
</script>

<style scoped>
.chat-input-container {
  background: white;
  border-radius: 16px;
  box-shadow: 0 -4px 20px rgba(0, 0, 0, 0.08);
  padding: 12px 16px;
}

/* Mode Toggle */
.mode-toggle {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
  padding: 4px;
  background: #f3f4f6;
  border-radius: 12px;
}

.toggle-btn {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 10px 16px;
  border: none;
  border-radius: 10px;
  background: transparent;
  color: #6b7280;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.toggle-btn:hover {
  color: #374151;
}

.toggle-btn.active {
  background: white;
  color: #667eea;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.toggle-btn.disabled {
  opacity: 0.5;
  cursor: not-allowed;
  color: #9ca3af;
}

.toggle-btn.disabled:hover {
  color: #9ca3af;
}

.toggle-btn svg {
  flex-shrink: 0;
}

/* Input Area */
.input-area {
  min-height: 56px;
}

/* Text Input */
.text-input-wrapper {
  display: flex;
  align-items: flex-end;
  gap: 10px;
  background: #f9fafb;
  border: 2px solid #e5e7eb;
  border-radius: 12px;
  padding: 8px 12px;
  transition: border-color 0.2s ease;
}

.text-input-wrapper:focus-within {
  border-color: #667eea;
}

.text-input {
  flex: 1;
  border: none;
  background: transparent;
  resize: none;
  font-size: 15px;
  line-height: 1.5;
  color: #1f2937;
  max-height: 120px;
  outline: none;
  font-family: inherit;
}

.text-input::placeholder {
  color: #9ca3af;
}

.send-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border: none;
  border-radius: 10px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  cursor: pointer;
  transition: all 0.2s ease;
  flex-shrink: 0;
}

.send-btn:hover:not(:disabled) {
  transform: scale(1.05);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.send-btn:active:not(:disabled) {
  transform: scale(0.95);
}

.send-btn:disabled {
  background: #d1d5db;
  cursor: not-allowed;
}

/* Voice Input */
.voice-input-wrapper {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 12px 0;
}

.voice-status {
  min-height: 20px;
  margin-bottom: 10px;
  text-align: center;
}

.voice-status .hint {
  color: #6b7280;
  font-size: 14px;
}

/* Recording Indicator */
.recording-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #ef4444;
  font-weight: 500;
  font-size: 14px;
  animation: fade-pulse 1.5s ease-in-out infinite;
}

.recording-indicator .dot {
  width: 10px;
  height: 10px;
  background: #ef4444;
  border-radius: 50%;
  animation: blink 1s ease-in-out infinite;
}

/* Playing Indicator */
.playing-indicator {
  display: flex;
  align-items: center;
  gap: 10px;
  color: #10b981;
  font-weight: 500;
  font-size: 14px;
}

.wave {
  display: flex;
  align-items: center;
  gap: 2px;
  height: 16px;
}

.wave span {
  width: 3px;
  height: 100%;
  background: #10b981;
  border-radius: 2px;
  animation: wave 1s ease-in-out infinite;
}

.wave span:nth-child(2) { animation-delay: 0.1s; }
.wave span:nth-child(3) { animation-delay: 0.2s; }
.wave span:nth-child(4) { animation-delay: 0.3s; }

/* Animations */
@keyframes fade-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}

@keyframes wave {
  0%, 100% { transform: scaleY(0.5); }
  50% { transform: scaleY(1); }
}
</style>
