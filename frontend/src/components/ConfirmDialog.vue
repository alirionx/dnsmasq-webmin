<script setup>
import FormDialog from './FormDialog.vue'

defineProps({
  title: { type: String, required: true },
  text: { type: String, default: '' },
  confirmText: { type: String, default: 'Delete' },
  color: { type: String, default: 'error' },
  submit: { type: Function, required: true },
})
const open = defineModel({ type: Boolean, default: false })
</script>

<template>
  <FormDialog v-model="open" :title="title" :submit="submit" :submit-text="confirmText" :submit-color="color" max-width="440">
    <p class="text-body-medium">{{ text }}</p>
  </FormDialog>
</template>
