<template>
  <div class="schedule-list">
    <h3 class="text-lg font-semibold mb-4 text-gray-800">Horarios configurados</h3>

    <!-- Empty state -->
    <div v-if="schedules.length === 0" class="text-center py-8">
      <svg class="w-16 h-16 mx-auto text-gray-300 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
      </svg>
      <p class="text-gray-500">No hay horarios configurados</p>
    </div>

    <!-- Schedule items -->
    <div v-else class="space-y-3">
      <div
        v-for="schedule in sortedSchedules"
        :key="schedule.schedule_id"
        class="schedule-item p-4 bg-white border border-gray-200 rounded-lg hover:shadow-md transition-shadow"
      >
        <div class="flex items-start justify-between">
          <!-- Schedule info -->
          <div class="flex-1">
            <div class="flex items-center mb-2">
              <span class="px-2 py-1 text-xs font-semibold rounded-full"
                :class="getDayBadgeClass(schedule.day_of_week)">
                {{ getDayLabel(schedule.day_of_week) }}
              </span>
              <span class="ml-2 px-2 py-1 text-xs font-semibold rounded-full"
                :class="getShiftBadgeClass(schedule.shift_type)">
                {{ getShiftLabel(schedule.shift_type) }}
              </span>
              <span v-if="!schedule.is_active" class="ml-2 px-2 py-1 text-xs font-semibold bg-gray-200 text-gray-600 rounded-full">
                Inactivo
              </span>
            </div>

            <div class="flex items-center text-sm text-gray-700 mb-1">
              <svg class="w-4 h-4 mr-2 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span class="font-medium">{{ schedule.start_time }} - {{ schedule.end_time }}</span>
            </div>

            <div v-if="schedule.break_start && schedule.break_end" class="flex items-center text-sm text-gray-600">
              <svg class="w-4 h-4 mr-2 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" />
              </svg>
              <span>Descanso: {{ schedule.break_start }} - {{ schedule.break_end }}</span>
            </div>
          </div>

          <!-- Actions -->
          <div class="flex items-center gap-2 ml-4">
            <button
              @click="$emit('edit', schedule)"
              class="p-2 text-blue-600 hover:bg-blue-50 rounded-lg transition"
              title="Editar"
            >
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
              </svg>
            </button>
            <button
              @click="confirmDelete(schedule)"
              class="p-2 text-red-600 hover:bg-red-50 rounded-lg transition"
              title="Eliminar"
            >
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  schedules: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['edit', 'delete'])

const dayLabels = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']

const shiftLabels = {
  morning: 'Matutino',
  afternoon: 'Vespertino',
  night: 'Nocturno',
  flexible: 'Flexible'
}

const sortedSchedules = computed(() => {
  return [...props.schedules].sort((a, b) => {
    // Sort by day of week first
    if (a.day_of_week !== b.day_of_week) {
      return a.day_of_week - b.day_of_week
    }
    // Then by start time
    return a.start_time.localeCompare(b.start_time)
  })
})

const getDayLabel = (dayOfWeek) => {
  return dayLabels[dayOfWeek] || 'N/A'
}

const getShiftLabel = (shiftType) => {
  return shiftLabels[shiftType] || shiftType
}

const getDayBadgeClass = (dayOfWeek) => {
  // Weekend days (5=Sábado, 6=Domingo)
  if (dayOfWeek >= 5) {
    return 'bg-purple-100 text-purple-700'
  }
  return 'bg-blue-100 text-blue-700'
}

const getShiftBadgeClass = (shiftType) => {
  const classes = {
    morning: 'bg-orange-100 text-orange-700',
    afternoon: 'bg-yellow-100 text-yellow-700',
    night: 'bg-indigo-100 text-indigo-700',
    flexible: 'bg-green-100 text-green-700'
  }
  return classes[shiftType] || 'bg-gray-100 text-gray-700'
}

const confirmDelete = (schedule) => {
  if (confirm(`¿Eliminar el horario de ${getDayLabel(schedule.day_of_week)}?`)) {
    emit('delete', schedule)
  }
}
</script>

<style scoped>
.schedule-list {
  @apply mb-6;
}

.schedule-item {
  @apply transition-all;
}

.schedule-item:hover {
  @apply transform scale-102;
}
</style>
