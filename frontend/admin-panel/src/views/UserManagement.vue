<template>
  <div class="user-management">
    <!-- Header -->
    <div class="page-header">
      <div>
        <h1>👥 Gestión de Usuarios</h1>
        <p class="subtitle">Administra usuarios y permisos del sistema</p>
      </div>
      <button @click="openAddUser" class="btn-primary">
        + Nuevo Usuario
      </button>
    </div>

    <!-- Loading/Error -->
    <div v-if="loading" class="loading">Cargando...</div>
    <div v-else-if="error" class="error">{{ error }}</div>

    <!-- Users Table -->
    <div v-else class="users-table-container">
      <table class="users-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>Usuario</th>
            <th>Email</th>
            <th>Rol</th>
            <th>Estado</th>
            <th>Creado</th>
            <th>Acciones</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="user in users" :key="user.id" :class="{ inactive: !user.is_active }">
            <td>{{ user.id }}</td>
            <td>
              <div class="user-cell">
                <span class="user-icon">{{ getRoleIcon(user.role) }}</span>
                <span class="user-name">{{ user.username }}</span>
              </div>
            </td>
            <td>{{ user.email }}</td>
            <td>
              <span class="role-badge" :class="`role-${user.role?.toLowerCase()}`">
                {{ getRoleName(user.role) }}
              </span>
            </td>
            <td>
              <span class="status-badge" :class="user.is_active ? 'active' : 'inactive'">
                {{ user.is_active ? 'Activo' : 'Inactivo' }}
              </span>
            </td>
            <td class="date-cell">{{ formatDate(user.created_at) }}</td>
            <td>
              <div class="actions">
                <button @click="openEditUser(user)" class="btn-action edit" title="Editar">
                  ✏️
                </button>
                <button @click="toggleUserStatus(user)" class="btn-action toggle" title="Activar/Desactivar">
                  {{ user.is_active ? '🚫' : '✅' }}
                </button>
                <button @click="confirmDelete(user)" class="btn-action delete" title="Eliminar">
                  🗑️
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- User Modal (Add/Edit) -->
    <Transition name="modal">
      <div v-if="showUserModal" class="modal-overlay" @click="closeUserModal">
        <div class="modal-content" @click.stop>
          <div class="modal-header">
            <h2>{{ editingUser ? '✏️ Editar Usuario' : '➕ Nuevo Usuario' }}</h2>
            <button @click="closeUserModal" class="btn-close">✕</button>
          </div>
          <form @submit.prevent="saveUser" class="form">
            <div class="form-group">
              <label>Nombre de Usuario *</label>
              <input v-model="userForm.username" required />
            </div>
            <div class="form-group">
              <label>Email *</label>
              <input v-model="userForm.email" type="email" required />
            </div>
            <div v-if="!editingUser" class="form-group">
              <label>Contraseña *</label>
              <input v-model="userForm.password" type="password" required />
            </div>
            <div class="form-group">
              <label>Rol *</label>
              <select v-model="userForm.role" required>
                <option value="">Seleccionar...</option>
                <option value="admin">Administrador</option>
                <option value="waiter">Mesero</option>
                <option value="cook">Cocinero</option>
                <option value="cashier">Cajero</option>
              </select>
            </div>
            <div class="form-group checkbox">
              <label>
                <input v-model="userForm.is_active" type="checkbox" />
                Usuario activo
              </label>
            </div>
            <div class="form-actions">
              <button type="button" @click="closeUserModal" class="btn-cancel">
                Cancelar
              </button>
              <button type="submit" class="btn-save">
                {{ editingUser ? 'Guardar Cambios' : 'Crear Usuario' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'

const users = ref([])
const loading = ref(false)
const error = ref(null)

const showUserModal = ref(false)
const editingUser = ref(null)

const userForm = ref({
  username: '',
  email: '',
  password: '',
  role: '',
  is_active: true
})

function getRoleIcon(role) {
  const icons = {
    admin: '👑',
    waiter: '🧑‍💼',
    cook: '👨‍🍳',
    cashier: '💰'
  }
  return icons[role?.toLowerCase()] || '👤'
}

function getRoleName(role) {
  const names = {
    admin: 'Administrador',
    waiter: 'Mesero',
    cook: 'Cocinero',
    cashier: 'Cajero'
  }
  return names[role?.toLowerCase()] || role
}

function formatDate(dateString) {
  if (!dateString) return '-'
  const date = new Date(dateString)
  return date.toLocaleDateString('es-ES', {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  })
}

function openAddUser() {
  editingUser.value = null
  userForm.value = {
    username: '',
    email: '',
    password: '',
    role: '',
    is_active: true
  }
  showUserModal.value = true
}

function openEditUser(user) {
  editingUser.value = user
  userForm.value = {
    username: user.username,
    email: user.email,
    password: '', // Don't show password
    role: user.role,
    is_active: user.is_active
  }
  showUserModal.value = true
}

function closeUserModal() {
  showUserModal.value = false
  editingUser.value = null
}

async function saveUser() {
  try {
    const payload = {
      username: userForm.value.username,
      email: userForm.value.email,
      role: userForm.value.role,
      is_active: userForm.value.is_active
    }

    // Include password only for new users or if changed
    if (!editingUser.value && userForm.value.password) {
      payload.password = userForm.value.password
    }

    if (editingUser.value) {
      await axios.put(
        `/api/v1/users/${editingUser.value.id}`,
        payload
      )
    } else {
      await axios.post('/api/v1/users', {
        ...payload,
        password: userForm.value.password
      })
    }
    await loadData()
    closeUserModal()
  } catch (err) {
    alert('Error al guardar usuario: ' + err.message)
  }
}

async function toggleUserStatus(user) {
  try {
    await axios.put(
      `/api/v1/users/${user.id}`,
      { ...user, is_active: !user.is_active }
    )
    user.is_active = !user.is_active
  } catch (err) {
    alert('Error al actualizar estado: ' + err.message)
  }
}

async function confirmDelete(user) {
  if (!confirm(`¿Eliminar usuario "${user.username}"?`)) return

  try {
    await axios.delete(`/api/v1/users/${user.id}`)
    await loadData()
  } catch (err) {
    alert('Error al eliminar usuario: ' + err.message)
  }
}

async function loadData() {
  loading.value = true
  error.value = null

  try {
    const response = await axios.get('/api/v1/users')
    users.value = response.data
  } catch (err) {
    error.value = 'Error al cargar usuarios. El servicio auth podría no estar disponible.'
    console.error(err)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.user-management {
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

.btn-primary {
  padding: 0.75rem 1.5rem;
  background: linear-gradient(135deg, #27ae60 0%, #229954 100%);
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 600;
  transition: all 0.3s;
}

.btn-primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(39, 174, 96, 0.3);
}

/* Table */
.users-table-container {
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.users-table {
  width: 100%;
  border-collapse: collapse;
}

.users-table thead {
  background: linear-gradient(135deg, #34495e 0%, #2c3e50 100%);
  color: white;
}

.users-table th {
  padding: 1rem;
  text-align: left;
  font-weight: 600;
}

.users-table tbody tr {
  border-bottom: 1px solid #e0e0e0;
  transition: background 0.2s;
}

.users-table tbody tr:hover {
  background: #f8f9fa;
}

.users-table tbody tr.inactive {
  opacity: 0.6;
}

.users-table td {
  padding: 1rem;
  color: #2c3e50;
}

.user-cell {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.user-icon {
  font-size: 1.5rem;
}

.user-name {
  font-weight: 600;
}

.role-badge {
  display: inline-block;
  padding: 0.25rem 0.75rem;
  border-radius: 12px;
  font-size: 0.85rem;
  font-weight: 600;
  text-transform: uppercase;
}

.role-badge.role-admin {
  background: #e74c3c;
  color: white;
}

.role-badge.role-waiter {
  background: #3498db;
  color: white;
}

.role-badge.role-cook {
  background: #f39c12;
  color: white;
}

.role-badge.role-cashier {
  background: #27ae60;
  color: white;
}

.status-badge {
  display: inline-block;
  padding: 0.25rem 0.75rem;
  border-radius: 12px;
  font-size: 0.85rem;
  font-weight: 600;
}

.status-badge.active {
  background: #27ae60;
  color: white;
}

.status-badge.inactive {
  background: #95a5a6;
  color: white;
}

.date-cell {
  color: #7f8c8d;
  font-size: 0.9rem;
}

.actions {
  display: flex;
  gap: 0.5rem;
}

.btn-action {
  padding: 0.5rem;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 1rem;
  transition: all 0.3s;
}

.btn-action.edit {
  background: #3498db;
}

.btn-action.toggle {
  background: #f39c12;
}

.btn-action.delete {
  background: #e74c3c;
}

.btn-action:hover {
  transform: scale(1.1);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
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
  max-width: 500px;
  width: 100%;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
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

.form {
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
.form-group select {
  width: 100%;
  padding: 0.75rem;
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  font-size: 1rem;
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

  .users-table-container {
    overflow-x: auto;
  }

  .users-table {
    min-width: 800px;
  }
}
</style>
