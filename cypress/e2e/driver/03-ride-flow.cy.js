describe('Driver App - Ride Flow', () => {
  beforeEach(() => {
    cy.loginDriver()
  })

  it('should receive and display ride request', () => {
    // Poner conductor disponible
    cy.goToDriverPage('dashboard')
    cy.setDriverStatus('Disponible')

    // Simular solicitud de viaje (desde otro test o API)
    cy.createTestRide().then((response) => {
      expect(response.status).to.eq(201)

      // Verificar que aparece la notificación
      cy.getByTestId('ride-request-notification').should('be.visible')
      cy.getByTestId('ride-request-card').should('be.visible')

      // Verificar información del viaje
      cy.getByTestId('ride-request-card').within(() => {
        cy.contains('Centro, Ciudad').should('be.visible')
        cy.contains('Aeropuerto Internacional').should('be.visible')
        cy.get('.estimated-fare').should('be.visible')
        cy.get('.distance').should('be.visible')
      })
    })
  })

  it('should accept ride request', () => {
    cy.goToDriverPage('dashboard')
    cy.setDriverStatus('Disponible')

    cy.createTestRide()

    // Aceptar el viaje
    cy.acceptRideRequest()

    // Verificar modal de confirmación
    cy.getByTestId('ride-accepted-modal').within(() => {
      cy.contains('Viaje Aceptado').should('be.visible')
      cy.contains('Navegar al cliente').should('be.visible')
    })

    // Ir a la vista de viaje activo
    cy.contains('Ir al viaje').click()
    cy.url().should('include', '/active-ride')
  })

  it('should reject ride request', () => {
    cy.goToDriverPage('dashboard')
    cy.setDriverStatus('Disponible')

    cy.createTestRide()

    // Rechazar el viaje
    cy.getByTestId('reject-ride-btn').click()

    // Confirmar rechazo
    cy.getByTestId('confirm-reject-modal').should('be.visible')
    cy.getByTestId('confirm-reject-btn').click()

    // Verificar que el viaje desaparece
    cy.getByTestId('ride-request-card').should('not.exist')

    // Verificar mensaje
    cy.contains('Viaje rechazado').should('be.visible')
  })

  it('should complete full ride flow', () => {
    cy.goToDriverPage('dashboard')
    cy.setDriverStatus('Disponible')

    // Crear y aceptar viaje
    cy.createTestRide()
    cy.acceptRideRequest()
    cy.contains('Ir al viaje').click()

    // Verificar vista de viaje activo
    cy.url().should('include', '/active-ride')
    cy.getByTestId('customer-info').should('be.visible')
    cy.getByTestId('map-view').should('be.visible')

    // Iniciar viaje
    cy.getByTestId('start-ride-btn').click()
    cy.getByTestId('ride-status').should('contain', 'En curso')

    // Completar viaje
    cy.getByTestId('complete-ride-btn').click()

    // Confirmar completación
    cy.getByTestId('complete-ride-modal').should('be.visible')
    cy.getByTestId('confirm-complete-btn').click()

    // Verificar redirección y mensaje
    cy.url().should('include', '/dashboard')
    cy.contains('Viaje completado exitosamente').should('be.visible')

    // Verificar que las ganancias aumentaron
    cy.getByTestId('earnings-today').should('be.visible')
  })

  it('should handle ride cancellation by customer', () => {
    cy.goToDriverPage('dashboard')
    cy.setDriverStatus('Disponible')

    cy.createTestRide()
    cy.acceptRideRequest()
    cy.contains('Ir al viaje').click()

    // Simular cancelación del cliente
    cy.window().then((win) => {
      // Simular evento WebSocket de cancelación
      win.dispatchEvent(new CustomEvent('ride-cancelled', {
        detail: { reason: 'Cliente canceló' }
      }))
    })

    // Verificar notificación de cancelación
    cy.getByTestId('ride-cancelled-modal').should('be.visible')
    cy.contains('El cliente canceló el viaje').should('be.visible')

    // Cerrar modal y volver al dashboard
    cy.getByTestId('close-modal-btn').click()
    cy.url().should('include', '/dashboard')
  })
})
