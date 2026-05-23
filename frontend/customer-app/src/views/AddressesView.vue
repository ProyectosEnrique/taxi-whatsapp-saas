<template>
  <div class="container mx-auto px-4 py-8 max-w-4xl">
    <div class="flex items-center justify-between mb-8">
      <h1 class="text-3xl font-bold">Mis Direcciones</h1>
      <button @click="showAddModal = true" class="btn-primary">
        <svg class="w-5 h-5 mr-2 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
        </svg>
        Nueva Dirección
      </button>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="text-center py-12">
      <div class="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mb-4"></div>
      <p class="text-gray-600">Cargando direcciones...</p>
    </div>

    <!-- Empty State -->
    <div v-else-if="addresses.length === 0" class="text-center py-12">
      <svg class="w-16 h-16 text-gray-300 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
      </svg>
      <p class="text-gray-500 mb-4">No tienes direcciones guardadas</p>
      <button @click="showAddModal = true" class="btn-primary">
        Agregar Primera Dirección
      </button>
    </div>

    <!-- Addresses Grid -->
    <div v-else class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <div
        v-for="address in addresses"
        :key="address.id"
        class="card hover:shadow-lg transition-shadow relative"
      >
        <!-- Badge de Default -->
        <div v-if="address.is_default" class="absolute top-4 right-4">
          <span class="badge badge-success">Principal</span>
        </div>

        <!-- Icon -->
        <div class="mb-4">
          <div class="w-12 h-12 bg-primary-100 rounded-full flex items-center justify-center">
            <svg class="w-6 h-6 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
          </div>
        </div>

        <!-- Address Info -->
        <div class="mb-4">
          <p v-if="address.label" class="font-bold mb-2">{{ address.label }}</p>
          <p class="text-gray-700">{{ address.street }}</p>
          <p class="text-gray-600 text-sm">
            {{ address.neighborhood }}, {{ address.city }}
          </p>
          <p class="text-gray-600 text-sm">
            {{ address.state }} {{ address.zipCode }}
          </p>
          <p v-if="address.reference" class="text-gray-500 text-sm mt-2">
            Ref: {{ address.reference }}
          </p>
        </div>

        <!-- Actions -->
        <div class="flex space-x-2">
          <button
            @click="handleEdit(address)"
            class="btn-secondary flex-1 text-sm"
          >
            Editar
          </button>
          <button
            v-if="!address.is_default"
            @click="handleSetDefault(address.id)"
            class="btn-secondary flex-1 text-sm"
          >
            Marcar Principal
          </button>
          <button
            @click="handleDelete(address.id)"
            class="text-red-600 hover:bg-red-50 px-3 rounded transition"
          >
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
          </button>
        </div>
      </div>
    </div>

    <!-- Add/Edit Modal -->
    <div
      v-if="showAddModal || showEditModal"
      class="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4"
      @click.self="closeModals"
    >
      <div class="bg-white rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto p-6">
        <div class="flex items-center justify-between mb-6">
          <h2 class="text-2xl font-bold">
            {{ showEditModal ? 'Editar Dirección' : 'Nueva Dirección' }}
          </h2>
          <button @click="closeModals" class="text-gray-400 hover:text-gray-600">
            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <form @submit.prevent="handleSubmit" class="space-y-4">
          <div>
            <label class="block text-sm font-medium mb-1">Etiqueta (opcional)</label>
            <input
              v-model="addressForm.label"
              type="text"
              class="input"
              placeholder="Casa, Oficina, etc."
            />
          </div>

          <div>
            <label class="block text-sm font-medium mb-1">Calle y Número *</label>
            <input
              v-model="addressForm.street"
              type="text"
              required
              class="input"
              placeholder="Av. Principal 123"
            />
          </div>

          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium mb-1">Colonia *</label>
              <input
                v-model="addressForm.neighborhood"
                type="text"
                required
                class="input"
              />
            </div>
            <div>
              <label class="block text-sm font-medium mb-1">Código Postal *</label>
              <input
                v-model="addressForm.zipCode"
                type="text"
                required
                class="input"
              />
            </div>
          </div>

          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium mb-1">Ciudad *</label>
              <input
                v-model="addressForm.city"
                type="text"
                required
                class="input"
              />
            </div>
            <div>
              <label class="block text-sm font-medium mb-1">Estado *</label>
              <input
                v-model="addressForm.state"
                type="text"
                required
                class="input"
              />
            </div>
          </div>

          <div>
            <label class="block text-sm font-medium mb-1">Referencia (opcional)</label>
            <textarea
              v-model="addressForm.reference"
              class="input"
              rows="2"
              placeholder="Casa blanca, portón negro..."
            ></textarea>
          </div>

          <div class="flex items-center">
            <input
              v-model="addressForm.is_default"
              type="checkbox"
              id="is_default"
              class="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
            />
            <label for="is_default" class="ml-2 text-sm text-gray-700">
              Marcar como dirección principal
            </label>
          </div>

          <div class="flex space-x-3 pt-4">
            <button type="button" @click="closeModals" class="btn-secondary flex-1">
              Cancelar
            </button>
            <button type="submit" :disabled="loading" class="btn-primary flex-1">
              {{ showEditModal ? 'Actualizar' : 'Guardar' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '@/services/api'

const addresses = ref([])
const loading = ref(false)
const showAddModal = ref(false)
const showEditModal = ref(false)
const editingId = ref(null)

const addressForm = ref({
  label: '',
  street: '',
  neighborhood: '',
  zipCode: '',
  city: '',
  state: '',
  reference: '',
  is_default: false
})

async function loadAddresses() {
  try {
    loading.value = true
    addresses.value = await api.getAddresses()
  } catch (error) {
    console.error('Error loading addresses:', error)
  } finally {
    loading.value = false
  }
}

function handleEdit(address) {
  addressForm.value = { ...address }
  editingId.value = address.id
  showEditModal.value = true
}

async function handleSubmit() {
  try {
    loading.value = true

    if (showEditModal.value) {
      await api.updateAddress(editingId.value, addressForm.value)
    } else {
      await api.createAddress(addressForm.value)
    }

    await loadAddresses()
    closeModals()
  } catch (error) {
    console.error('Error saving address:', error)
    alert('Error al guardar la dirección')
  } finally {
    loading.value = false
  }
}

async function handleSetDefault(addressId) {
  try {
    await api.updateAddress(addressId, { is_default: true })
    await loadAddresses()
  } catch (error) {
    console.error('Error setting default:', error)
  }
}

async function handleDelete(addressId) {
  if (!confirm('¿Estás seguro de eliminar esta dirección?')) return

  try {
    await api.deleteAddress(addressId)
    await loadAddresses()
  } catch (error) {
    console.error('Error deleting address:', error)
    alert('Error al eliminar la dirección')
  }
}

function closeModals() {
  showAddModal.value = false
  showEditModal.value = false
  editingId.value = null
  addressForm.value = {
    label: '',
    street: '',
    neighborhood: '',
    zipCode: '',
    city: '',
    state: '',
    reference: '',
    is_default: false
  }
}

onMounted(() => {
  loadAddresses()
})
</script>
