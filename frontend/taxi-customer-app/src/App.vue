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

    <!-- Botón SOS flotante — siempre visible cuando está autenticado -->
    <Transition name="fade">
      <button
        v-if="authStore.isAuthenticated && !isAuthPage"
        class="sos-float-button"
        :class="{ 'sos-active': sosPanicSent }"
        @click="sosShowModal = true"
        title="Botón de emergencia"
      >
        <span class="sos-label">{{ sosPanicSent ? '🚨' : 'SOS' }}</span>
      </button>
    </Transition>

    <!-- Modal SOS -->
    <Transition name="fade">
      <div v-if="sosShowModal" class="sos-overlay" @click.self="sosShowModal = false">
        <div class="sos-modal">
          <div class="sos-modal-header">
            <div class="sos-icon">🚨</div>
            <h2>EMERGENCIA</h2>
            <p>¿Necesitas ayuda ahora mismo?</p>
          </div>
          <div class="sos-modal-body">
            <button @click="sosTrigger" :disabled="sosSending" class="sos-confirm-btn">
              {{ sosSending ? 'Enviando alerta...' : '📞 SÍ, PEDIR AYUDA AHORA' }}
            </button>
            <button @click="sosShowModal = false" class="sos-cancel-btn">
              Cancelar — Estoy bien
            </button>
          </div>
        </div>
      </div>
    </Transition>

    <!-- Banner alerta activa -->
    <div v-if="sosPanicSent" class="sos-banner">
      🚨 ALERTA ENVIADA · {{ sosPanicTime }} · Ayuda en camino
    </div>

    <!-- Toast global -->
    <Transition name="toast-slide">
      <div
        v-if="toast"
        :class="['app-toast', toast.type === 'success' ? 'app-toast--success' : toast.type === 'info' ? 'app-toast--info' : 'app-toast--error']"
      >
        <span class="app-toast-icon">{{ toast.type === 'success' ? '✓' : toast.type === 'info' ? 'ℹ' : '✗' }}</span>
        {{ toast.message }}
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from './stores/authStore'
import { useChatStore } from './stores/chat'
import { ridesApi } from './services/api'
import VoiceAssistantModal from './components/VoiceAssistantModal.vue'
import { useToast } from './composables/useToast'

const { toast } = useToast()
const router = useRouter()

const authStore = useAuthStore()
const chatStore = useChatStore()
const route = useRoute()

const AUTH_PAGES = ['/login', '/register', '/']
const isAuthPage = computed(() => AUTH_PAGES.includes(route.path))

const sosShowModal = ref(false)
const sosSending   = ref(false)
const sosPanicSent = ref(false)
const sosPanicTime = ref('')

const sosTrigger = async () => {
  sosSending.value = true
  try {
    let lat = null, lng = null
    try {
      const pos = await new Promise((res, rej) =>
        navigator.geolocation.getCurrentPosition(res, rej, { timeout: 4000 })
      )
      lat = pos.coords.latitude
      lng = pos.coords.longitude
    } catch (_) {}

    const result = await ridesApi.reportIncident({ lat, lng, notes: 'SOS activado por cliente' })
    window.open(`tel:${result.emergency_phone || '911'}`)
  } catch (_) {
    window.open('tel:911')
  } finally {
    sosSending.value = false
    sosPanicSent.value = true
    sosPanicTime.value = new Date().toLocaleTimeString('es-MX', { hour: '2-digit', minute: '2-digit' })
    sosShowModal.value = false
  }
}

onMounted(() => {
  authStore.checkAuth()

  // Detectar regreso desde el checkout de MercadoPago
  // MP redirige a /cliente/?trip=TRIP-XXX&collection_status=approved|failure
  const params = new URLSearchParams(window.location.search)
  const tripFromMP  = params.get('trip') || sessionStorage.getItem('pending_mp_trip')
  const mpStatus    = params.get('collection_status') || params.get('status')

  if (tripFromMP) {
    sessionStorage.removeItem('pending_mp_trip')
    // Limpiar los query params de MP de la URL sin recargar
    window.history.replaceState({}, '', window.location.pathname)

    if (mpStatus === 'failure' || mpStatus === 'rejected') {
      // Ir igual al tracking — la vista mostrará el estado de pago fallido
    }
    // Siempre redirigir al tracking para que el usuario vea el estado real
    router.push(`/ride/${tripFromMP}`)
  }
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

/* ── SOS Button ───────────────────────────────────────────── */
.sos-float-button {
  position: fixed;
  bottom: 24px;
  left: 24px;
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: #dc2626;
  color: white;
  border: none;
  box-shadow: 0 4px 20px rgba(220, 38, 38, 0.5);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 998;
  transition: all 0.2s ease;
}
.sos-float-button:hover  { transform: scale(1.1); box-shadow: 0 6px 25px rgba(220,38,38,.6); }
.sos-float-button:active { transform: scale(0.95); }
.sos-float-button.sos-active { animation: sos-pulse 1.2s ease-in-out infinite; }

@keyframes sos-pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(220,38,38,.7); }
  50%       { box-shadow: 0 0 0 14px rgba(220,38,38,0); }
}

.sos-label { font-size: 15px; font-weight: 900; letter-spacing: 1px; }

.sos-overlay {
  position: fixed; inset: 0;
  background: rgba(0,0,0,.75);
  display: flex; align-items: center; justify-content: center;
  z-index: 9999;
  padding: 16px;
}

.sos-modal {
  background: white;
  border-radius: 20px;
  width: 100%; max-width: 340px;
  overflow: hidden;
  box-shadow: 0 25px 60px rgba(0,0,0,.4);
}

.sos-modal-header {
  background: #dc2626;
  color: white;
  padding: 28px 20px 20px;
  text-align: center;
}
.sos-modal-header .sos-icon { font-size: 56px; margin-bottom: 8px; }
.sos-modal-header h2 { font-size: 26px; font-weight: 900; margin: 0 0 6px; }
.sos-modal-header p  { font-size: 14px; margin: 0; opacity: .85; }

.sos-modal-body { padding: 20px; display: flex; flex-direction: column; gap: 10px; }

.sos-confirm-btn {
  background: #dc2626;
  color: white;
  border: none;
  border-radius: 14px;
  padding: 16px;
  font-size: 16px;
  font-weight: 900;
  cursor: pointer;
  transition: background .2s;
}
.sos-confirm-btn:hover:not(:disabled) { background: #b91c1c; }
.sos-confirm-btn:disabled { opacity: .5; cursor: not-allowed; }

.sos-cancel-btn {
  background: #f3f4f6;
  color: #374151;
  border: none;
  border-radius: 14px;
  padding: 14px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: background .2s;
}
.sos-cancel-btn:hover { background: #e5e7eb; }

.sos-banner {
  position: fixed; top: 0; left: 0; right: 0;
  background: #dc2626;
  color: white;
  text-align: center;
  padding: 10px 16px;
  font-size: 13px;
  font-weight: 700;
  z-index: 9998;
  letter-spacing: .5px;
}

/* ── Toast global ─────────────────────────────────────────── */
.app-toast {
  position: fixed;
  bottom: 100px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 10000;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 20px;
  border-radius: 12px;
  font-size: 14px;
  font-weight: 600;
  color: white;
  box-shadow: 0 4px 20px rgba(0,0,0,.25);
  max-width: calc(100vw - 32px);
  white-space: nowrap;
}
.app-toast--success { background: #16a34a; }
.app-toast--error   { background: #dc2626; }
.app-toast--info    { background: #2563eb; }
.app-toast-icon { font-size: 16px; }

.toast-slide-enter-active, .toast-slide-leave-active { transition: all 0.3s ease; }
.toast-slide-enter-from { opacity: 0; transform: translateX(-50%) translateY(16px); }
.toast-slide-leave-to   { opacity: 0; transform: translateX(-50%) translateY(16px); }
</style>
