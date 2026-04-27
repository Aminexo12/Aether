import csv
from pathlib import Path

from app.data.models import Airline, Airport

_DATA_DIR = Path(__file__).parent

# Loaded once at import time — O(1) lookups after that
_airports: dict[str, Airport] = {}
_airlines: dict[str, Airline] = {}


def _load_airports() -> dict[str, Airport]:
    result: dict[str, Airport] = {}
    with open(_DATA_DIR / "airports.dat", encoding="utf-8") as f:
        for row in csv.reader(f):
            if len(row) < 8:
                continue
            iata = row[4].strip()
            if not iata or iata == r"\N":
                continue
            try:
                result[iata] = Airport(
                    iata_code=iata,
                    name=row[1],
                    city=row[2] or None,
                    country=row[3] or None,
                    latitude=float(row[6]),
                    longitude=float(row[7]),
                )
            except (ValueError, IndexError):
                continue
    return result


def _load_airlines() -> dict[str, Airline]:
    result: dict[str, Airline] = {}
    with open(_DATA_DIR / "airlines.dat", encoding="utf-8") as f:
        for row in csv.reader(f):
            if len(row) < 7:
                continue
            iata = row[3].strip()
            if not iata or iata == r"\N" or iata == "-":
                continue
            result[iata] = Airline(
                iata_code=iata,
                name=row[1],
                country=row[6] or None,
                callsign=row[5] if row[5] and row[5] != r"\N" else None,
            )
    return result


def get_airport(iata_code: str) -> Airport | None:
    return _airports.get(iata_code.upper())


def get_airline(iata_code: str) -> Airline | None:
    return _airlines.get(iata_code.upper())


# Load on import
_airports = _load_airports()
_airlines = _load_airlines()
