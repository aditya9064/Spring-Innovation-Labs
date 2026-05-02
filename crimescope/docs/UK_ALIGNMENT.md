# CrimeScope — UK Alignment Plan (Project 1)

This doc maps the **Project 1: AI-Powered Crime Risk Intelligence & Decision Support** brief
onto the existing CrimeScope build. It is an alignment proposal, not a refactor diff. Read it
end-to-end before changing any contracts.

## TL;DR

- Brief is **England & Wales**, source is **data.police.uk** street-level CSVs, persona triad is
  **insurer / real-estate / urban planner**, and explicit deliverable is **risk score + pricing
  guidance + natural-language explanations**.
- Current repo is **Chicago, census-tract, insurer-first** with strong contracts, a Trust
  Passport, a Verified-vs-Live story, and a Databricks lakehouse path.
- The frontend, backend schemas, contracts, evaluation harness, and Databricks notebook
  scaffold are all reusable. The work to do is in the **data layer, the geo unit, and the
  pricing-guidance output** — plus a copy/persona pass on the UI.

## Rubric → Where the points come from

| Weight | Criterion | What we lean on | Gap to close |
|---|---|---|---|
| 30% | Problem Understanding & Approach | Trust Passport, What-Changed-and-Why, Blind-Spot view, persona decision package | Reframe explicitly around UK insurers + the two adjacent personas |
| 20% | Effectiveness & Accuracy | Holdout-window evaluation in `EVALUATION.md`, baseline + ML scores | Need real numbers on UK data: Brier, reliability, top-decile lift, AUROC vs naive recency |
| 40% | Industry Fit & Practicality | FastAPI + Next.js + Databricks; report-style output exists | Add **pricing guidance object** (relative multiplier + rationale) and a clean insurer report tab |
| 10% | Scalability | Databricks-first per `AGENTS.md`, `databricks/databricks.yml` exists, ML notebooks 01–04 | Surface one **Genie space** over the published table; mention **Lakebase** for serving in the deck |

## Geography mapping (Chicago → England & Wales)

| Chicago concept | UK equivalent | Notes |
|---|---|---|
| State / city | England & Wales / police force area | Force = Met, GMP, WMP, etc. |
| Community area | Local Authority District (LAD) | Useful for narrative context |
| **Census tract** | **LSOA (Lower Layer Super Output Area)** | Primary scoring unit; ~1.5k residents avg |
| Census tract GEOID (`17031010100`) | LSOA code (`E01000001`) | Wire format change in `regionId` |
| ACS demographics | ONS Census 2021 + IMD 2019 | Open and well-documented |
| Chicago Open Data crime | data.police.uk monthly CSVs | Public, no API key, monthly cadence |

`regionType` becomes `lsoa`. `city` becomes `forceArea` (and we keep a derived `lad` for the
report header). Sample payloads stay the same shape — only the values change.

## Data source — data.police.uk

- **Endpoint**: bulk monthly CSV downloads at `https://data.police.uk/data/`. No auth.
- **Coverage**: England, Wales, NI (we scope to England & Wales per the brief).
- **Granularity**: street-level lat/lon, snapped to anonymised "snap points" within ~1 mile.
  This snapping matters for the model — never claim sub-LSOA precision.
- **Crime types** (canonical list, 14 categories): anti-social-behaviour, bicycle-theft,
  burglary, criminal-damage-arson, drugs, other-theft, possession-of-weapons, public-order,
  robbery, shoplifting, theft-from-the-person, vehicle-crime, violent-crime, other-crime.
- **Outcomes** ship in a parallel CSV per month per force.
- **Licence**: Open Government Licence v3.0 — must attribute "Contains public sector
  information licensed under the Open Government Licence v3.0."

### Persona cuts of the 14 categories

- **Personal crime** (insurer life/health, urban planner safety): violent-crime, robbery,
  theft-from-the-person, possession-of-weapons, public-order, anti-social-behaviour.
- **Property crime** (insurer home/contents/auto, real-estate): burglary, vehicle-crime,
  bicycle-theft, other-theft, shoplifting, criminal-damage-arson.
- The brief explicitly names personal vs property — keep this split first-class in the score
  object (`scores.personal`, `scores.property`) instead of the current
  `scores.violent` / `scores.property`.

## Contract changes (smallest possible)

All shape-level, not structural — keep `frontend/lib/contracts.ts` and
`backend/app/schemas/contracts.py` in lockstep per the contract-first rule.

1. `regionType`: add `"lsoa"` as a valid value.
2. `scores`: rename `violent` → `personal` (more inclusive of the UK category set).
3. New top-level field `pricingGuidance` on `tract_risk_package`:

   ```jsonc
   "pricingGuidance": {
     "relativeMultiplier": 1.18,        // vs force-area median, 1.00 = neutral
     "band": "elevated",                // low | neutral | elevated | high
     "confidence": "moderate",          // mirrors trustPassport.confidence
     "rationale": "Personal-crime intensity is 22% above the force-area median over the last 90 days; property-crime trend is flat. Underreporting risk is moderate, so do not over-correct.",
     "appliesTo": ["home", "contents", "motor"]
   }
   ```

4. Optional: `personaView` enum on the report payload (`insurer` | `real_estate` | `planner`)
   so the frontend can render persona-specific copy from the same package.

These four edits unlock the pricing-guidance deliverable and the persona triad without
breaking any existing surface.

## Stack reuse — what stays, what changes

| Layer | Status | Action |
|---|---|---|
| `frontend/` (Next.js 15, map-first dashboard) | Reusable | Copy pass: UK terminology, £ units, force/LSOA labels. Swap basemap default to UK. |
| `backend/app/` (FastAPI) | Reusable | Add `pricingGuidance` to schema; add `/lsoa/{code}` route alias to `/region/{id}`. |
| `data_samples/` | Reusable | Re-emit one UK sample alongside the Chicago one to keep tests passing during the cutover. |
| `databricks/` + `notebooks/ML/01–04` | Reusable | Repoint ingestion (notebook 01) at data.police.uk; repoint geo joins (02) at LSOA + IMD. |
| `tests/` | Reusable | Add a UK fixture so `make verify-samples` covers both. |
| `workers/` (live signals) | Optional | Brief is historical-only; gate behind a feature flag. |

## Databricks plan (Unity Catalog, `varanasi.default`)

Tables — same names as today, new contents:

- `crime_raw_uk` — bronze, monthly CSV ingest from data.police.uk.
- `crime_resolved_uk` — silver, lat/lon → LSOA via ONS LSOA boundary parquet.
- `lsoa_features_historical` — gold, rolling 90/180/365-day counts per LSOA per persona-cut.
- `lsoa_risk_baseline` — calibrated rate model (negative-binomial or quantile baseline).
- `lsoa_risk_ml` — gradient-boosted residual model on top of baseline.
- `lsoa_risk_package` — published table that backs the API, matches the JSON contract 1:1.

Scalability hooks for the rubric:

- Stand up **one Genie space** scoped to `varanasi.default.lsoa_risk_package` and
  `lsoa_features_historical`. Include 5 saved questions an underwriter would actually ask.
- Mention **Lakebase** as the low-latency serving path for the published package; do not
  build it for the hackathon unless the demo needs sub-100ms reads.

## Evaluation plan (the 20% we're weakest on)

- **Split**: time-based holdout. Train on months `T-12 … T-3`, evaluate on `T-2 … T`.
- **Targets**:
  - Personal-crime count per LSOA per month.
  - Property-crime count per LSOA per month.
- **Metrics** (report all three so judges see calibration, not just discrimination):
  - **Brier score** on the binarised "elevated vs not" call.
  - **Reliability curve** (10 buckets) — must look diagonal.
  - **Top-decile lift** vs. the naive "last 90 days, same LSOA" baseline.
- **Stability check**: rank correlation of LSOA scores between consecutive monthly runs
  (insurers will not tolerate a model that reshuffles the top-100 every refresh).
- Land all of the above as a notebook (`notebooks/ML/04_evaluation.py`) and a one-page
  table in `EVALUATION.md`.

## Persona deliverables (what each tab actually shows)

- **Insurer** (primary): LSOA → relative pricing multiplier, top 3 drivers, Trust Passport,
  "what changed and why" since last quarter, comparable LSOAs in the same force area.
- **Real-estate**: LSOA → safety band, personal-vs-property split, 12-month trend chart,
  three nearest LSOAs with lower risk and similar character.
- **Urban planner**: LSOA → underreporting-risk view, blind-spot map, top crime types
  driving the score, suggested intervention bucket (lighting, ASB, vehicle).

All three render off the **same** `lsoa_risk_package` payload — the only thing that changes
is the framing block on the page.

## Cut list (do not build for the hackathon)

- Counterfactual action simulator
- Decision audit trail (beyond a static "what changed" list)
- Human challenge mode
- Live-events lane (keep the code, hide the surface)
- Multi-LLM cross-review
- iOS app polish

## Sequenced execution

1. **Contract pass** — add `pricingGuidance`, rename `violent` → `personal`, add `lsoa`
   to `regionType`. Update `data_samples/`, frontend types, backend schemas, tests.
2. **Data spike** — pull one month for one force (Met Police) into Databricks; resolve to
   LSOA; produce one real `lsoa_risk_package` row end-to-end.
3. **Frontend reframe** — UK copy, £ units, persona toggle wired to the new field.
4. **Evaluation harness** — notebook + numbers in `EVALUATION.md`.
5. **Genie space + 5 saved questions** — scalability points, ~1 hour of work.
6. **Demo script + slide** — one slide per rubric criterion, mapped to a screen.

Anything past step 4 is bonus. Steps 1–4 are the minimum viable submission.

## Open questions for the team

- Which forces do we ship in the demo? Recommend **Met Police only** for the demo, with the
  pipeline parameterised to add the other 42 forces without code changes.
- Do we want a £ pricing example in the report, or a relative multiplier only? The brief
  says "pricing guidance" — relative multiplier is defensible and avoids implying we know
  the underwriter's base rate.
- Are we comfortable using IMD 2019 as a contextual feature given its age? It is still the
  current official IMD, but call it out in the Trust Passport.
