from datetime import datetime

import httpx
from fastapi import HTTPException

from app.config import settings
from app.data.models import Airline, Airport, FlightSchedule
from app.utils.cache import TTLCache

_BASE_URL = "https://api.aviationstack.com/v1"
_TTL_24H = 86_400.0

_cache = TTLCache()


class AviationStackClient:
    def __init__(self) -> None:
        self._http = httpx.AsyncClient(timeout=10.0)

    async def _get(self, endpoint: str, params: dict) -> dict:
        if not settings.aviationstack_api_key:
            raise HTTPException(status_code=503, detail="AVIATIONSTACK_API_KEY not configured")

        response = await self._http.get(
            f"{_BASE_URL}/{endpoint}",
            params={"access_key": settings.aviationstack_api_key, **params},
        )
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=502,
                detail=f"AviationStack error ({e.response.status_code})",
            )
        data = response.json()
        if "error" in data:
            raise HTTPException(status_code=502, detail=data["error"].get("message", "AviationStack error"))
        return data

    async def get_airport(self, iata_code: str) -> Airport:
        key = f"airport:{iata_code.upper()}"
        cached = _cache.get(key)
        if cached is not None:
            return cached

        data = await self._get("airports", {"iata_code": iata_code.upper()})
        rows = data.get("data") or []
        if not rows:
            raise HTTPException(status_code=404, detail=f"Airport '{iata_code}' not found")

        airport = _parse_airport(rows[0])
        _cache.set(key, airport, ttl=_TTL_24H)
        return airport

    async def get_airline(self, iata_code: str) -> Airline:
        key = f"airline:{iata_code.upper()}"
        cached = _cache.get(key)
        if cached is not None:
            return cached

        data = await self._get("airlines", {"iata_code": iata_code.upper()})
        rows = data.get("data") or []
        if not rows:
            raise HTTPException(status_code=404, detail=f"Airline '{iata_code}' not found")

        airline = _parse_airline(rows[0])
        _cache.set(key, airline, ttl=_TTL_24H)
        return airline

    async def get_flight(self, flight_iata: str) -> FlightSchedule:
        key = f"flight:{flight_iata.upper()}"
        cached = _cache.get(key)
        if cached is not None:
            return cached

        data = await self._get("flights", {"flight_iata": flight_iata.upper()})
        rows = data.get("data") or []
        if not rows:
            raise HTTPException(status_code=404, detail=f"Flight '{flight_iata}' not found")

        flight = _parse_flight(rows[0])
        _cache.set(key, flight, ttl=_TTL_24H)
        return flight

    async def close(self) -> None:
        await self._http.aclose()


def _parse_airport(row: dict) -> Airport:
    return Airport(
        iata_code=row.get("iata_code") or "",
        name=row.get("airport_name") or "",
        city=row.get("city_iata_code"),
        country=row.get("country_name"),
        latitude=_to_float(row.get("latitude")),
        longitude=_to_float(row.get("longitude")),
    )


def _parse_airline(row: dict) -> Airline:
    return Airline(
        iata_code=row.get("iata_code") or "",
        name=row.get("airline_name") or "",
        country=row.get("country_name"),
        callsign=row.get("callsign"),
    )


def _parse_flight(row: dict) -> FlightSchedule:
    dep = row.get("departure") or {}
    arr = row.get("arrival") or {}
    flight = row.get("flight") or {}
    airline = row.get("airline") or {}
    return FlightSchedule(
        flight_iata=flight.get("iata") or "",
        airline_iata=airline.get("iata"),
        departure_iata=dep.get("iata"),
        arrival_iata=arr.get("iata"),
        scheduled_departure=_to_datetime(dep.get("scheduled")),
        scheduled_arrival=_to_datetime(arr.get("scheduled")),
        status=row.get("flight_status"),
    )


def _to_float(value: object) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _to_datetime(value: object) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None
