describe('Driver App - Authentication', () => {
  beforeEach(() => {
    cy.visit(Cypress.env('driverAppUrl'))
  })

  it('should display login page', () => {
    cy.url().should('include', '/login')
    cy.contains('Iniciar Sesión').should('be.visible')
    cy.get('input[name="email"]').should('be.visible')
    cy.get('input[name="password"]').should('be.visible')
  })

  it('should show error with invalid credentials', () => {
    cy.get('input[name="email"]').type('invalid@test.com')
    cy.get('input[name="password"]').type('wrongpassword')
    cy.get('button[type="submit"]').click()

    cy.contains('Credenciales inválidas').should('be.visible')
    cy.url().should('include', '/login')
  })

  it('should login successfully with valid credentials', () => {
    cy.loginDriver()

    // Verificar redirección al dashboard
    cy.url().should('include', '/dashboard')

    // Verificar que el token existe
    cy.window().its('localStorage').invoke('getItem', 'token').should('exist')

    // Verificar elementos del dashboard
    cy.contains('Bienvenido').should('be.visible')
    cy.getByTestId('driver-status').should('be.visible')
  })

  it('should logout successfully', () => {
    cy.loginDriver()
    cy.logout()

    // Verificar redirección al login
    cy.url().should('include', '/login')

    // Verificar que el token fue removido
    cy.window().its('localStorage').invoke('getItem', 'token').should('not.exist')
  })

  it('should persist authentication after page reload', () => {
    cy.loginDriver()
    cy.url().should('include', '/dashboard')

    // Recargar página
    cy.reload()

    // Debería seguir autenticado
    cy.url().should('include', '/dashboard')
    cy.window().its('localStorage').invoke('getItem', 'token').should('exist')
  })
})
