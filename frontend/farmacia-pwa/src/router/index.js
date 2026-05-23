/**
 * Vue Router - Multi-Tenant Ready
 * Configuración de rutas con soporte para tenant_id
 */
import { createRouter, createWebHistory } from 'vue-router'

// Lazy loading de vistas
const MenuView = () => import('@/views/MenuView.vue')
const CheckoutView = () => import('@/views/CheckoutView.vue')

const routes = [
  {
    path: '/',
    name: 'home',
    component: MenuView,
    meta: {
      title: 'Inicio',
      requiresAuth: false
    }
  },
  {
    path: '/menu',
    name: 'menu',
    component: MenuView,
    meta: {
      title: 'Menu',
      requiresAuth: false
    }
  },
  {
    path: '/categoria/:categoryId',
    name: 'category',
    component: MenuView,
    meta: {
      title: 'Categoria',
      requiresAuth: false
    }
  },
  {
    path: '/checkout',
    name: 'checkout',
    component: CheckoutView,
    meta: {
      title: 'Checkout',
      requiresAuth: false
    }
  },
  // Redirect cualquier ruta no encontrada a home
  {
    path: '/:pathMatch(.*)*',
    redirect: '/'
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) {
      return savedPosition
    } else {
      return { top: 0 }
    }
  }
})

// Guard para actualizar título de la página
router.beforeEach((to, from, next) => {
  // Obtener nombre del tenant desde query params o usar default
  const tenantName = 'Farmacia Santa Fe'
  document.title = to.meta.title ? `${to.meta.title} | ${tenantName}` : tenantName
  next()
})

export default router
