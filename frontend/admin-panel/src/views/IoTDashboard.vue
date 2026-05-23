<template>
  <div class="iot-dashboard">
    <!-- Header -->
    <div class="dashboard-header">
      <div class="header-content">
        <h1>IoT Sensores</h1>
        <p class="subtitle">Monitoreo en tiempo real de dispositivos ESP32</p>
      </div>
      <div class="header-actions">
        <span class="connection-status" :class="{ connected: wsConnected }">
          {{ wsConnected ? 'Conectado' : 'Desconectado' }}
        </span>
        <button @click="refreshData" class="btn-refresh" :disabled="loading">
          {{ loading ? 'Cargando...' : 'Actualizar' }}
        </button>
      </div>
    </div>

    <!-- Alertas Activas -->
    <div v-if="activeAlerts.length > 0" class="alerts-section">
      <h3>Alertas Activas ({{ activeAlerts.length }})</h3>
      <div class="alerts-list">
        <div
          v-for="alert in activeAlerts"
          :key="alert.alert_id"
          class="alert-card"
          :class="alert.severity"
        >
          <div class="alert-icon">
            {{ getAlertIcon(alert.severity) }}
          </div>
          <div class="alert-content">
            <strong>{{ alert.message }}</strong>
            <span class="alert-meta">
              {{ alert.device_id }} | {{ alert.location || 'Sin ubicacion' }} |
              {{ formatTime(alert.timestamp) }}
            </span>
          </div>
          <button @click="acknowledgeAlert(alert.alert_id)" class="btn-acknowledge">
            Reconocer
          </button>
        </div>
      </div>
    </div>

    <!-- Dispositivos -->
    <div class="devices-section">
      <h3>Dispositivos ({{ devices.length }})</h3>
      <div class="devices-grid">
        <div
          v-for="device in devices"
          :key="device.device_id"
          class="device-card"
          :class="{ online: device.is_online, offline: !device.is_online }"
        >
          <div class="device-header">
            <span class="device-type">{{ getDeviceIcon(device.device_type) }}</span>
            <span class="device-name">{{ device.device_id }}</span>
            <span class="device-status">{{ device.is_online ? 'Online' : 'Offline' }}</span>
          </div>
          <div class="device-info">
            <div v-if="device.metadata?.rssi" class="info-item">
              <span class="label">Senal</span>
              <span class="value">{{ device.metadata.rssi }} dBm</span>
            </div>
            <div v-if="device.metadata?.battery_level" class="info-item">
              <span class="label">Bateria</span>
              <span class="value">{{ device.metadata.battery_level }}%</span>
            </div>
            <div v-if="device.metadata?.connected_nodes" class="info-item">
              <span class="label">Nodos MESH</span>
              <span class="value">{{ device.metadata.connected_nodes.length }}</span>
            </div>
            <div class="info-item">
              <span class="label">Ultima vez</span>
              <span class="value">{{ formatTime(device.last_seen) }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Sensores Agrupados por Nodo -->
    <div class="nodes-section">
      <h3>Sensores por Nodo</h3>
      <div class="nodes-grid">
        <div
          v-for="(nodeData, nodeId) in groupedByNode"
          :key="nodeId"
          class="node-card"
          :class="{ online: isNodeOnline(nodeId) }"
        >
          <div class="node-header">
            <div class="node-info">
              <span class="node-icon">{{ getNodeIcon(nodeData.location) }}</span>
              <div class="node-details">
                <span class="node-name">{{ formatNodeName(nodeData.location) }}</span>
                <span class="node-id">{{ nodeId }}</span>
              </div>
            </div>
            <span class="node-status" :class="{ online: isNodeOnline(nodeId) }">
              {{ isNodeOnline(nodeId) ? 'Online' : 'Offline' }}
            </span>
          </div>
          <div class="node-sensors">
            <div
              v-for="sensor in nodeData.sensors"
              :key="sensor.sensor_type"
              class="node-sensor-item"
              :class="[sensor.sensor_type, { alert: isSensorAlert(sensor) }]"
            >
              <span class="sensor-icon-small">{{ getSensorIcon(sensor.sensor_type) }}</span>
              <span class="sensor-type-label">{{ getSensorLabel(sensor.sensor_type) }}</span>
              <span class="sensor-value-small">
                {{ formatSensorValue(sensor) }}
              </span>
              <span class="sensor-time">{{ formatTime(sensor.timestamp) }}</span>
            </div>
            <div v-if="nodeData.sensors.length === 0" class="no-sensors">
              Sin lecturas recientes
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Resumen General de Sensores -->
    <div class="sensors-section">
      <h3>Resumen General</h3>
      <div class="sensors-grid">
        <!-- Temperatura -->
        <div class="sensor-card temperature">
          <div class="sensor-icon">🌡️</div>
          <div class="sensor-data">
            <span class="sensor-value">{{ getAverageValue('temperature')?.toFixed(1) ?? '--' }}</span>
            <span class="sensor-unit">°C</span>
          </div>
          <div class="sensor-label">Temp. Promedio</div>
          <div class="sensor-meta">{{ countSensors('temperature') }} sensores</div>
        </div>

        <!-- Humedad -->
        <div class="sensor-card humidity">
          <div class="sensor-icon">💧</div>
          <div class="sensor-data">
            <span class="sensor-value">{{ getAverageValue('humidity')?.toFixed(1) ?? '--' }}</span>
            <span class="sensor-unit">%</span>
          </div>
          <div class="sensor-label">Humedad Promedio</div>
          <div class="sensor-meta">{{ countSensors('humidity') }} sensores</div>
        </div>

        <!-- CO2 -->
        <div class="sensor-card co2">
          <div class="sensor-icon">🌫️</div>
          <div class="sensor-data">
            <span class="sensor-value">{{ getAverageValue('co2')?.toFixed(0) ?? '--' }}</span>
            <span class="sensor-unit">ppm</span>
          </div>
          <div class="sensor-label">CO2 Promedio</div>
          <div class="sensor-meta">{{ countSensors('co2') }} sensores</div>
        </div>

        <!-- Alertas Activas -->
        <div class="sensor-card alerts-summary" :class="{ alert: getTotalAlerts() > 0 }">
          <div class="sensor-icon">🚨</div>
          <div class="sensor-data">
            <span class="sensor-value">{{ getTotalAlerts() }}</span>
          </div>
          <div class="sensor-label">Alertas Activas</div>
          <div class="sensor-meta">Humo/Gas/Movimiento</div>
        </div>
      </div>
    </div>

    <!-- Historico -->
    <div class="history-section">
      <h3>Historico de Sensores</h3>
      <div class="history-controls">
        <select v-model="selectedSensorType" class="select-sensor">
          <option value="temperature">Temperatura</option>
          <option value="humidity">Humedad</option>
          <option value="co2">CO2</option>
          <option value="light">Luz</option>
        </select>
        <select v-model="historyHours" class="select-hours">
          <option :value="1">Ultima hora</option>
          <option :value="6">Ultimas 6 horas</option>
          <option :value="24">Ultimas 24 horas</option>
          <option :value="168">Ultima semana</option>
        </select>
        <button @click="loadHistory" class="btn-load-history">Cargar</button>
      </div>
      <div v-if="historyData.length > 0" class="history-chart">
        <div class="chart-container">
          <div
            v-for="(point, index) in historyData.slice(-50)"
            :key="index"
            class="chart-bar"
            :style="{ height: getBarHeight(point.value) + '%' }"
            :title="`${point.value} - ${formatTime(point.timestamp)}`"
          ></div>
        </div>
        <div class="chart-labels">
          <span>{{ getMinValue() }}</span>
          <span>{{ getMaxValue() }}</span>
        </div>
      </div>
      <div v-else class="no-data">
        Sin datos historicos disponibles
      </div>
    </div>

    <!-- Estadisticas -->
    <div v-if="stats" class="stats-section">
      <h3>Estadisticas (ultima hora)</h3>
      <div class="stats-grid">
        <div v-for="(data, sensor) in stats.sensors" :key="sensor" class="stat-card">
          <div class="stat-label">{{ getSensorLabel(sensor) }}</div>
          <div class="stat-value">{{ data.mean?.toFixed(1) ?? '--' }}</div>
          <div class="stat-sublabel">Promedio</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'

// Estado
const loading = ref(false)
const wsConnected = ref(false)
const devices = ref([])
const activeAlerts = ref([])
const latestReadings = reactive({})
const allReadings = ref([])  // Todas las lecturas para agrupar por nodo
const historyData = ref([])
const stats = ref(null)
const selectedSensorType = ref('temperature')
const historyHours = ref(24)

// Computed: Agrupar sensores por nodo
const groupedByNode = computed(() => {
  const groups = {}

  for (const reading of allReadings.value) {
    const nodeId = reading.node_id || 'unknown'
    if (!groups[nodeId]) {
      groups[nodeId] = {
        location: reading.location || nodeId,
        sensors: []
      }
    }
    // Solo mantener la lectura más reciente de cada tipo de sensor por nodo
    const existingIndex = groups[nodeId].sensors.findIndex(
      s => s.sensor_type === reading.sensor_type
    )
    if (existingIndex >= 0) {
      // Reemplazar si es más reciente
      if (new Date(reading.timestamp) > new Date(groups[nodeId].sensors[existingIndex].timestamp)) {
        groups[nodeId].sensors[existingIndex] = reading
      }
    } else {
      groups[nodeId].sensors.push(reading)
    }
  }

  // Ordenar nodos por nombre
  const sortedGroups = {}
  Object.keys(groups).sort().forEach(key => {
    sortedGroups[key] = groups[key]
  })

  return sortedGroups
})

// WebSocket
let ws = null
// Usar rutas relativas a través de nginx proxy
const IOT_GATEWAY_URL = window.location.origin + '/api/iot'
const IOT_WS_URL = (window.location.protocol === 'https:' ? 'wss:' : 'ws:') + '//' + window.location.host + '/ws/iot'

// Conectar WebSocket
function connectWebSocket() {
  try {
    ws = new WebSocket(`${IOT_WS_URL}/sensors`)

    ws.onopen = () => {
      wsConnected.value = true
      console.log('[IoT] WebSocket conectado')
      // Suscribirse a todos los sensores
      ws.send(JSON.stringify({
        action: 'subscribe',
        sensor_types: ['temperature', 'humidity', 'co2', 'smoke', 'motion', 'door', 'light', 'gas']
      }))
    }

    ws.onclose = () => {
      wsConnected.value = false
      console.log('[IoT] WebSocket desconectado')
      // Reconectar en 5 segundos
      setTimeout(connectWebSocket, 5000)
    }

    ws.onerror = (error) => {
      console.error('[IoT] WebSocket error:', error)
    }

    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data)
        handleWebSocketMessage(message)
      } catch (e) {
        console.error('[IoT] Error parsing message:', e)
      }
    }
  } catch (error) {
    console.error('[IoT] Error connecting WebSocket:', error)
    setTimeout(connectWebSocket, 5000)
  }
}

// Manejar mensajes WebSocket
function handleWebSocketMessage(message) {
  switch (message.type) {
    case 'sensor_reading':
      latestReadings[message.data.sensor_type] = message.data
      // Actualizar también allReadings para la vista agrupada por nodo
      updateNodeReading(message.data)
      break
    case 'device_status':
      updateDevice(message.data)
      break
    case 'alert':
      if (!message.data.acknowledged) {
        activeAlerts.value.unshift(message.data)
      }
      break
  }
}

// Actualizar lectura en allReadings manteniendo agrupación por nodo
function updateNodeReading(reading) {
  const index = allReadings.value.findIndex(
    r => r.node_id === reading.node_id && r.sensor_type === reading.sensor_type
  )
  if (index >= 0) {
    allReadings.value[index] = reading
  } else {
    allReadings.value.push(reading)
  }
}

// Actualizar dispositivo en la lista
function updateDevice(deviceData) {
  const index = devices.value.findIndex(d => d.device_id === deviceData.device_id)
  if (index >= 0) {
    devices.value[index] = { ...devices.value[index], ...deviceData }
  } else {
    devices.value.push(deviceData)
  }
}

// Cargar datos iniciales
async function refreshData() {
  loading.value = true
  try {
    await Promise.all([
      loadDevices(),
      loadLatestReadings(),
      loadAlerts(),
      loadStats()
    ])
  } catch (error) {
    console.error('[IoT] Error refreshing data:', error)
  } finally {
    loading.value = false
  }
}

async function loadDevices() {
  try {
    const response = await fetch(`${IOT_GATEWAY_URL}/devices`)
    const data = await response.json()
    devices.value = data.devices || []
  } catch (error) {
    console.error('[IoT] Error loading devices:', error)
  }
}

async function loadLatestReadings() {
  try {
    const response = await fetch(`${IOT_GATEWAY_URL}/sensors/latest`)
    const data = await response.json()
    const readings = data.readings || []

    // Guardar todas las lecturas para agrupar por nodo
    allReadings.value = readings

    // También mantener el formato anterior por tipo de sensor
    for (const reading of readings) {
      latestReadings[reading.sensor_type] = reading
    }
  } catch (error) {
    console.error('[IoT] Error loading readings:', error)
  }
}

async function loadAlerts() {
  try {
    const response = await fetch(`${IOT_GATEWAY_URL}/alerts?hours=24&acknowledged=false`)
    const data = await response.json()
    activeAlerts.value = data.alerts || []
  } catch (error) {
    console.error('[IoT] Error loading alerts:', error)
  }
}

async function loadStats() {
  try {
    const response = await fetch(`${IOT_GATEWAY_URL}/stats/summary`)
    stats.value = await response.json()
  } catch (error) {
    console.error('[IoT] Error loading stats:', error)
  }
}

async function loadHistory() {
  try {
    const response = await fetch(
      `${IOT_GATEWAY_URL}/sensors/${selectedSensorType.value}/history?hours=${historyHours.value}`
    )
    const data = await response.json()
    historyData.value = data.readings || []
  } catch (error) {
    console.error('[IoT] Error loading history:', error)
  }
}

async function acknowledgeAlert(alertId) {
  try {
    await fetch(`${IOT_GATEWAY_URL}/alerts/${alertId}/acknowledge`, {
      method: 'POST'
    })
    activeAlerts.value = activeAlerts.value.filter(a => a.alert_id !== alertId)
  } catch (error) {
    console.error('[IoT] Error acknowledging alert:', error)
  }
}

// Helpers
function formatTime(timestamp) {
  if (!timestamp) return '--'
  const date = new Date(timestamp)
  return date.toLocaleTimeString('es-MX', { hour: '2-digit', minute: '2-digit' })
}

function getDeviceIcon(type) {
  const icons = {
    router: '📡',
    mesh_node: '📶',
    gateway: '🌐'
  }
  return icons[type] || '📱'
}

function getAlertIcon(severity) {
  const icons = {
    info: 'ℹ️',
    warning: '⚠️',
    critical: '🔴',
    emergency: '🚨'
  }
  return icons[severity] || '⚠️'
}

function getSensorLabel(sensor) {
  const labels = {
    temperature: 'Temperatura',
    humidity: 'Humedad',
    co2: 'CO2',
    smoke: 'Humo',
    motion: 'Movimiento',
    door: 'Puerta',
    light: 'Luz',
    gas: 'Gas'
  }
  return labels[sensor] || sensor
}

// Nuevas funciones para nodos agrupados
function getNodeIcon(location) {
  const icons = {
    gateway: '🌐',
    cocina: '👨‍🍳',
    comedor: '🍽️',
    comedor_principal: '🍽️',
    entrada: '🚪',
    terraza: '🌳',
    almacen: '📦',
    bano: '🚻',
    oficina: '💼',
    bar: '🍸'
  }
  const loc = (location || '').toLowerCase()
  for (const [key, icon] of Object.entries(icons)) {
    if (loc.includes(key)) return icon
  }
  return '📶'
}

function formatNodeName(location) {
  if (!location) return 'Desconocido'
  return location
    .replace(/_/g, ' ')
    .replace(/\b\w/g, l => l.toUpperCase())
}

function isNodeOnline(nodeId) {
  // Verificar si el nodo está en la lista de nodos conectados del router
  const router = devices.value.find(d => d.device_type === 'router')
  if (router?.metadata?.connected_nodes) {
    const nodeNum = parseInt(nodeId.replace('node_', ''))
    const node = router.metadata.connected_nodes[nodeNum - 1]
    return node?.is_online ?? false
  }
  return true // Por defecto mostrar como online
}

function getSensorIcon(sensorType) {
  const icons = {
    temperature: '🌡️',
    humidity: '💧',
    co2: '🌫️',
    smoke: '🔥',
    motion: '👁️',
    door: '🚪',
    light: '💡',
    gas: '⚠️'
  }
  return icons[sensorType] || '📊'
}

function formatSensorValue(sensor) {
  if (!sensor || sensor.value === null || sensor.value === undefined) return '--'

  switch (sensor.sensor_type) {
    case 'temperature':
      return `${sensor.value.toFixed(1)}°C`
    case 'humidity':
      return `${sensor.value.toFixed(1)}%`
    case 'co2':
      return `${sensor.value.toFixed(0)} ppm`
    case 'smoke':
      return sensor.value > 50 ? 'Alerta!' : 'Normal'
    case 'motion':
      return sensor.value ? 'Detectado' : 'Sin mov.'
    case 'door':
      return sensor.value ? 'Abierta' : 'Cerrada'
    case 'light':
      return `${sensor.value.toFixed(0)} lux`
    case 'gas':
      return `${sensor.value.toFixed(0)} ppm`
    default:
      return sensor.value
  }
}

function isSensorAlert(sensor) {
  if (!sensor) return false
  switch (sensor.sensor_type) {
    case 'smoke':
      return sensor.value > 50
    case 'gas':
      return sensor.value > 100
    case 'temperature':
      return sensor.value > 35 || sensor.value < 5
    case 'co2':
      return sensor.value > 1000
    default:
      return false
  }
}

function getAverageValue(sensorType) {
  const readings = allReadings.value.filter(r => r.sensor_type === sensorType)
  if (readings.length === 0) return null
  const sum = readings.reduce((acc, r) => acc + (r.value || 0), 0)
  return sum / readings.length
}

function countSensors(sensorType) {
  return allReadings.value.filter(r => r.sensor_type === sensorType).length
}

function getTotalAlerts() {
  let count = 0
  for (const reading of allReadings.value) {
    if (isSensorAlert(reading)) count++
  }
  return count
}

function getBarHeight(value) {
  if (historyData.value.length === 0) return 0
  const values = historyData.value.map(p => p.value)
  const min = Math.min(...values)
  const max = Math.max(...values)
  if (max === min) return 50
  return ((value - min) / (max - min)) * 100
}

function getMinValue() {
  if (historyData.value.length === 0) return '--'
  return Math.min(...historyData.value.map(p => p.value)).toFixed(1)
}

function getMaxValue() {
  if (historyData.value.length === 0) return '--'
  return Math.max(...historyData.value.map(p => p.value)).toFixed(1)
}

// Lifecycle
onMounted(() => {
  refreshData()
  connectWebSocket()
})

onUnmounted(() => {
  if (ws) {
    ws.close()
  }
})
</script>

<style scoped>
.iot-dashboard {
  padding: 0;
}

/* Header */
.dashboard-header {
  background: linear-gradient(135deg, #1a5276 0%, #154360 100%);
  color: white;
  padding: 2rem;
  border-radius: 12px;
  margin-bottom: 2rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-content h1 {
  margin: 0 0 0.5rem 0;
  font-size: 1.8rem;
}

.subtitle {
  margin: 0;
  opacity: 0.9;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.connection-status {
  padding: 0.5rem 1rem;
  border-radius: 20px;
  font-size: 0.85rem;
  font-weight: 600;
  background: rgba(231, 76, 60, 0.3);
  color: #e74c3c;
}

.connection-status.connected {
  background: rgba(39, 174, 96, 0.3);
  color: #27ae60;
}

.btn-refresh {
  padding: 0.75rem 1.5rem;
  background: rgba(255, 255, 255, 0.2);
  color: white;
  border: 2px solid white;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 600;
  transition: all 0.3s;
}

.btn-refresh:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.3);
}

.btn-refresh:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* Alertas */
.alerts-section {
  background: #fff;
  border-radius: 12px;
  padding: 1.5rem;
  margin-bottom: 2rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.alerts-section h3 {
  margin: 0 0 1rem 0;
  color: #e74c3c;
}

.alerts-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.alert-card {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem;
  border-radius: 8px;
  background: #fef9e7;
  border-left: 4px solid #f39c12;
}

.alert-card.critical {
  background: #fadbd8;
  border-left-color: #e74c3c;
}

.alert-card.emergency {
  background: #fadbd8;
  border-left-color: #c0392b;
  animation: pulse 1s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
}

.alert-icon {
  font-size: 1.5rem;
}

.alert-content {
  flex: 1;
}

.alert-content strong {
  display: block;
  margin-bottom: 0.25rem;
}

.alert-meta {
  font-size: 0.85rem;
  color: #7f8c8d;
}

.btn-acknowledge {
  padding: 0.5rem 1rem;
  background: #27ae60;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 600;
  transition: background 0.3s;
}

.btn-acknowledge:hover {
  background: #1e8449;
}

/* Dispositivos */
.devices-section {
  background: #fff;
  border-radius: 12px;
  padding: 1.5rem;
  margin-bottom: 2rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.devices-section h3 {
  margin: 0 0 1rem 0;
  color: #2c3e50;
}

.devices-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 1rem;
}

.device-card {
  border: 2px solid #e0e0e0;
  border-radius: 10px;
  padding: 1rem;
  transition: all 0.3s;
}

.device-card.online {
  border-color: #27ae60;
  background: linear-gradient(135deg, #eafaf1 0%, #d5f4e6 100%);
}

.device-card.offline {
  border-color: #e74c3c;
  background: linear-gradient(135deg, #fdf2f2 0%, #fadbd8 100%);
  opacity: 0.7;
}

.device-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 1rem;
  padding-bottom: 0.75rem;
  border-bottom: 1px solid #eee;
}

.device-type {
  font-size: 1.5rem;
}

.device-name {
  flex: 1;
  font-weight: 600;
  color: #2c3e50;
}

.device-status {
  font-size: 0.8rem;
  font-weight: 600;
  padding: 0.25rem 0.5rem;
  border-radius: 10px;
  background: #27ae60;
  color: white;
}

.device-card.offline .device-status {
  background: #e74c3c;
}

.device-info {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.5rem;
}

.info-item {
  display: flex;
  flex-direction: column;
}

.info-item .label {
  font-size: 0.75rem;
  color: #95a5a6;
}

.info-item .value {
  font-weight: 600;
  color: #2c3e50;
}

/* Nodos Agrupados */
.nodes-section {
  background: #fff;
  border-radius: 12px;
  padding: 1.5rem;
  margin-bottom: 2rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.nodes-section h3 {
  margin: 0 0 1rem 0;
  color: #2c3e50;
}

.nodes-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 1.25rem;
}

.node-card {
  background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
  border: 2px solid #dee2e6;
  border-radius: 12px;
  overflow: hidden;
  transition: all 0.3s;
}

.node-card.online {
  border-color: #27ae60;
  background: linear-gradient(135deg, #f0fff4 0%, #e6ffed 100%);
}

.node-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.12);
}

.node-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.25rem;
  background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%);
  color: white;
}

.node-card.online .node-header {
  background: linear-gradient(135deg, #27ae60 0%, #2ecc71 100%);
}

.node-info {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.node-icon {
  font-size: 1.75rem;
}

.node-details {
  display: flex;
  flex-direction: column;
}

.node-name {
  font-weight: 700;
  font-size: 1.1rem;
}

.node-id {
  font-size: 0.75rem;
  opacity: 0.85;
}

.node-status {
  font-size: 0.75rem;
  font-weight: 600;
  padding: 0.3rem 0.75rem;
  border-radius: 15px;
  background: rgba(231, 76, 60, 0.3);
  color: #fff;
}

.node-status.online {
  background: rgba(255, 255, 255, 0.25);
}

.node-sensors {
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.node-sensor-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.6rem 0.75rem;
  background: white;
  border-radius: 8px;
  border-left: 4px solid #95a5a6;
  transition: all 0.2s;
}

.node-sensor-item:hover {
  background: #f8f9fa;
}

.node-sensor-item.temperature { border-left-color: #e74c3c; }
.node-sensor-item.humidity { border-left-color: #3498db; }
.node-sensor-item.co2 { border-left-color: #9b59b6; }
.node-sensor-item.smoke { border-left-color: #e67e22; }
.node-sensor-item.motion { border-left-color: #1abc9c; }
.node-sensor-item.door { border-left-color: #34495e; }
.node-sensor-item.light { border-left-color: #f1c40f; }
.node-sensor-item.gas { border-left-color: #c0392b; }

.node-sensor-item.alert {
  background: linear-gradient(135deg, #fff5f5 0%, #fee2e2 100%);
  border-left-color: #e74c3c;
  animation: pulse-alert 1.5s infinite;
}

@keyframes pulse-alert {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
}

.sensor-icon-small {
  font-size: 1.25rem;
  width: 30px;
  text-align: center;
}

.sensor-type-label {
  flex: 1;
  font-size: 0.85rem;
  color: #7f8c8d;
}

.sensor-value-small {
  font-weight: 700;
  font-size: 1rem;
  color: #2c3e50;
  min-width: 80px;
  text-align: right;
}

.sensor-time {
  font-size: 0.7rem;
  color: #95a5a6;
  min-width: 45px;
  text-align: right;
}

.no-sensors {
  text-align: center;
  padding: 1rem;
  color: #95a5a6;
  font-style: italic;
}

/* Sensores */
.sensors-section {
  background: #fff;
  border-radius: 12px;
  padding: 1.5rem;
  margin-bottom: 2rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.sensors-section h3 {
  margin: 0 0 1rem 0;
  color: #2c3e50;
}

.sensor-card.alerts-summary {
  border-top: 4px solid #27ae60;
}

.sensor-card.alerts-summary.alert {
  border-top-color: #e74c3c;
}

.sensors-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 1rem;
}

.sensor-card {
  background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
  border-radius: 12px;
  padding: 1.25rem;
  text-align: center;
  transition: transform 0.3s, box-shadow 0.3s;
}

.sensor-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
}

.sensor-card.alert {
  background: linear-gradient(135deg, #fadbd8 0%, #f5b7b1 100%);
  animation: pulse 1.5s infinite;
}

.sensor-card.temperature {
  border-top: 4px solid #e74c3c;
}

.sensor-card.humidity {
  border-top: 4px solid #3498db;
}

.sensor-card.co2 {
  border-top: 4px solid #9b59b6;
}

.sensor-card.smoke {
  border-top: 4px solid #e67e22;
}

.sensor-card.motion {
  border-top: 4px solid #1abc9c;
}

.sensor-card.door {
  border-top: 4px solid #34495e;
}

.sensor-card.light {
  border-top: 4px solid #f1c40f;
}

.sensor-card.gas {
  border-top: 4px solid #c0392b;
}

.sensor-icon {
  font-size: 2rem;
  margin-bottom: 0.5rem;
}

.sensor-data {
  display: flex;
  align-items: baseline;
  justify-content: center;
  gap: 0.25rem;
  margin-bottom: 0.5rem;
}

.sensor-value {
  font-size: 2rem;
  font-weight: 700;
  color: #2c3e50;
}

.sensor-unit {
  font-size: 1rem;
  color: #7f8c8d;
}

.sensor-label {
  font-size: 0.9rem;
  color: #7f8c8d;
  font-weight: 600;
}

.sensor-meta {
  font-size: 0.75rem;
  color: #95a5a6;
  margin-top: 0.5rem;
}

/* Historico */
.history-section {
  background: #fff;
  border-radius: 12px;
  padding: 1.5rem;
  margin-bottom: 2rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.history-section h3 {
  margin: 0 0 1rem 0;
  color: #2c3e50;
}

.history-controls {
  display: flex;
  gap: 1rem;
  margin-bottom: 1rem;
}

.select-sensor,
.select-hours {
  padding: 0.5rem 1rem;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 0.9rem;
}

.btn-load-history {
  padding: 0.5rem 1.5rem;
  background: #3498db;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 600;
}

.btn-load-history:hover {
  background: #2980b9;
}

.history-chart {
  margin-top: 1rem;
}

.chart-container {
  display: flex;
  align-items: flex-end;
  height: 150px;
  gap: 2px;
  background: #f8f9fa;
  padding: 1rem;
  border-radius: 8px;
}

.chart-bar {
  flex: 1;
  background: linear-gradient(180deg, #3498db 0%, #2980b9 100%);
  border-radius: 2px 2px 0 0;
  min-height: 2px;
  transition: height 0.3s;
}

.chart-bar:hover {
  background: linear-gradient(180deg, #2980b9 0%, #1a5276 100%);
}

.chart-labels {
  display: flex;
  justify-content: space-between;
  margin-top: 0.5rem;
  font-size: 0.85rem;
  color: #7f8c8d;
}

.no-data {
  text-align: center;
  padding: 2rem;
  color: #95a5a6;
}

/* Estadisticas */
.stats-section {
  background: #fff;
  border-radius: 12px;
  padding: 1.5rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.stats-section h3 {
  margin: 0 0 1rem 0;
  color: #2c3e50;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 1rem;
}

.stat-card {
  background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
  padding: 1rem;
  border-radius: 8px;
  text-align: center;
}

.stat-label {
  font-size: 0.85rem;
  color: #7f8c8d;
  margin-bottom: 0.5rem;
}

.stat-value {
  font-size: 1.75rem;
  font-weight: 700;
  color: #2c3e50;
}

.stat-sublabel {
  font-size: 0.75rem;
  color: #95a5a6;
}

/* Responsive */
@media (max-width: 768px) {
  .dashboard-header {
    flex-direction: column;
    text-align: center;
    gap: 1rem;
  }

  .header-actions {
    flex-direction: column;
    width: 100%;
  }

  .sensors-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .history-controls {
    flex-direction: column;
  }

  .alert-card {
    flex-direction: column;
    text-align: center;
  }
}
</style>
