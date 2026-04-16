from fastapi import APIRouter

from app.api.routes import audit, challenge, chat, compare, health, live, map, regions, reports, simulator

api_router = APIRouter()
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(regions.router, prefix="/regions", tags=["regions"])
api_router.include_router(live.router, prefix="/live", tags=["live"])
api_router.include_router(compare.router, prefix="/compare", tags=["compare"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
api_router.include_router(map.router, prefix="/map", tags=["map"])
api_router.include_router(simulator.router, prefix="/simulator", tags=["simulator"])
api_router.include_router(audit.router, prefix="/audit", tags=["audit"])
api_router.include_router(challenge.router, prefix="/challenge", tags=["challenge"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
