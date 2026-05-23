<template>
  <div class="container mx-auto px-4 py-8 max-w-3xl">
    <h1 class="text-3xl font-bold text-center mb-8">Calificar Pedido</h1>

    <!-- Loading State -->
    <div v-if="loading" class="text-center py-12">
      <div class="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mb-4"></div>
      <p class="text-gray-600">Cargando información del pedido...</p>
    </div>

    <!-- Success State -->
    <div v-else-if="submitted" class="text-center py-12">
      <div class="w-16 h-16 bg-green-100 rounded-full mx-auto mb-4 flex items-center justify-center">
        <svg class="w-10 h-10 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
        </svg>
      </div>
      <h2 class="text-2xl font-bold mb-2">¡Gracias por tu Opinión!</h2>
      <p class="text-gray-600 mb-6">Tu reseña nos ayuda a mejorar nuestro servicio</p>
      <div class="flex space-x-4 justify-center">
        <router-link to="/order-history" class="btn-secondary">
          Ver Mis Pedidos
        </router-link>
        <router-link to="/" class="btn-primary">
          Hacer Otro Pedido
        </router-link>
      </div>
    </div>

    <!-- Review Form -->
    <form v-else @submit.prevent="handleSubmit" class="space-y-6">
      <!-- Order Info -->
      <div v-if="order" class="card bg-gray-50">
        <div class="flex items-start justify-between">
          <div>
            <h3 class="font-bold">Pedido #{{ order.order_id }}</h3>
            <p class="text-sm text-gray-600">{{ formatDate(order.created_at) }}</p>
          </div>
          <span class="text-2xl font-bold text-primary-600">
            ${{ order.total?.toFixed(2) }}
          </span>
        </div>
      </div>

      <!-- Food Quality Rating -->
      <div class="card">
        <h3 class="font-medium mb-3">Calidad de la Comida</h3>
        <div class="flex items-center space-x-2">
          <button
            v-for="star in 5"
            :key="star"
            type="button"
            @click="reviewForm.food_quality = star"
            class="focus:outline-none transition-transform hover:scale-110"
          >
            <svg
              :class="[
                'w-10 h-10',
                star <= reviewForm.food_quality ? 'text-yellow-400 fill-current' : 'text-gray-300'
              ]"
              viewBox="0 0 20 20"
            >
              <path d="M10 15l-5.878 3.09 1.123-6.545L.489 6.91l6.572-.955L10 0l2.939 5.955 6.572.955-4.756 4.635 1.123 6.545z"/>
            </svg>
          </button>
          <span class="ml-4 font-medium">
            {{ getRatingText(reviewForm.food_quality) }}
          </span>
        </div>
      </div>

      <!-- Delivery Time Rating -->
      <div class="card">
        <h3 class="font-medium mb-3">Tiempo de Entrega</h3>
        <div class="flex items-center space-x-2">
          <button
            v-for="star in 5"
            :key="star"
            type="button"
            @click="reviewForm.delivery_time = star"
            class="focus:outline-none transition-transform hover:scale-110"
          >
            <svg
              :class="[
                'w-10 h-10',
                star <= reviewForm.delivery_time ? 'text-yellow-400 fill-current' : 'text-gray-300'
              ]"
              viewBox="0 0 20 20"
            >
              <path d="M10 15l-5.878 3.09 1.123-6.545L.489 6.91l6.572-.955L10 0l2.939 5.955 6.572.955-4.756 4.635 1.123 6.545z"/>
            </svg>
          </button>
          <span class="ml-4 font-medium">
            {{ getRatingText(reviewForm.delivery_time) }}
          </span>
        </div>
      </div>

      <!-- Service Rating -->
      <div class="card">
        <h3 class="font-medium mb-3">Servicio</h3>
        <div class="flex items-center space-x-2">
          <button
            v-for="star in 5"
            :key="star"
            type="button"
            @click="reviewForm.service = star"
            class="focus:outline-none transition-transform hover:scale-110"
          >
            <svg
              :class="[
                'w-10 h-10',
                star <= reviewForm.service ? 'text-yellow-400 fill-current' : 'text-gray-300'
              ]"
              viewBox="0 0 20 20"
            >
              <path d="M10 15l-5.878 3.09 1.123-6.545L.489 6.91l6.572-.955L10 0l2.939 5.955 6.572.955-4.756 4.635 1.123 6.545z"/>
            </svg>
          </button>
          <span class="ml-4 font-medium">
            {{ getRatingText(reviewForm.service) }}
          </span>
        </div>
      </div>

      <!-- Comments -->
      <div class="card">
        <h3 class="font-medium mb-3">Comentarios (Opcional)</h3>
        <textarea
          v-model="reviewForm.comment"
          class="input"
          rows="4"
          placeholder="Cuéntanos sobre tu experiencia..."
        ></textarea>
      </div>

      <!-- Photo Upload -->
      <div class="card">
        <h3 class="font-medium mb-3">Agregar Foto (Opcional)</h3>

        <div v-if="!imagePreview" class="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center">
          <input
            ref="fileInput"
            type="file"
            accept="image/*"
            @change="handleImageSelect"
            class="hidden"
          />
          <button
            type="button"
            @click="$refs.fileInput.click()"
            class="btn-secondary"
          >
            <svg class="w-5 h-5 mr-2 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
            Seleccionar Foto
          </button>
          <p class="text-xs text-gray-500 mt-2">JPG, PNG (máx. 5MB)</p>
        </div>

        <div v-else class="relative">
          <img :src="imagePreview" class="w-full h-64 object-cover rounded-lg" />
          <button
            type="button"
            @click="removeImage"
            class="absolute top-2 right-2 bg-red-500 text-white p-2 rounded-full hover:bg-red-600"
          >
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>

      <!-- Submit Button -->
      <div class="flex space-x-4">
        <router-link to="/order-history" class="btn-secondary flex-1">
          Cancelar
        </router-link>
        <button
          type="submit"
          :disabled="!canSubmit || reviewsStore.loading"
          class="btn-primary flex-1"
        >
          <span v-if="!reviewsStore.loading">Enviar Reseña</span>
          <span v-else>Enviando...</span>
        </button>
      </div>
    </form>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useReviewsStore } from '@/stores/reviews'
import { useOrdersStore } from '@/stores/orders'

const route = useRoute()
const router = useRouter()
const reviewsStore = useReviewsStore()
const ordersStore = useOrdersStore()

const orderId = ref(route.params.orderId)
const order = ref(null)
const loading = ref(false)
const submitted = ref(false)

const reviewForm = ref({
  food_quality: 0,
  delivery_time: 0,
  service: 0,
  comment: ''
})

const selectedImage = ref(null)
const imagePreview = ref(null)

const canSubmit = computed(() => {
  return reviewForm.value.food_quality > 0 &&
         reviewForm.value.delivery_time > 0 &&
         reviewForm.value.service > 0
})

const averageRating = computed(() => {
  const sum = reviewForm.value.food_quality +
              reviewForm.value.delivery_time +
              reviewForm.value.service
  return Math.round(sum / 3)
})

function getRatingText(rating) {
  const texts = {
    0: '',
    1: 'Muy malo',
    2: 'Malo',
    3: 'Regular',
    4: 'Bueno',
    5: 'Excelente'
  }
  return texts[rating] || ''
}

function formatDate(dateString) {
  const date = new Date(dateString)
  return date.toLocaleDateString('es-MX', {
    day: '2-digit',
    month: 'long',
    year: 'numeric'
  })
}

function handleImageSelect(event) {
  const file = event.target.files[0]
  if (!file) return

  // Validate file size (5MB)
  if (file.size > 5 * 1024 * 1024) {
    alert('La imagen es muy grande. Máximo 5MB.')
    return
  }

  selectedImage.value = file

  // Preview
  const reader = new FileReader()
  reader.onload = (e) => {
    imagePreview.value = e.target.result
  }
  reader.readAsDataURL(file)
}

function removeImage() {
  selectedImage.value = null
  imagePreview.value = null
}

async function handleSubmit() {
  if (!canSubmit.value) return

  try {
    let imageUrl = null

    // Upload image if selected
    if (selectedImage.value) {
      imageUrl = await reviewsStore.uploadReviewImage(selectedImage.value)
    }

    // Submit review
    const reviewData = {
      order_id: orderId.value,
      food_quality: reviewForm.value.food_quality,
      delivery_time: reviewForm.value.delivery_time,
      service: reviewForm.value.service,
      rating: averageRating.value,
      comment: reviewForm.value.comment,
      image_url: imageUrl
    }

    const result = await reviewsStore.submitReview(reviewData)

    if (result.success) {
      submitted.value = true
    } else {
      alert(result.error || 'Error al enviar la reseña')
    }
  } catch (error) {
    console.error('Error submitting review:', error)
    alert('Error al enviar la reseña')
  }
}

onMounted(async () => {
  try {
    loading.value = true
    order.value = await ordersStore.loadOrder(orderId.value)
  } catch (error) {
    console.error('Error loading order:', error)
    router.push('/order-history')
  } finally {
    loading.value = false
  }
})
</script>
