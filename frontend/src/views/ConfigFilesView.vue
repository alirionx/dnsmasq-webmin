<script setup>
import { mdiDelete, mdiEye, mdiFileDocumentOutline, mdiPencil, mdiPlus } from '@mdi/js'
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
</script>

<template>
  <v-container fluid class="pa-4 pa-md-6">
    <v-row>
      <!-- file list -->
      <v-col cols="12" md="4" lg="3">
        <v-card rounded="xl" :loading="loading">
          <v-card-item>
            <v-card-title>{{ meta.title }}</v-card-title>
            <v-card-subtitle>Config files</v-card-subtitle>
            <template #append>
              <v-btn :icon="mdiPlus" variant="tonal" color="secondary" title="New config file" @click="openFileDialog()" />
            </template>
          </v-card-item>
          <v-list v-if="files.length" nav density="comfortable" class="pt-0">
            <v-list-item
              v-for="file in files"
              :key="file.name"
              :active="file.name === name"
              :title="file.name"
              :subtitle="file.description || file.filename"
              :prepend-icon="mdiFileDocumentOutline"
              rounded="lg"
              color="secondary"
              @click="select(file.name)"
            >
              <template #append>
                <v-badge :content="file.entries.length" inline color="surface-variant" />
              </template>
            </v-list-item>
          </v-list>
          <v-card-text v-else-if="!loading" class="text-medium-emphasis">
            No config files yet.
          </v-card-text>
        </v-card>
      </v-col>

      <!-- selected file -->
      <v-col cols="12" md="8" lg="9">
        <v-card v-if="selected" rounded="xl">
          <v-card-item>
            <v-card-title>{{ selected.name }}</v-card-title>
            <v-card-subtitle class="text-mono">{{ selected.filename }}</v-card-subtitle>
            <template #append>
              <div class="d-flex ga-1">
                <v-btn :icon="mdiEye" variant="text" title="Preview rendered file" @click="showPreview" />
                <v-btn :icon="mdiPencil" variant="text" title="Edit / rename" @click="openFileDialog(selected)" />
                <v-btn :icon="mdiDelete" variant="text" color="error" title="Delete file" @click="askDeleteFile" />
              </div>
            </template>
          </v-card-item>
          <v-card-text v-if="selected.description" class="pt-0 text-medium-emphasis">
            {{ selected.description }}
          </v-card-text>

          <v-divider />

          <div class="d-flex align-center px-4 py-3">
            <span class="text-title-medium">
              {{ selected.entries.length }} {{ selected.entries.length === 1 ? meta.entryLabel : meta.entryLabelPlural }}
            </span>
            <v-spacer />
            <v-btn color="primary" variant="flat" :prepend-icon="mdiPlus" @click="openEntryDialog()">
              Add {{ meta.entryLabel }}
            </v-btn>
          </div>

          <v-data-table
            :headers="meta.headers"
            :items="selected.entries"
            item-value="id"
            :items-per-page="-1"
            hide-default-footer
            density="comfortable"
            mobile-breakpoint="sm"
            :no-data-text="`No ${meta.entryLabelPlural} yet`"
          >
            <template #[`item.type`]="{ value }">
              <v-chip :color="dnsType(value)?.color" size="small" label>{{ dnsType(value)?.title ?? value }}</v-chip>
            </template>
            <template #[`item.comment`]="{ value }">
              <span class="text-medium-emphasis">{{ value }}</span>
            </template>
            <template #[`item.actions`]="{ item }">
              <v-btn :icon="mdiPencil" size="small" variant="text" title="Edit" @click="openEntryDialog(item)" />
              <v-btn :icon="mdiDelete" size="small" variant="text" color="error" title="Delete" @click="askDeleteEntry(item)" />
            </template>
          </v-data-table>
        </v-card>

        <v-empty-state
          v-else-if="!loading"
          :icon="meta.icon"
          :title="name ? `Config file '${name}' not found` : `Select a ${kind.toUpperCase()} config file`"
          :text="files.length ? 'Pick a file on the left or create a new one.' : 'Create your first config file to get started.'"
        >
          <template #actions>
            <v-btn color="primary" variant="flat" :prepend-icon="mdiPlus" @click="openFileDialog()">New config file</v-btn>
          </template>
        </v-empty-state>
      </v-col>
    </v-row>

    <FileDialog v-model="fileDialog.open" :file="fileDialog.file" :kind-label="kind.toUpperCase()" :submit="saveFile" />
    <component :is="EntryDialog" v-model="entryDialog.open" :entry="entryDialog.entry" :submit="saveEntry" />
    <ConfirmDialog v-model="confirm.open" :title="confirm.title" :text="confirm.text" :submit="confirm.action" />

    <v-dialog v-model="preview.open" max-width="760" scrollable>
      <v-card :title="preview.title" rounded="xl">
        <v-card-text><CodeBlock :code="preview.content" /></v-card-text>
        <v-card-actions class="px-6 pb-4">
          <v-spacer />
          <v-btn variant="text" @click="preview.open = false">Close</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>
