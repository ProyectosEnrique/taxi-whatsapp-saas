describe('Customer App - Request Ride', () => {
  beforeEach(() => {
    cy.loginCustomer()
  })

  it('should display request ride page', () => {
    cy.goToCustomerPage('request-ride')
    cy.url().should('include', '/request-ride')
    cy.get('input[name="pickup"]').should('be.visible')
    cy.get('input[name="dropoff"]').should('be.visible')
    cy.getByTestId('map-view').should('be.visible')
  })

  it('should request a ride successfully', () => {
    cy.requestRide('Centro, Ciudad', 'Aeropuerto Internacional')

    // Verificar pantalla de búsqueda
    cy.contains('Buscando conductor').should('be.visible')
    cy.getByTestId('searching-animation').should('be.visible')

    // Esperar asignación (simulada)
    cy.wait(3000)

    // Debería mostrar conductor asignado
    cy.getByTestId('driver-assigned').should('be.visible', { timeout: 10000 })
    cy.getByTestId('driver-info').should('be.visible')
    cy.getByTestId('driver-name').should('be.visible')
    cy.getByTestId('driver-rating').should('be.visible')
    cy.getByTestId('driver-vehicle').should('be.visible')
  })

  it('should show estimated fare', () => {
    cy.goToCustomerPage('request-ride')

    cy.get('input[name="pickup"]').type('Centro, Ciudad')
    cy.get('input[name="dropoff"]').type('Aeropuerto Internacional')

    // Verificar que aparece tarifa estimada
    cy.getByTestId('estimated-fare').should('be.visible')
    cy.getByTestId('estimated-fare').should('contain', '$')
    cy.getByTestId('estimated-distance').should('be.visible')
    cy.getByTestId('estimated-time').should('be.visible')
  })

  it('should cancel ride request', () => {
    cy.requestRide('Centro, Ciudad', 'Aeropuerto Internacional')

    // Cancelar búsqueda
    cy.getByTestId('cancel-search-btn').click()

    // Confirmar cancelación
    cy.getByTestId('confirm-cancel-modal').should('be.visible')
    cy.getByTestId('confirm-cancel-btn').click()

    // Verificar redirección
    cy.url().should('include', '/home')
    cy.contains('Búsqueda cancelada').should('be.visible')
  })

  it('should track ride in real-time', () => {
    cy.requestRide('Centro, Ciudad', 'Aeropuerto Internacional')

    // Esperar asignación
    cy.getByTestId('driver-assigned', { timeout: 10000 }).should('be.visible')

    // Verificar tracking
    cy.getByTestId('tracking-map').should('be.visible')
    cy.getByTestId('driver-location').should('be.visible')
    cy.getByTestId('eta').should('be.visible')
  })
})
