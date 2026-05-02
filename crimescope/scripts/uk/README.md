# CrimeScope — UK boundary refresh (offline-fallback only)

The real UK & Wales risk-scoring pipeline lives in Databricks under
`/Workspace/Shared/Team_varanasi/ML`:

| # | Notebook | Role |
|---|----------|------|
| 02 | `02_uk_ingest_and_geos.ipynb` | data.police.uk monthly archives + ONS LSOA/MSOA boundaries → Delta |
| 03 | `03_uk_panel_features_demographics.ipynb` | ONS Census 2021 + IMD 2019 (EN) + WIMD 2019 (WAL) → feature tables |
| 04 | `04_uk_train_and_evaluate.ipynb` | Optuna-tuned LightGBM ensemble + violent/property sub-models → MLflow → UC Model Registry |
| 05 | `05_uk_score_and_serve.ipynb` | Score every LSOA + MSOA → blended 0–100 + SHAP top-5 → Delta |
| 06 | `06_uk_export_for_backend.ipynb` | Emit JSON files to `/Volumes/varanasi/default/ml_data_uk/exports/latest/` |

Run as a Lakeflow Workflow:

```bash
databricks bundle deploy --profile team_varanasi -t prod
databricks bundle run crimescope_uk_pipeline --profile team_varanasi -t prod
```

Pull the exports back into the FastAPI bundle:

```bash
databricks fs cp -r \
  dbfs:/Volumes/varanasi/default/ml_data_uk/exports/latest/ \
  crimescope/backend/app/data/ \
  --profile team_varanasi --overwrite
```

## What this script (`prep_uk_msoa.py`) does

It is now **boundary-only**. It refreshes
`crimescope/backend/app/data/uk_msoa_boundaries.json` from ONS so a contributor
without Databricks access can still render the map. It will **not** generate
risk scores — those come from the Databricks export above.

```bash
python3 crimescope/scripts/uk/prep_uk_msoa.py
```

If ONS is unreachable, it falls back to a tiny synthetic 30×30 Greater London
grid so the demo doesn't 404 on boundaries.

## Local dev mirror of the ML pipeline

For iterating on the model logic without spinning up a cluster, see
`crimescope/ml/train_uk.py`. It runs a small slice (default: 1 force, 12
months) end-to-end on your laptop. Caches under `crimescope/ml/.cache/uk/`,
artifacts under `crimescope/ml/artifacts/uk/`. **Not** the source of truth for
the JSON files shipped to the backend.

## Data sources (canonical)

- **Crime** — [data.police.uk monthly archives](https://data.police.uk/data/archive/) (60 months × 43 territorial forces).
- **Boundaries** — ONS Open Geography Portal: LSOA Dec 2021 BGC + MSOA Dec 2021 BSC.
- **Demographics** — ONS Census 2021 via Nomis API (population + age structure).
- **Deprivation** — MHCLG English IMD 2019 + StatsWales WIMD 2019 (harmonized to a common national-rank percentile).
- **Lookup** — ONS LSOA(2021) → MSOA(2021) → LAD(2022) lookup.
