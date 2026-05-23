<template>
  <div class="table-management">
    <div class="header">
      <h1>🪑 Gestión de Mesas</h1>
      <button @click="showCreateModal = true" class="btn-primary">
        ➕ Nueva Mesa
      </button>
    </div>

    <div v-if="loading" class="loading">
      <div class="spinner"></div>
      <p>Cargando mesas...</p>
    </div>

    <div v-else-if="tables.length === 0" class="empty-state">
      <p>No hay mesas registradas</p>
      <button @click="showCreateModal = true" class="btn-primary">Crear Primera Mesa</button>
    </div>

    <div v-else class="tables-grid">
      <div v-for="table in tables" :key="table.id" :class="['table-card', { inactive: !table.is_active }]">
        <div class="table-header">
          <h3>Mesa {{ table.table_number }}</h3>
          <span :class="['status-badge', table.is_active ? 'active' : 'inactive']">
            {{ table.is_active ? 'Activa' : 'Inactiva' }}
          </span>
        </div>

        <div class="table-body">
          <p><strong>Capacidad:</strong> {{ table.capacity }} personas</p>
          <p v-if="table.location"><strong>Ubicación:</strong> {{ table.location }}</p>
          <p v-if="table.description" class="description">{{ table.description }}</p>

          <div v-if="table.qr_code_url" class="qr-section">
            <div class="qr-label">
              <span>📱 Código QR</span>
              <button @click="viewQR(table)" class="btn-icon" title="Ver QR">
                🔍
              </button>
            </div>
            <div class="qr-url">
              <input type="text" :value="getCustomerAppUrl(table)" readonly class="url-input">
              <button @click="copyUrl(table)" class="btn-copy" title="Copiar URL">
                📋
              </button>
            </div>
          </div>

          <div v-else class="qr-missing">
            <span>⚠️ QR no generado</span>
            <button @click="generateQR(table)" class="btn-secondary" :disabled="generatingQR === table.id">
              {{ generatingQR === table.id ? 'Generando...' : 'Generar QR' }}
            </button>
          </div>
        </div>

        <div class="table-actions">
          <button @click="editTable(table)" class="btn-edit">✏️ Editar</button>
          <button @click="toggleTableStatus(table)" class="btn-toggle">
            {{ table.is_active ? '❌ Desactivar' : '✅ Activar' }}
          </button>
          <button v-if="table.qr_code_url" @click="downloadQR(table)" class="btn-download">
            ⬇️ Descargar QR
          </button>
        </div>
      </div>
    </div>

    <!-- Modal para crear/editar mesa -->
    <div v-if="showCreateModal || showEditModal" class="modal-overlay" @click.self="closeModals">
      <div class="modal">
        <div class="modal-header">
          <h2>{{ showEditModal ? 'Editar Mesa' : 'Nueva Mesa' }}</h2>
          <button @click="closeModals" class="btn-close">✕</button>
        </div>

        <form @submit.prevent="submitTableForm" class="modal-body">
          <div class="form-group">
            <label>Número de Mesa *</label>
            <input
              v-model.number="tableForm.table_number"
              type="number"
              min="1"
              required
              placeholder="1, 2, 3..."
              class="form-input">
          </div>

          <div class="form-group">
            <label>Capacidad *</label>
            <input
              v-model.number="tableForm.capacity"
              type="number"
              min="1"
              max="20"
              required
              placeholder="4"
              class="form-input">
          </div>

          <div class="form-group">
            <label>Ubicación</label>
            <input
              v-model="tableForm.location"
              type="text"
              placeholder="Ej: Terraza, Interior, Ventana..."
              class="form-input">
          </div>

          <div class="form-group">
            <label>Descripción</label>
            <textarea
              v-model="tableForm.description"
              rows="3"
              placeholder="Información adicional sobre la mesa..."
              class="form-textarea"></textarea>
          </div>

          <div class="form-group">
            <label class="checkbox-label">
              <input v-model="tableForm.is_active" type="checkbox">
              <span>Mesa activa</span>
            </label>
          </div>

          <div v-if="formError" class="form-error">
            ❌ {{ formError }}
          </div>

          <div class="modal-footer">
            <button type="button" @click="closeModals" class="btn-secondary">Cancelar</button>
            <button type="submit" class="btn-primary" :disabled="submitting">
              {{ submitting ? 'Guardando...' : (showEditModal ? 'Actualizar' : 'Crear') }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- Modal para ver QR -->
    <div v-if="showQRModal && selectedTable" class="modal-overlay" @click.self="showQRModal = false">
      <div class="modal qr-modal">
        <div class="modal-header">
          <h2>Código QR - Mesa {{ selectedTable.table_number }}</h2>
          <button @click="showQRModal = false" class="btn-close">✕</button>
        </div>

        <div class="modal-body qr-display">
          <div class="qr-image-container">
            <img v-if="selectedTable.qr_code_url"
                 :src="selectedTable.qr_code_url"
                 :alt="`QR Mesa ${selectedTable.table_number}`"
                 class="qr-image">
          </div>

          <div class="qr-info">
            <p class="qr-title">Escanea este código para acceder al menú</p>
            <div class="qr-url-display">
              <code>{{ getCustomerAppUrl(selectedTable) }}</code>
            </div>
          </div>

          <div class="qr-actions">
            <button @click="downloadQR(selectedTable)" class="btn-primary">
              ⬇️ Descargar QR
            </button>
            <button @click="copyUrl(selectedTable)" class="btn-secondary">
              📋 Copiar URL
            </button>
            <button @click="printQR(selectedTable)" class="btn-secondary">
              🖨️ Imprimir
            </button>
          </div>
        </div>
      </div>
    </div>

    <div v-if="successMessage" class="toast success">
      ✅ {{ successMessage }}
    </div>

    <div v-if="error" class="toast error">
      ❌ {{ error }}
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'

const tables = ref([])
const loading = ref(true)
const error = ref(null)
const successMessage = ref(null)

const showCreateModal = ref(false)
const showEditModal = ref(false)
const showQRModal = ref(false)
const selectedTable = ref(null)
const generatingQR = ref(null)
const submitting = ref(false)
const formError = ref(null)

const tableForm = ref({
  table_number: null,
  capacity: 4,
  location: '',
  description: '',
  is_active: true
})

const CUSTOMER_APP_URL = 'http://localhost:5001/table' // URL base de la Customer App

onMounted(() => {
  loadTables()
})

/**
 * Carga todas las mesas desde Tables Service
 */
async function loadTables() {
  loading.value = true
  error.value = null

  try {
    const response = await axios.get('/api/v1/tables', {
      params: { limit: 200 }
    })
    tables.value = response.data.sort((a, b) => a.table_number - b.table_number)
    console.log(`✅ ${tables.value.length} mesas cargadas`)
  } catch (err) {
    console.error('❌ Error cargando mesas:', err)
    error.value = 'Error al cargar las mesas'
  } finally {
    loading.value = false
  }
}

/**
 * Abre modal de edición con datos de la mesa
 */
function editTable(table) {
  tableForm.value = {
    id: table.id,
    table_number: table.table_number,
    capacity: table.capacity,
    location: table.location || '',
    description: table.description || '',
    is_active: table.is_active
  }
  showEditModal.value = true
}

/**
 * Envía formulario para crear o actualizar mesa
 */
async function submitTableForm() {
  formError.value = null
  submitting.value = true

  try {
    if (showEditModal.value) {
      // Actualizar mesa existente
      await axios.put(`/api/v1/tables/${tableForm.value.id}`, {
        table_number: tableForm.value.table_number,
        capacity: tableForm.value.capacity,
        location: tableForm.value.location || null,
        description: tableForm.value.description || null,
        is_active: tableForm.value.is_active
      })
      showSuccessMessage('Mesa actualizada correctamente')
    } else {
      // Crear nueva mesa
      await axios.post('/api/v1/tables', {
        table_number: tableForm.value.table_number,
        capacity: tableForm.value.capacity,
        location: tableForm.value.location || null,
        description: tableForm.value.description || null,
        is_active: tableForm.value.is_active
      })
      showSuccessMessage('Mesa creada correctamente')
    }

    closeModals()
    await loadTables()

  } catch (err) {
    console.error('❌ Error guardando mesa:', err)
    formError.value = err.response?.data?.detail || 'Error al guardar la mesa'
  } finally {
    submitting.value = false
  }
}

/**
 * Activa/desactiva una mesa
 */
async function toggleTableStatus(table) {
  try {
    await axios.put(`/api/v1/tables/${table.id}`, {
      is_active: !table.is_active
    })
    showSuccessMessage(`Mesa ${table.is_active ? 'desactivada' : 'activada'} correctamente`)
    await loadTables()
  } catch (err) {
    console.error('❌ Error cambiando estado:', err)
    error.value = 'Error al cambiar el estado de la mesa'
  }
}

/**
 * Genera código QR para una mesa
 */
async function generateQR(table) {
  generatingQR.value = table.id

  try {
    console.log(`🔄 Generando QR para mesa ${table.table_number}...`)
    await axios.post(`/api/v1/tables/${table.id}/generate-qr`)
    showSuccessMessage('Código QR generado correctamente')
    await loadTables()
  } catch (err) {
    console.error('❌ Error generando QR:', err)
    error.value = 'Error al generar el código QR'
  } finally {
    generatingQR.value = null
  }
}

/**
 * Obtiene la URL de la Customer App para una mesa específica
 */
function getCustomerAppUrl(table) {
  return `${CUSTOMER_APP_URL}/${table.table_number}`
}

/**
 * Muestra el modal con el QR de una mesa
 */
function viewQR(table) {
  selectedTable.value = table
  showQRModal.value = true
}

/**
 * Copia la URL de la mesa al portapapeles
 */
async function copyUrl(table) {
  const url = getCustomerAppUrl(table)
  try {
    await navigator.clipboard.writeText(url)
    showSuccessMessage('URL copiada al portapapeles')
  } catch (err) {
    console.error('Error copiando URL:', err)
    // Fallback para navegadores antiguos
    const input = document.createElement('input')
    input.value = url
    document.body.appendChild(input)
    input.select()
    document.execCommand('copy')
    document.body.removeChild(input)
    showSuccessMessage('URL copiada al portapapeles')
  }
}

/**
 * Descarga el código QR como imagen
 */
async function downloadQR(table) {
  if (!table.qr_code_url) return

  try {
    // Crear enlace temporal para descarga
    const link = document.createElement('a')
    link.href = table.qr_code_url
    link.download = `mesa-${table.table_number}-qr.png`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)

    showSuccessMessage('Código QR descargado')
  } catch (err) {
    console.error('Error descargando QR:', err)
    error.value = 'Error al descargar el código QR'
  }
}

/**
 * Imprime el código QR
 */
function printQR(table) {
  if (!table.qr_code_url) return

  const printWindow = window.open('', '_blank')
  printWindow.document.write(`
    <!DOCTYPE html>
    <html>
      <head>
        <title>Mesa ${table.table_number} - Código QR</title>
        <style>
          body {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            margin: 0;
            font-family: Arial, sans-serif;
          }
          h1 { margin-bottom: 2rem; }
          img { max-width: 400px; border: 2px solid #333; }
          p { margin-top: 2rem; font-size: 0.9rem; color: #666; }
        </style>
      </head>
      <body>
        <h1>Mesa ${table.table_number}</h1>
        <img src="${table.qr_code_url}" alt="QR Code">
        <p>Escanea este código para acceder al menú</p>
      </body>
    </html>
  `)
  printWindow.document.close()
  printWindow.print()
}

/**
 * Cierra todos los modales
 */
function closeModals() {
  showCreateModal.value = false
  showEditModal.value = false
  formError.value = null
  tableForm.value = {
    table_number: null,
    capacity: 4,
    location: '',
    description: '',
    is_active: true
  }
}

/**
 * Muestra mensaje de éxito temporal
 */
function showSuccessMessage(message) {
  successMessage.value = message
  setTimeout(() => {
    successMessage.value = null
  }, 3000)
}
</script>

<style scoped>
.table-management {
  max-width: 1400px;
  margin: 0 auto;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
  padding-bottom: 1rem;
  border-bottom: 3px solid #3498db;
}

.header h1 {
  color: #2c3e50;
  margin: 0;
  font-size: 2rem;
}

.loading {
  text-align: center;
  padding: 4rem;
}

.spinner {
  width: 60px;
  height: 60px;
  margin: 0 auto 1rem;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #3498db;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.empty-state {
  text-align: center;
  padding: 4rem;
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.empty-state p {
  font-size: 1.3rem;
  color: #7f8c8d;
  margin-bottom: 2rem;
}

.tables-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: 1.5rem;
}

.table-card {
  background: white;
  border-radius: 12px;
  padding: 1.5rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  transition: transform 0.2s, box-shadow 0.2s;
  border-left: 6px solid #27ae60;
}

.table-card.inactive {
  border-left-color: #e74c3c;
  opacity: 0.7;
}

.table-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 16px rgba(0, 0, 0, 0.15);
}

.table-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
  padding-bottom: 0.75rem;
  border-bottom: 2px solid #ecf0f1;
}

.table-header h3 {
  margin: 0;
  color: #2c3e50;
  font-size: 1.5rem;
}

.status-badge {
  padding: 0.25rem 0.75rem;
  border-radius: 12px;
  font-size: 0.85rem;
  font-weight: 600;
  color: white;
}

.status-badge.active {
  background: #27ae60;
}

.status-badge.inactive {
  background: #e74c3c;
}

.table-body {
  margin-bottom: 1rem;
}

.table-body p {
  margin: 0.5rem 0;
  color: #555;
}

.description {
  font-style: italic;
  color: #7f8c8d;
  font-size: 0.9rem;
}

.qr-section {
  margin-top: 1rem;
  padding: 1rem;
  background: #f8f9fa;
  border-radius: 8px;
}

.qr-label {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
  font-weight: 600;
  color: #2c3e50;
}

.qr-url {
  display: flex;
  gap: 0.5rem;
}

.url-input {
  flex: 1;
  padding: 0.5rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 0.85rem;
  font-family: 'Courier New', monospace;
}

.btn-copy {
  padding: 0.5rem 1rem;
  background: #3498db;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 1rem;
}

.btn-copy:hover {
  background: #2980b9;
}

.qr-missing {
  margin-top: 1rem;
  padding: 1rem;
  background: #fff3cd;
  border: 1px solid #ffc107;
  border-radius: 8px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.table-actions {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.table-actions button {
  flex: 1;
  min-width: 100px;
}

/* Botones */
.btn-primary, .btn-secondary, .btn-edit, .btn-toggle, .btn-download, .btn-icon {
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-primary {
  background: linear-gradient(135deg, #3498db 0%, #2980b9 100%);
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: linear-gradient(135deg, #2980b9 0%, #21618c 100%);
  transform: translateY(-2px);
}

.btn-primary:disabled {
  background: #bdc3c7;
  cursor: not-allowed;
}

.btn-secondary {
  background: #95a5a6;
  color: white;
}

.btn-secondary:hover {
  background: #7f8c8d;
}

.btn-edit {
  background: #f39c12;
  color: white;
}

.btn-edit:hover {
  background: #e67e22;
}

.btn-toggle {
  background: #e74c3c;
  color: white;
}

.btn-toggle:hover {
  background: #c0392b;
}

.btn-download {
  background: #27ae60;
  color: white;
}

.btn-download:hover {
  background: #229954;
}

.btn-icon {
  padding: 0.5rem;
  background: #3498db;
  color: white;
  font-size: 1.2rem;
}

.btn-icon:hover {
  background: #2980b9;
}

/* Modales */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal {
  background: white;
  border-radius: 12px;
  max-width: 500px;
  width: 90%;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
}

.modal.qr-modal {
  max-width: 600px;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem;
  border-bottom: 2px solid #ecf0f1;
}

.modal-header h2 {
  margin: 0;
  color: #2c3e50;
}

.btn-close {
  background: none;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  color: #7f8c8d;
  padding: 0.5rem;
  border-radius: 4px;
}

.btn-close:hover {
  background: #ecf0f1;
  color: #2c3e50;
}

.modal-body {
  padding: 1.5rem;
}

.form-group {
  margin-bottom: 1.5rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 600;
  color: #2c3e50;
}

.form-input, .form-textarea {
  width: 100%;
  padding: 0.75rem;
  border: 2px solid #ecf0f1;
  border-radius: 8px;
  font-size: 1rem;
  transition: border-color 0.2s;
}

.form-input:focus, .form-textarea:focus {
  outline: none;
  border-color: #3498db;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
}

.checkbox-label input[type="checkbox"] {
  width: 20px;
  height: 20px;
  cursor: pointer;
}

.form-error {
  padding: 1rem;
  background: #f8d7da;
  border: 2px solid #e74c3c;
  border-radius: 8px;
  color: #721c24;
  margin-bottom: 1rem;
}

.modal-footer {
  display: flex;
  gap: 1rem;
  justify-content: flex-end;
  padding: 1.5rem;
  border-top: 2px solid #ecf0f1;
}

/* QR Display */
.qr-display {
  text-align: center;
}

.qr-image-container {
  background: #f8f9fa;
  padding: 2rem;
  border-radius: 12px;
  margin-bottom: 1.5rem;
}

.qr-image {
  max-width: 300px;
  width: 100%;
  border: 4px solid #2c3e50;
  border-radius: 8px;
}

.qr-info {
  margin-bottom: 1.5rem;
}

.qr-title {
  font-size: 1.1rem;
  color: #555;
  margin-bottom: 1rem;
}

.qr-url-display {
  background: #f8f9fa;
  padding: 1rem;
  border-radius: 8px;
  border: 1px solid #ddd;
}

.qr-url-display code {
  font-family: 'Courier New', monospace;
  font-size: 0.9rem;
  color: #2c3e50;
  word-break: break-all;
}

.qr-actions {
  display: flex;
  gap: 0.5rem;
  justify-content: center;
  flex-wrap: wrap;
}

/* Toast notifications */
.toast {
  position: fixed;
  bottom: 2rem;
  right: 2rem;
  padding: 1rem 2rem;
  border-radius: 8px;
  color: white;
  font-weight: 600;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
  animation: slideIn 0.3s ease-out;
  z-index: 2000;
}

@keyframes slideIn {
  from {
    transform: translateX(100%);
    opacity: 0;
  }
  to {
    transform: translateX(0);
    opacity: 1;
  }
}

.toast.success {
  background: #27ae60;
}

.toast.error {
  background: #e74c3c;
}

/* Responsive */
@media (max-width: 768px) {
  .header {
    flex-direction: column;
    gap: 1rem;
    align-items: flex-start;
  }

  .tables-grid {
    grid-template-columns: 1fr;
  }

  .table-actions {
    flex-direction: column;
  }

  .table-actions button {
    width: 100%;
  }

  .modal {
    width: 95%;
    max-height: 95vh;
  }

  .modal-footer {
    flex-direction: column;
  }

  .modal-footer button {
    width: 100%;
  }

  .qr-actions {
    flex-direction: column;
  }

  .qr-actions button {
    width: 100%;
  }
}
</style>
