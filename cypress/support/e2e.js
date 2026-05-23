// ***********************************************************
// Support file for E2E tests
// ***********************************************************

import './commands'

// Configuración global
Cypress.on('uncaught:exception', (err, runnable) => {
  // Prevenir que errores de aplicación fallen los tests
  // Excepto errores críticos
  if (err.message.includes('ResizeObserver')) {
    return false
  }
  if (err.message.includes('Script error')) {
    return false
  }
  // Permitir que otros errores fallen el test
  return true
})

// Configuración antes de cada test
beforeEach(() => {
  // Limpiar localStorage y cookies
  cy.clearLocalStorage()
  cy.clearCookies()

  // Log del test actual
  cy.log(`Running test: ${Cypress.currentTest.title}`)
})

// Configuración después de cada test
afterEach(function() {
  // Screenshot si el test falla
  if (this.currentTest.state === 'failed') {
    cy.screenshot(`${this.currentTest.title} - FAILED`, {
      capture: 'fullPage'
    })
  }
})

// Helpers globales
Cypress.Commands.add('getByTestId', (testId) => {
  return cy.get(`[data-testid="${testId}"]`)
})

Cypress.Commands.add('waitForPageLoad', () => {
  cy.window().its('document.readyState').should('equal', 'complete')
})
