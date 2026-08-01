import { useState, useEffect, useCallback, useRef, useMemo } from 'react'
import DeckGL from '@deck.gl/react'
import { ScatterplotLayer, GeoJsonLayer } from '@deck.gl/layers'
import './Map.css'

type Flight = {
  icao24: string
  callsign: string | null
  longitude: number | null
  latitude: number | null
  baro_altitude: number | null
  velocity: number | null
  vertical_rate: number | null
  true_track: number | null
  on_ground: boolean
  origin_country: string
}

type FlightLookup = {
  model: string | null
  typecode: string | null
  operator: string | null
  registration: string | null
  departure: string | null
  departure_name: string | null
  arrival: string | null
  arrival_name: string | null
}

type HoverInfo = { object: Flight; x: number; y: number } | null

type Region = 'EU' | 'FR' | 'WORLD'

const REGION_VIEW: Record<Region, { longitude: number; latitude: number; zoom: number }> = {
  EU:    { longitude: 10,  latitude: 50,   zoom: 3.7 },
  FR:    { longitude: 2.3, latitude: 46.5, zoom: 5.2 },
  WORLD: { longitude: 0,   latitude: 20,   zoom: 1.6 },
}

const REGION_LABEL: Record<Region, string> = {
  EU: 'EUROPE', FR: 'FRANCE', WORLD: 'WORLD',
}

const _lookupCache: Record<string, FlightLookup> = {}
let _airlineIndex: Record<string, string> | null = null

const WORLD_GEOJSON = 'https://d2ad6b4ur7yvpq.cloudfront.net/naturalearth-3.3.0/ne_50m_admin_0_countries.geojson'

const REFRESH_MS = 30_000
const TOOLTIP_W  = 230
const TOOLTIP_H  = 200

// Speed-bucket palette. Muted qualitative hues (sage / sky / violet / rose /
// slate) — perceptually distinct without being neon. Amber reserved for
// anomalies (DESIGN.md), so 800+ uses rose (warm but not amber).
type RGBA = [number, number, number, number]
function speedColor(speedKmh: number, onGround: boolean): RGBA {
  if (onGround)            return [96,  110, 130, 175]   // slate
  if (speedKmh < 200)      return [122, 175, 140, 200]   // sage
  if (speedKmh < 600)      return [75,  155, 205, 215]   // sky
  if (speedKmh < 800)      return [155, 140, 200, 215]   // violet
  return                          [215, 120, 130, 220]   // rose
}

function inferType(speedKmh: number, altM: number, onGround: boolean): string {
  if (onGround)        return 'Ground vehicle'
  if (speedKmh < 100)  return 'Helicopter / UAV'
  if (speedKmh < 350)  return 'Turboprop / Light'
  if (speedKmh < 600)  return 'Regional Jet'
  if (altM > 9000)     return 'Long-haul Jet'
  return 'Commercial Jet'
}

function headingLabel(deg: number | null): string {
  if (deg == null) return '—'
  const dirs = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']
  return `${Math.round(deg)}° ${dirs[Math.round(deg / 45) % 8]}`
}

function verticalState(vr: number | null, onGround: boolean): { label: string; symbol: string } {
  if (onGround)                       return { symbol: '●', label: 'On ground' }
  if (vr == null || Math.abs(vr) < 0.5) return { symbol: '→', label: 'Level' }
  if (vr > 0)                         return { symbol: '↑', label: 'Climbing' }
  return                                     { symbol: '↓', label: 'Descending' }
}

export default function Map() {
  const [region, setRegion]               = useState<Region>('EU')
  const [flights, setFlights]             = useState<Flight[]>([])
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [world, setWorld]                 = useState<any>(null)
  const [hover, setHover]                 = useState<HoverInfo>(null)
  const [lookup, setLookup]               = useState<FlightLookup | null>(null)
  const [lookupLoading, setLookupLoading] = useState(false)
  const [lastUpdate, setLastUpdate]       = useState<Date | null>(null)
  const [loading, setLoading]             = useState(true)
  const [error, setError]                 = useState(false)
  const [airlines, setAirlines]           = useState<Record<string, string>>({})
  const containerRef = useRef<HTMLDivElement>(null)
  const timerRef     = useRef<ReturnType<typeof setInterval> | null>(null)
  const lookupTimer  = useRef<ReturnType<typeof setTimeout> | null>(null)
  const hideTimer    = useRef<ReturnType<typeof setTimeout> | null>(null)

  const fetchFlights = useCallback(async (r: Region) => {
    try {
      const res = await fetch(`/api/flights/live?country=${r}`)
      if (!res.ok) throw new Error()
      const data: Flight[] = await res.json()
      setFlights(data.filter(f => f.longitude != null && f.latitude != null))
      setLastUpdate(new Date())
      setError(false)
    } catch {
      setError(true)
    } finally {
      setLoading(false)
    }
  }, [])

  const fetchLookup = useCallback(async (flight: Flight) => {
    const key = flight.icao24
    if (_lookupCache[key]) {
      setLookup(_lookupCache[key])
      setLookupLoading(false)
      return
    }
    setLookupLoading(true)
    try {
      const params = new URLSearchParams({ icao24: flight.icao24 })
      if (flight.callsign) params.set('callsign', flight.callsign)
      const res = await fetch(`/api/flights/lookup?${params}`)
      if (res.ok) {
        const data: FlightLookup = await res.json()
        _lookupCache[key] = data
        setLookup(data)
      }
    } catch { /* silent */ }
    finally { setLookupLoading(false) }
  }, [])

  // One-time loaders: world geojson + airline ICAO3 index
  useEffect(() => {
    fetch(WORLD_GEOJSON).then(r => r.json()).then(setWorld).catch(() => {})
    if (_airlineIndex) {
      setAirlines(_airlineIndex)
    } else {
      fetch('/api/flights/airlines/index')
        .then(r => r.ok ? r.json() : {})
        .then((idx: Record<string, string>) => {
          _airlineIndex = idx
          setAirlines(idx)
        })
        .catch(() => {})
    }
  }, [])

  // Refresh loop keyed on region
  useEffect(() => {
    setLoading(true)
    fetchFlights(region)
    if (timerRef.current) clearInterval(timerRef.current)
    timerRef.current = setInterval(() => fetchFlights(region), REFRESH_MS)
    return () => { if (timerRef.current) clearInterval(timerRef.current) }
  }, [region, fetchFlights])

  const handleHover = useCallback((info: { object?: Flight; x: number; y: number }) => {
    if (hideTimer.current) clearTimeout(hideTimer.current)

    if (!info.object) {
      hideTimer.current = setTimeout(() => {
        setHover(null)
        setLookup(null)
      }, 250)
      return
    }

    if (lookupTimer.current) clearTimeout(lookupTimer.current)

    const cw = containerRef.current?.offsetWidth ?? window.innerWidth
    const x  = Math.min(info.x + 16, cw - TOOLTIP_W - 8)
    const y  = Math.max(info.y - TOOLTIP_H - 12, 8)

    setHover({ object: info.object, x, y })
    setLookup(null)
    lookupTimer.current = setTimeout(() => fetchLookup(info.object!), 80)
  }, [fetchLookup])

  const airborne = useMemo(() => flights.filter(f => !f.on_ground), [flights])
  const onGround = useMemo(() => flights.filter(f =>  f.on_ground), [flights])

  // Deck.gl needs stable view state per region — recompute on region change only
  const viewState = useMemo(
    () => ({ ...REGION_VIEW[region], pitch: 0, bearing: 0 }),
    [region],
  )

  const layers = [
    world && new GeoJsonLayer({
      id: 'world',
      data: world,
      stroked: true,
      filled: true,
      getFillColor: [20, 29, 47],
      getLineColor: [38, 57, 90],
      lineWidthMinPixels: 0.5,
    }),
    // Soft halo around airborne flights — picks up sky-blue, no shadow.
    // Opacity reduced from 22 → 14 to soften the overall map glow.
    airborne.length > 0 && new ScatterplotLayer<Flight>({
      id: 'airborne-glow',
      data: airborne,
      getPosition: f => [f.longitude!, f.latitude!],
      getFillColor: [56, 145, 200, 14],
      getRadius: 11000,
      radiusMinPixels: 8,
      radiusMaxPixels: 20,
      pickable: false,
    }),
    // On-ground: small fog dots
    new ScatterplotLayer<Flight>({
      id: 'on-ground',
      data: onGround,
      getPosition: f => [f.longitude!, f.latitude!],
      getFillColor: f => speedColor(0, f.on_ground),
      getRadius: 2000,
      radiusMinPixels: 1.5,
      radiusMaxPixels: 5,
      pickable: true,
      onHover: handleHover,
    }),
    // Airborne: speed-coded core dots
    new ScatterplotLayer<Flight>({
      id: 'airborne',
      data: airborne,
      getPosition: f => [f.longitude!, f.latitude!],
      getFillColor: f => speedColor((f.velocity ?? 0) * 3.6, false),
      getRadius: 4800,
      radiusMinPixels: 2.8,
      radiusMaxPixels: 8,
      stroked: true,
      getLineColor: [11, 17, 32, 200],
      lineWidthMinPixels: 0.5,
      pickable: true,
      onHover: handleHover,
      updateTriggers: { getFillColor: airlines },
    }),
    // Hovered ring: sky-blue, structural (no decorative glow)
    hover && new ScatterplotLayer<Flight>({
      id: 'highlight',
      data: [hover.object],
      getPosition: f => [f.longitude!, f.latitude!],
      getFillColor: [56, 189, 248, 0],
      getLineColor: [56, 189, 248, 220],
      stroked: true,
      filled: false,
      getLineWidth: 2,
      lineWidthMinPixels: 1.5,
      getRadius: 10000,
      radiusMinPixels: 14,
      radiusMaxPixels: 26,
      pickable: false,
    }),
  ].filter(Boolean)

  const total       = flights.length
  const airborneCt  = airborne.length
  const onGroundCt  = onGround.length
  const positioned  = total // already filtered above

  // Tooltip data derivations (only when hovering)
  const h = hover?.object
  const speedKmh   = h?.velocity != null ? Math.round(h.velocity * 3.6) : null
  const altM       = h?.baro_altitude != null ? Math.round(h.baro_altitude) : null
  const altFt      = altM != null ? Math.round(altM * 3.281) : null
  const heading    = h ? headingLabel(h.true_track) : null
  const vState     = h ? verticalState(h.vertical_rate, h.on_ground) : null
  const airlineNm  = h?.callsign ? airlines[h.callsign.trim().slice(0, 3).toUpperCase()] : undefined
  const acType     = h && speedKmh != null ? inferType(speedKmh, altM ?? 0, h.on_ground) : null

  return (
    <div ref={containerRef} className="map-container">
      {/* ─── Metrics + controls strip ─── */}
      <div className="map-strip">
        <div className="map-metrics">
          <div className="map-metric">
            <span className="map-metric-label">TOTAL</span>
            <span className="map-metric-value">{loading ? '—' : total.toLocaleString()}</span>
          </div>
          <div className="map-metric">
            <span className="map-metric-label">AIRBORNE</span>
            <span className="map-metric-value map-metric-value--sky">{loading ? '—' : airborneCt.toLocaleString()}</span>
          </div>
          <div className="map-metric">
            <span className="map-metric-label">ON GROUND</span>
            <span className="map-metric-value map-metric-value--secondary">{loading ? '—' : onGroundCt.toLocaleString()}</span>
          </div>
          <div className="map-metric">
            <span className="map-metric-label">REGION</span>
            <span className="map-metric-value map-metric-value--text">{REGION_LABEL[region]}</span>
          </div>
        </div>

        <div className="map-controls">
          {(['FR', 'EU', 'WORLD'] as Region[]).map(r => (
            <button
              key={r}
              type="button"
              className={`map-region-btn ${region === r ? 'map-region-btn--active' : ''}`}
              onClick={() => setRegion(r)}
              aria-pressed={region === r}
            >
              {REGION_LABEL[r]}
            </button>
          ))}
        </div>
      </div>

      {/* ─── Legend: speed buckets + tooltip key glossary ─── */}
      <div className="map-legend">
        <div className="map-legend-row">
          <span className="map-legend-rowlabel">SPEED</span>
          <span className="map-legend-item"><span className="map-legend-dot" style={{ background: 'rgb(122,175,140)' }} /> &lt;200</span>
          <span className="map-legend-item"><span className="map-legend-dot" style={{ background: 'rgb(75,155,205)'  }} /> 200–600</span>
          <span className="map-legend-item"><span className="map-legend-dot" style={{ background: 'rgb(155,140,200)' }} /> 600–800</span>
          <span className="map-legend-item"><span className="map-legend-dot" style={{ background: 'rgb(215,120,130)' }} /> 800+</span>
          <span className="map-legend-item"><span className="map-legend-dot" style={{ background: 'rgb(96,110,130)'  }} /> GROUND</span>
          <span className="map-legend-unit">km/h</span>
        </div>
        <div className="map-legend-row map-legend-row--glossary">
          <span className="map-legend-rowlabel">KEY</span>
          <span className="map-legend-gloss"><b>ALT</b> altitude</span>
          <span className="map-legend-gloss"><b>SPD</b> speed</span>
          <span className="map-legend-gloss"><b>HDG</b> heading</span>
          <span className="map-legend-gloss"><b>VRT</b> vertical state</span>
          <span className="map-legend-gloss"><b>FROM / TO</b> route</span>
          <span className="map-legend-gloss"><b>est.</b> aircraft type inferred from speed and altitude</span>
        </div>
      </div>

      {/* ─── Deck.gl canvas ─── */}
      <div className="map-canvas">
        <DeckGL
          initialViewState={viewState}
          controller
          layers={layers}
          pickingRadius={12}
          getCursor={({ isHovering }) => isHovering ? 'pointer' : 'grab'}
          style={{ background: '#0B1120' }}
        />

        {lastUpdate && (
          <div className="map-refresh">
            <span className="map-refresh-dot" />
            UPDATED {lastUpdate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })} · {positioned.toLocaleString()} POSITIONED
          </div>
        )}

        {error && <div className="map-error">OpenSky unreachable. Retrying…</div>}

        {hover && h && (() => {
          // Derive stable values for the tooltip — every section has a defined state.
          const operatorLine = airlineNm
            ?? (h.origin_country ? `from ${h.origin_country}` : 'Unknown operator')
          const aircraftLine = lookup?.model
            ? `${lookup.model}${lookup.typecode ? ` · ${lookup.typecode}` : ''}`
            : (acType ?? '—')
          const hasRealAircraft = !!lookup?.model
          const hasRoute = !!(lookup?.departure_name || lookup?.arrival_name)
          const routeResolved = !lookupLoading && lookup !== null
          const altStr = altM != null ? `${altM.toLocaleString()} m · ${altFt!.toLocaleString()} ft` : '—'
          const spdStr = speedKmh != null ? `${speedKmh.toLocaleString()} km/h` : '—'
          const footerParts = [h.icao24.toUpperCase(), lookup?.registration].filter(Boolean)

          return (
            <div className="map-tooltip" style={{ left: hover.x, top: hover.y }}>
              {/* ─── Identity ─── */}
              <div className="tt-section tt-section--identity">
                <span className="tt-callsign">{h.callsign?.trim() || h.icao24}</span>
                <span className="tt-operator">{operatorLine}</span>
                <span className={`tt-aircraft ${hasRealAircraft ? '' : 'tt-aircraft--estimated'}`}>
                  {aircraftLine}
                  {!hasRealAircraft && aircraftLine !== '—' && (
                    <span className="tt-est-tag">est.</span>
                  )}
                </span>
              </div>

              {/* ─── Route (stable shape: 3 states) ─── */}
              <div className="tt-section tt-section--route">
                <span className="tt-section-label">ROUTE</span>
                {!routeResolved && (
                  <span className="tt-state">Loading…</span>
                )}
                {routeResolved && !hasRoute && (
                  <span className="tt-state">No route data available</span>
                )}
                {routeResolved && hasRoute && (
                  <div className="tt-route">
                    <div className="tt-route-row">
                      <span className="tt-route-label">FROM</span>
                      <span className="tt-route-value">
                        {lookup?.departure_name ?? '—'}
                      </span>
                    </div>
                    <div className="tt-route-row">
                      <span className="tt-route-label">TO</span>
                      <span className="tt-route-value">
                        {lookup?.arrival_name ?? '—'}
                      </span>
                    </div>
                  </div>
                )}
              </div>

              {/* ─── Telemetry (always 4 rows) ─── */}
              <div className="tt-section tt-section--telemetry">
                <div className="tt-tel">
                  <span className="tt-tel-key">ALT</span>
                  <span className="tt-tel-value">{altStr}</span>
                </div>
                <div className="tt-tel">
                  <span className="tt-tel-key">SPD</span>
                  <span className="tt-tel-value">{spdStr}</span>
                </div>
                <div className="tt-tel">
                  <span className="tt-tel-key">HDG</span>
                  <span className="tt-tel-value">{heading ?? '—'}</span>
                </div>
                <div className="tt-tel">
                  <span className="tt-tel-key">VRT</span>
                  <span className="tt-tel-value">
                    {vState ? `${vState.symbol} ${vState.label}` : '—'}
                  </span>
                </div>
              </div>

              {/* ─── Footer ─── */}
              <span className="tt-footer">{footerParts.join(' · ')}</span>
            </div>
          )
        })()}
      </div>
    </div>
  )
}
