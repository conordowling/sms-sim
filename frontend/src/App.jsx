import { useEffect, useState } from 'react'
import './App.css'

// Set at container startup from the REFRESH_INTERVAL_SECONDS env var
// (see docker-entrypoint.sh / public/config.js). Configured on startup
// only, not in the UI, so a running tab always polls at a fixed rate.
const REFRESH_INTERVAL_SECONDS = window.APP_CONFIG?.refreshIntervalSeconds ?? 5

function StatBox({ label, value }) {
  return (
    <div className="stat-box">
      <div className="stat-value">{value ?? '—'}</div>
      <div className="stat-label">{label}</div>
    </div>
  )
}

function App() {
  const [stats, setStats] = useState(null)
  const [lastUpdated, setLastUpdated] = useState(null)
  const [error, setError] = useState(null)
  const [numMessages, setNumMessages] = useState(1000)
  const [producing, setProducing] = useState(false)
  const [produceStatus, setProduceStatus] = useState(null)

  useEffect(() => {
    async function fetchStats() {
      try {
        const response = await fetch('/api/stats')
        if (!response.ok) {
          throw new Error(`request failed: ${response.status}`)
        }
        setStats(await response.json())
        setLastUpdated(new Date())
        setError(null)
      } catch (err) {
        setError(err.message)
      }
    }

    fetchStats()
    const intervalId = setInterval(fetchStats, REFRESH_INTERVAL_SECONDS * 1000)
    return () => clearInterval(intervalId)
  }, [])

  async function handleProduce() {
    setProducing(true)
    setProduceStatus(null)
    try {
      const response = await fetch('/api/produce', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ num_messages: Number(numMessages) }),
      })
      if (!response.ok) {
        throw new Error(`request failed: ${response.status}`)
      }
      const data = await response.json()
      setProduceStatus(`Queued ${data.num_messages} messages`)
    } catch (err) {
      setProduceStatus(`Failed to queue messages: ${err.message}`)
    } finally {
      setProducing(false)
    }
  }

  return (
    <div className="dashboard">
      <header className="header">
        <h1>SMS Simulation Monitor</h1>
        <span className="last-updated">
          {lastUpdated ? `Last updated: ${lastUpdated.toLocaleTimeString()}` : 'Loading…'}
        </span>
      </header>

      {error && <p className="error">Failed to load stats: {error}</p>}

      <div className="stat-row">
        <StatBox label="Sent" value={stats?.sent} />
        <StatBox label="Failed" value={stats?.failed} />
        <StatBox label="Avg Time (s)" value={stats?.avg_send_time_seconds?.toFixed(3)} />
      </div>

      <div className="produce-panel">
        <input
          type="number"
          min="1"
          value={numMessages}
          onChange={(e) => setNumMessages(e.target.value)}
          disabled={producing}
          aria-label="Number of messages"
        />
        <button onClick={handleProduce} disabled={producing}>
          {producing ? 'Sending…' : 'Send Messages'}
        </button>
        {produceStatus && <span className="produce-status">{produceStatus}</span>}
      </div>
    </div>
  )
}

export default App
