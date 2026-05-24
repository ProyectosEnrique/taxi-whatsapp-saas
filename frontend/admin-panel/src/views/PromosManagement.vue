<template>
  <div class="p-8">
    <!-- Header -->
    <div class="flex justify-between items-start mb-8">
      <div>
        <h1 class="text-3xl font-bold text-gray-900">Códigos de Promoción</h1>
        <p class="text-gray-600 mt-1">Crea y administra descuentos para tus clientes</p>
      </div>
      <button @click="openCreate" class="flex items-center px-5 py-2.5 bg-yellow-500 hover:bg-yellow-400 text-gray-900 font-semibold rounded-lg transition-colors">
        <span class="text-lg mr-2">+</span> Nuevo código
      </button>
    </div>

    <!-- Toast -->
    <Transition name="fade">
      <div
        v-if="toast"
        :class="['fixed top-6 right-6 z-50 px-5 py-3 rounded-lg shadow-lg text-white text-sm font-semibold flex items-center gap-2',
                 toast.type === 'success' ? 'bg-green-600' : 'bg-red-600']"
      >
        <span>{{ toast.type === 'success' ? '✓' : '✗' }}</span>{{ toast.message }}
      </div>
    </Transition>

    <!-- Stats -->
    <div class="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
      <div class="bg-white rounded-xl shadow-sm p-5 border border-gray-100">
        <p class="text-sm text-gray-500">Total códigos</p>
        <p class="text-3xl font-bold text-gray-900 mt-1">{{ promos.length }}</p>
      </div>
      <div class="bg-white rounded-xl shadow-sm p-5 border border-gray-100">
        <p class="text-sm text-gray-500">Activos</p>
        <p class="text-3xl font-bold text-green-600 mt-1">{{ promos.filter(p => p.is_active).length }}</p>
      </div>
      <div class="bg-white rounded-xl shadow-sm p-5 border border-gray-100">
        <p class="text-sm text-gray-500">Usos totales</p>
        <p class="text-3xl font-bold text-blue-600 mt-1">{{ totalUses }}</p>
      </div>
      <div class="bg-white rounded-xl shadow-sm p-5 border border-gray-100">
        <p class="text-sm text-gray-500">Expirados</p>
        <p class="text-3xl font-bold text-orange-500 mt-1">{{ expiredCount }}</p>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="flex items-center justify-center py-20 text-gray-400">
      <svg class="w-7 h-7 animate-spin mr-3" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/>
      </svg>
      Cargando códigos...
    </div>

    <!-- Empty -->
    <div v-else-if="promos.length === 0" class="bg-white rounded-xl shadow-sm p-16 text-center">
      <div class="text-6xl mb-4">🏷️</div>
      <p class="text-gray-500 text-lg mb-4">Aún no hay códigos de promoción</p>
      <button @click="openCreate" class="px-6 py-2.5 bg-yellow-500 hover:bg-yellow-400 text-gray-900 font-semibold rounded-lg">
        Crear el primero
      </button>
    </div>

    <!-- Table -->
    <div v-else class="bg-white rounded-xl shadow-sm overflow-hidden border border-gray-100">
      <table class="w-full">
        <thead class="bg-gray-50 border-b border-gray-200">
          <tr>
            <th class="text-left px-6 py-3.5 text-xs font-semibold text-gray-500 uppercase tracking-wider">Código</th>
            <th class="text-left px-6 py-3.5 text-xs font-semibold text-gray-500 uppercase tracking-wider">Descuento</th>
            <th class="text-left px-6 py-3.5 text-xs font-semibold text-gray-500 uppercase tracking-wider">Usos</th>
            <th class="text-left px-6 py-3.5 text-xs font-semibold text-gray-500 uppercase tracking-wider">Vencimiento</th>
            <th class="text-left px-6 py-3.5 text-xs font-semibold text-gray-500 uppercase tracking-wider">Estado</th>
            <th class="px-6 py-3.5"></th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-100">
          <tr v-for="promo in promos" :key="promo.id" class="hover:bg-gray-50 transition-colors">
            <!-- Código -->
            <td class="px-6 py-4">
              <div class="flex items-center gap-2">
                <code class="bg-gray-100 text-gray-800 px-2.5 py-1 rounded-md text-sm font-mono font-bold tracking-wide">
                  {{ promo.code }}
                </code>
                <button
                  @click="copyCode(promo.code)"
                  class="p-1 text-gray-400 hover:text-gray-600 transition-colors"
                  title="Copiar"
                >📋</button>
              </div>
              <p v-if="promo.description" class="text-xs text-gray-500 mt-1 ml-1">{{ promo.description }}</p>
            </td>

            <!-- Descuento -->
            <td class="px-6 py-4">
              <span class="text-2xl font-bold text-green-600">{{ pct(promo.discount_pct) }}%</span>
              <span class="text-xs text-gray-400 ml-1">descuento</span>
            </td>

            <!-- Usos -->
            <td class="px-6 py-4">
              <div class="flex items-center gap-2">
                <span class="font-semibold text-gray-900">{{ promo.used_count }}</span>
                <span class="text-gray-400">/</span>
                <span class="text-gray-500">{{ promo.max_uses === 0 ? '∞' : promo.max_uses }}</span>
              </div>
              <div v-if="promo.max_uses > 0" class="mt-1.5 w-24 bg-gray-200 rounded-full h-1.5">
                <div
                  class="h-1.5 rounded-full transition-all"
                  :class="usagePct(promo) >= 90 ? 'bg-red-500' : 'bg-green-500'"
                  :style="{ width: Math.min(usagePct(promo), 100) + '%' }"
                ></div>
              </div>
            </td>

            <!-- Vencimiento -->
            <td class="px-6 py-4 text-sm">
              <span v-if="!promo.expires_at" class="text-gray-400 italic">Sin vencimiento</span>
              <span v-else-if="isExpired(promo)" class="text-red-500 font-medium">
                ⚠ Expiró {{ formatDate(promo.expires_at) }}
              </span>
              <span v-else class="text-gray-600">
                {{ formatDate(promo.expires_at) }}
              </span>
            </td>

            <!-- Estado -->
            <td class="px-6 py-4">
              <button
                @click="toggleActive(promo)"
                :class="[
                  'px-3 py-1 rounded-full text-xs font-semibold transition-colors',
                  promo.is_active
                    ? 'bg-green-100 text-green-700 hover:bg-green-200'
                    : 'bg-gray-100 text-gray-500 hover:bg-gray-200'
                ]"
              >
                {{ promo.is_active ? '● Activo' : '○ Inactivo' }}
              </button>
            </td>

            <!-- Acciones -->
            <td class="px-6 py-4">
              <div class="flex items-center gap-1 justify-end">
                <button
                  @click="openEdit(promo)"
                  class="p-2 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                  title="Editar"
                >✏️</button>
                <button
                  @click="confirmDelete(promo)"
                  class="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                  title="Eliminar"
                >🗑️</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Modal Crear / Editar -->
    <Transition name="modal">
      <div v-if="showModal" class="fixed inset-0 z-40 flex items-center justify-center p-4 bg-black bg-opacity-50" @click.self="closeModal">
        <div class="bg-white rounded-2xl shadow-2xl w-full max-w-md">
          <div class="px-6 py-5 border-b border-gray-100 flex justify-between items-center">
            <h2 class="text-xl font-bold text-gray-900">{{ isEditing ? 'Editar código' : 'Nuevo código' }}</h2>
            <button @click="closeModal" class="text-gray-400 hover:text-gray-600 text-2xl leading-none">&times;</button>
          </div>

          <form @submit.prevent="savePromo" class="p-6 space-y-5">
            <!-- Código -->
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1.5">Código <span class="text-red-500">*</span></label>
              <input
                v-model="form.code"
                type="text"
                placeholder="Ej: VERANO25"
                :disabled="isEditing"
                class="w-full px-3.5 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-yellow-400 focus:border-transparent uppercase disabled:bg-gray-100 disabled:text-gray-400"
                @input="form.code = form.code.toUpperCase()"
                required
              />
            </div>

            <!-- Descuento -->
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1.5">
                Descuento: <strong class="text-green-600">{{ pct(form.discount_pct / 100) }}%</strong>
              </label>
              <div class="flex items-center gap-3">
                <input
                  v-model.number="form.discount_pct"
                  type="range" min="5" max="50" step="5"
                  class="flex-1 accent-yellow-500"
                />
                <div class="relative w-20">
                  <input
                    v-model.number="form.discount_pct"
                    type="number" min="1" max="100" step="1"
                    class="w-full pl-2 pr-6 py-2 border border-gray-300 rounded-lg text-center focus:ring-2 focus:ring-yellow-400 focus:border-transparent"
                  />
                  <span class="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 text-sm">%</span>
                </div>
              </div>
            </div>

            <!-- Descripción -->
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1.5">Descripción</label>
              <input
                v-model="form.description"
                type="text"
                placeholder="Ej: Descuento de bienvenida"
                class="w-full px-3.5 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-yellow-400 focus:border-transparent"
              />
            </div>

            <!-- Máx. usos y Activo -->
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1.5">Máx. usos</label>
                <input
                  v-model.number="form.max_uses"
                  type="number" min="0"
                  placeholder="0 = ilimitado"
                  class="w-full px-3.5 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-yellow-400 focus:border-transparent"
                />
                <p class="text-xs text-gray-400 mt-1">0 = ilimitado</p>
              </div>
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1.5">Estado</label>
                <label class="flex items-center gap-2 mt-3 cursor-pointer">
                  <div
                    @click="form.is_active = !form.is_active"
                    :class="['relative w-11 h-6 rounded-full transition-colors cursor-pointer', form.is_active ? 'bg-green-500' : 'bg-gray-300']"
                  >
                    <div :class="['absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full shadow transition-transform', form.is_active ? 'translate-x-5' : '']"></div>
                  </div>
                  <span class="text-sm text-gray-700">{{ form.is_active ? 'Activo' : 'Inactivo' }}</span>
                </label>
              </div>
            </div>

            <!-- Vencimiento -->
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1.5">Fecha de vencimiento</label>
              <input
                v-model="form.expires_at"
                type="datetime-local"
                class="w-full px-3.5 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-yellow-400 focus:border-transparent"
              />
              <p class="text-xs text-gray-400 mt-1">Dejar vacío para que no expire</p>
            </div>

            <!-- Acciones -->
            <div class="flex gap-3 pt-2">
              <button type="button" @click="closeModal" class="flex-1 px-4 py-2.5 border border-gray-300 text-gray-700 font-medium rounded-lg hover:bg-gray-50 transition-colors">
                Cancelar
              </button>
              <button
                type="submit"
                :disabled="saving"
                class="flex-1 px-4 py-2.5 bg-yellow-500 hover:bg-yellow-400 disabled:opacity-50 text-gray-900 font-semibold rounded-lg transition-colors flex items-center justify-center gap-2"
              >
                <svg v-if="saving" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/>
                </svg>
                {{ saving ? 'Guardando...' : isEditing ? 'Guardar cambios' : 'Crear código' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </Transition>

    <!-- Modal Confirmar Borrado -->
    <Transition name="modal">
      <div v-if="promoToDelete" class="fixed inset-0 z-40 flex items-center justify-center p-4 bg-black bg-opacity-50" @click.self="promoToDelete = null">
        <div class="bg-white rounded-2xl shadow-2xl w-full max-w-sm p-6 text-center">
          <div class="text-5xl mb-4">🗑️</div>
          <h3 class="text-xl font-bold text-gray-900 mb-2">¿Eliminar código?</h3>
          <p class="text-gray-600 mb-1">
            Se eliminará el código <code class="font-mono font-bold text-gray-800 bg-gray-100 px-1.5 py-0.5 rounded">{{ promoToDelete.code }}</code>
          </p>
          <p class="text-sm text-gray-400 mb-6">Esta acción no se puede deshacer</p>
          <div class="flex gap-3">
            <button @click="promoToDelete = null" class="flex-1 px-4 py-2.5 border border-gray-300 text-gray-700 font-medium rounded-lg hover:bg-gray-50">
              Cancelar
            </button>
            <button @click="deletePromo" :disabled="deleting" class="flex-1 px-4 py-2.5 bg-red-600 hover:bg-red-700 disabled:opacity-50 text-white font-semibold rounded-lg flex items-center justify-center gap-2">
              <svg v-if="deleting" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/>
              </svg>
              {{ deleting ? 'Eliminando...' : 'Sí, eliminar' }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'

const API = '/api/v1/admin'

const promos      = ref([])
const loading     = ref(false)
const saving      = ref(false)
const deleting    = ref(false)
const showModal   = ref(false)
const isEditing   = ref(false)
const promoToDelete = ref(null)
const toast       = ref(null)
let _toastTimer   = null

const emptyForm = () => ({
  code:         '',
  discount_pct: 10,
  description:  '',
  max_uses:     0,
  is_active:    true,
  expires_at:   '',
})

const form = ref(emptyForm())

// ── Computed ──────────────────────────────────────────────────────────────────

const totalUses = computed(() => promos.value.reduce((s, p) => s + (p.used_count || 0), 0))

const expiredCount = computed(() =>
  promos.value.filter(p => p.expires_at && new Date(p.expires_at) < new Date()).length
)

// ── Helpers ───────────────────────────────────────────────────────────────────

function pct(val) { return Math.round(val * 100) }

function usagePct(promo) {
  if (!promo.max_uses) return 0
  return Math.round((promo.used_count / promo.max_uses) * 100)
}

function isExpired(promo) {
  return promo.expires_at && new Date(promo.expires_at) < new Date()
}

function formatDate(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleDateString('es-MX', { day: '2-digit', month: 'short', year: 'numeric' })
}

function showToast(type, message) {
  if (_toastTimer) clearTimeout(_toastTimer)
  toast.value = { type, message }
  _toastTimer = setTimeout(() => { toast.value = null }, 3500)
}

function copyCode(code) {
  navigator.clipboard.writeText(code).then(() => showToast('success', `Código "${code}" copiado`))
}

// ── API ───────────────────────────────────────────────────────────────────────

async function load() {
  loading.value = true
  try {
    const res = await fetch(`${API}/promos`)
    if (!res.ok) throw new Error()
    const data = await res.json()
    promos.value = data.promos || []
  } catch {
    showToast('error', 'No se pudieron cargar los códigos')
  } finally {
    loading.value = false
  }
}

function openCreate() {
  isEditing.value = false
  form.value = emptyForm()
  showModal.value = true
}

function openEdit(promo) {
  isEditing.value = true
  form.value = {
    code:         promo.code,
    discount_pct: pct(promo.discount_pct),
    description:  promo.description || '',
    max_uses:     promo.max_uses,
    is_active:    promo.is_active,
    expires_at:   promo.expires_at
      ? new Date(promo.expires_at).toISOString().slice(0, 16)
      : '',
  }
  showModal.value = true
}

function closeModal() {
  showModal.value = false
}

async function savePromo() {
  saving.value = true
  try {
    const payload = {
      ...form.value,
      code:         form.value.code.trim().toUpperCase(),
      discount_pct: form.value.discount_pct / 100,
      expires_at:   form.value.expires_at || null,
    }

    let res
    if (isEditing.value) {
      res = await fetch(`${API}/promos/${payload.code}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
    } else {
      res = await fetch(`${API}/promos`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
    }

    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || `HTTP ${res.status}`)
    }

    showToast('success', isEditing.value ? 'Código actualizado' : 'Código creado correctamente')
    closeModal()
    await load()
  } catch (e) {
    showToast('error', 'Error al guardar: ' + e.message)
  } finally {
    saving.value = false
  }
}

function confirmDelete(promo) {
  promoToDelete.value = promo
}

async function deletePromo() {
  if (!promoToDelete.value) return
  deleting.value = true
  try {
    const res = await fetch(`${API}/promos/${promoToDelete.value.code}`, { method: 'DELETE' })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    showToast('success', `Código "${promoToDelete.value.code}" eliminado`)
    promoToDelete.value = null
    await load()
  } catch (e) {
    showToast('error', 'Error al eliminar: ' + e.message)
  } finally {
    deleting.value = false
  }
}

async function toggleActive(promo) {
  try {
    const res = await fetch(`${API}/promos/${promo.code}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ is_active: !promo.is_active }),
    })
    if (!res.ok) throw new Error()
    promo.is_active = !promo.is_active
    showToast('success', promo.is_active ? 'Código activado' : 'Código desactivado')
  } catch {
    showToast('error', 'Error al cambiar estado')
  }
}

onMounted(load)
</script>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.3s; }
.fade-enter-from, .fade-leave-to       { opacity: 0; }

.modal-enter-active, .modal-leave-active { transition: all 0.25s ease; }
.modal-enter-from, .modal-leave-to       { opacity: 0; transform: scale(0.95); }
</style>
