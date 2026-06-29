<template>
  <div class="p-8">
    <!-- Header -->
    <div class="flex items-center justify-between mb-8">
      <div>
        <h1 class="text-3xl font-bold text-gray-900">Lugares Locales</h1>
        <p class="text-gray-500 mt-1">Puntos de interés para mejorar el geocoding en la ciudad</p>
      </div>
      <button
        @click="openAdd"
        class="flex items-center space-x-2 px-4 py-2 bg-yellow-500 hover:bg-yellow-600 text-gray-900 font-semibold rounded-lg transition text-sm"
      >
        <span>+</span>
        <span>Agregar Lugar</span>
      </button>
    </div>

    <!-- Search -->
    <div class="bg-white rounded-lg shadow p-4 mb-6">
      <input
        v-model="search"
        type="text"
        placeholder="Buscar por nombre..."
        class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-yellow-400 text-sm"
      />
    </div>

    <!-- Loading / Empty -->
    <div v-if="loading" class="text-center py-16 text-gray-400">Cargando...</div>
    <div v-else-if="filtered.length === 0" class="bg-white rounded-lg shadow p-12 text-center text-gray-400">
      <p class="text-4xl mb-3">📍</p>
      <p class="font-medium">No hay lugares guardados</p>
      <p class="text-sm mt-1">Agrega colonias, mercados, parques u otros puntos de referencia locales</p>
    </div>

    <!-- Table -->
    <div v-else class="bg-white rounded-lg shadow overflow-hidden">
      <table class="min-w-full divide-y divide-gray-200">
        <thead class="bg-gray-50">
          <tr>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Lugar</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Dirección / Referencia</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Coordenadas</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Agregado por</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Acciones</th>
          </tr>
        </thead>
        <tbody class="bg-white divide-y divide-gray-200">
          <tr v-for="poi in filtered" :key="poi.db_id" class="hover:bg-gray-50">
            <td class="px-6 py-4">
              <div class="flex items-center space-x-2">
                <span class="text-lg">📍</span>
                <span class="font-medium text-gray-900 text-sm">{{ poi.name }}</span>
              </div>
            </td>
            <td class="px-6 py-4 text-sm text-gray-500">{{ poi.address || '—' }}</td>
            <td class="px-6 py-4 text-xs text-gray-400 font-mono">
              {{ Number(poi.lat).toFixed(5) }}, {{ Number(poi.lng).toFixed(5) }}
            </td>
            <td class="px-6 py-4 text-sm text-gray-500">{{ poi.added_by }}</td>
            <td class="px-6 py-4">
              <button
                @click="confirmDelete(poi)"
                class="text-red-500 hover:text-red-700 text-sm font-medium transition"
              >🗑️ Eliminar</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Modal Agregar -->
    <div
      v-if="showModal"
      class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
      @click.self="closeModal"
    >
      <div class="bg-white rounded-2xl shadow-2xl w-full max-w-xl max-h-[90vh] overflow-y-auto">
        <div class="p-6">
          <div class="flex items-center justify-between mb-5">
            <h2 class="text-lg font-bold text-gray-900">Agregar Lugar Local</h2>
            <button @click="closeModal" class="text-gray-400 hover:text-gray-600 text-xl">✕</button>
          </div>

          <form @submit.prevent="savePoi" class="space-y-4">
            <!-- Nombre -->
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">
                Nombre del lugar <span class="text-red-500">*</span>
              </label>
              <input
                v-model="form.name"
                type="text"
                required
                placeholder="Ej: Plaza Principal, Central de Autobuses, El Mercado"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-yellow-400"
              />
            </div>

            <!-- Dirección -->
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">
                Dirección o referencia <span class="text-gray-400 font-normal">(opcional)</span>
              </label>
              <input
                v-model="form.address"
                type="text"
                placeholder="Ej: Blvd. Torres Landa esq. Av. Irrigación"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-yellow-400"
              />
            </div>

            <!-- Mapa -->
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">
                Ubicación en el mapa <span class="text-red-500">*</span>
              </label>
              <p class="text-xs text-gray-400 mb-2">Haz clic en el mapa para fijar la ubicación</p>
              <div
                id="poi-picker-map"
                class="w-full rounded-lg border border-gray-300 overflow-hidden"
                style="height: 260px;"
              ></div>
            </div>

            <!-- Lat / Lng manuales -->
            <div class="grid grid-cols-2 gap-3">
              <div>
                <label class="block text-xs font-medium text-gray-500 mb-1">Latitud</label>
                <input
                  v-model.number="form.lat"
                  type="number"
                  step="0.0000001"
                  required
                  placeholder="20.5236"
                  @change="moveMarkerFromInputs"
                  class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm font-mono focus:outline-none focus:ring-2 focus:ring-yellow-400"
                />
              </div>
              <div>
                <label class="block text-xs font-medium text-gray-500 mb-1">Longitud</label>
                <input
                  v-model.number="form.lng"
                  type="number"
                  step="0.0000001"
                  required
                  placeholder="-100.8147"
                  @change="moveMarkerFromInputs"
                  class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm font-mono focus:outline-none focus:ring-2 focus:ring-yellow-400"
                />
              </div>
            </div>

            <p v-if="saveError" class="text-red-600 text-sm">{{ saveError }}</p>

            <div class="flex gap-3 pt-2">
              <button
                type="submit"
                :disabled="saving"
                class="flex-1 py-2.5 bg-yellow-500 hover:bg-yellow-600 text-gray-900 font-semibold rounded-lg transition disabled:opacity-50 text-sm"
              >
                {{ saving ? 'Guardando...' : '✓ Guardar Lugar' }}
              </button>
              <button
                type="button"
                @click="closeModal"
                class="px-5 py-2.5 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition text-sm"
              >
                Cancelar
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>

    <!-- Confirm delete -->
    <div
      v-if="deleteTarget"
      class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
    >
      <div class="bg-white rounded-2xl shadow-2xl w-full max-w-sm p-6 text-center">
        <p class="text-4xl mb-3">🗑️</p>
        <h3 class="font-bold text-gray-900 mb-1">¿Eliminar lugar?</h3>
        <p class="text-sm text-gray-500 mb-6">
          Se eliminará <strong>{{ deleteTarget.name }}</strong> de la lista de lugares locales.
        </p>
        <div class="flex gap-3">
          <button
            @click="doDelete"
            :disabled="deleting"
            class="flex-1 py-2 bg-red-600 hover:bg-red-700 text-white font-semibold rounded-lg transition disabled:opacity-50 text-sm"
          >
            {{ deleting ? 'Eliminando...' : 'Eliminar' }}
          </button>
          <button
            @click="deleteTarget = null"
            class="flex-1 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition text-sm"
          >
            Cancelar
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import 'leaflet/dist/leaflet.css'
import { ref, computed, nextTick, onUnmounted } from 'vue'

const API = '/api/v1/locations'

const pois         = ref([])
const search       = ref('')
const loading      = ref(true)
const showModal    = ref(false)
const saving       = ref(false)
const saveError    = ref('')
const deleteTarget = ref(null)
const deleting     = ref(false)

const form = ref({ name: '', address: '', lat: null, lng: null })

let pickerMap    = null
let pickerMarker = null

const filtered = computed(() => {
  const q = search.value.toLowerCase()
  return q ? pois.value.filter(p => p.name.toLowerCase().includes(q)) : pois.value
})

async function loadPois() {
  loading.value = true
  try {
    const res  = await fetch(`${API}/pois`)
    const data = await res.json()
    pois.value = data.pois || []
  } catch (e) {
    console.error('[LocalPois] load error:', e)
  } finally {
    loading.value = false
  }
}

const CITY_CENTER = [20.5236, -100.8147]

async function openAdd() {
  form.value  = { name: '', address: '', lat: null, lng: null }
  saveError.value = ''
  showModal.value = true
  await nextTick()
  initPickerMap()
}

function initPickerMap() {
  const el = document.getElementById('poi-picker-map')
  if (!el || pickerMap) return

  import('leaflet').then(L => {
    const Lm = L.default || L

    pickerMap = Lm.map(el, { zoomControl: true, attributionControl: false })
      .setView(CITY_CENTER, 13)

    Lm.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19 }).addTo(pickerMap)

    const pinIcon = Lm.divIcon({
      html: '<span style="font-size:32px;line-height:1">📍</span>',
      iconSize: [32, 32], iconAnchor: [16, 32], className: '',
    })

    pickerMap.on('click', e => {
      const { lat, lng } = e.latlng
      form.value.lat = parseFloat(lat.toFixed(7))
      form.value.lng = parseFloat(lng.toFixed(7))
      if (pickerMarker) {
        pickerMarker.setLatLng(e.latlng)
      } else {
        pickerMarker = Lm.marker(e.latlng, { icon: pinIcon }).addTo(pickerMap)
      }
    })
  })
}

function moveMarkerFromInputs() {
  if (!pickerMap || !form.value.lat || !form.value.lng) return
  const pos = [form.value.lat, form.value.lng]
  import('leaflet').then(L => {
    const Lm = L.default || L
    if (pickerMarker) {
      pickerMarker.setLatLng(pos)
    } else {
      const pinIcon = Lm.divIcon({
        html: '<span style="font-size:32px;line-height:1">📍</span>',
        iconSize: [32, 32], iconAnchor: [16, 32], className: '',
      })
      pickerMarker = Lm.marker(pos, { icon: pinIcon }).addTo(pickerMap)
    }
    pickerMap.setView(pos, pickerMap.getZoom())
  })
}

function closeModal() {
  showModal.value = false
  if (pickerMap) { pickerMap.remove(); pickerMap = null; pickerMarker = null }
}

async function savePoi() {
  if (!form.value.lat || !form.value.lng) {
    saveError.value = 'Selecciona la ubicación en el mapa'
    return
  }
  saving.value   = true
  saveError.value = ''
  try {
    const res = await fetch(`${API}/pois`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name:     form.value.name.trim(),
        address:  form.value.address.trim() || null,
        lat:      form.value.lat,
        lng:      form.value.lng,
        added_by: 'admin',
      }),
    })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    closeModal()
    await loadPois()
  } catch (e) {
    saveError.value = `Error al guardar: ${e.message}`
  } finally {
    saving.value = false
  }
}

function confirmDelete(poi) {
  deleteTarget.value = poi
}

async function doDelete() {
  if (!deleteTarget.value) return
  deleting.value = true
  try {
    const res = await fetch(`${API}/pois/${deleteTarget.value.db_id}`, { method: 'DELETE' })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    deleteTarget.value = null
    await loadPois()
  } catch (e) {
    console.error('[LocalPois] delete error:', e)
  } finally {
    deleting.value = false
  }
}

onUnmounted(() => {
  if (pickerMap) { pickerMap.remove(); pickerMap = null }
})

loadPois()
</script>
