import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes = [
  // FASE 1: Menú, Carrito y Tracking
  {
    path: '/',
    name: 'home',
    component: () => import('@/views/MenuView.vue'),
    meta: { title: 'Menú' }
  },
  {
    path: '/menu',
    name: 'menu',
    component: () => import('@/views/MenuView.vue'),
    meta: { title: 'Menú' }
  },
  {
    path: '/product/:id',
    name: 'product-detail',
    component: () => import('@/views/ProductDetailView.vue'),
    meta: { title: 'Detalle del Producto' }
  },
  {
    path: '/checkout',
    name: 'checkout',
    component: () => import('@/views/CheckoutView.vue'),
    meta: { title: 'Finalizar Pedido' }
  },
  {
    path: '/order-tracking/:orderId',
    name: 'order-tracking',
    component: () => import('@/views/OrderTrackingView.vue'),
    meta: { title: 'Seguimiento de Pedido' }
  },

  // FASE 2: Autenticación, Perfil e Historial
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/LoginView.vue'),
    meta: { title: 'Iniciar Sesión', hideHeader: true }
  },
  {
    path: '/register',
    name: 'register',
    component: () => import('@/views/RegisterView.vue'),
    meta: { title: 'Registrarse', hideHeader: true }
  },
  {
    path: '/profile',
    name: 'profile',
    component: () => import('@/views/ProfileView.vue'),
    meta: { title: 'Mi Perfil', requiresAuth: true }
  },
  {
    path: '/addresses',
    name: 'addresses',
    component: () => import('@/views/AddressesView.vue'),
    meta: { title: 'Mis Direcciones', requiresAuth: true }
  },
  {
    path: '/order-history',
    name: 'order-history',
    component: () => import('@/views/OrderHistoryView.vue'),
    meta: { title: 'Mis Pedidos', requiresAuth: true }
  },

  // FASE 3: Promociones, Reseñas y Puntos
  {
    path: '/promotions',
    name: 'promotions',
    component: () => import('@/views/PromotionsView.vue'),
    meta: { title: 'Promociones y Ofertas' }
  },
  {
    path: '/reviews/:orderId',
    name: 'review-order',
    component: () => import('@/views/ReviewOrderView.vue'),
    meta: { title: 'Calificar Pedido', requiresAuth: true }
  },
  {
    path: '/loyalty',
    name: 'loyalty',
    component: () => import('@/views/LoyaltyView.vue'),
    meta: { title: 'Programa de Lealtad', requiresAuth: true }
  },

  // Otras rutas
  {
    path: '/help',
    name: 'help',
    component: () => import('@/views/HelpView.vue'),
    meta: { title: 'Centro de Ayuda' }
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'not-found',
    component: () => import('@/views/NotFoundView.vue'),
    meta: { title: 'Página No Encontrada' }
  }
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) {
      return savedPosition
    } else {
      return { top: 0 }
    }
  }
})

// Navigation guard para rutas protegidas
router.beforeEach((to, from, next) => {
  const authStore = useAuthStore()

  // Actualizar título de la página
  document.title = to.meta.title
    ? `${to.meta.title} - Pedidos en Línea`
    : 'Pedidos en Línea'

  // Verificar autenticación
  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    next({ name: 'login', query: { redirect: to.fullPath } })
  } else {
    next()
  }
})

export default router
