from fastapi import APIRouter
from fastapi.responses import ORJSONResponse

from app.core.data_store import get_geojson

router = APIRouter()


@router.get("/geojson", response_class=ORJSONResponse)
def get_map_geojson():
    return get_geojson()
