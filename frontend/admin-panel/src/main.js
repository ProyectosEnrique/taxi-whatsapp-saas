import './main.css'
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { createRouter, createWebHistory } from 'vue-router'
import { registerSW } from 'virtual:pwa-register'
import App from './App.vue'
import DashboardView from './views/DashboardView.vue'
import DriversManagement from './views/DriversManagement.vue'
import DriversMap from './views/DriversMap.vue'
import DriverReports from './views/DriverReports.vue'
import RidesMonitor from './views/RidesMonitor.vue'
import IncidentsView from './views/IncidentsView.vue'
import FareConfiguration from './views/FareConfiguration.vue'
import PromosManagement from './views/PromosManagement.vue'
import DriversQRView from './views/DriversQRView.vue'
import LocalPoisView from './views/LocalPoisView.vue'

const basePath = window.location.pathname.startsWith('/admin') ? '/admin' : '/'

const router = createRouter({
  history: createWebHistory(basePath),
  routes: [
    { path: '/',          component: DashboardView },
    { path: '/drivers',   component: DriversManagement },
    { path: '/drivers-qr', component: DriversQRView },
    { path: '/map',       component: DriversMap },
    { path: '/reports',   component: DriverReports },
    { path: '/rides',     component: RidesMonitor },
    { path: '/incidents', component: IncidentsView },
    { path: '/fares',     component: FareConfiguration },
    { path: '/promos',    component: PromosManagement },
    { path: '/pois',      component: LocalPoisView },
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
