from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.data.models import BBOX_EUROPE, BBOX_FRANCE, BBOX_WORLD, BoundingBox
from app.data.opensky import OpenSkyClient

router = APIRouter(prefix="/analytics", tags=["analytics"])

_opensky = OpenSkyClient()

_COUNTRY_BBOX = {
    "FR": BBOX_FRANCE,
    "EU": BBOX_EUROPE,
    "WORLD": BBOX_WORLD,
}


class CountryCount(BaseModel):
    country: str
    count: int


class Bin(BaseModel):
    label: str
    count: int


class FlightStat(BaseModel):
    callsign: str
    value: float


class AnalyticsOverview(BaseModel):
    total: int
    airborne: int
    on_ground: int
    airborne_pct: float
    avg_speed_kmh: float | None
    avg_altitude_m: float | None
    top_countries: list[CountryCount]
    altitude_dist: list[Bin]
    speed_dist: list[Bin]
    climbing: int
    level: int
    descending: int
    fastest: FlightStat | None
    highest: FlightStat | None


@router.get("/overview", response_model=AnalyticsOverview)
async def get_overview(
    country: str | None = Query(None, description="FR, EU, WORLD"),
    bbox: str | None = Query(None, description="lamin,lomin,lamax,lomax"),
):
    if country and bbox:
        raise HTTPException(status_code=400, detail="Use either 'country' or 'bbox', not both.")

    if country:
        box = _COUNTRY_BBOX.get(country.upper())
        if box is None:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown country code '{country}'. Supported: {list(_COUNTRY_BBOX)}",
            )
    elif bbox:
        parts = bbox.split(",")
        if len(parts) != 4:
            raise HTTPException(status_code=400, detail="bbox must be 'lamin,lomin,lamax,lomax'")
        try:
            box = BoundingBox(
                lamin=float(parts[0]),
                lomin=float(parts[1]),
                lamax=float(parts[2]),
                lomax=float(parts[3]),
            )
        except ValueError:
            raise HTTPException(status_code=400, detail="bbox values must be numbers")
    else:
        box = BBOX_EUROPE

    flights = await _opensky.get_flights(box)

    if not flights:
        return AnalyticsOverview(
            total=0, airborne=0, on_ground=0, airborne_pct=0.0,
            avg_speed_kmh=None, avg_altitude_m=None,
            top_countries=[], altitude_dist=[], speed_dist=[],
            climbing=0, level=0, descending=0, fastest=None, highest=None,
        )

    total = len(flights)
    on_ground = sum(1 for f in flights if f.on_ground)
    airborne = total - on_ground
    airborne_pct = round(airborne / total * 100, 1) if total else 0.0

    speeds_kmh = [f.velocity * 3.6 for f in flights if f.velocity is not None and not f.on_ground]
    altitudes = [f.baro_altitude for f in flights if f.baro_altitude is not None and f.baro_altitude > 0]

    avg_speed_kmh = round(sum(speeds_kmh) / len(speeds_kmh), 1) if speeds_kmh else None
    avg_altitude_m = round(sum(altitudes) / len(altitudes), 1) if altitudes else None

    # Top 10 countries
    country_counts: dict[str, int] = {}
    for f in flights:
        country_counts[f.origin_country] = country_counts.get(f.origin_country, 0) + 1
    top_countries = [
        CountryCount(country=c, count=n)
        for c, n in sorted(country_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    ]

    # Altitude distribution (meters)
    alt_bins = [
        ("0-3000 m",    0,     3_000),
        ("3000-6000 m", 3_000, 6_000),
        ("6000-9000 m", 6_000, 9_000),
        ("9000-12000 m", 9_000, 12_000),
        ("12000+ m",    12_000, float("inf")),
    ]
    altitude_dist = [
        Bin(label=label, count=sum(1 for a in altitudes if lo <= a < hi))
        for label, lo, hi in alt_bins
    ]

    # Speed distribution (km/h)
    speed_bins = [
        ("0-200 km/h",   0,   200),
        ("200-400 km/h", 200, 400),
        ("400-600 km/h", 400, 600),
        ("600-800 km/h", 600, 800),
        ("800+ km/h",    800, float("inf")),
    ]
    speed_dist = [
        Bin(label=label, count=sum(1 for s in speeds_kmh if lo <= s < hi))
        for label, lo, hi in speed_bins
    ]

    # Vertical rate breakdown
    climbing = sum(1 for f in flights if not f.on_ground and f.vertical_rate and f.vertical_rate > 1.0)
    descending = sum(1 for f in flights if not f.on_ground and f.vertical_rate and f.vertical_rate < -1.0)
    level = airborne - climbing - descending

    # Fastest airborne flight
    airborne_with_speed = [f for f in flights if not f.on_ground and f.velocity]
    if airborne_with_speed:
        f_fast = max(airborne_with_speed, key=lambda f: f.velocity)
        fastest = FlightStat(
            callsign=((f_fast.callsign or "").strip() or f_fast.icao24),
            value=round(f_fast.velocity * 3.6, 1),
        )
    else:
        fastest = None

    # Highest airborne flight
    airborne_with_alt = [f for f in flights if not f.on_ground and f.baro_altitude and f.baro_altitude > 0]
    if airborne_with_alt:
        f_high = max(airborne_with_alt, key=lambda f: f.baro_altitude)
        highest = FlightStat(
            callsign=((f_high.callsign or "").strip() or f_high.icao24),
            value=round(f_high.baro_altitude, 0),
        )
    else:
        highest = None

    return AnalyticsOverview(
        total=total,
        airborne=airborne,
        on_ground=on_ground,
        airborne_pct=airborne_pct,
        avg_speed_kmh=avg_speed_kmh,
        avg_altitude_m=avg_altitude_m,
        top_countries=top_countries,
        altitude_dist=altitude_dist,
        speed_dist=speed_dist,
        climbing=climbing,
        level=level,
        descending=descending,
        fastest=fastest,
        highest=highest,
    )
