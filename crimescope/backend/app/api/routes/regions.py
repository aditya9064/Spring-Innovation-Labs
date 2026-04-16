from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import ORJSONResponse

from app.core.data_store import get_all_scores, get_score_by_tract, get_scores_by_tier

router = APIRouter()


@router.get("/score")
def get_region_score(region_id: str = Query(...)):
    score = get_score_by_tract(region_id)
    if not score:
        raise HTTPException(status_code=404, detail=f"Tract {region_id} not found")
    return score


@router.get("/scores", response_class=ORJSONResponse)
def get_region_scores():
    return {"tracts": get_all_scores()}


@router.get("/tiers")
def get_region_tiers():
    by_tier = get_scores_by_tier()
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
def get_blind_spots():
    scores = get_all_scores()
    low_confidence = [
        s for s in scores
        if s.get("model_vs_baseline") is not None
        and abs(s["model_vs_baseline"]) > 0.3
    ]
    return {"blind_spots": low_confidence[:20]}
