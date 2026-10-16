<script setup>
import { Eye, FileText, Pencil, Plus, Trash2 } from '@lucide/vue'
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '@/api'
import CodeBlock from '@/components/CodeBlock.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import DhcpRangeDialog from '@/components/DhcpRangeDialog.vue'
import DnsEntryDialog from '@/components/DnsEntryDialog.vue'
import FileDialog from '@/components/FileDialog.vue'
import { DNS_TYPES, KINDS } from '@/kinds'
import { notify, notifyError } from '@/notify'

const props = defineProps({
  kind: { type: String, required: true },
  name: { type: String, default: undefined },
})
const router = useRouter()

const meta = computed(() => KINDS[props.kind])
const files = ref([])
const loading = ref(false)
const selected = computed(() => files.value.find((f) => f.name === props.name) ?? null)
const EntryDialog = computed(() => (props.kind === 'dns' ? DnsEntryDialog : DhcpRangeDialog))

async function load() {
  loading.value = true
  try {
    files.value = await api.listFiles(props.kind)
  } catch (err) {
    notifyError(err)
  } finally {
    loading.value = false
  }
}
watch(() => props.kind, load, { immediate: true })

const select = (name) => router.push({ name: props.kind, params: { name } })

// -- config files ------------------------------------------------------------

const fileDialog = ref({ open: false, file: null })
const openFileDialog = (file = null) => (fileDialog.value = { open: true, file })

async function saveFile(data) {
  const current = fileDialog.value.file
  const saved = current
    ? await api.updateFile(props.kind, current.name, data)
    : await api.createFile(props.kind, data)
  await load()
  select(saved.name)
  notify(current ? `Saved ${saved.filename}` : `Created ${saved.filename}`)
}

// -- entries -----------------------------------------------------------------

const entryDialog = ref({ open: false, entry: null })
const openEntryDialog = (entry = null) => (entryDialog.value = { open: true, entry })

async function saveEntry(data) {
  const { name } = selected.value
  const current = entryDialog.value.entry
  if (current) await api.replaceEntry(props.kind, name, current.id, data)
  else await api.addEntry(props.kind, name, data)
  await load()
  notify(`${meta.value.entryLabel} ${current ? 'updated' : 'added'}`)
}

// -- delete confirmation -----------------------------------------------------

const confirm = ref({ open: false, title: '', text: '', action: async () => {} })

function askDeleteFile() {
  const file = selected.value
  confirm.value = {
    open: true,
    title: 'Delete config file?',
    text: `${file.filename} with ${file.entries.length} entries will be removed from the conf dir.`,
    action: async () => {
      await api.deleteFile(props.kind, file.name)
      await router.push({ name: props.kind })
      await load()
      notify(`Deleted ${file.filename}`)
    },
  }
}

function askDeleteEntry(entry) {
  confirm.value = {
    open: true,
    title: `Delete ${meta.value.entryLabel}?`,
    text: entry.comment ? `"${entry.comment}"` : 'This entry will be removed from the file.',
    action: async () => {
      await api.deleteEntry(props.kind, selected.value.name, entry.id)
      await load()
      notify(`${meta.value.entryLabel} deleted`)
    },
  }
}

// -- render preview ----------------------------------------------------------

const preview = ref({ open: false, title: '', content: '' })

async function showPreview() {
  try {
    const content = await api.renderFile(props.kind, selected.value.name)
    preview.value = { open: true, title: selected.value.filename, content }
  } catch (err) {
    notifyError(err)
  }
}

const dnsType = (type) => DNS_TYPES.find((t) => t.value === type)
const entryCount = computed(() => files.value.reduce((sum, f) => sum + f.entries.length, 0))
const plural = (n, one, many) => `${n} ${n === 1 ? one : many}`
</script>

<template>
  <v-container class="page">
    <div class="d-flex align-center flex-wrap ga-3 mb-6">
      <div>
        <h1 class="page-title">{{ meta.title }}</h1>
        <p class="text-body-medium text-medium-emphasis mt-1">
          {{ plural(files.length, 'config file', 'config files') }} ·
          {{ plural(entryCount, meta.entryLabel, meta.entryLabelPlural) }}
        </p>
      </div>
      <v-spacer />
      <v-btn color="primary" variant="flat" size="large" :prepend-icon="Plus" @click="openFileDialog()">
        New config file
      </v-btn>
    </div>

    <v-row>
      <!-- file list -->
      <v-col cols="12" md="4">
        <v-card class="panel" border flat :loading="loading">
          <v-list v-if="files.length" nav density="comfortable" class="files">
            <v-list-subheader class="nav-heading">Config files</v-list-subheader>
            <v-list-item
              v-for="file in files"
              :key="file.name"
              :active="file.name === name"
              :title="file.name"
              :subtitle="file.description || file.filename"
              :prepend-icon="FileText"
              rounded="lg"
              @click="select(file.name)"
            >
              <template #append>
                <span class="count">{{ file.entries.length }}</span>
              </template>
            </v-list-item>
          </v-list>
          <v-card-text v-else-if="!loading" class="text-medium-emphasis">No config files yet.</v-card-text>
        </v-card>
      </v-col>

      <!-- selected file -->
      <v-col cols="12" md="8">
        <v-card v-if="selected" class="panel" border flat>
          <div class="d-flex align-center ga-3 pa-4">
            <span class="icon-tile" aria-hidden="true"><component :is="meta.icon" :size="20" /></span>
            <div class="min-w-0">
              <div class="text-title-medium font-weight-bold text-truncate">{{ selected.name }}</div>
              <div class="text-body-medium text-medium-emphasis text-mono text-truncate">{{ selected.filename }}</div>
            </div>
            <v-spacer />
            <v-btn :icon="Eye" variant="text" size="small" aria-label="Preview rendered file" title="Preview rendered file" @click="showPreview" />
            <v-btn :icon="Pencil" variant="text" size="small" aria-label="Edit or rename" title="Edit / rename" @click="openFileDialog(selected)" />
            <v-btn :icon="Trash2" variant="text" size="small" color="secondary" aria-label="Delete file" title="Delete file" @click="askDeleteFile" />
          </div>
          <p v-if="selected.description" class="text-body-medium text-medium-emphasis px-4 mt-n2 mb-4">
            {{ selected.description }}
          </p>

          <v-divider />

          <div class="d-flex align-center px-4 py-3">
            <span class="text-title-small">
              {{ plural(selected.entries.length, meta.entryLabel, meta.entryLabelPlural) }}
            </span>
            <v-spacer />
            <v-btn color="primary" variant="flat" :prepend-icon="Plus" @click="openEntryDialog()">
              Add {{ meta.entryLabel }}
            </v-btn>
          </div>

          <v-data-table
            :headers="meta.headers"
            :items="selected.entries"
            item-value="id"
            :items-per-page="-1"
            hide-default-footer
            hover
            mobile-breakpoint="sm"
            :no-data-text="`No ${meta.entryLabelPlural} yet`"
          >
            <template #[`item.type`]="{ value }">
              <v-chip :color="dnsType(value)?.color" size="small" variant="tonal">{{ dnsType(value)?.title ?? value }}</v-chip>
            </template>
            <template #[`item.comment`]="{ value }">
              <span class="text-medium-emphasis">{{ value }}</span>
            </template>
            <template #[`item.actions`]="{ item }">
              <div class="d-flex justify-end">
                <v-btn :icon="Pencil" size="small" variant="text" aria-label="Edit" title="Edit" @click="openEntryDialog(item)" />
                <v-btn :icon="Trash2" size="small" variant="text" color="secondary" aria-label="Delete" title="Delete" @click="askDeleteEntry(item)" />
              </div>
            </template>
          </v-data-table>
        </v-card>

        <v-card v-else-if="!loading" class="panel" border flat>
          <v-empty-state
            :icon="meta.icon"
            :title="name ? `Config file '${name}' not found` : `Select a ${kind.toUpperCase()} config file`"
            :text="files.length ? 'Pick a file from the list or create a new one.' : 'Create your first config file to get started.'"
          />
        </v-card>
      </v-col>
    </v-row>

    <FileDialog v-model="fileDialog.open" :file="fileDialog.file" :kind-label="kind.toUpperCase()" :submit="saveFile" />
    <component :is="EntryDialog" v-model="entryDialog.open" :entry="entryDialog.entry" :submit="saveEntry" />
    <ConfirmDialog v-model="confirm.open" :title="confirm.title" :text="confirm.text" :submit="confirm.action" />

    <v-dialog v-model="preview.open" max-width="760" scrollable>
      <v-card :title="preview.title">
        <v-card-text><CodeBlock :code="preview.content" /></v-card-text>
        <v-card-actions class="px-6 pb-4">
          <v-spacer />
          <v-btn @click="preview.open = false">Close</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<style scoped>
.files :deep(.v-list-item--active) {
  background: rgb(var(--v-theme-surface-variant));
  color: rgb(var(--v-theme-on-surface));
}
.files :deep(.v-list-item--active .v-list-item__overlay) {
  opacity: 0;
}
.files :deep(.v-list-item--active .v-icon) {
  color: rgb(var(--v-theme-primary));
}
.count {
  font-size: 0.75rem;
  font-weight: 600;
  min-width: 1.6rem;
  padding: 0 0.45rem;
  border-radius: 999px;
  text-align: center;
  background: rgba(var(--v-theme-on-surface), 0.08);
}
.min-w-0 {
  min-width: 0;
}
</style>
