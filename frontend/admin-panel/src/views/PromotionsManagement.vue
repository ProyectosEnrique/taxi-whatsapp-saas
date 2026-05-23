<template>
  <div class="promotions-management">
    <!-- Header -->
    <div class="page-header">
      <div>
        <h1>Gestion de Promociones</h1>
        <p class="subtitle">Configura promociones y ofertas especiales</p>
      </div>
      <button @click="openAddPromotion" class="btn-primary">
        + Nueva Promocion
      </button>
    </div>

    <!-- Loading/Error -->
    <div v-if="loading" class="loading">Cargando...</div>
    <div v-else-if="error" class="error">{{ error }}</div>

    <!-- Promotions List -->
    <div v-else class="promotions-grid">
      <div
        v-for="promo in promotions"
        :key="promo.id"
        class="promotion-card"
        :class="{ inactive: !promo.is_active }">
        <div class="promo-header">
          <span class="promo-type-badge" :class="promo.promotion_type">
            {{ getTypeLabel(promo.promotion_type) }}
          </span>
          <span class="promo-priority">
            {{ '★'.repeat(promo.priority) }}{{ '☆'.repeat(5 - promo.priority) }}
          </span>
        </div>
        <div class="promo-body">
          <h3>{{ promo.name }}</h3>
          <p class="description">{{ promo.description }}</p>
          <div class="promo-value">
            {{ getValueDisplay(promo) }}
          </div>
          <div v-if="promo.products && promo.products.length" class="products-tags">
            <span
              v-for="product in promo.products.slice(0, 3)"
              :key="product.id"
              class="product-tag">
              {{ product.name }}
            </span>
            <span v-if="promo.products.length > 3" class="more-tag">
              +{{ promo.products.length - 3 }} mas
            </span>
          </div>
          <div v-else class="products-tags">
            <span class="product-tag all">Aplica a todos</span>
          </div>
        </div>
        <div class="promo-schedule">
          <div v-if="promo.start_date || promo.end_date" class="schedule-item">
            <span>Fecha:</span>
            {{ formatDateRange(promo.start_date, promo.end_date) }}
          </div>
          <div v-if="promo.start_time && promo.end_time" class="schedule-item">
            <span>Horario:</span>
            {{ promo.start_time }} - {{ promo.end_time }}
          </div>
          <div v-if="promo.days_of_week" class="schedule-item">
            <span>Dias:</span>
            {{ promo.days_of_week }}
          </div>
        </div>
        <div class="promo-stats">
          <span class="stat">Usado: {{ promo.times_used }} veces</span>
        </div>
        <div class="promo-actions">
          <button @click="toggleActive(promo)" class="btn-toggle" :class="{ active: promo.is_active }">
            {{ promo.is_active ? 'Desactivar' : 'Activar' }}
          </button>
          <button @click="openEditPromotion(promo)" class="btn-edit">
            Editar
          </button>
          <button @click="confirmDelete(promo)" class="btn-delete">
            Eliminar
          </button>
        </div>
        <button
          v-if="promo.is_active"
          @click="openWhatsAppBroadcast(promo)"
          class="btn-whatsapp"
          title="Enviar promocion por WhatsApp">
          📢 Enviar por WhatsApp
        </button>
      </div>

      <!-- Empty State -->
      <div v-if="promotions.length === 0" class="empty-state">
        <p>No hay promociones creadas</p>
        <button @click="openAddPromotion" class="btn-primary">
          Crear primera promocion
        </button>
      </div>
    </div>

    <!-- Promotion Modal -->
    <Transition name="modal">
      <div v-if="showModal" class="modal-overlay" @click="closeModal">
        <div class="modal-content large" @click.stop>
          <div class="modal-header">
            <h2>{{ editingPromotion ? 'Editar Promocion' : 'Nueva Promocion' }}</h2>
            <button @click="closeModal" class="btn-close">X</button>
          </div>
          <form @submit.prevent="savePromotion" class="promo-form">
            <!-- Basic Info -->
            <div class="form-section">
              <h3>Informacion Basica</h3>
              <div class="form-group">
                <label>Nombre *</label>
                <input v-model="form.name" required placeholder="Ej: 2x1 en Hamburguesas" />
              </div>
              <div class="form-group">
                <label>Descripcion</label>
                <textarea v-model="form.description" rows="2" placeholder="Describe la promocion..."></textarea>
              </div>
            </div>

            <!-- Promotion Type -->
            <div class="form-section">
              <h3>Tipo de Promocion</h3>
              <div class="form-row">
                <div class="form-group">
                  <label>Tipo *</label>
                  <select v-model="form.promotion_type" required>
                    <option value="percentage">Porcentaje de descuento</option>
                    <option value="fixed">Descuento fijo ($)</option>
                    <option value="2x1">2 x 1</option>
                    <option value="combo">Combo (precio especial)</option>
                    <option value="buy_x_get_y">Compra X lleva Y</option>
                  </select>
                </div>
                <div class="form-group" v-if="form.promotion_type === 'percentage'">
                  <label>Descuento (%)</label>
                  <input v-model.number="form.discount_value" type="number" min="1" max="100" placeholder="20" />
                </div>
                <div class="form-group" v-if="form.promotion_type === 'fixed'">
                  <label>Descuento ($)</label>
                  <input v-model.number="form.discount_value" type="number" min="1" placeholder="50" />
                </div>
                <div class="form-group" v-if="form.promotion_type === 'combo'">
                  <label>Precio especial ($)</label>
                  <input v-model.number="form.special_price" type="number" min="1" placeholder="99" />
                </div>
              </div>
              <div class="form-row" v-if="form.promotion_type === 'buy_x_get_y'">
                <div class="form-group">
                  <label>Compra (cantidad)</label>
                  <input v-model.number="form.buy_quantity" type="number" min="1" placeholder="2" />
                </div>
                <div class="form-group">
                  <label>Lleva (cantidad)</label>
                  <input v-model.number="form.get_quantity" type="number" min="1" placeholder="1" />
                </div>
              </div>
            </div>

            <!-- Schedule -->
            <div class="form-section">
              <h3>Vigencia y Horario</h3>
              <div class="form-row">
                <div class="form-group">
                  <label>Fecha inicio</label>
                  <input v-model="form.start_date" type="datetime-local" />
                </div>
                <div class="form-group">
                  <label>Fecha fin</label>
                  <input v-model="form.end_date" type="datetime-local" />
                </div>
              </div>
              <div class="form-row">
                <div class="form-group">
                  <label>Hora inicio</label>
                  <input v-model="form.start_time" type="time" />
                </div>
                <div class="form-group">
                  <label>Hora fin</label>
                  <input v-model="form.end_time" type="time" />
                </div>
              </div>
              <div class="form-group">
                <label>Dias de la semana (dejar vacio para todos)</label>
                <div class="days-selector">
                  <label v-for="day in daysOfWeek" :key="day.value">
                    <input
                      type="checkbox"
                      :value="day.value"
                      v-model="selectedDays" />
                    {{ day.label }}
                  </label>
                </div>
              </div>
            </div>

            <!-- Products -->
            <div class="form-section">
              <h3>Productos Aplicables</h3>
              <p class="form-hint">Selecciona los productos a los que aplica. Si no seleccionas ninguno, aplicara a todo el menu.</p>
              <div class="products-selector">
                <div
                  v-for="product in availableProducts"
                  :key="product.id"
                  class="product-checkbox"
                  :class="{ selected: form.product_ids.includes(product.id) }">
                  <input
                    type="checkbox"
                    :value="product.id"
                    v-model="form.product_ids"
                    :id="'prod-' + product.id" />
                  <label :for="'prod-' + product.id">
                    {{ product.name }}
                    <span class="price">${{ parseFloat(product.price).toFixed(2) }}</span>
                  </label>
                </div>
              </div>
            </div>

            <!-- Voice Agent -->
            <div class="form-section">
              <h3>Agente de Ventas</h3>
              <div class="form-group">
                <label>Frase sugerida para el agente</label>
                <textarea
                  v-model="form.voice_pitch"
                  rows="2"
                  placeholder="Ej: Hoy tenemos 2x1 en hamburguesas, te gustaria aprovechar la promocion?"></textarea>
                <small class="form-hint">El agente de voz usara esta frase para mencionar la promocion a los clientes.</small>
              </div>
              <div class="form-group">
                <label>Prioridad (1-5)</label>
                <input v-model.number="form.priority" type="range" min="1" max="5" />
                <span class="priority-display">{{ form.priority }} - {{ getPriorityLabel(form.priority) }}</span>
              </div>
            </div>

            <!-- Active Status -->
            <div class="form-group checkbox">
              <label>
                <input v-model="form.is_active" type="checkbox" />
                Promocion activa
              </label>
            </div>

            <div class="form-actions">
              <button type="button" @click="closeModal" class="btn-cancel">
                Cancelar
              </button>
              <button type="submit" class="btn-save">
                {{ editingPromotion ? 'Guardar Cambios' : 'Crear Promocion' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </Transition>

    <!-- Delete Confirmation -->
    <Transition name="modal">
      <div v-if="showDeleteConfirm" class="modal-overlay" @click="showDeleteConfirm = false">
        <div class="modal-content small" @click.stop>
          <h3>Confirmar Eliminacion</h3>
          <p>Estas seguro de eliminar la promocion "{{ promotionToDelete?.name }}"?</p>
          <div class="form-actions">
            <button @click="showDeleteConfirm = false" class="btn-cancel">Cancelar</button>
            <button @click="deletePromotion" class="btn-delete">Eliminar</button>
          </div>
        </div>
      </div>
    </Transition>

    <!-- WhatsApp Broadcast Modal -->
    <Transition name="modal">
      <div v-if="showWhatsAppModal" class="modal-overlay" @click="closeWhatsAppModal">
        <div class="modal-content" @click.stop>
          <div class="modal-header">
            <h2>📢 Enviar por WhatsApp</h2>
            <button @click="closeWhatsAppModal" class="btn-close">X</button>
          </div>
          <div class="broadcast-form">
            <div class="promo-summary">
              <h3>{{ selectedPromotion?.name }}</h3>
              <p class="promo-desc">{{ selectedPromotion?.description }}</p>
              <div class="promo-highlight">{{ getValueDisplay(selectedPromotion) }}</div>
            </div>

            <div class="form-section">
              <h3>Mensaje Personalizado (Opcional)</h3>
              <textarea
                v-model="broadcastForm.custom_message"
                rows="3"
                placeholder="Deja en blanco para usar el mensaje de la promocion..."></textarea>
            </div>

            <div class="form-section">
              <h3>Segmento de Clientes</h3>
              <div class="segment-selector">
                <label
                  v-for="segment in segments"
                  :key="segment.value"
                  class="segment-option"
                  :class="{ selected: broadcastForm.segment === segment.value }">
                  <input
                    type="radio"
                    :value="segment.value"
                    v-model="broadcastForm.segment"
                    @change="previewAudience" />
                  <div class="segment-info">
                    <span class="segment-label">{{ segment.label }}</span>
                    <span class="segment-desc">{{ segment.description }}</span>
                  </div>
                </label>
              </div>
            </div>

            <div class="form-section">
              <div class="audience-preview">
                <div class="preview-icon">👥</div>
                <div class="preview-info">
                  <div class="preview-count">
                    {{ audienceCount === null ? '...' : audienceCount }}
                  </div>
                  <div class="preview-label">Clientes seran contactados</div>
                </div>
              </div>
            </div>

            <div class="form-group checkbox">
              <label>
                <input v-model="broadcastForm.personalize" type="checkbox" />
                Personalizar mensajes (recomendado)
              </label>
              <small class="form-hint">
                Cada cliente recibira un mensaje personalizado con su nombre y productos favoritos
              </small>
            </div>

            <div v-if="broadcastStatus.sending" class="broadcast-progress">
              <div class="progress-spinner"></div>
              <p>Enviando mensajes...</p>
            </div>

            <div v-if="broadcastStatus.result" class="broadcast-result" :class="broadcastStatus.success ? 'success' : 'error'">
              <h4>{{ broadcastStatus.success ? '✅ Broadcast Enviado' : '❌ Error al Enviar' }}</h4>
              <div v-if="broadcastStatus.success" class="result-stats">
                <div class="stat-item">
                  <span class="stat-label">Enviados:</span>
                  <span class="stat-value">{{ broadcastStatus.result.total_sent }}</span>
                </div>
                <div class="stat-item">
                  <span class="stat-label">Exitosos:</span>
                  <span class="stat-value success">{{ broadcastStatus.result.successful }}</span>
                </div>
                <div class="stat-item">
                  <span class="stat-label">Fallidos:</span>
                  <span class="stat-value error">{{ broadcastStatus.result.failed }}</span>
                </div>
                <div class="stat-item">
                  <span class="stat-label">Tasa de éxito:</span>
                  <span class="stat-value">{{ broadcastStatus.result.success_rate }}%</span>
                </div>
              </div>
              <p v-else class="error-message">{{ broadcastStatus.error }}</p>
            </div>

            <div class="form-actions">
              <button @click="closeWhatsAppModal" class="btn-cancel">
                Cancelar
              </button>
              <button
                @click="sendBroadcast"
                class="btn-whatsapp-send"
                :disabled="broadcastStatus.sending || audienceCount === 0">
                <span v-if="!broadcastStatus.sending">📤 Enviar a {{ audienceCount || 0 }} clientes</span>
                <span v-else>Enviando...</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'

// API Base URL (ajustar segun configuracion)
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001'

// State
const loading = ref(true)
const error = ref(null)
const promotions = ref([])
const availableProducts = ref([])
const showModal = ref(false)
const showDeleteConfirm = ref(false)
const editingPromotion = ref(null)
const promotionToDelete = ref(null)
const selectedDays = ref([])

// WhatsApp Broadcast State
const showWhatsAppModal = ref(false)
const selectedPromotion = ref(null)
const audienceCount = ref(null)
const broadcastForm = reactive({
  custom_message: '',
  segment: 'all',
  personalize: true
})
const broadcastStatus = reactive({
  sending: false,
  success: false,
  result: null,
  error: null
})

const daysOfWeek = [
  { value: 'lunes', label: 'Lun' },
  { value: 'martes', label: 'Mar' },
  { value: 'miercoles', label: 'Mie' },
  { value: 'jueves', label: 'Jue' },
  { value: 'viernes', label: 'Vie' },
  { value: 'sabado', label: 'Sab' },
  { value: 'domingo', label: 'Dom' }
]

// Segmentos de WhatsApp
const segments = [
  {
    value: 'all',
    label: 'Todos los clientes',
    description: 'Todos los clientes con WhatsApp registrado'
  },
  {
    value: 'frequent',
    label: 'Clientes frecuentes',
    description: 'Clientes con 3 o más órdenes'
  },
  {
    value: 'inactive',
    label: 'Clientes inactivos',
    description: 'Sin ordenar en los últimos 30 días'
  },
  {
    value: 'new',
    label: 'Clientes nuevos',
    description: 'Clientes con 1-2 órdenes'
  },
  {
    value: 'vip',
    label: 'Clientes VIP',
    description: 'Gasto total mayor a $1000'
  }
]

// Form
const defaultForm = {
  name: '',
  description: '',
  promotion_type: 'percentage',
  discount_value: null,
  buy_quantity: 1,
  get_quantity: 1,
  special_price: null,
  start_date: null,
  end_date: null,
  start_time: null,
  end_time: null,
  days_of_week: null,
  is_active: true,
  voice_pitch: '',
  priority: 3,
  product_ids: []
}

const form = reactive({ ...defaultForm })

// Helpers
const getTypeLabel = (type) => {
  const labels = {
    percentage: '% Descuento',
    fixed: '$ Descuento',
    '2x1': '2 x 1',
    combo: 'Combo',
    buy_x_get_y: 'Compra X lleva Y'
  }
  return labels[type] || type
}

const getValueDisplay = (promo) => {
  switch (promo.promotion_type) {
    case 'percentage':
      return `${promo.discount_value}% de descuento`
    case 'fixed':
      return `$${promo.discount_value} de descuento`
    case '2x1':
      return 'Lleva 2 paga 1'
    case 'combo':
      return `Precio especial: $${promo.special_price}`
    case 'buy_x_get_y':
      return `Compra ${promo.buy_quantity} lleva ${promo.get_quantity}`
    default:
      return ''
  }
}

const getPriorityLabel = (priority) => {
  const labels = ['', 'Muy baja', 'Baja', 'Normal', 'Alta', 'Muy alta']
  return labels[priority] || ''
}

const formatDateRange = (start, end) => {
  if (!start && !end) return 'Sin fecha limite'
  const formatDate = (d) => d ? new Date(d).toLocaleDateString() : ''
  if (start && end) return `${formatDate(start)} - ${formatDate(end)}`
  if (start) return `Desde ${formatDate(start)}`
  return `Hasta ${formatDate(end)}`
}

// API Calls
const fetchPromotions = async () => {
  try {
    const response = await fetch(`${API_URL}/api/v1/promotions`)
    if (!response.ok) throw new Error('Error al cargar promociones')
    promotions.value = await response.json()
  } catch (err) {
    error.value = err.message
  }
}

const fetchProducts = async () => {
  try {
    const response = await fetch(`${API_URL}/api/v1/products`)
    if (!response.ok) throw new Error('Error al cargar productos')
    availableProducts.value = await response.json()
  } catch (err) {
    console.error('Error fetching products:', err)
  }
}

const savePromotion = async () => {
  try {
    // Build days_of_week from selected days
    form.days_of_week = selectedDays.value.length > 0 ? selectedDays.value.join(',') : null

    const url = editingPromotion.value
      ? `${API_URL}/api/v1/promotions/${editingPromotion.value.id}`
      : `${API_URL}/api/v1/promotions`

    const method = editingPromotion.value ? 'PUT' : 'POST'

    const response = await fetch(url, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(form)
    })

    if (!response.ok) throw new Error('Error al guardar promocion')

    await fetchPromotions()
    closeModal()
  } catch (err) {
    alert(err.message)
  }
}

const deletePromotion = async () => {
  try {
    const response = await fetch(`${API_URL}/api/v1/promotions/${promotionToDelete.value.id}`, {
      method: 'DELETE'
    })

    if (!response.ok) throw new Error('Error al eliminar promocion')

    await fetchPromotions()
    showDeleteConfirm.value = false
    promotionToDelete.value = null
  } catch (err) {
    alert(err.message)
  }
}

const toggleActive = async (promo) => {
  try {
    const response = await fetch(
      `${API_URL}/api/v1/promotions/${promo.id}/toggle?is_active=${!promo.is_active}`,
      { method: 'PATCH' }
    )

    if (!response.ok) throw new Error('Error al cambiar estado')

    await fetchPromotions()
  } catch (err) {
    alert(err.message)
  }
}

// Modal handlers
const openAddPromotion = () => {
  editingPromotion.value = null
  Object.assign(form, { ...defaultForm, product_ids: [] })
  selectedDays.value = []
  showModal.value = true
}

const openEditPromotion = (promo) => {
  editingPromotion.value = promo
  Object.assign(form, {
    ...promo,
    product_ids: promo.products ? promo.products.map(p => p.id) : []
  })
  selectedDays.value = promo.days_of_week ? promo.days_of_week.split(',') : []
  showModal.value = true
}

const closeModal = () => {
  showModal.value = false
  editingPromotion.value = null
}

const confirmDelete = (promo) => {
  promotionToDelete.value = promo
  showDeleteConfirm.value = true
}

// WhatsApp Broadcast handlers
const openWhatsAppBroadcast = (promo) => {
  selectedPromotion.value = promo
  broadcastForm.custom_message = promo.voice_pitch || ''
  broadcastForm.segment = 'all'
  broadcastForm.personalize = true
  broadcastStatus.sending = false
  broadcastStatus.success = false
  broadcastStatus.result = null
  broadcastStatus.error = null
  showWhatsAppModal.value = true
  previewAudience()
}

const closeWhatsAppModal = () => {
  showWhatsAppModal.value = false
  selectedPromotion.value = null
  audienceCount.value = null
}

const previewAudience = async () => {
  try {
    audienceCount.value = null
    const response = await fetch(`${API_URL}/api/admin/whatsapp/preview-audience`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        segment: broadcastForm.segment
      })
    })

    if (!response.ok) throw new Error('Error al obtener preview')

    const data = await response.json()
    audienceCount.value = data.count || 0
  } catch (err) {
    console.error('Error previewing audience:', err)
    // Fallback to mock data for development
    const mockCounts = {
      all: 150,
      frequent: 45,
      inactive: 32,
      new: 28,
      vip: 15
    }
    audienceCount.value = mockCounts[broadcastForm.segment] || 0
  }
}

const sendBroadcast = async () => {
  if (audienceCount.value === 0) {
    alert('No hay clientes en este segmento')
    return
  }

  try {
    broadcastStatus.sending = true
    broadcastStatus.success = false
    broadcastStatus.result = null
    broadcastStatus.error = null

    const response = await fetch(`${API_URL}/api/admin/whatsapp/broadcast`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        promotion_id: selectedPromotion.value.id,
        custom_message: broadcastForm.custom_message || null,
        audience_filter: {
          segment: broadcastForm.segment
        },
        personalize: broadcastForm.personalize
      })
    })

    if (!response.ok) throw new Error('Error al enviar broadcast')

    const result = await response.json()
    broadcastStatus.success = true
    broadcastStatus.result = result

    // Auto-cerrar después de 3 segundos si fue exitoso
    setTimeout(() => {
      if (broadcastStatus.success) {
        closeWhatsAppModal()
      }
    }, 3000)
  } catch (err) {
    broadcastStatus.success = false
    broadcastStatus.error = err.message
  } finally {
    broadcastStatus.sending = false
  }
}

// Lifecycle
onMounted(async () => {
  await Promise.all([fetchPromotions(), fetchProducts()])
  loading.value = false
})
</script>

<style scoped>
.promotions-management {
  max-width: 1400px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
}

.page-header h1 {
  margin: 0;
  font-size: 1.75rem;
}

.subtitle {
  color: #666;
  margin: 0.25rem 0 0;
}

.btn-primary {
  background: #3498db;
  color: white;
  border: none;
  padding: 0.75rem 1.5rem;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 600;
}

.btn-primary:hover {
  background: #2980b9;
}

.loading, .error {
  text-align: center;
  padding: 3rem;
  font-size: 1.25rem;
}

.error {
  color: #e74c3c;
}

/* Promotions Grid */
.promotions-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: 1.5rem;
}

.promotion-card {
  background: white;
  border-radius: 12px;
  padding: 1.5rem;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  transition: transform 0.2s, box-shadow 0.2s;
}

.promotion-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(0,0,0,0.15);
}

.promotion-card.inactive {
  opacity: 0.6;
  border: 2px dashed #ccc;
}

.promo-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.promo-type-badge {
  padding: 0.25rem 0.75rem;
  border-radius: 20px;
  font-size: 0.8rem;
  font-weight: 600;
  text-transform: uppercase;
}

.promo-type-badge.percentage { background: #e8f5e9; color: #2e7d32; }
.promo-type-badge.fixed { background: #e3f2fd; color: #1565c0; }
.promo-type-badge.2x1 { background: #fff3e0; color: #e65100; }
.promo-type-badge.combo { background: #fce4ec; color: #c2185b; }
.promo-type-badge.buy_x_get_y { background: #f3e5f5; color: #7b1fa2; }

.promo-priority {
  color: #f39c12;
  letter-spacing: 2px;
}

.promo-body h3 {
  margin: 0 0 0.5rem;
  font-size: 1.25rem;
}

.promo-body .description {
  color: #666;
  font-size: 0.9rem;
  margin-bottom: 0.75rem;
}

.promo-value {
  font-size: 1.1rem;
  font-weight: 600;
  color: #27ae60;
  margin-bottom: 1rem;
}

.products-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.product-tag {
  background: #f0f0f0;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-size: 0.8rem;
}

.product-tag.all {
  background: #e8f5e9;
  color: #2e7d32;
}

.more-tag {
  background: #e3f2fd;
  color: #1565c0;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-size: 0.8rem;
}

.promo-schedule {
  background: #f8f9fa;
  padding: 0.75rem;
  border-radius: 8px;
  margin-bottom: 1rem;
  font-size: 0.85rem;
}

.schedule-item {
  margin-bottom: 0.25rem;
}

.schedule-item span {
  font-weight: 600;
  margin-right: 0.5rem;
}

.promo-stats {
  font-size: 0.85rem;
  color: #666;
  margin-bottom: 1rem;
}

.promo-actions {
  display: flex;
  gap: 0.5rem;
}

.promo-actions button {
  flex: 1;
  padding: 0.5rem;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.85rem;
}

.btn-toggle {
  background: #e74c3c;
  color: white;
}

.btn-toggle.active {
  background: #27ae60;
}

.btn-edit {
  background: #3498db;
  color: white;
}

.btn-delete {
  background: #95a5a6;
  color: white;
}

.btn-delete:hover {
  background: #e74c3c;
}

.empty-state {
  grid-column: 1 / -1;
  text-align: center;
  padding: 4rem;
  background: white;
  border-radius: 12px;
}

/* Modal */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0,0,0,0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  border-radius: 12px;
  width: 90%;
  max-width: 600px;
  max-height: 90vh;
  overflow-y: auto;
}

.modal-content.large {
  max-width: 800px;
}

.modal-content.small {
  max-width: 400px;
  padding: 2rem;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem;
  border-bottom: 1px solid #eee;
  position: sticky;
  top: 0;
  background: white;
  z-index: 1;
}

.modal-header h2 {
  margin: 0;
}

.btn-close {
  background: none;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  color: #666;
}

.promo-form {
  padding: 1.5rem;
}

.form-section {
  margin-bottom: 2rem;
  padding-bottom: 1.5rem;
  border-bottom: 1px solid #eee;
}

.form-section h3 {
  margin: 0 0 1rem;
  font-size: 1rem;
  color: #333;
}

.form-group {
  margin-bottom: 1rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 500;
}

.form-group input[type="text"],
.form-group input[type="number"],
.form-group input[type="url"],
.form-group input[type="datetime-local"],
.form-group input[type="time"],
.form-group textarea,
.form-group select {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 8px;
  font-size: 1rem;
}

.form-group textarea {
  resize: vertical;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

.form-hint {
  display: block;
  color: #666;
  font-size: 0.85rem;
  margin-top: 0.25rem;
}

.days-selector {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
}

.days-selector label {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  cursor: pointer;
}

.products-selector {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 0.5rem;
  max-height: 200px;
  overflow-y: auto;
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 0.75rem;
}

.product-checkbox {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.2s;
}

.product-checkbox:hover {
  background: #f5f5f5;
}

.product-checkbox.selected {
  background: #e3f2fd;
}

.product-checkbox label {
  cursor: pointer;
  display: flex;
  justify-content: space-between;
  flex: 1;
}

.product-checkbox .price {
  color: #27ae60;
  font-weight: 600;
}

.form-group.checkbox label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
}

.priority-display {
  margin-left: 1rem;
  font-weight: 500;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 1rem;
  margin-top: 2rem;
}

.btn-cancel {
  background: #f5f5f5;
  border: none;
  padding: 0.75rem 1.5rem;
  border-radius: 8px;
  cursor: pointer;
}

.btn-save {
  background: #27ae60;
  color: white;
  border: none;
  padding: 0.75rem 1.5rem;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 600;
}

/* WhatsApp Broadcast Button */
.btn-whatsapp {
  width: 100%;
  background: linear-gradient(135deg, #25d366 0%, #128c7e 100%);
  color: white;
  border: none;
  padding: 0.75rem;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 600;
  margin-top: 0.75rem;
  transition: transform 0.2s, box-shadow 0.2s;
}

.btn-whatsapp:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(37, 211, 102, 0.4);
}

/* Broadcast Modal */
.broadcast-form {
  padding: 1.5rem;
}

.promo-summary {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 1.5rem;
  border-radius: 12px;
  margin-bottom: 1.5rem;
}

.promo-summary h3 {
  margin: 0 0 0.5rem;
  font-size: 1.25rem;
}

.promo-summary .promo-desc {
  margin: 0 0 0.75rem;
  opacity: 0.9;
  font-size: 0.9rem;
}

.promo-summary .promo-highlight {
  background: rgba(255, 255, 255, 0.2);
  padding: 0.5rem 1rem;
  border-radius: 8px;
  display: inline-block;
  font-weight: 600;
}

.segment-selector {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.segment-option {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  padding: 1rem;
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.segment-option:hover {
  border-color: #25d366;
  background: #f0fff4;
}

.segment-option.selected {
  border-color: #25d366;
  background: #e8f8f0;
}

.segment-option input[type="radio"] {
  margin-top: 0.25rem;
}

.segment-info {
  flex: 1;
}

.segment-label {
  display: block;
  font-weight: 600;
  margin-bottom: 0.25rem;
}

.segment-desc {
  display: block;
  font-size: 0.85rem;
  color: #666;
}

.audience-preview {
  display: flex;
  align-items: center;
  gap: 1.5rem;
  padding: 1.5rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 12px;
  color: white;
}

.preview-icon {
  font-size: 3rem;
}

.preview-info {
  flex: 1;
}

.preview-count {
  font-size: 2.5rem;
  font-weight: 700;
  line-height: 1;
  margin-bottom: 0.5rem;
}

.preview-label {
  font-size: 0.9rem;
  opacity: 0.9;
}

.broadcast-progress {
  text-align: center;
  padding: 2rem;
  background: #f8f9fa;
  border-radius: 8px;
  margin-bottom: 1rem;
}

.progress-spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #e0e0e0;
  border-top-color: #25d366;
  border-radius: 50%;
  margin: 0 auto 1rem;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.broadcast-result {
  padding: 1.5rem;
  border-radius: 8px;
  margin-bottom: 1rem;
}

.broadcast-result.success {
  background: #d4edda;
  border: 1px solid #c3e6cb;
  color: #155724;
}

.broadcast-result.error {
  background: #f8d7da;
  border: 1px solid #f5c6cb;
  color: #721c24;
}

.broadcast-result h4 {
  margin: 0 0 1rem;
}

.result-stats {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 0.75rem;
}

.stat-item {
  display: flex;
  justify-content: space-between;
  padding: 0.5rem;
  background: rgba(255, 255, 255, 0.5);
  border-radius: 6px;
}

.stat-label {
  font-weight: 500;
}

.stat-value {
  font-weight: 700;
}

.stat-value.success {
  color: #27ae60;
}

.stat-value.error {
  color: #e74c3c;
}

.error-message {
  margin: 0;
  font-weight: 500;
}

.btn-whatsapp-send {
  background: linear-gradient(135deg, #25d366 0%, #128c7e 100%);
  color: white;
  border: none;
  padding: 0.75rem 1.5rem;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 600;
  transition: all 0.2s;
}

.btn-whatsapp-send:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(37, 211, 102, 0.4);
}

.btn-whatsapp-send:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Transitions */
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.3s ease;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}
</style>
