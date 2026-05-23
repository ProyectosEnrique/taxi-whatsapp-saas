<template>
  <div id="app">
    <aside class="sidebar">
      <h2>Admin Panel</h2>
      <nav>
        <router-link to="/">Dashboard</router-link>
        <router-link to="/menu">Gestion de Menu</router-link>
        <router-link to="/promotions">Promociones</router-link>
        <router-link to="/tables">Gestion de Mesas</router-link>
        <router-link to="/users">Usuarios</router-link>
        <router-link to="/security" class="nav-security">Seguridad IoT</router-link>
        <router-link to="/iot" class="nav-iot">Sensores IoT</router-link>
        <router-link to="/notes" class="nav-highlight">Notas y Recordatorios</router-link>
        <router-link to="/whatsapp" class="nav-whatsapp">WhatsApp</router-link>
      </nav>
    </aside>
    <main class="content">
      <router-view />
    </main>
    <!-- Asistente Administrativo con Voz - Solo en páginas sin su propio asistente -->
    <AdminAssistant v-if="showAdminAssistant" />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import AdminAssistant from './components/AdminAssistant.vue'

const route = useRoute()

// Ocultar AdminAssistant en páginas que tienen su propio asistente especializado
const pagesWithOwnAssistant = ['/security', '/iot']
const showAdminAssistant = computed(() => !pagesWithOwnAssistant.includes(route.path))
</script>

<style scoped>
#app {
  display: flex;
  min-height: 100vh;
}

.sidebar {
  width: 250px;
  background: #2c3e50;
  color: white;
  padding: 2rem 1rem;
}

nav {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  margin-top: 2rem;
}

nav a {
  color: white;
  text-decoration: none;
  padding: 0.5rem;
  border-radius: 4px;
}

nav a:hover {
  background: #34495e;
}

nav a.nav-security {
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
  border: 1px solid #27ae60;
  border-radius: 6px;
  margin-top: 1rem;
  padding-top: 0.75rem;
  padding-bottom: 0.75rem;
}

nav a.nav-security::before {
  content: '🛡️ ';
}

nav a.nav-security:hover {
  background: linear-gradient(135deg, #16213e 0%, #1a1a2e 100%);
  border-color: #2ecc71;
}

nav a.nav-iot {
  background: linear-gradient(135deg, #1e3a5f 0%, #2980b9 100%);
  border: 1px solid #3498db;
  border-radius: 6px;
  margin-top: 0.5rem;
  padding-top: 0.75rem;
  padding-bottom: 0.75rem;
}

nav a.nav-iot::before {
  content: '📡 ';
}

nav a.nav-iot:hover {
  background: linear-gradient(135deg, #2980b9 0%, #1e3a5f 100%);
  border-color: #5dade2;
}

nav a.nav-highlight {
  background: linear-gradient(135deg, #2d5a27 0%, #4a7c45 100%);
  border-radius: 6px;
  margin-top: 0.5rem;
  padding-top: 0.75rem;
  padding-bottom: 0.75rem;
}

nav a.nav-highlight::before {
  content: '📝 ';
}

nav a.nav-whatsapp {
  background: linear-gradient(135deg, #128c7e 0%, #25d366 100%);
  border: 1px solid #25d366;
  border-radius: 6px;
  margin-top: 0.5rem;
  padding-top: 0.75rem;
  padding-bottom: 0.75rem;
}

nav a.nav-whatsapp::before {
  content: '📱 ';
}

nav a.nav-whatsapp:hover {
  background: linear-gradient(135deg, #25d366 0%, #128c7e 100%);
  border-color: #34e87e;
  box-shadow: 0 4px 12px rgba(37, 211, 102, 0.3);
}

.content {
  flex: 1;
  padding: 2rem;
  background: #ecf0f1;
}
</style>
