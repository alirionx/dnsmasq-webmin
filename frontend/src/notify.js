import { reactive } from 'vue'

/** Global snackbar state, rendered once in App.vue. */
export const snackbar = reactive({ show: false, text: '', color: 'success' })

export function notify(text, color = 'success') {
  Object.assign(snackbar, { show: true, text, color })
}

export function notifyError(err) {
  notify(err?.message ?? String(err), 'error')
}
