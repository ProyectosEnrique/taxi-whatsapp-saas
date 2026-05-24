<template>
  <div class="fare-configuration p-8">
    <!-- Header -->
    <div class="page-header">
      <div>
        <h1 class="text-3xl font-bold text-gray-900">Configuración de Tarifas</h1>
        <p class="text-gray-600 mt-1">Administra los precios y recargos del servicio</p>
      </div>

      <button @click="saveConfiguration" :disabled="saving" class="btn btn-primary">
        <svg v-if="saving" class="w-5 h-5 mr-2 animate-spin" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/>
        </svg>
        <svg v-else class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3 3m0 0l-3-3m3 3V4" />
        </svg>
        {{ saving ? 'Guardando...' : 'Guardar Cambios' }}
      </button>
    </div>

    <!-- Toast -->
    <transition name="fade">
      <div
        v-if="toast"
        :class="[
          'fixed top-6 right-6 z-50 px-5 py-3 rounded-lg shadow-lg text-white text-sm font-medium flex items-center space-x-2',
          toast.type === 'success' ? 'bg-green-600' : 'bg-red-600'
        ]"
      >
        <span>{{ toast.type === 'success' ? '✓' : '✗' }}</span>
        <span>{{ toast.message }}</span>
      </div>
    </transition>

    <!-- Loading overlay -->
    <div v-if="loading" class="flex items-center justify-center py-20 text-gray-500">
      <svg class="w-8 h-8 animate-spin mr-3" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/>
      </svg>
      Cargando configuración...
    </div>

    <div v-else>

    <!-- Warning Banner -->
    <div v-if="hasUnsavedChanges" class="bg-yellow-50 border-l-4 border-yellow-400 p-4 mb-6">
      <div class="flex">
        <svg class="h-5 w-5 text-yellow-400" fill="currentColor" viewBox="0 0 20 20">
          <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/>
        </svg>
        <div class="ml-3">
          <p class="text-sm text-yellow-700">
            Tienes cambios sin guardar. No olvides guardar antes de salir.
          </p>
        </div>
      </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <!-- Sidebar - Navigation -->
      <div class="lg:col-span-1">
        <div class="bg-white rounded-lg shadow p-4 sticky top-4">
          <nav class="space-y-1">
            <a
              v-for="section in sections"
              :key="section.id"
              @click="activeSection = section.id"
              :class="[
                activeSection === section.id
                  ? 'bg-blue-50 text-blue-700 border-l-4 border-blue-700'
                  : 'text-gray-600 hover:bg-gray-50',
                'flex items-center space-x-2 px-4 py-3 cursor-pointer transition-colors'
              ]"
            >
              <span>{{ section.emoji }}</span>
              <span class="font-medium">{{ section.label }}</span>
            </a>
          </nav>

          <!-- Preview Card -->
          <div class="mt-6 p-4 bg-gray-50 rounded-lg">
            <h3 class="text-sm font-semibold text-gray-900 mb-2">Vista Previa</h3>
            <div class="space-y-1 text-xs">
              <div class="flex justify-between">
                <span class="text-gray-600">Banderazo:</span>
                <span class="font-medium">${{ config.base_fare }}</span>
              </div>
              <div class="flex justify-between">
                <span class="text-gray-600">Por km:</span>
                <span class="font-medium">${{ config.per_km_rate }}</span>
              </div>
              <div class="flex justify-between">
                <span class="text-gray-600">Por min:</span>
                <span class="font-medium">${{ config.per_minute_rate }}</span>
              </div>
              <div class="border-t border-gray-300 my-2"></div>
              <div class="flex justify-between font-semibold">
                <span>Ejemplo (10km, 20min):</span>
                <span>${{ calculateExample() }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Main Content -->
      <div class="lg:col-span-2">
        <!-- Base Fares -->
        <section v-show="activeSection === 'base'" class="bg-white rounded-lg shadow p-6 mb-6">
          <h2 class="text-xl font-semibold text-gray-900 mb-6">Tarifas Base</h2>

          <div class="space-y-6">
            <!-- Base Fare -->
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-2">
                Banderazo
                <span class="text-gray-500 font-normal">(Tarifa inicial)</span>
              </label>
              <div class="relative">
                <span class="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-500">$</span>
                <input
                  v-model.number="config.base_fare"
                  type="number"
                  step="1"
                  class="input pl-8"
                  @input="markAsChanged"
                />
              </div>
            </div>

            <!-- Per KM Rate -->
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-2">
                Tarifa por Kilómetro
              </label>
              <div class="relative">
                <span class="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-500">$</span>
                <input
                  v-model.number="config.per_km_rate"
                  type="number"
                  step="0.5"
                  class="input pl-8"
                  @input="markAsChanged"
                />
              </div>
            </div>

            <!-- Per Minute Rate -->
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-2">
                Tarifa por Minuto
                <span class="text-gray-500 font-normal">(Compensación por tráfico)</span>
              </label>
              <div class="relative">
                <span class="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-500">$</span>
                <input
                  v-model.number="config.per_minute_rate"
                  type="number"
                  step="0.5"
                  class="input pl-8"
                  @input="markAsChanged"
                />
              </div>
            </div>

            <!-- Minimum Fare -->
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-2">
                Tarifa Mínima
              </label>
              <div class="relative">
                <span class="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-500">$</span>
                <input
                  v-model.number="config.minimum_fare"
                  type="number"
                  step="5"
                  class="input pl-8"
                  @input="markAsChanged"
                />
              </div>
            </div>
          </div>
        </section>

        <!-- Surge Pricing -->
        <section v-show="activeSection === 'surge'" class="bg-white rounded-lg shadow p-6 mb-6">
          <h2 class="text-xl font-semibold text-gray-900 mb-4">Surge Pricing (Recargos Dinámicos)</h2>
          <p class="text-sm text-gray-600 mb-6">
            Ajusta los precios automáticamente según la demanda y hora del día
          </p>

          <div class="space-y-6">
            <!-- Enable Surge -->
            <div class="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
              <div>
                <p class="font-medium text-gray-900">Activar Surge Pricing</p>
                <p class="text-sm text-gray-500">Recargos automáticos en horas pico</p>
              </div>
              <label class="relative inline-flex items-center cursor-pointer">
                <input
                  v-model="config.surge_pricing.enabled"
                  type="checkbox"
                  class="sr-only peer"
                  @change="markAsChanged"
                />
                <div class="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
              </label>
            </div>

            <div v-if="config.surge_pricing.enabled">
              <!-- Peak Hours Multiplier -->
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-2">
                  Multiplicador Hora Pico (7-9am, 6-9pm)
                </label>
                <div class="flex items-center space-x-4">
                  <input
                    v-model.number="config.surge_pricing.peak_hours_multiplier"
                    type="range"
                    min="1.0"
                    max="2.0"
                    step="0.1"
                    class="flex-1"
                    @input="markAsChanged"
                  />
                  <span class="text-lg font-semibold text-gray-900 w-16">
                    {{ config.surge_pricing.peak_hours_multiplier }}x
                  </span>
                </div>
                <p class="text-xs text-gray-500 mt-1">
                  +{{ ((config.surge_pricing.peak_hours_multiplier - 1) * 100).toFixed(0) }}% sobre tarifa normal
                </p>
              </div>

              <!-- Late Night Multiplier -->
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-2">
                  Multiplicador Madrugada (11pm-5am)
                </label>
                <div class="flex items-center space-x-4">
                  <input
                    v-model.number="config.surge_pricing.late_night_multiplier"
                    type="range"
                    min="1.0"
                    max="2.5"
                    step="0.1"
                    class="flex-1"
                    @input="markAsChanged"
                  />
                  <span class="text-lg font-semibold text-gray-900 w-16">
                    {{ config.surge_pricing.late_night_multiplier }}x
                  </span>
                </div>
                <p class="text-xs text-gray-500 mt-1">
                  +{{ ((config.surge_pricing.late_night_multiplier - 1) * 100).toFixed(0) }}% sobre tarifa normal
                </p>
              </div>

              <!-- Weekend Multiplier -->
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-2">
                  Multiplicador Fin de Semana
                </label>
                <div class="flex items-center space-x-4">
                  <input
                    v-model.number="config.surge_pricing.weekend_multiplier"
                    type="range"
                    min="1.0"
                    max="1.5"
                    step="0.05"
                    class="flex-1"
                    @input="markAsChanged"
                  />
                  <span class="text-lg font-semibold text-gray-900 w-16">
                    {{ config.surge_pricing.weekend_multiplier }}x
                  </span>
                </div>
                <p class="text-xs text-gray-500 mt-1">
                  +{{ ((config.surge_pricing.weekend_multiplier - 1) * 100).toFixed(0) }}% sobre tarifa normal
                </p>
              </div>
            </div>
          </div>
        </section>

        <!-- Special Charges -->
        <section v-show="activeSection === 'special'" class="bg-white rounded-lg shadow p-6 mb-6">
          <h2 class="text-xl font-semibold text-gray-900 mb-6">Recargos Especiales</h2>

          <div class="space-y-4">
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-2">Recogida en Aeropuerto</label>
                <div class="relative">
                  <span class="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-500">$</span>
                  <input
                    v-model.number="config.special_charges.airport_pickup"
                    type="number"
                    step="5"
                    class="input pl-8"
                    @input="markAsChanged"
                  />
                </div>
              </div>

              <div>
                <label class="block text-sm font-medium text-gray-700 mb-2">Destino Aeropuerto</label>
                <div class="relative">
                  <span class="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-500">$</span>
                  <input
                    v-model.number="config.special_charges.airport_dropoff"
                    type="number"
                    step="5"
                    class="input pl-8"
                    @input="markAsChanged"
                  />
                </div>
              </div>

              <div>
                <label class="block text-sm font-medium text-gray-700 mb-2">Pasajero Extra</label>
                <div class="relative">
                  <span class="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-500">$</span>
                  <input
                    v-model.number="config.special_charges.extra_passenger"
                    type="number"
                    step="5"
                    class="input pl-8"
                    @input="markAsChanged"
                  />
                </div>
              </div>

              <div>
                <label class="block text-sm font-medium text-gray-700 mb-2">Equipaje Grande</label>
                <div class="relative">
                  <span class="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-500">$</span>
                  <input
                    v-model.number="config.special_charges.luggage"
                    type="number"
                    step="1"
                    class="input pl-8"
                    @input="markAsChanged"
                  />
                </div>
              </div>
            </div>
          </div>
        </section>

        <!-- Discounts -->
        <section v-show="activeSection === 'discounts'" class="bg-white rounded-lg shadow p-6">
          <h2 class="text-xl font-semibold text-gray-900 mb-6">Descuentos</h2>

          <div class="space-y-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-2">
                Cliente Frecuente
                <span class="text-gray-500 font-normal">(3+ viajes)</span>
              </label>
              <div class="flex items-center space-x-2">
                <input
                  v-model.number="config.discounts.frequent_rider"
                  type="number"
                  min="0"
                  max="1"
                  step="0.05"
                  class="input flex-1"
                  @input="markAsChanged"
                />
                <span class="text-gray-600">{{ (config.discounts.frequent_rider * 100).toFixed(0) }}%</span>
              </div>
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-700 mb-2">
                Cuenta Corporativa
              </label>
              <div class="flex items-center space-x-2">
                <input
                  v-model.number="config.discounts.corporate"
                  type="number"
                  min="0"
                  max="1"
                  step="0.05"
                  class="input flex-1"
                  @input="markAsChanged"
                />
                <span class="text-gray-600">{{ (config.discounts.corporate * 100).toFixed(0) }}%</span>
              </div>
            </div>
          </div>
        </section>
      </div>
    </div>
    </div> <!-- end v-else -->
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'

const API = '/api/v1/admin'

const activeSection = ref('base')
const hasUnsavedChanges = ref(false)
const loading = ref(false)
const saving = ref(false)
const toast = ref(null) // { type: 'success'|'error', message }

const sections = [
  { id: 'base',      label: 'Tarifas Base',        emoji: '💵' },
  { id: 'surge',     label: 'Surge Pricing',        emoji: '📈' },
  { id: 'special',   label: 'Recargos Especiales',  emoji: '⭐' },
  { id: 'discounts', label: 'Descuentos',           emoji: '🏷️' },
]

const config = reactive({
  base_fare: 50.0,
  per_km_rate: 8.0,
  per_minute_rate: 2.0,
  minimum_fare: 70.0,
  surge_pricing: {
    enabled: false,
    peak_hours_multiplier: 1.3,
    late_night_multiplier: 1.5,
    weekend_multiplier: 1.2,
  },
  special_charges: {
    airport_pickup: 30.0,
    airport_dropoff: 30.0,
    extra_passenger: 10.0,
    luggage: 5.0,
  },
  discounts: {
    frequent_rider: 0.10,
    corporate: 0.15,
  },
})

function applyConfig(data) {
  config.base_fare        = data.base_fare
  config.per_km_rate      = data.per_km_rate
  config.per_minute_rate  = data.per_minute_rate
  config.minimum_fare     = data.minimum_fare
  Object.assign(config.surge_pricing,   data.surge_pricing   || {})
  Object.assign(config.special_charges, data.special_charges || {})
  Object.assign(config.discounts,       data.discounts       || {})
}

function showToast(type, message) {
  toast.value = { type, message }
  setTimeout(() => { toast.value = null }, 3500)
}

function markAsChanged() {
  hasUnsavedChanges.value = true
}

function calculateExample() {
  const fare = config.base_fare + 10 * config.per_km_rate + 20 * config.per_minute_rate
  return Math.max(fare, config.minimum_fare).toFixed(2)
}

onMounted(async () => {
  loading.value = true
  try {
    const res = await fetch(`${API}/fares`)
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    applyConfig(await res.json())
    hasUnsavedChanges.value = false
  } catch (e) {
    showToast('error', 'No se pudo cargar la configuración')
  } finally {
    loading.value = false
  }
})

async function saveConfiguration() {
  saving.value = true
  try {
    const res = await fetch(`${API}/fares`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config),
    })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    if (data.config) applyConfig(data.config)
    hasUnsavedChanges.value = false
    showToast('success', 'Configuración guardada correctamente')
  } catch (e) {
    showToast('error', 'Error al guardar: ' + e.message)
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.page-header {
  @apply flex justify-between items-start mb-8;
}

.input {
  @apply w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent;
}

.btn {
  @apply px-6 py-3 rounded-lg font-medium transition-colors flex items-center disabled:opacity-50 disabled:cursor-not-allowed;
}

.btn-primary {
  @apply bg-blue-600 text-white hover:bg-blue-700;
}

.fade-enter-active, .fade-leave-active { transition: opacity 0.3s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
