<template>
  <div class="top-products">
    <h3 class="title">{{ title }}</h3>
    <div v-if="products.length === 0" class="no-data">
      <p>No hay datos disponibles</p>
    </div>
    <div v-else class="products-list">
      <div
        v-for="(product, index) in products"
        :key="index"
        class="product-item">
        <div class="rank">{{ index + 1 }}</div>
        <div class="product-info">
          <div class="product-name">{{ product.name }}</div>
          <div class="product-stats">
            <span class="quantity">{{ product.quantity }} vendidos</span>
            <span class="revenue">${{ product.revenue.toFixed(2) }}</span>
          </div>
        </div>
        <div class="progress-bar">
          <div
            class="progress-fill"
            :style="{ width: `${getPercentage(product.quantity)}%` }">
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  title: {
    type: String,
    default: 'Top 10 Productos'
  },
  products: {
    type: Array,
    required: true,
    // Expected format: [{ name: 'Product', quantity: 10, revenue: 100 }, ...]
  }
})

const maxQuantity = computed(() => {
  if (props.products.length === 0) return 1
  return Math.max(...props.products.map(p => p.quantity))
})

function getPercentage(quantity) {
  return (quantity / maxQuantity.value) * 100
}
</script>

<style scoped>
.top-products {
  background: white;
  padding: 1.5rem;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.title {
  margin: 0 0 1.5rem 0;
  color: #2c3e50;
  font-size: 1.2rem;
}

.no-data {
  text-align: center;
  padding: 2rem;
  color: #95a5a6;
}

.products-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.product-item {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 0.75rem;
  background: #f8f9fa;
  border-radius: 8px;
  transition: all 0.3s;
}

.product-item:hover {
  background: #e9ecef;
  transform: translateX(4px);
}

.rank {
  width: 30px;
  height: 30px;
  background: linear-gradient(135deg, #3498db 0%, #2980b9 100%);
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  font-size: 0.9rem;
  flex-shrink: 0;
}

.product-item:nth-child(1) .rank {
  background: linear-gradient(135deg, #f39c12 0%, #e67e22 100%);
  font-size: 1.1rem;
}

.product-item:nth-child(2) .rank {
  background: linear-gradient(135deg, #95a5a6 0%, #7f8c8d 100%);
}

.product-item:nth-child(3) .rank {
  background: linear-gradient(135deg, #e67e22 0%, #d35400 100%);
}

.product-info {
  flex: 1;
}

.product-name {
  font-weight: 600;
  color: #2c3e50;
  margin-bottom: 0.25rem;
}

.product-stats {
  display: flex;
  gap: 1rem;
  font-size: 0.85rem;
  color: #7f8c8d;
}

.revenue {
  font-weight: 600;
  color: #27ae60;
}

.progress-bar {
  width: 100px;
  height: 8px;
  background: #e0e0e0;
  border-radius: 4px;
  overflow: hidden;
  flex-shrink: 0;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #3498db 0%, #2980b9 100%);
  transition: width 0.3s;
}

@media (max-width: 768px) {
  .product-stats {
    flex-direction: column;
    gap: 0.25rem;
  }

  .progress-bar {
    width: 60px;
  }
}
</style>
