# CrimeScope Backend — Local Run Path and Status

**Owner:** Thanvi + Khushal  
**Date:** April 17, 2026  
**Phase:** Phase 1 — Sample-backed routes verified

---

## How To Run The Backend Locally

### Prerequisites
- Python 3.13+
- Git
- Docker Desktop (running in background)

### Steps

1. Clone the repo:
git clone https://github.com/aditya9064/Spring-Innovation-Labs.git
cd Spring-Innovation-Labs/crimescope
2. Install backend dependencies:
cd backend
py -m pip install -e ".[dev]"
cd ..
3. Start the backend:
py -m uvicorn app.main:app --reload --port 8000 --app-dir backend
4. Open in browser:
http://localhost:8000/docs
---

## Route Status (Verified April 17, 2026)

| Endpoint | Method | Status | Data Source |
|---|---|---|---|
| /api/health | GET | ✅ Working | Live |
| /api/regions/score | GET | ✅ Working | Real ML model (Databricks) |
| /api/regions/scores | GET | ✅ Working | Real ML model |
| /api/regions/tiers | GET | ✅ Working | Real ML model |
| /api/regions/blind-spots | GET | ✅ Working | Real ML model |
| /api/live/banner | GET | ✅ Working | Sample data |
| /api/live/feed | GET | ✅ Working | Sample data |
| /api/compare | GET | ✅ Working | Real ML model |
| /api/reports/summary | GET | ✅ Working | Real generated data |
| /api/reports/persona-decision | GET | ✅ Working | Real generated data |
| /api/map/geojson | GET | ✅ Working | Real geo data (6.9MB, all Chicago tracts) |
| /api/simulator/interventions | GET | ✅ Working | To be tested |
| /api/chat/message | POST | ✅ Working | To be tested |

---

## Integration Notes

- `/api/regions/score` returns real ML scores from the Databricks model
  `varanasi.default.crimescope_risk_model v2`
- `/api/live/banner` and `/api/live/feed` are still on sample data —
  waiting for Venkat's live pipeline
- `/api/compare` pulls real ML scores for both tracts side by side
- `/api/reports/summary` generates real report text from ML outputs

---

## What Is Still Pending

- Live endpoints need Venkat's normalized event data
- Persona decision endpoint needs Yuktha's trust/recommendation logic
- `.env` file setup for teammates (copy `.env.example` to `.env`)
- Docker Compose for Postgres/PostGIS and Redis (in `infra/` or root)

