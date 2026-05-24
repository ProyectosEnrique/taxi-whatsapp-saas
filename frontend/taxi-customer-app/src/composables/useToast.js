import { ref } from 'vue'

// Singleton: estado compartido por toda la app
const _toast = ref(null)
let _timer = null

export function useToast() {
  function show(type, message, duration = 3500) {
    if (_timer) clearTimeout(_timer)
    _toast.value = { type, message }
    _timer = setTimeout(() => { _toast.value = null }, duration)
  }
  function success(message, duration) { show('success', message, duration) }
  function error(message, duration)   { show('error',   message, duration) }
  function info(message, duration)    { show('info',    message, duration) }

  return { toast: _toast, show, success, error, info }
}
