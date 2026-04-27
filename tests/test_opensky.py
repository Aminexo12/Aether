from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.data.models import BBOX_FRANCE, Flight
from app.data.opensky import OpenSkyClient, _parse_state
from app.utils.cache import TTLCache


def make_state_row(overrides: dict | None = None):
    row = [
        "abc123",     # 0 icao24
        "AFR123 ",    # 1 callsign (with trailing space)
        "France",     # 2 origin_country
        1700000000,   # 3 time_position
        1700000001,   # 4 last_contact
        2.35,         # 5 longitude
        48.85,        # 6 latitude
        10000.0,      # 7 baro_altitude
        False,        # 8 on_ground
        250.0,        # 9 velocity
        90.0,         # 10 true_track
        0.0,          # 11 vertical_rate
    ]
    for k, v in (overrides or {}).items():
        row[k] = v
    return row


def test_parse_state_basic():
    flight = _parse_state(make_state_row())
    assert flight.icao24 == "abc123"
    assert flight.callsign == "AFR123"  # trailing space stripped
    assert flight.origin_country == "France"
    assert flight.latitude == 48.85
    assert flight.longitude == 2.35
    assert flight.on_ground is False


def test_parse_state_null_callsign():
    flight = _parse_state(make_state_row({1: None}))
    assert flight.callsign is None


def test_parse_state_null_position():
    flight = _parse_state(make_state_row({5: None, 6: None}))
    assert flight.longitude is None
    assert flight.latitude is None


def test_ttl_cache_hit():
    cache = TTLCache()
    cache.set("k", [1, 2, 3], ttl=60)
    assert cache.get("k") == [1, 2, 3]


def test_ttl_cache_miss():
    cache = TTLCache()
    assert cache.get("missing") is None


def test_ttl_cache_expired():
    cache = TTLCache()
    cache.set("k", "value", ttl=-1)  # already expired
    assert cache.get("k") is None


@pytest.mark.asyncio
async def test_get_flights_uses_cache():
    client = OpenSkyClient()
    flights = [MagicMock(spec=Flight)]

    with patch.object(client, "_token_manager") as mock_tm, \
         patch.object(client, "_http") as mock_http:

        mock_tm.get_token = AsyncMock(return_value="tok")
        mock_http.get = AsyncMock(return_value=MagicMock(
            json=lambda: {"states": [make_state_row()]},
            raise_for_status=lambda: None,
        ))

        result1 = await client.get_flights(BBOX_FRANCE)
        result2 = await client.get_flights(BBOX_FRANCE)

    # Second call should hit cache — HTTP called only once
    assert mock_http.get.call_count == 1
    assert len(result1) == 1
    assert result1 == result2

    await client.close()
