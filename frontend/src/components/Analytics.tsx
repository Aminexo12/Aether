import { useState, useEffect, useCallback } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip,
  ResponsiveContainer, Cell,
} from 'recharts'
import './Analytics.css'

type CountryCount = { country: string; count: number }
type Bin          = { label: string; count: number }

type Overview = {
  total: number
  airborne: number
  on_ground: number
  airborne_pct: number
  avg_speed_kmh: number | null
  avg_altitude_m: number | null
  top_countries: CountryCount[]
  altitude_dist: Bin[]
  speed_dist: Bin[]
}

const REFRESH_MS = 60_000
const AMBER = '#F59E0B'
const SKY   = '#38BDF8'
const FOG   = '#4A5E78'

function StatCard({ label, value, unit }: { label: string; value: string; unit?: string }) {
  return (
    <div className="stat-card">
      <span className="stat-label">{label}</span>
      <span className="stat-value">
        {value}
        {unit && <span className="stat-unit">{unit}</span>}
      </span>
    </div>
  )
}

const ChartTooltip = ({ active, payload }: { active?: boolean; payload?: { value: number }[] }) => {
  if (!active || !payload?.length) return null
  return (
    <div className="chart-tooltip">
      <span className="chart-tooltip-value">{payload[0].value.toLocaleString()}</span>
    </div>
  )
}

export default function Analytics() {
  const [data, setData]       = useState<Overview | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState(false)

  const fetchData = useCallback(async () => {
    try {
      const res = await fetch('/api/analytics/overview?country=EU')
      if (!res.ok) throw new Error()
      setData(await res.json())
      setError(false)
    } catch {
      setError(true)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchData()
    const id = setInterval(fetchData, REFRESH_MS)
    return () => clearInterval(id)
  }, [fetchData])

  if (loading) {
    return (
      <div className="analytics-loading">
        <span className="analytics-loading-text">Loading traffic data…</span>
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="analytics-loading">
        <span className="analytics-error-text">Could not reach API</span>
      </div>
    )
  }

  return (
    <div className="analytics">
      {/* ── Stat cards ── */}
      <div className="stat-row">
        <StatCard label="TOTAL FLIGHTS" value={data.total.toLocaleString()} />
        <StatCard label="AIRBORNE" value={data.airborne_pct.toString()} unit="%" />
        <StatCard
          label="AVG SPEED"
          value={data.avg_speed_kmh != null ? Math.round(data.avg_speed_kmh).toLocaleString() : '—'}
          unit=" km/h"
        />
        <StatCard
          label="AVG ALTITUDE"
          value={data.avg_altitude_m != null ? Math.round(data.avg_altitude_m).toLocaleString() : '—'}
          unit=" m"
        />
      </div>

      {/* ── Charts ── */}
      <div className="charts-grid">

        {/* Top countries */}
        <div className="chart-card chart-card--wide">
          <span className="chart-title">TOP COUNTRIES · FLIGHTS</span>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart
              data={data.top_countries}
              layout="vertical"
              margin={{ top: 4, right: 16, left: 0, bottom: 0 }}
            >
              <XAxis type="number" tick={{ fill: FOG, fontSize: 11, fontFamily: 'JetBrains Mono' }} axisLine={false} tickLine={false} />
              <YAxis type="category" dataKey="country" width={120} tick={{ fill: '#8899AA', fontSize: 11, fontFamily: 'JetBrains Mono' }} axisLine={false} tickLine={false} />
              <Tooltip content={<ChartTooltip />} cursor={{ fill: 'rgba(56,189,248,0.06)' }} />
              <Bar dataKey="count" radius={[0, 2, 2, 0]}>
                {data.top_countries.map((_, i) => (
                  <Cell key={i} fill={i === 0 ? AMBER : `rgba(56,189,248,${0.7 - i * 0.05})`} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Altitude distribution */}
        <div className="chart-card">
          <span className="chart-title">ALTITUDE DISTRIBUTION</span>
          <ResponsiveContainer width="100%" height={160}>
            <BarChart data={data.altitude_dist} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
              <XAxis dataKey="label" tick={{ fill: FOG, fontSize: 10, fontFamily: 'JetBrains Mono' }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: FOG, fontSize: 10, fontFamily: 'JetBrains Mono' }} axisLine={false} tickLine={false} />
              <Tooltip content={<ChartTooltip />} cursor={{ fill: 'rgba(56,189,248,0.06)' }} />
              <Bar dataKey="count" fill={SKY} opacity={0.75} radius={[2, 2, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Speed distribution */}
        <div className="chart-card">
          <span className="chart-title">SPEED DISTRIBUTION</span>
          <ResponsiveContainer width="100%" height={160}>
            <BarChart data={data.speed_dist} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
              <XAxis dataKey="label" tick={{ fill: FOG, fontSize: 10, fontFamily: 'JetBrains Mono' }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: FOG, fontSize: 10, fontFamily: 'JetBrains Mono' }} axisLine={false} tickLine={false} />
              <Tooltip content={<ChartTooltip />} cursor={{ fill: 'rgba(245,158,11,0.06)' }} />
              <Bar dataKey="count" fill={AMBER} opacity={0.75} radius={[2, 2, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

      </div>
    </div>
  )
}
