<template>
  <button
    class="voice-button"
    :class="buttonClasses"
    @click.prevent="toggleRecording"
    @contextmenu.prevent
    :disabled="disabled || isPlaying"
    :title="buttonTitle"
  >
    <!-- Ripple effect when recording -->
    <div v-if="isRecording" class="ripple-container">
      <div class="ripple"></div>
      <div class="ripple delay-1"></div>
      <div class="ripple delay-2"></div>
    </div>

    <!-- Icon -->
    <span class="icon">
      <template v-if="isRecording">
        <svg viewBox="0 0 24 24" fill="currentColor" width="24" height="24">
          <rect x="6" y="6" width="12" height="12" rx="2"/>
        </svg>
      </template>
      <template v-else-if="isPlaying">
        <svg viewBox="0 0 24 24" fill="currentColor" width="24" height="24">
          <path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3A4.5 4.5 0 0014 7.97v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z"/>
        </svg>
      </template>
      <template v-else>
        <svg viewBox="0 0 24 24" fill="currentColor" width="24" height="24">
          <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3zm5.91-3c-.49 0-.9.36-.98.85C16.52 14.2 14.47 16 12 16s-4.52-1.8-4.93-4.15a.998.998 0 00-.98-.85c-.61 0-1.09.54-1 1.14.49 3 2.89 5.35 5.91 5.78V20c0 .55.45 1 1 1s1-.45 1-1v-2.08a6.993 6.993 0 005.91-5.78c.1-.6-.39-1.14-1-1.14z"/>
        </svg>
      </template>
    </span>
  </button>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  isRecording: {
    type: Boolean,
    default: false
  },
  isPlaying: {
    type: Boolean,
    default: false
  },
  disabled: {
    type: Boolean,
    default: false
  },
  size: {
    type: String,
    default: 'medium',
    validator: (val) => ['small', 'medium', 'large'].includes(val)
  }
})

const emit = defineEmits(['start', 'stop'])

const buttonClasses = computed(() => ({
  'recording': props.isRecording,
  'playing': props.isPlaying,
  'disabled': props.disabled,
  [`size-${props.size}`]: true
}))

const buttonTitle = computed(() => {
  if (props.isRecording) return 'Toca para enviar'
  if (props.isPlaying) return 'Reproduciendo respuesta...'
  if (props.disabled) return 'No disponible'
  return 'Toca para hablar'
})

function toggleRecording() {
  if (props.disabled || props.isPlaying) return

  if (props.isRecording) {
    emit('stop')
  } else {
    emit('start')
  }
}
</script>

<style scoped>
.voice-button {
  position: relative;
  border: none;
  border-radius: 50%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
  transition: all 0.3s ease;
  overflow: visible;

  /* Prevent selection */
  -webkit-user-select: none;
  -moz-user-select: none;
  user-select: none;
  -webkit-touch-callout: none;
  -webkit-tap-highlight-color: transparent;
}

/* Sizes */
.voice-button.size-small {
  width: 44px;
  height: 44px;
}

.voice-button.size-small .icon svg {
  width: 20px;
  height: 20px;
}

.voice-button.size-medium {
  width: 56px;
  height: 56px;
}

.voice-button.size-medium .icon svg {
  width: 24px;
  height: 24px;
}

.voice-button.size-large {
  width: 80px;
  height: 80px;
}

.voice-button.size-large .icon svg {
  width: 36px;
  height: 36px;
}

/* Hover state */
.voice-button:hover:not(.disabled):not(.recording) {
  transform: scale(1.05);
  box-shadow: 0 6px 20px rgba(102, 126, 234, 0.5);
}

/* Active/Press state */
.voice-button:active:not(.disabled) {
  transform: scale(0.95);
}

/* Recording state */
.voice-button.recording {
  background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
  box-shadow: 0 4px 20px rgba(239, 68, 68, 0.5);
  animation: pulse-button 1.5s ease-in-out infinite;
}

/* Playing state */
.voice-button.playing {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  box-shadow: 0 4px 15px rgba(16, 185, 129, 0.4);
  cursor: default;
}

/* Disabled state */
.voice-button.disabled {
  background: #9ca3af;
  cursor: not-allowed;
  box-shadow: none;
}

/* Icon container */
.icon {
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2;
}

/* Ripple container */
.ripple-container {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 100%;
  height: 100%;
  pointer-events: none;
}

/* Ripple effect */
.ripple {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 100%;
  height: 100%;
  border-radius: 50%;
  border: 2px solid rgba(239, 68, 68, 0.6);
  animation: ripple-effect 1.5s ease-out infinite;
}

.ripple.delay-1 {
  animation-delay: 0.3s;
}

.ripple.delay-2 {
  animation-delay: 0.6s;
}

/* Animations */
@keyframes pulse-button {
  0%, 100% {
    box-shadow: 0 4px 20px rgba(239, 68, 68, 0.5);
  }
  50% {
    box-shadow: 0 4px 30px rgba(239, 68, 68, 0.8);
  }
}

@keyframes ripple-effect {
  0% {
    width: 100%;
    height: 100%;
    opacity: 1;
  }
  100% {
    width: 200%;
    height: 200%;
    opacity: 0;
  }
}
</style>
