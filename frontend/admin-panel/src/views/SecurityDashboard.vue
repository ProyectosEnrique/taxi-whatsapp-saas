<template>
  <div class="security-dashboard">
    <!-- Header -->
    <header class="security-header">
      <div class="header-left">
        <h1>🛡️ Panel de Seguridad IoT</h1>
        <p class="subtitle">Monitoreo en tiempo real de sensores del restaurante</p>
      </div>
      <div class="header-right">
        <div class="connection-status" :class="wsConnected ? 'connected' : 'disconnected'">
          <span class="status-dot"></span>
          {{ wsConnected ? 'Conectado' : 'Desconectado' }}
        </div>
        <div class="last-update" v-if="lastUpdate">
          Actualizado: {{ formatTime(lastUpdate) }}
        </div>
      </div>
    </header>

    <!-- PANEL DE ACCIONES RAPIDAS -->
    <section class="quick-actions-panel">
      <button @click="viewAllCameras" class="action-btn camera-btn">
        <div class="btn-icon">📹</div>
        <div class="btn-content">
          <span class="btn-title">Ver Camaras</span>
          <span class="btn-subtitle">{{ activeCameras }} camaras activas</span>
        </div>
      </button>

      <button @click="silenceAlarms" class="action-btn alarm-btn" :disabled="activeAlerts.length === 0">
        <div class="btn-icon">🔕</div>
        <div class="btn-content">
          <span class="btn-title">Silenciar Alarmas</span>
          <span class="btn-subtitle">{{ activeAlerts.length }} alertas activas</span>
        </div>
      </button>

      <button @click="emergencyProtocol" class="action-btn emergency-btn">
        <div class="btn-icon">🚨</div>
        <div class="btn-content">
          <span class="btn-title">Protocolo Emergencia</span>
          <span class="btn-subtitle">Llamar autoridades</span>
        </div>
      </button>

      <button @click="viewReports" class="action-btn report-btn">
        <div class="btn-icon">📊</div>
        <div class="btn-content">
          <span class="btn-title">Reportes</span>
          <span class="btn-subtitle">Historial & Analytics</span>
        </div>
      </button>
    </section>

    <!-- KPIs IMPACTANTES -->
    <section class="kpi-mega-cards">
      <div class="kpi-card status-kpi" :class="overallStatus.toLowerCase()">
        <div class="kpi-icon">{{ getStatusIcon(overallStatus) }}</div>
        <div class="kpi-data">
          <div class="kpi-label">Estado General</div>
          <div class="kpi-value">{{ overallStatus }}</div>
          <div class="kpi-desc">{{ getStatusDescription(overallStatus) }}</div>
        </div>
      </div>

      <div class="kpi-card devices-kpi">
        <div class="kpi-icon">📡</div>
        <div class="kpi-data">
          <div class="kpi-label">Dispositivos Online</div>
          <div class="kpi-value">{{ onlineDevices }}/{{ totalDevices }}</div>
          <div class="kpi-desc">{{ Math.round((onlineDevices/totalDevices)*100) }}% disponibilidad</div>
        </div>
      </div>

      <div class="kpi-card alerts-kpi">
        <div class="kpi-icon">⚠️</div>
        <div class="kpi-data">
          <div class="kpi-label">Alertas Activas</div>
          <div class="kpi-value">{{ activeAlerts.length }}</div>
          <div class="kpi-desc">{{ criticalAlerts }} criticas</div>
        </div>
      </div>

      <div class="kpi-card savings-kpi">
        <div class="kpi-icon">💰</div>
        <div class="kpi-data">
          <div class="kpi-label">Ahorro Mensual</div>
          <div class="kpi-value">$45K</div>
          <div class="kpi-desc">ROI 300% anual</div>
        </div>
      </div>
    </section>

    <!-- MAPA INTERACTIVO DEL RESTAURANTE -->
    <section class="restaurant-map-section">
      <h3>📍 Mapa del Restaurante</h3>
      <div class="floor-plan">
        <div
          v-for="zone in restaurantZones"
          :key="zone.id"
          class="zone-card"
          :class="[zone.id, getZoneStatusClass(zone.id)]"
          @click="selectZone(zone.id)"
        >
          <div class="zone-header">
            <span class="zone-icon">{{ zone.icon }}</span>
            <h4>{{ zone.name }}</h4>
          </div>
          <div class="zone-stats">
            <div class="zone-stat">
              <span class="zone-stat-icon">📡</span>
              <span>{{ getZoneSensorCount(zone.id) }} sensores</span>
            </div>
            <div class="zone-stat">
              <span class="zone-stat-icon">📹</span>
              <span>{{ getZoneCameraCount(zone.id) }} camaras</span>
            </div>
          </div>
          <div v-if="getZoneAlertCount(zone.id) > 0" class="zone-alerts">
            ⚠️ {{ getZoneAlertCount(zone.id) }} alertas
          </div>
        </div>
      </div>
    </section>

    <!-- CAMARAS ESP32-CAM -->
    <section v-if="showCameraGrid" class="cameras-section">
      <div class="section-header">
        <h3>📹 Camaras en Vivo</h3>
        <button @click="showCameraGrid = false" class="btn-close-grid">✕ Cerrar</button>
      </div>
      <div class="cameras-grid">
        <div v-for="camera in cameras" :key="camera.id" class="camera-card">
          <div class="camera-header">
            <span class="camera-location">{{ camera.location }}</span>
            <span class="camera-status" :class="camera.online ? 'online' : 'offline'">
              {{ camera.online ? '● EN VIVO' : '○ OFFLINE' }}
            </span>
          </div>
          <div class="camera-viewer">
            <img
              v-if="camera.snapshot_url"
              :src="camera.snapshot_url"
              :alt="camera.location"
              class="camera-snapshot"
            />
            <div v-else class="camera-placeholder">
              📷 Sin imagen disponible
            </div>
          </div>
          <div class="camera-controls">
            <button @click="takeSnapshot(camera.id)" class="btn-camera-action">
              📸 Captura
            </button>
            <button @click="viewCameraHistory(camera.id)" class="btn-camera-action">
              🕐 Historial
            </button>
            <button @click="toggleRecording(camera.id)" class="btn-camera-action">
              {{ camera.recording ? '⏸️ Pausar' : '⏺️ Grabar' }}
            </button>
          </div>
          <div class="camera-info">
            <span>Ultima captura: {{ camera.last_snapshot_time || 'N/A' }}</span>
          </div>
        </div>
      </div>
    </section>

    <!-- Alertas Activas -->
    <section v-if="activeAlerts.length > 0" class="alerts-section">
      <h3>⚠️ Alertas Activas</h3>
      <div class="alerts-grid">
        <div
          v-for="alert in activeAlerts"
          :key="alert.id"
          class="alert-card"
          :class="alert.severity"
        >
          <div class="alert-header">
            <span class="alert-icon">{{ getAlertIcon(alert.tipo) }}</span>
            <span class="alert-type">{{ alert.tipo.toUpperCase() }}</span>
            <span class="alert-severity">{{ alert.severidad }}</span>
          </div>
          <div class="alert-location">{{ alert.ubicacion }}</div>
          <div class="alert-message">{{ alert.mensaje }}</div>
          <div v-if="alert.consecuencia" class="alert-consequence">
            <strong>Riesgo:</strong> {{ alert.consecuencia }}
          </div>
          <div v-if="alert.accion_requerida" class="alert-action">
            <strong>Accion:</strong> {{ alert.accion_requerida }}
          </div>
          <div class="alert-time">{{ alert.hora }}</div>
        </div>
      </div>
    </section>

    <!-- Nodos por Ubicacion -->
    <section class="nodes-section">
      <h3>Sensores por Ubicacion</h3>
      <div class="nodes-grid">
        <div
          v-for="(sensors, location) in sensorsByLocation"
          :key="location"
          class="node-card"
          :class="{ 'has-alert': locationHasAlert(location) }"
        >
          <div class="node-header">
            <span class="node-icon">{{ getLocationIcon(location) }}</span>
            <h4>{{ formatLocationName(location) }}</h4>
            <span class="node-status" :class="locationHasAlert(location) ? 'alert' : 'ok'">
              {{ locationHasAlert(location) ? 'ALERTA' : 'OK' }}
            </span>
          </div>
          <div class="node-sensors">
            <div
              v-for="sensor in sensors"
              :key="sensor.tipo"
              class="sensor-item"
              :class="{ 'alert': sensor.alerta }"
            >
              <span class="sensor-icon">{{ getSensorIcon(sensor.tipo) }}</span>
              <span class="sensor-type">{{ sensor.tipo }}</span>
              <span class="sensor-value">{{ sensor.valor }}{{ sensor.unidad }}</span>
              <span v-if="sensor.alerta" class="sensor-alert-badge">!</span>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- Historial de Alertas -->
    <section class="history-section">
      <h3>Historial de Alertas (Ultimas 24h)</h3>
      <div class="history-table">
        <table>
          <thead>
            <tr>
              <th>Hora</th>
              <th>Tipo</th>
              <th>Ubicacion</th>
              <th>Mensaje</th>
              <th>Estado</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(event, index) in alertHistory" :key="index">
              <td>{{ event.hora }}</td>
              <td>
                <span class="history-type">
                  {{ getAlertIcon(event.tipo) }} {{ event.tipo }}
                </span>
              </td>
              <td>{{ event.ubicacion }}</td>
              <td>{{ event.mensaje }}</td>
              <td>
                <span class="history-status" :class="event.resuelto ? 'resolved' : 'active'">
                  {{ event.resuelto ? 'Resuelto' : 'Activo' }}
                </span>
              </td>
            </tr>
            <tr v-if="alertHistory.length === 0">
              <td colspan="5" class="no-alerts">Sin alertas en las ultimas 24 horas</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- Asistente de Seguridad -->
    <SecurityAssistant />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import SecurityAssistant from '../components/SecurityAssistant.vue'

// Estado de conexion
const wsConnected = ref(false)
const lastUpdate = ref(null)
let ws = null
let reconnectInterval = null

// Datos de sensores
const sensorsByLocation = ref({})
const activeAlerts = ref([])
const alertHistory = ref([])
const devices = ref([])

// Camaras
const showCameraGrid = ref(false)
const cameras = ref([
  {
    id: 'cam_cocina_1',
    location: 'Cocina - Area de preparacion',
    online: true,
    snapshot_url: null,
    last_snapshot_time: null,
    recording: false
  },
  {
    id: 'cam_cocina_2',
    location: 'Cocina - Area de coccion',
    online: true,
    snapshot_url: null,
    last_snapshot_time: null,
    recording: false
  },
  {
    id: 'cam_comedor',
    location: 'Comedor principal',
    online: true,
    snapshot_url: null,
    last_snapshot_time: null,
    recording: false
  },
  {
    id: 'cam_almacen',
    location: 'Almacen',
    online: true,
    snapshot_url: null,
    last_snapshot_time: null,
    recording: false
  },
  {
    id: 'cam_entrada',
    location: 'Entrada/Salida',
    online: true,
    snapshot_url: null,
    last_snapshot_time: null,
    recording: false
  }
])

// Zonas del restaurante
const restaurantZones = ref([
  { id: 'cocina', name: 'Cocina', icon: '👨‍🍳' },
  { id: 'comedor', name: 'Comedor', icon: '🍽️' },
  { id: 'almacen', name: 'Almacen', icon: '📦' },
  { id: 'refrigeracion', name: 'Refrigeracion', icon: '🧊' },
  { id: 'entrada', name: 'Entrada', icon: '🚪' }
])

// URLs
const API_BASE_URL = ''
const IOT_WS_URL = (window.location.protocol === 'https:' ? 'wss:' : 'ws:') + '//' + window.location.host + '/ws/iot'

// Computed
const overallStatus = computed(() => {
  if (activeAlerts.value.some(a => a.severidad === 'emergency' || a.severidad === 'critical')) {
    return 'CRITICO'
  }
  if (activeAlerts.value.length > 0) {
    return 'ATENCION'
  }
  return 'NORMAL'
})

const onlineDevices = computed(() => {
  return devices.value.filter(d => d.is_online).length
})

const totalDevices = computed(() => {
  return devices.value.length
})

const activeCameras = computed(() => {
  return cameras.value.filter(c => c.online).length
})

const criticalAlerts = computed(() => {
  return activeAlerts.value.filter(a => a.severidad === 'critical' || a.severidad === 'emergency').length
})

// WebSocket
function connectWebSocket() {
  try {
    ws = new WebSocket(`${IOT_WS_URL}/sensors`)

    ws.onopen = () => {
      wsConnected.value = true
      console.log('[Security] WebSocket conectado')
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        handleSensorData(data)
        lastUpdate.value = new Date()
      } catch (e) {
        console.error('[Security] Error procesando mensaje:', e)
      }
    }

    ws.onclose = () => {
      wsConnected.value = false
      console.log('[Security] WebSocket desconectado')
      scheduleReconnect()
    }

    ws.onerror = (error) => {
      console.error('[Security] WebSocket error:', error)
      wsConnected.value = false
    }

  } catch (error) {
    console.error('[Security] Error conectando WebSocket:', error)
    scheduleReconnect()
  }
}

function scheduleReconnect() {
  if (reconnectInterval) return
  reconnectInterval = setTimeout(() => {
    reconnectInterval = null
    connectWebSocket()
  }, 5000)
}

function handleSensorData(data) {
  if (data.type === 'sensor_reading' || data.readings) {
    const readings = data.readings || [data]

    // Agrupar por ubicacion
    const grouped = {}
    for (const r of readings) {
      const loc = r.location || r.node_id || 'desconocido'
      if (!grouped[loc]) grouped[loc] = []

      grouped[loc].push({
        tipo: r.sensor_type,
        valor: r.value,
        unidad: getUnit(r.sensor_type),
        alerta: isAlert(r.sensor_type, r.value)
      })
    }
    sensorsByLocation.value = grouped
  }
}

// Fetch inicial de datos
async function fetchInitialData() {
  try {
    // Obtener estado IoT
    const response = await fetch(`${API_BASE_URL}/api/admin/iot/status`)
    if (response.ok) {
      const data = await response.json()
      if (data.success) {
        // Procesar alertas
        activeAlerts.value = [
          ...(data.alertas_criticas || []),
          ...(data.alertas_advertencia || [])
        ]

        // Procesar lecturas por ubicacion
        if (data.lecturas_por_ubicacion) {
          sensorsByLocation.value = data.lecturas_por_ubicacion
        }

        lastUpdate.value = new Date()
      }
    }

    // Obtener dispositivos
    const devResponse = await fetch(`${API_BASE_URL}/api/iot/devices`)
    if (devResponse.ok) {
      const devData = await devResponse.json()
      devices.value = devData.devices || []
    }

  } catch (error) {
    console.error('[Security] Error cargando datos:', error)
  }
}

// Helpers
function isAlert(sensorType, value) {
  const thresholds = {
    temperature: { min: 0, max: 35 },
    humidity: { min: 30, max: 70 },
    smoke: { max: 50 },
    gas: { max: 50 },
    co2: { max: 1000 }
  }

  const t = thresholds[sensorType]
  if (!t) return false

  if (t.min !== undefined && value < t.min) return true
  if (t.max !== undefined && value > t.max) return true
  return false
}

function getUnit(sensorType) {
  const units = {
    temperature: '°C',
    humidity: '%',
    smoke: ' ppm',
    gas: ' ppm',
    co2: ' ppm',
    light: ' lux',
    motion: ''
  }
  return units[sensorType] || ''
}

function locationHasAlert(location) {
  const sensors = sensorsByLocation.value[location] || []
  return sensors.some(s => s.alerta)
}

function getStatusIcon(status) {
  switch (status) {
    case 'CRITICO': return '🚨'
    case 'ATENCION': return '⚠️'
    default: return '✅'
  }
}

function getStatusDescription(status) {
  switch (status) {
    case 'CRITICO': return 'Hay alertas criticas que requieren atencion inmediata'
    case 'ATENCION': return 'Hay alertas que requieren revision'
    default: return 'Todos los sensores funcionando normalmente'
  }
}

function getAlertIcon(tipo) {
  const icons = {
    temperature: '🌡️',
    smoke: '🔥',
    gas: '⛽',
    co2: '🌫️',
    humidity: '💧',
    motion: '👁️'
  }
  return icons[tipo] || '📡'
}

function getSensorIcon(tipo) {
  return getAlertIcon(tipo)
}

function getLocationIcon(location) {
  const loc = location.toLowerCase()
  if (loc.includes('cocina')) return '👨‍🍳'
  if (loc.includes('comedor')) return '🍽️'
  if (loc.includes('almacen') || loc.includes('bodega')) return '📦'
  if (loc.includes('refrigerador') || loc.includes('frio')) return '🧊'
  if (loc.includes('entrada') || loc.includes('puerta')) return '🚪'
  if (loc.includes('oficina')) return '🏢'
  return '📍'
}

function formatLocationName(location) {
  return location.charAt(0).toUpperCase() + location.slice(1).replace(/_/g, ' ')
}

function formatTime(date) {
  if (!date) return ''
  return new Date(date).toLocaleTimeString('es-MX', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

// ============================================================================
// QUICK ACTIONS
// ============================================================================

function viewAllCameras() {
  showCameraGrid.value = !showCameraGrid.value
  if (showCameraGrid.value) {
    // Cargar snapshots de camaras
    fetchCameraSnapshots()
  }
}

function silenceAlarms() {
  if (activeAlerts.value.length === 0) return

  const confirmMsg = `¿Silenciar ${activeAlerts.value.length} alarmas activas?`
  if (confirm(confirmMsg)) {
    console.log('[Security] Alarmas silenciadas')
    // TODO: API call to silence alarms
    alert('Alarmas silenciadas temporalmente (30 minutos)')
  }
}

function emergencyProtocol() {
  const confirmMsg = '⚠️ ¿Activar protocolo de emergencia?\n\nEsto notificara a:\n- Bomberos\n- Policia\n- Administrador\n- Gerente'
  if (confirm(confirmMsg)) {
    console.log('[Security] Protocolo de emergencia activado')
    // TODO: API call to trigger emergency protocol
    alert('🚨 PROTOCOLO DE EMERGENCIA ACTIVADO\n\nAutoridades notificadas.\nGrabacion automatica iniciada.\nEquipo de respuesta en camino.')
  }
}

function viewReports() {
  alert('📊 Reportes de Seguridad\n\nEsta funcionalidad estara disponible proximamente.')
  // TODO: Navigate to reports view
}

// ============================================================================
// CAMARAS
// ============================================================================

async function fetchCameraSnapshots() {
  try {
    const response = await fetch(`${API_BASE_URL}/api/security/cameras/snapshots`)
    if (response.ok) {
      const data = await response.json()
      if (data.success && data.snapshots) {
        // Actualizar URLs de snapshots
        cameras.value.forEach(cam => {
          const snapshot = data.snapshots.find(s => s.camera_id === cam.id)
          if (snapshot) {
            cam.snapshot_url = snapshot.url
            cam.last_snapshot_time = snapshot.timestamp
          }
        })
      }
    }
  } catch (error) {
    console.error('[Security] Error cargando snapshots:', error)
  }
}

async function takeSnapshot(cameraId) {
  try {
    const response = await fetch(`${API_BASE_URL}/api/security/cameras/${cameraId}/snapshot`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      }
    })
    if (response.ok) {
      const data = await response.json()
      if (data.success) {
        alert(`📸 ${data.message}`)
        // Actualizar snapshot
        const camera = cameras.value.find(c => c.id === cameraId)
        if (camera && data.snapshot_url) {
          camera.snapshot_url = data.snapshot_url
          camera.last_snapshot_time = data.timestamp
        }
      }
    }
  } catch (error) {
    console.error('[Security] Error tomando snapshot:', error)
    alert('Error al tomar captura')
  }
}

function viewCameraHistory(cameraId) {
  alert(`📹 Historial de camara ${cameraId}\n\nEsta funcionalidad estara disponible proximamente.`)
  // TODO: Open modal with camera history
}

async function toggleRecording(cameraId) {
  const camera = cameras.value.find(c => c.id === cameraId)
  if (!camera) return

  const action = camera.recording ? 'stop' : 'start'

  try {
    const response = await fetch(`${API_BASE_URL}/api/security/cameras/${cameraId}/recording`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ action })
    })

    if (response.ok) {
      const data = await response.json()
      if (data.success) {
        camera.recording = data.recording
        alert(data.message)
      }
    }
  } catch (error) {
    console.error('[Security] Error controlando grabacion:', error)
    alert('Error al controlar grabacion')
  }
}

// ============================================================================
// ZONAS DEL RESTAURANTE
// ============================================================================

function getZoneStatusClass(zoneId) {
  const hasAlert = getZoneAlertCount(zoneId) > 0
  return hasAlert ? 'zone-alert' : 'zone-ok'
}

function getZoneSensorCount(zoneId) {
  const sensors = sensorsByLocation.value[zoneId] || []
  return sensors.length
}

function getZoneCameraCount(zoneId) {
  return cameras.value.filter(c => c.location.toLowerCase().includes(zoneId)).length
}

function getZoneAlertCount(zoneId) {
  return activeAlerts.value.filter(a =>
    a.ubicacion && a.ubicacion.toLowerCase().includes(zoneId)
  ).length
}

function selectZone(zoneId) {
  console.log('[Security] Zona seleccionada:', zoneId)
  // TODO: Highlight zone sensors and show details
  alert(`📍 Zona: ${restaurantZones.value.find(z => z.id === zoneId)?.name}\n\nSensores: ${getZoneSensorCount(zoneId)}\nCamaras: ${getZoneCameraCount(zoneId)}\nAlertas: ${getZoneAlertCount(zoneId)}`)
}

// Lifecycle
onMounted(() => {
  fetchInitialData()
  connectWebSocket()

  // Refrescar datos cada 30 segundos
  const refreshInterval = setInterval(fetchInitialData, 30000)

  onUnmounted(() => {
    clearInterval(refreshInterval)
    if (ws) ws.close()
    if (reconnectInterval) clearTimeout(reconnectInterval)
  })
})
</script>

<style scoped>
.security-dashboard {
  min-height: 100vh;
  background: linear-gradient(135deg, #0a0a0f 0%, #16213e 100%);
  color: #eee;
  padding: 2rem;
}

/* Header */
.security-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid rgba(255,255,255,0.1);
}

.security-header h1 {
  font-size: 2.5rem;
  margin: 0;
  color: #fff;
  text-shadow: 0 0 20px rgba(52, 152, 219, 0.5);
}

.subtitle {
  color: #888;
  margin: 0.5rem 0 0;
}

.header-right {
  text-align: right;
}

.connection-status {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  border-radius: 20px;
  font-size: 0.9rem;
  font-weight: 600;
}

.connection-status.connected {
  background: rgba(39, 174, 96, 0.2);
  color: #27ae60;
}

.connection-status.disconnected {
  background: rgba(231, 76, 60, 0.2);
  color: #e74c3c;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: currentColor;
  animation: pulse-dot 2s ease-in-out infinite;
}

@keyframes pulse-dot {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.6; transform: scale(1.2); }
}

.last-update {
  font-size: 0.8rem;
  color: #666;
  margin-top: 0.5rem;
}

/* ========================================================================== */
/* QUICK ACTIONS PANEL */
/* ========================================================================== */

.quick-actions-panel {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1.5rem;
  margin-bottom: 2rem;
}

.action-btn {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1.5rem;
  border: none;
  border-radius: 16px;
  background: rgba(255,255,255,0.05);
  border: 2px solid rgba(255,255,255,0.1);
  color: #fff;
  cursor: pointer;
  transition: all 0.3s;
  text-align: left;
}

.action-btn:hover:not(:disabled) {
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(0,0,0,0.3);
}

.action-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.action-btn .btn-icon {
  font-size: 2.5rem;
  line-height: 1;
}

.action-btn .btn-content {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.btn-title {
  font-size: 1.1rem;
  font-weight: 700;
}

.btn-subtitle {
  font-size: 0.85rem;
  color: #aaa;
}

.camera-btn {
  border-color: rgba(52, 152, 219, 0.5);
  background: linear-gradient(135deg, rgba(52, 152, 219, 0.15) 0%, rgba(52, 152, 219, 0.05) 100%);
}

.camera-btn:hover:not(:disabled) {
  border-color: rgba(52, 152, 219, 0.8);
  box-shadow: 0 8px 24px rgba(52, 152, 219, 0.3);
}

.alarm-btn {
  border-color: rgba(241, 196, 15, 0.5);
  background: linear-gradient(135deg, rgba(241, 196, 15, 0.15) 0%, rgba(241, 196, 15, 0.05) 100%);
}

.alarm-btn:hover:not(:disabled) {
  border-color: rgba(241, 196, 15, 0.8);
  box-shadow: 0 8px 24px rgba(241, 196, 15, 0.3);
}

.emergency-btn {
  border-color: rgba(231, 76, 60, 0.5);
  background: linear-gradient(135deg, rgba(231, 76, 60, 0.15) 0%, rgba(231, 76, 60, 0.05) 100%);
}

.emergency-btn:hover {
  border-color: rgba(231, 76, 60, 0.8);
  box-shadow: 0 8px 24px rgba(231, 76, 60, 0.3);
  animation: pulse-emergency 1s ease-in-out infinite;
}

@keyframes pulse-emergency {
  0%, 100% { transform: translateY(-4px) scale(1); }
  50% { transform: translateY(-4px) scale(1.02); }
}

.report-btn {
  border-color: rgba(155, 89, 182, 0.5);
  background: linear-gradient(135deg, rgba(155, 89, 182, 0.15) 0%, rgba(155, 89, 182, 0.05) 100%);
}

.report-btn:hover {
  border-color: rgba(155, 89, 182, 0.8);
  box-shadow: 0 8px 24px rgba(155, 89, 182, 0.3);
}

/* ========================================================================== */
/* KPI MEGA CARDS */
/* ========================================================================== */

.kpi-mega-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1.5rem;
  margin-bottom: 2rem;
}

.kpi-card {
  display: flex;
  align-items: center;
  gap: 1.5rem;
  padding: 2rem;
  border-radius: 20px;
  background: rgba(0,0,0,0.3);
  border: 2px solid rgba(255,255,255,0.1);
  transition: all 0.3s;
}

.kpi-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 32px rgba(0,0,0,0.4);
}

.kpi-icon {
  font-size: 4rem;
  line-height: 1;
}

.kpi-data {
  flex: 1;
}

.kpi-label {
  font-size: 0.85rem;
  color: #888;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin-bottom: 0.5rem;
}

.kpi-value {
  font-size: 2.5rem;
  font-weight: 700;
  line-height: 1;
  margin-bottom: 0.5rem;
}

.kpi-desc {
  font-size: 0.9rem;
  color: #aaa;
}

.status-kpi.normal {
  border-color: rgba(39, 174, 96, 0.5);
  background: linear-gradient(135deg, rgba(39, 174, 96, 0.2) 0%, rgba(39, 174, 96, 0.05) 100%);
}

.status-kpi.atencion {
  border-color: rgba(241, 196, 15, 0.5);
  background: linear-gradient(135deg, rgba(241, 196, 15, 0.2) 0%, rgba(241, 196, 15, 0.05) 100%);
}

.status-kpi.critico {
  border-color: rgba(231, 76, 60, 0.5);
  background: linear-gradient(135deg, rgba(231, 76, 60, 0.2) 0%, rgba(231, 76, 60, 0.05) 100%);
  animation: pulse-kpi 2s ease-in-out infinite;
}

@keyframes pulse-kpi {
  0%, 100% { box-shadow: 0 0 20px rgba(231, 76, 60, 0.3); }
  50% { box-shadow: 0 0 40px rgba(231, 76, 60, 0.6); }
}

.devices-kpi {
  border-color: rgba(52, 152, 219, 0.5);
  background: linear-gradient(135deg, rgba(52, 152, 219, 0.2) 0%, rgba(52, 152, 219, 0.05) 100%);
}

.alerts-kpi {
  border-color: rgba(241, 196, 15, 0.5);
  background: linear-gradient(135deg, rgba(241, 196, 15, 0.2) 0%, rgba(241, 196, 15, 0.05) 100%);
}

.savings-kpi {
  border-color: rgba(46, 204, 113, 0.5);
  background: linear-gradient(135deg, rgba(46, 204, 113, 0.2) 0%, rgba(46, 204, 113, 0.05) 100%);
}

/* ========================================================================== */
/* RESTAURANT MAP */
/* ========================================================================== */

.restaurant-map-section {
  margin-bottom: 2rem;
}

.restaurant-map-section h3 {
  margin-bottom: 1.5rem;
  font-size: 1.5rem;
}

.floor-plan {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1.5rem;
}

.zone-card {
  background: rgba(255,255,255,0.05);
  border: 2px solid rgba(255,255,255,0.1);
  border-radius: 16px;
  padding: 1.5rem;
  cursor: pointer;
  transition: all 0.3s;
}

.zone-card:hover {
  transform: translateY(-4px);
  border-color: rgba(52, 152, 219, 0.5);
  box-shadow: 0 8px 24px rgba(52, 152, 219, 0.2);
}

.zone-card.zone-ok {
  border-color: rgba(39, 174, 96, 0.3);
}

.zone-card.zone-alert {
  border-color: rgba(231, 76, 60, 0.6);
  background: linear-gradient(135deg, rgba(231, 76, 60, 0.15) 0%, rgba(231, 76, 60, 0.05) 100%);
  animation: pulse-zone-alert 2s ease-in-out infinite;
}

@keyframes pulse-zone-alert {
  0%, 100% { box-shadow: 0 0 15px rgba(231, 76, 60, 0.3); }
  50% { box-shadow: 0 0 30px rgba(231, 76, 60, 0.6); }
}

.zone-header {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid rgba(255,255,255,0.1);
}

.zone-icon {
  font-size: 2rem;
}

.zone-header h4 {
  margin: 0;
  flex: 1;
  font-size: 1.2rem;
}

.zone-stats {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.zone-stat {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.9rem;
  color: #aaa;
}

.zone-stat-icon {
  font-size: 1.1rem;
}

.zone-alerts {
  margin-top: 0.75rem;
  padding: 0.5rem;
  background: rgba(231, 76, 60, 0.2);
  border-radius: 8px;
  text-align: center;
  font-weight: 700;
  color: #e74c3c;
}

/* ========================================================================== */
/* CAMERAS SECTION */
/* ========================================================================== */

.cameras-section {
  margin-bottom: 2rem;
  background: rgba(0,0,0,0.3);
  border-radius: 20px;
  padding: 2rem;
  border: 2px solid rgba(52, 152, 219, 0.3);
}

.cameras-section .section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}

.cameras-section h3 {
  margin: 0;
  font-size: 1.5rem;
}

.btn-close-grid {
  padding: 0.5rem 1.5rem;
  background: rgba(231, 76, 60, 0.2);
  border: 1px solid rgba(231, 76, 60, 0.5);
  border-radius: 8px;
  color: #e74c3c;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
}

.btn-close-grid:hover {
  background: rgba(231, 76, 60, 0.3);
  transform: scale(1.05);
}

.cameras-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 1.5rem;
}

.camera-card {
  background: rgba(0,0,0,0.4);
  border: 2px solid rgba(255,255,255,0.1);
  border-radius: 16px;
  overflow: hidden;
  transition: all 0.3s;
}

.camera-card:hover {
  border-color: rgba(52, 152, 219, 0.5);
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(52, 152, 219, 0.2);
}

.camera-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  background: rgba(0,0,0,0.3);
}

.camera-location {
  font-weight: 600;
  font-size: 0.95rem;
}

.camera-status {
  font-size: 0.75rem;
  font-weight: 700;
  padding: 0.25rem 0.75rem;
  border-radius: 12px;
}

.camera-status.online {
  background: rgba(39, 174, 96, 0.2);
  color: #27ae60;
}

.camera-status.offline {
  background: rgba(231, 76, 60, 0.2);
  color: #e74c3c;
}

.camera-viewer {
  position: relative;
  width: 100%;
  aspect-ratio: 16 / 9;
  background: #000;
  display: flex;
  align-items: center;
  justify-content: center;
}

.camera-snapshot {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.camera-placeholder {
  font-size: 3rem;
  color: #444;
}

.camera-controls {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.5rem;
  padding: 1rem;
}

.btn-camera-action {
  padding: 0.75rem;
  background: rgba(52, 152, 219, 0.15);
  border: 1px solid rgba(52, 152, 219, 0.3);
  border-radius: 8px;
  color: #3498db;
  font-size: 0.85rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
}

.btn-camera-action:hover {
  background: rgba(52, 152, 219, 0.3);
  transform: scale(1.05);
}

.camera-info {
  padding: 0.75rem 1rem;
  background: rgba(0,0,0,0.3);
  font-size: 0.8rem;
  color: #888;
  text-align: center;
}

/* Alertas */
.alerts-section {
  margin-bottom: 2rem;
}

.alerts-section h3 {
  color: #e74c3c;
  margin-bottom: 1rem;
}

.alerts-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: 1rem;
}

.alert-card {
  background: rgba(0,0,0,0.3);
  border-radius: 12px;
  padding: 1.5rem;
  border-left: 4px solid;
}

.alert-card.critical, .alert-card.emergency {
  border-left-color: #e74c3c;
  animation: pulse-alert 1s ease-in-out infinite;
}

.alert-card.warning {
  border-left-color: #f1c40f;
}

@keyframes pulse-alert {
  0%, 100% { background: rgba(231, 76, 60, 0.1); }
  50% { background: rgba(231, 76, 60, 0.2); }
}

.alert-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.alert-icon {
  font-size: 1.5rem;
}

.alert-type {
  font-weight: 700;
}

.alert-severity {
  margin-left: auto;
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
  font-size: 0.75rem;
  background: rgba(231, 76, 60, 0.3);
}

.alert-location {
  color: #888;
  font-size: 0.9rem;
  margin-bottom: 0.5rem;
}

.alert-message {
  font-weight: 600;
  margin-bottom: 1rem;
}

.alert-consequence {
  background: rgba(231, 76, 60, 0.1);
  padding: 0.75rem;
  border-radius: 6px;
  font-size: 0.85rem;
  margin-bottom: 0.5rem;
}

.alert-action {
  background: rgba(52, 152, 219, 0.1);
  padding: 0.75rem;
  border-radius: 6px;
  font-size: 0.85rem;
  margin-bottom: 0.5rem;
}

.alert-time {
  font-size: 0.8rem;
  color: #666;
  text-align: right;
}

/* Nodos */
.nodes-section h3 {
  margin-bottom: 1rem;
}

.nodes-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 1rem;
  margin-bottom: 2rem;
}

.node-card {
  background: rgba(255,255,255,0.05);
  border-radius: 12px;
  padding: 1.5rem;
  border: 1px solid rgba(255,255,255,0.1);
  transition: all 0.3s;
}

.node-card:hover {
  border-color: rgba(255,255,255,0.2);
  transform: translateY(-2px);
}

.node-card.has-alert {
  border-color: rgba(231, 76, 60, 0.5);
  background: rgba(231, 76, 60, 0.05);
}

.node-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 1rem;
  padding-bottom: 0.75rem;
  border-bottom: 1px solid rgba(255,255,255,0.1);
}

.node-icon {
  font-size: 1.5rem;
}

.node-header h4 {
  margin: 0;
  flex: 1;
}

.node-status {
  padding: 0.25rem 0.75rem;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 700;
}

.node-status.ok {
  background: rgba(39, 174, 96, 0.2);
  color: #27ae60;
}

.node-status.alert {
  background: rgba(231, 76, 60, 0.2);
  color: #e74c3c;
}

.node-sensors {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.sensor-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem;
  background: rgba(0,0,0,0.2);
  border-radius: 6px;
}

.sensor-item.alert {
  background: rgba(231, 76, 60, 0.15);
}

.sensor-icon {
  font-size: 1.2rem;
}

.sensor-type {
  flex: 1;
  color: #aaa;
  font-size: 0.9rem;
}

.sensor-value {
  font-weight: 700;
  font-family: 'Courier New', monospace;
}

.sensor-alert-badge {
  background: #e74c3c;
  color: white;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.7rem;
  font-weight: 700;
}

/* Historial */
.history-section h3 {
  margin-bottom: 1rem;
}

.history-table {
  background: rgba(0,0,0,0.3);
  border-radius: 12px;
  overflow: hidden;
}

.history-table table {
  width: 100%;
  border-collapse: collapse;
}

.history-table th,
.history-table td {
  padding: 1rem;
  text-align: left;
  border-bottom: 1px solid rgba(255,255,255,0.05);
}

.history-table th {
  background: rgba(0,0,0,0.3);
  font-weight: 600;
  color: #888;
  font-size: 0.85rem;
  text-transform: uppercase;
}

.history-type {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.history-status {
  padding: 0.25rem 0.75rem;
  border-radius: 12px;
  font-size: 0.8rem;
  font-weight: 600;
}

.history-status.resolved {
  background: rgba(39, 174, 96, 0.2);
  color: #27ae60;
}

.history-status.active {
  background: rgba(231, 76, 60, 0.2);
  color: #e74c3c;
}

.no-alerts {
  text-align: center;
  color: #666;
  padding: 2rem !important;
}

/* Responsive */
@media (max-width: 768px) {
  .security-dashboard {
    padding: 1rem;
  }

  .security-header {
    flex-direction: column;
    text-align: center;
    gap: 1rem;
  }

  .header-right {
    text-align: center;
  }

  .overall-status {
    flex-direction: column;
    text-align: center;
  }

  .status-stats {
    margin-left: 0;
    margin-top: 1rem;
  }

  .alerts-grid,
  .nodes-grid {
    grid-template-columns: 1fr;
  }

  .history-table {
    overflow-x: auto;
  }
}
</style>
