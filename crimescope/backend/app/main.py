from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.api.routes.ws import router as ws_router
from app.core.config import settings

app = FastAPI(
    title="CrimeScope API",
    version="0.1.0",
    description="Starter API scaffold for tract-level risk and live intelligence.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.backend_cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router, prefix="/api")
app.include_router(ws_router, prefix="/ws")
