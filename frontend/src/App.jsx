import { useState } from 'react'
import { useApiKey } from './hooks/useApiKey'
import { convertTicket } from './api/pbgClient'
import SelectionRow from './components/SelectionRow'
import ConvertedResult from './components/ConvertedResult'

const EMPTY_SELECTION = () => ({
  event_id: `evt_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
  event_name: '',
  market: '1X2',
  pick: '',
  odds: '',
})

export default function App() {
  const { apiKey, loading: keyLoading, error: keyError } = useApiKey()

  const [bookingCode, setBookingCode] = useState('')
  const [stake, setStake] = useState('')
  const [selections, setSelections] = useState([EMPTY_SELECTION()])
  const [includeAnalysis, setIncludeAnalysis] = useState(false)

  const [converting, setConverting] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  function updateSelection(index, updated) {
    setSelections(prev => prev.map((s, i) => (i === index ? updated : s)))
  }

  function addSelection() {
    if (selections.length >= 10) return
    setSelections(prev => [...prev, EMPTY_SELECTION()])
  }

  function removeSelection(index) {
    if (selections.length <= 1) return
    setSelections(prev => prev.filter((_, i) => i !== index))
  }

  function reset() {
    setResult(null)
    setError(null)
    setBookingCode('')
    setStake('')
    setSelections([EMPTY_SELECTION()])
  }

  const isValid =
    bookingCode.trim() &&
    selections.every(s => s.event_name.trim() && s.pick.trim() && s.odds)

  async function handleConvert(e) {
    e.preventDefault()
    if (!isValid || converting || !apiKey) return

    setConverting(true)
    setError(null)

    try {
      const data = await convertTicket({
        apiKey,
        bookingCode: bookingCode.trim(),
        stake,
        includeAnalysis,
        selections: selections.map(s => ({
          event_id: s.event_id,
          event_name: s.event_name.trim(),
          market: s.market,
          pick: s.pick.trim(),
          odds: parseFloat(s.odds),
        })),
      })
      setResult(data)
    } catch (err) {
      setError(err.message || 'Conversion failed. Try again.')
    } finally {
      setConverting(false)
    }
  }

  if (keyLoading) {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center">
        <div className="text-center space-y-3">
          <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="text-gray-400 text-sm">Connecting to PBG…</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-950 text-white flex flex-col items-center px-4 py-12">

      {/* Header */}
      <header className="text-center mb-10">
        <h1 className="text-5xl font-bold tracking-tight mb-2">
          Prof<span className="text-blue-500">Bet</span>Geng
        </h1>
        <p className="text-gray-400 text-sm">
          SportyBet → Bet9ja · AI-Powered Ticket Converter
        </p>
      </header>

      <main className="w-full max-w-2xl">

        {keyError && (
          <div className="mb-6 bg-red-950 border border-red-800 rounded-xl px-4 py-3 text-red-300 text-sm">
            ⚠ {keyError}
          </div>
        )}

        {result ? (
          <ConvertedResult result={result} onReset={reset} />
        ) : (
          <form onSubmit={handleConvert} className="space-y-5">

            {/* Booking code + stake */}
            <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-gray-400 mb-1.5 uppercase tracking-wide">
                    Booking Code
                  </label>
                  <input
                    type="text"
                    value={bookingCode}
                    onChange={e => setBookingCode(e.target.value)}
                    placeholder="e.g. SB123456"
                    className="w-full px-4 py-2.5 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-400 mb-1.5 uppercase tracking-wide">
                    Stake (₦)
                  </label>
                  <input
                    type="number"
                    value={stake}
                    onChange={e => setStake(e.target.value)}
                    placeholder="e.g. 1000"
                    min="0"
                    className="w-full px-4 py-2.5 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
                  />
                </div>
              </div>

              {/* AI analysis toggle */}
              <label className="flex items-center gap-2.5 cursor-pointer group">
                <button
                  type="button"
                  role="switch"
                  aria-checked={includeAnalysis}
                  onClick={() => setIncludeAnalysis(v => !v)}
                  className={`relative w-9 h-5 rounded-full transition-colors ${
                    includeAnalysis ? 'bg-blue-600' : 'bg-gray-700'
                  }`}
                >
                  <span
                    className={`absolute top-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform ${
                      includeAnalysis ? 'translate-x-4' : 'translate-x-0.5'
                    }`}
                  />
                </button>
                <span className="text-sm text-gray-400 group-hover:text-gray-300 transition-colors">
                  Include TicketPulse AI risk analysis
                </span>
              </label>
            </div>

            {/* Selections */}
            <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6 space-y-3">
              <div className="flex items-center justify-between mb-1">
                <h2 className="text-sm font-semibold text-white">
                  Selections
                  <span className="ml-2 text-gray-500 font-normal">({selections.length}/10)</span>
                </h2>
              </div>

              <div className="grid grid-cols-12 gap-2">
                <span className="col-span-4 text-xs text-gray-600 uppercase tracking-wide">Match</span>
                <span className="col-span-3 text-xs text-gray-600 uppercase tracking-wide">Market</span>
                <span className="col-span-2 text-xs text-gray-600 uppercase tracking-wide">Pick</span>
                <span className="col-span-2 text-xs text-gray-600 uppercase tracking-wide">Odds</span>
              </div>

              <div className="space-y-2">
                {selections.map((sel, i) => (
                  <SelectionRow
                    key={sel.event_id}
                    index={i}
                    selection={sel}
                    onChange={updateSelection}
                    onRemove={removeSelection}
                    canRemove={selections.length > 1}
                  />
                ))}
              </div>

              {selections.length < 10 && (
                <button
                  type="button"
                  onClick={addSelection}
                  className="w-full py-2 border border-dashed border-gray-700 rounded-lg text-gray-500 hover:text-gray-300 hover:border-gray-500 text-sm transition-colors"
                >
                  + Add Selection
                </button>
              )}
            </div>

            {error && (
              <div className="bg-red-950 border border-red-800 rounded-xl px-4 py-3 text-red-300 text-sm">
                ⚠ {error}
              </div>
            )}

            <button
              type="submit"
              disabled={!isValid || converting || !apiKey}
              className="w-full py-3.5 bg-blue-600 hover:bg-blue-500 disabled:opacity-40 disabled:cursor-not-allowed text-white font-semibold rounded-xl transition-colors duration-200 flex items-center justify-center gap-2"
            >
              {converting ? (
                <>
                  <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  Converting…
                </>
              ) : (
                'Convert to Bet9ja →'
              )}
            </button>

            <p className="text-center text-gray-600 text-xs">
              M3 · Live Supabase · {apiKey ? `Key: ${apiKey.slice(0, 12)}…` : 'No key'}
            </p>
          </form>
        )}
      </main>
    </div>
  )
}
