"""Counterfactual Action Simulator — 'what-if' scenario modelling."""
import json
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.core.data_store import get_score_by_tract, get_all_scores

router = APIRouter()


class SimulationRequest(BaseModel):
    region_id: str
    interventions: list[dict[str, Any]]
    city: str | None = None


class SimulationResult(BaseModel):
    region_id: str
    region_name: str
    original_score: float
    simulated_score: float
    delta: float
    original_tier: str
    simulated_tier: str
    breakdown: list[dict[str, Any]]
    narrative: str


INTERVENTION_EFFECTS: dict[str, float] = {
    "increase_patrols": -0.12,
    "community_program": -0.08,
    "street_lighting": -0.06,
    "surveillance_cameras": -0.05,
    "youth_employment": -0.10,
    "vacant_lot_cleanup": -0.04,
    "business_investment": -0.07,
    "reduce_patrols": 0.10,
    "school_closure": 0.08,
    "economic_downturn": 0.15,
}


def _tier_for_score(score: float) -> str:
    if score >= 80:
        return "Critical"
    if score >= 60:
        return "High"
    if score >= 40:
        return "Elevated"
    if score >= 20:
        return "Moderate"
    return "Low"


@router.get("/interventions")
def list_interventions():
    return [
        {"id": k, "label": k.replace("_", " ").title(), "direction": "decrease" if v < 0 else "increase", "typical_impact_pct": round(abs(v) * 100)}
        for k, v in INTERVENTION_EFFECTS.items()
    ]


@router.post("/run", response_model=SimulationResult)
def run_simulation(req: SimulationRequest, city: str | None = Query(default=None)):
    # Accept ``city`` from either the query string or the request body so the
    # simulator works in multi-city deployments. Body wins when both are set.
    resolved_city = req.city or city
    score = get_score_by_tract(req.region_id, city=resolved_city)
    if not score:
        raise HTTPException(404, f"Tract {req.region_id} not found")

    original = score.get("risk_score", 50)
    name = score.get("NAMELSAD", f"Tract {req.region_id}")

    total_effect = 0.0
    breakdown = []
    for intervention in req.interventions:
        iid = intervention.get("id", "")
        intensity = intervention.get("intensity", 1.0)
        base_effect = INTERVENTION_EFFECTS.get(iid, 0)
        effect = base_effect * intensity
        total_effect += effect
        breakdown.append({
            "intervention": iid.replace("_", " ").title(),
            "intensity": intensity,
            "score_impact": round(original * effect, 1),
        })

    simulated = max(0, min(100, original * (1 + total_effect)))

    narrative_parts = []
    if total_effect < 0:
        narrative_parts.append(
            f"Applying {len(req.interventions)} intervention(s) is projected to reduce "
            f"the risk score from {original:.0f} to {simulated:.0f} "
            f"(a {abs(original - simulated):.0f}-point improvement)."
        )
    else:
        narrative_parts.append(
            f"Under the modelled scenario, the risk score would change from "
            f"{original:.0f} to {simulated:.0f}."
        )

    orig_tier = _tier_for_score(original)
    sim_tier = _tier_for_score(simulated)
    if orig_tier != sim_tier:
        narrative_parts.append(
            f"This would move the tract from {orig_tier} to {sim_tier} tier."
        )

    return SimulationResult(
        region_id=req.region_id,
        region_name=name,
        original_score=round(original, 1),
        simulated_score=round(simulated, 1),
        delta=round(simulated - original, 1),
        original_tier=orig_tier,
        simulated_tier=sim_tier,
        breakdown=breakdown,
        narrative=" ".join(narrative_parts),
    )
