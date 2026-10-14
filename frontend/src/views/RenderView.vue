<script setup>
import { mdiRefresh, mdiSync } from '@mdi/js'
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
  <v-container fluid class="pa-4 pa-md-6">
    <div class="d-flex flex-wrap align-center ga-3 mb-4">
      <div>
        <h1 class="text-headline-small">Rendered config</h1>
        <p class="text-body-medium text-medium-emphasis">What dnsmasq will read from the conf dir.</p>
      </div>
      <v-spacer />
      <v-btn-toggle v-model="filter" mandatory density="compact" variant="outlined" divided color="secondary">
        <v-btn value="all">All</v-btn>
        <v-btn value="dns">DNS</v-btn>
        <v-btn value="dhcp">DHCP</v-btn>
      </v-btn-toggle>
      <v-btn :icon="mdiRefresh" variant="text" title="Reload" :loading="loading" @click="load" />
      <v-btn color="primary" variant="flat" :prepend-icon="mdiSync" @click="syncDialog = true">Sync to disk</v-btn>
    </div>

    <v-empty-state v-if="!loading && !files.length" title="Nothing to render" text="No config files exist yet." />

    <v-card v-for="file in files" :key="file.filename" rounded="xl" class="mb-4">
      <v-card-item>
        <v-card-title class="text-mono text-title-medium">{{ file.filename }}</v-card-title>
        <template #append>
          <v-chip size="small" label :color="file.kind === 'dns' ? 'secondary' : 'tertiary'">
            {{ file.kind.toUpperCase() }}
          </v-chip>
        </template>
      </v-card-item>
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
