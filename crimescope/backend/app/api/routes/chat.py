"""OpenAI-powered chat endpoint with SSE streaming."""
import json
import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.core.config import settings
from app.core.data_store import get_all_scores, get_score_by_tract, get_pipeline_stats

logger = logging.getLogger(__name__)

router = APIRouter()

SYSTEM_PROMPT = """You are the CrimeScope AI Intelligence Assistant, an expert analyst embedded in a crime-risk intelligence terminal used by insurance underwriters and risk analysts.

You have access to real tract-level crime data for Cook County, Chicago. The system scores census tracts on a 0-100 risk scale using an ML model trained on 72 months of historical crime data. Risk tiers are: Critical (80-100), High (60-79), Elevated (40-59), Moderate (20-39), Low (0-19).

Your role:
- Analyze crime risk scores, trends, and drivers for specific census tracts
- Provide underwriting recommendations (accept, conditional accept, manual review, decline)
- Explain what risk drivers mean and how they affect scores
- Compare tracts and identify patterns
- Be concise, data-driven, and use the terminal aesthetic (uppercase headers, bullet points)

When a user asks about a specific tract, use the provided tract context data. When asked general questions, use the portfolio summary data provided.

Always cite specific numbers. Never fabricate data — if you don't have information, say so."""


class ChatRequest(BaseModel):
    message: str
    tract_context: dict[str, Any] | None = None
    history: list[dict[str, str]] | None = None


def _build_portfolio_context() -> str:
    scores = get_all_scores()
    if not scores:
        return "No tract data currently loaded."

    tiers: dict[str, int] = {}
    total_score = 0.0
    rising = 0
    for s in scores:
        tier = s.get("risk_tier", "Unknown")
        tiers[tier] = tiers.get(tier, 0) + 1
        total_score += s.get("risk_score", 0)
        if s.get("trend_direction") == "rising":
            rising += 1

    avg = total_score / len(scores) if scores else 0
    stats = get_pipeline_stats()

    top5 = sorted(scores, key=lambda s: s.get("risk_score", 0), reverse=True)[:5]
    top5_lines = "\n".join(
        f"  {i+1}. {s.get('NAMELSAD', s.get('tract_geoid', '?'))} — Score: {s.get('risk_score', 0):.0f} ({s.get('risk_tier', '?')})"
        for i, s in enumerate(top5)
    )

    tier_lines = "\n".join(f"  {t}: {c} tracts" for t, c in tiers.items())

    return f"""PORTFOLIO SUMMARY:
Total tracts: {len(scores)}
Average risk score: {avg:.1f}/100
Rising trends: {rising} tracts
Data period: {stats.get('data_start', 'N/A')} to {stats.get('data_end', 'N/A')}
Model trained on: {stats.get('total_rows', 'N/A')} observations

TIER DISTRIBUTION:
{tier_lines}

TOP 5 HIGHEST RISK:
{top5_lines}"""


def _build_tract_context(ctx: dict[str, Any]) -> str:
    lines = [f"SELECTED TRACT CONTEXT:"]
    if ctx.get("geoid"):
        score = get_score_by_tract(ctx["geoid"])
        if score:
            lines.append(f"  Tract: {score.get('NAMELSAD', ctx['geoid'])} ({ctx['geoid']})")
            lines.append(f"  Risk Score: {score.get('risk_score', 0):.0f}/100")
            lines.append(f"  Tier: {score.get('risk_tier', 'Unknown')}")
            lines.append(f"  Predicted (30d): {score.get('predicted_next_30d', 0):.0f} incidents")
            lines.append(f"  Recent incidents: {score.get('incident_count', 0)}")
            lines.append(f"  Trend: {score.get('trend_direction', 'stable')}")
            drivers_raw = score.get("top_drivers_json", "[]")
            try:
                drivers = json.loads(drivers_raw) if isinstance(drivers_raw, str) else drivers_raw
                if drivers:
                    lines.append("  Top Drivers:")
                    for d in drivers[:5]:
                        feat = d.get("feature", "?").replace("_", " ")
                        lines.append(f"    - {feat} ({d.get('direction', '?')}, SHAP: {abs(d.get('shap_value', 0)):.3f})")
            except Exception:
                pass
            return "\n".join(lines)

    for k, v in ctx.items():
        lines.append(f"  {k}: {v}")
    return "\n".join(lines)


@router.post("/message")
async def chat_message(req: ChatRequest):
    if not settings.openai_api_key:
        raise HTTPException(503, "OpenAI API key not configured. Set OPENAI_API_KEY in .env")

    try:
        from openai import OpenAI
    except ImportError:
        raise HTTPException(503, "openai package not installed. Run: pip install openai")

    context_parts = [_build_portfolio_context()]
    if req.tract_context:
        context_parts.append(_build_tract_context(req.tract_context))

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT + "\n\n" + "\n\n".join(context_parts)},
    ]

    if req.history:
        for h in req.history[-10:]:
            messages.append({"role": h.get("role", "user"), "content": h.get("content", "")})

    messages.append({"role": "user", "content": req.message})

    client = OpenAI(api_key=settings.openai_api_key)

    async def generate():
        try:
            stream = client.chat.completions.create(
                model=settings.openai_model,
                messages=messages,
                stream=True,
                max_tokens=1024,
                temperature=0.3,
            )
            for chunk in stream:
                delta = chunk.choices[0].delta if chunk.choices else None
                if delta and delta.content:
                    yield f"data: {json.dumps({'content': delta.content})}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            logger.error("OpenAI streaming error: %s", e)
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.get("/status")
def chat_status():
    return {
        "configured": bool(settings.openai_api_key),
        "model": settings.openai_model if settings.openai_api_key else None,
    }
