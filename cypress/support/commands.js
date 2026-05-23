// ***********************************************
// Custom Cypress Commands
// ***********************************************

// ===============================================
// AUTHENTICATION COMMANDS
// ===============================================

/**
 * Login como conductor
 */
Cypress.Commands.add('loginDriver', (email = 'driver@test.com', password = 'password123') => {
  cy.visit(Cypress.env('driverAppUrl') + '/login')
  cy.get('input[name="email"]').clear().type(email)
  cy.get('input[name="password"]').clear().type(password)
  cy.get('button[type="submit"]').click()

  // Esperar a que el login complete
  cy.url().should('include', '/dashboard')
  cy.window().its('localStorage').invoke('getItem', 'token').should('exist')
})

/**
 * Login como cliente
 */
Cypress.Commands.add('loginCustomer', (phone = '+1234567890', password = 'password123') => {
  cy.visit(Cypress.env('customerAppUrl') + '/login')
  cy.get('input[name="phone"]').clear().type(phone)
  cy.get('input[name="password"]').clear().type(password)
  cy.get('button[type="submit"]').click()

  cy.url().should('include', '/home')
  cy.window().its('localStorage').invoke('getItem', 'token').should('exist')
})

/**
 * Login como admin
 */
Cypress.Commands.add('loginAdmin', (email = 'admin@test.com', password = 'admin123') => {
  cy.visit(Cypress.env('adminPanelUrl') + '/login')
  cy.get('input[name="email"]').clear().type(email)
  cy.get('input[name="password"]').clear().type(password)
  cy.get('button[type="submit"]').click()

  cy.url().should('include', '/dashboard')
  cy.window().its('localStorage').invoke('getItem', 'token').should('exist')
})

/**
 * Logout general
 */
Cypress.Commands.add('logout', () => {
  cy.get('[data-testid="user-menu"]').click()
  cy.contains('Cerrar Sesión').click()
  cy.window().its('localStorage').invoke('getItem', 'token').should('not.exist')
})

// ===============================================
// API COMMANDS
// ===============================================

/**
 * API Request con autenticación
 */
Cypress.Commands.add('apiRequest', (method, endpoint, body = null, token = null) => {
  const headers = {
    'Content-Type': 'application/json'
  }

  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  } else {
    // Intentar obtener token del localStorage
    const storedToken = window.localStorage.getItem('token')
    if (storedToken) {
      headers['Authorization'] = `Bearer ${storedToken}`
    }
  }

  return cy.request({
    method,
    url: `${Cypress.env('apiUrl')}${endpoint}`,
    headers,
    body,
    failOnStatusCode: false
  })
})

/**
 * Crear viaje de prueba
 */
Cypress.Commands.add('createTestRide', (rideData = {}) => {
  const defaultData = {
    pickup_location: 'Centro, Ciudad',
    dropoff_location: 'Aeropuerto Internacional',
    pickup_lat: 19.4326,
    pickup_lng: -99.1332,
    dropoff_lat: 19.4363,
    dropoff_lng: -99.0728,
    tenant_id: 'tenant_taxi_001'
  }

  const data = { ...defaultData, ...rideData }

  return cy.window().then((win) => {
    const token = win.localStorage.getItem('token')
    return cy.apiRequest('POST', '/orders', data, token)
  })
})

// ===============================================
// NAVIGATION COMMANDS
// ===============================================

/**
 * Navegar en Driver App
 */
Cypress.Commands.add('goToDriverPage', (page) => {
  const pages = {
    'dashboard': '/dashboard',
    'schedules': '/schedules',
    'earnings': '/earnings',
    'history': '/history',
    'profile': '/profile'
  }
  cy.visit(Cypress.env('driverAppUrl') + pages[page])
})

/**
 * Navegar en Customer App
 */
Cypress.Commands.add('goToCustomerPage', (page) => {
  const pages = {
    'home': '/',
    'request-ride': '/request-ride',
    'history': '/history',
    'profile': '/profile'
  }
  cy.visit(Cypress.env('customerAppUrl') + pages[page])
})

/**
 * Navegar en Admin Panel
 */
Cypress.Commands.add('goToAdminPage', (page) => {
  const pages = {
    'dashboard': '/',
    'drivers': '/drivers',
    'users': '/users',
    'menu': '/menu',
    'promotions': '/promotions',
    'whatsapp': '/whatsapp',
    'security': '/security'
  }
  cy.visit(Cypress.env('adminPanelUrl') + pages[page])
})

// ===============================================
// DRIVER APP SPECIFIC COMMANDS
// ===============================================

/**
 * Cambiar estado del conductor
 */
Cypress.Commands.add('setDriverStatus', (status) => {
  cy.getByTestId('status-toggle').click()
  cy.contains(status).click()
  cy.getByTestId('current-status').should('contain', status)
})

/**
 * Aceptar solicitud de viaje
 */
Cypress.Commands.add('acceptRideRequest', () => {
  cy.getByTestId('ride-request-card').should('be.visible')
  cy.getByTestId('accept-ride-btn').click()
  cy.getByTestId('ride-accepted-modal').should('be.visible')
})

/**
 * Completar viaje
 */
Cypress.Commands.add('completeRide', () => {
  cy.getByTestId('start-ride-btn').click()
  cy.wait(1000)
  cy.getByTestId('complete-ride-btn').click()
  cy.getByTestId('ride-completed-modal').should('be.visible')
})

// ===============================================
// CUSTOMER APP SPECIFIC COMMANDS
// ===============================================

/**
 * Solicitar viaje
 */
Cypress.Commands.add('requestRide', (pickup, dropoff) => {
  cy.goToCustomerPage('request-ride')
  cy.get('input[name="pickup"]').type(pickup)
  cy.get('input[name="dropoff"]').type(dropoff)
  cy.get('button[type="submit"]').click()
  cy.contains('Buscando conductor').should('be.visible')
})

// ===============================================
// ADMIN PANEL SPECIFIC COMMANDS
// ===============================================

/**
 * Crear conductor
 */
Cypress.Commands.add('createDriver', (driverData = {}) => {
  const defaultData = {
    name: 'Test Driver',
    email: `driver-${Date.now()}@test.com`,
    phone: `+52${Math.floor(Math.random() * 1000000000)}`,
    license: `LIC-${Date.now()}`,
    vehicle: {
      brand: 'Toyota',
      model: 'Corolla',
      year: 2020,
      plates: `ABC-${Math.floor(Math.random() * 1000)}`
    }
  }

  const data = { ...defaultData, ...driverData }

  cy.goToAdminPage('drivers')
  cy.getByTestId('create-driver-btn').click()
  cy.get('input[name="name"]').type(data.name)
  cy.get('input[name="email"]').type(data.email)
  cy.get('input[name="phone"]').type(data.phone)
  cy.get('input[name="license"]').type(data.license)
  cy.get('input[name="vehicle.brand"]').type(data.vehicle.brand)
  cy.get('input[name="vehicle.model"]').type(data.vehicle.model)
  cy.get('input[name="vehicle.year"]').type(data.vehicle.year)
  cy.get('input[name="vehicle.plates"]').type(data.vehicle.plates)
  cy.get('button[type="submit"]').click()

  cy.contains('Conductor creado exitosamente').should('be.visible')
})

// ===============================================
// ASSERTION HELPERS
// ===============================================

/**
 * Verificar que PWA está instalable
 */
Cypress.Commands.add('checkPWAInstallable', () => {
  cy.window().its('navigator.serviceWorker').should('exist')
  cy.window().its('navigator.serviceWorker.controller').should('exist')
})

/**
 * Verificar multi-tenant isolation
 */
Cypress.Commands.add('checkTenantIsolation', (tenantId) => {
  cy.window().then((win) => {
    const token = win.localStorage.getItem('token')
    // Decodificar JWT y verificar tenant_id
    if (token) {
      const payload = JSON.parse(atob(token.split('.')[1]))
      expect(payload.tenant_id).to.equal(tenantId)
    }
  })
})

/**
 * Wait for network idle
 */
Cypress.Commands.add('waitForNetworkIdle', (timeout = 1000) => {
  let requestCount = 0

  cy.intercept('**', (req) => {
    requestCount++
    req.continue(() => {
      requestCount--
    })
  })

  cy.wrap(null).then(() => {
    return new Cypress.Promise((resolve) => {
      const checkIdle = () => {
        if (requestCount === 0) {
          resolve()
        } else {
          setTimeout(checkIdle, 100)
        }
      }
      setTimeout(checkIdle, timeout)
    })
  })
})
