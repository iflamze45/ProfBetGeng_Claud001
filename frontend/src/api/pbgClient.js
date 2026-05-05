const BASE_URL = import.meta.env.VITE_API_BASE_URL || ''

async function request(path, options = {}) {
  const { headers = {}, ...rest } = options
  const res = await fetch(`${BASE_URL}${path}`, {
    ...rest,
    headers: { 'Content-Type': 'application/json', ...headers },
  })
  const data = await res.json()
  if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`)
  return data
}

export async function generateApiKey(label = 'pbg-web-user') {
  const adminToken = import.meta.env.VITE_ADMIN_TOKEN || 'pbg_admin_secret'
  return request('/api/v1/keys', {
    method: 'POST',
    headers: { 'X-Admin-Token': adminToken },
    body: JSON.stringify({ label }),
  })
}

export function getOddsWebSocketUrl() {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = BASE_URL ? BASE_URL.replace(/^https?:\/\//, '') : window.location.host;
  return `${protocol}//${host}/api/v1/ws/odds`;
}

export async function convertTicket({ apiKey, bookingCode, stake, selections, includeAnalysis = false }) {
  return request('/api/v1/convert', {
    method: 'POST',
    headers: { 'X-API-Key': apiKey },
    body: JSON.stringify({
      booking_code: bookingCode,
      stake: stake ? parseFloat(stake) : null,
      include_analysis: includeAnalysis,
      selections,
    }),
  })
}

export async function getHistory(apiKey) {
  return request('/api/v1/history', {
    headers: { 'X-API-Key': apiKey },
  })
}

export async function* analyseTicketStream({ apiKey, converted, language = 'en' }) {
  const response = await fetch(`${BASE_URL}/api/v1/analyse/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': apiKey,
    },
    body: JSON.stringify({ converted, language }),
  })

  if (!response.ok) {
    const data = await response.json().catch(() => ({}))
    throw new Error(data.detail || `HTTP ${response.status}`)
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const parts = buffer.split('\n\n')
    buffer = parts.pop()

    for (const part of parts) {
      if (part.startsWith('data: ')) {
        const dataStr = part.slice(6).trim()
        if (dataStr === '[DONE]') return
        try {
          const data = JSON.parse(dataStr)
          if (data.text) yield data.text
        } catch (e) {
          console.error('Failed to parse SSE chunk', e)
        }
      }
    }
  }
}

export async function convertBatch({ apiKey, tickets }) {
  return request('/api/v1/convert-batch', {
    method: 'POST',
    headers: { 'X-API-Key': apiKey },
    body: JSON.stringify({ tickets }),
  })
}

export async function getArbWindows({ apiKey }) {
  return request('/api/v1/quant/arbs', {
    headers: { 'X-API-Key': apiKey }
  })
}

export async function getMarketSignals(apiKey, { limit = 20 } = {}) {
  return request(`/api/v1/signals?limit=${limit}`, {
    headers: { 'X-API-Key': apiKey }
  })
}

export async function getWhaleSignals(apiKey, { limit = 10 } = {}) {
  return request(`/api/v1/analytics/whales?limit=${limit}`, {
    headers: { 'X-API-Key': apiKey }
  })
}

export async function getNodes(apiKey) {
  const data = await request('/api/v1/mesh/nodes', { headers: { 'X-API-Key': apiKey } })
  return data.nodes || []
}

// Uses existing analytics/risk endpoint with a representative sample of returns
const _SAMPLE_RETURNS = '0.1,0.05,-0.03,0.08,0.12,-0.07,0.15,0.02,-0.01,0.09'
export async function getRiskProfile(apiKey) {
  return request(`/api/v1/analytics/risk?returns=${_SAMPLE_RETURNS}`, {
    headers: { 'X-API-Key': apiKey }
  })
}

function adminHeaders() {
  const token = import.meta.env.VITE_ADMIN_TOKEN || 'pbg_admin_secret'
  return { 'X-Admin-Token': token }
}

export async function adminListKeys() {
  return request('/api/v1/admin/keys', { headers: adminHeaders() })
}

export async function adminDeactivateKey(keyId) {
  return request(`/api/v1/admin/keys/${keyId}`, {
    method: 'DELETE',
    headers: adminHeaders(),
  })
}

export async function adminPatchKey(keyId, updates) {
  return request(`/api/v1/admin/keys/${keyId}`, {
    method: 'PATCH',
    headers: adminHeaders(),
    body: JSON.stringify(updates),
  })
}
