<script setup>
import { Check, Copy } from '@lucide/vue'
import { ref } from 'vue'
import { notify } from '@/notify'

const props = defineProps({ code: { type: String, required: true } })
const copied = ref(false)

async function copy() {
  try {
    await navigator.clipboard.writeText(props.code)
    copied.value = true
    setTimeout(() => (copied.value = false), 1500)
  } catch {
    notify('Clipboard not available (requires HTTPS or localhost)', 'warning')
  }
}
</script>

<template>
  <div class="code-block">
    <v-btn
      class="copy-btn"
      :icon="copied ? Check : Copy"
      size="small"
      variant="text"
      title="Copy"
      aria-label="Copy to clipboard"
      @click="copy"
    />
    <pre>{{ code }}</pre>
  </div>
</template>

<style scoped>
.code-block {
  position: relative;
  border-radius: 12px;
  background: rgba(var(--v-theme-on-surface), 0.05);
}
.copy-btn {
  position: absolute;
  top: 4px;
  right: 4px;
}
pre {
  margin: 0;
  padding: 16px 48px 16px 16px;
  overflow-x: auto;
  font-family: var(--app-font-mono);
  font-size: 0.85rem;
  line-height: 1.55;
}
</style>
