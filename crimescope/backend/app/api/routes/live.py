from fastapi import APIRouter, Query

from app.sample_data import live_event_package
from app.schemas.contracts import LiveBanner, LiveEvent, LiveEventPackage

router = APIRouter()


@router.get("/banner", response_model=LiveBanner)
def get_live_banner(region_id: str = Query(default="17031010100")) -> LiveBanner:
    package = live_event_package()
    package["regionId"] = region_id
    return LiveEventPackage.model_validate(package).banner


@router.get("/feed", response_model=list[LiveEvent])
def get_live_feed(region_id: str = Query(default="17031010100")) -> list[LiveEvent]:
    package = live_event_package()
    package["regionId"] = region_id
    return LiveEventPackage.model_validate(package).events

