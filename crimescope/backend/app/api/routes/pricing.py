"""Pricing guidance — translate a region's risk into actuarially-shaped premium guidance.

Two personas are supported in v1:

* ``insurer`` — premium surcharge guidance for an underwriting workflow.
* ``real_estate`` — property-risk loading suggestion for listing materials.

The suggested premium is a transparent linear loading on top of a caller-supplied
``base_premium``, so the API can be audited end-to-end::

    suggested = base_premium * (1 + alpha * risk_factor + beta * tier_loading)

where ``risk_factor = (risk_score - neutral_score) / neutral_score`` and
``tier_loading`` reflects the discrete risk tier. ``alpha`` and ``beta`` are
calibrated per-persona and returned in the response so the caller can
reproduce or audit the math.
"""
import json
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Query

from app.core.data_store import get_score_by_tract
from app.schemas.contracts import PricingDriver, PricingQuote

router = APIRouter()


_NEUTRAL_SCORE = 50.0  # tract score considered "average" risk


# Persona-specific coefficients. alpha drives sensitivity to score deviation;
# beta drives discrete tier loading. These are deliberately conservative so the
# guidance stays defensible without a real actuarial calibration table.
_PERSONA_COEFFS: dict[str, tuple[float, float]] = {
    "insurer": (0.45, 0.55),
    "real_estate": (0.25, 0.30),
}

_TIER_LOADING: dict[str, float] = {
    "Critical": 1.00,
    "High": 0.65,
    "Elevated": 0.30,
    "Moderate": 0.10,
    "Low": 0.00,
}

_DEFAULT_BASE_PREMIUM = {
    "insurer": 1200.0,
    "real_estate": 100.0,  # interpreted as a "risk loading on a $100 baseline"
}


def _band_for(multiplier: float, persona: str) -> str:
    if persona == "insurer":
        if multiplier >= 1.75:
            return "decline_recommended"
        if multiplier >= 1.40:
            return "high_risk"
        if multiplier >= 1.15:
            return "surcharge"
        if multiplier >= 0.95:
            return "standard"
        return "preferred"
    # real_estate uses gentler bands — still surfaces the same shape
    if multiplier >= 1.45:
        return "high_risk"
    if multiplier >= 1.20:
        return "surcharge"
    if multiplier >= 0.95:
        return "standard"
    return "preferred"


def _confidence_from_passport(score: dict[str, Any]) -> float:
    """Cheap, transparent confidence signal: how complete is the row?"""
    fields = [
        "risk_score",
        "baseline_predicted",
        "violent_score",
        "property_score",
        "incident_count",
        "y_incidents_12m",
        "rolling_mean_12m",
        "total_pop_acs",
        "median_hh_income_acs",
        "poverty_rate_acs",
        "top_drivers_json",
    ]
    present = sum(1 for f in fields if score.get(f) is not None)
    base = present / len(fields)
    # Penalise large model-vs-baseline divergence — pricing suggestion is
    # less defensible when the two models disagree.
    mvb = abs(score.get("model_vs_baseline") or 0)
    penalty = min(0.25, mvb * 0.5)
    return round(max(0.2, min(1.0, base - penalty)), 3)


def _top_pricing_drivers(
    score: dict[str, Any],
    risk_factor: float,
    tier_loading: float,
    alpha: float,
    beta: float,
) -> list[PricingDriver]:
    """Surface up to three drivers that explain the loading."""
    drivers: list[PricingDriver] = []

    risk_contribution = alpha * risk_factor * 100  # in % of base premium
    tier_contribution = beta * tier_loading * 100

    drivers.append(
        PricingDriver(
            name="Score deviation from neutral",
            contributionPct=round(risk_contribution, 2),
            evidence=(
                f"Risk score {round(score.get('risk_score', 0))}/100 deviates "
                f"{round(risk_factor * 100, 1)}% from the neutral baseline of "
                f"{int(_NEUTRAL_SCORE)}."
            ),
        )
    )
    drivers.append(
        PricingDriver(
            name=f"{score.get('risk_tier', 'Unknown')} tier loading",
            contributionPct=round(tier_contribution, 2),
            evidence=(
                f"Discrete loading for tier '{score.get('risk_tier', 'Unknown')}' "
                f"is {round(tier_loading * 100)}% of base."
            ),
        )
    )

    raw = score.get("top_drivers_json", "[]")
    try:
        shap = json.loads(raw) if isinstance(raw, str) else raw
    except (json.JSONDecodeError, TypeError):
        shap = []
    if shap:
        top = shap[0]
        feat = top.get("feature", "top driver").replace("_", " ").title()
        shap_val = top.get("shap_value", 0)
        # Translate SHAP value into a small share of the multiplier explanation
        share = max(-25.0, min(25.0, shap_val * 50))
        drivers.append(
            PricingDriver(
                name=f"ML driver: {feat}",
                contributionPct=round(share, 2),
                evidence=(
                    f"Top SHAP feature contributes {shap_val:+.2f} to the score; "
                    "directional only — not added on top of the base loading."
                ),
            )
        )
    return drivers[:3]


def _caveats_for(score: dict[str, Any], confidence: float) -> list[str]:
    out: list[str] = []
    if confidence < 0.6:
        out.append("Confidence in this region's data is low; treat the suggestion as advisory.")
    if (score.get("incident_count") or 0) < 5:
        out.append(
            "Observed incident count is low; underreporting risk is plausible — "
            "consider holding out a manual review window."
        )
    mvb = abs(score.get("model_vs_baseline") or 0)
    if mvb > 0.3:
        out.append(
            "ML model and baseline diverge by >30% — the suggested loading may move "
            "if the verified baseline is adopted as the score-of-record."
        )
    if not out:
        out.append("Suggestion is within the model's calibrated range; standard underwriting may apply.")
    return out


@router.get("/quote", response_model=PricingQuote)
def get_pricing_quote(
    region_id: str = Query(..., description="Region identifier (tract / MSOA / LSOA)"),
    persona: Literal["insurer", "real_estate"] = Query(
        "insurer", description="Pricing persona; selects coefficients and bands."
    ),
    base_premium: float | None = Query(
        None,
        ge=0,
        description="Caller's base premium (currency-agnostic). Defaults to a sensible per-persona baseline.",
    ),
    city: str | None = Query(default=None),
):
    """Return a transparent, persona-aware pricing suggestion for a region."""
    score = get_score_by_tract(region_id, city=city)
    if not score:
        raise HTTPException(status_code=404, detail=f"Region {region_id} not found")

    alpha, beta = _PERSONA_COEFFS[persona]
    base = base_premium if base_premium is not None else _DEFAULT_BASE_PREMIUM[persona]

    risk_score = float(score.get("risk_score") or _NEUTRAL_SCORE)
    risk_factor = (risk_score - _NEUTRAL_SCORE) / _NEUTRAL_SCORE
    tier = score.get("risk_tier", "Unknown")
    tier_loading = _TIER_LOADING.get(tier, 0.20)

    multiplier = 1.0 + alpha * risk_factor + beta * tier_loading
    multiplier = max(0.6, min(2.5, multiplier))  # clamp to a defensible range
    suggested = round(base * multiplier, 2)
    confidence = _confidence_from_passport(score)
    band = _band_for(multiplier, persona)
    drivers = _top_pricing_drivers(score, risk_factor, tier_loading, alpha, beta)
    caveats = _caveats_for(score, confidence)

    methodology = (
        "suggested_premium = base_premium × "
        f"(1 + α·(risk_score − {int(_NEUTRAL_SCORE)})/{int(_NEUTRAL_SCORE)} + β·tier_loading); "
        f"α={alpha}, β={beta}, multiplier clamped to [0.6, 2.5]."
    )

    return PricingQuote(
        regionId=score.get("tract_geoid", region_id),
        regionName=score.get("NAMELSAD") or region_id,
        persona=persona,
        basePremium=round(base, 2),
        suggestedPremium=suggested,
        riskMultiplier=round(multiplier, 4),
        band=band,  # type: ignore[arg-type]
        drivers=drivers,
        confidence=confidence,
        methodology=methodology,
        alpha=alpha,
        beta=beta,
        riskFactor=round(risk_factor, 4),
        tierLoading=tier_loading,
        caveats=caveats,
    )
