<template>
  <teleport to="body">
    <div class="fixed top-20 right-4 z-50 space-y-2">
      <transition-group name="slide-fade">
        <div
          v-for="notification in notifications"
          :key="notification.id"
          :class="[
            'max-w-sm bg-white rounded-lg shadow-lg border-l-4 p-4',
            notification.type === 'success' ? 'border-green-500' : '',
            notification.type === 'error' ? 'border-red-500' : '',
            notification.type === 'warning' ? 'border-yellow-500' : '',
            notification.type === 'info' ? 'border-blue-500' : ''
          ]"
        >
          <div class="flex items-start">
            <div class="flex-shrink-0">
              <!-- Success Icon -->
              <svg
                v-if="notification.type === 'success'"
                class="w-6 h-6 text-green-500"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
              </svg>

              <!-- Error Icon -->
              <svg
                v-else-if="notification.type === 'error'"
                class="w-6 h-6 text-red-500"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>

              <!-- Warning Icon -->
              <svg
                v-else-if="notification.type === 'warning'"
                class="w-6 h-6 text-yellow-500"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>

              <!-- Info Icon -->
              <svg
                v-else
                class="w-6 h-6 text-blue-500"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>

            <div class="ml-3 flex-1">
              <p class="text-sm font-medium text-gray-900">
                {{ notification.message }}
              </p>
            </div>

            <button
              @click="removeNotification(notification.id)"
              class="ml-4 flex-shrink-0 text-gray-400 hover:text-gray-600"
            >
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>
      </transition-group>
    </div>
  </teleport>
</template>

<script setup>
import { ref } from 'vue'

const notifications = ref([])
let notificationId = 0

function addNotification(message, type = 'info', duration = 3000) {
  const id = ++notificationId

  notifications.value.push({
    id,
    message,
    type
  })

  // Auto-remove después de duration
  setTimeout(() => {
    removeNotification(id)
  }, duration)
}

function removeNotification(id) {
  const index = notifications.value.findIndex(n => n.id === id)
  if (index !== -1) {
    notifications.value.splice(index, 1)
  }
}

// Exponer funciones globalmente
defineExpose({
  addNotification,
  success: (message, duration) => addNotification(message, 'success', duration),
  error: (message, duration) => addNotification(message, 'error', duration),
  warning: (message, duration) => addNotification(message, 'warning', duration),
  info: (message, duration) => addNotification(message, 'info', duration)
})
</script>

<style scoped>
.slide-fade-enter-active {
  transition: all 0.3s ease-out;
}

.slide-fade-leave-active {
  transition: all 0.2s ease-in;
}

.slide-fade-enter-from {
  transform: translateX(20px);
  opacity: 0;
}

.slide-fade-leave-to {
  transform: translateX(20px);
  opacity: 0;
}
</style>
