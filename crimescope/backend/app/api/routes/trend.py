"""Region trend + near-term forecast.

Given how the scoring pipeline currently exports data (per-tract aggregates,
not raw monthly panels), this endpoint reconstructs a 12-month *implied*
history from the rolling-mean fields we have on a score row, blends in mild
seasonality, and produces a damped-linear forecast for the requested horizon
with an empirical 80% confidence band derived from the in-sample residual
spread.

It is honest about its method via the ``method`` and ``calibrationNote``
fields on the response — the UI should display them.
"""
from __future__ import annotations

import math
from datetime import date, timedelta
from typing import Literal

from fastapi import APIRouter, HTTPException, Query

from app.core.data_store import get_score_by_tract
from app.schemas.contracts import RegionTrend, TrendForecastPoint, TrendPoint

router = APIRouter()


def _build_history(score: dict) -> list[tuple[date, float]]:
    """Construct an implied 12-month history of monthly incident-equivalent risk.

    We use the available rolling means to anchor recent values and gently
    interpolate older months. Seasonality is sinusoidal with a 12-month period.
    """
    today = date.today().replace(day=1)
    horizon_months = 12

    rm12 = float(score.get("rolling_mean_12m") or score.get("y_incidents_12m") or 0) / 12
    rm6 = float(score.get("rolling_mean_6m") or rm12 * 6) / 6 if score.get("rolling_mean_6m") else rm12
    rm3 = float(score.get("rolling_mean_3m") or rm6 * 3) / 3 if score.get("rolling_mean_3m") else rm6
    last_month = float(score.get("lag_1m_count") or rm3)

    # If we have no signal at all, fall back to a tiny neutral series so the
    # endpoint stays useful instead of returning empties.
    if rm12 == 0 and last_month == 0:
        rm12 = max(1.0, float(score.get("incident_count") or 1) / 12)
        rm3 = rm12
        rm6 = rm12
        last_month = rm12

    seasonal_amp = 0.12  # +/-12% seasonality on the level
    history: list[tuple[date, float]] = []
    for k in range(horizon_months, 0, -1):
        anchor_date = (today - timedelta(days=30 * k)).replace(day=1)
        # Linear blend toward the more recent anchors as k decreases
        if k > 6:
            base = rm12
        elif k > 3:
            base = rm6
        else:
            base = rm3
        season = 1 + seasonal_amp * math.sin(2 * math.pi * (anchor_date.month - 1) / 12)
        value = max(0.0, base * season)
        history.append((anchor_date, value))
    # Make the last point reflect the most recent observed month
    if history:
        last_date, _ = history[-1]
        history[-1] = (last_date, max(0.0, last_month))
    return history


def _forecast(history: list[tuple[date, float]], horizon_days: int) -> tuple[list[TrendForecastPoint], float, float, float, str]:
    """Damped-linear forecast with an empirical 80% confidence band."""
    if not history:
        today = date.today()
        empty = TrendForecastPoint(date=today.isoformat(), value=0.0, lo=0.0, hi=0.0)
        return [empty], 0.0, 0.0, 0.0, "stable"

    values = [v for _, v in history]
    n = len(values)
    last = values[-1]
    # Slope estimate: average month-over-month delta
    deltas = [values[i] - values[i - 1] for i in range(1, n)]
    slope = sum(deltas) / len(deltas) if deltas else 0.0
    # Damp so we don't extrapolate aggressively
    damping = 0.7
    # Empirical std for confidence band
    if len(deltas) > 1:
        mean = sum(deltas) / len(deltas)
        variance = sum((d - mean) ** 2 for d in deltas) / (len(deltas) - 1)
        sigma = math.sqrt(variance)
    else:
        sigma = max(1.0, last * 0.10)

    today = date.today()
    points: list[TrendForecastPoint] = []
    months_out = max(1, math.ceil(horizon_days / 30))
    accum = 0.0
    last_value = last
    for m in range(1, months_out + 1):
        damp = damping ** (m - 1)
        next_value = max(0.0, last_value + slope * damp)
        # 1.28 ≈ z for 80% two-sided
        spread = 1.28 * sigma * math.sqrt(m)
        lo = max(0.0, next_value - spread)
        hi = next_value + spread
        anchor = today + timedelta(days=30 * m)
        points.append(
            TrendForecastPoint(
                date=anchor.isoformat(),
                value=round(next_value, 2),
                lo=round(lo, 2),
                hi=round(hi, 2),
            )
        )
        last_value = next_value
        accum += next_value

    # Aggregate the requested horizon (typically 30 days = 1 month)
    if horizon_days <= 30:
        next_expected = points[0].value
        next_lo = points[0].lo
        next_hi = points[0].hi
    else:
        # Pro-rate from monthly points
        full_months = horizon_days // 30
        partial = (horizon_days % 30) / 30.0
        full_sum = sum(p.value for p in points[:full_months])
        full_lo = sum(p.lo for p in points[:full_months])
        full_hi = sum(p.hi for p in points[:full_months])
        if partial > 0 and len(points) > full_months:
            full_sum += points[full_months].value * partial
            full_lo += points[full_months].lo * partial
            full_hi += points[full_months].hi * partial
        next_expected = round(full_sum, 2)
        next_lo = round(full_lo, 2)
        next_hi = round(full_hi, 2)

    if slope > 0.05 * max(1.0, last):
        direction = "rising"
    elif slope < -0.05 * max(1.0, last):
        direction = "falling"
    else:
        direction = "stable"
    return points, next_expected, next_lo, next_hi, direction


@router.get("/trend", response_model=RegionTrend)
def get_region_trend(
    region_id: str = Query(...),
    horizon_days: int = Query(30, ge=7, le=180),
    metric: Literal["risk_score", "incident_rate"] = Query("incident_rate"),
    city: str | None = Query(default=None),
):
    score = get_score_by_tract(region_id, city=city)
    if not score:
        raise HTTPException(status_code=404, detail=f"Region {region_id} not found")

    history_pairs = _build_history(score)
    forecast_points, next_expected, next_lo, next_hi, computed_direction = _forecast(history_pairs, horizon_days)

    # If the score row carries an explicit predicted_next_30d, prefer it for the
    # 30-day point — the UI should show what the ML pipeline actually emitted.
    predicted = score.get("predicted_next_30d")
    if predicted is not None and horizon_days <= 30:
        next_expected = round(float(predicted), 2)
        # Keep the empirical band; centre it on the predicted value.
        spread = max(0.5, abs(next_hi - next_lo) / 2)
        next_lo = max(0.0, round(next_expected - spread, 2))
        next_hi = round(next_expected + spread, 2)
        if forecast_points:
            forecast_points[0] = TrendForecastPoint(
                date=forecast_points[0].date,
                value=next_expected,
                lo=next_lo,
                hi=next_hi,
            )

    # Prefer the persisted trend label if available
    trend_field = (score.get("trend_direction") or "").lower()
    if trend_field in ("rising", "falling", "stable"):
        direction = trend_field
    else:
        direction = computed_direction

    method = (
        "Implied 12-month history from rolling means + 12-month seasonality; "
        "damped-linear forecast (damping=0.7); 80% empirical band from in-sample "
        "month-over-month residual spread; 30-day anchor uses pipeline "
        "`predicted_next_30d` when available."
    )
    calibration = (
        "Forecast is illustrative — it should be regenerated against the "
        "Databricks ML pipeline's per-month forecasts when those are exposed. "
        "Treat the band as a rough plausibility envelope, not a calibrated PI."
    )

    if metric == "risk_score":
        # Optionally rescale the implied-incident series into a 0..100 score by
        # anchoring the most recent point to the row's risk_score.
        target = float(score.get("risk_score") or 50.0)
        anchor = history_pairs[-1][1] if history_pairs else 1.0
        factor = target / anchor if anchor > 0 else 1.0
        history = [TrendPoint(date=d.isoformat(), value=round(min(100, v * factor), 2)) for d, v in history_pairs]
        forecast_points = [
            TrendForecastPoint(
                date=p.date,
                value=round(min(100, p.value * factor), 2),
                lo=round(min(100, p.lo * factor), 2),
                hi=round(min(100, p.hi * factor), 2),
            )
            for p in forecast_points
        ]
        next_expected = round(min(100, next_expected * factor), 2)
        next_lo = round(min(100, next_lo * factor), 2)
        next_hi = round(min(100, next_hi * factor), 2)
    else:
        history = [TrendPoint(date=d.isoformat(), value=round(v, 2)) for d, v in history_pairs]

    return RegionTrend(
        regionId=score.get("tract_geoid", region_id),
        regionName=score.get("NAMELSAD") or region_id,
        metric=metric,
        horizonDays=horizon_days,
        history=history,
        forecast=forecast_points,
        method=method,
        calibrationNote=calibration,
        trendDirection=direction,  # type: ignore[arg-type]
        next30dExpected=next_expected,
        next30dLo=next_lo,
        next30dHi=next_hi,
    )
