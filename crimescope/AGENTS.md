# CrimeScope Agent Workflow

This file defines how an agent should work inside the CrimeScope build repo.

## Project Identity

- Product: `CrimeScope`
- Build repo: `/Volumes/External Sabrent ssd/Spring-Innovation-Labs/crimescope`
- Planning repo: `/Volumes/External Sabrent ssd/Spring-Innovation-Labs`
- First build city: `Chicago`
- Geography unit: `census tract`
- Primary persona: `insurer`
- Interface: `2D map-first dashboard + report surface`
- Main target: `next-30-day regional risk`
- Databricks account: `adityamiriyala08@gmail.com`
- Databricks host: `https://dbc-42cdc781-8591.cloud.databricks.com`
- Databricks app / repo mirror: `/Workspace/Shared/Team_varanasi/crimescope`
- Databricks ML notebooks (canonical): `/Workspace/Shared/Team_varanasi/ML` — pipeline `01`–`04` (see `notebooks/ML/README.md`)
- Databricks CLI profile: `team_varanasi`
- Databricks catalog: `varanasi`
- Databricks schema: `varanasi.default`
- All data ingestion, feature engineering, model training, and evaluation run in Databricks notebooks on Databricks compute (clusters), not as the primary path on a local machine

## Non-Negotiable Product Rules

- Treat this as an explainable decision-support product, not a generic crime map.
- Keep `verified historical scoring` separate from `governed live signals`.
- Do not silently let live signals overwrite the verified tract score.
- Keep the first build `Chicago-first`, `tract-level`, and `insurer-first`.
- Prioritize practicality, trust, and judged usefulness over flashy architecture.
- Do not turn the first build into a full agent-swarm system.
- Use `agent-lite` orchestration only where it improves modular execution.
- Use Databricks as the primary environment for all data ingestion, feature engineering, model training, and evaluation — run everything through Databricks notebooks.
- The local runtime (FastAPI, Next.js) consumes the outputs (scores, features) from Databricks, but all data work happens in Databricks.

## Canonical References

Read only what is needed for the task. Start with these:

- Planning index: `/Volumes/External Sabrent ssd/Spring-Innovation-Labs/docs/planning/CrimeScope_Planning_Index.md`
- Team split: `/Volumes/External Sabrent ssd/Spring-Innovation-Labs/docs/planning/CrimeScope_Tech_Stack_Team_Split.md`
- Rubric alignment: `/Volumes/External Sabrent ssd/Spring-Innovation-Labs/docs/planning/CrimeScope_Rubric_Alignment.md`

Use local repo files for implementation truth:

- frontend contracts: `/Volumes/External Sabrent ssd/Spring-Innovation-Labs/crimescope/frontend/lib/contracts.ts`
- backend schemas: `/Volumes/External Sabrent ssd/Spring-Innovation-Labs/crimescope/backend/app/schemas/contracts.py`
- sample payloads: `/Volumes/External Sabrent ssd/Spring-Innovation-Labs/crimescope/data_samples/`

## Required Workflow

When given a prompt, follow this order:

1. Classify the request.
   - `frontend`
   - `backend`
   - `workers`
   - `data/geospatial`
   - `ml/evaluation`
   - `trust/reporting`
   - `integration`
2. Read the smallest relevant set of files before changing anything.
3. Identify whether the task changes a contract.
4. If the task spans multiple files or systems, make a short plan first.
5. Implement the smallest complete slice that moves the product forward.
6. Run the narrowest useful verification.
7. Summarize exactly what changed, what was verified, and what remains.

## Contract-First Rule

If a task touches a shared payload or API shape, update all affected layers together:

- `data_samples/*.json`
- `frontend/lib/contracts.ts`
- `backend/app/schemas/contracts.py`
- backend routes or loaders if needed
- tests covering the changed contract

Never leave the frontend, backend, and sample payloads on different shapes.

## Workstream Routing

### Historical Risk Core

Use this lane for:

- historical ingestion
- ACS and contextual joins
- tract feature engineering
- baseline risk scoring
- ML scoring
- evaluation and calibration

Main outputs:

- `tract_features_historical`
- `tract_risk_baseline`
- `tract_risk_ml`
- `tract_risk_package`

### Live Intelligence And Backend

Use this lane for:

- live connectors
- normalization
- deduplication
- geospatial resolution
- published live events
- FastAPI routes
- Redis or realtime plumbing

Main outputs:

- `live_events_raw`
- `live_events_normalized`
- `live_events_resolved`
- `live_events_published`

### Trust, Persona, And Reporting

Use this lane for:

- Trust Passport
- Verified-vs-Live Disagreement
- What Changed And Why
- persona decision packaging
- report summary packaging
- selective cross-LLM narrative review

Main outputs:

- `persona_decision_package`
- `report_summary_package`
- trust metadata

## Frontend Convergence Rule

- Do not start final frontend polish until score, live, and trust contracts are stable.
- Frontend should render real or frozen contract payloads, not hand-wavy placeholders.
- The final app should read as one product, not two stitched surfaces.

## First-Build Feature Priorities

Build first:

1. Trust Passport
2. Verified-vs-Live Disagreement
3. What Changed And Why
4. Blind-Spot / Underreporting View
5. Persona Conflict or persona decision view

Build later:

1. Counterfactual Action Simulator
2. Decision Audit Trail
3. Human Challenge Mode

## Verification Rules

At minimum, run the verification that fits the change:

- contract or sample changes:
  - `make verify-samples`
- backend Python changes:
  - `python3 -m compileall backend/app workers/jobs`
- backend route or schema changes:
  - `python3 -m unittest discover -s tests`
- frontend changes after dependencies are installed:
  - `npm run typecheck`
  - `npm run lint`

If you cannot run a needed check, say so explicitly.

## Delivery Rules

Every substantial response should include:

- what the task was
- which files changed
- what checks ran
- any blockers or follow-up

Do not claim the full product is implemented when only the scaffold or one slice is done.

## What To Avoid

- decorative 3D-first map work
- generic chatbot behavior without grounding
- cross-LLM review on every output
- overbuilt orchestration that does not improve the judged demo
- schema changes made in only one layer
- mixing planning edits into the implementation repo unless explicitly asked
