import { useEffect, useState } from 'react'
import './LiveStatus.css'

type Flight = { on_ground: boolean }

const REFRESH_MS = 60_000

export default function LiveStatus() {
  const [count, setCount] = useState<number | null>(null)
  const [ts, setTs]       = useState<Date | null>(null)
  const [error, setError] = useState(false)

  const fetchStatus = async () => {
    try {
      const res = await fetch('/api/flights/live?country=EU')
      if (!res.ok) throw new Error()
      const data: Flight[] = await res.json()
      setCount(data.filter(f => !f.on_ground).length)
      setTs(new Date())
      setError(false)
    } catch {
      setError(true)
    }
  }

  useEffect(() => {
    fetchStatus()
    const id = setInterval(fetchStatus, REFRESH_MS)
    return () => clearInterval(id)
  }, [])

  if (error) return null

  return (
    <div className="live-status" role="status" aria-live="polite">
      <span className="live-status-dot" />
      <span className="live-status-text">
        {count == null
          ? 'CONNECTING TO LIVE FEED…'
          : <>
              <span className="live-status-num">{count.toLocaleString()}</span>
              <span className="live-status-sep"> · </span>
              AIRCRAFT AIRBORNE OVER EUROPE
            </>
        }
      </span>
      {ts && (
        <span className="live-status-time">
          {ts.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} UTC
        </span>
      )}
    </div>
  )
}
