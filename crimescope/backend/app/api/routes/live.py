from fastapi import APIRouter, Query

from app.core.data_store import get_city_config
from app.sample_data import live_event_package
from app.schemas.contracts import LiveBanner, LiveEvent, LiveEventPackage

router = APIRouter()


def _resolve_default_region(region_id: str | None, city: str | None) -> str:
    if region_id:
        return region_id
    return get_city_config(city)["default_region_id"]


@router.get("/banner", response_model=LiveBanner)
def get_live_banner(
    region_id: str | None = Query(default=None),
    city: str | None = Query(default=None),
) -> LiveBanner:
    package = live_event_package()
    package["regionId"] = _resolve_default_region(region_id, city)
    return LiveEventPackage.model_validate(package).banner


@router.get("/feed", response_model=list[LiveEvent])
def get_live_feed(
    region_id: str | None = Query(default=None),
    city: str | None = Query(default=None),
) -> list[LiveEvent]:
    package = live_event_package()
    package["regionId"] = _resolve_default_region(region_id, city)
    return LiveEventPackage.model_validate(package).events
