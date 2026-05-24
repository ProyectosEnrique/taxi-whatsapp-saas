<template>
  <div id="app" class="min-h-screen bg-gray-50">
    <router-view />

    <!-- Botón SOS flotante — siempre visible cuando está autenticado -->
    <Transition name="sos-fade">
      <button
        v-if="authStore.isAuthenticated && !isAuthPage"
        class="sos-float"
        :class="{ 'sos-active': panicSent }"
        @click="showModal = true"
        title="Botón de emergencia"
      >
        {{ panicSent ? '🚨' : 'SOS' }}
      </button>
    </Transition>

    <!-- Modal SOS -->
    <Transition name="sos-fade">
      <div v-if="showModal" class="sos-overlay" @click.self="showModal = false">
        <div class="sos-modal">
          <div class="sos-header">
            <div style="font-size:56px;margin-bottom:8px">🚨</div>
            <h2>EMERGENCIA</h2>
            <p>¿Necesitas ayuda ahora mismo?</p>
          </div>
          <div class="sos-body">
            <button @click="trigger" :disabled="sending" class="sos-confirm">
              {{ sending ? 'Enviando alerta...' : '📞 SÍ, PEDIR AYUDA AHORA' }}
            </button>
            <button @click="showModal = false" class="sos-cancel">
              Cancelar — Estoy bien
            </button>
          </div>
        </div>
      </div>
    </Transition>

    <!-- Banner alerta activa -->
    <div v-if="panicSent" class="sos-banner">
      🚨 ALERTA ENVIADA · {{ panicTime }} · Ayuda en camino
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
import { useRoute } from 'vue-router'
import { useAuthStore } from './stores/authStore'
import { useToast } from './composables/useToast'

const { toast } = useToast()
import { useDriverStore } from './stores/driverStore'
import { ridesApi } from './services/api'

const authStore   = useAuthStore()
const driverStore = useDriverStore()
const route = useRoute()

const AUTH_PAGES = ['/login', '/register']
const isAuthPage = computed(() => AUTH_PAGES.includes(route.path))

const showModal = ref(false)
const sending   = ref(false)
const panicSent = ref(false)
const panicTime = ref('')

const trigger = async () => {
  sending.value = true
  try {
    let lat = null, lng = null
    try {
      const pos = await new Promise((res, rej) =>
        navigator.geolocation.getCurrentPosition(res, rej, { timeout: 4000 })
      )
      lat = pos.coords.latitude
      lng = pos.coords.longitude
    } catch (_) {}

    const result = await ridesApi.reportIncident({ lat, lng, notes: 'SOS activado por conductor' })
    window.open(`tel:${result.emergency_phone || '911'}`)
  } catch (_) {
    window.open('tel:911')
  } finally {
    sending.value = false
    panicSent.value = true
    panicTime.value = new Date().toLocaleTimeString('es-MX', { hour: '2-digit', minute: '2-digit' })
    showModal.value = false
  }
}

onMounted(() => {
  authStore.checkAuth()
  if (authStore.isAuthenticated) {
    driverStore.startPolling()
  }
})
</script>

<style>
.sos-float {
  position: fixed;
  bottom: 24px;
  right: 24px;
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: #dc2626;
  color: white;
  border: none;
  box-shadow: 0 4px 20px rgba(220, 38, 38, 0.5);
  cursor: pointer;
  font-size: 15px;
  font-weight: 900;
  letter-spacing: 1px;
  z-index: 998;
  transition: all 0.2s ease;
}
.sos-float:hover  { transform: scale(1.1); }
.sos-float:active { transform: scale(0.95); }
.sos-float.sos-active { animation: sos-pulse 1.2s ease-in-out infinite; }

@keyframes sos-pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(220,38,38,.7); }
  50%       { box-shadow: 0 0 0 14px rgba(220,38,38,0); }
}

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

.sos-header {
  background: #dc2626;
  color: white;
  padding: 28px 20px 20px;
  text-align: center;
}
.sos-header h2 { font-size: 26px; font-weight: 900; margin: 0 0 6px; }
.sos-header p  { font-size: 14px; margin: 0; opacity: .85; }

.sos-body { padding: 20px; display: flex; flex-direction: column; gap: 10px; }

.sos-confirm {
  background: #dc2626; color: white; border: none;
  border-radius: 14px; padding: 16px;
  font-size: 16px; font-weight: 900; cursor: pointer;
  transition: background .2s;
}
.sos-confirm:hover:not(:disabled) { background: #b91c1c; }
.sos-confirm:disabled { opacity: .5; cursor: not-allowed; }

.sos-cancel {
  background: #f3f4f6; color: #374151; border: none;
  border-radius: 14px; padding: 14px;
  font-size: 14px; font-weight: 600; cursor: pointer;
}
.sos-cancel:hover { background: #e5e7eb; }

.sos-banner {
  position: fixed; top: 0; left: 0; right: 0;
  background: #dc2626; color: white;
  text-align: center; padding: 10px 16px;
  font-size: 13px; font-weight: 700;
  z-index: 9998; letter-spacing: .5px;
}

.sos-fade-enter-active, .sos-fade-leave-active { transition: opacity 0.25s; }
.sos-fade-enter-from,  .sos-fade-leave-to      { opacity: 0; }

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
