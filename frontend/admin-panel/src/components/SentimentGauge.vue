<template>
  <div class="sentiment-gauge">
    <h3 class="gauge-title">{{ title }}</h3>

    <div class="gauge-container">
      <!-- SVG Gauge -->
      <svg viewBox="0 0 200 120" class="gauge-svg">
        <!-- Background Arc -->
        <path
          d="M 20 100 A 80 80 0 0 1 180 100"
          fill="none"
          stroke="#e0e0e0"
          stroke-width="20"
          stroke-linecap="round"
        />

        <!-- Colored segments -->
        <path
          d="M 20 100 A 80 80 0 0 1 66 35"
          fill="none"
          stroke="#e74c3c"
          stroke-width="20"
          stroke-linecap="round"
          opacity="0.3"
        />
        <path
          d="M 66 35 A 80 80 0 0 1 134 35"
          fill="none"
          stroke="#f39c12"
          stroke-width="20"
          opacity="0.3"
        />
        <path
          d="M 134 35 A 80 80 0 0 1 180 100"
          fill="none"
          stroke="#27ae60"
          stroke-width="20"
          stroke-linecap="round"
          opacity="0.3"
        />

        <!-- Active Arc -->
        <path
          :d="activeArcPath"
          fill="none"
          :stroke="gaugeColor"
          stroke-width="20"
          stroke-linecap="round"
          class="active-arc"
        />

        <!-- Needle -->
        <g :transform="`rotate(${needleRotation}, 100, 100)`">
          <line
            x1="100"
            y1="100"
            x2="100"
            y2="35"
            stroke="#2c3e50"
            stroke-width="3"
            stroke-linecap="round"
          />
          <circle cx="100" cy="100" r="8" fill="#2c3e50" />
        </g>

        <!-- Labels -->
        <text x="20" y="115" font-size="10" fill="#7f8c8d" text-anchor="middle">0%</text>
        <text x="100" y="15" font-size="10" fill="#7f8c8d" text-anchor="middle">50%</text>
        <text x="180" y="115" font-size="10" fill="#7f8c8d" text-anchor="middle">100%</text>
      </svg>

      <!-- Value Display -->
      <div class="gauge-value" :class="valueClass">
        <span class="value-number">{{ value }}</span>
        <span class="value-percent">%</span>
      </div>

      <!-- Emoji Indicator -->
      <div class="emoji-indicator">{{ sentimentEmoji }}</div>
    </div>

    <!-- Description -->
    <div class="gauge-description">
      <span class="description-label">{{ sentimentLabel }}</span>
      <span class="description-detail">{{ description }}</span>
    </div>

    <!-- Mini Stats -->
    <div v-if="showStats" class="gauge-stats">
      <div class="stat-item">
        <span class="stat-value">{{ positiveCount }}</span>
        <span class="stat-label">Positivos</span>
      </div>
      <div class="stat-item">
        <span class="stat-value">{{ neutralCount }}</span>
        <span class="stat-label">Neutros</span>
      </div>
      <div class="stat-item">
        <span class="stat-value">{{ negativeCount }}</span>
        <span class="stat-label">Negativos</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  title: {
    type: String,
    default: 'Satisfacción del Cliente'
  },
  value: {
    type: Number,
    required: true,
    validator: (v) => v >= 0 && v <= 100
  },
  description: {
    type: String,
    default: 'Basado en análisis de sentimiento de conversaciones'
  },
  showStats: {
    type: Boolean,
    default: false
  },
  positiveCount: {
    type: Number,
    default: 0
  },
  neutralCount: {
    type: Number,
    default: 0
  },
  negativeCount: {
    type: Number,
    default: 0
  }
})

// Calculate needle rotation (-90 to 90 degrees)
const needleRotation = computed(() => {
  // 0% = -90deg, 50% = 0deg, 100% = 90deg
  return (props.value / 100) * 180 - 90
})

// Calculate active arc path
const activeArcPath = computed(() => {
  const percentage = Math.min(Math.max(props.value, 0), 100) / 100
  const radius = 80
  const centerX = 100
  const centerY = 100

  // Start angle is 180 degrees (left side)
  const startAngle = Math.PI
  const endAngle = Math.PI - (percentage * Math.PI)

  const startX = centerX + radius * Math.cos(startAngle)
  const startY = centerY - radius * Math.sin(startAngle)
  const endX = centerX + radius * Math.cos(endAngle)
  const endY = centerY - radius * Math.sin(endAngle)

  const largeArcFlag = percentage > 0.5 ? 1 : 0

  return `M ${startX} ${startY} A ${radius} ${radius} 0 ${largeArcFlag} 1 ${endX} ${endY}`
})

// Gauge color based on value
const gaugeColor = computed(() => {
  if (props.value >= 70) return '#27ae60'
  if (props.value >= 50) return '#f39c12'
  return '#e74c3c'
})

// Value class for styling
const valueClass = computed(() => {
  if (props.value >= 70) return 'positive'
  if (props.value >= 50) return 'neutral'
  return 'negative'
})

// Sentiment emoji
const sentimentEmoji = computed(() => {
  if (props.value >= 80) return '😄'
  if (props.value >= 70) return '😊'
  if (props.value >= 60) return '🙂'
  if (props.value >= 50) return '😐'
  if (props.value >= 40) return '😕'
  return '😞'
})

// Sentiment label
const sentimentLabel = computed(() => {
  if (props.value >= 80) return 'Excelente'
  if (props.value >= 70) return 'Muy Bueno'
  if (props.value >= 60) return 'Bueno'
  if (props.value >= 50) return 'Aceptable'
  if (props.value >= 40) return 'Regular'
  return 'Necesita Mejora'
})
</script>

<style scoped>
.sentiment-gauge {
  background: white;
  padding: 1.5rem;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  text-align: center;
}

.gauge-title {
  margin: 0 0 1rem 0;
  color: #2c3e50;
  font-size: 1.1rem;
}

.gauge-container {
  position: relative;
  width: 100%;
  max-width: 250px;
  margin: 0 auto;
}

.gauge-svg {
  width: 100%;
  height: auto;
}

.active-arc {
  transition: all 0.5s ease-out;
}

.gauge-value {
  position: absolute;
  bottom: 20%;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: baseline;
}

.value-number {
  font-size: 2.5rem;
  font-weight: bold;
  line-height: 1;
}

.value-percent {
  font-size: 1rem;
  margin-left: 2px;
}

.gauge-value.positive .value-number {
  color: #27ae60;
}

.gauge-value.neutral .value-number {
  color: #f39c12;
}

.gauge-value.negative .value-number {
  color: #e74c3c;
}

.emoji-indicator {
  font-size: 2rem;
  margin-top: -0.5rem;
}

.gauge-description {
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid #eee;
}

.description-label {
  display: block;
  font-size: 1.1rem;
  font-weight: 600;
  color: #2c3e50;
  margin-bottom: 0.25rem;
}

.description-detail {
  display: block;
  font-size: 0.85rem;
  color: #7f8c8d;
}

.gauge-stats {
  display: flex;
  justify-content: center;
  gap: 1.5rem;
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid #eee;
}

.stat-item {
  text-align: center;
}

.stat-value {
  display: block;
  font-size: 1.25rem;
  font-weight: bold;
  color: #2c3e50;
}

.stat-label {
  display: block;
  font-size: 0.75rem;
  color: #95a5a6;
  text-transform: uppercase;
}

@media (max-width: 768px) {
  .gauge-container {
    max-width: 200px;
  }

  .value-number {
    font-size: 2rem;
  }

  .emoji-indicator {
    font-size: 1.5rem;
  }
}
</style>
