from fastapi import APIRouter

from app.api.routes import (
    audit,
    breakdown,
    challenge,
    chat,
    compare,
    genie,
    health,
    live,
    map,
    pricing,
    regions,
    reports,
    simulator,
    trend,
)

api_router = APIRouter()
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(regions.router, prefix="/regions", tags=["regions"])
# trend + breakdown are region-scoped helpers; mounted under /regions for parity
api_router.include_router(trend.router, prefix="/regions", tags=["regions"])
api_router.include_router(breakdown.router, prefix="/regions", tags=["regions"])
api_router.include_router(pricing.router, prefix="/pricing", tags=["pricing"])
api_router.include_router(live.router, prefix="/live", tags=["live"])
api_router.include_router(compare.router, prefix="/compare", tags=["compare"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
api_router.include_router(map.router, prefix="/map", tags=["map"])
api_router.include_router(simulator.router, prefix="/simulator", tags=["simulator"])
api_router.include_router(audit.router, prefix="/audit", tags=["audit"])
api_router.include_router(challenge.router, prefix="/challenge", tags=["challenge"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(genie.router, prefix="/genie", tags=["genie"])
