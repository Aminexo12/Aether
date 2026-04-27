from fastapi import APIRouter, HTTPException, Query

from app.data.models import BBOX_EUROPE, BBOX_FRANCE, BBOX_WORLD, BoundingBox, Flight
from app.data.opensky import OpenSkyClient

router = APIRouter(prefix="/flights", tags=["flights"])

_client = OpenSkyClient()

_COUNTRY_BBOX = {
    "FR": BBOX_FRANCE,
    "EU": BBOX_EUROPE,
    "WORLD": BBOX_WORLD,
}


@router.get("/live", response_model=list[Flight])
async def get_live_flights(
    country: str | None = Query(None, description="Country code: FR, EU, WORLD"),
    bbox: str | None = Query(None, description="lamin,lomin,lamax,lomax"),
):
    if country and bbox:
        raise HTTPException(status_code=400, detail="Use either 'country' or 'bbox', not both.")

    if country:
        box = _COUNTRY_BBOX.get(country.upper())
        if box is None:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown country code '{country}'. Supported: {list(_COUNTRY_BBOX)}",
            )
    elif bbox:
        parts = bbox.split(",")
        if len(parts) != 4:
            raise HTTPException(status_code=400, detail="bbox must be 'lamin,lomin,lamax,lomax'")
        try:
            box = BoundingBox(
                lamin=float(parts[0]),
                lomin=float(parts[1]),
                lamax=float(parts[2]),
                lomax=float(parts[3]),
            )
        except ValueError:
            raise HTTPException(status_code=400, detail="bbox values must be numbers")
    else:
        box = BBOX_WORLD

    return await _client.get_flights(box)
