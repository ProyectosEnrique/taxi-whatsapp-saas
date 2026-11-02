<template>
  <div class="min-h-screen bg-white text-gray-900">
    <!-- Encabezado -->
    <header class="bg-gradient-to-br from-taxi-yellow to-yellow-500">
      <div class="max-w-3xl mx-auto px-4 pt-6 pb-12">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <img src="/logo-pin.svg" alt="" class="h-10 w-auto drop-shadow">
            <span class="text-2xl font-extrabold tracking-tight">Taxi<span class="text-white drop-shadow">Cerca</span></span>
          </div>
          <router-link to="/login" class="text-sm font-semibold bg-white/80 hover:bg-white rounded-full px-4 py-2">Entrar</router-link>
        </div>

        <h1 class="mt-10 text-4xl sm:text-5xl font-extrabold leading-tight">Pide tu taxi<br>por WhatsApp</h1>
        <p class="mt-4 text-lg max-w-xl">
          Escribe un mensaje y te conectamos con un taxi de una base aliada cerca de ti.
          Sin descargar aplicaciones.
        </p>
        <div class="mt-8 flex flex-col sm:flex-row gap-3">
          <a :href="waLink" target="_blank" rel="noopener"
             class="inline-flex items-center justify-center gap-2 bg-green-600 hover:bg-green-700 text-white font-bold text-lg rounded-xl px-6 py-4 shadow-lg">
            💬 Pedir taxi por WhatsApp
          </a>
          <router-link to="/login"
             class="inline-flex items-center justify-center bg-white hover:bg-gray-50 font-semibold rounded-xl px-6 py-4 shadow">
            Pedir desde esta página
          </router-link>
        </div>
      </div>
    </header>

    <main class="max-w-3xl mx-auto px-4">
      <!-- Cómo funciona -->
      <section class="py-12">
        <h2 class="text-2xl font-bold">¿Cómo funciona?</h2>
        <ol class="mt-6 space-y-4">
          <li v-for="(s, i) in steps" :key="i" class="flex gap-4 items-start">
            <span class="flex-none w-10 h-10 rounded-full bg-taxi-yellow font-extrabold flex items-center justify-center">{{ i + 1 }}</span>
            <div>
              <p class="font-semibold">{{ s.t }}</p>
              <p class="text-gray-600">{{ s.d }}</p>
            </div>
          </li>
        </ol>
      </section>

      <!-- Seguridad -->
      <section class="py-10 border-t">
        <h2 class="text-2xl font-bold">Viaja con tranquilidad</h2>
        <div class="mt-6 grid sm:grid-cols-3 gap-4">
          <div v-for="f in features" :key="f.t" class="rounded-xl bg-gray-50 p-4">
            <div class="text-3xl">{{ f.i }}</div>
            <p class="mt-2 font-semibold">{{ f.t }}</p>
            <p class="text-sm text-gray-600">{{ f.d }}</p>
          </div>
        </div>
      </section>

      <!-- Bases de taxis -->
      <section class="py-10 border-t">
        <h2 class="text-2xl font-bold">¿Tienes una base de taxis?</h2>
        <p class="mt-3 text-gray-700">
          TaxiCerca es una plataforma que conecta a los pasajeros con bases de taxis.
          Tus choferes reciben los viajes en su celular y aceptan con un botón.
          Tú sigues trabajando con tu fila, tu radio y tus tarifas.
        </p>
        <a :href="ownerLink" target="_blank" rel="noopener"
           class="mt-5 inline-flex items-center gap-2 font-semibold text-green-700 hover:underline">
          💬 Escríbenos: 477 199 9661 (solo mensajes)
        </a>
      </section>
    </main>

    <!-- Pie legal -->
    <footer class="bg-gray-900 text-gray-300 text-sm">
      <div class="max-w-3xl mx-auto px-4 py-8 space-y-2">
        <p class="text-white font-bold text-base flex items-center gap-2"><img src="/logo-pin.svg" alt="" class="h-6 w-auto"> TaxiCerca</p>
        <p>TaxiCerca es un servicio de <b>Enrique Hernández Parra</b> · Salvatierra, Guanajuato, México.</p>
        <p>
          TaxiCerca es una plataforma de comunicación: el viaje lo realizan los choferes y bases de taxis aliadas.
        </p>
        <p>
          WhatsApp para pedir taxi: <a :href="waLink" class="underline">+1 978 541 3145</a> ·
          Contacto: <a :href="ownerLink" class="underline">477 199 9661</a> (solo mensajes)
        </p>
        <p><router-link to="/privacidad" class="underline">Aviso de privacidad</router-link></p>
        <p class="text-gray-500">© {{ year }} TaxiCerca</p>
      </div>
    </footer>
  </div>
</template>

<script setup>
const TAXI_WA = '19785413145'
const OWNER_WA = '524771999661'

const waLink = `https://wa.me/${TAXI_WA}?text=${encodeURIComponent('Hola, quiero un taxi')}`
const ownerLink = `https://wa.me/${OWNER_WA}?text=${encodeURIComponent('Hola, me interesa TaxiCerca para mi base de taxis')}`
const year = new Date().getFullYear()

const steps = [
  { t: 'Escríbenos por WhatsApp', d: 'Dinos dónde estás y a dónde vas, o mándanos tu ubicación.' },
  { t: 'Te avisamos qué taxi va por ti', d: 'Recibes el nombre del chofer, el vehículo y las placas.' },
  { t: 'Sigue tu taxi en el mapa', d: 'Te avisamos cuando llegue y cuando termine el viaje.' },
]

const features = [
  { i: '🪪', t: 'Chofer identificado', d: 'Nombre, vehículo y placas antes de subirte.' },
  { i: '📍', t: 'Seguimiento en vivo', d: 'Comparte el link del viaje con tu familia.' },
  { i: '💵', t: 'Pago fácil', d: 'Paga en efectivo al chofer, o con tarjeta.' },
]
</script>
