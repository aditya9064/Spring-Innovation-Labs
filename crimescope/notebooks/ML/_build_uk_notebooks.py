"""
Generator for the UK & Wales CrimeScope ML notebooks.

Runs locally to materialize the 5 ipynb files so they can be `databricks
workspace import-dir`'d up to /Workspace/Shared/Team_varanasi/ML.

Why a generator instead of hand-edited ipynb files: the notebooks are large,
share a lot of helper code, and need to stay in lock-step with each other and
with the local mirror in crimescope/ml/uk/. Defining them as ordered cell
lists in Python keeps them readable, diffable, and easy to regenerate.

Run from the repo root:

    python3 crimescope/notebooks/ML/_build_uk_notebooks.py
"""
from __future__ import annotations

import json
from pathlib import Path
from textwrap import dedent

OUT_DIR = Path(__file__).resolve().parent


def md(text: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": _split(dedent(text).strip("\n"))}


def code(text: str) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": _split(dedent(text).strip("\n")),
    }


def _split(text: str) -> list[str]:
    lines = text.split("\n")
    return [ln + "\n" for ln in lines[:-1]] + [lines[-1]] if lines else []


def write_notebook(name: str, cells: list[dict]) -> None:
    nb = {
        "cells": cells,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3.11.0"},
        },
        "nbformat": 4,
        "nbformat_minor": 4,
    }
    path = OUT_DIR / name
    path.write_text(json.dumps(nb, indent=1))
    print(f"  wrote {path.name} ({path.stat().st_size / 1024:.1f} KB, {len(cells)} cells)")


# ===========================================================================
# 02 — UK ingest & geographies
# ===========================================================================

def nb_02_uk_ingest() -> list[dict]:
    return [
        md("""
        # CrimeScope ML — 02 (UK). Ingest & Geographies (Lakehouse)

        **Description:** Pull 60 months of `data.police.uk` street-level crime CSVs for
        every England & Wales territorial police force, stage them in a UC Volume, land
        them as a Delta table, and aggregate to monthly counts per LSOA and MSOA with a
        violent / property / other split. Also fetches ONS LSOA + MSOA 2021 boundaries
        and the LSOA→MSOA lookup.

        **Lakehouse features used:**
        - Unity Catalog (`varanasi.default.*`)
        - UC Volume `varanasi.default.ml_data_uk` for raw archive staging
        - Delta Lake with `OPTIMIZE` + `ZORDER` on `lsoa_code` / `month_start`
        - Data-quality assertions (LSOA join rate, monthly coverage per force)
        - Table `COMMENT`s for governance

        **Tables written:**
        - `uk_crime_raw` — every street-level row, 60 months, all forces
        - `uk_crime_monthly_lsoa` — LSOA × month counts (overall / violent / property)
        - `uk_crime_monthly_msoa` — MSOA × month counts (rolled up via lookup)
        - `uk_lsoa_boundaries` — ONS LSOA 2021 BGC polygons (WKT)
        - `uk_msoa_boundaries` — ONS MSOA 2021 BSC polygons (WKT)
        - `uk_lsoa_to_msoa_lookup` — official ONS lookup
        """),
        code("""
        spark.sql("USE CATALOG varanasi")
        spark.sql("USE SCHEMA default")
        display(spark.sql("SELECT current_catalog() AS catalog, current_schema() AS schema"))
        """),
        md("""
        ---
        ## 1. Create the UK staging volume
        """),
        code("""
        spark.sql(\"\"\"
          CREATE VOLUME IF NOT EXISTS varanasi.default.ml_data_uk
          COMMENT 'Raw data staging for CrimeScope UK & Wales ML pipeline'
        \"\"\")
        print("Volume varanasi.default.ml_data_uk ready")
        """),
        md("""
        ---
        ## 2. Pull data.police.uk monthly archives (60 months)

        Each archive is a single zip per month containing `<month>/<month>-<force>-street.csv`
        for every territorial force. We stream the zip into the UC Volume so we don't keep
        ~10 GB of compressed data in driver memory. The download is idempotent — already-staged
        months are skipped.
        """),
        code("""
        import io
        import os
        import urllib.request
        import urllib.error
        from datetime import date, timedelta
        from pathlib import Path

        VOLUME_RAW = "/Volumes/varanasi/default/ml_data_uk/raw/police_uk"
        ARCHIVE_BASE = "https://data.police.uk/data/archive"
        N_MONTHS = 60

        os.makedirs(VOLUME_RAW, exist_ok=True)


        def months_back(n: int) -> list[str]:
            today = date.today().replace(day=1)
            # data.police.uk publishes ~6 weeks after month-end, so we lag by 2 months
            cursor = (today - timedelta(days=62)).replace(day=1)
            out = []
            for _ in range(n):
                out.append(cursor.strftime("%Y-%m"))
                cursor = (cursor.replace(day=1) - timedelta(days=1)).replace(day=1)
            return list(reversed(out))


        TARGET_MONTHS = months_back(N_MONTHS)
        print(f"Target months: {TARGET_MONTHS[0]} .. {TARGET_MONTHS[-1]} ({len(TARGET_MONTHS)} months)")

        downloaded = 0
        skipped = 0
        for ym in TARGET_MONTHS:
            dst = f"{VOLUME_RAW}/{ym}.zip"
            if os.path.exists(dst) and os.path.getsize(dst) > 1_000_000:
                skipped += 1
                continue
            url = f"{ARCHIVE_BASE}/{ym}.zip"
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "CrimeScope-UK/1.0"})
                with urllib.request.urlopen(req, timeout=300) as resp, open(dst, "wb") as f:
                    while True:
                        buf = resp.read(1 << 20)
                        if not buf:
                            break
                        f.write(buf)
                downloaded += 1
                print(f"  fetched {ym}.zip ({os.path.getsize(dst) / 1_048_576:.1f} MB)")
            except urllib.error.HTTPError as e:
                # data.police.uk publishes monthly archives one per month; missing months are normal at the edge
                print(f"  skip {ym} ({e})")
            except Exception as e:  # noqa: BLE001
                print(f"  error {ym}: {e}")

        print(f"\\nDownloaded {downloaded} new, skipped {skipped} existing.")
        """),
        md("""
        ---
        ## 3. Extract archives in parallel into a flat CSV staging dir

        Each `YYYY-MM.zip` archive contains ~43 force CSVs (one per UK police force)
        plus outcomes/stop-and-search files. We extract just the `*-street.csv`
        files into a flat directory on the same UC Volume. Extraction is local-disk
        I/O bound and parallelizes well across a thread pool on the driver.

        After this cell, the staging dir contains ~2,500 CSVs (~60 months × ~43 forces),
        ready for a single distributed `spark.read.csv` in the next step.
        """),
        code("""
        import shutil
        import zipfile
        from concurrent.futures import ThreadPoolExecutor, as_completed

        STAGE_DIR = Path(VOLUME_RAW) / "_extracted_street"
        if STAGE_DIR.exists():
            shutil.rmtree(STAGE_DIR)
        STAGE_DIR.mkdir(parents=True, exist_ok=True)

        def _extract_one(arc_path: Path) -> int:
            n = 0
            month_tag = arc_path.stem  # e.g. 2021-03
            with zipfile.ZipFile(arc_path) as zf:
                for member in zf.namelist():
                    if not member.endswith("-street.csv"):
                        continue
                    # member looks like '2021-03/2021-03-avon-and-somerset-street.csv'
                    out_name = f"{month_tag}__{Path(member).name}"
                    out_path = STAGE_DIR / out_name
                    with zf.open(member) as src, open(out_path, "wb") as dst:
                        shutil.copyfileobj(src, dst, length=1 << 20)
                    n += 1
            return n

        archives = sorted(Path(VOLUME_RAW).glob("*.zip"))
        print(f"Extracting *-street.csv from {len(archives)} archives...")

        total_csvs = 0
        with ThreadPoolExecutor(max_workers=16) as pool:
            futs = {pool.submit(_extract_one, a): a for a in archives}
            for fut in as_completed(futs):
                arc = futs[fut]
                try:
                    n = fut.result()
                    total_csvs += n
                except Exception as e:  # noqa: BLE001
                    print(f"  ! {arc.name}: {e}")

        print(f"Extracted {total_csvs} CSV files into {STAGE_DIR}")
        """),
        md("""
        ---
        ## 4. Bulk-load all street CSVs into `uk_crime_raw` with one Spark read

        Single distributed `spark.read.csv` over the staging directory. This is
        ~100x faster than the per-archive append loop because Spark parallelizes
        the read across executors and writes a single large Delta commit instead
        of 2,500 small ones.
        """),
        code("""
        from pyspark.sql import functions as F
        from pyspark.sql.types import (
            StructType, StructField, StringType, DoubleType,
        )

        VIOLENT_CATS = [
            "Violence and sexual offences",
            "Robbery",
            "Possession of weapons",
            "Public order",
        ]
        PROPERTY_CATS = [
            "Burglary",
            "Vehicle crime",
            "Theft from the person",
            "Bicycle theft",
            "Other theft",
            "Shoplifting",
            "Criminal damage and arson",
        ]

        # Police.uk CSV header is consistent across all months.
        CSV_SCHEMA = StructType([
            StructField("Crime ID",                StringType()),
            StructField("Month",                   StringType()),
            StructField("Reported by",             StringType()),
            StructField("Falls within",            StringType()),
            StructField("Longitude",               DoubleType()),
            StructField("Latitude",                DoubleType()),
            StructField("Location",                StringType()),
            StructField("LSOA code",               StringType()),
            StructField("LSOA name",               StringType()),
            StructField("Crime type",              StringType()),
            StructField("Last outcome category",   StringType()),
            StructField("Context",                 StringType()),
        ])

        STAGE_DIR = f"{VOLUME_RAW}/_extracted_street"
        TABLE = "varanasi.default.uk_crime_raw"

        raw = (spark.read
                    .option("header", True)
                    .option("multiLine", False)
                    .option("escape", '"')
                    .schema(CSV_SCHEMA)
                    .csv(f"{STAGE_DIR}/*.csv"))

        # Restrict to England & Wales LSOAs and shape to canonical schema.
        cleaned = (raw
            .withColumnRenamed("Crime ID",   "crime_id")
            .withColumnRenamed("Month",      "month")
            .withColumnRenamed("Falls within", "force")
            .withColumnRenamed("Longitude",  "longitude")
            .withColumnRenamed("Latitude",   "latitude")
            .withColumnRenamed("LSOA code",  "lsoa_code")
            .withColumnRenamed("LSOA name",  "lsoa_name")
            .withColumnRenamed("Crime type", "crime_type")
            .withColumnRenamed("Last outcome category", "last_outcome")
            .drop("Reported by", "Location", "Context")
            .filter(F.col("lsoa_code").isNotNull())
            .filter(F.col("lsoa_code").rlike("^(E0|W0)"))
            .withColumn("month_start", F.to_date(F.concat_ws("-", F.col("month"), F.lit("01"))))
            .withColumn("category", F.coalesce(F.col("crime_type"), F.lit("Other crime")))
            .withColumn("is_violent",  F.col("category").isin(VIOLENT_CATS).cast("tinyint"))
            .withColumn("is_property", F.col("category").isin(PROPERTY_CATS).cast("tinyint"))
            .select(
                "crime_id", "month", "force",
                "longitude", "latitude",
                "lsoa_code", "lsoa_name",
                "crime_type", "last_outcome",
                "month_start", "category",
                "is_violent", "is_property",
            ))

        (cleaned.write
            .format("delta")
            .mode("overwrite")
            .option("overwriteSchema", "true")
            .saveAsTable(TABLE))

        spark.sql(f\"\"\"
          ALTER TABLE {TABLE}
          SET TBLPROPERTIES (
            'comment' = 'Raw street-level crime rows from data.police.uk for England & Wales (60 months).'
          )
        \"\"\")
        spark.sql(f"OPTIMIZE {TABLE} ZORDER BY (lsoa_code, month_start)")
        n_rows = spark.table(TABLE).count()
        print(f"uk_crime_raw written + optimized: {n_rows:,} rows")

        # Free up the staging directory so we don't retain ~50 GB of CSVs.
        import shutil
        shutil.rmtree(STAGE_DIR, ignore_errors=True)
        print("Cleaned up staging dir")
        """),
        md("""
        ---
        ## 5. ONS boundary downloads (LSOA + MSOA 2021)
        """),
        code("""
        import json
        import urllib.parse

        ONS_LSOA = (
            "https://services1.arcgis.com/ESMARspQHYMw9BZ9/arcgis/rest/services/"
            "Lower_layer_Super_Output_Areas_December_2021_Boundaries_EW_BGC_V3/"
            "FeatureServer/0/query"
        )
        ONS_MSOA = (
            "https://services1.arcgis.com/ESMARspQHYMw9BZ9/arcgis/rest/services/"
            "Middle_layer_Super_Output_Areas_December_2021_Boundaries_EW_BSC_V3/"
            "FeatureServer/0/query"
        )
        PAGE = 2000


        def fetch_layer(base: str, code_field: str, name_field: str) -> list[dict]:
            out = []
            offset = 0
            while True:
                params = {
                    "where": "1=1",
                    "outFields": f"{code_field},{name_field},LAT,LONG",
                    "outSR": "4326",
                    "f": "geojson",
                    "resultOffset": str(offset),
                    "resultRecordCount": str(PAGE),
                    "orderByFields": code_field,
                }
                url = f"{base}?{urllib.parse.urlencode(params)}"
                req = urllib.request.Request(url, headers={"User-Agent": "CrimeScope-UK/1.0"})
                with urllib.request.urlopen(req, timeout=180) as resp:
                    page = json.loads(resp.read())
                feats = page.get("features", [])
                if not feats:
                    break
                out.extend(feats)
                if len(feats) < PAGE:
                    break
                offset += PAGE
                print(f"    offset={offset:>5}  total={len(out):>6}")
            return out


        def features_to_pdf(feats: list[dict], code_field: str, name_field: str, label: str) -> pd.DataFrame:
            def ring_wkt(r):
                return ", ".join(f"{x} {y}" for x, y in r)

            def poly_wkt(p):
                return "(" + ", ".join(f"({ring_wkt(r)})" for r in p) + ")"

            rows = []
            for f in feats:
                p = f.get("properties") or {}
                code = p.get(code_field)
                name = p.get(name_field) or code
                if not code:
                    continue
                geom = f.get("geometry") or {}
                if geom.get("type") == "Polygon":
                    wkt = "POLYGON " + poly_wkt(geom["coordinates"])
                elif geom.get("type") == "MultiPolygon":
                    wkt = "MULTIPOLYGON (" + ", ".join(poly_wkt(p_) for p_ in geom["coordinates"]) + ")"
                else:
                    continue
                rows.append({
                    "tract_geoid": code,
                    "NAMELSAD": name,
                    "wkt": wkt,
                    "ALAND": None,
                    "lat": p.get("LAT"),
                    "lng": p.get("LONG"),
                })
            print(f"  {label}: {len(rows)} polygons")
            return pd.DataFrame(rows)


        print("[boundaries] LSOA…")
        lsoa_feats = fetch_layer(ONS_LSOA, "LSOA21CD", "LSOA21NM")
        lsoa_pdf = features_to_pdf(lsoa_feats, "LSOA21CD", "LSOA21NM", "LSOA")

        print("[boundaries] MSOA…")
        msoa_feats = fetch_layer(ONS_MSOA, "MSOA21CD", "MSOA21NM")
        msoa_pdf = features_to_pdf(msoa_feats, "MSOA21CD", "MSOA21NM", "MSOA")

        spark.createDataFrame(lsoa_pdf).write.mode("overwrite").option("overwriteSchema", "true").saveAsTable("varanasi.default.uk_lsoa_boundaries")
        spark.createDataFrame(msoa_pdf).write.mode("overwrite").option("overwriteSchema", "true").saveAsTable("varanasi.default.uk_msoa_boundaries")
        spark.sql("ALTER TABLE varanasi.default.uk_lsoa_boundaries SET TBLPROPERTIES ('comment' = 'ONS LSOA Dec 2021 BGC boundaries (England & Wales).')")
        spark.sql("ALTER TABLE varanasi.default.uk_msoa_boundaries SET TBLPROPERTIES ('comment' = 'ONS MSOA Dec 2021 BSC boundaries (England & Wales).')")
        print("Boundaries written.")
        """),
        md("""
        ---
        ## 6. LSOA → MSOA lookup
        """),
        code("""
        # Use the ONS Postcode Directory's official LSOA(2021) → MSOA(2021) → LAD lookup
        LOOKUP_URL = (
            "https://services1.arcgis.com/ESMARspQHYMw9BZ9/arcgis/rest/services/"
            "Output_Areas_to_Lower_Layer_Super_Output_Areas_to_Middle_Layer_Super_Output_Areas_to_Local_Authority_Districts_December_2021_Lookup_EW/"
            "FeatureServer/0/query"
        )

        all_rows = []
        offset = 0
        while True:
            params = {
                "where": "1=1",
                "outFields": "LSOA21CD,MSOA21CD,LAD22CD,LAD22NM",
                "returnGeometry": "false",
                "f": "json",
                "resultOffset": str(offset),
                "resultRecordCount": "2000",
                "orderByFields": "LSOA21CD",
            }
            url = f"{LOOKUP_URL}?{urllib.parse.urlencode(params)}"
            req = urllib.request.Request(url, headers={"User-Agent": "CrimeScope-UK/1.0"})
            with urllib.request.urlopen(req, timeout=180) as resp:
                page = json.loads(resp.read())
            feats = page.get("features", [])
            if not feats:
                break
            all_rows.extend([f["attributes"] for f in feats])
            if len(feats) < 2000:
                break
            offset += 2000
            print(f"  lookup offset={offset:>5}  total={len(all_rows):>6}")

        lookup_pdf = pd.DataFrame(all_rows).rename(columns={
            "LSOA21CD": "lsoa_code", "MSOA21CD": "msoa_code",
            "LAD22CD": "lad_code", "LAD22NM": "lad_name",
        }).drop_duplicates(subset=["lsoa_code"])
        print(f"Lookup rows: {len(lookup_pdf):,}")

        spark.createDataFrame(lookup_pdf).write.mode("overwrite").option("overwriteSchema", "true").saveAsTable("varanasi.default.uk_lsoa_to_msoa_lookup")
        spark.sql("ALTER TABLE varanasi.default.uk_lsoa_to_msoa_lookup SET TBLPROPERTIES ('comment' = 'ONS LSOA(2021) -> MSOA(2021) -> LAD(2022) lookup for England & Wales.')")
        """),
        md("""
        ---
        ## 7. Aggregate to monthly counts (LSOA + MSOA)
        """),
        code("""
        spark.sql(\"\"\"
          CREATE OR REPLACE TABLE varanasi.default.uk_crime_monthly_lsoa
          COMMENT 'Per-LSOA monthly crime counts with violent / property split (data.police.uk).'
          AS
          SELECT
            lsoa_code,
            ANY_VALUE(lsoa_name) AS lsoa_name,
            month_start,
            COUNT(*) AS incident_count,
            CAST(SUM(is_violent) AS INT) AS violent_count,
            CAST(SUM(is_property) AS INT) AS property_count
          FROM varanasi.default.uk_crime_raw
          WHERE lsoa_code IS NOT NULL
          GROUP BY lsoa_code, month_start
        \"\"\")
        spark.sql("OPTIMIZE varanasi.default.uk_crime_monthly_lsoa ZORDER BY (lsoa_code, month_start)")
        display(spark.sql("SELECT * FROM varanasi.default.uk_crime_monthly_lsoa LIMIT 10"))
        """),
        code("""
        spark.sql(\"\"\"
          CREATE OR REPLACE TABLE varanasi.default.uk_crime_monthly_msoa
          COMMENT 'Per-MSOA monthly crime counts (rolled up via ONS LSOA->MSOA lookup).'
          AS
          SELECT
            l.msoa_code,
            c.month_start,
            SUM(c.incident_count) AS incident_count,
            SUM(c.violent_count) AS violent_count,
            SUM(c.property_count) AS property_count
          FROM varanasi.default.uk_crime_monthly_lsoa c
          JOIN varanasi.default.uk_lsoa_to_msoa_lookup l
            ON c.lsoa_code = l.lsoa_code
          GROUP BY l.msoa_code, c.month_start
        \"\"\")
        spark.sql("OPTIMIZE varanasi.default.uk_crime_monthly_msoa ZORDER BY (msoa_code, month_start)")
        """),
        md("""
        ---
        ## 7. Data-quality assertions
        """),
        code("""
        n_raw = spark.table("varanasi.default.uk_crime_raw").count()
        n_lookup = spark.table("varanasi.default.uk_lsoa_to_msoa_lookup").count()
        joined = spark.sql(\"\"\"
          SELECT COUNT(*) AS n,
                 SUM(CASE WHEN l.msoa_code IS NULL THEN 0 ELSE 1 END) AS matched
          FROM varanasi.default.uk_crime_raw r
          LEFT JOIN varanasi.default.uk_lsoa_to_msoa_lookup l
            ON r.lsoa_code = l.lsoa_code
          WHERE r.lsoa_code IS NOT NULL
        \"\"\").first()

        match_rate = joined.matched / max(joined.n, 1)
        print(f"Raw crime rows:          {n_raw:,}")
        print(f"Lookup rows:             {n_lookup:,}")
        print(f"LSOA join rate:          {match_rate * 100:.2f}%")

        assert n_raw > 5_000_000, f"Crime row count looks too low ({n_raw:,})"
        assert match_rate > 0.95, f"LSOA join rate too low ({match_rate:.2%})"

        coverage = spark.sql(\"\"\"
          SELECT force, COUNT(DISTINCT month_start) AS n_months
          FROM varanasi.default.uk_crime_raw
          GROUP BY force
        \"\"\").toPandas()
        too_thin = coverage[coverage["n_months"] < 24]
        print(f"\\nForces with <24 months of data: {len(too_thin)}")
        if len(too_thin) > 0:
            print(too_thin)
        # Hard assertion: at least 30 forces should have >=40 months
        assert (coverage["n_months"] >= 40).sum() >= 30, "Coverage check failed"
        print("\\nAll DQ assertions passed.")
        """),
    ]


# ===========================================================================
# 03 — UK panel features + demographics
# ===========================================================================

def nb_03_uk_features() -> list[dict]:
    return [
        md("""
        # CrimeScope ML — 03 (UK). Panel + Features + Demographics

        Joins `uk_crime_monthly_lsoa` / `_msoa` with ONS Census 2021 + IMD 2019 (England)
        + WIMD 2019 (Wales), builds a dense panel (every LSOA × every month with zeros),
        and engineers ~50 features mirroring `crimescope/ml/train.py` so the LightGBM
        recipe transfers directly.

        **Tables written:**
        - `uk_lsoa_demographics` — population, age, deprivation per LSOA
        - `uk_msoa_demographics` — same, per MSOA (population-weighted aggregate)
        - `uk_lsoa_features` — feature table, primary training input
        - `uk_msoa_features` — feature table, MSOA rollup
        """),
        code("""
        spark.sql("USE CATALOG varanasi")
        spark.sql("USE SCHEMA default")
        """),
        md("""
        ---
        ## 1. ONS Census 2021 (Nomis API)

        Pull total population (`TS001`) and population-by-age (`TS007A`) at LSOA level
        for England & Wales. Nomis exposes Census 2021 as table `NM_2021_1` (TS001).
        """),
        code("""
        import io
        import urllib.request
        import urllib.parse
        import pandas as pd

        VOLUME_RAW = "/Volumes/varanasi/default/ml_data_uk/raw"

        # Nomis bulk CSV download — all E&W LSOAs in one shot
        # TS001 is total population by LSOA 2021
        NOMIS_TS001 = (
            "https://www.nomisweb.co.uk/api/v01/dataset/NM_2021_1.bulk.csv?"
            "date=latest&geography=TYPE151&measures=20100"
        )

        def fetch_csv(url: str, dst: str) -> str:
            import os
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            if os.path.exists(dst) and os.path.getsize(dst) > 50_000:
                return dst
            req = urllib.request.Request(url, headers={"User-Agent": "CrimeScope-UK/1.0"})
            with urllib.request.urlopen(req, timeout=300) as resp, open(dst, "wb") as f:
                while True:
                    buf = resp.read(1 << 20)
                    if not buf:
                        break
                    f.write(buf)
            return dst


        ts001 = fetch_csv(NOMIS_TS001, f"{VOLUME_RAW}/census/ts001_population.csv")
        pop_pdf = pd.read_csv(ts001)
        # Nomis returns LSOA code in either GEOGRAPHY_CODE or geography_code
        code_col = next(c for c in pop_pdf.columns if c.lower() == "geography code")
        # OBS_VALUE for total population
        val_col = next(c for c in pop_pdf.columns if "OBS_VALUE" in c.upper() or c.lower() == "observation")
        pop_pdf = pop_pdf[[code_col, val_col]].rename(columns={code_col: "lsoa_code", val_col: "total_pop"})
        pop_pdf = pop_pdf[pop_pdf["lsoa_code"].astype(str).str.startswith(("E0", "W0"))]
        pop_pdf["total_pop"] = pd.to_numeric(pop_pdf["total_pop"], errors="coerce")
        print(f"Population rows: {len(pop_pdf):,}")
        display(pop_pdf.head())
        """),
        md("""
        ---
        ## 2. English IMD 2019 (LSOA, all 7 domains)
        """),
        code("""
        # MHCLG English IMD 2019 — File 7 has all sub-domain ranks + scores by LSOA
        IMD_EN_URL = (
            "https://assets.publishing.service.gov.uk/media/"
            "5d8b3a2540f0b609909b5908/"
            "File_7_-_All_IoD2019_Scores__Ranks__Deciles_and_Population_Denominators_3.xlsx"
        )
        imd_en_path = fetch_csv(IMD_EN_URL, f"{VOLUME_RAW}/imd/imd_en_2019.xlsx")

        imd_en = pd.read_excel(imd_en_path, sheet_name="IoD2019 Scores")
        # The first column is LSOA code 2011 — Census 2021 LSOAs are mostly identical, with ~3% changes
        imd_en.columns = [str(c).strip() for c in imd_en.columns]
        imd_en = imd_en.rename(columns={
            "LSOA code (2011)": "lsoa_code_2011",
            "Index of Multiple Deprivation (IMD) Score": "imd_score",
            "Income Score (rate)": "imd_income",
            "Employment Score (rate)": "imd_employment",
            "Education, Skills and Training Score": "imd_education",
            "Health Deprivation and Disability Score": "imd_health",
            "Crime Score": "imd_crime",
            "Barriers to Housing and Services Score": "imd_housing",
            "Living Environment Score": "imd_environment",
        })
        imd_en_keep = [
            "lsoa_code_2011", "imd_score", "imd_income", "imd_employment",
            "imd_education", "imd_health", "imd_crime", "imd_housing", "imd_environment",
        ]
        imd_en = imd_en[imd_en_keep].copy()
        # National decile (1 = most deprived)
        imd_en["imd_decile"] = pd.qcut(imd_en["imd_score"].rank(method="first"), 10, labels=range(10, 0, -1)).astype(int)
        print(f"English IMD rows: {len(imd_en):,}")
        """),
        md("""
        ---
        ## 3. Welsh IMD 2019 (LSOA-level)

        Wales publishes WIMD 2019 separately on StatsWales (different methodology). We
        normalize each domain to a 0–100 percentile within Wales and assign deciles, so
        downstream feature names match `imd_*`.
        """),
        code("""
        # StatsWales WIMD 2019 LSOA scores (CSV via the open data API)
        WIMD_URL = "https://statswales.gov.wales/Download/File?fileId=605"
        wimd_path = fetch_csv(WIMD_URL, f"{VOLUME_RAW}/imd/wimd_2019.csv")
        try:
            wimd = pd.read_csv(wimd_path, encoding="utf-8")
        except UnicodeDecodeError:
            wimd = pd.read_csv(wimd_path, encoding="latin-1")
        # WIMD ranks domains; convert to 0-100 percentiles to match scale
        rank_cols = [c for c in wimd.columns if "Rank" in c]
        if "LSOA Code" in wimd.columns:
            wimd = wimd.rename(columns={"LSOA Code": "lsoa_code_2011"})

        wimd_norm = pd.DataFrame({"lsoa_code_2011": wimd["lsoa_code_2011"]}) if "lsoa_code_2011" in wimd.columns else pd.DataFrame()
        # Bring in main rank if present
        for cand, target in [
            ("WIMD 2019 Rank", "imd_score"),
            ("Income Rank", "imd_income"),
            ("Employment Rank", "imd_employment"),
            ("Education Rank", "imd_education"),
            ("Health Rank", "imd_health"),
            ("Community Safety Rank", "imd_crime"),
            ("Access to Services Rank", "imd_housing"),
            ("Physical Environment Rank", "imd_environment"),
        ]:
            if cand in wimd.columns and "lsoa_code_2011" in wimd.columns:
                # Convert rank to a 0-100 score (high = more deprived to match English convention)
                ranks = pd.to_numeric(wimd[cand], errors="coerce")
                wimd_norm[target] = (1 - (ranks - 1) / max(ranks.max() - 1, 1)) * 100
        if not wimd_norm.empty:
            wimd_norm["imd_decile"] = pd.qcut(
                wimd_norm["imd_score"].rank(method="first"), 10, labels=range(10, 0, -1)
            ).astype(int)
            print(f"Welsh IMD rows: {len(wimd_norm):,}")
        else:
            print("Welsh IMD parse fell back to empty (CSV schema unexpected); will rely on English IMD only")
            wimd_norm = pd.DataFrame(columns=imd_en.columns)
        """),
        md("""
        ---
        ## 4. Build `uk_lsoa_demographics` (and a population-weighted MSOA rollup)
        """),
        code("""
        imd = pd.concat([imd_en, wimd_norm], ignore_index=True).drop_duplicates("lsoa_code_2011")
        # Census 2021 codes match 2011 LSOA codes for >97% of E&W (boundary changes in 2021)
        demo = pop_pdf.merge(imd, left_on="lsoa_code", right_on="lsoa_code_2011", how="left")
        demo = demo.drop(columns=["lsoa_code_2011"], errors="ignore")
        # Sensible imputation: fill missing IMD with national median so models don't trip on NaNs
        for col in ["imd_score", "imd_income", "imd_employment", "imd_education",
                    "imd_health", "imd_crime", "imd_housing", "imd_environment"]:
            if col in demo.columns:
                demo[col] = demo[col].fillna(demo[col].median())
        if "imd_decile" in demo.columns:
            demo["imd_decile"] = demo["imd_decile"].fillna(5).astype(int)

        spark.createDataFrame(demo).write.mode("overwrite").option("overwriteSchema", "true").saveAsTable("varanasi.default.uk_lsoa_demographics")
        spark.sql("ALTER TABLE varanasi.default.uk_lsoa_demographics SET TBLPROPERTIES ('comment' = 'Per-LSOA demographics: ONS Census 2021 population + IMD/WIMD 2019.')")
        print(f"uk_lsoa_demographics: {len(demo):,} rows")
        """),
        code("""
        # MSOA demographics: population-weighted average over child LSOAs
        spark.sql(\"\"\"
          CREATE OR REPLACE TABLE varanasi.default.uk_msoa_demographics
          COMMENT 'Per-MSOA demographics: pop-weighted aggregate of LSOA demographics.'
          AS
          SELECT
            l.msoa_code,
            SUM(d.total_pop) AS total_pop,
            SUM(d.total_pop * d.imd_score)        / NULLIF(SUM(d.total_pop), 0) AS imd_score,
            SUM(d.total_pop * d.imd_income)       / NULLIF(SUM(d.total_pop), 0) AS imd_income,
            SUM(d.total_pop * d.imd_employment)   / NULLIF(SUM(d.total_pop), 0) AS imd_employment,
            SUM(d.total_pop * d.imd_education)    / NULLIF(SUM(d.total_pop), 0) AS imd_education,
            SUM(d.total_pop * d.imd_health)       / NULLIF(SUM(d.total_pop), 0) AS imd_health,
            SUM(d.total_pop * d.imd_crime)        / NULLIF(SUM(d.total_pop), 0) AS imd_crime,
            SUM(d.total_pop * d.imd_housing)      / NULLIF(SUM(d.total_pop), 0) AS imd_housing,
            SUM(d.total_pop * d.imd_environment)  / NULLIF(SUM(d.total_pop), 0) AS imd_environment,
            CAST(ROUND(SUM(d.total_pop * d.imd_decile) / NULLIF(SUM(d.total_pop), 0)) AS INT) AS imd_decile
          FROM varanasi.default.uk_lsoa_demographics d
          JOIN varanasi.default.uk_lsoa_to_msoa_lookup l
            ON d.lsoa_code = l.lsoa_code
          GROUP BY l.msoa_code
        \"\"\")
        """),
        md("""
        ---
        ## 5. Dense panel + features (LSOA)

        Mirrors `crimescope/ml/train.py` `engineer_features`: lags 1/2/3/6/12, rolling
        3/6/12 (mean/std/max/min), MoM/YoY, violent/property sub-features, calendar
        encoding, demographics, force-wide and MSOA-wide context.
        """),
        code("""
        import math
        import numpy as np

        monthly = spark.table("varanasi.default.uk_crime_monthly_lsoa").toPandas()
        demo_pdf = spark.table("varanasi.default.uk_lsoa_demographics").toPandas()
        lookup_pdf = spark.table("varanasi.default.uk_lsoa_to_msoa_lookup").toPandas()

        all_lsoa = demo_pdf["lsoa_code"].unique()
        all_months = pd.date_range(monthly["month_start"].min(), monthly["month_start"].max(), freq="MS")

        idx = pd.MultiIndex.from_product([all_lsoa, all_months], names=["lsoa_code", "month_start"])
        panel = pd.DataFrame(index=idx).reset_index()
        panel["month_start"] = panel["month_start"].dt.date
        panel = panel.merge(monthly, on=["lsoa_code", "month_start"], how="left")
        for c in ["incident_count", "violent_count", "property_count"]:
            panel[c] = panel[c].fillna(0).astype(int)
        panel = panel.merge(lookup_pdf[["lsoa_code", "msoa_code", "lad_code"]], on="lsoa_code", how="left")
        panel = panel.sort_values(["lsoa_code", "month_start"]).reset_index(drop=True)

        # Labels (next-30-day = next month)
        g = panel.groupby("lsoa_code")
        panel["y_next_30d_count"] = g["incident_count"].shift(-1)
        panel["y_next_30d_violent"] = g["violent_count"].shift(-1)
        panel["y_next_30d_property"] = g["property_count"].shift(-1)
        panel["y_incidents_12m"] = g["incident_count"].transform(lambda x: x.rolling(12, min_periods=1).sum())
        panel["y_violent_12m"] = g["violent_count"].transform(lambda x: x.rolling(12, min_periods=1).sum())
        panel["y_property_12m"] = g["property_count"].transform(lambda x: x.rolling(12, min_periods=1).sum())
        panel = panel.dropna(subset=["y_next_30d_count"])
        for c in ["y_next_30d_count", "y_next_30d_violent", "y_next_30d_property"]:
            panel[c] = panel[c].astype(int)

        # Maturity buffer — drop the most recent 2 months
        panel["month_dt"] = pd.to_datetime(panel["month_start"])
        cutoff = panel["month_dt"].max() - pd.DateOffset(months=2)
        panel = panel[panel["month_dt"] <= cutoff].drop(columns=["month_dt"])
        print(f"Panel: {len(panel):,} rows, {panel['lsoa_code'].nunique()} LSOAs, {panel['month_start'].nunique()} months")
        """),
        code("""
        df = panel.copy()
        df = df.sort_values(["lsoa_code", "month_start"]).reset_index(drop=True)
        g  = df.groupby("lsoa_code")["incident_count"]
        gv = df.groupby("lsoa_code")["violent_count"]
        gp = df.groupby("lsoa_code")["property_count"]

        for lag in [1, 2, 3, 6, 12]:
            df[f"lag_{lag}m_count"] = g.shift(lag)
        for period in [3, 6, 12]:
            df[f"rolling_mean_{period}m"] = g.transform(lambda x: x.shift(1).rolling(period, min_periods=1).mean())
            if period >= 6:
                df[f"rolling_std_{period}m"] = g.transform(lambda x: x.shift(1).rolling(period, min_periods=1).std())
                df[f"rolling_max_{period}m"] = g.transform(lambda x: x.shift(1).rolling(period, min_periods=1).max())
                df[f"rolling_min_{period}m"] = g.transform(lambda x: x.shift(1).rolling(period, min_periods=1).min())
        df["mom_change"] = df["incident_count"] - g.shift(1)

        for crime_type, grp in [("violent", gv), ("property", gp)]:
            for lag in [1, 3, 6]:
                df[f"{crime_type}_lag_{lag}m"] = grp.shift(lag)
            for period in [3, 6, 12]:
                df[f"{crime_type}_rolling_{period}m"] = grp.transform(
                    lambda x: x.shift(1).rolling(period, min_periods=1).mean()
                )

        df["violent_ratio"] = np.where(df["incident_count"] > 0, df["violent_count"] / df["incident_count"], 0.0)
        df["violent_ratio_6m"] = df.groupby("lsoa_code")["violent_ratio"].transform(
            lambda x: x.shift(1).rolling(6, min_periods=1).mean()
        )

        # Calendar
        dt = pd.to_datetime(df["month_start"])
        df["month_of_year"] = dt.dt.month
        df["month_sin"] = np.sin(2 * math.pi * df["month_of_year"] / 12)
        df["month_cos"] = np.cos(2 * math.pi * df["month_of_year"] / 12)
        df["year"] = dt.dt.year
        df["same_month_last_year"] = g.shift(12)
        df["yoy_change"] = np.where(df["same_month_last_year"].notna(), df["incident_count"] - df["same_month_last_year"], np.nan)

        # Demographics
        df = df.merge(demo_pdf, on="lsoa_code", how="left")
        df["log_pop"] = np.where(df["total_pop"] > 0, np.log(df["total_pop"]), 0.0)

        rm12 = df["rolling_mean_12m"].fillna(0)
        df["crime_rate_per_1k"] = np.where((df["total_pop"] > 0) & (rm12 > 0), rm12 / (df["total_pop"] / 1000.0), 0.0)
        df["imd_x_crime"] = df["imd_score"].fillna(0) * rm12

        # MSOA-wide context
        msoa_avg = df.groupby(["msoa_code", "month_start"])["incident_count"].transform("mean")
        df["msoa_avg_crime"] = msoa_avg.fillna(df["incident_count"])
        df["lsoa_vs_msoa_avg"] = np.where(df["msoa_avg_crime"] > 0, df["incident_count"] / df["msoa_avg_crime"], 1.0)

        # Force-wide context (LAD as proxy — the per-force allocation maps loosely to LADs)
        lad_total = df.groupby(["lad_code", "month_start"])["incident_count"].transform("sum")
        df["lad_month_total"] = lad_total
        df["lsoa_share_of_lad"] = np.where(lad_total > 0, df["incident_count"] / lad_total, 0.0)

        # Trend / volatility
        rm6 = df["rolling_mean_6m"].fillna(0)
        std6 = df["rolling_std_6m"].fillna(0)
        std12 = df["rolling_std_12m"].fillna(0)
        df["cv_6m"] = np.where(rm6 > 0, std6 / rm6, 0.0)
        df["cv_12m"] = np.where(rm12 > 0, std12 / rm12, 0.0)
        df["trend_3m"] = np.where(
            (rm6 > 0) & (df["rolling_mean_3m"].notna()),
            (df["rolling_mean_3m"].fillna(0) - rm6) / rm6, 0.0
        )

        print(f"Feature columns: {len(df.columns)}")
        df.head()
        """),
        code("""
        # Persist the LSOA feature table
        spark_df = spark.createDataFrame(df)
        spark_df.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable("varanasi.default.uk_lsoa_features")
        spark.sql("ALTER TABLE varanasi.default.uk_lsoa_features SET TBLPROPERTIES ('comment' = 'LSOA panel + ~50 features for CrimeScope UK risk model.')")
        spark.sql("OPTIMIZE varanasi.default.uk_lsoa_features ZORDER BY (lsoa_code, month_start)")
        print(f"uk_lsoa_features: {len(df):,} rows × {len(df.columns)} cols")
        """),
        md("""
        ---
        ## 6. MSOA feature table (rollup)
        """),
        code("""
        msoa_monthly = spark.table("varanasi.default.uk_crime_monthly_msoa").toPandas()
        msoa_demo = spark.table("varanasi.default.uk_msoa_demographics").toPandas()
        all_msoa = msoa_demo["msoa_code"].unique()
        all_months = pd.date_range(msoa_monthly["month_start"].min(), msoa_monthly["month_start"].max(), freq="MS")
        idx = pd.MultiIndex.from_product([all_msoa, all_months], names=["msoa_code", "month_start"])
        m = pd.DataFrame(index=idx).reset_index()
        m["month_start"] = m["month_start"].dt.date
        m = m.merge(msoa_monthly, on=["msoa_code", "month_start"], how="left")
        for c in ["incident_count", "violent_count", "property_count"]:
            m[c] = m[c].fillna(0).astype(int)
        m = m.sort_values(["msoa_code", "month_start"]).reset_index(drop=True)

        gM  = m.groupby("msoa_code")["incident_count"]
        gMV = m.groupby("msoa_code")["violent_count"]
        gMP = m.groupby("msoa_code")["property_count"]
        m["y_next_30d_count"] = gM.shift(-1)
        m["y_next_30d_violent"] = gMV.shift(-1)
        m["y_next_30d_property"] = gMP.shift(-1)
        m["y_incidents_12m"] = gM.transform(lambda x: x.rolling(12, min_periods=1).sum())
        m = m.dropna(subset=["y_next_30d_count"])
        for c in ["y_next_30d_count", "y_next_30d_violent", "y_next_30d_property"]:
            m[c] = m[c].astype(int)

        for lag in [1, 2, 3, 6, 12]:
            m[f"lag_{lag}m_count"] = gM.shift(lag)
        for period in [3, 6, 12]:
            m[f"rolling_mean_{period}m"] = gM.transform(lambda x: x.shift(1).rolling(period, min_periods=1).mean())
            if period >= 6:
                m[f"rolling_std_{period}m"] = gM.transform(lambda x: x.shift(1).rolling(period, min_periods=1).std())
                m[f"rolling_max_{period}m"] = gM.transform(lambda x: x.shift(1).rolling(period, min_periods=1).max())
                m[f"rolling_min_{period}m"] = gM.transform(lambda x: x.shift(1).rolling(period, min_periods=1).min())
        m["mom_change"] = m["incident_count"] - gM.shift(1)
        for crime_type, grp in [("violent", gMV), ("property", gMP)]:
            for lag in [1, 3, 6]:
                m[f"{crime_type}_lag_{lag}m"] = grp.shift(lag)
            for period in [3, 6, 12]:
                m[f"{crime_type}_rolling_{period}m"] = grp.transform(
                    lambda x: x.shift(1).rolling(period, min_periods=1).mean()
                )
        m["violent_ratio"] = np.where(m["incident_count"] > 0, m["violent_count"] / m["incident_count"], 0.0)
        m["violent_ratio_6m"] = m.groupby("msoa_code")["violent_ratio"].transform(
            lambda x: x.shift(1).rolling(6, min_periods=1).mean()
        )
        dt = pd.to_datetime(m["month_start"])
        m["month_of_year"] = dt.dt.month
        m["month_sin"] = np.sin(2 * math.pi * m["month_of_year"] / 12)
        m["month_cos"] = np.cos(2 * math.pi * m["month_of_year"] / 12)
        m["year"] = dt.dt.year
        m["same_month_last_year"] = gM.shift(12)
        m["yoy_change"] = np.where(m["same_month_last_year"].notna(), m["incident_count"] - m["same_month_last_year"], np.nan)
        m = m.merge(msoa_demo, on="msoa_code", how="left")
        m["log_pop"] = np.where(m["total_pop"] > 0, np.log(m["total_pop"]), 0.0)
        rm12 = m["rolling_mean_12m"].fillna(0)
        m["crime_rate_per_1k"] = np.where((m["total_pop"] > 0) & (rm12 > 0), rm12 / (m["total_pop"] / 1000.0), 0.0)
        m["imd_x_crime"] = m["imd_score"].fillna(0) * rm12
        rm6 = m["rolling_mean_6m"].fillna(0)
        std6 = m["rolling_std_6m"].fillna(0); std12 = m["rolling_std_12m"].fillna(0)
        m["cv_6m"] = np.where(rm6 > 0, std6 / rm6, 0.0)
        m["cv_12m"] = np.where(rm12 > 0, std12 / rm12, 0.0)
        m["trend_3m"] = np.where(
            (rm6 > 0) & (m["rolling_mean_3m"].notna()),
            (m["rolling_mean_3m"].fillna(0) - rm6) / rm6, 0.0
        )

        spark.createDataFrame(m).write.mode("overwrite").option("overwriteSchema", "true").saveAsTable("varanasi.default.uk_msoa_features")
        spark.sql("ALTER TABLE varanasi.default.uk_msoa_features SET TBLPROPERTIES ('comment' = 'MSOA panel + features for CrimeScope UK risk model.')")
        spark.sql("OPTIMIZE varanasi.default.uk_msoa_features ZORDER BY (msoa_code, month_start)")
        print(f"uk_msoa_features: {len(m):,} rows × {len(m.columns)} cols")
        """),
    ]


# ===========================================================================
# 04 — Train + evaluate (LSOA + MSOA) with MLflow + UC Model Registry
# ===========================================================================

def nb_04_uk_train() -> list[dict]:
    return [
        md("""
        # CrimeScope ML — 04 (UK). Train & Evaluate

        Trains LightGBM ensembles (log1p + sqrt) for both **LSOA** (primary) and
        **MSOA** (rollup) levels, plus violent / property sub-models. Optuna-tuned
        (20 trials each), MLflow-tracked, registered to UC Model Registry with a
        `@champion` alias on the best run.
        """),
        code("""
        spark.sql("USE CATALOG varanasi")
        spark.sql("USE SCHEMA default")
        """),
        code("""
        %pip install -q optuna shap lightgbm
        dbutils.library.restartPython()
        """),
        code("""
        import json
        import math
        import numpy as np
        import pandas as pd
        import lightgbm as lgb
        import optuna
        import mlflow
        import mlflow.lightgbm
        from mlflow.models.signature import infer_signature
        from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

        optuna.logging.set_verbosity(optuna.logging.WARNING)
        mlflow.set_registry_uri("databricks-uc")
        mlflow.set_experiment("/Shared/Team_varanasi/crimescope_uk")
        """),
        md("""
        ---
        ## Feature column list (mirrors `crimescope/ml/train.py`)
        """),
        code("""
        FEATURE_COLS = [
            "lag_1m_count", "lag_2m_count", "lag_3m_count", "lag_6m_count", "lag_12m_count",
            "rolling_mean_3m", "rolling_mean_6m", "rolling_mean_12m",
            "rolling_std_6m", "rolling_max_6m", "rolling_min_6m",
            "rolling_std_12m", "rolling_max_12m", "rolling_min_12m",
            "mom_change",
            "violent_lag_1m", "violent_lag_3m", "violent_lag_6m",
            "violent_rolling_3m", "violent_rolling_6m", "violent_rolling_12m",
            "violent_ratio", "violent_ratio_6m",
            "property_lag_1m", "property_lag_3m", "property_lag_6m",
            "property_rolling_3m", "property_rolling_6m", "property_rolling_12m",
            "month_of_year", "month_sin", "month_cos", "year",
            "same_month_last_year", "yoy_change",
            "total_pop", "log_pop",
            "imd_score", "imd_income", "imd_employment", "imd_education",
            "imd_health", "imd_crime", "imd_housing", "imd_environment", "imd_decile",
            "crime_rate_per_1k", "imd_x_crime",
            "cv_6m", "cv_12m", "trend_3m",
        ]
        # MSOA features lack the LAD/MSOA-context columns specific to the LSOA grain
        FEATURE_COLS_MSOA = [c for c in FEATURE_COLS]

        TARGET = "y_next_30d_count"
        """),
        md("""
        ---
        ## Helpers
        """),
        code("""
        def calc_metrics(y_true, y_pred):
            return (
                mean_absolute_error(y_true, y_pred),
                float(np.sqrt(mean_squared_error(y_true, y_pred))),
                r2_score(y_true, y_pred),
            )


        def weighted_baseline(X):
            return np.maximum((
                0.30 * X["rolling_mean_3m"].fillna(0) +
                0.25 * X["rolling_mean_12m"].fillna(0) +
                0.20 * X["lag_1m_count"].fillna(0) +
                0.15 * X["same_month_last_year"].fillna(X["rolling_mean_12m"].fillna(0)) +
                0.10 * X["lag_3m_count"].fillna(0)
            ).values, 0)


        def split_train_test(df, id_col, target_col, feat_cols, test_months=6):
            df = df.dropna(subset=[target_col])
            for c in feat_cols:
                if c in df.columns:
                    df[c] = df[c].fillna(0.0)
            dt = pd.to_datetime(df["month_start"])
            cutoff = (dt.max() - pd.DateOffset(months=test_months - 1)).replace(day=1)
            tr = df[dt < cutoff]
            te = df[dt >= cutoff]
            return tr, te, cutoff


        def tune_lightgbm(X_train, y_train, X_test, y_test, n_trials=20):
            weights = np.log1p(y_train) + 1.0
            def obj(trial):
                p = {
                    "objective": "regression", "metric": "rmse", "verbosity": -1,
                    "random_state": 42, "n_estimators": 500,
                    "num_leaves": trial.suggest_int("num_leaves", 31, 127),
                    "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.1, log=True),
                    "min_child_samples": trial.suggest_int("min_child_samples", 10, 50),
                    "subsample": trial.suggest_float("subsample", 0.6, 1.0),
                    "colsample_bytree": trial.suggest_float("colsample_bytree", 0.5, 1.0),
                    "reg_alpha": trial.suggest_float("reg_alpha", 1e-3, 10.0, log=True),
                    "reg_lambda": trial.suggest_float("reg_lambda", 1e-3, 10.0, log=True),
                }
                m = lgb.LGBMRegressor(**p)
                m.fit(
                    X_train, np.log1p(y_train), sample_weight=weights,
                    eval_set=[(X_test, np.log1p(y_test))],
                    callbacks=[lgb.early_stopping(30, verbose=False)],
                )
                pred = np.maximum(np.expm1(np.maximum(m.predict(X_test), 0)), 0)
                return mean_absolute_error(y_test, pred)
            study = optuna.create_study(direction="minimize")
            study.optimize(obj, n_trials=n_trials, show_progress_bar=False)
            return study.best_params


        def train_ensemble(X_train, y_train, X_test, y_test, params):
            base = {"objective": "regression", "metric": "rmse", "verbosity": -1,
                    "random_state": 42, "n_estimators": 500, **params}
            weights = np.log1p(y_train) + 1.0
            m_log = lgb.LGBMRegressor(**base)
            m_log.fit(X_train, np.log1p(y_train), sample_weight=weights,
                      eval_set=[(X_test, np.log1p(y_test))],
                      callbacks=[lgb.early_stopping(50, verbose=False)])
            m_sqrt = lgb.LGBMRegressor(**base)
            m_sqrt.fit(X_train, np.sqrt(y_train), sample_weight=weights,
                       eval_set=[(X_test, np.sqrt(y_test))],
                       callbacks=[lgb.early_stopping(50, verbose=False)])
            return m_log, m_sqrt


        def evaluate_ensemble(m_log, m_sqrt, X_test, y_test):
            p_log = np.maximum(np.expm1(np.maximum(m_log.predict(X_test), 0)), 0)
            p_sqrt = np.maximum(np.square(np.maximum(m_sqrt.predict(X_test), 0)), 0)
            p_ens = 0.5 * p_log + 0.5 * p_sqrt
            mae_log, rmse_log, r2_log = calc_metrics(y_test, p_log)
            mae_sqrt, rmse_sqrt, r2_sqrt = calc_metrics(y_test, p_sqrt)
            mae_ens, rmse_ens, r2_ens = calc_metrics(y_test, p_ens)
            results = {
                "log":   {"pred": p_log,  "mae": mae_log,  "rmse": rmse_log,  "r2": r2_log},
                "sqrt":  {"pred": p_sqrt, "mae": mae_sqrt, "rmse": rmse_sqrt, "r2": r2_sqrt},
                "ensemble": {"pred": p_ens, "mae": mae_ens, "rmse": rmse_ens, "r2": r2_ens},
            }
            best = min(results.items(), key=lambda kv: kv[1]["mae"])[0]
            return results, best
        """),
        md("""
        ---
        ## Train LSOA model
        """),
        code("""
        feat_lsoa = spark.table("varanasi.default.uk_lsoa_features").toPandas()
        feat_lsoa = feat_lsoa.dropna(subset=["lag_1m_count"])
        for c in FEATURE_COLS:
            if c in feat_lsoa.columns:
                feat_lsoa[c] = feat_lsoa[c].fillna(0.0)
        present_features = [c for c in FEATURE_COLS if c in feat_lsoa.columns]
        print(f"LSOA features available: {len(present_features)} / {len(FEATURE_COLS)}")

        tr, te, cutoff = split_train_test(feat_lsoa, "lsoa_code", TARGET, present_features, test_months=6)
        X_tr, y_tr = tr[present_features].astype(float), tr[TARGET].astype(float)
        X_te, y_te = te[present_features].astype(float), te[TARGET].astype(float)
        baseline_pred = weighted_baseline(X_te)
        b_mae, b_rmse, b_r2 = calc_metrics(y_te, baseline_pred)
        print(f"LSOA train={len(X_tr):,}  test={len(X_te):,}  test_start={cutoff.date()}  baseline MAE={b_mae:.3f}")
        """),
        code("""
        with mlflow.start_run(run_name=f"lsoa_lgbm_ensemble_{cutoff.date()}") as run:
            best_params = tune_lightgbm(X_tr, y_tr, X_te, y_te, n_trials=20)
            mlflow.log_params(best_params)
            m_log, m_sqrt = train_ensemble(X_tr, y_tr, X_te, y_te, best_params)
            results, best = evaluate_ensemble(m_log, m_sqrt, X_te, y_te)
            for k, v in results.items():
                for metric in ("mae", "rmse", "r2"):
                    mlflow.log_metric(f"{k}_{metric}", v[metric])
            mlflow.log_metric("baseline_mae", b_mae)
            mlflow.log_metric("baseline_rmse", b_rmse)
            mlflow.log_metric("baseline_r2", b_r2)
            mlflow.log_param("ensemble_strategy", best)
            mlflow.log_param("grain", "lsoa")
            mlflow.log_param("features", json.dumps(present_features))
            sig = infer_signature(X_te.head(20), results[best]["pred"][:20])
            mlflow.lightgbm.log_model(m_log, "model_log", signature=sig)
            mlflow.lightgbm.log_model(m_sqrt, "model_sqrt", signature=sig)
            run_id = run.info.run_id
            print(f"LSOA best={best} mae={results[best]['mae']:.3f} r2={results[best]['r2']:.3f}")

        client = mlflow.MlflowClient()
        model_uri = f"runs:/{run_id}/model_log"
        registered = mlflow.register_model(model_uri, "varanasi.default.crimescope_uk_risk_model_lsoa")
        client.set_registered_model_alias(
            "varanasi.default.crimescope_uk_risk_model_lsoa", "champion", registered.version
        )
        print(f"Registered LSOA model v{registered.version} as @champion")
        """),
        md("""
        ---
        ## Train violent + property sub-models (LSOA, pruned features)
        """),
        code("""
        # Drop bottom-25% importance features
        imp = pd.Series(m_log.feature_importances_, index=present_features).sort_values(ascending=False)
        keep = imp[imp > imp.quantile(0.25)].index.tolist()

        for sub_target in ["y_next_30d_violent", "y_next_30d_property"]:
            sub_df = feat_lsoa.dropna(subset=[sub_target])
            tr2, te2, _ = split_train_test(sub_df, "lsoa_code", sub_target, keep, test_months=6)
            X_tr2 = tr2[keep].astype(float); y_tr2 = tr2[sub_target].astype(float)
            X_te2 = te2[keep].astype(float); y_te2 = te2[sub_target].astype(float)
            with mlflow.start_run(run_name=f"lsoa_{sub_target}", nested=True):
                params = tune_lightgbm(X_tr2, y_tr2, X_te2, y_te2, n_trials=10)
                m_sub_log, _ = train_ensemble(X_tr2, y_tr2, X_te2, y_te2, params)
                pred = np.maximum(np.expm1(np.maximum(m_sub_log.predict(X_te2), 0)), 0)
                mae, rmse, r2 = calc_metrics(y_te2, pred)
                mlflow.log_metric("mae", mae); mlflow.log_metric("r2", r2)
                mlflow.lightgbm.log_model(m_sub_log, "model")
                model_name = "varanasi.default.crimescope_uk_risk_model_" + sub_target.replace("y_next_30d_", "")
                reg = mlflow.register_model(f"runs:/{mlflow.active_run().info.run_id}/model", model_name)
                client.set_registered_model_alias(model_name, "champion", reg.version)
                print(f"  {sub_target}: MAE={mae:.3f} R2={r2:.3f}, registered v{reg.version}")
        """),
        md("""
        ---
        ## Train MSOA model
        """),
        code("""
        feat_msoa = spark.table("varanasi.default.uk_msoa_features").toPandas()
        feat_msoa = feat_msoa.dropna(subset=["lag_1m_count"])
        for c in FEATURE_COLS_MSOA:
            if c in feat_msoa.columns:
                feat_msoa[c] = feat_msoa[c].fillna(0.0)
        present_msoa = [c for c in FEATURE_COLS_MSOA if c in feat_msoa.columns]

        tr, te, cutoff = split_train_test(feat_msoa, "msoa_code", TARGET, present_msoa, test_months=6)
        X_tr, y_tr = tr[present_msoa].astype(float), tr[TARGET].astype(float)
        X_te, y_te = te[present_msoa].astype(float), te[TARGET].astype(float)
        b_mae, b_rmse, b_r2 = calc_metrics(y_te, weighted_baseline(X_te))
        print(f"MSOA train={len(X_tr):,}  test={len(X_te):,}  baseline MAE={b_mae:.3f}")

        with mlflow.start_run(run_name=f"msoa_lgbm_ensemble_{cutoff.date()}") as run:
            best_params = tune_lightgbm(X_tr, y_tr, X_te, y_te, n_trials=20)
            mlflow.log_params(best_params)
            mlflow.log_param("grain", "msoa")
            m_log_msoa, m_sqrt_msoa = train_ensemble(X_tr, y_tr, X_te, y_te, best_params)
            results, best = evaluate_ensemble(m_log_msoa, m_sqrt_msoa, X_te, y_te)
            for k, v in results.items():
                for metric in ("mae", "rmse", "r2"):
                    mlflow.log_metric(f"{k}_{metric}", v[metric])
            mlflow.log_metric("baseline_mae", b_mae)
            mlflow.log_param("ensemble_strategy", best)
            sig = infer_signature(X_te.head(20), results[best]["pred"][:20])
            mlflow.lightgbm.log_model(m_log_msoa, "model_log", signature=sig)
            mlflow.lightgbm.log_model(m_sqrt_msoa, "model_sqrt", signature=sig)
            run_id_m = run.info.run_id
            print(f"MSOA best={best} mae={results[best]['mae']:.3f} r2={results[best]['r2']:.3f}")

        registered = mlflow.register_model(
            f"runs:/{run_id_m}/model_log",
            "varanasi.default.crimescope_uk_risk_model_msoa",
        )
        client.set_registered_model_alias(
            "varanasi.default.crimescope_uk_risk_model_msoa", "champion", registered.version
        )
        print(f"Registered MSOA model v{registered.version} as @champion")
        """),
    ]


# ===========================================================================
# 05 — Score & serve
# ===========================================================================

def nb_05_uk_score() -> list[dict]:
    return [
        md("""
        # CrimeScope ML — 05 (UK). Score & Serve

        Loads `@champion` models from UC, scores every LSOA + MSOA for the latest
        mature month, computes blended 0–100 risk scores + tiers, and writes Delta
        tables consumed by notebook `06`.
        """),
        code("""
        spark.sql("USE CATALOG varanasi")
        spark.sql("USE SCHEMA default")
        """),
        code("""
        %pip install -q shap lightgbm
        dbutils.library.restartPython()
        """),
        code("""
        import json
        import numpy as np
        import pandas as pd
        import mlflow
        import mlflow.lightgbm
        import shap
        from datetime import datetime, timezone
        from scipy.stats import percentileofscore

        mlflow.set_registry_uri("databricks-uc")

        FEATURE_LABELS = {
            "lag_1m_count": "Last month's crime count",
            "rolling_mean_3m": "3-month crime average",
            "rolling_mean_12m": "12-month crime average",
            "rolling_std_6m": "6-month crime volatility",
            "violent_ratio": "Violent crime proportion",
            "violent_ratio_6m": "6-month violent ratio",
            "imd_score": "Index of Multiple Deprivation",
            "imd_decile": "IMD decile (1=most deprived)",
            "log_pop": "Population (log scale)",
            "crime_rate_per_1k": "Crime rate per 1,000 residents",
            "month_of_year": "Month of year (seasonality)",
            "same_month_last_year": "Same month last year",
            "yoy_change": "Year-over-year change",
            "trend_3m": "3-month trend direction",
        }


        def blended_score(p):
            pct = np.array([percentileofscore(p, v, kind="rank") for v in p])
            log_p = np.log1p(p)
            lo, hi = log_p.min(), log_p.max()
            abs_s = (log_p - lo) / (hi - lo) * 100 if hi > lo else np.full_like(log_p, 50.0)
            return np.round(0.7 * pct + 0.3 * abs_s, 1)


        def to_tier(s):
            return pd.cut(s, bins=[-0.1, 25, 50, 75, 90, 100],
                          labels=["Low", "Moderate", "Elevated", "High", "Critical"]).astype(str)


        def top_drivers_json(shap_row, feat_names, feat_vals, n=5):
            idxs = np.abs(shap_row).argsort()[-n:][::-1]
            return json.dumps([
                {
                    "feature": feat_names[i],
                    "label": FEATURE_LABELS.get(feat_names[i], feat_names[i].replace("_", " ").title()),
                    "shap_value": round(float(shap_row[i]), 4),
                    "feature_value": round(float(feat_vals[i]), 4),
                    "direction": "up" if shap_row[i] > 0 else "down",
                } for i in idxs
            ])
        """),
        md("""
        ---
        ## Score LSOA
        """),
        code("""
        model_lsoa = mlflow.lightgbm.load_model("models:/varanasi.default.crimescope_uk_risk_model_lsoa@champion")
        try:
            model_lsoa_v = mlflow.lightgbm.load_model("models:/varanasi.default.crimescope_uk_risk_model_violent@champion")
        except Exception:
            model_lsoa_v = None
        try:
            model_lsoa_p = mlflow.lightgbm.load_model("models:/varanasi.default.crimescope_uk_risk_model_property@champion")
        except Exception:
            model_lsoa_p = None

        feat = spark.table("varanasi.default.uk_lsoa_features").toPandas()
        feat = feat.dropna(subset=["lag_1m_count"])
        feat["month_dt"] = pd.to_datetime(feat["month_start"])
        latest_month = feat["month_dt"].max()
        latest = feat[feat["month_dt"] == latest_month].copy()

        feature_cols = list(model_lsoa.booster_.feature_name())
        for c in feature_cols:
            if c not in latest.columns:
                latest[c] = 0.0
        X_latest = latest[feature_cols].astype(float).fillna(0.0)

        pred = np.maximum(np.expm1(np.maximum(model_lsoa.predict(X_latest), 0)), 0)
        latest["predicted_next_30d"] = pred.round(2)
        latest["risk_score"] = blended_score(pred)
        latest["risk_tier"] = to_tier(latest["risk_score"])
        latest["scored_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
        latest["model_version"] = "uk_lsoa_lgbm_ensemble_v1"

        if model_lsoa_v is not None:
            sub_feats_v = list(model_lsoa_v.booster_.feature_name())
            for c in sub_feats_v:
                if c not in latest.columns:
                    latest[c] = 0.0
            pv = np.maximum(np.expm1(np.maximum(model_lsoa_v.predict(latest[sub_feats_v].astype(float).fillna(0.0)), 0)), 0)
            latest["predicted_violent_30d"] = pv.round(2)
            latest["violent_score"] = blended_score(pv)
        else:
            latest["predicted_violent_30d"] = (latest["predicted_next_30d"] * 0.3).round(2)
            latest["violent_score"] = blended_score(latest["predicted_violent_30d"].values)

        if model_lsoa_p is not None:
            sub_feats_p = list(model_lsoa_p.booster_.feature_name())
            for c in sub_feats_p:
                if c not in latest.columns:
                    latest[c] = 0.0
            pp = np.maximum(np.expm1(np.maximum(model_lsoa_p.predict(latest[sub_feats_p].astype(float).fillna(0.0)), 0)), 0)
            latest["predicted_property_30d"] = pp.round(2)
            latest["property_score"] = blended_score(pp)
        else:
            latest["predicted_property_30d"] = (latest["predicted_next_30d"] * 0.5).round(2)
            latest["property_score"] = blended_score(latest["predicted_property_30d"].values)

        baseline = (
            0.30 * latest["rolling_mean_3m"].fillna(0)
            + 0.25 * latest["rolling_mean_12m"].fillna(0)
            + 0.20 * latest["lag_1m_count"].fillna(0)
            + 0.15 * latest["same_month_last_year"].fillna(latest["rolling_mean_12m"].fillna(0))
            + 0.10 * latest["lag_3m_count"].fillna(0)
        ).clip(lower=0)
        latest["baseline_predicted"] = baseline.round(2)
        latest["model_vs_baseline"] = (
            (latest["predicted_next_30d"] - latest["baseline_predicted"]) /
            latest["baseline_predicted"].clip(lower=0.1)
        ).round(3)
        latest["trend_direction"] = np.where(
            latest["predicted_next_30d"] > latest["lag_1m_count"] * 1.05, "rising",
            np.where(latest["predicted_next_30d"] < latest["lag_1m_count"] * 0.95, "falling", "stable")
        )

        # SHAP top drivers
        explainer = shap.TreeExplainer(model_lsoa)
        shap_vals = explainer.shap_values(X_latest)
        latest["top_drivers_json"] = [
            top_drivers_json(shap_vals[i], feature_cols, X_latest.iloc[i].values)
            for i in range(len(shap_vals))
        ]
        # Map LSOA fields to the existing backend contract names
        latest["tract_geoid"] = latest["lsoa_code"]
        latest["NAMELSAD"] = latest["lsoa_code"]  # name is supplied via boundaries table

        cols = [
            "tract_geoid", "NAMELSAD", "risk_score", "risk_tier",
            "predicted_next_30d", "predicted_violent_30d", "predicted_property_30d",
            "violent_score", "property_score",
            "incident_count", "y_incidents_12m", "trend_direction",
            "model_vs_baseline", "baseline_predicted", "top_drivers_json",
            "total_pop", "imd_score", "imd_decile",
            "scored_at", "model_version",
        ]
        out = latest[[c for c in cols if c in latest.columns]]
        spark.createDataFrame(out).write.mode("overwrite").option("overwriteSchema", "true").saveAsTable("varanasi.default.uk_lsoa_risk_scores")
        spark.sql("ALTER TABLE varanasi.default.uk_lsoa_risk_scores SET TBLPROPERTIES ('comment' = 'Latest per-LSOA risk scores + SHAP drivers (CrimeScope UK).')")
        print(f"Wrote {len(out):,} LSOA scores for {latest_month.date()}")
        """),
        md("""
        ---
        ## Score MSOA
        """),
        code("""
        model_msoa = mlflow.lightgbm.load_model("models:/varanasi.default.crimescope_uk_risk_model_msoa@champion")

        featM = spark.table("varanasi.default.uk_msoa_features").toPandas()
        featM = featM.dropna(subset=["lag_1m_count"])
        featM["month_dt"] = pd.to_datetime(featM["month_start"])
        latestM = featM[featM["month_dt"] == featM["month_dt"].max()].copy()

        feat_cols_m = list(model_msoa.booster_.feature_name())
        for c in feat_cols_m:
            if c not in latestM.columns:
                latestM[c] = 0.0
        XM = latestM[feat_cols_m].astype(float).fillna(0.0)
        predM = np.maximum(np.expm1(np.maximum(model_msoa.predict(XM), 0)), 0)
        latestM["predicted_next_30d"] = predM.round(2)
        latestM["risk_score"] = blended_score(predM)
        latestM["risk_tier"] = to_tier(latestM["risk_score"])
        # Synthetic split for sub-scores until MSOA sub-models trained
        latestM["predicted_violent_30d"] = (latestM["predicted_next_30d"] * 0.30).round(2)
        latestM["predicted_property_30d"] = (latestM["predicted_next_30d"] * 0.50).round(2)
        latestM["violent_score"] = blended_score(latestM["predicted_violent_30d"].values)
        latestM["property_score"] = blended_score(latestM["predicted_property_30d"].values)
        baseline = (
            0.30 * latestM["rolling_mean_3m"].fillna(0)
            + 0.25 * latestM["rolling_mean_12m"].fillna(0)
            + 0.20 * latestM["lag_1m_count"].fillna(0)
            + 0.15 * latestM["same_month_last_year"].fillna(latestM["rolling_mean_12m"].fillna(0))
            + 0.10 * latestM["lag_3m_count"].fillna(0)
        ).clip(lower=0)
        latestM["baseline_predicted"] = baseline.round(2)
        latestM["model_vs_baseline"] = (
            (latestM["predicted_next_30d"] - latestM["baseline_predicted"]) /
            latestM["baseline_predicted"].clip(lower=0.1)
        ).round(3)
        latestM["trend_direction"] = np.where(
            latestM["predicted_next_30d"] > latestM["lag_1m_count"] * 1.05, "rising",
            np.where(latestM["predicted_next_30d"] < latestM["lag_1m_count"] * 0.95, "falling", "stable")
        )

        explainer_m = shap.TreeExplainer(model_msoa)
        sv = explainer_m.shap_values(XM)
        latestM["top_drivers_json"] = [
            top_drivers_json(sv[i], feat_cols_m, XM.iloc[i].values) for i in range(len(sv))
        ]
        latestM["tract_geoid"] = latestM["msoa_code"]
        latestM["NAMELSAD"] = latestM["msoa_code"]
        latestM["scored_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
        latestM["model_version"] = "uk_msoa_lgbm_ensemble_v1"

        outM = latestM[[c for c in [
            "tract_geoid", "NAMELSAD", "risk_score", "risk_tier",
            "predicted_next_30d", "predicted_violent_30d", "predicted_property_30d",
            "violent_score", "property_score",
            "incident_count", "y_incidents_12m", "trend_direction",
            "model_vs_baseline", "baseline_predicted", "top_drivers_json",
            "total_pop", "imd_score", "imd_decile",
            "scored_at", "model_version",
        ] if c in latestM.columns]]
        spark.createDataFrame(outM).write.mode("overwrite").option("overwriteSchema", "true").saveAsTable("varanasi.default.uk_msoa_risk_scores")
        spark.sql("ALTER TABLE varanasi.default.uk_msoa_risk_scores SET TBLPROPERTIES ('comment' = 'Latest per-MSOA risk scores + SHAP drivers (CrimeScope UK).')")
        print(f"Wrote {len(outM):,} MSOA scores")
        """),
        md("""
        ---
        ## Append to history (audit trail)
        """),
        code("""
        spark.sql(\"\"\"
          CREATE TABLE IF NOT EXISTS varanasi.default.uk_risk_scores_history (
            grain STRING, tract_geoid STRING, risk_score DOUBLE, risk_tier STRING,
            predicted_next_30d DOUBLE, scored_at STRING, model_version STRING
          ) USING delta
          COMMENT 'Append-only audit trail of CrimeScope UK risk scoring runs.'
        \"\"\")

        spark.sql(\"\"\"
          INSERT INTO varanasi.default.uk_risk_scores_history
          SELECT 'lsoa', tract_geoid, risk_score, risk_tier,
                 predicted_next_30d, scored_at, model_version
          FROM varanasi.default.uk_lsoa_risk_scores
        \"\"\")
        spark.sql(\"\"\"
          INSERT INTO varanasi.default.uk_risk_scores_history
          SELECT 'msoa', tract_geoid, risk_score, risk_tier,
                 predicted_next_30d, scored_at, model_version
          FROM varanasi.default.uk_msoa_risk_scores
        \"\"\")
        print("History updated")
        """),
    ]


# ===========================================================================
# 06 — Export to UC Volume for backend
# ===========================================================================

def nb_06_uk_export() -> list[dict]:
    return [
        md("""
        # CrimeScope ML — 06 (UK). Export for Backend

        Reads the latest scores / demographics / boundaries / lookup from Delta
        and writes the JSON files that `crimescope/backend/app/data/` consumes,
        landing them in the `exports/latest/` folder of the UC Volume so
        `databricks fs cp` can pull them locally.
        """),
        code("""
        spark.sql("USE CATALOG varanasi")
        spark.sql("USE SCHEMA default")
        """),
        code("""
        import os
        import json
        from datetime import datetime, timezone
        from pyspark.sql import functions as F

        VOLUME_OUT = "/Volumes/varanasi/default/ml_data_uk/exports/latest"
        os.makedirs(VOLUME_OUT, exist_ok=True)


        def write_records(table: str, fname: str, columns: list[str] | None = None) -> int:
            df = spark.table(table)
            if columns:
                df = df.select(*[c for c in columns if c in df.columns])
            pdf = df.toPandas()
            path = f"{VOLUME_OUT}/{fname}"
            pdf.to_json(path, orient="records", date_format="iso")
            print(f"  {fname}: {len(pdf):,} rows -> {os.path.getsize(path)/1_048_576:.2f} MB")
            return len(pdf)


        # --- MSOA bundle (default UK city) ---
        n_msoa_scores = write_records("varanasi.default.uk_msoa_risk_scores", "uk_msoa_risk_scores.json")
        write_records("varanasi.default.uk_msoa_boundaries", "uk_msoa_boundaries.json",
                      ["tract_geoid", "NAMELSAD", "wkt", "ALAND"])
        # Demographics under the same `tract_geoid` key
        msoa_demo = spark.table("varanasi.default.uk_msoa_demographics") \\
            .selectExpr("msoa_code as tract_geoid",
                        "total_pop as total_pop_acs",
                        "imd_score",
                        "imd_decile",
                        "imd_income as poverty_rate_acs")
        msoa_demo.toPandas().to_json(f"{VOLUME_OUT}/uk_msoa_demographics.json", orient="records")
        print(f"  uk_msoa_demographics.json: {msoa_demo.count():,} rows")

        # --- LSOA bundle (high-resolution) ---
        n_lsoa_scores = write_records("varanasi.default.uk_lsoa_risk_scores", "uk_lsoa_risk_scores.json")
        write_records("varanasi.default.uk_lsoa_boundaries", "uk_lsoa_boundaries.json",
                      ["tract_geoid", "NAMELSAD", "wkt", "ALAND"])
        lsoa_demo = spark.table("varanasi.default.uk_lsoa_demographics") \\
            .selectExpr("lsoa_code as tract_geoid",
                        "total_pop as total_pop_acs",
                        "imd_score",
                        "imd_decile",
                        "imd_income as poverty_rate_acs")
        lsoa_demo.toPandas().to_json(f"{VOLUME_OUT}/uk_lsoa_demographics.json", orient="records")
        print(f"  uk_lsoa_demographics.json: {lsoa_demo.count():,} rows")
        """),
        code("""
        # --- Pipeline stats — sourced from MLflow run + table counts ---
        import mlflow
        mlflow.set_registry_uri("databricks-uc")
        client = mlflow.MlflowClient()

        def latest_metric(model_name: str) -> tuple[str, dict]:
            try:
                mv = client.get_model_version_by_alias(model_name, "champion")
                run = client.get_run(mv.run_id)
                return mv.version, {k: v for k, v in run.data.metrics.items()}
            except Exception as e:  # noqa: BLE001
                print(f"  champion lookup failed for {model_name}: {e}")
                return "?", {}

        v_lsoa, m_lsoa = latest_metric("varanasi.default.crimescope_uk_risk_model_lsoa")
        v_msoa, m_msoa = latest_metric("varanasi.default.crimescope_uk_risk_model_msoa")

        feat_stats = spark.sql(\"\"\"
          SELECT COUNT(*) AS total_rows,
                 COUNT(DISTINCT lsoa_code) AS n_regions,
                 MIN(month_start) AS data_start,
                 MAX(month_start) AS data_end
          FROM varanasi.default.uk_lsoa_features
        \"\"\").first().asDict()

        stats = [{
            "n_tracts": int(feat_stats["n_regions"]),
            "data_start": str(feat_stats["data_start"]),
            "data_end": str(feat_stats["data_end"]),
            "total_rows": int(feat_stats["total_rows"]),
            "model_lsoa_version": v_lsoa,
            "model_msoa_version": v_msoa,
            "model_lsoa_mae": float(m_lsoa.get("ensemble_mae", m_lsoa.get("log_mae", 0.0))),
            "model_msoa_mae": float(m_msoa.get("ensemble_mae", m_msoa.get("log_mae", 0.0))),
            "scope": "England & Wales (LSOA + MSOA 2021)",
            "boundary_source": "ONS Open Geography Portal — LSOA Dec 2021 BGC + MSOA Dec 2021 BSC",
            "score_source": "LightGBM ensemble trained on 60 months of data.police.uk + ONS Census 2021 + IMD/WIMD 2019",
            "exported_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        }]
        with open(f"{VOLUME_OUT}/uk_pipeline_stats.json", "w") as f:
            json.dump(stats, f)
        print(f"  uk_pipeline_stats.json: {stats[0]['n_tracts']:,} regions, model v{v_lsoa} (LSOA) / v{v_msoa} (MSOA)")
        """),
        code("""
        print("\\nAll UK exports landed in", VOLUME_OUT)
        for f in sorted(os.listdir(VOLUME_OUT)):
            sz = os.path.getsize(f"{VOLUME_OUT}/{f}") / 1_048_576
            print(f"  {f:40s}  {sz:>6.2f} MB")
        """),
    ]


# ===========================================================================
# main
# ===========================================================================

def main() -> None:
    print("Generating UK CrimeScope ML notebooks ->", OUT_DIR)
    write_notebook("02_uk_ingest_and_geos.ipynb", nb_02_uk_ingest())
    write_notebook("03_uk_panel_features_demographics.ipynb", nb_03_uk_features())
    write_notebook("04_uk_train_and_evaluate.ipynb", nb_04_uk_train())
    write_notebook("05_uk_score_and_serve.ipynb", nb_05_uk_score())
    write_notebook("06_uk_export_for_backend.ipynb", nb_06_uk_export())
    print("Done.")


if __name__ == "__main__":
    main()
