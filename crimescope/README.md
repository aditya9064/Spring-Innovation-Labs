# CrimeScope

> Tract- and MSOA-level crime risk scoring for insurance underwriters and risk analysts. Built on the Databricks Lakehouse — Unity Catalog, Delta Lake, MLflow, Lakeflow workflows, Genie, and Lakebase.

## What problem we're solving

Insurance underwriters today price crime risk from postcode-level claims history that lags reality by 6 to 18 months. That's three problems in one:

- **Granularity gap.** Postcode/ZIP is 5–50× too coarse for the actual perimeter risk of an asset.
- **Latency gap.** Claims history lags the underlying crime trend by quarters.
- **Trust gap.** Black-box risk scores fail compliance review.

CrimeScope fixes all three. Every score is **tract-level** (Chicago: 1,332 Cook County tracts) or **MSOA-level** (England & Wales: 7,264 areas), refreshed **monthly** by a Databricks Lakeflow workflow, and ships with a full **provenance trail** — Trust Passport, SHAP drivers, baseline-vs-ML divergence flag, and a per-region challenge log.

For the demo playbook and judge-facing talking points, read **[SHOWCASE.md](./SHOWCASE.md)**.
For the evaluation methodology and hard numbers, read **[EVALUATION.md](./EVALUATION.md)**.

## Headline numbers

- **Chicago model (real, MLflow-tracked):** Spearman ρ = **0.71**, top-decile precision = **0.83**, ECE = **0.04**, +12% lift over rolling-mean baseline. Time-aware split, 29 features, LightGBM with `log1p`.
- **England & Wales:** 7,264 MSOA boundaries from ONS, **synthetic gravity baseline** in the bundled JSON; the real LightGBM pipeline (`crimescope_uk_pipeline`) is wired and runs monthly.
- **Latency:** monthly refresh end-to-end. data.police.uk publishes by the 1st; pipeline runs at 06:00 UTC on the 5th.

## What's in the box

- `frontend/` — Next.js 15 / React 19 / MapLibre dashboard with persona switching, premium multiplier card, Genie-backed AI Analyst, simulator, audit and challenge flows.
- `backend/` — FastAPI service exposing scoring, comparison, simulation, pricing, audit, challenge, Genie proxy, and platform-status endpoints. Reads from JSON snapshots, local Postgres, or **Lakebase** depending on `DATA_STORE_BACKEND`.
- `notebooks/ML/` — five-step Databricks pipeline (ingest → features → train → score → export) for Chicago and the UK, in parallel.
- `databricks/` — Asset Bundle (`databricks bundle deploy/run`) defining the monthly Lakeflow workflow `crimescope_uk_pipeline` and the `crimescope-uk-risk` model serving endpoint (pending real training run).
- `scripts/uk/` — local synthetic-baseline generator that pulls real ONS MSOA boundaries and produces the demo JSON.
- `presentation/` — the deck and the build script that produced it.

## Architecture in one paragraph

`data.police.uk` + `Chicago Open Data` (open) → `Unity Catalog Volumes` (Delta staging) → `tract_*` and `msoa_*` Delta tables (Z-ordered by `tract_geoid`) → LightGBM training tracked in **MLflow**, registered in **UC Model Registry** → batch scoring writes `varanasi.default.tract_risk_scores` (and `_history`) → exported to JSON for the FastAPI demo, **also queryable directly from Lakebase** in production → FastAPI exposes scoring + pricing + simulator + Genie proxy → Next.js dashboard. **Same UC tables, same governance, end to end.** No ETL between training output and API serving.

## Databricks features wired

| Feature | Where | Status |
|---|---|---|
| **Unity Catalog** | All tables under `varanasi.default.*` | Live |
| **Delta Lake** | `OPTIMIZE` + `ZORDER (tract_geoid)` on hot tables | Live |
| **UC Volumes** | Raw data staged in `varanasi.default.ml_data` | Live |
| **MLflow** | `/Shared/Team_varanasi/crimescope_baseline` | Live |
| **UC Model Registry** | `varanasi.default.crimescope_risk_model` | Live |
| **Lakeflow Workflow** | `crimescope_uk_pipeline` (monthly cron) | Deployed |
| **Asset Bundle** | `crimescope/databricks/databricks.yml` | Live |
| **Genie** | `/api/genie/*` proxy + AI Analyst chips | Scaffolded; set `DATABRICKS_GENIE_SPACE_ID` to enable |
| **Lakebase** | `data_store.py` adapter via `LAKEBASE_URL` | Scaffolded; flip `DATA_STORE_BACKEND=lakebase` to enable |
| **Model Serving** | `crimescope-uk-risk` endpoint | Pending real UK training |
| **Serverless job compute** | All Lakeflow tasks | Live |

The frontend's KPI strip shows three pills — **LAKEBASE / GENIE / MODEL SERVING** — that light up green when each integration is live.

## Repo layout

```
crimescope/
├── README.md                ← you are here
├── SHOWCASE.md              ← judge talking points (read before demo)
├── EVALUATION.md            ← methodology + metrics
├── AGENTS.md                ← coding-agent workflow
├── frontend/                ← Next.js dashboard
├── backend/                 ← FastAPI service
├── notebooks/ML/            ← Databricks ML pipeline (5 steps × 2 regions)
├── databricks/              ← Asset Bundle (deploy + run)
├── ml/                      ← Local-train counterparts
├── scripts/                 ← Data prep + Databricks helpers
├── infra/                   ← Local Postgres + Redis docker-compose
├── data_samples/            ← Frozen JSON contracts
└── presentation/            ← Deck + build script
```

## Quickstart (local demo)

```bash
# 1. Backend
cd crimescope/backend
cp .env.example .env          # fill in OPENAI_API_KEY if you want LLM fallback
uvicorn app.main:app --reload --port 8000

# 2. Frontend
cd crimescope/frontend
npm install
npx next dev --port 3001

# 3. Open http://localhost:3001 — defaults to England & Wales (7,264 MSOAs)
```

To enable Genie and Lakebase, see `crimescope/backend/.env.example` — the relevant env vars are commented inline.

## Reproducing the Chicago numbers

The MLflow run lives at `/Shared/Team_varanasi/crimescope_baseline`. To re-run end-to-end:

```bash
databricks bundle deploy --profile team_varanasi -t prod
databricks bundle run crimescope_uk_pipeline --profile team_varanasi -t prod
# Or the Chicago equivalent — same five notebooks, different parameter cell.
```

To regenerate the synthetic UK demo bundle locally without Databricks:

```bash
python3 crimescope/scripts/uk/prep_uk_msoa.py
```

## Honest scope

- **Chicago is the production-grade story.** Real ML, real metrics, MLflow tracked.
- **UK is the same pipeline shape with a transparent synthetic baseline today.** The Asset Bundle runs the real LightGBM pipeline on the next monthly refresh; the Trust Passport flips automatically when real data lands.
- **Genie + Lakebase are scaffolded, not wired to live workspace tokens in this repo.** Both light up the moment env vars are set; the API and UI are ready.

That's deliberate. We'd rather ship a project where the synthetic parts are labeled and swappable than a demo that hides what's pending behind polish.

## Mentions

Built for the Persistent Innovation Labs hackathon by Team Varanasi.
