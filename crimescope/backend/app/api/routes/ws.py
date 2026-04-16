"""WebSocket endpoint for real-time live feed updates."""
import asyncio
import json
import random
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()

SOURCES = ["official_bulletin", "public_alert", "news_report", "radio_transcript", "social_media"]
STATUSES = ["verified", "reported", "unverified"]
TEMPLATES = [
    "Reports of vehicle break-ins near {area}",
    "Commercial burglary pattern identified in {area}",
    "Increased foot patrols requested for {area}",
    "Noise complaints and disturbances near {area}",
    "Suspicious activity reported in {area}",
    "Traffic stop yielded contraband in {area}",
    "Community watch alert for {area}",
    "Vandalism reported at {area} businesses",
    "Domestic disturbance call in {area}",
    "Shots fired report near {area}",
]
AREAS = [
    "Near North Side", "Austin", "Englewood", "Garfield Park",
    "Loop", "Hyde Park", "Pilsen", "Logan Square",
    "Bronzeville", "Chatham", "Humboldt Park", "Lawndale",
]
CENTER = (41.878, -87.635)


class ConnectionManager:
    def __init__(self) -> None:
        self.active: list[WebSocket] = []

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket) -> None:
        if ws in self.active:
            self.active.remove(ws)

    async def broadcast(self, message: str) -> None:
        for ws in list(self.active):
            try:
                await ws.send_text(message)
            except Exception:
                self.disconnect(ws)


manager = ConnectionManager()


def _generate_event() -> dict:
    area = random.choice(AREAS)
    return {
        "id": f"ws-evt-{random.randint(10000, 99999)}",
        "title": random.choice(TEMPLATES).format(area=area),
        "status": random.choices(STATUSES, weights=[0.3, 0.4, 0.3])[0],
        "confidence": random.choice(["high", "medium", "low"]),
        "sourceType": random.choice(SOURCES),
        "occurredAt": datetime.now(timezone.utc).isoformat(),
        "resolvedRegionId": f"1703{random.randint(1000000, 9999999)}",
        "lat": CENTER[0] + random.uniform(-0.08, 0.08),
        "lng": CENTER[1] + random.uniform(-0.08, 0.08),
        "summary": f"Automated signal for {area} area — awaiting corroboration.",
    }


@router.websocket("/live")
async def websocket_live_feed(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await asyncio.sleep(random.uniform(5, 15))
            event = _generate_event()
            await websocket.send_text(json.dumps(event))
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)
