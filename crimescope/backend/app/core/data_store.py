"""
Data store that tries PostgreSQL first, falls back to JSON files.

Supports multiple "cities" (geographic regions). Each city has its own bundle
of JSON files in ``app/data/``. Public functions accept an optional ``city``
parameter (default: ``"chicago"``) so existing callers keep working.

Currently supported cities:

  - ``"chicago"`` — Cook County, IL census tracts (PostgreSQL or JSON fallback)
  - ``"uk"``     — England & Wales MSOAs (JSON only; produced by
                    ``crimescope/scripts/uk/prep_uk_msoa.py``)
"""
import json
import logging
from pathlib import Path
from typing import Any

from sqlalchemy import text

from app.core.config import settings

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"


# ---------------------------------------------------------------------------
# City registry
# ---------------------------------------------------------------------------

CITIES: dict[str, dict[str, Any]] = {
    "chicago": {
        "label": "Chicago, IL",
        "country": "US",
        "geography": "Census tract",
        "geographyType": "census_tract",
        "scores_file": "tract_risk_scores.json",
        "boundaries_file": "cook_tract_boundaries.json",
        "demographics_file": "tract_acs_population.json",
        "stats_file": "pipeline_stats.json",
        "uses_db": True,
        "default_region_id": "17031839100",
        "scope_label": "Cook County",
        "data_window_label": "72 months of historical Chicago Open Data crime",
    },
    "uk": {
        "label": "England & Wales",
        "country": "UK",
        "geography": "MSOA",
        "geographyType": "msoa",
        "scores_file": "uk_msoa_risk_scores.json",
        "boundaries_file": "uk_msoa_boundaries.json",
        "demographics_file": "uk_msoa_demographics.json",
        "stats_file": "uk_pipeline_stats.json",
        "uses_db": False,
        "default_region_id": "E02000001",  # City of London 001
        "scope_label": "England & Wales",
        "data_window_label": (
            "60 months of data.police.uk crime, ONS Census 2021, IMD/WIMD 2019 "
            "(MSOA rollup, LightGBM model)"
        ),
    },
    "uk_lsoa": {
        "label": "England & Wales (LSOA detail)",
        "country": "UK",
        "geography": "LSOA",
        "geographyType": "lsoa",
        "scores_file": "uk_lsoa_risk_scores.json",
        "boundaries_file": "uk_lsoa_boundaries.json",
        "demographics_file": "uk_lsoa_demographics.json",
        "stats_file": "uk_pipeline_stats.json",
        "uses_db": False,
        "default_region_id": "E01000001",  # City of London 001A
        "scope_label": "England & Wales (LSOA)",
        "data_window_label": (
            "60 months of data.police.uk crime, ONS Census 2021, IMD/WIMD 2019 "
            "(LSOA primary grain, LightGBM model)"
        ),
    },
}

DEFAULT_CITY = "uk"


def _resolve_city(city: str | None) -> str:
    if not city:
        return DEFAULT_CITY
    c = city.lower().strip()
    if c not in CITIES:
        logger.warning("Unknown city %r — falling back to %s", city, DEFAULT_CITY)
        return DEFAULT_CITY
    return c


# ---------------------------------------------------------------------------
# JSON loading (per-city cache)
# ---------------------------------------------------------------------------

# Per-city in-memory caches
_json_scores: dict[str, list[dict[str, Any]]] = {}
_json_tracts: dict[str, dict[str, dict[str, Any]]] = {}
_json_acs: dict[str, dict[str, dict[str, Any]]] = {}
_json_pipeline_stats: dict[str, dict[str, Any]] = {}
_json_loaded: dict[str, bool] = {}

# DB availability is tracked per-city so the UK city is never probed
_use_db: dict[str, bool | None] = {}

# Which database the connected backend resolved to (per-city). Used in
# /api/health to surface "lakebase" vs "postgres" vs "json".
_db_backend_kind: dict[str, str] = {}


def _resolve_db_url() -> tuple[str, str] | None:
    """Resolve the database URL based on the ``DATA_STORE_BACKEND`` setting.

    Returns ``(sync_sqlalchemy_url, backend_kind)`` or ``None`` when the DB
    layer should be skipped entirely.

    Backends:

    * ``lakebase`` — Lakebase Postgres-on-Databricks via ``LAKEBASE_URL``
    * ``postgres`` — local Postgres via ``DATABASE_URL``
    * ``json``     — skip DB entirely; everything reads from JSON snapshots
    * ``auto``     — Lakebase if configured, else local Postgres, else JSON

    The same FastAPI process can be pointed at any of these by changing one
    env var, with no schema or query changes — Lakebase exposes Postgres
    semantics on top of Unity-Catalog-governed storage.
    """
    pref = (settings.data_store_backend or "auto").lower().strip()
    lakebase = (settings.lakebase_url or "").strip()
    pg = (settings.database_url or "").strip()

    if pref == "json":
        return None
    if pref == "lakebase":
        if not lakebase:
            return None
        return (lakebase.replace("+asyncpg", ""), "lakebase")
    if pref == "postgres":
        if not pg:
            return None
        return (pg.replace("+asyncpg", ""), "postgres")
    # auto
    if lakebase:
        return (lakebase.replace("+asyncpg", ""), "lakebase")
    if pg:
        return (pg.replace("+asyncpg", ""), "postgres")
    return None


def _check_db(city: str) -> bool:
    cfg = CITIES[city]
    if not cfg.get("uses_db"):
        return False
    cached = _use_db.get(city)
    if cached is not None:
        return cached
    resolved = _resolve_db_url()
    if resolved is None:
        _use_db[city] = False
        return False
    sync_url, kind = resolved
    try:
        from sqlalchemy import create_engine
        eng = create_engine(sync_url, pool_pre_ping=True)
        with eng.connect() as conn:
            count = conn.execute(text("SELECT COUNT(*) FROM tract_scores")).scalar()
            available = count is not None and count > 0
            _use_db[city] = available
            _db_backend_kind[city] = kind if available else "json"
            if available:
                logger.info(
                    "%s connected — %d %s scores available", kind.capitalize(), count, city
                )
            else:
                logger.info(
                    "%s connected but no %s data — JSON fallback", kind.capitalize(), city
                )
        eng.dispose()
    except Exception as exc:
        logger.info("%s unavailable for %s (%s) — using JSON files", kind, city, exc)
        _use_db[city] = False
        _db_backend_kind[city] = "json"
    return bool(_use_db[city])


def get_backend_kind(city: str | None = None) -> str:
    """Reports the active read backend for the given city: lakebase, postgres, or json."""
    c = _resolve_city(city)
    if _check_db(c):
        return _db_backend_kind.get(c, "postgres")
    return "json"


def _load_json(city: str) -> None:
    if _json_loaded.get(city):
        return

    cfg = CITIES[city]
    scores_path = _DATA_DIR / cfg["scores_file"]
    tracts_path = _DATA_DIR / cfg["boundaries_file"]
    acs_path = _DATA_DIR / cfg["demographics_file"]
    stats_path = _DATA_DIR / cfg["stats_file"]

    if scores_path.exists():
        with open(scores_path) as f:
            _json_scores[city] = json.load(f)
        logger.info("[%s] loaded %d scores from JSON", city, len(_json_scores[city]))
    else:
        logger.warning("[%s] no JSON scores at %s", city, scores_path)
        _json_scores[city] = []

    if tracts_path.exists():
        with open(tracts_path) as f:
            tracts_list = json.load(f)
        _json_tracts[city] = {t["tract_geoid"]: t for t in tracts_list}
        logger.info("[%s] loaded %d boundaries", city, len(_json_tracts[city]))
    else:
        _json_tracts[city] = {}

    if acs_path.exists():
        with open(acs_path) as f:
            acs_list = json.load(f)
        _json_acs[city] = {a["tract_geoid"]: a for a in acs_list}
    else:
        _json_acs[city] = {}

    if stats_path.exists():
        with open(stats_path) as f:
            stats_list = json.load(f)
        _json_pipeline_stats[city] = stats_list[0] if stats_list else {}
    else:
        _json_pipeline_stats[city] = {}

    _json_loaded[city] = True


def _query_db(query_text: str, params: dict | None = None) -> list[dict]:
    from sqlalchemy import create_engine
    resolved = _resolve_db_url()
    if resolved is None:
        return []
    sync_url, _ = resolved
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


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_city_config(city: str | None = None) -> dict[str, Any]:
    return dict(CITIES[_resolve_city(city)])


def list_cities() -> list[dict[str, Any]]:
    return [
        {
            "id": cid,
            "label": cfg["label"],
            "country": cfg["country"],
            "geography": cfg["geography"],
            "geographyType": cfg["geographyType"],
            "defaultRegionId": cfg["default_region_id"],
        }
        for cid, cfg in CITIES.items()
    ]


def get_all_scores(city: str | None = None) -> list[dict[str, Any]]:
    c = _resolve_city(city)
    if _check_db(c):
        rows = _query_db("SELECT * FROM tract_scores")
        return [_score_row_to_dict(r) for r in rows]
    _load_json(c)
    return _json_scores.get(c, [])


def get_score_by_tract(tract_geoid: str, city: str | None = None) -> dict[str, Any] | None:
    c = _resolve_city(city)
    if _check_db(c):
        rows = _query_db(
            "SELECT * FROM tract_scores WHERE tract_geoid = :geoid LIMIT 1",
            {"geoid": tract_geoid},
        )
        return _score_row_to_dict(rows[0]) if rows else None
    _load_json(c)
    for s in _json_scores.get(c, []):
        if s.get("tract_geoid") == tract_geoid:
            return s
    return None


def get_score_by_region(region_id: str, city: str | None = None) -> dict[str, Any] | None:
    """Look up a score by region ID, automatically figuring out the city if not
    specified by checking each loaded city's data. Useful for cross-city lookups
    where the caller only has the opaque ID."""
    if city is not None:
        return get_score_by_tract(region_id, city=city)
    for cid in CITIES:
        s = get_score_by_tract(region_id, city=cid)
        if s:
            return s
    return None


def infer_city_for_region(region_id: str) -> str | None:
    """Best-effort lookup: which city does this region_id belong to?"""
    for cid in CITIES:
        if get_score_by_tract(region_id, city=cid):
            return cid
    return None


def get_tract_boundary(tract_geoid: str, city: str | None = None) -> dict[str, Any] | None:
    c = _resolve_city(city)
    if _check_db(c):
        rows = _query_db(
            "SELECT tract_geoid, \"NAMELSAD\" as namelsad, wkt, \"ALAND\" as aland FROM tract_boundaries WHERE tract_geoid = :geoid LIMIT 1",
            {"geoid": tract_geoid},
        )
        if rows:
            r = rows[0]
            return {"tract_geoid": r["tract_geoid"], "NAMELSAD": r.get("namelsad"), "wkt": r.get("wkt"), "ALAND": r.get("aland")}
        return None
    _load_json(c)
    return _json_tracts.get(c, {}).get(tract_geoid)


def get_all_tracts(city: str | None = None) -> dict[str, dict[str, Any]]:
    c = _resolve_city(city)
    if _check_db(c):
        rows = _query_db("SELECT tract_geoid, \"NAMELSAD\" as namelsad, wkt, \"ALAND\" as aland FROM tract_boundaries")
        return {
            r["tract_geoid"]: {"tract_geoid": r["tract_geoid"], "NAMELSAD": r.get("namelsad"), "wkt": r.get("wkt"), "ALAND": r.get("aland")}
            for r in rows
        }
    _load_json(c)
    return _json_tracts.get(c, {})


def get_acs(tract_geoid: str, city: str | None = None) -> dict[str, Any] | None:
    c = _resolve_city(city)
    if _check_db(c):
        rows = _query_db(
            "SELECT * FROM tract_acs WHERE tract_geoid = :geoid LIMIT 1",
            {"geoid": tract_geoid},
        )
        if rows:
            d = dict(rows[0])
            d.pop("id", None)
            return d
        return None
    _load_json(c)
    return _json_acs.get(c, {}).get(tract_geoid)


def get_pipeline_stats(city: str | None = None) -> dict[str, Any]:
    c = _resolve_city(city)
    if _check_db(c):
        rows = _query_db("SELECT * FROM pipeline_stats LIMIT 1")
        if rows:
            d = dict(rows[0])
            d.pop("id", None)
            return d
    _load_json(c)
    return _json_pipeline_stats.get(c, {})


def get_scores_by_tier(city: str | None = None) -> dict[str, list[dict[str, Any]]]:
    scores = get_all_scores(city=city)
    tiers: dict[str, list[dict[str, Any]]] = {}
    for s in scores:
        tier = s.get("risk_tier", "Unknown")
        tiers.setdefault(tier, []).append(s)
    return tiers


def get_geojson(city: str | None = None) -> dict[str, Any]:
    """Build a GeoJSON FeatureCollection from scores + boundaries for a city."""
    from shapely import wkt

    scores = get_all_scores(city=city)
    tracts = get_all_tracts(city=city)

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


def reload(city: str | None = None) -> None:
    if city is None:
        _json_loaded.clear()
        _use_db.clear()
        for cid in CITIES:
            _load_json(cid)
    else:
        c = _resolve_city(city)
        _json_loaded.pop(c, None)
        _use_db.pop(c, None)
        _load_json(c)


# ---------------------------------------------------------------------------
# Audit helpers (DB-backed when possible) — city-agnostic
# ---------------------------------------------------------------------------

def get_audit_entries(region_id: str | None = None, limit: int = 50) -> list[dict]:
    if _check_db(DEFAULT_CITY):
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
    if _check_db(DEFAULT_CITY):
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
    if _check_db(DEFAULT_CITY):
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
    if _check_db(DEFAULT_CITY):
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
    if _check_db(DEFAULT_CITY):
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
