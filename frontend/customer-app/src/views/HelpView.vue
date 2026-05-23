<template>
  <div class="container mx-auto px-4 py-8 max-w-4xl">
    <div class="text-center mb-8">
      <h1 class="text-3xl font-bold mb-2">Centro de Ayuda</h1>
      <p class="text-gray-600">¿En qué podemos ayudarte?</p>
    </div>

    <!-- Search -->
    <div class="mb-8">
      <div class="relative">
        <input
          v-model="searchQuery"
          type="text"
          placeholder="Buscar en preguntas frecuentes..."
          class="input pl-12"
        />
        <svg
          class="absolute left-4 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
        </svg>
      </div>
    </div>

    <!-- Categories -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-12">
      <button
        @click="selectedCategory = 'pedidos'"
        :class="[
          'card text-center hover:shadow-lg transition-shadow',
          selectedCategory === 'pedidos' ? 'border-2 border-primary-600' : ''
        ]"
      >
        <svg class="w-12 h-12 text-primary-600 mx-auto mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z" />
        </svg>
        <h3 class="font-bold">Pedidos</h3>
      </button>

      <button
        @click="selectedCategory = 'pagos'"
        :class="[
          'card text-center hover:shadow-lg transition-shadow',
          selectedCategory === 'pagos' ? 'border-2 border-primary-600' : ''
        ]"
      >
        <svg class="w-12 h-12 text-primary-600 mx-auto mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" />
        </svg>
        <h3 class="font-bold">Pagos</h3>
      </button>

      <button
        @click="selectedCategory = 'entrega'"
        :class="[
          'card text-center hover:shadow-lg transition-shadow',
          selectedCategory === 'entrega' ? 'border-2 border-primary-600' : ''
        ]"
      >
        <svg class="w-12 h-12 text-primary-600 mx-auto mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path d="M9 17a2 2 0 11-4 0 2 2 0 014 0zM19 17a2 2 0 11-4 0 2 2 0 014 0z" />
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16V6a1 1 0 00-1-1H4a1 1 0 00-1 1v10a1 1 0 001 1h1m8-1a1 1 0 01-1 1H9m4-1V8a1 1 0 011-1h2.586a1 1 0 01.707.293l3.414 3.414a1 1 0 01.293.707V16a1 1 0 01-1 1h-1m-6-1a1 1 0 001 1h1M5 17a2 2 0 104 0m-4 0a2 2 0 114 0m6 0a2 2 0 104 0m-4 0a2 2 0 114 0" />
        </svg>
        <h3 class="font-bold">Entrega</h3>
      </button>
    </div>

    <!-- FAQs -->
    <div class="space-y-3">
      <div
        v-for="(faq, index) in filteredFaqs"
        :key="index"
        class="card"
      >
        <button
          @click="toggleFaq(index)"
          class="w-full flex items-center justify-between text-left"
        >
          <h3 class="font-medium pr-4">{{ faq.question }}</h3>
          <svg
            :class="['w-5 h-5 text-gray-400 transform transition-transform', openFaqs.includes(index) ? 'rotate-180' : '']"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
          </svg>
        </button>

        <div
          v-if="openFaqs.includes(index)"
          class="mt-3 text-gray-600 text-sm"
        >
          {{ faq.answer }}
        </div>
      </div>
    </div>

    <!-- Contact Section -->
    <div class="mt-12 card bg-primary-50 border-primary-200">
      <h2 class="text-xl font-bold mb-4">¿No encuentras lo que buscas?</h2>
      <p class="text-gray-700 mb-6">
        Nuestro equipo de soporte está listo para ayudarte
      </p>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <a
          :href="`tel:${tenantStore.tenant?.phone}`"
          class="flex items-center justify-center space-x-3 bg-white border-2 border-primary-200 rounded-lg p-4 hover:border-primary-400 transition"
        >
          <svg class="w-6 h-6 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
          </svg>
          <div>
            <p class="font-medium">Llamar</p>
            <p class="text-sm text-gray-600">{{ tenantStore.tenant?.phone }}</p>
          </div>
        </a>

        <a
          :href="`mailto:${tenantStore.tenant?.email}`"
          class="flex items-center justify-center space-x-3 bg-white border-2 border-primary-200 rounded-lg p-4 hover:border-primary-400 transition"
        >
          <svg class="w-6 h-6 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
          </svg>
          <div>
            <p class="font-medium">Email</p>
            <p class="text-sm text-gray-600">{{ tenantStore.tenant?.email }}</p>
          </div>
        </a>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useTenantStore } from '@/stores/tenant'

const tenantStore = useTenantStore()

const searchQuery = ref('')
const selectedCategory = ref('pedidos')
const openFaqs = ref([])

const faqs = [
  // Pedidos
  {
    category: 'pedidos',
    question: '¿Cómo hago un pedido?',
    answer: 'Puedes hacer tu pedido navegando por nuestro menú, agregando productos al carrito y finalizando en el checkout. También puedes hacer pedidos por WhatsApp.'
  },
  {
    category: 'pedidos',
    question: '¿Puedo modificar mi pedido después de haberlo hecho?',
    answer: 'Sí, puedes cancelar tu pedido si aún está en estado "Pendiente" o "Preparando". Una vez que esté "En Camino", ya no será posible modificarlo.'
  },
  {
    category: 'pedidos',
    question: '¿Cuál es el tiempo de entrega?',
    answer: 'El tiempo estimado de entrega varía según tu ubicación y la disponibilidad de repartidores. Generalmente es de 30-45 minutos. Puedes ver el tracking en tiempo real de tu pedido.'
  },
  {
    category: 'pedidos',
    question: '¿Hay un monto mínimo de pedido?',
    answer: 'Sí, el monto mínimo varía según tu ubicación. Lo puedes ver en el carrito antes de finalizar tu pedido.'
  },

  // Pagos
  {
    category: 'pagos',
    question: '¿Qué métodos de pago aceptan?',
    answer: 'Aceptamos efectivo, tarjetas de crédito/débito y transferencias bancarias. El pago se realiza al momento de la entrega o en línea según tu preferencia.'
  },
  {
    category: 'pagos',
    question: '¿Puedo pagar con tarjeta al recibir mi pedido?',
    answer: 'Sí, nuestros repartidores cuentan con terminal para pagos con tarjeta.'
  },
  {
    category: 'pagos',
    question: '¿Emiten factura?',
    answer: 'Sí, puedes solicitar factura proporcionando tus datos fiscales al momento de hacer tu pedido o contactando a soporte después.'
  },

  // Entrega
  {
    category: 'entrega',
    question: '¿Hacen envíos a domicilio?',
    answer: 'Sí, hacemos envíos a domicilio en toda el área metropolitana. El costo de envío se calcula automáticamente según tu ubicación.'
  },
  {
    category: 'entrega',
    question: '¿Puedo rastrear mi pedido?',
    answer: 'Sí, una vez confirmado tu pedido, recibirás un enlace para rastrear el estado en tiempo real.'
  },
  {
    category: 'entrega',
    question: '¿Qué hago si mi pedido llega incompleto o con errores?',
    answer: 'Contacta inmediatamente a nuestro soporte. Resolveremos el problema enviando lo faltante o reembolsando el monto correspondiente.'
  }
]

const filteredFaqs = computed(() => {
  let filtered = faqs.filter(faq => faq.category === selectedCategory.value)

  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    filtered = filtered.filter(faq =>
      faq.question.toLowerCase().includes(query) ||
      faq.answer.toLowerCase().includes(query)
    )
  }

  return filtered
})

function toggleFaq(index) {
  const position = openFaqs.value.indexOf(index)
  if (position > -1) {
    openFaqs.value.splice(position, 1)
  } else {
    openFaqs.value.push(index)
  }
}
</script>
