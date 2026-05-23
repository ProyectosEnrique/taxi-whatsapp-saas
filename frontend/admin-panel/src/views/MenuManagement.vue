<template>
  <div class="menu-management">
    <!-- Header -->
    <div class="page-header">
      <div>
        <h1>🍽️ Gestión de Menú</h1>
        <p class="subtitle">Administra productos y categorías</p>
      </div>
      <div class="header-actions">
        <button @click="showCategoryModal = true" class="btn-secondary">
          + Nueva Categoría
        </button>
        <button @click="openAddProduct" class="btn-primary">
          + Nuevo Producto
        </button>
      </div>
    </div>

    <!-- Loading/Error -->
    <div v-if="loading" class="loading">Cargando...</div>
    <div v-else-if="error" class="error">{{ error }}</div>

    <!-- Categories Tabs -->
    <div v-else>
      <div class="categories-tabs">
        <button
          @click="selectedCategory = null"
          :class="{ active: selectedCategory === null }"
          class="tab-btn">
          Todos ({{ products.length }})
        </button>
        <button
          v-for="category in categories"
          :key="category.id"
          @click="selectedCategory = category.id"
          :class="{ active: selectedCategory === category.id }"
          class="tab-btn">
          {{ category.icon }} {{ category.name }} ({{ getProductCount(category.id) }})
        </button>
      </div>

      <!-- Products Grid -->
      <div class="products-grid">
        <div
          v-for="product in filteredProducts"
          :key="product.id"
          class="product-card"
          :class="{ unavailable: !product.is_available }">
          <div class="product-image">
            <img
              v-if="product.image_url"
              :src="`http://localhost:5011${product.image_url}`"
              :alt="product.name"
              @error="handleImageLoadError" />
            <div v-else class="no-image">🍽️</div>
            <div v-if="!product.is_available" class="unavailable-badge">
              No Disponible
            </div>
          </div>
          <div class="product-info">
            <h3>{{ product.name }}</h3>
            <p class="description">{{ product.description }}</p>
            <div class="product-meta">
              <span class="price">${{ parseFloat(product.price).toFixed(2) }}</span>
              <span class="category-badge">
                {{ getCategoryName(product.category_id) }}
              </span>
            </div>
            <div v-if="product.preparation_time" class="extra-info">
              ⏱️ {{ product.preparation_time }} min
              <span v-if="product.calories">| 🔥 {{ product.calories }} cal</span>
              <span v-if="product.is_vegetarian">| 🌱 Vegetariano</span>
            </div>
            <div v-if="product.ingredients" class="ingredients-info">
              🥗 {{ product.ingredients }}
            </div>
          </div>
          <div class="product-actions">
            <button @click="openEditProduct(product)" class="btn-edit">
              ✏️ Editar
            </button>
            <button @click="toggleAvailability(product)" class="btn-toggle">
              {{ product.is_available ? '🚫 Desactivar' : '✅ Activar' }}
            </button>
            <button @click="confirmDelete(product)" class="btn-delete">
              🗑️ Eliminar
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Product Modal (Add/Edit) -->
    <Transition name="modal">
      <div v-if="showProductModal" class="modal-overlay" @click="closeProductModal">
        <div class="modal-content" @click.stop>
          <div class="modal-header">
            <h2>{{ editingProduct ? '✏️ Editar Producto' : '➕ Nuevo Producto' }}</h2>
            <button @click="closeProductModal" class="btn-close">✕</button>
          </div>
          <form @submit.prevent="saveProduct" class="product-form">
            <div class="form-group">
              <label>Nombre *</label>
              <input v-model="productForm.name" required />
            </div>
            <div class="form-group">
              <label>Descripción</label>
              <textarea v-model="productForm.description" rows="3"></textarea>
            </div>
            <div class="form-row">
              <div class="form-group">
                <label>Precio *</label>
                <input v-model.number="productForm.price" type="number" step="0.01" min="0" required />
              </div>
              <div class="form-group">
                <label>Categoría *</label>
                <select v-model="productForm.category_id" required>
                  <option value="">Seleccionar...</option>
                  <option v-for="cat in categories" :key="cat.id" :value="cat.id">
                    {{ cat.name }}
                  </option>
                </select>
              </div>
            </div>
            <div class="form-row">
              <div class="form-group">
                <label>Tiempo de Preparación (min)</label>
                <input v-model.number="productForm.preparation_time" type="number" min="0" />
              </div>
              <div class="form-group">
                <label>Calorías</label>
                <input v-model.number="productForm.calories" type="number" min="0" />
              </div>
            </div>
            <div class="form-group">
              <label>Imagen del Producto</label>
              <ImageUploader
                v-model="productForm.image_url"
                @upload-success="handleImageUpload"
                @upload-error="handleImageError"
              />
            </div>
            <div class="form-group">
              <label>Ingredientes</label>
              <textarea
                v-model="productForm.ingredients"
                rows="2"
                placeholder="cebolla, cilantro, queso, crema (separados por coma)"
              ></textarea>
              <small class="form-hint">Lista de ingredientes separados por coma. Se usarán para los modificadores (sin/extra).</small>
            </div>
            <div class="form-group checkbox">
              <label>
                <input v-model="productForm.is_vegetarian" type="checkbox" />
                Vegetariano
              </label>
            </div>
            <div class="form-group checkbox">
              <label>
                <input v-model="productForm.is_available" type="checkbox" />
                Disponible
              </label>
            </div>
            <div class="form-actions">
              <button type="button" @click="closeProductModal" class="btn-cancel">
                Cancelar
              </button>
              <button type="submit" class="btn-save">
                {{ editingProduct ? 'Guardar Cambios' : 'Crear Producto' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </Transition>

    <!-- Category Modal -->
    <Transition name="modal">
      <div v-if="showCategoryModal" class="modal-overlay" @click="showCategoryModal = false">
        <div class="modal-content small" @click.stop>
          <div class="modal-header">
            <h2>➕ Nueva Categoría</h2>
            <button @click="showCategoryModal = false" class="btn-close">✕</button>
          </div>
          <form @submit.prevent="saveCategory" class="product-form">
            <div class="form-group">
              <label>Nombre *</label>
              <input v-model="categoryForm.name" required />
            </div>
            <div class="form-group">
              <label>Descripción</label>
              <textarea v-model="categoryForm.description" rows="2"></textarea>
            </div>
            <div class="form-group">
              <label>Icono (emoji)</label>
              <input v-model="categoryForm.icon" placeholder="🍕" />
            </div>
            <div class="form-actions">
              <button type="button" @click="showCategoryModal = false" class="btn-cancel">
                Cancelar
              </button>
              <button type="submit" class="btn-save">
                Crear Categoría
              </button>
            </div>
          </form>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import axios from 'axios'
import ImageUploader from '../components/ImageUploader.vue'

const products = ref([])
const categories = ref([])
const loading = ref(false)
const error = ref(null)

const selectedCategory = ref(null)
const showProductModal = ref(false)
const showCategoryModal = ref(false)
const editingProduct = ref(null)

const productForm = ref({
  name: '',
  description: '',
  price: 0,
  category_id: '',
  preparation_time: null,
  calories: null,
  image_url: '',
  ingredients: '',
  is_vegetarian: false,
  is_available: true
})

const categoryForm = ref({
  name: '',
  description: '',
  icon: ''
})

const filteredProducts = computed(() => {
  if (!selectedCategory.value) return products.value
  return products.value.filter(p => p.category_id === selectedCategory.value)
})

function getCategoryName(categoryId) {
  const category = categories.value.find(c => c.id === categoryId)
  return category ? category.name : 'Sin categoría'
}

function getProductCount(categoryId) {
  return products.value.filter(p => p.category_id === categoryId).length
}

function openAddProduct() {
  editingProduct.value = null
  productForm.value = {
    name: '',
    description: '',
    price: 0,
    category_id: '',
    preparation_time: null,
    calories: null,
    image_url: '',
    ingredients: '',
    is_vegetarian: false,
    is_available: true
  }
  showProductModal.value = true
}

function openEditProduct(product) {
  editingProduct.value = product
  productForm.value = { ...product }
  showProductModal.value = true
}

function closeProductModal() {
  showProductModal.value = false
  editingProduct.value = null
}

async function saveProduct() {
  try {
    if (editingProduct.value) {
      await axios.put(
        `http://localhost:5011/api/v1/products/${editingProduct.value.id}`,
        productForm.value
      )
    } else {
      await axios.post('http://localhost:5011/api/v1/products', productForm.value)
    }
    await loadData()
    closeProductModal()
  } catch (err) {
    alert('Error al guardar producto: ' + err.message)
  }
}

async function toggleAvailability(product) {
  try {
    await axios.put(`http://localhost:5011/api/v1/products/${product.id}`, {
      ...product,
      is_available: !product.is_available
    })
    product.is_available = !product.is_available
  } catch (err) {
    alert('Error al actualizar disponibilidad: ' + err.message)
  }
}

async function confirmDelete(product) {
  if (!confirm(`¿Eliminar "${product.name}"?`)) return

  try {
    await axios.delete(`http://localhost:5011/api/v1/products/${product.id}`)
    await loadData()
  } catch (err) {
    alert('Error al eliminar producto: ' + err.message)
  }
}

async function saveCategory() {
  try {
    await axios.post('http://localhost:5011/api/v1/categories', categoryForm.value)
    await loadData()
    showCategoryModal.value = false
    categoryForm.value = { name: '', description: '', icon: '' }
  } catch (err) {
    alert('Error al crear categoría: ' + err.message)
  }
}

function handleImageLoadError(event) {
  event.target.style.display = 'none'
}

function handleImageUpload(data) {
  console.log('Imagen subida exitosamente:', data)
  // La URL ya se actualiza automáticamente via v-model
}

function handleImageError(errorMessage) {
  console.error('Error subiendo imagen:', errorMessage)
  alert('Error al subir imagen: ' + errorMessage)
}

async function loadData() {
  loading.value = true
  error.value = null

  try {
    const [productsRes, categoriesRes] = await Promise.all([
      axios.get('http://localhost:5011/api/v1/products'),
      axios.get('http://localhost:5011/api/v1/categories')
    ])
    products.value = productsRes.data
    categories.value = categoriesRes.data
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.menu-management {
  min-height: 100vh;
}

/* Header */
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
  padding: 1.5rem;
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.page-header h1 {
  margin: 0;
  color: #2c3e50;
}

.subtitle {
  margin: 0.25rem 0 0 0;
  color: #7f8c8d;
}

.header-actions {
  display: flex;
  gap: 1rem;
}

.btn-primary,
.btn-secondary {
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 600;
  transition: all 0.3s;
}

.btn-primary {
  background: linear-gradient(135deg, #27ae60 0%, #229954 100%);
  color: white;
}

.btn-secondary {
  background: linear-gradient(135deg, #3498db 0%, #2980b9 100%);
  color: white;
}

.btn-primary:hover,
.btn-secondary:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
}

/* Categories Tabs */
.categories-tabs {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 2rem;
  overflow-x: auto;
  padding: 0.5rem;
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.tab-btn {
  padding: 0.75rem 1.5rem;
  background: #f8f9fa;
  border: 2px solid transparent;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 600;
  white-space: nowrap;
  transition: all 0.3s;
  color: #7f8c8d;
}

.tab-btn.active {
  background: linear-gradient(135deg, #3498db 0%, #2980b9 100%);
  color: white;
  border-color: #2980b9;
}

/* Products Grid */
.products-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 1.5rem;
}

.product-card {
  background: white;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  transition: all 0.3s;
}

.product-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
}

.product-card.unavailable {
  opacity: 0.6;
}

.product-image {
  height: 180px;
  position: relative;
  background: #f8f9fa;
  overflow: hidden;
}

.product-image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.no-image {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 4rem;
}

.unavailable-badge {
  position: absolute;
  top: 10px;
  right: 10px;
  background: #e74c3c;
  color: white;
  padding: 0.25rem 0.75rem;
  border-radius: 12px;
  font-size: 0.8rem;
  font-weight: 600;
}

.product-info {
  padding: 1rem;
}

.product-info h3 {
  margin: 0 0 0.5rem 0;
  color: #2c3e50;
}

.description {
  font-size: 0.9rem;
  color: #7f8c8d;
  margin: 0 0 1rem 0;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.product-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}

.price {
  font-size: 1.5rem;
  font-weight: bold;
  color: #27ae60;
}

.category-badge {
  background: #ecf0f1;
  padding: 0.25rem 0.75rem;
  border-radius: 12px;
  font-size: 0.8rem;
  color: #7f8c8d;
}

.extra-info {
  font-size: 0.85rem;
  color: #95a5a6;
}

.ingredients-info {
  font-size: 0.8rem;
  color: #7f8c8d;
  margin-top: 0.5rem;
  font-style: italic;
}

.product-actions {
  display: flex;
  gap: 0.5rem;
  padding: 1rem;
  background: #f8f9fa;
  border-top: 1px solid #e0e0e0;
}

.btn-edit,
.btn-toggle,
.btn-delete {
  flex: 1;
  padding: 0.5rem;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.85rem;
  font-weight: 600;
  transition: all 0.3s;
}

.btn-edit {
  background: #3498db;
  color: white;
}

.btn-toggle {
  background: #f39c12;
  color: white;
}

.btn-delete {
  background: #e74c3c;
  color: white;
}

/* Modal */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 2rem;
}

.modal-content {
  background: white;
  border-radius: 16px;
  max-width: 600px;
  width: 100%;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
}

.modal-content.small {
  max-width: 400px;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem 2rem;
  border-bottom: 2px solid #e0e0e0;
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
}

.product-form {
  padding: 2rem;
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

.form-group input,
.form-group select,
.form-group textarea {
  width: 100%;
  padding: 0.75rem;
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  font-size: 1rem;
}

.form-hint {
  display: block;
  font-size: 0.75rem;
  color: #7f8c8d;
  margin-top: 0.25rem;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

.form-group.checkbox label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.form-group.checkbox input {
  width: auto;
}

.form-actions {
  display: flex;
  gap: 1rem;
  margin-top: 2rem;
}

.btn-cancel,
.btn-save {
  flex: 1;
  padding: 0.75rem;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 600;
  font-size: 1rem;
}

.btn-cancel {
  background: #95a5a6;
  color: white;
}

.btn-save {
  background: linear-gradient(135deg, #27ae60 0%, #229954 100%);
  color: white;
}

/* Transitions */
.modal-enter-active,
.modal-leave-active {
  transition: all 0.3s;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 1rem;
  }

  .header-actions {
    width: 100%;
    flex-direction: column;
  }

  .products-grid {
    grid-template-columns: 1fr;
  }

  .form-row {
    grid-template-columns: 1fr;
  }
}
</style>
