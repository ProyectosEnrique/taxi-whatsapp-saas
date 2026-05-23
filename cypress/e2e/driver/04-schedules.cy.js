describe('Driver App - Schedules', () => {
  beforeEach(() => {
    cy.loginDriver()
    cy.goToDriverPage('schedules')
  })

  it('should display schedules page', () => {
    cy.url().should('include', '/schedules')
    cy.contains('Mis Horarios').should('be.visible')
    cy.getByTestId('weekly-view-tab').should('be.visible')
    cy.getByTestId('configure-tab').should('be.visible')
  })

  it('should show weekly schedule view', () => {
    cy.getByTestId('weekly-view-tab').click()

    // Verificar que se muestran los 7 días
    cy.getByTestId('schedule-calendar').within(() => {
      cy.contains('Lunes').should('be.visible')
      cy.contains('Martes').should('be.visible')
      cy.contains('Miércoles').should('be.visible')
      cy.contains('Jueves').should('be.visible')
      cy.contains('Viernes').should('be.visible')
      cy.contains('Sábado').should('be.visible')
      cy.contains('Domingo').should('be.visible')
    })
  })

  it('should create new schedule', () => {
    cy.getByTestId('configure-tab').click()

    // Seleccionar turno matutino
    cy.getByTestId('shift-template-morning').click()

    // Seleccionar días
    cy.get('input[type="checkbox"][value="lunes"]').check()
    cy.get('input[type="checkbox"][value="martes"]').check()
    cy.get('input[type="checkbox"][value="miercoles"]').check()

    // Configurar horario
    cy.get('input[name="start_time"]').clear().type('06:00')
    cy.get('input[name="end_time"]').clear().type('14:00')

    // Configurar descanso
    cy.get('input[type="checkbox"][name="has_break"]').check()
    cy.get('input[name="break_start"]').clear().type('10:00')
    cy.get('input[name="break_end"]').clear().type('10:30')

    // Guardar
    cy.getByTestId('save-schedule-btn').click()

    // Verificar mensaje de éxito
    cy.contains('Horarios guardados exitosamente').should('be.visible')

    // Verificar en vista semanal
    cy.getByTestId('weekly-view-tab').click()
    cy.getByTestId('schedule-monday').should('contain', '06:00 - 14:00')
    cy.getByTestId('schedule-tuesday').should('contain', '06:00 - 14:00')
    cy.getByTestId('schedule-wednesday').should('contain', '06:00 - 14:00')
  })

  it('should edit existing schedule', () => {
    // Primero crear un horario
    cy.getByTestId('configure-tab').click()
    cy.getByTestId('shift-template-afternoon').click()
    cy.get('input[type="checkbox"][value="jueves"]').check()
    cy.getByTestId('save-schedule-btn').click()

    // Editar
    cy.getByTestId('schedule-list').within(() => {
      cy.getByTestId('edit-schedule-btn').first().click()
    })

    // Modificar horario
    cy.get('input[name="start_time"]').clear().type('15:00')
    cy.get('input[name="end_time"]').clear().type('23:00')

    // Guardar cambios
    cy.getByTestId('update-schedule-btn').click()

    // Verificar actualización
    cy.contains('Horario actualizado').should('be.visible')
  })

  it('should delete schedule', () => {
    // Crear horario
    cy.getByTestId('configure-tab').click()
    cy.getByTestId('shift-template-night').click()
    cy.get('input[type="checkbox"][value="viernes"]').check()
    cy.getByTestId('save-schedule-btn').click()

    // Eliminar
    cy.getByTestId('schedule-list').within(() => {
      cy.getByTestId('delete-schedule-btn').first().click()
    })

    // Confirmar eliminación
    cy.getByTestId('confirm-delete-modal').should('be.visible')
    cy.getByTestId('confirm-delete-btn').click()

    // Verificar eliminación
    cy.contains('Horario eliminado').should('be.visible')
  })

  it('should use predefined shift templates', () => {
    cy.getByTestId('configure-tab').click()

    // Probar turno matutino
    cy.getByTestId('shift-template-morning').click()
    cy.get('input[name="start_time"]').should('have.value', '06:00')
    cy.get('input[name="end_time"]').should('have.value', '14:00')

    // Probar turno vespertino
    cy.getByTestId('shift-template-afternoon').click()
    cy.get('input[name="start_time"]').should('have.value', '14:00')
    cy.get('input[name="end_time"]').should('have.value', '22:00')

    // Probar turno nocturno
    cy.getByTestId('shift-template-night').click()
    cy.get('input[name="start_time"]').should('have.value', '22:00')
    cy.get('input[name="end_time"]').should('have.value', '06:00')
  })
})
