const { defineConfig } = require('cypress')

module.exports = defineConfig({
  e2e: {
    baseUrl: 'http://localhost:3002', // Driver app por defecto
    specPattern: 'cypress/e2e/**/*.cy.{js,jsx,ts,tsx}',
    supportFile: 'cypress/support/e2e.js',
    videosFolder: 'cypress/videos',
    screenshotsFolder: 'cypress/screenshots',
    fixturesFolder: 'cypress/fixtures',

    // Configuración de timeouts
    defaultCommandTimeout: 10000,
    requestTimeout: 10000,
    responseTimeout: 10000,
    pageLoadTimeout: 30000,

    // Configuración de viewport
    viewportWidth: 1280,
    viewportHeight: 720,

    // Configuración de video y screenshots
    video: true,
    videoCompression: 32,
    screenshotOnRunFailure: true,

    // Retry fallidos
    retries: {
      runMode: 2,
      openMode: 0
    },

    setupNodeEvents(on, config) {
      // Plugin para manejo de variables de entorno
      require('dotenv').config()

      // Plugin para reportes
      on('after:run', (results) => {
        if (results) {
          console.log('==================================')
          console.log('       TEST RUN SUMMARY')
          console.log('==================================')
          console.log(`Total Tests: ${results.totalTests}`)
          console.log(`Passed: ${results.totalPassed}`)
          console.log(`Failed: ${results.totalFailed}`)
          console.log(`Skipped: ${results.totalSkipped}`)
          console.log(`Duration: ${results.totalDuration}ms`)
          console.log('==================================')
        }
      })

      return config
    },
  },

  // Configuración de component testing (opcional para futuro)
  component: {
    devServer: {
      framework: 'vue',
      bundler: 'vite',
    },
    specPattern: 'src/**/*.cy.{js,jsx,ts,tsx}',
  },

  // Variables de entorno
  env: {
    apiUrl: 'http://localhost:8000/api/v1',
    driverAppUrl: 'http://localhost:3002',
    customerAppUrl: 'http://localhost:3004',
    adminPanelUrl: 'http://localhost:8083',
  },
})
