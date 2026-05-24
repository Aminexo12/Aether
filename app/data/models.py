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


BBOX_FRANCE       = BoundingBox(lamin=41.3, lomin=-5.1,  lamax=51.1, lomax=9.5)
BBOX_SPAIN        = BoundingBox(lamin=36.0, lomin=-9.0,  lamax=43.8, lomax=3.3)
BBOX_GERMANY      = BoundingBox(lamin=47.3, lomin=5.9,   lamax=55.1, lomax=15.0)
BBOX_UK           = BoundingBox(lamin=49.9, lomin=-8.2,  lamax=60.9, lomax=1.8)
BBOX_ITALY        = BoundingBox(lamin=36.6, lomin=6.6,   lamax=47.1, lomax=18.5)
BBOX_BELGIUM      = BoundingBox(lamin=49.5, lomin=2.5,   lamax=51.5, lomax=6.4)
BBOX_NETHERLANDS  = BoundingBox(lamin=50.7, lomin=3.3,   lamax=53.7, lomax=7.2)
BBOX_SWITZERLAND  = BoundingBox(lamin=45.8, lomin=5.9,   lamax=47.8, lomax=10.5)
BBOX_AUSTRIA      = BoundingBox(lamin=46.4, lomin=9.5,   lamax=49.0, lomax=17.2)
BBOX_POLAND       = BoundingBox(lamin=49.0, lomin=14.1,  lamax=54.9, lomax=24.2)
BBOX_GREECE       = BoundingBox(lamin=34.8, lomin=19.4,  lamax=41.8, lomax=28.3)
BBOX_PORTUGAL     = BoundingBox(lamin=36.9, lomin=-9.5,  lamax=42.2, lomax=-6.2)
BBOX_IRELAND      = BoundingBox(lamin=51.4, lomin=-10.5, lamax=55.4, lomax=-5.4)
BBOX_CZECHIA      = BoundingBox(lamin=48.5, lomin=12.0,  lamax=51.1, lomax=18.9)
BBOX_SWEDEN       = BoundingBox(lamin=55.3, lomin=11.0,  lamax=69.1, lomax=24.2)
BBOX_NORWAY       = BoundingBox(lamin=57.9, lomin=4.6,   lamax=71.2, lomax=31.1)
BBOX_DENMARK      = BoundingBox(lamin=54.5, lomin=8.1,   lamax=57.8, lomax=15.2)
BBOX_EUROPE       = BoundingBox(lamin=35.0, lomin=-10.0, lamax=70.0, lomax=40.0)
BBOX_WORLD        = BoundingBox(lamin=-90,  lomin=-180,  lamax=90,   lomax=180)


class Airport(BaseModel):
    iata_code: str
    name: str
    city: str | None
    country: str | None
    latitude: float | None
    longitude: float | None


class Airline(BaseModel):
    iata_code: str
    name: str
    country: str | None
    callsign: str | None


class FlightSchedule(BaseModel):
    flight_iata: str
    airline_iata: str | None
    departure_iata: str | None
    arrival_iata: str | None
    scheduled_departure: datetime | None
    scheduled_arrival: datetime | None
    status: str | None
