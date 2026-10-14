<script setup>
import { computed, reactive, watch } from 'vue'
import FormDialog from './FormDialog.vue'
import { DNS_TYPES } from '@/kinds'
import { orNull, rules } from '@/rules'

const props = defineProps({
  entry: { type: Object, default: null }, // null = create
  submit: { type: Function, required: true },
})
const open = defineModel({ type: Boolean, default: false })

const blank = () => ({ type: 'host-record', names: [], ipv4: '', ipv6: '', ip: '', target: '', ttl: '', comment: '' })
const form = reactive(blank())

watch(open, (isOpen) => {
  if (!isOpen) return
  const e = props.entry
  Object.assign(form, blank(), e && {
    ...e,
    // the name list has a different field name per type
    names: e.names ?? e.domains ?? e.aliases ?? [],
    ipv4: e.ipv4 ?? '',
    ipv6: e.ipv6 ?? '',
    ttl: e.ttl ?? '',
    comment: e.comment ?? '',
  })
})

const namesLabel = computed(() => ({ 'host-record': 'Host names', address: 'Domains', cname: 'Aliases' })[form.type])
const hasTtl = computed(() => form.type !== 'address')
const needsAnIp = (v) => form.type !== 'host-record' || !!(form.ipv4 || form.ipv6 || v) || 'IPv4 or IPv6 required'

function payload() {
  const base = { type: form.type, comment: orNull(form.comment) }
  const ttl = form.ttl === '' ? null : Number(form.ttl)
  switch (form.type) {
    case 'host-record':
      return { ...base, names: form.names, ipv4: orNull(form.ipv4), ipv6: orNull(form.ipv6), ttl }
    case 'address':
      return { ...base, domains: form.names, ip: form.ip }
    case 'cname':
      return { ...base, aliases: form.names, target: form.target, ttl }
  }
}

const save = () => props.submit(payload())
</script>

<template>
  <FormDialog v-model="open" :title="entry ? 'Edit DNS entry' : 'New DNS entry'" :submit="save">
    <v-btn-toggle v-model="form.type" mandatory color="secondary" variant="outlined" divided class="mb-4 w-100">
      <v-btn v-for="t in DNS_TYPES" :key="t.value" :value="t.value" class="flex-grow-1">{{ t.title }}</v-btn>
    </v-btn-toggle>
    <p class="text-body-small text-medium-emphasis mb-4">
      {{ DNS_TYPES.find((t) => t.value === form.type).subtitle }}
    </p>

    <v-combobox
      v-model="form.names"
      :label="namesLabel"
      multiple
      chips
      closable-chips
      :rules="[rules.required, rules.hostnames]"
      hint="Press Enter after each name"
      persistent-hint
      class="mb-3"
    />

    <template v-if="form.type === 'host-record'">
      <v-row dense>
        <v-col cols="12" sm="6">
          <v-text-field v-model="form.ipv4" label="IPv4" placeholder="192.168.1.10" :rules="[rules.ipv4, needsAnIp]" />
        </v-col>
        <v-col cols="12" sm="6">
          <v-text-field v-model="form.ipv6" label="IPv6" placeholder="fd00::10" :rules="[rules.ipv6, needsAnIp]" />
        </v-col>
      </v-row>
    </template>
    <v-text-field
      v-else-if="form.type === 'address'"
      v-model="form.ip"
      label="IP address"
      placeholder="192.168.1.10"
      :rules="[rules.required, rules.ip]"
    />
    <v-text-field
      v-else
      v-model="form.target"
      label="Target"
      placeholder="nas.home.lan"
      :rules="[rules.required, rules.hostname]"
    />

    <v-row dense>
      <v-col v-if="hasTtl" cols="12" sm="4">
        <v-text-field v-model="form.ttl" label="TTL (s)" type="number" min="0" :rules="[rules.ttl]" />
      </v-col>
      <v-col cols="12" :sm="hasTtl ? 8 : 12">
        <v-text-field v-model="form.comment" label="Comment" :rules="[rules.singleLine]" />
      </v-col>
    </v-row>
  </FormDialog>
</template>
