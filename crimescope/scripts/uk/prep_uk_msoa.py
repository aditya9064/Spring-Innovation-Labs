"""
prep_uk_msoa.py — UK MSOA boundary refresh (offline-fallback / boundary-only).

This script used to also produce a SYNTHETIC multi-gravity risk score for every
MSOA so the demo had something on the map before the real pipeline was wired.
The real scoring now lives in the Databricks pipeline:

    /Workspace/Shared/Team_varanasi/ML/02_uk_ingest_and_geos.ipynb
    /Workspace/Shared/Team_varanasi/ML/03_uk_panel_features_demographics.ipynb
    /Workspace/Shared/Team_varanasi/ML/04_uk_train_and_evaluate.ipynb
    /Workspace/Shared/Team_varanasi/ML/05_uk_score_and_serve.ipynb
    /Workspace/Shared/Team_varanasi/ML/06_uk_export_for_backend.ipynb

…with the scored JSON pulled back into ``crimescope/backend/app/data/`` via
``databricks fs cp``. See ``crimescope/scripts/databricks/import_uk.sh`` and
the plan in ``.cursor/plans/uk_wales_real_models_*.plan.md``.

What this script still does (and only this):

  * Pulls the ONS MSOA Dec 2021 BSC layer and writes
    ``crimescope/backend/app/data/uk_msoa_boundaries.json`` so a developer
    without Databricks credentials can at least render the map.
  * If ONS is unreachable, writes a tiny synthetic Greater London grid as a
    last-resort fallback so the frontend doesn't 404 on boundaries.

It deliberately does **not** fabricate risk scores anymore; the consumer is
expected to populate ``uk_msoa_risk_scores.json`` (and the LSOA equivalents)
from the Databricks export volume.
"""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ONS_BASE = (
    "https://services1.arcgis.com/ESMARspQHYMw9BZ9/arcgis/rest/services/"
    "Middle_layer_Super_Output_Areas_December_2021_Boundaries_EW_BSC_V3/"
    "FeatureServer/0/query"
)
PAGE_SIZE = 2000
TOTAL_EXPECTED = 7264

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "backend" / "app" / "data"


# ---------------------------------------------------------------------------
# ONS boundary download
# ---------------------------------------------------------------------------


def _ons_query(offset: int) -> dict[str, Any]:
    params = {
        "where": "1=1",
        "outFields": "MSOA21CD,MSOA21NM,LAT,LONG",
        "outSR": "4326",
        "f": "geojson",
        "resultOffset": str(offset),
        "resultRecordCount": str(PAGE_SIZE),
        "orderByFields": "MSOA21CD",
    }
    url = f"{ONS_BASE}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": "CrimeScope-prep/2.0"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read())


def fetch_msoa_boundaries() -> list[dict[str, Any]]:
    print(f"[boundaries] fetching ~{TOTAL_EXPECTED} MSOA features in pages of {PAGE_SIZE}…")
    features: list[dict[str, Any]] = []
    offset = 0
    while True:
        attempt = 0
        while True:
            try:
                page = _ons_query(offset)
                break
            except (urllib.error.URLError, TimeoutError) as exc:
                attempt += 1
                if attempt >= 3:
                    raise
                wait = 2 ** attempt
                print(f"  retry offset={offset} attempt={attempt} after {wait}s ({exc})")
                time.sleep(wait)
        page_feats = page.get("features", [])
        if not page_feats:
            break
        features.extend(page_feats)
        print(f"  fetched offset={offset:>5} — running total {len(features):>5}")
        if len(page_feats) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
    print(f"[boundaries] total fetched: {len(features)}")
    return features


def _geometry_to_wkt(geom: dict[str, Any]) -> str | None:
    def ring(r):
        return ", ".join(f"{x} {y}" for x, y in r)

    def poly(p):
        return "(" + ", ".join(f"({ring(r)})" for r in p) + ")"

    gtype = geom.get("type")
    coords = geom.get("coordinates")
    if not coords:
        return None
    if gtype == "Polygon":
        return "POLYGON " + poly(coords)
    if gtype == "MultiPolygon":
        return "MULTIPOLYGON (" + ", ".join(poly(p) for p in coords) + ")"
    return None


def normalize_boundaries(features: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    skipped = 0
    for f in features:
        props = f.get("properties") or {}
        code = props.get("MSOA21CD")
        name = props.get("MSOA21NM")
        if not code:
            skipped += 1
            continue
        wkt = _geometry_to_wkt(f.get("geometry") or {})
        if not wkt:
            skipped += 1
            continue
        out.append({"tract_geoid": code, "NAMELSAD": name or code, "wkt": wkt, "ALAND": None})
    if skipped:
        print(f"[boundaries] skipped {skipped} features without geometry/code")
    return out


# ---------------------------------------------------------------------------
# Offline fallback (synthetic Greater London grid — boundaries only)
# ---------------------------------------------------------------------------


def synthetic_london_grid() -> list[dict[str, Any]]:
    print("[fallback] generating synthetic London grid (ONS unreachable)")
    cols = rows = 30
    lng0, lng1 = -0.55, 0.30
    lat0, lat1 = 51.30, 51.70
    dlng = (lng1 - lng0) / cols
    dlat = (lat1 - lat0) / rows
    feats: list[dict[str, Any]] = []
    for r in range(rows):
        for c in range(cols):
            x0 = lng0 + c * dlng
            x1 = x0 + dlng
            y0 = lat0 + r * dlat
            y1 = y0 + dlat
            ring = f"({x0} {y0}, {x1} {y0}, {x1} {y1}, {x0} {y1}, {x0} {y0})"
            feats.append({
                "tract_geoid": f"E99{r:02d}{c:02d}",
                "NAMELSAD": f"London Synthetic {r:02d}-{c:02d}",
                "wkt": f"POLYGON ({ring})",
                "ALAND": None,
            })
    return feats


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    print(f"output dir: {DATA_DIR}")
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    try:
        raw = fetch_msoa_boundaries()
        boundaries = normalize_boundaries(raw)
        if len(boundaries) < 1000:
            raise RuntimeError(f"only got {len(boundaries)} valid features — likely partial")
    except Exception as exc:  # noqa: BLE001 — we want a hard fallback
        print(f"[boundaries] ONS fetch failed: {exc}")
        boundaries = synthetic_london_grid()

    out_path = DATA_DIR / "uk_msoa_boundaries.json"
    out_path.write_text(json.dumps(boundaries, separators=(",", ":")))
    print(f"[write] {out_path.name} ({out_path.stat().st_size / 1_048_576:.1f} MB, {len(boundaries)} regions)")

    print(
        "\nBoundaries refreshed. To populate risk scores, run the Databricks pipeline:\n"
        "  databricks bundle run crimescope_uk_pipeline --profile team_varanasi -t prod\n"
        "and pull the JSON exports back with:\n"
        "  databricks fs cp -r dbfs:/Volumes/varanasi/default/ml_data_uk/exports/latest/ "
        f"{DATA_DIR}/ --profile team_varanasi --overwrite"
    )

    # Touch the pipeline_stats file with a 'boundaries-only' marker so the
    # backend reports the truth instead of the stale synthetic numbers.
    stats_path = DATA_DIR / "uk_pipeline_stats.json"
    if not stats_path.exists():
        stats_path.write_text(json.dumps([{
            "n_tracts": len(boundaries),
            "data_start": None,
            "data_end": None,
            "total_rows": 0,
            "model_lsoa_version": None,
            "model_msoa_version": None,
            "model_lsoa_mae": None,
            "model_msoa_mae": None,
            "scope": "England & Wales (MSOA 2021, boundaries only)",
            "boundary_source": "ONS Open Geography Portal — MSOA Dec 2021 BSC",
            "score_source": "PENDING — populated by Databricks pipeline 02→06",
            "exported_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        }]))

    return 0


if __name__ == "__main__":
    sys.exit(main())
