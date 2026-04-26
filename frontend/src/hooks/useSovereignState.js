import { useState, useEffect } from 'react'
import { getOddsWebSocketUrl } from '../api/pbgClient'

let globalState = {
    replication: null,
    evolution: null,
    treasury: null,
    outreach: null,
    singularity: null,
    strategy: null,
    pulse: null,
    governance: null,
    settlement: null,
    gateway: null,
    institutional: null,
    vault: 0,
    ghost: null,
    signals: [],
    active_nodes: 0,
    timestamp: null,
    status: 'OFFLINE',
    recentEvents: [],
}

let listeners = []

const notify = () => listeners.forEach(l => l(globalState))

let ws = null
let retryCount = 0

const connect = () => {
    if (ws) ws.close()

    try {
        ws = new WebSocket(getOddsWebSocketUrl())

        ws.onopen = () => {
            globalState.status = 'STABLE'
            retryCount = 0
            notify()
        }

        ws.onmessage = (event) => {
            try {
                const msg = JSON.parse(event.data)
                if (msg.type === 'STATE_UPDATE') {
                    globalState = {
                        ...globalState,
                        ...msg.data,
                        status: 'STABLE',
                        timestamp: msg.timestamp
                    }
                    notify()
                } else if (msg.type === 'CONVERSION_SUCCESS') {
                    const entry = {
                        type: 'CONVERSION',
                        source: msg.source?.toUpperCase() || 'SPORTYBET',
                        target: msg.target?.toUpperCase() || 'BET9JA',
                        selections: msg.selections || 0,
                        timestamp: msg.timestamp || new Date().toISOString(),
                    }
                    globalState = {
                        ...globalState,
                        recentEvents: [entry, ...globalState.recentEvents].slice(0, 20),
                    }
                    notify()
                }
            } catch (e) {
                console.error('State Sync Parse Error:', e)
            }
        }

        ws.onclose = () => {
            globalState.status = 'RECONNECTING'
            notify()
            const delay = Math.min(1000 * Math.pow(2, retryCount), 30000)
            retryCount++
            setTimeout(connect, delay)
        }

        ws.onerror = (err) => {
            console.error('State Sync WS Error:', err)
        }
    } catch (e) {
        console.error('State Sync Connection Error:', e)
    }
}

// Auto-start connection on first use or module load
if (typeof window !== 'undefined') {
    connect()
}

export function useSovereignState() {
    const [state, setState] = useState(globalState)

    useEffect(() => {
        listeners.push(setState)
        return () => {
            listeners = listeners.filter(l => l !== setState)
        }
    }, [])

    return state
}
