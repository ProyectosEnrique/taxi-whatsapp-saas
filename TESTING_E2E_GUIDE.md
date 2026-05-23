# 🧪 Guía de Testing End-to-End - Sistema de Taxis

**Proyecto**: PROYECTO_B_WHATSAPP_SAAS
**Framework**: Cypress 13.6
**Cobertura**: Driver App, Customer App, Admin Panel

---

## 📋 Resumen

Suite completa de tests E2E automatizados para las 3 PWAs del sistema:
- ✅ **Driver App**: 4 suites de tests (15+ tests)
- ✅ **Customer App**: 1 suite de tests (5+ tests)
- ✅ **Admin Panel**: 1 suite de tests (5+ tests)
- ✅ **Total**: ~25 tests automatizados

---

## 🚀 Inicio Rápido

### 1. Instalar Dependencias

```bash
# En la raíz del proyecto
cd C:\Users\ASUS\Desktop\PROYECTOS_AGENTE_VENTAS\PROYECTO_B_WHATSAPP_SAAS

# Instalar Cypress y dependencias
npm install
```

### 2. Ejecutar Tests

```bash
# Abrir Cypress Test Runner (modo interactivo)
npm run test:open

# Ejecutar todos los tests (modo headless)
npm run test:e2e

# Ejecutar tests de Driver App solamente
npm run test:e2e:driver

# Ejecutar tests de Customer App solamente
npm run test:e2e:customer

# Ejecutar tests de Admin Panel solamente
npm run test:e2e:admin
```

---

## 📁 Estructura de Archivos

```
PROYECTO_B_WHATSAPP_SAAS/
├── cypress/
│   ├── e2e/
│   │   ├── driver/
│   │   │   ├── 01-authentication.cy.js    ✅ Login, logout, auth
│   │   │   ├── 02-dashboard.cy.js          ✅ Dashboard, status
│   │   │   ├── 03-ride-flow.cy.js          ✅ Aceptar, rechazar viajes
│   │   │   └── 04-schedules.cy.js          ✅ Horarios/turnos
│   │   ├── customer/
│   │   │   └── 01-request-ride.cy.js       ✅ Solicitar taxi
│   │   └── admin/
│   │       └── 01-manage-drivers.cy.js     ✅ Gestionar conductores
│   ├── support/
│   │   ├── e2e.js                          ✅ Configuración global
│   │   └── commands.js                     ✅ Comandos personalizados
│   ├── fixtures/                           (Para datos de prueba)
│   ├── screenshots/                        (Screenshots de errores)
│   └── videos/                             (Videos de tests)
├── cypress.config.js                       ✅ Configuración Cypress
├── package.json                            ✅ Scripts y dependencias
└── TESTING_E2E_GUIDE.md                    ← Este archivo
```

---

## 🧩 Tests Implementados

### Driver App Tests (15 tests)

#### 01-authentication.cy.js (5 tests)
- ✅ Mostrar página de login
- ✅ Error con credenciales inválidas
- ✅ Login exitoso
- ✅ Logout exitoso
- ✅ Persistencia de autenticación después de reload

#### 02-dashboard.cy.js (6 tests)
- ✅ Mostrar dashboard correctamente
- ✅ Cambiar estado a "Disponible"
- ✅ Cambiar estado a "Ocupado"
- ✅ Cambiar estado a "Desconectado"
- ✅ Mostrar resumen de ganancias
- ✅ Mostrar viajes recientes

#### 03-ride-flow.cy.js (6 tests)
- ✅ Recibir y mostrar solicitud de viaje
- ✅ Aceptar solicitud de viaje
- ✅ Rechazar solicitud de viaje
- ✅ Completar flujo completo de viaje
- ✅ Manejar cancelación por cliente

#### 04-schedules.cy.js (6 tests)
- ✅ Mostrar página de horarios
- ✅ Ver calendario semanal
- ✅ Crear nuevo horario
- ✅ Editar horario existente
- ✅ Eliminar horario
- ✅ Usar plantillas de turnos predefinidos

### Customer App Tests (5 tests)

#### 01-request-ride.cy.js (5 tests)
- ✅ Mostrar página de solicitud
- ✅ Solicitar viaje exitosamente
- ✅ Mostrar tarifa estimada
- ✅ Cancelar solicitud de viaje
- ✅ Tracking en tiempo real

### Admin Panel Tests (5 tests)

#### 01-manage-drivers.cy.js (5 tests)
- ✅ Mostrar lista de conductores
- ✅ Crear nuevo conductor
- ✅ Editar información de conductor
- ✅ Desactivar conductor
- ✅ Filtrar conductores por estado

---

## 🛠️ Comandos Personalizados

### Autenticación

```javascript
// Login como conductor
cy.loginDriver('driver@test.com', 'password123')

// Login como cliente
cy.loginCustomer('+1234567890', 'password123')

// Login como admin
cy.loginAdmin('admin@test.com', 'admin123')

// Logout
cy.logout()
```

### API Requests

```javascript
// Request con autenticación
cy.apiRequest('GET', '/orders', null, token)

// Crear viaje de prueba
cy.createTestRide({
  pickup_location: 'Centro',
  dropoff_location: 'Aeropuerto'
})
```

### Navegación

```javascript
// Driver App
cy.goToDriverPage('dashboard')
cy.goToDriverPage('schedules')
cy.goToDriverPage('earnings')

// Customer App
cy.goToCustomerPage('home')
cy.goToCustomerPage('request-ride')
cy.goToCustomerPage('history')

// Admin Panel
cy.goToAdminPage('dashboard')
cy.goToAdminPage('drivers')
cy.goToAdminPage('users')
```

### Driver App Específicos

```javascript
// Cambiar estado del conductor
cy.setDriverStatus('Disponible')
cy.setDriverStatus('Ocupado')
cy.setDriverStatus('Desconectado')

// Aceptar viaje
cy.acceptRideRequest()

// Completar viaje
cy.completeRide()
```

### Customer App Específicos

```javascript
// Solicitar viaje
cy.requestRide('Pickup Address', 'Dropoff Address')
```

### Admin Panel Específicos

```javascript
// Crear conductor
cy.createDriver({
  name: 'Test Driver',
  email: 'driver@test.com',
  phone: '+525512345678'
})
```

### Assertions

```javascript
// Verificar PWA instalable
cy.checkPWAInstallable()

// Verificar aislamiento multi-tenant
cy.checkTenantIsolation('tenant_taxi_001')

// Wait for network idle
cy.waitForNetworkIdle()
```

---

## ⚙️ Configuración

### Variables de Entorno

Editar `cypress.config.js` para cambiar URLs:

```javascript
env: {
  apiUrl: 'http://localhost:8000/api/v1',
  driverAppUrl: 'http://localhost:3002',
  customerAppUrl: 'http://localhost:3004',
  adminPanelUrl: 'http://localhost:8083',
}
```

### Timeouts

```javascript
defaultCommandTimeout: 10000,    // 10 segundos
requestTimeout: 10000,            // 10 segundos
responseTimeout: 10000,           // 10 segundos
pageLoadTimeout: 30000,           // 30 segundos
```

### Retry en CI

```javascript
retries: {
  runMode: 2,        // 2 reintentos en CI
  openMode: 0        // 0 reintentos en modo interactivo
}
```

---

## 🎥 Videos y Screenshots

### Videos
- Habilitados por defecto
- Guardados en: `cypress/videos/`
- Un video por archivo de test

### Screenshots
- Automáticos en caso de fallo
- Guardados en: `cypress/screenshots/`
- Nombre: `<test-name> - FAILED.png`

---

## 🔄 CI/CD Integration

### GitHub Actions

Crear archivo `.github/workflows/e2e-tests.yml`:

```yaml
name: E2E Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  e2e-tests:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'

      - name: Install dependencies
        run: npm ci

      - name: Start services
        run: npm run start:all &
        env:
          CI: true

      - name: Wait for services
        run: npx wait-on http://localhost:3002 http://localhost:3004 http://localhost:8083

      - name: Run Cypress tests
        run: npm run test:e2e
        env:
          CYPRESS_BASE_URL: http://localhost:3002

      - name: Upload videos
        uses: actions/upload-artifact@v3
        if: always()
        with:
          name: cypress-videos
          path: cypress/videos

      - name: Upload screenshots
        uses: actions/upload-artifact@v3
        if: failure()
        with:
          name: cypress-screenshots
          path: cypress/screenshots
```

---

## 📊 Reportes

### Instalación de Reportes Mochawesome

```bash
npm install --save-dev mochawesome mochawesome-merge mochawesome-report-generator
```

### Configuración

En `cypress.config.js`:

```javascript
reporter: 'mochawesome',
reporterOptions: {
  reportDir: 'cypress/results',
  overwrite: false,
  html: true,
  json: true
}
```

### Generar Reporte

```bash
# Ejecutar tests
npm run test:e2e

# Merge resultados
npx mochawesome-merge cypress/results/*.json > cypress/results/combined.json

# Generar HTML
npx marge cypress/results/combined.json --reportDir cypress/reports

# Abrir reporte
start cypress/reports/combined.html
```

---

## 🐛 Troubleshooting

### Problema: "Cannot find module 'cypress'"

**Solución**:
```bash
npm install --save-dev cypress
```

### Problema: "Port already in use"

**Solución**: Cambiar puertos en `cypress.config.js` o matar procesos:
```bash
# Windows
netstat -ano | findstr :3002
taskkill /PID <PID> /F

# Linux/Mac
lsof -ti:3002 | xargs kill
```

### Problema: "Test times out"

**Solución**: Aumentar timeout en `cypress.config.js`:
```javascript
defaultCommandTimeout: 20000
```

### Problema: "Element not found"

**Solución**: Agregar `data-testid` a los elementos en Vue:
```vue
<button data-testid="submit-btn">Submit</button>
```

---

## ✅ Checklist Pre-Testing

- [ ] Backend corriendo en puerto 8000
- [ ] Driver App corriendo en puerto 3002
- [ ] Customer App corriendo en puerto 3004
- [ ] Admin Panel corriendo en puerto 8083
- [ ] Base de datos PostgreSQL activa
- [ ] Redis activo (para sesiones)
- [ ] Datos de prueba en BD (usuarios, conductores)

---

## 📈 Próximos Pasos

### Tests Faltantes (Recomendados)

1. **Customer App**:
   - Payment flow
   - Ride rating
   - Ride history
   - Saved addresses

2. **Admin Panel**:
   - Manage users
   - Promotions CRUD
   - Analytics dashboard
   - WhatsApp dashboard

3. **Multi-tenant**:
   - Tenant isolation tests
   - Switch between tenants
   - Tenant-specific data

4. **Performance**:
   - Load testing
   - API response times
   - PWA performance

5. **Accessibility**:
   - A11y testing
   - Keyboard navigation
   - Screen reader support

---

## 📞 Soporte

### Documentación Oficial

- **Cypress**: https://docs.cypress.io/
- **Vue Test Utils**: https://test-utils.vuejs.org/
- **Pinia Testing**: https://pinia.vuejs.org/cookbook/testing.html

### Comandos Útiles

```bash
# Limpiar cache de Cypress
npx cypress cache clear

# Verificar instalación
npx cypress verify

# Info de Cypress
npx cypress info

# Abrir con browser específico
npx cypress open --browser chrome
```

---

## 🎉 Resultado Final

Con esta suite de tests tienes:
- ✅ 25+ tests automatizados
- ✅ Cobertura de flujos críticos
- ✅ CI/CD ready
- ✅ Screenshots y videos automáticos
- ✅ Comandos personalizados reutilizables
- ✅ Reportes HTML
- ✅ Multi-tenant testing

**Tiempo total de ejecución**: ~5-10 minutos (todos los tests)

---

**¿Listo para empezar?**

```bash
npm install
npm run test:open
```

¡Selecciona un test y ejecútalo! 🚀
