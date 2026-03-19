import { useState } from 'react'

function App() {
  const [bookingCode, setBookingCode] = useState('')

  return (
    <div className="min-h-screen bg-gray-950 text-white flex flex-col items-center justify-center px-4">
      <header className="text-center mb-12">
        <h1 className="text-5xl font-bold tracking-tight mb-2">
          Prof<span className="text-blue-500">Bet</span>Geng
        </h1>
        <p className="text-gray-400 text-lg">
          SportyBet to Bet9ja — AI-Powered Ticket Converter
        </p>
      </header>

      <main className="w-full max-w-md">
        <div className="bg-gray-900 border border-gray-800 rounded-2xl p-8 shadow-xl">
          <label
            htmlFor="booking-code"
            className="block text-sm font-medium text-gray-400 mb-2"
          >
            SportyBet Booking Code
          </label>
          <input
            id="booking-code"
            type="text"
            value={bookingCode}
            onChange={(e) => setBookingCode(e.target.value)}
            placeholder="e.g. SB12345"
            className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent mb-6"
          />
          <button
            className="w-full py-3 bg-blue-600 hover:bg-blue-500 text-white font-semibold rounded-lg transition-colors duration-200 disabled:opacity-40 disabled:cursor-not-allowed"
            disabled={!bookingCode.trim()}
          >
            Convert to Bet9ja
          </button>
        </div>

        <p className="text-center text-gray-600 text-sm mt-8">
          Milestone 2 — Response Intelligence
        </p>
      </main>
    </div>
  )
}

export default App
