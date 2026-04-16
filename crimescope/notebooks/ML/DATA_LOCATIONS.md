# Where CrimeScope data is stored

## Delta tables (Unity Catalog: `varanasi.default`)

| Table | Notebook | Role | ZORDER |
|-------|----------|------|--------|
| `chicago_crimes_raw` | 02 | Raw Socrata crime incidents | `community_area, date` |
| `chicago_crime_monthly_by_community_area` | 02 | Monthly counts by community area (staging) | — |
| `cook_tract_boundaries` | 02 | Cook County tract polygons (`tract_geoid`, `wkt`) | `tract_geoid` |
| `chicago_crimes_with_tract` | 02 | Crimes + `tract_geoid` from spatial join | `tract_geoid, date` |
| `chicago_crime_monthly_by_tract` | 02 | Tract × month `incident_count` | `tract_geoid, month_start` |
| `tract_crime_monthly_panel_labeled` | 03 | Dense panel; `y_rate_12m`, `y_next_30d_count` | `tract_geoid, month_start` |
| `tract_acs_population` | 03 | ACS pop, income, poverty, housing | `tract_geoid` |
| `tract_crime_monthly_panel_with_acs` | 03 | Panel + per-1k rates | `tract_geoid, month_start` |
| `tract_crime_features` | 03 | Wide feature table (29 features) + labels | `tract_geoid, month_start` |
| `tract_risk_scores` | 05 | **Latest per-tract risk scores + SHAP drivers** | `tract_geoid` |
| `tract_risk_scores_history` | 05 | Append-only historical scores (audit trail) | — |

## Unity Catalog Volume

- `varanasi.default.ml_data` — Parquet copy of crime data (written by `02`)

## MLflow

- Experiment: `/Shared/Team_varanasi/crimescope_baseline`
- Runs:
  - `naive_lag1_y_next_30d` — lag-1 baseline
  - `lightgbm_y_next_30d` — LightGBM model (with SHAP + plots)

## UC Model Registry

- Model: `varanasi.default.crimescope_risk_model`
- Latest version served by notebook `05`

## Socrata throttling

If pagination stalls, set **`SOCRATA_APP_TOKEN`** as a cluster environment variable. Page size is 50k rows; full ingest is ~1M+ rows.
