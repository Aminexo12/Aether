import { useEffect, useState, useRef } from 'react'
import './AltitudeStrata.css'

type Flight = {
  icao24: string
  callsign: string | null
  baro_altitude: number | null
  velocity: number | null
  vertical_rate: number | null
  on_ground: boolean
}

type Stratum = {
  fl: string
  label: string
  altMin: number
  altMax: number
}

// Top-down: high altitude first. Altitude in meters; FL = flight level (hundreds of ft).
const STRATA: Stratum[] = [
  { fl: 'FL400',    label: 'STRATOSPHERE',          altMin: 12000, altMax: 20000 },
  { fl: 'FL350',    label: 'CRUISE / LONG-HAUL',    altMin: 10500, altMax: 12000 },
  { fl: 'FL300',    label: 'CRUISE / NARROW-BODY',  altMin:  9000, altMax: 10500 },
  { fl: 'FL250',    label: 'CRUISE / REGIONAL',     altMin:  7500, altMax:  9000 },
  { fl: 'FL200',    label: 'CLIMB / DESCENT',       altMin:  6000, altMax:  7500 },
  { fl: 'FL150',    label: 'CLIMB / DESCENT',       altMin:  4500, altMax:  6000 },
  { fl: 'FL100',    label: 'APPROACH / DEPARTURE',  altMin:  3000, altMax:  4500 },
  { fl: 'FL050',    label: 'APPROACH / DEPARTURE',  altMin:  1500, altMax:  3000 },
  { fl: 'FL010',    label: 'PATTERN',               altMin:   300, altMax:  1500 },
  { fl: 'GND',      label: 'GROUND',                altMin:     0, altMax:   300 },
]

const REFRESH_MS = 60_000
const MAX_DOTS_PER_STRATUM = 36 // sampled visually — full count shown numerically

export default function AltitudeStrata() {
  const [flights, setFlights]   = useState<Flight[] | null>(null)
  const [ts, setTs]             = useState<Date | null>(null)
  const [error, setError]       = useState(false)
  const timer = useRef<ReturnType<typeof setInterval> | null>(null)

  const fetchFlights = async () => {
    try {
      const res = await fetch('/api/flights/live?country=EU')
      if (!res.ok) throw new Error()
      const data: Flight[] = await res.json()
      setFlights(data)
      setTs(new Date())
      setError(false)
    } catch {
      setError(true)
    }
  }

  useEffect(() => {
    fetchFlights()
    timer.current = setInterval(fetchFlights, REFRESH_MS)
    return () => { if (timer.current) clearInterval(timer.current) }
  }, [])

  // Group flights by stratum, deterministic per icao24 so dots don't jump on refresh
  const grouped = STRATA.map(s => {
    if (!flights) return { ...s, all: [], shown: [] as { f: Flight; x: number }[] }
    const all = flights.filter(f => {
      const alt = f.baro_altitude ?? 0
      if (s.fl === 'GND') return f.on_ground || alt < s.altMax
      return !f.on_ground && alt >= s.altMin && alt < s.altMax
    })
    // Cheap deterministic hash for horizontal placement
    const shown = all.slice(0, MAX_DOTS_PER_STRATUM).map(f => {
      let h = 0
      for (let i = 0; i < f.icao24.length; i++) h = (h * 31 + f.icao24.charCodeAt(i)) >>> 0
      return { f, x: (h % 10000) / 10000 } // 0..1
    })
    return { ...s, all, shown }
  })

  const total       = flights?.length ?? 0
  const airborne    = flights?.filter(f => !f.on_ground).length ?? 0
  const climbing    = flights?.filter(f => !f.on_ground && (f.vertical_rate ?? 0) > 1.0).length ?? 0
  const descending  = flights?.filter(f => !f.on_ground && (f.vertical_rate ?? 0) < -1.0).length ?? 0

  return (
    <div className="strata" role="img" aria-label="Live altitude distribution of European air traffic">
      {/* Header tiles */}
      <div className="strata-head">
        <div className="strata-tile">
          <span className="strata-tile-label">TRACKED · EU</span>
          <span className="strata-tile-value">{total.toLocaleString()}</span>
        </div>
        <div className="strata-tile">
          <span className="strata-tile-label">AIRBORNE</span>
          <span className="strata-tile-value strata-tile-value--sky">{airborne.toLocaleString()}</span>
        </div>
        <div className="strata-tile">
          <span className="strata-tile-label">CLIMBING</span>
          <span className="strata-tile-value">↑ {climbing.toLocaleString()}</span>
        </div>
        <div className="strata-tile">
          <span className="strata-tile-label">DESCENDING</span>
          <span className="strata-tile-value">↓ {descending.toLocaleString()}</span>
        </div>
      </div>

      {/* Strata grid */}
      <div className={`strata-grid ${error ? 'strata-grid--err' : ''}`}>
        {grouped.map(s => (
          <div key={s.fl} className="stratum">
            <div className="stratum-meta">
              <span className="stratum-fl">{s.fl}</span>
              <span className="stratum-label">{s.label}</span>
            </div>
            <div className="stratum-track" aria-hidden="true">
              <div className="stratum-rule" />
              {s.shown.map(({ f, x }) => (
                <span
                  key={f.icao24}
                  className={`dot ${s.fl === 'GND' ? 'dot--gnd' : ''}`}
                  style={{ left: `${x * 100}%` }}
                  title={(f.callsign ?? f.icao24).trim()}
                />
              ))}
            </div>
            <span className="stratum-count">{s.all.length || '—'}</span>
          </div>
        ))}
      </div>

      <div className="strata-foot">
        <span className="strata-foot-item">
          <span className="strata-foot-dot" /> POSITION SAMPLED · LIVE
        </span>
        <span className="strata-foot-item">
          UPDATED · {ts ? ts.toUTCString().slice(17, 25) + ' UTC' : '—'}
        </span>
      </div>
    </div>
  )
}
