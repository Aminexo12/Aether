import { useEffect, useRef, useState, useCallback } from 'react'
import './StarField.css'

/*
 * CSS-driven night sky.
 *
 * Three star classes:
 *  - pinprick (60%) — tiny solid dots, subtle halo
 *  - medium   (30%) — larger dots with a soft halo + gentle pulse
 *  - beacon   (10%) — bright stars with 4-point diffraction spikes,
 *                     slow pulse — the "anchor" stars
 *
 * Spontaneous events:
 *  - Meteor streak crosses the canvas every 8-18 seconds. Tapered contrail,
 *    diagonal travel, fades at endpoint.
 *  - Click anywhere → ignition burst: a beacon star + 6 sparks that radiate
 *    out and fade. Beacon stays and drifts with the rest of the field.
 */

type StarClass = 'pinprick' | 'medium' | 'beacon'

interface Star {
  id: string
  x: number          // % of container width
  y: number          // % of container height
  dx: number         // drift offset multiplier (in px later)
  dy: number
  size: number       // px
  alpha: number
  blueTint: boolean
  duration: number   // drift cycle in seconds
  delay: number
  klass: StarClass
  spawned: boolean
}

interface Spark {
  id: string
  x: number
  y: number
  angle: number      // degrees
  distance: number   // px to travel
}

interface Meteor {
  id: string
  startX: number     // %
  startY: number     // %
  angle: number      // degrees (travel direction)
  length: number     // px (trail length)
  duration: number   // s
}

const INITIAL_COUNT = 130
const MAX_STARS     = 280
const METEOR_MIN_MS = 8_000
const METEOR_MAX_MS = 18_000

function rand(min: number, max: number) {
  return min + Math.random() * (max - min)
}

function pickClass(): StarClass {
  const r = Math.random()
  if (r < 0.10) return 'beacon'
  if (r < 0.40) return 'medium'
  return 'pinprick'
}

function makeStar(opts: Partial<Star> & { spawned: boolean }): Star {
  const klass = opts.klass ?? pickClass()
  const sizeByClass = {
    pinprick: rand(0.8, 1.4),
    medium:   rand(1.8, 2.8),
    beacon:   rand(3.2, 5.0),
  }[klass]
  const alphaByClass = {
    pinprick: rand(0.35, 0.75),
    medium:   rand(0.55, 0.9),
    beacon:   rand(0.75, 1.0),
  }[klass]
  return {
    id: opts.id ?? `s-${Math.random().toString(36).slice(2, 9)}`,
    x: opts.x ?? rand(0, 100),
    y: opts.y ?? rand(0, 100),
    dx: opts.dx ?? rand(-4, 4),
    dy: opts.dy ?? rand(-4, 4),
    size: opts.size ?? sizeByClass,
    alpha: opts.alpha ?? alphaByClass,
    blueTint: opts.blueTint ?? Math.random() < 0.18,
    duration: opts.duration ?? rand(32, 64),
    delay: opts.delay ?? rand(-30, 0),
    klass,
    spawned: opts.spawned,
  }
}

export default function StarField() {
  const [stars, setStars]     = useState<Star[]>(() =>
    Array.from({ length: INITIAL_COUNT }, () => makeStar({ spawned: false }))
  )
  const [meteors, setMeteors] = useState<Meteor[]>([])
  const [sparks, setSparks]   = useState<Spark[]>([])
  const containerRef = useRef<HTMLDivElement>(null)

  /* ───── Random meteor scheduler ───── */
  useEffect(() => {
    let timer: ReturnType<typeof setTimeout>
    const schedule = () => {
      const wait = rand(METEOR_MIN_MS, METEOR_MAX_MS)
      timer = setTimeout(() => {
        const meteor: Meteor = {
          id: `m-${Math.random().toString(36).slice(2, 9)}`,
          startX: rand(-5, 80),
          startY: rand(-5, 40),
          angle: rand(30, 50),      // diagonal, top-left → bottom-right
          length: rand(90, 180),
          duration: rand(0.9, 1.5),
        }
        setMeteors(prev => [...prev, meteor])
        setTimeout(() => {
          setMeteors(prev => prev.filter(m => m.id !== meteor.id))
        }, meteor.duration * 1000 + 200)
        schedule()
      }, wait)
    }
    schedule()
    return () => clearTimeout(timer)
  }, [])

  /* ───── Click → ignition burst (beacon + sparks) ───── */
  const handleClick = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    const rect = containerRef.current?.getBoundingClientRect()
    if (!rect) return
    const xPct = ((e.clientX - rect.left) / rect.width)  * 100
    const yPct = ((e.clientY - rect.top)  / rect.height) * 100

    // Beacon star at click point
    const beacon = makeStar({
      x: xPct,
      y: yPct,
      klass: 'beacon',
      size: rand(3.5, 4.8),
      alpha: 1,
      delay: 0,
      spawned: true,
    })

    // 6 sparks radiating in different directions
    const sparkCount = 6
    const baseAngle = rand(0, 360)
    const fresh: Spark[] = Array.from({ length: sparkCount }, (_, i) => ({
      id: `sp-${beacon.id}-${i}`,
      x: xPct,
      y: yPct,
      angle: baseAngle + (i * 360) / sparkCount + rand(-8, 8),
      distance: rand(20, 42),
    }))

    setStars(prev => {
      const next = [...prev, beacon]
      return next.length > MAX_STARS ? next.slice(next.length - MAX_STARS) : next
    })
    setSparks(prev => [...prev, ...fresh])

    setTimeout(() => {
      setSparks(prev => prev.filter(s => !fresh.some(f => f.id === s.id)))
    }, 720)
  }, [])

  /* ───── Settle spawn flag after animation completes ───── */
  useEffect(() => {
    const hasSpawning = stars.some(s => s.spawned)
    if (!hasSpawning) return
    const t = setTimeout(() => {
      setStars(prev => prev.map(s => s.spawned ? { ...s, spawned: false } : s))
    }, 720)
    return () => clearTimeout(t)
  }, [stars])

  return (
    <div
      ref={containerRef}
      className="star-field"
      onClick={handleClick}
      aria-hidden="true"
    >
      {/* ─── Stars ─── */}
      {stars.map(s => (
        <span
          key={s.id}
          className={`star star--${s.klass} ${s.spawned ? 'star--spawn' : ''}`}
          style={{
            // Center-anchor the star via calc so transform stays free for drift
            left: `calc(${s.x}% - ${s.size / 2}px)`,
            top:  `calc(${s.y}% - ${s.size / 2}px)`,
            width:  `${s.size}px`,
            height: `${s.size}px`,
            opacity: s.alpha,
            background: s.blueTint
              ? 'rgb(220, 235, 250)'
              : 'rgb(255, 255, 255)',
            ['--dx' as string]: `${s.dx * 8}px`,
            ['--dy' as string]: `${s.dy * 8}px`,
            ['--drift-dur' as string]: `${s.duration}s`,
            animationDelay: `${s.delay}s, 0s`,
          }}
        />
      ))}

      {/* ─── Meteor streaks ─── */}
      {meteors.map(m => (
        <span
          key={m.id}
          className="meteor"
          style={{
            left: `${m.startX}%`,
            top:  `${m.startY}%`,
            width:  `${m.length}px`,
            ['--rot' as string]: `${m.angle}deg`,
            animationDuration: `${m.duration}s`,
          }}
        />
      ))}

      {/* ─── Click-burst sparks ─── */}
      {sparks.map(sp => (
        <span
          key={sp.id}
          className="spark"
          style={{
            left: `${sp.x}%`,
            top:  `${sp.y}%`,
            ['--spark-tx' as string]: `${Math.cos(sp.angle * Math.PI / 180) * sp.distance}px`,
            ['--spark-ty' as string]: `${Math.sin(sp.angle * Math.PI / 180) * sp.distance}px`,
          }}
        />
      ))}
    </div>
  )
}
