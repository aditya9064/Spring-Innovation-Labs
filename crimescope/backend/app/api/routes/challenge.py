"""Human Challenge Mode — allow users to contest a risk score with evidence."""
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.core.data_store import (
    DEFAULT_CITY,
    get_challenge_entries,
    add_challenge_entry,
    update_challenge_entry,
    _check_db,
)

router = APIRouter()

_challenges: list[dict[str, Any]] = []


class ChallengeRequest(BaseModel):
    region_id: str
    challenger_name: str
    challenge_type: str
    evidence: str
    proposed_adjustment: float | None = None


class ChallengeRecord(BaseModel):
    id: str
    timestamp: str
    region_id: str
    challenger_name: str
    challenge_type: str
    evidence: str
    proposed_adjustment: float | None
    status: str
    reviewer_notes: str | None


class ChallengeReview(BaseModel):
    status: str
    reviewer_notes: str


@router.get("", response_model=list[ChallengeRecord])
def list_challenges(
    region_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
):
    if _check_db(DEFAULT_CITY):
        return get_challenge_entries(region_id=region_id, status=status)

    items = _challenges
    if region_id:
        items = [c for c in items if c["region_id"] == region_id]
    if status:
        items = [c for c in items if c["status"] == status]
    return items


@router.post("", response_model=ChallengeRecord, status_code=201)
def create_challenge(req: ChallengeRequest):
    record = {
        "id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **req.model_dump(),
        "status": "pending",
        "reviewer_notes": None,
    }

    if _check_db(DEFAULT_CITY):
        add_challenge_entry(record)
    else:
        _challenges.append(record)

    return record


@router.put("/{challenge_id}", response_model=ChallengeRecord)
def review_challenge(challenge_id: str, review: ChallengeReview):
    if _check_db(DEFAULT_CITY):
        updated = update_challenge_entry(challenge_id, review.status, review.reviewer_notes)
        if updated:
            return updated
        raise HTTPException(404, f"Challenge {challenge_id} not found")

    for c in _challenges:
        if c["id"] == challenge_id:
            c["status"] = review.status
            c["reviewer_notes"] = review.reviewer_notes
            return c
    raise HTTPException(404, f"Challenge {challenge_id} not found")


@router.get("/stats")
def challenge_stats():
    if _check_db(DEFAULT_CITY):
        entries = get_challenge_entries()
    else:
        entries = _challenges

    total = len(entries)
    by_status: dict[str, int] = {}
    by_type: dict[str, int] = {}
    for c in entries:
        by_status[c["status"]] = by_status.get(c["status"], 0) + 1
        by_type[c["challenge_type"]] = by_type.get(c["challenge_type"], 0) + 1
    return {
        "total_challenges": total,
        "by_status": by_status,
        "by_type": by_type,
    }
