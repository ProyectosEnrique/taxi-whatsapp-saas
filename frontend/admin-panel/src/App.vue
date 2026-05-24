<template>
  <div id="app" class="flex min-h-screen bg-gray-100">
    <!-- Sidebar -->
    <aside class="w-64 bg-gray-900 text-white flex flex-col flex-shrink-0">
      <!-- Logo -->
      <div class="px-6 py-5 border-b border-gray-700">
        <div class="flex items-center space-x-3">
          <span class="text-3xl">🚕</span>
          <div>
            <h1 class="text-lg font-bold leading-tight">TaxiAdmin</h1>
            <p class="text-xs text-gray-400">Panel de Control</p>
          </div>
        </div>
      </div>

      <!-- Nav -->
      <nav class="flex-1 px-3 py-4 space-y-1">
        <router-link
          v-for="item in navItems"
          :key="item.to"
          :to="item.to"
          class="flex items-center space-x-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors"
          :class="$route.path === item.to
            ? 'bg-yellow-500 text-gray-900'
            : 'text-gray-300 hover:bg-gray-800 hover:text-white'"
        >
          <span class="text-lg">{{ item.icon }}</span>
          <span>{{ item.label }}</span>
          <span
            v-if="item.badge"
            class="ml-auto bg-red-500 text-white text-xs font-bold px-1.5 py-0.5 rounded-full"
          >{{ item.badge }}</span>
        </router-link>
      </nav>

      <!-- Footer -->
      <div class="px-4 py-4 border-t border-gray-700 text-xs text-gray-500">
        v1.0 · {{ today }}
      </div>
    </aside>

    <!-- Main content -->
    <main class="flex-1 overflow-auto">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()

const today = computed(() =>
  new Date().toLocaleDateString('es-MX', { day: 'numeric', month: 'short' })
)

const navItems = [
  { to: '/',          icon: '📊', label: 'Dashboard' },
  { to: '/drivers',   icon: '🚗', label: 'Conductores' },
  { to: '/rides',     icon: '🗺️', label: 'Monitor de Viajes' },
  { to: '/incidents', icon: '🚨', label: 'Incidentes' },
  { to: '/fares',     icon: '💰', label: 'Tarifas' },
  { to: '/promos',    icon: '🏷️', label: 'Promociones' },
]
</script>
