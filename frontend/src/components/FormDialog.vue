<script setup>
/**
 * Dialog shell for forms: validates, calls the async `submit` prop,
 * shows a spinner while saving and the server error if it fails.
 */
import { ref, watch } from 'vue'

const props = defineProps({
  title: { type: String, required: true },
  submit: { type: Function, required: true },
  submitText: { type: String, default: 'Save' },
  submitColor: { type: String, default: 'primary' },
  maxWidth: { type: [Number, String], default: 560 },
})
const open = defineModel({ type: Boolean, default: false })

const form = ref(null)
const saving = ref(false)
const error = ref('')

watch(open, (isOpen) => {
  if (isOpen) error.value = ''
})

async function onSubmit() {
  const { valid } = (await form.value?.validate()) ?? { valid: true }
  if (!valid) return
  saving.value = true
  error.value = ''
  try {
    await props.submit()
    open.value = false
  } catch (err) {
    error.value = err.message
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <v-dialog v-model="open" :max-width="maxWidth" :persistent="saving" scrollable>
    <v-card :title="title">
      <v-card-text class="pt-2">
        <v-form ref="form" @submit.prevent="onSubmit">
          <slot />
          <!-- hidden submit so Enter in a text field submits the form -->
          <button type="submit" hidden />
        </v-form>
        <v-alert
          v-if="error"
          type="error"
          variant="tonal"
          density="compact"
          class="mt-2 error-text"
          :text="error"
        />
      </v-card-text>
      <v-card-actions class="px-6 pb-4">
        <v-spacer />
        <v-btn :disabled="saving" @click="open = false">Cancel</v-btn>
        <v-btn :color="submitColor" variant="flat" :loading="saving" @click="onSubmit">{{ submitText }}</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<style scoped>
.error-text :deep(.v-alert__content) {
  white-space: pre-line;
}
</style>
