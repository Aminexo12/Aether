"""Train the anomaly detection model on a live OpenSky snapshot.

Usage:
    uv run python -m app.ml.train
"""

import asyncio

from app.data.models import BBOX_EUROPE
from app.data.opensky import OpenSkyClient
from app.ml.anomaly import train


async def main() -> None:
    client = OpenSkyClient()
    try:
        print("Fetching live flights for training...")
        flights = await client.get_flights(BBOX_EUROPE)
    finally:
        await client.close()

    print(f"Got {len(flights)} flights. Training Isolation Forest...")
    model = train(flights)
    print(f"Model trained on {model.n_features_in_} features. Saved to app/ml/artifacts/.")


if __name__ == "__main__":
    asyncio.run(main())
