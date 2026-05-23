<template>
  <div id="app">
    <!-- Router View - Contenido principal -->
    <router-view />

    <!-- Modal de Sofia (global) -->
    <VoiceAssistantModal />
  </div>
</template>

<script setup>
import VoiceAssistantModal from './components/VoiceAssistantModal.vue'
</script>

<style>
/* Reset y estilos base */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

#app {
  min-height: 100vh;
}
</style>
