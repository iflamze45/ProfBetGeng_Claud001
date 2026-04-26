const BASE_URL = '' // Use relative path for Vite proxy in dev and same-origin in prod

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

export async function parseRawText({ apiKey, rawText }) {
  return request('/api/v1/parse-ticket', {
    method: 'POST',
    headers: { 'X-API-Key': apiKey },
    body: JSON.stringify({ raw_text: rawText }),
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

export async function executeInstitutionalTrade({ apiKey, marketId, amountUsd }) {
  return request('/api/v1/institutional/execute', {
    method: 'POST',
    headers: { 'X-API-Key': apiKey },
    body: JSON.stringify({ market_id: marketId, amount_usd: amountUsd }),
  })
}

export async function initiateGhostProtocol({ apiKey }) {
  return request('/api/v1/ghost/initiate', {
    method: 'POST',
    headers: { 'X-API-Key': apiKey }
  })
}

export async function getArbWindows({ apiKey }) {
  return request('/api/v1/quant/arbs', {
    headers: { 'X-API-Key': apiKey }
  })
}

export async function getDarkPoolDepth({ apiKey, marketId }) {
  return request(`/api/v1/institutional/depth/${marketId}`, {
    headers: { 'X-API-Key': apiKey }
  })
}

export async function executeTreasuryRebalance({ apiKey }) {
  return request('/api/v1/treasury/rebalance', {
    method: 'POST',
    headers: { 'X-API-Key': apiKey }
  })
}

export async function executeTreasuryFlatten({ apiKey }) {
  return request('/api/v1/treasury/flatten', {
    method: 'POST',
    headers: { 'X-API-Key': apiKey }
  })
}

export async function initiateOmegaLock({ apiKey }) {
  return request('/api/v1/singularity/omega-lock', {
    method: 'POST',
    headers: { 'X-API-Key': apiKey }
  })
}

export async function executeRecursiveFeedback({ apiKey }) {
  return request('/api/v1/singularity/recursive-feedback', {
    method: 'POST',
    headers: { 'X-API-Key': apiKey }
  })
}

export async function executeGovernanceVote({ apiKey, proposalId, voterName, voteType }) {
  return request('/api/v1/gov/vote', {
    method: 'POST',
    headers: { 'X-API-Key': apiKey },
    body: JSON.stringify({ proposal_id: proposalId, voter_name: voterName, vote_type: voteType })
  })
}

export async function executeGovernanceProposal({ apiKey, proposalId }) {
  return request(`/api/v1/gov/execute/${proposalId}`, {
    method: 'POST',
    headers: { 'X-API-Key': apiKey }
  })
}

export async function simulateMeshFailure({ apiKey, nodeId }) {
  return request('/api/v1/mesh/simulate-failure', {
    method: 'POST',
    headers: { 'X-API-Key': apiKey },
    body: JSON.stringify({ node_id: nodeId })
  })
}

export async function getMarketSignals(apiKey) {
  return request('/api/v1/market/signals', {
    headers: { 'X-API-Key': apiKey },
  })
}

export async function getSgnNodes(apiKey) {
  return request('/api/v1/sgn/nodes', {
    headers: { 'X-API-Key': apiKey },
  })
}

export async function getMindStatus(apiKey) {
  return request('/api/v1/mind/status', {
    headers: { 'X-API-Key': apiKey },
  })
}

export async function getGovProposals(apiKey) {
  return request('/api/v1/gov/proposals', {
    headers: { 'X-API-Key': apiKey },
  })
}
