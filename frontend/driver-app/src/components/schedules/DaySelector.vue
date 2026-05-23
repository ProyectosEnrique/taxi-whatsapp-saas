<template>
  <div class="day-selector">
    <h3 class="text-lg font-semibold mb-3 text-gray-800">Días de la semana</h3>
    <div class="grid grid-cols-2 gap-2">
      <label
        v-for="(day, index) in days"
        :key="index"
        class="flex items-center p-3 border rounded-lg cursor-pointer transition-all"
        :class="selectedDays.includes(index) ? 'bg-yellow-50 border-yellow-500' : 'bg-white border-gray-300 hover:border-gray-400'"
      >
        <input
          type="checkbox"
          :value="index"
          v-model="localSelectedDays"
          @change="emitChange"
          class="w-5 h-5 text-yellow-500 focus:ring-yellow-500"
        />
        <span class="ml-3 text-sm font-medium text-gray-700">{{ day }}</span>
      </label>
    </div>

    <!-- Select all / Deselect all -->
    <div class="flex gap-2 mt-3">
      <button
        @click="selectAll"
        type="button"
        class="flex-1 px-3 py-2 text-sm font-medium text-yellow-700 bg-yellow-50 border border-yellow-300 rounded-lg hover:bg-yellow-100 transition"
      >
        Seleccionar todos
      </button>
      <button
        @click="deselectAll"
        type="button"
        class="flex-1 px-3 py-2 text-sm font-medium text-gray-700 bg-gray-50 border border-gray-300 rounded-lg hover:bg-gray-100 transition"
      >
        Limpiar
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  modelValue: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['update:modelValue'])

const days = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
const localSelectedDays = ref([...props.modelValue])

watch(() => props.modelValue, (newValue) => {
  localSelectedDays.value = [...newValue]
})

const emitChange = () => {
  emit('update:modelValue', localSelectedDays.value)
}

const selectAll = () => {
  localSelectedDays.value = [0, 1, 2, 3, 4, 5, 6]
  emitChange()
}

const deselectAll = () => {
  localSelectedDays.value = []
  emitChange()
}

const selectedDays = localSelectedDays
</script>

<style scoped>
.day-selector {
  @apply p-4 bg-gray-50 rounded-lg;
}
</style>
