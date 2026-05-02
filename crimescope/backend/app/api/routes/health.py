from fastapi import APIRouter

from app.core.config import settings
from app.core.data_store import get_backend_kind, list_cities

router = APIRouter()


@router.get("")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/platform")
def platform_status() -> dict:
    """Surface which Databricks features are wired and the active read backend.

    Used by the frontend status pills and by judges who want a one-stop
    "show me what's enabled" check during the demo.
    """
    cities = list_cities()
    backends = {c["id"]: get_backend_kind(c["id"]) for c in cities}
    return {
        "status": "ok",
        "data_store_pref": settings.data_store_backend,
        "backends_by_city": backends,
        "lakebase_configured": bool(settings.lakebase_url),
        "genie_configured": bool(
            settings.databricks_host
            and settings.databricks_token
            and settings.databricks_genie_space_id
        ),
        "model_serving_configured": bool(settings.databricks_serving_url),
        "openai_configured": bool(settings.openai_api_key),
    }
