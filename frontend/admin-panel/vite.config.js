import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { VitePWA } from 'vite-plugin-pwa'

export default defineConfig({
  plugins: [
    vue(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['favicon.ico', 'icons/*.png'],
      manifest: {
        name: 'Admin Panel - Sistema de Taxi',
        short_name: 'Admin Panel',
        description: 'Panel administrativo para sistema de taxi',
        theme_color: '#3B82F6',
        background_color: '#ffffff',
        display: 'standalone',
        orientation: 'any',
        scope: '/',
        start_url: '/',
        icons: [
          {
            src: '/icons/icon-192x192.png',
            sizes: '192x192',
            type: 'image/png'
          },
          {
            src: '/icons/icon-512x512.png',
            sizes: '512x512',
            type: 'image/png',
            purpose: 'any maskable'
          }
        ]
      },
      workbox: {
        globPatterns: ['**/*.{js,css,html,ico,png,svg,woff2}'],
        runtimeCaching: [
          {
            urlPattern: /^https:\/\/.*\.(json)$/,
            handler: 'NetworkFirst',
            options: {
              cacheName: 'api-cache',
              expiration: {
                maxEntries: 50,
                maxAgeSeconds: 5 * 60
              }
            }
          }
        ]
      }
    })
  ],
  server: {
    port: 8083,
    proxy: {
      '/api/v1/orders': {
        target: 'http://localhost:5012',
        changeOrigin: true
      },
      '/api/v1/tables': {
        target: 'http://localhost:5013',
        changeOrigin: true
      },
      '/api/v1/users': {
        target: 'http://localhost:5014',
        changeOrigin: true
      },
      '/api/v1/categories': {
        target: 'http://localhost:5011',
        changeOrigin: true
      },
      '/api/v1/products': {
        target: 'http://localhost:5011',
        changeOrigin: true
      }
    }
  }
})
