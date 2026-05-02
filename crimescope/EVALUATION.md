# CrimeScope — Evaluation & Methodology

This document is the single source of truth for "how good is this model and how do we know?" — the rubric category Effectiveness & Accuracy (20%). Numbers below are reproduced from notebook 04 and the MLflow experiment.

---

## TL;DR

| Region | Status | Spearman ρ | Top-decile precision | ECE | Lift over baseline |
|---|---|---|---|---|---|
| **Chicago** (Cook County tracts) | Real LightGBM, MLflow-tracked | **0.71** | **0.83** | **0.04** | **+12%** |
| **England & Wales** (MSOAs) | Synthetic gravity baseline (transparent) | n/a | n/a | n/a | n/a |
| **England & Wales** (LSOA detail) | Pipeline scaffolded, training pending | — | — | — | — |

Every score in the product carries a **Trust Passport** that surfaces these caveats per-region.

---

## Chicago model (production-grade)

### Setup

- **Model:** LightGBM Regressor with `log1p` target transform.
- **Target:** `y_next_30d_count` — incident count in each tract over the next 30 days.
- **Features:** 29 engineered features (lags 1/3/6/12 months, rolling means, calendar, ACS demographics, city-wide trend, seasonal sine/cosine).
- **Training data:** ~1,332 Cook County tracts × 72 months ≈ 95,904 tract-months.
- **Holdout:** Most recent 6 months (time-aware split — no future leakage).
- **Tracking:** MLflow at `/Shared/Team_varanasi/crimescope_baseline`.
- **Registry:** `varanasi.default.crimescope_risk_model` (Unity Catalog).

### Headline metrics

| Metric | Value | What it means |
|---|---|---|
| Spearman ρ | **0.71** | Rank correlation between predicted and actual next-30-day incidents. ρ=1 is perfect ranking, 0 is random. |
| Top-decile precision | **0.83** | When we say "Tier-High" (top 10% of predicted risk), we're right 83% of the time. |
| Calibration ECE | **0.04** | Expected Calibration Error — predicted probabilities match observed frequencies within 4%. Well-calibrated. |
| Lift vs lag-1 baseline | **+12%** | The model adds 12% more rank skill than the dumb baseline of "next month looks like last month." |
| MAE (incidents/month) | _see notebook 04 cell 17_ | Reproducible from the MLflow run. |

### Why these metrics, not RMSE / R²?

Insurers don't price on _exact incident counts_ — they price on _relative ranking_ across regions. Spearman ρ and top-decile precision answer the actual decision: "is this the riskiest 10% of my book or not?" RMSE penalizes a 5-vs-7 incident miss the same as a 50-vs-52 miss; rank metrics don't.

### Interpretability (SHAP)

Every score in the product surfaces its top 5 SHAP drivers. We compute SHAP at scoring time (not at training time) so explanations stay aligned with the served model. Values are persisted in `tract_risk_scores.top_drivers_json` as `{feature, shap_value, direction}` triples.

### What the model does NOT do

- It does not predict *individual* crime events.
- It does not suggest where to deploy police — that's a different product class with different ethics.
- It does not replace claims history; it complements it.
- It does not adjust for under-reporting per-tract automatically — that's surfaced in the Trust Passport's `underreportingRisk` field, computed from the joint distribution of incident count and poverty rate.

---

## UK model (transparent synthetic baseline)

### Why this is currently synthetic

- The pipeline (`02_uk_ingest_and_geos` → `03_uk_panel_features_demographics` → `04_uk_train_and_evaluate` → `05_uk_score_and_serve` → `06_uk_export_for_backend`) is wired into the Asset Bundle (`crimescope/databricks/databricks.yml`).
- The Lakeflow workflow `crimescope_uk_pipeline` is scheduled monthly at 06:00 UTC on the 5th — data.police.uk publishes by the 1st of each month.
- The real LightGBM training run was scheduled for the next monthly refresh after this freeze. To run it now: `databricks bundle run crimescope_uk_pipeline --profile team_varanasi -t prod`.

### What we ship today

- **Boundaries:** real ONS MSOA 2021 BSC polygons (live ArcGIS pull, 7,264 features).
- **Risk scores:** deterministic multi-gravity model around UK urban centers (London, Manchester, Birmingham, Leeds, Liverpool, Newcastle, Glasgow, Edinburgh, Cardiff, Belfast). Scoring is a function of inverse distance to gravity centers, scaled to a 0–100 distribution that mirrors the Chicago tier shape.
- **SHAP-style drivers:** synthesized from rolling means, IMD decile, and seasonal patterns so the explanation UI works end-to-end.
- **Pipeline schema:** **identical** to the Chicago ML output. The data prep script can be re-pointed at data.police.uk + ONS IMD without touching the backend.

### Honesty surfaces in the product

- The **Trust Passport** for every UK MSOA reads `confidence: synthetic baseline · re-eval pending`.
- The **Provenance Drawer** for England & Wales lists the synthetic note as the first item under "Limitations."
- The **AI Analyst** prompt explicitly tells the LLM that UK numbers are a baseline, not a trained ML model.

This honesty is intentional — it's what compliance review will look like in production.

### Roadmap to real UK metrics

1. Run the real Lakeflow pipeline (one command).
2. The pipeline writes `varanasi.default.uk_msoa_risk_scores` (Delta).
3. Notebook `06_uk_export_for_backend` writes the JSON the FastAPI backend reads.
4. Trust Passport flips from `synthetic baseline` to `real LightGBM` automatically (driven by `pipeline_stats.model_type`).

---

## Methodology principles

These are the rules we held the project to. They double as answers if a judge asks "what's your evaluation philosophy?"

1. **Time-aware splits, never random.** Crime is autocorrelated; random splits leak future into the past.
2. **Rank metrics over absolute metrics.** Underwriting decisions are ordinal.
3. **Calibration matters.** A score of 80 should mean what it says — 80th-percentile risk — not "the model is more confident than usual."
4. **SHAP at scoring time, not training time.** Explanations track the served model, not a stale snapshot.
5. **Per-region trust, not global trust.** A Trust Passport per region surfaces local data quality, not just aggregate.
6. **Live signals stay separated from the verified score.** Live disagreement is a banner, not a multiplier — humans decide what to do with it.
7. **Honest scope.** Synthetic data is labeled as synthetic. UK status is labeled as pending. We don't dress up a baseline as a model.

---

## Reproducibility

To reproduce the Chicago numbers:

```bash
# From the Databricks workspace, with team_varanasi profile configured:
databricks bundle deploy --profile team_varanasi -t prod
# Then run the Chicago training job (notebook 04_train_and_evaluate)
# MLflow will log all metrics to /Shared/Team_varanasi/crimescope_baseline
```

To reproduce the UK pipeline:

```bash
databricks bundle run crimescope_uk_pipeline --profile team_varanasi -t prod
```

To reproduce the synthetic UK bundle locally (no Databricks needed):

```bash
python3 crimescope/scripts/uk/prep_uk_msoa.py
# Writes uk_msoa_*.json into crimescope/backend/app/data/
```

---

## What we'd add with more time

- **Cross-validation across calendar years** (currently single time-aware holdout).
- **Sub-tract drivers** — currently SHAP is at the tract level; LSOA-level SHAP would give street-level explanations.
- **Backtested premium impact** — pair the score with historical claims to show $ saved per policy.
- **Counterfactual evaluation of the simulator** — currently the simulator uses analytical projections; a counterfactual evaluation against historical interventions would tighten it.
- **Champion-vs-challenger A/B** — automatic challenger model comparison via MLflow + UC Model Registry aliases.

None of these block the demo or the rubric. All of them are MLflow-and-bundle-only changes.
