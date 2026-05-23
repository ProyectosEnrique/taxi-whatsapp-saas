describe('Driver App - Dashboard', () => {
  beforeEach(() => {
    cy.loginDriver()
  })

  it('should display dashboard correctly', () => {
    cy.goToDriverPage('dashboard')

    // Verificar elementos principales
    cy.getByTestId('driver-status').should('be.visible')
    cy.getByTestId('earnings-today').should('be.visible')
    cy.getByTestId('trips-today').should('be.visible')
    cy.getByTestId('rating').should('be.visible')
  })

  it('should change driver status to Available', () => {
    cy.goToDriverPage('dashboard')
    cy.setDriverStatus('Disponible')

    // Verificar que el estado cambió
    cy.getByTestId('current-status').should('contain', 'Disponible')
    cy.getByTestId('status-indicator').should('have.class', 'bg-green-500')
  })

  it('should change driver status to Busy', () => {
    cy.goToDriverPage('dashboard')
    cy.setDriverStatus('Ocupado')

    cy.getByTestId('current-status').should('contain', 'Ocupado')
    cy.getByTestId('status-indicator').should('have.class', 'bg-yellow-500')
  })

  it('should change driver status to Offline', () => {
    cy.goToDriverPage('dashboard')
    cy.setDriverStatus('Desconectado')

    cy.getByTestId('current-status').should('contain', 'Desconectado')
    cy.getByTestId('status-indicator').should('have.class', 'bg-gray-500')
  })

  it('should display earnings summary', () => {
    cy.goToDriverPage('dashboard')

    cy.getByTestId('earnings-today').within(() => {
      cy.contains('Hoy').should('be.visible')
      cy.get('.amount').should('be.visible')
    })

    cy.getByTestId('earnings-week').within(() => {
      cy.contains('Esta semana').should('be.visible')
      cy.get('.amount').should('be.visible')
    })
  })

  it('should display recent trips', () => {
    cy.goToDriverPage('dashboard')

    cy.getByTestId('recent-trips').should('be.visible')
    cy.getByTestId('recent-trips').within(() => {
      cy.contains('Viajes Recientes').should('be.visible')
    })
  })
})
