<template>
  <div class="min-h-screen bg-gray-50">
    <header class="bg-white shadow-sm sticky top-0 z-10">
      <div class="max-w-7xl mx-auto px-4 py-4">
        <div class="flex items-center space-x-4">
          <button @click="goBack" class="p-2 hover:bg-gray-100 rounded-lg">
            <span class="text-2xl">←</span>
          </button>
          <div class="flex-1">
            <h1 class="text-xl font-bold text-gray-900">Métodos de Pago</h1>
            <p class="text-sm text-gray-500">Administra tus formas de pago</p>
          </div>
        </div>
      </div>
    </header>

    <main class="max-w-7xl mx-auto px-4 py-6">
      <div class="space-y-4">
        <div class="bg-white rounded-lg shadow p-6">
          <div class="flex items-center justify-between p-4 bg-green-50 border border-green-200 rounded-lg">
            <div class="flex items-center space-x-3">
              <span class="text-3xl">💵</span>
              <div>
                <p class="font-semibold text-gray-900">Efectivo</p>
                <p class="text-sm text-gray-600">Paga directamente al conductor</p>
              </div>
            </div>
            <span class="px-3 py-1 bg-green-500 text-white rounded-full text-sm font-medium">Predeterminado</span>
          </div>
        </div>

        <div class="bg-white rounded-lg shadow p-6">
          <div class="flex items-center justify-between mb-4">
            <h3 class="text-lg font-semibold text-gray-900">Tarjetas de Crédito/Débito</h3>
            <button @click="showAddCard = true" class="text-blue-600 hover:underline font-medium">+ Agregar</button>
          </div>

          <div v-if="paymentMethods.length === 0" class="text-center py-8 text-gray-500">
            <div class="text-5xl mb-3">💳</div>
            <p>No hay tarjetas guardadas</p>
          </div>

          <div v-else class="space-y-3">
            <div
              v-for="method in paymentMethods"
              :key="method.id"
              class="flex items-center justify-between p-4 border border-gray-200 rounded-lg hover:border-taxi-yellow"
            >
              <div class="flex items-center space-x-3">
                <span class="text-3xl">{{ getCardIcon(method.card_type) }}</span>
                <div>
                  <p class="font-semibold text-gray-900">{{ method.card_type }} •••• {{ method.last_four }}</p>
                  <p class="text-sm text-gray-600">Expira {{ method.exp_month}}/{{ method.exp_year }}</p>
                </div>
              </div>
              <div class="flex items-center space-x-2">
                <button @click="setDefault(method.id)" v-if="!method.is_default" class="text-sm text-blue-600 hover:underline">
                  Predeterminado
                </button>
                <span v-else class="text-sm text-green-600 font-medium">✓ Predeterminada</span>
                <button @click="deleteMethod(method.id)" class="text-red-600 hover:text-red-700 p-2">🗑️</button>
              </div>
            </div>
          </div>
        </div>

        <div class="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div class="flex items-start">
            <span class="text-2xl mr-3">ℹ️</span>
            <div>
              <p class="font-medium text-blue-900 mb-1">Pagos seguros</p>
              <p class="text-sm text-blue-800">Tus datos de pago están encriptados y protegidos.</p>
            </div>
          </div>
        </div>
      </div>
    </main>

    <div v-if="showAddCard" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4" @click.self="showAddCard = false">
      <div class="bg-white rounded-lg shadow-2xl max-w-md w-full p-6">
        <h3 class="text-xl font-bold text-gray-900 mb-4">Agregar Tarjeta</h3>

        <form @submit.prevent="addCard">
          <div class="mb-4">
            <label class="block text-sm font-medium text-gray-700 mb-2">Número de tarjeta</label>
            <input
              v-model="newCard.number"
              type="text"
              placeholder="1234 5678 9012 3456"
              maxlength="19"
              required
              class="w-full px-4 py-3 border border-gray-300 rounded-lg"
            />
          </div>

          <div class="grid grid-cols-2 gap-4 mb-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-2">Fecha de expiración</label>
              <input
                v-model="newCard.expiry"
                type="text"
                placeholder="MM/AA"
                maxlength="5"
                required
                class="w-full px-4 py-3 border border-gray-300 rounded-lg"
              />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-2">CVV</label>
              <input
                v-model="newCard.cvv"
                type="text"
                placeholder="123"
                maxlength="4"
                required
                class="w-full px-4 py-3 border border-gray-300 rounded-lg"
              />
            </div>
          </div>

          <div class="mb-4">
            <label class="block text-sm font-medium text-gray-700 mb-2">Nombre en la tarjeta</label>
            <input
              v-model="newCard.name"
              type="text"
              placeholder="Juan Pérez"
              required
              class="w-full px-4 py-3 border border-gray-300 rounded-lg"
            />
          </div>

          <div class="flex space-x-3">
            <button
              type="button"
              @click="showAddCard = false"
              class="flex-1 bg-gray-200 hover:bg-gray-300 text-gray-700 font-semibold py-3 rounded-lg"
            >
              Cancelar
            </button>
            <button
              type="submit"
              class="flex-1 bg-taxi-blue text-white font-semibold py-3 rounded-lg hover:bg-blue-600"
            >
              Agregar
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

const paymentMethods = ref([])
const showAddCard = ref(false)

const newCard = reactive({
  number: '',
  expiry: '',
  cvv: '',
  name: ''
})

const getCardIcon = (type) => {
  const icons = {
    visa: '💳',
    mastercard: '💳',
    amex: '💳'
  }
  return icons[type?.toLowerCase()] || '💳'
}

const addCard = () => {
  alert('Tarjeta agregada (integración con Stripe pendiente)')
  showAddCard.value = false
  Object.keys(newCard).forEach(key => newCard[key] = '')
}

const setDefault = (id) => {
  alert(`Tarjeta ${id} establecida como predeterminada`)
}

const deleteMethod = (id) => {
  if (confirm('¿Eliminar esta tarjeta?')) {
    alert(`Tarjeta ${id} eliminada`)
  }
}

const goBack = () => {
  router.push('/profile')
}

onMounted(() => {
  // Load payment methods from API
})
</script>
