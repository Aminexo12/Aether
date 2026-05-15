from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.data.models import Flight
from app.main import app

_SAMPLE_FLIGHTS = [
    Flight(icao24=f"icao{i}", callsign=f"AF{i:03d}", origin_country="France",
           longitude=2.3 + i, latitude=48.8 + i,
           baro_altitude=10000.0, velocity=250.0, true_track=90.0,
           vertical_rate=0.0, on_ground=False, last_contact=datetime.utcnow())
    for i in range(8)
] + [
    Flight(icao24=f"de{i}", callsign=f"DLH{i:03d}", origin_country="Germany",
           longitude=10.0 + i, latitude=51.0 + i,
           baro_altitude=8000.0, velocity=220.0, true_track=180.0,
           vertical_rate=0.0, on_ground=False, last_contact=datetime.utcnow())
    for i in range(4)
] + [
    Flight(icao24="gnd1", callsign="GND001", origin_country="France",
           longitude=2.5, latitude=49.0,
           baro_altitude=0.0, velocity=0.0, true_track=0.0,
           vertical_rate=0.0, on_ground=True, last_contact=datetime.utcnow())
]


@pytest.fixture
def mock_opensky():
    with patch("app.api.analytics._opensky.get_flights", new_callable=AsyncMock) as m:
        m.return_value = _SAMPLE_FLIGHTS
        yield m


@pytest.mark.asyncio
async def test_overview_totals(mock_opensky):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.get("/analytics/overview?country=EU")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 13
    assert data["on_ground"] == 1
    assert data["airborne"] == 12


@pytest.mark.asyncio
async def test_overview_top_countries(mock_opensky):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.get("/analytics/overview?country=EU")
    data = r.json()
    countries = {c["country"]: c["count"] for c in data["top_countries"]}
    assert countries["France"] == 9   # 8 airborne + 1 on ground
    assert countries["Germany"] == 4


@pytest.mark.asyncio
async def test_overview_empty(mock_opensky):
    mock_opensky.return_value = []
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.get("/analytics/overview?country=FR")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 0
    assert data["top_countries"] == []


@pytest.mark.asyncio
async def test_overview_invalid_country(mock_opensky):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.get("/analytics/overview?country=XX")
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_overview_both_params_rejected(mock_opensky):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.get("/analytics/overview?country=FR&bbox=41,2,51,9")
    assert r.status_code == 400
