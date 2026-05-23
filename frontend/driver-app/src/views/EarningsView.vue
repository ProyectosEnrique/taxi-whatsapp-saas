<template>
  <div class="min-h-screen bg-gray-50">
    <!-- Header -->
    <header class="bg-white shadow-sm sticky top-0 z-10">
      <div class="max-w-7xl mx-auto px-4 py-4">
        <div class="flex items-center space-x-4">
          <button
            @click="goBack"
            class="p-2 hover:bg-gray-100 rounded-lg"
          >
            <span class="text-2xl">←</span>
          </button>
          <div class="flex-1">
            <h1 class="text-xl font-bold text-gray-900">Ganancias</h1>
            <p class="text-sm text-gray-500">Resumen de tus ingresos</p>
          </div>
        </div>
      </div>
    </header>

    <!-- Contenido -->
    <main class="max-w-7xl mx-auto px-4 py-6">
      <!-- Selector de periodo -->
      <div class="bg-white rounded-lg shadow mb-6 p-4">
        <div class="flex items-center space-x-2">
          <button
            v-for="period in periods"
            :key="period.value"
            @click="selectedPeriod = period.value; loadEarnings()"
            :class="[
              'px-4 py-2 rounded-lg font-medium transition-all',
              selectedPeriod === period.value
                ? 'bg-taxi-yellow text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            ]"
          >
            {{ period.label }}
          </button>
        </div>
      </div>

      <!-- Loading -->
      <div v-if="loading" class="flex items-center justify-center h-64">
        <div class="text-center">
          <div class="text-6xl mb-4">⏳</div>
          <p class="text-gray-500">Cargando ganancias...</p>
        </div>
      </div>

      <!-- Error -->
      <div v-else-if="error" class="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
        <div class="text-6xl mb-4">❌</div>
        <p class="text-red-600">{{ error }}</p>
      </div>

      <!-- Resumen de ganancias -->
      <div v-else class="space-y-6">
        <!-- Tarjeta principal -->
        <div class="bg-gradient-to-r from-green-500 to-green-600 text-white rounded-lg shadow-lg p-8">
          <div class="text-center">
            <p class="text-lg mb-2">{{ getPeriodLabel() }}</p>
            <p class="text-6xl font-bold mb-4">${{ earnings.total.toFixed(2) }}</p>
            <div class="flex items-center justify-center space-x-6 text-green-100">
              <span>🚗 {{ earnings.total_rides }} viajes</span>
              <span>📊 ${{ earnings.average_per_ride.toFixed(2) }} promedio</span>
            </div>
          </div>
        </div>

        <!-- Estadísticas detalladas -->
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div class="bg-white rounded-lg p-6 shadow">
            <div class="flex items-center justify-between mb-4">
              <h3 class="text-sm font-medium text-gray-500">Total Ganado</h3>
              <span class="text-2xl">💰</span>
            </div>
            <p class="text-3xl font-bold text-gray-900">${{ earnings.total.toFixed(2) }}</p>
          </div>

          <div class="bg-white rounded-lg p-6 shadow">
            <div class="flex items-center justify-between mb-4">
              <h3 class="text-sm font-medium text-gray-500">En Efectivo</h3>
              <span class="text-2xl">💵</span>
            </div>
            <p class="text-3xl font-bold text-gray-900">${{ earnings.cash.toFixed(2) }}</p>
            <p class="text-sm text-gray-500 mt-1">{{ earnings.cash_rides }} viajes</p>
          </div>

          <div class="bg-white rounded-lg p-6 shadow">
            <div class="flex items-center justify-between mb-4">
              <h3 class="text-sm font-medium text-gray-500">Con Tarjeta</h3>
              <span class="text-2xl">💳</span>
            </div>
            <p class="text-3xl font-bold text-gray-900">${{ earnings.card.toFixed(2) }}</p>
            <p class="text-sm text-gray-500 mt-1">{{ earnings.card_rides }} viajes</p>
          </div>
        </div>

        <!-- Desglose por día (si aplica) -->
        <div v-if="earnings.daily_breakdown && earnings.daily_breakdown.length > 0" class="bg-white rounded-lg shadow p-6">
          <h3 class="text-lg font-semibold text-gray-900 mb-4">Desglose Diario</h3>
          <div class="space-y-3">
            <div
              v-for="day in earnings.daily_breakdown"
              :key="day.date"
              class="flex items-center justify-between p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition"
            >
              <div>
                <p class="font-medium text-gray-900">{{ formatDate(day.date) }}</p>
                <p class="text-sm text-gray-500">{{ day.rides }} viajes</p>
              </div>
              <div class="text-right">
                <p class="text-xl font-bold text-green-600">${{ day.earnings.toFixed(2) }}</p>
                <p class="text-sm text-gray-500">${{ (day.earnings / day.rides).toFixed(2) }} promedio</p>
              </div>
            </div>
          </div>
        </div>

        <!-- Mejor día -->
        <div v-if="earnings.best_day" class="bg-white rounded-lg shadow p-6">
          <h3 class="text-lg font-semibold text-gray-900 mb-4">🏆 Mejor Día</h3>
          <div class="flex items-center justify-between">
            <div>
              <p class="text-xl font-semibold text-gray-900">{{ formatDate(earnings.best_day.date) }}</p>
              <p class="text-sm text-gray-500">{{ earnings.best_day.rides }} viajes completados</p>
            </div>
            <p class="text-4xl font-bold text-green-600">${{ earnings.best_day.earnings.toFixed(2) }}</p>
          </div>
        </div>

        <!-- Objetivos -->
        <div class="bg-white rounded-lg shadow p-6">
          <h3 class="text-lg font-semibold text-gray-900 mb-4">Objetivos de Ganancias</h3>

          <!-- Objetivo diario -->
          <div class="mb-4">
            <div class="flex items-center justify-between mb-2">
              <span class="text-sm font-medium text-gray-700">Objetivo Diario: $500</span>
              <span class="text-sm font-medium text-gray-700">
                ${{ earnings.today?.toFixed(2) || '0.00' }} / $500
              </span>
            </div>
            <div class="w-full bg-gray-200 rounded-full h-4">
              <div
                class="bg-green-500 h-4 rounded-full transition-all"
                :style="{ width: `${Math.min(((earnings.today || 0) / 500) * 100, 100)}%` }"
              ></div>
            </div>
            <p class="text-xs text-gray-500 mt-1">
              {{ ((earnings.today || 0) / 500 * 100).toFixed(0) }}% completado
            </p>
          </div>

          <!-- Objetivo semanal -->
          <div>
            <div class="flex items-center justify-between mb-2">
              <span class="text-sm font-medium text-gray-700">Objetivo Semanal: $3,500</span>
              <span class="text-sm font-medium text-gray-700">
                ${{ earnings.total.toFixed(2) }} / $3,500
              </span>
            </div>
            <div class="w-full bg-gray-200 rounded-full h-4">
              <div
                class="bg-blue-500 h-4 rounded-full transition-all"
                :style="{ width: `${Math.min((earnings.total / 3500) * 100, 100)}%` }"
              ></div>
            </div>
            <p class="text-xs text-gray-500 mt-1">
              {{ (earnings.total / 3500 * 100).toFixed(0) }}% completado
            </p>
          </div>
        </div>

        <!-- Tips y consejos -->
        <div class="bg-blue-50 border border-blue-200 rounded-lg p-6">
          <h3 class="text-lg font-semibold text-blue-900 mb-3">💡 Consejos para Aumentar Ganancias</h3>
          <ul class="space-y-2 text-sm text-blue-800">
            <li>• Trabaja durante las horas pico (7-9 AM, 5-8 PM)</li>
            <li>• Mantén una alta tasa de aceptación para recibir más viajes</li>
            <li>• Prioriza áreas con alta demanda (centros comerciales, aeropuertos)</li>
            <li>• Ofrece un excelente servicio para obtener mejores calificaciones</li>
            <li>• Mantén tu vehículo limpio y en buen estado</li>
          </ul>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { earningsApi } from '../services/api'

const router = useRouter()

const loading = ref(true)
const error = ref(null)
const selectedPeriod = ref('week')

const periods = [
  { value: 'today', label: 'Hoy' },
  { value: 'week', label: 'Esta Semana' },
  { value: 'month', label: 'Este Mes' },
  { value: 'year', label: 'Este Año' }
]

const earnings = ref({
  total: 0,
  total_rides: 0,
  average_per_ride: 0,
  cash: 0,
  cash_rides: 0,
  card: 0,
  card_rides: 0,
  today: 0,
  daily_breakdown: [],
  best_day: null
})

const loadEarnings = async () => {
  loading.value = true
  error.value = null

  try {
    const response = await earningsApi.getEarnings(selectedPeriod.value)
    earnings.value = {
      total: response.total || 0,
      total_rides: response.total_rides || 0,
      average_per_ride: response.average_per_ride || 0,
      cash: response.cash || 0,
      cash_rides: response.cash_rides || 0,
      card: response.card || 0,
      card_rides: response.card_rides || 0,
      today: response.today || 0,
      daily_breakdown: response.daily_breakdown || [],
      best_day: response.best_day || null
    }
  } catch (err) {
    error.value = 'Error al cargar ganancias'
    console.error(err)
  } finally {
    loading.value = false
  }
}

const getPeriodLabel = () => {
  const labels = {
    today: 'Ganancias de Hoy',
    week: 'Ganancias de Esta Semana',
    month: 'Ganancias de Este Mes',
    year: 'Ganancias de Este Año'
  }
  return labels[selectedPeriod.value] || 'Ganancias'
}

const formatDate = (dateString) => {
  const date = new Date(dateString)
  const options = { weekday: 'long', month: 'short', day: 'numeric' }
  return date.toLocaleDateString('es-ES', options)
}

const goBack = () => {
  router.push('/dashboard')
}

onMounted(() => {
  loadEarnings()
})
</script>
