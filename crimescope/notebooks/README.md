# Notebooks

## Where training runs

**All model training, fitting, and evaluation runs in Databricks** — on a Databricks cluster (Python/SQL notebooks), not on a laptop as the source of truth.

- **In scope for Databricks:** ingestion, cleaning, feature engineering, **baseline + ML training**, hyperparameter runs, SHAP, calibration, MLflow experiment logging, registered models.
- **Out of scope for local dev:** training production scores on raw CSVs only on your machine; use Databricks for anything that feeds `tract_risk_*` outputs.

This repo’s `notebooks/` folder holds **exports, drafts, or Git-tracked copies** of notebooks. The **canonical place to create and run** all ML notebooks is:

**`/Workspace/Shared/Team_varanasi/ML`**

The `crimescope` folder under `Team_varanasi` is for the app scaffold / shared code; **do not** put training notebooks there — use **`ML`** alongside it.

## Databricks Environment

- Host: `https://dbc-42cdc781-8591.cloud.databricks.com`
- Profile: `team_varanasi` (CLI: `databricks ... --profile team_varanasi`)
- Catalog: `varanasi`
- Schema: `varanasi.default`
- **Notebooks (execute here):** `/Workspace/Shared/Team_varanasi/ML`
- **App mirror (optional):** `/Workspace/Shared/Team_varanasi/crimescope`
- Local mirror for review: `crimescope/notebooks/` (export copies into `notebooks/ML/` if you want parity)

## Notebook Organization (`ML/` folder)

| Prefix | Purpose | Owner |
|--------|---------|-------|
| `01_`–`04_` | ML pipeline notebooks (`notebooks/ML/`); see `ML/README.md` | Person 1 |

## Rules

- Each notebook begins with a short **Description** under the title (what it does, who it is for, and how it fits the pipeline).
- All raw and curated data lands in `varanasi.default` as **Delta** tables.
- Feature tables follow naming: `tract_features_{category}` or `tract_features_historical`.
- **MLflow:** log training runs and register models under the workspace MLflow registry (team policy: use `varanasi` catalog where applicable).
- Notebooks must run **end-to-end on a Databricks cluster** (attach cluster before Run All).
- The local backend (FastAPI) reads **tables or batch exports** produced by Databricks; it does not train models.

## Sync workflow (optional)

1. Edit and run notebooks in Databricks UI (or Repos linked to Git).
2. Periodically **export** `.ipynb` or use **Repos** so `crimescope/notebooks/` stays in sync for code review.
3. Use `databricks workspace export` / import if you manage paths via CLI.

