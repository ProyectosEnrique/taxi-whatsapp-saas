describe('Admin Panel - Manage Drivers', () => {
  beforeEach(() => {
    cy.loginAdmin()
    cy.goToAdminPage('drivers')
  })

  it('should display drivers list', () => {
    cy.url().should('include', '/drivers')
    cy.contains('Gestión de Conductores').should('be.visible')
    cy.getByTestId('drivers-table').should('be.visible')
  })

  it('should create new driver', () => {
    cy.createDriver({
      name: 'Juan Pérez',
      email: `driver-${Date.now()}@test.com`,
      phone: '+525512345678'
    })

    // Verificar que aparece en la lista
    cy.getByTestId('drivers-table').should('contain', 'Juan Pérez')
  })

  it('should edit driver information', () => {
    // Editar primer conductor
    cy.getByTestId('drivers-table').within(() => {
      cy.getByTestId('edit-driver-btn').first().click()
    })

    // Modificar nombre
    cy.get('input[name="name"]').clear().type('Carlos Rodríguez')
    cy.get('button[type="submit"]').click()

    // Verificar actualización
    cy.contains('Conductor actualizado').should('be.visible')
    cy.getByTestId('drivers-table').should('contain', 'Carlos Rodríguez')
  })

  it('should deactivate driver', () => {
    cy.getByTestId('drivers-table').within(() => {
      cy.getByTestId('deactivate-driver-btn').first().click()
    })

    cy.getByTestId('confirm-deactivate-modal').should('be.visible')
    cy.getByTestId('confirm-btn').click()

    cy.contains('Conductor desactivado').should('be.visible')
  })

  it('should filter drivers by status', () => {
    cy.getByTestId('filter-status').select('active')
    cy.wait(500)

    cy.getByTestId('drivers-table').within(() => {
      cy.get('tr').each(($row) => {
        cy.wrap($row).find('.status').should('contain', 'Activo')
      })
    })
  })
})
