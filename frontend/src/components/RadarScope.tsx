import { useEffect, useRef, useState, useCallback, useMemo } from 'react'
import './RadarScope.css'

/*
 * Sonar pulse scope — the chat-tab background.
 *
 * No rotating sweep arm. Instead, concentric rings emanate from the center
 * every ~3.5s, expanding outward. Each ping's animation-delay is computed
 * from its distance to the center, so it lights up exactly when the wave
 * passes over it. Two pulses overlap (staggered 50%) so motion is continuous.
 *
 * Click anywhere → contact-lock animation, then the click point is promoted
 * to a persistent ping that rings react to.
 */

const PULSE_DURATION = 3.6  // seconds per sonar pulse
const PING_COUNT     = 26
const MAX_DISTANCE   = 70.71  // sqrt(50² + 50²): center → corner of a 100×100 grid

interface Ping {
  id: string
  x: number         // % of container
  y: number         // % of container
  size: number      // px
  delay: number     // s, animation-delay relative to pulse cycle
}

interface ClickPing {
  id: string
  x: number
  y: number
}

function rand(min: number, max: number) {
  return min + Math.random() * (max - min)
}

/**
 * For a ping at (x%, y%), compute the negative delay that aligns its peak
 * brightness keyframe with the moment the expanding sonar wave reaches it.
 */
function distanceDelay(x: number, y: number): number {
  const d = Math.hypot(x - 50, y - 50)
  const fraction = Math.min(d / MAX_DISTANCE, 1)
  return -fraction * PULSE_DURATION
}

function makePing(): Ping {
  const angle = rand(0, 360)
  const radius = rand(10, 46)    // % from center — keeps pings off the dead center
  const x = 50 + Math.cos(angle * Math.PI / 180) * radius
  const y = 50 + Math.sin(angle * Math.PI / 180) * radius
  return {
    id: `p-${Math.random().toString(36).slice(2, 9)}`,
    x,
    y,
    size: rand(2.0, 3.6),
    delay: distanceDelay(x, y),
  }
}

export default function RadarScope() {
  const containerRef = useRef<HTMLDivElement>(null)
  const [pings,      setPings]      = useState<Ping[]>(() =>
    Array.from({ length: PING_COUNT }, makePing)
  )
  const [clickPings, setClickPings] = useState<ClickPing[]>([])

  /* Rotate the ambient pings every ~18s — replace a few to simulate aircraft
     entering / leaving range. */
  useEffect(() => {
    const id = setInterval(() => {
      setPings(prev => {
        const next = [...prev]
        const replaceCount = Math.floor(rand(3, 6))
        for (let i = 0; i < replaceCount; i++) {
          const idx = Math.floor(Math.random() * next.length)
          next[idx] = makePing()
        }
        return next
      })
    }, 18_000)
    return () => clearInterval(id)
  }, [])

  const handleClick = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    const rect = containerRef.current?.getBoundingClientRect()
    if (!rect) return
    const x = ((e.clientX - rect.left) / rect.width)  * 100
    const y = ((e.clientY - rect.top)  / rect.height) * 100
    const cp: ClickPing = { id: `c-${Math.random().toString(36).slice(2, 9)}`, x, y }

    setClickPings(prev => [...prev, cp])
    setTimeout(() => {
      setClickPings(prev => prev.filter(p => p.id !== cp.id))
    }, 2200)

    // After the lock-in brackets converge, promote the click into a persistent
    // ping. Each subsequent sonar wave will light it up on its way out.
    setTimeout(() => {
      const newPing: Ping = {
        id: `det-${cp.id}`,
        x,
        y,
        size: rand(2.8, 3.6),
        delay: distanceDelay(x, y),
      }
      setPings(prev => {
        const next = [...prev, newPing]
        return next.length > 60 ? next.slice(next.length - 60) : next
      })
    }, 600)
  }, [])

  const rings = useMemo(() => [22, 38, 54, 70], [])

  return (
    <div
      ref={containerRef}
      className="radar"
      onClick={handleClick}
      aria-hidden="true"
    >
      {/* ─── Range rings + crosshair ─── */}
      <svg className="radar-grid" viewBox="0 0 100 100" preserveAspectRatio="none">
        {rings.map(r => (
          <circle
            key={r}
            cx="50" cy="50" r={r}
            fill="none"
            stroke="rgba(56, 145, 200, 0.10)"
            strokeWidth="0.18"
            vectorEffect="non-scaling-stroke"
          />
        ))}
        <line x1="50" y1="0" x2="50" y2="100"
              stroke="rgba(56, 145, 200, 0.07)" strokeWidth="0.15"
              strokeDasharray="0.4 1.2" vectorEffect="non-scaling-stroke"/>
        <line x1="0" y1="50" x2="100" y2="50"
              stroke="rgba(56, 145, 200, 0.07)" strokeWidth="0.15"
              strokeDasharray="0.4 1.2" vectorEffect="non-scaling-stroke"/>
      </svg>

      {/* ─── Sonar pulses (2 rings, staggered) ─── */}
      <svg className="sonar" viewBox="0 0 200 200" preserveAspectRatio="xMidYMid slice">
        <circle
          cx="100" cy="100"
          className="sonar-ring sonar-ring--1"
          style={{ animationDuration: `${PULSE_DURATION}s` }}
        />
        <circle
          cx="100" cy="100"
          className="sonar-ring sonar-ring--2"
          style={{
            animationDuration: `${PULSE_DURATION}s`,
            animationDelay: `${-PULSE_DURATION / 2}s`,
          }}
        />
      </svg>

      {/* ─── Center origin ─── */}
      <div className="radar-origin" />

      {/* ─── Ambient pings (sync to incoming wave) ─── */}
      {pings.map(p => (
        <span
          key={p.id}
          className="radar-ping"
          style={{
            left:  `${p.x}%`,
            top:   `${p.y}%`,
            width:  `${p.size}px`,
            height: `${p.size}px`,
            animationDuration: `${PULSE_DURATION}s`,
            animationDelay:    `${p.delay}s`,
          }}
        />
      ))}

      {/* ─── Click pings: contact-lock composite ─── */}
      {clickPings.map(cp => (
        <div
          key={cp.id}
          className="contact-lock"
          style={{ left: `${cp.x}%`, top: `${cp.y}%` }}
        >
          <span className="lock-bracket lock-bracket--tl" />
          <span className="lock-bracket lock-bracket--tr" />
          <span className="lock-bracket lock-bracket--bl" />
          <span className="lock-bracket lock-bracket--br" />
          <span className="lock-ring lock-ring--1" />
          <span className="lock-ring lock-ring--2" />
          <span className="lock-ring lock-ring--3" />
          <span className="lock-dot" />
          <span className="lock-label">CONTACT · {cp.id.slice(2, 6).toUpperCase()}</span>
        </div>
      ))}
    </div>
  )
}
