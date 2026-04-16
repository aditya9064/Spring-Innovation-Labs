try:
    from jobs.ingest import NormalizedLiveEvent
except ImportError:
    from ingest import NormalizedLiveEvent


def build_feed_row(event: NormalizedLiveEvent) -> dict[str, object]:
    return {
        "eventId": event.event_id,
        "source": event.source,
        "status": event.status,
        "regionId": event.region_id,
        "title": event.title,
        "occurredAt": event.occurred_at.isoformat(),
        "confidence": round(event.confidence, 2),
    }
