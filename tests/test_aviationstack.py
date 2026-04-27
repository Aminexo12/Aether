from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.data.aviationstack import (
    AviationStackClient,
    _parse_airline,
    _parse_airport,
    _parse_flight,
)


def airport_row(**overrides):
    row = {
        "iata_code": "CDG",
        "airport_name": "Charles de Gaulle",
        "city_iata_code": "PAR",
        "country_name": "France",
        "latitude": "49.0097",
        "longitude": "2.5479",
    }
    return {**row, **overrides}


def airline_row(**overrides):
    row = {
        "iata_code": "AF",
        "airline_name": "Air France",
        "country_name": "France",
        "callsign": "AIRFRANS",
    }
    return {**row, **overrides}


def flight_row(**overrides):
    row = {
        "flight_status": "active",
        "flight": {"iata": "AF123"},
        "airline": {"iata": "AF"},
        "departure": {"iata": "CDG", "scheduled": "2026-04-27T10:00:00+00:00"},
        "arrival": {"iata": "JFK", "scheduled": "2026-04-27T13:00:00+00:00"},
    }
    return {**row, **overrides}


def test_parse_airport():
    airport = _parse_airport(airport_row())
    assert airport.iata_code == "CDG"
    assert airport.name == "Charles de Gaulle"
    assert airport.latitude == 49.0097
    assert airport.country == "France"


def test_parse_airport_missing_coords():
    airport = _parse_airport(airport_row(latitude=None, longitude=None))
    assert airport.latitude is None
    assert airport.longitude is None


def test_parse_airline():
    airline = _parse_airline(airline_row())
    assert airline.iata_code == "AF"
    assert airline.name == "Air France"
    assert airline.callsign == "AIRFRANS"


def test_parse_flight():
    flight = _parse_flight(flight_row())
    assert flight.flight_iata == "AF123"
    assert flight.airline_iata == "AF"
    assert flight.departure_iata == "CDG"
    assert flight.arrival_iata == "JFK"
    assert flight.status == "active"


@pytest.mark.asyncio
async def test_get_airport_uses_cache():
    client = AviationStackClient()
    mock_response = MagicMock(
        json=lambda: {"data": [airport_row()]},
        raise_for_status=lambda: None,
    )

    with patch.object(client, "_http") as mock_http, \
         patch("app.data.aviationstack.settings") as mock_settings:
        mock_settings.aviationstack_api_key = "test_key"
        mock_http.get = AsyncMock(return_value=mock_response)

        result1 = await client.get_airport("CDG")
        result2 = await client.get_airport("CDG")

    # Second call must hit cache — API called only once
    assert mock_http.get.call_count == 1
    assert result1.iata_code == "CDG"
    assert result1 == result2

    await client.close()
