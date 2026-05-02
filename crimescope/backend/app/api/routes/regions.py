import json
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import ORJSONResponse

from app.core.data_store import (
    get_all_scores,
    get_city_config,
    get_score_by_tract,
    get_scores_by_tier,
    list_cities,
)
from app.schemas.contracts import (
    Driver,
    LiveDisagreement,
    ScoreBreakdown,
    TractRiskPackage,
    TrustPassport,
    WhatChanged,
)

router = APIRouter()

FEATURE_LABELS: dict[str, str] = {
    "rolling_mean_12m": "12-month crime average",
    "rolling_mean_6m": "6-month crime average",
    "rolling_mean_3m": "3-month crime average",
    "lag_1m_count": "Last month incident count",
    "tract_share_of_city": "Tract's share of city-wide crime",
    "city_month_total": "City-wide monthly total",
    "city_total_lag1": "City-wide total (prior month)",
    "total_pop_acs": "Tract population",
    "median_hh_income_acs": "Median household income",
    "poverty_rate_acs": "Poverty rate",
    "housing_units_acs": "Housing unit count",
    "violent_ratio": "Violent crime ratio",
    "violent_ratio_6m": "Violent ratio (6-month)",
    "month_of_year": "Seasonal pattern (month)",
    "month_cos": "Seasonal cycle",
    "month_sin": "Seasonal cycle (sine)",
    "year": "Year trend",
    "y_incidents_12m": "12-month incident total",
    "imd_decile": "Index of Multiple Deprivation decile",
    "violent_ratio_6m": "Violent crime ratio (6-month)",
}


def _compute_trust_passport(score: dict) -> TrustPassport:
    has_acs = score.get("total_pop_acs") is not None
    has_income = score.get("median_hh_income_acs") is not None
    incident_count = score.get("incident_count", 0)
    poverty_rate = score.get("poverty_rate_acs") or 0
    mvb = score.get("model_vs_baseline") or 0
    scored_at = score.get("scored_at", "")

    non_null_fields = sum(1 for k in [
        "risk_score", "predicted_next_30d", "baseline_predicted",
        "violent_score", "property_score", "incident_count",
        "y_incidents_12m", "rolling_mean_3m", "rolling_mean_12m",
        "total_pop_acs", "median_hh_income_acs", "poverty_rate_acs",
        "top_drivers_json", "trend_direction",
    ] if score.get(k) is not None)
    completeness_ratio = non_null_fields / 14

    if completeness_ratio >= 0.85:
        completeness = "high"
    elif completeness_ratio >= 0.6:
        completeness = "moderate"
    else:
        completeness = "low"

    if has_acs and has_income and incident_count >= 5 and completeness == "high":
        confidence = "high"
    elif has_acs and incident_count >= 2:
        confidence = "moderate"
    else:
        confidence = "low"

    if scored_at:
        try:
            scored_dt = datetime.fromisoformat(scored_at.replace("Z", "+00:00"))
            hours_ago = (datetime.now(timezone.utc) - scored_dt).total_seconds() / 3600
            if hours_ago < 24:
                freshness = "live"
            elif hours_ago < 168:
                freshness = "recent"
            else:
                freshness = "stale"
        except (ValueError, TypeError):
            freshness = "unknown"
    else:
        freshness = "unknown"

    abs_mvb = abs(mvb)
    if abs_mvb < 0.1:
        source_agreement = "strong"
    elif abs_mvb < 0.3:
        source_agreement = "mixed"
    else:
        source_agreement = "weak"

    if incident_count < 3 and poverty_rate > 0.25:
        underreporting_risk = "high"
    elif incident_count < 8 and poverty_rate > 0.15:
        underreporting_risk = "moderate"
    else:
        underreporting_risk = "low"

    tier = score.get("risk_tier", "Unknown")
    if tier in ("Critical", "High") or confidence == "low":
        action = "manual review"
    elif tier == "Elevated" and source_agreement != "strong":
        action = "conditional accept"
    elif confidence == "high" and source_agreement == "strong":
        action = "standard processing"
    else:
        action = "conditional accept"

    return TrustPassport(
        confidence=confidence,
        completeness=completeness,
        freshness=freshness,
        sourceAgreement=source_agreement,
        underreportingRisk=underreporting_risk,
        action=action,
    )


def _compute_disagreement(score: dict) -> LiveDisagreement:
    mvb = score.get("model_vs_baseline") or 0
    delta_pct = round(mvb * 100)

    abs_mvb = abs(mvb)
    if abs_mvb < 0.1:
        status = "aligned"
        summary = "ML model and historical baseline are in close agreement for this region."
    elif abs_mvb < 0.3:
        direction = "above" if mvb > 0 else "below"
        summary = f"ML model scores this region {abs(delta_pct)}% {direction} the historical baseline, suggesting moderate divergence."
        status = "watch"
    else:
        direction = "above" if mvb > 0 else "below"
        summary = f"Significant divergence: ML model scores {abs(delta_pct)}% {direction} the historical baseline. Manual review recommended."
        status = "divergent"

    return LiveDisagreement(status=status, summary=summary, delta=delta_pct)


def _compute_drivers(score: dict) -> list[Driver]:
    raw = score.get("top_drivers_json", "[]")
    try:
        shap_drivers = json.loads(raw) if isinstance(raw, str) else raw
    except (json.JSONDecodeError, TypeError):
        return []

    drivers = []
    for d in (shap_drivers or [])[:5]:
        feature = d.get("feature", "unknown")
        label = d.get("label") or FEATURE_LABELS.get(feature, feature.replace("_", " ").title())
        shap_val = abs(d.get("shap_value", 0))
        direction_raw = d.get("direction", "flat")
        direction = direction_raw if direction_raw in ("up", "down") else "flat"

        if shap_val > 0.3:
            impact = "high"
        elif shap_val > 0.1:
            impact = "medium"
        else:
            impact = "low"

        feat_val = d.get("feature_value")
        if feat_val is not None:
            if isinstance(feat_val, float) and feat_val < 1:
                evidence = f"Current value: {feat_val:.1%}. This feature pushes the score {'higher' if direction == 'up' else 'lower'}."
            else:
                evidence = f"Current value: {feat_val:,.1f}. This feature pushes the score {'higher' if direction == 'up' else 'lower'}."
        else:
            evidence = f"This feature has a {'positive' if direction == 'up' else 'negative' if direction == 'down' else 'neutral'} effect on the score."

        drivers.append(Driver(name=label, direction=direction, impact=impact, evidence=evidence))

    return drivers


def _compute_what_changed(score: dict, drivers: list[Driver]) -> WhatChanged:
    trend = score.get("trend_direction", "stable")
    tier = score.get("risk_tier", "Unknown")
    risk_score = round(score.get("risk_score", 0))

    if trend == "rising":
        trend_phrase = "is trending upward"
    elif trend == "falling":
        trend_phrase = "is trending downward"
    else:
        trend_phrase = "remains stable"

    top_driver_name = drivers[0].name if drivers else "overall crime patterns"
    summary = (
        f"This region's risk score ({risk_score}/100, {tier}) {trend_phrase}, "
        f"driven primarily by {top_driver_name.lower()}."
    )

    top_changes = []
    for d in drivers[:3]:
        verb = "increases" if d.direction == "up" else "decreases" if d.direction == "down" else "has a neutral effect on"
        top_changes.append(f"{d.name} ({d.impact} impact) {verb} the risk score. {d.evidence}")

    mvb = score.get("model_vs_baseline") or 0
    if abs(mvb) > 0.1:
        direction = "above" if mvb > 0 else "below"
        top_changes.append(
            f"ML model diverges {abs(round(mvb * 100))}% {direction} the lag-1 baseline prediction."
        )

    if trend == "rising":
        top_changes.append("The trend direction is rising compared to the prior scoring window.")
    elif trend == "falling":
        top_changes.append("The trend direction is falling, indicating improvement.")

    return WhatChanged(summary=summary, topChanges=top_changes)


@router.get("/cities")
def get_cities():
    """List all configured cities/regions the frontend can switch between."""
    return {"cities": list_cities()}


@router.get("/score")
def get_region_score(region_id: str = Query(...), city: str | None = Query(default=None)):
    score = get_score_by_tract(region_id, city=city)
    if not score:
        raise HTTPException(status_code=404, detail=f"Region {region_id} not found")
    return score


@router.get("/scores", response_class=ORJSONResponse)
def get_region_scores(city: str | None = Query(default=None)):
    return {"tracts": get_all_scores(city=city)}


@router.get("/risk-package", response_model=TractRiskPackage)
def get_risk_package(
    region_id: str = Query(...),
    city: str | None = Query(default=None),
):
    score = get_score_by_tract(region_id, city=city)
    if not score:
        raise HTTPException(status_code=404, detail=f"Region {region_id} not found")

    drivers = _compute_drivers(score)
    trust = _compute_trust_passport(score)
    disagreement = _compute_disagreement(score)
    what_changed = _compute_what_changed(score, drivers)

    tier = score.get("risk_tier", "Unknown")
    risk_level_map = {
        "Critical": "critical",
        "High": "high",
        "Elevated": "elevated",
        "Moderate": "moderate",
        "Low": "low",
    }

    scored_at_str = score.get("scored_at", "")
    try:
        updated_at = datetime.fromisoformat(scored_at_str.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        updated_at = datetime.now(timezone.utc)

    cfg = get_city_config(city)
    return TractRiskPackage(
        regionId=score.get("tract_geoid", ""),
        regionType=cfg["geographyType"],
        regionName=score.get("NAMELSAD", "") or score.get("tract_geoid", ""),
        city=cfg["label"],
        timeHorizonDays=30,
        riskLevel=risk_level_map.get(tier, "unknown"),
        baselineScore=round(score.get("baseline_predicted", 0)),
        mlScore=round(score.get("risk_score", 0)),
        scores=ScoreBreakdown(
            overall=round(score.get("risk_score", 0)),
            violent=round(score.get("violent_score", 0)),
            property=round(score.get("property_score", 0)),
        ),
        drivers=drivers,
        trustPassport=trust,
        liveDisagreement=disagreement,
        whatChanged=what_changed,
        updatedAt=updated_at,
    )


@router.get("/tiers")
def get_region_tiers(city: str | None = Query(default=None)):
    by_tier = get_scores_by_tier(city=city)
    total = sum(len(v) for v in by_tier.values())
    return [
        {
            "tier": tier,
            "count": len(tracts),
            "pct": round(len(tracts) / total * 100, 1) if total else 0,
        }
        for tier, tracts in by_tier.items()
    ]


@router.get("/blind-spots")
def get_blind_spots(city: str | None = Query(default=None)):
    scores = get_all_scores(city=city)
    low_confidence = [
        s for s in scores
        if s.get("model_vs_baseline") is not None
        and abs(s["model_vs_baseline"]) > 0.3
    ]
    return {"blind_spots": low_confidence[:20]}
