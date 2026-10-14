/**
 * Client-side validation rules (Vuetify rule functions). They mirror the backend
 * patterns for quick feedback; the backend stays the source of truth.
 */

const HOSTNAME = /^[A-Za-z0-9]([A-Za-z0-9-]{0,61}[A-Za-z0-9])?(\.[A-Za-z0-9]([A-Za-z0-9-]{0,61}[A-Za-z0-9])?)*\.?$/
const IPV4 = /^((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)\.){3}(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)$/
const IPV6 = /^[0-9A-Fa-f:.]+$/ // rough check, the backend validates exactly
const TAG = /^[A-Za-z0-9_-]{1,64}$/
const FILE_NAME = /^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$/
const LEASE = /^(infinite|\d+[smhdw]?)$/

const empty = (v) => v === null || v === undefined || v === '' || (Array.isArray(v) && v.length === 0)

export const isIPv6 = (v) => typeof v === 'string' && v.includes(':')

export const rules = {
  required: (v) => !empty(v) || 'Required',
  fileName: (v) => empty(v) || FILE_NAME.test(v) || 'Letters, digits, - and _ only (max. 64)',
  hostname: (v) => empty(v) || HOSTNAME.test(v) || 'Invalid hostname',
  hostnames: (v) => empty(v) || v.every((h) => HOSTNAME.test(h)) || 'Contains an invalid hostname',
  ipv4: (v) => empty(v) || IPV4.test(v) || 'Invalid IPv4 address',
  ipv6: (v) => empty(v) || (isIPv6(v) && IPV6.test(v)) || 'Invalid IPv6 address',
  ip: (v) => empty(v) || IPV4.test(v) || (isIPv6(v) && IPV6.test(v)) || 'Invalid IP address',
  tag: (v) => empty(v) || TAG.test(v) || 'Letters, digits, - and _ only',
  tags: (v) => empty(v) || v.every((t) => TAG.test(t)) || 'Contains an invalid tag',
  lease: (v) => empty(v) || LEASE.test(v) || "e.g. 12h, 30m, 3600 or 'infinite'",
  singleLine: (v) => empty(v) || (!/[\r\n]/.test(v) && v.length <= 200) || 'One line, max. 200 characters',
  ttl: (v) => empty(v) || (Number.isInteger(Number(v)) && Number(v) >= 0) || 'Non-negative integer',
}

/** Empty strings from text fields become null, so optional fields are omitted properly. */
export const orNull = (v) => (empty(v) ? null : v)
