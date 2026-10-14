<script setup>
/** dnsmasq status chip + restart button. Renders nothing unless dnsmasq runs as systemd unit. */
import { mdiRestart } from '@mdi/js'
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

const stateColor = computed(() => ({ active: 'success', failed: 'error', activating: 'warning' })[status.value?.active_state] ?? 'grey')

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
  <template v-if="status?.available">
    <v-chip
      class="mr-1 d-none d-sm-flex"
      size="small"
      variant="tonal"
      :title="status.since ? `since ${status.since}` : undefined"
    >
      <v-badge dot inline :color="stateColor" class="mr-1" />
      dnsmasq {{ status.active_state }}
    </v-chip>
    <v-btn :icon="mdiRestart" title="Restart dnsmasq" @click="confirmOpen = true" />

    <ConfirmDialog
      v-model="confirmOpen"
      title="Restart dnsmasq?"
      :text="`The configuration is checked with 'dnsmasq --test' first. Only if it is valid, ${status.unit} is restarted - DNS and DHCP are briefly unavailable.`"
      confirm-text="Restart"
      color="primary"
      :submit="restart"
    />
  </template>
</template>
