"""Decision Audit Trail — record and replay every underwriting decision."""
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.core.data_store import get_audit_entries, add_audit_entry, _check_db

router = APIRouter()

_audit_log: list[dict[str, Any]] = []


class AuditEntry(BaseModel):
    region_id: str
    persona: str
    decision: str
    rationale: str
    risk_score: float
    risk_tier: str
    overridden: bool = False
    override_reason: str | None = None


class AuditRecord(BaseModel):
    id: str
    timestamp: str
    region_id: str
    persona: str
    decision: str
    rationale: str
    risk_score: float
    risk_tier: str
    overridden: bool
    override_reason: str | None


@router.get("", response_model=list[AuditRecord])
def list_audit_trail(
    region_id: str | None = Query(default=None),
    limit: int = Query(default=50, le=200),
):
    if _check_db():
        return get_audit_entries(region_id=region_id, limit=limit)

    items = _audit_log
    if region_id:
        items = [i for i in items if i["region_id"] == region_id]
    return items[-limit:]


@router.post("", response_model=AuditRecord, status_code=201)
def create_audit_entry_route(entry: AuditEntry):
    record = {
        "id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **entry.model_dump(),
    }

    if _check_db():
        add_audit_entry(record)
    else:
        _audit_log.append(record)

    return record


@router.get("/stats")
def audit_stats():
    if _check_db():
        entries = get_audit_entries(limit=10000)
    else:
        entries = _audit_log

    total = len(entries)
    decisions: dict[str, int] = {}
    overrides = 0
    for r in entries:
        decisions[r["decision"]] = decisions.get(r["decision"], 0) + 1
        if r.get("overridden"):
            overrides += 1
    return {
        "total_decisions": total,
        "decision_breakdown": decisions,
        "total_overrides": overrides,
        "override_rate": round(overrides / total * 100, 1) if total > 0 else 0,
    }
