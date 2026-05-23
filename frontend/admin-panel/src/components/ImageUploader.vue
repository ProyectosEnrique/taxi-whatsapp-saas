<template>
  <div class="image-uploader">
    <!-- Preview de imagen -->
    <div class="preview-container" @click="triggerFileInput">
      <div v-if="uploading" class="uploading-overlay">
        <div class="spinner"></div>
        <p>Subiendo... {{ uploadProgress }}%</p>
      </div>

      <img
        v-else-if="displayUrl"
        :src="displayUrl"
        alt="Preview"
        class="preview-image" />

      <div v-else class="placeholder">
        <div class="icon">📸</div>
        <p>Click o arrastra una imagen aquí</p>
        <small>Máximo 5MB (JPG, PNG, GIF, WEBP)</small>
      </div>

      <!-- Badge si hay cambios sin guardar -->
      <div v-if="hasUnsavedChanges" class="unsaved-badge">
        Sin guardar
      </div>
    </div>

    <!-- Drag & Drop zone -->
    <div
      class="drop-zone"
      :class="{ 'dragging': isDragging, 'has-file': selectedFile }"
      @drop.prevent="onDrop"
      @dragover.prevent="onDragEnter"
      @dragleave="onDragLeave"
      @click="triggerFileInput">

      <input
        ref="fileInput"
        type="file"
        accept="image/*"
        @change="onFileSelect"
        style="display: none" />

      <template v-if="!selectedFile">
        <p class="drop-text">
          <span v-if="isDragging">📥 Suelta la imagen aquí</span>
          <span v-else>📤 Arrastra una imagen o haz click para seleccionar</span>
        </p>
      </template>

      <template v-else>
        <p class="file-info">
          ✅ {{ selectedFile.name }} ({{ formatFileSize(selectedFile.size) }})
        </p>
        <div class="actions">
          <button
            @click.stop="uploadImage"
            :disabled="uploading"
            class="btn-upload">
            ☁️ Subir Imagen
          </button>
          <button
            @click.stop="clearSelection"
            :disabled="uploading"
            class="btn-clear">
            ✕ Cancelar
          </button>
        </div>
      </template>
    </div>

    <!-- Error message -->
    <div v-if="error" class="error-message">
      ⚠️ {{ error }}
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import axios from 'axios'

const props = defineProps({
  modelValue: String,  // URL de imagen existente
  autoUpload: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:modelValue', 'upload-success', 'upload-error'])

// State
const selectedFile = ref(null)
const previewUrl = ref(null)
const isDragging = ref(false)
const uploading = ref(false)
const uploadProgress = ref(0)
const error = ref(null)
const uploadedUrl = ref(null)

// Computed
const displayUrl = computed(() => {
  if (previewUrl.value) return previewUrl.value
  if (uploadedUrl.value) return `http://localhost:5011${uploadedUrl.value}`
  if (props.modelValue) return `http://localhost:5011${props.modelValue}`
  return null
})

const hasUnsavedChanges = computed(() => {
  return selectedFile.value && !uploadedUrl.value
})

// Watchers
watch(() => props.modelValue, (newUrl) => {
  if (newUrl && !uploadedUrl.value) {
    uploadedUrl.value = newUrl
  }
})

// Methods
function triggerFileInput() {
  if (!uploading.value) {
    this.$refs.fileInput?.click()
  }
}

function onDragEnter() {
  isDragging.value = true
}

function onDragLeave() {
  isDragging.value = false
}

function onDrop(event) {
  isDragging.value = false
  const files = event.dataTransfer.files

  if (files.length > 0) {
    handleFile(files[0])
  }
}

function onFileSelect(event) {
  const file = event.target.files[0]
  if (file) {
    handleFile(file)
  }
}

function handleFile(file) {
  error.value = null

  // Validar que sea imagen
  if (!file.type.startsWith('image/')) {
    error.value = 'Por favor selecciona una imagen válida'
    return
  }

  // Validar tamaño (máx 5MB)
  if (file.size > 5 * 1024 * 1024) {
    error.value = 'La imagen es muy grande. Máximo 5MB.'
    return
  }

  selectedFile.value = file

  // Crear preview local
  const reader = new FileReader()
  reader.onload = (e) => {
    previewUrl.value = e.target.result
  }
  reader.readAsDataURL(file)

  // Auto-upload si está habilitado
  if (props.autoUpload) {
    setTimeout(() => uploadImage(), 500)
  }
}

async function uploadImage() {
  if (!selectedFile.value || uploading.value) return

  uploading.value = true
  uploadProgress.value = 0
  error.value = null

  try {
    // Crear FormData
    const formData = new FormData()
    formData.append('file', selectedFile.value)

    // Upload al backend
    const response = await axios.post('http://localhost:5011/api/v1/upload/image', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      },
      onUploadProgress: (progressEvent) => {
        if (progressEvent.total) {
          uploadProgress.value = Math.round(
            (progressEvent.loaded * 100) / progressEvent.total
          )
        }
      }
    })

    // Guardar URL
    uploadedUrl.value = response.data.url

    // Emitir evento de éxito
    emit('update:modelValue', response.data.url)
    emit('upload-success', response.data)

    // Limpiar estado
    setTimeout(() => {
      selectedFile.value = null
      uploadProgress.value = 0
    }, 1000)

  } catch (err) {
    error.value = err.response?.data?.detail || err.message || 'Error al subir imagen'
    emit('upload-error', error.value)
    console.error('Upload error:', err)
  } finally {
    uploading.value = false
  }
}

function clearSelection() {
  selectedFile.value = null
  previewUrl.value = null
  error.value = null

  // Reset file input
  if (this.$refs.fileInput) {
    this.$refs.fileInput.value = ''
  }
}

function formatFileSize(bytes) {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

// Exponer métodos públicos
defineExpose({
  uploadImage,
  clearSelection
})
</script>

<style scoped>
.image-uploader {
  width: 100%;
}

/* Preview Container */
.preview-container {
  width: 100%;
  height: 250px;
  background: #f8f9fa;
  border: 3px dashed #dee2e6;
  border-radius: 12px;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  position: relative;
  transition: all 0.3s;
  margin-bottom: 1rem;
}

.preview-container:hover {
  border-color: #3498db;
  background: #f0f7ff;
}

.preview-image {
  width: 100%;
  height: 100%;
  object-fit: contain;
  background: #000;
}

.placeholder {
  text-align: center;
  color: #6c757d;
  padding: 2rem;
}

.placeholder .icon {
  font-size: 4rem;
  margin-bottom: 1rem;
  opacity: 0.5;
}

.placeholder p {
  font-size: 1.1rem;
  margin: 0.5rem 0;
  font-weight: 600;
}

.placeholder small {
  color: #95a5a6;
  font-size: 0.85rem;
}

.uploading-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.8);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: white;
  z-index: 10;
}

.spinner {
  width: 50px;
  height: 50px;
  border: 4px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 1rem;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.unsaved-badge {
  position: absolute;
  top: 10px;
  right: 10px;
  background: #f39c12;
  color: white;
  padding: 0.5rem 1rem;
  border-radius: 20px;
  font-size: 0.85rem;
  font-weight: 600;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
}

/* Drop Zone */
.drop-zone {
  padding: 2rem;
  background: #f8f9fa;
  border: 2px dashed #bdc3c7;
  border-radius: 12px;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s;
  margin-bottom: 1rem;
}

.drop-zone.dragging {
  background: #e8f4f8;
  border-color: #3498db;
  transform: scale(1.02);
}

.drop-zone.has-file {
  background: #e8f5e9;
  border-color: #27ae60;
}

.drop-zone:hover:not(.dragging) {
  border-color: #7f8c8d;
}

.drop-text {
  margin: 0;
  font-size: 1rem;
  color: #7f8c8d;
  font-weight: 500;
}

.file-info {
  margin: 0 0 1rem 0;
  font-size: 0.95rem;
  color: #27ae60;
  font-weight: 600;
}

.actions {
  display: flex;
  gap: 1rem;
  justify-content: center;
}

.btn-upload,
.btn-clear {
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 600;
  font-size: 0.95rem;
  transition: all 0.3s;
}

.btn-upload {
  background: linear-gradient(135deg, #27ae60 0%, #229954 100%);
  color: white;
}

.btn-upload:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(39, 174, 96, 0.4);
}

.btn-upload:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-clear {
  background: #95a5a6;
  color: white;
}

.btn-clear:hover:not(:disabled) {
  background: #7f8c8d;
}

/* Error Message */
.error-message {
  padding: 1rem;
  background: #fee;
  border: 1px solid #fcc;
  border-radius: 8px;
  color: #c33;
  font-size: 0.9rem;
  margin-top: 1rem;
}

/* Responsive */
@media (max-width: 768px) {
  .preview-container {
    height: 200px;
  }

  .actions {
    flex-direction: column;
  }

  .btn-upload,
  .btn-clear {
    width: 100%;
  }
}
</style>
