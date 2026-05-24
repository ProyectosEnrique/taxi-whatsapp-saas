import './main.css'
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { createRouter, createWebHistory } from 'vue-router'
import { registerSW } from 'virtual:pwa-register'
import App from './App.vue'
import DashboardView from './views/DashboardView.vue'
import DriversManagement from './views/DriversManagement.vue'
import RidesMonitor from './views/RidesMonitor.vue'
import IncidentsView from './views/IncidentsView.vue'
import FareConfiguration from './views/FareConfiguration.vue'

const basePath = window.location.pathname.startsWith('/admin') ? '/admin' : '/'

const router = createRouter({
  history: createWebHistory(basePath),
  routes: [
    { path: '/',          component: DashboardView },
    { path: '/drivers',   component: DriversManagement },
    { path: '/rides',     component: RidesMonitor },
    { path: '/incidents', component: IncidentsView },
    { path: '/fares',     component: FareConfiguration },
  ]
})

createApp(App).use(createPinia()).use(router).mount('#app')

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
