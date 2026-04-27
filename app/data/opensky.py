import time
from datetime import datetime

import httpx

from app.config import settings
from app.data.models import BoundingBox, Flight
from app.utils.cache import TTLCache

_TOKEN_URL = "https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token"
_STATES_URL = "https://opensky-network.org/api/states/all"

_cache = TTLCache()


class TokenManager:
    def __init__(self) -> None:
        self._token: str | None = None
        self._expires_at: float = 0.0

    async def get_token(self, client: httpx.AsyncClient) -> str:
        if self._token and time.monotonic() < self._expires_at - 30:
            return self._token

        response = await client.post(
            _TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": settings.opensky_client_id,
                "client_secret": settings.opensky_client_secret,
            },
        )
        response.raise_for_status()
        payload = response.json()

        self._token = payload["access_token"]
        self._expires_at = time.monotonic() + payload["expires_in"]
        return self._token


class OpenSkyClient:
    def __init__(self) -> None:
        self._token_manager = TokenManager()
        self._http = httpx.AsyncClient(timeout=10.0)

    async def get_flights(self, bbox: BoundingBox) -> list[Flight]:
        cache_key = f"flights:{bbox.lamin},{bbox.lomin},{bbox.lamax},{bbox.lomax}"
        cached = _cache.get(cache_key)
        if cached is not None:
            return cached

        token = await self._token_manager.get_token(self._http)
        response = await self._http.get(
            _STATES_URL,
            params={
                "lamin": bbox.lamin,
                "lomin": bbox.lomin,
                "lamax": bbox.lamax,
                "lomax": bbox.lomax,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        response.raise_for_status()

        data = response.json()
        flights = [_parse_state(row) for row in (data.get("states") or [])]

        _cache.set(cache_key, flights, ttl=30.0)
        return flights

    async def close(self) -> None:
        await self._http.aclose()


def _parse_state(row: list) -> Flight:
    # OpenSky state vector column order (index → field):
    # 0 icao24, 1 callsign, 2 origin_country, 3 time_position,
    # 4 last_contact, 5 longitude, 6 latitude, 7 baro_altitude,
    # 8 on_ground, 9 velocity, 10 true_track, 11 vertical_rate
    return Flight(
        icao24=row[0],
        callsign=row[1].strip() if row[1] else None,
        origin_country=row[2],
        longitude=row[5],
        latitude=row[6],
        baro_altitude=row[7],
        velocity=row[9],
        true_track=row[10],
        vertical_rate=row[11],
        on_ground=row[8],
        last_contact=datetime.fromtimestamp(row[4]),
    )
