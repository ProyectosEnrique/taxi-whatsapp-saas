import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import './style.css'
import { registerSW } from 'virtual:pwa-register'

// Recarga forzada cuando un chunk lazy-loaded ya no existe en el servidor
// (típico tras un deploy: el navegador tiene un index.html/SW viejo apuntando
// a un archivo con hash que ya no está). Sin esto, el import() dinámico de
// Vue Router falla en silencio y la pantalla queda en blanco.
const RELOAD_FLAG = 'chunk-reload-attempted'
function reloadOnce() {
  if (sessionStorage.getItem(RELOAD_FLAG)) return
  sessionStorage.setItem(RELOAD_FLAG, '1')
  window.location.reload()
}
window.addEventListener('vite:preloadError', reloadOnce)

const app = createApp(App)

app.use(createPinia())
app.use(router)

router.onError((err) => {
  if (/Failed to fetch dynamically imported module|Importing a module script failed|Loading chunk/i.test(err?.message || '')) {
    reloadOnce()
  }
})

app.mount('#app')
router.isReady().then(() => sessionStorage.removeItem(RELOAD_FLAG))

// Registrar Service Worker
const updateSW = registerSW({
  onNeedRefresh() {
    if (confirm('Nueva versión disponible. ¿Actualizar ahora?')) {
      updateSW(true)
    }
  },
  onOfflineReady() {
    console.log('App lista para funcionar offline')
  }
})
