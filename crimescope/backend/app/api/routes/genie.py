"""Databricks Genie proxy.

Genie lets users ask natural-language questions over Unity Catalog
tables and returns governed SQL + a result set. We expose it through
the FastAPI backend so the frontend AI Analyst panel can call it
without holding workspace tokens in the browser.

Docs: https://docs.databricks.com/api/workspace/genie

The proxy is a thin shim over two endpoints on the workspace API:

  POST  /api/2.0/genie/spaces/{space_id}/start-conversation
  POST  /api/2.0/genie/spaces/{space_id}/conversations/{conv}/messages
  GET   /api/2.0/genie/spaces/{space_id}/conversations/{conv}/messages/{msg}
  GET   /api/2.0/genie/spaces/{space_id}/conversations/{conv}/messages/{msg}/query-result

When ``DATABRICKS_HOST``, ``DATABRICKS_TOKEN``, and
``DATABRICKS_GENIE_SPACE_ID`` are all set, the route is enabled.
Otherwise it returns 503 so the frontend can fall back to OpenAI
streaming (the existing ``/api/chat/message`` route).

The frontend ships pre-curated example questions; this route turns
each one into a Genie conversation and returns the assistant text
plus the resulting rows so the UI can render either.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.config import settings
from app.core.data_store import get_city_config

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Curated suggestion chips for the AI Analyst panel.
#
# These are the questions the demo will showcase. They double as a quick
# regression check that the configured Genie space sees the expected
# tables (varanasi.default.tract_risk_scores, tract_risk_scores_history,
# tract_crime_features, tract_acs_population).
# ---------------------------------------------------------------------------
SUGGESTIONS: dict[str, list[dict[str, str]]] = {
    "chicago": [
        {
            "label": "Top 10 critical tracts",
            "prompt": (
                "List the top 10 tracts in Cook County by current risk score, "
                "with their tier, predicted incidents next 30 days, and trend direction."
            ),
        },
        {
            "label": "Tier movers (last month)",
            "prompt": (
                "Which tracts moved into the Critical or High tier compared to last month?"
            ),
        },
        {
            "label": "Disagreement watchlist",
            "prompt": (
                "Show tracts where the ML score diverges from the historical baseline by more "
                "than 30 percent."
            ),
        },
        {
            "label": "Compare two tracts",
            "prompt": (
                "Compare risk for tract 17031839100 vs 17031320102 — scores, tiers, "
                "and the top three SHAP drivers for each."
            ),
        },
        {
            "label": "Underreporting risk",
            "prompt": (
                "Which tracts have low recent incident counts but high poverty rates? "
                "Flag the ten with the highest underreporting risk."
            ),
        },
    ],
    "uk": [
        {
            "label": "Top 10 critical MSOAs",
            "prompt": (
                "List the top 10 MSOAs in England & Wales by current risk score, "
                "with their tier and trend direction."
            ),
        },
        {
            "label": "London hotspots",
            "prompt": (
                "Which Greater London MSOAs are in the Critical or High tier right now?"
            ),
        },
        {
            "label": "Compare two MSOAs",
            "prompt": (
                "Compare risk for E02000001 (City of London 001) and E02006781 — "
                "scores, tiers, and top drivers."
            ),
        },
        {
            "label": "Rising trend",
            "prompt": (
                "Which 20 MSOAs have the steepest rising trend in risk score?"
            ),
        },
        {
            "label": "By region",
            "prompt": (
                "Average risk score by ONS region (Greater London, North West, etc.)."
            ),
        },
    ],
}


class GenieQueryRequest(BaseModel):
    message: str
    city: str | None = None
    conversation_id: str | None = None  # for follow-ups


class GenieQueryResponse(BaseModel):
    enabled: bool
    answer: str | None = None
    sql: str | None = None
    rows: list[dict[str, Any]] | None = None
    columns: list[str] | None = None
    conversation_id: str | None = None
    message_id: str | None = None
    error: str | None = None


def _genie_configured() -> bool:
    return bool(
        settings.databricks_host
        and settings.databricks_token
        and settings.databricks_genie_space_id
    )


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.databricks_token}",
        "Content-Type": "application/json",
    }


def _api_base() -> str:
    host = settings.databricks_host.rstrip("/")
    space = settings.databricks_genie_space_id
    return f"{host}/api/2.0/genie/spaces/{space}"


async def _poll_message(
    client: httpx.AsyncClient, conv_id: str, msg_id: str, timeout_s: float = 30.0
) -> dict[str, Any]:
    """Poll a Genie message until status is COMPLETED, FAILED, or CANCELLED."""
    base = _api_base()
    deadline = asyncio.get_event_loop().time() + timeout_s
    while True:
        r = await client.get(
            f"{base}/conversations/{conv_id}/messages/{msg_id}",
            headers=_headers(),
        )
        r.raise_for_status()
        msg = r.json()
        status = msg.get("status")
        if status in {"COMPLETED", "FAILED", "CANCELLED"}:
            return msg
        if asyncio.get_event_loop().time() > deadline:
            raise HTTPException(504, "Genie message timed out")
        await asyncio.sleep(1.0)


async def _query_result(
    client: httpx.AsyncClient, conv_id: str, msg_id: str
) -> tuple[list[str], list[dict[str, Any]]] | tuple[None, None]:
    base = _api_base()
    r = await client.get(
        f"{base}/conversations/{conv_id}/messages/{msg_id}/query-result",
        headers=_headers(),
    )
    if r.status_code == 404:
        return None, None
    r.raise_for_status()
    payload = r.json()
    schema = payload.get("statement_response", {}).get("manifest", {}).get("schema", {})
    cols = [c.get("name") for c in schema.get("columns", [])]
    data_arrays = (
        payload.get("statement_response", {})
        .get("result", {})
        .get("data_typed_array", [])
    )
    rows: list[dict[str, Any]] = []
    for row in data_arrays:
        values = [v.get("str") for v in row.get("values", [])]
        rows.append(dict(zip(cols, values)))
    return cols, rows


@router.get("/status")
def genie_status() -> dict[str, Any]:
    return {
        "configured": _genie_configured(),
        "host": settings.databricks_host or None,
        "space_id_set": bool(settings.databricks_genie_space_id),
    }


@router.get("/suggestions")
def genie_suggestions(city: str | None = None) -> dict[str, Any]:
    cfg = get_city_config(city)
    key = "uk" if cfg["country"] == "UK" else "chicago"
    return {
        "city": key,
        "label": cfg["label"],
        "geography": cfg["geography"],
        "suggestions": SUGGESTIONS.get(key, []),
        "configured": _genie_configured(),
    }


@router.post("/query", response_model=GenieQueryResponse)
async def genie_query(req: GenieQueryRequest) -> GenieQueryResponse:
    if not _genie_configured():
        return GenieQueryResponse(
            enabled=False,
            error=(
                "Genie not configured. Set DATABRICKS_HOST, DATABRICKS_TOKEN, "
                "and DATABRICKS_GENIE_SPACE_ID."
            ),
        )

    base = _api_base()
    timeout = httpx.Timeout(60.0, connect=10.0)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            if req.conversation_id:
                r = await client.post(
                    f"{base}/conversations/{req.conversation_id}/messages",
                    headers=_headers(),
                    json={"content": req.message},
                )
            else:
                r = await client.post(
                    f"{base}/start-conversation",
                    headers=_headers(),
                    json={"content": req.message},
                )
            r.raise_for_status()
            payload = r.json()

            conv_id = payload.get("conversation_id") or payload.get(
                "conversation", {}
            ).get("id")
            msg_id = payload.get("message_id") or payload.get("message", {}).get("id")
            if not conv_id or not msg_id:
                raise HTTPException(502, f"Unexpected Genie response shape: {payload}")

            msg = await _poll_message(client, conv_id, msg_id)
            if msg.get("status") != "COMPLETED":
                return GenieQueryResponse(
                    enabled=True,
                    conversation_id=conv_id,
                    message_id=msg_id,
                    error=f"Genie status: {msg.get('status')}",
                )

            attachments = msg.get("attachments") or []
            answer_text = None
            sql_text = None
            for a in attachments:
                if a.get("text", {}).get("content"):
                    answer_text = a["text"]["content"]
                if a.get("query", {}).get("query"):
                    sql_text = a["query"]["query"]

            cols, rows = await _query_result(client, conv_id, msg_id)

            return GenieQueryResponse(
                enabled=True,
                answer=answer_text,
                sql=sql_text,
                rows=rows,
                columns=cols,
                conversation_id=conv_id,
                message_id=msg_id,
            )
    except httpx.HTTPStatusError as e:
        logger.warning("Genie HTTP error: %s — %s", e.response.status_code, e.response.text[:300])
        raise HTTPException(e.response.status_code, f"Genie error: {e.response.text[:300]}")
    except Exception as e:
        logger.exception("Genie call failed")
        raise HTTPException(502, f"Genie call failed: {e}")
