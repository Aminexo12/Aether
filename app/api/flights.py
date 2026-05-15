import asyncio

import httpx
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.data.models import (
    BBOX_EUROPE,
    BBOX_FRANCE,
    BBOX_WORLD,
    Airline,
    Airport,
    BoundingBox,
    Flight,
)
from app.data.opensky import OpenSkyClient
from app.data.static_data import get_airline, get_airport, get_airport_by_icao
from app.utils.cache import TTLCache

_lookup_cache = TTLCache()

router = APIRouter(prefix="/flights", tags=["flights"])

_opensky = OpenSkyClient()

_COUNTRY_BBOX = {
    "FR": BBOX_FRANCE,
    "EU": BBOX_EUROPE,
    "WORLD": BBOX_WORLD,
}


@router.get("/live", response_model=list[Flight])
async def get_live_flights(
    country: str | None = Query(None, description="Country code: FR, EU, WORLD"),
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
        box = BBOX_WORLD

    return await _opensky.get_flights(box)


@router.get("/airports/{iata_code}", response_model=Airport)
async def get_airport_route(iata_code: str):
    airport = get_airport(iata_code)
    if airport is None:
        raise HTTPException(status_code=404, detail=f"Airport '{iata_code.upper()}' not found")
    return airport


@router.get("/airlines/{iata_code}", response_model=Airline)
async def get_airline_route(iata_code: str):
    airline = get_airline(iata_code)
    if airline is None:
        raise HTTPException(status_code=404, detail=f"Airline '{iata_code.upper()}' not found")
    return airline


class FlightLookup(BaseModel):
    icao24: str
    model: str | None = None
    typecode: str | None = None
    operator: str | None = None
    registration: str | None = None
    departure: str | None = None       # ICAO code
    departure_name: str | None = None  # "City, Country (IATA)"
    arrival: str | None = None         # ICAO code
    arrival_name: str | None = None    # "City, Country (IATA)"


def _resolve_airport(icao: str | None) -> str | None:
    if not icao:
        return None
    ap = get_airport_by_icao(icao)
    if ap is None:
        return icao  # fallback to raw ICAO code
    parts = [ap.city or ap.name]
    if ap.country:
        parts.append(ap.country)
    label = ", ".join(parts)
    return f"{label} ({ap.iata_code})"


async def _fetch_route(client: httpx.AsyncClient, callsign: str) -> tuple[str | None, str | None]:
    try:
        r = await client.get(
            "https://opensky-network.org/api/routes",
            params={"callsign": callsign.strip()},
            timeout=4.0,
        )
        if r.status_code == 200:
            data = r.json()
            route: list[str] = data.get("route") or []
            dep = route[0] if len(route) > 0 else None
            arr = route[-1] if len(route) > 1 else None
            return dep, arr
    except Exception:
        pass
    return None, None


async def _fetch_aircraft(client: httpx.AsyncClient, icao24: str) -> dict:
    try:
        r = await client.get(
            f"https://opensky-network.org/api/metadata/aircraft/icao/{icao24.lower()}",
            timeout=4.0,
        )
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return {}


@router.get("/lookup", response_model=FlightLookup)
async def lookup_flight(
    icao24: str = Query(...),
    callsign: str | None = Query(None),
):
    cache_key = f"lookup:{icao24}:{callsign}"
    cached = _lookup_cache.get(cache_key)
    if cached is not None:
        return cached

    async with httpx.AsyncClient() as client:
        tasks = [_fetch_aircraft(client, icao24)]
        if callsign:
            tasks.append(_fetch_route(client, callsign))
        results = await asyncio.gather(*tasks)

    aircraft = results[0]
    dep, arr = results[1] if callsign else (None, None)

    result = FlightLookup(
        icao24=icao24,
        model=aircraft.get("model") or None,
        typecode=aircraft.get("typecode") or None,
        operator=aircraft.get("operator") or None,
        registration=aircraft.get("registration") or None,
        departure=dep,
        departure_name=_resolve_airport(dep),
        arrival=arr,
        arrival_name=_resolve_airport(arr),
    )

    _lookup_cache.set(cache_key, result, ttl=1800.0)
    return result
