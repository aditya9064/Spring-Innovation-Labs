from fastapi import APIRouter, Query
from fastapi.responses import ORJSONResponse

from app.core.data_store import get_geojson

router = APIRouter()


@router.get("/geojson", response_class=ORJSONResponse)
def get_map_geojson(city: str | None = Query(default=None)):
    return get_geojson(city=city)
