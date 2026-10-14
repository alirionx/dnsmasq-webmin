<script setup>
import { computed, reactive, watch } from 'vue'
import FormDialog from './FormDialog.vue'
import { isIPv6, orNull, rules } from '@/rules'

const props = defineProps({
  entry: { type: Object, default: null }, // null = create
  submit: { type: Function, required: true },
})
const open = defineModel({ type: Boolean, default: false })

const LEASE_SUGGESTIONS = ['1h', '12h', '24h', '7d', 'infinite']

const blank = () => ({
  start: '', end: '', netmask: '', prefix_length: '', lease_time: '12h', match_tags: [], set_tag: '', comment: '',
})
const form = reactive(blank())

watch(open, (isOpen) => {
  if (!isOpen) return
  const e = props.entry
  Object.assign(form, blank(), e && {
    ...e,
    netmask: e.netmask ?? '',
    prefix_length: e.prefix_length ?? '',
    lease_time: e.lease_time ?? '',
    set_tag: e.set_tag ?? '',
    comment: e.comment ?? '',
  })
})

const v6 = computed(() => isIPv6(form.start))
const sameFamily = (v) => !v || !form.start || isIPv6(v) === v6.value || 'Start and end must be the same IP version'

function save() {
  return props.submit({
    start: form.start,
    end: form.end,
    netmask: v6.value ? null : orNull(form.netmask),
    prefix_length: v6.value && form.prefix_length !== '' ? Number(form.prefix_length) : null,
    lease_time: orNull(form.lease_time),
    match_tags: form.match_tags,
    set_tag: orNull(form.set_tag),
    comment: orNull(form.comment),
  })
}
</script>

<template>
  <FormDialog v-model="open" :title="entry ? 'Edit DHCP range' : 'New DHCP range'" :submit="save">
    <v-row dense>
      <v-col cols="12" sm="6">
        <v-text-field v-model="form.start" label="Start" placeholder="192.168.1.100" :rules="[rules.required, rules.ip]" autofocus />
      </v-col>
      <v-col cols="12" sm="6">
        <v-text-field v-model="form.end" label="End" placeholder="192.168.1.200" :rules="[rules.required, rules.ip, sameFamily]" />
      </v-col>
      <v-col cols="12" sm="6">
        <v-text-field
          v-if="v6"
          v-model="form.prefix_length"
          label="Prefix length"
          type="number"
          min="64"
          max="128"
          placeholder="64"
        />
        <v-text-field v-else v-model="form.netmask" label="Netmask" placeholder="255.255.255.0" :rules="[rules.ipv4]" />
      </v-col>
      <v-col cols="12" sm="6">
        <v-combobox v-model="form.lease_time" :items="LEASE_SUGGESTIONS" label="Lease time" :rules="[rules.lease]" />
      </v-col>
      <v-col cols="12" sm="6">
        <v-combobox
          v-model="form.match_tags"
          label="Match tags"
          multiple
          chips
          closable-chips
          :rules="[rules.tags]"
          hint="Rendered as tag:<name>"
        />
      </v-col>
      <v-col cols="12" sm="6">
        <v-text-field v-model="form.set_tag" label="Set tag" :rules="[rules.tag]" hint="Rendered as set:<name>" />
      </v-col>
      <v-col cols="12">
        <v-text-field v-model="form.comment" label="Comment" :rules="[rules.singleLine]" />
      </v-col>
    </v-row>
  </FormDialog>
</template>
