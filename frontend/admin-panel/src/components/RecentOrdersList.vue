<template>
  <div class="recent-orders">
    <h3 class="title">{{ title }}</h3>
    <div v-if="orders.length === 0" class="no-data">
      <p>No hay órdenes recientes</p>
    </div>
    <div v-else class="orders-table">
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Mesa</th>
            <th>Estado</th>
            <th>Total</th>
            <th>Hora</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="order in orders"
            :key="order.id"
            class="order-row">
            <td class="order-id">#{{ order.id }}</td>
            <td class="table-number">Mesa {{ order.table_number || order.table_id }}</td>
            <td>
              <span class="status-badge" :class="getStatusClass(order.status)">
                {{ formatStatus(order.status) }}
              </span>
            </td>
            <td class="amount">${{ parseFloat(order.total_amount).toFixed(2) }}</td>
            <td class="time">{{ formatTime(order.created_at) }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  title: {
    type: String,
    default: 'Órdenes Recientes'
  },
  orders: {
    type: Array,
    required: true
  }
})

function getStatusClass(status) {
  const statusLower = status?.toLowerCase() || ''
  if (statusLower === 'pending') return 'status-pending'
  if (statusLower === 'preparing') return 'status-preparing'
  if (statusLower === 'ready') return 'status-ready'
  if (statusLower === 'delivered') return 'status-delivered'
  if (statusLower === 'cancelled') return 'status-cancelled'
  return 'status-default'
}

function formatStatus(status) {
  const statusMap = {
    pending: 'Pendiente',
    preparing: 'Preparando',
    ready: 'Listo',
    delivered: 'Entregado',
    cancelled: 'Cancelado',
    paid: 'Pagado'
  }
  return statusMap[status?.toLowerCase()] || status
}

function formatTime(timestamp) {
  if (!timestamp) return '-'
  const date = new Date(timestamp)
  return date.toLocaleTimeString('es-ES', {
    hour: '2-digit',
    minute: '2-digit'
  })
}
</script>

<style scoped>
.recent-orders {
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

.orders-table {
  overflow-x: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
}

thead {
  background: #f8f9fa;
}

th {
  padding: 0.75rem;
  text-align: left;
  font-weight: 600;
  color: #7f8c8d;
  font-size: 0.9rem;
  border-bottom: 2px solid #e0e0e0;
}

.order-row {
  border-bottom: 1px solid #e9ecef;
  transition: background 0.2s;
}

.order-row:hover {
  background: #f8f9fa;
}

td {
  padding: 0.75rem;
  color: #2c3e50;
}

.order-id {
  font-weight: 600;
  color: #3498db;
}

.table-number {
  font-weight: 500;
}

.status-badge {
  display: inline-block;
  padding: 0.25rem 0.75rem;
  border-radius: 12px;
  font-size: 0.8rem;
  font-weight: 600;
  text-transform: uppercase;
}

.status-pending {
  background: #e74c3c;
  color: white;
}

.status-preparing {
  background: #f39c12;
  color: white;
}

.status-ready {
  background: #27ae60;
  color: white;
}

.status-delivered {
  background: #3498db;
  color: white;
}

.status-cancelled {
  background: #95a5a6;
  color: white;
}

.status-default {
  background: #ecf0f1;
  color: #7f8c8d;
}

.amount {
  font-weight: 600;
  color: #27ae60;
}

.time {
  color: #7f8c8d;
  font-size: 0.9rem;
}

@media (max-width: 768px) {
  th,
  td {
    padding: 0.5rem;
    font-size: 0.85rem;
  }

  .status-badge {
    font-size: 0.7rem;
    padding: 0.2rem 0.5rem;
  }
}
</style>
