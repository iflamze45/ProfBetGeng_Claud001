import { useState, useEffect } from 'react'
import { generateApiKey } from '../api/pbgClient'

const STORAGE_KEY = 'pbg_api_key'
let initPromise = null

export function useApiKey() {
  const [apiKey, setApiKey] = useState(() => localStorage.getItem(STORAGE_KEY) || '')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!apiKey) initKey()
  }, [])

  async function initKey() {
    setLoading(true)
    setError(null)
    try {
      if (!initPromise) {
        initPromise = generateApiKey('pbg-web-' + Date.now()).finally(() => {
          initPromise = null
        })
      }
      const res = await initPromise
      localStorage.setItem(STORAGE_KEY, res.key)
      setApiKey(res.key)
    } catch (err) {
      setError('Could not connect to PBG server. Is it running?')
    } finally {
      setLoading(false)
    }
  }

  return { apiKey, loading, error }
}

export default useApiKey;
