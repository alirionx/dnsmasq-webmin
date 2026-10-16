import { Globe, Network } from '@lucide/vue'

const dnsNames = (e) => (e.names ?? e.domains ?? e.aliases ?? []).join(', ')

const dnsValue = (e) => {
  switch (e.type) {
    case 'host-record':
      return [e.ipv4, e.ipv6].filter(Boolean).join(', ')
    case 'address':
      return e.ip
    case 'cname':
      return `→ ${e.target}`
    default:
      return ''
  }
}

const dhcpTags = (e) => [...e.match_tags.map((t) => `tag:${t}`), e.set_tag && `set:${e.set_tag}`].filter(Boolean).join(', ')

const actions = { title: '', key: 'actions', sortable: false, align: 'end', width: 112 }

/** Per-kind UI metadata, so the files view can stay generic. */
export const KINDS = {
  dns: {
    title: 'DNS entries',
    icon: Globe,
    entryLabel: 'DNS entry',
    entryLabelPlural: 'DNS entries',
    headers: [
      { title: 'Type', key: 'type', width: 140 },
      { title: 'Names', key: 'names', value: dnsNames },
      { title: 'Value', key: 'value', value: dnsValue },
      { title: 'TTL', key: 'ttl', width: 90 },
      { title: 'Comment', key: 'comment' },
      actions,
    ],
  },
  dhcp: {
    title: 'DHCP ranges',
    icon: Network,
    entryLabel: 'DHCP range',
    entryLabelPlural: 'DHCP ranges',
    headers: [
      { title: 'Range', key: 'range', value: (e) => `${e.start} – ${e.end}` },
      { title: 'Netmask / Prefix', key: 'mask', value: (e) => e.netmask ?? (e.prefix_length ? `/${e.prefix_length}` : '') },
      { title: 'Lease', key: 'lease_time', width: 110 },
      { title: 'Tags', key: 'tags', value: dhcpTags },
      { title: 'Comment', key: 'comment' },
      actions,
    ],
  },
}

export const DNS_TYPES = [
  { value: 'host-record', title: 'Host record', subtitle: 'A/AAAA + PTR for one or more names', color: 'primary' },
  { value: 'address', title: 'Address', subtitle: 'Domain incl. all subdomains → IP', color: 'secondary' },
  { value: 'cname', title: 'CNAME', subtitle: 'Alias for a name known to dnsmasq', color: 'info' },
]
