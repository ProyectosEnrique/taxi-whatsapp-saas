import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { createRouter, createWebHistory } from 'vue-router'
import { registerSW } from 'virtual:pwa-register'
import App from './App.vue'
import DashboardView from './views/DashboardView.vue'
import MenuManagement from './views/MenuManagement.vue'
import PromotionsManagement from './views/PromotionsManagement.vue'
import TableManagement from './views/TableManagement.vue'
import UserManagement from './views/UserManagement.vue'
import SecurityDashboard from './views/SecurityDashboard.vue'  // Panel de Seguridad IoT
import IoTDashboard from './views/IoTDashboard.vue'  // Dashboard de Sensores IoT
import NotesReminders from './views/AgricultureAssistant.vue'  // Renombrado a Notas y Recordatorios
import WhatsAppDashboard from './views/WhatsAppDashboard.vue'  // Dashboard de WhatsApp

// Detectar si estamos en /admin o en raíz
const basePath = window.location.pathname.startsWith('/admin') ? '/admin' : '/'

const router = createRouter({
  history: createWebHistory(basePath),
  routes: [
    { path: '/', component: DashboardView },
    { path: '/menu', component: MenuManagement },
    { path: '/promotions', component: PromotionsManagement },
    { path: '/tables', component: TableManagement },
    { path: '/users', component: UserManagement },
    { path: '/security', component: SecurityDashboard },  // Panel de Seguridad IoT dedicado
    { path: '/iot', component: IoTDashboard },  // Dashboard de Sensores IoT
    { path: '/notes', component: NotesReminders },
    { path: '/whatsapp', component: WhatsAppDashboard }  // Dashboard de WhatsApp
  ]
})

createApp(App).use(createPinia()).use(router).mount('#app')

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
