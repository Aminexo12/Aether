from datetime import datetime

from pydantic import BaseModel, Field


class Flight(BaseModel):
    icao24: str
    callsign: str | None
    origin_country: str
    longitude: float | None
    latitude: float | None
    baro_altitude: float | None  # meters
    velocity: float | None       # m/s
    true_track: float | None     # degrees from north
    vertical_rate: float | None
    on_ground: bool
    last_contact: datetime


class BoundingBox(BaseModel):
    lamin: float = Field(..., ge=-90, le=90)
    lomin: float = Field(..., ge=-180, le=180)
    lamax: float = Field(..., ge=-90, le=90)
    lomax: float = Field(..., ge=-180, le=180)


BBOX_FRANCE = BoundingBox(lamin=41.3, lomin=-5.1, lamax=51.1, lomax=9.5)
BBOX_EUROPE = BoundingBox(lamin=35.0, lomin=-10.0, lamax=70.0, lomax=40.0)
BBOX_WORLD = BoundingBox(lamin=-90, lomin=-180, lamax=90, lomax=180)
