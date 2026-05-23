<template>
  <div id="app" class="min-h-screen">
    <router-view />

    <!-- Botón flotante de Sofia (oculto cuando el chat está abierto) -->
    <Transition name="fade">
      <button
        v-if="!chatStore.isOpen"
        class="sofia-float-button"
        @click="chatStore.openChat"
        title="Hablar con Sofia"
      >
        <svg viewBox="0 0 24 24" fill="currentColor" width="28" height="28">
          <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H6l-2 2V4h16v12z"/>
        </svg>
        <span class="sofia-name">Sofia</span>
      </button>
    </Transition>

    <!-- Modal de Sofia -->
    <VoiceAssistantModal />
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useAuthStore } from './stores/authStore'
import { useChatStore } from './stores/chat'
import VoiceAssistantModal from './components/VoiceAssistantModal.vue'

const authStore = useAuthStore()
const chatStore = useChatStore()

onMounted(() => {
  authStore.checkAuth()
})
</script>

<style scoped>
.sofia-float-button {
  position: fixed;
  bottom: 24px;
  right: 24px;
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  box-shadow: 0 4px 20px rgba(102, 126, 234, 0.4);
  cursor: pointer;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  z-index: 999;
  transition: all 0.3s ease;
}

.sofia-float-button:hover {
  transform: scale(1.1);
  box-shadow: 0 6px 25px rgba(102, 126, 234, 0.5);
}

.sofia-float-button:active {
  transform: scale(0.95);
}

.sofia-name {
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.5px;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
