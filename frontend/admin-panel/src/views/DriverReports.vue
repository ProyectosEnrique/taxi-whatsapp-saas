<template>
  <div class="p-8">
    <div class="flex items-center justify-between mb-6">
      <div>
        <h1 class="text-3xl font-bold text-gray-900">Reportes por Conductor</h1>
        <p class="text-gray-500 mt-1">Ganancias y viajes por periodo para liquidaciones</p>
      </div>
    </div>

    <!-- Date range filter -->
    <div class="bg-white rounded-lg shadow p-4 mb-6 flex items-end space-x-4">
      <div>
        <label class="block text-xs font-medium text-gray-500 mb-1">Desde</label>
        <input v-model="fromDate" type="date" class="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-yellow-400" />
      </div>
      <div>
        <label class="block text-xs font-medium text-gray-500 mb-1">Hasta</label>
        <input v-model="toDate" type="date" class="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-yellow-400" />
      </div>
      <button @click="load" class="px-5 py-2 bg-yellow-400 hover:bg-yellow-500 text-gray-900 font-semibold rounded-lg text-sm transition">
        Consultar
      </button>
      <div class="flex space-x-2 ml-4">
        <button @click="setPreset('week')"  class="px-3 py-2 text-xs bg-gray-100 hover:bg-gray-200 rounded-lg">Esta semana</button>
        <button @click="setPreset('month')" class="px-3 py-2 text-xs bg-gray-100 hover:bg-gray-200 rounded-lg">Este mes</button>
        <button @click="setPreset('today')" class="px-3 py-2 text-xs bg-gray-100 hover:bg-gray-200 rounded-lg">Hoy</button>
      </div>
    </div>

    <!-- Loading / error -->
    <div v-if="loading" class="flex items-center justify-center h-40">
      <div class="text-center">
        <div class="text-5xl mb-3">⏳</div>
        <p class="text-gray-500">Cargando reporte...</p>
      </div>
    </div>
    <div v-else-if="error" class="bg-red-50 border border-red-200 rounded-lg p-6 text-center text-red-600">{{ error }}</div>

    <template v-else-if="report">
      <!-- Summary cards -->
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div class="bg-white rounded-lg shadow p-6">
          <p class="text-xs font-medium text-gray-500 uppercase mb-1">Total viajes</p>
          <p class="text-4xl font-bold text-gray-900">{{ report.total_trips }}</p>
          <p class="text-xs text-gray-400 mt-1">{{ report.period.from }} → {{ report.period.to }}</p>
        </div>
        <div class="bg-white rounded-lg shadow p-6">
          <p class="text-xs font-medium text-gray-500 uppercase mb-1">Ingresos totales</p>
          <p class="text-4xl font-bold text-green-600">${{ report.total_earnings.toFixed(2) }}</p>
          <p class="text-xs text-gray-400 mt-1">MXN · todos los conductores</p>
        </div>
        <div class="bg-white rounded-lg shadow p-6">
          <p class="text-xs font-medium text-gray-500 uppercase mb-1">Conductores activos</p>
          <p class="text-4xl font-bold text-blue-600">{{ report.drivers.length }}</p>
          <p class="text-xs text-gray-400 mt-1">con al menos 1 viaje</p>
        </div>
      </div>

      <!-- Table -->
      <div class="bg-white rounded-lg shadow overflow-hidden">
        <div class="p-5 border-b border-gray-200 flex items-center justify-between">
          <h2 class="text-lg font-semibold text-gray-900">Desglose por conductor</h2>
          <button @click="exportCSV" class="px-3 py-1.5 text-xs bg-gray-100 hover:bg-gray-200 rounded-lg text-gray-700">
            ⬇ Exportar CSV
          </button>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead class="bg-gray-50 text-xs font-medium text-gray-500 uppercase">
              <tr>
                <th class="px-4 py-3 text-left">Conductor</th>
                <th class="px-4 py-3 text-center">Viajes</th>
                <th class="px-4 py-3 text-right">Total</th>
                <th class="px-4 py-3 text-right">Efectivo</th>
                <th class="px-4 py-3 text-right">Tarjeta</th>
                <th class="px-4 py-3 text-center">Calificación</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-100">
              <tr v-for="d in report.drivers" :key="d.phone" class="hover:bg-gray-50">
                <td class="px-4 py-3">
                  <p class="font-medium text-gray-900">{{ d.name }}</p>
                  <p class="text-xs text-gray-500">{{ d.phone }}</p>
                </td>
                <td class="px-4 py-3 text-center font-semibold text-gray-700">{{ d.trips }}</td>
                <td class="px-4 py-3 text-right font-bold text-green-600">${{ d.earnings.toFixed(2) }}</td>
                <td class="px-4 py-3 text-right text-gray-700">${{ d.cash_earnings.toFixed(2) }}</td>
                <td class="px-4 py-3 text-right text-gray-700">${{ d.card_earnings.toFixed(2) }}</td>
                <td class="px-4 py-3 text-center text-yellow-500">⭐ {{ d.rating.toFixed(1) }}</td>
              </tr>
            </tbody>
            <!-- Totals row -->
            <tfoot class="bg-gray-50 font-bold text-sm border-t-2 border-gray-200">
              <tr>
                <td class="px-4 py-3 text-gray-700">TOTAL</td>
                <td class="px-4 py-3 text-center text-gray-900">{{ report.total_trips }}</td>
                <td class="px-4 py-3 text-right text-green-600">${{ report.total_earnings.toFixed(2) }}</td>
                <td class="px-4 py-3 text-right text-gray-700">${{ totalCash.toFixed(2) }}</td>
                <td class="px-4 py-3 text-right text-gray-700">${{ totalCard.toFixed(2) }}</td>
                <td></td>
              </tr>
            </tfoot>
          </table>
        </div>
        <div v-if="report.drivers.length === 0" class="p-10 text-center text-gray-400">
          <div class="text-4xl mb-2">📭</div>
          <p>No hay viajes completados en este periodo</p>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const loading  = ref(false)
const error    = ref(null)
const report   = ref(null)

// Default: current month
const today = new Date()
const fromDate = ref(today.toISOString().slice(0, 8) + '01')
const toDate   = ref(today.toISOString().slice(0, 10))

const totalCash = computed(() => report.value?.drivers.reduce((s, d) => s + d.cash_earnings, 0) ?? 0)
const totalCard = computed(() => report.value?.drivers.reduce((s, d) => s + d.card_earnings, 0) ?? 0)

function setPreset(preset) {
  const now = new Date()
  const pad = n => String(n).padStart(2, '0')
  if (preset === 'today') {
    fromDate.value = now.toISOString().slice(0, 10)
    toDate.value   = now.toISOString().slice(0, 10)
  } else if (preset === 'week') {
    const mon = new Date(now)
    mon.setDate(now.getDate() - now.getDay() + 1)
    fromDate.value = `${mon.getFullYear()}-${pad(mon.getMonth()+1)}-${pad(mon.getDate())}`
    toDate.value   = now.toISOString().slice(0, 10)
  } else if (preset === 'month') {
    fromDate.value = `${now.getFullYear()}-${pad(now.getMonth()+1)}-01`
    toDate.value   = now.toISOString().slice(0, 10)
  }
  load()
}

async function load() {
  loading.value = true
  error.value   = null
  try {
    const params = new URLSearchParams()
    if (fromDate.value) params.set('from_date', fromDate.value)
    if (toDate.value)   params.set('to_date',   toDate.value)
    const res = await fetch(`/api/v1/admin/reports/drivers?${params}`)
    if (!res.ok) throw new Error(`Error ${res.status}`)
    report.value = await res.json()
  } catch (e) {
    error.value = 'No se pudo cargar el reporte. ' + e.message
  } finally {
    loading.value = false
  }
}

function exportCSV() {
  if (!report.value) return
  const rows = [
    ['Conductor', 'Teléfono', 'Viajes', 'Total', 'Efectivo', 'Tarjeta', 'Calificación'],
    ...report.value.drivers.map(d => [
      d.name, d.phone, d.trips, d.earnings.toFixed(2),
      d.cash_earnings.toFixed(2), d.card_earnings.toFixed(2), d.rating.toFixed(1)
    ]),
    ['TOTAL', '', report.value.total_trips, report.value.total_earnings.toFixed(2),
     totalCash.value.toFixed(2), totalCard.value.toFixed(2), ''],
  ]
  const csv = rows.map(r => r.join(',')).join('\n')
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
  const url  = URL.createObjectURL(blob)
  const a    = document.createElement('a')
  a.href     = url
  a.download = `reporte_conductores_${fromDate.value}_${toDate.value}.csv`
  a.click()
  URL.revokeObjectURL(url)
}

// Load on mount with default range
load()
</script>
