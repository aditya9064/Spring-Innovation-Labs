import json
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.core.data_store import get_city_config, get_score_by_tract
from app.schemas.contracts import (
    CompareDriver,
    CompareRecommendation,
    CompareRegionSnapshot,
    CompareResponse,
    LiveDisagreement,
)

router = APIRouter()


def _trust_passport_quality(score: dict[str, Any]) -> tuple[float, float, int, str]:
    """Reuse the same idea as regions._compute_trust_passport but in numeric form."""
    fields = [
        "risk_score", "predicted_next_30d", "baseline_predicted",
        "violent_score", "property_score", "incident_count",
        "y_incidents_12m", "rolling_mean_3m", "rolling_mean_12m",
        "total_pop_acs", "median_hh_income_acs", "poverty_rate_acs",
        "top_drivers_json", "trend_direction",
    ]
    non_null = sum(1 for f in fields if score.get(f) is not None)
    completeness = round(non_null / len(fields), 3)

    has_acs = score.get("total_pop_acs") is not None
    has_income = score.get("median_hh_income_acs") is not None
    incident_count = int(score.get("incident_count") or 0)

    if has_acs and has_income and incident_count >= 5 and completeness >= 0.85:
        confidence = 0.88
    elif has_acs and incident_count >= 2:
        confidence = 0.7
    else:
        confidence = 0.45

    scored_at = score.get("scored_at", "")
    freshness_hours = 168
    if scored_at:
        try:
            scored_dt = datetime.fromisoformat(scored_at.replace("Z", "+00:00"))
            freshness_hours = max(0, int((datetime.now(timezone.utc) - scored_dt).total_seconds() / 3600))
        except (ValueError, TypeError):
            freshness_hours = 168

    mvb = abs(score.get("model_vs_baseline") or 0)
    if mvb < 0.1:
        trust_status = "verified"
    elif mvb < 0.3:
        trust_status = "watch"
    else:
        trust_status = "divergent"

    return confidence, completeness, freshness_hours, trust_status


def _disagreement(score: dict[str, Any]) -> LiveDisagreement:
    mvb = score.get("model_vs_baseline") or 0
    delta_pct = round(mvb * 100)
    abs_mvb = abs(mvb)
    if abs_mvb < 0.1:
        status = "aligned"
        summary = "ML model and historical baseline are in close agreement."
    elif abs_mvb < 0.3:
        status = "watch"
        direction = "above" if mvb > 0 else "below"
        summary = f"ML model scores {abs(delta_pct)}% {direction} the historical baseline."
    else:
        status = "divergent"
        direction = "above" if mvb > 0 else "below"
        summary = f"Significant divergence: ML scores {abs(delta_pct)}% {direction} the baseline. Manual review recommended."
    return LiveDisagreement(status=status, summary=summary, delta=delta_pct)


def _underreporting_label(score: dict[str, Any]) -> str:
    incident = int(score.get("incident_count") or 0)
    poverty = float(score.get("poverty_rate_acs") or 0)
    if incident < 3 and poverty > 0.25:
        return "high"
    if incident < 8 and poverty > 0.15:
        return "moderate"
    return "low"


def _persona_recommendation(risk_score: float, persona: str = "insurer") -> CompareRecommendation:
    if risk_score > 70:
        return CompareRecommendation(
            persona=persona,
            label="manual review",
            nextStep="Send to manual underwriting; pull last 24 mo of claims.",
            caveat="Score is high — score-of-record stays anchored to verified baseline.",
            reviewRequired=True,
        )
    if risk_score > 40:
        return CompareRecommendation(
            persona=persona,
            label="conditional accept",
            nextStep="Apply standard surcharge; monitor live signals.",
            caveat="Live signals may diverge from the verified score.",
            reviewRequired=False,
        )
    return CompareRecommendation(
        persona=persona,
        label="standard accept",
        nextStep="Standard underwriting workflow.",
        caveat="Continue periodic re-scoring.",
        reviewRequired=False,
    )


def _build_snapshot(score: dict[str, Any], city: str | None = None) -> CompareRegionSnapshot:
    cfg = get_city_config(city)
    risk_score = float(score.get("risk_score") or 0)
    baseline = float(score.get("baseline_predicted") or risk_score)
    drivers_raw = score.get("top_drivers_json", "[]")
    try:
        drivers = json.loads(drivers_raw) if isinstance(drivers_raw, str) else drivers_raw
    except (json.JSONDecodeError, TypeError):
        drivers = []

    top_drivers: list[CompareDriver] = []
    for d in (drivers or [])[:3]:
        feat = d.get("feature", "unknown")
        direction_raw = d.get("direction", "flat")
        direction = direction_raw if direction_raw in ("up", "down") else "flat"
        top_drivers.append(
            CompareDriver(
                name=feat.replace("_", " ").title(),
                direction=direction,  # type: ignore[arg-type]
                impact=round(abs(float(d.get("shap_value") or 0)), 4),
                summary=(
                    f"{feat.replace('_', ' ').title()} "
                    f"{'increases' if direction == 'up' else 'decreases' if direction == 'down' else 'has neutral effect on'} risk."
                ),
            )
        )

    confidence, completeness, freshness_hours, trust_status = _trust_passport_quality(score)

    return CompareRegionSnapshot(
        regionId=score.get("tract_geoid", ""),
        regionName=score.get("NAMELSAD") or f"Region {score.get('tract_geoid', '')}",
        city=cfg["label"],
        geographyType=cfg["geographyType"],
        score=int(round(risk_score)),
        baselineScore=int(round(baseline)),
        mlScore=int(round(risk_score)),
        confidence=confidence,
        completeness=completeness,
        freshnessHours=freshness_hours,
        trustStatus=trust_status,
        underreportingRisk=_underreporting_label(score),
        topDrivers=top_drivers,
        recommendation=_persona_recommendation(risk_score),
        liveDisagreement=_disagreement(score),
    )


@router.get("", response_model=CompareResponse)
def compare_regions(
    left_region_id: str = Query(default="17031839100"),
    right_region_id: str = Query(default="17031320102"),
    city: str | None = Query(default=None),
):
    left_score = get_score_by_tract(left_region_id, city=city)
    right_score = get_score_by_tract(right_region_id, city=city)

    if not left_score:
        raise HTTPException(404, f"Region {left_region_id} not found")
    if not right_score:
        raise HTTPException(404, f"Region {right_region_id} not found")

    left_snap = _build_snapshot(left_score, city=city)
    right_snap = _build_snapshot(right_score, city=city)

    diff = left_snap.score - right_snap.score
    if abs(diff) < 10:
        summary = f"Both regions have similar risk levels (difference: {abs(diff)} points)."
    elif diff > 0:
        summary = f"{left_snap.regionName} has higher risk than {right_snap.regionName} by {diff} points."
    else:
        summary = f"{right_snap.regionName} has higher risk than {left_snap.regionName} by {abs(diff)} points."

    return CompareResponse(left=left_snap, right=right_snap, summary=summary)
