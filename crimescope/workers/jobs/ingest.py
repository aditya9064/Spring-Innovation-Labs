from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class NormalizedLiveEvent:
    event_id: str
    source: str
    title: str
    region_id: str
    occurred_at: datetime
    confidence: float
    status: str


def normalize_live_event(raw_event: dict[str, Any]) -> NormalizedLiveEvent:
    return NormalizedLiveEvent(
        event_id=str(raw_event["event_id"]),
        source=str(raw_event["source"]),
        title=str(raw_event["title"]),
        region_id=str(raw_event["region_id"]),
        occurred_at=datetime.fromisoformat(str(raw_event["occurred_at"]).replace("Z", "+00:00")),
        confidence=float(raw_event["confidence"]),
        status=str(raw_event.get("status", "reported")),
    )
