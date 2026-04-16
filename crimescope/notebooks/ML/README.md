# ML notebooks (Databricks Lakehouse)

Canonical Databricks folder: **`/Workspace/Shared/Team_varanasi/ML`**

## Pipeline (5 notebooks)

| # | File | Contents |
|---|------|----------|
| 01 | `01_data_sources_and_assumptions.ipynb` | Assumptions, scope, source checklist, catalog check |
| 02 | `02_ingest_and_tracts.ipynb` | Crime ingest (Socrata → Delta), TIGER tracts, spatial join, monthly counts, `OPTIMIZE`+`ZORDER` |
| 03 | `03_panel_features_acs.ipynb` | Dense panel + labels, ACS population/income/poverty, per-1k rates, 29-feature engineering |
| 04 | `04_train_and_evaluate.ipynb` | Lag-1 baseline + LightGBM (log1p) + SHAP + MLflow + Unity Catalog model registry |
| 05 | `05_score_and_serve.ipynb` | Score all tracts, risk tiers (0–100), SHAP drivers per tract, `tract_risk_scores` Delta table |

**Run order:** **`01`** (read once) → **`02` → `03` → `04` → `05`**.

## Lakehouse Features Used

- **Unity Catalog** — all tables under `varanasi.default.*`, model in UC registry
- **Delta Lake** — every table is Delta with `OPTIMIZE` + `ZORDER` for query performance
- **Unity Catalog Volumes** — raw data staged in `varanasi.default.ml_data`
- **MLflow** — experiment tracking at `/Shared/Team_varanasi/crimescope_baseline`
- **UC Model Registry** — model registered as `varanasi.default.crimescope_risk_model`
- **Data-quality assertions** — notebook 02 and 03 assert row counts, coverage, null rates
- **Table comments** — governance metadata on all major tables

## Key Tables

| Table | Written by | Role |
|-------|-----------|------|
| `chicago_crimes_raw` | 02 | Raw Socrata crime incidents (Delta) |
| `cook_tract_boundaries` | 02 | Cook County tract polygons (WKT) |
| `chicago_crimes_with_tract` | 02 | Crimes + `tract_geoid` from spatial join |
| `chicago_crime_monthly_by_tract` | 02 | Tract × month incident counts |
| `tract_acs_population` | 03 | ACS 2022: pop, income, poverty, housing |
| `tract_crime_features` | 03 | 29-feature wide table + labels |
| `tract_risk_scores` | 05 | **Latest per-tract risk scores + SHAP drivers** |
| `tract_risk_scores_history` | 05 | Append-only audit trail of scoring runs |

## Model

- **Type:** LightGBM Regressor (log1p target transform)
- **Target:** `y_next_30d_count` (next-month incident count per tract)
- **Features:** 29 (lags, rolling stats, calendar, ACS context, city-wide, seasonal)
- **Registry:** `varanasi.default.crimescope_risk_model`

## Where data lives

See `DATA_LOCATIONS.md`.
