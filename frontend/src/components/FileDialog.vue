<script setup>
import { computed, ref, watch } from 'vue'
import FormDialog from './FormDialog.vue'
import { orNull, rules } from '@/rules'

const props = defineProps({
  file: { type: Object, default: null }, // null = create
  kindLabel: { type: String, required: true },
  submit: { type: Function, required: true },
})
const open = defineModel({ type: Boolean, default: false })

const name = ref('')
const description = ref('')

watch(open, (isOpen) => {
  if (!isOpen) return
  name.value = props.file?.name ?? ''
  description.value = props.file?.description ?? ''
})

const renamed = computed(() => props.file && name.value !== props.file.name)

function save() {
  return props.submit({ name: name.value, description: orNull(description.value) })
}
</script>

<template>
  <FormDialog
    v-model="open"
    :title="file ? `Edit ${kindLabel} config file` : `New ${kindLabel} config file`"
    :submit="save"
    :submit-text="file ? 'Save' : 'Create'"
  >
    <v-text-field
      v-model="name"
      label="Name"
      :rules="[rules.required, rules.fileName]"
      hint="Used in the file name, e.g. home-lan"
      persistent-hint
      autofocus
      class="mb-3"
    />
    <v-text-field
      v-model="description"
      label="Description"
      :rules="[rules.singleLine]"
      hint="Written as comment into the file header"
      persistent-hint
    />
    <v-alert
      v-if="renamed"
      type="info"
      variant="tonal"
      density="compact"
      class="mt-4"
      text="Renaming also renames the file in the dnsmasq conf dir."
    />
  </FormDialog>
</template>
