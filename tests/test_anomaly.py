from datetime import datetime

import numpy as np

from app.data.models import Flight
from app.ml.anomaly import _features, detect, train


def _flight(icao: str, velocity: float, altitude: float, vrate: float, on_ground: bool = False) -> Flight:
    return Flight(
        icao24=icao, callsign=icao, origin_country="France",
        longitude=2.0, latitude=48.0,
        baro_altitude=altitude, velocity=velocity, vertical_rate=vrate,
        true_track=90.0, on_ground=on_ground, last_contact=datetime.utcnow(),
    )


def _normal_fleet(n: int = 50) -> list[Flight]:
    rng = np.random.default_rng(0)
    return [
        _flight(f"n{i}", velocity=float(rng.uniform(200, 280)),
                altitude=float(rng.uniform(8000, 12000)),
                vrate=float(rng.uniform(-1, 1)))
        for i in range(n)
    ]


def test_features_drops_missing():
    flights = [
        _flight("ok", 250.0, 10000.0, 0.0),
        Flight(icao24="bad", callsign=None, origin_country="France",
               longitude=None, latitude=None, baro_altitude=None,
               velocity=None, vertical_rate=None, true_track=None,
               on_ground=False, last_contact=datetime.utcnow()),
    ]
    X, valid = _features(flights)
    assert X.shape == (1, 3)
    assert valid[0].icao24 == "ok"


def test_features_shape():
    fleet = _normal_fleet(20)
    X, valid = _features(fleet)
    assert X.shape == (20, 3)
    assert len(valid) == 20


def test_train_and_detect():
    fleet = _normal_fleet(60)
    model = train(fleet, contamination=0.05)
    assert model is not None

    # Inject one obvious outlier (extreme speed + altitude)
    outlier = _flight("out", velocity=900.0, altitude=25000.0, vrate=50.0)
    results = detect(fleet + [outlier])

    assert len(results) > 0
    assert isinstance(results[0]["icao24"], str)
    assert "anomaly_score" in results[0]
    # The outlier should be near the top of the anomaly list
    top_ids = [r["icao24"] for r in results[:3]]
    assert "out" in top_ids


def test_detect_empty_input():
    results = detect([])
    assert results == []


def test_detect_no_valid_features():
    flight = Flight(
        icao24="x", callsign=None, origin_country="France",
        longitude=None, latitude=None, baro_altitude=None,
        velocity=None, vertical_rate=None, true_track=None,
        on_ground=False, last_contact=datetime.utcnow(),
    )
    results = detect([flight])
    assert results == []
