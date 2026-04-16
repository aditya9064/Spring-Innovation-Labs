import json
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.core.data_store import get_score_by_tract, get_pipeline_stats

router = APIRouter()


@router.get("/summary")
def get_report_summary(region_id: str = Query(default="17031839100")):
    score = get_score_by_tract(region_id)
    if not score:
        raise HTTPException(404, f"Tract {region_id} not found")

    risk_score = score.get("risk_score", 0)
    predicted = score.get("predicted_next_30d", 0)
    name = score.get("NAMELSAD", f"Tract {region_id}")
    tier = score.get("risk_tier", "Unknown")

    drivers_raw = score.get("top_drivers_json", "[]")
    try:
        drivers = json.loads(drivers_raw) if isinstance(drivers_raw, str) else drivers_raw
    except Exception:
        drivers = []
    driver_names = [d.get("feature", "").replace("_", " ").title() for d in drivers[:3]]

    stats = get_pipeline_stats()

    return {
        "regionId": region_id,
        "title": f"Risk Report: {name}",
        "executiveSummary": (
            f"{name} has a risk score of {risk_score:.0f}/100 ({tier} tier). "
            f"The model predicts approximately {predicted:.0f} incidents in the next 30 days. "
            f"This assessment is based on {stats.get('n_months', 'N/A')} months of historical data "
            f"across {stats.get('n_tracts', 'N/A')} census tracts in Cook County."
        ),
        "riskDrivers": driver_names,
        "trustNotes": [
            f"Data spans from {stats.get('data_start', 'N/A')} to {stats.get('data_end', 'N/A')}.",
            f"Model trained on {stats.get('total_rows', 'N/A')} tract-month observations.",
            "Scores are percentile-based (0-100) relative to all Cook County tracts.",
        ],
        "compareSummary": f"This tract ranks in the {tier.lower()} tier among {stats.get('n_tracts', 'N/A')} tracts.",
        "challengeState": "none",
    }


@router.get("/persona-decision")
def get_persona_decision(region_id: str = Query(default="17031839100")):
    score = get_score_by_tract(region_id)
    if not score:
        raise HTTPException(404, f"Tract {region_id} not found")

    risk_score = score.get("risk_score", 0)
    name = score.get("NAMELSAD", f"Tract {region_id}")

    if risk_score >= 75:
        decision = "manual review"
        headline = f"Elevated risk in {name} requires manual underwriting review."
        next_step = "Route to senior underwriter. Request supplemental safeguards and verify property details."
        caveat = "High-risk score driven by recent crime trends. Verify with on-ground assessment."
        abstain = False
    elif risk_score >= 50:
        decision = "conditional accept"
        headline = f"Moderate risk in {name}. Conditional acceptance recommended."
        next_step = "Apply standard risk surcharge. Monitor quarterly for score changes."
        caveat = "Score is in the elevated range but not extreme. Standard precautions apply."
        abstain = False
    else:
        decision = "accept"
        headline = f"Low risk in {name}. Standard processing recommended."
        next_step = "Proceed with standard underwriting. No additional review required."
        caveat = "Historical patterns indicate stable, low-risk area."
        abstain = False

    return {
        "persona": "insurer",
        "regionId": region_id,
        "decision": decision,
        "headline": headline,
        "nextStep": next_step,
        "caveat": caveat,
        "abstain": abstain,
    }
