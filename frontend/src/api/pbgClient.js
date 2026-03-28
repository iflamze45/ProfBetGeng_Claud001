const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

async function request(path, options = {}) {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  })
  const data = await res.json()
  if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`)
  return data
}

export async function generateApiKey(label = 'pbg-web-user') {
  return request('/api/v1/keys', {
    method: 'POST',
    body: JSON.stringify({ label }),
  })
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
