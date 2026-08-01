import csv
from pathlib import Path

from app.data.models import Airline, Airport

_DATA_DIR = Path(__file__).parent

# Loaded once at import time — O(1) lookups after that
_airports: dict[str, Airport] = {}
_airports_icao: dict[str, Airport] = {}
_airlines: dict[str, Airline] = {}
_airlines_icao3: dict[str, str] = {}  # ICAO 3-letter code → airline name


def _load_airports() -> tuple[dict[str, Airport], dict[str, Airport]]:
    by_iata: dict[str, Airport] = {}
    by_icao: dict[str, Airport] = {}
    with open(_DATA_DIR / "airports.dat", encoding="utf-8") as f:
        for row in csv.reader(f):
            if len(row) < 8:
                continue
            iata = row[4].strip()
            icao = row[5].strip() if len(row) > 5 else ""
            if not iata or iata == r"\N":
                continue
            try:
                airport = Airport(
                    iata_code=iata,
                    name=row[1],
                    city=row[2] or None,
                    country=row[3] or None,
                    latitude=float(row[6]),
                    longitude=float(row[7]),
                )
                by_iata[iata] = airport
                if icao and icao != r"\N":
                    by_icao[icao.upper()] = airport
            except (ValueError, IndexError):
                continue
    return by_iata, by_icao


def _load_airlines() -> tuple[dict[str, Airline], dict[str, str]]:
    by_iata: dict[str, Airline] = {}
    by_icao3: dict[str, str] = {}
    with open(_DATA_DIR / "airlines.dat", encoding="utf-8") as f:
        for row in csv.reader(f):
            if len(row) < 8:
                continue
            iata = row[3].strip()
            icao3 = row[4].strip()
            name = row[1].strip()
            active = row[7].strip()
            if iata and iata not in (r"\N", "-"):
                by_iata[iata] = Airline(
                    iata_code=iata,
                    name=name,
                    country=row[6] or None,
                    callsign=row[5] if row[5] and row[5] != r"\N" else None,
                )
            if icao3 and icao3 not in (r"\N", "-") and name and active == "Y":
                by_icao3[icao3.upper()] = name
    return by_iata, by_icao3


def get_airport(iata_code: str) -> Airport | None:
    return _airports.get(iata_code.upper())


def get_airport_by_icao(icao_code: str) -> Airport | None:
    return _airports_icao.get(icao_code.upper())


def get_airline(iata_code: str) -> Airline | None:
    return _airlines.get(iata_code.upper())


def get_airline_icao3_index() -> dict[str, str]:
    return _airlines_icao3


# Load on import
_airports, _airports_icao = _load_airports()
_airlines, _airlines_icao3 = _load_airlines()
