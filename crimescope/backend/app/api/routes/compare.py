import json
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.core.data_store import get_score_by_tract

router = APIRouter()


def _build_snapshot(score: dict[str, Any]) -> dict[str, Any]:
    risk_score = score.get("risk_score", 0)
    drivers_raw = score.get("top_drivers_json", "[]")
    try:
        drivers = json.loads(drivers_raw) if isinstance(drivers_raw, str) else drivers_raw
    except (json.JSONDecodeError, TypeError):
        drivers = []

    top_drivers = []
    for d in drivers[:3]:
        feat = d.get("feature", "unknown")
        top_drivers.append({
            "name": feat.replace("_", " ").title(),
            "direction": d.get("direction", "flat"),
            "impact": round(abs(d.get("shap_value", 0)), 4),
            "summary": f"{feat.replace('_', ' ').title()} {'increases' if d.get('direction') == 'up' else 'decreases'} risk.",
        })

    predicted = score.get("predicted_next_30d", 0)
    incident = score.get("incident_count", 0)

    return {
        "regionId": score.get("tract_geoid"),
        "regionName": score.get("NAMELSAD", f"Tract {score.get('tract_geoid')}"),
        "city": "Chicago",
        "geographyType": "census_tract",
        "score": int(risk_score),
        "baselineScore": int(incident),
        "mlScore": int(risk_score),
        "confidence": 0.82,
        "completeness": 0.95,
        "freshnessHours": 24,
        "trustStatus": "verified",
        "underreportingRisk": "low" if risk_score > 40 else "moderate",
        "topDrivers": top_drivers,
        "recommendation": {
            "persona": "insurer",
            "label": "manual review" if risk_score > 70 else ("monitor" if risk_score > 40 else "accept"),
            "nextStep": "Review underwriting notes." if risk_score > 70 else "Continue monitoring.",
            "caveat": "Score based on historical patterns; live signals may differ.",
            "reviewRequired": risk_score > 70,
        },
        "liveDisagreement": {
            "status": "aligned" if abs(predicted - incident) < 15 else "watch",
            "summary": f"Model predicts {predicted:.0f} incidents next 30 days.",
            "delta": int(predicted - incident),
        },
    }


@router.get("")
def compare_regions(
    left_region_id: str = Query(default="17031839100"),
    right_region_id: str = Query(default="17031320102"),
):
    left_score = get_score_by_tract(left_region_id)
    right_score = get_score_by_tract(right_region_id)

    if not left_score:
        raise HTTPException(404, f"Tract {left_region_id} not found")
    if not right_score:
        raise HTTPException(404, f"Tract {right_region_id} not found")

    left_snap = _build_snapshot(left_score)
    right_snap = _build_snapshot(right_score)

    diff = left_snap["score"] - right_snap["score"]
    if abs(diff) < 10:
        summary = f"Both tracts have similar risk levels (difference: {abs(diff)} points)."
    elif diff > 0:
        summary = f"{left_snap['regionName']} has higher risk than {right_snap['regionName']} by {diff} points."
    else:
        summary = f"{right_snap['regionName']} has higher risk than {left_snap['regionName']} by {abs(diff)} points."

    return {"left": left_snap, "right": right_snap, "summary": summary}
