"""Collect OpenSky snapshots over time and save to a JSONL file for model training.

Usage:
    uv run python scripts/collect_flights.py --duration 1440 --interval 60
    # duration in minutes (1440 = 24h), interval in seconds between calls
"""

import argparse
import asyncio
import json
import time
from pathlib import Path

from app.data.models import BBOX_EUROPE
from app.data.opensky import OpenSkyClient

OUTPUT_PATH = Path("app/ml/data/flights.jsonl")


async def collect(duration_minutes: int, interval_seconds: int) -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    client = OpenSkyClient()
    end_time = time.monotonic() + duration_minutes * 60
    snapshot = 0

    print(f"Collecting for {duration_minutes} min, every {interval_seconds}s → {OUTPUT_PATH}")

    try:
        while time.monotonic() < end_time:
            try:
                flights = await client.get_flights(BBOX_EUROPE)
                rows = [
                    {
                        "velocity": f.velocity,
                        "baro_altitude": f.baro_altitude,
                        "vertical_rate": f.vertical_rate,
                    }
                    for f in flights
                    if f.velocity is not None and f.baro_altitude is not None and f.vertical_rate is not None
                ]
                with OUTPUT_PATH.open("a", encoding="utf-8") as fh:
                    for row in rows:
                        fh.write(json.dumps(row) + "\n")
                snapshot += 1
                print(f"Snapshot {snapshot}: {len(rows)} flights saved", end="\r")
            except Exception as e:
                print(f"\nSnapshot {snapshot} failed: {e}")

            await asyncio.sleep(interval_seconds)
    finally:
        await client.close()

    print(f"\nDone. {snapshot} snapshots collected → {OUTPUT_PATH}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--duration", type=int, default=1440, help="Collection duration in minutes")
    parser.add_argument("--interval", type=int, default=60, help="Interval between snapshots in seconds")
    args = parser.parse_args()
    asyncio.run(collect(args.duration, args.interval))
