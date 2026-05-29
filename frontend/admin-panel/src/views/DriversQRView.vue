<template>
  <div class="p-8">
    <!-- Header -->
    <div class="flex items-center justify-between mb-6">
      <div>
        <h1 class="text-3xl font-bold text-gray-900">Códigos QR — Taxis</h1>
        <p class="text-gray-500 mt-1">Un código QR único por conductor. Colócalo en el asiento para que pasajeros puedan reportar o contactar.</p>
      </div>
    </div>

    <!-- Config -->
    <div class="bg-white rounded-lg shadow p-5 mb-6 flex gap-4 flex-wrap items-end">
      <div class="flex-1 min-w-48">
        <label class="block text-xs font-semibold text-gray-500 uppercase mb-1">Número WhatsApp de la empresa</label>
        <input
          v-model="waNumber"
          @change="save('wa_number_taxi', waNumber)"
          placeholder="521XXXXXXXXXX"
          class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-yellow-400"
        />
        <p class="text-xs text-gray-400 mt-1">Sin + ni espacios. Ej: 5214611234567</p>
      </div>
      <div class="flex-1 min-w-48">
        <label class="block text-xs font-semibold text-gray-500 uppercase mb-1">URL base de la app</label>
        <input
          v-model="appUrl"
          @change="save('app_url_taxi', appUrl)"
          placeholder="https://taxi.nexoai.lat"
          class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-yellow-400"
        />
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="text-center py-16 text-gray-400">
      <div class="text-5xl mb-3">⏳</div>
      <p>Cargando conductores...</p>
    </div>

    <!-- Empty -->
    <div v-else-if="drivers.length === 0" class="text-center py-16 text-gray-400">
      <div class="text-5xl mb-3">🚕</div>
      <p>No hay conductores registrados.</p>
    </div>

    <!-- Driver QR Grid -->
    <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
      <div
        v-for="d in drivers"
        :key="d.driver_id"
        class="bg-white rounded-xl shadow p-5 flex flex-col items-center text-center"
        :class="!d.is_active ? 'opacity-50' : ''"
      >
        <!-- Driver info -->
        <div class="w-14 h-14 rounded-full bg-yellow-100 flex items-center justify-center text-yellow-700 font-bold text-2xl mb-2">
          {{ d.name.charAt(0).toUpperCase() }}
        </div>
        <h3 class="font-bold text-gray-900 text-base">{{ d.name }}</h3>
        <p class="text-xs text-gray-500 mb-1">{{ d.phone }}</p>
        <p class="text-xs text-gray-600 font-medium mb-3">
          🚗 {{ d.vehicle?.brand }} {{ d.vehicle?.model }}
          <span class="ml-1 bg-gray-100 text-gray-700 px-1.5 py-0.5 rounded font-mono">{{ d.vehicle?.plates }}</span>
        </p>

        <!-- QR Image -->
        <img
          :src="qrUrl(d)"
          :alt="`QR ${d.name}`"
          class="w-36 h-36 border-2 border-yellow-200 rounded-lg mb-3"
        />

        <!-- QR link preview -->
        <p class="text-xs text-gray-400 break-all max-w-[200px] mb-3">{{ waLink(d) }}</p>

        <!-- Actions -->
        <div class="flex gap-2 w-full">
          <a
            :href="qrUrl(d)"
            :download="`qr-taxi-${d.vehicle?.plates || d.driver_id}.png`"
            class="flex-1 text-center text-xs font-semibold py-2 px-3 bg-yellow-500 text-gray-900 rounded-lg hover:bg-yellow-400 transition"
          >⬇ Descargar</a>
          <button
            @click="printQR(d)"
            class="flex-1 text-xs font-semibold py-2 px-3 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition"
          >🖨 Imprimir</button>
        </div>
      </div>
    </div>

    <!-- Print overlay -->
    <div v-if="printDriver" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4" @click.self="printDriver = null">
      <div class="bg-white rounded-2xl shadow-2xl p-8 text-center max-w-sm w-full">
        <div class="text-5xl mb-2">🚕</div>
        <h2 class="text-xl font-bold text-gray-900 mb-1">{{ printDriver.name }}</h2>
        <p class="text-sm text-gray-500 mb-1">{{ printDriver.vehicle?.brand }} {{ printDriver.vehicle?.model }}</p>
        <p class="text-lg font-mono font-bold text-gray-700 mb-4">{{ printDriver.vehicle?.plates }}</p>
        <img :src="qrUrl(printDriver)" class="w-48 h-48 border-2 border-yellow-200 rounded-xl mx-auto mb-4" />
        <p class="text-xs text-gray-400 mb-6">Escanea el código QR para reportar o contactar</p>
        <button @click="doPrint(printDriver)" class="w-full py-2.5 bg-yellow-500 text-gray-900 font-bold rounded-lg hover:bg-yellow-400 transition mb-2">
          🖨 Imprimir ahora
        </button>
        <button @click="printDriver = null" class="w-full py-2 text-sm text-gray-500 hover:text-gray-700 transition">
          Cerrar
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const QR_API = 'https://api.qrserver.com/v1/create-qr-code/?size=250x250&format=png&data='

const waNumber  = ref(localStorage.getItem('wa_number_taxi') || '521XXXXXXXXXX')
const appUrl    = ref(localStorage.getItem('app_url_taxi') || 'https://taxi.nexoai.lat')
const drivers   = ref([])
const loading   = ref(true)
const printDriver = ref(null)

function save(key, val) {
  localStorage.setItem(key, val)
}

function waLink(d) {
  const plates = d.vehicle?.plates || ''
  const msg = `Hola, estoy en el taxi de ${d.name} placas ${plates}`
  return `https://wa.me/${waNumber.value}?text=${encodeURIComponent(msg)}`
}

function qrUrl(d) {
  return QR_API + encodeURIComponent(waLink(d))
}

function printQR(d) {
  printDriver.value = d
}

function doPrint(d) {
  const w = window.open('', '_blank', 'width=480,height=640')
  w.document.write(`
    <html><head><title>QR Taxi ${d.name}</title>
    <style>
      body { font-family: system-ui, sans-serif; text-align: center; padding: 2rem; }
      h2 { color: #374151; margin: .5rem 0; font-size: 1.4rem; }
      .plates { font-size: 1.6rem; font-family: monospace; font-weight: 700; background: #f9fafb; padding: .3rem .8rem; border-radius: .5rem; display: inline-block; margin-bottom: 1rem; }
      p { color: #6b7280; font-size: .9rem; }
      img { width: 200px; height: 200px; border: 2px solid #fde68a; border-radius: .75rem; margin: 1rem auto; display: block; }
      .hint { font-size: .8rem; color: #9ca3af; margin-top: .5rem; }
    </style></head>
    <body>
      <div style="font-size:2.5rem">🚕</div>
      <h2>${d.name}</h2>
      <p>${d.vehicle?.brand || ''} ${d.vehicle?.model || ''}</p>
      <div class="plates">${d.vehicle?.plates || ''}</div>
      <img src="${qrUrl(d)}" />
      <p class="hint">Escanea para contactar o reportar</p>
      <script>window.onload=()=>window.print()<\/script>
    </body></html>
  `)
  w.document.close()
}

async function loadDrivers() {
  loading.value = true
  try {
    const res = await fetch('/api/v1/admin/drivers')
    if (res.ok) {
      const data = await res.json()
      drivers.value = (data.drivers || []).filter(d => d.is_active)
    }
  } catch (e) {
    console.error('loadDrivers:', e)
  } finally {
    loading.value = false
  }
}

onMounted(loadDrivers)
</script>
