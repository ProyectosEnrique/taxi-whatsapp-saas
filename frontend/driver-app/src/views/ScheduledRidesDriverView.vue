<template>
  <div class="min-h-screen bg-gray-50">
    <header class="bg-white shadow-sm sticky top-0 z-10">
      <div class="max-w-7xl mx-auto px-4 py-4 flex items-center space-x-3">
        <button @click="router.push('/dashboard')" class="p-2 hover:bg-gray-100 rounded-lg text-xl">←</button>
        <div>
          <h1 class="text-xl font-bold text-gray-900">Agenda de Viajes</h1>
          <p class="text-sm text-gray-500">Reservas programadas</p>
        </div>
      </div>
    </header>

    <main class="max-w-7xl mx-auto px-4 py-6 space-y-6">

      <!-- Mis reservas -->
      <section>
        <h2 class="text-base font-semibold text-gray-700 mb-3 flex items-center space-x-2">
          <span>📌 Mis reservas</span>
          <span v-if="myRides.length" class="bg-yellow-400 text-white text-xs font-bold px-2 py-0.5 rounded-full">
            {{ myRides.length }}
          </span>
        </h2>

        <div v-if="loading" class="text-center text-gray-400 py-6">Cargando...</div>

        <div v-else-if="myRides.length === 0" class="bg-white rounded-lg p-6 text-center text-gray-400 shadow">
          <p>No tienes viajes reservados.</p>
          <p class="text-sm mt-1">Reserva alguno de los disponibles abajo.</p>
        </div>

        <div v-else class="space-y-3">
          <div
            v-for="ride in myRides"
            :key="ride.ride_id"
            class="bg-white rounded-lg shadow p-5 border-l-4 border-yellow-400"
          >
            <RideCard :ride="ride">
              <template #action>
                <button
                  @click="confirmRelease(ride)"
                  class="w-full mt-3 border-2 border-red-200 hover:border-red-400 text-red-500 hover:text-red-600 font-semibold py-2 rounded-lg text-sm transition"
                >
                  🔓 Liberar viaje
                </button>
              </template>
            </RideCard>
          </div>
        </div>
      </section>

      <!-- Pool disponible -->
      <section>
        <h2 class="text-base font-semibold text-gray-700 mb-3 flex items-center space-x-2">
          <span>🔍 Disponibles para reservar</span>
          <span v-if="poolRides.length" class="bg-blue-500 text-white text-xs font-bold px-2 py-0.5 rounded-full">
            {{ poolRides.length }}
          </span>
        </h2>

        <div v-if="poolRides.length === 0" class="bg-white rounded-lg p-6 text-center text-gray-400 shadow">
          <p>No hay viajes programados disponibles.</p>
        </div>

        <div v-else class="space-y-3">
          <div
            v-for="ride in poolRides"
            :key="ride.ride_id"
            class="bg-white rounded-lg shadow p-5 border-l-4 border-blue-300"
          >
            <RideCard :ride="ride">
              <template #action>
                <button
                  @click="handleClaim(ride.ride_id)"
                  :disabled="claiming === ride.ride_id"
                  class="w-full mt-3 bg-yellow-400 hover:bg-yellow-500 text-white font-bold py-2 rounded-lg text-sm disabled:opacity-50 transition"
                >
                  {{ claiming === ride.ride_id ? 'Reservando...' : '📅 Reservar este viaje' }}
                </button>
              </template>
            </RideCard>
          </div>
        </div>
      </section>
    </main>

    <!-- Modal confirmar liberación -->
    <div
      v-if="rideToRelease"
      class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
      @click.self="rideToRelease = null"
    >
      <div class="bg-white rounded-2xl shadow-2xl max-w-sm w-full p-6">
        <h3 class="text-lg font-bold text-gray-900 mb-2">¿Liberar este viaje?</h3>
        <p class="text-gray-500 text-sm mb-1">
          {{ formatDate(rideToRelease.scheduled_at) }}
        </p>
        <p class="text-gray-700 text-sm mb-4">
          {{ rideToRelease.origin.address }} → {{ rideToRelease.destination.address }}
        </p>
        <p class="text-xs text-gray-400 mb-5">
          El cliente recibirá una notificación para que decida si busca otro conductor o cancela.
        </p>
        <div class="flex space-x-3">
          <button
            @click="rideToRelease = null"
            class="flex-1 bg-gray-100 hover:bg-gray-200 text-gray-700 font-semibold py-3 rounded-lg"
          >
            Conservar
          </button>
          <button
            @click="handleRelease"
            :disabled="releasing"
            class="flex-1 bg-red-500 hover:bg-red-600 text-white font-semibold py-3 rounded-lg disabled:opacity-50"
          >
            {{ releasing ? 'Liberando...' : 'Sí, liberar' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, defineComponent, h } from 'vue'
import { useRouter } from 'vue-router'
import { useRideStore } from '../stores/rideStore'

const router = useRouter()
const rideStore = useRideStore()

const loading = ref(false)
const claiming = ref(null)
const releasing = ref(false)
const rideToRelease = ref(null)

const myRides   = computed(() => rideStore.myScheduledRides)
const poolRides = computed(() => rideStore.poolScheduledRides)

const formatDate = (iso) => {
  if (!iso) return ''
  return new Date(iso).toLocaleString('es-MX', { dateStyle: 'medium', timeStyle: 'short' })
}

const timeUntil = (iso) => {
  if (!iso) return ''
  const diff = new Date(iso) - Date.now()
  if (diff <= 0) return 'Próximamente'
  const hours = Math.floor(diff / 3600000)
  const days = Math.floor(hours / 24)
  if (days > 0) return `En ${days} día${days > 1 ? 's' : ''}`
  if (hours > 0) return `En ${hours}h`
  return `En ${Math.floor(diff / 60000)} min`
}

const confirmRelease = (ride) => { rideToRelease.value = ride }

const handleClaim = async (rideId) => {
  claiming.value = rideId
  const result = await rideStore.claimScheduledRide(rideId)
  claiming.value = null
  if (!result.success) alert(result.error || 'No se pudo reservar')
}

const handleRelease = async () => {
  if (!rideToRelease.value) return
  releasing.value = true
  const result = await rideStore.releaseScheduledRide(rideToRelease.value.ride_id)
  releasing.value = false
  rideToRelease.value = null
  if (!result.success) alert(result.error || 'No se pudo liberar')
}

// Componente inline para las tarjetas de viaje
const RideCard = defineComponent({
  props: ['ride'],
  setup(props, { slots }) {
    return () => h('div', [
      h('div', { class: 'flex items-center justify-between mb-2' }, [
        h('div', [
          h('p', { class: 'font-bold text-gray-900' }, formatDate(props.ride.scheduled_at)),
          h('p', { class: 'text-sm text-green-600 font-medium' }, timeUntil(props.ride.scheduled_at)),
        ]),
        h('span', { class: 'text-lg font-bold text-green-600' }, `$${props.ride.total_fare}`),
      ]),
      h('p', { class: 'text-sm font-medium text-gray-700 mb-2' }, `👤 ${props.ride.customer?.name || 'Pasajero'}`),
      h('div', { class: 'space-y-1 text-sm text-gray-600 mb-2' }, [
        h('p', `📍 ${props.ride.origin?.address}`),
        h('p', `🏁 ${props.ride.destination?.address}`),
      ]),
      h('div', { class: 'flex space-x-3 text-xs text-gray-500' }, [
        h('span', `📏 ${props.ride.distance_km} km`),
        h('span', `⏱️ ${props.ride.duration_minutes} min`),
        h('span', props.ride.payment_method === 'cash' ? '💵 Efectivo' : '💳 Tarjeta'),
      ]),
      slots.action?.(),
    ])
  }
})

onMounted(async () => {
  loading.value = true
  await rideStore.fetchScheduledRides()
  loading.value = false
})
</script>
