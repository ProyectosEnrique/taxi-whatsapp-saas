<template>
  <div class="min-h-screen bg-white text-gray-800">
    <header class="bg-taxi-yellow">
      <div class="max-w-3xl mx-auto px-4 py-4 flex items-center justify-between">
        <router-link to="/" class="flex items-center gap-2 font-extrabold text-xl text-gray-900">
          <span class="text-2xl">🚕</span> TaxiCerca
        </router-link>
      </div>
    </header>

    <main class="max-w-3xl mx-auto px-4 py-8 leading-relaxed space-y-6">
      <h1 class="text-3xl font-bold text-gray-900">Aviso de privacidad</h1>
      <p class="text-sm text-gray-500">Última actualización: 2 de noviembre de 2026</p>

      <section>
        <h2 class="text-xl font-semibold text-gray-900">¿Quién es responsable de tus datos?</h2>
        <p>
          <b>Enrique Hernández Parra</b>, persona física con domicilio en Salvatierra, Guanajuato, México,
          que ofrece el servicio <b>TaxiCerca</b> (en adelante, "TaxiCerca"), es responsable del tratamiento
          de los datos personales que nos proporcionas, conforme a la Ley Federal de Protección de Datos
          Personales en Posesión de los Particulares.
        </p>
      </section>

      <section>
        <h2 class="text-xl font-semibold text-gray-900">¿Qué datos recabamos?</h2>
        <ul class="list-disc pl-6 space-y-1">
          <li><b>Pasajeros:</b> nombre, número de teléfono (WhatsApp), lugares de origen y destino, ubicación que decidas compartir, historial de viajes y forma de pago.</li>
          <li><b>Choferes:</b> nombre, teléfono, datos del vehículo (marca, modelo, color y placas) y ubicación mientras están disponibles para recibir viajes.</li>
        </ul>
        <p class="mt-2">
          No recabamos datos personales sensibles. Si pagas con tarjeta, el pago lo procesa Mercado Pago;
          TaxiCerca no recibe ni guarda los datos de tu tarjeta.
        </p>
      </section>

      <section>
        <h2 class="text-xl font-semibold text-gray-900">¿Para qué usamos tus datos?</h2>
        <p>Finalidades necesarias para darte el servicio:</p>
        <ul class="list-disc pl-6 space-y-1">
          <li>Recibir tu solicitud de taxi y calcular la tarifa.</li>
          <li>Conectarte con un chofer y una base de taxis aliada cercana.</li>
          <li>Avisarte quién va por ti, cuándo llega y cuándo termina tu viaje, y permitir el seguimiento en el mapa.</li>
          <li>Atender dudas, quejas, objetos olvidados y situaciones de seguridad o emergencia.</li>
          <li>Llevar el registro de viajes y los cortes con las bases de taxis.</li>
        </ul>
        <p class="mt-2">
          Finalidad adicional: avisarte de cambios en el servicio (por ejemplo, un nuevo número de WhatsApp).
          Si no deseas recibir estos avisos, escríbenos y dejaremos de enviarlos; esto no afecta tu servicio.
        </p>
      </section>

      <section>
        <h2 class="text-xl font-semibold text-gray-900">¿Con quién compartimos tus datos?</h2>
        <ul class="list-disc pl-6 space-y-1">
          <li><b>El chofer y la base de taxis</b> que atienden tu viaje: tu nombre, teléfono, origen y destino, para poder recogerte.</li>
          <li><b>Proveedores que nos ayudan a operar</b>, que solo usan los datos por cuenta nuestra: mensajería de WhatsApp (Meta y Twilio), notificaciones a choferes (Telegram), mapas (Google Maps y OpenStreetMap), pagos (Mercado Pago) y alojamiento del sistema.</li>
          <li><b>Autoridades</b>, cuando la ley lo exija o en caso de emergencia.</li>
        </ul>
        <p class="mt-2">No vendemos tus datos personales.</p>
      </section>

      <section>
        <h2 class="text-xl font-semibold text-gray-900">Tus derechos (ARCO)</h2>
        <p>
          Puedes pedir el <b>acceso</b>, la <b>rectificación</b> o la <b>cancelación</b> de tus datos, u
          <b>oponerte</b> a su uso, así como revocar tu consentimiento. Escríbenos por WhatsApp al
          <a :href="ownerLink" class="text-green-700 underline">477 199 9661</a> (solo mensajes) indicando tu nombre,
          el teléfono con el que usas TaxiCerca y lo que solicitas. Te responderemos en un máximo de 20 días hábiles.
        </p>
      </section>

      <section>
        <h2 class="text-xl font-semibold text-gray-900">Cambios a este aviso</h2>
        <p>Cualquier cambio a este aviso de privacidad se publicará en esta misma página.</p>
      </section>

      <p class="pt-4">
        <router-link to="/" class="text-green-700 font-semibold underline">← Volver a TaxiCerca</router-link>
      </p>
    </main>
  </div>
</template>

<script setup>
const ownerLink = `https://wa.me/524771999661?text=${encodeURIComponent('Hola, tengo una solicitud sobre mis datos en TaxiCerca')}`
</script>
