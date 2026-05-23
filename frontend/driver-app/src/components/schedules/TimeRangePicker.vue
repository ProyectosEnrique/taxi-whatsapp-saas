<template>
  <div class="time-range-picker">
    <h3 class="text-lg font-semibold mb-3 text-gray-800">{{ label }}</h3>

    <div class="grid grid-cols-2 gap-4">
      <!-- Start Time -->
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-2">
          Hora de inicio
        </label>
        <input
          type="time"
          v-model="localStartTime"
          @change="emitChange"
          class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-yellow-500 focus:border-transparent"
        />
      </div>

      <!-- End Time -->
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-2">
          Hora de fin
        </label>
        <input
          type="time"
          v-model="localEndTime"
          @change="emitChange"
          class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-yellow-500 focus:border-transparent"
        />
      </div>
    </div>

    <!-- Duration display -->
    <div v-if="duration" class="mt-3 p-2 bg-blue-50 rounded-lg">
      <p class="text-sm text-blue-700">
        <span class="font-medium">Duración:</span> {{ duration }}
      </p>
    </div>

    <!-- Error message -->
    <div v-if="error" class="mt-3 p-2 bg-red-50 rounded-lg">
      <p class="text-sm text-red-700">{{ error }}</p>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, computed } from 'vue'

const props = defineProps({
  label: {
    type: String,
    default: 'Horario'
  },
  startTime: {
    type: String,
    default: ''
  },
  endTime: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['update:startTime', 'update:endTime'])

const localStartTime = ref(props.startTime)
const localEndTime = ref(props.endTime)

watch(() => props.startTime, (newValue) => {
  localStartTime.value = newValue
})

watch(() => props.endTime, (newValue) => {
  localEndTime.value = newValue
})

const emitChange = () => {
  emit('update:startTime', localStartTime.value)
  emit('update:endTime', localEndTime.value)
}

const duration = computed(() => {
  if (!localStartTime.value || !localEndTime.value) return null

  const [startHour, startMin] = localStartTime.value.split(':').map(Number)
  const [endHour, endMin] = localEndTime.value.split(':').map(Number)

  let totalMinutes = (endHour * 60 + endMin) - (startHour * 60 + startMin)

  // Handle overnight shifts
  if (totalMinutes < 0) {
    totalMinutes += 24 * 60
  }

  const hours = Math.floor(totalMinutes / 60)
  const minutes = totalMinutes % 60

  return `${hours}h ${minutes}min`
})

const error = computed(() => {
  if (!localStartTime.value || !localEndTime.value) return null

  const [startHour, startMin] = localStartTime.value.split(':').map(Number)
  const [endHour, endMin] = localEndTime.value.split(':').map(Number)

  const startMinutes = startHour * 60 + startMin
  const endMinutes = endHour * 60 + endMin

  // Allow overnight shifts, so no error in this case
  // Just validate that times are different
  if (startMinutes === endMinutes) {
    return 'La hora de inicio y fin deben ser diferentes'
  }

  return null
})
</script>

<style scoped>
.time-range-picker {
  @apply p-4 bg-gray-50 rounded-lg;
}

input[type="time"] {
  @apply text-base;
}
</style>
