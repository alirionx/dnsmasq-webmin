<script setup>
import { HardDriveDownload, RefreshCw } from '@lucide/vue'
import { ref, watch } from 'vue'
import { api } from '@/api'
import CodeBlock from '@/components/CodeBlock.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import { notify, notifyError } from '@/notify'

const filter = ref('all')
const files = ref([])
const loading = ref(false)
const syncDialog = ref(false)

async function load() {
  loading.value = true
  try {
    files.value = await api.renderAll(filter.value === 'all' ? undefined : filter.value)
  } catch (err) {
    notifyError(err)
  } finally {
    loading.value = false
  }
}
watch(filter, load, { immediate: true })

async function sync() {
  const result = await api.sync()
  const removed = result.removed.length ? `, removed ${result.removed.length} orphaned` : ''
  notify(`Wrote ${result.written.length} files${removed}`)
}
</script>

<template>
  <v-container class="page">
    <div class="d-flex align-center flex-wrap ga-3 mb-6">
      <div>
        <h1 class="page-title">Rendered config</h1>
        <p class="text-body-medium text-medium-emphasis mt-1">What dnsmasq reads from the conf dir.</p>
      </div>
      <v-spacer />
      <v-btn-toggle v-model="filter" mandatory density="compact" variant="outlined" divided>
        <v-btn value="all">All</v-btn>
        <v-btn value="dns">DNS</v-btn>
        <v-btn value="dhcp">DHCP</v-btn>
      </v-btn-toggle>
      <v-btn :icon="RefreshCw" variant="text" aria-label="Reload" title="Reload" :loading="loading" @click="load" />
      <v-btn color="primary" variant="flat" size="large" :prepend-icon="HardDriveDownload" @click="syncDialog = true">
        Sync to disk
      </v-btn>
    </div>

    <v-card v-if="!loading && !files.length" class="panel" border flat>
      <v-empty-state title="Nothing to render" text="No config files exist yet." />
    </v-card>

    <v-card v-for="file in files" :key="file.filename" class="panel mb-4" border flat>
      <div class="d-flex align-center ga-3 px-4 pt-4">
        <span class="text-title-small text-mono text-truncate">{{ file.filename }}</span>
        <v-spacer />
        <v-chip size="small" variant="tonal" :color="file.kind === 'dns' ? 'primary' : 'secondary'">
          {{ file.kind.toUpperCase() }}
        </v-chip>
      </div>
      <v-card-text><CodeBlock :code="file.content" /></v-card-text>
    </v-card>

    <ConfirmDialog
      v-model="syncDialog"
      title="Sync all files to disk?"
      text="Rewrites every managed file in the conf dir and removes managed files that no longer exist here. Other files are not touched."
      confirm-text="Sync"
      color="primary"
      :submit="sync"
    />
  </v-container>
</template>
