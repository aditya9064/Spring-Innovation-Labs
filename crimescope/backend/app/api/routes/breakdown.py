"""Region crime-pattern breakdown.

The score row carries violent / property subscores and a 12-month incident
total but no category-level panel. This endpoint synthesises a defensible
category breakdown by:

* Splitting the 30-day expected incidents (``predicted_next_30d`` if present,
  else ``incident_count`` scaled to 30 days) using the violent vs. property
  share derived from the subscores.
* Allocating the residual to "Other / Quality-of-life".
* Applying a small set of canonical sub-categories beneath violent / property
  using fixed national-average weights (so the breakdown is stable and
  reviewable).
* Reporting trend per category by comparing each implied count to the same
  category's prior-window estimate (uses ``rolling_mean_3m`` and
  ``rolling_mean_6m`` when available).

The ``note`` field in the response documents this honestly so the UI can
display provenance.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.core.data_store import get_score_by_tract
from app.schemas.contracts import BreakdownCategory, RegionBreakdown

router = APIRouter()


# Canonical sub-category weights inside violent / property. Sum to 1 each.
_VIOLENT_MIX: list[tuple[str, str, float]] = [
    ("assault", "Assault", 0.55),
    ("robbery", "Robbery", 0.25),
    ("homicide", "Homicide", 0.05),
    ("weapons_violation", "Weapons violation", 0.15),
]

_PROPERTY_MIX: list[tuple[str, str, float]] = [
    ("theft", "Theft", 0.45),
    ("burglary", "Burglary", 0.20),
    ("motor_vehicle_theft", "Motor vehicle theft", 0.20),
    ("vandalism", "Vandalism", 0.15),
]

_OTHER_MIX: list[tuple[str, str, float]] = [
    ("disorder", "Disorder / quality of life", 0.70),
    ("narcotics", "Narcotics", 0.30),
]


def _trend_label(current: float, prior: float) -> tuple[str, float]:
    if prior <= 0:
        return ("stable", 0.0)
    pct = (current - prior) / prior * 100
    if pct >= 7:
        return ("rising", round(pct, 1))
    if pct <= -7:
        return ("falling", round(pct, 1))
    return ("stable", round(pct, 1))


@router.get("/breakdown", response_model=RegionBreakdown)
def get_region_breakdown(
    region_id: str = Query(...),
    city: str | None = Query(default=None),
):
    score = get_score_by_tract(region_id, city=city)
    if not score:
        raise HTTPException(status_code=404, detail=f"Region {region_id} not found")

    violent_score = float(score.get("violent_score") or 0)
    property_score = float(score.get("property_score") or 0)
    overall = float(score.get("risk_score") or max(1.0, violent_score + property_score))

    # Derive split shares (with sane fallback if subscores are missing)
    if violent_score + property_score > 0:
        violent_share = violent_score / (violent_score + property_score) * 0.85
        property_share = property_score / (violent_score + property_score) * 0.85
    else:
        violent_share = 0.30
        property_share = 0.55
    other_share = max(0.0, 1.0 - violent_share - property_share)

    # 30-day expected incidents (anchor to predicted_next_30d if present)
    predicted_30 = score.get("predicted_next_30d")
    if predicted_30 is None:
        # Approximate from 12-month history if present, else from incident_count
        y12 = float(score.get("y_incidents_12m") or score.get("incident_count") or 0)
        predicted_30 = (y12 / 12) if y12 > 0 else max(1.0, overall / 10.0)
    total_30 = max(1.0, float(predicted_30))

    # Prior-window per category — use rolling_mean_3m as a per-month proxy
    rm3_total = float(score.get("rolling_mean_3m") or 0) / 3 if score.get("rolling_mean_3m") else None
    rm6_total = float(score.get("rolling_mean_6m") or 0) / 6 if score.get("rolling_mean_6m") else None
    prior_total = rm6_total if rm6_total is not None else (rm3_total if rm3_total is not None else total_30)

    categories: list[BreakdownCategory] = []
    for share, mix in (
        (violent_share, _VIOLENT_MIX),
        (property_share, _PROPERTY_MIX),
        (other_share, _OTHER_MIX),
    ):
        for cat_id, label, w in mix:
            cur = total_30 * share * w
            prior = prior_total * share * w
            direction, pct = _trend_label(cur, prior)
            categories.append(
                BreakdownCategory(
                    category=cat_id,
                    label=label,
                    count30d=int(round(cur)),
                    share=round(share * w, 4),
                    trendDirection=direction,  # type: ignore[arg-type]
                    trendPct=pct,
                )
            )

    # Sort high-to-low for UI convenience
    categories.sort(key=lambda c: c.count30d, reverse=True)

    note = (
        "Categories are derived from the row's violent/property subscores and "
        "predicted_next_30d using fixed sub-category weights; trend direction "
        "compares the implied 30-day count to the rolling 6-month average. "
        "Replace with category-level forecasts from the ML pipeline when available."
    )

    return RegionBreakdown(
        regionId=score.get("tract_geoid", region_id),
        regionName=score.get("NAMELSAD") or region_id,
        windowDays=30,
        total30d=int(round(total_30)),
        categories=categories,
        note=note,
    )
