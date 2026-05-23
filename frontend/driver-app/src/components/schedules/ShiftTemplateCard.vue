<template>
  <div
    @click="selectTemplate"
    class="shift-template-card p-4 border-2 rounded-lg cursor-pointer transition-all"
    :class="isSelected ? 'border-yellow-500 bg-yellow-50' : 'border-gray-300 bg-white hover:border-gray-400 hover:shadow-md'"
  >
    <!-- Header -->
    <div class="flex items-center justify-between mb-3">
      <div class="flex items-center">
        <div
          class="w-10 h-10 rounded-full flex items-center justify-center text-xl"
          :class="iconBgColor"
        >
          {{ icon }}
        </div>
        <div class="ml-3">
          <h4 class="text-base font-semibold text-gray-800">{{ template.name }}</h4>
          <p class="text-xs text-gray-500">{{ template.shift_type }}</p>
        </div>
      </div>

      <!-- Check icon when selected -->
      <div v-if="isSelected" class="text-yellow-500">
        <svg class="w-6 h-6" fill="currentColor" viewBox="0 0 20 20">
          <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
        </svg>
      </div>
    </div>

    <!-- Time -->
    <div class="flex items-center text-sm text-gray-600 mb-2">
      <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      <span class="font-medium">{{ template.start_time }} - {{ template.end_time }}</span>
    </div>

    <!-- Break time -->
    <div v-if="template.break_start && template.break_end" class="flex items-center text-sm text-gray-600 mb-2">
      <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" />
      </svg>
      <span>Descanso: {{ template.break_start }} - {{ template.break_end }}</span>
    </div>

    <!-- Description -->
    <p class="text-sm text-gray-500 mt-3">{{ template.description }}</p>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  template: {
    type: Object,
    required: true
  },
  selected: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['select'])

const isSelected = computed(() => props.selected)

const icon = computed(() => {
  const icons = {
    morning: '🌅',
    afternoon: '☀️',
    night: '🌙',
    flexible: '⏰'
  }
  return icons[props.template.shift_type] || '📅'
})

const iconBgColor = computed(() => {
  const colors = {
    morning: 'bg-orange-100',
    afternoon: 'bg-yellow-100',
    night: 'bg-indigo-100',
    flexible: 'bg-green-100'
  }
  return colors[props.template.shift_type] || 'bg-gray-100'
})

const selectTemplate = () => {
  emit('select', props.template)
}
</script>

<style scoped>
.shift-template-card {
  @apply transition-transform;
}

.shift-template-card:hover {
  @apply transform scale-105;
}
</style>
