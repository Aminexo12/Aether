import { useMemo } from 'react'
import './HeadingRose.css'

/*
 * Polar "compass rose" showing the distribution of flight headings.
 *
 * Each of the 16 compass directions (N, NNE, NE, ENE, E, …, NNW) gets one
 * spoke; spoke length = count of flights heading in that bucket. Cardinal
 * labels around the perimeter. Pure SVG, no library.
 */

interface Props {
  headings: (number | null)[]   // raw degrees (0..360) or null
}

const SECTORS = 16  // 22.5° each
const CARDINALS: { label: string; angle: number }[] = [
  { label: 'N',  angle: 0   },
  { label: 'NE', angle: 45  },
  { label: 'E',  angle: 90  },
  { label: 'SE', angle: 135 },
  { label: 'S',  angle: 180 },
  { label: 'SW', angle: 225 },
  { label: 'W',  angle: 270 },
  { label: 'NW', angle: 315 },
]

function polar(cx: number, cy: number, r: number, angleDeg: number): [number, number] {
  // angleDeg: 0 = up (north), increases clockwise
  const rad = (angleDeg - 90) * Math.PI / 180
  return [cx + r * Math.cos(rad), cy + r * Math.sin(rad)]
}

export default function HeadingRose({ headings }: Props) {
  const buckets = useMemo(() => {
    const b = new Array(SECTORS).fill(0)
    let max = 0
    for (const h of headings) {
      if (h == null) continue
      const idx = Math.floor(((h % 360) + 360) % 360 / (360 / SECTORS)) % SECTORS
      b[idx]++
      if (b[idx] > max) max = b[idx]
    }
    return { counts: b, max: max || 1 }
  }, [headings])

  const SIZE = 240
  const CX = SIZE / 2
  const CY = SIZE / 2
  const R_OUTER = 95
  const R_INNER = 14
  const SECTOR_DEG = 360 / SECTORS

  return (
    <svg className="rose" viewBox={`0 0 ${SIZE} ${SIZE}`} preserveAspectRatio="xMidYMid meet">
      {/* Concentric guide circles */}
      {[0.33, 0.66, 1.0].map(p => (
        <circle
          key={p}
          cx={CX} cy={CY} r={R_OUTER * p}
          fill="none"
          stroke="rgba(56, 145, 200, 0.12)"
          strokeWidth="0.6"
          strokeDasharray={p === 1.0 ? 'none' : '2 3'}
        />
      ))}

      {/* Cardinal cross */}
      <line x1={CX} y1={CY - R_OUTER - 2} x2={CX} y2={CY + R_OUTER + 2}
            stroke="rgba(56, 145, 200, 0.10)" strokeWidth="0.5" strokeDasharray="2 3"/>
      <line x1={CX - R_OUTER - 2} y1={CY} x2={CX + R_OUTER + 2} y2={CY}
            stroke="rgba(56, 145, 200, 0.10)" strokeWidth="0.5" strokeDasharray="2 3"/>

      {/* Heading spokes — wedges from center outward, length ∝ count */}
      {buckets.counts.map((count, i) => {
        if (count === 0) return null
        const angle  = i * SECTOR_DEG
        const length = (count / buckets.max) * (R_OUTER - R_INNER - 2)
        const halfArc = SECTOR_DEG * 0.42

        const [x1, y1] = polar(CX, CY, R_INNER, angle - halfArc)
        const [x2, y2] = polar(CX, CY, R_INNER + length, angle - halfArc)
        const [x3, y3] = polar(CX, CY, R_INNER + length, angle + halfArc)
        const [x4, y4] = polar(CX, CY, R_INNER, angle + halfArc)

        return (
          <polygon
            key={i}
            points={`${x1},${y1} ${x2},${y2} ${x3},${y3} ${x4},${y4}`}
            fill="rgba(56, 189, 248, 0.82)"
            stroke="rgba(56, 189, 248, 1)"
            strokeWidth="0.4"
          />
        )
      })}

      {/* Center origin */}
      <circle cx={CX} cy={CY} r="2.5" fill="rgba(56, 189, 248, 0.95)"/>
      <circle cx={CX} cy={CY} r="6" fill="none" stroke="rgba(56, 189, 248, 0.4)" strokeWidth="0.5"/>

      {/* Cardinal labels — 8 directions */}
      {CARDINALS.map(({ label, angle }) => {
        const [lx, ly] = polar(CX, CY, R_OUTER + 12, angle)
        const isPrimary = angle % 90 === 0
        return (
          <text
            key={label}
            x={lx} y={ly}
            textAnchor="middle"
            dominantBaseline="middle"
            className={`rose-label ${isPrimary ? 'rose-label--primary' : ''}`}
          >
            {label}
          </text>
        )
      })}
    </svg>
  )
}
