/** Thin fetch wrapper around the FastAPI backend (mounted under /api). */

export class ApiError extends Error {
  constructor(status, detail) {
    super(formatDetail(detail))
    this.status = status
    this.detail = detail
  }
}

/** Turns FastAPI error details (string or list of validation errors) into readable text. */
function formatDetail(detail) {
  if (!Array.isArray(detail)) return String(detail ?? 'Unknown error')
  return detail
    .map((err) => {
      // loc looks like ["body", "host-record", "names", 0] - drop the noise
      const field = err.loc.slice(1).filter((p) => !['body', 'host-record', 'address', 'cname'].includes(p))
      const msg = err.msg.replace(/^Value error, /, '')
      return field.length ? `${field.join('.')}: ${msg}` : msg
    })
    .join('\n')
}

async function request(method, path, body) {
  const init = { method, headers: { Accept: 'application/json, text/plain' } }
  if (body !== undefined) {
    init.headers['Content-Type'] = 'application/json'
    init.body = JSON.stringify(body)
  }
  const res = await fetch(`/api${path}`, init)
  if (!res.ok) {
    let detail = res.statusText
    try {
      detail = (await res.json()).detail
    } catch {
      // non-JSON error body - keep status text
    }
    throw new ApiError(res.status, detail)
  }
  if (res.status === 204) return null
  return res.headers.get('content-type')?.includes('application/json') ? res.json() : res.text()
}

const files = (kind, name) => `/${kind}-files${name ? `/${encodeURIComponent(name)}` : ''}`

export const api = {
  listFiles: (kind) => request('GET', files(kind)),
  createFile: (kind, data) => request('POST', files(kind), data),
  updateFile: (kind, name, data) => request('PATCH', files(kind, name), data),
  deleteFile: (kind, name) => request('DELETE', files(kind, name)),
  renderFile: (kind, name) => request('GET', `${files(kind, name)}/render`),

  addEntry: (kind, name, data) => request('POST', `${files(kind, name)}/entries`, data),
  replaceEntry: (kind, name, id, data) => request('PUT', `${files(kind, name)}/entries/${id}`, data),
  deleteEntry: (kind, name, id) => request('DELETE', `${files(kind, name)}/entries/${id}`),

  renderAll: (kind) => request('GET', `/render${kind ? `?kind=${kind}` : ''}`),
  sync: () => request('POST', '/sync'),

  serviceStatus: () => request('GET', '/service'),
  restartService: () => request('POST', '/service/restart'),
}
