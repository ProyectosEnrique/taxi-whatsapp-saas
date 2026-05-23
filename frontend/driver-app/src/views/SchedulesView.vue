<template>
  <div class="min-h-screen bg-gray-50">
    <!-- Header -->
    <header class="bg-white shadow-sm sticky top-0 z-10">
      <div class="max-w-7xl mx-auto px-4 py-4">
        <div class="flex items-center space-x-4">
          <button
            @click="goBack"
            class="p-2 hover:bg-gray-100 rounded-lg"
          >
            <span class="text-2xl">←</span>
          </button>
          <div class="flex-1">
            <h1 class="text-xl font-bold text-gray-900">Mis Horarios</h1>
            <p class="text-sm text-gray-500">Configura tus turnos de trabajo</p>
          </div>
        </div>
      </div>
    </header>

    <!-- Loading -->
    <div v-if="loading" class="flex items-center justify-center py-12">
      <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-yellow-500"></div>
    </div>

    <!-- Content -->
    <main v-else class="max-w-7xl mx-auto px-4 py-6">
      <!-- Tabs -->
      <div class="bg-white rounded-lg shadow mb-6">
        <div class="flex border-b">
          <button
            @click="activeTab = 'weekly'"
            class="flex-1 px-6 py-4 font-medium text-center transition"
            :class="activeTab === 'weekly' ? 'text-yellow-600 border-b-2 border-yellow-600 bg-yellow-50' : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'"
          >
            📅 Vista Semanal
          </button>
          <button
            @click="activeTab = 'configure'"
            class="flex-1 px-6 py-4 font-medium text-center transition"
            :class="activeTab === 'configure' ? 'text-yellow-600 border-b-2 border-yellow-600 bg-yellow-50' : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'"
          >
            ⚙️ Configurar
          </button>
        </div>
      </div>

      <!-- Weekly View -->
      <div v-if="activeTab === 'weekly'" class="space-y-4">
        <!-- Stats Card -->
        <div class="bg-white rounded-lg shadow p-6">
          <div class="grid grid-cols-3 gap-4">
            <div class="text-center">
              <p class="text-sm text-gray-500 mb-1">Días configurados</p>
              <p class="text-3xl font-bold text-yellow-600">{{ activeDaysCount }}</p>
            </div>
            <div class="text-center">
              <p class="text-sm text-gray-500 mb-1">Horarios activos</p>
              <p class="text-3xl font-bold text-green-600">{{ activeSchedulesCount }}</p>
            </div>
            <div class="text-center">
              <p class="text-sm text-gray-500 mb-1">Próximo turno</p>
              <p class="text-lg font-bold text-blue-600">{{ nextShiftLabel }}</p>
            </div>
          </div>
        </div>

        <!-- Weekly Calendar -->
        <div class="bg-white rounded-lg shadow p-6">
          <h2 class="text-lg font-semibold mb-4 text-gray-800">Calendario Semanal</h2>

          <!-- Empty state -->
          <div v-if="!hasSchedules" class="text-center py-12">
            <svg class="w-20 h-20 mx-auto text-gray-300 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
            <p class="text-gray-500 text-lg mb-2">No tienes horarios configurados</p>
            <p class="text-gray-400 mb-6">Configura tus turnos de trabajo en la pestaña "Configurar"</p>
            <button
              @click="activeTab = 'configure'"
              class="px-6 py-3 bg-yellow-500 text-white font-medium rounded-lg hover:bg-yellow-600 transition"
            >
              Configurar ahora
            </button>
          </div>

          <!-- Calendar Grid -->
          <div v-else class="space-y-2">
            <div
              v-for="day in 7"
              :key="day"
              class="border border-gray-200 rounded-lg p-4 hover:shadow-md transition"
              :class="hasScheduleForDay(day - 1) ? 'bg-white' : 'bg-gray-50'"
            >
              <div class="flex items-center justify-between mb-2">
                <h3 class="font-semibold text-gray-800">{{ getDayLabel(day - 1) }}</h3>
                <span
                  v-if="hasScheduleForDay(day - 1)"
                  class="px-2 py-1 text-xs font-semibold bg-green-100 text-green-700 rounded-full"
                >
                  {{ getDaySchedules(day - 1).length }} turno(s)
                </span>
                <span v-else class="text-sm text-gray-400">Sin horario</span>
              </div>

              <div v-if="hasScheduleForDay(day - 1)" class="space-y-2">
                <div
                  v-for="schedule in getDaySchedules(day - 1)"
                  :key="schedule.schedule_id"
                  class="p-3 bg-yellow-50 border border-yellow-200 rounded-lg"
                >
                  <div class="flex items-center justify-between">
                    <div>
                      <p class="font-medium text-gray-800">
                        {{ schedule.start_time }} - {{ schedule.end_time }}
                      </p>
                      <p class="text-sm text-gray-600">
                        {{ getShiftLabel(schedule.shift_type) }}
                      </p>
                      <p v-if="schedule.break_start && schedule.break_end" class="text-xs text-gray-500 mt-1">
                        Descanso: {{ schedule.break_start }} - {{ schedule.break_end }}
                      </p>
                    </div>
                    <span
                      class="px-2 py-1 text-xs font-semibold rounded-full"
                      :class="getShiftBadgeClass(schedule.shift_type)"
                    >
                      {{ getShiftIcon(schedule.shift_type) }}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Configure View -->
      <div v-if="activeTab === 'configure'" class="space-y-6">
        <!-- Existing Schedules -->
        <div class="bg-white rounded-lg shadow p-6">
          <ScheduleList
            :schedules="schedules"
            @edit="editSchedule"
            @delete="deleteSchedule"
          />
        </div>

        <!-- Shift Templates -->
        <div class="bg-white rounded-lg shadow p-6">
          <h2 class="text-lg font-semibold mb-4 text-gray-800">Plantillas de Turno</h2>
          <p class="text-sm text-gray-600 mb-4">Selecciona una plantilla predefinida para configurar rápidamente tus horarios</p>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <ShiftTemplateCard
              v-for="(template, key) in shiftTemplates"
              :key="key"
              :template="template"
              :selected="selectedTemplate === key"
              @select="selectTemplate(key)"
            />
          </div>
        </div>

        <!-- Day Selector -->
        <div v-if="selectedTemplate" class="bg-white rounded-lg shadow p-6">
          <DaySelector v-model="selectedDays" />
        </div>

        <!-- Time Customization -->
        <div v-if="selectedTemplate" class="bg-white rounded-lg shadow p-6">
          <TimeRangePicker
            label="Horario de Trabajo"
            v-model:start-time="customStartTime"
            v-model:end-time="customEndTime"
          />
        </div>

        <!-- Break Configuration -->
        <div v-if="selectedTemplate" class="bg-white rounded-lg shadow p-6">
          <div class="flex items-center justify-between mb-4">
            <h3 class="text-lg font-semibold text-gray-800">Configurar Descanso</h3>
            <label class="flex items-center cursor-pointer">
              <input
                type="checkbox"
                v-model="hasBreak"
                class="w-5 h-5 text-yellow-500 focus:ring-yellow-500"
              />
              <span class="ml-2 text-sm font-medium text-gray-700">Incluir descanso</span>
            </label>
          </div>

          <div v-if="hasBreak">
            <TimeRangePicker
              label="Horario de Descanso"
              v-model:start-time="breakStartTime"
              v-model:end-time="breakEndTime"
            />
          </div>
        </div>

        <!-- Action Buttons -->
        <div v-if="selectedTemplate && selectedDays.length > 0" class="flex gap-4">
          <button
            @click="saveSchedules"
            :disabled="saving"
            class="flex-1 px-6 py-4 bg-yellow-500 text-white font-semibold rounded-lg hover:bg-yellow-600 transition disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
          >
            <span v-if="!saving">💾 Guardar Horarios</span>
            <span v-else class="flex items-center">
              <svg class="animate-spin h-5 w-5 mr-2" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              Guardando...
            </span>
          </button>
          <button
            @click="resetForm"
            class="px-6 py-4 bg-gray-200 text-gray-700 font-semibold rounded-lg hover:bg-gray-300 transition"
          >
            🔄 Limpiar
          </button>
        </div>
      </div>

      <!-- Error Message -->
      <div v-if="error" class="mt-6 p-4 bg-red-50 border border-red-200 rounded-lg">
        <p class="text-red-700">❌ {{ error }}</p>
      </div>

      <!-- Success Message -->
      <div v-if="successMessage" class="mt-6 p-4 bg-green-50 border border-green-200 rounded-lg">
        <p class="text-green-700">✅ {{ successMessage }}</p>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useScheduleStore } from '../stores/scheduleStore'
import DaySelector from '../components/schedules/DaySelector.vue'
import TimeRangePicker from '../components/schedules/TimeRangePicker.vue'
import ShiftTemplateCard from '../components/schedules/ShiftTemplateCard.vue'
import ScheduleList from '../components/schedules/ScheduleList.vue'

const router = useRouter()
const scheduleStore = useScheduleStore()

// State
const activeTab = ref('weekly')
const selectedTemplate = ref(null)
const selectedDays = ref([])
const customStartTime = ref('')
const customEndTime = ref('')
const hasBreak = ref(false)
const breakStartTime = ref('')
const breakEndTime = ref('')
const saving = ref(false)
const error = ref(null)
const successMessage = ref(null)

// Computed
const loading = computed(() => scheduleStore.loading)
const schedules = computed(() => scheduleStore.schedules)
const shiftTemplates = computed(() => scheduleStore.shiftTemplates)
const hasSchedules = computed(() => scheduleStore.hasSchedules)
const activeSchedulesCount = computed(() => scheduleStore.activeSchedulesCount)

const activeDaysCount = computed(() => {
  const daysWithSchedules = new Set()
  schedules.value.forEach(s => {
    if (s.is_active) daysWithSchedules.add(s.day_of_week)
  })
  return daysWithSchedules.size
})

const nextShiftLabel = computed(() => {
  const nextShift = scheduleStore.nextShift
  if (!nextShift) return 'N/A'
  return nextShift.dayLabel
})

const dayLabels = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']

const shiftLabels = {
  morning: 'Matutino',
  afternoon: 'Vespertino',
  night: 'Nocturno',
  flexible: 'Flexible'
}

// Methods
const goBack = () => {
  router.back()
}

const getDayLabel = (dayOfWeek) => {
  return dayLabels[dayOfWeek]
}

const getShiftLabel = (shiftType) => {
  return shiftLabels[shiftType] || shiftType
}

const getShiftIcon = (shiftType) => {
  const icons = {
    morning: '🌅',
    afternoon: '☀️',
    night: '🌙',
    flexible: '⏰'
  }
  return icons[shiftType] || '📅'
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

const hasScheduleForDay = (dayOfWeek) => {
  return scheduleStore.hasScheduleForDay(dayOfWeek)
}

const getDaySchedules = (dayOfWeek) => {
  return scheduleStore.schedulesByDay[dayOfWeek] || []
}

const selectTemplate = (key) => {
  selectedTemplate.value = key
  const template = shiftTemplates.value[key]

  if (template) {
    customStartTime.value = template.start_time
    customEndTime.value = template.end_time

    if (template.break_start && template.break_end) {
      hasBreak.value = true
      breakStartTime.value = template.break_start
      breakEndTime.value = template.break_end
    } else {
      hasBreak.value = false
      breakStartTime.value = ''
      breakEndTime.value = ''
    }
  }
}

const saveSchedules = async () => {
  if (selectedDays.value.length === 0) {
    error.value = 'Debes seleccionar al menos un día'
    return
  }

  if (!customStartTime.value || !customEndTime.value) {
    error.value = 'Debes configurar el horario de trabajo'
    return
  }

  if (hasBreak.value && (!breakStartTime.value || !breakEndTime.value)) {
    error.value = 'Debes configurar el horario de descanso'
    return
  }

  saving.value = true
  error.value = null
  successMessage.value = null

  try {
    const schedulesData = selectedDays.value.map(day => ({
      day_of_week: day,
      shift_type: shiftTemplates.value[selectedTemplate.value].shift_type,
      start_time: customStartTime.value,
      end_time: customEndTime.value,
      break_start: hasBreak.value ? breakStartTime.value : null,
      break_end: hasBreak.value ? breakEndTime.value : null,
      is_active: true,
      is_recurring: true
    }))

    const result = await scheduleStore.createBulkSchedules(schedulesData)

    if (result.success) {
      successMessage.value = `${schedulesData.length} horario(s) creado(s) exitosamente`
      resetForm()
      activeTab.value = 'weekly'

      // Clear success message after 3 seconds
      setTimeout(() => {
        successMessage.value = null
      }, 3000)
    } else {
      error.value = result.error
    }
  } catch (err) {
    error.value = 'Error al guardar horarios'
  } finally {
    saving.value = false
  }
}

const resetForm = () => {
  selectedTemplate.value = null
  selectedDays.value = []
  customStartTime.value = ''
  customEndTime.value = ''
  hasBreak.value = false
  breakStartTime.value = ''
  breakEndTime.value = ''
}

const editSchedule = (schedule) => {
  // TODO: Implement edit functionality
  console.log('Edit schedule:', schedule)
  alert('Funcionalidad de edición en desarrollo')
}

const deleteSchedule = async (schedule) => {
  error.value = null
  successMessage.value = null

  const result = await scheduleStore.deleteSchedule(schedule.schedule_id)

  if (result.success) {
    successMessage.value = 'Horario eliminado exitosamente'
    setTimeout(() => {
      successMessage.value = null
    }, 3000)
  } else {
    error.value = result.error
  }
}

// Lifecycle
onMounted(async () => {
  await scheduleStore.fetchTemplates()
  await scheduleStore.fetchSchedules()
})
</script>

<style scoped>
/* Add any custom styles here if needed */
</style>
