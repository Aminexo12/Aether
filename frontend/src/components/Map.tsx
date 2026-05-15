import { useState, useEffect, useCallback, useRef } from 'react'
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

const _lookupCache: Record<string, FlightLookup> = {}

const WORLD_GEOJSON = 'https://d2ad6b4ur7yvpq.cloudfront.net/naturalearth-3.3.0/ne_50m_admin_0_countries.geojson'

const INITIAL_VIEW = {
  longitude: 10,
  latitude: 50,
  zoom: 3.8,
  pitch: 0,
  bearing: 0,
}

const REFRESH_MS = 30_000
const TOOLTIP_W  = 230  // max tooltip width in px — used for edge clamping
const TOOLTIP_H  = 160

export default function Map() {
  const [flights, setFlights]               = useState<Flight[]>([])
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [world, setWorld]                   = useState<any>(null)
  const [hover, setHover]                   = useState<HoverInfo>(null)
  const [lookup, setLookup]                 = useState<FlightLookup | null>(null)
  const [lookupLoading, setLookupLoading]   = useState(false)
  const [lastUpdate, setLastUpdate]         = useState<Date | null>(null)
  const [loading, setLoading]               = useState(true)
  const [error, setError]                   = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)
  const timerRef     = useRef<ReturnType<typeof setInterval> | null>(null)
  const lookupTimer  = useRef<ReturnType<typeof setTimeout> | null>(null)
  const hideTimer    = useRef<ReturnType<typeof setTimeout> | null>(null)

  const fetchFlights = useCallback(async () => {
    try {
      const res = await fetch('/api/flights/live?country=EU')
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

  useEffect(() => {
    fetch(WORLD_GEOJSON).then(r => r.json()).then(setWorld).catch(() => {})
    fetchFlights()
    timerRef.current = setInterval(fetchFlights, REFRESH_MS)
    return () => { if (timerRef.current) clearInterval(timerRef.current) }
  }, [fetchFlights])

  const handleHover = useCallback((info: { object?: Flight; x: number; y: number }) => {
    // Cancel any pending hide
    if (hideTimer.current) clearTimeout(hideTimer.current)

    if (!info.object) {
      // Delay hiding so brief mouse-out gaps don't flash the tooltip away
      hideTimer.current = setTimeout(() => {
        setHover(null)
        setLookup(null)
      }, 250)
      return
    }

    if (lookupTimer.current) clearTimeout(lookupTimer.current)

    // Clamp tooltip to container bounds
    const cw = containerRef.current?.offsetWidth ?? window.innerWidth
    const x  = Math.min(info.x + 16, cw - TOOLTIP_W - 8)
    const y  = Math.max(info.y - TOOLTIP_H - 12, 8)

    setHover({ object: info.object, x, y })
    setLookup(null)
    lookupTimer.current = setTimeout(() => fetchLookup(info.object!), 80)
  }, [fetchLookup])

  const airborne = flights.filter(f => !f.on_ground)
  const onGround = flights.filter(f => f.on_ground)

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
    // On-ground: small grey-blue dots
    new ScatterplotLayer<Flight>({
      id: 'on-ground',
      data: onGround,
      getPosition: f => [f.longitude!, f.latitude!],
      getFillColor: [74, 94, 120, 180],
      getRadius: 2000,
      radiusMinPixels: 1.5,
      radiusMaxPixels: 5,
      pickable: true,
      onHover: handleHover,
    }),
    // Airborne: bright amber dots
    new ScatterplotLayer<Flight>({
      id: 'airborne',
      data: airborne,
      getPosition: f => [f.longitude!, f.latitude!],
      getFillColor: [245, 158, 11, 220],
      getRadius: 5000,
      radiusMinPixels: 3,
      radiusMaxPixels: 9,
      pickable: true,
      onHover: handleHover,
    }),
    // Highlight ring around hovered flight
    hover && new ScatterplotLayer<Flight>({
      id: 'highlight',
      data: [hover.object],
      getPosition: f => [f.longitude!, f.latitude!],
      getFillColor: [245, 158, 11, 40],
      getLineColor: [245, 158, 11, 200],
      stroked: true,
      filled: true,
      getLineWidth: 2,
      lineWidthMinPixels: 1.5,
      getRadius: 9000,
      radiusMinPixels: 14,
      radiusMaxPixels: 28,
      pickable: false,
    }),
  ].filter(Boolean)

  return (
    <div ref={containerRef} className="map-container">
      <DeckGL
        initialViewState={INITIAL_VIEW}
        controller
        layers={layers}
        pickingRadius={12}
        getCursor={({ isHovering }) => isHovering ? 'pointer' : 'grab'}
        style={{ background: '#0B1120' }}
      />

      <div className="map-badge">
        <div className="map-badge-row">
          <span className="map-badge-dot map-badge-dot--amber" />
          <span className="map-badge-count">{loading ? '—' : airborne.length.toLocaleString()}</span>
          <span className="map-badge-label">AIRBORNE</span>
        </div>
        <div className="map-badge-row">
          <span className="map-badge-dot map-badge-dot--grey" />
          <span className="map-badge-count map-badge-count--secondary">{loading ? '—' : onGround.length.toLocaleString()}</span>
          <span className="map-badge-label">ON GROUND</span>
        </div>
      </div>

      {lastUpdate && (
        <div className="map-refresh">
          <span className="map-refresh-dot" />
          {lastUpdate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
        </div>
      )}

      {error && <div className="map-error">Could not reach OpenSky API</div>}

      {hover && (
        <div className="map-tooltip" style={{ left: hover.x, top: hover.y }}>
          <span className="map-tooltip-callsign">
            {hover.object.callsign ?? hover.object.icao24}
          </span>

          {lookupLoading && !lookup && (
            <span className="map-tooltip-loading">loading…</span>
          )}

          {(lookup?.departure_name || lookup?.arrival_name) && (
            <div className="map-tooltip-route">
              {lookup?.departure_name && (
                <span className="map-tooltip-route-row">
                  <span className="map-tooltip-key">FROM</span>
                  <span className="map-tooltip-place">{lookup.departure_name}</span>
                </span>
              )}
              {lookup?.arrival_name && (
                <span className="map-tooltip-route-row">
                  <span className="map-tooltip-key">TO</span>
                  <span className="map-tooltip-place">{lookup.arrival_name}</span>
                </span>
              )}
            </div>
          )}

          <div className="map-tooltip-divider" />

          <div className="map-tooltip-stats">
            {lookup?.model && (
              <span className="map-tooltip-row">
                <span className="map-tooltip-key">TYPE</span>
                {lookup.model}{lookup.typecode ? ` (${lookup.typecode})` : ''}
              </span>
            )}
            {hover.object.velocity != null && (
              <span className="map-tooltip-row">
                <span className="map-tooltip-key">SPD</span>
                {Math.round(hover.object.velocity * 3.6)} km/h
              </span>
            )}
            {hover.object.baro_altitude != null && (
              <span className="map-tooltip-row">
                <span className="map-tooltip-key">ALT</span>
                {Math.round(hover.object.baro_altitude).toLocaleString()} m
              </span>
            )}
            {lookup?.operator && (
              <span className="map-tooltip-row">
                <span className="map-tooltip-key">OPR</span>
                {lookup.operator}
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
