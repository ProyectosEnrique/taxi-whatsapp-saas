<template>
  <div class="metrics-card" :class="variant">
    <div class="icon">{{ icon }}</div>
    <div class="content">
      <div class="label">{{ label }}</div>
      <div class="value">{{ formattedValue }}</div>
      <div v-if="trend !== null && trend !== undefined" class="trend" :class="trendClass">
        {{ trend > 0 ? '↑' : trend < 0 ? '↓' : '→' }} {{ Math.abs(trend) }}%
      </div>
      <div v-if="subtitle" class="subtitle">{{ subtitle }}</div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  label: {
    type: String,
    required: true
  },
  value: {
    type: [Number, String],
    required: true
  },
  icon: {
    type: String,
    default: '📊'
  },
  variant: {
    type: String,
    default: 'default', // default, success, warning, danger, info
    validator: (value) => ['default', 'success', 'warning', 'danger', 'info'].includes(value)
  },
  format: {
    type: String,
    default: 'number' // number, currency, percent
  },
  subtitle: {
    type: String,
    default: ''
  },
  trend: {
    type: Number,
    default: null
  }
})

const formattedValue = computed(() => {
  const val = props.value
  switch (props.format) {
    case 'currency':
      return `$${parseFloat(val).toFixed(2)}`
    case 'percent':
      return `${val}%`
    default:
      return val
  }
})

const trendClass = computed(() => {
  if (props.trend > 0) return 'trend-up'
  if (props.trend < 0) return 'trend-down'
  return 'trend-neutral'
})
</script>

<style scoped>
.metrics-card {
  background: white;
  padding: 1.5rem;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  display: flex;
  align-items: center;
  gap: 1rem;
  transition: all 0.3s;
  border-left: 4px solid #95a5a6;
}

.metrics-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.metrics-card.success {
  border-left-color: #27ae60;
  background: linear-gradient(135deg, #ffffff 0%, #eafaf1 100%);
}

.metrics-card.warning {
  border-left-color: #f39c12;
  background: linear-gradient(135deg, #ffffff 0%, #fef5e7 100%);
}

.metrics-card.danger {
  border-left-color: #e74c3c;
  background: linear-gradient(135deg, #ffffff 0%, #fadbd8 100%);
}

.metrics-card.info {
  border-left-color: #3498db;
  background: linear-gradient(135deg, #ffffff 0%, #ebf5fb 100%);
}

.icon {
  font-size: 2.5rem;
  line-height: 1;
}

.content {
  flex: 1;
}

.label {
  font-size: 0.9rem;
  color: #7f8c8d;
  margin-bottom: 0.25rem;
  font-weight: 500;
}

.value {
  font-size: 2rem;
  font-weight: bold;
  color: #2c3e50;
  line-height: 1.2;
}

.trend {
  display: inline-block;
  padding: 0.2rem 0.5rem;
  border-radius: 12px;
  font-size: 0.85rem;
  font-weight: 600;
  margin-top: 0.25rem;
}

.trend-up {
  background: #d4edda;
  color: #155724;
}

.trend-down {
  background: #f8d7da;
  color: #721c24;
}

.trend-neutral {
  background: #e2e3e5;
  color: #383d41;
}

.subtitle {
  font-size: 0.8rem;
  color: #95a5a6;
  margin-top: 0.25rem;
}

@media (max-width: 768px) {
  .metrics-card {
    padding: 1rem;
  }

  .icon {
    font-size: 2rem;
  }

  .value {
    font-size: 1.5rem;
  }
}
</style>
