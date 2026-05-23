<template>
  <div class="container mx-auto px-4 py-8 max-w-6xl">
    <h1 class="text-3xl font-bold text-center mb-8">Programa de Lealtad</h1>

    <!-- Loading State -->
    <div v-if="loyaltyStore.loading" class="text-center py-12">
      <div class="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mb-4"></div>
      <p class="text-gray-600">Cargando información...</p>
    </div>

    <div v-else class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <!-- Left Column: Points and Level -->
      <div class="lg:col-span-1 space-y-6">
        <!-- Points Card -->
        <div class="card bg-gradient-to-br from-primary-500 to-primary-700 text-white">
          <div class="text-center py-6">
            <p class="text-sm opacity-90 mb-2">Tus Puntos</p>
            <p class="text-5xl font-bold mb-4">{{ loyaltyStore.points }}</p>
            <div class="w-16 h-1 bg-white opacity-50 mx-auto mb-4"></div>
            <p class="text-lg font-medium">Nivel {{ loyaltyStore.level }}</p>
          </div>
        </div>

        <!-- Level Progress -->
        <div class="card">
          <h3 class="font-bold mb-4">Progreso al Siguiente Nivel</h3>

          <div v-if="loyaltyStore.nextLevelPoints" class="space-y-3">
            <!-- Progress Bar -->
            <div class="relative h-8 bg-gray-200 rounded-full overflow-hidden">
              <div
                :style="{ width: `${loyaltyStore.progressToNextLevel}%` }"
                class="absolute inset-y-0 left-0 bg-gradient-to-r from-primary-500 to-primary-600 transition-all duration-500"
              ></div>
              <p class="absolute inset-0 flex items-center justify-center text-sm font-medium">
                {{ Math.round(loyaltyStore.progressToNextLevel) }}%
              </p>
            </div>

            <p class="text-sm text-gray-600">
              Faltan <strong>{{ loyaltyStore.nextLevelPoints - loyaltyStore.points }}</strong> puntos
              para alcanzar el siguiente nivel
            </p>
          </div>

          <div v-else class="text-center py-4">
            <svg class="w-12 h-12 text-yellow-400 mx-auto mb-2" fill="currentColor" viewBox="0 0 20 20">
              <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"></path>
            </svg>
            <p class="font-medium text-gray-900">¡Nivel Máximo Alcanzado!</p>
            <p class="text-sm text-gray-600 mt-1">Eres un cliente VIP</p>
          </div>
        </div>

        <!-- Levels Info -->
        <div class="card">
          <h3 class="font-bold mb-4">Niveles de Lealtad</h3>
          <div class="space-y-2">
            <div :class="['flex items-center justify-between p-2 rounded', loyaltyStore.level === 'Bronze' ? 'bg-orange-100' : '']">
              <span class="text-sm">🥉 Bronze</span>
              <span class="text-xs text-gray-600">0 pts</span>
            </div>
            <div :class="['flex items-center justify-between p-2 rounded', loyaltyStore.level === 'Silver' ? 'bg-gray-200' : '']">
              <span class="text-sm">🥈 Silver</span>
              <span class="text-xs text-gray-600">500 pts</span>
            </div>
            <div :class="['flex items-center justify-between p-2 rounded', loyaltyStore.level === 'Gold' ? 'bg-yellow-100' : '']">
              <span class="text-sm">🥇 Gold</span>
              <span class="text-xs text-gray-600">1,500 pts</span>
            </div>
            <div :class="['flex items-center justify-between p-2 rounded', loyaltyStore.level === 'Platinum' ? 'bg-purple-100' : '']">
              <span class="text-sm">💎 Platinum</span>
              <span class="text-xs text-gray-600">3,000 pts</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Right Column: Rewards and History -->
      <div class="lg:col-span-2 space-y-6">
        <!-- Available Rewards -->
        <div class="card">
          <h2 class="text-xl font-bold mb-4">Recompensas Disponibles</h2>

          <div v-if="loyaltyStore.availableRewards.length === 0" class="text-center py-8">
            <svg class="w-12 h-12 text-gray-300 mx-auto mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v13m0-13V6a2 2 0 112 2h-2zm0 0V5.5A2.5 2.5 0 109.5 8H12zm-7 4h14M5 12a2 2 0 110-4h14a2 2 0 110 4M5 12v7a2 2 0 002 2h10a2 2 0 002-2v-7" />
            </svg>
            <p class="text-gray-500">No tienes suficientes puntos para canjear recompensas</p>
            <p class="text-sm text-gray-400 mt-1">¡Sigue comprando para ganar más puntos!</p>
          </div>

          <div v-else class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div
              v-for="reward in loyaltyStore.availableRewards"
              :key="reward.id"
              class="border-2 border-primary-200 rounded-lg p-4 hover:border-primary-400 transition"
            >
              <div class="flex items-start justify-between mb-3">
                <div class="flex-1">
                  <h3 class="font-bold">{{ reward.name }}</h3>
                  <p class="text-sm text-gray-600 mt-1">{{ reward.description }}</p>
                </div>
                <div class="text-right ml-3">
                  <p class="font-bold text-primary-600">{{ reward.points_required }}</p>
                  <p class="text-xs text-gray-500">puntos</p>
                </div>
              </div>

              <button
                @click="handleRedeem(reward)"
                class="btn-primary w-full text-sm"
              >
                Canjear
              </button>
            </div>
          </div>
        </div>

        <!-- All Rewards (Locked) -->
        <div class="card">
          <h2 class="text-xl font-bold mb-4">Todas las Recompensas</h2>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div
              v-for="reward in loyaltyStore.rewards"
              :key="reward.id"
              :class="[
                'border-2 rounded-lg p-4',
                reward.points_required <= loyaltyStore.points
                  ? 'border-primary-200 hover:border-primary-400'
                  : 'border-gray-200 opacity-60'
              ]"
            >
              <div class="flex items-start justify-between mb-2">
                <div class="flex-1">
                  <h3 class="font-bold">{{ reward.name }}</h3>
                  <p class="text-sm text-gray-600 mt-1">{{ reward.description }}</p>
                </div>
                <div class="text-right ml-3">
                  <p :class="[
                    'font-bold',
                    reward.points_required <= loyaltyStore.points ? 'text-primary-600' : 'text-gray-400'
                  ]">
                    {{ reward.points_required }}
                  </p>
                  <p class="text-xs text-gray-500">puntos</p>
                </div>
              </div>

              <div v-if="reward.points_required > loyaltyStore.points" class="mt-2">
                <p class="text-xs text-gray-500">
                  Faltan {{ reward.points_required - loyaltyStore.points }} puntos
                </p>
              </div>
            </div>
          </div>
        </div>

        <!-- Points History -->
        <div class="card">
          <h2 class="text-xl font-bold mb-4">Historial de Puntos</h2>

          <div v-if="loyaltyStore.history.length === 0" class="text-center py-8">
            <p class="text-gray-500">No hay transacciones todavía</p>
          </div>

          <div v-else class="space-y-3">
            <div
              v-for="(transaction, index) in loyaltyStore.history"
              :key="index"
              class="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
            >
              <div class="flex items-center space-x-3">
                <div :class="[
                  'w-10 h-10 rounded-full flex items-center justify-center',
                  transaction.points > 0 ? 'bg-green-100' : 'bg-red-100'
                ]">
                  <svg v-if="transaction.points > 0" class="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                  </svg>
                  <svg v-else class="w-6 h-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 12H4" />
                  </svg>
                </div>
                <div>
                  <p class="font-medium text-sm">{{ transaction.description }}</p>
                  <p class="text-xs text-gray-500">{{ formatDate(transaction.date) }}</p>
                </div>
              </div>
              <p :class="[
                'font-bold',
                transaction.points > 0 ? 'text-green-600' : 'text-red-600'
              ]">
                {{ transaction.points > 0 ? '+' : '' }}{{ transaction.points }}
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useLoyaltyStore } from '@/stores/loyalty'

const loyaltyStore = useLoyaltyStore()

function formatDate(dateString) {
  const date = new Date(dateString)
  return date.toLocaleDateString('es-MX', {
    day: '2-digit',
    month: 'short',
    year: 'numeric'
  })
}

async function handleRedeem(reward) {
  if (!confirm(`¿Canjear ${reward.points_required} puntos por ${reward.name}?`)) return

  const result = await loyaltyStore.redeemReward(reward.id)

  if (result.success) {
    alert('¡Recompensa canjeada exitosamente!')
  } else {
    alert(result.error || 'Error al canjear la recompensa')
  }
}

onMounted(() => {
  loyaltyStore.loadLoyaltyData()
  loyaltyStore.loadRewards()
})
</script>
