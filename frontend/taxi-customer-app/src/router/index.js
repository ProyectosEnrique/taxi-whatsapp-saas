import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/authStore'

const routes = [
  {
    // Página pública de TaxiCerca (con sesión abierta se va directo a /home)
    path: '/',
    name: 'Landing',
    component: () => import('../views/LandingView.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/privacidad',
    name: 'Privacy',
    component: () => import('../views/PrivacyView.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/LoginView.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('../views/RegisterView.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/forgot-password',
    name: 'ForgotPassword',
    component: () => import('../views/ForgotPasswordView.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/home',
    name: 'Home',
    component: () => import('../views/HomeView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/ride/:rideId',
    name: 'RideTracking',
    component: () => import('../views/RideTrackingView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/history',
    name: 'History',
    component: () => import('../views/HistoryView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/payment',
    name: 'Payment',
    component: () => import('../views/PaymentView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/profile',
    name: 'Profile',
    component: () => import('../views/ProfileView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/schedule',
    name: 'ScheduleRide',
    component: () => import('../views/ScheduleRideView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/scheduled',
    name: 'ScheduledRides',
    component: () => import('../views/ScheduledRidesView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/conductor/viaje/:rideId',
    name: 'DriverNavigate',
    component: () => import('../views/DriverNavigateView.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/seguimiento/:rideId',
    name: 'PublicTracking',
    component: () => import('../views/TrackPublicView.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/track/:incidentId',
    name: 'EmergencyTracking',
    component: () => import('../views/EmergencyTrackingView.vue'),
    meta: { requiresAuth: false }
  },
  {
    // Enlace de los QR impresos. nginx ya redirige a WhatsApp; esto cubre
    // teléfonos con un Service Worker viejo que sirva la app desde caché.
    path: '/pedir',
    beforeEnter() {
      window.location.replace('https://wa.me/13162412111?text=Hola%2C%20quiero%20pedir%20un%20taxi')
      return false
    }
  },
  {
    // Cualquier ruta no reconocida (ej. /cliente si el Service Worker la
    // sirve desde caché antes de que nginx redirija) → inicio en vez de
    // <router-view> vacío.
    path: '/:pathMatch(.*)*',
    redirect: '/'
  }
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes
})

// Arranque solo por WhatsApp (2026-11-10): cuenta y pedidos desde la web
// apagados (la API también los rechaza, WEB_RIDES_ENABLED). Siguen abiertas la
// portada, /seguimiento, /track, /pedir, /privacidad y /conductor.
const WEB_RIDES_ENABLED = false
const WEB_ONLY = ['Login', 'Register', 'ForgotPassword', 'Home', 'RideTracking', 'History',
  'Payment', 'Profile', 'ScheduleRide', 'ScheduledRides']

router.beforeEach((to, from, next) => {
  if (!WEB_RIDES_ENABLED && WEB_ONLY.includes(to.name)) return next('/')
  try {
    const authStore = useAuthStore()

    if (to.meta.requiresAuth && !authStore.isAuthenticated) {
      next('/login')
    } else if (WEB_RIDES_ENABLED && (to.path === '/' || to.path === '/login' || to.path === '/register') && authStore.isAuthenticated) {
      next('/home')
    } else {
      next()
    }
  } catch (err) {
    // Si el guard falla (ej. datos corruptos en localStorage) no dejar la
    // navegación colgada con <router-view> vacío — ir a login sin sesión.
    localStorage.removeItem('customer_token')
    localStorage.removeItem('customer_data')
    next('/login')
  }
})

export default router
