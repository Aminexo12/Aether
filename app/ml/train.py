"""Train the anomaly detection model.

Two modes:
  1. Live snapshot (default) — fetches current OpenSky data (~2500 flights)
  2. Collected data — loads from app/ml/data/flights.jsonl if it exists (run
     scripts/collect_flights.py first to build this file over 24h)

Usage:
    uv run python -m app.ml.train
"""

import asyncio
import json
from dataclasses import dataclass
from pathlib import Path

from app.data.models import BBOX_EUROPE
from app.data.opensky import OpenSkyClient
from app.ml.anomaly import train

_DATA_PATH = Path("app/ml/data/flights.jsonl")


@dataclass
class _MinFlight:
    velocity: float
    baro_altitude: float
    vertical_rate: float
    origin_country: str = ""
    icao24: str = ""
    callsign: str | None = None
    on_ground: bool = False
    longitude: float | None = None
    latitude: float | None = None
    true_track: float | None = None
    last_contact: object = None


def _load_from_file() -> list:
    rows = []
    with _DATA_PATH.open(encoding="utf-8") as fh:
        for line in fh:
            d = json.loads(line)
            rows.append(_MinFlight(**d))
    return rows


async def main() -> None:
    if _DATA_PATH.exists():
        print(f"Loading collected data from {_DATA_PATH}...")
        flights = _load_from_file()
        print(f"Loaded {len(flights)} records from file.")
    else:
        client = OpenSkyClient()
        try:
            print("No collected data found. Fetching live snapshot...")
            flights = await client.get_flights(BBOX_EUROPE)
        finally:
            await client.close()
        print(f"Got {len(flights)} live flights.")

    print("Training Isolation Forest...")
    model = train(flights)
    print(f"Model trained on {model.n_features_in_} features. Saved to app/ml/artifacts/.")
    print("\nTip: run 'uv run python scripts/collect_flights.py --duration 1440' to")
    print("collect 24h of data, then retrain for a better model.")


if __name__ == "__main__":
    asyncio.run(main())
