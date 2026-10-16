<script setup>
/** dnsmasq status + restart in the sidebar. Renders nothing unless dnsmasq runs as systemd unit. */
import { RotateCw } from '@lucide/vue'
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { api } from '@/api'
import ConfirmDialog from './ConfirmDialog.vue'
import { notify } from '@/notify'

const REFRESH_MS = 30_000

const status = ref(null)
const confirmOpen = ref(false)
let timer

async function refresh() {
  try {
    status.value = await api.serviceStatus()
  } catch {
    status.value = null // backend unreachable - hide the control
  }
}

onMounted(() => {
  refresh()
  timer = setInterval(refresh, REFRESH_MS)
})
onBeforeUnmount(() => clearInterval(timer))

const stateColor = computed(
  () => ({ active: 'success', failed: 'error', activating: 'warning' })[status.value?.active_state] ?? 'surface-variant',
)

async function restart() {
  try {
    status.value = await api.restartService()
    notify(`${status.value.unit} restarted`)
  } finally {
    refresh()
  }
}
</script>

<template>
  <v-list v-if="status?.available" nav density="comfortable" class="px-3 pb-0">
    <v-list-subheader class="nav-heading">Service</v-list-subheader>
    <div class="status d-flex align-center ga-2 px-4 pb-2" :title="status.since ? `since ${status.since}` : undefined">
      <span class="dot" :class="`bg-${stateColor}`" />
      <span class="text-body-medium">{{ status.unit }}</span>
      <span class="text-body-medium text-medium-emphasis">{{ status.active_state }}</span>
    </div>
    <v-list-item :prepend-icon="RotateCw" title="Restart dnsmasq" role="button" rounded="lg" @click="confirmOpen = true" />

    <ConfirmDialog
      v-model="confirmOpen"
      title="Restart dnsmasq?"
      :text="`The configuration is checked with 'dnsmasq --test' first. Only if it is valid, ${status.unit} is restarted - DNS and DHCP are briefly unavailable.`"
      confirm-text="Restart"
      color="primary"
      :submit="restart"
    />
  </v-list>
</template>

<style scoped>
.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex: none;
}
</style>
