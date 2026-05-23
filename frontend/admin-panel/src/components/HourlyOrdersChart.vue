<template>
  <div class="chart-container">
    <h3 class="chart-title">{{ title }}</h3>
    <div class="chart">
      <div
        v-for="(item, index) in chartData"
        :key="index"
        class="bar-wrapper"
        @mouseenter="hoveredIndex = index"
        @mouseleave="hoveredIndex = null">
        <div class="bar-container">
          <div
            class="bar"
            :style="{
              height: `${getBarHeight(item.value)}%`,
              background: hoveredIndex === index ? '#2980b9' : '#3498db'
            }">
            <div v-if="hoveredIndex === index" class="tooltip">
              {{ item.value }}
            </div>
          </div>
        </div>
        <div class="label">{{ item.label }}</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  title: {
    type: String,
    default: 'Gráfica'
  },
  data: {
    type: Array,
    required: true,
    // Expected format: [{ label: 'Label', value: 10 }, ...]
  }
})

const hoveredIndex = ref(null)

const chartData = computed(() => props.data)

const maxValue = computed(() => {
  const values = chartData.value.map(d => d.value)
  return Math.max(...values, 1) // At least 1 to avoid division by zero
})

function getBarHeight(value) {
  if (maxValue.value === 0) return 0
  return (value / maxValue.value) * 100
}
</script>

<style scoped>
.chart-container {
  background: white;
  padding: 1.5rem;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.chart-title {
  margin: 0 0 1.5rem 0;
  color: #2c3e50;
  font-size: 1.2rem;
}

.chart {
  display: flex;
  align-items: flex-end;
  gap: 0.5rem;
  height: 200px;
  padding: 1rem 0;
  border-bottom: 2px solid #e0e0e0;
  overflow-x: auto;
}

.bar-wrapper {
  flex: 1;
  min-width: 30px;
  display: flex;
  flex-direction: column;
  align-items: center;
  height: 100%;
}

.bar-container {
  flex: 1;
  width: 100%;
  display: flex;
  align-items: flex-end;
  justify-content: center;
  position: relative;
}

.bar {
  width: 100%;
  max-width: 40px;
  background: #3498db;
  border-radius: 4px 4px 0 0;
  transition: all 0.3s;
  cursor: pointer;
  position: relative;
  min-height: 2px;
}

.bar:hover {
  opacity: 0.8;
}

.tooltip {
  position: absolute;
  top: -30px;
  left: 50%;
  transform: translateX(-50%);
  background: #2c3e50;
  color: white;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-size: 0.8rem;
  white-space: nowrap;
  z-index: 10;
}

.label {
  font-size: 0.7rem;
  color: #7f8c8d;
  text-align: center;
  margin-top: 0.5rem;
  white-space: nowrap;
  transform: rotate(-45deg);
  transform-origin: center;
}

@media (max-width: 768px) {
  .chart {
    height: 150px;
  }

  .label {
    font-size: 0.6rem;
  }
}
</style>
