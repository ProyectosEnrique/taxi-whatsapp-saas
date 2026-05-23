import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { schedulesApi } from '../services/api'
import { useAuthStore } from './authStore'

export const useScheduleStore = defineStore('schedule', () => {
  // State
  const schedules = ref([])
  const shiftTemplates = ref({})
  const loading = ref(false)
  const error = ref(null)

  // Getters
  const schedulesByDay = computed(() => {
    const byDay = {}
    for (let i = 0; i < 7; i++) {
      byDay[i] = schedules.value.filter(s => s.day_of_week === i && s.is_active)
    }
    return byDay
  })

  const hasScheduleForDay = computed(() => (dayOfWeek) => {
    return schedulesByDay.value[dayOfWeek]?.length > 0
  })

  const nextShift = computed(() => {
    const now = new Date()
    const currentDay = (now.getDay() + 6) % 7 // Convertir domingo=0 a domingo=6
    const currentTime = now.getHours() * 60 + now.getMinutes()

    // Buscar próximo turno hoy
    const todaySchedules = schedulesByDay.value[currentDay] || []
    for (const schedule of todaySchedules) {
      const [startHour, startMin] = schedule.start_time.split(':').map(Number)
      const startTimeMinutes = startHour * 60 + startMin

      if (startTimeMinutes > currentTime) {
        return {
          ...schedule,
          isToday: true,
          dayLabel: 'Hoy'
        }
      }
    }

    // Buscar en días siguientes
    for (let i = 1; i <= 7; i++) {
      const checkDay = (currentDay + i) % 7
      const daySchedules = schedulesByDay.value[checkDay] || []

      if (daySchedules.length > 0) {
        const dayLabels = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
        return {
          ...daySchedules[0],
          isToday: false,
          dayLabel: dayLabels[checkDay]
        }
      }
    }

    return null
  })

  const activeSchedulesCount = computed(() => {
    return schedules.value.filter(s => s.is_active).length
  })

  const hasSchedules = computed(() => {
    return schedules.value.length > 0
  })

  // Actions
  const fetchSchedules = async () => {
    loading.value = true
    error.value = null

    try {
      const authStore = useAuthStore()
      const driverId = authStore.user?.driver_id
      const tenantId = authStore.user?.tenant_id

      if (!driverId || !tenantId) {
        throw new Error('Driver ID o Tenant ID no disponibles')
      }

      const response = await schedulesApi.getAll(driverId, tenantId)

      if (response.success) {
        schedules.value = response.schedules
      } else {
        throw new Error(response.error || 'Error al obtener horarios')
      }

      return { success: true }
    } catch (err) {
      error.value = err.response?.data?.error || err.message || 'Error al cargar horarios'
      return { success: false, error: error.value }
    } finally {
      loading.value = false
    }
  }

  const createSchedule = async (scheduleData) => {
    loading.value = true
    error.value = null

    try {
      const authStore = useAuthStore()
      const driverId = authStore.user?.driver_id
      const tenantId = authStore.user?.tenant_id

      if (!driverId || !tenantId) {
        throw new Error('Driver ID o Tenant ID no disponibles')
      }

      const response = await schedulesApi.create({
        driver_id: driverId,
        tenant_id: tenantId,
        ...scheduleData
      })

      if (response.success) {
        schedules.value.push(response.schedule)
      } else {
        throw new Error(response.error || 'Error al crear horario')
      }

      return { success: true, schedule: response.schedule }
    } catch (err) {
      error.value = err.response?.data?.error || err.message || 'Error al crear horario'
      return { success: false, error: error.value }
    } finally {
      loading.value = false
    }
  }

  const createBulkSchedules = async (schedulesData) => {
    loading.value = true
    error.value = null

    try {
      const authStore = useAuthStore()
      const driverId = authStore.user?.driver_id
      const tenantId = authStore.user?.tenant_id

      if (!driverId || !tenantId) {
        throw new Error('Driver ID o Tenant ID no disponibles')
      }

      const response = await schedulesApi.createBulk({
        driver_id: driverId,
        tenant_id: tenantId,
        schedules: schedulesData
      })

      if (response.success) {
        schedules.value = [...schedules.value, ...response.schedules]
      } else {
        throw new Error(response.error || 'Error al crear horarios')
      }

      return { success: true, schedules: response.schedules }
    } catch (err) {
      error.value = err.response?.data?.error || err.message || 'Error al crear horarios'
      return { success: false, error: error.value }
    } finally {
      loading.value = false
    }
  }

  const updateSchedule = async (scheduleId, updates) => {
    loading.value = true
    error.value = null

    try {
      const authStore = useAuthStore()
      const tenantId = authStore.user?.tenant_id

      if (!tenantId) {
        throw new Error('Tenant ID no disponible')
      }

      const response = await schedulesApi.update(scheduleId, {
        tenant_id: tenantId,
        ...updates
      })

      if (response.success) {
        const index = schedules.value.findIndex(s => s.schedule_id === scheduleId)
        if (index !== -1) {
          schedules.value[index] = response.schedule
        }
      } else {
        throw new Error(response.error || 'Error al actualizar horario')
      }

      return { success: true, schedule: response.schedule }
    } catch (err) {
      error.value = err.response?.data?.error || err.message || 'Error al actualizar horario'
      return { success: false, error: error.value }
    } finally {
      loading.value = false
    }
  }

  const deleteSchedule = async (scheduleId) => {
    loading.value = true
    error.value = null

    try {
      const authStore = useAuthStore()
      const tenantId = authStore.user?.tenant_id

      if (!tenantId) {
        throw new Error('Tenant ID no disponible')
      }

      const response = await schedulesApi.delete(scheduleId, tenantId)

      if (response.success) {
        schedules.value = schedules.value.filter(s => s.schedule_id !== scheduleId)
      } else {
        throw new Error(response.error || 'Error al eliminar horario')
      }

      return { success: true }
    } catch (err) {
      error.value = err.response?.data?.error || err.message || 'Error al eliminar horario'
      return { success: false, error: error.value }
    } finally {
      loading.value = false
    }
  }

  const fetchTemplates = async () => {
    try {
      const response = await schedulesApi.getTemplates()

      if (response.success) {
        shiftTemplates.value = response.templates
      }

      return { success: true }
    } catch (err) {
      console.error('Error al cargar plantillas:', err)
      return { success: false, error: err.message }
    }
  }

  const clearSchedules = () => {
    schedules.value = []
    shiftTemplates.value = {}
    error.value = null
  }

  // Aplicar plantilla a múltiples días
  const applyTemplateToMultipleDays = async (templateKey, selectedDays) => {
    const template = shiftTemplates.value[templateKey]

    if (!template) {
      return { success: false, error: 'Plantilla no encontrada' }
    }

    const schedulesData = selectedDays.map(day => ({
      day_of_week: day,
      shift_type: template.shift_type,
      start_time: template.start_time,
      end_time: template.end_time,
      break_start: template.break_start || null,
      break_end: template.break_end || null,
      is_active: true,
      is_recurring: true
    }))

    return await createBulkSchedules(schedulesData)
  }

  return {
    // State
    schedules,
    shiftTemplates,
    loading,
    error,
    // Getters
    schedulesByDay,
    hasScheduleForDay,
    nextShift,
    activeSchedulesCount,
    hasSchedules,
    // Actions
    fetchSchedules,
    createSchedule,
    createBulkSchedules,
    updateSchedule,
    deleteSchedule,
    fetchTemplates,
    clearSchedules,
    applyTemplateToMultipleDays
  }
})
