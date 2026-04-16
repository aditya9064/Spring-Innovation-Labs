"""
Data store that tries PostgreSQL first, falls back to JSON files.
Keeps the same public API so all route modules work unchanged.
"""
import json
import logging
from pathlib import Path
from typing import Any

from sqlalchemy import select, func, text

from app.core.config import settings

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"

_json_scores: list[dict[str, Any]] = []
_json_tracts: dict[str, dict[str, Any]] = {}
_json_acs: dict[str, dict[str, Any]] = {}
_json_pipeline_stats: dict[str, Any] = {}
_json_loaded = False
_use_db: bool | None = None


def _check_db() -> bool:
    """Synchronous check whether PostgreSQL is reachable and seeded."""
    global _use_db
    if _use_db is not None:
        return _use_db

    try:
        from sqlalchemy import create_engine
        sync_url = settings.database_url.replace("+asyncpg", "")
        eng = create_engine(sync_url, pool_pre_ping=True)
        with eng.connect() as conn:
            count = conn.execute(text("SELECT COUNT(*) FROM tract_scores")).scalar()
            _use_db = count is not None and count > 0
            if _use_db:
                logger.info("PostgreSQL connected — %d tract scores available", count)
            else:
                logger.info("PostgreSQL connected but no data — falling back to JSON")
        eng.dispose()
    except Exception as exc:
        logger.info("PostgreSQL unavailable (%s) — using JSON files", exc)
        _use_db = False

    return _use_db


def _load_json() -> None:
    global _json_scores, _json_tracts, _json_acs, _json_pipeline_stats, _json_loaded
    if _json_loaded:
        return

    scores_path = _DATA_DIR / "tract_risk_scores.json"
    tracts_path = _DATA_DIR / "cook_tract_boundaries.json"
    acs_path = _DATA_DIR / "tract_acs_population.json"
    stats_path = _DATA_DIR / "pipeline_stats.json"

    if scores_path.exists():
        with open(scores_path) as f:
            _json_scores = json.load(f)
        logger.info("Loaded %d tract scores from JSON", len(_json_scores))
    else:
        logger.warning("No JSON scores at %s", scores_path)
        _json_scores = []

    if tracts_path.exists():
        with open(tracts_path) as f:
            tracts_list = json.load(f)
        _json_tracts = {t["tract_geoid"]: t for t in tracts_list}

    if acs_path.exists():
        with open(acs_path) as f:
            acs_list = json.load(f)
        _json_acs = {a["tract_geoid"]: a for a in acs_list}

    if stats_path.exists():
        with open(stats_path) as f:
            stats_list = json.load(f)
        _json_pipeline_stats = stats_list[0] if stats_list else {}

    _json_loaded = True


def _query_db(query_text: str, params: dict | None = None) -> list[dict]:
    from sqlalchemy import create_engine
    sync_url = settings.database_url.replace("+asyncpg", "")
    eng = create_engine(sync_url)
    with eng.connect() as conn:
        result = conn.execute(text(query_text), params or {})
        rows = [dict(r._mapping) for r in result]
    eng.dispose()
    return rows


def _score_row_to_dict(row: dict) -> dict[str, Any]:
    """Normalize a DB row to match the JSON schema (NAMELSAD key etc.)."""
    d = dict(row)
    if "namelsad" in d and "NAMELSAD" not in d:
        d["NAMELSAD"] = d.pop("namelsad")
    d.pop("id", None)
    return d


# ---- Public API (same signatures as before) ----

def get_all_scores() -> list[dict[str, Any]]:
    if _check_db():
        rows = _query_db("SELECT * FROM tract_scores")
        return [_score_row_to_dict(r) for r in rows]
    _load_json()
    return _json_scores


def get_score_by_tract(tract_geoid: str) -> dict[str, Any] | None:
    if _check_db():
        rows = _query_db(
            "SELECT * FROM tract_scores WHERE tract_geoid = :geoid LIMIT 1",
            {"geoid": tract_geoid},
        )
        return _score_row_to_dict(rows[0]) if rows else None
    _load_json()
    for s in _json_scores:
        if s.get("tract_geoid") == tract_geoid:
            return s
    return None


def get_tract_boundary(tract_geoid: str) -> dict[str, Any] | None:
    if _check_db():
        rows = _query_db(
            "SELECT tract_geoid, \"NAMELSAD\" as namelsad, wkt, \"ALAND\" as aland FROM tract_boundaries WHERE tract_geoid = :geoid LIMIT 1",
            {"geoid": tract_geoid},
        )
        if rows:
            r = rows[0]
            return {"tract_geoid": r["tract_geoid"], "NAMELSAD": r.get("namelsad"), "wkt": r.get("wkt"), "ALAND": r.get("aland")}
        return None
    _load_json()
    return _json_tracts.get(tract_geoid)


def get_all_tracts() -> dict[str, dict[str, Any]]:
    if _check_db():
        rows = _query_db("SELECT tract_geoid, \"NAMELSAD\" as namelsad, wkt, \"ALAND\" as aland FROM tract_boundaries")
        return {
            r["tract_geoid"]: {"tract_geoid": r["tract_geoid"], "NAMELSAD": r.get("namelsad"), "wkt": r.get("wkt"), "ALAND": r.get("aland")}
            for r in rows
        }
    _load_json()
    return _json_tracts


def get_acs(tract_geoid: str) -> dict[str, Any] | None:
    if _check_db():
        rows = _query_db(
            "SELECT * FROM tract_acs WHERE tract_geoid = :geoid LIMIT 1",
            {"geoid": tract_geoid},
        )
        if rows:
            d = dict(rows[0])
            d.pop("id", None)
            return d
        return None
    _load_json()
    return _json_acs.get(tract_geoid)


def get_pipeline_stats() -> dict[str, Any]:
    if _check_db():
        rows = _query_db("SELECT * FROM pipeline_stats LIMIT 1")
        if rows:
            d = dict(rows[0])
            d.pop("id", None)
            return d
    _load_json()
    return _json_pipeline_stats


def get_scores_by_tier() -> dict[str, list[dict[str, Any]]]:
    scores = get_all_scores()
    tiers: dict[str, list[dict[str, Any]]] = {}
    for s in scores:
        tier = s.get("risk_tier", "Unknown")
        tiers.setdefault(tier, []).append(s)
    return tiers


def get_geojson() -> dict[str, Any]:
    """Build a GeoJSON FeatureCollection from scores + boundaries."""
    from shapely import wkt

    scores = get_all_scores()
    tracts = get_all_tracts()

    features = []
    for score in scores:
        geoid = score.get("tract_geoid")
        tract = tracts.get(geoid)
        if not tract or not tract.get("wkt"):
            continue

        try:
            geom = wkt.loads(tract["wkt"])
            geojson_geom = json.loads(json.dumps(geom.__geo_interface__))
        except Exception:
            continue

        props = {
            "tract_geoid": geoid,
            "name": tract.get("NAMELSAD", ""),
            "risk_score": score.get("risk_score", 0),
            "risk_tier": score.get("risk_tier", "Unknown"),
            "predicted_next_30d": score.get("predicted_next_30d", 0),
            "predicted_violent_30d": score.get("predicted_violent_30d"),
            "predicted_property_30d": score.get("predicted_property_30d"),
            "violent_score": score.get("violent_score"),
            "property_score": score.get("property_score"),
            "incident_count": score.get("incident_count", 0),
            "y_incidents_12m": score.get("y_incidents_12m", 0),
            "trend_direction": score.get("trend_direction"),
            "model_vs_baseline": score.get("model_vs_baseline"),
            "top_drivers_json": score.get("top_drivers_json", "[]"),
            "total_pop_acs": score.get("total_pop_acs"),
            "median_hh_income_acs": score.get("median_hh_income_acs"),
            "poverty_rate_acs": score.get("poverty_rate_acs"),
        }

        features.append({
            "type": "Feature",
            "properties": props,
            "geometry": geojson_geom,
        })

    return {"type": "FeatureCollection", "features": features}


def reload() -> None:
    global _json_loaded, _use_db
    _json_loaded = False
    _use_db = None
    _load_json()


# ---- Audit helpers (DB-backed when possible) ----

def get_audit_entries(region_id: str | None = None, limit: int = 50) -> list[dict]:
    if _check_db():
        if region_id:
            rows = _query_db(
                "SELECT * FROM audit_entries WHERE region_id = :rid ORDER BY id DESC LIMIT :lim",
                {"rid": region_id, "lim": limit},
            )
        else:
            rows = _query_db("SELECT * FROM audit_entries ORDER BY id DESC LIMIT :lim", {"lim": limit})
        result = []
        for r in rows:
            d = dict(r)
            d["id"] = d.pop("entry_id", d.get("id"))
            d.pop("id", None) if "entry_id" not in r else None
            result.append(d)
        return result
    return []


def add_audit_entry(record: dict) -> dict:
    if _check_db():
        from sqlalchemy import create_engine
        sync_url = settings.database_url.replace("+asyncpg", "")
        eng = create_engine(sync_url)
        with eng.connect() as conn:
            conn.execute(text(
                "INSERT INTO audit_entries (entry_id, timestamp, region_id, persona, decision, rationale, risk_score, risk_tier, overridden, override_reason) "
                "VALUES (:entry_id, :timestamp, :region_id, :persona, :decision, :rationale, :risk_score, :risk_tier, :overridden, :override_reason)"
            ), {
                "entry_id": record["id"],
                "timestamp": record["timestamp"],
                "region_id": record["region_id"],
                "persona": record["persona"],
                "decision": record["decision"],
                "rationale": record.get("rationale", ""),
                "risk_score": record.get("risk_score", 0),
                "risk_tier": record.get("risk_tier", "Unknown"),
                "overridden": record.get("overridden", False),
                "override_reason": record.get("override_reason"),
            })
            conn.commit()
        eng.dispose()
    return record


def get_challenge_entries(region_id: str | None = None, status: str | None = None) -> list[dict]:
    if _check_db():
        where_parts = []
        params: dict = {}
        if region_id:
            where_parts.append("region_id = :rid")
            params["rid"] = region_id
        if status:
            where_parts.append("status = :st")
            params["st"] = status
        where_clause = " WHERE " + " AND ".join(where_parts) if where_parts else ""
        rows = _query_db(f"SELECT * FROM challenges{where_clause} ORDER BY id DESC", params)
        result = []
        for r in rows:
            d = dict(r)
            d["id"] = d.pop("challenge_id", d.get("id"))
            result.append(d)
        return result
    return []


def add_challenge_entry(record: dict) -> dict:
    if _check_db():
        from sqlalchemy import create_engine
        sync_url = settings.database_url.replace("+asyncpg", "")
        eng = create_engine(sync_url)
        with eng.connect() as conn:
            conn.execute(text(
                "INSERT INTO challenges (challenge_id, timestamp, region_id, challenger_name, challenge_type, evidence, proposed_adjustment, status, reviewer_notes) "
                "VALUES (:challenge_id, :timestamp, :region_id, :challenger_name, :challenge_type, :evidence, :proposed_adjustment, :status, :reviewer_notes)"
            ), {
                "challenge_id": record["id"],
                "timestamp": record["timestamp"],
                "region_id": record["region_id"],
                "challenger_name": record["challenger_name"],
                "challenge_type": record["challenge_type"],
                "evidence": record.get("evidence", ""),
                "proposed_adjustment": record.get("proposed_adjustment"),
                "status": record.get("status", "pending"),
                "reviewer_notes": record.get("reviewer_notes"),
            })
            conn.commit()
        eng.dispose()
    return record


def update_challenge_entry(challenge_id: str, status: str, reviewer_notes: str) -> dict | None:
    if _check_db():
        from sqlalchemy import create_engine
        sync_url = settings.database_url.replace("+asyncpg", "")
        eng = create_engine(sync_url)
        with eng.connect() as conn:
            conn.execute(text(
                "UPDATE challenges SET status = :status, reviewer_notes = :notes WHERE challenge_id = :cid"
            ), {"status": status, "notes": reviewer_notes, "cid": challenge_id})
            conn.commit()
            result = conn.execute(text("SELECT * FROM challenges WHERE challenge_id = :cid"), {"cid": challenge_id})
            row = result.first()
            if row:
                d = dict(row._mapping)
                d["id"] = d.pop("challenge_id", d.get("id"))
                eng.dispose()
                return d
        eng.dispose()
    return None
